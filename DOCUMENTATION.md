# DOCUMENTATION.md — Cheirograph

The **dated ledger** of planned vs. actually achieved, session by session.

Rules:
- One block per work session, newest at the top.
- Include failures — the honesty is the value.
- Update in the **same commit** as the code it describes.
- Never edit a past entry to look better than it was.

---

## Block template

```
---

### YYYY-MM-DD | Phase N — <short name>

**Plan:** What I intended to accomplish this session.

**Achieved:** What I actually got working (be specific — serial output, test result, video evidence).

**Problems & blockers:** What went wrong, what surprised me, what I had to look up.

**Next:** The very first thing to do at the start of the next session.
```

---

## Entries

*(Newest entry goes here, above this line.)*

---

### 2026-07-17 | Phase 5 visualization fix + mounting-angle explanation, finger 5 mount anomaly found

**Plan:** Visualize the two Phase 5 captures (drift + movement) as roll/pitch/yaw time series, then investigate why the hand (onboard) sensor's readings differ so much from the five finger sensors even though everything sits on the same breadboard.

**Achieved:**
- **Wrote `tools/plot_fusion.py`** — first version had a real bug: it plotted `millis` timestamps as if they were roll, making it look like roll ramped to 45,000° over 30 seconds. Fixed the column indexing.
- **Diagnosed the hand-vs-finger angle gap.** Raw finger pitch sits near -75° to -80° while the hand sits near 0° — not a sensor fault. The finger MPU-6050 breakout modules are plugged straight into the breadboard (standing upright on their pin legs) while the XIAO sits closer to flat, so gravity lands on a different local axis for each. Verified with actual quaternion math (not guessed): a fixed +90° rotation about each finger sensor's local Y-axis brings fingers 1-4's roll and yaw into close agreement with the hand sensor, leaving a small residual pitch (9-16°, each finger's real resting tilt).
- **Finger 5 does not follow the pattern** — the same correction leaves it out of alignment with fingers 1-4 (yaw stays near 56° instead of settling near 0). Combined with finger 5's consistently elevated gyro noise across every capture this session and last, this points at finger 5 being seated at a genuinely different angle in its breadboard slot, not just a noisier unit.
- **Added the correction to `plot_fusion.py`** as an opt-out (`--no-mount-correction`), clearly documented as a rough, hand-picked, visualization-only fix — not a substitute for Phase 6's real `q_rel = conj(q_hand) ⊗ q_finger`, which will handle this properly and per-session regardless of how each sensor happens to be mounted.
- Regenerated `docs/media/phase5_drift_rpy.png` and `phase5_movement_rpy.png` with the correction applied; both now show fingers 1-4 clustering close to the hand's baseline, with finger 5 visibly offset. Logged the correction as a design decision in DECISIONS.md (2026-07-17).

**Problems & blockers:** None beyond the initial plotting bug (caught before it made it into the docs). The mount-angle explanation is inferred from the data and physical reasoning about how breadboard-mounted breakout modules typically sit, not confirmed by physically measuring the rig's angles — worth a quick visual check next session.

**Next:** Before glove-mounting, physically check finger 5's breadboard orientation against fingers 1-4 to confirm the mount-angle theory. Once on the glove, sensors will be mounted at deliberate, known angles (flat on each phalanx) so this particular ~90° bench artifact goes away — but the underlying lesson (compare `q_rel`, never raw absolute angles) carries forward permanently.

---

### 2026-07-17 | Phase 5 second pass — seeded orientation, two-stage β, first bench drift + movement data

**Plan:** Replace the first Madgwick fusion sketch with an improved version (accel-seeded initial orientation, two-stage β, roll/pitch/yaw output), then bench-test it with a still-hold drift capture and a movement capture, and give a final read on whether the 6 sensors are healthy and how to best configure them going forward.

**Achieved:**
- **Replaced `firmware/05_madgwick_fusion/05_madgwick_fusion.ino`** with the improved version: each sensor's Madgwick filter is now seeded from its own calibration-window accel average instead of starting at identity (`quatFromAccel()`), uses a two-stage β (`BETA_INIT=2.0` for 1.5 s after calibration, then `BETA_STEADY=0.033`), and the serial contract grew to `millis,sensor_id,qw,qx,qy,qz,roll_deg,pitch_deg,yaw_deg` with an optional raw-column tail (`INCLUDE_RAW`). Logged the seeding/two-stage-β design choice in DECISIONS.md.
- **Captured and analyzed two bench sessions**, saved under `data/phase5_madgwick_fusion/` with a new `tools/analyze_drift.py` (computes per-sensor roll/pitch/yaw drift in deg/min from first-vs-last sample):
  - `capture_01_movement.csv` (~29.5 s, deliberate movement, `SUBTRACT_GYRO_BIAS=1`) — confirms the fusion runs stably under motion (no NaNs, no stuck values, all 6 sensors keep reporting).
  - `capture_02_drift.csv` (~31.5 s, held still) — the actual drift test.
- **Calibration quality is now trustworthy**: gyro bias std is 0.05-0.35 deg/s across all six sensors (from `capture_01`'s embedded boot log), two orders of magnitude better than every Phase 4 capture (std 38-84 deg/s) — this window was genuinely held still. Finger 5 remains the noisiest sensor of the six (std ~3x the others), a finding that's now repeated across every capture taken so far.
- **No sensor dropouts in either capture** — all 6 report OK at boot and hold matched sample counts through both sessions. Finger 2's intermittent all-zero dropout (seen in both Phase 4 captures) did not reproduce here.
- **Drift result**: roll/pitch essentially flat (≤ ~1.7 deg/min, mostly < 0.5) — expected, gravity-anchored by Madgwick's accel correction regardless of gyro bias. Yaw crept at ~0.2-2.1 deg/min depending on sensor — small, and matches the predicted unbounded 6-DOF yaw drift (DECISIONS.md 2026-07-14), not a bug.
- **Rate dropped to ~84-86 Hz** (from Phase 4's ~93.6 Hz) — the added Madgwick math, Euler conversion, and extra printed columns cost real time inside the 10 ms tick budget.

**Final verdict on sensor health:** all 6 IMUs (onboard hand + 5 fingers) are electrically sound and read correctly. The intermittent finger-2 dropout seen twice in Phase 4 has not reproduced across two more sessions, but with only one clean run it should be called "not currently reproducing," not "fixed" — a marginal breadboard contact doesn't announce itself on a schedule. Finger 5 is consistently the noisiest unit (higher gyro std, and previously an outlier accel magnitude that has since resolved) but is not faulty — just the weakest of the six, worth an isolated single-channel re-check before fully trusting it in later phases. The calibration-window-not-still problem that flagged three Phase 4 captures in a row is gone in this session — the fix was capture discipline (physically hold the rig motionless), not code, exactly as suspected.

**How to stabilize / pre-configure for optimal reading (going forward):**
1. **Keep `SUBTRACT_GYRO_BIAS=1`** — the measured biases are non-trivial (e.g. finger 5's y-axis bias is -6.98 deg/s), and leaving them uncorrected would dominate any real drift measurement.
2. **Hold the rig on a fixed surface during the 10 s calibration window**, not in-hand — every prior "bad calibration" finding traced back to hand tremor during that window, never a code fault.
3. **Re-check finger 2's mux-channel-1 contact** before glove-mounting — reflow or replace the jumper, since its failure mode (intermittent, not permanent) is exactly what a marginal solder/breadboard contact looks like, and strain relief on the glove won't fix a connection that's already borderline.
4. **Bench-test finger 5 in isolation** (single-channel, no mux) to determine whether its elevated noise is intrinsic to that unit or still a contact-quality artifact.
5. **If 100 Hz is required before Phase 6**, trim per-tick serial output first (each `Serial.print` blocks on UART) — that's the most likely place the extra ~10 Hz went missing between Phase 4 and Phase 5.

**Problems & blockers:** Still missing a proper `SUBTRACT_GYRO_BIAS` on/off **paired** A/B drift capture from the same sitting — the current drift number is compared against Phase 4's uncorrected noise floor, not a same-session control. The drift capture was also only ~31.5 s; the sketch's own comment asks for "several minutes," so the deg/min figures should be treated as directionally right but not final. The 84-86 Hz rate shortfall hasn't been profiled to find exactly which added step costs the most.

**Next:** Capture a same-session bias-on/bias-off drift pair, run one multi-minute (5+) still-hold drift test for a solid deg/min number, and re-check finger 2's physical contact before moving to glove-mounting. Once drift is confirmed acceptable, move on to Phase 6 (`q_rel = conj(q_hand) ⊗ q_finger`, re-zero pose, skeleton viz).

---

### 2026-07-17 | Phase 4 re-check + Phase 5 first pass — Madgwick fusion written, sensor health re-verified

**Plan:** Before moving forward, re-run the Phase 4 six-sensor sketch to confirm all 6 IMU connections are still good, then write the first Madgwick fusion implementation for Phase 5, with the intent of mounting all sensors on the glove soon and moving toward Phase 6 (relative orientation).

**Achieved:**
- **Re-ran `firmware/04_all_imus_raw/04_all_imus_raw.ino`** and captured a fresh ~15 s full session (`data/phase4_six_imu_capture/capture_03_full_session.csv`), analyzed with `tools/analyze_calibration.py` and re-plotted with `tools/plot_6imu_3d.py` (`docs/media/phase4_6imu_accel_3d_capture03.png`/`.gif`).
- **All 6 sensors initialize and read correctly** — no dead channel at boot.
- **Measured rate: ~93.6-93.7 Hz**, not the 100 Hz target, from the firmware's own `# rate_hz=` log lines — the six sequential mux-switch+read cycles cost more than the naive 10 ms tick budget allows. Recorded as an open item in `firmware/04_all_imus_raw/README.md`.
- **Calibration window (10 s) still wasn't genuinely still** — printed gyro bias/std table shows 38-84°/s std across all six sensors, an order of magnitude above a real at-rest noise floor. Third capture in a row with this same finding; it's confirmed as a capture-discipline problem (rig gets moved before/during the window), not a firmware bug.
- **Finger 2 (mux channel 1) had another intermittent dropout** — all-zero readings for the last ~340 ms of this session (vs. a full-session dropout in the earlier `capture_02`). Two different dropout windows on the same channel across two sessions points at a loose physical contact (breadboard jumper), not a code fault — worth watching once mounted on the glove, where proper strain relief should help.
- **Finger 5's earlier elevated accel magnitude (~1.23 g) did not reappear** in this run — likely was contact-quality noise in the previous session rather than a persistent hardware issue on that channel.
- **Wrote `firmware/05_madgwick_fusion/05_madgwick_fusion.ino`** — first real implementation, replacing the placeholder `main.cpp`. Reuses Phase 4's mux switching, per-sensor read, and boot-time gyro-bias calibration, and adds one independent Madgwick filter instance per sensor (gradient-descent IMU fusion, no magnetometer), emitting the project's fused contract `millis,sensor_id,qw,qx,qy,qz`. β left at 0.1 (Madgwick's published default), untuned. Logged the Madgwick-vs-Mahony-vs-complementary-filter choice in DECISIONS.md (2026-07-17).

**Problems & blockers:** Not yet flashed/bench-tested — this session's Phase 5 work is code only, no verification yet that the quaternions behave correctly under real rotation (hold-flat-near-identity, slow-360°-return-to-start). The 93.6 Hz rate shortfall and the intermittent finger-2 contact are both still open from Phase 4 and haven't been root-caused (mux/read timing profiling and physical contact fix, respectively). Didn't get to mounting sensors on the glove or starting Phase 6 this session — bench-level fusion needs to be verified first.

**Next:** Flash `05_madgwick_fusion.ino`, verify no NaNs, check the flat-hold-near-identity and slow-rotation-returns-to-start behavior, and record measured drift before/after calibration (the phase's actual deliverable). Then mount all 6 sensors on the glove with proper strain relief and start Phase 6 (`q_rel = conj(q_hand) ⊗ q_finger`, re-zero pose, skeleton viz).

---

### 2026-07-17 | Phase 4 — full 6-sensor sketch (accel + gyro + calibration), rest-window analysis flags a bad "still" capture

**Plan:** Extend the mux/5-finger sketch to the full Phase 4 target: read the
onboard hand IMU alongside all 5 fingers, add accelerometer, emit the real
serial contract, and add a still-calibration + rate-measurement routine.

**Achieved:**
- Rewrote `firmware/04_all_imus_raw/04_all_imus_raw.ino`: all 6 sensors
  (onboard LSM6DS3 + 5 finger MPU-6050s), accel + gyro, real
  `millis,sensor_id,ax,ay,az,gx,gy,gz` contract, `millis()`-scheduled ~100 Hz
  loop, a 10 s boot-time still-calibration window that accumulates per-sensor
  gyro mean/std and prints a bias table, and a periodic achieved-rate report.
- Captured a bench run and saved the opening calibration-window excerpt to
  `data/phase4_six_imu_capture/capture_01_raw.csv` (the full ~9.8 s capture
  was too large to transcribe by hand — see that folder's README).
- Wrote `tools/analyze_calibration.py` and ran it on the excerpt: all six
  sensors show sane accel magnitudes (~1.0-1.25 g), confirming they're alive
  and reading real gravity.

**Problems & blockers:**
- **The "still" calibration window wasn't still.** The hand sensor's gZ
  climbs monotonically from -10.43 to -35.00 deg/s across the 16 saved
  samples (~160 ms) — that's real angular acceleration, meaning the rig was
  being moved during the "Calibrating... hold still" phase. The large
  resting-gyro means seen on the fingers (15-25 deg/s) are an artifact of
  that motion, not their true zero-rate bias. **A genuinely motionless
  capture is still needed** before the bias table means anything.
- **Finger 5 is an outlier**: accel magnitude 1.246 g (vs ~1.0-1.02 g for
  the others) and gyro noise std 5-13 deg/s (vs 1-3 deg/s) — worth
  re-checking that sensor in isolation (loose connection on its mux channel
  is the first suspect).
- The full multi-thousand-line capture couldn't be persisted to the repo
  from a chat paste — only the calibration-window excerpt was saved at
  first. **Resolved within the same session**: the full session log turned
  up saved as a plain file (`datalog.txt.txt`, 5052 lines) rather than
  pasted text — moved into `data/phase4_six_imu_capture/capture_02_full_session.csv`
  and analyzed directly. That let the earlier excerpt-only findings above be
  checked against the complete run.

**Full-session findings (`capture_02_full_session.csv`, ~8.7 s, all 6
sensors) — supersede the excerpt guesses above:**
- **Finger 2 (mux channel 1), not finger 5, is the sensor that drops out** —
  and it's not intermittent: it goes to a permanent `0,0,0,0,0,0` at
  millis=1468 and never recovers for the remaining ~8.3 s of the run (801 of
  841 samples). Confirms the "exact zeros = dead registers, not noise"
  diagnosis from earlier in this session — a live MPU always carries ~1 g of
  gravity somewhere. Visible directly in the new
  `docs/media/phase4_6imu_accel_3d.png` (trajectory stops dead at the
  origin) and `docs/media/phase4_6imu_accel_3d.gif` (one arrow freezes while
  the other five keep swinging).
- **Confirmed at full scale**: the whole capture sits inside the firmware's
  declared 10 s calibration window, yet every live sensor's gyro std across
  the run is 25-102 deg/s — nowhere near a still-capture noise floor. The
  "hold still" instruction was not followed for this run; the bias table
  this sketch would print from it is not usable.
- Wrote `tools/analyze_calibration.py` (already existed) and added
  `tools/plot_6imu_3d.py` (new — static 3D trajectory + animated 3D vector
  GIF) to produce these findings and visuals.

**Harder problems worked through this session (worth remembering):**
- **Onboard IMU is a "trunk" device, not a mux channel.** The LSM6DS3TR-C
  lives on the same D4/D5 bus as the PCA9548A at a fixed `0x6A`, which
  doesn't collide with the mux (`0x70`) or the finger MPUs (`0x68`, only
  reachable *through* the mux). The fix: write `0x00` to the mux
  (`tcaDisable()`) to deselect every channel before touching `0x6A` — read it
  like any other bus device, no special-casing needed beyond that one write.
  Forgetting this deselect is a plausible-looking-data trap: whichever finger
  channel was last selected stays wired through, so the "onboard" reading is
  silently actually a finger's.
- **Axis labels legitimately differ between the onboard chip and the
  breadboard MPUs, and that's not a bug.** The onboard LSM6DS3 is soldered
  flat on the XIAO in its own orientation; the finger MPUs sit in a different
  orientation on the breadboard. On a flat, still rig this shows up as
  gravity landing on *different* accel axes per sensor (onboard: ~1 g on Z;
  fingers: ~1 g on X) — same physical "down," different local axis. Any
  fusion math later has to account for each sensor's own mounting frame, not
  assume a shared axis convention.
- **A sensor reading exact `0.0000,0.0000,0.0000,0.00,0.00,0.00` means the
  chip ACKed on the bus but its data registers are dead** (asleep or reset) —
  never a real reading, since a live MPU always carries ~1 g of gravity
  somewhere. Finger 5 (mux channel 3) dropped to this exact all-zero pattern
  mid-session, having worked earlier in the same run — the fingerprint of an
  intermittent physical contact (loose jumper on VCC/GND/SDA/SCL for that
  channel), not a code bug. Diagnosed a targeted software mitigation for
  next time: in the per-frame read, if `|ax|+|ay|+|az|` comes back under a
  small threshold, re-run that sensor's `begin()` and re-read once before
  moving on — a live-but-glitched sensor re-wakes within one frame instead of
  streaming zeros for the rest of the run. **Not yet added to the sketch** —
  flagged for the next firmware pass, with the caveat that a fully
  disconnected wire will just add a failed-init retry cost every frame, so
  watch the `# rate_hz=` line for a sag if this is leaned on instead of fixing
  the wire.

**Next session — move off the breadboard onto the glove:**
1. **Fix finger 2's channel-1 connection properly before mounting** —
   confirmed dead (permanent all-zero from millis=1468 onward) in the full
   session capture; reseat or re-solder (breadboard jumpers are exactly the
   kind of loose contact that caused today's dropout, and glove wiring needs
   to be more reliable than a breadboard, not less).
2. **Physically mount the XIAO, PCA9548A, and all 5 MPU-6050s on the glove**:
   finger sensors on the middle phalanx (thumb on proximal), hand IMU
   (onboard XIAO) flat and rigid on the back of the hand. Follow
   `hardware/WIRING.md`'s strain-relief rules — anchor every wire run on the
   insulation (not the solder pad) on both sides of each knuckle, stranded
   28-30 AWG wire only, flex-test 20x per finger before trusting continuity.
   Assign the real thumb/index/middle/ring/pinky-to-channel mapping in
   `hardware/WIRING.md` once wiring is physically committed (it's currently
   just placeholder `IMU0..IMU4` labels from the bench rig).
3. **Reconnect everything and re-run `firmware/04_all_imus_raw/04_all_imus_raw.ino`
   as-is first** — confirm all 6 sensors still read cleanly after the move
   from breadboard to glove before changing anything else. Wiring that
   worked flat on a breadboard is not guaranteed to survive being bent
   around knuckles; that's exactly what this re-test is for.
4. **Capture a genuinely still calibration run** (rig at rest, hand relaxed,
   nobody touching it) to finally get a trustworthy bias/noise table — this
   was blocked all of today's session by the rig moving during "hold still."
5. Once 6-sensor reads are solid on the glove: add the self-heal retry for
   dropped sensors, confirm the achieved rate from `# rate_hz=`, then this
   closes Phase 4 and Phase 7 (glove mount) together.

---

### 2026-07-16 | Phase 3/4 — mux bring-up + all 5 finger IMUs reading coherently

**Plan:** Get the serial bus working with all 5 finger sensors — bring up the
PCA9548A mux, read the data from the MCU (hand IMU) and all 5 finger sensors,
then finally mount all the components (the MCU, the 5 IMUs, and the mux/serial
bus) onto the glove.

**Achieved:**
- Wired the PCA9548A on a breadboard: XIAO D4/D5 → mux SDA/SCL, mux VIN/GND →
  3V3/GND shared rail, A0/A1/A2 → GND (mux address `0x70`), RST → 3V3 (held
  high, active-low). All five MPU-6050 clones sit on mux channels 0-4
  (SD0/SC0 .. SD4/SC4), every one with AD0 → GND (address `0x68` — identical
  across all five; the mux is the only thing that tells them apart). Photos:
  `docs/media/phase3-4_breadboard_top.jpg`, `docs/media/phase3-4_breadboard_angle.jpg`.
- Wrote `firmware/04_all_imus_raw/04_all_imus_raw.ino`: one `MPU6050_light`
  object reused across channels per sensor, a `tcaSelect()` helper that writes
  the one-hot channel byte to `0x70` before every access, and a boot-time
  `scanChannels()` sweep. That sweep found `0x68` on channels 0-4 with nothing
  on 5-7 and no cross-talk — mux switching confirmed working (closes Phase 3,
  no separate isolated-channel sketch needed).
- Streamed gyro (deg/s) from all 5 finger sensors live over serial at ~50 Hz
  (`delay(20)`-paced, not yet the target `millis()`-scheduled 100 Hz loop).
  Captured a hand-motion bench run — `data/phase3-4_five_imu_gyro/movement_test.csv`
  (41 samples, gyro only) — and wrote `tools/analyze_multi_imu.py` +
  `tools/plot_multi_imu.py` to check it, producing
  `docs/media/phase3-4_five_imu_movement.png`.
- **The data checks out:** all five sensors track the same physical rotation
  (Pearson r vs. IMU0 on the dominant Y-axis swing: IMU1 0.999, IMU2 0.994,
  IMU3 0.986, IMU4 0.975 — falling off slightly with "wiring distance" from
  IMU0, consistent with sequential-read timing skew, not a bad sensor).
  Cross-sensor spread (std across the 5 sensors per sample, averaged over the
  whole run) is small — gx 0.61°/s, gy 1.44°/s, gz 0.90°/s — confirming no
  dead, duplicated, or cross-talking channel.

**Problems & blockers:**
- This capture is gyro-only (no accel yet) and the sketch doesn't emit the
  project's `millis,sensor_id,ax..gz` serial contract — it prints a
  human-readable `IMUn [gx, gy, gz]` line instead, and timestamps in the saved
  CSV are the Serial Monitor's host-side receive time, not device `millis()`.
  Fine for this bring-up check, but the contract rework has to happen before
  this feeds into fusion.
- No clean "at rest" calibration baseline was captured this session — the
  bench-motion CSV never holds fully still, so the noise numbers above
  (frame-to-frame std in the calmest 9-sample stretch: gx 1.97°/s, gy 0.69°/s,
  gz 0.50°/s) are an upper bound, not a proper per-sensor bias table. A
  deliberate "sit still for 10s" capture is still needed.
- The onboard XIAO hand IMU (sensor 0) isn't wired into this sketch yet —
  Phase 4 isn't closed until it's reading alongside the five fingers in the
  same loop.
- The glove-mounting step (MCU + 5 IMUs + mux physically on the glove,
  Phase 7) did **not** happen this session — everything above is still on a
  breadboard. That's next, not done.

**Next:**
1. Add the onboard LSM6DS3 (hand reference, sensor 0) into the same loop as
   the five fingers.
2. Rework the print loop to emit the real `millis,sensor_id,ax,ay,az,gx,gy,gz`
   contract (add accel while at it) and switch from `delay(20)` to a
   `millis()`-scheduled loop; measure the real achieved rate from the
   timestamps rather than assuming 100 Hz.
3. Capture a deliberate still-calibration log for a proper per-sensor gyro
   bias table.
4. Only once the six-sensor bench read is solid: move the MCU, mux, and five
   IMUs onto the glove (Phase 7) with strain relief per `hardware/WIRING.md`,
   and re-verify — bench-solid isn't glove-solid until the wires have taken a
   bend.

---

### 2026-07-14 (evening) | Phase 2 — first external MPU-6050 alive, raw accel + gyro plotted

**Plan:** Wire up one MPU-6050 straight to the XIAO (no mux yet) and get raw accel
and gyro out over serial. Goal was just to prove a single finger sensor works
before I add the multiplexer, since debugging one sensor is a lot easier than
debugging five behind a mux.

**Achieved:**
- Wired it with four lines — VCC→3V3, GND→GND, SDA→D4, SCL→D5 — and tied AD0 to
  GND so it sits at `0x68`. Diagram's in `hardware/WIRING.md` now.
- Hit a wall first though: the Adafruit MPU6050 example just printed
  `Failed to find MPU6050 chip!` and halted. Ran an I²C scanner to check — it
  found a device at `0x68`, so the wiring was clearly fine. Then I read the
  `WHO_AM_I` register (0x75) directly and it came back **`0x72`**, not `0x68`.
  So the "MPU-6050" I have is actually a clone (the 0x72 points to the
  MPU-6500/9250 family), and Adafruit's driver checks WHO_AM_I strictly and
  refuses anything that isn't exactly 0x68.
- Swapped to `MPU6050_light`, which doesn't gate on that check — worked
  immediately. It also does bias calibration (`calcOffsets()`) in one call and is
  small enough to actually read. The whole fork is written up in DECISIONS.md, and
  I added an `i2c_scan` diagnostic sketch so the 0x68-present / WHO_AM_I=0x72
  finding is reproducible, not just a story.
- Milestone sketch `02_single_mpu6050_test.ino` streams the full contract line
  (`millis,sensor_id,aX,aY,aZ,gX,gY,gZ`) at 400 kHz. I also kept the two stripped
  diagnostic sketches I actually flashed to grab clean single-axis-set streams —
  `diagnostics/gyro_raw/` and `diagnostics/accel_raw/`. Arduino IDE only compiles
  one sketch per folder so each got its own subfolder.
- Captured both streams by hand-waving the sensor around then setting it still,
  saved them under `data/phase2_single_mpu6050/`, and wrote `tools/plot_imu_3d.py`
  to draw each as a 3D path coloured by time. PNGs are in `docs/media/`.
- The plots actually told me something. The accel one sits on a ~1 g sphere like
  it should (gravity is constant magnitude), with a tight cluster where I put it
  down at the end — that's the sanity check that calibration and axes are right.
  The gyro one loops way out to ±100–240 deg/s on the fast twists and comes back
  toward zero when I stop. First `requirements.txt` landed too (numpy, matplotlib
  pinned).

**Problems & blockers:** The clone chip is the one to keep an eye on — it works
now, but a clone can differ from a real MPU-6050 in register defaults, self-test,
or full-scale calibration, so if the Madgwick fusion behaves oddly later this is a
prime suspect. All five finger modules came from the same batch, so odds are
they're all 0x72 clones; I should scan every one when they go on. Separately, the
gyro doesn't return to a clean zero at rest — a couple deg/s of leftover bias even
after `calcOffsets()`. Not a bug, that's the drift the filter has to fight, but
good to see it this early. Library version now recorded (MPU6050_light 1.2.1);
board-package version still a placeholder, and still no breadboard photo — that
media slip from Phase 1 is open. Left the bench-only `while(!Serial)` in the
milestone sketch on purpose, flagged in a comment.

**Next:** the road from here is a straight line —
1. **Set up the bus** (Phase 3): bring in the PCA9548A mux at `0x70`, select a
   channel, and reach the same `0x68` clone *through* it. Run the WIRING.md
   pre-flight checks (master-side pull-ups, 400 kHz) first.
2. **Read everyone at once** (Phase 4): loop over all five finger sensors behind
   the mux *plus* the XIAO's onboard IMU (the hand reference), and stream all six
   at a steady 100 Hz. Scan each finger module as it goes on — they're probably
   all the same `0x72` clone.
3. **Put it on the glove** (Phase 7): once the six-sensor read is solid on the
   bench, mount everything onto the left glove, strain-relieve every knuckle run,
   and re-verify — bench-solid is not glove-solid until the wires have taken a bend.

---

### 2026-07-14 (later) | Repo audit — docs brought in line with reality, two risks surfaced

**Plan:** Full technical audit of the repo: architecture, the two working sketches, the docs system, and the forward plan.

**Achieved:**
- **Surfaced the yaw-drift risk** (the big one): 6-DOF sensors have no yaw reference, so the yaw of `q_rel` drifts unboundedly even with perfect calibration. Mitigation decided and logged in DECISIONS.md: gravity-referenced features + a "flat hand" re-zero pose. Phases 5/6 deliverables updated to include measured drift numbers and a time-dimension acceptance test.
- **Computed the I²C bus budget:** at the default 100 kHz, five muxed MPU-6050 reads ≈ ~10 ms — the entire 100 Hz budget. 400 kHz required; baked into Phase 4 and WIRING.md pre-flight checks.
- **Fixed the toolchain fiction:** README claimed PlatformIO + `pio run`; reality is Arduino IDE + `.ino`. README now documents the real workflow; the fork is logged in DECISIONS.md with PlatformIO migration deferred.
- **Aligned sketch 01 with the serial contract** (`millis,sensor_id,...` — was missing timestamp + id), flagged `while(!Serial)` as bench-only, deleted the stale `tree.md`, ticked Phases 0–1, added GY-521 LDO / pull-up pre-flight checks to WIRING.md, added five new gotchas to CLAUDE.md.

**Problems & blockers:** No devlog entry or media captured for Phase 1 yet — the media-discipline rule slipped in the very first phase. Board-package/library versions not yet recorded (placeholders left in `01`'s README).

**Next:** Re-flash sketch 01 to confirm the contract-format output, screenshot the serial trace + photo the LED test into `docs/media/`, fill in the version placeholders, write the Phase 1 devlog entry. Then Phase 2: single MPU-6050 on D4/D5 — run the WIRING.md pre-flight checks first.

---

### 2026-07-14 | Phase 1 — First light: MCU + onboard IMU alive

**Plan:** Electrically verify the Seeed XIAO nRF52840 Sense for the first time — get it
flashing, then read its onboard 6-DOF IMU. This is the first gate: is the board even alive?

**Achieved:**
- **Got the board flashing.** It initially would *not* connect / show up as a
  programmable port. Fix: **double-tap the RESET button** to force the nRF52840 into UF2
  bootloader mode — after that the port enumerated and uploads worked. Set up the Arduino
  IDE with the Seeed board package URL and installed the `seeed nrf52` boards.
- **LED sanity test passing** → new milestone folder `firmware/00_led_sanity_test/`
  (`.ino`). Cycles the onboard RGB user-LED red → green → blue, 500 ms each. Confirmed the
  full toolchain + USB + bootloader + MCU are good. Noted the LED is **active-LOW**
  (`LOW` = on).
- **Onboard IMU reading** → filled in `firmware/01_xiao_imu_test/main.cpp` with real code
  using the [Seeed_Arduino_LSM6DS3](https://github.com/Seeed-Studio/Seeed_Arduino_LSM6DS3)
  library. Streams `aX,aY,aZ,gX,gY,gZ` CSV at 115200 baud. Key detail: the onboard
  LSM6DS3TR-C answers at I²C **`0x6A`** (not `0x68`, which is the finger MPU-6050s).
- **Reference doc** → captured the full XIAO spec sheet, pin map, both pinout images
  (front/back), and the "which of the two Seeed libraries to install" note in
  `hardware/datasheets/XIAO_nRF52840_Sense.md`.

**Problems & blockers:** The board-not-connecting scare at the start (resolved by the
double-tap-RESET trick — worth remembering, it'll happen again). No IMU issues once the
right address (`0x6A`) and library were in place.

**Next:** Move to `firmware/02_single_mpu6050_test/` — wire up one external MPU-6050
(GY-521) on the D4/D5 I²C bus and confirm a single finger sensor reads at `0x68`, before
introducing the PCA9548A mux.

---

### 2026-07-10 | Phase 0 — GitHub repo scaffold

**Plan:** Create a well-structured, rigid GitHub repository where I can properly document progress, test firmware milestone by milestone, and share the build publicly as a portfolio piece.

**Achieved:** Full repo scaffold in place — `README.md`, `GENERAL_PLAN.md`, `DECISIONS.md`, `DOCUMENTATION.md`, seven numbered firmware milestone folders (`01`–`07`) with placeholder stubs, `hardware/BOM.md`, `hardware/WIRING.md`, `tools/`, `data/`, `ml/`, and `docs/log/` templates. Remote set to `https://github.com/PiyushPapaya/Cheirograph`. Initial commit made locally.

**Problems & blockers:** None with the scaffold itself. Components are in hand and soldered but not yet electrically verified — that's the next gate.

**Next:** Get the XIAO nRF52840 Sense connected to the laptop, install PlatformIO, find a suitable Arduino library for the onboard LSM6DS3, and run the first serial read to confirm the MCU and onboard IMU are alive.

---

### 2026-07-03 | Phase 0 — Component arrival and soldering

**Plan:** Unpack the ordered components, inspect for external damage, and solder the header pins on the PCA9548A mux and all five MPU-6050 breakout boards.

**Achieved:** Everything arrived. Soldered header pins on the PCA9548A (bus driver) and all five GY-521 / MPU-6050 modules. No signs of external shipping damage on any board.

**Problems & blockers:** Electrical functionality still unconfirmed — visual inspection and soldering done, but no firmware run yet. Some product reviews had mentioned units occasionally arriving dead or with cold joints from the factory, so this stays an open question until first power-on.

**Next:** Create the GitHub project structure so testing is properly documented from the first run.

---

### 2025-07-27 | Phase 0 — Project planning and component research

**Plan:** Form a rough project concept; decide where each sensor, MCU, and component would physically go on the glove; and think through the hard problems before ordering anything — specifically: the I²C address collision with five MPU-6050s all defaulting to `0x68`, noise in the raw IMU data and how to filter it, and how to ultimately deploy a trained ML model on the MCU. Then order the final component list.

**Achieved:** After several hours of research, settled on the architecture (PCA9548A mux to resolve the `0x68` collision, Madgwick filter for noise/fusion, Edge Impulse + on-device TinyML for classification) and confirmed component compatibility. Ordered the full BOM:

| Part | Role | Notes |
|---|---|---|
| Seeed XIAO nRF52840 Sense | MCU + hand-reference IMU + BLE | Onboard LSM6DS3 on internal I²C; **not** behind the mux |
| 5× MPU-6050 (GY-521) | Finger IMUs | All at I²C addr **0x68**; sit behind the mux |
| PCA9548A | 8-channel I²C multiplexer | Addr **0x70**; selects one finger IMU at a time |
| Half-finger glove (left) | Substrate | Finger IMUs on middle phalanx; thumb on proximal phalanx |
| Leukoplast tape / cable ties | Mounting + strain relief | Wires will fatigue at the knuckles — anchor every run |

**Problems & blockers:** Product reviews flagged that some MPU-6050 units occasionally arrive with factory defects or dead on arrival. No way to know until they're powered up.

**Next:** Wait for delivery; on arrival, inspect for external damage, solder headers, and test each component individually.
