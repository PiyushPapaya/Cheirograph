# Phase 2 — The first finger sensor, and the chip that lied about who it was

**Date:** 2026-07-14

---

## What I set out to do

Get one MPU-6050 talking. Just one, wired straight to the XIAO's D4/D5 I²C bus, no
multiplexer yet — because debugging a single bare sensor is a completely different
sport from debugging five of them hidden behind a mux. If this one sensor reads
clean accel and gyro, I've proven the driver and the wiring, and the mux in Phase 3
becomes the *only* new variable.

![MPU-6050 → XIAO direct wiring](../../hardware/wiring_mpu6050_direct.png)

---

## What happened

Four wires — VCC, GND, SDA→D4, SCL→D5 — and AD0 tied to ground to lock the address
at `0x68`. Loaded the Adafruit MPU6050 example, opened the serial monitor, and got:

```
Failed to find MPU6050 chip!
```

Nothing. On a fresh solder joint that message is genuinely ambiguous — bad wire?
cold joint? dead sensor? So instead of re-flowing solder blindly, I ran an **I²C
scanner**. It found a device at `0x68`. So the board is powered, wired, and
ACKing — the wiring is *fine*. The library is refusing it for some other reason.

The other reason turned up when I read the `WHO_AM_I` register (`0x75`) directly. A
genuine MPU-6050 returns `0x68`. Mine returned **`0x72`**. That's not an MPU-6050 at
all — it's a clone from the MPU-6500/9250 family, the kind of silicon that fills a
lot of cheap "MPU-6050" breakouts. Adafruit's driver checks `WHO_AM_I` strictly and
bails the moment it isn't exactly `0x68`. My hardware wasn't broken; the library was
just stricter than my bargain-bin sensor.

Swapped to `MPU6050_light`, which doesn't gate on that check. Worked on the first
try. It also folds bias calibration into a single `calcOffsets()` call, which I want
anyway. Then I captured a couple of runs — waving the sensor around and setting it
down still — and plotted each as a path through 3D space, coloured by time:

![Accelerometer 3D trajectory](../media/phase2_accel_3d.png)

The accelerometer plot is the satisfying one. Because gravity always has the same
magnitude, every point sits on a sphere of radius ~1 g; slow rotation just walks the
gravity vector around that sphere, and the bright knot is where I set the sensor
down at the end. That shape is the proof the axes and calibration are right — you
can't fake it.

![Gyroscope 3D trajectory](../media/phase2_gyro_3d.png)

The gyroscope plot loops far out on every fast twist (±100–240 °/s) and collapses
back toward the origin when I stop, because it measures *rate*, not angle. It never
quite returns to a clean zero, though — there's a couple of °/s of leftover bias
sitting there even after calibration. That's not a defect; that's the drift the
Madgwick filter is going to have to fight in Phase 5, and it's oddly nice to see it
this early.

---

## The hard part

Trusting the scanner over the error message. "Failed to find MPU6050 chip!" *sounds*
like a wiring problem, and the instinct is to reach for the soldering iron. The scan
result — device present at `0x68` — was the thing that reframed it from "bad
connection" to "wrong chip identity," and that's the whole ballgame.

---

## How I solved it

Separated "is it wired?" from "is it the chip the driver expected?" using two dumb,
library-free reads: an address scan, then `WHO_AM_I`. The `0x72` answer pointed
straight at a clone, and the fix was a more permissive library. I kept that scanner
as `diagnostics/i2c_scan/` so the finding is reproducible, not just a war story.

---

## Photos / traces

- Wiring diagram: [`hardware/wiring_mpu6050_direct.png`](../../hardware/wiring_mpu6050_direct.png)
- Accel 3D plot: [`docs/media/phase2_accel_3d.png`](../media/phase2_accel_3d.png)
- Gyro 3D plot: [`docs/media/phase2_gyro_3d.png`](../media/phase2_gyro_3d.png)
- Breadboard photo: `docs/media/phase2_breadboard.jpg` *(to capture)*
- Short clip: tilt the sensor while the serial numbers scroll *(to capture)*

---

## What's next

The clone is a watch-item — a non-genuine chip can differ in register defaults or
self-test, so if fusion looks wrong later this is a prime suspect, and my other four
modules are probably the same. Next up is Phase 3: bring in the PCA9548A mux, select
a channel, and reach that same `0x68` sensor *through* it.
