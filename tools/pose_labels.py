"""pose_labels.py - the one place that names the touch poses and what each one touches.

A pose label in the batch CSV decides the touch labels through this table, so
the CSV format does not change. The dashboard keeps a copy of the keys as
POSE_LABELS; tools/verify_touch_model.py checks the two stay equal.
"""

PAIRS = ["TI", "TM", "TR", "TP"]   # thumb to index, middle, ring, pinky
POSES = {
    "FLAT": (), "FISTOUT": (), "FISTIN": (), "THUMBOUT": (),
    "TI": ("TI",), "TM": ("TM",), "TR": ("TR",), "TP": ("TP",),
    "OKRING": ("TI",),            # thumb and index form a ring, other fingers straight
    "ROCK": ("TM", "TR"),         # thumb on middle and ring, index and pinky straight
    "TRSTRAIGHT": ("TR",),        # thumb on ring only, other fingers straight
    "TRP": ("TR", "TP"),
    "NEARTI": (), "NEARTR": (),   # thumb about 1 cm away: must read as NOT touching
}
NEAR_MISS = ("NEARTI", "NEARTR")


def touch_vector(label):
    """0/1 per PAIRS entry, or None if the label is not a touch pose."""
    if label not in POSES:
        return None
    return [int(p in POSES[label]) for p in PAIRS]
