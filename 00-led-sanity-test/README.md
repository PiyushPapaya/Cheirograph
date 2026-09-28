# 00 — XIAO LED Sanity Test

> *This folder's number is a flexible guide, not a permanent label. Rename or renumber as the real build dictates.*

**Phase:** 0

**Goal:** Confirm the Seeed XIAO nRF52840 Sense powers on, enumerates over USB, accepts a flash, and runs code — before trusting it with any sensor work. The classic first-light test: blink the onboard LED.

**"Done" looks like:**
- The onboard RGB user-LED cycles **red → green → blue**, 500 ms per colour, forever.
- Upload completes from the Arduino IDE with no bootloader errors.

**What this is not:** No IMU, no I²C, no serial — just proof that the board and toolchain are alive.

**Why it matters:** If flashing fails, nothing downstream matters. This isolates "is the board/toolchain working?" from every later, harder question.

---

## First-contact gotcha — the board wouldn't connect

On first plug-in the XIAO would not show up as a programmable port. The fix for the
nRF52840 bootloader: **double-tap the RESET button** (quick double-press). This drops
the board into UF2 bootloader mode and it re-enumerates as a flashable device. After
that the port appears and uploads work normally. Expect to do this any time the board
gets stuck or a bad sketch bricks the port.

## Toolchain setup (Arduino IDE)

1. **File → Preferences → Additional Boards Manager URLs**, add:
   `https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json`
2. **Tools → Board → Boards Manager**, search `seeed nrf52`, install the latest.
   - Two packages exist — see [`../../hardware/datasheets/XIAO_nRF52840_Sense.md`](../../hardware/datasheets/XIAO_nRF52840_Sense.md)
     for which to use when.
3. **Tools → Board →** *Seeed XIAO nRF52840 Sense*.
4. **Tools → Port →** the COM port shown as *Seeed Studio XIAO nRF52840 Sense*
   (double-tap RESET first if it's missing).
5. Open `00_led_sanity_test.ino` and click **Upload**.

## The LED is active-LOW

`digitalWrite(LED_RED, LOW)` turns the red segment **on**; `HIGH` turns it off. Same for
green and blue. The `LED_RED` / `LED_GREEN` / `LED_BLUE` symbols are defined by the Seeed
board package, so no raw `P0.xx` pin numbers are needed here.
