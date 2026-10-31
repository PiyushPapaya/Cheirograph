# Build log

The dated ledger of this project: what I planned each session, what actually worked, and what broke. Newest entry first.

Rules I keep:
- One entry per work session.
- Failures go in. A log that only shows wins is useless as evidence.
- The log is updated in the same commit as the code it describes.
- Past entries aren't edited to look better. The 2026-10-31 docs pass changed wording and fixed old paths to match the current folder layout. Facts and results were left as they were.

Roadmap: [GENERAL_PLAN.md](GENERAL_PLAN.md). Design choices: [DECISIONS.md](DECISIONS.md).

---

## Where things stand (2026-10-31)

| Area | State | Evidence |
|---|---|---|
| Six IMUs on one I²C bus via mux | Works, ~94 Hz raw | [04](04-all-six-imus-raw/) |
| Madgwick fusion per sensor | Works on the bench, roll/pitch drift ≤ 0.35 °/min | [05](05-madgwick-fusion/) |
| Glove mount | 30 min wear test passed | [07](07-full-glove-assembly/) |
| BLE stream + live 3D dashboard | Live on the glove since 2026-08-07, ~47 Hz | [08](08-ble-wireless-dashboard/) |
| Hand-relative quaternion | In the dashboard (JS), not in firmware | [tools/](tools/) |
| v5 firmware (runtime fault recovery) | **v5 plus the self-healing dashboard works on the glove (user-observed, 2026-10-31). Motion tests not re-run, no new numbers.** Dashboard also learns accel offsets live (synthetic test only). Flashed 2026-10-31. Motion tests found gyro clipping, a 17 Hz frame rate and a dashboard calibration bug. Fixes written and compiled (gyro ±2000 °/s, BLE link requests, closed-form calibration settle). Updated v5 flashed: serial shows 50 Hz connected, MTU 527, 15 ms interval. Dashboard RATE and CSV rate not yet confirmed, motion tests not re-run. Dashboard now has self-healing (stillness-based bias tracking, adaptive snap-back, auto re-zero on a flat hand, HEALTH readout): replay on the old captures cut end-of-test finger error to under 5 deg in most tests, not yet tried on the glove. Recovery paths still untested | [09](09-firmware-hardening/) |
| Dataset tooling (checker, kNN baseline) | Built, tested on synthetic data only | [tools/](tools/) |
| Real labelled data, classifier, BLE HID | Not started | |

Pinky accel "25–28 % low" (2026-08-07): explained on 2026-10-31. It is a zero-g offset of about (0.250, 0.190, -0.165) g, not a scale error. Corrected by a constant in the dashboard. Root cause of the offset is unverified. Not yet re-checked on the glove.

---

## Entry template

```
### YYYY-MM-DD | Phase N: short name

**Plan:** what I meant to do.
**Achieved:** what actually works, with evidence.
**Problems:** what broke or surprised me.
**Next:** the first thing to do next session.
```

---

## Entries

### 2026-10-31 | Phase 7.5/8: v5 flashed, finger drift found

#### What changed today, and why the glove works now

**The symptom.** With v5 flashed, the fingers drifted while held straight. After big or fast moves they did not come back to the rest pose. The pinky worked only some of the time. After the fixes below were flashed and the new dashboard loaded, it works on the glove. That is a visual, qualitative observation. No new CSV has been recorded, so there are no new numbers yet.

There was no single bug. There were four, and a missing safety net on top.

1. **The glove sent 16.7 frames per second, not 50.**
   - Cause: the firmware waited on every Bluetooth write. The link was moving small packets (most likely the default 23-byte MTU), so one 80-byte frame took four packets, at one packet per 15 ms. That is one frame per 60 ms.
   - Why it hurts: gyro integration loses angle when samples are far apart. Even the hand IMU, which never clipped, ended 24 to 35 deg off in two tests.
   - Fix: on connect, the firmware now asks the browser for a 247-byte MTU, 2M PHY, longer packets and a 15 ms interval.
   - Evidence: the serial report now shows `mtu=527 ci_ms=15.0 hz=50.0 tx_fail=0`.
2. **The gyros clipped at ±500 deg/s.**
   - Cause: a fast finger snap goes well past that. In the fast-fist test 11 to 15 % of finger samples sat at the limit, and those fingers ended 43 to 127 deg off.
   - Fix: ±2000 deg/s on all six sensors. Firmware and dashboard scale were changed together.
3. **The dashboard's calibration was wrong by 17 to 27 deg on every sensor.**
   - Cause: it "settled" each filter with 40 small steps that can turn about 92 deg in total. Every sensor starts about 100 deg away (the model's up is +Y, the filter's is +Z). So the model kept moving after every calibration and never sat at zero.
   - Fix: compute the settled orientation directly (shortest rotation from the measured up to +Z).
   - Evidence: it matches a fully converged filter within 0.2 deg.
4. **The pinky's accelerometer has a fixed offset of (0.25, 0.19, -0.17) g.**
   - Cause: its scale is fine (sphere radius 1.005 g), but the zero point is off. That tilted its gravity reading by up to about 20 deg. Its |a| of about 0.75 g also sat right on the dashboard's "bad accel" cutoff, so the sensor was switched off in some tests and not in others. That is the "pinky worked sometimes".
   - Fix: subtract the offset before fusion.
5. **Self-healing on top (all in the dashboard).**
   - Snap-back: when a finger stops, trust the accelerometer more, scaled by how far off it is. It settles in about a second without jitter.
   - Auto re-zero: hand flat and still for about 1 s slides every finger's zero back. This is the only cure for sideways (yaw) drift, because the sensors have no yaw reference.
   - Live gyro-bias tracking, trust flags with the HEALTH readout, and a smoothed 3D display.
   - Evidence (replay of the 7 recorded tests, worst finger at the end): T0 9 to 2.5 deg, T1 16 to 5, T3 15 to 0.8, T5 5.5 to 0.4, T6 94 to 0.5. T2 is unchanged because the hand never held still for a full second at the end of that recording.

**What is still limited.** Yaw has no absolute reference, so only the re-zero fixes it. Fingers spread on a flat palm-down hand get zeroed too. All thresholds are first guesses tuned on the old captures. The motion tests have not been re-run on the fixed system, so the glove is "works by eye", not measured.

---

**Plan:** Compile and flash v5 on the glove for the first time and see how it behaves with the current dashboard.

**Achieved:**
- v5 (`09-firmware-hardening/09_firmware_hardening/09_firmware_hardening.ino`) compiles and is flashed. The Arduino IDE moved the sketch into a subfolder with the same name as the sketch (it requires that), so the folder layout changed.
- Wrote a motion test protocol in `09-firmware-hardening/motion-tests/README.md`. Tests T0 to T6: still baseline, slow fist, fast fist, single fingers, spread, whole-hand rotation, mixed movement then hold. Each test records a hand video, a dashboard screen recording and the dashboard raw CSV. The CSV is the raw sensor frame (g and °/s), so clipping would show as a gyro trace sitting flat at ±500. The CSVs get committed, the videos stay local.
- Decided to run the dashboard's full 20 s calibration before every motion test, not once per session (DECISIONS 2026-10-31). Order per test: ● Record, Calibrate (20 s), clap, 5 s flat, movement, 5 s flat, Stop. The dashboard clears its buffer on Record, so one test is one CSV. The CSV is raw (no bias correction, no remap, no calibration markers), so keeping the calibration hold inside the recording lets the analysis recompute the bias and zero the dashboard used. The clap marks the end of calibration.
- Checked in `tools/handrig_dashboard.html`: `finishCalibration()` re-estimates gyro bias, noise and accel offset per sensor, flags bad sensors (|a| off by more than 0.25 g, bias over 40 °/s, noise over 15 °/s), re-settles each Madgwick filter from the averaged gravity vector and captures a new zero reference.

