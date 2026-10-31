# tools/

Python scripts that plot and check captures from the glove, the live BLE
dashboard, and small test scripts that check the dashboard's logic. Everything
listed here exists and runs.

---

## Implemented

### `plot_imu_3d.py`  *(Phase 2)*
3D visualiser for a single-sensor raw capture. Reads a 3-column `x,y,z` CSV
(skips `#` comments and a header row), draws the samples as a time-coloured path
through 3D space, and either opens a window or saves a PNG.
- Dependency: `numpy`, `matplotlib`.
- Used to plot the Phase 2 accel/gyro bench captures.
```bash
python plot_imu_3d.py <capture.csv> --kind gyro
```

### `analyze_multi_imu.py`  *(Phase 3/4)*
Cross-sensor coherence + noise check for a multi-IMU mux bench capture.
Computes cross-sensor spread per axis, pairwise correlation against a
reference sensor, and a frame-to-frame noise estimate over the calmest
stretch of the run.
- Dependency: `numpy`.
```bash
python analyze_multi_imu.py ../04-all-six-imus-raw/movement_test.csv
```

### `analyze_calibration.py`  *(Phase 4)*
Per-sensor at-rest bias/noise check for the full 6-sensor contract format
(`millis,sensor_id,ax,ay,az,gx,gy,gz`). Reports mean accel vector + magnitude
and gyro mean/std per sensor_id — the mean accel magnitude close to 1 g is
the liveness check; a sensor stuck at exact zeros (dead mid-run) shows up
immediately.
- Dependency: `numpy`.
```bash
python analyze_calibration.py ../04-all-six-imus-raw/capture_02_full_session.csv
```

### `plot_6imu_3d.py`  *(Phase 4)*
3D accelerometer trajectory (static PNG) and animated 3D vector quiver (GIF)
for the six-sensor capture. The static plot overlays all six sensors' accel
paths, time-implicit in the curve; a sensor that dropped out shows as a
trajectory that stops dead at a point. The GIF redraws each sensor's
instantaneous accel vector as an arrow from the origin, frame by frame.
- Dependency: `numpy`, `matplotlib`, `pillow` (for the GIF writer).
```bash
python plot_6imu_3d.py ../04-all-six-imus-raw/capture_02_full_session.csv \
    --save-static ../04-all-six-imus-raw/6imu_accel_3d.png \
    --save-gif ../04-all-six-imus-raw/6imu_accel_3d.gif --stride 4
```

### `plot_multi_imu.py`  *(Phase 3/4)*
Static multi-sensor time-series plot: one subplot per gyro axis (gx/gy/gz),
one coloured line per sensor, plus a cross-sensor-spread subplot on a shared
time axis.
- Dependency: `numpy`, `matplotlib`.
```bash
python plot_multi_imu.py ../04-all-six-imus-raw/movement_test.csv --save ../04-all-six-imus-raw/five_imu_movement.png
```

---

### `handrig_dashboard.html`  *(Phase 7.5)*
Live BLE dashboard — no build step, no server, open the file directly in
Chrome or Edge (desktop or Android, needs Web Bluetooth). Connects to the
glove's Nordic UART service, decodes the 80-byte binary frame (sync, seq, timestamp, validity mask, six sensors, XOR checksum) streamed by
`08-ble-wireless-dashboard/08_ble_dashboard.ino`, runs Madgwick fusion
per-sensor client-side in JS, and renders a live Three.js 3D hand plus raw
accel/gyro trace canvases and a 20-second gyro-bias calibration per sensor.
Also has Record / Export CSV, a Noise Check (GO/NO-GO on a recorded buffer),
and Batch Capture (labelled static-pose samples, hand-relative quaternions,
A-Z coverage grid, crash-safe via localStorage). The look is monochrome
(see DECISIONS.md, 2026-10-06). `verify_*.mjs` in this folder test its pure logic.
Flags a sensor "bad" and freezes it in the 3D view if its calibrated accel
magnitude, gyro bias, or gyro noise falls outside a healthy-at-rest range,
so a broken finger sensor can't make the whole hand look broken.
Two Display controls wait on a hardware check. **Curl sign** picks how pitch
becomes the curl %: `|pitch|` (the old reading), `+pitch = curl` or
`-pitch = curl`. The signed modes read 0 for bending the other way. To choose,
curl one finger slowly and keep the mode where its % rises. **Model hand**
switches the 3D rig between the original right-hand model (thumb at +X) and a
left-hand model mirrored to match the glove. To choose, swing the thumb away
from the index and keep the model where it moves away too. Both are display
only and saved in localStorage. Record, Export CSV, Noise Check and Batch
Capture produce the same numbers whatever they are set to.
Self-healing (2026-10-31, not yet tried on the glove): per sensor it detects
stillness, tracks gyro bias slowly while still, raises the Madgwick beta in
proportion to the tilt error to snap back, and re-zeroes automatically when the
hand lies flat in the calibration pose. The header **HEALTH** cell shows `OK`,
`re-zero`, `slow link` (under 40 Hz) or `zero? <fingers>` for sensors that
clipped or dropped frames since their last zero. Batch Capture rejects a rep in
those states. The drawn hand is eased (40 ms) for smoothness. None of this
changes the raw CSV or the batch CSV format. It expects v5 firmware (gyro
±2000 °/s); v4 gyro reads 4x too large here.
Live accel-offset learning: the same sphere fit as `fit_accel_offsets.py`, run
in the browser. While a sensor is quiet (steady gyro, accel not creeping) for
0.5 s, one raw accel sample every 0.25 s feeds running least-squares sums (no
samples stored). It refits every 10 samples after 60 and only trusts the result
if the samples cover enough directions and the fit is a clean sphere (radius
within 0.05 of 1 g, rms under 0.03 g). A trusted offset is applied and saved in
localStorage (`gestura_acc_offset_v1`); the built-in constants are the defaults.
It needs about 15 s of still time over different hand orientations. Tested on
synthetic frames only (unverified on the glove). Batch Capture reps also need
every sensor's tilt error under 2 deg.
- Dependency: none (vanilla JS + Three.js from CDN).
- Frame format and the clone-IMU init bug this uncovered are documented in
  `08-ble-wireless-dashboard/README.md`.

