#!/usr/bin/env python3
"""verify_features.py - checks the gravity feature sets in train_baseline.py (spec S06).

Builds poses by hand, turns them into raw accel the way a real export stores it
(each sensor's own frame, with a known accel offset added), and checks:

  1. the remaps are proper rotations (det +1)
  2. flat hand: G18 = six (0,1,0) after remap, P5 and R5 = 0
  3. index curled 30 deg about X: P5[index] = 30 +- 0.5, the other fingers 0
  4. whole hand rolled 20 deg about Z, fingers straight: P5 and R5 change < 1 deg
  5. a sensor whose calUp is tilted ~27 deg (25 roll + 10 pitch): G18z reads (0,1,0) in the calibration pose
  6. no calUp in meta: G18z falls back to G18
  7. the quat-only call features(quat, "dir") still works and matches the BatchFile call

Prints PASS or FAIL per check and exits 1 on any failure.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import train_baseline as tb                                          # noqa: E402

UP = np.array([0.0, 1.0, 0.0])          # gravity reaction, world frame = model frame of a flat hand
OFFSETS = np.array([[0.02, -0.01, 0.03]] * 5 + [[0.25, 0.19, -0.165]])   # pinky like the real one
failures = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} - {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        failures.append(name)


def rot(axis, deg):
    """Rotation matrix for `deg` about a model axis (right-hand rule)."""
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return {"x": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]),
            "y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
            "z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[axis]


def sample(hand_R, finger_R, scale=0.97):
    """One BatchFile-like sample.

    hand_R: world orientation of the hand. finger_R: 5 orientations relative to the
    hand. Each sensor sees gravity as R_world^T * UP in the model frame; the real
    file stores it in the sensor frame, which is M^T * model (M = remap, a rotation),
    plus the sensor's offset. scale != 1 checks that only the direction is used."""
    worlds = [hand_R] + [hand_R @ f for f in finger_R]
    raw = np.zeros((1, 6, 6))
    for s, R in enumerate(worlds):
        g_model = R.T @ UP
        raw[0, s, :3] = scale * (tb.REMAP_OF[s].T @ g_model) + OFFSETS[s]
    meta = {"offsets": OFFSETS.tolist(), "calUp": [UP.tolist()] * 6}
    return SimpleNamespace(raw=raw, quat=np.tile([1.0, 0, 0, 0], (1, 6, 1)), meta=meta)


def feats(bf, kind):
    return tb.features(bf, kind)[0]


def main():
    straight = [np.eye(3)] * 5

    # 1
    dets = [np.linalg.det(m) for m in (tb.REMAP_HAND, tb.REMAP_FINGER)]
    check("remaps are proper rotations", np.allclose(dets, 1) and
          all(np.allclose(m @ m.T, np.eye(3)) for m in (tb.REMAP_HAND, tb.REMAP_FINGER)), f"det {dets}")

    # 2
    flat = sample(np.eye(3), straight)
    g = feats(flat, "G18").reshape(6, 3)
    check("flat: G18 = six (0,1,0)", np.allclose(g, UP, atol=1e-9), f"max err {np.abs(g - UP).max():.2e}")
    p5, r5 = feats(flat, "P5"), feats(flat, "R5")
    check("flat: P5 = 0 and R5 = 0", np.allclose(p5, 0, atol=1e-6) and np.allclose(r5, 0, atol=1e-6),
          f"P5 {np.round(p5, 3)} R5 {np.round(r5, 3)}")

    # 3: R_x(+30) turns the fingertip (+Z) toward -Y, the palm
    curl = sample(np.eye(3), [np.eye(3), rot("x", 30)] + [np.eye(3)] * 3)
    p5 = feats(curl, "P5")
    check("index curl 30 deg: P5[index] = 30 +- 0.5, others 0",
          abs(p5[1] - 30) <= 0.5 and np.allclose(np.delete(p5, 1), 0, atol=1e-6),
          f"P5 {np.round(p5, 3)}, CURL_SIGN {tb.CURL_SIGN:+d}")

    # 4
    roll = sample(rot("z", 20), straight)
    dp = np.abs(feats(roll, "P5") - feats(flat, "P5")).max()
    dr = np.abs(feats(roll, "R5") - feats(flat, "R5")).max()
    check("whole-hand roll 20 deg: P5 and R5 change < 1 deg", dp < 1 and dr < 1,
          f"max change P5 {dp:.3f}, R5 {dr:.3f}")

    # 5: the index sensor sits rolled 25 deg about the finger axis (plus 10 deg about X,
    # so the tilt axis is oblique). In the calibration pose (flat hand) it sees UP
    # rotated, and calUp records exactly that vector.
    mount = rot("z", 25) @ rot("x", 10)
    cal = sample(np.eye(3), [np.eye(3), mount] + [np.eye(3)] * 3)
    cal_up = (mount.T @ UP).tolist()
    cal.meta["calUp"][2] = cal_up
    g18 = feats(cal, "G18").reshape(6, 3)
    g18z = feats(cal, "G18z").reshape(6, 3)
    check("calUp tilted ~27 deg: G18 sees the tilt, G18z reads (0,1,0)",
          np.degrees(np.arccos(np.clip(g18[2] @ UP, -1, 1))) > 24 and np.allclose(g18z, UP, atol=1e-9),
          f"G18 index {np.round(g18[2], 3)}, G18z index {np.round(g18z[2], 6)}")

    # 6
    nocal = sample(np.eye(3), [np.eye(3), mount] + [np.eye(3)] * 3)
    nocal.meta.pop("calUp")
    check("no calUp: G18z = G18 (with a warning)", np.allclose(feats(nocal, "G18z"), feats(nocal, "G18")))

    # 7
    rng = np.random.default_rng(1)
    q = rng.normal(size=(4, 6, 4))
    q /= np.linalg.norm(q, axis=-1, keepdims=True)
    bf = SimpleNamespace(raw=np.zeros((4, 6, 6)), quat=q, meta=None)
    check("features(quat, 'dir') unchanged and equal to the BatchFile call",
          tb.features(q, "dir").shape == (4, 15) and np.allclose(tb.features(q, "dir"), tb.features(bf, "dir")))

    print(f"\nCURL_SIGN = {tb.CURL_SIGN:+d}: P5 is positive for a curl toward the palm in the model "
          "frame. The curl sign on the glove is not chosen yet (open item); this is a convention.")
    print("RESULT: " + ("PASS" if not failures else f"FAIL ({len(failures)})"))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
