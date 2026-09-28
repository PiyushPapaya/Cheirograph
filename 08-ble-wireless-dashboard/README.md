# 08 — BLE Live Dashboard

> *This folder's number is a flexible guide, not a permanent label. Rename or renumber as the real build dictates.*

**Phase:** 7.5 — Live wireless visualization (see `GENERAL_PLAN.md`)

**Goal:** Stream all 6 IMUs wirelessly over BLE and render live orientation + raw
accel/gyro in a browser dashboard — the practical proof that the glove works,
untethered, before committing to full data collection in Phase 8.

**Sketch:** `08_ble_dashboard.ino` — flash with Arduino IDE onto the Seeed
XIAO nRF52840 Sense. Requires the `Adafruit nRF52` board package (for
`bluefruit.h`) and the Seeed `LSM6DS3` library (for the onboard hand IMU).

**Companion tool:** `tools/handrig_dashboard.html` — open directly in Chrome
or Edge (desktop or Android; needs Web Bluetooth). No build step, no server.

---

## Why this firmware exists (v4, not v1)

The first two firmware attempts fed all 6 IMUs through the `MPU6050_light`
library and got garbage back for 4 of 5 fingers: exact-stuck register values
(e.g. `thumb_gx` pinned at `246.0938`, `middle_ay` pinned at `1.9688`) and
linear ramps with an exact `±0x2000` LSB step per frame. These are digital
init artifacts, not physical motion or noise — see the raw evidence in
`data/phase7_5_ble_diagnostics/`.

Root cause: the five finger modules are **MPU-6050 clones** — they answer
`WHO_AM_I = 0x72` (the MPU-6500/9250 family register value), not the genuine
MPU-6050's `0x68`. `MPU6050_light` talks to them (I²C ACKs fine) but never
runs a correct reset → wake → enable-all-axes sequence for that chip family,
so the clones boot half-asleep and return a fixed internal register pattern
instead of live sensor data. One finger (pinky, on mux channel 4) happened to
be a genuine MPU-6050 and worked from the start — that's what made this a
"4 out of 5 broken, always the same 4" pattern instead of "all 5 randomly
flaky," which was the clue that pointed at initialization, not wiring.

**Fix:** drop `MPU6050_light` for the fingers entirely and drive them with
raw I²C register writes:
1. `PWR_MGMT_1 = 0x80` — `DEVICE_RESET`, then wait.
2. `PWR_MGMT_1 = 0x01` — wake, clock source = gyro-X PLL.
3. `PWR_MGMT_2 = 0x00` — **enable all 6 accel+gyro axes.** This is the step
   the clones specifically need; without it they stay in whatever partial
   power state they booted into.
4. DLPF, sample-rate divider, and full-scale range registers.

The accel/gyro data register map (`0x3B`..`0x48`) is identical across the
MPU-6050/6500/9250 family, so once init is correct, a genuine 0x68 and a
0x72 clone are read exactly the same way — the fix is entirely in the
wake-up sequence, not the data path.

## What v4 changed (and why)

v3 wrote the right registers but **assumed every write landed**. Each item
below closes a path where a bad reading could still reach the dashboard
looking like real data.

| # | Change | The hole it closes |
|---|---|---|
| 1 | **Checked writes** — every I²C write's ACK is tested | A NACKed config write used to pass silently |
| 2 | **Checked mux select** | If the PCA9548A NACKed, v3 kept going and wrote finger N's config to whichever channel was still latched |
| 3 | **Full 6500-family reset** — poll `DEVICE_RESET` until it self-clears, then `SIGNAL_PATH_RESET` + `USER_CTRL.SIG_COND_RST`, plus `ACCEL_CONFIG_2` (`0x1D`) | A blind `delay(100)` may not cover reset; skipping the signal-path resets is how a chip ACKs happily while its output register stays frozen |
| 4 | **Config readback** — the four config registers are read back and compared after init | An ACK only proves *something* answered. A matching readback proves *this* chip stored it. This is what actually makes "init succeeded" trustworthy |
| 5 | **Init retry** — 3 attempts per channel | Marginal contacts get a second chance before being declared dead |
| 6 | **Runtime stuck watchdog** | The boot check only ever saw boot. A sensor that froze 10 minutes into a session was invisible |
| 7 | **I²C bus recovery** — bit-bang 9 clocks + STOP | A slave holding SDA low wedges the whole bus, so *all six* sensors read garbage — looks like total hardware failure, is a 20-line fix |
| 8 | **Honest validity mask** | v3 sent zeros for a failed read with the mask bit still set, so the dashboard fused a 0 g gravity vector as though it were real |
| 9 | **Frame checksum** | `0xAB` is not a rare byte — it appears inside int16 payload constantly. One dropped byte false-syncs the parser and produces a whole screen of plausible garbage |

