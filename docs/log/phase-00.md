# Phase 0 — Deciding what to build, then building the skeleton

**Date:** 2025-07-27 → 2026-07-10 (planning → components → repo scaffold)

---

## What I set out to do

Before touching a soldering iron I wanted the concept pinned down: a glove that
reads finger orientation and turns hand-shapes into text. The hard questions
weren't mechanical, they were "will this even work" questions — five identical
MPU-6050s all default to the same I²C address `0x68`, raw IMU data is noisy, and
somehow a trained model has to end up running on a tiny microcontroller. I didn't
want to order a pile of parts and then discover the architecture was a dead end.

---

## What happened

A few hours of research settled the three big unknowns, and each answer became a
line in `DECISIONS.md`:

- **The address collision** → a PCA9548A I²C multiplexer. It sits in front of the
  five sensors and switches which one is "live" before each read, so they can all
  keep address `0x68`.
- **The noise** → sensor fusion with a Madgwick filter, running on the MCU rather
  than leaning on the MPU-6050's fiddly onboard DMP.
- **On-device ML** → Edge Impulse + TinyML, classifying on-device so the glove
  types over BLE without a laptop in the loop.

I also made the call that surprises people: the glove is for the **left** (non-
dominant) hand, so my right stays free to solder and drive the keyboard while
testing. It's a real trade-off — ASL fingerspelling uses the dominant hand, so the
dataset won't transfer without re-collecting — but for a solo build the ergonomics
win. Then I ordered the full BOM, and when it arrived I soldered headers on the mux
and all five GY-521 boards. No visible shipping damage, though whether every board
was *electrically* alive stayed an open question until first power-on.

Last step was the part that keeps me honest: a rigid repo. Four documentation
lanes, numbered firmware milestone folders that never get deleted, wiring and BOM
docs. The idea is that the *record* of the engineering is as much the deliverable
as the glove.

---

## The hard part

Resisting the urge to order first and think later. The `0x68` collision especially
looked like a wall until the mux turned up in research — it would have been an
expensive thing to discover *after* wiring five sensors to one bus.

---

## How I solved it

Front-loading the architecture. By the time anything got soldered, every major
component already had a justified reason to exist, written down. That's what
`DECISIONS.md` is for.

---

## Photos / traces

- Soldered mux + five GY-521 boards: `docs/media/phase0_boards.jpg` *(to capture)*
- Repo structure: see the tree in [`README.md`](../../README.md)

---

## What's next

Stop planning and find out if the hardware is alive. Phase 1: get the XIAO
nRF52840 Sense flashing and read its onboard IMU — the first electrical gate.
