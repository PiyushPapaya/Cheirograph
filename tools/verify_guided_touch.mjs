#!/usr/bin/env node
// verify_guided_touch.mjs - checks the pure part of guided touch calibration in
// tools/handrig_dashboard.html (no DOM, no BLE): stages, templates, matching and the coach.
//
// Usage: node tools/verify_guided_touch.mjs

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "handrig_dashboard.html"), "utf8");
const kin = html.match(/\/\/ ===== hand kinematics =====[\s\S]*?\/\/ ===== end hand kinematics =====/);
const sec = html.match(/\/\/ ===== touch detection =====[\s\S]*?\/\/ ===== end touch detection =====/);
if (!kin || !sec) { console.error("FAIL: kinematics or touch section not found"); process.exit(1); }
const names = "GUIDED_STAGES,makeTemplate,finishTemplates,templateTouch,digitDist,stageDigits,coachLines,replayCheck,flatCheckDeg,FLAT_DIRS,TOUCH_TPL_MIN";
const stubs = "const FINGER_ANCHORS={THUMB:{x:1,z:0,len:1}};const THUMB_BASE_FRAC=0.5;";
let L;
try { L = new Function(stubs + kin[0] + "\n" + sec[0] + `\nreturn {${names}};`)(); }
catch (e) { console.error("FAIL: guided functions missing: " + e.message); process.exit(1); }
const { GUIDED_STAGES, makeTemplate, finishTemplates, templateTouch, digitDist, stageDigits, coachLines, replayCheck, flatCheckDeg, FLAT_DIRS, TOUCH_TPL_MIN } = L;

let failed = 0;
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) failed++; };

// Unit direction for a curl (about X) of deg degrees plus a sideways swing (about Y).
const dir = (curl, swing = 0) => {
  const c = curl*Math.PI/180, s = swing*Math.PI/180;
  return [Math.cos(c)*Math.sin(s), -Math.sin(c), Math.cos(c)*Math.cos(s)];
};
// 15 numbers from curl per digit, thumb to pinky. off is a whole-session offset in degrees.
const pose = (curls, thumbSwing = 0, off = 0) =>
  curls.flatMap((c, i) => dir(c + off, i === 0 ? thumbSwing + off : 0));
let seed = 1;
const rnd = () => (seed = seed*16807 % 2147483647)/2147483647 - 0.5;
const hold = (p, jitter = 0.01, n = 60) => Array.from({ length: n }, () => p.map(v => v + rnd()*jitter));
const tpl = (pairs, shape, p) => makeTemplate({ kind: "touch", pairs, shape }, hold(p));
const ready = (ts, negs = []) => finishTemplates(ts, negs);

// Stages
const touch = GUIDED_STAGES.filter(s => s.kind === "touch");
for (const pair of ["TI", "TM", "TR", "TP"]) {
  const mine = touch.filter(s => s.pairs.length === 1 && s.pairs[0] === pair).map(s => s.shape).join();
  check(mine === "ring,straight", `${pair} has ring and straight`);
  check(GUIDED_STAGES.some(s => s.kind === "neg" && s.pairs && s.pairs[0] === pair), `${pair} has a near-miss stage`);
}
check(touch.some(s => s.pairs.length === 2), "there is a two-finger stage (rock)");
check(GUIDED_STAGES.some(s => s.kind === "move"), "there is a hand-turn stage");
check(GUIDED_STAGES.filter(s => s.kind === "neg" && !s.pairs).length >= 3, "there are fist, spread and flat-check stages");
check(GUIDED_STAGES[GUIDED_STAGES.length - 1].label === "FLATCHECK", "the run ends on a flat hand, to measure drift");
check(stageDigits({ pairs: ["TM", "TR"] }).join() === "0,2,3", "rock compares thumb, middle and ring");
check(stageDigits({}).join() === "0,1,2,3,4", "a whole-hand stage compares every digit");

// Templates and matching
const ringTI = [60, 70, 0, 0, 0], ringTR = [70, 0, 0, 80, 0];
const T = ready([tpl(["TI"], "ring", pose(ringTI, 30)), tpl(["TR"], "ring", pose(ringTR, 45))]);
check(digitDist(T[0].digits, T[0].mean, pose(ringTI, 30)) < 0.02, "template mean sits on the held pose");
check(T[0].radius >= TOUCH_TPL_MIN, `steady hold keeps the minimum radius (${T[0].radius.toFixed(2)})`);
const on = templateTouch({}, T, pose(ringTI, 30));
check(on.TI && !on.TR, "the held pose reads thumb and index only");
check(!templateTouch({}, T, FLAT_DIRS).TI, "flat hand reads no touch");
check(!templateTouch({}, T, pose([0, 0, 0, 0, 0], -30)).TI, "thumb out sideways reads no touch");
check(!templateTouch({}, T, pose([60, 0, 0, 0, 0], 30)).TI, "index straight, thumb in place: no touch");

// Hysteresis
const edge = pose(ringTI, 30).map((v, i) => v + (i === 0 ? T[0].radius*1.1 : 0));
check(!templateTouch({}, T, edge).TI, "just outside the radius: stays off");
check(templateTouch({ TI: true }, T, edge).TI, "just outside the radius: stays on when already on");

