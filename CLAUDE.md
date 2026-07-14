# CLAUDE.md — Cheirograph

Standing context for Claude Code. Read this fully before acting in this repo.
Repo: https://github.com/PiyushPapaya/Cheirograph

## What this project is

**Cheirograph** (Greek *cheir* "hand" + *graph* "writing" — literally "hand-writing")
is a wearable **gesture-tracking glove**. It reads the orientation of each finger and,
ultimately, classifies static hand-shapes / the fingerspelling alphabet and turns them
into text or control signals.

This is a solo, hands-on learning project and portfolio **flagship**. The goal is not
only a working glove but a *legible record of the engineering* — the reasoning, the
dead-ends, and the skills demonstrated. Treat documentation as a first-class
deliverable, never an afterthought.

**Handedness: the glove is built for the LEFT hand** (non-dominant, for build/test
ergonomics). This is fixed for the dataset — all training data is collected on this hand,
and the sensor-to-finger map and wiring layout assume it. If this ever changes, it's a
breaking change: note it here, in the README, and re-collect data.

## How it works (architecture)

- **6 IMUs total.** Five MPU-6050 sensors, one per finger, plus the XIAO's onboard IMU
  used as a **back-of-hand reference**.
- Each IMU's raw accel + gyro is fused with a **Madgwick filter** into an orientation
  quaternion.
- A finger's meaningful pose is its orientation **relative to the hand**:
  `q_rel = conjugate(q_hand) ⊗ q_finger`. This makes the signal rotation- and
  position-invariant — waving the arm doesn't change it, curling a finger does.
- Relative quaternions → features → a small **TinyML classifier** (Edge Impulse) running
  **on-device** → output via **BLE HID** (type the recognized letter) or control signals.
- The read/fuse loop runs at a fixed **100 Hz**.

## Hardware

| Part | Role | Notes |
|---|---|---|
| Seeed XIAO nRF52840 Sense | MCU + hand-reference IMU + BLE | Onboard LSM6DS3 IMU on internal I²C; **not** behind the mux |
| 5× MPU-6050 (GY-521) | Finger IMUs | All at I²C addr **0x68**; sit behind the mux |
| PCA9548A | 8-channel I²C multiplexer | Addr **0x70**; selects which finger IMU is live before each read |
| Half-finger glove (left) | Substrate | Finger IMUs on **middle phalanx**; thumb on **proximal phalanx** |
| Leukoplast tape / cable ties | Mounting + strain relief | Wires **will** fatigue at the knuckles — anchor every run so solder pads never take the bend |

Hand IMU (the XIAO) mounts **flat and rigid** on the back of the hand — any wobble here
injects error into all five finger calculations, since everything is measured against it.

## Scope boundary (important — do not creep past this)

- **In scope:** fingerspelling / a fixed vocabulary of **static** hand-shapes.
- **Out of scope:** full sign-language translation. Real signing also encodes hand
  *location* relative to the body, *motion* trajectories, *two* hands, and *facial*
  expression — none of which an IMU glove captures. Keep targets finishable; never
  re-scope this toward "translate ASL."

## Repository conventions

**Four separate documentation lanes. Keep them distinct — never merge them.**

