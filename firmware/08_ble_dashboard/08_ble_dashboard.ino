/*
 * HandRig BLE v4 — 6-IMU live streamer, clone-robust + self-healing
 * Seeed XIAO nRF52840 SENSE
 *
 *   sensor 0    = onboard LSM6DS3TR-C (hand / palm reference)  @ 0x6A
 *   sensor 1..5 = finger IMUs via PCA9548A mux ch 0..4         @ 0x68
 *
 * ---------------------------------------------------------------------------
 * WHY v3 EXISTED (the original bug, 2026-07-19)
 *   The finger modules are clones reporting WHO_AM_I=0x72 (MPU-6500/9250
 *   family), not the genuine MPU-6050's 0x68. MPU6050_light talks to them but
 *   never does a proper reset/wake/enable-axes sequence, so several boot
 *   half-asleep and return FIXED register patterns — the "stuck 0x3F00" and
 *   "+/-0x2000 linear ramp" garbage seen in data/phase7_5_ble_diagnostics/.
 *   v3 dropped MPU6050_light for the fingers and drove them by raw I2C.
 *
 * WHAT v4 ADDS (and why each one is here)
 *   v3 wrote the right registers but *assumed* every write landed. Everything
 *   below closes a gap where a bad reading could still reach the dashboard
 *   looking like real data:
 *
 *   1. CHECKED WRITES        — every I2C write's ACK is tested. A NACKed
 *                              config write used to pass silently.
 *   2. CHECKED MUX SELECT    — if the PCA9548A NACKs, v3 kept going and wrote
 *                              finger N's config to whichever channel was
 *                              still latched. Now a failed select aborts.
 *   3. 6500-FAMILY RESET     — clones need more than PWR_MGMT_1=0x80: poll the
 *                              reset bit until it self-clears, then
 *                              SIGNAL_PATH_RESET + USER_CTRL.SIG_COND_RST, and
 *                              ACCEL_CONFIG_2 for the accel DLPF (a register
 *                              that does not exist on a real 6050).
 *   4. CONFIG READBACK       — after init we read the four config registers
 *                              back and compare. This is what actually proves
 *                              the chip is awake, not just that it ACKed.
 *   5. INIT RETRY            — 3 attempts per channel before giving up.
 *   6. RUNTIME STUCK WATCHDOG— the boot check only ever saw boot. A sensor that
 *                              freezes 10 minutes in was invisible. Now every
 *                              sensor's six raw int16s are compared frame to
 *                              frame; STUCK_FRAMES bit-identical frames in a
 *                              row = frozen, and the channel is dropped from
 *                              the validity mask and re-initialised live.
 *   7. I2C BUS RECOVERY      — a slave holding SDA low wedges the whole bus and
 *                              every sensor reads garbage forever. Bit-bang 9
 *                              clocks + STOP to release it.
 *   8. HONEST VALIDITY MASK  — v3 sent zeros for a failed read with the mask
 *                              bit still set, so the dashboard fused a 0g
 *                              gravity vector as if it were real. A sensor is
 *                              now only in the mask if THIS frame's read
 *                              actually succeeded and it is not stuck.
 *   9. FRAME CHECKSUM        — 0xAB alone is not a safe sync byte; it occurs
 *                              inside payload data all the time, so one lost
 *                              byte could false-sync the parser and produce a
 *                              whole screen of plausible-looking garbage. A
 *                              trailing XOR byte lets the dashboard reject it.
 *
 * ---------------------------------------------------------------------------
 * FRAME (80 B, little-endian)
 *   [0]      0xAB sync
 *   [1]      seq (wraps)
 *   [2..5]   t_ms  uint32
 *   [6]      validity mask, bit N set = sensor N's data in THIS frame is real
 *   [7..78]  6 x { int16 ax ay az gx gy gz }
 *   [79]     XOR checksum of bytes 0..78
 *
 *   accel int16 = g   * 8192      (+/-4 g)
 *   gyro  int16 = dps * 65.536    (+/-500 dps)
 *
 * SENSOR AXES (measured on the glove, 2026-07-19)
 *   fingers: -Y -> fingertip, +Z -> up
 *   hand:    reads az ~ -0.98 g lying flat palm-down, i.e. +Z points DOWN
 *   The remap into the viewer's frame lives in tools/handrig_dashboard.html,
 *   deliberately NOT here — keeping the firmware emitting raw sensor-frame data
 *   means every capture in data/ stays re-interpretable if the convention
 *   changes later.
 *
 * 3.3 V ONLY.
 */

