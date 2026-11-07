#!/usr/bin/env node
// verify_dashboard_states.mjs - checks the pure parts added around guided calibration in
// tools/handrig_dashboard.html (no DOM, no BLE): NaN guards in the kinematics, the black box
// that records a run, the touch state line and the self-test readout. The button and timer
// state machine needs the page itself, so that was exercised in a browser instead.
//
// Usage: node tools/verify_dashboard_states.mjs

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "handrig_dashboard.html"), "utf8");
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
const grab = re => { const m = script.match(re); if (!m) { console.error("FAIL: section not found: " + re); process.exit(1); } return m[0]; };
const src = [grab(/const FINGER_ANCHORS=\{[\s\S]*?\n\};/), grab(/const THUMB_BASE_FRAC=[^\n]*/),
  grab(/\/\/ ===== hand kinematics =====[\s\S]*?\/\/ ===== end hand kinematics =====/),
  grab(/\/\/ ===== touch detection =====[\s\S]*?\/\/ ===== end touch detection =====/),
  grab(/\/\/ ===== black box =====[\s\S]*?\/\/ ===== end black box =====/)].join("\n");
const names = "qPow,qArc,thumbWarp,rollFromFist,qMul,contactFix,handDefault,coachLines,stageName,GUIDED_STAGES,"
  + "makeBlackBox,bbFrame,bbEvent,bbStageBegin,bbHoldBegin,bbStageEnd,bbRowsJson,bbCols,touchStateInfo,readInstead";
let L;
try { L = new Function(src + `\nreturn {${names}};`)(); }
catch (e) { console.error("FAIL: " + e.message); process.exit(1); }
const { qPow, qArc, thumbWarp, rollFromFist, contactFix, handDefault, coachLines, stageName, GUIDED_STAGES,
  makeBlackBox, bbFrame, bbEvent, bbStageBegin, bbHoldBegin, bbStageEnd, bbRowsJson, bbCols, touchStateInfo, readInstead } = L;

let failed = 0;
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) failed++; };
const finite = a => a.every(Number.isFinite);

// NaN and edge inputs must never come out as NaN: they end up in three.js quaternions.
check(finite(qPow([NaN, 0, 0, 0], 0.5)), "qPow of a NaN quaternion is finite");
check(finite(qPow([1, NaN, 0, 0], 0.5)), "qPow with a NaN axis is finite");
check(qPow([1, 0, 0, 0], 0.5).join() === "1,0,0,0", "qPow of identity is identity");
check(finite(qPow([-1, 0, 0, 0], 0.5)), "qPow of -identity is finite");
check(finite(qArc([NaN, 0, 1], [0, 0, 1])), "qArc with a NaN direction is finite");
check(finite(qArc([0, 0, 1], [0, 0, -1])), "qArc of opposite directions is finite");
check(finite(qArc([0, 0, 0], [0, 0, 1])), "qArc of a zero vector is finite");
const flat = Array.from({ length: 15 }, (_, i) => i%3 === 2 ? 1 : 0);
const anchors = [{ dirs: flat, offset: [0, 0, 0] }, { dirs: flat.map(v => v + 0.1), offset: [0.5, -0.2, 0.3] }];
check(finite(thumbWarp(anchors, flat.map((v, i) => i === 4 ? NaN : v))), "thumbWarp with a NaN direction is finite");
check(thumbWarp(anchors, flat.map((v, i) => i === 4 ? NaN : v)).every(v => v === 0), "thumbWarp with a NaN direction leaves the thumb at home");
check(finite(thumbWarp([{ dirs: flat, offset: [NaN, 0, 0] }], flat)), "thumbWarp with a NaN anchor offset is finite");
check(finite(thumbWarp(anchors, flat.slice(0, 6))), "thumbWarp with too few numbers is finite");
check(rollFromFist([NaN, NaN, 1]) === 0, "finger roll from a NaN fist direction is 0");
check(rollFromFist([0.3, -0.9, 0.1]) !== 0, "finger roll from a real fist direction is not 0");
const hand = handDefault();
const bad = [[1, 0, 0, 0], [NaN, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]];
check(contactFix(bad, ["TI"], hand, -1).every(finite), "contactFix with one NaN sensor stays finite");