// Moving between touches, and two at once
const S2 = ready([tpl(["TI"], "straight", pose([25, 20, 0, 0, 0])), tpl(["TM"], "straight", pose([30, 0, 25, 0, 0]))]);
const moved = templateTouch({ TI: true }, S2, pose([30, 0, 25, 0, 0]));
check(moved.TM && !moved.TI, "moving from index to middle drops the index");
const rock = ready([tpl(["TM", "TR"], "rock", pose([67, 0, 75, 80, 0]))]);
const rk = templateTouch({}, rock, pose([67, 0, 75, 80, 0]));
check(rk.TM && rk.TR, "the rock template turns both pairs on");
check(!templateTouch({}, rock, pose([67, 0, 75, 0, 0])).TM, "rock needs every finger in it: ring straight reads no rock");

// Negatives limit the radius: this is what the near-miss stage buys.
const touchP = pose(ringTI, 30), nearP = pose([48, 70, 0, 0, 0], 30);
const nm = ready([tpl(["TI"], "ring", touchP)], [{ label: "NEARTI", mean: nearP }]);
check(nm[0].radius < TOUCH_TPL_MIN, `a near miss shrinks the radius (${nm[0].radius.toFixed(2)})`);
check(nm[0].limitedBy === "NEARTI", "and the template says what limited it");
check(templateTouch({}, nm, touchP).TI, "the real touch still reads");
check(!templateTouch({}, nm, nearP).TI, "the near miss reads no touch");
const noNeg = ready([tpl(["TI"], "ring", touchP)]);
check(templateTouch({}, noNeg, nearP).TI, "without the near-miss stage that same pose was a false touch");

// A 1 cm gap is the same size in any pose, so a pair's tightest radius applies to all its poses.
const both2 = ready([tpl(["TI"], "ring", touchP), tpl(["TI"], "straight", pose([25, 20, 0, 0, 0]))], [{ label: "NEARTI", mean: nearP }]);
check(Math.abs(both2[1].radius - both2[0].radius) < 1e-9, `straight inherits the near-miss radius (${both2[1].radius.toFixed(2)})`);
check(!templateTouch({}, both2, pose([34, 28, 0, 0, 0])).TI, "a pose near the straight touch but not on it reads no touch");

const fist = pose([60, 110, 110, 110, 110], 30);
const nf = ready([tpl(["TI"], "ring", pose([60, 100, 0, 0, 0], 30))], [{ label: "FIST", mean: fist }]);
check(!templateTouch({}, nf, fist).TI, "a fist reads no touch");

const nearFlat = ready([tpl(["TI"], "straight", pose([5, 4, 0, 0, 0], 3))]);
check(!templateTouch({}, nearFlat, FLAT_DIRS).TI, `straight touch close to flat: radius shrinks (${nearFlat[0].radius.toFixed(2)})`);
check(nearFlat[0].weak === true, "and is flagged weak");

// Session offsets cancel.
const off = 15, sess = ready([tpl(["TI"], "ring", pose(ringTI, 30, off))]);
check(templateTouch({}, sess, pose(ringTI, 30, off)).TI, "session offset of 15 deg: still detected");
check(!templateTouch({}, T, pose(ringTI, 30, off)).TI, "the same offset defeats a template from another session");

// Replay: run the recorded holds back through the detector.
const rp = (name, kind, pairs, p) => ({ name, kind, pairs, rows: hold(p, 0.01, 20) });
const good = replayCheck([rp("TI ring", "touch", ["TI"], pose(ringTI, 30)), rp("FIST", "neg", undefined, pose([20, 110, 110, 110, 110]))], T);
check(good.ok === 2 && good.bad.length === 0, "replay: correct holds pass");
const wrong = replayCheck([rp("TM ring", "touch", ["TM"], pose(ringTI, 30))], T);
check(wrong.ok === 0 && wrong.bad[0] === "TM ring", "replay: a hold read as the wrong finger fails, and is named");

// Flat check
check(Math.abs(flatCheckDeg(FLAT_DIRS)) < 1e-6, "flat check: a flat hand reads 0");
check(Math.abs(flatCheckDeg(pose([20, 20, 20, 20, 20])) - 20) < 1e-6, "flat check: 20 deg of drift reads 20");

// Coach
const lines = coachLines([...T, ...nearFlat], ["NEARTP"], { replay: { ok: 11, total: 13, bad: ["TM ring", "TP ring"] }, flatDeg: 22 }).join("\n");
check(/thumb·index/.test(lines) && /weak/.test(lines), "coach names the weak pair");
check(/NEARTP/.test(lines), "coach names the missed hold");
check(/11 of 13/.test(lines) && /TM ring/.test(lines), "coach reports the replay and what failed");
check(/22/.test(lines) && /drift/i.test(lines), "coach warns about drift");
const clean = coachLines(T, [], { replay: { ok: 13, total: 13, bad: [] }, flatDeg: 4 }).join("\n");
check(/13 of 13/.test(clean) && !/drift/i.test(clean) && /run Self-test/i.test(clean), "a clean run says so and points to Self-test");

console.log(failed ? `\n${failed} check(s) failed` : "\nall guided touch checks passed");
process.exit(failed ? 1 : 0);