#include <bluefruit.h>
#include <Wire.h>
#include <LSM6DS3.h>
#include <math.h>

// ---------------- config ----------------
#define TCA_ADDR      0x70
#define MPU_ADDR      0x68
#define SAMPLE_MS     20
#define DEV_NAME      "HandRig-6IMU"
#define ACC_SCALE     8192.0f     // +/-4 g    -> 8192 LSB/g
#define GYR_SCALE     65.536f     // +/-500 dps-> 65.536 LSB/(deg/s)
#define I2C_HZ        400000      // drop to 100000 if a channel is flaky
#define INIT_TRIES    3           // init attempts per channel at boot
#define STUCK_FRAMES  50          // ~1 s @ 50 Hz of bit-identical data = frozen
#define RECOVER_MS    2000        // min gap between live re-init attempts
// ----------------------------------------

// MPU register map. Shared across 6050 / 6500 / 9250 except where noted.
#define R_SMPLRT      0x19
#define R_CONFIG      0x1A
#define R_GYRO_CFG    0x1B
#define R_ACC_CFG     0x1C
#define R_ACC_CFG2    0x1D   // 6500/9250 accel DLPF. Reserved (harmless) on 6050.
#define R_ACCEL       0x3B
#define R_SIGPATH_RST 0x68
#define R_PWR1        0x6B
#define R_PWR2        0x6C
#define R_USER_CTRL   0x6A   // register 0x6A — unrelated to the LSM6DS3's 0x6A *address*
#define R_WHOAMI      0x75

const uint8_t NUM_SENSORS = 6;
const uint8_t NUM_FING    = 5;
const uint8_t CH[NUM_FING] = {0, 1, 2, 3, 4};   // sid 1..5 -> mux channel

LSM6DS3 mcuIMU(I2C_MODE, 0x6A);
BLEUart bleuart;

// ---- per-sensor state ----
bool     present[NUM_SENSORS] = {false};   // initialised OK at boot
bool     stuck[NUM_SENSORS]   = {false};   // watchdog tripped, data not trusted
uint8_t  whoami[NUM_SENSORS]  = {0};
int16_t  lastRaw[NUM_SENSORS][6] = {{0}};
uint16_t sameCount[NUM_SENSORS]  = {0};    // consecutive bit-identical frames
uint16_t recoveries[NUM_SENSORS] = {0};    // live re-inits performed

uint8_t  seq = 0;
uint32_t accReadUs = 0, accWriteUs = 0; uint16_t accN = 0;
uint32_t lastRecoverMs = 0;

// =========================================================================
// I2C plumbing
// =========================================================================

// Every helper returns success so callers can actually branch on failure —
// the whole v3 bug class was "the write silently didn't land".

bool tcaSelect(uint8_t ch){
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << ch);
  return Wire.endTransmission() == 0;
}
bool tcaDisable(){
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(0x00);
  return Wire.endTransmission() == 0;
}

bool wReg(uint8_t reg, uint8_t val){
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg); Wire.write(val);
  return Wire.endTransmission() == 0;
}

// ok=false means the device did not ACK — distinct from "it returned 0x00".
uint8_t rReg(uint8_t reg, bool* ok = nullptr){
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  if(Wire.endTransmission(false) != 0){ if(ok) *ok = false; return 0; }
  if(Wire.requestFrom((int)MPU_ADDR, 1) != 1){ if(ok) *ok = false; return 0; }
  if(ok) *ok = true;
  return Wire.read();
}

bool rBurst(uint8_t reg, uint8_t* buf, uint8_t n){
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  if(Wire.endTransmission(false) != 0) return false;
  if(Wire.requestFrom((int)MPU_ADDR, (int)n) != n) return false;
  for(uint8_t i = 0; i < n; i++) buf[i] = Wire.read();
  return true;
}

/*
 * Bus recovery. If a slave was reset mid-byte it can sit holding SDA low
 * forever; the master then sees a permanently "busy" bus and EVERY sensor
 * reads garbage — which looks exactly like six dead IMUs. The standard fix is
 * to release the peripheral and manually clock SCL until the slave finishes
 * the byte it thinks it is transmitting and lets go of SDA, then issue a STOP.
 */
