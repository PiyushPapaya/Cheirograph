// Phase 1 — XIAO onboard IMU test (LSM6DS3TR-C)
//
// Reads the XIAO nRF52840 Sense's onboard 6-DOF IMU over its internal I2C bus
// and streams raw accelerometer + gyroscope values to serial as CSV. This is
// the "hand reference" sensor — every finger's relative orientation is measured
// against it, so it has to be proven trustworthy first.
//
// Library: Seeed_Arduino_LSM6DS3
//   https://github.com/Seeed-Studio/Seeed_Arduino_LSM6DS3
//
// I2C address: the onboard IMU answers at 0x6A (NOT 0x68). 0x68 is the address
// the external MPU-6050 finger sensors use — don't confuse the two.
//
// Line format (matches the project serial contract, raw variant):
//   aX,aY,aZ,gX,gY,gZ    accel in g, gyro in deg/s

#include <Wire.h>
#include "LSM6DS3.h"

// I2C_MODE = talk over I2C (as opposed to SPI); 0x6A = onboard IMU address.
LSM6DS3 myIMU(I2C_MODE, 0x6A);

void setup() {
  Serial.begin(115200);
  while (!Serial);  // wait for the USB serial monitor to attach

  // begin() returns 0 on success. Non-zero => the chip didn't answer on I2C.
  if (myIMU.begin() != 0) {
    Serial.println("IMU initialization failed!");
    while (1);  // halt — nothing downstream works without the IMU
  }

  Serial.println("IMU initialized");
  Serial.println("aX,aY,aZ,gX,gY,gZ");  // CSV header for the plotter/parser
}

void loop() {
  // Accelerometer, in g
  float aX = myIMU.readFloatAccelX();
  float aY = myIMU.readFloatAccelY();
  float aZ = myIMU.readFloatAccelZ();

  // Gyroscope, in degrees/second
  float gX = myIMU.readFloatGyroX();
  float gY = myIMU.readFloatGyroY();
  float gZ = myIMU.readFloatGyroZ();

  Serial.print(aX, 3);
  Serial.print(",");
  Serial.print(aY, 3);
  Serial.print(",");
  Serial.print(aZ, 3);
  Serial.print(",");
  Serial.print(gX, 3);
  Serial.print(",");
  Serial.print(gY, 3);
  Serial.print(",");
  Serial.println(gZ, 3);

  delay(50);  // ~20 Hz for eyeballing; the real fused loop targets 100 Hz later
}
