# REFERENCES.md — Cheirograph

External sources that actually fed the build — datasheets, libraries, and the
specific pages that unblocked a problem. Grouped by topic; the ones that were
*decisive* for a debugging session are flagged. Add to this as the build grows.

---

## Board — Seeed XIAO nRF52840 Sense

| Source | Link | How it helped |
|---|---|---|
| XIAO Sense IMU usage | https://wiki.seeedstudio.com/XIAO-BLE-Sense-IMU-Usage/ | The onboard 6-DOF IMU (LSM6DS3), its internal-I²C usage, and example code. Confirmed the board *already* has an IMU (our hand reference) and how I²C is exposed. |
| XIAO nRF52840 pinout / getting started | https://wiki.seeedstudio.com/XIAO_BLE/ | **Decisive for pin mapping:** on the XIAO nRF52840 Sense, **D4 = SDA, D5 = SCL**, plus 3V3 / GND placement. This is the wiring the whole external bus hangs off. Local copies of the pinout images live in `hardware/datasheets/`. |

## Sensor — MPU-6050 (and why ours is a clone)

| Source | Link | How it helped |
|---|---|---|
| Adafruit MPU6050 library | https://github.com/adafruit/Adafruit_MPU6050 | The library behind the *first* attempt. Good accel/gyro examples — but it validates `WHO_AM_I` strictly and rejected our module (see debugging log below). |
| Adafruit MPU6050 guide | https://learn.adafruit.com/mpu6050-6-dof-accelerometer-and-gyro | Wiring, sensor ranges, and how to read the accel (g) / gyro (deg/s) values. |
| MPU-6050 datasheet (TDK InvenSense) | https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Datasheet1.pdf | Register definitions: `WHO_AM_I` (0x75), I²C address (0x68 / 0x69 via AD0), accel/gyro full-scale behaviour. The reference for any I²C debugging. |
| WHO_AM_I in i2cdevlib (Rowberg) | https://github.com/jrowberg/i2cdevlib/blob/master/Arduino/MPU6050/MPU6050.cpp | Showed *why* checking `WHO_AM_I` is worthwhile. A genuine MPU-6050 returns `0x68`; **ours returned `0x72`**, which is how we caught that the chip is a clone. |
| MPU6050_light (rfetick) | https://github.com/rfetick/MPU6050_light | **Decisive fix:** supports MPU-6050-compatible modules/clones that Adafruit's stricter driver refuses. This is the library the Phase 2 firmware uses. |
| MPU6050_light examples | https://github.com/rfetick/MPU6050_light/tree/master/examples | Ready-made sketches for accel, gyro, angles, calibration and offsets — the basis for the diagnostic sketches. |
| SparkFun MPU-9250/6500 library | https://github.com/sparkfun/SparkFun_MPU-9250_Breakout_Arduino_Library | Useful precisely because many cheap "MPU-6050" boards are actually MPU-6500/9250-family silicon (matches our `0x72`). A fallback if MPU6050_light ever falls short. |

## I²C

| Source | Link | How it helped |
|---|---|---|
| Arduino Wire (I²C) reference | https://docs.arduino.cc/language-reference/en/functions/communication/wire/ | `Wire.begin()`, transmissions, `requestFrom` — the API the scanner and register-read code are built on. |
| I²C Scanner example | https://playground.arduino.cc/Main/I2cScanner/ | Basis for `diagnostics/i2c_scan/`. Detects whether the sensor is physically present and at which address (0x68 for us) — separates "not wired" from "wrong chip". |

---

## Debugging log — how the sources combined

**Problem:** `Failed to find MPU6050 chip!` (Adafruit example halts on startup).

1. **I²C scanner** → device found at **0x68** ⇒ wiring and power are fine, the board is ACKing.
2. **WHO_AM_I (reg 0x75)** → returns **0x72**, not the `0x68` a real MPU-6050 gives
   ⇒ the module is a **clone** (MPU-6500/9250 family). Sources: MPU-6050 datasheet +
   i2cdevlib WHO_AM_I code.
3. **Fix:** switch to **MPU6050_light**, which doesn't gate on the strict `WHO_AM_I`
   check → works immediately. Logged in `DECISIONS.md` (2026-07-14).

**Problem:** finding the correct I²C pins on the XIAO.
- **Seeed XIAO documentation** confirmed `D4 → SDA`, `D5 → SCL`, `3V3 → VCC`, `GND → GND`.

Reproduce the chip-ID finding yourself with
`firmware/02_single_mpu6050_test/diagnostics/i2c_scan/i2c_scan.ino` — it scans the
bus and prints `WHO_AM_I` for anything at 0x68/0x69.
