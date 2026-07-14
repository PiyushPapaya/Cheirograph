#!/usr/bin/env python3
"""plot_imu_3d.py - 3D visualiser for a single-sensor raw MPU-6050 capture.

Reads a 3-column CSV (one axis triple per row) and draws the samples as a path
through 3D space, coloured by time so you can read the *order* of motion, not
just the cloud of points. Built for the Phase 2 bench captures in
data/phase2_single_mpu6050/, but it will plot any 3-column x,y,z log.

Why 3D and not three flat line charts: the three axes of an IMU are not
independent - a real hand motion is a single trajectory that sweeps through
(x, y, z) together. Seeing it as one curve makes the structure obvious (e.g. the
accelerometer path stays on a sphere of radius ~1 g because gravity has constant
magnitude; the gyro path loops out and back as the sensor is twisted and
returned). The raw numbers are never altered - this only draws them.

Usage:
    python plot_imu_3d.py <capture.csv> [--kind accel|gyro] [--save out.png]

    # examples
    python plot_imu_3d.py ../data/phase2_single_mpu6050/accel_raw.csv --kind accel
    python plot_imu_3d.py ../data/phase2_single_mpu6050/gyro_raw.csv  --kind gyro \
        --save ../docs/media/phase2_gyro_3d.png

Dependencies: numpy, matplotlib (see requirements.txt).
"""

import argparse
import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers the 3d projection)

# Per-kind cosmetics + axis labels. accel is in g, gyro in deg/s.
KINDS = {
    "accel": {"unit": "g", "title": "Accelerometer", "cmap": "viridis"},
    "gyro":  {"unit": "deg/s", "title": "Gyroscope", "cmap": "plasma"},
}


def load_xyz(path: Path):
    """Read a 3-column CSV, skipping '#' comment lines and a non-numeric header.

    Returns an (N, 3) float array. Kept deliberately dumb - no smoothing, no
    unit conversion - so what you plot is exactly what the sensor logged.
    """
    rows = []
    with path.open(newline="") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            try:
                rows.append([float(parts[0]), float(parts[1]), float(parts[2])])
            except (ValueError, IndexError):
                # header row (e.g. "ax,ay,az") or a malformed line - skip it
                continue
    if not rows:
        raise SystemExit(f"No numeric rows found in {path}")
    return np.asarray(rows, dtype=float)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path, help="3-column x,y,z capture file")
    ap.add_argument("--kind", choices=KINDS.keys(), default="accel",
                    help="which sensor produced this (sets labels/units)")
    ap.add_argument("--save", type=Path, default=None,
                    help="write a PNG here instead of opening a window")
    args = ap.parse_args()

    style = KINDS[args.kind]
    xyz = load_xyz(args.csv)
    x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    t = np.arange(len(xyz))  # sample index = time, since dt is fixed ~10 ms

    fig = plt.figure(figsize=(9, 8))
    ax = fig.add_subplot(111, projection="3d")

    # Faint line for continuity, points on top coloured by time so the eye can
    # follow the motion from start (dark) to end (bright).
    ax.plot(x, y, z, color="0.8", linewidth=0.6, zorder=1)
    p = ax.scatter(x, y, z, c=t, cmap=style["cmap"], s=8, zorder=2)

    ax.set_xlabel(f"X ({style['unit']})")
    ax.set_ylabel(f"Y ({style['unit']})")
    ax.set_zlabel(f"Z ({style['unit']})")
    ax.set_title(f"Cheirograph Phase 2 - {style['title']} 3D trajectory\n"
                 f"{args.csv.name}  ({len(xyz)} samples)")

    cbar = fig.colorbar(p, ax=ax, shrink=0.6, pad=0.1)
    cbar.set_label("sample index (time ->)")

    fig.tight_layout()
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.save, dpi=130)
        print(f"saved {args.save}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
