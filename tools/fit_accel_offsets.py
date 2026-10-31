"""Fit each sensor's accel zero-g offset from dashboard raw CSVs.

A still accelerometer reads gravity, so its samples should lie on a sphere of
radius 1 g centred on zero. A zero-g offset shifts the centre; a scale error
changes the radius. Fitting the sphere separates the two.

Linear least squares: |a - b|^2 = r^2  rearranges to
    |a|^2 = 2 a.b + (r^2 - |b|^2)
which is linear in (b, c) with c = r^2 - |b|^2.

Needs captures where the hand points in many directions (the whole-hand
rotation test is ideal). Only quasi-static samples (|gyro| < 15 deg/s) are used,
because during motion the accel also measures linear acceleration.

Usage: python fit_accel_offsets.py capture1.csv [capture2.csv ...]
Paste the printed centres into ACC_OFFSET in handrig_dashboard.html.
"""
import sys
import numpy as np

NAMES = ["hand", "thumb", "index", "middle", "ring", "pinky"]


def load(path):
    d = np.genfromtxt(path, delimiter=",", skip_header=2)
    return d[:, 1:].reshape(len(d), 6, 6)  # [frame, sensor, ax ay az gx gy gz]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    x = np.concatenate([load(p) for p in sys.argv[1:]])
    for s, name in enumerate(NAMES):
        a = x[:, s, :3]
        still = (np.linalg.norm(x[:, s, 3:], axis=1) < 15) & np.any(a != 0, axis=1)
        a = a[still]
        M = np.c_[2 * a, np.ones(len(a))]
        sol, *_ = np.linalg.lstsq(M, (a ** 2).sum(1), rcond=None)
        b = sol[:3]
        r = np.sqrt(sol[3] + b @ b)
        rms = (np.linalg.norm(a - b, axis=1) - r).std()
        u = a / np.linalg.norm(a, axis=1, keepdims=True)
        spread = u.max(0) - u.min(0)   # < ~1 on an axis: too few orientations to trust that axis
        print(f"{name:6s} n={len(a):5d} offset=[{b[0]:.3f}, {b[1]:.3f}, {b[2]:.3f}] g  "
              f"radius={r:.3f} g  fit rms={rms:.3f}  orientation spread={np.round(spread, 2)}")


if __name__ == "__main__":
    main()
