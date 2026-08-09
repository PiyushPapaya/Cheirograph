# DOCUMENTATION.md — Cheirograph

The **dated ledger** of planned vs. actually achieved, session by session.

Rules:
- One block per work session, newest at the top.
- Include failures — the honesty is the value.
- Update in the **same commit** as the code it describes.
- Never edit a past entry to look better than it was.

---

## Block template

```
---

### YYYY-MM-DD | Phase N — <short name>

**Plan:** What I intended to accomplish this session.

**Achieved:** What I actually got working (be specific — serial output, test result, video evidence).

**Problems & blockers:** What went wrong, what surprised me, what I had to look up.

**Next:** The very first thing to do at the start of the next session.
```

---

## Entries

*(Newest entry goes here, above this line.)*

---

### 2026-08-09 | Pre-Phase-8 checklist hardening (2/2): capture-duration gate

**Plan:** Follow-up to the exit-code change above. The checklist mandates
holding the glove flat and still for 60 s before running
`analyze_noise_baseline.py`, but the script never verified the exported CSV
actually covered that window — a short capture (dropped BLE connection,
early export click) could still print a clean per-sensor GO built on far
too few seconds to be a meaningful noise baseline.

**Achieved:** Added `MIN_DURATION_S = 50.0` and a `short_capture` check:
if the CSV's timestamp span is under 50 s, the script now forces NO-GO
(exit 1) with an explicit "capture is only Xs, re-run the 60s baseline"
message, regardless of how clean the per-sensor stats look. Verified with
two throwaway synthetic CSVs: a 10 s capture with otherwise-clean sensor
stats now correctly reports NO-GO / exit 1 (previously would have been a
false GO), and a full 60 s capture still reports GO / exit 0 unchanged.

**Problems & blockers:** None.

**Next:** Run the full pre-Phase-8 checklist for real on the glove (boot
diagnostic -> calibrate -> 60 s baseline -> `analyze_noise_baseline.py`)
before starting actual Phase 8 labelled-data collection.

---

### 2026-08-09 | Pre-Phase-8 checklist hardening (1/2): enforceable exit code

**Plan:** The pre-Phase-8 noise QA checklist (`firmware/08_ble_dashboard/README.md`,
just committed) says `analyze_noise_baseline.py` "must print GO" before real
Phase 8 collection starts — but the script always exited `0` regardless of
verdict, so that rule was advisory text a tired future-me has to remember to
read correctly, not something enforceable.

**Achieved:** `analyze_noise_baseline.py` now exits `0` on GO and `1` on
NO-GO (`sys.exit(0 if all_ok else 1)`). Verified with two throwaway
synthetic 6-sensor CSVs before touching real hardware data: an all-still
noisy-but-clean capture (GO, exit 0) and a constant-value capture that
trips the stuck-frame detector on every sensor (NO-GO, exit 1). This makes
the checklist's step 3 gate scriptable
(`analyze_noise_baseline.py ... && <start batch capture>`) instead of
relying on someone reading the printed verdict correctly every time.

**Problems & blockers:** None — additive change to an already-working
script.

**Next:** Add a capture-duration sanity check (the checklist mandates a
60 s hold; the script never verified the CSV actually covers that window).

---

### 2026-08-08 | Live dashboard: thumb rig geometry + calibration stillness-gate fix

**Plan:** Fix two live-dashboard (`tools/handrig_dashboard.html`) bugs found while wearing
the glove: the rendered thumb didn't match a real relaxed hand, and all four fingers read
a fixed nonzero pitch (~20-29°) right after a 10 s calibration hold on a hand the wearer
insists never moved.

**Achieved:**
- **Thumb rig**, several iterations, each verified with actual matrix math in a scratch
  Node script instead of eyeballing screenshots after the first two guesses went wrong:
  1. First bug: the thumb's static rest-pose "bend" rotated about local X (pitch), which
     pops it out of the flat plane the other four fingers rest in. Root cause of "why does
     the thumb look broken even before any BLE data arrives."
  2. Second bug, after switching bend to a Y-axis (in-plane) rotation: got the sign
     backwards — positive yaw sweeps the pointing direction toward +X, and the thumb's
     anchor already sits on the +X side, so it was flaring further away from the hand
     instead of curling in toward the index.
  3. Third bug, after fixing the sign: the anchor position itself sat *inside* the solid
     palm box (`BoxGeometry(2.4,0.55,2.6)`, solid x:[-1.2,1.2] y:[-0.275,0.275]
     z:[-1.3,1.3]) — most of the segment rendered hidden inside opaque geometry, only a
     stray sliver visible (the "floating disconnected stub" screenshot).
  4. Fourth bug: redesigned with a two-axis kink at the segTip joint (restCurl + new
     restSweep) to reach the index's base — checked that the *endpoint* cleared the box,
     but never walked the *path* to it. A full 200-step path check found 22.8% of the
     digit's total length was still buried inside the box — the "twisted broken blob"
     screenshot. Final fix: dropped the kink entirely, went back to a straight segment
     (same proven zero-clip design as the other four fingers), anchored outside the box's
     x-edge with a small inward yaw. Verified clip fraction: 7.5%, all at the tip end,
     same negligible-overlap category the real fingers already have at their own base.
- **Calibration stillness gate**: root-caused the fixed post-calibration pitch offset to
  the calibration average including whatever motion happened in the first moment(s) of
  the 10 s hold (before the hand was actually still), which bakes a wrong reference into
  every subsequent reading. First attempt gated the calibration average on *absolute* raw
  gyro magnitude (`<6°/s`) — this was WRONG and it was a live regression, not a fix: a
  stationary MPU-6050 reads near its own fixed per-chip bias, not near zero, and this
  file's own `finishCalibration()` already expects bias up to ~40°/s per axis. One real
  sensor (pinky) has a bias over 6°/s, so the absolute gate rejected every frame from it
  for the entire hold, it never reached the 5-sample minimum, and `finishCalibration`'s
  own `c.n<5` bailout left it permanently stuck on raw, uncalibrated gyro (`roll:-105°
  yaw:-100°` on a still hand). Fixed by gating on deviation from a rolling per-sensor
  EMA of its own raw gyro instead of an absolute threshold — bias-agnostic, correctly
  admits a still sensor at any fixed bias level while still excluding real motion.

**Problems & blockers:** Iterating on 3D rig geometry from user-taken phone screenshots of
a live BLE-connected render is slow and error-prone — several rounds of plausible-looking
fixes failed because the reasoning covered the wrong failure mode (direction sign, box
clipping at the endpoint vs. along the whole path, etc.). Verifying with actual coordinate
math in a throwaway Node script before touching the file again was far more productive
than continuing to eyeball screenshots, and should be the default approach going forward
for anything geometric in this file. Also: any future "only average frames where X is
below a threshold" style filter needs a second look for whether X has a legitimate nonzero
baseline (bias) before picking that threshold — the first calibration fix attempt is a
concrete example of that mistake causing a real regression on live hardware.

**Next:** Verify the straight-thumb rig and the recalibrated stillness gate on the actual
glove across a few calibration cycles (not just one), including intentionally moving
during the hold to confirm real motion still gets excluded. If the thumb's straight
segment reads as anatomically too plain, consider a proper multi-joint thumb model later
rather than another single-kink patch — this session's failures suggest the two-segment
rig can't cleanly express both "in that box" and "touches the index" at once.

---

### 2026-08-07 | Gestura social pipeline agents + live dashboard rebrand/UI pass

**Plan:** Two unrelated pieces of housekeeping/polish, not a firmware milestone: stand up
the tooling for the Gestura social-media content pipeline, and give
`tools/handrig_dashboard.html` a visual pass now that it's stable enough to demo.

**Achieved:**
- **Nine project-scoped subagents added** (`.claude/agents/gestura-*.md`): story-scout →
  ideator → strategist → brand-designer → prompt-smith → producer → repurposer →
  copywriter → brand-guardian. Together they run the Gestura content pipeline end to end
  — mining the repo for filmable beats, turning them into scheduled ideas, producing and
  repurposing renders, writing captions, and a final scope-safety QA pass before
  anything posts. The `social/` folder they operate on (brand kit, content backlog,
  renders) is gitignored — local-only, deliberately never pushed to this public repo.