**Problems:**
- The first compile failed with `'LSM6DS3' does not name a type`. Two libraries ship an `LSM6DS3.h`, and the IDE picked `Arduino_LSM6DS3` instead of `Seeed_Arduino_LSM6DS3` 2.0.7. Fix: uninstall `Arduino_LSM6DS3`. After that it compiled and flashed.
- With v5 and the current dashboard, the fingers drift and tilt by themselves while held straight. Small movements look fine. After big movements the fingers don't return to the rest pose. Nothing is confirmed yet. Suspects:
  - **Gyro clipping.** The finger gyros are at ±500 °/s (`GYRO_CONFIG 0x08`, `GYR_SCALE 65.536` in firmware and dashboard), and the hand LSM6DS3 is at 500 dps too. A fast finger snap can go over 500 °/s. A clipped rate integrates less rotation, so the finger ends up in the wrong place. Accel slowly pulls pitch and roll back, but yaw never comes back. That fits "small is fine, big doesn't return".
  - **Leftover gyro bias** that moves with temperature after the one-time calibration.
  - **Yaw drift.** No magnetometer, so nothing anchors yaw (DECISIONS 2026-07-14).
  - **Weak accel correction.** The dashboard smoothing slider (Madgwick β) defaults to 0.1, range 0.1 to 0.3.
  - **Tape wobble** on a single finger.
- Not tested yet: the v5 recovery paths (SDA-to-GND test, hand IMU re-init). Unverified.
- Recalibrating every test hides bias drift between tests (for example gyro warm-up). T0 and T6 still show drift inside one test. Mitigation: power the glove about 5 minutes before the first calibration (unverified for these sensors).
- If the dashboard flags a sensor after calibration, the calibration is redone before the test starts.

**Motion tests, later the same day (evening).** I ran all seven tests (recorded as t1 to t7, renamed to T0 to T6) with a hand video, a dashboard screen recording and the dashboard CSV each. What I saw: fingers drift and don't return after movement, and the pinky "didn't work in between but at the end it did". Deviations from the protocol: calibration was done before pressing Record (so no 20 s hold in the CSVs, only about 3 s of stillness), no clap, and the hand-axes setting differed between tests (T0 "fwd +X, up -Z", T2 "fwd +Y, up -Z"). Results are in `09-firmware-hardening/motion-tests/README.md`. I wrote two scripts to analyse them: `tools/analyze_motion_test.py` (rate, dropped frames, clipped samples, |a|, return error) and `tools/fit_accel_offsets.py` (sphere fit of accel zero-g offsets).

**Findings:**
1. **Frame rate collapsed.** Six of seven tests ran at 16.5 to 20 Hz instead of 50 Hz (median dt exactly 60 ms). T5 ran at 43 Hz. The dashboard showed RATE 15 to 17 Hz, LOSS 0.0 %, BAD FRAMES 0. Zero loss with a steady 60 ms means the firmware itself only sent a frame every 60 ms, so `bleuart.write()` blocks until the link drains. 60 ms fits an unraised 23 byte MTU (an 80 byte frame is 4 packets) at one packet per 15 ms connection event. **Unverified:** needs the firmware's 2 s serial report line (mtu, hz, write_us, tx_fail). v4 reached about 47 Hz with the same BLE config, so link conditions vary between connections.
2. **Gyro clipping at ±500 °/s confirmed.** T2 fast fist: 84 to 120 clipped samples per finger (11 to 15 % of samples). T6: 13 to 34 per finger. Single samples elsewhere.
3. **Return error** (gyro integrated from the start hold to the end hold, compared with the accel-measured up direction, yaw not included). T0 still: 2 to 4 deg. T1 slow fist: hand 7, thumb 4, index 15, middle 24, ring 37, pinky 30. T2 fast fist: thumb 18, index 127, middle 95, ring 43, pinky 69. T3: middle 29, pinky 25, others 3 to 8. T4: 14 to 25. T5 (43 Hz): 10 to 15. T6: 25 to 35, pinky 78. The hand IMU (LSM6DS3, never clipped) still lost 24 to 35 deg in T4 and T6 at 16.7 Hz, so the low sample rate is a cause on its own, not only clipping. Slow fist already fails (T1), so clipping is not the whole story.
4. **Dashboard calibration bug.** `finishCalibration()` settled each filter with 40 Madgwick steps at beta 1.0, dt 0.02. One step turns at most 2 * beta * dt = 0.04 rad, so 40 steps cover about 92 deg. Every sensor starts about 97 to 109 deg away (viewer "up" is +Y, the Madgwick reference is +Z). Replaying the CSVs left 17 to 27 deg of error in every sensor's zero. The live filter then corrected it slowly, so the model drifted after every calibration and never sat at zero. 100+ steps converge to under 1.6 deg.
5. **Pinky accel zero-g offset.** Sphere fit over all quasi-static samples: pinky centre (0.250, 0.190, -0.165) g, radius 1.005 g, rms 0.014. The other five sensors are within 0.025 g of zero with radius 0.98 to 1.01. So the pinky's scale is fine and its zero point is off. This is the old "pinky reads 25 to 28 % low" item. It tilts the measured gravity direction by up to about 20 deg. It also explains "pinky works sometimes": the dashboard flags a sensor "bad accel" when calibration |a| is off by more than 0.25 g, and the pinky's calibration |a| was 0.74 to 0.82, right at the 0.75 cut, so it was dropped in some tests and not in others. **Unverified:** why the offset exists (the pinky is the only genuine MPU-6050, `WHO_AM_I` 0x68).
6. **Video vs dashboard.** At the end of T2 the real hand is flat, the dashboard shows index pitch 44 deg and yaw -105 deg, middle pitch 58 deg. Yaw is never corrected (6-DOF, no magnetometer). Pitch is corrected by Madgwick at beta 0.1 (about 11 deg/s at most), so it recovers over seconds.
7. **No firmware dropouts** (no all-zero frames) and no accel clipping in any test.
8. **Tried in a replay, not changed:** switching the finger-vs-hand formula from `rel_h^-1 * rel_f` to `(qRef_h^-1 qRef_f)^-1 (q_h^-1 q_f)`, beta 0.3, and removing the deadband. None was a clear win on these captures. Left open (DECISIONS, open).

**Changes (committed and pushed the same day, `e344839` firmware, `cf04ace` dashboard):**
- Firmware `09_firmware_hardening.ino` (compiles: 133312 B flash, 14688 B RAM, `Seeeduino:nrf52:xiaonRF52840Sense`): gyro ±2000 °/s (`GYR_SCALE 16.384`, finger `GYRO_CONFIG 0x18` plus its readback check, hand LSM6DS3 `gyroRange 2000`). `connect_callback` now asks the central for 2M PHY, data length update, MTU 247 and a 15 ms connection interval (non-blocking SoftDevice requests, the central may refuse). The 2 s report line also prints `ci_ms`.
- Dashboard `tools/handrig_dashboard.html` (copied byte-identical to `08-ble-wireless-dashboard/` and `Data/html/`, md5 `0c660afef0af30e9457dab7fa8eada33`): `GYR_SCALE 16.384` to match v5. **Breaking:** this dashboard now reads v4 (stage 08) gyro 4x too large (v4 sends 65.5 counts per deg/s, the dashboard divides by 16.4). Corrected later the same day, it first said "too small". `ACC_OFFSET` per sensor (pinky [0.250, 0.190, -0.165], others 0) subtracted in the raw sensor frame before remap, fusion and calibration checks. The CSV export stays raw. Calibration settle is now a closed form: shortest rotation taking measured up onto +Z, `q = normalise(1+uz, uy, -ux, 0)`, upside-down case handled. Checked against the dashboard's own Madgwick run to convergence: within 0.2 deg including heading. A frame with dt == 0 (same-ms catch-up) now integrates 0 instead of 0.02 s. Not seen in these captures, preventive.
- Verification done: firmware compiles. All existing `verify_*.mjs` and `verify_check_dataset.py` tests pass with the new dashboard. The closed-form settle was compared with the iterative one offline. Not done: flash, link rate, anything on the glove.

