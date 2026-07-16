# data/phase3-4_five_imu_gyro/ — bench captures

Raw serial capture from the Phase 3/4 bring-up: all five finger MPU-6050
clones read through the PCA9548A mux (`firmware/04_all_imus_raw/`), gyro
only, while the breadboard rig was picked up and rotated by hand then set
down. Diagnostic capture, not training data — see `data/README.md` for that
distinction.

| File | Sketch | Columns | Units |
|---|---|---|---|
| `movement_test.csv` | `firmware/04_all_imus_raw/04_all_imus_raw.ino` | `sample_idx,host_time,sensor_id,gx,gy,gz` | deg/s |

`sensor_id`: 1 = IMU0 (mux ch0) .. 5 = IMU4 (mux ch4). No finger identity is
assigned yet — the sensors sit flat on a breadboard, not mounted on the glove
(that's Phase 7). `host_time` is the Arduino Serial Monitor's receive
timestamp, not a device-side `millis()` value — this sketch doesn't emit the
project's `millis,sensor_id,...` contract yet (see the firmware README).

## Analyze / re-plot

```bash
cd tools
python analyze_multi_imu.py ../data/phase3-4_five_imu_gyro/movement_test.csv
python plot_multi_imu.py ../data/phase3-4_five_imu_gyro/movement_test.csv \
    --save ../docs/media/phase3-4_five_imu_movement.png
```
