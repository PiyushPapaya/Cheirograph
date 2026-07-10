# 01 — XIAO Onboard IMU Test

> *This folder's number is a flexible guide, not a permanent label. Rename or renumber as the real build dictates.*

**Phase:** 1

**Goal:** Read the XIAO nRF52840 Sense's onboard LSM6DS3 IMU via its internal I²C bus and stream raw accelerometer + gyroscope values to serial at 115 200 baud.

**"Done" looks like:**
- Six values per line: `ax, ay, az, gx, gy, gz` in a stable CSV format.
- No I²C errors, no NaN, consistent at ≥ 100 Hz.
- You can tilt the XIAO and watch the accel values change predictably.

**What this is not:** No fusion, no mux, no finger sensors — just the one onboard chip confirmed working.

**Why it matters:** Every relative-orientation calculation for every finger is subtracted from this sensor's reading. If the hand reference is noisy or wrong, all five finger poses are wrong. Prove this one first.
