# Decisions

Every engineering fork in this project: what the options were, what I picked, and why. Each entry also says what the choice cost, because every option had a downside. Newest first.

For what happened session by session, see [DOCUMENTATION.md](DOCUMENTATION.md). For the roadmap, see [GENERAL_PLAN.md](GENERAL_PLAN.md).

## Index

| Date | Decision | Area |
|---|---|---|
| open | [Thumb-aware ML features](#open-thumb-aware-ml-features) | Data |
| open | [Guided functional calibration](#open-guided-functional-calibration) | Calibration |
| open | [Real contact sensing vs inferred touch](#open-real-contact-sensing-vs-inferred-touch) | Hardware |
| open | [SPREAD reads 25 deg bent](#open-spread-reads-25-deg-bent) | Calibration |
| open | [Calibration posture against mount slip](#open-calibration-posture-against-mount-slip) | Calibration |
| open | [Touch poses as separable classes](#open-touch-poses-as-separable-classes) | Touch detection |
| open | [Gravity-only features enough, and thumb features](#open-gravity-only-features-enough-and-thumb-features) | Data |
| open | [Can UART and HID run at once](#open-can-uart-and-hid-run-at-once) | BLE |
| open | [Watchdog against the bootloader](#open-watchdog-against-the-bootloader) | Firmware |
| open | [Pinky part faulty?](#open-pinky-part-faulty) | Hardware |
| 2026-11-23 | [v5 frames: banner and drop, no guessed scale](#2026-11-23--v5-frames-banner-and-drop-no-guessed-scale) | BLE |
| 2026-11-23 | [Synthetic batches are tagged as model frame](#2026-11-23--synthetic-batches-are-tagged-as-model-frame) | Data |
| 2026-11-20 | [Bias tracking anchored to the still-start gravity](#2026-11-20--bias-tracking-anchored-to-the-still-start-gravity) | Fusion |
| 2026-11-16 | [Alphabet: ASL, one-handed, 24 static letters](#2026-11-16--alphabet-asl-one-handed-24-static-letters) | Data |
| 2026-11-16 | [Between-rep recalibration in Batch Capture is bias-only](#2026-11-16--between-rep-recalibration-in-batch-capture-is-bias-only) | Calibration |
| 2026-11-16 | [Auto re-zero is off while Batch Capture runs](#2026-11-16--auto-re-zero-is-off-while-batch-capture-runs) | Fusion |
| 2026-11-16 | [Batch file metadata: one # meta line](#2026-11-16--batch-file-metadata-one--meta-line) | Data |
| 2026-11-16 | [check_dataset.py subtracts the accel offsets from the meta line](#2026-11-16--check_datasetpy-subtracts-the-accel-offsets-from-the-meta-line) | Data |
| 2026-11-16 | [Calibration posture: palm down, fingers straight, hand in the air](#2026-11-16--calibration-posture-palm-down-fingers-straight-hand-in-the-air) | Calibration |
| 2026-11-16 | [Touch scope: IMU poses only, a near miss counts](#2026-11-16--touch-scope-imu-poses-only-a-near-miss-counts) | Touch detection |
| 2026-11-16 | [Touch detector: fold touch poses into the letter classifier](#2026-11-16--touch-detector-fold-touch-poses-into-the-letter-classifier) | Touch detection |
| 2026-11-16 | [Hardware watchdog: 2 s, started first in setup()](#2026-11-16--hardware-watchdog-2-s-started-first-in-setup) | Firmware |
| 2026-11-16 | [Gyro scale flag in the frame: mask bit 6](#2026-11-16--gyro-scale-flag-in-the-frame-mask-bit-6) | BLE |
| 2026-11-16 | [Firmware version in the BLE name](#2026-11-16--firmware-version-in-the-ble-name) | BLE |
| 2026-11-16 | [New firmware in stage folder 11-firmware-watchdog](#2026-11-16--new-firmware-in-stage-folder-11-firmware-watchdog) | Firmware |
| 2026-11-16 | [No per-finger mount roll correction in the features](#2026-11-16--no-per-finger-mount-roll-correction-in-the-features) | Calibration |
| 2026-11-16 | [Features: drift-free gravity features first](#2026-11-16--features-drift-free-gravity-features-first) | Data |
| 2026-11-16 | [Classifier ladder: kNN, logistic regression, small MLP](#2026-11-16--classifier-ladder-knn-logistic-regression-small-mlp) | Data |
| 2026-11-16 | [Device math: plain C++ with a host golden-file test](#2026-11-16--device-math-plain-c-with-a-host-golden-file-test) | Firmware |
| 2026-11-16 | [Python pins: numpy 2.5.4, matplotlib 3.11.2, pillow 12.0.0, Python 3.12](#2026-11-16--python-pins-numpy-254-matplotlib-3112-pillow-1200-python-312) | Tooling |
| 2026-11-16 | [Samples per letter: 30 over 3 sessions, 50 for confusable groups](#2026-11-16--samples-per-letter-30-over-3-sessions-50-for-confusable-groups) | Data |
| 2026-11-16 | [BLE throughput fallback: closed for this laptop](#2026-11-16--ble-throughput-fallback-closed-for-this-laptop) | BLE |
| 2026-11-16 | [Phase 4 100 Hz: won't fix](#2026-11-16--phase-4-100-hz-wont-fix) | Firmware |
| 2026-11-16 | [Finger-vs-hand formula: keep rel_h^-1 rel_f](#2026-11-16--finger-vs-hand-formula-keep-rel_h-1-rel_f) | Fusion |
| 2026-11-16 | [Curl sign: measure once and write it down](#2026-11-16--curl-sign-measure-once-and-write-it-down) | Calibration |
| 2026-11-16 | [Boot hang covered by the watchdog and a skip marker](#2026-11-16--boot-hang-covered-by-the-watchdog-and-a-skip-marker) | Firmware |
| 2026-11-16 | [Build target: Seeeduino:nrf52:xiaonRF52840Sense, core 1.1.13](#2026-11-16--build-target-seeeduinonrf52xiaonrf52840sense-core-1113) | Tooling |
| 2026-11-08 | [Ring vs straight drawn by a template-guided shape weight](#2026-11-08--ring-vs-straight-drawn-by-a-template-guided-shape-weight) | Display |
| 2026-11-07 | [Thumb display: nearest-anchor weights plus near-pair contact](#2026-11-07--thumb-display-nearest-anchor-weights-plus-near-pair-contact) | Display |
| 2026-11-07 | [Learned thumb base movement](#2026-11-07--learned-thumb-base-movement) | Calibration |
| 2026-11-07 | [Finger roll from the fist hold](#2026-11-07--finger-roll-from-the-fist-hold) | Calibration |
| 2026-11-07 | [Stillness gate removed from guided holds](#2026-11-07--stillness-gate-removed-from-guided-holds) | Calibration |
| 2026-11-07 | [Contact correction as a display-only cap](#2026-11-07--contact-correction-as-a-display-only-cap) | UI |
| 2026-11-07 | [Fitted hand with a rejection rule](#2026-11-07--fitted-hand-with-a-rejection-rule) (superseded) | Calibration |
| 2026-11-07 | [Three finger segments, joint shares guessed](#2026-11-07--three-finger-segments-joint-shares-guessed) | UI |
| 2026-11-07 | [Touch labels derived from the pose name, no new CSV column](#2026-11-07--touch-labels-derived-from-the-pose-name-no-new-csv-column) | Data |
| 2026-11-07 | [Session templates as the live touch detector](#2026-11-07--session-templates-as-the-live-touch-detector) | Fusion |
| 2026-11-07 | [Small committed GIF and mp4 for README video](#2026-11-07--small-committed-gif-and-mp4-for-readme-video) | Docs |
| 2026-11-07 | [Thumb rotation split over base and tip joint](#2026-11-07--thumb-rotation-split-over-base-and-tip-joint) | Fusion |
| 2026-11-07 | [Thumb bend measured as twist about a measured axis](#2026-11-07--thumb-bend-measured-as-twist-about-a-measured-axis) (superseded) | Fusion |
| 2026-11-07 | [Thumb anchored below the palm plane](#2026-11-07--thumb-anchored-below-the-palm-plane) | UI |
| 2026-10-31 | [Hand IMU tilt measured at calibration, hand-axes picker removed](#2026-10-31--hand-imu-tilt-measured-at-calibration-hand-axes-picker-removed) | Calibration |
| 2026-10-31 | [Hand IMU mount angle learned live from the gyros](#2026-10-31--hand-imu-mount-angle-learned-live-from-the-gyros) | Calibration |
| 2026-10-31 | [Hand axes fwd +X, left model, headings aligned at calibration](#2026-10-31--hand-axes-fwd-x-left-model-headings-aligned-at-calibration) | Calibration |
| 2026-10-31 | [Accel offsets learned live, saved per browser](#2026-10-31--accel-offsets-learned-live-saved-per-browser) | Calibration |
| 2026-10-31 | [Accel-magnitude gating rejected for now](#2026-10-31--accel-magnitude-gating-rejected-for-now) | Fusion |
| 2026-10-31 | [Heading drift: automatic re-zero in the calibration pose](#2026-10-31--heading-drift-automatic-re-zero-in-the-calibration-pose) | Fusion |
| 2026-10-31 | [Snap-back: beta scaled by tilt error when still](#2026-10-31--snap-back-beta-scaled-by-tilt-error-when-still) | Fusion |
| 2026-10-31 | [Quality gate rejects reps, no new CSV columns](#2026-10-31--quality-gate-rejects-reps-no-new-csv-columns) | Data |
| 2026-10-31 | [Gyro full scale ±2000 °/s](#2026-10-31--gyro-full-scale-2000-s) | Firmware |
| 2026-10-31 | [Pinky accel offset corrected by a dashboard constant](#2026-10-31--pinky-accel-offset-corrected-by-a-dashboard-constant) | Calibration |
| 2026-10-31 | [Calibration settle in closed form](#2026-10-31--calibration-settle-in-closed-form) | Fusion |
| 2026-10-31 | [Calibrate before every motion test, not once per session](#2026-10-31--calibrate-before-every-motion-test-not-once-per-session) | Calibration |
| 2026-10-06 | [Batch export uses the hand-relative quaternion](#2026-10-06--batch-export-uses-the-hand-relative-quaternion) | Data |
| 2026-10-06 | [Dashboard goes monochrome](#2026-10-06--dashboard-goes-monochrome) | UI |
| 2026-08-08 | [Calibration stillness gate uses deviation, not an absolute threshold](#2026-08-08--calibration-stillness-gate-uses-deviation-not-an-absolute-threshold) | Calibration |
| 2026-08-08 | [Straight thumb segment in the 3D model](#2026-08-08--straight-thumb-segment-in-the-3d-model) | UI |
| 2026-08-07 | [Settle the calibration reference instantly instead of waiting](#2026-08-07--settle-the-calibration-reference-instantly-instead-of-waiting) | Fusion |
| 2026-08-07 | [Widen the BLE link instead of shrinking the data](#2026-08-07--widen-the-ble-link-instead-of-shrinking-the-data) | BLE |
| 2026-08-07 | [Dashboard carries the public name "Gestura"](#2026-08-07--dashboard-carries-the-public-name-gestura) | Naming |
| 2026-07-25 | [Verify every I²C write and watch for frozen sensors at runtime](#2026-07-25--verify-every-i²c-write-and-watch-for-frozen-sensors-at-runtime) | Firmware |
| 2026-07-25 | [Checksum on the BLE frame](#2026-07-25--checksum-on-the-ble-frame) | BLE |
| 2026-07-25 | [Axis remap lives in the dashboard; hand axis picked at runtime](#2026-07-25--axis-remap-lives-in-the-dashboard-hand-axis-picked-at-runtime) | Fusion |
| 2026-07-19 | [Remap sensor axes before fusion](#2026-07-19--remap-sensor-axes-before-fusion) | Fusion |
| 2026-07-19 | [Raw register driver for the clone finger IMUs](#2026-07-19--raw-register-driver-for-the-clone-finger-imus) | Firmware |
| 2026-07-18 | [Tape for finger sensors, velcro for the MCU](#2026-07-18--tape-for-finger-sensors-velcro-for-the-mcu) | Hardware |
| 2026-07-17 | [Fixed +90° plot correction on the bench](#2026-07-17--fixed-90-plot-correction-on-the-bench) | Tooling |
| 2026-07-17 | [Seed the filter from gravity, two-stage β](#2026-07-17--seed-the-filter-from-gravity-two-stage-β) | Fusion |
| 2026-07-17 | [Madgwick over Mahony and complementary](#2026-07-17--madgwick-over-mahony-and-complementary) | Fusion |
| 2026-07-14 | [MPU6050_light over Adafruit_MPU6050](#2026-07-14--mpu6050_light-over-adafruit_mpu6050) | Firmware |
| 2026-07-14 | [Arduino IDE now, PlatformIO later](#2026-07-14--arduino-ide-now-platformio-later) | Tooling |
| 2026-07-14 | [Live with 6-DOF yaw drift](#2026-07-14--live-with-6-dof-yaw-drift) | Fusion |
| pre-build | [PCA9548A mux](#pre-build--pca9548a-mux-over-two-i²c-addresses) | Hardware |
| pre-build | [Fusion on the MCU, not the DMP](#pre-build--fusion-on-the-mcu-not-the-dmp) | Fusion |
| pre-build | [Sensors on the middle phalanx](#pre-build--sensors-on-the-middle-phalanx) | Hardware |
| pre-build | [Onboard IMU as the hand reference](#pre-build--onboard-imu-as-the-hand-reference) | Hardware |
| pre-build | [Left hand](#pre-build--left-hand) | Hardware |

## Entry format

```
### YYYY-MM-DD | Short title

**Options:** A vs. B (vs. C)
**Choice:** what won.
**Why:** the reasoning, including what it costs.
```

---

## Open decisions

### Open: thumb-aware ML features

**Options:** (a) keep the `curl` feature set (d_y only). (b) Use `dir` or `quat` for the thumb. (c) Add a thumb total-rotation feature (`2 acos|w|`, no direction, like the dashboard readout) or a two-axis one. The single measured flex axis was dropped on 2026-11-07.

**Leaning:** (b) or (c), unverified.

**Update 2026-11-16:** the feature-set ablation (see the open item on gravity-only features) decides this too.

**Why it's open:** `curl` is nearly blind to the thumb's motion, which is mostly sideways swing plus some downward bend. `dir` and `quat` carry the thumb's yaw drift, because gravity cannot correct that axis when the hand is flat. Letters that differ mainly by thumb position depend on this. Needs real Phase 8 data from several sessions to compare.

### Open: guided functional calibration

**Options:** (a) keep the current one-step calibration: hold still, flat. It sets gyro bias and the zero pose. (b) Add a guided routine with several movement sets, per finger and multi-finger, to calibrate each sensor and how they relate. This is called functional calibration in motion capture. Steps:
- still on the table (gyro bias, already done)
- flat hand (zero pose)
- several fists (each finger's real bend axis and sign, replaces guessing the curl sign and hand axes)
- spread (the sideways axis)
- six-face placement, done offline (accel scale per sensor, could explain the pinky reading 25 to 28 % low)

**Leaning:** (b), but only after the gyro range is settled and the dashboard tracks bias in the background.

**Why it's open:** it cannot fix gyro clipping, and it cannot stop yaw drift during use. Calibrating against clipped data would bake the error in. The cost is more dashboard UI work, plus a routine of about a minute that has to be done each session. The gain is that axes and signs are measured instead of picked by hand. Unverified until tried.

**Update 2026-11-07, 3D hand fit built:** fitting the 3D hand is now done in simulation (`fitHand`, see [fitted hand](#2026-11-07--fitted-hand-with-a-rejection-rule)). Guided calibration grew to 20 s still plus 16 steps of about 15 s (hand turn, fist, spread, near misses, rock, ring and straight for each finger), about 4.5 minutes. Unverified on the glove. The joint split is still a guess.

**Update 2026-11-07, touch-template stage built:** the guided calibration now has a touch-template stage (20 s still, then 8 holds of 10 s: index, middle, ring, pinky, each as ring and as straight). It does not fit the 3D hand. It only stores each hold as a template of the session, see [session templates](#2026-11-07--session-templates-as-the-live-touch-detector). Fitting finger lengths, thumb base and the joint split from the touch constraints is still open. Not tried on the glove (unverified).

**Update 2026-11-07, first real export and third pass:** the first real guided run (13 of 15 holds kept) rejected the fitted hand (gap 0.83), so fitting finger lengths and thumb base from the touch constraints is dropped, see [learned thumb base movement](#2026-11-07--learned-thumb-base-movement). The guided run now has 17 steps (a final flat check added), about 4.6 minutes, with no stillness gate. Still open: the new capture has not run on the glove, Self-test has never run, and guided holds are not in the Batch Capture dataset.

**Added 2026-11-07, touch-pose constraints:** the touch poses (thumb to each fingertip, see "Touch-pose test set" in [ml/future-data-collection-plan.md](ml/future-data-collection-plan.md)) are known geometric constraints: at that moment the thumb tip and the finger tip are at the same point. They could be used to fit finger lengths, the thumb base position and the base/tip joint split, instead of using generic hand proportions. The 3D model today uses generic proportions. On that model the closest fingertip distance to the thumb base is index 0.68, middle 1.13, ring 1.66 (only at about 130 deg curl) and pinky 2.19 units, against a thumb reach of 1.8 units, so the pinky cannot reach. That is a calculation on model geometry, not glove data. Record the touch poses first, then decide.

### Open: real contact sensing vs inferred touch

**Options:** (a) IMU pose only: touch is inferred from the six segment orientations, as now. (b) Fingertip pads: conductive pads on the fingertips, read by spare XIAO pins.

**Leaning:** (a) until the near-miss data says otherwise.

**Update 2026-11-07:** (a) is now built twice: a trained model per pair and session templates (see the two decisions below). Both detect "this pose matches a touch pose", not contact. Whether touch and a 1 cm near miss separate on the glove is still unverified. The synthetic gate failed when sessions had offsets bigger than the near-miss gap, which is a warning that the answer may be no. Pads stay on the table until real near-miss data is in.

**Why it's open:** the glove never measures contact. Touching and nearly touching (about 1 cm apart) may look identical in the IMU data, but this is unverified until the touch-pose set is recorded and `train_baseline.py` shows how touch and near-miss poses get confused. The classifier mostly needs repeatable, distinct poses, not true contact. Cost of (b): more wires on a glove that already has wire-fatigue risk, new firmware, and a BLE frame change that has to go through the dashboard parser and `check_dataset.py` together. Hardware option, not started.

### Open: SPREAD reads 25 deg bent

**Options:** (a) drift in the hand-relative pose by that point in the run. (b) The finger roll or sensor mount makes sideways spread look like bend. (c) The spread was not really flat or open in that hold.

**Leaning:** none. Cause unknown (unverified).

**Why it's open:** in the first real export (`10-touch-detection/calibration_2026-11-07.json`) SPREAD read about 25 deg bent on all fingers. The new FLATCHECK stage at the end of the guided run repeats a flat hand. If it also reads off, that points at drift (a). If it reads flat, look at (b) and (c). Needs the rerun.

**Update 2026-11-07 (v3 session):** the flat check read 10.7 deg bent, against about 25 for SPREAD in the first export. So some of the 25 is not drift. Cause still unverified.

**Update 2026-11-16:** re-measure after the new calibration posture (palm down, hand in the air) is in use.

### Open: Calibration posture against mount slip

**Options:** (a) Keep the palm-down posture. (b) Move calibration to a different posture.

**Leaning:** (a), pending the test.

**Why it's open:** Does the hand-versus-finger gravity change on returning to the calibration posture come from posture or from the sensors slipping? A pen line across the mount gives the slip offset. Decide after one session. Unverified until then.

### Open: Touch poses as separable classes

**Options:** (a) Touch poses become classes of the letter classifier. (b) Drop the touch idea.

**Leaning:** (a), pending data.

**Why it's open:** The one-session test of the pose-class detector gives the recall and the wrong-pair rate. Unverified until then.

### Open: Gravity-only features enough, and thumb features

**Options:** (a) Gravity-only features. (b) Add heading-based features. (c) Add thumb features.

**Leaning:** (a), pending the ablation.

**Why it's open:** An ablation table with leave-one-session-out scores per feature set decides this and the thumb-aware features item. Needs real data from several sessions.

### Open: Can UART and HID run at once

**Options:** (a) Both services at once. (b) Switch between them.

**Leaning:** None.

**Why it's open:** A spike on the glove shows whether the Nordic UART stream and a HID keyboard can share the radio. Unverified until then.

### Open: Watchdog against the bootloader

**Options:** (a) Keep the 2 s watchdog. (b) Lengthen the timeout to 4 s. (c) Drop the skip marker if the bootloader uses `GPREGRET2`.

**Leaning:** (a), pending the fault tests.

**Why it's open:** Three things to measure on the glove: whether the bootloader can live with a running watchdog after a power cycle, whether a pin reset stops it, and whether any boot step takes more than 1.5 s between feeds. Also whether the reset-loop guard works. Unverified until then.

### Open: Pinky part faulty?

**Options:** (a) Keep the part and correct the offset in software. (b) Replace it with a spare.

**Leaning:** (a).

**Why it's open:** Read the offset registers and compare the offset between sessions. If it moves more than 0.03 g, replace the part. The root cause of the offset is unverified.

---

## Decisions

### 2026-11-23 | v5 frames: banner and drop, no guessed scale

**Options:** (a) Refuse frames without mask bit 6 silently. (b) Assume ±2000 °/s and fuse them anyway. (c) Show a banner, log one black-box event and drop the frames before fusion.

**Choice:** (c). The banner says `firmware v5 detected, flash v6`. The frames still count for RATE.

**Why:** A guessed scale corrupts data without any sign of it. A silent refusal looks like a dead link. The banner says exactly what to do.

**Cost:** v5 firmware can't be used with this dashboard at all. Recorded v5 sessions still replay, because the replay helper sets bit 6.

### 2026-11-23 | Synthetic batches are tagged as model frame

**Options:** (a) Rewrite the synthetic generator to emit sensor-frame accel and run it through the remap. (b) Tag synthetic meta with `rawFrame:"model"` and skip the remap for those files.

**Choice:** (b). Real exports never carry the key.

**Why:** `verify_touch_model.py` pins the synthetic letter rows with a digest. Changing the frame would break that pin for no gain in the classifier tests.

**Cost:** the remap code path is tested only by `verify_features.py`, not end to end on synthetic batches.

### 2026-11-20 | Bias tracking anchored to the still-start gravity

**Options:** (a) Keep the creep gate (0.03 g between two accel averages) and the 1.5 deg/s residual cap as the only guards. (b) Lower both gates. (c) Remember the gravity direction where a still period began, and end the bias clock if gravity moves more than 0.8 deg from it.

**Choice:** (c). The tilt limit is `HEAL_STILL_TILT_DEG`, 0.8. It restarts only the bias clock (`biasS`), not `stillS`, so snap-back and auto re-zero keep their old meaning of still.

**Why:** A slow real tilt passes both old gates. The creep gate only trips above about 4.8 deg/s. The residual cap lets anything under 1.5 deg/s through. So a finger rotating at 1 deg/s was learned as gyro bias: in the replay it moved the bias by 0.93 deg/s in 30 s. Lowering the gates (b) would also reject real stillness on a noisy sensor. Gravity does not lie about tilt, so comparing against where the period began catches any tilt rate, however slow. Turning about the vertical axis still looks like bias to a 6-DOF sensor. That limit stays.

**Cost:** A hand that wanders by more than 0.8 deg never gets bias tracking, and the gyro bias then stays at its calibration value. I first tried 0.5 deg. It broke the replay of the real v3 session (4 of the checks in `verify_selftest_replay.mjs` failed, worst hold error 0.28 against a limit of 0.07), because real held hands wander about 0.7 deg and lost bias tracking. 0.7 still failed 2 checks, 0.8 and 0.9 pass all. At 1.0 deg the 1 deg/s tilt leaks 0.17 deg/s of bias. So 0.8 sits between the two limits with little room either side, and it was tuned on one session (unverified on others). The first 0.8 s of a tilt is still tracked (0.08 deg/s of bias in the test).

### 2026-11-16 | Alphabet: ASL, one-handed, 24 static letters

**Options:** (a) ASL one-handed. (b) Another fingerspelling alphabet. (c) Include the motion letters J and Z.

**Choice:** (a). 24 static letters. J and Z are out because they are motions.

**Why:** They need a path through space, which six IMUs on one hand cannot give. It also keeps the scope rule intact.

**Cost:** Some letters depend on hand attitude (G and H against P and Q), which the features have to carry. Revisit: never, it is the scope rule.

### 2026-11-16 | Between-rep recalibration in Batch Capture is bias-only

**Options:** (a) A full calibration between reps. (b) Bias and noise only. (c) None.

**Choice:** (b). It never touches the filter state, the reference orientation, the accel offsets, the zero pose, the mount or the headings.

**Why:** A full calibration moves the zero to whatever pose is held at that moment, so every later rep would be measured against a different zero. Relying on the user to lay the hand flat each time is fragile.

**Cost:** A clip or a firmware drop now forces a full flat calibration before the next rep. Revisit if heading error on flat reps stays above 10 degrees after 20 reps.

### 2026-11-16 | Auto re-zero is off while Batch Capture runs

**Options:** (a) Leave auto re-zero on. (b) Off while a batch is active.

**Choice:** (b).

**Why:** The dataset must not be rewritten silently halfway through a run. The bias refresh still runs, so drift inside a run is handled that way. This settles the dataset side of the open question about auto re-zero erasing small thumb poses. The live display case is unchanged.

**Cost:** Heading drift inside a run is not healed, only the gyro bias is. Revisit under the same condition as the between-rep recal.

### 2026-11-16 | Batch file metadata: one # meta line

**Options:** (a) New CSV columns. (b) One `# meta {json}` line at the top of each batch CSV. (c) A separate sidecar file.

**Choice:** (b). Raw values stay unchanged. The line holds the dashboard version, device name, accel offsets and bias.

**Why:** Traceability: a file says how it was made, and raw data stays reinterpretable. A sidecar gets separated from its file. Columns would repeat constants on every row.

**Cost:** Every parser has to read the line, and a format change and its parsers change in the same commit. Revisit: never.

### 2026-11-16 | check_dataset.py subtracts the accel offsets from the meta line

**Options:** (a) Correct the pinky offset in the file. (b) Loosen the limit for the pinky. (c) Subtract the per-sensor offsets recorded in the meta line before the magnitude check, and fall back to slot defaults with a warning when the line is missing.

**Choice:** (c). This closes the open item about the batch quality gate and the pinky offset.

**Why:** Raw stays raw, and the offset is known: (0.2572, 0.1864, -0.1609) g, learned on 2026-11-07. Without this the gate could reject every pinky rep.

**Cost:** Old files without a meta line get the defaults. If the offset moves more than 0.03 g between sessions, replace the pinky part.

### 2026-11-16 | Calibration posture: palm down, fingers straight, hand in the air

**Options:** (a) Hand flat on the table. (b) A letter posture. (c) Palm down, fingers straight and together, hand in the air with the elbow resting on the table.

**Choice:** (c). Agreed 2026-11-16.

**Why:** It keeps the hand off the table. A letter posture breaks two assumptions in the code: the hand IMU tilt reading assumes a flat hand, and heading alignment needs the forward axis horizontal (it returns nothing when the fingers point up).

**Cost:** Pending the posture test, which can still move it. Revisit if that test shows the shift is mount slip and not posture.

### 2026-11-16 | Touch scope: IMU poses only, a near miss counts

**Options:** (a) Claim contact. (b) Touch poses inferred from IMU data, where a near miss of about 1 cm counts as a touch.

**Choice:** (b). This closes the open item about separating a touch from a near miss.

**Why:** The measured repeat error is 10 to 27 degrees per digit against a 4 to 10 degree template radius, so contact cannot be told from a close pose.

**Cost:** No contact claim. Revisit if a letter pair that needs contact stays confused after 3 sessions.

### 2026-11-16 | Touch detector: fold touch poses into the letter classifier

**Options:** (a) Keep the separate template matcher. (b) Run one more session testing the pose-class detector, then fold the touch poses into the letter classifier as classes. Retire the matcher from detection, keep it for the 3D drawing.

**Choice:** (b). Agreed 2026-11-16.

**Why:** One classifier is simpler to port and to explain. The poses that matter are letters anyway: F is thumb on index, W is thumb on pinky. Two non-letter touch poses (ASL number 8, thumb on middle, and number 7, thumb on ring) become the SPACE and BACKSPACE classes.

**Cost:** Two extra classes to collect. 7 against W and 8 against F are part of the go/no-go test. If either pair is below the pair threshold, the replacement command pose is picked from the confusion matrix, not guessed now.

### 2026-11-16 | Hardware watchdog: 2 s, started first in setup()

**Options:** (a) Leave a stuck SCL line to hang the glove. (b) nRF52 watchdog, 2 s, started first in `setup()`, fed between boot steps and once per `loop()` tick, with the reset reason reported in bit 7 of the validity mask.

**Choice:** (b). This closes the open watchdog decision.

**Why:** A stuck SCL makes the `Wire` driver wait forever (no timeout in its loops, read in the core source), so no recovery code can run. Only a reset helps.

**Cost:** About 3 s of link loss and a recalibration after a reset. Revisit if a boot step takes more than 1.5 s between feeds (then 4 s), or if the bootloader cannot live with a running watchdog even after a power cycle. Those tests are in the open item on the watchdog and the bootloader.

### 2026-11-16 | Gyro scale flag in the frame: mask bit 6

**Options:** (a) Assume ±2000 deg/s. (b) Mask bit 6 means gyro ±2000 deg/s. When it is clear the dashboard does not fuse, shows the banner "firmware v5 detected, flash v6" and logs it in the black box.

**Choice:** (b).

**Why:** Today a v4 glove (±500 deg/s) would be read 4 times wrong with no warning. A refusal has to be loud, never silent.

**Cost:** One firmware change and one dashboard change in the same commit. Revisit: never.

### 2026-11-16 | Firmware version in the BLE name

**Options:** (a) A version field in the frame. (b) The version in the device name: `HandRig-6IMU-v6`. The dashboard stores `device.name` in the session facts and the batch meta.

**Choice:** (b).

**Why:** The dashboard connects with `acceptAllDevices`, so the name can change freely and the frame stays as it is.

**Cost:** The name must fit the scan response (it does). Revisit: never.

### 2026-11-16 | New firmware in stage folder 11-firmware-watchdog

**Options:** (a) Edit stage 09 in place. (b) A new numbered stage folder for v6.

**Choice:** (b). `09-firmware-hardening/` stays as the v5 record.

**Why:** Milestone folders are never overwritten.

**Cost:** One more folder.

### 2026-11-16 | No per-finger mount roll correction in the features

**Options:** (a) Correct each finger's mount roll in the features. (b) None, the display roll stays.

**Choice:** (b). This closes the open item on per-finger mount correction.

**Why:** A fixed roll is a constant the classifier absorbs. Leave-one-session-out scoring shows whether it is not constant.

**Cost:** None up front. Revisit if leave-one-session-out is more than 10 points under a random split on the `dir` features while the gravity features hold up.

### 2026-11-16 | Features: drift-free gravity features first

**Options:** (a) Quaternion features with headings. (b) A base model on gravity-only features, with heading-based features added only if an ablation earns them.

**Choice:** (b).

**Why:** With 6 DOF there is no heading reference, so heading-based features drift.

**Cost:** The model is blind to rotation about the vertical. The ablation decides. Revisit after it.

### 2026-11-16 | Classifier ladder: kNN, logistic regression, small MLP

**Options:** (a) Edge Impulse straight away. (b) kNN, then logistic regression, then a one-hidden-layer MLP, written by hand. Edge Impulse or TFLite Micro only if the MLP is not enough.

**Choice:** (b).

**Why:** Hand-written models can be explained line by line.

**Cost:** Training code in numpy. Revisit if the MLP fails the go/no-go and a bigger model passes.

### 2026-11-16 | Device math: plain C++ with a host golden-file test

**Options:** (a) Port everything including self-healing. (b) Port fusion and features to plain C++ and check them against the JS on recorded frames in a host test. Self-healing is not ported.

**Choice:** (b).

**Why:** Explainable and testable without the glove.

**Cost:** The device needs a re-zero pose instead of automatic healing. Revisit if heading features are kept and drift on the device.

### 2026-11-16 | Python pins: numpy 2.5.4, matplotlib 3.11.2, pillow 12.0.0, Python 3.12

**Options:** (a) Keep numpy 2.2.6 as in `tools/requirements.txt`. (b) Pin the versions that run and pass today.

**Choice:** (b). This closes the open Python pin item. It leaned to 2.5.3, and the installed version is 2.5.4.

**Why:** It is what runs and passes the checks today.

**Cost:** None. Revisit on the next fresh install.

### 2026-11-16 | Samples per letter: 30 over 3 sessions, 50 for confusable groups

**Options:** (a) 30 per letter over 3 sessions on 3 days. (b) 90 per letter. (c) 30, with 50 for confusable groups.

**Choice:** (c). This closes the open item on samples per letter.

**Why:** Start small, then check leave-one-session-out accuracy.

**Cost:** About 6 extra short sessions. Revisit if leave-one-session-out plateaus.

### 2026-11-16 | BLE throughput fallback: closed for this laptop

**Options:** (a) Keep asking for the faster link. (b) Shrink the frame. (c) Another host. (d) Lower the rate.

**Choice:** (a), closed for this laptop. This closes the open BLE throughput item. The smaller frame stays the written fallback.

**Why:** Measured in the 2026-11-07 session: 50 Hz at the dashboard, firmware spacing 20.0 ms median, 15609 frames, 0 lost, 0 bad. The real MTU is 247 at most (core source), so the larger figure the serial report once printed was the central's offer, not the link.

**Cost:** None. Revisit if another central gives under 45 Hz.

### 2026-11-16 | Phase 4 100 Hz: won't fix

**Options:** (a) Keep chasing 100 Hz on the bench loop. (b) Close it. 50 Hz is the design rate.

**Choice:** (b).

**Why:** Nothing downstream needs 100 Hz.

**Cost:** None. Revisit: never.

### 2026-11-16 | Finger-vs-hand formula: keep rel_h^-1 rel_f

**Options:** (a) Keep `rel_h^-1 * rel_f`. (b) Compare the raw quaternions with the calibration zero offset removed.

**Choice:** (a). This closes the open formula item.

**Why:** No better option was shown on the replays.

**Cost:** None. Revisit if the ablation shows the `dir` features doing worse than expected.

### 2026-11-16 | Curl sign: measure once and write it down

**Options:** (a) Leave it open. (b) Measure it once on the glove and record it here. Display only.

**Choice:** (b).

**Why:** It has been open since August and takes about a minute.

**Cost:** None. Revisit: never.

### 2026-11-16 | Boot hang covered by the watchdog and a skip marker

**Options:** (a) Accept a boot hang until a power cycle. (b) The watchdog runs from the start of `setup()`. Before touching a sensor the firmware writes its id to `GPREGRET2`. After a watchdog reset that sensor is skipped until the next power cycle.

**Choice:** (b). About 30 lines, no hardware.

**Why:** It costs little and turns a dead glove into a missing finger.

**Cost:** Worst case 5 resets (about 25 s) before streaming. A skipped finger stays missing until power-off. Revisit if the bootloader uses `GPREGRET2` (then use `.noinit` RAM).

### 2026-11-16 | Build target: Seeeduino:nrf52:xiaonRF52840Sense, core 1.1.13

**Options:** (a) Another core. (b) FQBN `Seeeduino:nrf52:xiaonRF52840Sense` with the Seeeduino nrf52 core 1.1.13.

**Choice:** (b). Confirmed with `arduino-cli board listall`.

**Why:** It is the core the firmware builds on.

**Cost:** None. Revisit on a core upgrade.

### 2026-11-08 | Ring vs straight drawn by a template-guided shape weight

**Options:** (a) raise the fixed joint shares globally. (b) Display-only shape weight per pair: a logistic on the distance to this session's ring and straight templates picks how much ring shape to draw. (c) Leave as is.

**Choice:** (b). `w = 1/(1+exp((d_ring - d_straight)/SHAPE_TAU))`, `SHAPE_TAU` 0.04, smoothed 0.2 per frame. Ring adds 35 deg (`RING_EXTRA_DEG`) of flatten to the proximal segment and curl to the distal one, and flattens the thumb base. Detection, templates and exports are untouched.

**Why:** with fixed shares, ring and straight looked the same (PIP/DIP 35 vs 31 deg for TM). (a) changes every pose and is not driven by data. (b) uses the session's own holds and separates exponentially, so the two touches differ clearly (TM 70 vs 0 deg). It stays display-only, so detection results do not move.

**Cost:** the drawn joint shape is a model guess, not measured. It works only after guided calibration. TI templates are only 0.052 apart (others 0.21 to 0.30), so TI draws a partial blend (w 0.78/0.22). The fix is a more distinct re-record, not a smaller TAU. Not tried on the live glove (unverified).

### 2026-11-07 | Thumb display: nearest-anchor weights plus near-pair contact

**Options:** (a) keep the fixed weight floor (1e-3) in the thumb warp. (b) Loosen detection so it drives the drawing. (c) Weight the anchors relative to the nearest one, and draw the contact correction for the fingertip nearest the thumb tip when nothing is detected.

**Choice:** (c). Weights are `w_i = exp(-(d_i^2 - d_min^2) / 2 sigma^2)`, normalised. New `nearPair` with `NEAR_GAP` 0.75 (about two finger widths, a guess): with no detected touch, the nearest fingertip within 0.75 of the drawn thumb tip gets the existing contact correction. A detected touch still wins. The 40 deg cap stays. Detection is unchanged.

**Why:** in the first v3 session the 3D thumb lay along the palm during a live thumb-to-middle ring. With the floor, once the pose was more than about 0.6 from every anchor, all weights fell below it and the thumb went back home onto the palm. Rest poses still stay home, because FLAT, FIST, SPREAD and FLATCHECK are anchors with zero offset. (b) would make the drawing look right by faking detection, and detection has to stay honest. On the recorded file the drawn thumb-tip gap during self-test touches is TI 0.33 to 0.12, TM 0.46 to 0.07, TR 0.37 to 0.03, TP 0.20 to 0.12. Guided holds stay at 0.045 or less. A flat hand draws no contact.

**Cost:** a near miss is drawn closed too. Unverified on the glove: thumb to middle may draw closing onto the ring finger (gap 0.55 in one replay variant), a fist may draw the thumb snapped onto a finger, and `NEAR_GAP` and `THUMB_BASE_FRAC` 0.5 are guesses.

### 2026-11-07 | Learned thumb base movement

**Options:** (a) keep `fitHand` (rigid lengths, fixed thumb base). (b) Loosen it: wider bounds, plus a free joint share. (c) Let the thumb base move: each touch hold stores the thumb base offset that puts the tip on the fingertip, and live poses blend those offsets.

**Choice:** (c). Blend weight is a Gaussian on whole-hand similarity (sigma 0.18). Non-touch poses anchor at zero offset. Near misses use their pair's ring offset.

**Why:** the first real calibration export rejected the fit (gap 0.83). Offline: current bounds 0.88, wide bounds 0.59, wide plus a free joint share 0.51 (per-hold up to 0.92). So (a) and (b) fail. The thumb sensor turned only 29 to 45 deg for every touch, because the thumb's base joint travels and a sensor on the tip cannot see it. Replay on the real holds: mean tip gap 1.84 default, 0.11 with the learned thumb, 0.009 drawn. Held-out rows (templates from the first half of each hold) 13 of 13 correct (`tools/verify_real_calibration.mjs`).

**Cost:** this is pose-space interpolation, not a model of the thumb. The gaps are small partly by construction, because the offsets come from the same holds. Poses between holds are blended and unmeasured. One session, one person. Not tried live on the glove (unverified).

### 2026-11-07 | Finger roll from the fist hold

**Options:** (a) no correction, as before. (b) Gravity mount per finger. (c) Gyro mount per finger. (d) Take each finger's roll from the fist hold and correct the drawn fingers only.

**Choice:** (d). `rollFromFist` and `unrollQs`. Display only: detection and exports keep the raw orientation.

**Why:** the first real fist hold gave rolls of 11, 27, 29 and 34 deg (index to pinky), the same pattern as the T5 gyro fit (10, 17, 21, 30 deg). Two separate sources agree, and the fist is already in the guided run.

**Cost:** it assumes all fingers really curl about the same axis in a fist. Detection and the dataset do not get the correction, so for ML features the question was settled later, see [no per-finger mount roll correction](#2026-11-16--no-per-finger-mount-roll-correction-in-the-features). Needs a fist at every calibration. Unverified live.

### 2026-11-07 | Stillness gate removed from guided holds

**Options:** (a) keep the gate (hand, thumb and finger still, 30 samples, spread <= 0.2). (b) Loosen the thresholds. (c) Remove the gate: use the last 7 s of each 10 s hold and let spread <= 0.1 decide.

**Choice:** (c).

**Why:** in the first real export only 35 to 82 of about 100 samples were kept per hold and 2 of 15 holds were missed (NEARTM, NEARTP), while the spread was only 0.007 to 0.017. The gate rejected good holds. Spread already measures what matters. Skipping the first 3 s drops the move-into-position part.

**Cost:** a hold with a slow drift or a pause could pass, which the old gate would have caught. The stricter spread limit (0.1, was 0.2) and the replay check after each run are the safeguards. Not tried on the glove (unverified).

### 2026-11-07 | Contact correction as a display-only cap

**Options:** (a) leave the 3D model alone: detection only changes a label. (b) While a touch is detected, turn the touching digits toward the point between the tips until they meet, with no limit. (c) Same as (b), capped at 40 deg per digit, eased in and out, display only.

**Choice:** (c). 8 passes, 40 deg cap, eased through the same group that handles rest bend.

**Why:** the user saw touches felt on the glove but never drawn on the model. An uncapped pull (b) would show contact whatever the sensors said, so a wrong detection would look like a right one. The cap keeps the picture tied to the measured pose. Nothing feeds back into fusion, features or the dataset. Corrections release to 0 deg when the touch ends (simulated page run).

**Cost:** on a straight touch the thumb can only reach a thin shell of tip positions (one sensor couples its joints), so a gap can remain. In the run with the fit rejected it was up to about 0.6. Not tried on the glove (unverified).

### 2026-11-07 | Fitted hand with a rejection rule

**Superseded 2026-11-07 (later) by [learned thumb base movement](#2026-11-07--learned-thumb-base-movement).** The first real export rejected the fit (gap 0.83), and exploring it offline showed no rigid length fit can work. `fitHand`, `solveN` and the saved hand are deleted. The text below is kept as the record of what was tried.

**Options:** (a) keep the generic hand. (b) Fit the hand to the user from the touch holds and trust any result. (c) Fit, but reject the result when the holds do not agree.

**Choice:** (c). `fitHand`: Levenberg-Marquardt over thumb base, thumb length and 4 finger scales. Each touch hold is a constraint that two tips are in the same place. Bounds: base +-0.5, length 2.2 to 3.1, scale 0.85 to 1.2. It starts from the default each session. If the mean gap stays over 0.35 the fit is rejected and the default hand is used. Saved in `localStorage`.

**Why:** on a simulated different hand the old model left ring-pose tips 0.64 to 0.73 apart (finger width about 0.38). That simulation was rough. With a second parameter set of the same joint model, 7 of 8 holds real and 2 deg noise, the gap went from 0.46 to 0.03 (0.001 with contact correction). Testing the full run showed the cost of no rejection: a fit dragged the thumb base onto the palm on poses that were not real touches. Tighter bounds and the rejection rule came from that, tests first.

**Cost:** sloppy holds give the default hand, not a better one. The numbers show the solver works, not that the joint model matches a real hand. Updates the open item "Guided functional calibration": fitting the 3D hand is done in simulation, unverified on the glove.

### 2026-11-07 | Three finger segments, joint shares guessed

**Options:** (a) keep 2 segments and a cosmetic 40 % tip bend. (b) 3 segments with the sensor's rotation split over the joints.

**Choice:** (b). Segment lengths 0.45 / 0.30 / 0.25. Joint shares are q^0.5, q, q^1.35 (knuckle, middle joint, tip).

**Why:** the sensor sits on the middle phalanx, but its whole rotation was applied at the knuckle, so fingers bent wrongly and tips landed in the wrong place. Three segments let a touch use real geometry.

**Cost:** only the sensor's own segment is measured. The shares are guesses, and the fit and contact correction partly hide a wrong split. Tune from the exported holds. Not tried on the glove (unverified).

Related: the thumb was lengthened to len 2.6, z -1.1 (was the phalanges' length). The thumb pivots near the wrist, so with the old length it reached the index only at about 100 deg of curl and a straight touch could not be drawn. A 2.6 palm is about 10 cm, unverified against the user's hand. This updates the anchor in "Thumb anchored below the palm plane" (anchor idea stays, length and depth change).

### 2026-11-07 | Touch labels derived from the pose name, no new CSV column

**Options:** (a) add a touch column to the batch CSV. (b) One lookup table from pose name to touch set (`tools/pose_labels.py`), applied when training. (c) Label touches by hand after recording.

**Choice:** (b). 14 poses, four pairs (thumb to index, middle, ring, pinky). The same pose name is used by the dashboard list, `make_synthetic_batch.py`, `check_dataset.py` and `train_touch.py`. `train_touch.py` skips rows whose label is not a pose and says how many.

**Why:** the CSV format stays fixed, so no parser changes and old files stay valid. One table is one place to fix a wrong label. A new touch set means a new pose name, not a format change. (c) is slow and error-prone.

**Cost:** the label is only as good as the pose I actually held. A rep where the thumb slipped is still labelled as touching. Pose names are limited to 12 characters by the dashboard label field. Finger-to-finger contact is not covered. Synthetic checks only, not recorded on the glove (unverified).

### 2026-11-07 | Session templates as the live touch detector

**Options:** (a) only a trained model per pair (logistic regression on the 15 `dir` numbers), loaded as JSON. (b) Session templates: in guided calibration, hold each touch pose and keep it as a template of this session. A pair touches when the thumb and that finger are near one of its templates. (c) Both, with templates first.

**Choice:** (c). Readout order: session templates, then the loaded model, then the old thumb-index rule. The model stays for the dataset path. Templates are the live path.

**Why:** the synthetic leave-one-session-out runs showed that session-to-session offset, not the model, limits the trained detector. Recall / near-miss false alarm for the linear model: no offset 1.00 / 0.00 on all pairs; curl offset sd 6 deg with a 12 deg near miss, TI 0.90 / 0.28 and TR 0.76 / 0.25; plus 10 deg yaw drift, TI 0.95 / 0.53. kNN was not better on near misses (TI 1.00 / 0.15 and TR 1.00 / 0.12 even with no offset). A template and the live pose share the session offset, so it cancels. On synthetic numbers a 15 deg offset is still detected by a same-session template and defeats a template from another session. The gate in `train_touch.py` was not weakened to pass.

**Cost:** about 140 s of guided calibration each session. The radius rule (max of 0.3 and 3 x spread, capped at half the distance to the flat hand) is a guess. Straight touches can sit close to flat and be weak. Templates age with sideways drift and live in memory only. The guided holds are not saved to the dataset. Only the pose is matched, not contact. All synthetic or simulated-page checks, nothing on the glove (unverified).

### 2026-11-07 | Small committed GIF and mp4 for README video

**Options:** (a) drag an mp4 into the README in GitHub's web editor. GitHub hosts it, free limit 10 MB per file. (b) Commit a short GIF to `docs/media/` and embed it. (c) Commit a small mp4 and link it. (d) No video, images only. (e) A combination of (b) and (c).

**Choice:** (e). The T2 fast-fist before/after clip is committed twice in `docs/media/`: a GIF (`t2-fast-fist-before-after.gif`, 270 px, 10 fps, 64 colours, 3.8 MB) that plays inline in the README, and an mp4 (`t2-fast-fist-before-after.mp4`, 540 px wide, CRF 28, silent, 1.4 MB) that the README links for the better-quality version. A cover frame (`t2-fast-fist-cover.jpg`) is committed too.

**Why:** GitHub does not play an mp4 from the repo inline in a README, so only the GIF gives playback on the page. A web-uploaded mp4 (a) plays inline, but it is hosted outside the repo history, so the link can break and the video is not versioned with the docs. The GIF alone is too soft to show the fast snap properly, so the mp4 is there for anyone who wants to look closely. A moving glove is the best proof on the page, so (d) was not worth it. The big raw recordings (45 MB and 50 MB) and the other motion-test mp4s stay local and gitignored.

**Cost:** about 5.5 MB (GIF, mp4 and cover together) goes into git history for good, and deleting the files later does not shrink the history. The GIF is low resolution and only 10 fps, so it looks choppy. Only one test is shown. How it renders on GitHub is unverified until pushed. The 163° in the hook is read off the dashboard by eye, and the after run is video only, not re-measured.


### 2026-11-07 | Thumb rotation split over base and tip joint

**Options:** (a) apply the tip sensor's whole rotation at the base, plus a cosmetic extra tip bend (the model before this). (b) Single measured flex axis (the entry below). (c) Split the sensor's rotation over the two joints: base gets `q^f`, tip gets `q^(1-f)`, so the product is `q`.

**Choice:** (c), with `THUMB_BASE_FRAC = 0.5`. Supersedes "Thumb bend measured as twist about a measured axis". `THUMB_FLEX_AXIS` and `thumbFlexRad` are removed. The thumb bend readout is the total rotation from rest, `2 acos|w|`.

**Why:** the user said the thumb sensor is already at the tip, so (a) sent the whole thumb where the tip points (the "points straight down" look). Per-capture axis energy share (X / Y / Z): T1 0.16 / 0.74 / 0.10, T2 0.12 / 0.65 / 0.23, T3 0.07 / 0.90 / 0.03, T4 0.05 / 0.78 / 0.17, T6 0.62 / 0.28 / 0.09. T1 to T4 are mostly sideways swing, T6 is mostly downward bend about X. One axis cannot cover both, which kills (b). With (c) the tip segment ends exactly where the sensor points, about any axis. `tools/verify_thumb_rig.mjs`: 0.0 % inside the palm for swing up to 90 deg and tip bend up to 90 deg. Browser check with an injected 90 deg bend: tip direction (0, -1, 0), bend reads 90.0.

**Cost:** `f = 0.5` is a guess at how the two joints share the bend. Only the tip direction is measured, so the base and the mid joint position are not. The readout has no direction, so an outward swing also reads as bend, and the curl sign control does not apply to the thumb. Not tried on the glove (unverified).

### 2026-11-07 | Thumb bend measured as twist about a measured axis

**Superseded later the same day by "Thumb rotation split over base and tip joint" (above). Kept as written to show the failure.** The single axis was incomplete: the thumb moves on two axes. Its premise (sensor on the proximal phalanx, tip cosmetic) was also wrong per the user, and I took it from the docs without checking the glove.

**Options: (a) keep pitch about X for the thumb, like the fingers. (b) Measure the thumb's bend axis from its gyro and take the twist of `q_rel` about it. (c) Learn the axis live.

**Choice:** (b). `THUMB_FLEX_AXIS` is the normalised mean of the T3 and T4 gyro PCA axes, and `thumbFlexRad(q) = 2 atan2(v.n, w)`, wrapped. It drives the curl readout and the tip bend.

**Why:** PCA of the thumb gyro on thumb-dominant samples gave axes 19 and 27 deg off Y (93 % and 91 % of the variance), not X. Flex range grew in most captures, for example T1 -9.0..21.7 (pitch) vs -25.3..44.8 (flex). Fists read positive, outward spreads negative.

**Cost:** the axis comes from low-rate captures (17 to 43 Hz) and mostly outward motion. It is stored in the thumb sensor frame, so a remount shifts it. Near vertical (flat hand) it is gyro-only and drifts. The curl sign control no longer applies to the thumb. Not tried on the glove (unverified). Option (c) needs a guided motion at calibration and is not built.

### 2026-11-07 | Thumb anchored below the palm plane

**Options:** (a) keep the anchor level with the palm (x 1.45, y 0.1). (b) Move it under the palm: x 1.3, y -0.6, z -0.9, yaw 0.11. (c) Make the palm box smaller or hollow.

**Choice:** (b). Supersedes the thumb placement part of "Straight thumb segment in the 3D model" (2026-08-08). The straight segment itself stays.

**Why:** the 2026-08-08 check only covered the rest pose (7.5 % buried). Walking the axis in 200 steps, an inward swing about Y buried 65.0 % of the thumb at 15 deg, 77.5 % at 30, 82.5 % at 45 and 86 % at 90. Under the palm it is 0.0 % buried at 0, 15, 30 and 45 deg. The default camera also moved to the thumb's side (camYaw -0.7), because it looked from +X while the left thumb is at -X. `tools/verify_thumb_rig.mjs` checks this.

**Cost:** the anchor is a guess from the rest direction (6.5 deg outward), and the thumb now looks tucked under the palm, not beside it. (Later correction: the sensor is on the tip segment per the user, so the tip joint is not purely cosmetic; see the split decision.) The thumb-index gesture rule thresholds were guesses and the anchor moved, so they are unverified.

### 2026-10-31 | Hand IMU tilt measured at calibration, hand-axes picker removed

**Options:** (a) add a hard-coded remap for the mapping seen on the glove (up shows as -X, a left turn shows as Y, Z unchanged) and make it the only option. (b) Measure the XIAO's tilt from gravity at every calibration, keep one base remap, and drop the picker.

**Choice:** (b).

**Why:** the symptom (pitch and turn swapped, roll fine) is a hand frame rolled 90 deg, which a tipped XIAO produces. A fixed remap would match only today's mount and break at the next remount. Gravity gives the tilt for free at calibration, and the gyro learner already gives the in-plane angle, so (b) handles every mount with no picker. The user's requested mapping is what (b) produces for a XIAO tipped 90 deg (tested in the browser: the palm matched the real hand within 1.2 deg right after calibration).

**Cost:** the calibration pose must really be flat with straight fingers, because the fingers' up defines the hand's up. With fewer than two good fingers, it falls back to the model's +Y. No manual override is left in the UI.

### 2026-10-31 | Hand IMU mount angle learned live from the gyros

**Options:** (a) re-pick the hand-axes dropdown after every remount (only 90° steps, by eye). (b) Mount the XIAO rigidly (glue or a 3D-printed clip). (c) Learn the in-plane mount angle live by matching the hand gyro to the finger gyros during whole-hand turns.

**Choice:** (c), and (b) stays worth doing later.

**Why:** the velcro mount changes between sessions, and any angle is possible, not just 90° steps. The gyro match is closed form, needs about 1 s of turning, and ignores finger-only motion. Tested offline (T5, recovered 0/35/90/180 deg within 4 deg) and in the browser (fingers 74 to 134 deg off before, under 0.5 deg after).

**Cost:** assumes the four long fingers point along the hand's forward. Their mean splay becomes the hand's forward (about 4 deg on this glove). Assumes the XIAO lies flat in the hand plane. Each session needs one short hand turn before Batch Capture accepts reps.

### 2026-10-31 | Hand axes fwd +X, left model, headings aligned at calibration

**Options:** (a) keep offering four hand-axes guesses with fwd +Y as default and a right-hand model. (b) Measure the hand axes from data and fix the default. (c) Also align every finger filter's heading to the hand's at calibration.

**Choice:** (b) and (c). Default hand axes fwd +X, default model hand left, `alignHeadings()` after each calibration.

**Why:** A gyro fit on motion test T5 (hand turned with fingers straight) puts every finger within 10 deg of the hand's forward with fwd +X and 80 to 180 deg off with the other three. Left is physically right for this glove (thumb at -X in the viewer frame). Heading alignment assumes the fingers point the hand's way in the calibration pose, which is the calibration pose by definition. It cut the T5 replay error a little (thumb p90 15 to 12 deg).

**Cost:** if the hand IMU is remounted the default is wrong again and has to be re-measured. Heading alignment forces a straight-finger assumption: a finger that really sits splayed at calibration gets its splay removed from the zero. Display storage key bumped, so the curl sign setting resets once.

### 2026-10-31 | Accel offsets learned live, saved per browser

**Options:** (a) fixed constants in the dashboard. (b) Run `tools/fit_accel_offsets.py` offline after each recording and paste the result. (c) Learn the offsets live in the dashboard from still moments, save them in the browser, and keep the constants as defaults.
**Choice:** (c). Every 0.25 s while a sensor has been quiet for 0.5 s, one raw accel sample goes into running least-squares sums for a sphere fit. It refits every 10 samples after 60 and applies the result only if the directions are spread out and the sphere is clean (radius within 0.05 of 1 g, radial rms under 0.03 g). Saved under `gestura_acc_offset_v1`.
**Why:** the offset is a property of the sensor, so it should follow the sensor, and a fit that runs by itself needs no remembering. Constants alone break when a sensor is swapped or its offset shifts. The offline script works but needs a manual step each time. In a synthetic test it recovered the pinky offset within 0.003 g after 5 orientations.
- Cost: the saved value is tied to one browser profile. A different browser or cleared storage starts from the constants again.
- Cost: a wrong fit could get saved. The sphere-quality and direction-coverage checks reduce that risk, but they are not proof. Clearing localStorage resets it.
- Cost: needs about 15 s of still time spread over different orientations before it can confirm anything. Real-glove behaviour is unverified.

### 2026-10-31 | Accel-magnitude gating rejected for now

**Options:** (a) always trust the accelerometer at the same weight. (b) Down-weight it when |a| is far from 1 g, since then the sensor is feeling motion on top of gravity.
**Choice:** (a), for now.
**Why:** I replayed the 7 motion-test recordings with (b). Nothing changed measurably, and the fast-fist index got slightly worse (106 to 116 deg). The error in this data comes from gyro clipping and yaw, not linear acceleration. The recordings are 17 Hz and clipped, so this is a weak test.
- Cost: during very fast moves the accel may still pull the filter the wrong way. Not seen in the data so far.
- Revisit with clean 50 Hz, ±2000 deg/s captures (unverified until then).

### 2026-10-31 | Heading drift: automatic re-zero in the calibration pose

**Options:** (a) add a magnetometer for a yaw reference. (b) Manual re-zero only (the Zero Orient button). (c) Re-zero automatically whenever the hand is back in the calibration pose and still.
**Choice:** (c). When every non-bad sensor has been still for 1 s or more, has tilt error under 2 deg and has its up within 8 deg of the calibration up, each zero is slerped toward the current orientation (0.4 s time constant).
**Why:** a 6-DOF IMU cannot observe yaw, so heading drifts by physics. A magnetometer is new hardware on every finger, and magnetometers are generally unreliable indoors near metal (unverified here). A manual button works but the drift is gone only when I remember to press it. The calibration pose is the one place where the right answer is known, so correcting there is safe. In the replay, T3, T5 and T6 end under 1 deg per finger.
- Cost: fingers spread sideways while the hand lies flat palm-down look identical to gravity, so that spread is zeroed too. T4 still ends at 13.9 deg for the thumb after healing.
- Cost: it only fires palm-down flat. Letter poses are not that pose, so they do not trigger it, but it also means no yaw fix during long use in other poses.
- Thresholds are first guesses tuned on old captures. Unverified on the glove.

### 2026-10-31 | Snap-back: beta scaled by tilt error when still

**Options:** (a) a fixed higher Madgwick beta. (b) Raise beta from the slider value toward 1.0 in proportion to the tilt error, only after 0.2 s still.
**Choice:** (b). Full at 20 deg error. 2 deg gives 0.19, 0.5 deg gives about 0.12.
**Why:** Madgwick steps a fixed beta along a normalised gradient. A big fixed beta therefore chatters once the filter has converged. Scaling by error gives a fast pull when the drift is large and almost no change near zero. Max correction is 2 * beta rad/s, 115 °/s.
- Cost: two more tuning constants (the 0.2 s still time and the 20 deg full-scale error) to explain and keep right.
- Cost: it only helps pitch and roll. Yaw still needs the re-zero above.

### 2026-10-31 | Quality gate rejects reps, no new CSV columns

**Options:** (a) add quality columns to the batch CSV (link rate, trust per sensor). (b) Reject a rep in the dashboard when the link is under 40 Hz or any sensor is untrusted, and leave the format unchanged.
**Choice:** (b). The rep flashes red and Batch Capture stays armed.
**Why:** a changed format means changing `check_dataset.py` and `train_baseline.py` in the same commit, and old files stop matching. Rejecting at capture time keeps bad reps out of the data in the first place. A sensor is untrusted if it clipped (|g| at or above 1990 °/s) or dropped a frame since its last zero.
- Cost: the reason for a rejection is not stored in the file. I only see it live on the HEALTH cell.
- Cost: the rule can be too strict (a single dropped frame blocks that sensor until the next re-zero). Unverified on real captures.

### 2026-10-31 | Gyro full scale ±2000 °/s

**Options:** (a) keep ±500 °/s. (b) ±1000 °/s. (c) ±2000 °/s on the fingers and the hand IMU.
**Choice:** (c). Finger `GYRO_CONFIG 0x18` (16.384 LSB per °/s), hand LSM6DS3 `gyroRange 2000`, `GYR_SCALE 16.384` in firmware and dashboard together.
**Why:** the fast-fist test (T2) had 84 to 120 clipped samples per finger, 11 to 15 % of all samples, at the ±500 limit. A clipped rate integrates too little rotation. ±1000 would probably still clip on a snap and I have no peak measurement, so I took the range that cannot clip on a hand.
- Cost: 4x coarser resolution, 0.061 °/s per LSB instead of 0.015. That is still far below the sensor noise (unverified at ±2000, not measured).
- Cost: firmware and dashboard now have to match. The new dashboard reads v4 (stage 08) gyro 4x too large.
- The slow fist (T1) also failed to return, so clipping is not the only cause. See DOCUMENTATION 2026-10-31.

### 2026-10-31 | Pinky accel offset corrected by a dashboard constant

**Options:** (a) subtract a fitted constant in the dashboard. (b) subtract it in the firmware. (c) write the offset into the MPU offset registers.
**Choice:** (a). `ACC_OFFSET` per sensor in `handrig_dashboard.html`, pinky [0.250, 0.190, -0.165] g, others 0. Applied in the raw sensor frame before remap, fusion and the calibration checks. The CSV export stays raw.
**Why:** a sphere fit over the quasi-static samples gave the pinky a centre of (0.250, 0.190, -0.165) g and a radius of 1.005 g, so the scale is right and the zero point is off. The other five are within 0.025 g. Keeping the CSV raw means the correction can be redone or changed later from the same files.
- Cost: the constant must be re-fitted if the sensor changes or moves, and the dashboard is now tied to this glove.
- Cost: firmware (b) would have kept every client correct, but it hides the raw data and needs a reflash for each re-fit. Registers (c) are unverified on this chip and lost on a power cycle unless the firmware writes them.
- Root cause of the offset is unverified (the pinky is the only genuine MPU-6050).

### 2026-10-31 | Calibration settle in closed form

**Options:** (a) keep stepping the Madgwick filter at high beta until it settles (40 steps). (b) Compute the settled quaternion directly from the averaged gravity vector.
**Choice:** (b). The shortest rotation taking the measured up `u` onto +Z: `q = normalise(1+uz, uy, -ux, 0)`, with the upside-down case handled separately.
**Why:** 40 steps at beta 1.0 and dt 0.02 turn at most 40 * 0.04 rad, about 92 deg. Every sensor starts 97 to 109 deg away, so replaying the captures left 17 to 27 deg of error in every zero. More steps would work (100+ gave under 1.6 deg), but the closed form does not depend on a step count. Checked against the dashboard's own Madgwick run to convergence: within 0.2 deg including heading.
- Cost: one more piece of quaternion math to explain and keep right. It sets heading to the shortest rotation, so heading is arbitrary, which is fine since yaw cannot be observed anyway.

### 2026-10-31 | Calibrate before every motion test, not once per session

**Options:** (a) calibrate once at the start of the session and run all tests on that bias and zero. (b) Run the full 20 s calibration before every test, with the calibration hold inside the recording.
**Choice:** (b). Press ● Record, then Calibrate, then clap, 5 s flat, movement, 5 s flat, Stop.
**Why:**
- Each test is independent. It starts from a fresh gyro bias and a fresh zero pose, so one bad test can't spoil the next.
- The CSV is raw (no bias correction, no remap, no calibration markers). With the 20 s hold inside the recording, the analysis can recompute the exact bias and zero the dashboard used. The clap marks where calibration ended.
- Cost: it hides bias drift across the session, for example while the MEMS gyros warm up. T0 and T6 still show drift within one test, but not between tests. Powering the glove about 5 minutes before the first calibration should remove most of the warm-up drift (unverified for these sensors).
- Cost: about 20 s more per test.
- Calibrate in the same flat pose and on the same surface as the 5 s flat holds. "Did the fingers return" is measured against the calibration zero.

### 2026-10-06 | Batch export uses the hand-relative quaternion

**Options:** (a) keep exporting `st.rel`, each sensor relative to its own calibration zero. (b) Export `conj(q_hand) ⊗ q_finger`, the same value the 3D model draws, with the sign pinned to `w ≥ 0`.

**Choice:** (b). The localStorage key moved from `_v1` to `_v2` so old and new rows can't end up in one CSV.

**Why:** the whole point of the glove is that a finger's pose is measured against the hand, so arm tilt doesn't leak in. Option (a) put arm tilt into every finger feature, which would have poisoned the training data. `q` and `−q` are the same rotation, so without pinning the sign a classifier would see two encodings of one pose. The cost: anything captured before this change can't be mixed in.

### 2026-10-06 | Dashboard goes monochrome

**Options:** (a) keep the copper accent. (b) Pure black and white, with state shown by symbols, words and line style. (c) Black and white plus one warning colour.

**Choice:** (b), dark only, with a hidden-line wireframe hand.

**Why:** if no state depends on colour, everything stays readable for colour-blind users, in a grey-scale print and in a screenshot. X, Y and Z are solid, dashed and dotted everywhere: traces, bars, the axis triad and the key. The cost is losing the copper brand accent on this one screen.

### 2026-08-08 | Calibration stillness gate uses deviation, not an absolute threshold

**Options:** (a) drop calibration samples where raw gyro is above a fixed 6 °/s. (b) Drop samples that deviate from that sensor's own rolling average.

**Choice:** (b), after (a) broke the live glove.

**Why:** a still MPU-6050 doesn't read zero. It reads its own fixed bias, which can be up to ~40 °/s on these clones. The pinky's bias was over 6 °/s, so option (a) threw out every one of its samples. It never calibrated and showed −105° roll on a hand lying still. Option (b) works at any bias and still rejects real motion. The lesson: before filtering on "X below a threshold", check whether X has a real non-zero baseline.

### 2026-08-08 | Straight thumb segment in the 3D model

**Options:** (a) a two-segment thumb with a bend, so it visibly touches the index. (b) A straight segment like the other fingers, angled toward the index.

**Choice:** (b).

**Why:** (a) looked right at both endpoints, but a 200-step walk along the segment showed 22.8 % of it hidden inside the palm box. That was the "broken, twisted" look on the live view. The straight version clips 7.5 %, only at the tip, the same as the other fingers. The cost is that the thumb doesn't literally touch the index. A real multi-joint rig is the fix if it ever matters.

### 2026-08-07 | Settle the calibration reference instantly instead of waiting

**Options:** (a) reset the filter and wait longer before grabbing the zero reference (600 ms already failed, then 2.5 s failed). (b) Derive the quaternion from gravity with a hand-written formula. (c) Run the existing `Madgwick.update()` ~40 times on the calibration-average accel, with zero gyro and β = 1, then grab the reference.

**Choice:** (c).

**Why:** how long the filter takes to converge depends on the smoothing slider and on how far from flat the hand is, so no fixed wait is safe. Option (b) risks a sign or axis mismatch with the filter's own conventions that nothing would catch. Option (c) reuses the exact code the live path uses, so the conventions can't diverge, and it converges in about 0 ms. Confirmed on the glove.

### 2026-08-07 | Widen the BLE link instead of shrinking the data

**Options:** (a) cut the sample rate or frame size to fit the default BLE settings. (b) Call `Bluefruit.configPrphBandwidth(BANDWIDTH_MAX)` for a bigger MTU and a deeper send queue, and relax the connection interval.

**Choice:** (b).

**Why:** on the first live session the rate fell from 50 to 8.3 Hz. Sensor reads stayed flat at ~5.9 ms while `bleuart.write()` blocked for over 100 ms, so the link was the bottleneck, not the data. The default config sits far below what the nRF52840 can do, so shrinking the frame would have thrown away data for nothing. After the change the dashboard held ~47 Hz / 3.7 KB/s. I also moved the connection interval from (6, 12) to (12, 24). About 4 KB/s never needed sub-15 ms intervals.

### 2026-08-07 | Dashboard carries the public name "Gestura"

**Options:** (a) keep the dashboard named "HandRig" like the rest of the repo's internal names. (b) Call it Gestura, the public product name.

**Choice:** (b).

**Why:** the dashboard is the demo people actually see, so it gets the product name. The repo, firmware and engineering docs stay "Cheirograph". Firmware still advertises as `HandRig-6IMU` over BLE. That's an internal name and changing it would break nothing, but it isn't worth a reflash on its own.

### 2026-07-25 | Verify every I²C write and watch for frozen sensors at runtime

**Options:** (a) keep v3: write the right clone-init sequence and trust it, with a one-shot check at boot. (b) Check every write's ACK, read config registers back, retry on failure, and run a continuous per-sensor "stuck" detector.

**Choice:** (b).

**Why:**
- v3 wrote the right registers but ignored every return value. A NACKed write looked like success. That includes a NACKed mux select, which sends the next config to whichever channel is still latched.
- An ACK only proves something answered. A matching readback of `PWR_MGMT_1/2`, `GYRO_CONFIG` and `ACCEL_CONFIG` proves that chip stored the value.
- The runtime check exists because the boot check only sees boot. Six raw axes bit-identical for 50 frames means frozen. At ±4 g one LSB is 122 µg, and the noise floor is ~20 LSB, so a working sensor can't repeat exactly even lying still. That test is stronger than "|a| ≈ 1 g", which the original stuck thumb passed.

The cost is a visible 30–250 ms rate dip during a live re-init. I kept it visible on purpose so hardware faults don't get hidden.

### 2026-07-25 | Checksum on the BLE frame

**Options:** (a) rely on the `0xAB` sync byte alone. (b) Add a trailing XOR checksum (frame goes 79 → 80 bytes) and re-sync on mismatch.

**Choice:** (b).

**Why:** `0xAB` shows up inside normal sensor data all the time. One dropped byte lets the parser lock onto a false sync and draw a full screen of plausible garbage, which looks exactly like the clone bug. One XOR byte costs ~1.3 % bandwidth and turns silent corruption into a counter. I skipped CRC because the failure here is misalignment, not bit flips, and XOR catches misalignment.

### 2026-07-25 | Axis remap lives in the dashboard; hand axis picked at runtime

**Options:** (a) remap axes in firmware. (b) Remap in the dashboard and keep the stream raw. For the hand's forward axis: (c) hard-code a guess, or (d) offer the candidates in the UI.

**Choice:** (b) + (d).

**Why:** the raw stream is what gets archived. If firmware remapped it, re-mounting one sensor would make old captures impossible to reinterpret. For the hand sensor I had measured only one fact: `az ≈ −0.98 g` lying flat, so up is `−Z`. Which horizontal axis points at the fingers was never checked. Four remaps satisfy that, so the UI offers all four, and you tilt the hand forward and pick the one that tips forward. All remaps are proper rotations (det +1), so the gyro transforms with the same matrix as the accel.

### 2026-07-19 | Remap sensor axes before fusion

**Options:** (a) rebuild the 3D model's rest pose per sensor to match each mounting. (b) Remap raw accel/gyro into one model frame before Madgwick.

**Choice:** (b). Fingers use `(x, y, z) → (x, z, −y)`.

**Why:** one small function before fusion keeps Madgwick and `q_rel` in a single frame for all six sensors. Per-mesh transforms would be harder to audit and would break when a sensor is re-mounted. The finger remap comes from the measured mounting (sensor `−Y` toward the fingertip, `+Z` up), with the third axis from a right-handed cross product.

### 2026-07-19 | Raw register driver for the clone finger IMUs

**Options:** (a) keep `MPU6050_light` and coax the clones awake. (b) Adafruit's library, which rejects `WHO_AM_I ≠ 0x68`. (c) Write a small raw-register driver.

**Choice:** (c).

**Why:** two captures showed 4 of 5 fingers stuck at exact values or ramping by exactly `±0x2000` LSB per frame. Those are digital artifacts, not noise. The four are MPU-6500/9250 clones (`WHO_AM_I = 0x72`), and `MPU6050_light` never writes `PWR_MGMT_2` to enable all axes, so they boot half-awake. The pinky is a genuine 0x68 and always worked, which was the clue. About 15 lines of reset → wake → enable axes → configure work for both chips. A boot diagnostic now prints each channel's health within 2 s.

### 2026-07-18 | Tape for finger sensors, velcro for the MCU

**Options:** tape everywhere, velcro everywhere, or split by component.

**Choice:** split. Leukoplast on the finger IMUs, velcro (or tape) for the XIAO and mux.

**Why:** finger sensors need zero wobble and never come off, so rigid tape wins. The XIAO comes off to reflash and charge, so a bit less rigidity is worth it there. Taping over the MPU chip itself is fine.

### 2026-07-17 | Fixed +90° plot correction on the bench

**Options:** (a) plot raw absolute angles. (b) A per-capture mount correction. (c) One fixed +90° rotation about each finger sensor's Y, in the plotting tool only.

**Choice:** (c), labelled as a visual aid, not a calibration.

**Why:** on the breadboard the finger modules stand upright on their pins while the XIAO lies flat, so their raw pitch sat at −75° to −80°. One fixed rotation (checked with quaternion math) lines up fingers 1–4 with the hand. Doing a real per-sensor calibration on a temporary breadboard would have been wasted work, since `q_rel` handles it properly later. Side finding: finger 5 didn't line up, which showed it was seated at a different angle.

### 2026-07-17 | Seed the filter from gravity, two-stage β

**Options:** (a) start every filter at identity with one fixed β. (b) Seed roll/pitch from the calibration accel average, run a high β briefly, then drop to a low one.

**Choice:** (b): `BETA_INIT = 2.0` for 1.5 s, then `BETA_STEADY = 0.033`.

**Why:** one β can't be both fast to converge and quiet at rest. Seeding is free, since the calibration window already collects the accel average. The cost is two more constants. It also depends on actually holding still during calibration: a bad window gives a bad seed.

### 2026-07-17 | Madgwick over Mahony and complementary

**Options:** Madgwick, Mahony, or a fixed-weight complementary filter.

**Choice:** Madgwick, one instance per sensor.

**Why:**
- Madgwick and Mahony solve the same problem and would both work if tuned. Madgwick has one gain (β) instead of two (Kp, Ki), and it converges faster from a bad start, which helps at boot.
- A complementary filter doesn't account for how wrong its estimate is. It either lags under fast motion or lets noise through at rest, and it doesn't give a clean quaternion.
- The extra math is irrelevant: six filters at 100 Hz fit easily on the nRF52840.

### 2026-07-14 | MPU6050_light over Adafruit_MPU6050

**Options:** `Adafruit_MPU6050` or `MPU6050_light`.

**Choice:** `MPU6050_light`. Later replaced for the fingers by the raw driver (2026-07-19).

**Why:** Adafruit's driver refused the module with `Failed to find MPU6050 chip!`. An I²C scan found `0x68`, so wiring was fine. `WHO_AM_I` (register `0x75`) returned `0x72`, so the module is a clone, and Adafruit checks that value strictly. `MPU6050_light` doesn't, and it includes bias calibration. The risk I noted then was that a clone might differ in register defaults. That risk later turned out to be real.

### 2026-07-14 | Arduino IDE now, PlatformIO later

**Options:** PlatformIO from day one, or the Arduino IDE first.

**Choice:** Arduino IDE. Board package and library versions are recorded in each stage README instead.

**Why:** Seeed's docs, board package and LSM6DS3 library all assume the Arduino IDE, so first flash was painless. The cost is weaker reproducibility until a `platformio.ini` exists.

### 2026-07-14 | Live with 6-DOF yaw drift

**Options:** (a) 9-DOF IMUs with magnetometers. (b) Feed raw `q_rel` to the classifier and hope drift is slow. (c) Keep 6-DOF and design the features around drift.

**Choice:** (c). Treat yaw as untrusted, prefer gravity-referenced features, and add a "flat hand" re-zero pose.

**Why:** without a magnetometer nothing anchors yaw, so it drifts without bound. That's physics, not tuning. Finger curl is pitch relative to the hand, which gravity anchors. Only spread-based pairs like U vs. V need yaw, and the re-zero pose covers those. Magnetometers would sit centimetres from current-carrying wires and need new parts and drivers. `tools/train_baseline.py` now measures this tradeoff directly.

### Pre-build | PCA9548A mux over two I²C addresses

**Options:** use AD0 for addresses `0x68`/`0x69`, or an 8-channel mux.

**Choice:** PCA9548A at `0x70`.

**Why:** two addresses cover two sensors per bus, and I have five. The mux lets all five sit at `0x68` and adds one chip. Selecting a channel before each read is cheap at 100 Hz.

### Pre-build | Fusion on the MCU, not the DMP

**Options:** the MPU-6050's onboard Digital Motion Processor, or Madgwick on the XIAO.

**Choice:** Madgwick on the MCU.

**Why:** the DMP needs undocumented register sequences that get fragile through a mux, five times over. MCU-side fusion is readable, works the same for all six sensors including the LSM6DS3, and makes me actually understand the math, which is the point of this project.

### Pre-build | Sensors on the middle phalanx

**Options:** fingertip, base, or middle phalanx.

**Choice:** middle phalanx. The thumb uses its proximal phalanx.

*Note, 2026-11-07:* the thumb sensor is on the tip segment now, per the user. When it moved is unknown (unverified). The July photo does not show the thumb clearly. The text above is the original plan and is left as written. See `hardware/WIRING.md`.

**Why:** past the middle knuckle, one sensor sees both the base and middle knuckle bending, which is the strongest single curl signal. The fingertip sees the same thing but needs a longer wire and gets in the way of touch. The base misses most of the curl.

### Pre-build | Onboard IMU as the hand reference

**Options:** a sixth MPU-6050 behind the mux, or the XIAO's onboard LSM6DS3.

**Choice:** the onboard LSM6DS3.

**Why:** it's already flat on the PCB, on its own internal bus, with zero extra wiring. The cost is a second driver and slightly different noise. Both go through the same Madgwick code.

### Pre-build | Left hand

**Options:** dominant (right) or non-dominant (left) hand.

**Choice:** left.

**Why:** my right hand stays free to solder, type and watch the serial monitor while testing alone. The cost is that fingerspelling is usually done with the dominant hand, so the dataset won't carry over to a right hand without re-collecting.
