#!/usr/bin/env node
// verify_touch_js.mjs - the dashboard's touchProbs() must give the same numbers as Python.
// Extracts the section between "// ===== touch detection =====" and
// "// ===== end touch detection =====" from handrig_dashboard.html (pure functions,
// no DOM) and checks it against a fixture written by verify_touch_model.py:
//   {"model": {...train_touch.py JSON...}, "dirs": [[15] x n], "probs": [[4] x n]}
//
// Usage: node tools/verify_touch_js.mjs <fixture.json>

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "handrig_dashboard.html"), "utf8");
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
const start = script.indexOf("// ===== touch detection =====");
const end = script.indexOf("// ===== end touch detection =====");
if (start < 0 || end < 0) {
  console.error("could not locate the touch detection section in handrig_dashboard.html");
  process.exit(1);
}
if (!process.argv[2]) {
  console.log("skipped: needs a fixture, which verify_touch_model.py writes and passes in (step 6). Usage: node tools/verify_touch_js.mjs <fixture.json>");
  process.exit(0);
}
const fx = JSON.parse(readFileSync(process.argv[2], "utf8"));

// eslint-disable-next-line no-new-func
const { touchProbs, touchState, validTouchModel } =
  new Function(script.match(/const PAIR_FINGER=.*/)[0] + script.slice(start, end) + "; return {touchProbs, touchState, validTouchModel};")();

let failures = 0;
function check(name, cond) {
  console.log(`${cond ? "PASS" : "FAIL"} - ${name}`);
  if (!cond) failures++;
}

let worst = 0;
fx.dirs.forEach((d, r) => {
  const p = touchProbs(fx.model, d);
  p.forEach((v, i) => { worst = Math.max(worst, Math.abs(v - fx.probs[r][i])); });
});
check(`touchProbs matches Python on ${fx.dirs.length} rows (max diff ${worst.toExponential(2)})`, worst < 1e-9);

check("touchState holds at 0.5 when already on", touchState([true], [0.5])[0] === true);
check("touchState stays off at 0.5 when already off", touchState([false], [0.5])[0] === false);
check("touchState turns on at 0.61", touchState([false], [0.61])[0] === true);
check("touchState turns off at 0.39 when on", touchState([true], [0.39])[0] === false);
check("validTouchModel accepts the fixture model", validTouchModel(fx.model) === true);
check("validTouchModel rejects a short mu", validTouchModel({ ...fx.model, mu: fx.model.mu.slice(1) }) === false);
check("validTouchModel rejects sd = 0", validTouchModel({ ...fx.model, sd: fx.model.sd.map(() => 0) }) === false);

process.exit(failures ? 1 : 0);