- **`tools/handrig_dashboard.html` restyled and rebranded as Gestura.** Full visual pass:
  copper/graphite brand palette driven from a single `BRAND` token object (kept in sync
  with the CSS custom properties at startup so canvas/Three.js and CSS can't drift),
  Gestura wordmark + hand-topology SVG mark in the header, animated grain/ambient
  background, redesigned instrument-style telemetry cluster and finger cards (visible
  bar tracks with a centre tick — the old near-black track read as broken/empty), a
  hero treatment for card S0 (the hand/reference sensor), card entrance animation, and a
  warm copper rim light + point light on the hand-reference cube in the Three.js scene
  so the 3D model picks up the same accent. Functionally unchanged — same BLE parsing,
  calibration, curl/gesture logic from the previous session; this was UI only.
- Decided, on being asked, to drop the internal "HandRig" name entirely from this file in
  favor of "Gestura" — this is a scoped exception to the standing convention that
  engineering-facing docs stay Cheirograph-branded and Gestura stays confined to
  `social/`; the dashboard alone now carries the public brand since it's a portfolio-
  facing demo. Everything else (README, this file, DECISIONS.md, firmware) stays
  Cheirograph. See DECISIONS.md (2026-08-07).

**Problems & blockers:**
- The CSS/JS diff was large (~440 lines) and mixes true UI/UX fixes (fixed an invisible
  bar-track color, fixed a grid-row-height clipping bug via `grid-auto-rows:max-content`)
  with pure rebrand changes — worth remembering these were bundled in one working-tree
  edit rather than two separate commits.
- Not independently re-tested live on the glove after the restyle — the previous
  session's functional confirmation (calibration-settle fix, BLE throughput) still
  stands, but the visual changes themselves haven't been eyeballed against real hardware
  yet.

**Next:** Open the dashboard against the live glove once to confirm nothing about the
restyle (new grid-auto-rows behavior, animation timing, palette swap) broke readability
or introduced layout regressions under real streaming data.

---

### 2026-08-07 | Phase 7.5 — Calibration-settle root-caused for real, curl readout, thumb rig fix, first gesture rule

**Plan:** Follow up on the previous session's "probably fixed (not yet independently
re-confirmed)" calibration-settle bug, and pick up the open issues it left behind: no
curl/flex readout, thumb rest-pose rig looking wrong, tilt-drift not yet distinguished
from the settle bug.

**Achieved:**
- **Calibration-settle bug actually root-caused and fixed.** The previous session's fix
  (waiting 600 ms → 2.5 s after resetting the filter to identity, then capturing that as
  the model's "zero" orientation) was still not enough — reported live as the hand model
  continuing to slowly rotate/point downward on its own even with the glove dead still.
  Root cause: that approach depended on live frames re-converging the filter from
  identity back to true gravity-referenced orientation within the fixed wait, and
  convergence time depends on both the smoothing slider and how far the calibration pose
  was from flat — no fixed wall-clock wait can cover every case, which is exactly why the
  first attempt (600 ms) and the second (2.5 s) both eventually failed the same way.
  Fixed for real in `tools/handrig_dashboard.html` `finishCalibration()`: instead of
  resetting to identity and waiting, it now runs the *existing* `Madgwick.update()` method
  synchronously ~40 times against the calibration-average gravity vector (zero rotation,
  beta forced to 1.0), which converges to the same fixed point live frames eventually
  would — in effectively 0 ms instead of an unverifiable wall-clock guess — then captures
  `qRef` immediately. No more timing window where the model can drift out from under a
  reference grabbed mid-convergence. **User-confirmed working live** after this change.
  See DECISIONS.md (2026-08-07) for why the synchronous-solve approach was chosen over
  just extending the wait again.
- **Accel jitter reduced before fusion.** Separately from the settle bug, the hand model
  showed small continuous "random" rotation even once calibrated and still — raw accel
  noise (~0.02 g/sample) was being fed straight into Madgwick's per-frame gravity
  correction, nudging the orientation a little in a new direction every sample. Added an
  EMA low-pass on the accel *before* fusion (not on the orientation output, to avoid
  adding lag) — gyro path is untouched.
- **Accel calibration-relative readout added.** `Calibrate (10 s)` now also captures each
  sensor's mean accel alongside the existing gyro bias, and the accel cards display
  `raw − accBias` post-calibration (reads ~0 in the calibration pose, signed deviation
  away from it afterward) — mirrors the gyro `bias-corr` readout. Raw accel (with real
  gravity) still feeds Madgwick unchanged; zeroing it there would blind the filter to
  "up".
- **Curl/flex readout added** (was open item #4 from the previous session) — each
  finger card now shows a curl bar, curl percentage, and a label (extended / bending /
  curled), derived from the same relative pitch already driving the 3D model, not a new
  measurement.
- **Thumb rig restructured** (relates to open item #2, thumb not resting/abducting
  correctly) — found the actual bug: the per-frame render loop was overwriting each
  finger's static rest-pose transform every frame by folding it into the same quaternion
  multiply as the live sensor rotation (`g.quaternion = local.multiply(rest)`), which
  applies the live rotation in world space rather than relative to the already-rotated
  rest pose. Split the rig into a static parent (yaw + a new baked-in "bend" for the
  thumb) and a live-driven child (`segBase`/`segTip`), so the thumb's curled-up-against-
  index rest pose survives instead of being clobbered each frame.
- **First gesture-detection rule added**, at the user's request (a specific pose: thumb
  bent up and pressed against the index finger). No ML classifier exists in this repo
  yet, so this is a plain threshold rule on geometry the 3D rig already computes: thumb
  tip world-position close to index tip, and the thumb's own forward axis pointing
  mostly upward (distinguishes "folded up against the index" from "resting alongside
  it" at the same distance). Shown live as a "gesture" pill in the header. Thresholds
  (`TOUCH_DIST=0.9`, `UP_MIN=0.35`) are geometry-scaled guesses, not yet tuned against a
  real hand.

**Problems & blockers:**
- The calibration-settle bug took **two sessions and two wrong fixes** (600 ms, then
  2.5 s) before the actual root cause (blind reset + hope-it-converged timing, not a
  "needs more time" problem) was found — worth remembering: a wall-clock wait tied to a
  physics convergence process that depends on user-controlled parameters is not a fix,
  it's a bigger gamble.
- **Pinky accel magnitude issue (from the previous session) is still open** — not
  touched this session, no new information.
- The gesture rule, accel jitter smoothing, accel calibration-relative readout, curl
  readout, and thumb rig fix were **not independently re-tested live** in this session
  the way the calibration-settle fix was — only the calibration-settle fix got explicit
  user confirmation ("good working") on the real glove. The others should be treated as
  implemented-but-unverified until tried live.

**Next:** Live-test the remaining unverified items above on the actual glove (curl
readout accuracy, thumb visual rest pose, gesture rule thresholds, whether the accel
jitter fix actually reads as smoother). Physically inspect the pinky connector/solder at
the knuckle — still outstanding from the previous session. If the gesture rule proves
noisy in practice, that's the point where collecting labeled data for the real TinyML
classifier (still not started) becomes the better investment over more threshold-tuning.

---

### 2026-08-07 | Phase 7.5 — First live BLE session: throughput fix, calibration-settle fix, and new issues surfaced

**Plan:** Flash v4 and finally get a live BLE session end to end — this was the first
time the hardened firmware from the previous session actually touched the glove.

**Achieved:**
- **BLE throughput collapse, root-caused and fixed.** First connect showed the dashboard
  stuck at 0 Hz / 0.0 KB/s with bad-frames climbing. The Serial report line already added
  in v4 made the diagnosis immediate: `read_us` (all 6 sensors) stayed flat at ~5.9 ms the
  whole time, while `write_us` (time inside `bleuart.write()`) ballooned from 0 to
  114,000+ µs and `hz` collapsed 50 → 8.3 in lockstep — the sensors and fusion loop were
  never the problem, `bleuart.write()` was blocking on a starved BLE link. Fixed in
  `firmware/08_ble_dashboard/08_ble_dashboard.ino` with `Bluefruit.configPrphBandwidth(BANDWIDTH_MAX)`
  before `Bluefruit.begin()` (wider MTU + notification queue), a relaxed connection
  interval (12,24 instead of the spec-floor 6,12), and connect/disconnect callbacks that
  log the negotiated MTU/interval so future sessions get hard numbers instead of
  guesswork. **Confirmed working live**: dashboard now holds ~47 Hz / 3.7 KB/s.
- **Calibration-settle bug fixed (probably).** With the smoothing slider dragged to its
  minimum (0.02), the hand's roll/pitch showed large, slowly-changing values (pitch
  50°→87° between two flat-and-still snapshots) — not noise, but the fusion filter still
  converging toward true gravity-referenced orientation out from under a `qRef` that was
  captured too early. Root cause: `finishCalibration()` in `tools/handrig_dashboard.html`
  resets every filter to identity then waits a fixed 600 ms before capturing the "zero"
  reference — fine at the default beta (0.06), nowhere near enough at 0.02. Bumped the
  wait to 2.5 s. **Not yet independently re-confirmed** — the next report from the user
  was about a *different* pose (tilted, not flat), so it's unclear yet whether the
  original flat-and-still case is actually fixed or just untested since the change.
- Live session also surfaced several real, distinct new issues, not yet fixed:
  1. **Pinky accel reads ~25-28% low in magnitude** (`|a| ≈ 0.72-0.77g` where a
     stationary sensor should read ~1.00g regardless of orientation) across every pose
     tested. Per-axis ratios against a working finger aren't a clean proportional scale,
     so it doesn't cleanly match a single known failure mode (not obviously one dead
     axis, not obviously a full-scale/config mismatch). The dashboard's existing
     `|a|` sanity check correctly flags it `bad accel` and freezes that finger's model
     segment straight rather than rendering garbage — the flagging logic is doing its
     job; the sensor itself is the open question. Intermittent: sometimes registers/moves
     after a recalibration, sometimes doesn't.
  2. **Thumb doesn't visually abduct (point sideways) at rest** — it renders pointing the
     same direction as the other fingers instead of the anatomically expected sideways
     angle. Suspect the hard-coded cosmetic "rest yaw" baked into the 3D rig
     (`tools/handrig_dashboard.html`, `anchors.THUMB.yaw`) is now double-counting or
     conflicting with the real sensor-derived relative rotation now that live thumb data
     actually works — not yet root-caused.
  3. **Hand orientation keeps drifting/rotating on its own when tilted palm-down
     (near-vertical)**, reported as still happening after the calibration-settle fix.
     Possibly the same convergence issue at a different beta setting, possibly a distinct
     weakness of gradient-descent Madgwick near-vertical (gimbal-adjacent) orientations —
     not yet distinguished; needs a controlled retest (flat vs. tilted, confirmed beta
     value) before touching code again.
  4. **No curl/flex indicator per finger yet** — requested as a new feature, not started.

