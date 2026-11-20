# Plan

The roadmap for Cheirograph: goal, scope, hardware and the phase checklist. This file looks forward. What actually happened, session by session, is in [DOCUMENTATION.md](DOCUMENTATION.md). Why each design choice was made is in [DECISIONS.md](DECISIONS.md).

Last updated: 2026-11-20.

---

## Goal

A left-hand glove that reads the shape of the hand with six IMUs, fuses each sensor into an orientation on the device, classifies static fingerspelling shapes with a small on-device model, and types the letter on a paired device over Bluetooth.

The second goal is the record. Every decision is written down, every dead end is logged, and every layer is understood well enough to rebuild from scratch and explain in an interview.

---

## Scope

| In scope | Out of scope |
|---|---|
| Static hand shapes: the fingerspelling alphabet plus a few custom shapes | Full sign language translation |
| Left hand only | Two-hand signs |
| Inference on the nRF52840 | Cloud inference |
| Bluetooth HID keyboard output | Hand position and motion paths |

Real signing also uses where the hand is, how it moves, both hands and the face. Six IMUs on one hand can't see any of that, so the project stops at static shapes. That keeps it finishable.

---

## Hardware

| Part | Qty | Role |
|---|---|---|
| Seeed XIAO nRF52840 Sense | 1 | MCU, Bluetooth, onboard LSM6DS3 IMU as the hand reference |
| MPU-6050 (GY-521), in practice MPU-6500/9250 clones | 5 | One per finger, all at I²C `0x68`, behind the mux |
| PCA9548A I²C mux | 1 | Address `0x70`, picks one finger sensor at a time |
| Half-finger glove, left hand | 1 | Everything mounts on it |
| Mini breadboard, jumpers, Leukoplast tape | | Wiring hub and strain relief |

Pin map and channel map: [hardware/WIRING.md](hardware/WIRING.md). Parts list: [hardware/BOM.md](hardware/BOM.md).

**Handedness is fixed.** All training data is recorded on the left hand. Switching hands means re-collecting the dataset.

---

## Phase checklist

Each phase has its own folder at the repo root (`00-…` to `10-…`). Folder numbers and phase numbers don't line up one to one: stage folder `08` is Phase 7.5, stage folder `09` hardens the firmware for Phase 8, and stage folder `10` is touch detection, also part of Phase 8. Old folders are never deleted or overwritten.

**Legend:** ✅ done · 🟡 partly done · ⬜ not started

| Phase | What | Folder | Status |
|---|---|---|---|
| 0 | First flash, LED test | [`00-led-sanity-test`](00-led-sanity-test/) | ✅ 2026-07-14 |
| 1 | Onboard IMU over serial | [`01-xiao-onboard-imu`](01-xiao-onboard-imu/) | ✅ 2026-07-14 |
| 2 | One MPU-6050, direct I²C | [`02-single-mpu6050`](02-single-mpu6050/) | ✅ 2026-07-14 |
| 3 | I²C mux bring-up | [`03-i2c-multiplexer`](03-i2c-multiplexer/) | ✅ 2026-07-16 |
| 4 | All six IMUs raw | [`04-all-six-imus-raw`](04-all-six-imus-raw/) | 🟡 works at ~94 Hz, 100 Hz not reached |
| 5 | Madgwick fusion per IMU | [`05-madgwick-fusion`](05-madgwick-fusion/) | 🟡 bench-tested, closing test missing |
| 6 | Relative orientation | [`06-relative-orientation`](06-relative-orientation/) | 🟡 works in the dashboard, firmware is a stub |
| 7 | Mount on the glove | [`07-full-glove-assembly`](07-full-glove-assembly/) | ✅ 2026-07-18 |
| 7.5 | Live wireless dashboard | [`08-ble-wireless-dashboard`](08-ble-wireless-dashboard/), [`tools/`](tools/) | 🟡 50 Hz on v5 (2026-11-07 black box), open issues below |
| 8 | Labelled data collection | [`09-firmware-hardening`](09-firmware-hardening/), [`tools/`](tools/), [`ml/`](ml/) | 🟡 tooling built, no real data yet |
| 8 | Touch detection from IMU poses | [`10-touch-detection`](10-touch-detection/) | 🟡 built, ran once on the glove (2026-11-07), live detection scored 0 % |
| 9 | Train the classifier | [`ml/`](ml/) | ⬜ kNN baseline exists, synthetic data only |
| 10 | On-device model + Bluetooth HID | | ⬜ |
| 11 | Iterate and write up, tag `v1.0` | | ⬜ |

### Phase 4: all six IMUs raw

**Goal:** read all six sensors in one timed loop at a measured 100 Hz with no missed samples.

**Done:** all six sensors read in one `millis()`-scheduled loop at 400 kHz, using the `millis,sensor_id,ax,ay,az,gx,gy,gz` format, with a 10 s still calibration at boot.

**Open:** the measured rate is ~93.6 Hz, not 100. The likely cause is blocking `Serial.print` calls. The BLE firmware streams at 50 Hz anyway, so this doesn't block anything downstream.

### Phase 5: Madgwick fusion

**Goal:** one Madgwick filter per sensor, gyro bias calibrated at startup, and measured drift with bias correction on vs. off.

**Done:** the filter is seeded from the calibration accel and uses a two-stage β. Gyro bias std is 0.05–0.35 °/s. Roll/pitch drift is at most ~0.35 °/min and yaw drift is 0.03–2.2 °/min, both line-fit over a 31.5 s still capture. Yaw drift is expected without a magnetometer.

