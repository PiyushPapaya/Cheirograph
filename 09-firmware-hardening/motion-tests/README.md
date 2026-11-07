# Motion tests (v5 firmware, finger drift)

On v5 the fingers drift and tilt on their own while held straight. Small movements look fine. After a big movement, the fingers don't come back to the rest pose. These tests pin down why before any code changes.

## Suspects

| Suspect | What it predicts | How the CSV shows it |
|---|---|---|
| Gyro clipping at ±500 °/s | Fast moves don't return, slow ones do | Raw gyro sits flat at ±500 during the move |
| Leftover gyro bias | Slow drift while still, even right after calibration | Gyro mean in the still holds isn't ~0 after bias removal |
| Yaw drift (no magnetometer) | Fingers swing sideways, curl stays fine | Accel tilt at start and end matches, model doesn't |
| Weak accel correction (β) | Pitch/roll come back, but slowly | Model recovers over seconds, not instantly |
| Tape wobble | One finger worse than the rest | Noise only on that sensor |

Accel gives tilt directly. If the accel tilt at the end matches the start but the model doesn't, the sensor is fine and the fusion is the problem.

## Setup, every session

1. Flash v5, glove flat, check the boot diagnostic shows 6/6 `OK`.
2. Power the glove about 5 minutes before the first calibration, so gyro warm-up drift is mostly over (unverified for these sensors).
3. Connect the dashboard.

## Setup, every test

Calibrate before every test, not once per session. Every test then starts from a fresh gyro bias and zero. See DECISIONS 2026-10-31.

1. Start the phone video and the dashboard screen recording.
2. Press **● Record** in the dashboard. It clears its buffer, so one test is one CSV.
3. Press **Calibrate**, hand flat and still for the full 20 s. Use the same pose and surface as the 5 s flat holds. "Did the fingers return" is measured against this zero.
4. If the dashboard flags a sensor (bad accel, bad gyro bias, noisy), redo the calibration before going on.
5. Clap once (a sharp spike in every sensor). That lines up the video and the CSV, and marks the end of calibration.
6. 5 s flat and still, the movement, 5 s flat and still.
7. Press Stop and save the CSV.

The CSV is raw (no bias correction, no remap, no calibration markers). The calibration hold stays inside the recording so the analysis can recompute the bias and zero the dashboard used.

Every test starts and ends with **5 s flat and still**. The return error is the difference between those two holds.

## Tests

| ID | Movement | Why |
|---|---|---|
| T0 | 60 s flat and still | Baseline drift and bias |
| T1 | Fist and back, **slow** (2 s each way), 3× | Should return if fusion is fine |
| T2 | Fist and back, **fast** (snap), 3× | Clipping test. Compare with T1 |
| T3 | Each finger alone, slow then fast, thumb to pinky | Which finger, and whether it's per sensor |
| T4 | Spread and close, 3× | Sideways axis, yaw |
| T5 | Fingers straight, rotate the whole hand: roll, pitch, turn, 2× each | Fingers should stay still relative to the hand |
| T6 | Mixed fast movement for 20 s, then 60 s flat | Real-use drift and recovery |

Do T1 and T2 first. If T1 returns and T2 doesn't, clipping is confirmed and the rest can wait for the fix.

## File names

```
<ID>_<movement>_<firmware>_<date>.<ext>
T2_fast-fist_v5_2026-10-31.csv
T2_fast-fist_v5_2026-10-31_hand.mp4
T2_fast-fist_v5_2026-10-31_screen.mp4
```

One folder per run, named `<run>_<date>`:

```
motion-tests/
  README.md                  protocol and log (this file)
  before-fix_2026-10-31/     first run, before the fixes: 7 CSVs + hand and screen videos (T0-T6)
  after-fix_2026-10-31/      second run, after the fixes: hand and screen videos only (t0-t7)
  edited_2026-10-31/         trimmed, synced clips of both runs (local only), own README
```

