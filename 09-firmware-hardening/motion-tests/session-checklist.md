# Glove session checklist

One page. Tests: S03 protocol table (`docs/log/specs/S03-calibration-posture-test.md`) and `README.md` in this folder.

## Before
- [ ] Battery charged.
- [ ] Photos of the wiring and the glove (pen line across the XIAO edge, with a ruler).
- [ ] Firmware name shows in the BLE picker (v5 or newer).
- [ ] The dashboard is the current `tools/handrig_dashboard.html` (`md5sum` matches the other two copies).

## Calibration
1. Glove on, powered 5 min.
2. Elbow on the table, forearm about 30 degrees up, hand in the air, palm down, fingers straight and together, thumb alongside the index.
3. Calibrate (20 s). Do not move. Do not talk with the hand.
4. Do the 2 s whole-hand tilt and roll the dashboard asks for (mount check).
5. Noise Check until GO.

## This session's tests
- [ ] Posture test T1 to R1, one Record each, file names from the S03 table.
- [ ] Then: `python tools/analyze_posture.py <folder>` and save the output as `result.txt`.
- [ ] Other tests from `README.md` in this folder.

## Curl sign
- [ ] Curl the index finger. Read the sign of the curl value. Write it down: ______

## After
- [ ] Copy the files into the repo today.
- [ ] Mirror them into `Data/` as `<stage>__<name>`.
- [ ] Back up `docs/log/`.