void i2cRecover(){
#if defined(PIN_WIRE_SDA) && defined(PIN_WIRE_SCL)
  const uint8_t sda = PIN_WIRE_SDA, scl = PIN_WIRE_SCL;
#else
  const uint8_t sda = SDA, scl = SCL;
#endif
  Wire.end();
  pinMode(sda, INPUT_PULLUP);
  pinMode(scl, OUTPUT);
  for(uint8_t i = 0; i < 9 && digitalRead(sda) == LOW; i++){
    digitalWrite(scl, LOW);  delayMicroseconds(5);
    digitalWrite(scl, HIGH); delayMicroseconds(5);
  }
  // manual STOP: SDA low->high while SCL is high
  pinMode(sda, OUTPUT);
  digitalWrite(sda, LOW);  delayMicroseconds(5);
  digitalWrite(scl, HIGH); delayMicroseconds(5);
  digitalWrite(sda, HIGH); delayMicroseconds(5);
  Wire.begin();
  Wire.setClock(I2C_HZ);
}

// =========================================================================
// Finger IMU init — the clone-robust sequence
// =========================================================================

/*
 * Order matters here, and each step exists for a reason:
 *   PWR_MGMT_1 = 0x80        full device reset. On the 6500 family this bit
 *                            SELF-CLEARS when reset completes, so we poll it
 *                            instead of guessing a delay. The chip may NACK
 *                            while resetting, which is normal — tolerate it.
 *   SIGNAL_PATH_RESET        clears the gyro/accel/temp analog signal paths.
 *   USER_CTRL.SIG_COND_RST   clears the digital filter + FIFO state. Skipping
 *                            these two is how a chip ends up ACKing happily
 *                            while its output register is frozen.
 *   PWR_MGMT_1 = 0x01        wake (sleep bit clear), clock = gyro-X PLL, which
 *                            is more stable than the internal oscillator.
 *   PWR_MGMT_2 = 0x00        enable all 6 axes. THIS is the write MPU6050_light
 *                            omits, and the direct cause of the original bug.
 *   CONFIG / ACCEL_CONFIG_2  gyro + accel DLPF ~44 Hz. 0x1D is 6500-only; on a
 *                            genuine 6050 it is reserved and the write is a
 *                            harmless no-op, so we can send it unconditionally.
 */
bool initFingerOnce(uint8_t sid, uint8_t ch, bool hardReset){
  if(!tcaSelect(ch)) return false;              // (2) never write blind

  bool ack = false;
  uint8_t who = rReg(R_WHOAMI, &ack);
  whoami[sid] = who;                            // index by sid, not channel
  if(!ack) return false;

  if(hardReset){
    if(!wReg(R_PWR1, 0x80)) return false;
    // (3) poll DEVICE_RESET until it self-clears, max ~200 ms
    bool cleared = false;
    for(uint8_t i = 0; i < 40; i++){
      delay(5);
      bool a2 = false;
      uint8_t v = rReg(R_PWR1, &a2);
      if(a2 && !(v & 0x80)){ cleared = true; break; }
    }
    if(!cleared) return false;
    if(!wReg(R_SIGPATH_RST, 0x07)) return false;   // gyro+accel+temp path reset
    delay(10);
    if(!wReg(R_USER_CTRL,   0x01)) return false;   // SIG_COND_RST (bit4 I2C_IF_DIS stays 0!)
    delay(10);
  }

  if(!wReg(R_PWR1,     0x01)) return false;   // wake, PLL clock
  delay(10);
  if(!wReg(R_PWR2,     0x00)) return false;   // enable all axes  <-- the key write
  if(!wReg(R_CONFIG,   0x03)) return false;   // gyro DLPF ~44 Hz
  if(!wReg(R_ACC_CFG2, 0x03)) return false;   // accel DLPF ~44 Hz (6500 family)
  if(!wReg(R_SMPLRT,   0x04)) return false;   // 1 kHz/(1+4) = 200 Hz
  if(!wReg(R_GYRO_CFG, 0x08)) return false;   // FS_SEL=1  -> +/-500 dps
  if(!wReg(R_ACC_CFG,  0x08)) return false;   // AFS_SEL=1 -> +/-4 g
  delay(20);

  // (4) Read the config back. An ACK only proves something on the bus
  // answered; a matching readback proves THIS chip stored what we sent.
  bool a = false;
  uint8_t p1 = rReg(R_PWR1,     &a); if(!a) return false;
  uint8_t p2 = rReg(R_PWR2,     &a); if(!a) return false;
  uint8_t gc = rReg(R_GYRO_CFG, &a); if(!a) return false;
  uint8_t ac = rReg(R_ACC_CFG,  &a); if(!a) return false;

  if((p1 & 0x47) != 0x01) return false;   // sleep clear (bit6) + CLKSEL==1
  if((p2 & 0x3F) != 0x00) return false;   // all six axes enabled
  if((gc & 0x18) != 0x08) return false;   // gyro full scale
  if((ac & 0x18) != 0x08) return false;   // accel full scale
  return true;
}

