#!/usr/bin/env python3
"""plot_multi_imu.py - static multi-sensor time-series plot for a mux bench capture.

Five IMUs, three gyro axes each, over time - four numbers per sample (t, gx,
gy, gz) times five sensors. Rather than force that into one 3D/4D plot, this
draws it the way that's actually readable: one subplot per axis (gx, gy, gz),
five coloured lines each (one per sensor) sharing a time axis, plus a fourth
subplot showing the cross-sensor spread (std across the 5 sensors) over time -
the "how well do the five agree right now" signal. Stacking them with a shared
x-axis lets you correlate "big motion" with "big spread" directly by eye.

Usage:
    python plot_multi_imu.py ../data/phase3-4_five_imu_gyro/movement_test.csv \
        --save ../docs/media/phase3-4_five_imu_movement.png
"""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load(path: Path):
    samples = {}
    with path.open(newline="") as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#"):
                continue
            idx, sensor_id = int(row[0]), int(row[2])
            gx, gy, gz = float(row[3]), float(row[4]), float(row[5])
            samples.setdefault(idx, {})[sensor_id] = (gx, gy, gz)
    sensor_ids = sorted({sid for s in samples.values() for sid in s})
    idxs = sorted(i for i, s in samples.items() if len(s) == len(sensor_ids))
    data = np.array([[samples[i][sid] for sid in sensor_ids] for i in idxs])
    return idxs, sensor_ids, data  # data: (n_samples, n_sensors, 3)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    ap.add_argument("--save", type=Path, default=None)
    args = ap.parse_args()

    idxs, sensor_ids, data = load(args.csv)
    colors = plt.cm.tab10(np.linspace(0, 1, len(sensor_ids)))
    axis_names = ["gx", "gy", "gz"]

    fig, axes = plt.subplots(4, 1, figsize=(10, 11), sharex=True)

    for a, name in enumerate(axis_names):
        ax = axes[a]
        for i, sid in enumerate(sensor_ids):
            ax.plot(idxs, data[:, i, a], color=colors[i], label=f"IMU{sid - 1}", linewidth=1.2)
        ax.set_ylabel(f"{name} (deg/s)")
        ax.axhline(0, color="0.8", linewidth=0.6, zorder=0)
    axes[0].legend(loc="upper right", ncol=len(sensor_ids), fontsize=8)
    axes[0].set_title("Phase 3/4 - 5x MPU-6050 via PCA9548A mux, gyro during hand motion")

    spread = data.std(axis=1)  # (n_samples, 3)
    ax = axes[3]
    for a, name in enumerate(axis_names):
        ax.plot(idxs, spread[:, a], label=f"{name} spread", linewidth=1.2)
    ax.set_ylabel("cross-sensor\nstd (deg/s)")
    ax.set_xlabel("sample index")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Cross-sensor spread (std across the 5 IMUs per sample) - "
                 "spikes = fast motion outrunning sample sync", fontsize=9)

    fig.tight_layout()
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.save, dpi=130)
        print(f"saved {args.save}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