**Open:** a bias on/off pair from the same session, and one still run of 5+ minutes. `tools/analyze_drift.py A.csv --compare B.csv` is ready for both.

### Phase 6: relative orientation

**Goal:** compute `q_rel = conj(q_hand) ⊗ q_finger` for each finger. Rotating the wrist shouldn't change it, curling a finger should, and this has to hold after 5+ minutes of wear.

**Done:** the dashboard computes it in JS and exports it in the batch CSV, sign-pinned to `w ≥ 0`.

**Open:** the firmware version (`06-relative-orientation/main.cpp` is a stub), the "flat hand" re-zero pose for yaw drift, and the 5-minute wrist-rotation test on the glove.

### Phase 7.5: live wireless dashboard

**Goal:** move a finger on the glove and watch the same finger move in a 3D view, with no cable.

**Done:**
- v4 firmware flashed on the glove on 2026-08-07. It streams 80-byte frames over the Nordic UART service at ~47 Hz / 3.7 KB/s after the bandwidth fix. v5 holds 50 Hz (2026-11-07 black box: 15609 frames, 0 lost).
- Clone-IMU init bug found and fixed.
- In-browser Madgwick, calibration with a stillness gate and an instant filter settle, a GO/NO-GO noise check, and batch capture.

**Open, needs the glove:**
- The pinky accel "25–28 % low" is a zero-g offset, corrected and learned live in the dashboard. Root cause unverified.
- Hand axes and model hand: done 2026-10-31. The hand IMU mount is now measured live (tilt and in-plane angle), and the model is a left hand (DECISIONS 2026-10-31).
- Measure the curl sign.
- Tilted, palm-down hand drifts on its own. Retest flat vs. tilted at a known β.
- Not yet tried live: the October dashboard redesign, the curl readout, the thumb rest pose and the thumb-index gesture rule.

### Phase 8: labelled data collection

**Goal:** a balanced, checked dataset of static letter shapes.

**Target:** 30 reps per letter, spread over 3 sessions (10 per session). This is what the dashboard grid and `check_dataset.py` use by default. A stricter 90 reps per letter (`--goal-reps 90`) is the stretch goal once the first 30 train cleanly.

**Done:**
- Batch capture in the dashboard, crash-safe via localStorage.
- The A–Z coverage grid.
- The `check_dataset.py` quality gate (13/13 planted faults caught).
- A synthetic data generator.
- v5 firmware that recovers from bus faults at runtime.

**Open:**
- v5 is compiled and flashed (2026-10-31). Its fault-recovery paths are untested.
- No real session has been recorded yet.

Exports go in `ml/dataset/` using the naming rule in [ml/future-data-collection-plan.md](ml/future-data-collection-plan.md). CSVs under `ml/` are gitignored until the dataset is final.

### Phase 9: train the classifier

Edge Impulse, with 20 inputs (five relative quaternions) or the reduced `dir`/`curl` features. Compare it against the kNN baseline in `tools/train_baseline.py` and trust only the leave-one-session-out score. Export it as an Arduino library.

### Phase 10: on-device model + Bluetooth HID

Run the model on the XIAO and send the letter as a Bluetooth HID keystroke. Done when a recognised letter shows up in a text field on a paired phone or laptop.

### Phase 11: iterate and write up

Collect more data for letter pairs the model confuses, write the final devlog, record a demo video and tag `v1.0`.

---

## Next steps, in order

1. Clean slate: the dashboard work is committed and the status lines match the evidence (done 2026-11-20). Add a CI workflow that runs the offline checks.
2. Fix Batch Capture before recording anything: the between-rep recal is bias-only (DECISIONS 2026-11-16) and must not move the zero pose, auto re-zero must be off while a batch runs, and the export needs a header with dashboard version, accel offsets and bias.
3. Make `check_dataset.py` subtract the accel offsets from that header. Today it would reject the pinky.
4. One glove session to close the open loops: motion tests T0 to T6 with Record on before Calibrate, the 5-minute still run and the bias on/off pair for Phase 5, the curl sign, and the flat-repeat test for the hand IMU mount. Add the posture test from `docs/log/specs/S03-calibration-posture-test.md`: `tools/analyze_posture.py` and `09-firmware-hardening/motion-tests/session-checklist.md` are ready.
5. v5 fault tests from [`09-firmware-hardening/README.md`](09-firmware-hardening/README.md), including the SDA-to-GND short. Then add the watchdog.
6. The one-session touch test in [`10-touch-detection`](10-touch-detection/). Pick the pose-class detector or stop. Do not spend more than one session.
7. Record a 20 to 30 s clip of the glove driving the 3D hand for the README.
8. First real Phase 8 session with the 9-letter starter set. Run `check_dataset.py` on the export before anything else.
9. Two more sessions on other days. Run `train_baseline.py` and compare the feature sets, leave-one-session-out only.
10. Port fusion and features to C++ in a new stage folder and check it against the dashboard on recorded frames.

---

## Timeline

| Period | What happened |
|---|---|
| 2025-07 | Research and parts ordered |
| 2026-07-03 → 07-14 | Soldering, repo scaffold, Phases 0–2 |
| 2026-07-16 → 07-18 | Mux, six IMUs, Madgwick, glove mount and wear test |
| 2026-07-19 → 08-13 | BLE dashboard, clone-IMU fix, first live sessions, Phase 8 tooling |
| 2026-10-06 → 10-19 | Dashboard redesign, bug sweep, dataset checker, kNN baseline, v5 firmware |
| Next | Glove verification, first real dataset, classifier |

TU Munich starts in October 2026, so work happens in blocks. The order above matters more than the dates.
