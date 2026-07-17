# data/phase4_six_imu_capture/ — bench captures

Raw serial capture from the Phase 4 six-sensor sketch
(`firmware/04_all_imus_raw/04_all_imus_raw.ino`): onboard LSM6DS3 (hand,
sensor_id 0) + five finger MPU-6050 clones via the PCA9548A mux (sensor_id
1-5), full project contract (`millis,sensor_id,ax,ay,az,gx,gy,gz`).

| File | Columns | Units | Notes |
|---|---|---|---|
| `capture_01_raw.csv` | `millis,sensor_id,ax,ay,az,gx,gy,gz` | accel g, gyro deg/s | First ~160 ms of the still-calibration window only — hand-transcribed excerpt, superseded by capture_02 below |
| `capture_02_full_session.csv` | `millis,sensor_id,ax,ay,az,gx,gy,gz` | accel g, gyro deg/s | **Full session**, ~8.7 s, millis 1048-9797, all 6 sensors |
| `capture_03_full_session.csv` | `millis,sensor_id,ax,ay,az,gx,gy,gz` | accel g, gyro deg/s | **Full session, re-run**, ~15 s, millis 1000-16000, all 6 sensors, includes the firmware's own printed bias table + `# rate_hz=` lines |

`capture_02_full_session.csv` is the complete run (the file the firmware
actually wrote, saved directly rather than transcribed from a chat paste —
see DOCUMENTATION.md 2026-07-17 for why that distinction mattered). It
entirely falls inside the firmware's declared 10 s calibration window
(`# calib_start hold_still_ms=10000` at the top) but is clearly **not**
a still capture — see findings below.

## capture_02 findings (`tools/analyze_calibration.py`, `tools/plot_6imu_3d.py`)

- **Finger 2 (mux channel 1) drops to a permanent all-zero reading at
  millis=1468 and never recovers for the rest of the ~8.3 s remaining in the
  run** (801 of 841 samples are `0,0,0,0,0,0`). A live MPU always carries
  ~1 g of gravity somewhere, so exact zeros mean the chip ACKed at init but
  its data registers went dead mid-run — almost certainly a loose physical
  contact on that channel (breadboard jumper), not a code fault. Visible in
  `docs/media/phase4_6imu_accel_3d.png` as a trajectory that stops dead at
  the origin partway through, and in the animated
  `docs/media/phase4_6imu_accel_3d.gif` as one arrow that stops moving while
  the other five keep swinging.
- **The whole run was declared "calibration" but contains a large hand
  rotation** — every live sensor's gyro std across the full run is 25-102
  deg/s, far from a still-capture noise floor. The calibration window needs
  to actually be still next time, or the bias table it produces is
  meaningless (same finding as the capture_01 excerpt, now confirmed at full
  scale).

## Re-run the analysis / regenerate the plots

```bash
cd tools
python analyze_calibration.py ../data/phase4_six_imu_capture/capture_02_full_session.csv
python plot_6imu_3d.py ../data/phase4_six_imu_capture/capture_02_full_session.csv \
    --save-static ../docs/media/phase4_6imu_accel_3d.png \
    --save-gif ../docs/media/phase4_6imu_accel_3d.gif --stride 4
```

## capture_03 findings (re-verification, 2026-07-17)

Same rig, same sketch, run again to re-check sensor health before moving on to
Phase 5. This capture embeds the firmware's own instrumentation: a printed
gyro bias/std table at the end of the 10 s calibration window, and periodic
`# rate_hz=` achieved-rate reports.

- **All 6 sensors initialized OK** (`# sensor N OK` for N=0..5) — no dead
  channel at boot this time.
- **Achieved loop rate: ~93.6-93.7 Hz** (from the embedded `# rate_hz=93.7
  frames=188 over_ms=2007` / `93.6` lines), not the 100 Hz target. Six
  sequential mux-switch-then-I²C-read cycles per 10 ms tick apparently cost
  more than the tick budget allows even at 400 kHz — worth profiling
  per-sensor read time before Phase 4 is called fully done.
