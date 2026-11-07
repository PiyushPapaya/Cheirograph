#!/usr/bin/env python3
"""verify_touch_model.py - end-to-end checks for the touch-detection tooling.

1. Pose names fit the dashboard's 12-character label field; touch sets use known pairs.
2. POSE_LABELS in the dashboard equals the keys of POSES, in order.
3. make_synthetic_batch.py --poses output passes check_dataset.py, and its letter
   output for a fixed seed is unchanged (digest taken from the version before --poses).
4. Clean synthetic data (no session offset, near misses well apart) prints GATE PASS, and
   data with session offsets as large as the near-miss gap prints GATE FAIL: the gate must
   be able to reject touches it can't separate.
5. Leak check: the same data with labels shuffled per row must print GATE FAIL.
6. JS inference matches Python (verify_touch_js.mjs).

Usage:
    python verify_touch_model.py
Exit code 0 = every check passed. All checks run even if one fails.
"""

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PY = sys.executable
sys.path.insert(0, str(HERE))

from batch_io import find_csvs, load_batch                # noqa: E402
from pose_labels import PAIRS, POSES                       # noqa: E402
from train_baseline import features                        # noqa: E402
import train_touch                                         # noqa: E402

# sha256 over the letter rows (t_ms column dropped, files sorted by letter and session) of
#   make_synthetic_batch.py --sessions 2 --reps 3 --seed 5
# as written by the script before --poses existed.
LETTER_DIGEST = "a47369d8badd5ea7cc8646f25bd4dca0c5e4ac4df76752e777937f9b44d9b3a6"

failures = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} - {name}" + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def run(*cmd):
    r = subprocess.run([PY, *map(str, cmd)], capture_output=True, text=True, cwd=HERE)
    return r.returncode, r.stdout + r.stderr


def letter_digest(folder):
    h = hashlib.sha256()
    names = sorted(Path(folder).glob("*.csv"),
                   key=lambda p: (p.name.split("_")[2], p.name.split("_")[3]))
    for p in names:
        h.update(p.name.rsplit("_", 1)[0].encode())
        for line in p.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#"):
                f = line.split(",")
                h.update(",".join(f[:2] + f[3:]).encode())
    return h.hexdigest()


def main():
    tmp = Path(tempfile.mkdtemp(prefix="verify_touch_"))

    # 1
    long_names = [n for n in POSES if len(n) > 12]
    bad_pairs = [(n, t) for n, ts in POSES.items() for t in ts if t not in PAIRS]
    check("pose names <= 12 chars, touch entries in PAIRS", not long_names and not bad_pairs,
          f"{long_names} {bad_pairs}")

    # 2
    html = (HERE / "handrig_dashboard.html").read_text(encoding="utf-8")
    m = re.search(r"const POSE_LABELS=\[(.*?)\];", html)
    js_labels = re.findall(r'"([^"]+)"', m.group(1)) if m else None
    check("dashboard POSE_LABELS equals POSES keys in order", js_labels == list(POSES),
          f"{js_labels} vs {list(POSES)}")

    # 3
    code, out = run("make_synthetic_batch.py", "--out", tmp / "poses", "--poses",
                    "--sessions", 2, "--reps", 10)
    code2, out2 = run("check_dataset.py", tmp / "poses", "--goal-reps", 20, "--goal-sessions", 2)
    check("--poses output passes check_dataset.py", code == 0 and code2 == 0, out + out2)
    code, out = run("make_synthetic_batch.py", "--out", tmp / "letters", "--sessions", 2,
                    "--reps", 3, "--seed", 5)
    check("letter output unchanged for a fixed seed", code == 0 and letter_digest(tmp / "letters") == LETTER_DIGEST)

    # 4
    run("make_synthetic_batch.py", "--out", tmp / "clean", "--poses", "--sessions", 2, "--reps", 10,
        "--drift-deg", 0, "--curl-offset-sd", 0, "--near-deg", 30)
    code, out = run("train_touch.py", tmp / "clean", "--out", tmp / "model.json")
    gate = [l for l in out.splitlines() if l.startswith("GATE")]
    print("   " + (gate[0] if gate else "no GATE line"))
    check("clean synthetic data trains to GATE PASS", code == 0 and bool(gate) and gate[0].startswith("GATE PASS"),
          " | ".join(out.splitlines()[-9:]))
    code, out = run("train_touch.py", tmp / "poses", "--out", tmp / "hard.json")
    gate = [l for l in out.splitlines() if l.startswith("GATE")]
    print("   " + (gate[0] if gate else "no GATE line"))
    check("session offsets over the near-miss gap give GATE FAIL", bool(gate) and gate[0].startswith("GATE FAIL"), out)

    # 5: shuffle labels across rows, keep everything else
    shuf = tmp / "shuffled"
    shuf.mkdir()
    rng = np.random.default_rng(0)
    paths = find_csvs([tmp / "poses"])
    rows, labels = [], []
    for p in paths:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith(("#", "label")):
                rows.append(line.split(","))
                labels.append(rows[-1][0])
    perm = rng.permutation(len(labels))
    i = 0
    for p in paths:
        out_lines = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith(("#", "label")):
                f = line.split(",")
                f[0] = labels[perm[i]]
                i += 1
                line = ",".join(f)
            out_lines.append(line)
        (shuf / p.name).write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    code, out = run("train_touch.py", shuf, "--out", tmp / "shuffled_model.json")
    gate = [l for l in out.splitlines() if l.startswith("GATE")]
    print("   " + (gate[0] if gate else "no GATE line"))
    check("shuffled labels give GATE FAIL", gate and gate[0].startswith("GATE FAIL"), out)

    # 6
    model = json.loads((tmp / "model.json").read_text()) if (tmp / "model.json").exists() else None
    if model is None:
        check("JS inference matches Python", False, "no model.json from step 4")
    else:
        bf = [load_batch(p) for p in find_csvs([tmp / "poses"])]
        X = features(np.concatenate([b.quat for b in bf]), "dir")[::14][:20]
        mu, sd = np.array(model["mu"]), np.array(model["sd"])
        probs = 1 / (1 + np.exp(-((X - mu) / sd) @ np.array(model["w"]).T - np.array(model["b"])))
        fx = tmp / "fixture.json"
        fx.write_text(json.dumps({"model": model, "dirs": X.tolist(), "probs": probs.tolist()}))
        r = subprocess.run(["node", str(HERE / "verify_touch_js.mjs"), str(fx)], capture_output=True, text=True)
        print(r.stdout.rstrip())
        check("JS inference matches Python", r.returncode == 0, r.stderr)

    print(f"\n{'FAILED: ' + ', '.join(failures) if failures else 'all checks passed'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
