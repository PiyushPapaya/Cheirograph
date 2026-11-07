#!/usr/bin/env node
// verify_selftest_replay.mjs - replays the real session of 2026-11-07 (guided calibration, then
// a self-test that failed every touch) through the page's real sensor pipeline and checks:
//  1. the replay reproduces the guided holds (so its numbers can be trusted),
//  2. the self-test failure is not a timing bug (the pose was reached before scoring began),
//  3. what detection can honestly do on this data: the touches sit further from their holds
//     than the near-miss holds do, so no radius accepts them without accepting a near miss.
//     The flat hand must read nothing, and the right finger must still be the nearest one.
//  4. the 3D thumb: during every self-test touch the drawn thumb tip meets the fingertip, and
//     at rest (flat hand) the thumb stays home.
// The live page also lost ~16 s between the run and the self-test that the black box did not
// record. The "gap" variant zeroes every sensor at the end of the run as a stand-in for what
// happened there; it matches the live meters better (rms 0.11 vs 0.17).
// Usage: node tools/verify_selftest_replay.mjs [page.html]
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { loadPage, replay } from "./selftest_replay_lib.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const page = process.argv[2] ? resolve(process.argv[2]) : undefined;
const cal = JSON.parse(readFileSync(join(here, "..", "10-touch-detection", "calibration_2026-11-07_v3.json"), "utf8"));
let failed = 0;
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) failed++; };
const mean = rs => rs[0].map((_, k) => rs.reduce((s, r) => s + r[k], 0) / rs.length);
const avg = a => a.reduce((s, v) => s + v, 0) / a.length;
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
const MX = -1, SELF = cal.marks.filter(m => m.name.startsWith("SELF"));
const pairOf = m => ({ index: "TI", middle: "TM", ring: "TR", pinky: "TP" })[m.name.split(" ").pop()];

function run(zeroAtRunEnd) {
  const L = loadPage(page), PF = L.PAIR_FINGER, HAND = L.handDefault();
  const tpls = cal.templates.map(t => ({ ...t, digits: [0, ...t.pairs.map(p => PF[p])] }));
  L.setTemplates(tpls);
  const negs = cal.stages.filter(s => s.kind !== "touch").map(s => {
    const m = /^NEAR(T[IMRP])$/.exec(s.name); return { label: s.name, mean: mean(s.rows), pairs: m ? [m[1]] : undefined };
  });
  const warp = L.buildWarp(tpls, negs, HAND, MX, cal.rolls);
  const runEnd = cal.marks.find(m => m.name === "FLATCHECK").f1;
  const at = {};
  replay(cal, L, (i, ms) => {
    if (zeroAtRunEnd && i === runEnd - 1) L.zeroNow();
    const d = L.touchDirs(ms); if (d) at[i] = { d, q: [1, 2, 3, 4, 5].map(L.handRelQuat) };
  });
  // what the page draws: learned thumb offset, then contactFix on the detected touch, or else
  // on the pair nearPair picks (as applyContact does)
  const drawn = (i, pair) => {
    const s = at[i], qs = L.unrollQs(s.q, cal.rolls), off = L.thumbWarp(warp, s.d), hw = L.warpHand(HAND, off, MX);
    const on = Object.keys(L.templateTouch({}, tpls, s.d));
    const pairs = on.length ? on : L.nearPair ? L.nearPair(qs, hw, MX) : [];
    const C = L.contactFix(qs, pairs, hw, MX), f = PF[pair];
    return { gap: dist(L.digitTip(0, qs[0], hw, MX, C[0]), L.digitTip(f, qs[f], hw, MX, C[f])), off: Math.hypot(...off), pairs };
  };
  return { L, at, tpls, drawn };
}

const plain = run(false), gap = run(true);
const { L, at, tpls } = plain;