- **Calibration window still wasn't still.** The printed bias table shows
  gyro std of 38-84 deg/s across all six sensors over the full 934-sample
  window (`# 0,934,-4.614,-10.784,-0.878,83.302,53.905,40.212` etc.) — an
  order of magnitude above a genuine at-rest noise floor (which should be a
  few deg/s, per the capture_02 finding below). The rig was moved during
  what the firmware logs as calibration, again.
- **Finger 2 (mux channel 1) dropped to an all-zero reading again, but only
  for the last ~340 ms of the ~15 s run** (34 of 1404 samples, millis
  15660-16000) — a much smaller and later dropout than capture_02's, where
  it died at millis=1468 and stayed dead for the rest of the session. Two
  different capture sessions, two different dropout windows on the *same*
  channel: this pattern (intermittent, not a fixed dead time) points at a
  loose physical contact on that mux channel or its finger sensor's
  breadboard jumper, not a firmware bug — confirms the capture_02
  hypothesis rather than replacing it. Visible in
  `docs/media/phase4_6imu_accel_3d_capture03.png` / `.gif` as five sensors
  tracking one shared motion cluster, with no full-session flatline this
  time (the dropout is too short at this timescale to show as a stationary
  point).
- **Finger 5's earlier accel-magnitude outlier is gone in this run** — no
  longer runs ~1.23 g high; worth treating capture_02's finding as
  session-specific breadboard contact quality rather than a fixed hardware
  fault on that channel, unless it reappears.

**Conclusion:** electrically, all 6 sensors are alive and none is
permanently dead — the intermittent finger-2 dropout is the one open item to
watch once this moves onto the glove, where strain relief should reduce (not
necessarily eliminate) loose-contact risk. The calibration-window-not-still
problem is now confirmed across three separate capture attempts and is a
capture-discipline issue (hold the rig physically still), not a firmware
issue — the still-window code itself is working as designed.

```bash
cd tools
python analyze_calibration.py ../data/phase4_six_imu_capture/capture_03_full_session.csv
python plot_6imu_3d.py ../data/phase4_six_imu_capture/capture_03_full_session.csv \
    --save-static ../docs/media/phase4_6imu_accel_3d_capture03.png \
    --save-gif ../docs/media/phase4_6imu_accel_3d_capture03.gif --stride 4
```

## What the saved excerpt shows

Running `tools/analyze_calibration.py` on this excerpt:

```
sensor              n       aX     aY     aZ  |a|     gX mean  gY mean  gZ mean     gX std  gY std  gZ std
hand (onboard)     16    0.027  0.002  1.005  1.005      0.01    -1.50   -24.71       0.52    0.16    8.05
finger 1           16    0.999 -0.006  0.142  1.009    -22.84     1.81    -2.46       7.54    0.96    1.11
finger 2           16    1.005 -0.015  0.164  1.019    -23.41     1.56    -6.23       7.41    0.94    1.57
finger 3           16    0.989  0.006  0.227  1.015    -24.91     2.36    -6.68       7.35    2.58    1.94
finger 4           16    0.974 -0.009  0.258  1.008    -23.30     2.79    -8.61       8.98    1.30    2.72
finger 5           16    1.232  0.163  0.085  1.246    -15.97    -7.80    -9.28      12.75    4.89    8.03
```

- **Accel magnitudes are all close to 1 g** (0.999-1.246) — sane, sensors alive.
  Finger 5's `|a|` at 1.246 g is the outlier worth another look (loose
  breadboard contact? different mux channel misbehaving?).
- **This was not actually a still hold.** The hand sensor's gZ climbs
  monotonically from -10.43 to -35.00 deg/s across these 16 samples (~160 ms)
  — that's real angular acceleration, not noise. The rig was being moved
  during what the firmware logs as "Calibrating... hold still." The large
  resting gyro means (15-25 deg/s on the fingers) are a symptom of that, not
  the sensors' true zero-rate bias.
- **Conclusion:** can't yet answer "is it well calibrated" from this data —
  need a genuinely still capture. Finger 5's higher noise (std ~5-13 deg/s
  vs. ~1-3 deg/s for the others) is also worth a repeat measurement in
  isolation before trusting it.

## Re-run the analysis

```bash
cd tools
python analyze_calibration.py ../data/phase4_six_imu_capture/capture_01_raw.csv
```
