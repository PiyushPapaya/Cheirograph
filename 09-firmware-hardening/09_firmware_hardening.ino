/*
 * HandRig BLE v5 — 6-IMU live streamer, clone-robust + self-healing
 * Seeed XIAO nRF52840 SENSE
 *
 * Stage 09 = stage 08's v4 sketch plus four runtime-recovery fixes (WHAT v5
 * ADDS, at the end of this header). The BLE frame is byte-for-byte unchanged,
 * so tools/handrig_dashboard.html works with either.
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
 *   "+/-0x2000 linear ramp" garbage seen in this folder's CSV captures.
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
 *
 * ---------------------------------------------------------------------------
 * 2026-07-26 patch — BLE throughput collapse fixed
 *   All of the above was verified on hardware and correct; the read/init path
 *   was never the problem. First connect showed hz collapsing 50 -> 8.3 with
 *   write_us (time inside bleuart.write()) ballooning past 100 ms while
 *   read_us stayed flat at ~5.9 ms — the default peripheral BLE config (small
 *   ATT MTU + notification queue) couldn't drain 80 B/20 ms. Fixed with
 *   Bluefruit.configPrphBandwidth(BANDWIDTH_MAX) before begin(), a relaxed
 *   connection interval (12,24 instead of the spec-floor 6,12), and
 *   connect/disconnect callbacks that log the negotiated MTU/interval so this
 *   is verified by readback too, not just assumed fixed.
 *
 * ---------------------------------------------------------------------------
 * WHAT v5 ADDS (2026-10-19; written without hardware, NOT yet flashed)
 *   Found in the 2026-10-06 review: v4 could detect most faults but could
 *   only recover from some of them.
 *
 *  10. RUNTIME BUS RECOVERY  — i2cRecover() only ran inside initFinger() at
 *                              boot, so a bus that wedged mid-session stayed
 *                              dead until a reboot. Now if EVERY finger looks
 *                              dead for BUS_DEAD_FRAMES frames in a row, the
 *                              bus is unwedged and every finger re-initialised.
 *                              "Looks dead" must include an all-zero read, not
 *                              only a failed one: with SDA held low the nRF52
 *                              I2C peripheral sees every ACK bit as low (= ACK),
 *                              so writes "succeed" and reads return 0x00.
 *  11. HAND IMU RECOVERY     — serviceRecovery() started its loop at sid 1, so
 *                              the hand IMU (sid 0) was never re-initialised.
 *                              It is now, and a hard attempt power-cycles it
 *                              through its power pin.
 *  12. HAND READ CAN FAIL    — readSensor(0) went through readFloatAccelX() and
 *                              friends, which return a float and no error, so
 *                              it always returned true. It now does one burst
 *                              read with a byte-count check. The hand IMU is on
 *                              the separate internal bus Wire1 (the LSM6DS3
 *                              library maps Wire -> Wire1 on the Sense), so the
 *                              tcaDisable() v4 did before each hand read was
 *                              talking to the wrong bus and is gone.
 *  13. CHECKED BLE WRITE     — bleuart.write()'s return value was ignored. It
 *                              returns 0 if the frame was not sent in full; that
 *                              is now counted (tx_fail= on the report line), and
 *                              we no longer write before the dashboard has
 *                              subscribed (those writes fail by design). The
 *                              report line also prints the current MTU: under 83
 *                              an 80 B frame is split over two packets and the
 *                              second can be lost.
 *
 *   A sensor whose reads keep FAILING (not frozen, just failing) now also gets
 *   re-initialised: v4 only re-initialised sensors flagged stuck.
 *
 *   Not covered: if a device holds SCL (not SDA) low, the nRF52 Wire driver
 *   waits forever inside endTransmission() and loop() never runs again. Only a
 *   hardware watchdog reset gets out of that. Left as an open decision.
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
#define FAIL_FRAMES   50          // ~1 s of failed reads in a row = re-init that sensor
#define BUS_DEAD_FRAMES 5         // 100 ms of every finger dead at once = wedged bus
// ----------------------------------------

// LSM6DS3 (hand IMU) registers. Gyro X,Y,Z then accel X,Y,Z sit in 12
// consecutive bytes from 0x22, little-endian, so one burst read gets all six.
#define LSM_ADDR      0x6A
#define LSM_OUTX_L_G  0x22

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
uint16_t failRun[NUM_SENSORS]    = {0};    // consecutive failed reads

uint8_t  seq = 0;
uint32_t accReadUs = 0, accWriteUs = 0; uint16_t accN = 0;
uint32_t lastRecoverMs = 0;
uint8_t  busDeadRun = 0;                   // consecutive frames with every finger dead
uint16_t busRecoveries = 0;
uint32_t lastBusRecoverMs = 0;
uint16_t txFail = 0;                       // frames bleuart.write() did not fully send

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

// A live IMU at rest still reads ~1 g of gravity, so all six axes at exactly 0
// is never real data. It is what a read returns when SDA is stuck low (every
// bit clocks in as 0) or when the firmware zeroed a failed read.
bool allZero(const int16_t raw[6]){
  for(uint8_t k = 0; k < 6; k++) if(raw[k] != 0) return false;
  return true;
}

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
  return !allZero(raw);                            // (10) zeros = not a reading
}

/*
 * (12) Hand read with a real failure path. v4 called readFloatAccelX() etc.:
 * six separate transactions, each returning a float with no error, so a dead
 * hand IMU still produced a "successful" frame. Here: one 12-byte burst on
 * Wire1 (the Sense's internal IMU bus), checking that every byte arrived.
 * Scaling goes through the library's calcGyro()/calcAccel(), the same maths
 * readFloat*() used, so the numbers sent are unchanged from v4.
 */
