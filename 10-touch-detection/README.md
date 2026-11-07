# 10 Touch detection

**What this stage proves (or tries to):** whether the six IMUs can tell which fingers touch the thumb, for example thumb and index forming a ring. The glove has no contact sensor, so touch is inferred from the pose. Status: built and checked on synthetic data, a simulated page and a replay of one real calibration export (2026-11-07). **The current capture (17 steps) has not run on the glove.**

Full plan: [PLAN.md](PLAN.md).

## What is here

- Dataset path: `tools/pose_labels.py` (14 poses, touch sets), pose list and coverage in the dashboard, `tools/train_touch.py` (one logistic regression per pair, leave-one-session-out, GATE PASS or FAIL), model loading in the dashboard.
- Live path: **Guided calibration** in the dashboard. It records touch templates for this session and the GESTURE readout matches the live pose against them. The 3D model draws the touch (display-only correction) using a learned thumb base movement and a finger roll taken from the fist hold. The old hand fit was removed.
- Checking: the **04 Touch** section (top of the right column: live bar per thumb-finger pair, status, coach notes, coverage grid), **Self-test**, and **Export calibration**.

## Run guided calibration

1. Connect the dashboard and calibrate as usual (flat, still).
2. Press **Guided calibration**.
3. Keep still for 20 s.
4. Seventeen steps follow, 10 s holds: hand turn (mount check), fist, spread, then each finger to the thumb as a ring and as straight as you can make both digits, near misses (about 1 cm apart), the rock pose, and a final flat check. The last 7 s of each hold are used and a spread of 0.1 or less decides. There is no stillness gate. About 4.6 minutes in total.
5. Afterwards touch the thumb to a finger. The GESTURE readout names the pair and the 3D model draws the touch. The live bars show all four pairs as distance / limit, for example `TI 0.18/0.30`. Report these for touch and non-touch poses so the radius can be tuned.
6. Press **Self-test**. It asks for 5 touches and scores what the detector says (pass at 70 %). The coach names weak or missed holds, the replay result and a drift warning over 15 deg.
7. Press **Export calibration** to download JSON (version 2): holds with rows and q, templates, replay, flat check, finger rolls, thumb anchors and the self-test. Analyse it offline.

After each run a replay check feeds the holds back through the detector. The learned thumb movement stores, per touch hold, the thumb base offset that puts the tip on the fingertip, and blends the offsets live.

Rerun it if detection gets worse (sideways drift ages the templates). Templates are lost on disconnect.

## Checks

```bash
python tools/verify_touch_model.py
node tools/verify_touch_js.mjs
node tools/verify_guided_touch.mjs
node tools/verify_thumb_rig.mjs
node tools/verify_hand_fit.mjs
node tools/verify_real_calibration.mjs
python tools/verify_check_dataset.py
```

`verify_hand_fit.mjs` covers kinematics, finger roll, thumb warp and contact. `verify_real_calibration.mjs` replays `calibration_2026-11-07.json` (the first real export). All exit 0 as of 2026-11-07. The three dashboard copies must match (`md5sum`).

## Evidence

- `calibration_2026-11-07.json`: first real export (old 15-step capture).
- `calibration_2026-11-07_v3.json` (3.8 MB, mirrored in `Data/csv/`): first real version 3 session, guided calibration then Self-test. 16 of 16 holds kept, Self-test 0 % on all four touches.
- `report_2026-11-07_v3.txt`: the offline analysis of that file.
- `node tools/verify_selftest_replay.mjs` replays the v3 session through the page code and checks the drawn thumb gaps.

## Known limits

- It detects "this pose matches your touch pose", not contact. Touching and a 1 cm near miss may look alike (unverified).
- On synthetic data the trained detector failed the gate once session offsets exceeded the near-miss gap. Not a glove result.
- Straight touches can sit close to a flat hand and be weak.
- Auto re-zero can erase a straight touch held on a flat hand after about 1 s, outside the guided run.
- Guided holds are in the JSON export, not in the Batch Capture dataset. Batch Capture is the dataset path.
- The joint shares (q^0.5, q, q^1.35) are guesses. The learned thumb movement is interpolation between the holds of one session. Its small tip gaps (0.11 learned, 0.009 drawn, against 1.84 default) are partly by construction, because the offsets came from the same holds.
- The first real export: 13 of 15 holds kept (NEARTM, NEARTP missed), ring and straight nearly one pose (distance 0.25 to 0.33), SPREAD read about 25 deg bent (cause unknown, unverified), Self-test not run.
- Self-test ran once on the glove (2026-11-07): all four touches 0 %, flat hand 100 %. Repeat touches land about as far from their holds as the near-miss holds do. See the v3 report.
- Model file loading through the file picker and the saved-model restore were not exercised.
