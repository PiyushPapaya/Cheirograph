#!/usr/bin/env node
// verify_blackbox.mjs - end to end test of the dashboard's black box: build version 3 exports
// with the page's REAL code (re-read from handrig_dashboard.html on every run), write each to
// a temp file, run analyze_touch_calibration.py on it and check what the report says.
// Usage: node tools/verify_blackbox.mjs
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "handrig_dashboard.html"), "utf8");
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
const grab = re => { const m = script.match(re); if (!m) { console.error("FAIL: not found in page: " + re); process.exit(1); } return m[0]; };
const NL = String.fromCharCode(10);
// a whole top-level function, found by name: one line, or up to the closing brace in column 0
function fn(name) {
  const i = script.indexOf("function " + name + "(");
  if (i < 0) { console.error("FAIL: function not found: " + name); process.exit(1); }
  const eol = script.indexOf(NL, i);
  if (script.slice(i, eol).trimEnd().endsWith("}")) return script.slice(i, eol);
  return script.slice(i, script.indexOf(NL + "}", i) + 2);
}
const src = [grab(/\/\/ ===== black box =====[\s\S]*?\/\/ ===== end black box =====/),
  grab(/const META=\[[\s\S]*?\];/), grab(/const r3=[^\n]*/), grab(/const SELF_PREP_MS=.*/), grab(/const DASH_VERSION=.*/),
  ...["scriptHash", "newRunRec", "bbLog", "runOver", "sessionFacts", "buildExport"].map(fn)].join("\n");
// stand-ins for the page's globals: only the data the export reads
const stubs = `
const T={now:0}; const performance={now:()=>T.now};
const document={scripts:[]}, location={pathname:"/handrig_dashboard.html"}, navigator={userAgent:"test"};
const pageErrors=[], S=[], DEG=Math.PI/180, DISPLAY={handModel:"left",curlMode:"abs"}, REMAP_OF=[[0,1,2]];
const ACC_OFFSET=[[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]];
let badFrames=0, mountTiltDeg=3, handMount=0, mountChecked=true, zeroEpoch=0, tplEpoch=0, tplFrom=null, touchTemplates=[];
let runRec=null, guided=null, selfT=null, calState="idle";
for(let i=0;i<6;i++)S.push({calibrated:true,bad:false,flag:"",bias:[0,0,0],noise:[.1,.1,.1],accBias:[0,0,0],dropCount:0,dropBad:false});
const GUIDED_PREP_MS=5000,GUIDED_HOLD_MS=10000,GUIDED_USE_MS=7000,GUIDED_MIN_ROWS=30,GUIDED_MAX_SPREAD=0.1,GUIDED_TRIES=3;
const TOUCH_TPL_MIN=.3,TOUCH_TPL_OFF=1.3,TOUCH_TPL_WEAK=.08,GUIDED_STAGES=new Array(17);`;
const L = new Function(stubs + "\n" + src + `
return {T,newRunRec(){runRec=newRunRec();return runRec;},bbLog,runOver,buildExport,bbFrame,bbStageBegin,bbHoldBegin,bbStageEnd,makeBlackBox};`)();

const dir = mkdtempSync(join(tmpdir(), "bb-"));
let failed = 0;
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) failed++; };

// Simulate a run at 50 Hz. Each stage is 100 prep frames and 300 hold frames. One option at a time
// breaks something.
function run(o = {}) {
  L.T.now = 0;
  const r = L.newRunRec();
  if (o.frameCap) r.bb = L.makeBlackBox(6, o.frameCap);   // same constructor as the page, small cap
  let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647 - 0.5;
  const vals = new Float64Array(36), frozenRef = new Float64Array(36), stages = [];
  let frame = 0;
  const push = () => {
    const t = frame * 20; L.T.now = t;
    const mask = o.invalid != null && frame > 20 ? 63 & ~(1 << o.invalid) : 63;
    for (let s = 0; s < 6; s++) for (let a = 0; a < 6; a++) {
      let v = a < 3 ? (a === 2 ? 1 : 0) + rnd() * 0.02 : rnd() * 2;   // g around gravity on z; gyro almost still
      if (o.frozen === s && frame >= 5) v = frozenRef[s * 6 + a];       // bit-identical from frame 5 on
      if (o.clip && o.clip.sensor === s && a === 4 && frame % 7 === 0) v = 500;   // gyro at the rail
      vals[s * 6 + a] = v;
    }
    if (frame === 4) for (let i = 0; i < 36; i++) frozenRef[i] = Math.fround(vals[i]);
    L.bbFrame(r.bb, t, mask, vals);
    r.framesIn++; frame++;
  };
  const total = o.cutAt ?? 17;
  for (let i = 0; i < total; i++) {
    const name = i === 0 ? "STILL" : "ST" + i;
    L.bbStageBegin(r.bb, frame * 20, name, 1);
    for (let k = 0; k < 100; k++) push();
    L.bbHoldBegin(r.bb, frame * 20);
    for (let k = 0; k < 300; k++) push();
    L.bbStageEnd(r.bb, frame * 20, "kept", { n: 300, spread: 0.02 });
    if (i > 0) stages.push({ name, n: 300, spread: 0.02, attempt: 1, rows: null });
  }
  if (o.cutAt != null) {   // the run ends in the middle of a stage
    L.bbStageBegin(r.bb, frame * 20, "CUT", 1);
    for (let k = 0; k < 50; k++) push();
    if (o.disconnect) L.bbLog("disconnect", { guided: true, selfTest: false, calibrating: false });
    L.runOver(o.disconnect ? "disconnected" : "stopped");
  } else L.runOver("complete");
  r.g = { log: stages, missed: [] };
  r.result = { replay: null, flatDeg: null, rolls: null, anchors: [], templates: [] };
  if (o.selfTest) { r.selfTest = o.selfTest; r.selfStatus = "complete"; }
  r.hz.min = 48; r.hz.sum = 98; r.hz.n = 2;
  if (o.lost) r.lost = o.lost;
  if (o.clip) { r.clip[o.clip.sensor] = 40; L.bbLog("gyro clipping", { sensor: o.clip.name, samples: 40 }); }
  return { r, json: L.buildExport() };
}
function report(name, o) {
  const { r, json } = run(o);
  const file = join(dir, name + ".json"); writeFileSync(file, json);
  const p = spawnSync("python", [join(here, "analyze_touch_calibration.py"), file], { encoding: "utf8" });
  const out = (p.stdout || "") + (p.stderr || "");
  return { r, json, out, tail: out.split("What looks wrong, most serious first")[1] || "", code: p.status };
}
const okTest = [{ text: "TI touch reads TI", score: 0.95, n: 100, skipped: 0, sets: { TI: 95, "": 5 } }];
const base = { selfTest: okTest };