**Result of the updated v5 (serial log, 14:15 to 14:17):**
- Before the browser connects: `# link=down hz=50.0 read_us=3906 write_us=0 tx_fail=0 bus_rec=0 stuck=none failing=none`.
- After connecting: `# link=up mtu=527 ci_ms=15.0 hz=50.0 read_us=3906..3925 write_us=0 tx_fail=0 bus_rec=0 stuck=none failing=none`.
- So the loop holds 50 Hz while connected. The central granted a 15 ms interval and offered an MTU of 527, more than the 247 the firmware asked for. No tx failures, no stuck or failing sensors, no bus recoveries. Reading all six sensors takes about 3.9 ms.

**Problems (additional):**
- `write_us=0` while connected is suspicious (unverified). A real notify should take tens of microseconds. It may mean the dashboard had not subscribed to notifications yet, so the firmware skipped the writes. Until the dashboard RATE readout and a recorded CSV show about 50 Hz, the throughput fix is not verified.
- The motion tests were recorded with the wrong order (calibrate before Record), so the bias and zero the dashboard used cannot be recomputed from the CSVs.
- Data recorded before these fixes should not be used for ML training: 17 Hz frames, clipped gyro, off pinky accel and a wrong calibration zero.

**Self-healing dashboard (later the same day).** After the 50 Hz serial line I asked for the dashboard to fix drift on its own, using what the seven test captures showed, and to do it during live viewing so the hand looks smooth. Everything is in a "self-healing" block in `tools/handrig_dashboard.html` (copied byte-identical to `08-ble-wireless-dashboard/` and `Data/html/`, md5 `f1f6480f8a8cac7a6e2a8b99648b366a`). None of it changes the raw CSV.
1. **Stillness detector** per sensor. A sensor is still if its gyro is within max(3 °/s, 4x its calibration noise) of its own recent average on every axis, its accel direction is not creeping (fast average vs slow average differ by under 0.03 g, so a slow steady turn does not count), and |a| is within 0.1 g of 1. Time is measured in seconds of frame time, not frame counts. Counted in frames, "1 s" took 3 s at the 16.7 Hz of the motion tests and short end holds never qualified.
2. **Live gyro-bias tracking.** After 1 s still (and calibrated), the bias moves toward the current reading by 0.002 per frame (about a 10 s time constant at 50 Hz), only for residuals under 1.5 °/s. It fine-tunes warm-up drift and cannot swallow real motion.
3. **Adaptive snap-back.** After 0.2 s still, Madgwick beta rises from the slider value toward 1.0 in proportion to the tilt error (full at 20 deg, 2 deg gives 0.19, 0.5 deg gives about 0.12). A fixed big beta chatters once converged, because Madgwick steps a fixed beta along a normalised gradient. Tilt error is the angle between the filter's predicted up and the smoothed accel. Max correction is 2 * beta rad/s, 115 °/s. The beta slider now sets the user value.
4. **Auto re-zero on a flat hand.** When every non-bad sensor (hand required) has been still for 1 s or more, has tilt error under 2 deg, and its up is within 8 deg of the up it had at calibration, each sensor's zero is slerped toward its current orientation with a 0.4 s time constant (about 95 % in 1.2 s, no visible jump). This removes yaw drift, which a 6-DOF IMU cannot observe. Letter poses are not palm-down flat, so they do not trigger it.
5. **Trust and HEALTH readout.** Each sensor records the time of its last clipped gyro sample (|g| at or above 1990 °/s) and its last dropped frame. A sensor is trusted if neither happened since its last zero (calibration, Zero Orient or auto re-zero). The header has a new HEALTH cell: "—" disconnected, "slow link" under 40 Hz, "re-zero" while auto re-zero runs, "zero? index,pinky" for untrusted sensors, else "OK". Batch Capture now rejects a rep (flashes red, stays armed) if the link is under 40 Hz or any sensor is untrusted. The batch CSV format is unchanged.
6. **Display smoothing.** The drawn palm and finger rotations ease toward the true ones (slerp, 40 ms time constant, frame-rate independent). The fingertip curl uses the same easing. Display only: stored quaternions, cards and exports keep the unsmoothed values.
7. The Connect panel text now says to flash `09-firmware-hardening` (v5) and that v4 gyro reads 4x too large in this dashboard.

Verification so far:
- Replay of all seven motion-test CSVs in a Python port of the pipeline (with ACC_OFFSET and the closed-form settle). Displayed finger-vs-hand angle averaged over the last 1 s, in degrees, thumb/index/middle/ring/pinky, before then with healing:

| Test | Before | With healing |
|---|---|---|
| T0 still | 6.4 / 9.0 / 8.8 / 6.0 / 6.7 | 2.5 / 2.1 / 2.1 / 1.5 / 1.7 |
| T1 slow fist | 1.5 / 5.6 / 7.7 / 15.7 / 11.6 | 0.4 / 1.9 / 2.5 / 4.9 / 3.6 (re-zero still sliding when the CSV ended) |
| T2 fast fist | 26.8 / 106.4 / 70.0 / 78.8 / 162.0 | unchanged (hand never still for a full second at the end) |
| T3 each finger | 5.6 / 9.8 / 4.7 / 1.9 / 14.5 | 0.4 / 0.6 / 0.4 / 0.2 / 0.8 |
| T4 spread | 53.7 / 2.8 / 10.0 / 6.9 / 18.6 | 13.9 / 0.8 / 2.5 / 1.5 / 5.1 |
| T5 hand rotate | 3.4 / 4.1 / 5.5 / 3.3 / 1.3 | 0.4 / 0.1 / 0.4 / 0.4 / 0.3 |
| T6 mixed | 8.1 / 18.0 / 16.8 / 5.4 / 93.7 | 0.4 / 0.3 / 0.4 / 0.3 / 0.5 |

- Synthetic frames through the real dashboard code in a browser, no console errors. Pinky with its offset calibrates to |a| 0.998 and is not flagged. A 40 deg sideways drift on a flat hand fell to 2.2 deg after 2.5 s still (auto re-zero fired). A clipped burst over 2000 °/s (115 deg error) fell to 1.2 deg after 3 s, sensors untrusted after the clip and trusted again after re-zero. A held 90 deg curl stayed at 90 deg for 3 s (no re-zero). A slow 2 °/s turn changed the bias by 0.008 °/s or less.
- Existing `verify_*.mjs` tests: 0 failures.

**Live accel-offset learning and a stricter rep gate (later the same day).** The pinky offset above was a constant from an offline fit. The dashboard now learns it live (`learnAccOffset`, `solve4` in `tools/handrig_dashboard.html`, three copies byte-identical, md5 `08e1b8bf40872c65133454cf94b659da`).
- It is the same sphere fit as `tools/fit_accel_offsets.py`, running while the glove is worn. A sensor counts as "quiet" when its gyro is steady and its accel is not creeping, for 0.5 s. While quiet, one raw accel sample is added every 0.25 s to running sums of the least-squares normal equations (`|a|^2 = 2 a.b + c`, row `(2ax, 2ay, 2az, 1)`). No samples are stored. It refits every 10 samples after the first 60.
- "Quiet" and not "still", because "still" also wants |a| near 1 g, and a sensor with a big unknown offset never shows that.
- The fit is only trusted when the samples cover enough directions (two axes spanning at least 1.0 in unit-vector terms) and it is a clean sphere (radius within 0.05 of 1 g, radial rms under 0.03 g, computed from the sums: SSE = yy - 2 x.v + x.M.x, divided by 2r).
- Once trusted, the offset is applied and saved in the browser (localStorage key `gestura_acc_offset_v1`), so later sessions start from it. The old constants are the defaults. If the offset moves by more than 0.02 g, a status message asks to recalibrate.
- Verified in a browser with synthetic frames: pinky offset wiped to 0, 14 orientations held 5 s each. It learned (0.2512, 0.1906, -0.165) against the true (0.25, 0.19, -0.165), radius 0.9975, rms 0.006, after the 5th orientation. The other five sensors stayed within 0.002 g of zero. The value was saved. **Real-glove behaviour is unverified.** It needs about 15 s of total still time spread over different hand orientations.
- Batch Capture reps now also need every sensor's tilt error under 2 deg (filter settled), so a rep grabbed mid snap-back is rejected.
- Checks: all `verify_*` tests pass, 13/13 dataset checks pass.

