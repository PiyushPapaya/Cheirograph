# DECISIONS.md — Cheirograph

Every meaningful engineering fork — what was chosen between, what won, and why.
Keep entries short (~3 sentences each). Log a decision the moment it's made.

---

## Entry format

```
### YYYY-MM-DD | <Short title>

**Alternatives:** A vs. B (vs. C …)
**Choice:** What was chosen.
**Rationale:** Why. Include the trade-off honestly.
```

---

## Decisions

### 2026-07-17 | Fixed +90°/Y visualization correction for finger sensors, not a real mount calibration

**Alternatives:** (a) plot each sensor's raw absolute roll/pitch/yaw as-is, accepting that fingers and hand look wildly different because they're mounted at different physical angles on the bench; (b) apply a per-session, data-derived mount-offset correction (e.g. compute it from each capture's own seed-accel reading); (c) apply one fixed, hand-picked correction quaternion (+90° about each finger sensor's local Y-axis) to all finger sensors in `tools/plot_fusion.py`, purely for visual comparison.

**Choice:** (c), applied only in the plotting tool, clearly labeled as a rough diagnostic and explicitly not a substitute for Phase 6's real `q_rel = conj(q_hand) ⊗ q_finger`.

**Rationale:** The raw finger pitch sitting near -75° to -80° while the hand sits near 0° isn't a sensor fault — the GY-521 finger modules are plugged straight into the breadboard (standing upright on their pin legs) while the XIAO sits closer to flat, so gravity shows up on a different local axis for each. A single fixed +90°/Y correction (verified by hand with quaternion math, not guessed) brings fingers 1-4's roll and yaw into close agreement with the hand sensor, leaving a small residual pitch (9-16°, their real physical tilt) — good enough to make the plots readable side by side. It deliberately does **not** attempt a proper per-sensor mount calibration, because that's Phase 6's job once sensors are actually glove-mounted at known angles; doing it properly now, on a temporary breadboard rig, would be wasted precision. Trade-off / finding: the same correction does **not** line up finger 5, which stays off by roughly the same amount it was before — this is itself useful signal that finger 5 is mounted at a distinctly different angle than 1-4, not merely noisier as previously suspected (see DOCUMENTATION.md 2026-07-17).

---

### 2026-07-17 | Accel-seeded orientation + two-stage β, instead of identity start + fixed β

**Alternatives:** (a) start every filter at identity `(1,0,0,0)` with a single fixed β and let accel correction converge it over several seconds, (b) seed each filter's initial quaternion from its own calibration-window accel average (roll/pitch only — yaw is unobservable), with a temporarily high β right after seeding that drops to a lower steady-state value once converged.

**Choice:** (b) — `quatFromAccel()` seeds roll/pitch at the end of calibration, then `BETA_INIT = 2.0` runs for `CONVERGE_MS = 1500` ms before dropping to `BETA_STEADY = 0.033`.

**Rationale:** A single fixed β can't satisfy both ends of the trade-off: high enough to converge quickly from a bad start injects accelerometer noise into the steady-state estimate, low enough to be quiet at rest takes too long to snap in from identity if a sensor is mounted at a real tilt (all five fingers are, by design — resting near-horizontal, not flat). Seeding from the already-collected calibration-window accel average is free (that data is gathered anyway for the gyro bias table) and gives every filter a correct starting tilt instead of fighting toward one. Trade-off: two more tuning constants (`CONVERGE_MS`, `BETA_INIT`) than a one-β design, and if the calibration window itself wasn't still (as happened in earlier Phase 4 captures), the seed accel average would be wrong too — this fix doesn't help if the underlying capture discipline (hold still during calibration) fails.

---

### 2026-07-17 | Madgwick vs. Mahony vs. complementary filter for per-sensor fusion

**Alternatives:** Madgwick gradient-descent filter, Mahony explicit-complementary filter (PI controller on the same accel-vs-gravity error), or a simple fixed-weight complementary filter (`angle = a*gyro_integral + (1-a)*accel_angle`).

