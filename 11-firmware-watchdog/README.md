# 11 - Firmware v6 (watchdog)

**Phase 8, a hung I²C bus must reset the glove instead of freezing it.**

**Status: compiled only. NOT flashed or tested on the glove.** Every test below is "not run yet".

Stage 09's v5 recovers from a stuck SDA line, but not from a stuck SCL line. The core's `Wire` driver waits in loops with no timeout, so a slave holding SCL low hangs `endTransmission()` forever. No software check can catch that, because the code that would check never runs. v6 adds the nRF52 hardware watchdog (WDT): a separate timer that resets the chip if the sketch stops feeding it.

**Firmware:** [`11_firmware_watchdog.ino`](11_firmware_watchdog/11_firmware_watchdog.ino). Stage 09's sketch is untouched. Mirror: `Data/firmware/11-firmware-watchdog__11_firmware_watchdog.ino`.

## What v6 changes

| # | Change |
|---|---|
| 1 | 2 s hardware WDT, started first thing in `setup()`. Fed between boot steps and once per `loop()` tick, never inside a loop that waits on hardware. |
| 2 | Boot-hang guard. Before touching a sensor, its number goes into `GPREGRET2` (survives a watchdog reset). If the reset was the dog, the next boot skips that finger, so a bad wire cannot cause a reset loop. A power cycle clears it. |
| 3 | Mask bit 6 = gyro is ±2000 °/s, always set. |
| 4 | Mask bit 7 = this boot came from a watchdog reset. |
| 5 | Device name `HandRig-6IMU-v6`. |
| 6 | MTU clamped to 247 when stored and printed. |
| 7 | Absent sensors are retried every 5 s (not the ones the guard skipped). |
| 8 | `skipped=` in the report line (20 ms ticks lost to a stall). |
| 9 | Hand IMU at 104 Hz ODR, accel bandwidth 50 Hz. Effect unverified, F6 compares it with v5. |
| 10 | Boot print of the pinky's accel offset registers (`offs=`) when `who=0x68`. |
| 11 | `# t=<ms> after <step>` after each boot step. |

The frame is still 80 bytes. v4 used 65.536 LSB/(°/s) for gyro, v5 and v6 use 16.384.

The spec asks for a feed inside the boot bias-calibration loop. This firmware has no such loop (bias is calibrated in the dashboard), so there is nothing to feed there.

## Toolchain

- Board package: Seeed nRF52 Boards (Seeeduino nrf52) 1.1.13, FQBN `Seeeduino:nrf52:xiaonRF52840Sense`
- Library: Seeed Arduino LSM6DS3 2.0.7. The `Arduino_LSM6DS3` library must stay uninstalled (it shadows the Seeed one).
- Compile: `arduino-cli compile --fqbn Seeeduino:nrf52:xiaonRF52840Sense 11-firmware-watchdog/11_firmware_watchdog`
- Result 2026-11-23: 135456 bytes flash (16 %), 14696 bytes RAM (6 %). v5 is 133312 bytes.

## How the watchdog works (the interview version)

I²C on this chip can hang forever if a device holds the clock low. The watchdog is a hardware timer I restart every 20 ms and between boot steps. If anything hangs for 2 s, the chip resets. Before touching a sensor I write its number into a register that survives that reset. If the reset came from the watchdog, the next boot skips that sensor. Bit 7 of every frame says "I rebooted from the watchdog", bit 6 says "gyro is ±2000".

## Glove test plan (about 75 min), all not run yet

Before: export the v5 binary from the IDE (rollback). Log serial to a file the whole time. Screen-record the dashboard.

- [ ] **F1 Boot.** Flash v6. Pass: `reset reason=` printed, 6/6 OK, `# t=` gaps all under 1.5 s, pinky offset registers printed, picker shows `HandRig-6IMU-v6`, dashboard fuses. `gpregret2=0x0` after a power-on (if not, the bootloader uses it, switch to a `.noinit` RAM variable). If a gap is over 1.5 s, set `WDT_TIMEOUT_MS` to 4000 and log it in DECISIONS.
- [ ] **F1b v5 banner.** Before flashing v6 (still on v5), connect the new dashboard. Pass: banner `firmware v5 detected, flash v6`, one `firmware scale` black box event.
- [ ] **F2 SDA short.** Jumper D4 (SDA) to GND for 1 s, release. Pass: fingers drop, `bus_rec` +1 within 2 s, fingers back within 3 s, no reboot.
- [ ] **F3 SCL short at run time.** Jumper D5 (SCL) to GND for 3 s, release. Pass: reboot within about 2 s of the hang, `reset reason=0x2`, dashboard shows the watchdog notice once after reconnect. Note: the finger being read at that moment is skipped on the next boot until a power cycle.
- [ ] **F4 Late finger.** Power off, unplug the pinky's SDA lead, power on (pinky NOT FOUND), plug it back in. Pass: within 10 s `# late init sid 5 -> ok`, pinky appears.
- [ ] **F5 Upload and the bootloader.** (a) Upload v6 again from the IDE. (b) Double-tap RESET with v6 running: does the UF2 drive or port stay up for 30 s? (c) If not: unplug USB and battery for 10 s, plug in, double-tap within the first second. Record which one works. If only (c) works, a pin reset does not stop the WDT and the bootloader does not feed it, so the procedure is "power-cycle, then double-tap". If (c) fails too, see the rollback.
- [ ] **F6 Soak.** 10 min streaming, glove on, normal moves. Pass: `hz` 50.0, `skipped=0`, `tx_fail=0`, no reboot. Compare hand gyro std when still with v5 (2026-11-07: 0.62 / 0.60 / 0.88 °/s).
- [ ] **F7 Boot-hang guard.** Power off. Jumper the ring finger's SCL lead (mux channel 3 side) to GND. Power on, wait 30 s. Pass: one or more watchdog resets, then `# sid 4 skipped...`, then streaming with 5 sensors. Remove the jumper and power-cycle: 6/6 OK.

Shorts through the pull-ups are safe. Never short to 3V3. Check `hardware/WIRING.md` for where the channel-3 SCL lead is easiest to reach.

## Unverified

- "A pin reset does not stop a running WDT" is the author's reading of the nRF52840 docs. It is not verified. F5 tests it.
- Whether the bootloader changes `GPREGRET2`. F1 checks it.
- Whether Bluefruit start-up and a connect event stay under the 2 s timeout. F1 timings and F6 show it.
- The hand ODR change (104 Hz) has no measured effect yet.

## Rollback if it ends in a reset loop

1. Unplug USB and the battery for 10 s. A power-on reset clears the WDT for certain.
2. Plug in and double-tap RESET at once. The UF2 bootloader starts with no WDT running.
3. Upload v5 from the IDE (or the exported v5 binary).
4. Log it here. If the bootloader cannot live with a running WDT, the options are: feed before entering the bootloader and accept a 2 s upload window, or stop using IDE auto-reset and always power-cycle then double-tap. Decide only if F5 fails.