bool readHand(int16_t raw[6]){
  uint8_t b[12];
  Wire1.beginTransmission(LSM_ADDR);
  Wire1.write(LSM_OUTX_L_G);
  if(Wire1.endTransmission(false) != 0) return false;
  if(Wire1.requestFrom((int)LSM_ADDR, 12) != 12) return false;
  for(uint8_t i = 0; i < 12; i++) b[i] = Wire1.read();

  int16_t g[3], a[3];
  for(uint8_t k = 0; k < 3; k++){
    g[k] = (int16_t)(((uint16_t)b[2*k + 1] << 8) | b[2*k]);       // bytes 0..5:  gyro
    a[k] = (int16_t)(((uint16_t)b[2*k + 7] << 8) | b[2*k + 6]);   // bytes 6..11: accel
  }
  for(uint8_t k = 0; k < 3; k++){
    raw[k]     = clampI16(mcuIMU.calcAccel(a[k]), ACC_SCALE);
    raw[k + 3] = clampI16(mcuIMU.calcGyro(g[k]),  GYR_SCALE);
  }
  return !allZero(raw);
}

inline int16_t clampI16(float v, float scale){
  long q = lroundf(v * scale);
  if(q >  32767) q =  32767;
  if(q < -32768) q = -32768;
  return (int16_t)q;
}

