# 01 - XIAO Onboard IMU Test

**Phase 1. Status: done.**

Once I knew the board was alive, the next question was whether its onboard IMU works. The XIAO nRF52840 Sense has an LSM6DS3 built in, and in this project it plays a specific role: it's the "hand reference" sensor. Every finger's orientation later gets measured relative to this one, so if this sensor is noisy or wrong, everything downstream is wrong too. Worth getting right early.

## What it does

Reads the onboard LSM6DS3 over its internal I²C bus and streams raw accelerometer and gyroscope values to serial as CSV: `millis, sensor_id, ax, ay, az, gx, gy, gz`. `sensor_id` is 0 here, the "hand" slot in the project's numbering. Fingers come later at 1 through 5.

## The one detail that trips people up

This chip answers at I²C address `0x6A`, not `0x68`. The external MPU-6050 finger sensors use `0x68`. It's easy to mix these up if you're moving fast, and if you do, you'll spend a while wondering why the "wrong" chip is responding.

## What "done" looks like

- Six clean values per line, stable, no I²C errors, no NaNs.
- Tilt the board and watch the accel numbers move the way you'd expect.
- `begin()` returns 0. If it doesn't, the chip never even ACKed on the bus. Check wiring before you go blaming your code.

## What this isn't

No fusion yet, no mux, no finger sensors. Just confirming this one chip is honest.

## Library

[Seeed_Arduino_LSM6DS3](https://github.com/Seeed-Studio/Seeed_Arduino_LSM6DS3), installed through the Arduino Library Manager (search "Seeed LSM6DS3").

## Proof

- [`01_xiao_imu_test.ino`](01_xiao_imu_test.ino), the sketch.
- [`story.md`](story.md), how this session actually went.
