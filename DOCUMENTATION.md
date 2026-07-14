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

### 2026-07-14 (evening) | Phase 2 — first external MPU-6050 alive, raw accel + gyro plotted

**Plan:** Wire up one MPU-6050 straight to the XIAO (no mux yet) and get raw accel
and gyro out over serial. Goal was just to prove a single finger sensor works
before I add the multiplexer, since debugging one sensor is a lot easier than
debugging five behind a mux.

**Achieved:**
- Wired it with four lines — VCC→3V3, GND→GND, SDA→D4, SCL→D5 — and tied AD0 to
  GND so it sits at `0x68`. Sensor answered on the first try, no I²C hangs, no
  `0xFF` garbage. Diagram's in `hardware/WIRING.md` now.
- Went with the `MPU6050_light` library instead of the Adafruit one. It does the
  bias calibration (`calcOffsets()`) in a single call and the code is small
  enough to actually read, which is what I wanted. Wrote up the reasoning in
  DECISIONS.md.
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

**Problems & blockers:** The gyro doesn't quite return to a clean zero at rest —
there's a couple deg/s of leftover bias sitting there even after `calcOffsets()`.
Not a bug, that's the drift the Madgwick filter has to deal with later, but worth
noting it's visible this early. Still haven't recorded the exact library/board
versions (placeholders in the folder README) and no photo of the breadboard yet —
that media-discipline slip from Phase 1 is still open. Also left the bench-only
`while(!Serial)` in the milestone sketch on purpose, flagged in a comment.

**Next:** Phase 3 — bring in the PCA9548A mux. Address `0x70`, select a channel,
then reach the same `0x68` sensor *through* it. Run the WIRING.md pre-flight
checks (master-side pull-ups, 400 kHz) before I commit to any glove wiring.

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
