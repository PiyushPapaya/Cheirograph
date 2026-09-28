// Phase 2 — Single MPU-6050 direct I2C test (milestone sketch)
//
// One MPU-6050 (GY-521) wired straight to the XIAO's external I2C bus (D4/D5),
// NO multiplexer yet. Goal: prove the sensor answers at 0x68 and that the raw
// accel + gyro readings are sane before the PCA9548A mux layer goes in. If a
// finger later misbehaves, this sketch is the reference for "one bare sensor,
// known good".
//
// Library: MPU6050_light by rfetick
//   Arduino IDE -> Library Manager -> "MPU6050_light"
//   (record the exact version you install in this folder's README)
// Why this library and not Adafruit_MPU6050: MPU6050_light does the gyro/accel
// bias calibration (calcOffsets) and the tilt math in one small package, which
// is all Phase 2 needs. The Adafruit stack is heavier and we don't use its
// event abstraction here. Logged in DECISIONS.md.
//
// I2C address: 0x68 (AD0 tied to GND). 0x6A is the XIAO's ONBOARD LSM6DS3 -
// different chip, different bus, don't confuse them.
//
// Line format (project serial contract, raw variant - see tools/README.md):
//   millis,sensor_id,aX,aY,aZ,gX,gY,gZ    accel in g, gyro in deg/s
// sensor_id 1 = the lone bench sensor. On the real glove 1..5 map thumb..pinky;
// here there is only one, so it reports as 1. The millis timestamp is not
// decoration - Madgwick needs a real dt later, and any "100 Hz" claim has to be
// checkable from the log, not assumed.

#include <Wire.h>
#include <MPU6050_light.h>

MPU6050 mpu(Wire);

const uint8_t SENSOR_ID = 1;  // lone bench sensor

void setup() {
  Serial.begin(115200);
  // Wait for the USB monitor to attach. BENCH-TEST ONLY: on battery with no USB
  // host this blocks forever - never copy this line into glove firmware.
  while (!Serial);

  Wire.begin();
  // 400 kHz: the whole-glove budget (6 sensors @ 100 Hz) needs fast-mode I2C.
  // A single bench sensor is happy at 100 kHz too, but we run the target speed
  // from the start so nothing surprises us when the mux arrives. See WIRING.md.
  Wire.setClock(400000);

  // begin() returns 0 on success; non-zero => the chip never ACKed on I2C.
  // Usual culprits: AD0 not grounded, SDA/SCL swapped, or missing pull-ups.
  byte status = mpu.begin();
  if (status != 0) {
    Serial.print("MPU6050 init failed, code ");
    Serial.println(status);
    while (1);  // halt - nothing downstream works without the sensor
  }

  // Hold the sensor DEAD STILL for this: calcOffsets measures gyro bias (should
  // read ~0 deg/s at rest) and accel bias (levels X/Y, leaves ~1g on Z). Drift
  // almost always traces back to skipping or fouling this step - see CLAUDE.md.
  Serial.println("Calibrating - keep the sensor still...");
  delay(1000);
  mpu.calcOffsets();  // gyro + accel

  Serial.println("millis,sensor_id,aX,aY,aZ,gX,gY,gZ");  // CSV header for the parser/plotter
}

void loop() {
  mpu.update();  // pull a fresh sample from the sensor

  // One CSV line per reading, matching the raw serial contract exactly.
  Serial.print(millis());        Serial.print(',');
  Serial.print(SENSOR_ID);       Serial.print(',');
  Serial.print(mpu.getAccX());   Serial.print(',');
  Serial.print(mpu.getAccY());   Serial.print(',');
  Serial.print(mpu.getAccZ());   Serial.print(',');
  Serial.print(mpu.getGyroX());  Serial.print(',');
  Serial.print(mpu.getGyroY());  Serial.print(',');
  Serial.println(mpu.getGyroZ());

  delay(10);  // ~100 Hz. Real rate is I2C- and print-bound; trust the log, not this.
}
