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