**Problems (self-healing):**
- Fingers spread sideways while the hand lies flat palm-down look identical to gravity, so auto re-zero erases that spread too. T4 shows it: the thumb stays at 13.9 deg and the pinky at 5.1 deg after healing.
- T2 (fast fist) is unchanged. The recording ends before the hand is still for a full second, so nothing fires. This is a test-protocol gap, not proof that healing fails there.
- Not verified in numbers on the glove. It looks right by eye (user-observed). The thresholds (8 deg pose, 2 deg tilt, 1 s still, 0.03 g creep) are first guesses tuned on these captures, which were recorded at 17 Hz with ±500 °/s clipping, not on the new firmware.
- **Tried, not kept:** down-weighting the accelerometer when |a| is far from 1 g during fast moves (a standard trick). On the 7 recordings it changed nothing measurable and made the fast-fist index slightly worse (106 to 116 deg). The error in this data comes from clipping and yaw, not from linear acceleration. Revisit with clean 50 Hz, ±2000 deg/s data. See DECISIONS 2026-10-31.

**Next (added, in order):**
- Re-run the motion tests on the fixed system, with at least 3 s of stillness at the end of each.
- Move the hand through many orientations for about 30 s so the offset learner can confirm the pinky value.
- Then start Phase 8 data collection.

**Next (earlier list, still valid):**
0. Try it live. Move fast, lay the hand flat for 1 to 2 s, and watch HEALTH go "re-zero" then "OK". Check the 3D hand looks smooth and not laggy. Then re-run the motion tests with at least 3 s of stillness at the end of each, so the end-of-test numbers can be compared with the table above.
1. Confirm 50 Hz where it counts. Connect the dashboard, check that RATE shows about 50 Hz, record a short CSV and run `python tools/analyze_motion_test.py <csv>` (expect about 50 rows per second, median dt 20 ms). Also check that `write_us` becomes non-zero once the dashboard is subscribed. If the dashboard still shows about 16 Hz, the central or browser is the limit: shrink the frame or try another host (open decision, DECISIONS).
2. Re-run the motion tests with the new firmware and dashboard. Press Record before Calibrate so the 20 s hold is in the CSV, clap at the start, use one hand-axes setting for all tests. Run `python tools/analyze_motion_test.py <csv>` on each (default `--clip 2000`). Success: 50 Hz, 0 clipped, T1 and T2 return error under about 5 deg.
3. Re-fit `ACC_OFFSET` after the re-run, using the T5 hand-rotate CSV, to check the pinky offset is stable.
4. For ML: yaw relative to the hand still drifts by physics. Use gravity-referenced features plus the re-zero pose before each capture (DECISIONS 2026-07-14). Do not train on data recorded before these fixes.
5. Later: the guided calibration routine (open decision). It comes after the re-test, otherwise it calibrates against bad data. Background gyro-bias tracking from this item is done (self-healing block above).

**Ideas raised today, not built yet:**
- Keep sideways spread on a flat hand. Auto re-zero erases it (T4). Option: only re-zero yaw for fingers that were straight at calibration, or skip re-zero while the spread gesture is active. Needs the re-run data first.
- Revisit accel down-weighting during fast moves once there is clean 50 Hz, ±2000 °/s data (rejected for now, DECISIONS 2026-10-31).
- If a browser refuses the link requests and the rate stays near 17 Hz: shrink the frame or send fewer sensors per frame (open decision, DECISIONS).
- Hardware watchdog for a stuck SCL line (open decision).
- Find out why the pinky has its offset at all. It is the only genuine MPU-6050 (`WHO_AM_I` 0x68). Unverified.
- Re-tune the healing thresholds (1 s still, 2 deg tilt, 8 deg pose, 0.03 g creep) on the re-run data. They were tuned on 17 Hz, clipped captures.

**Known loose ends:**
- Two comments in `09_firmware_hardening.ino` are stale: the header says the frame works with either dashboard (the gyro scale changed, so the v4 dashboard reads v5 gyro 4x too small, and this dashboard reads v4 gyro 4x too large), and the MTU comment says the firmware never requests an MTU exchange (it now does). Code is correct, comments are not.
- Before and after per test, with an empty column for the re-run: `09-firmware-hardening/motion-tests/README.md`, "Before and after the fixes".

---

### 2026-10-31 | Docs pass: public ledger, plan and decision log

**Plan:** Bring the docs in line with reality and make the repo readable for someone seeing it for the first time.

**Achieved:**
- GENERAL_PLAN.md, DOCUMENTATION.md and DECISIONS.md are now tracked and public. Before this they were gitignored, so nobody on GitHub could see the actual engineering record.
- Fixed the phase status. Phase 7.5 had said "v3 not yet reflashed", but v4 has been streaming live since 2026-08-07. Phase 4 still described the first `delay(20)` sketch.
- Fixed a merged DECISIONS entry (the readback/watchdog decision had lost its heading) and added open decisions: the watchdog, the numpy pin and samples per letter.
- Replaced pre-reorg paths (`firmware/…`, `data/phase…`, `docs/media/…`) with the current stage folders, in the docs and in code comments.
- Rewrote the README for a first-time reader.

**Problems:** The Phase 8 drop-in folder from 2026-08-13 (`data/phase8_labelled_gestures/`) didn't survive the folder reorg. Its README now lives at `ml/future-data-collection-plan.md`. Exports will go in `ml/dataset/`, where `ml/**/*.csv` is already gitignored.

**Next:** The glove. Compile and flash v5, then work through the next-steps list in GENERAL_PLAN.md.

---

### 2026-10-19 | Phase 8/9 prep: dataset checker, kNN baseline, drift tool, v5 firmware (no hardware)

**Plan:** Do the work that doesn't need the glove: a quality gate for batch exports, a baseline classifier, the Phase 5 drift A/B tool, version pinning, and the firmware recovery bugs from the 2026-10-06 review.

**Achieved:**
- **`tools/check_dataset.py`** (+ `batch_io.py` loader). Fails on:
  - pre-2026-10-06 exports (not hand-relative)
  - NaN
  - quaternions that aren't unit length or have `qw < 0`
  - a sensor not reading ~1 g
  - raw values identical to the previous rep (frozen register)
  - duplicate rows
  
  It also prints a letters × sessions coverage table. `verify_check_dataset.py` plants each fault in synthetic data: **13/13 caught**.
- **`tools/make_synthetic_batch.py`**: fake exports in the exact format, with 10 rough letter shapes, random hand tilt and a per-session yaw error. Every file is marked `# SYNTHETIC` and the checker warns about it.
- **`tools/train_baseline.py`**: kNN on three feature sets. `quat` is the raw `q_rel`, `dir` is the finger direction in the hand frame, `curl` is only the palm-ward part. Synthetic only, not a glove result:
  - A random split scores 100 % at every yaw error, which shows how optimistic it is.
  - Leave-one-session-out for `quat` drops 100 → 96 → 87 % as yaw error goes 0 → 10 → 25°.
  - `curl` holds ~90 % but can never split U from V.
  
  That's the 2026-07-14 yaw tradeoff, now measurable.
- **`tools/analyze_drift.py`** fits a line instead of comparing the first and last sample, and has `--compare` for the bias on/off pair. Re-running the old capture corrected a number: finger 1 roll drift was 1.70 °/min by endpoints and **0.01** by line fit. Roll/pitch are all ≤ 0.35 °/min now, yaw is 0.03–2.2.
- **Toolchain versions** added to every stage README: Seeed nRF52 Boards 1.1.13, LSM6DS3 lib 2.0.7, MPU6050_light 1.2.1.
- **`09-firmware-hardening/` (v5):**
  - runtime I²C bus recovery
  - hand IMU re-init (the old loop started at sensor 1)
  - a hand read that can actually report failure
  - checked `bleuart.write()`
  - re-init for sensors whose reads keep failing
  - the MTU on the report line
  
  The BLE frame is unchanged.
