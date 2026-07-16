# 04 — All 6 IMUs Raw at 100 Hz

> *This folder's number is a flexible guide, not a permanent label. Rename or renumber as the real build dictates.*

**Phase:** 4
**Status:** 🟡 partial — all 5 finger IMUs confirmed reading coherently through the mux (bench-verified 2026-07-16, see below). Onboard hand IMU (sensor 0) and accelerometer channels are **not yet in this sketch** — still open before this phase can be checked off.

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

**What this is not:** not fused, not at the target contract format, no hand IMU, no accelerometer.
