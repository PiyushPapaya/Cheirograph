#!/usr/bin/env node
// verify_noise_baseline_js.mjs - throwaway-style verification for the
// GO/NO-GO noise-baseline logic ported into tools/handrig_dashboard.html
// (window.NoiseBaseline.analyze). Same idea as feeding a hand-built synthetic
// CSV into tools/analyze_noise_baseline.py: build synthetic frame arrays in
// the exact recFrames shape ([t_ms, hand_ax,...,pinky_gz]) and check the
// verdict, instead of needing a live BLE capture to exercise the three
// documented cases (clean-noisy-still -> GO, constant-value -> NO-GO,
// short array -> NO-GO).
//
// Usage: node tools/verify_noise_baseline_js.mjs

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "handrig_dashboard.html"), "utf8");
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
const start = script.indexOf("// ===== noise baseline GO/NO-GO");
const end = script.indexOf("// ===== batch capture =====");
if (start < 0 || end < 0) {
  console.error("could not locate the noise-baseline section in handrig_dashboard.html");
  process.exit(1);
}

// The ported block only touches window.NoiseBaseline (plain object assignment)
// and a handful of pure helper functions -- no THREE.js, no DOM. A bare
// `window` stub is enough to load it standalone.
globalThis.window = globalThis;
// eslint-disable-next-line no-eval
(0, eval)(script.slice(start, end));

const { analyze } = window.NoiseBaseline;
const N_SENSORS = 6;
const HZ = 20;

function mkFrames(n, sensorFn) {
  const frames = [];
  for (let i = 0; i < n; i++) {
    const t = i * (1000 / HZ);
    const row = [t];
    for (let s = 0; s < N_SENSORS; s++) row.push(...sensorFn(i, s));
    frames.push(row);
  }
  return frames;
}

let failures = 0;
function check(name, cond) {
  console.log(`${cond ? "PASS" : "FAIL"} - ${name}`);
  if (!cond) failures++;
}

// 1) clean-noisy-still: 60s, |a|~1g with small noise, gyro noise/bias well
//    under threshold -> GO.
const clean = mkFrames(60 * HZ, () => {
  const n = () => (Math.random() - 0.5) * 0.01;
  return [n(), n(), 1 + n(), (Math.random() - 0.5) * 2, (Math.random() - 0.5) * 2, (Math.random() - 0.5) * 2];
});
const rClean = analyze(clean);
check("clean-noisy-still -> GO", rClean.go === true);

// 2) constant-value: every frame bit-identical per sensor -> stuck-frame
//    detector trips -> NO-GO, even though duration is long enough.
const constant = mkFrames(60 * HZ, () => [0, 0, 1, 0, 0, 0]);
const rConstant = analyze(constant);
check("constant-value -> NO-GO", rConstant.go === false);
check("constant-value flagged via stuck-frame detector", rConstant.sensors[0].stuck > 0);

// 3) short array: only 5s of otherwise-clean data -> 50s minimum-duration
//    guard trips -> NO-GO regardless of per-sensor health.
const short = mkFrames(5 * HZ, () => {
  const n = () => (Math.random() - 0.5) * 0.01;
  return [n(), n(), 1 + n(), (Math.random() - 0.5) * 2, (Math.random() - 0.5) * 2, (Math.random() - 0.5) * 2];
});
const rShort = analyze(short);
check("short-capture -> NO-GO", rShort.go === false && rShort.shortCapture === true);

process.exit(failures === 0 ? 0 : 1);
