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

Mounting correction (on by default, --no-mount-correction to disable):
The finger MPU-6050 breakout modules are plugged straight into the
breadboard (standing upright on their pin legs), while the XIAO (hand,
sensor 0) sits closer to flat. That ~90 degree difference in physical
mounting angle - not a sensor fault - is why raw finger pitch reads
~-75 to -80 deg while the hand reads ~0 deg even though everything sits on
the same breadboard (see DOCUMENTATION.md / DECISIONS.md, 2026-07-17).
This script applies a fixed +90 deg rotation about each finger sensor's
own local Y-axis (q_corrected = q_raw (x) q_offset) before computing Euler
angles, purely so the plot is easier to eyeball against the hand sensor.
This is NOT the real Phase 6 q_rel = conj(q_hand) (x) q_finger computation -
it's a rough, fixed, hand-picked correction for this one rig's approximate
mounting angle, not derived per-session from data. Finger 5 does NOT line
up under this correction as well as fingers 1-4 do, which is itself a
finding: it's mounted at a distinctly different angle, not just noisier.

Usage:
    python plot_fusion.py ../data/phase5_madgwick_fusion/capture_02_drift.csv \
        --save ../docs/media/phase5_drift_rpy.png --title "Drift test (held still)"
"""

import argparse
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

SENSOR_NAMES = {0: "hand", 1: "finger1", 2: "finger2", 3: "finger3", 4: "finger4", 5: "finger5"}
COLORS = {0: "#e8a33d", 1: "#5fb3a3", 2: "#6a8fd8", 3: "#9a7fd4", 4: "#d97a92", 5: "#c9c14a"}

# Fixed rough mount correction: +90 deg about local Y, applied to finger
# sensors only (sensor_id != 0). See module docstring for why.
_MOUNT_CORRECTION_Q = (math.cos(math.radians(45)), 0.0, math.sin(math.radians(45)), 0.0)


def qmul(a, b):
    """Hamilton product a (x) b, both (w,x,y,z)."""
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    )


def quat_to_euler_deg(q):
    """Same roll/pitch/yaw convention as the firmware's quatToEuler()."""
    w, x, y, z = q
    roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    s = max(-1.0, min(1.0, 2 * (w * y - z * x)))
    pitch = math.asin(s)
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return tuple(math.degrees(v) for v in (roll, pitch, yaw))


def load(path: Path):
    """Returns {sid: [(ms, qw,qx,qy,qz), ...]}."""
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
                q = tuple(float(x) for x in parts[2:6])
            except ValueError:
                continue
            rows[sid].append((ms, q))
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
    ap.add_argument("--no-mount-correction", action="store_true",
                     help="plot raw per-sensor Euler angles, skip the +90deg/Y finger correction")
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
        t = [(ms - t0) / 1000.0 for ms, _ in r]

        apply_corr = sid != 0 and not args.no_mount_correction
        eulers = []
        for _, q in r:
            qc = qmul(q, _MOUNT_CORRECTION_Q) if apply_corr else q
            eulers.append(quat_to_euler_deg(qc))

        roll = unwrap_deg([e[0] for e in eulers])
        pitch = unwrap_deg([e[1] for e in eulers])
        yaw = unwrap_deg([e[2] for e in eulers])

        name = SENSOR_NAMES.get(sid, str(sid))
        if apply_corr:
            name += " (corr.)"
        color = COLORS.get(sid, "#888888")
        for ax, series in zip(axes, (roll, pitch, yaw)):
            ax.plot(t, series, label=name, color=color, linewidth=1)

    for ax, lab in zip(axes, labels):
        ax.set_ylabel(lab)
        ax.grid(alpha=0.3)
    axes[0].legend(loc="upper right", ncol=6, fontsize=8)
    axes[-1].set_xlabel("time (s)")
    default_title = f"Phase 5 fused orientation - {args.csv.name}"
    if not args.no_mount_correction:
        default_title += "\n(fingers rotated +90deg/local-Y to roughly align with hand sensor for comparison)"
    fig.suptitle(args.title or default_title, fontsize=11)
    fig.tight_layout()

    if args.save:
        fig.savefig(args.save, dpi=130)
        print(f"saved {args.save}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
