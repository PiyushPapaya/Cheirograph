#!/usr/bin/env python3
"""verify_check_dataset.py - prove check_dataset.py catches each fault it claims to.

Generates a small clean synthetic dataset, confirms the checker PASSES it,
then plants one fault at a time in a copy and confirms the checker FAILS with
the expected message. Same idea as the verify_*.mjs scripts for the dashboard.

Usage:
    python verify_check_dataset.py
Exit code 0 = every check passed.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable


def run_checker(folder, *extra):
    r = subprocess.run([PY, str(HERE / "check_dataset.py"), str(folder), *extra],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def edit_first_row(path, fn):
    """Apply fn(list_of_fields) -> list_of_fields to the first data row of a CSV."""
    lines = path.read_text(encoding="utf-8").splitlines()
    i = next(k for k, l in enumerate(lines) if l and not l.startswith("#") and not l.startswith("label"))
    lines[i] = ",".join(fn(lines[i].split(",")))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def col(name):
    from batch_io import EXPECTED_HEADER
    return EXPECTED_HEADER.index(name)


def set_fields(**vals):
    def fn(f):
        for k, v in vals.items():
            f[col(k)] = v
        return f
    return fn


def main():
    sys.path.insert(0, str(HERE))
    results = []

    def check(name, ok, out=""):
        results.append(ok)
        print(f"  [{'ok' if ok else 'FAIL'}] {name}")
        if not ok:
            print("        " + out.replace("\n", "\n        ")[:1500])

    with tempfile.TemporaryDirectory() as tmp:
        clean = Path(tmp) / "clean"
        subprocess.run([PY, str(HERE / "make_synthetic_batch.py"), "--out", str(clean),
                        "--letters", "AB", "--sessions", "3", "--reps", "10"],
                       check=True, capture_output=True)

        code, out = run_checker(clean)
        check("clean data passes", code == 0 and "RESULT: PASS" in out, out)
        code, out = run_checker(clean, "--strict")
        check("--strict passes when every letter has 30 reps over 3 sessions",
              code == 0, out)
        code, out = run_checker(clean, "--strict", "--goal-reps", "40")
        check("--strict fails when a letter is short", code == 1 and "SHORT" in out, out)

        # (description, function that breaks the copied folder, text expected in the output)
        def first_file(d):
            return sorted(d.glob("*.csv"))[0]

        def legacy(d):
            p = first_file(d)
            p.write_text(p.read_text(encoding="utf-8").replace("hand-relative", "own-zero"), encoding="utf-8")

        def duplicate_file(d):
            p = first_file(d)
            shutil.copy(p, d / p.name.replace(".csv", "1.csv"))

        def stuck(d):
            p = first_file(d)
            lines = p.read_text(encoding="utf-8").splitlines()
            rows = [k for k, l in enumerate(lines) if l and not l[0] in "#l"]
            a, b = lines[rows[0]].split(","), lines[rows[1]].split(",")
            s = col("thumb_ax")
            b[s:s + 6] = a[s:s + 6]                     # thumb raw frozen across two reps
            lines[rows[1]] = ",".join(b)
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")

        faults = [
            ("pre-fix export (no hand-relative marker)", legacy, "pre-2026-10-06 export"),
            ("dropped sensor (all-zero accel)",
             lambda d: edit_first_row(first_file(d), set_fields(ring_ax="0", ring_ay="0", ring_az="0")),
             "ring: dropped"),
            ("accel far from 1 g",
             lambda d: edit_first_row(first_file(d), set_fields(index_ax="1.5")), "index: |a| ="),
            ("non-unit quaternion",
             lambda d: edit_first_row(first_file(d), set_fields(middle_qw="0.5", middle_qx="0.5",
                                                                middle_qy="0", middle_qz="0")),
             "not unit"),
            ("unpinned sign (qw < 0)",
             lambda d: edit_first_row(first_file(d), set_fields(pinky_qw="-1", pinky_qx="0",
                                                                pinky_qy="0", pinky_qz="0")),
             "qw < 0"),
            ("NaN", lambda d: edit_first_row(first_file(d), set_fields(hand_gx="nan")), "NaN/inf"),
            ("short row", lambda d: edit_first_row(first_file(d), lambda f: f[:-3]), "columns, expected"),
            ("stuck sensor", stuck, "thumb: raw values identical"),
            ("same export saved twice", duplicate_file, "exact duplicate"),
        ]
        for name, breaker, expect in faults:
            broken = Path(tmp) / "broken"
            if broken.exists():
                shutil.rmtree(broken)
            shutil.copytree(clean, broken)
            breaker(broken)
            code, out = run_checker(broken)
            check(f"catches {name}", code == 1 and expect in out, out)

        # unrenamed file: warning only, still passes
        unnamed = Path(tmp) / "unnamed"
        unnamed.mkdir()
        shutil.copy(first_file(clean), unnamed / "handrig_batch_1760000000000.csv")
        code, out = run_checker(unnamed)
        check("un-renamed file warns but passes", code == 0 and "session unknown" in out, out)

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
