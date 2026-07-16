#!/usr/bin/env python3
"""plot_6imu_3d.py - 3D accelerometer trajectory + animation for the Phase 4
six-IMU full-session capture (data/phase4_six_imu_capture/capture_02_full_session.csv).

Two outputs from the same data:

1. Static 3D trajectory (--save-static): each sensor's (ax,ay,az) path drawn
   as a time-coloured curve through 3D space, all six overlaid. This is the
   Phase 2 single-sensor plot (tools/plot_imu_3d.py) generalised to six
   sensors at once - lets you see which sensors moved together (a rigid rig
   should trace correlated, offset-but-parallel paths) and which one is
   flatlined (a dropped-out sensor sits frozen at a single point).

2. Animated 3D quiver (--save-gif): one arrow per sensor from the origin,
   redrawn frame by frame as the accelerometer vector changes - literally
   watching each sensor's "which way is down" reorient over time. A dropped
   sensor's arrow never moves.

Both are read-only visualisations of the raw accel channel; no filtering or
fusion applied.

Usage:
    python plot_6imu_3d.py ../data/phase4_six_imu_capture/capture_02_full_session.csv \
        --save-static ../docs/media/phase4_6imu_accel_3d.png \
        --save-gif ../docs/media/phase4_6imu_accel_3d.gif --stride 4
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

SENSOR_NAMES = {0: "hand", 1: "finger1", 2: "finger2", 3: "finger3", 4: "finger4", 5: "finger5"}
COLORS = {0: "#e8a33d", 1: "#5fb3a3", 2: "#6a8fd8", 3: "#9a7fd4", 4: "#d97a92", 5: "#c9c14a"}


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
                t = int(parts[0])
                sid = int(parts[1])
                vals = [float(x) for x in parts[2:5]]  # ax, ay, az only
            except ValueError:
                continue
            rows[sid].append((t, *vals))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    ap.add_argument("--save-static", type=Path, default=None)
    ap.add_argument("--save-gif", type=Path, default=None)
    ap.add_argument("--stride", type=int, default=4, help="use every Nth sample for the GIF (perf)")
    args = ap.parse_args()

    rows = load(args.csv)
    sensor_ids = sorted(rows)

    if args.save_static:
        fig = plt.figure(figsize=(9, 8))
        ax3d = fig.add_subplot(111, projection="3d")
        for sid in sensor_ids:
            arr = np.array(rows[sid])
            t, xyz = arr[:, 0], arr[:, 1:4]
            ax3d.plot(xyz[:, 0], xyz[:, 1], xyz[:, 2], color=COLORS[sid],
                      linewidth=0.8, alpha=0.85, label=SENSOR_NAMES[sid])
        ax3d.set_xlabel("aX (g)"); ax3d.set_ylabel("aY (g)"); ax3d.set_zlabel("aZ (g)")
        ax3d.set_title("Phase 4 - 6-sensor accelerometer trajectory\n"
                       "(a flatlined single point = that sensor dropped out)")
        ax3d.legend(loc="upper left", fontsize=8)
        fig.tight_layout()
        args.save_static.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.save_static, dpi=130)
        print(f"saved {args.save_static}")
        plt.close(fig)

    if args.save_gif:
        # Common timeline: use sensor 0's timestamps, nearest-match others.
        ref_t = np.array([r[0] for r in rows[0]])[::args.stride]
        series = {}
        for sid in sensor_ids:
            arr = np.array(rows[sid])
            t_s, xyz_s = arr[:, 0], arr[:, 1:4]
            idx = np.searchsorted(t_s, ref_t)
            idx = np.clip(idx, 0, len(t_s) - 1)
            series[sid] = xyz_s[idx]

        fig = plt.figure(figsize=(7, 7))
        ax3d = fig.add_subplot(111, projection="3d")
        ax3d.set_xlim(-1.5, 1.5); ax3d.set_ylim(-1.5, 1.5); ax3d.set_zlim(-1.5, 1.5)
        ax3d.set_xlabel("aX (g)"); ax3d.set_ylabel("aY (g)"); ax3d.set_zlabel("aZ (g)")
        quivers = []
        title = ax3d.set_title("")

        def update(frame):
            for q in quivers:
                q.remove()
            quivers.clear()
            for sid in sensor_ids:
                v = series[sid][frame]
                q = ax3d.quiver(0, 0, 0, v[0], v[1], v[2], color=COLORS[sid], linewidth=2)
                quivers.append(q)
            title.set_text(f"Phase 4 - accel vectors over time  t={int(ref_t[frame])} ms")
            return quivers

        anim = FuncAnimation(fig, update, frames=len(ref_t), interval=60, blit=False)
        args.save_gif.parent.mkdir(parents=True, exist_ok=True)
        anim.save(args.save_gif, writer=PillowWriter(fps=15))
        print(f"saved {args.save_gif}")
        plt.close(fig)


if __name__ == "__main__":
    main()
