/*
 * Phase 5 — 6-IMU capture rig + per-sensor Madgwick fusion
 *   sensor 0    = onboard LSM6DS3TR-C (hand reference)      @ 0x6A
 *   sensor 1..5 = finger MPU-6050 clones via PCA9548A mux, channels 0..4 @ 0x68
 *
 * Builds on the Phase-1 capture rig. Adds:
 *   1. Still-calibration that logs gyro bias AND average accel per sensor.
 *   2. A standalone, IMU-only (no mag) Madgwick filter instance per sensor —
 *      6 independent orientation estimators, each seeded from its own
 *      calibration-window accel reading (not just identity), each with a
 *      two-stage beta (fast snap-in right after calibration, then a lower
 *      steady-state gain).
 *
 * Serial contract (CSV):
 *   millis,sensor_id,qw,qx,qy,qz,roll_deg,pitch_deg,yaw_deg[,ax,ay,az,gx,gy,gz]
 *   the trailing raw columns only appear if INCLUDE_RAW == 1.
 *   Lines starting with '#' are comments/metadata.
 *
 * Drift test procedure (see DOCUMENTATION.md):
 *   Set SUBTRACT_GYRO_BIAS to 0, hold every sensor still through calibration
 *   and for several minutes after, log yaw_deg per sensor, compute deg/min.
 *   Repeat with SUBTRACT_GYRO_BIAS = 1. Record both numbers per sensor.
 *   This is the "drift -> check calibration, not the filter" test.
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
#define SUBTRACT_GYRO_BIAS 1         // 1 = subtract measured bias live; 0 = raw
                                      // (flip this for the drift A/B test)
#define INIT_TRIES         3         // init attempts per sensor
#define LIVE_ACC_MIN       0.1f      // min |accel| sum (g) to count a live sensor
#define INCLUDE_RAW         0        // 1 = also print raw accel/gyro columns

#define BETA_INIT           2.0f     // Madgwick gain during snap-in window
#define BETA_STEADY         0.033f   // Madgwick gain once settled
#define CONVERGE_MS         1500     // snap-in window length after calib ends
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
double   aSum[6][3]  = {{0}};              // accel sum during calib, for init pose
uint32_t calN[6]     = {0};
float    biasG[6][3] = {{0}};
bool     applyBias   = false;

// ---- Madgwick state, one filter per logical sensor ----
float    quat[6][4]  = {{1, 0, 0, 0}};     // w,x,y,z — identity until seeded
float    beta[6]     = {0};
uint32_t convergeEndMs[6] = {0};
uint32_t lastUpdUs[6] = {0};

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

// =================== Madgwick (IMU-only, no mag) ===================
// Standard gradient-descent orientation filter (Madgwick, 2010). Each of
// the 6 sensors gets its own quat[sid]/beta[sid] state — they never share
// data, so a bad finger sensor can't pollute the others' orientation.

void quatNormalize(float q[4]) {
  float n = sqrtf(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3]);
  if (n < 1e-8f) { q[0] = 1; q[1] = q[2] = q[3] = 0; return; }
  float inv = 1.0f / n;
  q[0] *= inv; q[1] *= inv; q[2] *= inv; q[3] *= inv;
}

// Build an initial quaternion from a still accel reading: gives the filter
// a correct roll/pitch starting point instead of forcing it to fight its
// way there from identity (yaw is unobservable without a mag, left at 0).
void quatFromAccel(float ax, float ay, float az, float q[4]) {
  float norm = sqrtf(ax*ax + ay*ay + az*az);
  if (norm < 1e-6f) { q[0] = 1; q[1] = q[2] = q[3] = 0; return; }
  ax /= norm; ay /= norm; az /= norm;

  float roll  = atan2f(ay, az);
  float pitch = atan2f(-ax, sqrtf(ay*ay + az*az));
  float yaw   = 0.0f;

  float cr = cosf(roll * 0.5f),  sr = sinf(roll * 0.5f);
  float cp = cosf(pitch * 0.5f), sp = sinf(pitch * 0.5f);
  float cy = cosf(yaw * 0.5f),   sy = sinf(yaw * 0.5f);

  q[0] = cr*cp*cy + sr*sp*sy;   // w
  q[1] = sr*cp*cy - cr*sp*sy;   // x
  q[2] = cr*sp*cy + sr*cp*sy;   // y
  q[3] = cr*cp*sy - sr*sp*cy;   // z
  quatNormalize(q);
}

void quatToEuler(const float q[4], float &rollDeg, float &pitchDeg, float &yawDeg) {
  float w = q[0], x = q[1], y = q[2], z = q[3];
  float sinr_cosp = 2.0f * (w*x + y*z);
  float cosr_cosp = 1.0f - 2.0f * (x*x + y*y);
  rollDeg = atan2f(sinr_cosp, cosr_cosp) * RAD_TO_DEG;

  float sinp = 2.0f * (w*y - z*x);
  sinp = constrain(sinp, -1.0f, 1.0f);
  pitchDeg = asinf(sinp) * RAD_TO_DEG;

  float siny_cosp = 2.0f * (w*z + x*y);
  float cosy_cosp = 1.0f - 2.0f * (y*y + z*z);
  yawDeg = atan2f(siny_cosp, cosy_cosp) * RAD_TO_DEG;
}

// gx,gy,gz in rad/s; ax,ay,az any consistent unit (normalized inside); dt in s
void madgwickUpdate(float q[4], float gainBeta,
                     float gx, float gy, float gz,
                     float ax, float ay, float az, float dt) {
  float q0 = q[0], q1 = q[1], q2 = q[2], q3 = q[3];

  // rate of change of quaternion from gyroscope
  float qDot1 = 0.5f * (-q1*gx - q2*gy - q3*gz);
  float qDot2 = 0.5f * ( q0*gx + q2*gz - q3*gy);
  float qDot3 = 0.5f * ( q0*gy - q1*gz + q3*gx);
  float qDot4 = 0.5f * ( q0*gz + q1*gy - q2*gx);

  // only correct with accel if it's a valid, non-degenerate reading
  float aNorm = sqrtf(ax*ax + ay*ay + az*az);
  if (aNorm > 1e-6f) {
    ax /= aNorm; ay /= aNorm; az /= aNorm;

    // auxiliary variables to avoid repeated arithmetic
    float _2q0 = 2.0f*q0, _2q1 = 2.0f*q1, _2q2 = 2.0f*q2, _2q3 = 2.0f*q3;
    float _4q0 = 4.0f*q0, _4q1 = 4.0f*q1, _4q2 = 4.0f*q2;
    float _8q1 = 8.0f*q1, _8q2 = 8.0f*q2;
    float q0q0 = q0*q0, q1q1 = q1*q1, q2q2 = q2*q2, q3q3 = q3*q3;

    // gradient descent algorithm corrective step
    float s0 = _4q0*q2q2 + _2q2*ax + _4q0*q1q1 - _2q1*ay;
    float s1 = _4q1*q3q3 - _2q3*ax + 4.0f*q0q0*q1 - _2q0*ay - _4q1 + _8q1*q1q1 + _8q1*q2q2 + _4q1*az;
    float s2 = 4.0f*q0q0*q2 + _2q0*ax + _4q2*q3q3 - _2q3*ay - _4q2 + _8q2*q1q1 + _8q2*q2q2 + _4q2*az;
    float s3 = 4.0f*q1q1*q3 - _2q1*ax + 4.0f*q2q2*q3 - _2q2*ay;

    float sNorm = sqrtf(s0*s0 + s1*s1 + s2*s2 + s3*s3);
    if (sNorm > 1e-8f) {
      float inv = 1.0f / sNorm;
      s0 *= inv; s1 *= inv; s2 *= inv; s3 *= inv;
      qDot1 -= gainBeta * s0;
      qDot2 -= gainBeta * s1;
      qDot3 -= gainBeta * s2;
      qDot4 -= gainBeta * s3;
    }
  }

  q0 += qDot1 * dt;
  q1 += qDot2 * dt;
  q2 += qDot3 * dt;
  q3 += qDot4 * dt;

  q[0] = q0; q[1] = q1; q[2] = q2; q[3] = q3;
  quatNormalize(q);
}
// =====================================================================

// ---- read all 6, fuse, print CSV rows, optionally accumulate calib stats ----
void emitFrame(uint32_t ts, bool accumulate, bool fuse) {
  float a[3], g[3];
  for (uint8_t sid = 0; sid < 6; sid++) {
    if (!present[sid]) continue;
    readSensor(sid, a, g);

    float gCorr[3] = {g[0], g[1], g[2]};
    if (applyBias) {
      gCorr[0] -= biasG[sid][0];
      gCorr[1] -= biasG[sid][1];
      gCorr[2] -= biasG[sid][2];
    }

    if (accumulate) {
      for (uint8_t k = 0; k < 3; k++) { gSum[sid][k] += g[k]; gSqr[sid][k] += (double)g[k] * g[k]; }
      aSum[sid][0] += a[0]; aSum[sid][1] += a[1]; aSum[sid][2] += a[2];
      calN[sid]++;
    }

    if (fuse) {
      uint32_t nowUs = micros();
      float dt = (lastUpdUs[sid] == 0) ? (PERIOD_MS / 1000.0f)
                                        : (nowUs - lastUpdUs[sid]) / 1e6f;
      lastUpdUs[sid] = nowUs;
      if (dt <= 0 || dt > 0.2f) dt = PERIOD_MS / 1000.0f;   // clamp glitches

      // two-stage gain: fast snap-in right after calibration, then settle
      float useBeta = (millis() < convergeEndMs[sid]) ? BETA_INIT : BETA_STEADY;

      madgwickUpdate(quat[sid], useBeta,
                     gCorr[0] * DEG_TO_RAD, gCorr[1] * DEG_TO_RAD, gCorr[2] * DEG_TO_RAD,
                     a[0], a[1], a[2], dt);

      float roll, pitch, yaw;
      quatToEuler(quat[sid], roll, pitch, yaw);

      Serial.print(ts);   Serial.print(',');
      Serial.print(sid);  Serial.print(',');
      Serial.print(quat[sid][0], 5); Serial.print(',');
      Serial.print(quat[sid][1], 5); Serial.print(',');
      Serial.print(quat[sid][2], 5); Serial.print(',');
      Serial.print(quat[sid][3], 5); Serial.print(',');
      Serial.print(roll, 2);  Serial.print(',');
      Serial.print(pitch, 2); Serial.print(',');
      Serial.print(yaw, 2);
#if INCLUDE_RAW
      Serial.print(',');
      Serial.print(a[0], 4); Serial.print(',');
      Serial.print(a[1], 4); Serial.print(',');
      Serial.print(a[2], 4); Serial.print(',');
      Serial.print(gCorr[0], 2); Serial.print(',');
      Serial.print(gCorr[1], 2); Serial.print(',');
      Serial.print(gCorr[2], 2);
#endif
      Serial.println();
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

// seed each sensor's quaternion from its own average still-accel reading,
// and arm the fast-converge window
void seedOrientations() {
  Serial.println("# ---- seeding orientation from calibration-window accel ----");
  for (uint8_t sid = 0; sid < 6; sid++) {
    if (!present[sid] || calN[sid] == 0) continue;
    float ax = aSum[sid][0] / calN[sid];
    float ay = aSum[sid][1] / calN[sid];
    float az = aSum[sid][2] / calN[sid];
    quatFromAccel(ax, ay, az, quat[sid]);
    convergeEndMs[sid] = millis() + CONVERGE_MS;
    lastUpdUs[sid] = 0;
    Serial.print("# sensor "); Serial.print(sid);
    Serial.print(" seed_accel="); Serial.print(ax, 3); Serial.print(',');
    Serial.print(ay, 3); Serial.print(','); Serial.println(az, 3);
  }
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
  Serial.print("# SUBTRACT_GYRO_BIAS="); Serial.println(SUBTRACT_GYRO_BIAS);
  Serial.println("# units: quat unitless, roll/pitch/yaw deg");
  Serial.print("millis,sensor_id,qw,qx,qy,qz,roll_deg,pitch_deg,yaw_deg");
#if INCLUDE_RAW
  Serial.print(",ax,ay,az,gx,gy,gz");
#endif
  Serial.println();   // CSV header

  // ---- still-calibration phase (accumulate gyro bias + accel, no fusion yet) ----
  Serial.print("# calib_start hold_still_ms="); Serial.println(CALIB_MS);
  applyBias = false;
  uint32_t calEnd = millis() + CALIB_MS;
  uint32_t next   = millis();
  while ((int32_t)(millis() - calEnd) < 0) {
    if ((int32_t)(millis() - next) < 0) continue;
    next += PERIOD_MS;
    emitFrame(millis(), true, false);   // accumulate only, don't fuse/print yet
  }
  printBiasTable();
  applyBias = (SUBTRACT_GYRO_BIAS != 0);
  seedOrientations();
  Serial.println("# calib_end — fusion running now");
}

void loop() {
  static uint32_t next = 0, rptT = 0, frames = 0;
  if (next == 0) { next = millis(); rptT = millis(); }

  if ((int32_t)(millis() - next) < 0) return;   // not due yet
  next += PERIOD_MS;

  emitFrame(millis(), false, true);
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
