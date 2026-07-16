# tools/ — Python Utility Scripts

Python 3 scripts for interacting with the glove over serial during development.
None are implemented yet — this README documents what will land here.

---

## Implemented

### `plot_imu_3d.py`  *(Phase 2)*
3D visualiser for a single-sensor raw capture. Reads a 3-column `x,y,z` CSV
(skips `#` comments and a header row), draws the samples as a time-coloured path
through 3D space, and either opens a window or saves a PNG.
- Dependency: `numpy`, `matplotlib`.
- Used to plot the Phase 2 accel/gyro bench captures → `docs/media/phase2_*_3d.png`.
```bash
python plot_imu_3d.py ../data/phase2_single_mpu6050/gyro_raw.csv --kind gyro
```

### `analyze_multi_imu.py`  *(Phase 3/4)*
Cross-sensor coherence + noise check for a multi-IMU mux bench capture.
Computes cross-sensor spread per axis, pairwise correlation against a
reference sensor, and a frame-to-frame noise estimate over the calmest
stretch of the run.
- Dependency: `numpy`.
```bash
python analyze_multi_imu.py ../data/phase3-4_five_imu_gyro/movement_test.csv
```

### `plot_multi_imu.py`  *(Phase 3/4)*
Static multi-sensor time-series plot: one subplot per gyro axis (gx/gy/gz),
one coloured line per sensor, plus a cross-sensor-spread subplot on a shared
time axis.
- Dependency: `numpy`, `matplotlib`.
```bash
python plot_multi_imu.py ../data/phase3-4_five_imu_gyro/movement_test.csv --save ../docs/media/phase3-4_five_imu_movement.png
```

---

## Planned scripts

### `plot_raw.py`
Live serial plotter for raw IMU data.
- Reads `millis,sensor_id,ax,ay,az,gx,gy,gz` lines.
- Plots the six channels (ax/ay/az/gx/gy/gz) per selected sensor_id.
- Dependency: `pyserial`, `matplotlib`.
- Added in Phase 4.

### `skeleton_viz.py`
3D hand-skeleton visualiser using relative quaternions.
- Reads `millis,sensor_id,qw,qx,qy,qz` lines (relative quaternions, Phases 6+).
- Renders a simplified 5-finger hand skeleton rotating in real time.
- Dependency: `pyserial`, `matplotlib` (3D).
- Added in Phase 6.

### `capture_data.py`
Labelled training-data capture tool.
- Prompts for a label (A–Z or custom), records N samples, saves to `data/<label>/`.
- Used in Phase 8 for Edge Impulse dataset collection.

---

## Serial data contract

Stable formats — do not change without updating the relevant parser in the same commit.

**Raw (Phases 1–4):**
```
millis,sensor_id,ax,ay,az,gx,gy,gz
```

**Fused / relative (Phases 5–):**
```
millis,sensor_id,qw,qx,qy,qz
```

`sensor_id`: 0 = hand (onboard XIAO), 1–5 = fingers (mux channels 0–4 = thumb–pinky).

---

## Setup

```bash
cd tools
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` is committed and pinned (Phase 2). Update it in the same commit
as any script that adds a dependency.