---

### `check_dataset.py`  *(Phase 8)*
Quality gate for the dashboard's **Export batch CSV** files. Run it on every
export before it goes into training. It fails on anything that makes a row
unusable: a pre-2026-10-06 export (quaternions not hand-relative), NaN, a
non-unit or unpinned (`qw < 0`) quaternion, a sensor not reading ~1 g (zeros =
dropped), a sensor whose raw values repeat exactly between reps (frozen
register), or the same rows saved twice. Then it prints reps per letter per
session against the target (30 reps over 3 sessions). It reads the session
number from the renamed file name (`handrig_batch_<letter>_<session#>_<ts>.csv`).
Exit code 0 = pass, 1 = problems (`--strict` also fails on short coverage).
- Dependency: `numpy`. Shares the file loader `batch_io.py`.
```bash
python check_dataset.py path/to/exports/
```
`verify_check_dataset.py` plants each of those faults in synthetic data and
checks the gate catches every one (13 checks).

### `make_synthetic_batch.py`  *(Phase 8, testing only)*
Writes fake batch CSVs in the exact export format (10 rough fingerspelling
shapes, a random hand tilt per rep, a per-session yaw error on each finger's
quaternion) so the data tools can be built before real data exists. Every
file is marked `# SYNTHETIC` and `check_dataset.py` warns about it. Never mix
these into the real dataset.
```bash
python make_synthetic_batch.py --out synth/ --sessions 3 --reps 30
```

### `train_baseline.py`  *(Phase 9 prep)*
A k-nearest-neighbours baseline to compare Edge Impulse against. Compares three
feature sets built from the hand-relative quaternions: `quat` (raw, 20 numbers),
`dir` (the direction each finger points in the hand's frame, 15) and `curl`
(only the palm-ward component of that direction, 5, which yaw drift can't
touch). Reports accuracy on a random 80/20 split and with leave-one-session-out,
plus a confusion matrix and the most confused letter pairs. Leave-one-session-out
is the number to trust: the random split mixes reps from the same sitting.
- Dependency: `numpy`.
```bash
python train_baseline.py path/to/exports/
```
On synthetic data (illustration of the method only, NOT a glove result) the
pattern is: random split says 100 % at any yaw error; leave-one-session-out drops
from 100 % to ~87 % for `quat` as the per-session yaw error grows from 0 to 25°;
`curl` holds ~90 % regardless but can never separate U from V.

### `analyze_drift.py`  *(Phase 5)*
Roll/pitch/yaw drift in deg/min per sensor from a still fused capture
(`millis,sensor_id,qw,qx,qy,qz,roll,pitch,yaw`). Fits a line through each
unwrapped angle (skipping the first 2 s of filter snap-in) and reports the
slope. `--compare` prints two captures side by side, for the Phase 5 closing
test: one still run with `SUBTRACT_GYRO_BIAS 0`, one with `1`, same session.
- Dependency: `numpy`.
```bash
python analyze_drift.py bias_off.csv --compare bias_on.csv
```

### `analyze_motion_test.py`  *(Phase 8)*
Checks a dashboard raw CSV from a motion test (`09-firmware-hardening/motion-tests/`):
frame rate, dropped frames, clipped gyro samples (`--clip`, default 2000 °/s),
|a|, and the return error between the start hold and the end hold.
- Dependency: `numpy`.
```bash
python analyze_motion_test.py path/to/test.csv
```

### `fit_accel_offsets.py`  *(Phase 8)*
Sphere fit over quasi-static samples to find each sensor's accel zero-g offset
and radius. Used to get the pinky `ACC_OFFSET` in the dashboard.
- Dependency: `numpy`.
```bash
python fit_accel_offsets.py path/to/test.csv
```

## Dropped from the original plan

The first plan had three more Python scripts. The dashboard covers all of them, so they were never built:
- `plot_raw.py` (live serial plotter): replaced by the dashboard's live traces.
- `skeleton_viz.py` (3D hand from relative quaternions): replaced by the dashboard's 3D hand.
- `capture_data.py` (labelled capture): replaced by Batch Capture plus `check_dataset.py`.

---

## Serial data contract

Stable formats — do not change without updating the relevant parser in the same commit.

**Raw (Phases 1–4):**
```
millis,sensor_id,ax,ay,az,gx,gy,gz
```

**Fused (Phase 5):**
```
millis,sensor_id,qw,qx,qy,qz,roll_deg,pitch_deg,yaw_deg[,ax,ay,az,gx,gy,gz]
```

**BLE (Phase 7.5+):** 80-byte binary frames, documented in
`08-ble-wireless-dashboard/README.md`. The dashboard's CSV export records the
raw sensor frame; Batch Capture exports hand-relative quaternions.

`sensor_id`: 0 = hand (onboard XIAO), 1–5 = fingers (mux channels 0–4 = thumb–pinky).

---

## Setup

```bash
cd tools
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` is pinned. Update it in the same commit as any script that
adds a dependency. Note: it pins numpy 2.2.6, but the October scripts were
tested on 2.5.3 (open decision in `DECISIONS.md`).

Tests: `python verify_check_dataset.py`, and `node verify_*.mjs` for the
dashboard logic.
