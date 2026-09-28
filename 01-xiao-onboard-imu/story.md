# Phase 1 — First light

**Date:** 2026-07-14

---

## What I set out to do

One question: is the board even alive? Everything downstream — five finger
sensors, fusion, a classifier — assumes the XIAO nRF52840 Sense flashes and that I
can read its onboard IMU. That onboard IMU isn't a throwaway either: it's the
**hand reference**. Every finger's orientation later gets measured *against* it, so
if it's flaky the whole glove is flaky. I wanted it proven first.

---

## What happened

The board wouldn't show up as a programmable port. New board, and it just wasn't
there in the IDE. That's a deflating way to start — is it dead on arrival?

Turned out to be the nRF52840's bootloader: **double-tap the RESET button** and it
drops into UF2 mode, the port enumerates, and uploads work. Filed under "will
happen again, remember the trick." After that the toolchain came together — Seeed
board package, the LSM6DS3 library — and a dumb little LED sanity test cycling the
onboard RGB red→green→blue confirmed the whole chain: USB, bootloader, MCU, upload.
(The LED is active-LOW, so `LOW` means on — mildly confusing the first time.)

Then the onboard IMU. One gotcha that cost a minute: the LSM6DS3 answers at I²C
`0x6A`, **not** `0x68`. `0x68` is what the finger MPU-6050s use — mixing them up is
going to be a recurring trap, so it's now written down in a few places. With the
right address and library it streamed clean `aX,aY,aZ,gX,gY,gZ` at 115200 baud.

---

## The hard part

The board-not-connecting scare, purely because it was minute one of a new build and
I had no reason yet to trust anything. Once it flashed, the IMU was easy.

---

## How I solved it

Double-tap RESET → UF2 bootloader mode. That's the whole fix, and it's now the
first entry in the repo's "quick gotchas" list so future-me doesn't panic.

---

## Photos / traces

- LED sanity test running: `docs/media/phase1_led.jpg` *(to capture)*
- Onboard IMU serial stream: `docs/media/phase1_serial.png` *(to capture)*
- Board pinouts / spec: [`hardware/datasheets/XIAO_nRF52840_Sense.md`](../../hardware/datasheets/XIAO_nRF52840_Sense.md)

---

## What's next

Move off the onboard IMU and onto the real sensors. Phase 2: wire a single external
MPU-6050 to the D4/D5 bus and confirm one finger sensor reads at `0x68` — before the
mux complicates everything.
