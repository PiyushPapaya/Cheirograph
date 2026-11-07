#!/usr/bin/env node
// verify_hand_fit.mjs - checks the hand kinematics in tools/handrig_dashboard.html (no DOM):
// joint split, finger roll, the learned thumb movement and closing the drawn gap in a touch.
// Real glove data is covered by verify_real_calibration.mjs.
//
// Usage: node tools/verify_hand_fit.mjs

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
  "\nreturn {handDefault,digitTip,contactFix,qMul,qPow,qRot,rollFromFist,unrollQs,thumbWarp,warpHand,PAIR_FINGER};")();
const { handDefault, digitTip, contactFix, qMul, qPow, qRot, rollFromFist, unrollQs, thumbWarp, warpHand, PAIR_FINGER } = K;

let failed = 0;
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) failed++; };
const MX = -1, I = [1, 0, 0, 0];
const axisQ = (k, deg) => { const t = deg*Math.PI/360, s = Math.sin(t); return [Math.cos(t), k[0]*s, k[1]*s, k[2]*s]; };
const rv = v => { const a = Math.hypot(...v); if (a < 1e-9) return I; const s = Math.sin(a/2)/a; return [Math.cos(a/2), v[0]*s, v[1]*s, v[2]*s]; };
const dist = (a, b) => Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2]);

// Maths basics
const q90 = axisQ([1, 0, 0], 90);
const h = qPow(q90, 0.5);
check(Math.abs(qMul(h, h)[0] - q90[0]) < 1e-9, "q^0.5 twice gives q");
check(dist(qRot(q90, [0, 0, 1]), [0, -1, 0]) < 1e-9, "+90 about X turns +Z toward the palm (-Y)");

// Joint split: a straight finger reaches its full length, a bent one comes back toward the palm.
const hand = handDefault();
const straight = digitTip(2, I, hand, MX), bent = digitTip(2, axisQ([1, 0, 0], 100), hand, MX);
check(Math.abs(dist(straight, [0.27*MX, 0.1, 1.35]) - 2.3) < 1e-9, "straight middle finger is its full length");
check(bent[1] < straight[1] - 1 && bent[2] < straight[2], "a bent finger curls down and back");

// Finger roll: a sensor rolled about the finger makes a straight curl look crooked.
const rollDeg = 30, rz = axisQ([0, 0, 1], -rollDeg), curl = axisQ([1, 0, 0], 120);
const seen = qMul(qMul(rz, curl), [rz[0], -rz[1], -rz[2], -rz[3]]);     // what the sensor reports
const seenDir = qRot(seen, [0, 0, 1]);
const roll = rollFromFist(seenDir);
check(Math.abs(roll*180/Math.PI - rollDeg) < 1e-6, `fist direction gives the roll back (${(roll*180/Math.PI).toFixed(1)} deg)`);
const fixed = unrollQs([I, seen, I, I, I], [0, roll, 0, 0, 0])[1];
check(Math.abs(qRot(fixed, [0, 0, 1])[0]) < 1e-9, "after correction the finger curls straight, no sideways lean");
check(rollFromFist([0, 0.05, 1]) === 0, "a hand that didn't really make a fist gives no roll");
check(unrollQs([I, I, I, I, I], [0, 0.5, 0, 0, 0])[1].every((v, i) => Math.abs(v - I[i]) < 1e-12), "a straight finger is unaffected");

// Learned thumb movement
const flatD = Array.from({ length: 15 }, (_, i) => i%3 === 2 ? 1 : 0);
const poseD = flatD.map((v, i) => i < 3 ? v - 0.5 : v);
const wa = [{ dirs: flatD, offset: [0, 0, 0] }, { dirs: poseD, offset: [0.4, -0.2, 0.6] }];
check(dist(thumbWarp(wa, poseD), [0.4, -0.2, 0.6]) < 0.02, "at a learned pose the thumb gets its learned offset");
check(dist(thumbWarp(wa, flatD), [0, 0, 0]) < 0.02, "at the flat hand it stays home");
const midW = thumbWarp(wa, flatD.map((v, i) => (v + poseD[i])/2));
check(midW[0] > 0.05 && midW[0] < 0.35, `between two poses it blends (x ${midW[0].toFixed(2)})`);
check(dist(thumbWarp(wa, flatD.map(v => v + 5)), [0, 0, 0]) < 0.2, "far from everything it does not jump");
check(dist(thumbWarp([], flatD), [0, 0, 0]) === 0, "no calibration: no movement");
const moved = warpHand(hand, [0.5, 0, 0], MX);
check(Math.abs(digitTip(0, I, moved, MX)[0] - digitTip(0, I, hand, MX)[0] - 0.5) < 1e-9, "the offset moves the thumb tip by that much in the palm frame");

// Contact: while a touch is active, the drawn tips must meet.
const q = [axisQ([0, 1, 0], 25), axisQ([1, 0, 0], 85), I, I, I];
const g0 = dist(digitTip(0, q[0], hand, MX), digitTip(1, q[1], hand, MX));
const C = contactFix(q, ["TI"], hand, MX);
const g1 = dist(digitTip(0, q[0], hand, MX, C[0]), digitTip(1, q[1], hand, MX, C[1]));
check(g1 < g0/2, `contact pulls the tips together: ${g0.toFixed(2)} to ${g1.toFixed(2)}`);
const off = contactFix(q, [], hand, MX);
check(off.every(c => Math.abs(c[0] - 1) < 1e-12), "no active touch: no correction at all");
check(C[2].every((v, i) => v === I[i]) && C[3].every((v, i) => v === I[i]), "only the touching digits are moved");
const far = contactFix([axisQ([0, 1, 0], -120), I, I, I, I], ["TP"], hand, MX);
check(far.every(c => 2*Math.acos(Math.min(1, Math.abs(c[0])))*180/Math.PI <= 40.001), "a correction never exceeds 40 deg");

console.log(failed ? `\n${failed} check(s) failed` : "\nall hand checks passed");
process.exit(failed ? 1 : 0);