bool initFinger(uint8_t sid, uint8_t ch){
  for(uint8_t t = 0; t < INIT_TRIES; t++){          // (5)
    if(initFingerOnce(sid, ch, true)) return true;
    delay(20);
    if(t == 0) i2cRecover();                        // (7) try unwedging once
  }
  return false;
}

// =========================================================================
// Reads
// =========================================================================

// Returns false if the read failed — caller must then leave the mask bit clear.
bool readFinger(uint8_t ch, int16_t raw[6]){
  if(!tcaSelect(ch)) return false;
  uint8_t b[14];
  if(!rBurst(R_ACCEL, b, 14)) return false;
  // registers are big-endian; bytes 6..7 are temperature and are skipped
  raw[0] = (int16_t)(((uint16_t)b[0]  << 8) | b[1]);
  raw[1] = (int16_t)(((uint16_t)b[2]  << 8) | b[3]);
  raw[2] = (int16_t)(((uint16_t)b[4]  << 8) | b[5]);
  raw[3] = (int16_t)(((uint16_t)b[8]  << 8) | b[9]);
  raw[4] = (int16_t)(((uint16_t)b[10] << 8) | b[11]);
  raw[5] = (int16_t)(((uint16_t)b[12] << 8) | b[13]);
  return true;
}

inline int16_t clampI16(float v, float scale){
  long q = lroundf(v * scale);
  if(q >  32767) q =  32767;
  if(q < -32768) q = -32768;
  return (int16_t)q;
}

bool readSensor(uint8_t sid, int16_t raw[6]){
  if(sid == 0){
    if(!tcaDisable()) return false;
    raw[0] = clampI16(mcuIMU.readFloatAccelX(), ACC_SCALE);
    raw[1] = clampI16(mcuIMU.readFloatAccelY(), ACC_SCALE);
    raw[2] = clampI16(mcuIMU.readFloatAccelZ(), ACC_SCALE);
    raw[3] = clampI16(mcuIMU.readFloatGyroX(),  GYR_SCALE);
    raw[4] = clampI16(mcuIMU.readFloatGyroY(),  GYR_SCALE);
    raw[5] = clampI16(mcuIMU.readFloatGyroZ(),  GYR_SCALE);
    return true;
  }
  return readFinger(CH[sid - 1], raw);
}

// =========================================================================
// Stuck detection
// =========================================================================

/*
 * A live MEMS IMU always dithers. At +/-4 g and 8192 LSB/g one LSB is 122 ug,
 * while the part's own noise is ~2-3 mg RMS — roughly 20 LSB. Gyro noise is a
 * few LSB too. So the probability that all six axes repeat BIT-IDENTICAL
 * values 50 frames running is effectively zero for a working sensor, even one
 * sitting motionless on a table. If it happens, the output registers are
 * frozen — which is precisely the failure the 2026-07-19 captures showed.
 *
 * This is a strictly stronger test than "is |a| about 1 g": the original stuck
 * thumb still reported a perfectly plausible ~1 g magnitude.
 */
bool updateStuck(uint8_t sid, const int16_t raw[6]){
  bool same = true;
  for(uint8_t k = 0; k < 6; k++){
    if(raw[k] != lastRaw[sid][k]){ same = false; break; }
  }
  for(uint8_t k = 0; k < 6; k++) lastRaw[sid][k] = raw[k];

  if(same){
    if(sameCount[sid] < 0xFFFF) sameCount[sid]++;
  } else {
    sameCount[sid] = 0;
    if(stuck[sid]){
      stuck[sid] = false;                       // recovered on its own
      Serial.print("# sid "); Serial.print(sid); Serial.println(" UNSTUCK");
    }
  }
  if(sameCount[sid] >= STUCK_FRAMES && !stuck[sid]){
    stuck[sid] = true;
    Serial.print("# sid "); Serial.print(sid);
    Serial.println(" STUCK (bit-identical output) -> dropping from mask, will re-init");
  }
  return stuck[sid];
}