CSVs are committed. Videos stay local (gitignored, too big). Add a line per test to the log below: what you saw, anything odd.

## Log

### First run, before the fixes (`before-fix_2026-10-31/`)

The first run (2026-10-31) was recorded as t1 to t7. They map to the protocol as t1 = T0, t2 = T1, and so on up to t7 = T6. Files are renamed to the protocol IDs.

Deviations from the protocol in that run: the 20 s calibration was done before pressing Record, so only about 3 s of stillness is inside each CSV. No clap. The hand-axes setting was not the same in every test (T0 "fwd +X, up -Z", T2 "fwd +Y, up -Z").

"Clipped" is the number of samples at the ±500 °/s limit, worst finger. "Return error" is gyro integration from the start hold to the end hold compared with the accel-measured up direction (yaw is not included). Two outlier values are the hand IMU and the pinky.

| Test | Date | Firmware | Seen by eye | CSV result |
|---|---|---|---|---|
| T0 still | 2026-10-31 | v5 | Fingers drift while the hand lies still | 16.5 to 20 Hz, 0 clipped, return error 2 to 4 deg all sensors |
| T1 slow fist | 2026-10-31 | v5 | Fingers do not fully come back | ~17 Hz, single clipped samples, hand 7, thumb 4, index 15, middle 24, ring 37, pinky 30 deg |
| T2 fast fist | 2026-10-31 | v5 | Real hand flat at the end. Dashboard shows index pitch 44 deg, yaw -105 deg, middle pitch 58 deg ("bending") | ~17 Hz, 84 to 120 clipped per finger (11 to 15 % of samples), thumb 18, index 127, middle 95, ring 43, pinky 69 deg |
| T3 each finger | 2026-10-31 | v5 | Pinky missing for part of the test, fine at the end | ~17 Hz, middle 29, pinky 25, others 3 to 8 deg |
| T4 spread | 2026-10-31 | v5 | Sideways drift | ~17 Hz, 14 to 25 deg. Hand IMU (never clipped) lost 24 to 35 deg in T4/T6, so the low frame rate hurts on its own |
| T5 hand rotate | 2026-10-31 | v5 | Best of the set | 43 Hz, 10 to 15 deg |
| T6 mixed fast | 2026-10-31 | v5 | Fingers off after the fast phase | ~17 Hz, 13 to 34 clipped per finger, 25 to 35 deg, pinky 78 deg |

### Before and after the fixes

One row per test. The user's names (t1 to t7) are in brackets. Every number is the worst sensor in that test.

- **Rate, clipped, gyro return error:** from `analyze_motion_test.py --clip 500` on the raw CSVs. These describe the data itself, so they can only improve with a new recording.
- **Shown at the end, old dashboard:** finger-vs-hand angle the dashboard displayed in the last 1 s, replayed in a Python port of the old pipeline.
- **Same, replay with fixes:** the same CSV through the fixed pipeline (closed-form calibration, pinky offset, self-healing). Same 17 Hz, ±500 °/s data, so this shows what the dashboard fixes alone can do.
- **Re-run:** the real "after", on the fixed firmware (50 Hz, ±2000 °/s) and dashboard. Empty until the tests are re-recorded.

| Test | Rate | Clipped samples | Gyro return error | Shown at the end, old dashboard | Same, replay with fixes | Re-run (rate / clipped / return error / shown) |
|---|---|---|---|---|---|---|
| T0 still (t1) | 20.2 Hz | 0 | 4.1 deg (hand) | 9.0 deg (index) | 2.5 deg | pending |
| T1 slow fist (t2) | 16.6 Hz | 2 (pinky) | 36.9 deg (ring) | 15.7 deg (ring) | 4.9 deg, still sliding when the CSV ended | pending |
| T2 fast fist (t3) | 16.5 Hz | 120 (middle), 84 to 120 per finger | 126.9 deg (index) | 162.0 deg (pinky) | unchanged, hand never still 1 s at the end | pending |
| T3 each finger (t4) | 16.7 Hz | 0 | 29.3 deg (middle) | 14.5 deg (pinky) | 0.8 deg | pending |
| T4 spread (t5) | 16.7 Hz | 1 | 25.3 deg (ring), hand 24.3 | 53.7 deg (thumb) | 13.9 deg (thumb, spread erased by re-zero) | pending |
| T5 hand rotate (t6) | 43.3 Hz | 0 | 14.6 deg (hand) | 5.5 deg (middle) | 0.4 deg | pending |
| T6 mixed fast (t7) | 16.7 Hz | 34 (pinky) | 77.7 deg (pinky) | 93.7 deg (pinky) | 0.5 deg | pending |

