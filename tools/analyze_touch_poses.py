#!/usr/bin/env python3
"""analyze_touch_poses.py - score two touch detectors on the touch-pose test (S05 section 7).

Input: the TOUCHTEST batch files, one per hand attitude (01 palm forward,
02 palm down, 03 palm toward the face), classes F, SPACE, BKSP, W (touches),
NF, NSPACE, NBKSP, NW (the same with a ~1 cm gap), REST and FREE.

Near misses count as touches (decision L7): they are relabelled to their touch
class for training and scoring, and their acceptance is also shown on its own.

Two designs:

  A  nearest class centroid on dir15, the hand-relative finger directions from
     the fused quaternions (train_baseline.features(..., "dir")). Accept the
     nearest class only if its distance is < 0.7 x the second nearest, else "none".
  C  multinomial logistic regression on G18z, the per-sensor gravity vectors with
     each sensor's calibration tilt removed (spec S06). Accept the top class only
     if its probability is >= 0.6, else "none".

Both z-score the features with the training fold's mean and std only.

Splits: leave-one-attitude-out (train on two attitudes, test on the third) and
leave-one-rep-out (hold out every row with the same rep number).

Metrics:
  touch recall      real touches (not near misses) read as the right touch
  wrong pair        touch-class rows (near misses included) read as another touch
  false accept      REST and FREE rows read as any touch
  near-miss accept  near misses read as their own touch (information only)

Verdict (S05 7.4): a design passes on a split if recall >= 90 %, wrong pair <= 5 %
and false accept <= 5 %. Leave-one-attitude-out is the split that decides.

Usage:
    python analyze_touch_poses.py path/to/TOUCHTEST/files/
"""

import argparse
import sys

import numpy as np

from batch_io import find_csvs, load_batch, session_key
from train_baseline import features

TOUCHES = ["F", "SPACE", "BKSP", "W"]
NEAR = {"N" + t: t for t in TOUCHES}
CLASSES = TOUCHES + ["REST", "FREE"]
RATIO_A = 0.7          # design A: best distance must be < this x the second best
PMIN_C = 0.6           # design C: reject below this top probability
PASS_RECALL, PASS_WRONG, PASS_FALSE = 0.90, 0.05, 0.05


def zscore(Xtr, Xte):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    return (Xtr - mu) / sd, (Xte - mu) / sd


def design_a(Xtr, ytr, Xte):
    A, B = zscore(Xtr, Xte)
    cls = [c for c in CLASSES if (ytr == c).any()]
    cent = np.array([A[ytr == c].mean(0) for c in cls])
    d = np.linalg.norm(B[:, None, :] - cent[None, :, :], axis=-1)     # (test, classes)
    order = np.argsort(d, axis=1)
    best, second = d[np.arange(len(B)), order[:, 0]], d[np.arange(len(B)), order[:, 1]]
    pred = np.array(cls)[order[:, 0]].astype(object)
    pred[~(best < RATIO_A * second)] = "none"
    return pred


def fit_softmax(X, y, iters=3000, lr=0.5, l2=1e-3):
    """Multinomial logistic regression by plain gradient descent.
    p = softmax(X W + b); the gradient of the mean cross-entropy is X^T (p - onehot) / n."""
    n, d = X.shape
    k = len(CLASSES)
    Y = np.zeros((n, k))
    Y[np.arange(n), [CLASSES.index(c) for c in y]] = 1
    W, b = np.zeros((d, k)), np.zeros(k)
    for _ in range(iters):
        p = softmax(X @ W + b)
        W -= lr * (X.T @ (p - Y) / n + l2 * W)
        b -= lr * (p - Y).mean(0)
    return W, b


def softmax(z):
    z = z - z.max(1, keepdims=True)          # subtracting the max avoids overflow in exp
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


def design_c(Xtr, ytr, Xte):
    A, B = zscore(Xtr, Xte)
    W, b = fit_softmax(A, ytr)
    p = softmax(B @ W + b)
    pred = np.array(CLASSES, dtype=object)[p.argmax(1)]
    pred[p.max(1) < PMIN_C] = "none"
    return pred