// Re-init one stuck finger, rate-limited so a permanently dead channel cannot
// stall the sample loop. Costs ~30-250 ms when it fires; that shows up as a
// visible one-off rate dip, which is intentional — silent recovery hides a
// hardware problem you want to know about.
void serviceRecovery(){
  uint32_t now = millis();
  if(now - lastRecoverMs < RECOVER_MS) return;
  for(uint8_t sid = 1; sid < NUM_SENSORS; sid++){
    if(!present[sid] || !stuck[sid]) continue;
    lastRecoverMs = now;
    recoveries[sid]++;
    // soft re-init first (cheap); every 4th attempt escalate to a hard reset
    bool hard = (recoveries[sid] % 4 == 0);
    bool ok = initFingerOnce(sid, CH[sid - 1], hard);
    Serial.print("# re-init sid "); Serial.print(sid);
    Serial.print(hard ? " (hard)" : " (soft)");
    Serial.println(ok ? " -> ok" : " -> FAILED");
    if(ok) sameCount[sid] = 0;
    return;                                     // one per service tick
  }
}

// =========================================================================
// Boot diagnostic
// =========================================================================

/*
 * Classifies each channel into OK / STUCK / RAMP / BAD-ACCEL / DEAD. The RAMP
 * check is here because one of the original failures was ring_gx stepping by a
 * constant +/-0x2000 every frame: a perfectly constant delta is a digital
 * artifact, not motion. Real movement never produces an exactly linear ramp.
 */
void bootCheck(uint8_t sid){
  const uint8_t N = 24;
  int16_t raw[6], prev[6], firstDelta[6];
  bool anyChange = false, constDelta = true, haveDelta = false;
  float amagSum = 0; uint8_t good = 0;

  for(uint8_t i = 0; i < N; i++){
    if(!readSensor(sid, raw)){ delay(20); continue; }
    good++;
    amagSum += sqrtf((float)raw[0]*raw[0] + (float)raw[1]*raw[1] + (float)raw[2]*raw[2]) / ACC_SCALE;
    if(i > 0){
      int16_t d[6];
      bool ch = false;
      for(uint8_t k = 0; k < 6; k++){ d[k] = raw[k] - prev[k]; if(d[k] != 0) ch = true; }
      if(ch) anyChange = true;
      if(!haveDelta){ for(uint8_t k = 0; k < 6; k++) firstDelta[k] = d[k]; haveDelta = true; }
      else { for(uint8_t k = 0; k < 6; k++) if(d[k] != firstDelta[k]) constDelta = false; }
    }
    for(uint8_t k = 0; k < 6; k++) prev[k] = raw[k];
    delay(20);
  }

  Serial.print("#   sid "); Serial.print(sid);
  if(sid > 0){ Serial.print(" who=0x"); Serial.print(whoami[sid], HEX); }
  if(good == 0){ Serial.println("  -> DEAD (no successful read)"); return; }

  float amag = amagSum / good;
  Serial.print("  |a|="); Serial.print(amag, 2); Serial.print("g");

  if(!anyChange)                       Serial.println("  -> STUCK (bit-identical, output registers frozen)");
  else if(constDelta && haveDelta)     Serial.println("  -> RAMP (constant per-frame delta = digital artifact, not motion)");
  else if(amag < 0.7f || amag > 1.3f)  Serial.println("  -> BAD ACCEL (|a| not ~1 g while still)");
  else                                 Serial.println("  -> OK");
}

// =========================================================================
// Framing / BLE
// =========================================================================

void sendFrame(){
  uint8_t buf[80];
  buf[0] = 0xAB;
  buf[1] = seq++;
  uint32_t t = millis();
  buf[2] = t & 0xFF; buf[3] = (t >> 8) & 0xFF; buf[4] = (t >> 16) & 0xFF; buf[5] = (t >> 24) & 0xFF;

  uint32_t r0 = micros();
  uint8_t mask = 0, idx = 7;
  int16_t raw[6];
  for(uint8_t sid = 0; sid < NUM_SENSORS; sid++){
    bool ok = present[sid] && readSensor(sid, raw);
    if(ok && updateStuck(sid, raw)) ok = false;      // frozen -> not real data
    if(!ok) for(uint8_t k = 0; k < 6; k++) raw[k] = 0;
    else    mask |= (1 << sid);                      // (8) only real data is masked in
    for(uint8_t k = 0; k < 6; k++){
      buf[idx]     = raw[k] & 0xFF;
      buf[idx + 1] = (raw[k] >> 8) & 0xFF;
      idx += 2;
    }
  }
  buf[6] = mask;

  uint8_t ck = 0;                                    // (9) XOR checksum
  for(uint8_t i = 0; i < 79; i++) ck ^= buf[i];
  buf[79] = ck;

  uint32_t r1 = micros();
  if(Bluefruit.connected()) bleuart.write(buf, sizeof(buf));
  uint32_t r2 = micros();
  accReadUs += (r1 - r0); accWriteUs += (r2 - r1); accN++;
}

