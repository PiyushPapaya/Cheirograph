# hardware/BOM.md — Bill of Materials

All components used in Cheirograph. Update this file as parts are added or swapped.

| # | Part | Designator | Qty | Notes |
|---|---|---|---|---|
| 1 | Seeed XIAO nRF52840 Sense | U1 | 1 | MCU, BLE, onboard LSM6DS3 IMU on internal I²C (not behind mux) |
| 2 | MPU-6050 breakout (GY-521) | IMU1–5 | 5 | All wired at I²C addr 0x68; sit behind the PCA9548A mux |
| 3 | PCA9548A I²C multiplexer breakout | U2 | 1 | Addr 0x70; 8-channel; selects one MPU-6050 at a time |
| 4 | Half-finger glove (left hand) | — | 1 | Substrate; finger IMUs on middle phalanx, thumb on proximal phalanx |
| 5 | Solderless breadboard (mini) | — | 1–2 | Prototyping phase |
| 6 | Dupont jumper wires (M–F, F–F) | — | ~30 | I²C runs + power rails |
| 7 | Leukoplast medical tape | — | 1 roll | Sensor mounting + primary strain relief on glove |
| 8 | Cable ties (small, ~100 mm) | — | ~10 | Secondary wire anchoring at knuckle runs |
| 9 | Stranded wire (28–30 AWG) | — | ~2 m | For permanent glove wiring (replace Dupont wires once layout is confirmed) |

---

## Notes

- **Strain relief is not optional.** Wires crossing a knuckle will fatigue and fail. Anchor every run so no solder pad takes a flex.
- **3.3 V logic** throughout — the XIAO operates at 3.3 V; the MPU-6050 and PCA9548A both support 3.3 V. Do not use 5 V pull-ups.
- Pull-up resistors (4.7 kΩ) on SDA and SCL are typically provided on the GY-521 breakout boards; verify before adding external ones or the bus will be over-pulled.
