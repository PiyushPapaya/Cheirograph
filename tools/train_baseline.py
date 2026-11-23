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

  G18, G18z, P5, R5 and their combinations: gravity-only sets from the raw
        accel (spec S06), explained at gravity_up() below. They cannot drift
        in heading, and they keep the hand's own attitude (needed for G/H/P/Q).

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
    python train_baseline.py path/to/exports/ [--k 5] [--report-drift]
"""

import argparse
import sys
from collections import Counter
from types import SimpleNamespace

import numpy as np

from batch_io import find_csvs, load_batch, offsets_of, session_key

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


# ---------- gravity features (spec S06) ----------
#
# A still accelerometer measures the reaction to gravity: a vector pointing UP,
# expressed in that sensor's own frame. Normalised, it is three numbers per sensor
# that cannot drift, because gravity is always there. Flat hand: every g_s = (0,1,0)
# in the model frame (+Y out of the back of the hand, +Z to the fingertips).

# Sensor frame -> model frame, the same remaps as REMAPS in the dashboard. Row i of
# the matrix says which sensor axis becomes model axis i:
#   hand  hand_fwd_pX: (x, y, z) -> (-y, -z, x)
#   thumb and fingers: (x, y, z) -> ( x,  z, -y)
# Both have det +1 (proper rotations), so the inverse is the transpose.
REMAP_HAND = np.array([[0, -1, 0], [0, 0, -1], [1, 0, 0]], float)
REMAP_FINGER = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)
REMAP_OF = np.array([REMAP_HAND] + [REMAP_FINGER] * 5)

# Sign of P5. +1: positive = the finger rotated about the model +X axis relative to
# the hand (right-hand rule), which is a curl toward the palm (it turns +Z toward -Y).
# S06 writes the formula with the opposite sign. The curl sign on the glove itself is
# still an open item, so this is a convention, not a measured fact. A classifier does
# not care which sign is used, only that every file uses the same one.
CURL_SIGN = +1

# Below this length the in-plane part of gravity is too short to give a stable angle
# (gravity lies close to the rotation axis). The angle is set to 0 there (S06).
PLANE_MIN = 0.3


def _meta(meta, key):
    return meta.get(key) if isinstance(meta, dict) else None


def gravity_up(raw, meta=None):
    """raw (rows, 6, 6) -> unit "up" vectors (rows, 6, 3) in the model frame.

    1. subtract each sensor's accel offset (meta offsets, else the defaults),
    2. remap sensor frame -> model frame (skipped for synthetic files that say
       rawFrame = "model"),
    3. normalise, so only the direction is kept."""
    off = offsets_of(SimpleNamespace(meta=meta))
    a = raw[:, :, 0:3] - off[None, :, :]
    if _meta(meta, "rawFrame") != "model":
        # for every row r and sensor s: a_model = M_s @ a_sensor
        a = np.einsum("sij,rsj->rsi", REMAP_OF, a)
    n = np.linalg.norm(a, axis=-1, keepdims=True)
    return a / np.where(n > 1e-9, n, 1.0)


def shortest_arc_to_y(u):
    """Rotation matrix taking unit vector u onto +Y along the shortest arc.

    The quaternion is q = normalise(1 + u.Y, u x Y): the axis u x Y is perpendicular
    to both, and the half-angle trick (1 + cos a, sin a * axis) needs no trig.
    u x Y = (-u_z, 0, u_x), so q = normalise(1 + u_y, -u_z, 0, u_x) in (w, x, y, z).
    (S06 writes (u_z, 0, -u_x): that is the inverse rotation, Y onto u.)
    u = -Y: u x Y vanishes and any 180 deg turn about a horizontal axis works; use X."""
    ux, uy, uz = u
    if uy < -0.9999:
        q = np.array([0.0, 1.0, 0.0, 0.0])
    else:
        q = np.array([1 + uy, -uz, 0.0, ux])
        q /= np.linalg.norm(q)
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


_warned = set()


def _warn_once(msg):
    if msg not in _warned:
        _warned.add(msg)
        print("WARNING: " + msg, file=sys.stderr)


def gravity_zeroed(g, meta):
    """G18z: rotate each sensor's up vector by Z_s, the rotation that takes the up
    vector it saw at the session's calibration (meta calUp, model frame) onto +Y.
    So in the calibration pose every sensor reads (0,1,0), whatever its mount tilt.
    Missing calUp for a sensor -> that sensor stays as in G18, with a warning."""
    cal = _meta(meta, "calUp")
    out = g.copy()
    for s in range(6):
        u = cal[s] if isinstance(cal, list) and len(cal) == 6 else None
        if u is None:
            _warn_once("no calUp in meta for some sensors: G18z falls back to G18 there")
            continue
        u = np.asarray(u, float)
        out[:, s, :] = g[:, s, :] @ shortest_arc_to_y(u / np.linalg.norm(u)).T
    return out


def rel_angle(h, f, axis):
    """Signed angle (deg) the finger is rotated by relative to the hand about a model
    axis, read from the two up vectors alone (S06 P5, and R5 the same way about Z).

    If the finger is the hand rotated by +theta about axis A, the finger sees gravity
    turned by -theta, so the angle from f back to h about A is +theta:
        theta = atan2(A . (f x h), f . h), both taken in the plane perpendicular to A.
    Turning the whole hand turns h and f together, so the angle does not change.
    Set to 0 when either vector has less than PLANE_MIN in that plane: gravity then
    lies near the axis and the angle is undefined (P5: hand on its side; R5: fingers
    pointing straight up or down, which includes the ASL neutral posture)."""
    i, j = {"x": (1, 2), "z": (0, 1)}[axis]      # the two in-plane components
    cross = f[..., i] * h[..., j] - f[..., j] * h[..., i]
    dot = f[..., i] * h[..., i] + f[..., j] * h[..., j]
    ang = np.degrees(np.arctan2(cross, dot))
    ok = (np.hypot(h[..., i], h[..., j]) >= PLANE_MIN) & (np.hypot(f[..., i], f[..., j]) >= PLANE_MIN)
    return np.where(ok, ang, 0.0)


# ---------- feature sets ----------

def _part(kind, quat, raw, meta):
    if kind in ("quat", "dir", "curl", "T3"):
        fq = quat[:, 1:, :]                       # sensor 0 (hand) is skipped
        if kind == "quat":
            return fq.reshape(len(fq), -1)
        d = finger_direction(fq)                  # (rows, 5, 3)
        if kind == "dir":
            return d.reshape(len(d), -1)
        if kind == "curl":
            return d[:, :, 1]
        return d[:, 0, :]                         # T3: thumb direction only
    if raw is None:
        raise ValueError(f"feature set {kind!r} needs raw accel: pass a BatchFile, not a quat array")
    g = gravity_up(raw, meta)                     # (rows, 6, 3)
    if kind == "G18":
        return g.reshape(len(g), -1)
    if kind == "Ghand":
        return g[:, 0, :]
    if kind == "G18z":
        gz = gravity_zeroed(g, meta)
        return gz.reshape(len(gz), -1)
    h = g[:, :1, :]                               # hand, broadcast against the 5 fingers
    if kind == "P5":
        return CURL_SIGN * rel_angle(h, g[:, 1:, :], "x")
    if kind == "R5":
        return rel_angle(h, g[:, 1:, :], "z")
    raise ValueError(kind)


def features(data, kind, raw=None, meta=None):
    """Feature matrix (rows, dims) for one feature set.

    data: a BatchFile (raw, quat and meta are taken from it), or a quat array
    (rows, 6 sensors, 4) as before, plus raw and meta as keywords for the gravity
    sets. Sensor 0 is the hand. A "+" joins sets side by side: "G18z+P5"."""
    if hasattr(data, "quat"):
        quat, raw, meta = data.quat, data.raw, data.meta
    else:
        quat = data
    return np.concatenate([_part(k, quat, raw, meta) for k in kind.split("+")], axis=1)


# quat, dir, curl, T3 come from the fused orientation and drift in heading.
# G18, G18z, P5, R5 come from gravity only (spec S06 section 2).
FEATURE_SETS = ["quat", "dir", "curl", "G18", "G18z", "P5", "P5+R5",
                "G18z+P5", "G18z+T3", "dir+Ghand"]
HEADING_SETS = {"quat", "dir", "curl", "G18z+T3", "dir+Ghand"}

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

# ---------- drift timing ----------

DRIFT_BINS = [(0, 5), (5, 10), (10, 20), (20, float("inf"))]   # minutes, as in S06 section 6


def minutes_since_zero(bf):
    """Per row: minutes since the last full calibration or Zero press before it.

    meta.zeros holds the epoch ms of each one, the rows' t_ms column is epoch ms
    too (Date.now() in the dashboard). NaN when the file has no zeros or a row
    comes before the first one."""
    zeros = _meta(bf.meta, "zeros")
    t = np.asarray(bf.t_ms, float)
    if not isinstance(zeros, list) or not zeros:
        return np.full(len(t), np.nan)
    z = np.sort(np.asarray(zeros, float))
    i = np.searchsorted(z, t, side="right") - 1           # index of the last zero <= t
    out = np.where(i >= 0, (t - z[np.maximum(i, 0)]) / 60000.0, np.nan)
    return out


def report_drift(files, y, all_preds):
    """Accuracy per time bin. Heading sets should fall off as the bins get later,
    gravity sets should not: that is the drift the choice rule in S06 tests for."""
    mins = np.concatenate([minutes_since_zero(f) for f in files])
    known = np.isfinite(mins)
    print(f"\nAccuracy vs minutes since the last zero (leave-one-session-out), "
          f"{int(known.sum())} of {len(y)} reps have a time:")
    if not known.any() or not all_preds:
        print("  nothing to report (no meta zeros, or fewer than 2 named sessions)")
        return
    heads = [f"{a:g}-{b:g} min" if b != float("inf") else f">{a:g} min" for a, b in DRIFT_BINS]
    print(f"{'features':<11}" + "".join(f"{h:>14}" for h in heads))
    masks = [known & (mins >= a) & (mins < b) for a, b in DRIFT_BINS]
    print(f"{'  reps':<11}" + "".join(f"{int(m.sum()):>14}" for m in masks))
    for kind, preds in all_preds.items():
        cells = [f"{(preds[m] == y[m]).mean():>14.1%}" if m.any() else f"{'-':>14}" for m in masks]
        print(f"{kind:<11}" + "".join(cells))


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="batch CSV files and/or folders (run check_dataset.py first)")
    ap.add_argument("--k", type=int, default=5, help="neighbours to vote (default 5)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--report-drift", action="store_true",
                    help="leave-one-session-out accuracy binned by minutes since the last "
                         "calibration or Zero press (needs meta zeros in the files)")
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
    sess = np.array([session_key(f) for f in files for _ in f.labels])
    labels = sorted(set(y))
    n_sess = len(set(sess) - {"?"})
    print(f"{len(y)} reps, {len(labels)} letters, {n_sess} sessions, k = {args.k}\n")

    rng = np.random.default_rng(args.seed)
    print(f"{'features':<11}{'dims':>5}{'random split':>15}{'leave-one-session-out':>24}")
    best, all_preds = None, {}
    for kind in FEATURE_SETS:
        # per file, because offsets and calUp in the meta line belong to one file
        X = np.concatenate([features(f, kind) for f in files])
        acc_rand = random_split(X, y, args.k, rng)
        if n_sess >= 2 and "?" not in sess:
            acc_loso, preds = leave_one_session_out(X, y, sess, args.k)
            all_preds[kind] = preds
            loso_txt = f"{acc_loso:>23.1%}"
            if best is None or acc_loso > best[1]:
                best = (kind, acc_loso, preds)
        else:
            loso_txt = f"{'(needs 2+ named sessions)':>24}"
        drift = "" if kind not in HEADING_SETS else "   (heading drifts)"
        print(f"{kind:<11}{X.shape[1]:>5}{acc_rand:>15.1%} {loso_txt}{drift}")

    if args.report_drift:
        report_drift(files, y, all_preds)

    if best is None:
        return
    kind, acc, preds = best
    m = confusion(y, preds, labels)
    print(f"\nConfusion matrix, '{kind}' features, leave-one-session-out "
          "(rows = true letter, columns = predicted)")
    print("     " + "".join(f"{l:>4}" for l in labels))
    for i, l in enumerate(labels):
        print(f"{l:>4} " + "".join(f"{v:>4}" if v else "   ." for v in m[i]))

    # recall = of the reps that really were this letter, the share read as it
    recall = m.diagonal() / np.maximum(m.sum(1), 1)
    print(f"\nPer-letter recall, '{kind}' features, leave-one-session-out (worst first):")
    for i in np.argsort(recall, kind="stable"):
        print(f"  {labels[i]:>6}  {recall[i]:6.1%}  ({m[i, i]}/{m[i].sum()})")

    pairs = [(m[i, j] + m[j, i], labels[i], labels[j])
             for i in range(len(labels)) for j in range(i + 1, len(labels)) if m[i, j] + m[j, i]]
    if pairs:
        print("\nMost confused pairs (collect more varied data for these first):")
        for n, a, b in sorted(pairs, reverse=True)[:5]:
            print(f"  {a} <-> {b}: {n} reps")


if __name__ == "__main__":
    main()