void startAdv(){
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();
  Bluefruit.Advertising.addService(bleuart);
  Bluefruit.Advertising.addName();
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);
  Bluefruit.Advertising.setFastTimeout(30);
  Bluefruit.Advertising.start(0);
}

// =========================================================================

void setup(){
  Serial.begin(115200);
  // bounded wait — never `while(!Serial)`, that hangs the glove on battery
  uint32_t t0 = millis(); while(!Serial && millis() - t0 < 1800){}

  Wire.begin(); Wire.setClock(I2C_HZ);
#ifdef PIN_LSM6DS3TR_C_POWER
  pinMode(PIN_LSM6DS3TR_C_POWER, OUTPUT);
  digitalWrite(PIN_LSM6DS3TR_C_POWER, HIGH);
  delay(5);
#endif

  // hand (onboard, not behind the mux)
  tcaDisable();
  mcuIMU.settings.gyroRange = 500;
  mcuIMU.settings.accelRange = 4;
  present[0] = (mcuIMU.begin() == 0);

  // fingers
  for(uint8_t i = 0; i < NUM_FING; i++) present[i + 1] = initFinger(i + 1, CH[i]);

  Serial.println("# ---- boot diagnostic (hold the glove flat and still) ----");
  uint8_t okCount = 0;
  for(uint8_t sid = 0; sid < NUM_SENSORS; sid++){
    if(present[sid]){ bootCheck(sid); okCount++; }
    else { Serial.print("#   sid "); Serial.print(sid);
           Serial.println("  -> NOT FOUND (no ACK / init or readback failed)"); }
  }
  Serial.print("# ");
  Serial.print(okCount); Serial.println("/6 sensors initialised.");
  Serial.println("# fingers may report WHO=0x68 (genuine 6050) or 0x70/0x71/0x72/0x73");
  Serial.println("# (6500/9250-family clone) — both are fine, v4 configures either.");
  Serial.println("# Anything not OK above is now ELECTRICAL (solder joint, pull-ups,");
  Serial.println("# mux channel wiring) — the firmware init path is verified by readback.");
  Serial.println("# ---------------------------------------------------------");

  Bluefruit.begin(); Bluefruit.setTxPower(4); Bluefruit.setName(DEV_NAME);
  Bluefruit.Periph.setConnInterval(6, 12);
  bleuart.begin(); startAdv();
  Serial.print("# advertising as "); Serial.println(DEV_NAME);
}

void loop(){
  static uint32_t next = 0, rptT = 0, frames = 0;
  if(next == 0){ next = millis(); rptT = millis(); }
  if((int32_t)(millis() - next) < 0) return;

  next += SAMPLE_MS;
  // after a recovery stall, resync instead of firing a burst of catch-up frames
  if((int32_t)(millis() - next) > (int32_t)(4 * SAMPLE_MS)) next = millis() + SAMPLE_MS;

  sendFrame(); frames++;
  serviceRecovery();

  uint32_t now = millis();
  if(now - rptT >= 2000){
    Serial.print("# link=");  Serial.print(Bluefruit.connected() ? "up" : "down");
    Serial.print(" hz=");     Serial.print(frames * 1000.0f / (now - rptT), 1);
    Serial.print(" read_us="); Serial.print(accN ? accReadUs / accN : 0);
    Serial.print(" write_us="); Serial.print(accN ? accWriteUs / accN : 0);
    Serial.print(" stuck=");
    bool any = false;
    for(uint8_t sid = 0; sid < NUM_SENSORS; sid++)
      if(stuck[sid]){ Serial.print(sid); Serial.print(","); any = true; }
    if(!any) Serial.print("none");
    Serial.println();
    frames = 0; rptT = now; accReadUs = accWriteUs = 0; accN = 0;
  }
}
