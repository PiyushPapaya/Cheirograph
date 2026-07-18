# hardware/WIRING.md — Wiring Diagram and Pin Map

**This is the single authoritative source for the sensor ↔ mux-channel ↔ finger mapping.**
Keep it in sync with the firmware. If you change a wire, update this file in the same commit.

---

## XIAO nRF52840 Sense pin assignments

| XIAO Pin | Signal | Connected to |
|---|---|---|
| 3V3 | Power | PCA9548A VCC, all GY-521 VCC |
| GND | Ground | PCA9548A GND, all GY-521 GND |
| SDA (D4) | I²C data (external) | PCA9548A SDA |
| SCL (D5) | I²C clock (external) | PCA9548A SCL |
| Internal SDA | I²C data (onboard) | LSM6DS3 (hand reference IMU) — do not expose externally |
| Internal SCL | I²C clock (onboard) | LSM6DS3 — do not expose externally |

---

## PCA9548A channel assignments

> **Complete this table once you wire the glove. This is the one authoritative mapping.**

| Mux Channel | I²C Address | Finger | Sensor placement |
|---|---|---|---|
| 0 | 0x68 | Thumb | Proximal phalanx |
| 1 | 0x68 | Index | Middle phalanx |
| 2 | 0x68 | Middle | Middle phalanx |
| 3 | 0x68 | Ring | Middle phalanx |
| 4 | 0x68 | Pinky | Middle phalanx |
| — | — | Hand (back) | XIAO onboard LSM6DS3 |

*Channels 5–7 are unused.*

---

## Wiring diagram

Full-glove schematic / photo to be added once the first physical layout is confirmed.
Placeholder: `docs/media/wiring_v1.jpg` — coming soon.

**Phase 2 — single sensor, direct (no mux), verified 2026-07-14:**

![MPU-6050 → XIAO direct wiring](./wiring_mpu6050_direct.png)

```
        MPU-6050 (GY-521)                 XIAO nRF52840 Sense
        VCC ──────────────────────────────► 3V3
        GND ──────────────────────────────► GND
        SDA ──────────────────────────────► D4 / SDA
        SCL ──────────────────────────────► D5 / SCL
        AD0 ──► GND   (sets I²C addr 0x68)
        INT ──► (not connected)
```

This is the same D4/D5 external bus the PCA9548A will occupy in Phase 3; the mux
inserts between this sensor and the XIAO without changing the XIAO-side pins.

---

**Phase 3/4 — PCA9548A mux + all 5 finger IMUs, bench breadboard, verified 2026-07-16:**

Photos: `docs/media/phase3-4_breadboard_top.jpg`, `docs/media/phase3-4_breadboard_angle.jpg`.

```
        PCA9548A                          XIAO nRF52840 Sense
        VIN ──────────────────────────────► 3V3
        GND ──────────────────────────────► GND
        SDA ──────────────────────────────► D4 / SDA
        SCL ──────────────────────────────► D5 / SCL
        A0, A1, A2 ──► GND   (sets mux addr 0x70)
        RST ──► 3V3          (active-low — hold high to keep the mux enabled)

        MPU-6050 #0..#4 (all identical, all AD0 -> GND -> addr 0x68)
        VCC ──────────────────────────────► 3V3 (shared rail)
        GND ──────────────────────────────► GND (shared rail)
        SDA ──────────────────────────────► mux SD0..SD4 (one channel each)
        SCL ──────────────────────────────► mux SC0..SC4 (one channel each)
```

This is a bench bring-up: sensors sit flat on a breadboard, referred to in
firmware/data as `IMU0`..`IMU4` (= mux channels 0-4). **No finger identity is
assigned yet** — that mapping (thumb/index/middle/ring/pinky) happens when
these move onto the glove in Phase 7; the table above is the plan for that
point, not the current wiring.

---

## Physical mounting (Phase 7 — glove)

- **Finger IMUs → leukoplast (fabric tape) only.** Needs to be rigidly coupled to the
  phalanx — any wobble injects noise into that finger's whole orientation signal. Tape
  can go directly over the MPU-6050 chip itself; it does not damage the IC (no pressure
  risk, no static risk from the tape).
- **XIAO + PCA9548A → velcro, or leukoplast if serviceability isn't a priority.** These
  need occasional removal (reflash the XIAO, recharge the battery); leukoplast is
  semi-permanent once stuck down hard. Velcro (hook on the board/enclosure, loop sewn or
  taped to the glove) trades a little rigidity for that removability.
- **PCA9548A has no orientation constraint** — it has no axes, so mount it however wiring
  is shortest: upstream pins (VIN/GND/SDA/SCL) facing the XIAO, channel pins facing the
  fingers.
- **Pin-header orientation on the finger breakouts**: mount so VCC/GND/SCL/SDA sit closest
  to the hand (shortest run back to the mux) and the two unused pins (AD0, INT) point
  toward the fingertip, out of the way.
- **IMU axis convention on the glove**: Y toward the fingertip (down the finger). X and Z
  follow from the board's fixed geometry once Y is chosen — don't try to align them
  independently. Verify empirically after taping: hold the hand flat, palm down, and check
  which raw accel axis reads ~-9.81 (that's local "down"); note the sign per sensor before
  trusting any relative-orientation math.
- **Leave slack in the finger→mux wire runs** and tack the slack loop down with one strip
  of tape — see strain-relief notes below; this is the #1 cause of a glove sensor that
  worked on the bench and died once mounted.

---

## Pre-flight checks (verify at first MPU-6050 power-on, Phase 2)

- [ ] **GY-521 LDO vs. 3.3 V supply:** most GY-521 boards route VCC through an onboard
  3.3 V LDO that expects 5 V in. Feeding 3.3 V *through* the LDO can undervolt the
  MPU-6050 depending on dropout. Verify these specific boards run reliably from 3.3 V
  (measure the MPU-6050 VDD pin); note the result here.
- [ ] **Master-side I²C pull-ups:** each GY-521 has pull-ups on its own (mux-channel)
  segment, but the XIAO→PCA9548A master segment needs its own — check whether the mux
  breakout provides them; add 4.7 kΩ to 3V3 if not.
- [ ] **Pull-ups do NOT parallel across GY-521s** — the mux connects one channel at a
  time, so only one board's pull-ups are ever active. Do not "fix" this.
- [ ] **I²C clock:** plan for 400 kHz (`Wire.setClock(400000)`) — required for the
  100 Hz × 6-sensor budget. Re-verify signal integrity once wiring moves onto the glove
  (long flexible runs at 400 kHz are where marginal edges bite).

---

## Strain relief notes

- All wire runs crossing a knuckle must be anchored with Leukoplast tape on both sides of the flex point.
- Use stranded 28–30 AWG wire for all glove runs; solid-core wire will fracture at the knuckle.
- No solder pad should take a bend directly — the anchor must be on the wire insulation, not the pad.
- After mounting, flex each finger 20× and check continuity before running firmware.

---

## Change log

| Date | Change | Changed by |
|---|---|---|
| 2026-07-16 | Added Phase 3/4 mux + 5-finger-IMU bench wiring (breadboard, no finger identity assigned yet). Mux channel switching verified via `scanChannels()` — 0x68 on channels 0-4, no cross-talk. | Piyush |
| 2026-07-14 | Added Phase 2 single-sensor direct-connect diagram (MPU-6050 → D4/D5, AD0→GND = 0x68). Verified on the bench. | Piyush |
