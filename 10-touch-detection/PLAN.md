# Touch detection: implementation plan

**Goal:** record which fingers touch the thumb as dataset labels, train a small detector on them, and show live which fingers are touching (for example thumb and index forming a ring).

**Approach:** the glove has no contact sensor, so touch is learned from pose. The pose label already in the CSV decides the touch labels through one lookup table, so the CSV format does not change. One small logistic regression per thumb-finger pair runs on the existing `dir` features. The exported model runs in the dashboard.

**Tools:** Python 3 with numpy only, dashboard JS, Node for JS checks.

**Status:** code is testable now on synthetic data. Whether it works on the glove is unknown until real data exists (see Gate).

## Rules

- Display and tooling only: firmware, frame format, CSV format, `S[].rel` and the thumb rig stay as they are.
- Edit `tools/handrig_dashboard.html`, then copy to `08-ble-wireless-dashboard/handrig_dashboard.html` and `Data/html/08-ble-wireless-dashboard__handrig_dashboard.html`. Compare with `md5sum`.
- Comment the non-obvious math. Write a failing check before each feature.

## Files

| File | Change |
|---|---|
| `tools/pose_labels.py` | New. The only Python source of pose names and touch sets |
| `tools/check_dataset.py` | Accept mixed-label `POSES` files |
| `tools/make_synthetic_batch.py` | Add `--poses` |
| `tools/train_touch.py` | New. Train, evaluate, export the model |
| `tools/handrig_dashboard.html` | Pose picker and coverage, model loading, live touch readout |
| `tools/verify_touch_model.py` | New. End-to-end Python checks |
| `tools/verify_touch_js.mjs` | New. JS inference must match Python |
| `tools/verify_hand_fit.mjs` | New (second pass). Hand fit, solver and contact correction on a second parameter set |

## Task 1: pose table

`tools/pose_labels.py`:

```python
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
```

Names stay at 12 characters or fewer, because the dashboard's label field is limited to 12. An export holding all poses is named `handrig_batch_POSES_<session>_<ts>.csv`, which `_NAME_RE` in `batch_io.py` already accepts.

## Task 2: dataset checker

`check_dataset.py` near line 79 complains when a file's labels differ from the name in its file name. Skip that check when the name is `POSES`. Change nothing else.

## Task 3: synthetic poses

Add `--poses` to `make_synthetic_batch.py`. It writes one `handrig_batch_POSES_<sess>_<ts>.csv` per session, with `--reps` reps of every label in `POSES`, through the existing `make_rep` path and with the `# SYNTHETIC` marker. Give each pose its own curl and spread values. A near-miss pose uses its touching pose's values with the thumb offset by about 12 degrees, so it is close but separable. Existing letter output must not change for the same seed.

## Task 4: trainer

`tools/train_touch.py`, usage `python train_touch.py <paths> [--out touch_model.json]`.

- Load with `batch_io`. Build `X = features(quat, "dir")` from `train_baseline`, which is 15 numbers in the order thumb to pinky, x y z each.
- Skip rows where `touch_vector` is `None` and print how many were skipped.
- Exit with a clear message if there are fewer than 2 named sessions.
- Per pair, fit logistic regression in numpy: standardise with training statistics only, full-batch gradient descent, L2 penalty, weight the classes by inverse frequency, fixed seed.
- Evaluate leave-one-session-out. Print per pair: precision, recall, and the false-alarm rate on the `NEAR_MISS` rows.
- Print `GATE PASS` only if every pair with positive examples has recall >= 0.90 and near-miss false alarms <= 0.10. Otherwise print `GATE FAIL` and the failing pairs.
- Print the synthetic-data note used by `train_baseline.py` when any input is synthetic.
- Train on all rows and write JSON: `{"pairs":[...],"mu":[15],"sd":[15],"w":[[15]x4],"b":[4],"synthetic":bool,"reps":n}`.

## Task 5: dashboard labelling

- Add `POSE_LABELS`, the keys of `POSES` in the same order, and a `<datalist>` on `#batchLabel`.
- Add pose cells to the coverage grid after A to Z, with a goal of 20 reps (2 sessions of 10). Letters keep their goal of 30.
- Check at 1400 px wide and at phone width that the grid doesn't overflow.

## Task 6: live detector

