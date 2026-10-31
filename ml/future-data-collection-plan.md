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
