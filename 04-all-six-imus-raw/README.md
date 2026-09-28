# 04 — All 6 IMUs Raw at 100 Hz

> *This folder's number is a flexible guide, not a permanent label. Rename or renumber as the real build dictates.*

**Phase:** 4
**Status:** 🟡 near-complete — the sketch now reads all 6 sensors (onboard hand IMU + 5 fingers), both accel and gyro, in the project's real serial contract, with a `millis()`-scheduled loop, a boot-time still-calibration window with a printed bias/noise table, and a periodic achieved-rate report (2026-07-17). Re-verified in a second bench capture the same day: measured rate is **~93.6-93.7 Hz, not ≥100 Hz** (see `data/phase4_six_imu_capture/capture_03_full_session.csv` and its README) — the 10 ms/tick budget doesn't hold once all 6 sequential mux-switch+read cycles are accounted for. Calibration window still wasn't genuinely still in this capture either (bias table std 38-84°/s). Finger 2 (mux ch1) had another brief intermittent dropout (~340 ms this time, vs. a full-session dropout previously) — pattern now points at a loose physical contact rather than a code fault. These are open items to close before Phase 4 is fully done, but not blockers for starting Phase 5.

**Goal:** Read all six IMUs (five MPU-6050s via mux + onboard LSM6DS3) in a single timed loop at 100 Hz. Stream raw data to serial in the stable CSV format. Add `tools/plot_raw.py` to plot it live.

**Serial data contract (raw):**
```
millis,sensor_id,ax,ay,az,gx,gy,gz
```
One line per sensor per sample. `sensor_id`: 0 = hand (onboard), 1–5 = finger (mux channels 0–4).

**"Done" looks like:**
- Loop period ≤ 10 ms (≥ 100 Hz) with no missed samples.
- All six sensor IDs appear in the serial output.
- `tools/plot_raw.py` shows six live traces.

**What this is not:** No fusion yet.

**Why it matters:** This is the last hardware-only milestone. If the 100 Hz budget holds here with all six reads, adding Madgwick won't break it.

---

## Bench result (2026-07-16)

`04_all_imus_raw.ino` — one `MPU6050_light` object per finger sensor, reused
across mux channels 0–4 (only one is ever electrically live at a time). A
`tcaSelect()` helper writes the one-hot channel byte to `0x70` before every
`begin()`/`update()` call — same pattern as `03_mux_channel_test/`, just now
looping over all five instead of one at a time. `scanChannels()` at boot
confirmed `0x68` present on channels 0–4 with no cross-talk.

**Not the target contract yet:** this sketch prints `IMUn [gx, gy, gz]` for
eyeballing, not the project's `millis,sensor_id,ax..gz` CSV line — that
rework, plus the onboard hand IMU and a `millis()`-scheduled 100 Hz loop
(currently `delay(20)`, ~50 Hz), is the next step before Phase 4 is done.

**Captured data + analysis:** a hand-motion bench capture is saved at
`data/phase3-4_five_imu_gyro/movement_test.csv` (gyro only, 41 samples).
`tools/analyze_multi_imu.py` computes cross-sensor spread, pairwise
correlation, and a rough noise estimate; `tools/plot_multi_imu.py` renders
`docs/media/phase3-4_five_imu_movement.png`. Findings:

- **Correlation vs. IMU0 (Y axis):** IMU1 r=0.999, IMU2 r=0.994, IMU3 r=0.986, IMU4 r=0.975 — all five tracked the same physical rotation, confirming no dead/duplicated/cross-talking channel.
- **Cross-sensor spread** (std across the 5 sensors per sample, averaged over the run): gx 0.61°/s, gy 1.44°/s, gz 0.90°/s. This bundles real sensor noise, physical misalignment on the breadboard, and sequential-read timing skew (the 5 channels are read one after another, not simultaneously) — it is not a clean noise figure.
- **Frame-to-frame noise** in the calmest stretch of the capture (9 samples, all axes < 4°/s): gx 1.97°/s, gy 0.69°/s, gz 0.50°/s — an upper bound, since the rig was settling rather than perfectly still. A proper still-calibration capture is still needed for a clean per-sensor bias table.

Bench photos: `docs/media/phase3-4_breadboard_top.jpg`, `docs/media/phase3-4_breadboard_angle.jpg`.
Interactive time-series + vector visualizer (source: `docs/media/phase3-4_visualizer.html`): https://claude.ai/code/artifact/42a29277-c048-45e2-adf7-df7abe635b00 (private link — share it from the artifact page if you want others to see it).

---

## 2026-07-17 update — full 6-sensor sketch (accel + gyro, real contract, calibration)

Replaced the gyro-only 5-finger sketch above with the complete Phase 4
implementation: reads onboard LSM6DS3 (sensor 0) + 5 finger MPU-6050s
(sensors 1-5), both accel and gyro, on a `millis()`-scheduled ~100 Hz loop,
emits the real `millis,sensor_id,ax,ay,az,gx,gy,gz` contract, runs a 10 s
still-calibration window at boot that accumulates gyro mean/std per sensor
and prints a bias table, and logs an achieved-rate report every 2 s
(`# rate_hz=...`) so "100 Hz" is a measured fact, not an assumption.

A bench capture from this sketch is saved (partial — see
`data/phase4_six_imu_capture/README.md`) and analyzed with
`tools/analyze_calibration.py`. Finding: the logged "still" calibration
window wasn't actually still (the hand sensor's gZ climbs from -10 to -35
deg/s across it), so the resting-bias numbers from that run aren't
trustworthy yet — a genuinely motionless capture is still needed. Finger 5
also shows elevated accel magnitude (1.246 g vs ~1.0-1.02 g for the others)
and gyro noise (std 5-13°/s vs 1-3°/s) worth checking in isolation.

**What this is not:** not fused, not at the target contract format, no hand IMU, no accelerometer.
