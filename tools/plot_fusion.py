#!/usr/bin/env python3
"""plot_fusion.py - roll/pitch/yaw time-series visualization for the Phase 5
Madgwick fusion captures (data/phase5_madgwick_fusion/), fused contract
(millis,sensor_id,qw,qx,qy,qz,roll_deg,pitch_deg,yaw_deg[,...]).

Three stacked subplots (roll, pitch, yaw), one line per sensor, x-axis in
seconds since the first sample. This is the fused-orientation equivalent of
tools/plot_6imu_3d.py (which plots raw accel) - here the point is to see
what the filter output actually does over time: does roll/pitch sit flat
when the rig is still, does yaw creep, does anything jump or go flat
(a stuck/dead sensor's line would flatline).

Usage:
    python plot_fusion.py ../data/phase5_madgwick_fusion/capture_02_drift.csv \
        --save ../docs/media/phase5_drift_rpy.png --title "Drift test (held still)"
"""

import argparse
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

SENSOR_NAMES = {0: "hand", 1: "finger1", 2: "finger2", 3: "finger3", 4: "finger4", 5: "finger5"}
COLORS = {0: "#e8a33d", 1: "#5fb3a3", 2: "#6a8fd8", 3: "#9a7fd4", 4: "#d97a92", 5: "#c9c14a"}


def load(path: Path):
    rows = defaultdict(list)
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("millis"):
                continue
            parts = line.split(",")
            if len(parts) < 9:
                continue
            try:
                ms = int(parts[0])
                sid = int(parts[1])
                roll, pitch, yaw = float(parts[6]), float(parts[7]), float(parts[8])
            except ValueError:
                continue
            rows[sid].append((ms, roll, pitch, yaw))
    return rows


def unwrap_deg(values):
    """Unwrap a list of angles in degrees so +/-180 wraparound doesn't show
    as a vertical jump in the plot."""
    out = [values[0]]
    for v in values[1:]:
        out.append(out[-1] + ((v - out[-1] + 180) % 360 - 180))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    ap.add_argument("--save", type=Path, default=None)
    ap.add_argument("--title", default=None)
    args = ap.parse_args()

    rows = load(args.csv)
    if not rows:
        print("no data rows found")
        return

    t0 = min(r[0][0] for r in rows.values())

    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    labels = ["roll (deg)", "pitch (deg)", "yaw (deg)"]
    for sid in sorted(rows):
        r = rows[sid]
        t = [(ms - t0) / 1000.0 for ms, *_ in r]
        roll = unwrap_deg([v[1] for v in r])
        pitch = unwrap_deg([v[2] for v in r])
        yaw = unwrap_deg([v[3] for v in r])
        name = SENSOR_NAMES.get(sid, str(sid))
        color = COLORS.get(sid, "#888888")
        for ax, series in zip(axes, (roll, pitch, yaw)):
            ax.plot(t, series, label=name, color=color, linewidth=1)

    for ax, lab in zip(axes, labels):
        ax.set_ylabel(lab)
        ax.grid(alpha=0.3)
    axes[0].legend(loc="upper right", ncol=6, fontsize=8)
    axes[-1].set_xlabel("time (s)")
    fig.suptitle(args.title or f"Phase 5 fused orientation - {args.csv.name}")
    fig.tight_layout()

    if args.save:
        fig.savefig(args.save, dpi=130)
        print(f"saved {args.save}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