bool readSensor(uint8_t sid, int16_t raw[6]){
  if(sid == 0) return readHand(raw);
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

// (11) Hand IMU re-init. Soft = run the library's begin() again, which rewrites
// its config registers. Hard = also cut and restore the chip's power through
// its power pin first, the only full reset available for it.
bool initHand(bool hard){
#ifdef PIN_LSM6DS3TR_C_POWER
  if(hard){
    digitalWrite(PIN_LSM6DS3TR_C_POWER, LOW);  delay(20);
    digitalWrite(PIN_LSM6DS3TR_C_POWER, HIGH); delay(10);
  }
#endif
  return mcuIMU.begin() == 0;
}

// A sensor needs a re-init if its output froze (stuck) OR its reads keep
// failing. v4 only checked stuck, so a sensor that NACKed every read was
// simply left out of the mask forever.
bool needsRecovery(uint8_t sid){
  return present[sid] && (stuck[sid] || failRun[sid] >= FAIL_FRAMES);
}

// Re-init one sensor, rate-limited so a permanently dead channel cannot
// stall the sample loop. Costs ~30-250 ms when it fires; that shows up as a
// visible one-off rate dip, which is intentional — silent recovery hides a
// hardware problem you want to know about.
void serviceRecovery(){
  uint32_t now = millis();
  if(now - lastRecoverMs < RECOVER_MS) return;
  if(busDeadRun > 0) return;                    // whole bus is down: serviceBus() handles that
  for(uint8_t sid = 0; sid < NUM_SENSORS; sid++){   // (11) starts at 0 now: the hand too
    if(!needsRecovery(sid)) continue;
    lastRecoverMs = now;
    recoveries[sid]++;
    // soft re-init first (cheap); every 4th attempt escalate to a hard reset
    bool hard = (recoveries[sid] % 4 == 0);
    bool ok = (sid == 0) ? initHand(hard) : initFingerOnce(sid, CH[sid - 1], hard);
    Serial.print("# re-init sid "); Serial.print(sid);
    Serial.print(hard ? " (hard)" : " (soft)");
    Serial.println(ok ? " -> ok" : " -> FAILED");
    if(ok){ sameCount[sid] = 0; failRun[sid] = 0; }
    return;                                     // one per service tick
  }
}

/*
 * (10) Runtime bus recovery. All five fingers share one bus through the mux.
 * One finger dying is that finger's problem (serviceRecovery). ALL of them
 * dying in the same frames is the bus: almost always a slave that was reset
 * or glitched mid-byte and is still holding SDA low. Re-initialising fingers
 * one by one cannot fix that, since every transaction on the bus fails, so
 * unwedge the bus first (i2cRecover), then soft re-init every finger, since
 * a chip that was cut off mid-transaction may have lost its config too.
 *
 * Only the finger bus (Wire) is handled here. The hand IMU is on Wire1, so a
 * finger-bus wedge cannot take it down and it is not part of this check.
 */
void serviceBus(){
  if(busDeadRun < BUS_DEAD_FRAMES) return;
  uint32_t now = millis();
  if(now - lastBusRecoverMs < RECOVER_MS) return;
  lastBusRecoverMs = now;
  busRecoveries++;

  i2cRecover();
  uint8_t ok = 0, tried = 0;
  for(uint8_t sid = 1; sid < NUM_SENSORS; sid++){
    if(!present[sid]) continue;
    tried++;
    if(initFingerOnce(sid, CH[sid - 1], false)){ ok++; sameCount[sid] = 0; failRun[sid] = 0; }
  }
  busDeadRun = 0;
  Serial.print("# BUS: every finger dead for "); Serial.print(BUS_DEAD_FRAMES);
  Serial.print(" frames -> bus recovery #"); Serial.print(busRecoveries);
  Serial.print(", fingers re-init "); Serial.print(ok); Serial.print("/"); Serial.println(tried);
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
  uint8_t fingersPresent = 0, fingersDead = 0;
  int16_t raw[6];
  for(uint8_t sid = 0; sid < NUM_SENSORS; sid++){
    bool ok = present[sid] && readSensor(sid, raw);
    if(present[sid]){
      if(ok) failRun[sid] = 0;
      else if(failRun[sid] < 0xFFFF) failRun[sid]++;
      if(sid > 0){ fingersPresent++; if(!ok) fingersDead++; }
    }
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

  // (10) every finger failed in the same frame -> count toward a bus recovery
  if(fingersPresent > 0 && fingersDead == fingersPresent){
    if(busDeadRun < 0xFF) busDeadRun++;
  } else {
    busDeadRun = 0;
  }

  uint8_t ck = 0;                                    // (9) XOR checksum
  for(uint8_t i = 0; i < 79; i++) ck ^= buf[i];
  buf[79] = ck;

  uint32_t r1 = micros();
  // (13) Only write once the dashboard has subscribed to notifications (before
  // that every write returns 0 by design), and check the result: write()
  // returns the full length or 0. A 0 with the MTU under 83 can still mean the
  // first half of the frame went out; the dashboard's checksum rejects that one.
  if(Bluefruit.connected() && bleuart.notifyEnabled()){
    if(bleuart.write(buf, sizeof(buf)) != sizeof(buf)) txFail++;
  }
  uint32_t r2 = micros();
  accReadUs += (r1 - r0); accWriteUs += (r2 - r1); accN++;
}

/*
 * BLE throughput diagnosis (2026-07-26): the periodic report line already in
 * this sketch showed read_us flat (~5.9 ms, sensors/fusion are fine) while
 * write_us ballooned from 0 to 100ms+ and hz collapsed 50 -> 8.3 in lockstep.
 * That pins bleuart.write() itself as the bottleneck: it blocks until the
 * SoftDevice's notification queue has room, and the default peripheral config
 * (23 B ATT MTU, a tiny HVN queue, a short per-connection-event packet budget)
 * can't drain an 80 B frame every 20 ms (~4 KB/s). Fix is BLE link config, not
 * the sensor/fusion loop.
 */
void connect_callback(uint16_t conn_handle){
  BLEConnection* c = Bluefruit.Connection(conn_handle);
  // mtu here is usually still the 23 B default: the exchange that raises it
  // finishes after this callback. The 2 s report line shows the real value.
  Serial.print("# BLE connected: mtu(pre-exchange)="); Serial.print(c->getMtu());
  Serial.print(" interval="); Serial.print(c->getConnectionInterval() * 1.25f, 1);
  Serial.println(" ms");
}
void disconnect_callback(uint16_t conn_handle, uint8_t reason){
  Serial.print("# BLE disconnected, HCI reason=0x"); Serial.println(reason, HEX);
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

  // hand (onboard, on its own bus Wire1, not behind the mux). tcaDisable() is
  // for the finger bus: it starts the fingers' init with every channel off.
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

  // must be called BEFORE begin(): widens the MTU and the notification queue
  // so bleuart.write() has somewhere to put data instead of blocking on it.
  Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
  Bluefruit.begin(); Bluefruit.setTxPower(4); Bluefruit.setName(DEV_NAME);
  // (12,24) = 15-30 ms. Our ~4 KB/s need doesn't require the spec-floor 7.5 ms
  // interval this used to request — that aggressiveness bought nothing and
  // some host controllers renegotiate around it rather than honouring it.
  Bluefruit.Periph.setConnInterval(12, 24);
  Bluefruit.Periph.setConnectCallback(connect_callback);
  Bluefruit.Periph.setDisconnectCallback(disconnect_callback);
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
  serviceBus();
  serviceRecovery();

  uint32_t now = millis();
  if(now - rptT >= 2000){
    Serial.print("# link=");  Serial.print(Bluefruit.connected() ? "up" : "down");
    // (13) the MTU in effect NOW. The connect callback fires before the MTU
    // exchange finishes, so the value it logs is usually the 23 B default.
    if(Bluefruit.connected()){
      Serial.print(" mtu=");
      Serial.print(Bluefruit.Connection(Bluefruit.connHandle())->getMtu());
    }
    Serial.print(" hz=");     Serial.print(frames * 1000.0f / (now - rptT), 1);
    Serial.print(" read_us="); Serial.print(accN ? accReadUs / accN : 0);
    Serial.print(" write_us="); Serial.print(accN ? accWriteUs / accN : 0);
    Serial.print(" tx_fail="); Serial.print(txFail);
    Serial.print(" bus_rec="); Serial.print(busRecoveries);
    Serial.print(" stuck=");
    bool any = false;
    for(uint8_t sid = 0; sid < NUM_SENSORS; sid++)
      if(stuck[sid]){ Serial.print(sid); Serial.print(","); any = true; }
    if(!any) Serial.print("none");
    Serial.print(" failing=");
    any = false;
    for(uint8_t sid = 0; sid < NUM_SENSORS; sid++)
      if(present[sid] && failRun[sid] >= FAIL_FRAMES){ Serial.print(sid); Serial.print(","); any = true; }
    if(!any) Serial.print("none");
    Serial.println();
    frames = 0; rptT = now; accReadUs = accWriteUs = 0; accN = 0; txFail = 0;
  }
}
