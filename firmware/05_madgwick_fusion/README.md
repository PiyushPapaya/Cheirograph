# 05 — Madgwick Fusion Per IMU

> *This folder's number is a flexible guide, not a permanent label. Rename or renumber as the real build dictates.*

**Phase:** 5
**Status:** 🟡 second pass, bench-verified (2026-07-17) — `05_madgwick_fusion.ino` now seeds each sensor's orientation from its own calibration-window accel reading (instead of starting at identity and fighting its way to the correct pose), uses a two-stage β (fast snap-in right after calibration, lower steady-state gain), and prints roll/pitch/yaw alongside the quaternion. Bench-tested with a still-hold drift capture and a movement capture — see `data/phase5_madgwick_fusion/README.md` for full results. Still open before this phase fully closes: a proper `SUBTRACT_GYRO_BIAS` on/off A/B pair from the same sitting, and a multi-minute (not 31 s) drift run.

**Goal:** Run a Madgwick filter on each of the six IMUs' raw accel + gyro data. Output quaternions (w, x, y, z) to serial. Verify orientation holds under slow rotation without visible drift.

**Serial data contract (fused):**
```
millis,sensor_id,qw,qx,qy,qz,roll_deg,pitch_deg,yaw_deg[,ax,ay,az,gx,gy,gz]
```
The trailing raw columns only appear if `INCLUDE_RAW` is set to `1` (default `0`). Roll/pitch/yaw are derived from the quaternion for human-readable logging/debugging — the quaternion is still the value Phase 6 will consume for `q_rel = conj(q_hand) ⊗ q_finger`.

**"Done" looks like:**
- Six quaternion streams at 100 Hz, no NaN. *(Bench result: no NaNs seen in either capture, but rate is ~84-86 Hz, not 100 Hz — see below.)*
- Holding the XIAO flat: quaternion stays near (1, 0, 0, 0). *(Superseded — see "seeded orientation" below: identity is no longer the expected resting quaternion for a sensor that isn't mounted flat.)*
- Slow 360° rotation: heading returns to start within ~5°. *(Not yet tested — the two captures so far are a still-hold and a general movement test, not a controlled 360° rotation.)*
- Gyro-bias calibration runs at startup (sensor still for the calibration window). *(Confirmed working — see bias table results below.)*

**What this is not:** Not relative orientation yet — these are still absolute (per-sensor body-frame) quaternions.

**Gotcha:** Drift is almost always gyro bias, not a bug in the filter. If you see drift, recalibrate before touching Madgwick code.

## What changed in this pass

- **Accel-seeded initial orientation** (`quatFromAccel()`): instead of every filter starting at identity `(1,0,0,0)` and needing several seconds of accel correction to "fight" its way to the sensor's actual resting tilt, each filter is seeded directly from the average accel vector measured during its own calibration window. Yaw is left at 0 since it's unobservable from accel alone. This means "done" criterion #2 above (identity at rest) no longer applies as originally written — a correctly-seeded sensor mounted at an angle should read *its actual tilt*, not identity, even at rest.
- **Two-stage β** (`BETA_INIT = 2.0` for `CONVERGE_MS = 1500` ms after calibration, then `BETA_STEADY = 0.033`): a high gain right after seeding lets the filter snap in fast if the seed was slightly off (e.g. non-gravity acceleration during the calibration window), then drops to a low steady-state gain so noisy accelerometer readings during real use don't inject jitter into the orientation estimate. This is a standard trick for the "startup convergence vs. steady-state noise rejection" trade-off that a single fixed β can't satisfy at once. Logged as a design fork in DECISIONS.md (2026-07-17).
- **Calibration window kept at 10 s** (not the 2 s originally sketched below) — a 2 s window is too easy to disturb with hand-jitter before it closes; 10 s gives a cleaner bias estimate. Trade-off is a longer boot.

**Why Madgwick (not Mahony or a complementary filter):** see DECISIONS.md (2026-07-17). Short version — Madgwick's gradient-descent correction converges faster from a bad initial estimate and needs no manually-tuned integral gain, at the cost of being more expensive per sample; six filters at 100 Hz still leaves the nRF52840 headroom to spare, so the cost side of that trade-off doesn't bite here.

## Bench results (2026-07-17) — see `data/phase5_madgwick_fusion/README.md` for the full write-up

- **Calibration is finally trustworthy.** Gyro bias std is 0.05-0.35 deg/s across all six sensors in `capture_01_movement.csv`'s boot log — two orders of magnitude better than Phase 4's captures (std 38-84 deg/s), because this window was actually held still. Finger 5 remains the noisiest of the six (std ~3x the others) — a recurring finding across every capture so far, worth an isolated bench re-check.
- **No dropouts in either capture** — all 6 sensors report `OK` and hold a full, matched sample count through both the ~29.5 s movement run and the ~31.5 s drift run. Finger 2's intermittent dead-channel issue (seen twice in Phase 4) did not reproduce here — treat as "not observed this run," not "fixed," since it was already intermittent.
- **Drift (still-hold, ~31.5 s, `SUBTRACT_GYRO_BIAS=1`):** roll/pitch stayed essentially flat (≤ ~1.7 deg/min, mostly under 0.5) — expected, since Madgwick's accel correction anchors both against gravity every tick. Yaw crept at ~0.2-2.1 deg/min depending on sensor — small, and exactly the unbounded-yaw-drift behavior predicted for a 6-DOF IMU with no magnetometer (DECISIONS.md 2026-07-14). No same-session bias-off capture exists yet for a true paired A/B; that's the next thing to capture.
- **Rate dropped to ~84-86 Hz**, down from Phase 4's ~93.6 Hz — the added Madgwick math + Euler conversion + extra printed columns costs real time inside the 10 ms tick. Below the 100 Hz target; see the data README for candidate fixes (trim per-tick Serial.print calls first).

**Known open items carried in from Phase 4:** the achieved loop rate is now further from 100 Hz than before (was ~93.6 Hz, now ~84-86 Hz) because Phase 5 does strictly more work per tick. Finger 2's intermittent contact issue is unconfirmed either way (not fixed, not currently reproducing).