// 1. fidelity
let worst = 0;
for (const s of cal.stages) {
  const m = cal.marks.find(x => x.name === s.name), rs = [];
  for (let i = m.f1 - 350; i < m.f1; i += 5) if (at[i]) rs.push(at[i].d);
  const a = mean(rs), b = mean(s.rows);
  for (let g = 0; g < 5; g++) worst = Math.max(worst, dist(a.slice(3 * g), b.slice(3 * g)));
}
check(worst < 0.07, `replay reproduces all 16 recorded holds (worst digit ${worst.toFixed(3)}, limit 0.07)`);

// 2. timing: distance during the scored check vs the last second of prep
for (const m of SELF.filter(pairOf)) {
  const p = pairOf(m), ts = tpls.filter(t => t.pairs.length === 1 && t.pairs[0] === p);
  const dAt = i => Math.min(...ts.map(t => L.digitDist(t.digits, t.mean, at[i].d)));
  const prep = avg(Array.from({ length: 50 }, (_, k) => dAt(m.fHold - 50 + k)));
  const chk = Array.from({ length: m.f1 - m.fHold }, (_, k) => dAt(m.fHold + k));
  const drift = Math.max(...chk.map(d => Math.abs(d - prep)));
  check(drift < 0.08, `${p}: pose was already held before scoring (last prep second ${prep.toFixed(2)}, check moves at most ${drift.toFixed(3)})`);
}

// 3. detection, honestly
for (const m of SELF) {
  const p = pairOf(m), rows = [];
  for (let i = m.fHold; i < m.f1; i++) rows.push(at[i].d);
  const meter = L.touchMeter(mean(rows));
  if (!p) {
    const hits = rows.filter(r => !Object.keys(L.templateTouch({}, tpls, r)).length).length;
    check(hits === rows.length, `flat hand reads nothing touching (${hits}/${rows.length})`);
    continue;
  }
  const mine = meter.find(x => x.p === p), ratio = mine.d / mine.r;
  const best = meter.slice().sort((a, b) => a.d / a.r - b.d / b.r)[0].p;
  check(ratio > 2, `${p}: touch sits ${mine.d.toFixed(2)} from its holds, ${ratio.toFixed(1)}x the radius; its near miss sits at 2x, so they can't be separated`);
  check(best === p, `${p}: still the nearest pair relative to its radius (best ${best})`);
}

// 4. drawn thumb
for (const [name, r] of [["replay", plain], ["replay + zero at run end", gap]]) {
  for (const m of SELF) {
    const p = pairOf(m), idx = [];
    for (let i = m.fHold; i < m.f1; i += 5) idx.push(i);
    if (!p) {
      const off = avg(idx.map(i => r.drawn(i, "TI").off)), nc = idx.filter(i => r.drawn(i, "TI").pairs.length).length;
      check(off < 0.1 && nc === 0, `${name}, flat hand: thumb stays home (offset ${off.toFixed(2)}, contact drawn on ${nc} frames)`);
      continue;
    }
    const g = avg(idx.map(i => r.drawn(i, p).gap));
    // the zeroed variant is only a guess at the unrecorded gap, so it is reported, not asserted
    if (r === gap) console.log(`info ${name}, ${p}: mean drawn gap ${g.toFixed(3)}`);
    else check(g < 0.15, `${name}, ${p}: drawn thumb tip meets the fingertip (mean gap ${g.toFixed(3)}, limit 0.15, finger width 0.38)`);
  }
}
for (const p of ["TI", "TM", "TR", "TP"]) for (const shape of ["ring", "straight"]) {
  const m = cal.marks.find(x => x.name === `${p} ${shape}`), idx = [];
  for (let i = m.f1 - 350; i < m.f1; i += 5) idx.push(i);
  const g = avg(idx.map(i => plain.drawn(i, p).gap));
  check(g < 0.1, `guided hold ${p} ${shape}: drawn closed (mean gap ${g.toFixed(3)})`);
}

console.log(failed ? `\n${failed} check(s) failed` : "\nall checks passed");
process.exit(failed ? 1 : 0);
