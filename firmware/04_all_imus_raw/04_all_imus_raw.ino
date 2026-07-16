/*
 * Phase 3/4 (combined) — 5x MPU-6050 via PCA9548A I2C multiplexer on the
 * Seeed XIAO nRF52840 Sense. Reads gyroscope rate (deg/s) from all 5 finger
 * IMUs. This is the bench-verified version: all five channels ACK through the
 * mux and stream coherent data (see docs/log/ and the analysis in
 * tools/analyze_multi_imu.py + data/phase3-4_five_imu_gyro/).
 *
 * NOT in this sketch yet: the 6th sensor (XIAO onboard LSM6DS3, the hand
 * reference) and accelerometer readings. Phase 4 isn't fully closed until
 * those are added — see this folder's README "Status" for what's left.
 *
 * IMUs are CLONES (WHO_AM_I = 0x72, not the genuine 0x68) — use rfetick's
 * "MPU6050_light" library, which does NOT verify WHO_AM_I. Install via
 * Arduino Library Manager: search "MPU6050_light". Same clone/library fork
 * as Phase 2 — see DECISIONS.md (2026-07-14).
 *
 * WIRING (bench breadboard — see hardware/WIRING.md for the authoritative
 * copy and photos in docs/media/phase3-4_breadboard_*.jpg)
 *   XIAO D4 (SDA) -> PCA9548A SDA
 *   XIAO D5 (SCL) -> PCA9548A SCL
 *   XIAO 3V3      -> PCA9548A VIN  + every MPU VCC
 *   XIAO GND      -> PCA9548A GND  + every MPU GND
 *   PCA9548A A0/A1/A2 -> GND     (address 0x70)
 *   PCA9548A RST  -> 3V3         (active-low, hold high)
 *   MPU #0: SDA->SD0 SCL->SC0    MPU #1: SDA->SD1 SCL->SC1
 *   MPU #2: SDA->SD2 SCL->SC2    MPU #3: SDA->SD3 SCL->SC3
 *   MPU #4: SDA->SD4 SCL->SC4
 *   Every MPU AD0 -> GND         (address 0x68, all identical — the mux is
 *                                 the only thing that tells them apart)
 *
 * nRF52840 is 3.3 V ONLY. Power everything from 3V3, never 5V.
 */

#include <Wire.h>
#include <MPU6050_light.h>

#define TCA_ADDR 0x70                 // PCA9548A address (A0=A1=A2=GND)

const uint8_t NUM_IMU = 5;
const uint8_t CH[NUM_IMU] = {0, 1, 2, 3, 4};   // mux channel per IMU

// One MPU6050 object per sensor; all share Wire and sit at 0x68 (isolated by mux)
MPU6050 mpu0(Wire), mpu1(Wire), mpu2(Wire), mpu3(Wire), mpu4(Wire);
MPU6050* imu[NUM_IMU] = {&mpu0, &mpu1, &mpu2, &mpu3, &mpu4};

bool ok[NUM_IMU] = {false, false, false, false, false};

// ---- select ONE channel on the PCA9548A ----
void tcaSelect(uint8_t ch) {
  if (ch > 7) return;
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << ch);                // one-hot: bit n enables channel n
  Wire.endTransmission();
}

// ---- optional: map what's detected on each channel (great for debugging) ----
void scanChannels() {
  Serial.println("Scanning mux channels...");
  for (uint8_t ch = 0; ch < 8; ch++) {
    tcaSelect(ch);
    for (uint8_t a = 1; a < 127; a++) {
      if (a == TCA_ADDR) continue;
      Wire.beginTransmission(a);
      if (Wire.endTransmission() == 0) {
        Serial.print("  ch"); Serial.print(ch);
        Serial.print(" -> 0x"); Serial.println(a, HEX);   // expect 0x68 per channel
      }
    }
  }
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 3000) { }   // wait up to 3 s for USB serial

  Wire.begin();
  Wire.setClock(400000);              // 400 kHz; drop to 100000 if you see errors

  scanChannels();                     // comment out once wiring is confirmed

  // ---- init every IMU ----
  for (uint8_t i = 0; i < NUM_IMU; i++) {
    tcaSelect(CH[i]);
    byte status = imu[i]->begin();    // begin() ignores WHO_AM_I -> clones work
    ok[i] = (status == 0);
    Serial.print("IMU "); Serial.print(i);
    Serial.print(" (ch "); Serial.print(CH[i]); Serial.print("): ");
    Serial.println(ok[i] ? "OK" : "NOT FOUND");
  }

  // ---- calibrate offsets: KEEP THE WHOLE RIG COMPLETELY STILL ----
  Serial.println("Calibrating... hold all sensors still.");
  delay(1000);
  for (uint8_t i = 0; i < NUM_IMU; i++) {
    if (!ok[i]) continue;
    tcaSelect(CH[i]);
    imu[i]->calcOffsets(true, true);  // gyro + accel offsets
  }
  Serial.println("Ready.\n");
}

void loop() {
  // 1) refresh every sensor -- MUST select its channel before update()
  for (uint8_t i = 0; i < NUM_IMU; i++) {
    if (!ok[i]) continue;
    tcaSelect(CH[i]);
    imu[i]->update();                 // reads registers on the current channel
  }

  // 2) print gyro rates (deg/s). getGyro*() returns cached values -> no bus access,
  //    so no channel switching needed here.
  for (uint8_t i = 0; i < NUM_IMU; i++) {
    if (!ok[i]) { Serial.print("IMU"); Serial.print(i); Serial.print(":--  "); continue; }
    Serial.print("IMU"); Serial.print(i); Serial.print(" [");
    Serial.print(imu[i]->getGyroX(), 1); Serial.print(", ");
    Serial.print(imu[i]->getGyroY(), 1); Serial.print(", ");
    Serial.print(imu[i]->getGyroZ(), 1); Serial.print("]  ");
  }
  Serial.println();

  delay(20);                          // ~50 Hz output
}
