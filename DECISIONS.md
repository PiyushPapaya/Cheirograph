# Decisions

Every engineering fork in this project: what the options were, what I picked, and why. Each entry also says what the choice cost, because every option had a downside. Newest first.

For what happened session by session, see [DOCUMENTATION.md](DOCUMENTATION.md). For the roadmap, see [GENERAL_PLAN.md](GENERAL_PLAN.md).

## Index

| Date | Decision | Area |
|---|---|---|
| open | [Hardware watchdog for a stuck SCL line](#open-hardware-watchdog-for-a-stuck-scl-line) | Firmware |
| open | [Python dependency pin](#open-python-dependency-pin) | Tooling |
| open | [Samples per letter](#open-samples-per-letter) | Data |
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

### Open: hardware watchdog for a stuck SCL line

**Options:** (a) leave it. A stuck SCL hangs the glove until someone power-cycles it. (b) Enable the nRF52 hardware watchdog so a hung loop reboots the chip.

**Leaning:** (b), but only after the v5 SDA-to-GND test shows how the `Wire` driver actually behaves.

**Why it's open:** with SCL held low, the nRF52 `Wire` driver waits forever (no timeout in its loops), so no recovery code can run. A watchdog reboot fixes that. The cost is a dropped BLE link and a recalibration, roughly a 3 s gap. That's better than a dead glove halfway through a labelling session, but I want the test result first.

### Open: Python dependency pin

**Options:** keep `tools/requirements.txt` at numpy 2.2.6, or bump it to 2.5.3, the version the October scripts were tested on.

**Leaning:** bump to 2.5.3, since that is the version that has actually run the current tools.

### Open: samples per letter

**Options:** 30 reps per letter over 3 sessions (dashboard grid and `check_dataset.py` default), or 90 (30 × 3 sessions, the original plan).

**Leaning:** 30 first, then check leave-one-session-out accuracy. Go to 90 only for letters that need it. The plan already uses this. Confirm after the first real session shows how long a session takes.

---

## Decisions

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

**Why:** past the middle knuckle, one sensor sees both the base and middle knuckle bending, which is the strongest single curl signal. The fingertip sees the same thing but needs a longer wire and gets in the way of touch. The base misses most of the curl.

### Pre-build | Onboard IMU as the hand reference

**Options:** a sixth MPU-6050 behind the mux, or the XIAO's onboard LSM6DS3.

**Choice:** the onboard LSM6DS3.

**Why:** it's already flat on the PCB, on its own internal bus, with zero extra wiring. The cost is a second driver and slightly different noise. Both go through the same Madgwick code.

### Pre-build | Left hand

**Options:** dominant (right) or non-dominant (left) hand.

**Choice:** left.

**Why:** my right hand stays free to solder, type and watch the serial monitor while testing alone. The cost is that fingerspelling is usually done with the dominant hand, so the dataset won't carry over to a right hand without re-collecting.
