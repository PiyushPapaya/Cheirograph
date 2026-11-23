"""train_classifier.py - rung 2 and 3 of the classifier ladder (spec S07).

Trains a multinomial logistic regression or a one-hidden-layer MLP on the batch
CSVs, in plain numpy, so every gradient can be explained. Compares with the kNN
from train_baseline.py using leave-one-session-out (LOSO), and exports the model.

    python train_classifier.py ml/dataset/ --features G18z --model logreg
    python train_classifier.py ml/dataset/ --model mlp --export ml/model_G18z_mlp
    python train_classifier.py --selftest

Pieces
    standardise   mean and std come from the TRAINING fold only, and are stored in the export.
    logreg        scores = x W^T + b, softmax, cross-entropy, L2 1e-3, full-batch
                  gradient descent, lr 0.5, 2000 steps. Gradient of the loss wrt the scores
                  is (p - onehot) / n, so dW = that^T x + l2 W.
    mlp           D -> 32 -> C, ReLU, softmax, Adam (lr 1e-2), L2 1e-4, 300 epochs,
                  fixed seed, backprop written out in train_mlp().
    reject        a prediction counts only if top probability >= tau and
                  top - second >= margin (0.2). A rejected rep counts as wrong in the
                  accuracy printed here.
    export        PREFIX.json (schema 1) and PREFIX.h (static const float arrays, same
                  numbers). W is stored one ROW PER CLASS: logreg W[C][D]; mlp W1[H][D],
                  W2[C][H]. --fixture FILE writes 50 rows of (features, probabilities)
                  for JS and C++ checks.

Not done here: confusion PNG, transition rejection and the tau sweep against raw
windows (S07 section 3 and 4). The tau sweep printed is over the LOSO predictions only.
Synthetic input is flagged, and accuracies on it say nothing about the glove.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import numpy as np

from batch_io import find_csvs, load_batch, session_key
from train_baseline import FEATURE_SETS, features, knn_predict

HIDDEN = 32
MARGIN = 0.2


# ---------- models ----------

def softmax(z):
    z = z - z.max(axis=1, keepdims=True)            # shift so exp() cannot overflow
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def standardise_fit(X):
    return X.mean(0), X.std(0) + 1e-9


def train_logreg(Z, yi, C, l2=1e-3, lr=0.5, steps=2000):
    n, d = Z.shape
    Y = np.eye(C)[yi]
    W = np.zeros((C, d))
    b = np.zeros(C)
    for _ in range(steps):
        P = softmax(Z @ W.T + b)
        G = (P - Y) / n                              # d loss / d scores
        W -= lr * (G.T @ Z + l2 * W)
        b -= lr * G.sum(0)
    return {"kind": "logreg", "W": W, "b": b}


def train_mlp(Z, yi, C, h=HIDDEN, l2=1e-4, lr=1e-2, epochs=300, seed=0):
    n, d = Z.shape
    rng = np.random.default_rng(seed)
    p = {"W1": rng.normal(0, np.sqrt(2.0 / d), (h, d)), "b1": np.zeros(h),
         "W2": rng.normal(0, np.sqrt(2.0 / h), (C, h)), "b2": np.zeros(C)}
    m = {k: np.zeros_like(v) for k, v in p.items()}
    v2 = {k: np.zeros_like(v) for k, v in p.items()}
    Y = np.eye(C)[yi]
    b1c, b2c, eps = 0.9, 0.999, 1e-8
    bs = 64
    t = 0
    for _ in range(epochs):
        order = rng.permutation(n)
        for s in range(0, n, bs):
            idx = order[s:s + bs]
            x, y = Z[idx], Y[idx]
            a1 = x @ p["W1"].T + p["b1"]
            r1 = np.maximum(a1, 0)                   # ReLU
            P = softmax(r1 @ p["W2"].T + p["b2"])
            G2 = (P - y) / len(idx)                  # d loss / d scores
            grad = {"W2": G2.T @ r1 + l2 * p["W2"], "b2": G2.sum(0)}
            G1 = (G2 @ p["W2"]) * (a1 > 0)           # back through the ReLU
            grad["W1"] = G1.T @ x + l2 * p["W1"]
            grad["b1"] = G1.sum(0)
            t += 1
            for k in p:                              # Adam
                m[k] = b1c * m[k] + (1 - b1c) * grad[k]
                v2[k] = b2c * v2[k] + (1 - b2c) * grad[k] ** 2
                mh, vh = m[k] / (1 - b1c ** t), v2[k] / (1 - b2c ** t)
                p[k] -= lr * mh / (np.sqrt(vh) + eps)
    return {"kind": "mlp", **p}


def scores_to_proba(model, Z):
    if model["kind"] == "logreg":
        return softmax(Z @ model["W"].T + model["b"])
    r1 = np.maximum(Z @ model["W1"].T + model["b1"], 0)
    return softmax(r1 @ model["W2"].T + model["b2"])


def fit(X, yi, C, kind, seed=0):
    mu, sd = standardise_fit(X)
    Z = (X - mu) / sd
    m = train_logreg(Z, yi, C) if kind == "logreg" else train_mlp(Z, yi, C, seed=seed)
    m["mean"], m["std"] = mu, sd
    return m


def proba(model, X):
    return scores_to_proba(model, (X - model["mean"]) / model["std"])


def accept(P, tau, margin=MARGIN):
    """Boolean per row: top probability >= tau and top - second >= margin."""
    s = np.sort(P, axis=1)
    return (s[:, -1] >= tau) & (s[:, -1] - s[:, -2] >= margin)


# ---------- evaluation ----------

def loso(X, yi, sess, C, kind, seed=0):
    """Out-of-fold probabilities (kNN has none: returns predictions as a one-hot)."""
    P = np.zeros((len(yi), C))
    for s in np.unique(sess):
        te = sess == s
        if kind == "knn":
            pred = knn_predict(X[~te], yi[~te], X[te], 5)
            P[te] = np.eye(C)[pred]
        else:
            P[te] = proba(fit(X[~te], yi[~te], C, kind, seed), X[te])
    return P


def report(P, yi, classes, tau):
    pred = P.argmax(1)
    ok = accept(P, tau)
    print(f"  accuracy, rejects counted wrong (tau {tau}): {np.mean(ok & (pred == yi)):.1%}"
          f"   without reject: {np.mean(pred == yi):.1%}   rejected: {np.mean(~ok):.1%}")
    print(f"  {'class':<7}{'n':>5}{'recall':>9}{'precision':>11}")
    for c, name in enumerate(classes):
        n = int((yi == c).sum())
        tp = int(((pred == c) & (yi == c)).sum())
        npred = int((pred == c).sum())
        print(f"  {name:<7}{n:>5}{tp / max(n, 1):>9.1%}{tp / max(npred, 1):>11.1%}")


# ---------- export ----------

def export_json(model, classes, feat, tau, sessions, path):
    d = {"schema": 1, "features": feat, "classes": list(classes),
         "mean": model["mean"].tolist(), "std": model["std"].tolist(),
         "kind": model["kind"], "tau": tau, "margin": MARGIN, "trainedOn": sorted(sessions)}
    if model["kind"] == "logreg":
        d.update(W=model["W"].tolist(), b=model["b"].tolist(), hidden=None)
    else:
        d.update(W1=model["W1"].tolist(), b1=model["b1"].tolist(),
                 W2=model["W2"].tolist(), b2=model["b2"].tolist(), hidden=model["W1"].shape[0])
    Path(path).write_text(json.dumps(d), encoding="utf-8")


def load_json(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    m = {k: (np.array(v) if isinstance(v, list) and k != "classes" and k != "trainedOn" else v)
         for k, v in d.items()}
    return m


def predict_json(d, X):
    """Probabilities from an exported model, using only what is in the JSON."""
    Z = (X - d["mean"]) / d["std"]
    return scores_to_proba(d, Z)


def _arr(name, a):
    flat = ", ".join(f"{v:.9g}f" for v in np.ravel(a))
    dims = "".join(f"[{n}]" for n in np.shape(a))
    return f"static const float {name}{dims} = {{ {flat} }};\n" if np.ndim(a) == 1 else \
        f"static const float {name}{dims} = {{\n" + "".join(
            "  { " + ", ".join(f"{v:.9g}f" for v in row) + " },\n" for row in a) + "};\n"


def export_header(d, json_name, path):
    classes = d["classes"]
    out = [f"// Generated by tools/train_classifier.py from {json_name} on {date.today()}. Do not edit.\n",
           f"// Features: {d['features']}, model: {d['kind']}. Weights are one ROW PER CLASS.\n",
           "#pragma once\n",
           f"#define MODEL_D {len(d['mean'])}\n#define MODEL_C {len(classes)}\n",
           f"#define MODEL_TAU {d['tau']}f\n#define MODEL_MARGIN {d['margin']}f\n"]
    if d["kind"] == "mlp":
        out.append(f"#define MODEL_H {d['W1'].shape[0]}\n")
    out.append("static const char* const MODEL_CLASSES[MODEL_C] = { "
               + ", ".join(json.dumps(c) for c in classes) + " };\n")
    out.append(_arr("MODEL_MEAN", d["mean"]))
    out.append(_arr("MODEL_STD", d["std"]))
    for k in (("W", "b") if d["kind"] == "logreg" else ("W1", "b1", "W2", "b2")):
        out.append(_arr("MODEL_" + k, d[k]))
    Path(path).write_text("".join(out), encoding="utf-8")


def export_fixture(d, X, path, n=50):
    rows = X[np.linspace(0, len(X) - 1, min(n, len(X))).astype(int)]
    P = predict_json(d, rows)
    Path(path).write_text(json.dumps([{"x": r.tolist(), "p": p.tolist()}
                                      for r, p in zip(rows, P)]), encoding="utf-8")


# ---------- data ----------

def load_data(paths, feat):
    files = [load_batch(p) for p in find_csvs(paths)]
    files = [f for f in files if len(f.labels)]
    if not files:
        sys.exit("no data rows found")
    if any(not f.hand_relative for f in files):
        sys.exit("some files are pre-2026-10-06 exports (not hand-relative). Run check_dataset.py.")
    if any(f.synthetic for f in files):
        print("NOTE: input includes SYNTHETIC data. These accuracies say nothing about the glove.\n")
    X = np.concatenate([features(f, feat) for f in files])
    y = np.array([lab for f in files for lab in f.labels])
    sess = np.array([session_key(f) for f in files for _ in f.labels])
    return X, y, sess


# ---------- self-test ----------

def find_cxx():
    import shutil
    from glob import glob
    c = shutil.which("g++")
    if c:
        return c
    hits = glob(str(Path.home() / "AppData/Local/Arduino15/packages/*/tools/arm-none-eabi-gcc/*/bin/arm-none-eabi-g++*"))
    return hits[0] if hits else None


def selftest():
    here = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        subprocess.run([sys.executable, str(here / "make_synthetic_batch.py"), "--out", str(tmp / "b"),
                        "--sessions", "5", "--reps", "15", "--seed", "0"],
                       check=True, capture_output=True, text=True)
        X, y, sess = load_data([str(tmp / "b")], "quat")
        classes = sorted(set(y))
        yi = np.array([classes.index(c) for c in y])
        C = len(classes)
        assert len(np.unique(sess)) == 5, "expected 5 sessions"

        acc = {}
        for kind in ("knn", "logreg", "mlp"):
            P = loso(X, yi, sess, C, kind)
            acc[kind] = float(np.mean(P.argmax(1) == yi))
            print(f"selftest LOSO {kind:<7} {acc[kind]:.1%}")
        assert acc["logreg"] >= acc["knn"] - 0.03, f"logreg {acc['logreg']:.3f} vs knn {acc['knn']:.3f}"
        assert acc["mlp"] > 0.5, "mlp failed to learn at all"

        for kind in ("logreg", "mlp"):
            m = fit(X, yi, C, kind)
            jp, hp = tmp / f"m_{kind}.json", tmp / f"m_{kind}.h"
            export_json(m, classes, "quat", 0.8, sorted(set(sess)), jp)
            d = load_json(jp)
            P0, P1 = proba(m, X), predict_json(d, X)
            assert np.array_equal(P0.argmax(1), P1.argmax(1)), f"{kind}: predictions differ after reload"
            assert np.allclose(P0, P1, atol=1e-12), f"{kind}: probabilities differ after reload"
            print(f"selftest JSON round trip {kind}: identical predictions on {len(X)} rows")

            export_header(d, jp.name, hp)
            cxx = find_cxx()
            if cxx is None:
                print(f"selftest C header {kind}: SKIPPED (no g++ or arm-none-eabi-g++ found)")
                continue
            tu = tmp / f"t_{kind}.cpp"
            tu.write_text(f'#include "{hp.name}"\nint main(){{ return (int)MODEL_D + (int)MODEL_C; }}\n')
            r = subprocess.run([cxx, "-fsyntax-only", "-Wall", str(tu)], capture_output=True, text=True)
            assert r.returncode == 0, f"{kind} header failed to compile:\n{r.stderr}"
            print(f"selftest C header {kind}: syntax OK ({Path(cxx).name})")

        fx = tmp / "fix.json"
        export_fixture(load_json(tmp / "m_logreg.json"), X, fx)
        assert len(json.loads(fx.read_text())) == 50
    print("PASS")


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="batch CSV files and/or folders")
    ap.add_argument("--features", default="quat", choices=FEATURE_SETS, help="feature set (default quat)")
    ap.add_argument("--model", default="logreg", choices=["knn", "logreg", "mlp"])
    ap.add_argument("--tau", type=float, default=0.8, help="reject threshold on the top probability")
    ap.add_argument("--export", metavar="PREFIX", help="write PREFIX.json and PREFIX.h (not for knn)")
    ap.add_argument("--fixture", metavar="FILE", help="write 50 rows of (features, probabilities)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.paths:
        ap.error("give batch CSV paths, or --selftest")

    X, y, sess = load_data(args.paths, args.features)
    classes = sorted(set(y))
    yi = np.array([classes.index(c) for c in y])
    C = len(classes)
    sessions = sorted(set(sess))
    print(f"{len(y)} reps, {C} classes, {len(sessions)} sessions, features {args.features}, model {args.model}\n")

    if len(sessions) >= 2 and "?" not in sessions:
        P = loso(X, yi, sess, C, args.model, args.seed)
        print("Leave-one-session-out:")
        report(P, yi, classes, args.tau)
        if args.model != "knn":
            print("\n  tau sweep (LOSO): tau, accuracy with rejects wrong, fraction rejected")
            for tau in np.arange(0.4, 0.96, 0.1):
                ok = accept(P, tau)
                print(f"  {tau:.2f}  {np.mean(ok & (P.argmax(1) == yi)):.1%}  {np.mean(~ok):.1%}")
    else:
        print("LOSO needs 2+ named sessions, skipped.")

    if args.export:
        if args.model == "knn":
            sys.exit("knn has nothing to export")
        m = fit(X, yi, C, args.model, args.seed)
        jp, hp = Path(args.export + ".json"), Path(args.export + ".h")
        export_json(m, classes, args.features, args.tau, sessions, jp)
        d = load_json(jp)
        assert np.array_equal(proba(m, X).argmax(1), predict_json(d, X).argmax(1)), "reload check failed"
        export_header(d, jp.name, hp)
        print(f"\nwrote {jp} and {hp}")
        if args.fixture:
            export_fixture(d, X, args.fixture)
            print(f"wrote {args.fixture}")


if __name__ == "__main__":
    main()