**Choice:** Madgwick, one independent instance per sensor (`firmware/05_madgwick_fusion/05_madgwick_fusion.ino`).

**Rationale:** Both Madgwick and Mahony solve the same problem (blend gyro integration with an accel-derived gravity reference) and would likely perform similarly well tuned; Madgwick was picked because it needs only one hand-tuned parameter (β) instead of Mahony's two (Kp and Ki), and its gradient-descent correction converges from a bad initial orientation faster than Mahony's proportional-integral controller — useful at boot, before any calibration pose is guaranteed. The plain complementary filter was rejected outright: fixed-weight blending doesn't reason about *how wrong* the current estimate is, so it either lags under fast motion or lets noise through at rest, and can't produce a proper quaternion without extra bookkeeping. Trade-off: Madgwick is a few more FLOPs per sample than a complementary filter — irrelevant here, since six filters at 100 Hz is well within the nRF52840's headroom.

---

### 2026-07-14 | MPU6050_light vs. Adafruit_MPU6050 for the finger sensors

**Alternatives:** `Adafruit_MPU6050` (+ Adafruit_Sensor + BusIO) vs. `MPU6050_light` by rfetick.

**Choice:** `MPU6050_light` for the finger IMUs.

**Rationale:** This wasn't a style preference — Adafruit's driver flat-out refused the module with `Failed to find MPU6050 chip!`. An I²C scan proved the board was wired and ACKing at `0x68`, so the bus was fine; the `WHO_AM_I` register (0x75) came back **`0x72`**, not the `0x68` a genuine MPU-6050 returns. The module is a clone (MPU-6500/9250 family is common on cheap "MPU-6050" breakouts), and Adafruit validates `WHO_AM_I` strictly, so it bails. `MPU6050_light` doesn't gate on that check, talks to the clone happily, and as a bonus bundles bias calibration (`calcOffsets()`) and tilt math in one small readable library. Trade-off / risk: it's a single-maintainer lib, and the clone may differ from a true MPU-6050 in register defaults or self-test — something to watch if fusion misbehaves later. A later switch is cheap since the sketch only touches `getAcc*/getGyro*`. **If more clone modules arrive, expect the same 0x72 and reach for MPU6050_light first.**

---

### 2026-07-14 | Arduino IDE now vs. PlatformIO from day one

**Alternatives:** Start on PlatformIO immediately (version pinning, `platformio.ini` per milestone) vs. start on the Arduino IDE and migrate later.

**Choice:** Arduino IDE for the bring-up phases; PlatformIO migration deferred until the milestone folders stabilise.

**Rationale:** The Seeed tutorials, board package, and LSM6DS3 library all target the Arduino IDE, which made first-flash friction minimal on day one — the priority was proving the hardware alive, not toolchain purity. The trade-off is weaker reproducibility for now; mitigated by recording the exact board-package and library versions in each milestone README until `platformio.ini` takes over that job.

---

### 2026-07-14 | Accept 6-DOF yaw drift; classify on gravity-referenced features + re-zero pose

**Alternatives:** (a) 9-DOF IMUs with magnetometers for absolute yaw, (b) accept 6-DOF and feed raw `q_rel` to the classifier hoping drift is slow, (c) accept 6-DOF but design features around the drift.

**Choice:** (c) — keep the 6-DOF sensors, but treat the yaw component of `q_rel` as untrusted: favour gravity-referenced features (relative pitch/roll), and plan a "flat hand" re-zero pose that snapshots and subtracts accumulated yaw offsets.

**Rationale:** Without a magnetometer, Madgwick has no absolute yaw reference, so each of the six filters drifts in yaw independently and the yaw of `q_rel` drifts without bound — this is physics, not a tuning problem. Finger *curl* (the dominant fingerspelling signal) is pitch relative to the hand, which gravity anchors and which does not drift; only abduction-like letter pairs (e.g. U vs. V) lean on yaw, and the re-zero pose covers those. Magnetometers were rejected because they behave badly centimetres from current-carrying glove wiring and would mean new sensors, new drivers, and a new BOM for marginal gain.