`0x1D` is `ACCEL_CONFIG_2` on the 6500/9250 family and *reserved* on a genuine
MPU-6050, so the write is a harmless no-op there — which is why v4 can send
one sequence to both chip types without branching on `WHO_AM_I`.

### The stuck watchdog, in one paragraph

A live MEMS IMU always dithers. At ±4 g and 8192 LSB/g one LSB is 122 µg,
while the part's own noise floor is ~2–3 mg RMS — roughly **20 LSB**. Gyro
noise is a few LSB too. So the chance that all six axes repeat *bit-identical*
values 50 frames running is effectively zero for a working sensor, even one
sitting motionless on a table. If it happens, the output registers are frozen.
This is a strictly stronger test than "is |a| about 1 g" — the original stuck
thumb still reported a perfectly plausible ~1 g magnitude, which is exactly
why it took a CSV export to catch. On a trip, the channel is dropped from the
validity mask and re-initialised live (soft re-init, escalating to a hard reset
every 4th attempt, rate-limited to once per 2 s).

## Boot diagnostic

On every boot, before advertising starts, the sketch runs a per-channel check
and prints it to Serial (115200 baud). **Hold the glove flat and still.**

```
#   sid 1 who=0x72  |a|=1.01g  -> OK
#   sid 2 who=0x72  |a|=1.00g  -> STUCK (bit-identical, output registers frozen)
#   sid 3 who=0x72  |a|=0.98g  -> RAMP (constant per-frame delta = digital artifact, not motion)
#   sid 4           -> NOT FOUND (no ACK / init or readback failed)
# 5/6 sensors initialised.
```

- **OK** — dithers like a real sensor, `|a|` ≈ 1 g.
- **STUCK** — bit-identical across 24 reads. Frozen output register.
- **RAMP** — values change, but by an *exactly constant* delta every frame.
  Real movement never does that; this is the `±0x2000`-per-frame artifact from
  the original captures. Worth naming separately because it *looks* alive.
- **BAD ACCEL** — dithers fine but `|a|` isn't ~1 g while still.
- **NOT FOUND** — no ACK, or init/readback failed after 3 tries.

Read this once after every flash before trusting anything downstream. **If a
channel is still not OK here, the problem is now electrical** — cold solder
joint, shared pull-ups, wire fatigue at a knuckle, or wrong mux channel. The
firmware init path is verified by readback at this point, so it is no longer a
candidate.

During the session, the periodic status line reports the same thing live:

```
# link=up hz=50.0 read_us=8100 write_us=210 stuck=none
```

## BLE frame format (new — not the CSV serial contract)

This sketch streams over Bluetooth LE (Nordic UART Service), not USB serial,
so it uses a compact binary frame instead of the project's usual
`millis,sensor_id,...` CSV line (that CSV contract is unchanged for
USB-tethered sketches — see `tools/README.md`).

```
80-byte frame, little-endian:      <- v4: was 79 B, checksum byte added
[0] 0xAB              sync byte
[1] seq                uint8, wraps 0-255, used client-side for loss %
[2..5] t_ms             uint32, millis() at send time
[6] mask               bit i set => sensor i's data in THIS frame is real
[7..78] 6 × (ax,ay,az,gx,gy,gz)   int16 each, one block per sensor id 0-5
[79] checksum          XOR of bytes 0..78

accel int16 = g    * 8192.0   (±4 g range)
gyro  int16 = °/s  * 65.536   (±500 °/s range)
```