let c = report("a", base);
check(c.code === 0 && !/Traceback/.test(c.out), "a. complete run: exit 0, no traceback");
check(/nothing flagged/.test(c.tail), "a. complete run: nothing listed " + c.tail.trim());

c = report("b", { ...base, cutAt: 1 });
check(c.code === 0 && JSON.parse(c.json).status === "stopped" && /did not finish \(status stopped\)/.test(c.tail), "b. stopped: status recorded, report says it was stopped");

c = report("c", { ...base, cutAt: 1, disconnect: true });
check(c.code === 0 && JSON.parse(c.json).status === "disconnected" && /disconnected/.test(c.tail), "c. disconnected: status recorded, report says so");

c = report("d", { ...base, frozen: 2 });
check(c.code === 0 && /INDEX|index/.test(c.tail) && /same value|frozen/.test(c.tail), "d. frozen INDEX named " + c.tail.trim());

c = report("e", { ...base, invalid: 3 });
check(c.code === 0 && /middle/i.test(c.tail) && /invalid/.test(c.tail), "e. invalid MIDDLE named " + c.tail.trim());

c = report("f", { ...base, lost: 800 });
check(c.code === 0 && /frames lost/.test(c.tail), "f. frame loss reported " + c.tail.trim());

c = report("g", { ...base, clip: { sensor: 4, name: "RING" } });
check(c.code === 0 && /ring/i.test(c.tail) && /clip/i.test(c.tail), "g. clipped RING named " + c.tail.trim());

c = report("h", { ...base, frameCap: 1000 });
check(c.code === 0 && /end of the stream is missing/.test(c.tail), "h. buffer full warns " + c.tail.trim());

c = report("i", { selfTest: [{ text: "TI touch reads TI", score: 0.2, n: 100, skipped: 0, sets: { TM: 80, TI: 20 } }] });
check(c.code === 0 && /FAIL/.test(c.out) && /self-test failed/.test(c.tail), "i. self-test failure shown " + c.tail.trim());

// raw values survive the trip: float32 in the box, 3 decimals in the file
{
  const { r, json } = run(base);
  const rows = JSON.parse(json).raw.rows; let worst = 0;
  for (let i = 0; i < r.bb.n; i++) {
    if (rows[i][0] !== r.bb.t[i]) worst = Infinity;
    for (let k = 0; k < 36; k++) worst = Math.max(worst, Math.abs(rows[i][2 + k] - r.bb.v[i * 36 + k]));
  }
  check(rows.length === r.bb.n && worst <= 0.0005 + 1e-6, `raw rows match the stored float32 values (max diff ${worst.toExponential(1)})`);
}
// size of a full 5 minute run (15000 frames at 50 Hz)
{
  const { r, json } = run(base);
  const mb = json.length / r.bb.n * 15000 / 1e6;
  console.log(`size: ${(json.length / 1e6).toFixed(2)} MB for ${r.bb.n} frames, about ${mb.toFixed(1)} MB for 5 min at 50 Hz`);
  check(mb < 40, "5 minute export under 40 MB");
}
if (process.env.BB_KEEP) console.log("kept: " + dir); else rmSync(dir, { recursive: true, force: true });
console.log(failed ? `\n${failed} FAILED` : "\nall cases passed");
process.exit(failed ? 1 : 0);
