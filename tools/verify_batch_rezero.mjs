#!/usr/bin/env node
// verify_batch_rezero.mjs - auto re-zero (healRezero) must not touch qRef while Batch Capture is
// active. Replays the real session of 2026-11-07: full calibration, then the guided run (re-zero is
// off there by design), then the FLATCHECK window, where the hand lies in the calibration pose and
// re-zero is allowed to slide every sensor's zero onto its current orientation.
// In the recorded session the hand and thumb lie 11 to 14 deg away from their calibration "up"
// during FLATCHECK, outside the 8 deg pose window, so real re-zero never fires there. To make the
// window live, calUp is re-anchored to the current gravity vector at FLAT.f0 + 520 (the hand then
// sits in its "calibration pose" by construction). Same anchoring in both cases.
// Case 1: batchActive=true over FLATCHECK -> every qRef unchanged (< 0.01 deg).
// Case 2: batchActive=false, same frames -> qRef moves. Proves the test can see the bug.
// Usage: node tools/verify_batch_rezero.mjs [page.html]
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { loadPage, frameOf } from "./selftest_replay_lib.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const page = process.argv[2] ? resolve(process.argv[2]) : undefined;
const cal = JSON.parse(readFileSync(join(here, "..", "10-touch-detection", "calibration_2026-11-07_v3.json"), "utf8"));
let failed = 0;
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) failed++; };

const rows = cal.raw.rows, t0 = rows[0][0];
const STILL = cal.marks.find(m => m.name === "STILL");
const FLAT = cal.marks.find(m => m.name === "FLATCHECK");
const ANCHOR = FLAT.f0 + 520;
const qAngle = (a, b) => 2 * Math.acos(Math.min(1, Math.abs(a.w*b.w + a.x*b.x + a.y*b.y + a.z*b.z))) * 180 / Math.PI;

function run(batch) {
  const L = loadPage(page);
  cal.session.sensors.forEach((s, i) => { L.ACC_OFFSET[i] = s.accOffset.slice(); });
  L.setHandMount(cal.session.mount.psiDeg * Math.PI / 180);
  L.startCal("initial");
  L.setMode({ phase: "still" }, null);
  let refs0;
  for (let i = 0; i < FLAT.f1; i++) {
    L.T.now = rows[i][0] - t0;
    if (i === STILL.f1) { L.finishCalibration(); L.setMode({ phase: "run" }, null); }
    if (i === FLAT.f0) L.setMode(null, null);
    if (i === ANCHOR) {
      L.S.forEach(st => { const n = Math.hypot(...st.aSmooth); st.calUp = st.aSmooth.map(v => v / n); });
      L.setBatch(batch); refs0 = L.qRefs();
    }
    L.parseFrame(frameOf(rows[i], i));
  }
  const refs1 = L.qRefs();
  return Math.max(...refs0.map((q, k) => qAngle(q, refs1[k])));
}

const on = run(true), off = run(false);
check(on < 0.01, `batchActive: qRef of every sensor unchanged over FLATCHECK, max ${on.toExponential(2)} deg (limit 0.01)`);
check(off > 0.1, `control, batchActive=false: qRef moves ${off.toFixed(3)} deg (must be > 0.1)`);
console.log(failed ? `\n${failed} check(s) failed` : "\nall ok");
process.exit(failed ? 1 : 0);
