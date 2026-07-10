# 04 — All 6 IMUs Raw at 100 Hz

> *This folder's number is a flexible guide, not a permanent label. Rename or renumber as the real build dictates.*

**Phase:** 4

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
