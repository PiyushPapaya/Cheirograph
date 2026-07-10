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
