# 02 — Single MPU-6050 Test (Direct I²C)

> *This folder's number is a flexible guide, not a permanent label. Rename or renumber as the real build dictates.*

**Phase:** 2

**Goal:** Wire one MPU-6050 (GY-521) directly to the XIAO's external I²C pins — no mux — and confirm raw accel + gyro readings over serial.

**"Done" looks like:**
- Sensor responds at 0x68; six raw values per line on serial.
- Tilting the module produces predictable axis changes.
- No I²C bus hangs or `0xFF` garbage reads.

**What this is not:** No mux, no fusion, no other sensors.

**Why it matters:** Proves the MPU-6050 driver and wiring before adding the multiplexer layer. If a sensor misbehaves later, you'll know whether to blame the mux or the sensor itself.