- Reading the core's source showed two things. First, the hand IMU is on **Wire1**, not the finger bus, so v4's `tcaDisable()` before each hand read did nothing. Second, with SDA stuck low the nRF52 sees every ACK, so a jammed bus reads as zeros, not errors. The bus check now uses "all six axes exactly 0".
- Later the same day:
  - Firmware fixes 14–16: the full name in the scan response, the MTU logged from the exchange event, and `loop()` sleeping in `delay()` instead of spinning.
  - The dashboard got display options for the curl sign and for a left vs. right model hand. Both are display-only. Export and noise-check output is identical in every mode (checked in headless Chromium).
  - `verify_*.mjs`: 24/24 pass.

**Problems:**
- v5 is **not compiled or flashed**. An `arduino-cli` build stalled in library detection, and the retry was stopped when the machine ran low on memory.
- A stuck SCL hangs the nRF52 `Wire` driver forever, so only a hardware watchdog can recover from it. That's an open decision.
- `requirements.txt` pins numpy 2.2.6, but the scripts were tested on 2.5.3.
- The coverage target is read two ways: 90 per letter in the plan, 30 in the dashboard.

**Next:** Compile and flash v5 and run its test plan. On the dashboard, set the hand axes, curl sign and model hand on the glove. Then the first real Phase 8 session.

---

### 2026-10-06 | Phase 8: dashboard redesign and bug sweep

**Plan:** Redesign `tools/handrig_dashboard.html` as a clean black-and-white UI, and hunt for bugs across the code.

**Achieved:**
- **Redesign:** monochrome, 1 px lines, one monospace font, no gradients or shadows. State never depends on colour: ● LIVE / ○ NO DATA / ▲ CHECK / ▲ FAULT. X/Y/Z are solid/dashed/dotted everywhere. The 3D hand is a hidden-line wireframe. Checked at 1440, 820 and 390 px.
- **Document hygiene:** proper doctype (it was rendering in quirks mode), one font request instead of three, an SRI hash on Three.js r128, and a clear error if the library fails to load.
- **Bugs fixed (17):**
  - Reconnecting kept stale buffers, which showed a false loss %.
  - Listeners were added after notifications started, so the first packets were lost.
  - A failed connect left the GATT link up behind a "Connect" button.
  - Recording and calibration survived a disconnect.
  - A dropout latch froze a finger until recalibration.
  - Changing the hand axes kept a bias measured in the old frame.
  - Calibration finished on `requestAnimationFrame`, so it stalled in a hidden tab.
  - One exception in the refresh loop froze the UI.
  - The stuck detector was off by one (49 frames vs. 50).
  - A NaN could poison the filter.
  - **The big one: batch export wrote each sensor against its own zero instead of the hand-relative quaternion. Tilting the hand changed the finger features in the training data.** It now exports `conj(q_hand) ⊗ q_finger` with `w ≥ 0`, and the storage key was bumped so old and new rows can't mix.
- **Evidence:** the three `verify_*.mjs` scripts pass (24 checks). A headless-Chromium harness feeds synthetic 80-byte frames through the real parser and mocks `navigator.bluetooth`: 26 behaviour checks and 22 connection-flow checks pass.
- "Before" screenshot: `docs/media/dashboard-before.png`.

**Problems:**
- Not tested on the glove. Everything ran against synthetic frames and a mocked Bluetooth stack.
- Curl uses `|pitch|`. Which pitch sign means "curl" hasn't been measured.
- The model is a right hand (thumb at +X), but the glove is a left hand. Spread may look mirrored.
- Firmware bugs found but not fixed here, since they need a reflash. They became v5 (2026-10-19).

**Next:** Connect the real glove, calibrate, and check the curl sign and the thumb side. Take an "after" screenshot.

---

### 2026-08-13 | Phase 8: letter coverage grid and data folder

**Plan:** Show A–Z coverage in the dashboard and set up a folder and naming rule for exports.

**Achieved:**
- An A–Z grid on the 3D stage. Each letter shows its rep count and turns "done" at 30. It refreshes from the same function as the batch counter, so the two can't disagree.
- A drop-in folder and naming rule: `handrig_batch_<letter>_<session#>_<timestamp>.csv`.
- `tools/verify_batch_persist_js.mjs` covers the localStorage round trip and the grid math: 12/12 pass.

**Problems:** None. UI and tooling only.

**Next:** A real labelling session on the glove.

---

### 2026-08-12 | Phase 8: batch capture survives a crash

**Plan:** A tab crash between exports would lose every rep since the last one. For a 30+ rep session that's the biggest risk to collection.

**Achieved:**
- Batch rows are mirrored into localStorage after every capture and restored on page load.
- The backup is cleared once the CSV is exported.
- Labels are uppercased at capture time.

**Problems:** None.

**Next:** The coverage grid and the drop-in folder.

---

### 2026-08-11 | Phase 7.5: Batch Capture needs a GO noise check first

**Plan:** Make it impossible to collect training data before the noise floor has passed this session.

**Achieved:**
- `window.BatchGate`, a small state machine. A GO from the noise check unlocks Batch Capture until the next disconnect.
- A later NO-GO doesn't undo an earlier GO.
- The capture function re-checks the gate itself.
- Merged as two PRs to keep the diffs reviewable.
- `tools/verify_batch_gate_js.mjs`: 8/8 pass.

**Problems:** None.

**Next:** Keep the GO result across page reloads.

---

### 2026-08-10 | Phase 7.5: noise check moved into the dashboard

**Plan:** Port the GO/NO-GO checks from `tools/analyze_noise_baseline.py` into the browser, so a recording can be checked without exporting it first.

**Achieved:**
- `nbAnalyze(frames)`, pure math with no DOM or BLE. It checks dropped and stuck frames, per-sensor gyro bias and noise, and a 50 s minimum length.
- The thresholds are named constants copied from calibration, so the two can't drift apart.
- A "Noise Check" button shows a GO/NO-GO overlay with the same per-sensor breakdown as the Python script.
- `tools/verify_noise_baseline_js.mjs` tests three synthetic cases:
  - a clean 60 s capture → GO
  - a bit-identical capture → NO-GO
  - a 5 s capture → NO-GO

**Problems:** None. The only trap was the column order, which I checked against the parser's loop.

**Next:** Run a real 60 s still capture through both the browser and Python checks and confirm they agree.

---

### 2026-08-09 | Pre-Phase-8 checks (2/2): capture length

**Plan:** The noise baseline needs a 60 s still hold, but the script never checked how long the capture actually was.

**Achieved:** Under 50 s now forces NO-GO, however clean the stats look. Verified with a 10 s capture (now NO-GO, before it was a false GO) and a 60 s capture (still GO).

**Problems:** None.

**Next:** Run the full checklist on the glove.

---

### 2026-08-09 | Pre-Phase-8 checks (1/2): real exit code

**Plan:** `analyze_noise_baseline.py` must "print GO" before collection, but it always exited 0. The rule depended on someone reading the output correctly.

**Achieved:** It exits 0 on GO and 1 on NO-GO, so the gate can be scripted. Verified with a clean synthetic capture and a stuck one.

**Problems:** None.

**Next:** Check the capture length too.

---

### 2026-08-08 | Live dashboard: thumb geometry and calibration gate fix

**Plan:** Fix two bugs seen while wearing the glove. The 3D thumb looked wrong, and every finger showed a fixed 20–29° pitch right after calibration, even though the hand didn't move.

