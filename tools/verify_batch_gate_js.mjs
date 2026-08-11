#!/usr/bin/env node
// verify_batch_gate_js.mjs - throwaway-style verification for the Batch
// Capture GO-baseline gate ported into tools/handrig_dashboard.html
// (window.BatchGate). Same idea as verify_noise_baseline_js.mjs: eval just
// the pure state-machine slice of the script (no DOM/BLE) and drive it
// through the two documented states -- no baseline recorded yet, and a GO
// recorded this session -- plus the "never cleared by a later NO-GO" and
// "reset on disconnect" rules.
//
// Usage: node tools/verify_batch_gate_js.mjs

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "handrig_dashboard.html"), "utf8");
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
const start = script.indexOf("// ===== batch-capture gate:");
const end = script.indexOf("function applyBatchGate(){");
if (start < 0 || end < 0) {
  console.error("could not locate the batch-capture gate section in handrig_dashboard.html");
  process.exit(1);
}

// The gate slice only touches window.BatchGate (plain object assignment) and
// a closed-over `baselineGoAt` var -- no DOM, no `device`. A bare `window`
// stub is enough to load it standalone.
globalThis.window = globalThis;
// eslint-disable-next-line no-eval
(0, eval)(script.slice(start, end));

const { BatchGate } = window;

let failures = 0;
function check(name, cond) {
  console.log(`${cond ? "PASS" : "FAIL"} - ${name}`);
  if (!cond) failures++;
}

// 1) no-baseline-yet: fresh session, never ran a noise check -> not satisfied,
//    even while connected.
check("no baseline yet -> not satisfied (connected)", BatchGate.satisfied(true) === false);
check("no baseline yet -> not satisfied (disconnected)", BatchGate.satisfied(false) === false);
check("no baseline yet -> hasBaseline() false", BatchGate.hasBaseline() === false);

// 2) GO recorded this session -> satisfied while connected, not while
//    disconnected (connection is checked independently of the flag).
BatchGate.setGo(true);
check("GO recorded -> hasBaseline() true", BatchGate.hasBaseline() === true);
check("GO recorded + connected -> satisfied", BatchGate.satisfied(true) === true);
check("GO recorded + disconnected -> not satisfied", BatchGate.satisfied(false) === false);

// 3) a later NO-GO does not clear an earlier GO this session.
BatchGate.setGo(false);
check("later NO-GO does not clear earlier GO", BatchGate.satisfied(true) === true);

// 4) reset() (called on BLE disconnect) clears the flag for the next session.
BatchGate.reset();
check("reset() clears the flag", BatchGate.satisfied(true) === false);

process.exit(failures === 0 ? 0 : 1);
