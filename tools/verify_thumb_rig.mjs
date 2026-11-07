#!/usr/bin/env node
// verify_thumb_rig.mjs - checks the thumb model in tools/handrig_dashboard.html (no DOM,
// no BLE, no three.js). The thumb sensor sits on the tip segment, so:
//
// 1. Curl: the rotation is split over the two joints, so the TIP segment ends up exactly
//    where the sensor points while the base moves only part of the way.
// 2. Geometry: neither segment may be buried in the solid palm box, for the sideways
//    swing (T1-T4) or the downward tip bend (T6).
// 3. Readout: thumbBendRad() reads total rotation from rest, about any axis.
//
// Usage: node tools/verify_thumb_rig.mjs

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "handrig_dashboard.html"), "utf8");
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];

const anchors = script.match(/const FINGER_ANCHORS=(\{[\s\S]*?\n\});/);
const sec = script.match(/\/\/ ===== thumb bend =====[\s\S]*?\/\/ ===== end thumb bend =====/);
if (!anchors || !sec) {
  console.error("FAIL: FINGER_ANCHORS or the thumb bend section not found");
  process.exit(1);
}
const A = (0, eval)("(" + anchors[1] + ")").THUMB;
const { THUMB_BASE_FRAC, thumbBendRad } = new Function(sec[0] + "\nreturn {THUMB_BASE_FRAC,thumbBendRad};")();

let failed = 0;
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) failed++; };

// Rodrigues rotation of v about unit axis k by angle t.
const rot = (v, k, t) => {
  const c = Math.cos(t), s = Math.sin(t), d = k[0]*v[0] + k[1]*v[1] + k[2]*v[2];
  const x = [k[1]*v[2] - k[2]*v[1], k[2]*v[0] - k[0]*v[2], k[0]*v[1] - k[1]*v[0]];
  return v.map((vi, i) => vi*c + x[i]*s + k[i]*d*(1 - c));
};
const unit = v => { const n = Math.hypot(...v); return v.map(c => c/n); };
const SWING = unit([0.13, 0.95, 0.28]), DOWN = [1, 0, 0];   // measured T1-T4 swing; tip bend toward the palm side
const R = Math.PI/180, baseLen = A.len*0.55, tipLen = A.len*0.45;
const base = [-A.x, A.y ?? 0.1, A.z], yaw = -A.yaw;         // left model, mirrored as in buildFingers()

// Points along both segments for a total rotation t about k, in the palm frame.
function thumbPoints(k, t) {
  const b = THUMB_BASE_FRAC*t, pts = [], n = 100;
  const place = p => rot(p, [0, 1, 0], yaw).map((v, j) => v + base[j]);
  for (let i = 0; i < n; i++) pts.push(place(rot([0, 0, baseLen*i/(n - 1)], k, b)));
  const joint = rot([0, 0, baseLen], k, b);
  for (let i = 0; i < n; i++) {
    const q = rot([0, 0, tipLen*i/(n - 1)], k, t);          // tip segment carries the full rotation
    pts.push(place(joint.map((v, j) => v + q[j])));
  }
  return pts;
}
const buried = (k, d) => {
  const p = thumbPoints(k, d*R);
  return 100*p.filter(q => Math.abs(q[0]) < 1.2 && Math.abs(q[1]) < 0.275 && Math.abs(q[2]) < 1.3).length/p.length;
};
for (const d of [0, 30, 60, 90]) check(buried(SWING, d) <= 10, `swing ${d} deg: ${buried(SWING, d).toFixed(1)} % inside the palm (limit 10)`);
for (const d of [30, 60, 90]) check(buried(DOWN, d) <= 10, `tip bend ${d} deg: ${buried(DOWN, d).toFixed(1)} % inside the palm (limit 10)`);

// Curl: at a 90 deg bend the tip points straight down, the base only halfway.
const baseDir = rot([0, 0, 1], DOWN, THUMB_BASE_FRAC*90*R), tipDir = rot([0, 0, 1], DOWN, 90*R);
const pitch = v => Math.asin(-v[1])/R;
check(Math.abs(pitch(tipDir) - 90) < 0.01, `90 deg bend: tip segment points ${pitch(tipDir).toFixed(0)} deg down, matching the sensor`);
check(pitch(baseDir) < 60, `90 deg bend: base segment only ${pitch(baseDir).toFixed(0)} deg down, so the thumb curls`);

const axisQ = (k, t) => ({ w: Math.cos(t/2), x: k[0]*Math.sin(t/2), y: k[1]*Math.sin(t/2), z: k[2]*Math.sin(t/2) });
for (const [name, k] of [["swing", SWING], ["tip bend", DOWN]]) {
  const r = thumbBendRad(axisQ(k, 40*R))/R;
  check(Math.abs(r - 40) < 0.01, `40 deg ${name} reads ${r.toFixed(1)} deg`);
}
const neg = thumbBendRad({ w: -Math.cos(20*R), x: -Math.sin(20*R), y: 0, z: 0 })/R;
check(Math.abs(neg - 40) < 0.01, `-q is the same rotation: reads ${neg.toFixed(1)} deg`);

console.log(failed ? `\n${failed} check(s) failed` : "\nall thumb checks passed");
process.exit(failed ? 1 : 0);
