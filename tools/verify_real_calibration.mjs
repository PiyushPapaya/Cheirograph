#!/usr/bin/env node
// verify_real_calibration.mjs - runs the dashboard's calibration maths on a REAL glove
// calibration (first export, 2026-11-07) instead of simulated numbers.
//
// Detection is checked on held-out samples: templates come from the first half of each hold
// and are tested on the second half. It is still one session, so this says nothing about a
// new session. Those use their own templates anyway.
//
// Usage: node tools/verify_real_calibration.mjs

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "handrig_dashboard.html"), "utf8");
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
const grab = re => { const m = script.match(re); if (!m) { console.error("FAIL: section not found: " + re); process.exit(1); } return m[0]; };
const src = [grab(/const FINGER_ANCHORS=\{[\s\S]*?\n\};/), grab(/const THUMB_BASE_FRAC=[^\n]*/),
  grab(/\/\/ ===== hand kinematics =====[\s\S]*?\/\/ ===== end hand kinematics =====/),
  grab(/\/\/ ===== touch detection =====[\s\S]*?\/\/ ===== end touch detection =====/)].join("\n");
const names = "handDefault,digitTip,contactFix,rollFromFist,unrollQs,buildWarp,thumbWarp,warpHand,makeTemplate,finishTemplates,templateTouch,replayCheck,PAIR_FINGER";
const L = new Function(src + `\nreturn {${names}};`)();
const { handDefault, digitTip, contactFix, rollFromFist, unrollQs, buildWarp, thumbWarp, warpHand, makeTemplate, finishTemplates, templateTouch, replayCheck, PAIR_FINGER } = L;

const cal = JSON.parse(readFileSync(join(here, "..", "10-touch-detection", "calibration_2026-11-07.json"), "utf8"));
let failed = 0;
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) failed++; };
const MX = -1, hand = handDefault();
const dist = (a, b) => Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2]);
const mean = a => a.reduce((s, v) => s + v, 0)/a.length;

const stageOf = s => {
  if (s.kind === "touch") { const [p, shape] = s.name.split(" "); return { kind: "touch", pairs: p.split("+"), shape }; }
  const near = /^NEAR(T[IMRP])$/.exec(s.name);
  return near ? { kind: "neg", pairs: [near[1]], label: s.name } : { kind: "neg", label: s.name };
};
function build(rowsOf) {
  const templates = [], negs = [];
  for (const s of cal.stages) {
    const st = stageOf(s), t = makeTemplate(st, rowsOf(s), null);
    if (st.kind === "touch") { t.q = cal.templates.find(x => x.pairs.join("+") === st.pairs.join("+") && x.shape === st.shape).q; templates.push(t); }
    else negs.push({ label: st.label, mean: t.mean, pairs: st.pairs });
  }
  return { templates: finishTemplates(templates, negs), negs };
}

// Detection on held-out rows
const firstHalf = s => s.rows.slice(0, s.rows.length >> 1), secondHalf = s => s.rows.slice(s.rows.length >> 1);
const half = build(firstHalf);
const heldOut = cal.stages.map(s => ({ name: s.name, kind: s.kind, pairs: stageOf(s).pairs, rows: secondHalf(s) }));
const r = replayCheck(heldOut, half.templates);
check(r.ok === r.total, `held-out rows: ${r.ok}/${r.total} holds read correctly${r.bad.length ? " (" + r.bad.join(", ") + ")" : ""}`);

// Finger roll, from the fist hold
const fist = cal.stages.find(s => s.name === "FIST");
const fm = [0, 1, 2, 3, 4].map(i => [0, 1, 2].map(k => mean(fist.rows.map(r2 => r2[3*i + k]))));
const rolls = [0, ...[1, 2, 3, 4].map(i => rollFromFist(fm[i]))];
const deg = rolls.map(a => a*180/Math.PI);
console.log("     finger roll from the fist hold, deg: " + deg.slice(1).map(v => v.toFixed(0)).join(" "));
check(deg.slice(1).every(a => Math.abs(a) > 5 && Math.abs(a) < 45), "every finger shows a real, plausible roll");
check(deg[1] < deg[4], "roll grows from index to pinky, as the T5 gyro fit found");

// Thumb warp: each touch must be drawn closed on the real holds
const all = build(s => s.rows);
const warp = buildWarp(all.templates, all.negs, hand, MX, rolls);
const gapOf = (t, hnd, C) => mean(t.pairs.map(p => {
  const qs = unrollQs(t.q, rolls), f = PAIR_FINGER[p];
  return dist(digitTip(0, qs[0], hnd, MX, C ? C[0] : undefined), digitTip(f, qs[f], hnd, MX, C ? C[f] : undefined));
}));
const before = all.templates.map(t => gapOf(t, hand));
const warped = all.templates.map(t => gapOf(t, warpHand(hand, thumbWarp(warp, t.mean), MX)));
const drawn = all.templates.map(t => {
  const hw = warpHand(hand, thumbWarp(warp, t.mean), MX);
  return gapOf(t, hw, contactFix(unrollQs(t.q, rolls), t.pairs, hw, MX));
});
console.log(`     mean tip gap on real holds: ${mean(before).toFixed(2)} default, ${mean(warped).toFixed(2)} warped, ${mean(drawn).toFixed(3)} drawn`);
check(mean(warped) < 0.35, `learned thumb movement closes most of it (mean ${mean(warped).toFixed(2)}, limit 0.35)`);
check(Math.max(...drawn) < 0.1, `every real touch is drawn closed (worst ${Math.max(...drawn).toFixed(3)}, limit 0.1, finger width 0.38)`);

const flatOff = thumbWarp(warp, Array.from({ length: 15 }, (_, i) => i%3 === 2 ? 1 : 0));
check(Math.hypot(...flatOff) < 0.05, `flat hand: thumb stays home (moved ${Math.hypot(...flatOff).toFixed(3)})`);
const fistRow = fist.rows[0];
check(Object.keys(templateTouch({}, all.templates, fistRow)).length === 0, "a real fist reads no touch");

console.log(failed ? `\n${failed} check(s) failed` : "\nall real calibration checks passed");
process.exit(failed ? 1 : 0);
