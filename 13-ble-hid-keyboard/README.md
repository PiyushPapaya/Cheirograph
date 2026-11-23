# 13 - BLE HID keyboard spike

**Phase 10, can the glove be a Bluetooth keyboard and still stream to the dashboard?**

**Status: compiled only. NOT flashed or paired yet.**

The final device types the recognised letter over BLE HID. The dashboard still needs the Nordic UART stream for debugging. This spike checks whether one device can offer both services.

**Sketch:** [`hid_spike/hid_spike.ino`](hid_spike/hid_spike.ino). It sends a dummy 80-byte frame at 50 Hz (valid checksum, mask `0x7F`) over `BLEUart` and types `a` every 2 s with `BLEHidAdafruit`. Device name `HandRig-HID-spike`. Both services are added before advertising. The HID UUID and keyboard appearance are in the advertising packet. The NUS UUID and the name are in the scan response.

Mirror: `Data/firmware/13-ble-hid-keyboard__hid_spike.ino`.

## Toolchain

- Board package: Seeed nRF52 Boards (Seeeduino nrf52) 1.1.13, FQBN `Seeeduino:nrf52:xiaonRF52840Sense`
- Compile: `arduino-cli compile --fqbn Seeeduino:nrf52:xiaonRF52840Sense 13-ble-hid-keyboard/hid_spike`

## Pairing

First use: pair from the OS Bluetooth settings. Just Works, no PIN. HID characteristics need an encrypted link, so the central must bond.

## Test cases (not run yet)

| Case | Setup | Pass | Result |
|---|---|---|---|
| S1 | `Bluefruit.begin()` (one link). Windows pairs it as a keyboard, then the dashboard connects over Web Bluetooth on the same laptop | Notepad shows `a` every 2 s and dashboard RATE is about 50 Hz | not run yet |
| S2 | `Bluefruit.begin(2, 0)`, `configPrphBandwidth(BANDWIDTH_HIGH)`. Phone pairs as keyboard, laptop dashboard connects | Phone gets `a`s, dashboard about 50 Hz | not run yet |
| S3 | Whichever passed, 10 min | No disconnect, no missed `a` | not run yet |

Decision after the tests:
- S1 passes: one build, the laptop does both.
- Only S2 passes: one build, the phone types, the laptop debugs.
- Neither: build flag `OUTPUT_HID`. HID build for the demo, UART build for development.

## Unverified

- Two services on one link while Chrome's Web Bluetooth and the Windows HID driver share it.
- Two peripheral links with `BANDWIDTH_MAX`.
- That the advert and scan-response split lets Windows both pair as a keyboard and let Web Bluetooth find the UART.