Add a section between `// ===== touch detection =====` and `// ===== end touch detection =====`, holding pure functions with no DOM:

```js
// dirs: 15 numbers, each finger's +Z axis rotated by its hand-relative quaternion.
function touchProbs(model,dirs){
  return model.w.map((w,i)=>{
    let z=model.b[i];
    for(let k=0;k<dirs.length;k++)z+=w[k]*(dirs[k]-model.mu[k])/model.sd[k];
    return 1/(1+Math.exp(-z));
  });
}
// Hysteresis, so a pair near the threshold doesn't flicker: on at 0.6, off at 0.4.
function touchState(prev,probs){return probs.map((p,i)=>prev[i]?p>0.4:p>0.6);}
```

- `dirs` comes from `handRelQuat(id)` for ids 1 to 5, using the same formula as `finger_direction` in `train_baseline.py`.
- Add a "load touch model" file input in the Display row. Validate the JSON shape and show an error status on bad input. Keep the model in `localStorage` inside try/catch.
- With a model loaded, the GESTURE readout lists the touching pairs, for example `thumb·index`, and `—` for none. Add `· synthetic` when the model is synthetic. Without a model it behaves exactly as it does today.
- Treat any bad or stale sensor as no touch.

## Task 7: checks

`tools/verify_touch_model.py` exits non-zero on failure and uses a temp folder:

1. Every `POSES` name is 12 characters or fewer, and every touch entry is in `PAIRS`.
2. `POSE_LABELS` in the dashboard equals the keys of `POSES`, in the same order.
3. `--poses` output passes `check_dataset.py`. `make_synthetic_batch.py` letter output is unchanged for a fixed seed.
4. Training on 2 clean synthetic sessions prints `GATE PASS`. Changed after the first run: that run printed `GATE FAIL`, and the gate was kept. The check now has both sides: clean data must pass, and data whose session offsets are bigger than the near-miss gap (`--curl-offset-sd`, `--near-deg`) must print `GATE FAIL`.
5. Leak check: the same data with labels shuffled per row must print `GATE FAIL`.
6. Fixture: write the model, 20 feature rows and Python's probabilities to JSON, then run `node tools/verify_touch_js.mjs <fixture>`.

`tools/verify_touch_js.mjs` extracts the touch section from the dashboard and checks that `touchProbs` matches Python within 1e-9. It also checks that `touchState` holds at 0.5 when already on, stays off at 0.5 when already off, and turns on at 0.61.

## Acceptance

```bash
python tools/verify_touch_model.py
node tools/verify_thumb_rig.mjs
node tools/verify_hand_fit.mjs
node tools/verify_batch_gate_js.mjs
node tools/verify_batch_persist_js.mjs
node tools/verify_noise_baseline_js.mjs
python tools/verify_check_dataset.py
md5sum tools/handrig_dashboard.html 08-ble-wireless-dashboard/handrig_dashboard.html Data/html/08-ble-wireless-dashboard__handrig_dashboard.html
```

All must exit 0, and all three hashes must match.

## Guided calibration (added later, live path)

Not in the first plan. Reason: on synthetic data the trained detector fails when sessions carry offsets bigger than the near-miss gap (recall / near-miss false alarm, leave-one-session-out, linear model: no offset 1.00 / 0.00; curl offset sd 6 deg and 12 deg near miss, TI 0.90 / 0.28, TR 0.76 / 0.25; plus 10 deg yaw drift, TI 0.95 / 0.53). Synthetic, so a warning only. A template recorded in the same session shares the offset, so the live detector uses templates.

- Button "Guided calibration": 20 s still, then 8 stages (index, middle, ring, pinky, each as a ring and as straight as possible). Each stage has 5 s to get into position and a 10 s hold. About 140 s in total.
- Samples are kept only while the hand, thumb and that finger are still. A hold needs 30 samples and a spread of 0.2 or less. Otherwise it repeats, up to 3 tries, then it is reported as missed.
- Each hold becomes a template of this session. A pair touches when the thumb and that finger are near one of its templates. Only those two digits count, so several pairs can be on at once.
- Radius = max(0.3, 3 x spread), capped at half the distance to the flat hand. Templates under 0.15 are reported as too close to flat. Leaving a touch takes 1.3 x radius, and only when no other touch matches.
- GESTURE readout order: session templates, loaded model, old thumb-index rule. `touchStatus` shows the nearest template, its distance and its limit.
- Auto re-zero is blocked during the guided run. Templates are cleared on disconnect and live in memory only.
- Checks: `tools/verify_guided_touch.mjs`, plus a run of the real page with simulated sensors and simulated time (8 of 8 stages, retry on a moving hold, correct live readout).
- Fixed on the way: going from an index touch to a straight middle touch showed both pairs because hysteresis kept the old one.
- Not done: guided holds are not saved to the dataset, and nothing was tried on the glove. The 0.3 radius is a guess.

