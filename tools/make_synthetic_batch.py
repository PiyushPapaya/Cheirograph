#!/usr/bin/env python3
"""make_synthetic_batch.py - fake Phase 8 batch CSVs, for testing the tools only.

Writes files in exactly the dashboard's batch-export format so
check_dataset.py and train_baseline.py can be built and tested before real
data exists. THE NUMBERS ARE INVENTED. Every file carries a "# SYNTHETIC"
comment line; never mix these into the real dataset, and never quote an
accuracy measured on them as a result for the glove.

How a synthetic rep is built (viewer frame, the same one the dashboard uses:
+Y = out of the back of the hand, +Z = along the fingers, left hand so the
thumb is at -X):

    q_hand   = a random tilt of up to ~25 deg   (hand never held the same way twice)
    q_pose   = R_y(spread) * R_x(curl)          (per letter, per finger)
    q_true   = q_pose * small per-rep wobble    (a person never repeats a pose exactly)
    q_drift  = R_y(yaw error)                   (6-DOF filters drift in yaw, see
                                                 DECISIONS.md 2026-07-14)
    exported quaternion = q_drift * q_true      (what the filter THINKS q_rel is)
    exported accel      = gravity seen in the finger's own frame, from the TRUE
                          world orientation q_hand * q_true. Accel has no yaw
                          drift: it measures gravity directly.

R_x(+curl) turns +Z toward -Y, i.e. toward the palm. The letter shapes below
are rough approximations of ASL fingerspelling, good enough to make classes
that differ the way real ones do: most by curl, U vs V only by spread.

Usage:
    python make_synthetic_batch.py --out synth/ --sessions 3 --reps 30
"""

import argparse
import time
from pathlib import Path

import numpy as np

from batch_io import EXPECTED_HEADER
from pose_labels import NEAR_MISS, POSES

# Curl in degrees for (thumb, index, middle, ring, pinky), plus index/middle
# spread. 0 = straight, ~140 = fully curled at the middle phalanx.
LETTERS = {
    #     T    I    M    R    P    spread_I spread_M
    "A": ([0, 140, 140, 140, 140], 0, 0),
    "B": ([70, 0, 0, 0, 0], 0, 0),
    "C": ([30, 70, 70, 70, 70], 0, 0),
    "D": ([60, 0, 110, 110, 110], 0, 0),
    "I": ([60, 140, 140, 140, 0], 0, 0),
    "L": ([0, 0, 140, 140, 140], 0, 0),
    "U": ([60, 0, 0, 140, 140], 0, 0),
    "V": ([60, 0, 0, 140, 140], -12, 12),
    "W": ([60, 0, 0, 0, 140], -12, 0),
    "Y": ([0, 140, 140, 140, 0], 0, 0),
}

# Touch poses (--poses): same layout as LETTERS. Each touch pose bends the thumb
# to its own angle and curls the touched finger toward it. NEAR* poses reuse a
# touching pose's values with the thumb 12 degrees short, so the tip is about
# 1 cm away: close, but separable.
POSE_SHAPES = {
    #                 T    I    M    R    P    spread_I spread_M
    "FLAT":       ([0, 0, 0, 0, 0], 0, 0),
    "FISTOUT":    ([20, 140, 140, 140, 140], 0, 0),
    "FISTIN":     ([120, 140, 140, 140, 140], 0, 0),
    "THUMBOUT":   ([0, 140, 140, 140, 140], 0, 8),
    "TI":         ([40, 70, 0, 0, 0], 0, 0),
    "TM":         ([60, 0, 70, 0, 0], 0, 0),
    "TR":         ([80, 0, 0, 70, 0], 0, 0),
    "TP":         ([100, 0, 0, 0, 70], 0, 0),
    "OKRING":     ([45, 80, 0, 0, 0], 0, 0),
    "ROCK":       ([70, 0, 70, 70, 0], 0, 0),
    "TRSTRAIGHT": ([85, 0, 0, 80, 0], 0, 0),
    "TRP":        ([90, 0, 0, 70, 70], 0, 0),
}
for _near, _src in (("NEARTI", "TI"), ("NEARTR", "TR")):
    _c, _si, _sm = POSE_SHAPES[_src]
    POSE_SHAPES[_near] = ([_c[0] - 12] + _c[1:], _si, _sm)
assert set(POSE_SHAPES) == set(POSES) and set(NEAR_MISS) <= set(POSE_SHAPES)

THUMB_REST_DEG = -40      # thumb points forward and out toward -X when "straight"


HEADER_LINES = ["# SYNTHETIC test data from tools/make_synthetic_batch.py, NOT a glove capture",
                "# batch-captured static-pose samples. raw = median over a ~0.6s held-still window (noise-reduced).",
                "# q* = hand-relative orientation conj(q_hand)*q_finger (viewer frame, bias-corrected) "
                "at capture time, order (w,x,y,z), sign pinned to w>=0."]


def q_axis_angle(axis, deg):
    """Unit quaternion (w,x,y,z) for a rotation of `deg` about `axis`."""
    axis = np.asarray(axis, float)
    axis = axis / np.linalg.norm(axis)
    h = np.radians(deg) / 2
    return np.concatenate([[np.cos(h)], np.sin(h) * axis])


def q_mul(a, b):
    """Hamilton product a (x) b, both (w,x,y,z)."""
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
                     w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                     w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def q_rotate_inv(q, v):
    """Express world vector v in the body frame of q: conj(q) (x) v (x) q."""
    qc = q * np.array([1, -1, -1, -1])
    return q_mul(q_mul(qc, np.concatenate([[0], v])), q)[1:]