Pinky |a| while still was 0.74 to 0.77 g in every test (the zero-g offset). The other sensors read 0.98 to 1.02 g.

Pass for the re-run: about 50 Hz, 0 clipped samples (at `--clip 2000`), gyro return error under about 5 deg on T1 and T2, shown angle under about 2 deg after the end hold.

Other results from the same run: no all-zero frames (no bus dropouts) and no accel clipping in any test. The dashboard showed RATE 15 to 17 Hz with LOSS 0.0 % and 0 bad frames, which means the firmware sent a frame every 60 ms (median dt exactly 60 ms) and did not drop any. See DOCUMENTATION 2026-10-31.

### Second run, after the fixes (`after-fix_2026-10-31/`, 2026-10-31 afternoon)

I re-ran the motion tests on the fixed system: v5 firmware with ±2000 °/s gyro and the BLE link requests, plus the self-healing dashboard. I recorded a real-hand video and a dashboard screen recording for each test. These are the "after" videos for the comparison with the first run. Videos are in `after-fix_2026-10-31/` (local only, gitignored like the first run, about 286 MB).

| File | Real hand video | Dashboard screen recording |
|---|---|---|
| t0 | none | `t0_v5-fixed_2026-10-31_screen.mp4` |
| t1 | `t1_v5-fixed_2026-10-31_hand.mp4` | `t1_v5-fixed_2026-10-31_screen.mp4` |
| t2 | `t2_v5-fixed_2026-10-31_hand.mp4` | `t2_v5-fixed_2026-10-31_screen.mp4` |
| t3 | `t3_v5-fixed_2026-10-31_hand.mp4` | `t3_v5-fixed_2026-10-31_screen.mp4` |
| t4 | `t4_v5-fixed_2026-10-31_hand.mp4` | `t4_v5-fixed_2026-10-31_screen.mp4` |
| t5 | `t5_v5-fixed_2026-10-31_hand.mp4` | `t5_v5-fixed_2026-10-31_screen.mp4` |
| t6 | `t6_v5-fixed_2026-10-31_hand.mp4` | `t6_v5-fixed_2026-10-31_screen.mp4` |
| t7 | none | `t7_v5-fixed_2026-10-31_screen.mp4` |

Original names were `tN_realfixed.mp4` (hand) and `tN_fixed.mp4` (screen). They are kept as tN, not renamed to protocol IDs. There are eight screen recordings (t0 to t7) and six hand videos (t1 to t6). Mapping: screen recording tN = test TN (t0 still, t1 slow fist, t2 fast fist, t3 each finger, t4 spread, t5 hand rotate, t6 mixed fast), and hand video tN = TN (t1 to t6). In the first run, t1 to t7 meant T0 to T6, so do not mix the two.

One exception, found by matching poses on video (not with data): the hand video t6 matches screen recording t7 (offset -0.6 s), not t6. With t6 the model ends curled while the real hand is flat. With t7 both end flat. So t7 is the dashboard recording of the T6 hand video, and screen t6 is another T6 attempt without a hand video.