## Second pass: draw the touch, fit the hand, check it (2026-11-07, later)

Reason: on the glove the model did not show touches, and I could not check recognition. Everything below is in the dashboard and tested in simulation only.

Steps now (20 s still plus 16 steps of about 15 s, about 4.5 minutes): hand turn, fist, spread, then for index, middle, ring and pinky a ring and a straight hold, near misses, and the rock pose (a two-pair template needs all its digits).

Buttons: **Guided calibration**, **Self-test**, **Export calibration**.
- Self-test: 5 prompts, pass at 70 %. Run it after guided calibration.
- Live meter: all four pairs as distance / limit, for example `TI 0.18/0.30`. A pair touches when the distance is under the limit.
- Coach: plain rules that name weak or missed holds and the fit status. It no longer says "learned cleanly" above a rejected fit.
- Export calibration: JSON with holds (with rows), templates, fit and self-test. Use it to tune joint shares and radii offline.

Changes:
- Radius is capped at half the distance to the nearest non-touch pose (near miss, fist, spread). A pair's tightest radius applies to all its poses.
- `fitHand` fits thumb base, thumb length and 4 finger scales from the holds (bounds +-0.5, 2.2 to 3.1, 0.85 to 1.2). Rejected when the mean gap stays over 0.35.
- Fingers have 3 segments (0.45 / 0.30 / 0.25), joint shares q^0.5, q, q^1.35 (guesses). Thumb len 2.6, z -1.1.
- Contact correction: touching digits turn toward the point between the tips, 8 passes, 40 deg cap per digit, display only.
- Auto re-zero is blocked while a touch is detected.

Checks: `tools/verify_hand_fit.mjs` (7 of 8 holds real, 2 deg noise: gap 0.46 to 0.03, with contact 0.001), plus a run of the real page with simulated sensors and time (16 stages, scene vs maths 0.0000, self-test passed). All verify scripts exit 0.

Not done: nothing tried on the glove. Guided holds are not in the Batch Capture dataset. The thumb-index gesture rule was not retuned. Model loading through the real file picker was not exercised.

Next on the glove: guided calibration, Self-test, Export calibration, analyse the JSON, tune joint shares and radii, record the pose set.

## Third pass: first real calibration (2026-11-07, later)

Reason: the first guided run on the glove "did not work out well", and the coverage grid covered the thumb in the 3D view. Real data: `calibration_2026-11-07.json` (mirror in `Data/csv/`). 13 of 15 holds kept, 35 to 82 of about 100 samples per hold at a spread of only 0.007 to 0.017, so the stillness gate was too strict. Replay detection was right (touches 100 %, non-touches 0 %). The hand fit was rejected (gap 0.83) and no rigid length fit can work (best 0.51). The thumb sensor turned only 29 to 45 deg per touch. Fist rolls were 11, 27, 29, 34 deg, matching the T5 gyro fit.

Steps now: 20 s still, then 17 steps of 10 s holds: hand turn, fist, spread, ring and straight for index, middle, ring and pinky, near misses, rock, and a final FLATCHECK. About 4.6 minutes. Buttons: **Guided calibration**, **Self-test**, **Export calibration** (version 2).

The five items:
1. New section "04 Touch" at the top of the right column, with live bars (distance / limit per pair), status, coach notes and the coverage grid. The grid no longer overlays the 3D view. Checked at 1400 px and 375 px.
2. No stillness gate. Last 7 s of each hold, spread <= 0.1 decides. FLATCHECK added.
3. Finger roll from the fist hold (`rollFromFist`, `unrollQs`), display only.
4. `fitHand`, `solveN` and the saved hand deleted. Learned thumb base movement instead: per touch hold, the thumb base offset that puts the tip on the fingertip. Live blend with a Gaussian weight on whole-hand similarity (sigma 0.18). Non-touch poses anchor at zero, near misses use their pair's ring offset.
5. Replay check after each run (reported by the coach), drift warning over 15 deg, export version 2 (q for all holds, replay, flat check, rolls, anchors).

