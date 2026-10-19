#!/usr/bin/env python3
"""analyze_drift.py - per-sensor orientation drift check for the Phase 5
Madgwick fusion capture (05-madgwick-fusion/), fused contract
(millis,sensor_id,qw,qx,qy,qz,roll_deg,pitch_deg,yaw_deg[,ax,ay,az,gx,gy,gz]).

Reports roll/pitch/yaw drift in degrees/minute per sensor. Roll and pitch are
gravity-anchored (Madgwick corrects them from accel every tick) so they should
stay near ~0 deg/min even with a biased gyro. Yaw has no absolute reference in
a 6-DOF IMU, so some drift there is expected physics, not a bug - see
CLAUDE.md and DECISIONS.md (2026-07-14) on the 6-DOF yaw drift decision.

How drift is measured: a straight line is fitted (least squares) through each
angle over time, and the slope is the drift rate. The first version of this
script used only the first and last sample, so one noisy sample at either end
moved the answer. Angles are unwrapped first so a yaw crossing +-180 deg is not
read as a 360 deg jump. The first --skip-s seconds are dropped: right after
calibration the filter runs a high-gain snap-in (CONVERGE_MS in the sketch),
and that settling is not drift.

The Phase 5 closing test is an A/B pair from ONE session, glove untouched:
    run A with SUBTRACT_GYRO_BIAS 0, run B with SUBTRACT_GYRO_BIAS 1,
    each held still for a few minutes. Pass both files to see the effect of
    calibration alone (--compare).

Usage:
    python analyze_drift.py ../05-madgwick-fusion/capture_02_drift.csv
    python analyze_drift.py bias_off.csv --compare bias_on.csv
"""

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np

SENSOR_NAMES = {0: "hand (onboard)", 1: "finger 1", 2: "finger 2",
                3: "finger 3", 4: "finger 4", 5: "finger 5"}
AXES = ["roll", "pitch", "yaw"]


def load(path: Path):
    """Return ({sensor_id: (t_s array, rpy array (n,3))}, SUBTRACT_GYRO_BIAS or None)."""
    rows = defaultdict(list)
    bias_flag = None
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("# SUBTRACT_GYRO_BIAS="):
                bias_flag = line.split("=", 1)[1].strip()
            if not line or line.startswith("#") or line.startswith("millis"):
                continue
            parts = line.split(",")
            if len(parts) < 9:
                continue
            try:
                ms = int(parts[0])
                sid = int(parts[1])
                rpy = [float(x) for x in parts[6:9]]
            except ValueError:
                continue
            rows[sid].append((ms, rpy))
    out = {}
    for sid, r in rows.items():
        t = np.array([ms for ms, _ in r], float) / 1000.0
        out[sid] = (t, np.array([v for _, v in r]))
    return out, bias_flag


def drift_rates(data, skip_s):
    """{sensor_id: (n, duration_s, [roll, pitch, yaw] deg/min)} from a line fit."""
    res = {}
    for sid, (t, rpy) in sorted(data.items()):
        keep = t >= t[0] + skip_s
        t, rpy = t[keep], rpy[keep]
        if len(t) < 10 or t[-1] - t[0] <= 0:
            continue
        # unwrap works in radians: it removes jumps bigger than pi between neighbours
        ang = np.degrees(np.unwrap(np.radians(rpy), axis=0))
        slopes = [np.polyfit(t, ang[:, k], 1)[0] * 60 for k in range(3)]   # deg/s -> deg/min
        res[sid] = (len(t), t[-1] - t[0], slopes)
    return res


def print_table(title, res):
    print(title)
    print(f"{'sensor':<16}{'n':>6}{'dur_s':>8}  " + "".join(f"{'d' + a + '/min':>11}" for a in AXES))
    for sid, (n, dur, s) in res.items():
        print(f"{SENSOR_NAMES.get(sid, str(sid)):<16}{n:>6}{dur:>8.1f}  "
              + "".join(f"{v:>11.2f}" for v in s))
    if any(dur < 120 for _, dur, _ in res.values()):
        print("  note: under 2 minutes of data; a slow drift can hide in the noise. "
              "Aim for 3-5 minutes still.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path, help="capture A (e.g. bias subtraction OFF)")
    ap.add_argument("--compare", type=Path, help="capture B (e.g. bias subtraction ON)")
    ap.add_argument("--skip-s", type=float, default=2.0,
                    help="seconds to drop at the start, for filter snap-in (default 2)")
    args = ap.parse_args()

    data_a, flag_a = load(args.csv)
    res_a = drift_rates(data_a, args.skip_s)
    print_table(f"A: {args.csv.name}  (SUBTRACT_GYRO_BIAS={flag_a or 'not in file'})", res_a)
    if not args.compare:
        return

    data_b, flag_b = load(args.compare)
    res_b = drift_rates(data_b, args.skip_s)
    print()
    print_table(f"B: {args.compare.name}  (SUBTRACT_GYRO_BIAS={flag_b or 'not in file'})", res_b)

    print("\n|drift| A -> B, deg/min (smaller is better)")
    print(f"{'sensor':<16}" + "".join(f"{a:>17}" for a in AXES))
    for sid in sorted(set(res_a) & set(res_b)):
        cells = "".join(f"{abs(va):>7.2f} -> {abs(vb):>6.2f}"
                        for va, vb in zip(res_a[sid][2], res_b[sid][2]))
        print(f"{SENSOR_NAMES.get(sid, str(sid)):<16}{cells}")
    if flag_a and flag_b and flag_a == flag_b:
        print(f"\nwarning: both files say SUBTRACT_GYRO_BIAS={flag_a}; this is not a bias on/off pair")


if __name__ == "__main__":
    main()
