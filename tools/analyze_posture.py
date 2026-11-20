"""Calibration posture test (docs/log/specs/S03): did the hand IMU move against the fingers?

Reads every raw dashboard CSV (header starts "t_ms,hand_ax,") in a folder. Files are matched
by name prefix (T1_table.csv -> T1). For each pair of recordings it prints the tilt change
theta per sensor and shift = theta_hand - median(theta_index, theta_middle, theta_ring, theta_pinky).

Why shift works: gravity in sensor s is M_s^T R^T g, with M_s the mount rotation of the sensor
and R the pose of the body. The angle between two such vectors depends only on R, because M_s
is a rotation and keeps angles. So parts fixed to the same body all see the same theta,
whatever their mount angle. Shift 0 = the hand IMU moved with the fingers. A rotation about
the gravity axis is invisible (the pen line covers that). The thumb is excluded.

Usage: python analyze_posture.py <folder> [--offsets file.json]
       python analyze_posture.py --selftest
"""
import argparse
import json
import os
import sys
import tempfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from batch_io import DEFAULT_OFFSETS

NAMES = ["hand", "thumb", "index", "middle", "ring", "pinky"]
PAIRS = [("T1", "T2"), ("T2", "T3"), ("T1", "T3"), ("T4", "T5"), ("T5", "T6"), ("T4", "T6"),
         ("A1", "A2"), ("M1", "M3"), ("T1", "R1"), ("T1", "A1")]


def load(path):
    """Return (t_s, data) with data shape (n, 6 sensors, 6 values), or None if not a raw CSV."""
    with open(path) as f:
        lines = [l for l in f if not l.startswith("#") and l.strip()]
    if not lines or not lines[0].startswith("t_ms,hand_ax,"):
        return None
    arr = np.array([[float(v) for v in l.split(",")] for l in lines[1:]])
    return (arr[:, 0] - arr[0, 0]) / 1000.0, arr[:, 1:].reshape(len(arr), 6, 6)


def summarise(t, data, offsets):
    """Unit gravity vector (6,3) and gyro std (6,) after dropping the settling time."""
    drop = 10.0 if t[-1] > 30.0 else 5.0
    d = data[t >= drop]
    g = d[:, :, :3].mean(axis=0) - offsets
    return g / np.linalg.norm(g, axis=1, keepdims=True), d[:, :, 3:].std(axis=0).max(axis=1)


def angle_deg(a, b):
    return np.degrees(np.arccos(np.clip(np.sum(a * b, axis=1), -1.0, 1.0)))


def shift_of(theta):
    return theta[0] - np.median(theta[2:])


def analyse(folder, offsets):
    recs = {}
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(".csv"):
            continue
        r = load(os.path.join(folder, name))
        if r is None:
            continue
        g, gstd = summarise(*r, offsets)
        recs[name.split("_")[0].upper()] = g
        warn = [f"{n} {s:.1f}" for n, s in zip(NAMES, gstd) if s > 3.0]
        print(f"{name}: gyro std max {gstd.max():.2f} deg/s" + (f"  WARN not still: {', '.join(warn)}" if warn else ""))
    results = {}
    for x, y in PAIRS:
        if x in recs and y in recs:
            theta = angle_deg(recs[x], recs[y])
            results[(x, y)] = shift_of(theta)
            print(f"{x}->{y}  theta " + " ".join(f"{n}={v:.1f}" for n, v in zip(NAMES, theta))
                  + f"  | shift {results[(x, y)]:+.1f}")
    return results


def rot(axis, deg):
    """Rotation matrix (Rodrigues) about axis by deg."""
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    r = np.radians(deg)
    return np.eye(3) + np.sin(r) * k + (1 - np.cos(r)) * k @ k


def write_synth(path, mounts, tilt_deg, rng):
    """tilt_deg: per-sensor tilt about world X. Accel in sensor s = M_s^T R^T g."""
    n = 1500  # 30 s at 50 Hz
    cols = ["t_ms"] + [f"{s}_{a}" for s in NAMES for a in ["ax", "ay", "az", "gx", "gy", "gz"]]
    rows = np.zeros((n, 37))
    rows[:, 0] = np.arange(n) * 20
    for s in range(6):
        a = mounts[s].T @ rot([1, 0, 0], tilt_deg[s]).T @ np.array([0, 0, 1.0])
        rows[:, 1 + 6 * s:4 + 6 * s] = a + rng.normal(0, 0.003, (n, 3))
        rows[:, 4 + 6 * s:7 + 6 * s] = rng.normal(0, 0.3, (n, 3))
    with open(path, "w") as f:
        f.write("# synthetic\n" + ",".join(cols) + "\n")
        for r in rows:
            f.write(",".join(f"{v:.4f}" for v in r) + "\n")


def selftest():
    rng = np.random.default_rng(1)
    # a different fixed mount rotation per sensor, so the invariance is really exercised
    mounts = [rot(rng.normal(size=3), rng.uniform(0, 180)) for _ in range(6)]
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        write_synth(os.path.join(tmp, "T1_a.csv"), mounts, [0] * 6, rng)
        write_synth(os.path.join(tmp, "T2_b.csv"), mounts, [32] + [20] * 5, rng)  # hand +12 extra
        write_synth(os.path.join(tmp, "T3_c.csv"), mounts, [20] * 6, rng)
        res = analyse(tmp, np.zeros((6, 3)))
    for pair, want in [(("T1", "T2"), 12.0), (("T1", "T3"), 0.0)]:
        got = res[pair]
        good = abs(got - want) <= 0.2
        ok &= good
        print(f"{pair[0]}->{pair[1]} expect {want:.1f} got {got:.2f}: {'ok' if good else 'bad'}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="?")
    ap.add_argument("--offsets", help="JSON file with a 6x3 list (g)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if not args.folder:
        ap.error("folder required")
    off = np.array(json.load(open(args.offsets))) if args.offsets else DEFAULT_OFFSETS
    analyse(args.folder, off)