Checks: `tools/verify_real_calibration.mjs`. Held-out rows 13 of 13 holds correct. Mean tip gap 1.84 default, 0.11 learned, 0.009 drawn. The real page fed the real holds: 17 steps, 9 touches learned, replay 16 of 16, drawn gaps 0.000 to 0.026 (NEARTM, NEARTP and the flat check were synthesised). All verify scripts exit 0.

Limits: one session replayed, gaps small partly by construction, poses between holds unmeasured, the new capture and live drawing not run on the glove, Self-test never run, touch inferred, guided holds not in the Batch Capture dataset.

Next: rerun guided calibration on the glove, run Self-test, export, compare with the first file (kept holds, SPREAD reading, flat check, rolls, replay). Then record the pose set.

## Black box and audit

One run now records everything needed to find what is still wrong. Export calibration saves a version 3 JSON: raw frames of all six sensors (cap 20000, about 6.7 min at 50 Hz), event log (cap 3000), stage marks, session facts, holds, results and the self-test. It also works after a stopped or disconnected run. A 5 minute run is about 3.5 MB.

Steps (nothing here has run on the glove yet, unverified):
1. Hard-reload the dashboard (version string "touch-calibration v3 · black box · 2026-11-07").
2. Connect, run Guided calibration, run Self-test.
3. Export calibration.
4. `python tools/analyze_touch_calibration.py <file>`. It flags frozen sensors (50 or more identical frames) and pinned gyro axes (240 deg/s or more for 5 or more samples).
5. Compare with the first export: kept holds, SPREAD reading, flat check, rolls, replay.
6. Then record the pose set.

Test without a glove: `node tools/verify_blackbox.mjs`.

## First real v3 session (2026-11-07)

Result: guided calibration worked, live detection did not. 16 of 16 holds kept, replay 100 % on every hold, 0 retries, 15609 frames with 0 lost and 0 bad. Self-test: all four touches 0 %, flat hand 100 %.

Cause (from replaying the raw frames through the page code, which reproduces all 16 holds within 0.058 per digit): not a code bug. A repeat touch lands about as far from its guided hold as the near-miss hold does. Distance vs radius: TI 0.33/0.156, TM 0.47/0.179, TR 0.36/0.102, TP 0.25/0.072, so 2.1x to 3.5x the radius. A near miss sits at 2x by construction, so no radius accepts these touches without accepting the near misses. Detection is left as it is. The display was fixed instead (nearest-anchor thumb weights, near-pair contact), see DECISIONS.md.

Next on the glove:
1. Reload, run guided calibration, go straight into Self-test with nothing in between.
2. Use the same firm curled pose as in the guided hold.
3. Watch whether the 3D thumb lands on the right fingertip, especially thumb to middle, and whether a fist snaps the thumb onto a finger.
4. Then decide the open detection question (DECISIONS.md, "Open: separating a touch from a near miss").

## After the code: on the glove

1. Record 2 sessions: Noise Check GO, Batch Capture, 10 reps per pose, taking the glove off and on between sessions. Pick labels from the list. About 25 minutes per session (estimate).
2. Run `python tools/check_dataset.py <folder> --goal-reps 20 --goal-sessions 2`.
3. Run `python tools/train_touch.py <folder> --out touch_model.json`.
4. Load the model in the dashboard and try the poses live.

## Gate

The result in step 3 decides the next move.

- **GATE PASS:** the detector stays. Add letters with their touch sets to `POSES` and continue Phase 8.
- **Fails on near misses only:** poses are recognised, but touch itself is not visible to the IMUs. Decide on fingertip contact pads, see DECISIONS.md. Pads would also label every rep automatically.
- **Fails on real touches too:** read which pairs fail and collect more varied data for those before changing the model.

Out of scope for now: finger-to-finger contact (for example index on middle), fitting the 3D hand to real finger lengths (tried in the second pass, rejected by the real hand, see the third pass), on-device inference, and contact pads.