**Achieved:**
- **Thumb, four iterations.** I checked each one with coordinate math in a scratch Node script after the first guesses failed:
  1. The bend rotated about X, which lifted the thumb out of the hand's plane.
  2. Switched to Y, but with the sign backwards, so it flared away from the index.
  3. The anchor sat inside the solid palm box, so most of the segment was hidden.
  4. A two-axis kink cleared the box at the endpoint, but a 200-step walk along the segment found 22.8 % still buried.
  
  The final version is a straight segment anchored outside the box, with 7.5 % clipping at the tip only. See DECISIONS.md.
- **Calibration gate.** The pitch offset came from motion at the start of the 10 s hold getting averaged in.
  - My first fix rejected samples with raw gyro above 6 °/s. **That was a regression.** A still MPU-6050 reads its own bias, not zero, and the pinky's bias is over 6 °/s. It never got 5 good samples, stayed uncalibrated, and showed −105° roll on a still hand.
  - The real fix gates on deviation from each sensor's own rolling average.

**Problems:** Debugging 3D geometry from phone screenshots is slow. Several plausible fixes covered the wrong failure mode. Doing the math first is the default from now on. Also, before filtering on a threshold, check whether the value has a real non-zero baseline.

**Next:** Verify the thumb and the calibration gate on the glove across several calibrations, including moving on purpose during the hold.

---

### 2026-08-07 | Dashboard renamed Gestura, visual pass

**Plan:** A visual pass on the dashboard now that it's stable enough to demo.

**Achieved:**
- Renamed from "HandRig" to Gestura, the public product name. See DECISIONS.md.
- A copper brand palette driven from one token object, so CSS and the 3D scene can't drift apart.
- Redesigned the telemetry and finger cards.
- Fixed an invisible bar track and a grid-row clipping bug.
- BLE parsing, calibration and gesture logic are unchanged. The palette was later replaced by the monochrome redesign on 2026-10-06.

**Problems:** About 440 lines of CSS/JS. Real UI fixes and pure rebranding went into one change instead of two. Not re-checked on the glove after the restyle.

**Next:** Open it against the live glove and check that nothing broke under real data.

---

### 2026-08-07 | Phase 7.5: calibration settle fixed properly, curl readout, first gesture rule

**Plan:** Confirm the earlier settle fix, and add the missing curl readout and thumb fix.

**Achieved:**
- **The calibration settle bug was actually fixed this time.**
  - The hand model kept rotating slowly even with the glove dead still.
  - Waiting a fixed time after resetting the filter (600 ms, then 2.5 s) can't work, because convergence time depends on the smoothing slider and the pose.
  - `finishCalibration()` now runs `Madgwick.update()` ~40 times on the calibration gravity vector with β = 1 and grabs the reference immediately. **Confirmed working on the glove.**
- **Accel low-pass before fusion.** Raw accel noise (~0.02 g) was nudging the orientation every frame. An EMA on the accel input fixes it without adding lag to the output.
- **Accel shown relative to calibration.** Cards show `raw − accBias`. The filter still gets raw accel, because it needs gravity.
- **Curl readout per finger:** a bar, a percentage and a label, from the same relative pitch that drives the model.
- **Thumb rig fix.** The render loop was overwriting the static rest pose every frame. The rig is now split into a static parent and a live child.
- **First gesture rule**, on request: thumb bent up against the index. It's a threshold on the 3D rig's geometry, not ML. The thresholds are guesses.

**Problems:**
- The settle bug took two sessions and two wrong fixes. A fixed wait for a process whose speed depends on user settings is a gamble, not a fix.
- The pinky accel issue is still open.
- Only the settle fix was confirmed on the glove. The accel smoothing, curl readout, thumb fix and gesture rule are implemented but unverified.

**Next:** Test the unverified items on the glove. Inspect the pinky solder joint.

---

### 2026-08-07 | Phase 7.5: first live BLE session on the glove

**Plan:** Flash v4 and get a live BLE session working end to end. This was the first time the hardened firmware touched the glove.

**Achieved:**
- **BLE throughput collapse found and fixed.** The dashboard sat at 0 Hz with bad frames climbing.
  - The serial report line made it obvious. `read_us` (all six sensors) stayed flat at ~5.9 ms, while `write_us` (inside `bleuart.write()`) grew past 114,000 µs and `hz` fell from 50 to 8.3.
  - The sensors were never the problem. The BLE link was starved.
  - Fixed with `Bluefruit.configPrphBandwidth(BANDWIDTH_MAX)`, a relaxed connection interval (12, 24), and callbacks that log the MTU and interval.
  - **Confirmed live: ~47 Hz / 3.7 KB/s.**
- **Calibration settle, first attempt:** the wait went from 600 ms to 2.5 s. Not confirmed. It was replaced later the same day by the real fix above.
- **New issues from the live session:**
  1. **Pinky accel reads 25–28 % low** (`|a|` ≈ 0.72–0.77 g where 1.00 g is expected) in every pose. The per-axis ratios don't match one simple failure. The dashboard flags it `bad accel` and freezes that finger instead of drawing garbage. It's intermittent.
  2. **The thumb doesn't point sideways at rest.** The suspect is the cosmetic rest yaw fighting the real sensor rotation. Fixed later that day.
  3. **The hand drifts on its own when tilted palm-down.** It could be the same settle issue or a real weakness of Madgwick near vertical. Not separated yet.
  4. No curl readout yet. Added later that day.

**Problems:** Several new problems showed up at once. I avoided guess-fixing them all in one pass and kept them separate for controlled retests.

**Next:** Controlled tilt-drift test (flat vs. tilted, known β). Fix the thumb rest pose. Add the curl readout. Check the pinky wiring.

---

### 2026-07-25 | Phase 7.5: hardening the IMU path (v4) and the axis remap

**Plan:** Review the v3 fix before reflashing. It started with "would new IMUs fix the bad readings?" The answer is no: the chips are fine, the init was wrong.

**Achieved:**
- **New hardware wouldn't help.** Replacements from the same market would be the same 0x72 clones with the same bug. "Replace the part" was the tempting wrong answer.
- **`08-ble-wireless-dashboard/08_ble_dashboard.ino` rewritten as v4.** v3 wrote the right registers but ignored every `wReg()` return, so a NACK looked like success. That includes a NACKed mux select, which configures the wrong finger. v4 adds:
  - **Config readback:** `PWR_MGMT_1/2`, `GYRO_CONFIG` and `ACCEL_CONFIG` are read back and compared. An ACK proves something answered. A readback proves the chip stored the value.
  - **Runtime stuck watchdog:** 50 bit-identical frames (~1 s) means frozen. At ±4 g one LSB is 122 µg against ~20 LSB of noise, so a live sensor can't repeat exactly. That's stronger than the `|a| ≈ 1 g` check, **which the original stuck thumb passed.**
  - **A full reset for the 6500 family:** poll `DEVICE_RESET` until it clears, then signal path reset and `ACCEL_CONFIG_2`. That register is reserved on a genuine 6050, so one sequence serves both chips.
  - **Checked writes and mux selects**, 3× init retry, and **bus recovery** (9 clocks + STOP) for a slave holding SDA low.
  - **An honest validity mask.** v3 sent zeros with the valid bit still set, which told the filter that gravity had vanished.
  - **A frame checksum** (79 → 80 bytes). `0xAB` shows up inside the payload constantly, so one dropped byte could false-sync the parser.
  - Fixed `whoami[]` being indexed by mux channel instead of sensor id.
- **Axis remap implemented in the dashboard.** Fingers use the measured `(x, y, z) → (x, z, −y)`. For the hand, only "up = `−Z`" was measured, so the four valid options are in a dropdown. All remaps are proper rotations, so the gyro and accel use the same matrix.
- The dashboard validates the checksum, counts rejected frames, skips masked sensors, and calibrates bias in the remapped frame. CSV export stays in the raw sensor frame.

**Problems:**
- **None of this ran on hardware.** That's the same state v3 was left in. Two unverified versions stacked up, and that's worth saying plainly.
- The hand remap default is a guess and will probably need the dropdown.
- The 50-frame threshold and 2 s recovery interval are reasoned, not tuned.
- v4 firmware and the new dashboard must be used together because of the frame length change.

