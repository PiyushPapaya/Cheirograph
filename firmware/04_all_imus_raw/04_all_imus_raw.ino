/*
 * 6-IMU capture rig — Seeed XIAO nRF52840 SENSE
 *   sensor 0    = onboard LSM6DS3TR-C (hand reference)      @ 0x6A
 *   sensor 1..5 = finger MPU-6050 clones via PCA9548A mux, channels 0..4 @ 0x68
 *
 * Serial contract (CSV):  millis,sensor_id,ax,ay,az,gx,gy,gz
 *   accel = g,  gyro = deg/s.   Lines starting with '#' are comments/metadata.
 *
 * Libraries:
 *   "MPU6050_light" (rfetick)
 *   "Seeed Arduino LSM6DS3"  (class LSM6DS3 / I2C_MODE) — NOT Arduino_LSM6DS3,
 *                             NOT the stm32duino LSM6DS3. Remove any other
 *                             folder named "LSM6DS3" from your libraries dir.
 * Board: Seeed XIAO nRF52840 Sense.   3.3 V ONLY — never 5 V.
 */

#include <Wire.h>
#include <MPU6050_light.h>
#include <LSM6DS3.h>
#include <math.h>

// ---------------- config ----------------
#define TCA_ADDR           0x70
#define PERIOD_MS          10        // target sample period -> 100 Hz
#define CALIB_MS           10000     // still-calibration window (10 s)
#define REPORT_MS          2000      // achieved-rate report interval
#define SUBTRACT_GYRO_BIAS 0         // 1 = subtract measured bias live; 0 = raw
#define INIT_TRIES         3         // init attempts per sensor
#define LIVE_ACC_MIN       0.1f      // min |accel| sum (g) to count a live sensor
// ----------------------------------------

const uint8_t NUM_FING = 5;
const uint8_t CH[NUM_FING] = {0, 1, 2, 3, 4};   // mux channel per finger

// external finger MPUs (all 0x68, isolated by mux)
MPU6050 mpu0(Wire), mpu1(Wire), mpu2(Wire), mpu3(Wire), mpu4(Wire);
MPU6050* fing[NUM_FING] = {&mpu0, &mpu1, &mpu2, &mpu3, &mpu4};

// onboard reference IMU
LSM6DS3 mcuIMU(I2C_MODE, 0x6A);

// per logical sensor 0..5
bool     present[6]  = {false, false, false, false, false, false};
double   gSum[6][3]  = {{0}}, gSqr[6][3] = {{0}};
uint32_t calN[6]     = {0};
float    biasG[6][3] = {{0}};
bool     applyBias   = false;

// ---- mux control ----
void tcaSelect(uint8_t ch) {
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << ch);
  Wire.endTransmission();
}
void tcaDisable() {
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(0x00);
  Wire.endTransmission();
}

// ---- read one logical sensor into a[3] (g) and g[3] (deg/s) ----
void readSensor(uint8_t sid, float a[3], float g[3]) {
  if (sid == 0) {                       // onboard: deselect mux, read trunk 0x6A
    tcaDisable();
    a[0] = mcuIMU.readFloatAccelX(); a[1] = mcuIMU.readFloatAccelY(); a[2] = mcuIMU.readFloatAccelZ();
    g[0] = mcuIMU.readFloatGyroX();  g[1] = mcuIMU.readFloatGyroY();  g[2] = mcuIMU.readFloatGyroZ();
  } else {                              // finger: select its channel
    uint8_t f = sid - 1;
    tcaSelect(CH[f]);
    fing[f]->update();
    a[0] = fing[f]->getAccX();  a[1] = fing[f]->getAccY();  a[2] = fing[f]->getAccZ();
    g[0] = fing[f]->getGyroX(); g[1] = fing[f]->getGyroY(); g[2] = fing[f]->getGyroZ();
  }
}

// ---- init one sensor with retries; require a live (~1g) accel reading ----
bool initSensor(uint8_t sid) {
  float a[3], g[3];
  for (uint8_t t = 0; t < INIT_TRIES; t++) {
    bool began;
    if (sid == 0) {
      tcaDisable();
      mcuIMU.settings.gyroRange  = 500;     // ±500 dps  (match the fingers)
      mcuIMU.settings.accelRange = 4;       // ±4 g
      began = (mcuIMU.begin() == 0);
    } else {
      tcaSelect(CH[sid - 1]);
      began = (fing[sid - 1]->begin(1, 1) == 0);   // gyro ±500 dps, accel ±4 g
    }
    if (began) {
      delay(10);
      readSensor(sid, a, g);
      float m = fabs(a[0]) + fabs(a[1]) + fabs(a[2]);
      if (m > LIVE_ACC_MIN) return true;    // real device, actually sampling
    }
    delay(20);
  }
  return false;
}