// Stage names, including the hand-turn stage that has neither label nor pairs
check(stageName(GUIDED_STAGES[0]) === "MOVE", "the hand-turn stage has a name");
check(GUIDED_STAGES.every(s => /^[A-Z0-9+ a-z]+$/.test(stageName(s))), "every stage has a plain name");

// Black box
const NAMES = ["HAND", "THUMB", "INDEX", "MIDDLE", "RING", "PINKY"];
const cols = bbCols(NAMES);
check(cols.length === 2 + 36 && cols[0] === "t_ms" && cols[1] === "mask" && cols[2] === "hand_ax" && cols[37] === "pinky_gz", "columns: time, mask, 6 sensors x 6 axes");
const bb = makeBlackBox(6, 5, 3);
bbStageBegin(bb, 100, "FIST", 1);
bbFrame(bb, 5000, 0x3f, Array.from({ length: 36 }, (_, i) => i + 0.123456));
bbHoldBegin(bb, 200);
bbFrame(bb, 5020, 0x3e, Array.from({ length: 36 }, () => -0.0004));
bbStageEnd(bb, 300, "kept", { rows: 2 });
const m = bb.marks[0];
check(bb.marks.length === 1 && m.name === "FIST" && m.f0 === 0 && m.fHold === 1 && m.f1 === 2 && m.outcome === "kept", "a stage mark covers its frames");
const rows = JSON.parse(bbRowsJson(bb));
check(rows.length === 2 && rows[0].length === 38, "rows have 38 numbers");
check(rows[0][0] === 5000 && rows[0][1] === 63 && rows[0][2] === 0.123 && rows[0][3] === 1.123, "values are rounded to 3 decimals");
check(rows[1][2] === 0 && !Object.is(rows[1][2], -0), "a tiny negative value is written as 0, not -0");
for (let i = 0; i < 6; i++) bbFrame(bb, 6000 + i, 0x3f, new Array(36).fill(0));
check(bb.n === 5 && bb.full === 3, `a full buffer stops at the cap and counts what it refused (kept ${bb.n}, refused ${bb.full})`);
for (let i = 0; i < 6; i++) bbEvent(bb, 1000 + i, "test", { i });
check(bb.events.length === 3 && bb.eventsLost === 3, "the event log is capped and counts what it dropped");
check(bb.events[0].frame === 5 && bb.events[0].type === "test", "an event records the frame it happened at");
bbStageEnd(bb, 400, "kept");   // nothing open: must not throw or invent a mark
check(bb.marks.length === 1, "closing with no open stage does nothing");
const bb2 = makeBlackBox(6, 10, 10);
bbStageBegin(bb2, 0, "A", 1); bbStageBegin(bb2, 50, "B", 1);
check(bb2.marks.length === 2 && bb2.marks[0].outcome === "cancelled" && bb2.marks[0].name === "A", "opening a stage closes the open one as cancelled");

// Touch state line
const ts = o => touchStateInfo({ running: false, n: 0, total: 9, weak: 0, stale: false, model: false, ...o });
check(/NOT CALIBRATED/.test(ts({}).text) && /Guided calibration/.test(ts({}).text), "no templates: says not calibrated and what to do");
check(/model/i.test(ts({ model: true }).text) && /NOT CALIBRATED/.test(ts({ model: true }).text), "a loaded model without templates is still not calibrated, and says what the bars do");
check(/^CALIBRATED/.test(ts({ n: 9 }).text) && ts({ n: 9 }).level === "ok", "templates learned: calibrated");
check(/STALE/.test(ts({ n: 9, stale: true }).text) && /Guided calibration/.test(ts({ n: 9, stale: true }).text), "re-zeroed after learning: stale, rerun");
check(/step 4 of 17/.test(ts({ running: true, step: 4, steps: 17 }).text), "running: names the step");
check(/weak/.test(ts({ n: 8, weak: 2 }).text), "weak templates are counted");

