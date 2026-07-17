#!/usr/bin/env python3
"""analyze_drift.py - per-sensor orientation drift check for the Phase 5
Madgwick fusion capture (data/phase5_madgwick_fusion/), fused contract
(millis,sensor_id,qw,qx,qy,qz,roll_deg,pitch_deg,yaw_deg[,ax,ay,az,gx,gy,gz]).

Compares the first and last sample per sensor and reports roll/pitch/yaw
drift in degrees/minute. Roll and pitch are gravity-anchored (Madgwick
corrects them from accel every tick) so they should stay near ~0 deg/min
even with a biased gyro. Yaw has no absolute reference in a 6-DOF IMU, so
some drift there is expected physics, not a bug - see CLAUDE.md and
DECISIONS.md (2026-07-14) on the 6-DOF yaw drift decision.

Usage:
    python analyze_drift.py ../data/phase5_madgwick_fusion/capture_02_drift.csv
"""

import argparse
from collections import defaultdict
from pathlib import Path

SENSOR_NAMES = {0: "hand (onboard)", 1: "finger 1", 2: "finger 2",
                3: "finger 3", 4: "finger 4", 5: "finger 5"}


def wrap180(deg: float) -> float:
    while deg > 180:
        deg -= 360
    while deg < -180:
        deg += 360
    return deg


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
                vals = [float(x) for x in parts[2:9]]
            except ValueError:
                continue
            rows[sid].append((ms, vals))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    args = ap.parse_args()

    rows = load(args.csv)
    print(f"{'sensor':<16}{'n':>6}{'dur_s':>8}  "
          f"{'droll/min':>10}{'dpitch/min':>11}{'dyaw/min':>10}")
    for sid in sorted(rows):
        r = rows[sid]
        if len(r) < 2:
            continue
        ms0, v0 = r[0]
        msN, vN = r[-1]
        dur_s = (msN - ms0) / 1000.0
        if dur_s <= 0:
            continue
        roll0, pitch0, yaw0 = v0[4], v0[5], v0[6]
        rollN, pitchN, yawN = vN[4], vN[5], vN[6]
        droll = wrap180(rollN - roll0) / dur_s * 60
        dpitch = wrap180(pitchN - pitch0) / dur_s * 60
        dyaw = wrap180(yawN - yaw0) / dur_s * 60
        name = SENSOR_NAMES.get(sid, str(sid))
        print(f"{name:<16}{len(r):>6}{dur_s:>8.1f}  "
              f"{droll:>10.2f}{dpitch:>11.2f}{dyaw:>10.2f}")


if __name__ == "__main__":
    main()