- **GENERAL_PLAN.md** — the roadmap: goal, scope, hardware, phase checklist, Gantt. Forward-looking, mostly static.
- **DOCUMENTATION.md** — the dated ledger. One block per session: *Date / Phase / Plan / Actually achieved / Problems & next*. Factual and honest, **including failures** — the honesty is the value.
- **DECISIONS.md** — every engineering fork: what was chosen between, what won, and why. ~3 sentences each.
- **docs/log/** — the narrative devlog, one entry per phase, with photos. The human story.

**Firmware layout — numbered milestone folders that are NEVER deleted or overwritten.**
The numbering is a *scaffold*, not a contract: rename, renumber, split, or insert folders
as the real work dictates. What's fixed is the *principle* — each meaningful milestone
gets its own self-contained, runnable folder that stays forever as evidence of the
journey. Accept minor duplication early; factor common code into `firmware/lib/` only when
it's stable and genuinely reused. Python (serial plotter, hand-skeleton viz, data capture)
lives in `tools/`.

## Operating conventions (keep these stable across the build)

- **Sensor ↔ mux-channel ↔ finger map.** Maintain one mapping and keep it in sync between
  firmware and `hardware/WIRING.md`. Suggested default: channel 0 = thumb, 1 = index,
  2 = middle, 3 = ring, 4 = pinky; hand IMU = XIAO onboard (no channel). Adapt to however
  you actually wire it, but document it in exactly one authoritative place.
- **Serial data contract.** Pick a stable line format early so `tools/` scripts can parse
  it without churn. Suggested: raw → `millis,sensor_id,ax,ay,az,gx,gy,gz`; fused →
  `millis,sensor_id,qw,qx,qy,qz`. One reading per line, CSV, newline-terminated. If you
  change it, update the parser in the same commit.
- **Quaternion convention.** Order `(w, x, y, z)`; document the coordinate frame and
  stick to it everywhere so relative-orientation math stays consistent.
- **Calibration.** Every IMU needs per-sensor gyro-bias (and ideally accel) offsets;
  compute at startup while still, and keep calibration code/data out of the hot loop.
  Drift almost always traces back to bias — check calibration before blaming the filter.
- **Reproducibility.** Pin library and toolchain versions (PlatformIO `platformio.ini`,
  Python `requirements.txt`). "Works on my machine" is not a milestone.

## Git & sync policy

- **Commit — automatic.** Make one meaningful local commit per increment, and **update
  DOCUMENTATION.md in the same commit as the code it describes**. Commit messages name the
  real thing (`fix gyro bias causing 4°/min drift`). Local commits are cheap and reversible
  — do them freely.
- **Tag — at milestones.** When a phase closes, tag it (`phase-02-sensors`) and write the
  devlog entry + drop media.
- **Push — on confirmation, not silently.** This is a public flagship repo, so pushing is
  a publish action. Do NOT push unprompted. Instead, at the end of each work session and
  immediately after tagging a milestone, summarize what's staged and say
  *"ready to push — want me to?"* — then push only on an explicit yes.

## Coding conventions

- Firmware: **Arduino framework.** Currently built with the **Arduino IDE** (`.ino`
  sketches); PlatformIO migration deferred until milestones stabilise — see DECISIONS.md
  (2026-07-14). Until then, record board-package + library versions in each milestone
  README. One sketch per milestone folder.
- Python 3, `pyserial` + `matplotlib` for visualization. Small, runnable scripts.
- Comment the non-obvious math — quaternion ops, fusion, channel switching. Clarity over
  cleverness.
- **Media discipline:** before changing something that works or fixing something broken,
  the author should capture the "before" (photo / short clip / serial trace). Remind them
  at natural moments; these captures are irreplaceable later.

## The rule that matters most

**Never produce code the user cannot reconstruct or explain.**

This repo's value depends on genuine understanding surviving a technical interview. When
writing anything non-trivial — especially sensor fusion, quaternion math, or the mux
switching — explain it well enough that the author could rewrite it from scratch. Teach,
don't just deliver. When a choice has real alternatives (Madgwick vs. Mahony vs.
complementary; onboard DMP vs. MCU-side fusion), surface the tradeoff so it can be
recorded in DECISIONS.md. **Understanding stays with the human.**

## Quick gotchas (hard-won; check these first)

- **Board won't show a COM port / won't flash** → double-tap the RESET button to force
  UF2 bootloader mode, then re-select the port. (Bit us on day one.)
- **Drift** → almost always gyro bias, not the filter. Recalibrate before rewriting fusion.
- **Relative *yaw* drifts even with perfect calibration** → expected physics, not a bug.
  6-DOF sensors have no yaw reference; gravity anchors only pitch/roll. Classify on
  gravity-referenced features and use the re-zero pose — see DECISIONS.md (2026-07-14).
- **100 Hz loop can't keep up with 6 sensors** → check the I²C clock first. At the default
  100 kHz, five muxed MPU-6050 reads ≈ ~10 ms of bus time alone; set 400 kHz
  (`Wire.setClock(400000)`) and re-verify once wiring moves onto the glove.
- **Firmware hangs on battery but works on USB** → a leftover `while (!Serial);` from a
  bench sketch. Fine for bench tests; must not be copy-pasted into glove firmware.
- **Onboard IMU won't init** → the LSM6DS3 is at I²C **0x6A**, not 0x68 (that's the MPU-6050s).
- **`Failed to find MPU6050 chip!` yet the I²C scanner clearly sees 0x68** → the board
  ACKs, so wiring is fine; the driver is rejecting the `WHO_AM_I` (reg 0x75) value. Cheap
  "MPU-6050" modules are frequently MPU-6500/9250-family clones — ours reports **0x72**,
  not 0x68. Adafruit's library refuses the mismatch; `MPU6050_light` is lenient and works.
  See DECISIONS.md (2026-07-14). Run `firmware/02_single_mpu6050_test/diagnostics/i2c_scan/`
  to confirm the address and read WHO_AM_I yourself before blaming wiring.
- **A finger's angle changes when you rotate your whole hand** → you're reading absolute,
  not relative orientation. Apply `conjugate(q_hand) ⊗ q_finger`.
- **I²C reads garbage / hangs** → check pull-ups, the active mux channel, and that you
  selected 0x70's channel before addressing 0x68.
- **A sensor works on the bench, dies on the glove** → wire fatigue at a knuckle. Strain-
  relief, stranded wire, anchor the run.
- **Classifier confuses two letters** → collect more data for that pair across sessions;
  it's usually data coverage, not the model.

## Working with this repo

- Use a strong model (e.g. Opus) for hard conceptual work — the fusion pipeline, drift
  math, architecture. Use a fast model (e.g. Sonnet) for routine sketches, viz, and docs.
- When a step is completed, prompt the author to update DOCUMENTATION.md, and DECISIONS.md
  if a fork was hit.
- Prefer small, incremental, runnable steps that mirror the phase order. Don't jump a
  layer ahead before the previous one is proven (sensors → mux → raw → filter → relative
  → glove → ML).
- Don't over-engineer. This is a solo learning build, not production.