// Self-test readout: what was read instead
const sets = { "TM": 14, "": 4, "TI": 2 };
const ri = readInstead(sets, 20, ["TI"]);
check(/thumb·middle 70 %/.test(ri) && /nothing 20 %/.test(ri) && !/thumb·index/.test(ri), "self-test readout lists what was read instead of the wanted pair");
check(readInstead({ "TI": 10 }, 10, ["TI"]) === "", "a correct check has nothing read instead");
check(readInstead({}, 0, ["TI"]) === "no live frames", "a check with no live frames says so");

// Coach says what to do next
const T0 = [{ pairs: ["TI"], shape: "ring", weak: true, limitedBy: "FLAT" }];
const l1 = coachLines(T0, ["NEARTP"], { replay: { ok: 10, total: 13, bad: ["TI ring"] }, flatDeg: 22 }).join("\n");
check(/Next:/.test(l1), "a messy run ends with a next step");
check(/Missed: NEARTP/.test(l1) && /Replay: 10 of 13/.test(l1), "existing coach lines are kept");

// A throw inside parseFrame must not freeze the stream: the bad frame has to be consumed,
// the next one still parsed, and the error noted (before, onNotify threw and kept the frame
// in rxBuf, so every later packet hit the same frame and the dashboard went dead).
{
  const onSrc = grab(/function onNotify\(e\)\{[\s\S]*?\n\}\n/);
  const mk = n => { const b = new Uint8Array(80 * n); for (let f = 0; f < n; f++) { b[80 * f] = 0xAB; b[80 * f + 1] = f; let ck = 0; for (let k = 0; k < 79; k++) ck ^= b[80 * f + k]; b[80 * f + 79] = ck; } return b; };
  const run = bad => {
    const st = { parsed: [], errs: [] };
    const f = new Function("st", "bad", `let rxBuf=new Uint8Array(0),bytesWin=0,badFrames=0;const SYNC=0xAB,FRAME_LEN=80;
      const parseFrame=fr=>{if(fr[1]===bad)throw new Error("boom");st.parsed.push(fr[1]);};
      const noteError=(k,e)=>st.errs.push(k);
      ${onSrc}
      return {go:v=>onNotify({target:{value:new DataView(v.buffer)}}),left:()=>rxBuf.length};`)(st, bad);
    let threw = false;
    try { f.go(mk(3)); } catch (e) { threw = true; }
    return { threw, left: f.left(), ...st };
  };
  const r = run(1);
  check(!r.threw && r.left === 0 && r.parsed.join() === "0,2" && r.errs.length === 1, "a frame that throws is skipped, noted, and the next frames still parse");
}

// The touch-model loader called setTouchModel, which did not exist: every load failed with
// "not a valid touch model JSON" and the saved model never came back. A model with a pair name
// the contact solver does not know would have thrown inside render() on every frame.
{
  const fn = script.match(/function setTouchModel\(m\)\{[^\n]*\}/);
  check(!!fn, "setTouchModel exists");
  if (fn) {
    const f = new Function(`let TOUCH_MODEL=null,touchOn=[];${fn[0]}
      return {set:setTouchModel,get:()=>[TOUCH_MODEL,touchOn]};`)();
    const m = { pairs: ["TI", "TM"] };
    f.set(m);
    const [tm, on] = f.get();
    check(tm === m && on.length === 2 && on.every(v => v === false), "setTouchModel installs the model and resets the hysteresis state");
  }
  const vt = new Function(src + "\nreturn validTouchModel;")();
  const n15 = Array.from({ length: 15 }, () => 1), mk = pairs => ({ pairs, mu: n15, sd: n15, b: pairs.map(() => 0), w: pairs.map(() => n15) });
  check(vt(mk(["TI", "TP"])) === true, "a model with known pairs is valid");
  check(vt(mk(["TI", "XX"])) === false, "a model with an unknown pair name is rejected");
}

// three.js reschedules its loop AFTER the callback, so a throw inside render() would stop the 3D view for good.
check(/setAnimationLoop\(\(\)=>\{try\{render\(\)/.test(script), "the 3D loop catches a throw from render()");

console.log(failed ? `\n${failed} check(s) failed` : "\nall dashboard state checks passed");
process.exit(failed ? 1 : 0);
