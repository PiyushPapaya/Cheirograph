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

> Schematic / photo to be added here once the first physical layout is confirmed.
> Placeholder: `docs/media/wiring_v1.jpg` — coming soon.

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
| *(first entry goes here)* | | |
