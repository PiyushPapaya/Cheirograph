#!/usr/bin/env node
// verify_bias_tilt.mjs - background gyro-bias tracking must not learn a slow real tilt as bias.
// One finger (index) is fed synthetic frames, all other sensors lie still. After a 3 s calibration
// and 5 s of stillness:
// Case 1: the finger tilts about its X axis at 1 deg/s for 30 s, gyro and accel consistent with it.
//   That rate is under the creep gate and under the 1.5 deg/s residual cap, so before the fix the
//   tracker pulled the bias toward the tilt rate. The bias must stay within 0.1 deg/s on every axis.
// Case 2 (control): the finger is perfectly still but its gyro now reads 0.5 deg/s more than at
//   calibration (warm-up drift). The tracker must follow it (moves by more than 0.2 deg/s), so this
//   shows the fix did not switch the tracker off.
// Usage: node tools/verify_bias_tilt.mjs [page.html]
import { resolve } from "node:path";
import { loadPage, frameOf } from "./selftest_replay_lib.mjs";

const page = process.argv[2] ? resolve(process.argv[2]) : undefined;
let failed = 0;
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) failed++; };

const DT = 20, ID = 2;                       // 50 Hz, index finger
const row = (i, tiltDeg, gx) => {
  const r = [i * DT, 0x3f];
  for (let s = 0; s < 6; s++) {
    if (s === ID) {                           // body-frame gravity after turning by tilt about +X, then gyro
      const th = tiltDeg * Math.PI / 180;
      r.push(0, Math.sin(th), Math.cos(th), gx, 0, 0);
    } else r.push(0, 0, 1, 0, 0, 0);
  }
  return r;
};

function run(tilt, gxStill) {
  const L = loadPage(page);
  L.ACC_OFFSET.forEach(o => o.fill(0));
  let i = 0;
  const feed = (n, f) => { for (let k = 0; k < n; k++, i++) { L.T.now = i * DT; const [t, g] = f(k); L.parseFrame(frameOf(row(i, t, g), i)); } };
  L.startCal("initial");
  feed(150, () => [0, 0]);                    // 3 s still, gx = 0
  L.finishCalibration();
  feed(250, () => [0, 0]);                    // 5 s still
  const b0 = L.bias(ID);
  feed(1500, k => tilt ? [k * DT / 1000 * 1.0, 1.0] : [0, gxStill]);   // 30 s
  const b1 = L.bias(ID);
  return Math.max(...b0.map((v, k) => Math.abs(v - b1[k])));
}

const d1 = run(true, 0);
check(d1 < 0.1, `1 deg/s tilt for 30 s: bias moved ${d1.toFixed(3)} deg/s (limit 0.1)`);
const d2 = run(false, 0.5);
check(d2 > 0.2, `control, still with 0.5 deg/s offset: bias moved ${d2.toFixed(3)} deg/s (must be > 0.2)`);
console.log(failed ? `\n${failed} check(s) failed` : "\nall ok");
process.exit(failed ? 1 : 0);
