# Cheirograph

> *cheir* (χείρ) "hand" + *graph* (γράφω) "writing" — a hand that writes itself.

A wearable **gesture-tracking glove** that reads the orientation of each finger, fuses it with a Madgwick filter, and classifies static hand-shapes / the fingerspelling alphabet into text or control signals — entirely on-device.

---

## Demo

![Demo](docs/media/demo.gif)

*Coming soon — will be updated as the glove reaches a working state.*

---

## What it is

Cheirograph is a left-hand glove instrumented with six IMUs: five MPU-6050 modules (one per finger) multiplexed behind a PCA9548A, plus the XIAO nRF52840 Sense's onboard IMU as a rigid back-of-hand reference. Each sensor's raw accelerometer and gyroscope data is fused into an orientation quaternion with a Madgwick filter running at 100 Hz on the MCU. A finger's pose is expressed as its orientation *relative to the hand* — making the signal invariant to arm rotation. Those relative quaternions feed a small TinyML classifier (trained in Edge Impulse and deployed on-device) that outputs recognised letters over BLE HID.

This is a solo engineering project and portfolio flagship, built to understand every layer of the stack firsthand — from I²C bus multiplexing through quaternion math to on-device inference.

---

## How it works

```
MPU-6050 × 5 ──┐
                ├── PCA9548A mux ──┐
XIAO onboard ──┘                   ├── Madgwick fusion (100 Hz)
                                   │     → q_hand, q_finger[0..4]
                                   ├── Relative orientation
                                   │     q_rel = conj(q_hand) ⊗ q_finger
                                   ├── Feature vector (5 × quat)
                                   ├── TinyML classifier (Edge Impulse)
                                   └── BLE HID → typed letter / control signal
```

Key design choices:

- **MCU-side Madgwick** (not the MPU-6050 onboard DMP) — uniform, transparent, works through a mux.
- **Relative-to-hand quaternions** — waving your arm changes nothing; curling a finger changes everything.
- **Middle-phalanx placement** for fingers (proximal for thumb) — captures combined MCP+PIP bend, richest single-sensor curl signal.
- **Left hand** — non-dominant, keeps the right hand free for soldering and laptop during live testing. Fixed for the dataset.

---

## Hardware

| Part | Role | Notes |
|---|---|---|
| Seeed XIAO nRF52840 Sense | MCU + hand-reference IMU + BLE | Onboard LSM6DS3 on internal I²C — **not** behind the mux |
| 5× MPU-6050 (GY-521) | Finger IMUs | All at I²C addr **0x68**; sit behind the mux |
| PCA9548A | 8-channel I²C multiplexer | Addr **0x70**; selects one finger IMU at a time |
| Half-finger glove (left) | Substrate | Finger IMUs on **middle phalanx**; thumb on **proximal phalanx** |
| Leukoplast tape / cable ties | Mounting + strain relief | Wires fatigue at knuckles — anchor every run |

Authoritative wiring + sensor-to-finger map: [`hardware/WIRING.md`](hardware/WIRING.md).

---

## Repository structure

```
Cheirograph/
├── README.md                  — this file
├── CLAUDE.md                  — standing context for Claude Code
├── GENERAL_PLAN.md            — roadmap, phases, Gantt
├── DOCUMENTATION.md           — dated ledger of planned vs. achieved
├── DECISIONS.md               — engineering forks and rationale
├── .gitignore
├── LICENSE
│
├── firmware/                  — numbered milestone folders (never overwritten)
│   ├── 00_led_sanity_test/    — Phase 0: first flash, onboard RGB LED blink
│   ├── 01_xiao_imu_test/      — Phase 1: XIAO onboard IMU over serial
│   ├── 02_single_mpu6050_test/— Phase 2: single MPU-6050, direct I²C
│   ├── 03_mux_channel_test/   — Phase 3: PCA9548A mux bring-up
│   ├── 04_all_imus_raw/       — Phase 4: all 6 IMUs streaming @ 100 Hz
│   ├── 05_madgwick_fusion/    — Phase 5: Madgwick filter per IMU
│   ├── 06_relative_orientation/— Phase 6: relative quaternions + skeleton viz
│   ├── 07_full_glove/         — Phase 7: mounted on glove, strain-relieved
│   └── lib/                   — shared library code (only after it stabilises)
│
├── tools/                     — Python scripts: plotter, visualiser, data capture
├── data/                      — labelled training samples
├── ml/                        — Edge Impulse export, model artefacts
│
├── hardware/
│   ├── BOM.md                 — bill of materials
│   ├── WIRING.md              — authoritative sensor ↔ mux-channel ↔ finger map
│   └── datasheets/            — board references, pinouts, spec sheets
│
└── docs/
    ├── log/                   — narrative devlog, one entry per phase
    └── media/                 — photos, GIFs, serial traces
```

---

## Tech and skills exercised

Skills this project exercises, layer by layer (see [`GENERAL_PLAN.md`](GENERAL_PLAN.md) for which phases are actually complete):

- **Embedded C/C++** — Arduino framework on PlatformIO; real-time sensor read/fuse loop at 100 Hz.
- **I²C bus multiplexing** — PCA9548A channel switching; address collision resolution.
- **Sensor fusion (Madgwick filter)** — quaternion-based orientation from raw accel + gyro; gyro-bias calibration; coordinate frame discipline.
- **Real-time data visualisation** — Python / pyserial / matplotlib serial plotter; 3D hand-skeleton visualiser.
- **TinyML / on-device inference** — Edge Impulse pipeline; model quantisation; deploying to nRF52840.
- **BLE HID** — keystroke output over Bluetooth Low Energy.

---

## Build phases

The project is structured as eleven incremental, proven-before-advancing phases. Full roadmap, deliverables, and Gantt chart: [`GENERAL_PLAN.md`](GENERAL_PLAN.md).

---

## Getting started

> *This section will be expanded as phases land.*

**Toolchain (current — Arduino IDE):**
1. Arduino IDE with the Seeed board package — add
   `https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json`
   under **File → Preferences → Additional Boards Manager URLs**, then install
   **Seeed nRF52 Boards** via Boards Manager.
2. **Tools → Board →** *Seeed XIAO nRF52840 Sense*; select its COM port
   (double-tap **RESET** if the port doesn't appear).
3. Open the `.ino` in any `firmware/NN_*/` milestone folder and **Upload**.
4. Serial Monitor at **115200 baud**.

Full board reference, pinout, and library notes:
[`hardware/datasheets/XIAO_nRF52840_Sense.md`](hardware/datasheets/XIAO_nRF52840_Sense.md).

> A PlatformIO migration (for `platformio.ini` version pinning) is planned once the
> milestone folders stabilise — see `DECISIONS.md`. Until then, the board-package and
> library versions in use are recorded in each milestone README.

- Python 3 for `tools/` — dependencies pinned in `tools/requirements.txt` (lands with the first script).

---

## Scope

Fingerspelling / static gestures only. Not full ASL translation — see [`GENERAL_PLAN.md`](GENERAL_PLAN.md) for the scope boundary.

---

## License

MIT — see [`LICENSE`](LICENSE).