def run_split(design, X, y, groups):
    pred = np.empty(len(y), dtype=object)
    for g in np.unique(groups):
        te = groups == g
        if len(set(y[~te])) < 2:
            sys.exit(f"split leaves fewer than 2 classes to train on (group {g})")
        pred[te] = design(X[~te], y[~te], X[te])
    return pred


def metrics(y, pred, near):
    touch = np.isin(y, TOUCHES)
    real = touch & ~near
    other_touch = np.isin(pred, TOUCHES) & (pred != y)
    nontouch = ~touch
    rate = lambda m, sel: m[sel].mean() if sel.any() else float("nan")   # noqa: E731
    return {"recall": rate(pred == y, real),
            "wrong": rate(other_touch, touch),
            "false": rate(np.isin(pred, TOUCHES), nontouch),
            "near": rate(pred == y, near)}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="TOUCHTEST batch CSV files and/or folders")
    args = ap.parse_args()

    files = [load_batch(p) for p in find_csvs(args.paths)]
    files = [f for f in files if len(f.labels)]
    if not files:
        sys.exit("no data rows found")
    if any(f.synthetic for f in files):
        print("NOTE: input includes SYNTHETIC data. These numbers say nothing about the glove.\n")

    labels = np.array([lab for f in files for lab in f.labels])
    keep = np.isin(labels, CLASSES + list(NEAR))
    if not keep.any():
        sys.exit("no touch-test rows (F, SPACE, BKSP, W, N*, REST, FREE). "
                 "Synthetic: make_synthetic_batch.py --poses touchtest")
    near = np.isin(labels, list(NEAR))[keep]
    y = np.array([NEAR.get(l, l) for l in labels])[keep]
    att = np.array([session_key(f) for f in files for _ in f.labels])[keep]
    rep = np.array([r for f in files for r in f.reps])[keep]
    Xa = np.concatenate([features(f, "dir") for f in files])[keep]
    Xc = np.concatenate([features(f, "G18z") for f in files])[keep]

    print(f"{keep.sum()} rows ({int(near.sum())} near misses), {len(set(att))} attitudes "
          f"{sorted(map(str, set(att)))}, skipped {int((~keep).sum())} rows with other labels\n")

    splits = [("leave-one-attitude-out", att), ("leave-one-rep-out", rep)]
    designs = [("A dir15 centroid", design_a, Xa), ("C G18z logreg", design_c, Xc)]
    print(f"{'design':<18}{'split':<24}{'recall':>8}{'wrong pr':>10}{'false acc':>11}"
          f"{'near acc':>10}  verdict")
    verdict = {}
    for dname, design, X in designs:
        for sname, groups in splits:
            if len(set(groups)) < 2:
                print(f"{dname:<18}{sname:<24}  (needs 2+ groups)")
                continue
            m = metrics(y, run_split(design, X, y, groups), near)
            ok = m["recall"] >= PASS_RECALL and m["wrong"] <= PASS_WRONG and m["false"] <= PASS_FALSE
            verdict[(dname[0], sname)] = ok
            print(f"{dname:<18}{sname:<24}{m['recall']:>8.1%}{m['wrong']:>10.1%}{m['false']:>11.1%}"
                  f"{m['near']:>10.1%}  {'PASS' if ok else 'fail'}")

    loao = {d: verdict.get((d, "leave-one-attitude-out"), False) for d in "AC"}
    loro = {d: verdict.get((d, "leave-one-rep-out"), False) for d in "AC"}
    print("\nDecision (S05 7.4):")
    if loao["A"] and loao["C"]:
        print("  both pass leave-one-attitude-out -> take C (drift-free, easy on the device)")
    elif loao["A"] or loao["C"]:
        print(f"  only {'A' if loao['A'] else 'C'} passes leave-one-attitude-out -> take it")
    elif loro["A"] or loro["C"]:
        print("  passes only leave-one-rep-out -> go ahead; the letter data varies attitude. Note it.")
    else:
        print("  neither passes even leave-one-rep-out -> kill rule K1: SPACE and BKSP become non-touch poses")


if __name__ == "__main__":
    main()
