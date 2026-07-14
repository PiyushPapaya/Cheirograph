// Phase 2 diagnostic - RAW GYROSCOPE ONLY
//
// Stripped-down sibling of ../../02_single_mpu6050_test.ino. Streams just the
// three gyro axes, no timestamp, no id, no header - the smallest thing that
// isolates the gyroscope so it can be plotted on its own. This is one of the
// two sketches actually flashed during the Phase 2 bench test; the capture it
// produced lives in data/phase2_single_mpu6050/gyro_raw.csv.
//
// Output:  gX,gY,gZ   (degrees/second)
// Library: MPU6050_light by rfetick
//
// Keep this deliberately minimal - it is a scope, not the milestone. The
// contract-format sketch one level up is the real deliverable.

#include <Wire.h>
#include <MPU6050_light.h>

MPU6050 mpu(Wire);

void setup() {
  Serial.begin(115200);
  Wire.begin();

  byte status = mpu.begin();
  if (status != 0) {
    while (1);  // sensor didn't answer - halt
  }

  delay(1000);
  mpu.calcOffsets();  // hold still: zeroes gyro bias
}

void loop() {
  mpu.update();

  Serial.print(mpu.getGyroX());
  Serial.print(",");
  Serial.print(mpu.getGyroY());
  Serial.print(",");
  Serial.println(mpu.getGyroZ());

  delay(10);  // ~100 Hz
}
