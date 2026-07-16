#!/usr/bin/env python3
"""analyze_calibration.py - per-sensor at-rest bias/noise check for the Phase 4
six-IMU capture (data/phase4_six_imu_capture/), full contract format
(millis,sensor_id,ax,ay,az,gx,gy,gz).

Unlike analyze_multi_imu.py (Phase 3/4 gyro-only bring-up), this reads the
full 8-column contract and reports, per sensor_id:
  - mean accel vector (should be ~1 g pointing wherever gravity is, if still)
  - mean + std of gyro (should be ~0 deg/s at rest - std is the noise floor)

Usage:
    python analyze_calibration.py ../data/phase4_six_imu_capture/capture_01_raw.csv
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

SENSOR_NAMES = {0: "hand (onboard)", 1: "finger 1", 2: "finger 2",
                3: "finger 3", 4: "finger 4", 5: "finger 5"}


def load(path: Path):
    rows = defaultdict(list)
    with path.open(newline="") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("millis"):
                continue
            parts = line.split(",")
            if len(parts) != 8:
                continue
            try:
                sid = int(parts[1])
                vals = [float(x) for x in parts[2:]]
            except ValueError:
                continue
            rows[sid].append(vals)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    args = ap.parse_args()

    rows = load(args.csv)
    print(f"{'sensor':<16}{'n':>5}  {'aX':>7}{'aY':>7}{'aZ':>7}  |a|   "
          f"{'gX mean':>9}{'gY mean':>9}{'gZ mean':>9}   "
          f"{'gX std':>8}{'gY std':>8}{'gZ std':>8}")
    for sid in sorted(rows):
        arr = np.array(rows[sid])
        if len(arr) == 0:
            continue
        a_mean = arr[:, 0:3].mean(axis=0)
        a_mag = np.linalg.norm(a_mean)
        g_mean = arr[:, 3:6].mean(axis=0)
        g_std = arr[:, 3:6].std(axis=0)
        name = SENSOR_NAMES.get(sid, str(sid))
        print(f"{name:<16}{len(arr):>5}  "
              f"{a_mean[0]:7.3f}{a_mean[1]:7.3f}{a_mean[2]:7.3f}  {a_mag:.3f} "
              f"{g_mean[0]:9.2f}{g_mean[1]:9.2f}{g_mean[2]:9.2f}   "
              f"{g_std[0]:8.2f}{g_std[1]:8.2f}{g_std[2]:8.2f}")


if __name__ == "__main__":
    main()