**Next:** Flash v4, read the boot diagnostic with the glove flat and still, and confirm 6/6 `OK`. Then connect the dashboard and set the hand axes.

---

### 2026-07-19 | Phase 7.5: BLE dashboard, and the clone-IMU init bug

**Plan:** With everything on the glove, stream all six IMUs over BLE and render the hand live in a browser, to prove the whole chain end to end.

**Achieved:**
- First BLE sketch: Nordic UART service, 79-byte binary frames, ~50 Hz. Plus `tools/handrig_dashboard.html`: a Three.js hand, live traces per sensor, and 10 s in-browser calibration.
- Got live data, but **4 of 5 fingers were garbage**, either flailing or frozen. I exported two CSVs ([`08-ble-wireless-dashboard/`](08-ble-wireless-dashboard/)) and went through them numerically instead of guessing:
  - `thumb_gx` stuck at exactly `246.0938` on every row.
  - `middle_ay` stuck at exactly `1.9688`.
  - `ring_gx` stepping by exactly `±0x2000` LSB per frame.
  
  Those are digital artifacts, not noise. Only the hand and the pinky were clean.
- **Root cause:** the four bad fingers are MPU-6500/9250 clones (`WHO_AM_I = 0x72`), and `MPU6050_light` never writes `PWR_MGMT_2`, so they boot half-awake. The pinky is a genuine 0x68.
- **Fix:** a raw-register driver (reset → wake → enable all axes → configure), plus a boot diagnostic that prints each channel's health within 2 s. That's v3.
- Confirmed the mux map on the glove: thumb = ch0, pinky = ch4.
- Measured the mounting axes. On the fingers, `−Y` points to the fingertip and `+Z` points up. The hand IMU reads `az ≈ −0.98 g` lying flat, so its Z is flipped compared to the fingers.
- Ruled out the tape. It's non-conductive and can't freeze a register, though it can still cause intermittent dropouts by straining wires.

**Problems:**
- It looked like a fusion or calibration problem ("garbage no matter how I calibrate"). The real fault was two layers below, in the I²C init. Lesson: when calibration "does nothing", check whether the raw bytes are real.
- The axis remap was designed but not implemented.
- v3 was written but not flashed this session.

**Next:** Flash v3, read the boot diagnostic, then implement the axis remap.

---

### 2026-07-18 | Phase 7: everything on the glove, 30-minute wear test

**Plan:** Mount the XIAO and mux on the glove, wire all five fingers with strain relief, and re-run the six-IMU sketch.

**Achieved:**
- All five finger sensors taped on: middle phalanx, and proximal phalanx for the thumb.
- The XIAO, mux and a mini breadboard as a wiring hub went on the wrist strap.
- **All six IMUs power up and read live on the glove.** Each finger module's LED is on and serial data streams. Photos in [`07-full-glove-assembly/`](07-full-glove-assembly/).
- **30-minute wear test passed.** Continuous data, no connection drop. I took the glove off and on several times during the test, which re-flexes every knuckle and re-seats every jumper. That's harder than one continuous wear. **Phase 7 closed.**

**Problems:**
- No capture file was saved from the wear test. It was watched live in the serial monitor.
- The wires are loose jumpers, not taped at every knuckle the way `hardware/WIRING.md` says. Surviving 30 minutes is a good sign, but fatigue builds over many sessions.
- The mux channel map wasn't re-checked against this exact wiring. That was done on 2026-07-19.

**Next:** Strain relief at every knuckle. Save a capture from the glove. Then build a wireless live view.

---

### 2026-07-17 | Phase 5: plot fix, mount angles explained, finger 5 anomaly

**Plan:** Plot the two Phase 5 captures as roll/pitch/yaw, and work out why the hand reads so differently from the fingers on the same breadboard.

**Achieved:**
- **Wrote `tools/plot_fusion.py`.** The first version plotted `millis` as roll (45,000° over 30 s). I fixed the column index.
- **The hand-vs-finger gap is mounting, not a fault.** The finger modules stand upright on their pins and the XIAO lies flat, so gravity lands on a different axis for each. A fixed +90° rotation about each finger's Y (checked with quaternion math) lines up fingers 1–4 with the hand, leaving 9–16° of real tilt.
- **Finger 5 doesn't line up** (yaw stays near 56°). Together with its higher gyro noise, that points to it sitting at a different angle in its slot.
- The correction is in `plot_fusion.py` (opt out with `--no-mount-correction`) and labelled as a visual aid only. Regenerated plots are in [`05-madgwick-fusion/`](05-madgwick-fusion/).

**Problems:** The plotting bug was caught before it reached the docs. The mount-angle theory comes from the data, not from measuring the rig.

**Next:** Check finger 5's seating, then mount on the glove at known angles.

---

### 2026-07-17 | Phase 5 second pass: seeded filter, two-stage β, first drift data

**Plan:** Improve the fusion sketch, then bench-test it with a still drift capture and a movement capture.

**Achieved:**
- **`05-madgwick-fusion/05_madgwick_fusion.ino`:**
  - Each filter is seeded from its own calibration accel (`quatFromAccel()`).
  - Two-stage β: 2.0 for 1.5 s, then 0.033.
  - The output grew to `millis,sensor_id,qw,qx,qy,qz,roll,pitch,yaw` with an optional raw tail.
- **Two bench captures** in [`05-madgwick-fusion/`](05-madgwick-fusion/), analysed with the new `tools/analyze_drift.py`:
  - `capture_01_movement.csv` (~29.5 s): fusion stays stable under motion. No NaNs, no stuck values.
  - `capture_02_drift.csv` (~31.5 s, still): the drift test.
- **Calibration finally works:** gyro bias std is 0.05–0.35 °/s on all six sensors, two orders of magnitude better than Phase 4 (38–84 °/s). The fix was holding the rig still, not code.
- **No dropouts** in either capture. Finger 2's dropout didn't reproduce.
- **Drift:** roll/pitch ≤ ~1.7 °/min, mostly under 0.5. Yaw is 0.2–2.1 °/min, which matches the predicted 6-DOF drift. *(Corrected 2026-10-19: these were endpoint numbers. A line fit gives roll/pitch ≤ 0.35, yaw 0.03–2.2.)*
- **Rate fell to ~84–86 Hz** from ~93.6, because of the filter math, the Euler conversion and the extra columns.

**Verdict on sensor health:** all six IMUs are electrically fine. Finger 2's dropout is "not currently reproducing", not "fixed". Finger 5 is the noisiest unit but not faulty.

**How to get clean readings from here:**
1. Keep `SUBTRACT_GYRO_BIAS=1`. Biases are significant, e.g. −6.98 °/s on finger 5's Y axis.
2. Calibrate with the rig on a table, not in the hand.
3. Re-check finger 2's contact before mounting.
4. Test finger 5 alone to see if its noise is the chip or the contact.
5. For 100 Hz, cut per-tick serial output first.

**Problems:** No same-session bias on/off pair yet. The drift run is 31.5 s, not several minutes. The rate drop isn't profiled.

**Next:** The bias on/off pair, a 5+ minute drift run, then the glove.

---

### 2026-07-17 | Phase 4 re-check and first Madgwick sketch

**Plan:** Confirm all six sensors still read, then write the first fusion sketch.

**Achieved:**
- Re-ran the Phase 4 sketch and saved `04-all-six-imus-raw/capture_03_full_session.csv` (~15 s). Analysed and plotted it.
- **All six sensors initialise and read.**
- **Measured rate ~93.6–93.7 Hz**, not 100. Six sequential mux reads cost more than the 10 ms budget.
- **The calibration window still wasn't still** (gyro std 38–84 °/s). That's the third capture in a row. It's a capture-discipline problem.
- **Finger 2 dropped out again**: all zeros for the last ~340 ms. The same channel in two sessions points to a loose jumper.
- **Wrote `05_madgwick_fusion.ino`**: one Madgwick filter per sensor, β = 0.1, untuned. The Madgwick vs. Mahony vs. complementary choice is in DECISIONS.md.

