#!/usr/bin/env node
// verify_touch_shape.mjs - checks the ring vs straight touch drawing in
// tools/handrig_dashboard.html (no DOM, no three.js), on the real v3 session's templates:
//
// 1. Shape weight: w ~ 1 at a ring template, ~ 0 at the straight one, 0.5 halfway.
// 2. The drawn ring and straight poses of a pair differ clearly (joint angles, fingertip).
// 3. NaN in, no NaN out; no templates leaves the old joint split untouched.
//
// Usage: node tools/verify_touch_shape.mjs

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "handrig_dashboard.html"), "utf8");
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
const anchors = script.match(/const FINGER_ANCHORS=\{[\s\S]*?\n\};/);
const frac = script.match(/const THUMB_BASE_FRAC=[^\n]*/);
const kin = script.match(/\/\/ ===== hand kinematics =====[\s\S]*?\/\/ ===== end hand kinematics =====/);
if (!anchors || !frac || !kin) { console.error("FAIL: kinematics section not found"); process.exit(1); }
const K = new Function(anchors[0] + "\n" + frac[0] + "\n" + kin[0] +
  "\nreturn {buildWarp,thumbWarp,warpHand,SHAPE_TAU,handDefault,digitTip,digitLocal,digitJoints,digitSegs,contactFix,shapeWeight,shapeWeights,unrollQs,qPow,qMul,PAIR_FINGER,FINGER_BASE_FRAC,FINGER_TIP_FRAC,THUMB_BASE_FRAC,FINGER_SEGS,THUMB_SEGS,FINGER_ANCHORS,DIGIT_NAMES,RING_EXTRA_DEG,SHAPE_TAU};")();

const cal = JSON.parse(readFileSync(join(here, "..", "10-touch-detection", "calibration_2026-11-07_v3.json"), "utf8"));
const T = cal.templates, rolls = cal.rolls, MX = -1, hand = K.handDefault(), hand0 = hand;
const warpAnchors = K.buildWarp(T, [], hand0, MX, rolls);

let failed = 0;
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) failed++; };
const ang = (a, b) => {   // angle between two rotations, deg
  const d = Math.abs(a[0]*b[0] + a[1]*b[1] + a[2]*b[2] + a[3]*b[3]);
  return 2*Math.acos(Math.min(1, d))*180/Math.PI;
};
const finite = v => v.flat(2).every(Number.isFinite);

// 1. weight at the templates and halfway. A pair whose two holds came out nearly alike
// (v3: TI only 0.05 apart on thumb + index) can't saturate, and shouldn't: the data doesn't
// tell them apart. Those only have to lean the right way.
const sep = {};
for (const p of ["TI", "TM", "TR", "TP"]) {
  const r = T.find(t => t.pairs[0] === p && t.shape === "ring").mean;
  const s = T.find(t => t.pairs[0] === p && t.shape === "straight").mean;
  const g = [0, K.PAIR_FINGER[p]];
  sep[p] = Math.sqrt(g.reduce((a, i) => a + [0, 1, 2].reduce((b, k) => b + (r[i*3 + k] - s[i*3 + k])**2, 0), 0));
  const wr = K.shapeWeight(T, p, r), ws = K.shapeWeight(T, p, s), wm = K.shapeWeight(T, p, r.map((v, k) => (v + s[k])/2));
  const clear = sep[p] >= 3*K.SHAPE_TAU;
  check((clear ? wr > 0.95 && ws < 0.05 : wr > 0.5 && ws < 0.5) && Math.abs(wm - 0.5) < 1e-9,
    `${p}: templates ${sep[p].toFixed(3)} apart${clear ? "" : " (too close to saturate)"}; w at ring ${wr.toFixed(4)}, at straight ${ws.toFixed(4)}, halfway ${wm.toFixed(3)}`);
}

