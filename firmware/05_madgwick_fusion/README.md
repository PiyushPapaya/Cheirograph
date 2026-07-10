# 05 — Madgwick Fusion Per IMU

> *This folder's number is a flexible guide, not a permanent label. Rename or renumber as the real build dictates.*

**Phase:** 5

**Goal:** Run a Madgwick filter on each of the six IMUs' raw accel + gyro data. Output quaternions (w, x, y, z) to serial. Verify orientation holds under slow rotation without visible drift.

**Serial data contract (fused):**
```
millis,sensor_id,qw,qx,qy,qz
```

**"Done" looks like:**
- Six quaternion streams at 100 Hz, no NaN.
- Holding the XIAO flat: quaternion stays near (1, 0, 0, 0).
- Slow 360° rotation: heading returns to start within ~5°.
- Gyro-bias calibration runs at startup (sensor still for 2 s).

**What this is not:** Not relative orientation yet — these are still absolute quaternions.

**Gotcha:** Drift is almost always gyro bias, not a bug in the filter. If you see drift, recalibrate before touching Madgwick code.

**Key parameter:** Madgwick β (beta) — a higher value trusts the accelerometer more and converges faster but is more susceptible to dynamic acceleration noise. Start with β ≈ 0.1 and tune.