**Problems:** The fusion sketch isn't flashed yet. The rate shortfall and finger 2's contact are both still open.

**Next:** Flash the fusion sketch, check for NaNs and flat-hold behaviour, and measure drift.

---

### 2026-07-17 | Phase 4: full six-sensor sketch, a "still" capture that wasn't

**Plan:** Add the onboard IMU and the accelerometer, use the real serial format, and add calibration and rate measurement.

**Achieved:**
- Rewrote `04-all-six-imus-raw/04_all_imus_raw.ino` with:
  - all six sensors, accel + gyro
  - the `millis,sensor_id,ax,ay,az,gx,gy,gz` format
  - a `millis()`-scheduled loop
  - a 10 s still calibration with a bias table at boot
  - a periodic rate report
- Wrote `tools/analyze_calibration.py`. All six sensors read ~1.0–1.25 g, so they're alive.
- The full session log turned up as a file (5052 lines) and became `capture_02_full_session.csv`. I added `tools/plot_6imu_3d.py` (a static 3D path plus an animated GIF).

**Problems:**
- **The "still" window wasn't still.** The hand's gZ climbed from −10 to −35 °/s across 160 ms. That's real motion, so the bias table is useless.
- **Finger 2 (ch1), not finger 5, is the one that drops out.** It goes to `0,0,0,0,0,0` at 1468 ms and never recovers (801 of 841 samples). The GIF shows one arrow freezing while the others move.

**Things worth remembering:**
- **The onboard IMU isn't a mux channel.** I thought it shared the external bus and deselected the mux before reading it. (Later, on 2026-10-19, it turned out to be on its own internal bus, Wire1, so that deselect did nothing.)
- **Axis labels differ between chips, and that's fine.** On a flat rig, gravity lands on Z for the onboard chip and on X for the breadboard fingers. Fusion has to handle each sensor's own frame.
- **Exactly 0, 0, 0 accel means a dead sensor, not a calm one.** A live accelerometer always sees gravity. A self-heal retry for that case was designed but not added yet.

**Next:** Fix finger 2's contact. Mount everything on the glove following `hardware/WIRING.md`. Re-run this sketch on the glove. Capture a real still calibration.

---

### 2026-07-16 | Phase 3/4: mux bring-up, all five fingers read together

**Plan:** Bring up the PCA9548A and read all five finger sensors, then mount everything on the glove.

**Achieved:**
- Wired the PCA9548A on a breadboard:
  - XIAO D4/D5 → mux SDA/SCL
  - A0–A2 → GND (address `0x70`)
  - RST → 3V3
  - five MPU-6050s on channels 0–4, all at `0x68`
  
  Photos in [`04-all-six-imus-raw/`](04-all-six-imus-raw/).
- The sketch has a `tcaSelect()` helper and a boot `scanChannels()`. It found `0x68` on channels 0–4, nothing on 5–7, no cross-talk. **Phase 3 closed.**
- Streamed gyro from all five at ~50 Hz (`delay(20)` at this point) and saved `movement_test.csv`. Wrote `tools/analyze_multi_imu.py` and `plot_multi_imu.py`.
- **All five track the same motion.** Correlation vs. IMU0 is 0.999, 0.994, 0.986 and 0.975, dropping with position in the read order, which fits timing skew. Cross-sensor spread is 0.6–1.4 °/s.

**Problems:**
- Gyro only. No serial format yet, and the timestamps are host-side.
- No still baseline.
- The hand IMU isn't in the loop.
- The glove mount didn't happen.

**Next:** Add the hand IMU and accel, use the real format with a timed loop, and capture a still calibration.

---

### 2026-07-14 (evening) | Phase 2: first MPU-6050 alive, and it's a clone

**Plan:** Wire one MPU-6050 straight to the XIAO and get raw data out before adding the mux. One sensor is much easier to debug than five.

**Achieved:**
- Four wires plus AD0 → GND for address `0x68`. The diagram is in `hardware/WIRING.md`.
- Adafruit's library printed `Failed to find MPU6050 chip!`. An I²C scan found `0x68`, so the wiring was fine. Reading `WHO_AM_I` (`0x75`) directly gave **`0x72`**: an MPU-6500/9250 clone. Adafruit rejects anything but `0x68`.
- Switched to `MPU6050_light`, which worked immediately. Added an `i2c_scan` diagnostic so the finding is reproducible.
- The milestone sketch streams the full format at 400 kHz. There are two stripped-down diagnostic sketches for clean gyro-only and accel-only captures.
- `tools/plot_imu_3d.py` draws each capture as a 3D path. The accel points sit on a ~1 g sphere, so axes and calibration look right. The gyro swings to ±100–240 °/s on twists and returns near zero.

**Problems:** The clone could differ from a real MPU-6050 in register defaults. If fusion misbehaves, it's a suspect. It did turn out to matter, on 2026-07-19. The gyro keeps a couple °/s of bias after `calcOffsets()`.

**Next:** The mux, then all six sensors, then the glove.

---

### 2026-07-14 (later) | Repo audit: docs matched to reality, two risks found

**Plan:** A full audit of the architecture, the working sketches, the docs and the plan.

**Achieved:**
- **Yaw drift risk:** 6-DOF sensors have no yaw reference, so the yaw of `q_rel` drifts without bound. The plan is gravity-referenced features plus a re-zero pose (DECISIONS.md).
- **I²C budget:** five muxed reads at 100 kHz take ~10 ms, the whole 100 Hz budget. 400 kHz is required.
- **Toolchain:** the README claimed PlatformIO, but the reality was the Arduino IDE. Fixed, and logged in DECISIONS.md.
- Sketch 01 now uses the serial format. Removed a stale file and added WIRING.md pre-flight checks.

**Problems:** No media captured for Phase 1, and no versions recorded.

**Next:** Phase 2, with the pre-flight checks first.

---

### 2026-07-14 | Phase 1: first light, board and onboard IMU alive

**Plan:** Get the XIAO flashing, then read its onboard IMU.

**Achieved:**
- **The board didn't show up at first.** Double-tapping RESET puts it into UF2 bootloader mode, and then it enumerated.
- **LED test passes** ([`00-led-sanity-test/`](00-led-sanity-test/)): red → green → blue. The LED is active-LOW.
- **Onboard IMU reads** ([`01-xiao-onboard-imu/`](01-xiao-onboard-imu/)) with the Seeed LSM6DS3 library. It answers at **`0x6A`**, not `0x68`.
- Board specs and pinouts saved in `hardware/datasheets/`.

**Problems:** Only the bootloader scare.

**Next:** One external MPU-6050 on D4/D5.

---

### 2026-07-10 | Phase 0: repo scaffold

**Plan:** Set up a repo that documents every milestone from the first run.

**Achieved:** README, plan, decision log and ledger, numbered milestone folders, hardware docs, `tools/`, `ml/`. Remote: `github.com/PiyushPapaya/Cheirograph`.

**Problems:** The parts were soldered but not powered yet.

**Next:** Get the XIAO talking to the laptop.

---

### 2026-07-03 | Phase 0: parts arrive, soldering

**Plan:** Unpack, inspect and solder the headers.

**Achieved:** Headers soldered on the PCA9548A and all five GY-521 boards. No visible damage.

**Problems:** Reviews mention dead-on-arrival units. Unknown until power-on.

**Next:** Set up the repo.

---

### 2025-07-27 | Phase 0: planning and research

**Plan:** Settle the architecture before buying anything. The hard questions were five sensors on one address, noisy IMU data, and running ML on the MCU.

**Achieved:** A PCA9548A mux for the address collision, Madgwick for fusion, and Edge Impulse for on-device ML. Ordered the XIAO nRF52840 Sense, 5× MPU-6050, the PCA9548A, a left half-finger glove, and tape and ties for strain relief.

**Problems:** Some reviews mention dead MPU-6050 units on arrival.

**Next:** Wait for delivery, then inspect and test each part.