// ---- read all 6, print CSV rows, optionally accumulate bias stats ----
void emitFrame(uint32_t ts, bool accumulate) {
  float a[3], g[3];
  for (uint8_t sid = 0; sid < 6; sid++) {
    if (!present[sid]) continue;
    readSensor(sid, a, g);
    if (applyBias) { g[0] -= biasG[sid][0]; g[1] -= biasG[sid][1]; g[2] -= biasG[sid][2]; }

    Serial.print(ts);   Serial.print(',');
    Serial.print(sid);  Serial.print(',');
    Serial.print(a[0], 4); Serial.print(',');
    Serial.print(a[1], 4); Serial.print(',');
    Serial.print(a[2], 4); Serial.print(',');
    Serial.print(g[0], 2); Serial.print(',');
    Serial.print(g[1], 2); Serial.print(',');
    Serial.println(g[2], 2);

    if (accumulate) {
      for (uint8_t k = 0; k < 3; k++) { gSum[sid][k] += g[k]; gSqr[sid][k] += (double)g[k] * g[k]; }
      calN[sid]++;
    }
  }
}

void printBiasTable() {
  Serial.println("# ---- gyro bias table (deg/s) from still window ----");
  Serial.println("# sensor_id,n,bias_x,bias_y,bias_z,std_x,std_y,std_z");
  for (uint8_t sid = 0; sid < 6; sid++) {
    if (!present[sid] || calN[sid] == 0) continue;
    Serial.print("# "); Serial.print(sid); Serial.print(','); Serial.print(calN[sid]);
    for (uint8_t k = 0; k < 3; k++) {
      double m = gSum[sid][k] / calN[sid];
      biasG[sid][k] = (float)m;
      Serial.print(','); Serial.print(m, 3);
    }
    for (uint8_t k = 0; k < 3; k++) {
      double m = gSum[sid][k] / calN[sid];
      double var = gSqr[sid][k] / calN[sid] - m * m;
      if (var < 0) var = 0;
      Serial.print(','); Serial.print(sqrt(var), 3);
    }
    Serial.println();
  }
  Serial.println("# --------------------------------------------------");
}

void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 3000) { }

  Wire.begin();
  Wire.setClock(400000);              // drop to 100000 if a channel misbehaves

#ifdef PIN_LSM6DS3TR_C_POWER
  pinMode(PIN_LSM6DS3TR_C_POWER, OUTPUT);
  digitalWrite(PIN_LSM6DS3TR_C_POWER, HIGH);   // enable onboard IMU power rail
  delay(5);
#endif

  // --- init all six with retry + liveness check ---
  present[0] = initSensor(0);                        // onboard
  for (uint8_t i = 0; i < NUM_FING; i++)
    present[i + 1] = initSensor(i + 1);              // fingers

  for (uint8_t sid = 0; sid < 6; sid++) {
    Serial.print("# sensor "); Serial.print(sid);
    Serial.println(present[sid] ? " OK" : " NOT FOUND");
  }
  Serial.println("# sensor 0 = onboard LSM6DS3, 1..5 = finger MPU-6050");
  Serial.println("# units: accel g, gyro deg/s");
  Serial.println("millis,sensor_id,ax,ay,az,gx,gy,gz");   // CSV header

  // ---- still-calibration phase (logged + bias table) ----
  Serial.print("# calib_start hold_still_ms="); Serial.println(CALIB_MS);
  applyBias = false;
  uint32_t calEnd = millis() + CALIB_MS;
  uint32_t next   = millis();
  while ((int32_t)(millis() - calEnd) < 0) {
    if ((int32_t)(millis() - next) < 0) continue;
    next += PERIOD_MS;
    emitFrame(millis(), true);
  }
  printBiasTable();
  Serial.println("# calib_end");

  applyBias = (SUBTRACT_GYRO_BIAS != 0);
}

void loop() {
  static uint32_t next = 0, rptT = 0, frames = 0;
  if (next == 0) { next = millis(); rptT = millis(); }

  if ((int32_t)(millis() - next) < 0) return;   // not due yet
  next += PERIOD_MS;

  emitFrame(millis(), false);
  frames++;

  uint32_t now = millis();
  if (now - rptT >= REPORT_MS) {
    float hz = frames * 1000.0f / (now - rptT);
    Serial.print("# rate_hz=");   Serial.print(hz, 1);
    Serial.print(" frames=");     Serial.print(frames);
    Serial.print(" over_ms=");    Serial.println(now - rptT);
    frames = 0; rptT = now;
  }
}