**Problems & blockers:** Several genuinely new problems surfaced in the same session
(pinky accel magnitude, thumb rest pose, tilt-drift) that need to be diagnosed
independently rather than all being one bug — resisted the urge to guess-fix all of them
in one pass without controlled retests.

**Next:** Get controlled test data for the tilt-drift question (flat vs. tilted, with a
known beta value) before changing the fusion/rig code again. Root-cause the thumb
rest-pose rig math. Design and add the curl/flex readout. Physically inspect the pinky
connector/solder at the knuckle next time the glove is off-hand.

---

### 2026-07-25 | Phase 7.5 — Hardening the IMU path: v4 firmware (verify-by-readback + stuck watchdog) and the axis remap

**Plan:** Before reflashing, review the v3 fix written last session and close the gaps in it. The question that started the session was "would buying new IMUs fix the bad readings?" — answering that properly (no: the chips are fine, the init sequence was the fault) turned into a full hardening pass over the firmware and the dashboard.

**Achieved:**
- **Established that new hardware would not have helped.** The finger modules are MPU-6500/9250-family clones (`WHO_AM_I=0x72`) and replacements from the same market would overwhelmingly be the same clone, reproducing the identical bug. The fault was the init sequence, not the silicon. Worth recording because "replace the part" is the tempting and wrong first instinct here.
- **Rewrote `firmware/08_ble_dashboard/08_ble_dashboard.ino` as v4.** v3 wrote the right registers but discarded every `wReg()` return value, so a NACK was indistinguishable from success — including a NACKed *mux* select, which would silently write one finger's config to whichever channel was still latched. v4 adds, in order of how much each one was actually hiding:
  - **Config readback verification.** After init, `PWR_MGMT_1/2`, `GYRO_CONFIG`, `ACCEL_CONFIG` are read back and compared. An ACK only proves *something* answered; a matching readback proves *that chip* stored it. This is what makes "init succeeded" mean anything.
  - **Runtime stuck watchdog.** The boot check only ever saw boot — a sensor freezing ten minutes into a wear test was invisible. Now all six raw int16s are compared frame to frame; 50 consecutive bit-identical frames (~1 s) means frozen. Justification is numeric, not vibes: at ±4 g / 8192 LSB/g one LSB is 122 µg against the part's ~2–3 mg RMS noise floor (~20 LSB), so a working sensor physically cannot repeat exactly, even motionless on a table. Strictly stronger than the `|a| ≈ 1 g` check — **the original stuck thumb passed that test.**
  - **Full 6500-family reset**: poll `DEVICE_RESET` until it self-clears instead of a blind `delay(100)`, then `SIGNAL_PATH_RESET` + `USER_CTRL.SIG_COND_RST`, plus `ACCEL_CONFIG_2` (`0x1D`, a register that doesn't exist on a genuine 6050 — reserved there, so the write is a harmless no-op and one sequence serves both chip types).
  - **Checked writes and checked mux selects**, 3× init retry, and **I²C bus recovery** (bit-bang 9 clocks + STOP) for the case where a slave holds SDA low and wedges the bus — which makes all six sensors read garbage and looks like catastrophic hardware failure.
  - **Honest validity mask.** v3 zero-filled a failed read while leaving the mask bit set, so the dashboard fused a `(0,0,0)` accel vector — not a neutral value, but a claim that gravity has vanished. The bit now means "this frame's data is real."
  - **Frame checksum** (frame 79 → 80 B). `0xAB` is not a rare byte; it appears inside int16 payload constantly, so one dropped byte can false-sync the parser and render a full screen of plausible garbage — the same *symptom* as the clone bug, and it would have cost another CSV-forensics session to find.
  - Also fixed a latent indexing bug: `whoami[]` was indexed by mux channel while everything else used sensor id. Harmless only because `CH[i] == i` today.
- **Implemented the axis remap in `tools/handrig_dashboard.html`** — designed last session, never written. Raw sensor data was going straight into Madgwick. Fingers use the empirically confirmed `(x,y,z)→(x,z,−y)` (sensor `−Y`→fingertip, `+Z`→up).
- **Did *not* guess the hand sensor's forward axis.** Only one fact was measured (`az ≈ −0.98 g` flat palm-down ⇒ up = `−sZ`); which horizontal axis points at the fingers was never checked. Rather than bake a guess into source where it would be indistinguishable from the finger remap that *is* empirical, the four candidates satisfying the measured constraint are exposed in a **hand axes** dropdown — tilt the hand forward, pick the one where the model tips forward. All remaps are constrained to proper rotations (det +1) so the gyro (a pseudovector) transforms with the same matrix as the accel.
- Dashboard also now validates the checksum and re-hunts on mismatch, counts rejected frames in the header telemetry, skips fusion for mask-cleared sensors, and calibrates gyro bias in the *remapped* frame (bias must be measured in the frame it's later subtracted in). CSV export still records the **raw** sensor frame with a header comment saying so — the capture must stay re-interpretable if the remap changes.

**Problems & blockers:**
- **None of this is verified on hardware.** v4 is written and reviewed; the JS parses clean; the firmware has not been compiled or flashed, and the glove was not connected this session. This is the *same* state v3 was left in last session, and it is worth naming plainly rather than letting two unverified versions stack up.
- The hand remap default (`fwd +Y, up −Z`) is a starting guess by analogy with the finger mounting, not a measurement. It is expected to need changing via the dropdown on first connect.
- The stuck threshold (50 frames) and recovery interval (2 s) are reasoned from the noise floor but not empirically tuned against a real session; a false positive would show as a channel flickering out and re-initing.
- The frame length change (79 → 80 B) means **v4 firmware and the updated dashboard must be used together** — an old dashboard against v4 firmware will fail to sync entirely.

**Next:** Compile and flash `firmware/08_ble_dashboard/08_ble_dashboard.ino`, read the boot diagnostic on Serial (115200) with the glove flat and still, and confirm `6/6 sensors initialised` with every channel `OK`. Any channel reporting `STUCK`/`RAMP`/`BAD ACCEL`/`NOT FOUND` is now electrical — the init path is verified by readback, so go straight to that channel's solder joints, pull-ups and mux wiring. Then connect the dashboard, resolve the hand axes dropdown empirically (tilt forward, pick the option that tips the model forward), verify spread/abduction tracks correctly in the 3D view, and log the winning hand remap in `DECISIONS.md`. Watch `stuck=` in the periodic serial line and `bad frames` in the dashboard header across a full session before calling Phase 7.5 done.

---

### 2026-07-19 | Phase 7.5 — BLE live dashboard, found & fixed clone-IMU init bug

**Plan:** With all hardware now mounted on the glove (XIAO, mux, all 5 finger IMUs, power rails — from the 2026-07-18 session), build a live wireless dashboard: the XIAO streams all 6 IMUs over BLE, and a browser page shows the post-Madgwick-fusion 3D hand alongside each sensor's raw accel/gyro, so I can actually *see* my hand tracked live and confirm the whole chain works end to end (Phase 7.5 in `GENERAL_PLAN.md`).

**Achieved:**
- Wrote and flashed a first BLE streaming sketch (`bluefruit.h` NUS service, 79-byte binary frames, ~50 Hz) plus `tools/handrig_dashboard.html` (Three.js 3D hand, live accel/gyro trace canvases per sensor, in-browser calibration that measures gyro bias/noise over 10 s of stillness).
- Connected over Web Bluetooth and got live data — but 4 of the 5 finger sensors were clearly garbage (fingers flailing on their own, or frozen). Captured two raw CSVs via the dashboard's Export button (`data/phase7_5_ble_diagnostics/`) and went through them numerically instead of guessing.
- Diagnosed the pattern precisely: `thumb_gx` stuck at exactly `246.0938` every single row, `middle_ay` stuck at exactly `1.9688`, `ring_gx` ramping in a perfectly linear `±0x2000` LSB step per frame — not sensor noise, not drift, but digital init artifacts. Only `hand` (onboard LSM6DS3) and `pinky` (mux ch4) were clean.
- Root-caused it to the finger modules being MPU-6500/9250-family clones (`WHO_AM_I = 0x72`, not the genuine MPU-6050's `0x68`) that `MPU6050_light` never fully wakes (missing `PWR_MGMT_2` axis-enable write) — see `DECISIONS.md`.
- Rewrote the finger IMU driver as raw I²C (explicit reset → wake → enable-all-axes → configure), dropping `MPU6050_light` for the fingers entirely. Added a boot-time per-channel diagnostic (`WHO_AM_I` + 10-sample liveness/stuck-value check) so this class of bug is visible on Serial within 2 seconds of every boot from now on. New sketch lives at `firmware/08_ble_dashboard/08_ble_dashboard.ino` (v3).
- Confirmed the mux channel map against the physical build: thumb = ch0 (`SD0/SC0`), pinky = ch4 (`SD4/SC4`) — matches `hardware/WIRING.md`.
- Confirmed the finger sensor mounting axis convention empirically: sensor `-Y` → fingertip, sensor `+Z` → up. Also found the hand IMU (LSM6DS3) reads `az≈-0.98g` flat/palm-down — a different Z sense than the fingers — so the hand sensor needs its own axis handling, not the same one as the fingers.
- Ruled out the leukoplast tape (used to mount every finger sensor) as a cause of the garbage data — it's non-conductive and physically can't produce a stuck digital register; it remains a real but separate risk for *intermittent* dropouts from wire strain during flex.

**Problems & blockers:**
- The core bug looked at first like a fusion/calibration problem ("garbage in, garbage out no matter how I calibrate") — the actual fix was two layers below that, in the I²C init sequence, before any math ran. Lesson: when calibration "does nothing," check whether the raw bytes are even real before touching the filter.
- The dashboard's 3D model uses a different axis convention (`+Z=forward, +Y=up`) than either sensor's raw frame, so a per-sensor axis remap is needed before Madgwick. **This was designed (see `DECISIONS.md`) but not yet implemented** — `tools/handrig_dashboard.html` currently feeds raw sensor-frame data straight into fusion. Finger curl should already look roughly right (the mounting keeps that rotation axis aligned); spread/abduction will look wrong until the remap lands.
- v3 firmware (the clone-init fix) was written and reviewed but **not yet reflashed and reverified on the physical glove this session** — the boot diagnostic output confirming all 6 channels read `OK` is the first thing to check next time.

**Next:** Flash `firmware/08_ble_dashboard/08_ble_dashboard.ino`, read the boot diagnostic on Serial (115200) with the glove flat and still, and confirm all 6 sensors report `OK`. If any channel is still `BAD`/`SUSPECT` at boot, that's now electrical (solder joint, pull-ups), not firmware — go straight to that channel's connections. Then implement the `(x,y,z)→(x,z,-y)` axis remap for the fingers (and derive the hand sensor's own remap) in `tools/handrig_dashboard.html`, reconnect, and verify spread/abduction motion tracks correctly in the 3D view before calling Phase 7.5 done.

---

### 2026-07-18 | Phase 7 — full glove mount + wiring, all 6 IMUs confirmed reading

**Plan:** Mount the remaining loose components (XIAO, PCA9548A mux) onto the glove, wire all 5 finger IMUs to the mux and the mux to the XIAO with proper strain relief, then re-flash `firmware/04_all_imus_raw` to confirm all 6 sensors still read cleanly off the breadboard bench.

**Achieved:**
- All 5 finger MPU-6050s (thumb → pinky, middle phalanx / thumb proximal phalanx) mounted with leukoplast tape, snug with no play. Confirmed in earlier session's photos and re-confirmed today before wiring.
- XIAO + PCA9548A mux + a small breadboard mounted together on the wrist strap (breadboard used as the wiring hub between the finger jumpers and the mux/XIAO, rather than mux-and-XIAO going directly to bare wire splices) — see `docs/media/phase7_glove_mount_breadboard_wrist.jpg`.
- All five fingers wired back to the mux via jumper wire, routed loosely across the back of the hand (`docs/media/phase7_glove_mount_hand_top.jpg`, `phase7_glove_mount_fingers_wired.jpg`).
- **Flashed and ran the sketch — all 6 IMUs power up and read live**, confirmed visually by each finger sensor's onboard red LED lighting (`docs/media/phase7_glove_mount_sensors_live.jpg`) and by serial data streaming. This closes the electrical half of Phase 7: the glove-mounted wiring works, not just the breadboard bench wiring.
- **Ran the full 30-minute wear test — passed.** Continuous data throughout, no connection drop. The glove was taken off and put back on multiple times during the test (a harder condition than one continuous static wear — it re-flexes every knuckle run and re-seats every jumper each time) and every sensor kept reading afterward. Fit stayed snug and comfortable the whole session. **This closes Phase 7.**

**Problems & blockers:**
- **No capture file was saved from the wear test** — the 30-minute run and the on/off cycles were watched live in the Serial Monitor, not logged to `data/`. Nothing to run `tools/analyze_calibration.py` or `tools/plot_6imu_3d.py` against yet from the glove-mounted rig specifically.
- Wire routing is currently loose dupont jumpers, not strain-relief-taped at every knuckle per `hardware/WIRING.md`'s rule (anchor on both sides of each flex point, on the insulation not the pad) — visible in the photos as a loose bundle rather than tacked-down runs. The wear test surviving without this is a good sign, but it's still the most likely long-term failure point (fatigue accumulates over many more than one 30-minute session) and should get done before this rig sees regular use.
- No finger-identity-to-mux-channel table was captured from this exact wiring pass — `hardware/WIRING.md`'s channel-assignment table is still the *planned* mapping from Phase 3/4, not confirmed re-verified against the physical glove wiring today.

**Next:** Tape down strain relief at every knuckle crossing (cheap insurance now that Phase 7 is otherwise closed). Save an actual capture from the glove-mounted rig and run it through the existing analysis tools to confirm sensor health hasn't regressed from moving off the bare bench. Then: build a Python tool (`tools/`) that receives fused orientation data live over a wireless link (BLE or Thread/Zigbee — pick one, log the choice in DECISIONS.md) instead of USB serial, and visualizes the current finger pose in real time — this is the practical, watchable proof that Phase 6's `q_rel` math is working before committing to Phase 8's data collection. Then: Phase 8 labelled data collection, then Phase 9 (Edge Impulse classifier).

---

### 2026-07-17 | Phase 5 visualization fix + mounting-angle explanation, finger 5 mount anomaly found

**Plan:** Visualize the two Phase 5 captures (drift + movement) as roll/pitch/yaw time series, then investigate why the hand (onboard) sensor's readings differ so much from the five finger sensors even though everything sits on the same breadboard.

**Achieved:**
- **Wrote `tools/plot_fusion.py`** — first version had a real bug: it plotted `millis` timestamps as if they were roll, making it look like roll ramped to 45,000° over 30 seconds. Fixed the column indexing.
- **Diagnosed the hand-vs-finger angle gap.** Raw finger pitch sits near -75° to -80° while the hand sits near 0° — not a sensor fault. The finger MPU-6050 breakout modules are plugged straight into the breadboard (standing upright on their pin legs) while the XIAO sits closer to flat, so gravity lands on a different local axis for each. Verified with actual quaternion math (not guessed): a fixed +90° rotation about each finger sensor's local Y-axis brings fingers 1-4's roll and yaw into close agreement with the hand sensor, leaving a small residual pitch (9-16°, each finger's real resting tilt).
- **Finger 5 does not follow the pattern** — the same correction leaves it out of alignment with fingers 1-4 (yaw stays near 56° instead of settling near 0). Combined with finger 5's consistently elevated gyro noise across every capture this session and last, this points at finger 5 being seated at a genuinely different angle in its breadboard slot, not just a noisier unit.
- **Added the correction to `plot_fusion.py`** as an opt-out (`--no-mount-correction`), clearly documented as a rough, hand-picked, visualization-only fix — not a substitute for Phase 6's real `q_rel = conj(q_hand) ⊗ q_finger`, which will handle this properly and per-session regardless of how each sensor happens to be mounted.
- Regenerated `docs/media/phase5_drift_rpy.png` and `phase5_movement_rpy.png` with the correction applied; both now show fingers 1-4 clustering close to the hand's baseline, with finger 5 visibly offset. Logged the correction as a design decision in DECISIONS.md (2026-07-17).

**Problems & blockers:** None beyond the initial plotting bug (caught before it made it into the docs). The mount-angle explanation is inferred from the data and physical reasoning about how breadboard-mounted breakout modules typically sit, not confirmed by physically measuring the rig's angles — worth a quick visual check next session.

**Next:** Before glove-mounting, physically check finger 5's breadboard orientation against fingers 1-4 to confirm the mount-angle theory. Once on the glove, sensors will be mounted at deliberate, known angles (flat on each phalanx) so this particular ~90° bench artifact goes away — but the underlying lesson (compare `q_rel`, never raw absolute angles) carries forward permanently.

---

### 2026-07-17 | Phase 5 second pass — seeded orientation, two-stage β, first bench drift + movement data

**Plan:** Replace the first Madgwick fusion sketch with an improved version (accel-seeded initial orientation, two-stage β, roll/pitch/yaw output), then bench-test it with a still-hold drift capture and a movement capture, and give a final read on whether the 6 sensors are healthy and how to best configure them going forward.

**Achieved:**
- **Replaced `firmware/05_madgwick_fusion/05_madgwick_fusion.ino`** with the improved version: each sensor's Madgwick filter is now seeded from its own calibration-window accel average instead of starting at identity (`quatFromAccel()`), uses a two-stage β (`BETA_INIT=2.0` for 1.5 s after calibration, then `BETA_STEADY=0.033`), and the serial contract grew to `millis,sensor_id,qw,qx,qy,qz,roll_deg,pitch_deg,yaw_deg` with an optional raw-column tail (`INCLUDE_RAW`). Logged the seeding/two-stage-β design choice in DECISIONS.md.
- **Captured and analyzed two bench sessions**, saved under `data/phase5_madgwick_fusion/` with a new `tools/analyze_drift.py` (computes per-sensor roll/pitch/yaw drift in deg/min from first-vs-last sample):
  - `capture_01_movement.csv` (~29.5 s, deliberate movement, `SUBTRACT_GYRO_BIAS=1`) — confirms the fusion runs stably under motion (no NaNs, no stuck values, all 6 sensors keep reporting).
  - `capture_02_drift.csv` (~31.5 s, held still) — the actual drift test.
- **Calibration quality is now trustworthy**: gyro bias std is 0.05-0.35 deg/s across all six sensors (from `capture_01`'s embedded boot log), two orders of magnitude better than every Phase 4 capture (std 38-84 deg/s) — this window was genuinely held still. Finger 5 remains the noisiest sensor of the six (std ~3x the others), a finding that's now repeated across every capture taken so far.
- **No sensor dropouts in either capture** — all 6 report OK at boot and hold matched sample counts through both sessions. Finger 2's intermittent all-zero dropout (seen in both Phase 4 captures) did not reproduce here.
- **Drift result**: roll/pitch essentially flat (≤ ~1.7 deg/min, mostly < 0.5) — expected, gravity-anchored by Madgwick's accel correction regardless of gyro bias. Yaw crept at ~0.2-2.1 deg/min depending on sensor — small, and matches the predicted unbounded 6-DOF yaw drift (DECISIONS.md 2026-07-14), not a bug.
- **Rate dropped to ~84-86 Hz** (from Phase 4's ~93.6 Hz) — the added Madgwick math, Euler conversion, and extra printed columns cost real time inside the 10 ms tick budget.

**Final verdict on sensor health:** all 6 IMUs (onboard hand + 5 fingers) are electrically sound and read correctly. The intermittent finger-2 dropout seen twice in Phase 4 has not reproduced across two more sessions, but with only one clean run it should be called "not currently reproducing," not "fixed" — a marginal breadboard contact doesn't announce itself on a schedule. Finger 5 is consistently the noisiest unit (higher gyro std, and previously an outlier accel magnitude that has since resolved) but is not faulty — just the weakest of the six, worth an isolated single-channel re-check before fully trusting it in later phases. The calibration-window-not-still problem that flagged three Phase 4 captures in a row is gone in this session — the fix was capture discipline (physically hold the rig motionless), not code, exactly as suspected.

**How to stabilize / pre-configure for optimal reading (going forward):**
1. **Keep `SUBTRACT_GYRO_BIAS=1`** — the measured biases are non-trivial (e.g. finger 5's y-axis bias is -6.98 deg/s), and leaving them uncorrected would dominate any real drift measurement.
2. **Hold the rig on a fixed surface during the 10 s calibration window**, not in-hand — every prior "bad calibration" finding traced back to hand tremor during that window, never a code fault.
3. **Re-check finger 2's mux-channel-1 contact** before glove-mounting — reflow or replace the jumper, since its failure mode (intermittent, not permanent) is exactly what a marginal solder/breadboard contact looks like, and strain relief on the glove won't fix a connection that's already borderline.
4. **Bench-test finger 5 in isolation** (single-channel, no mux) to determine whether its elevated noise is intrinsic to that unit or still a contact-quality artifact.
5. **If 100 Hz is required before Phase 6**, trim per-tick serial output first (each `Serial.print` blocks on UART) — that's the most likely place the extra ~10 Hz went missing between Phase 4 and Phase 5.

**Problems & blockers:** Still missing a proper `SUBTRACT_GYRO_BIAS` on/off **paired** A/B drift capture from the same sitting — the current drift number is compared against Phase 4's uncorrected noise floor, not a same-session control. The drift capture was also only ~31.5 s; the sketch's own comment asks for "several minutes," so the deg/min figures should be treated as directionally right but not final. The 84-86 Hz rate shortfall hasn't been profiled to find exactly which added step costs the most.

**Next:** Capture a same-session bias-on/bias-off drift pair, run one multi-minute (5+) still-hold drift test for a solid deg/min number, and re-check finger 2's physical contact before moving to glove-mounting. Once drift is confirmed acceptable, move on to Phase 6 (`q_rel = conj(q_hand) ⊗ q_finger`, re-zero pose, skeleton viz).

---

### 2026-07-17 | Phase 4 re-check + Phase 5 first pass — Madgwick fusion written, sensor health re-verified

**Plan:** Before moving forward, re-run the Phase 4 six-sensor sketch to confirm all 6 IMU connections are still good, then write the first Madgwick fusion implementation for Phase 5, with the intent of mounting all sensors on the glove soon and moving toward Phase 6 (relative orientation).

**Achieved:**
- **Re-ran `firmware/04_all_imus_raw/04_all_imus_raw.ino`** and captured a fresh ~15 s full session (`data/phase4_six_imu_capture/capture_03_full_session.csv`), analyzed with `tools/analyze_calibration.py` and re-plotted with `tools/plot_6imu_3d.py` (`docs/media/phase4_6imu_accel_3d_capture03.png`/`.gif`).
- **All 6 sensors initialize and read correctly** — no dead channel at boot.
- **Measured rate: ~93.6-93.7 Hz**, not the 100 Hz target, from the firmware's own `# rate_hz=` log lines — the six sequential mux-switch+read cycles cost more than the naive 10 ms tick budget allows. Recorded as an open item in `firmware/04_all_imus_raw/README.md`.
- **Calibration window (10 s) still wasn't genuinely still** — printed gyro bias/std table shows 38-84°/s std across all six sensors, an order of magnitude above a real at-rest noise floor. Third capture in a row with this same finding; it's confirmed as a capture-discipline problem (rig gets moved before/during the window), not a firmware bug.
- **Finger 2 (mux channel 1) had another intermittent dropout** — all-zero readings for the last ~340 ms of this session (vs. a full-session dropout in the earlier `capture_02`). Two different dropout windows on the same channel across two sessions points at a loose physical contact (breadboard jumper), not a code fault — worth watching once mounted on the glove, where proper strain relief should help.
- **Finger 5's earlier elevated accel magnitude (~1.23 g) did not reappear** in this run — likely was contact-quality noise in the previous session rather than a persistent hardware issue on that channel.
- **Wrote `firmware/05_madgwick_fusion/05_madgwick_fusion.ino`** — first real implementation, replacing the placeholder `main.cpp`. Reuses Phase 4's mux switching, per-sensor read, and boot-time gyro-bias calibration, and adds one independent Madgwick filter instance per sensor (gradient-descent IMU fusion, no magnetometer), emitting the project's fused contract `millis,sensor_id,qw,qx,qy,qz`. β left at 0.1 (Madgwick's published default), untuned. Logged the Madgwick-vs-Mahony-vs-complementary-filter choice in DECISIONS.md (2026-07-17).

**Problems & blockers:** Not yet flashed/bench-tested — this session's Phase 5 work is code only, no verification yet that the quaternions behave correctly under real rotation (hold-flat-near-identity, slow-360°-return-to-start). The 93.6 Hz rate shortfall and the intermittent finger-2 contact are both still open from Phase 4 and haven't been root-caused (mux/read timing profiling and physical contact fix, respectively). Didn't get to mounting sensors on the glove or starting Phase 6 this session — bench-level fusion needs to be verified first.

**Next:** Flash `05_madgwick_fusion.ino`, verify no NaNs, check the flat-hold-near-identity and slow-rotation-returns-to-start behavior, and record measured drift before/after calibration (the phase's actual deliverable). Then mount all 6 sensors on the glove with proper strain relief and start Phase 6 (`q_rel = conj(q_hand) ⊗ q_finger`, re-zero pose, skeleton viz).

---

### 2026-07-17 | Phase 4 — full 6-sensor sketch (accel + gyro + calibration), rest-window analysis flags a bad "still" capture

**Plan:** Extend the mux/5-finger sketch to the full Phase 4 target: read the
onboard hand IMU alongside all 5 fingers, add accelerometer, emit the real
serial contract, and add a still-calibration + rate-measurement routine.

**Achieved:**
- Rewrote `firmware/04_all_imus_raw/04_all_imus_raw.ino`: all 6 sensors
  (onboard LSM6DS3 + 5 finger MPU-6050s), accel + gyro, real
  `millis,sensor_id,ax,ay,az,gx,gy,gz` contract, `millis()`-scheduled ~100 Hz
  loop, a 10 s boot-time still-calibration window that accumulates per-sensor
  gyro mean/std and prints a bias table, and a periodic achieved-rate report.
- Captured a bench run and saved the opening calibration-window excerpt to
  `data/phase4_six_imu_capture/capture_01_raw.csv` (the full ~9.8 s capture
  was too large to transcribe by hand — see that folder's README).
- Wrote `tools/analyze_calibration.py` and ran it on the excerpt: all six
  sensors show sane accel magnitudes (~1.0-1.25 g), confirming they're alive
  and reading real gravity.

**Problems & blockers:**
- **The "still" calibration window wasn't still.** The hand sensor's gZ
  climbs monotonically from -10.43 to -35.00 deg/s across the 16 saved
  samples (~160 ms) — that's real angular acceleration, meaning the rig was
  being moved during the "Calibrating... hold still" phase. The large
  resting-gyro means seen on the fingers (15-25 deg/s) are an artifact of
  that motion, not their true zero-rate bias. **A genuinely motionless
  capture is still needed** before the bias table means anything.
- **Finger 5 is an outlier**: accel magnitude 1.246 g (vs ~1.0-1.02 g for
  the others) and gyro noise std 5-13 deg/s (vs 1-3 deg/s) — worth
  re-checking that sensor in isolation (loose connection on its mux channel
  is the first suspect).
- The full multi-thousand-line capture couldn't be persisted to the repo
  from a chat paste — only the calibration-window excerpt was saved at
  first. **Resolved within the same session**: the full session log turned
  up saved as a plain file (`datalog.txt.txt`, 5052 lines) rather than
  pasted text — moved into `data/phase4_six_imu_capture/capture_02_full_session.csv`
  and analyzed directly. That let the earlier excerpt-only findings above be
  checked against the complete run.

**Full-session findings (`capture_02_full_session.csv`, ~8.7 s, all 6
sensors) — supersede the excerpt guesses above:**
- **Finger 2 (mux channel 1), not finger 5, is the sensor that drops out** —
  and it's not intermittent: it goes to a permanent `0,0,0,0,0,0` at
  millis=1468 and never recovers for the remaining ~8.3 s of the run (801 of
  841 samples). Confirms the "exact zeros = dead registers, not noise"
  diagnosis from earlier in this session — a live MPU always carries ~1 g of
  gravity somewhere. Visible directly in the new
  `docs/media/phase4_6imu_accel_3d.png` (trajectory stops dead at the
  origin) and `docs/media/phase4_6imu_accel_3d.gif` (one arrow freezes while
  the other five keep swinging).
- **Confirmed at full scale**: the whole capture sits inside the firmware's
  declared 10 s calibration window, yet every live sensor's gyro std across
  the run is 25-102 deg/s — nowhere near a still-capture noise floor. The
  "hold still" instruction was not followed for this run; the bias table
  this sketch would print from it is not usable.
- Wrote `tools/analyze_calibration.py` (already existed) and added
  `tools/plot_6imu_3d.py` (new — static 3D trajectory + animated 3D vector
  GIF) to produce these findings and visuals.

**Harder problems worked through this session (worth remembering):**
- **Onboard IMU is a "trunk" device, not a mux channel.** The LSM6DS3TR-C
  lives on the same D4/D5 bus as the PCA9548A at a fixed `0x6A`, which
  doesn't collide with the mux (`0x70`) or the finger MPUs (`0x68`, only
  reachable *through* the mux). The fix: write `0x00` to the mux
  (`tcaDisable()`) to deselect every channel before touching `0x6A` — read it
  like any other bus device, no special-casing needed beyond that one write.
  Forgetting this deselect is a plausible-looking-data trap: whichever finger
  channel was last selected stays wired through, so the "onboard" reading is
  silently actually a finger's.
- **Axis labels legitimately differ between the onboard chip and the
  breadboard MPUs, and that's not a bug.** The onboard LSM6DS3 is soldered
  flat on the XIAO in its own orientation; the finger MPUs sit in a different
  orientation on the breadboard. On a flat, still rig this shows up as
  gravity landing on *different* accel axes per sensor (onboard: ~1 g on Z;
  fingers: ~1 g on X) — same physical "down," different local axis. Any
  fusion math later has to account for each sensor's own mounting frame, not
  assume a shared axis convention.
- **A sensor reading exact `0.0000,0.0000,0.0000,0.00,0.00,0.00` means the
  chip ACKed on the bus but its data registers are dead** (asleep or reset) —
  never a real reading, since a live MPU always carries ~1 g of gravity
  somewhere. Finger 5 (mux channel 3) dropped to this exact all-zero pattern
  mid-session, having worked earlier in the same run — the fingerprint of an
  intermittent physical contact (loose jumper on VCC/GND/SDA/SCL for that
  channel), not a code bug. Diagnosed a targeted software mitigation for
  next time: in the per-frame read, if `|ax|+|ay|+|az|` comes back under a
  small threshold, re-run that sensor's `begin()` and re-read once before
  moving on — a live-but-glitched sensor re-wakes within one frame instead of
  streaming zeros for the rest of the run. **Not yet added to the sketch** —
  flagged for the next firmware pass, with the caveat that a fully
  disconnected wire will just add a failed-init retry cost every frame, so
  watch the `# rate_hz=` line for a sag if this is leaned on instead of fixing
  the wire.

**Next session — move off the breadboard onto the glove:**
1. **Fix finger 2's channel-1 connection properly before mounting** —
   confirmed dead (permanent all-zero from millis=1468 onward) in the full
   session capture; reseat or re-solder (breadboard jumpers are exactly the
   kind of loose contact that caused today's dropout, and glove wiring needs
   to be more reliable than a breadboard, not less).
2. **Physically mount the XIAO, PCA9548A, and all 5 MPU-6050s on the glove**:
   finger sensors on the middle phalanx (thumb on proximal), hand IMU
   (onboard XIAO) flat and rigid on the back of the hand. Follow
   `hardware/WIRING.md`'s strain-relief rules — anchor every wire run on the
   insulation (not the solder pad) on both sides of each knuckle, stranded
   28-30 AWG wire only, flex-test 20x per finger before trusting continuity.
   Assign the real thumb/index/middle/ring/pinky-to-channel mapping in
   `hardware/WIRING.md` once wiring is physically committed (it's currently
   just placeholder `IMU0..IMU4` labels from the bench rig).
3. **Reconnect everything and re-run `firmware/04_all_imus_raw/04_all_imus_raw.ino`
   as-is first** — confirm all 6 sensors still read cleanly after the move
   from breadboard to glove before changing anything else. Wiring that
   worked flat on a breadboard is not guaranteed to survive being bent
   around knuckles; that's exactly what this re-test is for.
4. **Capture a genuinely still calibration run** (rig at rest, hand relaxed,
   nobody touching it) to finally get a trustworthy bias/noise table — this
   was blocked all of today's session by the rig moving during "hold still."
5. Once 6-sensor reads are solid on the glove: add the self-heal retry for
   dropped sensors, confirm the achieved rate from `# rate_hz=`, then this
   closes Phase 4 and Phase 7 (glove mount) together.

---

### 2026-07-16 | Phase 3/4 — mux bring-up + all 5 finger IMUs reading coherently

**Plan:** Get the serial bus working with all 5 finger sensors — bring up the
PCA9548A mux, read the data from the MCU (hand IMU) and all 5 finger sensors,
then finally mount all the components (the MCU, the 5 IMUs, and the mux/serial
bus) onto the glove.

**Achieved:**
- Wired the PCA9548A on a breadboard: XIAO D4/D5 → mux SDA/SCL, mux VIN/GND →
  3V3/GND shared rail, A0/A1/A2 → GND (mux address `0x70`), RST → 3V3 (held
  high, active-low). All five MPU-6050 clones sit on mux channels 0-4
  (SD0/SC0 .. SD4/SC4), every one with AD0 → GND (address `0x68` — identical
  across all five; the mux is the only thing that tells them apart). Photos:
  `docs/media/phase3-4_breadboard_top.jpg`, `docs/media/phase3-4_breadboard_angle.jpg`.
- Wrote `firmware/04_all_imus_raw/04_all_imus_raw.ino`: one `MPU6050_light`
  object reused across channels per sensor, a `tcaSelect()` helper that writes
  the one-hot channel byte to `0x70` before every access, and a boot-time
  `scanChannels()` sweep. That sweep found `0x68` on channels 0-4 with nothing
  on 5-7 and no cross-talk — mux switching confirmed working (closes Phase 3,
  no separate isolated-channel sketch needed).
- Streamed gyro (deg/s) from all 5 finger sensors live over serial at ~50 Hz
  (`delay(20)`-paced, not yet the target `millis()`-scheduled 100 Hz loop).
  Captured a hand-motion bench run — `data/phase3-4_five_imu_gyro/movement_test.csv`
  (41 samples, gyro only) — and wrote `tools/analyze_multi_imu.py` +
  `tools/plot_multi_imu.py` to check it, producing
  `docs/media/phase3-4_five_imu_movement.png`.
- **The data checks out:** all five sensors track the same physical rotation
  (Pearson r vs. IMU0 on the dominant Y-axis swing: IMU1 0.999, IMU2 0.994,
  IMU3 0.986, IMU4 0.975 — falling off slightly with "wiring distance" from
  IMU0, consistent with sequential-read timing skew, not a bad sensor).
  Cross-sensor spread (std across the 5 sensors per sample, averaged over the
  whole run) is small — gx 0.61°/s, gy 1.44°/s, gz 0.90°/s — confirming no
  dead, duplicated, or cross-talking channel.

**Problems & blockers:**
- This capture is gyro-only (no accel yet) and the sketch doesn't emit the
  project's `millis,sensor_id,ax..gz` serial contract — it prints a
  human-readable `IMUn [gx, gy, gz]` line instead, and timestamps in the saved
  CSV are the Serial Monitor's host-side receive time, not device `millis()`.
  Fine for this bring-up check, but the contract rework has to happen before
  this feeds into fusion.
- No clean "at rest" calibration baseline was captured this session — the
  bench-motion CSV never holds fully still, so the noise numbers above
  (frame-to-frame std in the calmest 9-sample stretch: gx 1.97°/s, gy 0.69°/s,
  gz 0.50°/s) are an upper bound, not a proper per-sensor bias table. A
  deliberate "sit still for 10s" capture is still needed.
- The onboard XIAO hand IMU (sensor 0) isn't wired into this sketch yet —
  Phase 4 isn't closed until it's reading alongside the five fingers in the
  same loop.
- The glove-mounting step (MCU + 5 IMUs + mux physically on the glove,
  Phase 7) did **not** happen this session — everything above is still on a
  breadboard. That's next, not done.

**Next:**
1. Add the onboard LSM6DS3 (hand reference, sensor 0) into the same loop as
   the five fingers.
2. Rework the print loop to emit the real `millis,sensor_id,ax,ay,az,gx,gy,gz`
   contract (add accel while at it) and switch from `delay(20)` to a
   `millis()`-scheduled loop; measure the real achieved rate from the
   timestamps rather than assuming 100 Hz.
3. Capture a deliberate still-calibration log for a proper per-sensor gyro
   bias table.
4. Only once the six-sensor bench read is solid: move the MCU, mux, and five
   IMUs onto the glove (Phase 7) with strain relief per `hardware/WIRING.md`,
   and re-verify — bench-solid isn't glove-solid until the wires have taken a
   bend.

---

### 2026-07-14 (evening) | Phase 2 — first external MPU-6050 alive, raw accel + gyro plotted

**Plan:** Wire up one MPU-6050 straight to the XIAO (no mux yet) and get raw accel
and gyro out over serial. Goal was just to prove a single finger sensor works
before I add the multiplexer, since debugging one sensor is a lot easier than
debugging five behind a mux.

**Achieved:**
- Wired it with four lines — VCC→3V3, GND→GND, SDA→D4, SCL→D5 — and tied AD0 to
  GND so it sits at `0x68`. Diagram's in `hardware/WIRING.md` now.
- Hit a wall first though: the Adafruit MPU6050 example just printed
  `Failed to find MPU6050 chip!` and halted. Ran an I²C scanner to check — it
  found a device at `0x68`, so the wiring was clearly fine. Then I read the
  `WHO_AM_I` register (0x75) directly and it came back **`0x72`**, not `0x68`.
  So the "MPU-6050" I have is actually a clone (the 0x72 points to the
  MPU-6500/9250 family), and Adafruit's driver checks WHO_AM_I strictly and
  refuses anything that isn't exactly 0x68.
- Swapped to `MPU6050_light`, which doesn't gate on that check — worked
  immediately. It also does bias calibration (`calcOffsets()`) in one call and is
  small enough to actually read. The whole fork is written up in DECISIONS.md, and
  I added an `i2c_scan` diagnostic sketch so the 0x68-present / WHO_AM_I=0x72
  finding is reproducible, not just a story.
- Milestone sketch `02_single_mpu6050_test.ino` streams the full contract line
  (`millis,sensor_id,aX,aY,aZ,gX,gY,gZ`) at 400 kHz. I also kept the two stripped
  diagnostic sketches I actually flashed to grab clean single-axis-set streams —
  `diagnostics/gyro_raw/` and `diagnostics/accel_raw/`. Arduino IDE only compiles
  one sketch per folder so each got its own subfolder.
- Captured both streams by hand-waving the sensor around then setting it still,
  saved them under `data/phase2_single_mpu6050/`, and wrote `tools/plot_imu_3d.py`
  to draw each as a 3D path coloured by time. PNGs are in `docs/media/`.
- The plots actually told me something. The accel one sits on a ~1 g sphere like
  it should (gravity is constant magnitude), with a tight cluster where I put it
  down at the end — that's the sanity check that calibration and axes are right.
  The gyro one loops way out to ±100–240 deg/s on the fast twists and comes back
  toward zero when I stop. First `requirements.txt` landed too (numpy, matplotlib
  pinned).

**Problems & blockers:** The clone chip is the one to keep an eye on — it works
now, but a clone can differ from a real MPU-6050 in register defaults, self-test,
or full-scale calibration, so if the Madgwick fusion behaves oddly later this is a
prime suspect. All five finger modules came from the same batch, so odds are
they're all 0x72 clones; I should scan every one when they go on. Separately, the
gyro doesn't return to a clean zero at rest — a couple deg/s of leftover bias even
after `calcOffsets()`. Not a bug, that's the drift the filter has to fight, but
good to see it this early. Library version now recorded (MPU6050_light 1.2.1);
board-package version still a placeholder, and still no breadboard photo — that
media slip from Phase 1 is open. Left the bench-only `while(!Serial)` in the
milestone sketch on purpose, flagged in a comment.

**Next:** the road from here is a straight line —
1. **Set up the bus** (Phase 3): bring in the PCA9548A mux at `0x70`, select a
   channel, and reach the same `0x68` clone *through* it. Run the WIRING.md
   pre-flight checks (master-side pull-ups, 400 kHz) first.
2. **Read everyone at once** (Phase 4): loop over all five finger sensors behind
   the mux *plus* the XIAO's onboard IMU (the hand reference), and stream all six
   at a steady 100 Hz. Scan each finger module as it goes on — they're probably
   all the same `0x72` clone.
3. **Put it on the glove** (Phase 7): once the six-sensor read is solid on the
   bench, mount everything onto the left glove, strain-relieve every knuckle run,
   and re-verify — bench-solid is not glove-solid until the wires have taken a bend.

---

### 2026-07-14 (later) | Repo audit — docs brought in line with reality, two risks surfaced

**Plan:** Full technical audit of the repo: architecture, the two working sketches, the docs system, and the forward plan.

**Achieved:**
- **Surfaced the yaw-drift risk** (the big one): 6-DOF sensors have no yaw reference, so the yaw of `q_rel` drifts unboundedly even with perfect calibration. Mitigation decided and logged in DECISIONS.md: gravity-referenced features + a "flat hand" re-zero pose. Phases 5/6 deliverables updated to include measured drift numbers and a time-dimension acceptance test.
- **Computed the I²C bus budget:** at the default 100 kHz, five muxed MPU-6050 reads ≈ ~10 ms — the entire 100 Hz budget. 400 kHz required; baked into Phase 4 and WIRING.md pre-flight checks.
- **Fixed the toolchain fiction:** README claimed PlatformIO + `pio run`; reality is Arduino IDE + `.ino`. README now documents the real workflow; the fork is logged in DECISIONS.md with PlatformIO migration deferred.
- **Aligned sketch 01 with the serial contract** (`millis,sensor_id,...` — was missing timestamp + id), flagged `while(!Serial)` as bench-only, deleted the stale `tree.md`, ticked Phases 0–1, added GY-521 LDO / pull-up pre-flight checks to WIRING.md, added five new gotchas to CLAUDE.md.

**Problems & blockers:** No devlog entry or media captured for Phase 1 yet — the media-discipline rule slipped in the very first phase. Board-package/library versions not yet recorded (placeholders left in `01`'s README).

**Next:** Re-flash sketch 01 to confirm the contract-format output, screenshot the serial trace + photo the LED test into `docs/media/`, fill in the version placeholders, write the Phase 1 devlog entry. Then Phase 2: single MPU-6050 on D4/D5 — run the WIRING.md pre-flight checks first.

---

### 2026-07-14 | Phase 1 — First light: MCU + onboard IMU alive

**Plan:** Electrically verify the Seeed XIAO nRF52840 Sense for the first time — get it
flashing, then read its onboard 6-DOF IMU. This is the first gate: is the board even alive?

**Achieved:**
- **Got the board flashing.** It initially would *not* connect / show up as a
  programmable port. Fix: **double-tap the RESET button** to force the nRF52840 into UF2
  bootloader mode — after that the port enumerated and uploads worked. Set up the Arduino
  IDE with the Seeed board package URL and installed the `seeed nrf52` boards.
- **LED sanity test passing** → new milestone folder `firmware/00_led_sanity_test/`
  (`.ino`). Cycles the onboard RGB user-LED red → green → blue, 500 ms each. Confirmed the
  full toolchain + USB + bootloader + MCU are good. Noted the LED is **active-LOW**
  (`LOW` = on).
- **Onboard IMU reading** → filled in `firmware/01_xiao_imu_test/main.cpp` with real code
  using the [Seeed_Arduino_LSM6DS3](https://github.com/Seeed-Studio/Seeed_Arduino_LSM6DS3)
  library. Streams `aX,aY,aZ,gX,gY,gZ` CSV at 115200 baud. Key detail: the onboard
  LSM6DS3TR-C answers at I²C **`0x6A`** (not `0x68`, which is the finger MPU-6050s).
- **Reference doc** → captured the full XIAO spec sheet, pin map, both pinout images
  (front/back), and the "which of the two Seeed libraries to install" note in
  `hardware/datasheets/XIAO_nRF52840_Sense.md`.

**Problems & blockers:** The board-not-connecting scare at the start (resolved by the
double-tap-RESET trick — worth remembering, it'll happen again). No IMU issues once the
right address (`0x6A`) and library were in place.

**Next:** Move to `firmware/02_single_mpu6050_test/` — wire up one external MPU-6050
(GY-521) on the D4/D5 I²C bus and confirm a single finger sensor reads at `0x68`, before
introducing the PCA9548A mux.

---

### 2026-07-10 | Phase 0 — GitHub repo scaffold

**Plan:** Create a well-structured, rigid GitHub repository where I can properly document progress, test firmware milestone by milestone, and share the build publicly as a portfolio piece.

**Achieved:** Full repo scaffold in place — `README.md`, `GENERAL_PLAN.md`, `DECISIONS.md`, `DOCUMENTATION.md`, seven numbered firmware milestone folders (`01`–`07`) with placeholder stubs, `hardware/BOM.md`, `hardware/WIRING.md`, `tools/`, `data/`, `ml/`, and `docs/log/` templates. Remote set to `https://github.com/PiyushPapaya/Cheirograph`. Initial commit made locally.

**Problems & blockers:** None with the scaffold itself. Components are in hand and soldered but not yet electrically verified — that's the next gate.

**Next:** Get the XIAO nRF52840 Sense connected to the laptop, install PlatformIO, find a suitable Arduino library for the onboard LSM6DS3, and run the first serial read to confirm the MCU and onboard IMU are alive.

---

### 2026-07-03 | Phase 0 — Component arrival and soldering

**Plan:** Unpack the ordered components, inspect for external damage, and solder the header pins on the PCA9548A mux and all five MPU-6050 breakout boards.

**Achieved:** Everything arrived. Soldered header pins on the PCA9548A (bus driver) and all five GY-521 / MPU-6050 modules. No signs of external shipping damage on any board.

**Problems & blockers:** Electrical functionality still unconfirmed — visual inspection and soldering done, but no firmware run yet. Some product reviews had mentioned units occasionally arriving dead or with cold joints from the factory, so this stays an open question until first power-on.

**Next:** Create the GitHub project structure so testing is properly documented from the first run.

---

### 2025-07-27 | Phase 0 — Project planning and component research

**Plan:** Form a rough project concept; decide where each sensor, MCU, and component would physically go on the glove; and think through the hard problems before ordering anything — specifically: the I²C address collision with five MPU-6050s all defaulting to `0x68`, noise in the raw IMU data and how to filter it, and how to ultimately deploy a trained ML model on the MCU. Then order the final component list.

**Achieved:** After several hours of research, settled on the architecture (PCA9548A mux to resolve the `0x68` collision, Madgwick filter for noise/fusion, Edge Impulse + on-device TinyML for classification) and confirmed component compatibility. Ordered the full BOM:

| Part | Role | Notes |
|---|---|---|
| Seeed XIAO nRF52840 Sense | MCU + hand-reference IMU + BLE | Onboard LSM6DS3 on internal I²C; **not** behind the mux |
| 5× MPU-6050 (GY-521) | Finger IMUs | All at I²C addr **0x68**; sit behind the mux |
| PCA9548A | 8-channel I²C multiplexer | Addr **0x70**; selects one finger IMU at a time |
| Half-finger glove (left) | Substrate | Finger IMUs on middle phalanx; thumb on proximal phalanx |
| Leukoplast tape / cable ties | Mounting + strain relief | Wires will fatigue at the knuckles — anchor every run |

**Problems & blockers:** Product reviews flagged that some MPU-6050 units occasionally arrive with factory defects or dead on arrival. No way to know until they're powered up.

**Next:** Wait for delivery; on arrival, inspect for external damage, solder headers, and test each component individually.