Recorded between about 17:23 and 17:30 (screen recordings). That is before the last two dashboard changes the same day: the live mount-angle learner and the tilt correction with the hand-axes picker removed. So these videos show the fixed firmware plus the earlier dashboard fixes (calibration settle, pinky offset, self-healing, fwd +X and left model defaults), not the final dashboard. (Order inferred from file times, unverified.)

No dashboard CSVs were saved with this run, so the "Re-run" column in the table above stays without numbers. The comparison is visual only. For numbers, record the CSV (● Record before Calibrate) and run `analyze_motion_test.py`.

#### Edited videos

`edited_2026-10-31/` (local only, mp4 is gitignored, about 1.1 GB) holds trimmed, frame-synced versions of both runs. Its own `README.md` lists every file with trims, sync offsets, rotations and crops.

- `clips/`: per test and run, a 1080x1080 real-glove clip and a 1080x1080 dashboard 3D-model clip. Calibration countdowns, black and blurry frames, a browser context menu (T5 before) and long idle ends are cut. A short still hold stays at the end of each test, to show whether the model returns to the rest pose. Hand videos are rotated so the fingers point up.
- `sync/`: side-by-side glove | dashboard per test (T0 to T6 before, T1 to T6 after).
- `picks/`: before-vs-after comparisons for T2 fast fist, T4 spread and T6 mixed fast (9:16 and 4:5 videos plus an end-frame PNG).
- Sync came from cross-correlating motion energy in the glove video and the dashboard 3D view, then checking distinct poses by eye.

What the videos show (visual only, nothing re-measured): T2 before, the real hand ends open and flat while the model ends with fingers splayed in different directions. T2 after, the model ends flat. T6 before ends with the model's fingers crossed while the hand is flat. T6 after ends flat. T4 before droops, after is flat. T1 before is a weak comparison, because the hand ends clenched. The after-run hand videos t3 to t6 are blurry and the glove fills the frame. The after-run recordings predate the mount-angle learner and the tilt fix, so they do not show the final dashboard.

## Thumb re-test (2026-11-07, not run yet)

On the current dashboard (thumb anchored under the palm, sensor rotation split over base and tip joint with `THUMB_BASE_FRAC` 0.5). The thumb sensor is on the tip segment. Reload with Ctrl+F5, reconnect, recalibrate. Press Record before Calibrate. Save the CSV, a hand video and a screen recording per test.

- TH1: thumb in and out alone, slow, 5x, hand flat.
- TH2: same, fast, 5x.
- TH3: thumb tucked across the palm and held 5 s, then back, 3x.
- TH4: fist with the thumb outside, 3x.
- TH5: fingers straight, thumb still, rotate the whole hand.
- TH6: bend only the thumb tip, slow, 5x. Does the model's thumb curl, and does it still point sensibly (not straight down)?

Analyse the CSV first: check the tip direction against the video and the joint split (is 0.5 about right, or does the base look over- or under-rotated), check the thumb return error, and decide the re-zero gate (DECISIONS.md, open items). Check the rate first; it needs to be about 50 Hz.

## Analysis commands

```
python tools/analyze_motion_test.py 09-firmware-hardening/motion-tests/before-fix_2026-10-31/T2_fast-fist_v5_2026-10-31.csv --clip 500   # first run (±500 °/s)
python tools/analyze_motion_test.py <csv>               # new captures, default --clip 2000
python tools/fit_accel_offsets.py <csv> [<csv> ...]     # per-sensor accel zero-g offset (sphere fit)
```

`analyze_motion_test.py` prints rate, dropped frames, clipped samples, |a| and the return error. Options `--clip` and `--still` set the clip limit and the still-hold length.

## Lessons

- Press **● Record before Calibrate**. In the first run calibration happened before Record, so the 20 s hold is missing from every CSV and the bias and zero cannot be recomputed.
- Clap at the start. (The hand-axes setting no longer exists. The dashboard measures the XIAO's mount itself, so turn the whole hand for about 2 s after calibrating.)
- Check the frame rate first. A 17 Hz capture is not usable for fusion checks or for ML data.
