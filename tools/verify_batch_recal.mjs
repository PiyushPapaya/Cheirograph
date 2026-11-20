#!/usr/bin/env node
// verify_batch_recal.mjs - the between-rep recal in Batch Capture must refresh gyro bias only
// and never move the zero pose (qRef). Replays the real session of 2026-11-07: full calibration
// on the flat hand, then the hand holds a fist (FIST mark) while a 5 s recal runs. If the recal
// re-zeroed, the fist would become the new "flat" and the index curl would collapse to ~0.
// Control: the same run with a full calibration in place of the recal must move the pose by
// more than 20 degrees, which proves this test can see the bug.
// Usage: node tools/verify_batch_recal.mjs [page.html]
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
const F_REC0 = 2000, F_REC1 = 2250;                 // inside FIST (2006 hold .. 2511)
const angle = (a, b) => 2 * Math.acos(Math.min(1, Math.abs(a[0]*b[0] + a[1]*b[1] + a[2]*b[2] + a[3]*b[3]))) * 180 / Math.PI;
const qAngle = (a, b) => 2 * Math.acos(Math.min(1, Math.abs(a.w*b.w + a.x*b.x + a.y*b.y + a.z*b.z))) * 180 / Math.PI;
const meanQ = qs => { const m = [0, 1, 2, 3].map(k => qs.reduce((s, q) => s + q[k], 0) / qs.length), n = Math.hypot(...m); return m.map(v => v / n); };

function run(kind) {
  const L = loadPage(page);
  cal.session.sensors.forEach((s, i) => { L.ACC_OFFSET[i] = s.accOffset.slice(); });
  L.setHandMount(cal.session.mount.psiDeg * Math.PI / 180);
  L.startCal("initial");
  L.setMode({ phase: "still" }, null);
  let before = [], after = [], refs0, bias0, bias1;
  for (let i = 0; i <= F_REC1 + 30; i++) {
    L.T.now = rows[i][0] - t0;
    if (i === STILL.f1) { L.finishCalibration(); L.setMode({ phase: "run" }, null); }
    if (i === F_REC0) { refs0 = L.qRefs(); bias0 = L.bias(2); if (kind !== "none") L.startCal(kind); }
    if (i === F_REC1 && kind !== "none") L.finishCalibration();
    L.parseFrame(frameOf(rows[i], i));
    if (i >= 1980 && i < 2000) before.push(L.handRelQuat(2));
    if (i >= F_REC1 + 10 && i < F_REC1 + 30) after.push(L.handRelQuat(2));
    if (i === F_REC1) bias1 = L.bias(2);
  }
  const refs1 = L.qRefs();
  return { dq: angle(meanQ(before), meanQ(after)), qAfter: meanQ(after), refMax: Math.max(...refs0.map((q, k) => qAngle(q, refs1[k]))), bias0, bias1 };
}

// Baseline: the same replay with NO recal. The fist is not perfectly still (the finger keeps
// settling, ~2 deg over this window), so the recal is judged against that, not against zero.
const n = run("none"), r = run("recal");
const dRecal = angle(n.qAfter, r.qAfter);
check(dRecal < 1, `recal keeps the pose: index q_rel differs ${dRecal.toFixed(3)} deg from a run with no recal (limit 1; natural settling ${n.dq.toFixed(2)} deg)`);
check(r.refMax < 0.01, `qRef of every sensor unchanged: max ${r.refMax.toExponential(2)} deg (limit 0.01)`);
const dB = Math.max(...r.bias0.map((v, k) => Math.abs(v - r.bias1[k])));
check(dB > 0 && dB < 3, `index bias refreshed: max change ${dB.toFixed(3)} deg/s (0 < d < 3)`);
const c = run("initial");
check(c.dq > 20, `control, full calibration in the fist: pose moved ${c.dq.toFixed(1)} deg (must be > 20)`);

console.log(failed ? `\n${failed} check(s) failed` : "\nall ok");
process.exit(failed ? 1 : 0);