---

### Pre-build | PCA9548A mux vs. two I²C addresses (0x68 / 0x69)

**Alternatives:** Use the MPU-6050's AD0 pin to select between address 0x68 and 0x69 (gives two sensors per bus) vs. a PCA9548A 8-channel multiplexer.

**Choice:** PCA9548A mux.

**Rationale:** Five MPU-6050s cannot coexist on one I²C bus with only two available addresses — two buses would still leave one sensor unaddressable. The mux lets all five sit at 0x68 and be selected one channel at a time, keeps the wiring uniform, and requires only one extra component at a known address (0x70). The trade-off is an extra IC and the need to switch channels explicitly before every read; that overhead is trivial at 100 Hz.

---

### Pre-build | Madgwick (MCU-side) vs. MPU-6050 onboard DMP

**Alternatives:** Use the MPU-6050's built-in Digital Motion Processor (DMP) for fusion vs. run Madgwick on the XIAO MCU.

**Choice:** MCU-side Madgwick.

**Rationale:** The DMP requires undocumented register sequences and a specific I²C setup that becomes fragile through a mux; getting it to work reliably for five sensors in parallel would be a debugging sink. Running Madgwick on the MCU is transparent (source code readable and modifiable), identical for all six IMUs including the onboard one, and forces genuine understanding of the fusion math — which is exactly what this project is for. The trade-off is that the MCU does six filter updates per loop iteration; the nRF52840 at 64 MHz handles this comfortably inside a 10 ms budget.

---

### Pre-build | Middle-phalanx sensor placement vs. fingertip or base

**Alternatives:** Mount each finger IMU at the fingertip (distal phalanx), at the base (proximal phalanx / MCP joint area), or on the middle phalanx.

**Choice:** Middle phalanx.

**Rationale:** The middle phalanx sits past the PIP joint, so one sensor captures the combined MCP + PIP bend — the richest single-sensor curl signal available. The fingertip would capture the same bend but with a longer, harder-to-strain-relieve wire run, and the tip is used for touch. The base would only see MCP flex and miss most of the curl. Thumb is an exception: its proximal phalanx is used because of the CMC joint's range; the thumb has no true middle phalanx with a comparable bend arc.

---

### Pre-build | XIAO onboard IMU as hand reference

**Alternatives:** Dedicate a sixth MPU-6050 behind the mux as the hand-reference IMU vs. use the XIAO's onboard LSM6DS3.

**Choice:** XIAO onboard LSM6DS3.

**Rationale:** The onboard IMU is on the XIAO's internal I²C bus — always available, already mounted flat on the PCB (which mounts flat on the back of the hand), and requires zero extra wiring. Using a sixth MPU-6050 through the mux would consume a mux channel, add wiring, and need physical mounting on the hand-back. The trade-off is that the LSM6DS3 uses a different driver than the MPU-6050s and has slightly different noise characteristics; both run through the same Madgwick filter, so the interface is uniform.

---

### Pre-build | Left hand vs. right hand

**Alternatives:** Instrument the dominant (right) hand vs. the non-dominant (left) hand.

**Choice:** Left hand.

**Rationale:** Building on the non-dominant hand keeps the right hand free to solder, adjust, and operate the laptop keyboard and serial monitor during live testing — a significant ergonomic advantage when working alone. The trade-off is that ASL fingerspelling conventionally uses the dominant hand, so the dataset will not generalise to right-hand use without re-collection. This is accepted as a prototype constraint: the dataset is labelled, the hardware is built, and swapping hands would be a breaking change requiring full data re-collection. The non-dominant choice is fixed and documented here and in `CLAUDE.md`.