**The mask's meaning tightened in v4.** It used to mean "sensor i was found at
boot"; it now means "sensor i's data *in this frame* is real" — the read
succeeded and the stuck watchdog has not tripped. A clear bit means don't fuse
it, don't plot it. This matters because v3 zero-filled failed reads while
leaving the bit set, and a `(0,0,0)` accel vector fed into Madgwick is not a
neutral value — it is a claim that gravity has vanished.

Sensor id order is fixed: `0=hand(onboard), 1=thumb, 2=index, 3=middle,
4=ring, 5=pinky` — matches `hardware/WIRING.md`'s channel map (thumb=ch0 …
pinky=ch4). `tools/handrig_dashboard.html` decodes this exact layout; if you
change the frame, update the parser in the same commit.

## Sensor mounting axis convention

The firmware streams **raw sensor-frame** accel/gyro and always will — the
remap into the viewer's frame lives in `tools/handrig_dashboard.html`, so
every capture in `data/` stays re-interpretable if the convention changes.

Measured on the glove (2026-07-19):

- **Fingers:** sensor **−Y → fingertip**, sensor **+Z → up**. The viewer uses
  `+Z = forward, +Y = up, +X = right`, so the remap is
  `(x, y, z) → (x, z, −y)`. **Implemented in the dashboard as of v4** — before
  that, raw sensor data went straight into Madgwick, which is why curl looked
  roughly right (that rotation axis happened to line up) but spread/abduction
  did not.
- **Hand:** reads `az ≈ −0.98 g` lying flat palm-down, so sensor **+Z points
  down** ⇒ viewer-up = `−sZ`. *Which* horizontal sensor axis points at the
  fingers was never measured. Rather than hard-code a guess, the dashboard
  offers the four candidate remaps that all satisfy the one thing we did
  measure, in the **hand axes** dropdown. Tilt your hand forward and pick the
  one where the model tips forward too — a 10-second empirical check that
  beats an assumption baked into source.

All remaps are **proper rotations (determinant +1)**. That is not decoration:
the gyro is a pseudovector, and it transforms with the same matrix as the
accelerometer *only* when the determinant is +1. A mirrored remap would need
the gyro signs flipped separately, and the symptom would be fusion that fights
itself — orientation that snaps back instead of settling.

Leukoplast tape (used to mount every finger sensor) was ruled out as a cause
of the clone-init garbage — it's non-conductive and can't produce stuck
digital register values. It remains a real, separate risk for **intermittent**
dropouts if it pulls on a wire during flex; the boot diagnostic with the
glove flat and still is the way to tell the two failure modes apart (bad at
boot = init/electrical; fine at boot, degrades while worn = wire strain).

## Pre-Phase-8 checklist (run before any real labelled-data session)

Bad data collected now is bad data trained on in Phase 9 — cheaper to catch
here than to notice as an unexplained confusion-matrix problem later.

1. Flash the current firmware, glove flat and still, watch the **boot
   diagnostic** over Serial at 115200 — all 6 sensors must report `OK`
   (see `bootCheck()` in `08_ble_dashboard.ino`). Anything else (`STUCK`,
   `RAMP`, `BAD ACCEL`, `NOT FOUND`) is electrical — fix it before going
   further, don't try to average it away in software.
2. Connect the dashboard, run **Calibrate (20 s)** once, glove flat and
   still, to confirm every sensor calibrates clean (no red "bad" flag on
   any card).
3. Hit **● Record**, hold the glove flat and still for 60 s, **Export
   CSV**, then run:
   ```
   python tools/analyze_noise_baseline.py handrig_raw_<timestamp>.csv
   ```
   It must print **GO**. If it prints **NO-GO**, re-seat the flagged
   sensor's wiring / mux channel and repeat from step 1 — don't proceed
   to real collection on a NO-GO.
4. Only once that passes: use **Batch Capture** (label input + button in
   the dashboard) to collect the actual Phase 8 reps. Type a letter,
   start Batch Capture, hold each pose and press Space to save — it
   recalibrates for 5 s between reps automatically to keep bias drift
   from accumulating across a long session. Export the batch CSV and
   move it into `data/phase8_labelled_gestures/`.
