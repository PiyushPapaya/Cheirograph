# Phase 8 data collection plan

How labelled training data gets recorded, named and checked. Nothing has been recorded yet. This is the plan for the first real session.

## Where the data comes from

The dashboard's **Batch Capture** ([`tools/handrig_dashboard.html`](../tools/handrig_dashboard.html)). You hold a letter shape still and press capture. Each rep saves:
- the per-sensor median raw accel/gyro over the still window
- the hand-relative quaternion `conj(q_hand) ⊗ q_finger` for each finger, sign-pinned to `w ≥ 0`

The header comment inside every exported CSV lists the exact columns.

Batch Capture stays locked until the in-browser **Noise Check** has returned GO in the current session, so bad sensors can't sneak into the dataset.

## Where files go

Put exports in `ml/dataset/`. CSVs under `ml/` are gitignored until the dataset is final.

## File names

The dashboard downloads `handrig_batch_<timestamp>.csv`. Rename it to:

```
handrig_batch_<letter>_<session#>_<timestamp>.csv
```

- `<letter>`: the label, uppercase, matching the dashboard (`A`, `B`, `SPACE`).
- `<session#>`: `01`, `02`, `03`. Increase it per sitting, not per export.
- `<timestamp>`: keep the one from the download so names never collide.

Example: `handrig_batch_A_02_1755000000000.csv` is letter A, second session.

If one export holds several labels, name it after the main one and note the mix in DOCUMENTATION.md. `check_dataset.py` reads the session number from the file name.

## Target

30 reps per letter across 3 sessions (10 per session). The dashboard grid turns a letter "done" at 30, and `check_dataset.py` checks the same thing by default. Once a first model trains, add reps for letters that get confused. The stretch goal is 90 per letter (`check_dataset.py --goal-reps 90`). See the open decision in [DECISIONS.md](../DECISIONS.md#open-samples-per-letter).

Re-seat the glove and change hand position between sessions. Variety between sessions matters more than raw volume, because the honest accuracy number is leave-one-session-out.

## Before every session

1. Flash the current firmware, hold the glove flat and still, and confirm the boot diagnostic shows 6/6 `OK`.
2. Connect the dashboard and calibrate with the glove flat and still.
3. Record 60 s still and run Noise Check. It must say GO.

## After every session

1. Rename the exports and move them into `ml/dataset/`.
2. Run `python tools/check_dataset.py ml/dataset/`. Fix or re-record anything it flags. Never hand-edit a sample file.
3. Log the session in DOCUMENTATION.md: letters, reps, anything odd.

## Touch-pose test set

Status: planned (2026-11-07). Nothing is recorded.

Why: the glove has no contact sensing. It measures the orientation of six segments, so "ring finger touches thumb" is never measured, only inferred from the pose. The classifier does not need the 3D fingertips to touch in the dashboard. It needs each pose to give repeatable, distinct readings. These poses test exactly that. Whether touching and nearly touching look different in the data is unverified until this set is recorded.

Prerequisite: the thumb curl fix is confirmed visually on the glove (2026-11-07).

Poses (14), names from `tools/pose_labels.py`. 10 reps each, fully release the hand between reps. 2 sessions, re-seat the glove between sessions. Run Batch Capture after Noise Check says GO. That is 140 reps per session. The dashboard pose list and coverage cells (goal 20) use the same names.

| Group | Poses |
|---|---|
| References | `FLAT`, `FISTOUT` (fist, thumb outside), `FISTIN` (fist, thumb tucked), `THUMBOUT` (thumb out sideways) |
| Thumb touches | `TI`, `TM`, `TR`, `TP` (thumb to index, middle, ring, pinky tip) |
| Combinations | `OKRING` (thumb and index ring, others straight), `ROCK` (thumb on middle and ring, index and pinky straight), `TRSTRAIGHT` (thumb on ring only, others straight), `TRP` (thumb on ring and pinky) |
| Near misses | `NEARTI`, `NEARTR` (thumb about 1 cm away, must read as not touching) |

Files holding several poses are named `handrig_batch_POSES_<session>_<ts>.csv`. Batch Capture and `check_dataset.py` accept these non-letter labels now (synthetic data only, not yet with a real export). Check with `python tools/check_dataset.py ml/dataset/ --goal-reps 20 --goal-sessions 2`.

After recording, in order:
1. Run `train_touch.py` (see [10-touch-detection](../10-touch-detection/PLAN.md)) and `train_baseline.py`, both leave-one-session-out. Read the confusion between poses, especially touch vs near miss.
2. If the 3D view matters, fit finger lengths, thumb base and the joint split, using the touch poses as known constraints. This is the open decision [guided functional calibration](../DECISIONS.md#open-guided-functional-calibration).
3. Only if touch vs near miss matters and the data cannot separate them: add real contact sensing (conductive pads on the fingertips, read by spare XIAO pins). Hardware option, not started. See [real contact sensing vs inferred touch](../DECISIONS.md#open-real-contact-sensing-vs-inferred-touch).
