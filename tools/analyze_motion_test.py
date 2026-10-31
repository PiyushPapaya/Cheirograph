"""Health check for a dashboard raw CSV (motion tests, 09-firmware-hardening).

Per capture: frame rate and gaps (from the firmware timestamps).
Per sensor:  dropped frames (all six values 0 = firmware cleared the mask bit),
             gyro samples at the clip limit, |a| while still, and the return
             error of plain gyro integration.

Return error: the capture must start and end with a few seconds flat and still.
The gyro is integrated from the start hold to the end hold (bias = mean of the
start hold), and the "up" direction it predicts at the end is compared with
the one the accelerometer measures there. Accel tilt is drift-free, so the
angle between them is what the gyro lost on the way: clipping, too few
samples, bias. Heading (yaw) is invisible to the accel and not included.

Usage: python analyze_motion_test.py capture.csv [--clip 2000] [--still 2.5]
"""
import argparse
import numpy as np

NAMES = ["hand", "thumb", "index", "middle", "ring", "pinky"]


def qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1*w2 - x1*x2 - y1*y2 - z1*z2, w1*x2 + x1*w2 + y1*z2 - z1*y2,
                     w1*y2 - x1*z2 + y1*w2 + z1*x2, w1*z2 + x1*y2 - y1*x2 + z1*w2])


def up_in_body(q):
    # world +Z expressed in the body frame: conj(q) * (0,0,0,1) * q
    w, x, y, z = q
    return np.array([2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x*x + y*y)])


def settle(a):
    # shortest rotation taking measured up (normalised a) onto world +Z
    u = a / np.linalg.norm(a)
    q = np.array([1 + u[2], u[1], -u[0], 0.0])
    return q / np.linalg.norm(q)


def return_error(t, acc, gyr, still):
    s0, s1 = t < still, t > t[-1] - still
    bias = gyr[s0].mean(0)
    q = settle(acc[s0].mean(0))
    for i in range(1, len(t)):
        dt = t[i] - t[i - 1]
        if dt <= 0:
            continue
        w = np.radians(gyr[i] - bias)   # body rate; dq/dt = 0.5 q (0,w)
        q = q + 0.5 * qmul(q, np.r_[0, w]) * dt
        q /= np.linalg.norm(q)
    measured = acc[s1].mean(0)
    measured /= np.linalg.norm(measured)
    return np.degrees(np.arccos(np.clip(up_in_body(q) @ measured, -1, 1)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--clip", type=float, default=2000, help="gyro full scale in deg/s")
    ap.add_argument("--still", type=float, default=2.5, help="seconds of still hold at each end")
    a = ap.parse_args()

    d = np.genfromtxt(a.csv, delimiter=",", skip_header=2)
    t = (d[:, 0] - d[0, 0]) / 1000
    x = d[:, 1:].reshape(len(d), 6, 6)
    dt = np.diff(t) * 1000
    lost = int(np.sum(np.maximum(np.round(dt / 20) - 1, 0)))
    print(f"{a.csv}: {len(t)} frames over {t[-1]:.1f} s = {len(t)/t[-1]:.1f} Hz "
          f"(target 50). dt median {np.median(dt):.0f} ms, max {dt.max():.0f} ms, "
          f"~{lost} frames missing, {np.sum(dt == 0)} same-ms frames")
    for s, name in enumerate(NAMES):
        zero = np.all(x[:, s] == 0, axis=1)
        acc, gyr = x[~zero, s, :3], x[~zero, s, 3:]
        ts = t[~zero]
        clip = int(np.sum(np.abs(gyr) >= a.clip * 0.998))
        amag = np.linalg.norm(acc[ts < a.still], axis=1).mean()
        err = return_error(ts, acc, gyr, a.still)
        print(f"  {name:6s} dropped={zero.sum():4d}  gyro clipped={clip:4d}  "
              f"|a| still={amag:.3f} g  return error={err:5.1f} deg")


if __name__ == "__main__":
    main()
