#!/usr/bin/env python3
"""train_touch.py - learn which fingers touch the thumb, from pose labels.

The glove has no contact sensor. Touch is learned from pose: each pose label in
the batch CSV maps to a 0/1 touch vector through tools/pose_labels.py, and one
small logistic regression per thumb-finger pair (TI, TM, TR, TP) predicts that
bit from the 15 'dir' features of train_baseline.py (each finger's +Z axis in
the hand's frame, thumb to pinky, x y z each).

Evaluation is leave-one-session-out: train on all sessions but one, test on the
held-out one. A new session means the glove was taken off and put back on, so
this is the honest number. The gate also needs the near-miss poses (thumb about
1 cm away from the finger) to read as NOT touching.

The model is then trained on all rows and written as JSON for the dashboard:
    {"pairs":[...], "mu":[15], "sd":[15], "w":[[15] x 4], "b":[4],
     "synthetic":bool, "reps":n}
Inference is p = sigmoid(b + sum_k w[k] * (x[k] - mu[k]) / sd[k]).

Usage:
    python train_touch.py path/to/exports/ [--out touch_model.json]
"""

import argparse
import json
import sys

import numpy as np

from batch_io import find_csvs, load_batch
from pose_labels import NEAR_MISS, PAIRS, touch_vector
from train_baseline import features

RECALL_MIN = 0.90
FALSE_ALARM_MAX = 0.10


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def fit_logreg(X, y, seed=0, iters=5000, lr=0.5, l2=1e-4):
    """Full-batch gradient descent on weighted logistic loss with an L2 penalty.

    Standardises with this training set's mean/std only (the test set must not
    leak in). Class weights are inverse frequency, so a pair that touches in
    few poses is not ignored. Returns (mu, sd, w, b).
    """
    mu, sd = X.mean(0), X.std(0) + 1e-9
    A = (X - mu) / sd
    n_pos = max(int(y.sum()), 1)
    n_neg = max(int(len(y) - y.sum()), 1)
    sw = np.where(y == 1, len(y) / (2 * n_pos), len(y) / (2 * n_neg))
    rng = np.random.default_rng(seed)
    w = rng.normal(0, 0.01, X.shape[1])
    b = 0.0
    for _ in range(iters):
        p = sigmoid(A @ w + b)
        g = sw * (p - y)                       # d loss / d logit, per row
        w -= lr * (A.T @ g / len(y) + l2 * w)  # bias is not penalised
        b -= lr * g.mean()
    return mu, sd, w, b


def predict(model, X):
    mu, sd, w, b = model
    return sigmoid(((X - mu) / sd) @ w + b) > 0.5


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="batch CSV files and/or folders (run check_dataset.py first)")
    ap.add_argument("--out", default="touch_model.json")
    args = ap.parse_args()

    files = [load_batch(p) for p in find_csvs(args.paths)]
    files = [f for f in files if len(f.labels)]
    if not files:
        sys.exit("no data rows found")
    if any(not f.hand_relative for f in files):
        sys.exit("some files are pre-2026-10-06 exports (not hand-relative). Run check_dataset.py.")
    synthetic = any(f.synthetic for f in files)
    if synthetic:
        print("NOTE: input includes SYNTHETIC data. These numbers say nothing about the glove.\n")

    labels = [lab for f in files for lab in f.labels]
    sess = np.array([f.session for f in files for _ in f.labels])
    quat = np.concatenate([f.quat for f in files])
    T = [touch_vector(lab) for lab in labels]
    keep = np.array([t is not None for t in T])
    print(f"skipped {int((~keep).sum())} rows with a label that is not a touch pose")
    if not keep.any():
        sys.exit("no touch-pose rows found")
    labels = np.array(labels)[keep]
    sess = sess[keep]
    X = features(quat[keep], "dir")
    Y = np.array([t for t in T if t is not None])            # (rows, 4)

    named = set(sess) - {"?"}
    if len(named) < 2 or "?" in sess:
        sys.exit("need at least 2 named sessions (file names like handrig_batch_POSES_01_<ts>.csv)")
    print(f"{len(Y)} rows, {len(named)} sessions\n")

    # Leave-one-session-out predictions for every pair.
    pred = np.zeros_like(Y)
    for s in sorted(named):
        te = sess == s
        for j in range(len(PAIRS)):
            pred[te, j] = predict(fit_logreg(X[~te], Y[~te, j]), X[te])

    near = np.isin(labels, NEAR_MISS)
    print(f"{'pair':<6}{'positives':>10}{'precision':>11}{'recall':>9}{'near-miss false alarms':>25}")
    failing = []
    for j, pair in enumerate(PAIRS):
        pos = Y[:, j] == 1
        tp = int((pred[:, j] & pos).sum())
        fp = int((pred[:, j] & ~pos).sum())
        prec = tp / (tp + fp) if tp + fp else float("nan")
        rec = tp / pos.sum() if pos.any() else float("nan")
        fa = pred[near, j].mean() if near.any() else float("nan")
        print(f"{pair:<6}{int(pos.sum()):>10}{prec:>11.1%}{rec:>9.1%}{fa:>25.1%}")
        if pos.any() and not (rec >= RECALL_MIN and (np.isnan(fa) or fa <= FALSE_ALARM_MAX)):
            failing.append(pair)
    if failing:
        print(f"\nGATE FAIL: {', '.join(failing)} "
              f"(need recall >= {RECALL_MIN:.0%} and near-miss false alarms <= {FALSE_ALARM_MAX:.0%})")
    else:
        print("\nGATE PASS")

    models = [fit_logreg(X, Y[:, j]) for j in range(len(PAIRS))]
    out = {"pairs": PAIRS,
           "mu": models[0][0].tolist(), "sd": models[0][1].tolist(),    # same X, so same for all pairs
           "w": [m[2].tolist() for m in models], "b": [float(m[3]) for m in models],
           "synthetic": synthetic, "reps": int(len(Y))}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
