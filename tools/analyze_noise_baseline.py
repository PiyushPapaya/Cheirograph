#!/usr/bin/env python3
"""analyze_noise_baseline.py - pre-Phase-8 go/no-go noise QA check.

Takes a 60 s "flat and still" capture exported from tools/handrig_dashboard.html
(the existing #rec / Export CSV button — NOT the batch-capture export) and
reports, per sensor: gyro bias, gyro noise std, accel |a| deviation from 1 g,
a suspected-dropped-frame count, and a suspected-stuck-frame count. Thresholds
mirror the ones already encoded in finishCalibration() in
tools/handrig_dashboard.html, so this script and the live dashboard's
calibration "bad" flag agree on what counts as OK.

Expects the dashboard's wide raw-CSV format:
    # raw sensor frame (no axis remap, no bias correction)
    t_ms,hand_ax,hand_ay,hand_az,hand_gx,hand_gy,hand_gz,thumb_ax,...,pinky_gz

Dropped/stuck frames are not flagged in that CSV (the firmware's validity
mask isn't exported), so this script infers them from the data itself:
  - "dropped" (heuristic): |a| < 0.05 g for a sensor's block in a frame -- the
    firmware sends all-zero when its validity-mask bit was clear for that
    sensor, and a live IMU essentially never reads exactly 0 g on all three
    axes simultaneously.
  - "stuck" (heuristic): >= STUCK_RUN consecutive frames with bit-identical
    (to float precision) raw values for a sensor -- same test the firmware's
    own runtime watchdog uses (STUCK_FRAMES in the .ino), just re-applied
    here against the exported CSV instead of live registers.

Dropped/stuck frames are excluded from the bias/noise statistics so a few bad
frames can't quietly bias the "OK" numbers.

Usage:
    python analyze_noise_baseline.py handrig_raw_<timestamp>.csv
"""

import argparse
from pathlib import Path

import numpy as np

SENSOR_NAMES = ["hand", "thumb", "index", "middle", "ring", "pinky"]

# Mirrors finishCalibration()'s thresholds in tools/handrig_dashboard.html.
ACCEL_MAG_TOL = 0.25     # |am - 1| > this -> bad accel
MAX_BIAS_DPS = 40.0      # max |gyro mean| > this -> bad gyro
MAX_NOISE_DPS = 15.0     # max gyro std > this -> noisy

DROPPED_AMAG_THRESH = 0.05   # g; below this, treat the frame as a dropped/zeroed read
STUCK_RUN = 50                # consecutive bit-identical frames = stuck (matches STUCK_FRAMES)


def load(path: Path):
    """Returns (t_ms array, {sensor_name: Nx6 array of ax,ay,az,gx,gy,gz})."""
    with path.open(newline="") as f:
        lines = [ln.rstrip("\n") for ln in f if ln.strip()]
    lines = [ln for ln in lines if not ln.startswith("#")]
    if not lines:
        raise ValueError(f"{path}: no data rows found")
    header = lines[0].split(",")
    if header[0] != "t_ms":
        raise ValueError(f"{path}: unexpected header {header[:3]}... "
                          "(expected the dashboard's wide raw-CSV export)")

    cols_per_sensor = 6
    n_sensors = (len(header) - 1) // cols_per_sensor
    names = [header[1 + i * cols_per_sensor].rsplit("_", 1)[0] for i in range(n_sensors)]

    t = []
    data = [[] for _ in range(n_sensors)]
    for ln in lines[1:]:
        parts = ln.split(",")
        if len(parts) != len(header):
            continue
        try:
            vals = [float(x) for x in parts]
        except ValueError:
            continue
        t.append(vals[0])
        for i in range(n_sensors):
            off = 1 + i * cols_per_sensor
            data[i].append(vals[off:off + cols_per_sensor])

    return np.array(t), {names[i]: np.array(data[i]) for i in range(n_sensors)}


def find_dropped(arr):
    amag = np.linalg.norm(arr[:, 0:3], axis=1)
    return amag < DROPPED_AMAG_THRESH


def find_stuck(arr):
    stuck = np.zeros(len(arr), dtype=bool)
    if len(arr) < 2:
        return stuck
    same = np.all(arr[1:] == arr[:-1], axis=1)
    run = 0
    for i, s in enumerate(same):
        run = run + 1 if s else 0
        if run >= STUCK_RUN - 1:
            stuck[i - (STUCK_RUN - 2):i + 2] = True
    return stuck


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    args = ap.parse_args()

    t, sensors = load(args.csv)
    duration_s = (t[-1] - t[0]) / 1000.0 if len(t) > 1 else 0.0
    print(f"# {args.csv.name} - {len(t)} frames, {duration_s:.1f}s\n")

    header = (f"{'sensor':<8}{'n_ok':>6}{'dropped':>9}{'stuck':>7}   "
              f"{'aX':>7}{'aY':>7}{'aZ':>7}  {'|a|':>6}   "
              f"{'gX bias':>9}{'gY bias':>9}{'gZ bias':>9}   "
              f"{'gX std':>8}{'gY std':>8}{'gZ std':>8}  verdict")
    print(header)
    all_ok = True

    for name in SENSOR_NAMES:
        if name not in sensors:
            continue
        arr = sensors[name]
        dropped = find_dropped(arr)
        stuck = find_stuck(arr)
        bad = dropped | stuck
        ok = arr[~bad]
        n_ok = len(ok)

        if n_ok < 5:
            print(f"{name:<8}{n_ok:>6}{dropped.sum():>9}{stuck.sum():>7}   "
                  f"{'--- not enough clean samples ---':<70}  FAIL")
            all_ok = False
            continue

        a_mean = ok[:, 0:3].mean(axis=0)
        a_mag = np.linalg.norm(a_mean)
        g_mean = ok[:, 3:6].mean(axis=0)
        g_std = ok[:, 3:6].std(axis=0)
        max_bias = np.max(np.abs(g_mean))
        max_noise = np.max(g_std)

        verdict = "OK"
        if abs(a_mag - 1) > ACCEL_MAG_TOL:
            verdict = "BAD ACCEL"
            all_ok = False
        elif max_bias > MAX_BIAS_DPS:
            verdict = "BAD GYRO (bias)"
            all_ok = False
        elif max_noise > MAX_NOISE_DPS:
            verdict = "NOISY"
            all_ok = False
        elif dropped.sum() > 0 or stuck.sum() > 0:
            verdict = "OK (had drops/stuck)"

        print(f"{name:<8}{n_ok:>6}{dropped.sum():>9}{stuck.sum():>7}   "
              f"{a_mean[0]:7.3f}{a_mean[1]:7.3f}{a_mean[2]:7.3f}  {a_mag:6.3f}   "
              f"{g_mean[0]:9.2f}{g_mean[1]:9.2f}{g_mean[2]:9.2f}   "
              f"{g_std[0]:8.2f}{g_std[1]:8.2f}{g_std[2]:8.2f}  {verdict}")

    print()
    if all_ok:
        print("GO - all sensors within calibration-agreed thresholds. Safe to start Batch Capture.")
    else:
        print("NO-GO — at least one sensor failed. Re-seat wiring / re-run boot diagnostic "
              "before starting Phase 8 capture (see CLAUDE.md gotchas for the usual causes).")


if __name__ == "__main__":
    main()
