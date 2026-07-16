#!/usr/bin/env python3
"""analyze_multi_imu.py - cross-sensor coherence + noise check for the 5-IMU
mux bench capture (Phase 3/4, data/phase3-4_five_imu_gyro/movement_test.csv).

The rig is 5 MPU-6050s glued flat to the same rigid breadboard, all read
through one PCA9548A mux channel-by-channel. If the mux/wiring is sound, all
five should report (approximately) the same angular velocity at every instant,
because they share one rigid body. This script quantifies "approximately":

  1. Cross-sensor spread: at each timestamp, the std-dev across the 5 sensors'
     readings, per axis. Small during motion = the rig is behaving as one
     rigid body (mux isn't scrambling channels, no dead/duplicate sensor).
     This number bundles together sensor noise, physical misalignment, AND
     sequential-sampling skew (the 5 channels are NOT read simultaneously) -
     it is a "how well do they agree" number, not a pure noise floor.
  2. Pairwise correlation: Pearson r between IMU0 and each of IMU1-4 on the Y
     axis (the axis with the largest swings in this capture) across the whole
     run. High r confirms they captured the same physical motion, not five
     independent/garbage streams.
  3. Consecutive-sample noise: std-dev of frame-to-frame differences within
     the calmest stretch of the capture, per sensor. This is an upper bound on
     noise, not a clean bench figure - the rig was still settling, not
     perfectly stationary (see caveat in the CSV header).

Reads gyro-only data (gx,gy,gz in deg/s); no accel was logged in this capture.

Usage:
    python analyze_multi_imu.py ../data/phase3-4_five_imu_gyro/movement_test.csv
"""

import argparse
import csv
from pathlib import Path

import numpy as np


def load(path: Path):
    """Returns dict: sample_idx -> {sensor_id: (gx, gy, gz)}"""
    samples = {}
    with path.open(newline="") as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#"):
                continue
            idx, _host_time, sensor_id = int(row[0]), row[1], int(row[2])
            gx, gy, gz = (float(row[3]), float(row[4]), float(row[5]))
            samples.setdefault(idx, {})[sensor_id] = (gx, gy, gz)
    return samples


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    args = ap.parse_args()

    samples = load(args.csv)
    sensor_ids = sorted({sid for s in samples.values() for sid in s})
    idxs = sorted(i for i, s in samples.items() if len(s) == len(sensor_ids))
    n_dropped = len(samples) - len(idxs)

    # (n_samples, n_sensors, 3) array, sensor order = sensor_ids
    data = np.array([[samples[i][sid] for sid in sensor_ids] for i in idxs])

    print(f"Loaded {len(idxs)} complete samples across {len(sensor_ids)} sensors "
          f"(sensor_ids {sensor_ids}); {n_dropped} incomplete rows dropped.\n")

    # 1. Cross-sensor spread per axis, averaged over the whole run.
    axis_names = ["gx", "gy", "gz"]
    spread_per_sample = data.std(axis=1)          # (n_samples, 3)
    mean_spread = spread_per_sample.mean(axis=0)  # (3,)
    print("Cross-sensor spread (std across the 5 sensors, deg/s) - mean over run:")
    for name, val in zip(axis_names, mean_spread):
        print(f"  {name}: {val:.2f} deg/s")
    print("  (bundles sensor noise + physical misalignment + sequential-read skew)\n")

    # 2. Correlation: IMU0 (sensor_ids[0]) vs each other sensor, Y axis.
    ref = data[:, 0, 1]  # first sensor's gy series
    print("Pearson correlation vs. first sensor (Y axis, the dominant motion axis):")
    for i, sid in enumerate(sensor_ids[1:], start=1):
        r = np.corrcoef(ref, data[:, i, 1])[0, 1]
        print(f"  sensor {sensor_ids[0]} vs sensor {sid}: r = {r:.4f}")
    print()

    # 3. Consecutive-sample noise in the calmest stretch (all |g| < 4 deg/s).
    calm_mask = (np.abs(data) < 4.0).all(axis=(1, 2))
    calm_idxs = np.where(calm_mask)[0]
    if len(calm_idxs) > 3:
        calm = data[calm_idxs]
        frame_diff = np.diff(calm, axis=0)   # (n-1, n_sensors, 3)
        noise_std = frame_diff.std(axis=(0, 1))  # (3,) - pooled across sensors
        print(f"Frame-to-frame noise in calmest stretch ({len(calm_idxs)} samples, "
              f"all |gyro| < 4 deg/s), pooled across sensors:")
        for name, val in zip(axis_names, noise_std):
            print(f"  {name}: {val:.2f} deg/s (upper bound - rig was settling, not perfectly still)")
    else:
        print("No sufficiently calm stretch found for a noise estimate.")


if __name__ == "__main__":
    main()
