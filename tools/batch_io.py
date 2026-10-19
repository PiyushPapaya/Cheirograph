"""batch_io.py - load the dashboard's batch-capture CSV (Phase 8 training data).

Shared by check_dataset.py and train_baseline.py so both read the file the
same way. Not a script on its own.

File format (written by exportBatchCSV() in tools/handrig_dashboard.html):

    # batch-captured static-pose samples. raw = median over ...
    # q* = hand-relative orientation conj(q_hand)*q_finger ...
    label,rep,t_ms,hand_ax,...,pinky_gz,hand_qw,...,pinky_qz

    3 id columns, then 6 sensors x 6 raw values (accel in g, gyro in deg/s,
    raw sensor frame), then 6 sensors x 4 quaternion values (w,x,y,z).

The second comment line says "hand-relative". Exports from before the
2026-10-06 fix wrote each sensor against its own zero instead, which is a
different (and wrong) feature, so the loader records whether that marker is
present and check_dataset.py refuses files without it.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

SENSORS = ["hand", "thumb", "index", "middle", "ring", "pinky"]
FINGERS = SENSORS[1:]
RAW_AXES = ["ax", "ay", "az", "gx", "gy", "gz"]
QUAT = ["qw", "qx", "qy", "qz"]

EXPECTED_HEADER = (["label", "rep", "t_ms"]
                   + [f"{s}_{a}" for s in SENSORS for a in RAW_AXES]
                   + [f"{s}_{q}" for s in SENSORS for q in QUAT])

# handrig_batch_<letter>_<session#>_<timestamp>.csv, the rename convention in
# ml/future-data-collection-plan.md. The bare download name has no session.
_NAME_RE = re.compile(r"handrig_batch_(?P<letter>[A-Za-z]+)_(?P<session>\d+)_(?P<ts>\d+)\.csv$")


@dataclass
class BatchFile:
    path: Path
    session: str                  # "01", "02", ... or "?" if the name doesn't say
    hand_relative: bool           # True if the post-2026-10-06 comment marker is there
    synthetic: bool               # True if written by make_synthetic_batch.py
    header_ok: bool
    labels: list = field(default_factory=list)   # one per row
    reps: list = field(default_factory=list)
    t_ms: list = field(default_factory=list)
    raw: np.ndarray = None        # (rows, 6 sensors, 6 axes)
    quat: np.ndarray = None       # (rows, 6 sensors, 4)
    bad_lines: list = field(default_factory=list)  # (line number, reason)


def session_of(path: Path) -> str:
    m = _NAME_RE.search(path.name)
    return m.group("session") if m else "?"


def load_batch(path) -> BatchFile:
    path = Path(path)
    bf = BatchFile(path=path, session=session_of(path), hand_relative=False,
                   synthetic=False, header_ok=False)
    raw_rows, quat_rows = [], []
    n_num = len(EXPECTED_HEADER) - 3

    with path.open(encoding="utf-8", errors="replace") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                if "hand-relative" in line:
                    bf.hand_relative = True
                if "SYNTHETIC" in line:
                    bf.synthetic = True
                continue
            parts = line.split(",")
            if parts[0] == "label":
                bf.header_ok = parts == EXPECTED_HEADER
                continue
            if len(parts) != len(EXPECTED_HEADER):
                bf.bad_lines.append((lineno, f"{len(parts)} columns, expected {len(EXPECTED_HEADER)}"))
                continue
            try:
                rep, t = int(parts[1]), int(parts[2])
                nums = [float(x) for x in parts[3:]]
            except ValueError as e:
                bf.bad_lines.append((lineno, f"not a number ({e})"))
                continue
            bf.labels.append(parts[0].strip().upper())
            bf.reps.append(rep)
            bf.t_ms.append(t)
            nums = np.array(nums)
            assert nums.size == n_num
            raw_rows.append(nums[:36].reshape(6, 6))
            quat_rows.append(nums[36:].reshape(6, 4))

    bf.raw = np.array(raw_rows).reshape(-1, 6, 6)
    bf.quat = np.array(quat_rows).reshape(-1, 6, 4)
    return bf


def find_csvs(paths):
    """Expand a mix of files and folders into a sorted list of .csv files."""
    out = []
    for p in map(Path, paths):
        if p.is_dir():
            out.extend(sorted(p.glob("*.csv")))
        else:
            out.append(p)
    return out
