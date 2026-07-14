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

---

## Implementation notes

- **Library:** [Seeed_Arduino_LSM6DS3](https://github.com/Seeed-Studio/Seeed_Arduino_LSM6DS3) —
  install via Arduino Library Manager (search "Seeed LSM6DS3") or drop the repo into `libraries/`.
- **I²C address is `0x6A`, not `0x68`.** The onboard LSM6DS3TR-C answers at `0x6A`;
  `0x68` is what the external MPU-6050 finger sensors use. Easy to mix up.
- **`begin()` returns 0 on success.** Non-zero means the chip never ACKed on the bus —
  check wiring/board package before blaming code.
- **This first version runs at ~20 Hz** (`delay(50)`), which is plenty for eyeballing that
  the values move sensibly when you tilt the board. The ≥ 100 Hz target above belongs to the
  final fused read loop, not this raw sanity read — don't over-optimise the test.

