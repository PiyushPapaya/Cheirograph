#!/usr/bin/env python3
"""check_dataset.py - quality gate for Phase 8 batch-capture CSVs.

Run it on every export before the file goes anywhere near training. It reads
one or more batch CSVs (or folders of them) written by the dashboard's
"Export batch CSV" button and reports two things:

1. Problems that make a row or a file unusable (these fail the exit code):
   - file has no "hand-relative" marker: exported before the 2026-10-06 fix,
     so its quaternions are each sensor against its own zero, not against the
     hand (see DECISIONS.md, 2026-10-06). Recapture, don't convert.
   - header or column count doesn't match the format in batch_io.py
   - NaN / inf anywhere
   - a quaternion that isn't unit length (|q| off by more than 0.01), or one
     with w < 0 (the dashboard pins w >= 0 so q and -q can't both appear)
   - a sensor whose median |accel| isn't near 1 g. The pose is held still, so
     the only acceleration is gravity. Near 0 g means the firmware sent zeros
     for a dropped sensor.
   - a sensor whose six raw medians are bit-identical to the previous rep:
     a live IMU dithers by ~20 LSB, so this means a frozen register (the
     "stuck thumb" gotcha in CLAUDE.md)
   - the same row twice (one export re-saved, or the pre-fix double export)

2. Coverage: reps per letter per session, against the Phase 8 target
   (--goal-reps total per letter, spread over --goal-sessions sessions).
   Missing coverage is a warning, not a failure, unless --strict.

Session numbers come from the file name, so rename exports first:
    handrig_batch_<letter>_<session#>_<timestamp>.csv
(see ml/future-data-collection-plan.md).

Usage:
    python check_dataset.py path/to/exports/
    python check_dataset.py a.csv b.csv --strict

Exit code: 0 = no problems, 1 = problems found (or coverage short with --strict).
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from batch_io import SENSORS, find_csvs, load_batch

QUAT_NORM_TOL = 0.01      # exported at 6 decimals, so a real unit quaternion is far inside this
ACCEL_MIN_G = 0.8         # held-still pose: |a| should be ~1 g. Wider than the
ACCEL_MAX_G = 1.2         # noise-baseline check on purpose, it's a sanity bound
DROPPED_G = 0.05          # firmware sends all-zero for a sensor whose read failed


def check_file(bf, problems, warnings):
    name = bf.path.name

    def bad(msg):
        problems.append(f"{name}: {msg}")

    if not bf.hand_relative:
        bad("no 'hand-relative' marker in the header comment -> pre-2026-10-06 export, "
            "quaternions are NOT hand-relative. Recapture.")
    if not bf.header_ok:
        bad("column header missing or different from the expected batch format")
    for lineno, why in bf.bad_lines:
        bad(f"line {lineno}: {why}")
    if bf.synthetic:
        warnings.append(f"{name}: SYNTHETIC test data, not a glove capture")
    if bf.session == "?":
        warnings.append(f"{name}: not renamed to handrig_batch_<letter>_<session#>_<ts>.csv, "
                        "session unknown")

    n = len(bf.labels)
    if n == 0:
        bad("no data rows")
        return

    letter_in_name = name.split("_")[2].upper() if bf.session != "?" else None
    if letter_in_name and set(bf.labels) != {letter_in_name}:
        warnings.append(f"{name}: file name says {letter_in_name} but rows are labelled "
                        f"{sorted(set(bf.labels))}")

    if not np.all(np.isfinite(bf.raw)) or not np.all(np.isfinite(bf.quat)):
        rows = sorted(set(np.where(~np.isfinite(bf.raw).all(axis=(1, 2))
                                   | ~np.isfinite(bf.quat).all(axis=(1, 2)))[0]))
        bad(f"NaN/inf in rows {rows[:10]}")

    norms = np.linalg.norm(bf.quat, axis=2)                       # (rows, 6)
    for r, s in zip(*np.where(np.abs(norms - 1) > QUAT_NORM_TOL)):
        bad(f"rep {bf.labels[r]}#{bf.reps[r]} {SENSORS[s]}: |q| = {norms[r, s]:.4f}, not unit")
    for r, s in zip(*np.where(bf.quat[:, :, 0] < 0)):
        bad(f"rep {bf.labels[r]}#{bf.reps[r]} {SENSORS[s]}: qw < 0, sign not pinned")

    amag = np.linalg.norm(bf.raw[:, :, :3], axis=2)               # (rows, 6) in g
    for r, s in zip(*np.where((amag < ACCEL_MIN_G) | (amag > ACCEL_MAX_G))):
        what = "dropped (all-zero)" if amag[r, s] < DROPPED_G else f"|a| = {amag[r, s]:.2f} g"
        bad(f"rep {bf.labels[r]}#{bf.reps[r]} {SENSORS[s]}: {what}")

    # Frozen register: all six medians exactly equal to the previous rep's.
    for r in range(1, n):
        same = np.all(bf.raw[r] == bf.raw[r - 1], axis=1)       # (6,) per sensor
        for s in np.where(same)[0]:
            bad(f"rep {bf.labels[r]}#{bf.reps[r]} {SENSORS[s]}: raw values identical to the "
                "previous rep -> stuck sensor")

    seen = defaultdict(list)
    for r in range(n):
        seen[(bf.labels[r], bf.reps[r])].append(r)
    for (lab, rep), rows in seen.items():
        if len(rows) > 1:
            bad(f"rep {lab}#{rep} appears {len(rows)} times")


def coverage_report(files, goal_reps, goal_sessions):
    """Print a letter x session table. Returns the letters short of the goal."""
    counts = defaultdict(lambda: defaultdict(int))     # letter -> session -> reps
    for bf in files:
        for lab in bf.labels:
            counts[lab][bf.session] += 1
    if not counts:
        return []

    sessions = sorted({s for per in counts.values() for s in per})
    print(f"\nCoverage (goal: >= {goal_reps} reps over >= {goal_sessions} sessions per letter)")
    print("letter " + "".join(f"{'s' + s:>6}" for s in sessions) + "  total  status")
    short = []
    for lab in sorted(counts):
        per = counts[lab]
        total = sum(per.values())
        n_sess = sum(1 for s in per if s != "?")
        ok = total >= goal_reps and n_sess >= goal_sessions
        if not ok:
            short.append(lab)
        cells = "".join(f"{per.get(s, 0):>6}" for s in sessions)
        print(f"{lab:<7}{cells}  {total:>5}  {'ok' if ok else 'SHORT'}")

    totals = [sum(per.values()) for per in counts.values()]
    print(f"\n{len(counts)} letters, {sum(totals)} reps. "
          f"Smallest class {min(totals)}, largest {max(totals)} "
          f"(ratio {min(totals) / max(totals):.2f}; aim for > 0.7 so no letter is drowned out)")
    return short


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="batch CSV files and/or folders of them")
    ap.add_argument("--goal-reps", type=int, default=30)
    ap.add_argument("--goal-sessions", type=int, default=3)
    ap.add_argument("--strict", action="store_true",
                    help="also fail if any letter is short of the coverage goal")
    args = ap.parse_args()

    paths = find_csvs(args.paths)
    if not paths:
        print("no .csv files found")
        sys.exit(1)

    problems, warnings, files = [], [], []
    for p in paths:
        bf = load_batch(p)
        check_file(bf, problems, warnings)
        files.append(bf)

    # Same row in two files = an export that was saved twice. Compare the numbers,
    # not the label/rep, since rep numbers legitimately restart in a new browser.
    first_seen = {}
    for bf in files:
        for r in range(len(bf.labels)):
            key = (bf.raw[r].tobytes(), bf.quat[r].tobytes())
            where = f"{bf.path.name} rep {bf.labels[r]}#{bf.reps[r]}"
            if key in first_seen:
                problems.append(f"{where}: exact duplicate of {first_seen[key]}")
            else:
                first_seen[key] = where

    print(f"Checked {len(files)} file(s), {sum(len(bf.labels) for bf in files)} rows.")
    for w in warnings:
        print(f"  warn: {w}")
    for p in problems:
        print(f"  FAIL: {p}")
    if not problems:
        print("  no problems found")

    short = coverage_report(files, args.goal_reps, args.goal_sessions)

    failed = bool(problems) or (args.strict and bool(short))
    print("\nRESULT:", "FAIL" if failed else "PASS")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
