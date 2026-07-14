// Phase 2 diagnostic - RAW ACCELEROMETER ONLY
//
// Stripped-down sibling of ../../02_single_mpu6050_test.ino. Streams just the
// three accel axes, no timestamp, no id, no header - the smallest thing that
// isolates the accelerometer so it can be plotted on its own. This is the
// second of the two sketches flashed during the Phase 2 bench test; the capture
// it produced lives in data/phase2_single_mpu6050/accel_raw.csv.
//
// Output:  aX,aY,aZ   (g - so a flat, still sensor reads ~0,0,1)
// Library: MPU6050_light by rfetick
//
// Deliberately minimal - a scope, not the milestone. The contract-format sketch
// one level up is the real deliverable.

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
  mpu.calcOffsets();  // hold still: levels X/Y, leaves ~1g on Z
}

void loop() {
  mpu.update();

  Serial.print(mpu.getAccX());
  Serial.print(",");
  Serial.print(mpu.getAccY());
  Serial.print(",");
  Serial.println(mpu.getAccZ());

  delay(10);  // ~100 Hz
}
