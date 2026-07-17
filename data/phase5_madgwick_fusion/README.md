# data/phase5_madgwick_fusion/ — bench captures

Serial captures from `firmware/05_madgwick_fusion/05_madgwick_fusion.ino`:
per-sensor Madgwick fusion (accel-seeded orientation, two-stage beta),
fused contract `millis,sensor_id,qw,qx,qy,qz,roll_deg,pitch_deg,yaw_deg`.

| File | What it is |
|---|---|
| `capture_01_movement.csv` | ~29.5 s bench run with deliberate hand/finger movement, `SUBTRACT_GYRO_BIAS=1`. Includes the boot log (bias table + seed-accel table). |
| `capture_02_drift.csv` | ~31.5 s of the sensors held still after calibration (the drift test). Boot log missing from the saved file — the top of the serial capture (setup + calibration echo) wasn't captured, so we don't have that run's own printed bias table, but the firmware default (`SUBTRACT_GYRO_BIAS=1`) applies unless it was edited before this run. |

Re-run the analysis:
```bash
cd tools
python analyze_drift.py ../data/phase5_madgwick_fusion/capture_01_movement.csv
python analyze_drift.py ../data/phase5_madgwick_fusion/capture_02_drift.csv
```
Note: both captures were taken with `INCLUDE_RAW=0`, so they carry only the
fused columns (`qw,qx,qy,qz,roll,pitch,yaw`), not raw accel/gyro —
`tools/analyze_calibration.py` (which expects the 8-column raw contract from
Phase 4) doesn't apply here. The gyro bias/noise table for these runs is the
one the firmware itself prints at boot (reproduced below), not something
recomputed from the CSV.

## Findings

### Calibration quality — big improvement over Phase 4

`capture_01_movement.csv`'s embedded bias table (10 s still window, 1001 samples):

| sensor | bias_x | bias_y | bias_z | std_x | std_y | std_z |
|---|---|---|---|---|---|---|
| 0 (hand) | -0.198 | -1.596 | -0.458 | 0.213 | 0.049 | 0.055 |
| 1 | 1.071 | 2.047 | 1.060 | 0.081 | 0.109 | 0.084 |
| 2 | 0.360 | 2.009 | -1.217 | 0.090 | 0.125 | 0.085 |
| 3 | -0.938 | 3.508 | -0.463 | 0.089 | 0.147 | 0.084 |
| 4 | -0.317 | 3.755 | -1.464 | 0.091 | 0.203 | 0.101 |
| 5 | 5.788 | -6.984 | -0.814 | 0.286 | 0.344 | 0.119 |

Std is now **0.05-0.35 deg/s** across all six sensors — two orders of
magnitude better than the Phase 4 captures, where the "still" window std
was 38-84 deg/s because the rig was actually being moved during
calibration. This run's window was genuinely still, and it shows: this is
the first calibration table in the project worth trusting. Finger 5 is
still the noisiest (std ~3x the others, bias also the largest in magnitude)
— consistent with every earlier capture. Not disqualifying, but worth an
isolated single-channel re-check before trusting it as much as the other
four.

### Connection health — no dropouts in either capture

Both files: all 6 sensors report `# sensor N OK` at boot, and every sensor
has the *same* sample count for the full session (2503/2503 in the
movement capture, 2719-2720/2719 in the drift capture — the ±1 is just tail
truncation, not a dropout). No all-zero rows, no NaNs. This is the first
capture where **finger 2's intermittent dead-channel issue (seen in both
Phase 4 sessions) did not reproduce.** That's good news but not proof it's
fixed — it was already intermittent (a full-session dropout once, a
340 ms dropout once, nothing this time), consistent with a marginal
physical contact rather than a resolved fault. Treat it as "not observed
this run," not "fixed," until it survives a longer session or a proper
continuity check.

### Rate — dropped further, ~84-86 Hz (was ~93.6 Hz in Phase 4)

`# rate_hz=` lines across both captures: 84.2-86.4 Hz. Adding the Madgwick
update + quaternion→Euler conversion + three extra printed columns per
sensor per tick costs real time inside the same 10 ms budget — expected,
since Phase 5 does strictly more work per tick than Phase 4's raw read.
Still short of the 100 Hz target from GENERAL_PLAN.md. Candidates to claw
time back, in rough order of expected payoff: drop `INCLUDE_RAW`-style
extra Serial.print calls in the hot loop (each one blocks on UART), profile
whether `quatToEuler` is needed every tick or only for human-readable
debugging, and re-check whether 400 kHz I²C is actually being honored by
every mux channel.

### Drift test (`capture_02_drift.csv`, sensors held still, ~31.5 s)

Run with `python analyze_drift.py`:

| sensor | droll/min | dpitch/min | dyaw/min |
|---|---|---|---|
| hand | 0.00 | 0.10 | 2.12 |
| finger 1 | 1.70 | -0.23 | -2.04 |
| finger 2 | -0.06 | 0.17 | 0.19 |
| finger 3 | 1.20 | 0.02 | -1.73 |
| finger 4 | 0.04 | -0.06 | -0.97 |
| finger 5 | 0.51 | -0.02 | -0.53 |

**Roll and pitch are essentially flat** (≤ ~1.7 deg/min, most under 0.5) —
exactly what's expected, since Madgwick's accel correction anchors both
against gravity every tick regardless of gyro bias. **Yaw drifts at
roughly 0.2-2.1 deg/min** — small, and exactly the un-correctable behavior
CLAUDE.md's gotcha list and DECISIONS.md (2026-07-14) already predict for a
6-DOF IMU with no magnetometer: nothing anchors yaw, so any residual bias
after subtraction integrates slowly and without bound. This run used
`SUBTRACT_GYRO_BIAS=1` (the sketch's default); we don't have a same-session
`SUBTRACT_GYRO_BIAS=0` capture to do the full A/B the sketch's own comment
asks for (`# calib_end` header for this run wasn't preserved either), so
"calibration made this better" is inferred from comparison against Phase
4's uncalibrated noise floor, not proven with a controlled pair from the
same sitting. **Still open:** re-run the same still-hold test with bias
subtraction forced off to get a real paired before/after number.

**Caveat on run length:** 31.5 s is short for a deg/min estimate — the
sketch's own comment asks for "several minutes." The numbers above are
consistent in direction and small in magnitude, so the headline conclusion
(roll/pitch hold, yaw creeps slowly) is probably right, but the precise
deg/min figures should be treated as a rough first read, not a final
number, until a multi-minute capture confirms them.

### Movement capture (`capture_01_movement.csv`)

Used here only to confirm the fusion runs stably under real motion (no
NaNs, no stuck quaternions, all sensors keep reporting through ~30 s of
deliberate movement) — `analyze_drift.py`'s first/last-sample numbers on
this file are not drift figures (the rig wasn't held still), they just
show large swings because fingers were being moved, e.g. finger 1
droll/min of -32.6 is motion, not gyro error. Sanity-check only.
