#!/usr/bin/env python3
"""train_baseline.py - a simple, explainable baseline before Edge Impulse (Phase 9).

Why this exists: when the Edge Impulse model reports an accuracy, we need a
number to compare it against. This script uses a k-nearest-neighbours
classifier (no training step, nothing hidden) on three feature sets, and
measures accuracy two ways.

Feature sets (all from the hand-relative finger quaternions q_rel; the hand's
own quaternion is ignored because it only says how the hand is tilted, which
must not change the letter):

  quat  20 numbers: q_rel (w,x,y,z) for each finger, as-is. What
        ml/README.md originally planned to feed Edge Impulse.

  dir   15 numbers: where each finger points, in the hand's frame:
        d = R(q_rel) * (0,0,1), i.e. the finger's +Z axis rotated by q_rel.
        Unlike the raw quaternion this has no q / -q ambiguity and no
        wrap-around, and it means something physical: d_y says how far the
        finger curls toward the palm, d_x how far it spreads sideways.

  curl  5 numbers: only d_y per finger. Yaw drift (DECISIONS.md, 2026-07-14)
        is a rotation about the vertical axis; with the hand flat that is the
        hand's Y axis, and a rotation about Y leaves d_y unchanged. So this set
        is immune to yaw drift, but it also throws away spread, so letters that
        differ only by spread (U vs V) become indistinguishable.

Accuracy is measured two ways:

  random split           80/20 split of all reps, ignoring sessions. Reps from
                         the same session are near-identical, so this mostly
                         tests "can you recognise a rep you nearly saw" and is
                         optimistic.
  leave-one-session-out  train on all sessions but one, test on the held-out
                         one, repeat for each session. This is the honest
                         number: a new session means the glove was taken off,
                         re-seated and recalibrated, exactly like real use.

If the two numbers are far apart, the model is learning the session, not the
letter, and the fix is more sessions (more variety), not a bigger model.

Usage:
    python train_baseline.py path/to/exports/ [--k 5]
"""

import argparse
import sys
from collections import Counter

import numpy as np

from batch_io import find_csvs, load_batch

# ---------- features ----------

def finger_direction(q):
    """Rotate (0,0,1) by unit quaternions q (..., 4) in (w,x,y,z) order.

    This is the third column of the rotation matrix of q, written out:
        R * z = (2(xz + wy), 2(yz - wx), 1 - 2(x^2 + y^2))
    Every term is a product of two components, so q and -q give the same
    answer: the sign ambiguity is gone.
    """
    w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    return np.stack([2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y)], axis=-1)


def features(quat, kind):
    """quat: (rows, 6 sensors, 4). Sensor 0 is the hand and is skipped."""
    fq = quat[:, 1:, :]
    if kind == "quat":
        return fq.reshape(len(fq), -1)
    d = finger_direction(fq)                      # (rows, 5, 3)
    if kind == "dir":
        return d.reshape(len(d), -1)
    if kind == "curl":
        return d[:, :, 1]
    raise ValueError(kind)


FEATURE_SETS = ["quat", "dir", "curl"]

# ---------- classifier ----------

def knn_predict(Xtr, ytr, Xte, k):
    # Standardise with the TRAINING set's mean/std only: using the test set's
    # statistics would leak information about it into the model.
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    A, B = (Xtr - mu) / sd, (Xte - mu) / sd
    dist = ((B[:, None, :] - A[None, :, :]) ** 2).sum(-1)      # (test, train)
    nearest = np.argsort(dist, axis=1)[:, :k]
    return np.array([Counter(ytr[row]).most_common(1)[0][0] for row in nearest])


def random_split(X, y, k, rng):
    idx = rng.permutation(len(y))
    cut = int(0.8 * len(y))
    tr, te = idx[:cut], idx[cut:]
    pred = knn_predict(X[tr], y[tr], X[te], k)
    return (pred == y[te]).mean()


def leave_one_session_out(X, y, sess, k):
    preds = np.empty_like(y)
    for s in np.unique(sess):
        te = sess == s
        preds[te] = knn_predict(X[~te], y[~te], X[te], k)
    return (preds == y).mean(), preds


def confusion(y, pred, labels):
    m = np.zeros((len(labels), len(labels)), int)
    pos = {l: i for i, l in enumerate(labels)}
    for a, b in zip(y, pred):
        m[pos[a], pos[b]] += 1
    return m

# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="batch CSV files and/or folders (run check_dataset.py first)")
    ap.add_argument("--k", type=int, default=5, help="neighbours to vote (default 5)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    files = [load_batch(p) for p in find_csvs(args.paths)]
    files = [f for f in files if len(f.labels)]
    if not files:
        sys.exit("no data rows found")
    if any(not f.hand_relative for f in files):
        sys.exit("some files are pre-2026-10-06 exports (not hand-relative). Run check_dataset.py.")
    if any(f.synthetic for f in files):
        print("NOTE: input includes SYNTHETIC data. These accuracies say nothing about the glove.\n")

    y = np.array([lab for f in files for lab in f.labels])
    sess = np.array([f.session for f in files for _ in f.labels])
    quat = np.concatenate([f.quat for f in files])
    labels = sorted(set(y))
    n_sess = len(set(sess) - {"?"})
    print(f"{len(y)} reps, {len(labels)} letters, {n_sess} sessions, k = {args.k}\n")

    rng = np.random.default_rng(args.seed)
    print(f"{'features':<9}{'dims':>5}{'random split':>15}{'leave-one-session-out':>24}")
    best = None
    for kind in FEATURE_SETS:
        X = features(quat, kind)
        acc_rand = random_split(X, y, args.k, rng)
        if n_sess >= 2 and "?" not in sess:
            acc_loso, preds = leave_one_session_out(X, y, sess, args.k)
            loso_txt = f"{acc_loso:>23.1%}"
            if best is None or acc_loso > best[1]:
                best = (kind, acc_loso, preds)
        else:
            loso_txt = f"{'(needs 2+ named sessions)':>24}"
        print(f"{kind:<9}{X.shape[1]:>5}{acc_rand:>15.1%} {loso_txt}")

    if best is None:
        return
    kind, acc, preds = best
    m = confusion(y, preds, labels)
    print(f"\nConfusion matrix, '{kind}' features, leave-one-session-out "
          "(rows = true letter, columns = predicted)")
    print("     " + "".join(f"{l:>4}" for l in labels))
    for i, l in enumerate(labels):
        print(f"{l:>4} " + "".join(f"{v:>4}" if v else "   ." for v in m[i]))

    pairs = [(m[i, j] + m[j, i], labels[i], labels[j])
             for i in range(len(labels)) for j in range(i + 1, len(labels)) if m[i, j] + m[j, i]]
    if pairs:
        print("\nMost confused pairs (collect more varied data for these first):")
        for n, a, b in sorted(pairs, reverse=True)[:5]:
            print(f"  {a} <-> {b}: {n} reps")


if __name__ == "__main__":
    main()
