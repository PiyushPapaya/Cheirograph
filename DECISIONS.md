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