def random_tilt(rng, max_deg):
    axis = rng.normal(size=3)
    return q_axis_angle(axis, rng.uniform(0, max_deg))


def finger_pose(i, curl, spread):
    """Pose of finger i (0 = thumb) relative to the hand."""
    if i == 0:
        # thumb: swings across the palm (about Y) and dips toward it (about X) as it "curls"
        return q_mul(q_axis_angle([0, 1, 0], THUMB_REST_DEG + curl), q_axis_angle([1, 0, 0], curl / 2))
    return q_mul(q_axis_angle([0, 1, 0], spread), q_axis_angle([1, 0, 0], curl))


def pin(q):
    return q if q[0] >= 0 else -q


def make_rep(rng, letter, sess, shapes=LETTERS):
    curls, spread_i, spread_m = shapes[letter]
    spreads = [0, spread_i, spread_m, 0, 0]
    q_hand = random_tilt(rng, 25)
    up = np.array([0.0, 1.0, 0.0])     # an accelerometer at rest reads +1 g pointing UP

    raw, quat = [], []
    # hand: exported quaternion is the hand against its own (flat) zero pose
    a = q_rotate_inv(q_hand, up) + rng.normal(0, 0.004, 3)
    raw.append(np.concatenate([a, sess["gyro_bias"][0] + rng.normal(0, 0.05, 3)]))
    quat.append(pin(q_hand))

    for i in range(5):
        curl = curls[i] + sess["curl_offset"][i] + rng.normal(0, 4)
        spread = spreads[i] + rng.normal(0, 2)
        q_true = finger_pose(i, curl, spread)
        q_drift = q_axis_angle([0, 1, 0], sess["yaw_drift"][i] + rng.normal(0, 1))
        q_est = pin(q_mul(q_drift, q_true))

        a = q_rotate_inv(q_mul(q_hand, q_true), up) + rng.normal(0, 0.004, 3)
        raw.append(np.concatenate([a, sess["gyro_bias"][i + 1] + rng.normal(0, 0.05, 3)]))
        quat.append(q_est)
    return np.array(raw), np.array(quat)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="folder to write the CSVs into")
    ap.add_argument("--letters", default="".join(LETTERS), help="e.g. ABUV (default: all)")
    ap.add_argument("--sessions", type=int, default=3)
    ap.add_argument("--reps", type=int, default=30, help="reps per letter per session")
    ap.add_argument("--drift-deg", type=float, default=10.0,
                    help="std of the per-session, per-finger yaw error in degrees (0 = perfect filter)")
    ap.add_argument("--poses", action="store_true",
                    help="write one handrig_batch_POSES_<sess>_<ts>.csv per session with every "
                         "touch pose (tools/pose_labels.py) instead of the letter files")
    ap.add_argument("--curl-offset-sd", type=float, default=6.0,
                    help="per-session curl offset in degrees, what re-seating the glove does")
    ap.add_argument("--near-deg", type=float, default=12.0,
                    help="how far NEAR* poses sit from their touching pose, thumb curl in degrees")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    for near, src in (("NEARTI", "TI"), ("NEARTR", "TR")):
        c, si, sm = POSE_SHAPES[src]
        POSE_SHAPES[near] = ([c[0] - args.near_deg] + c[1:], si, sm)

    rng = np.random.default_rng(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)

    for s in range(1, args.sessions + 1):
        # Things that change when the glove is taken off and put back on.
        sess = {"yaw_drift": rng.normal(0, args.drift_deg, 5) if args.drift_deg else np.zeros(5),
                "curl_offset": rng.normal(0, args.curl_offset_sd, 5),
                "gyro_bias": rng.normal(0, 1.5, (6, 3))}
        if args.poses:
            lines = [HEADER_LINES[0], HEADER_LINES[1], HEADER_LINES[2], ",".join(EXPECTED_HEADER)]
            for label in POSE_SHAPES:
                for rep in range(1, args.reps + 1):
                    raw, quat = make_rep(rng, label, sess, POSE_SHAPES)
                    row = [label, str(rep), str(ts)]
                    row += [f"{v:.5f}" for v in raw.ravel()]
                    row += [f"{v:.6f}" for v in quat.ravel()]
                    lines.append(",".join(row))
                    ts += 1500
            path = out / f"handrig_batch_POSES_{s:02d}_{ts}.csv"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            continue
        for letter in args.letters.upper():
            lines = ["# SYNTHETIC test data from tools/make_synthetic_batch.py, NOT a glove capture",
                     "# batch-captured static-pose samples. raw = median over a ~0.6s held-still window (noise-reduced).",
                     "# q* = hand-relative orientation conj(q_hand)*q_finger (viewer frame, bias-corrected) "
                     "at capture time, order (w,x,y,z), sign pinned to w>=0.",
                     ",".join(EXPECTED_HEADER)]
            for rep in range(1, args.reps + 1):
                raw, quat = make_rep(rng, letter, sess)
                row = [letter, str(rep), str(ts)]
                row += [f"{v:.5f}" for v in raw.ravel()]
                row += [f"{v:.6f}" for v in quat.ravel()]
                lines.append(",".join(row))
                ts += 1500
            path = out / f"handrig_batch_{letter}_{s:02d}_{ts}.csv"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    n_files = args.sessions * (1 if args.poses else len(args.letters))
    print(f"wrote {n_files} files to {out}")


if __name__ == "__main__":
    main()
