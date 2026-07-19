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

## Why this firmware exists (v3, not v1)

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

## Boot diagnostic

On every boot, before advertising starts, the sketch runs a per-channel
liveness check and prints it to Serial (115200 baud):

```
#   sid 1 who=0x72 |a|=1.01g accel_range=0.014  -> OK
#   sid 3 who=0x68 |a|=1.97g accel_range=0.000  -> BAD (|a| not ~1g: stuck/asleep/dead)
```

- **OK** — accel magnitude near 1 g and the reading actually dithers between
  samples (a real sensor never returns bit-identical values 10 times running).
- **BAD** — `|a|` isn't ~1 g. Stuck/asleep/dead at the register level.
- **SUSPECT** — `|a|` looks plausible but the value never moves at all across
  10 reads — bit-identical, so it's a frozen register, not a live sample.

Read this once after every flash before trusting anything downstream. If a
channel is still `BAD`/`SUSPECT` here (glove flat, untouched), the problem is
electrical (cold solder joint, shared pull-ups, wire fatigue at a knuckle),
not firmware — the clone-init fix has already been applied by this point in
`setup()`.

## BLE frame format (new — not the CSV serial contract)

This sketch streams over Bluetooth LE (Nordic UART Service), not USB serial,
so it uses a compact binary frame instead of the project's usual
`millis,sensor_id,...` CSV line (that CSV contract is unchanged for
USB-tethered sketches — see `tools/README.md`).

```
79-byte frame, little-endian:
[0] 0xAB              sync byte
[1] seq                uint8, wraps 0-255, used client-side for loss %
[2..5] t_ms             uint32, millis() at send time
[6] mask               bit i set => sensor i present this frame
[7..78] 6 × (ax,ay,az,gx,gy,gz)   int16 each, one block per sensor id 0-5

accel int16 = g    * 8192.0   (±4 g range)
gyro  int16 = °/s  * 65.536   (±500 °/s range)
```

Sensor id order is fixed: `0=hand(onboard), 1=thumb, 2=index, 3=middle,
4=ring, 5=pinky` — matches `hardware/WIRING.md`'s channel map (thumb=ch0 …
pinky=ch4). `tools/handrig_dashboard.html` decodes this exact layout; if you
change the frame, update the parser in the same commit.

## Known open item: sensor mounting axis convention

The finger sensors are mounted with **sensor −Y pointing toward the
fingertip and sensor +Z pointing up** (out of the back of the finger) —
confirmed empirically after taping all 5 units to the glove. The dashboard's
3D model uses `+Z = forward (fingertip), +Y = up`, which does **not** match
the sensor's physical mounting frame 1:1. Right now the dashboard applies
**no axis remap** — it feeds raw sensor-frame accel/gyro straight into
Madgwick and then into the model. This means finger curl (rotation about the
sensor/model X axis, which the mounting keeps aligned) should already look
correct, but abduction/spread motion (which involves the swapped Y/Z axes)
will likely show up on the wrong visual axis until a per-sensor axis remap
`(x, y, z) → (x, z, −y)` is added before the Madgwick update in
`tools/handrig_dashboard.html`. **Not implemented yet — do this before
trusting spread/roll data from the dashboard.** See `DECISIONS.md` for the
reasoning behind the chosen remap.

Leukoplast tape (used to mount every finger sensor) was ruled out as a cause
of the clone-init garbage — it's non-conductive and can't produce stuck
digital register values. It remains a real, separate risk for **intermittent**
dropouts if it pulls on a wire during flex; the boot diagnostic with the
glove flat and still is the way to tell the two failure modes apart (bad at
boot = init/electrical; fine at boot, degrades while worn = wire strain).
