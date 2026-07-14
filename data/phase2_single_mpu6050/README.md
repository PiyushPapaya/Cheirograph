# data/phase2_single_mpu6050/ — bench captures

Raw serial dumps from the Phase 2 single-MPU-6050 bench test (one sensor, direct
I²C, **no mux**). Kept as evidence and as sample input for `tools/plot_imu_3d.py`.

These are *diagnostic* captures, not training data — that's why they live in a
named subfolder and are committed to the repo, unlike the bulk per-letter dataset
(`data/<label>/`) which `.gitignore` keeps out.

| File | Sketch | Columns | Units |
|---|---|---|---|
| `gyro_raw.csv` | `firmware/02_single_mpu6050_test/diagnostics/gyro_raw/` | `gx,gy,gz` | deg/s |
| `accel_raw.csv` | `firmware/02_single_mpu6050_test/diagnostics/accel_raw/` | `ax,ay,az` | g |

Both were captured at ~100 Hz (10 ms loop delay) while the sensor was rotated and
shaken freely by hand, then set down still at the end. The leading `#` lines are
capture notes; the first data row is the header.

## Re-plot

```bash
cd tools
python plot_imu_3d.py ../data/phase2_single_mpu6050/accel_raw.csv --kind accel
python plot_imu_3d.py ../data/phase2_single_mpu6050/gyro_raw.csv  --kind gyro
```

Add `--save ../docs/media/phase2_gyro_3d.png` to write a PNG instead of opening a window.