const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
// 2. drawn ring vs straight, each from its own template's held orientation, contact closed
function draw(p, shape) {
  const t = T.find(t => t.pairs[0] === p && t.shape === shape), f = K.PAIR_FINGER[p];
  const qs = K.unrollQs(t.q, rolls);
  const { ws } = K.shapeWeights({}, T, [p], t.mean);
  const hand = K.warpHand(hand0, K.thumbWarp(warpAnchors, t.mean), MX);   // the learned thumb movement, as live
  const C = K.contactFix(qs, [p], hand, MX, ws);
  const J = K.digitJoints(f, qs[f], ws[f]);
  const Jt = K.digitJoints(0, qs[0], ws[0]);
  const C0 = K.contactFix(qs, [p], hand, MX);   // the old drawing, no shape
  return {
    tip: K.digitTip(f, qs[f], hand, MX, C[f], ws[f]), thumb: K.digitTip(0, qs[0], hand, MX, C[0], ws[0]),
    oldTip: K.digitTip(f, qs[f], hand, MX, C0[f]),
    // the same held orientation drawn as a full ring and as fully straight
    pure: [1, 0].map(w => { const J = K.digitJoints(f, qs[f], w); return (ang(J[0], J[1]) + ang(J[1], J[2]))/2; }),
    joints: (ang(J[0], J[1]) + ang(J[1], J[2]))/2, thumbJoint: ang(Jt[0], Jt[1]),
    oldJoints: (ang(K.qPow(qs[f], K.FINGER_BASE_FRAC), qs[f]) + ang(qs[f], K.qPow(qs[f], 1 + K.FINGER_TIP_FRAC)))/2,
  };
}
for (const p of ["TI", "TM", "TR", "TP"]) {
  const r = draw(p, "ring"), s = draw(p, "straight");
  const dj = r.joints - s.joints, dt = dist(r.tip, s.tip), dOld = dist(r.oldTip, s.oldTip);
  check(r.pure[0] - r.pure[1] >= 40, `${p}: ring hold drawn full ring vs full straight: PIP/DIP ${r.pure[0].toFixed(0)} vs ${r.pure[1].toFixed(0)} deg`);
  check(sep[p] < 3*K.SHAPE_TAU || dj >= 40 || dt >= 0.5,
    `${p}: mean PIP/DIP ring ${r.joints.toFixed(0)} vs straight ${s.joints.toFixed(0)} deg (was ${r.oldJoints.toFixed(0)} vs ${s.oldJoints.toFixed(0)}), ` +
    `thumb joint ${r.thumbJoint.toFixed(0)} vs ${s.thumbJoint.toFixed(0)}, fingertip ${dt.toFixed(2)} apart (was ${dOld.toFixed(2)})`);
  check(dist(r.tip, r.thumb) < 0.1 && dist(s.tip, s.thumb) < 0.1,
    `${p}: tips meet, gap ring ${dist(r.tip, r.thumb).toFixed(3)}, straight ${dist(s.tip, s.thumb).toFixed(3)}`);
}

// Segments nested in the scene graph multiply back to the joint totals.
{
  const q = K.unrollQs(T[0].q, rolls)[1], seg = K.digitSegs(1, q, 0.7), J = K.digitJoints(1, q, 0.7);
  const tot = K.qMul(K.qMul(seg[0], seg[1]), seg[2]);
  check(ang(tot, J[2]) < 1e-3 && ang(J[1], q) < 1e-3, "segments compose to the totals; middle phalanx stays the measured q");
}

// 3. NaN and no templates
{
  const nanDirs = Array(15).fill(NaN);
  const a = K.shapeWeights({}, T, ["TI"], nanDirs);
  check(a.ws.every(w => w === null), "NaN dirs: no shape weight");
  check(finite(K.digitJoints(1, [1, 0, 0, 0], NaN)) && finite(K.digitJoints(0, [1, 0, 0, 0], NaN)), "NaN weight: falls back to the plain split");
  check(K.shapeWeight(T, "TI", null) === null && K.shapeWeight(T, "TI", T[0].mean.map(() => NaN)) === null, "missing dirs: null");
  const none = K.shapeWeights({}, [], ["TI"], T[0].mean);
  const qs = K.unrollQs(T[0].q, rolls);
  // the old digitLocal, written out
  const oldLocal = (i, q) => {
    const L = i === 0 ? hand.thumbLen : K.FINGER_ANCHORS[K.DIGIT_NAMES[i]].len*hand.scale[i - 1];
    const rot = (q, v) => { const [w, x, y, z] = q, tx = 2*(y*v[2] - z*v[1]), ty = 2*(z*v[0] - x*v[2]), tz = 2*(x*v[1] - y*v[0]);
      return [v[0] + w*tx + y*tz - z*ty, v[1] + w*ty + z*tx - x*tz, v[2] + w*tz + x*ty - y*tx]; };
    const add = (a, b) => a.map((c, k) => c + b[k]), z = l => [0, 0, l];
    if (i === 0) return add(rot(K.qPow(q, K.THUMB_BASE_FRAC), z(L*K.THUMB_SEGS[0])), rot(q, z(L*K.THUMB_SEGS[1])));
    return add(add(rot(K.qPow(q, K.FINGER_BASE_FRAC), z(L*K.FINGER_SEGS[0])), rot(q, z(L*K.FINGER_SEGS[1]))),
      rot(K.qPow(q, 1 + K.FINGER_TIP_FRAC), z(L*K.FINGER_SEGS[2])));
  };
  const same = [0, 1, 2, 3, 4].every(i => dist(K.digitLocal(i, qs[i], hand, none.ws[i]), oldLocal(i, qs[i])) === 0);
  const C1 = K.contactFix(qs, ["TI"], hand, MX, none.ws), C2 = K.contactFix(qs, ["TI"], hand, MX);
  check(none.ws.every(w => w === null) && same && JSON.stringify(C1) === JSON.stringify(C2), "no templates: pose identical to the old one");
}

console.log(failed ? `\n${failed} check(s) FAILED` : "\nall checks passed");
process.exit(failed ? 1 : 0);
