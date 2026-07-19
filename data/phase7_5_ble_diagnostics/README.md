# data/phase7_5_ble_diagnostics/

Two raw captures taken from `handrig_dashboard.html`'s "Export CSV" during the
first BLE bring-up session on the glove (2026-07-19), **before** the clone-init
fix (firmware v3, `firmware/08_ble_dashboard/`) was written. Kept as evidence
for the debugging story, not as usable training data.

Format: `t_ms,<name>_ax,<name>_ay,<name>_az,<name>_gx,<name>_gy,<name>_gz` for
`name` in `hand,thumb,index,middle,ring,pinky` — accel in g, gyro in °/s.

## What these show

| Sensor | accel \|a\| | gyro | Verdict |
|---|---|---|---|
| hand (LSM6DS3) | ≈0.99 g | ≈0 at rest | healthy |
| pinky (ch4, genuine 0x68) | ≈0.99 g | ≈0 at rest | healthy |
| thumb (ch0) | ≈3.5 g | `gx` stuck at exactly `246.0938` every row | dead — frozen register |
| index (ch1) | ≈0.98 g (accel looks OK) | `gy` stuck at `-330`-ish, `gz` ramping | gyro path dead |
| middle (ch2) | `ay` stuck at exactly `1.9688` every row | `gy` stuck at `-122`-ish | dead — frozen register |
| ring (ch3) | ≈2.6 g | `gx` ramping in a straight line, step size = exactly `±0x2000/scale` per frame | dead — free-running counter, not real motion |

The exact-repeat values (`246.0938`, `1.9688`, etc.) and the perfectly linear
`±0x2000` ramps are the tell: real sensor noise never repeats a float to 4
decimal places or increments by a perfectly constant integer step. That ruled
out calibration, filtering, and wiring flakiness as the cause and pointed
straight at initialization — see `firmware/08_ble_dashboard/README.md` and
`DECISIONS.md` (2026-07-19) for the root cause (MPU-6050 clones at
`WHO_AM_I=0x72`) and the fix.

- `capture_01_pre_fix_garbage.csv` — first capture, ~70 rows.
- `capture_02_pre_fix_garbage_calibrated.csv` — second capture (dashboard's
  bias/deadband calibration applied client-side), same garbage underneath
  since calibration can only remove an offset, not a frozen register.
