#!/usr/bin/env node
// verify_batch_export_js.mjs - Phase 8 batch export (WP-22, spec S05 and S02).
// Pulls the real batch logic out of handrig_dashboard.html, stubs the DOM and sensors, runs a
// prompt plan, exports two rows, then parses the file with tools/batch_io.load_batch.
// Checks: 24 letters + REST + SPACE + BKSP, the 10-round plan, goals, file name, session == "NN",
// meta.session, meta.posture (one code per row, never in the label).
// Usage: node tools/verify_batch_export_js.mjs
import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "handrig_dashboard.html"), "utf8");
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
let failed = 0;
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) failed++; };

const start = script.indexOf("// ===== per-letter coverage grid =====");
const end = script.indexOf('document.addEventListener("keydown"', script.indexOf("function exportBatchCSV(){"));
const names = ["HAND", "THUMB", "INDEX", "MIDDLE", "RING", "PINKY"];
const els = { batchSet: { value: "FIST" }, batchSession: { value: "7" }, batchPromptOn: { checked: true }, batchTopup: { value: "" },
  batchLabel: { value: "" }, batchPrompt: { textContent: "" } };
let saved = null;
Object.assign(globalThis, {
  document: { getElementById: (id) => els[id] || null },
  META: names.map((n, id) => ({ id, name: n })),
  ACC_OFFSET: names.map(() => [0, 0, 0]),
  S: names.map(() => ({ bias: [0, 0, 0], noise: [0, 0, 0], calUp: null })),
  r3: (v) => +v.toFixed(4), DASH_VERSION: "test", scriptHash: () => "x", device: null, deviceName: "HandRig-6IMU-v6",
  lastMask: 0xFF, mountTiltDeg: 0, handMount: 0, DEG: Math.PI / 180, mountChecked: true, REMAP_OF: [0],
  DISPLAY: { curlMode: "x" }, LINK: { hzN: 0, hzSum: 0, lost: 0 }, ZEROS: [], batchActive: true,
  batchRepCounts: {}, clearPersistedBatchRows() {}, updateBatchUI() {},
  downloadCSV: (text, name) => { saved = { text, name }; },
});
globalThis.batchRows = [];
const { BATCH_ALPHABET, BATCH_SETS, batchGoal, buildPromptPlan, batchFileName, exportBatchCSV } =
  new Function(script.slice(start, end) + " return {BATCH_ALPHABET,BATCH_SETS,batchGoal,buildPromptPlan,batchFileName,exportBatchCSV};")();

// classes and plan
const cls = BATCH_ALPHABET;
check(cls.length === 27 && !cls.includes("J") && !cls.includes("Z") && ["REST", "SPACE", "BKSP"].every((c) => cls.includes(c)), "grid = 24 letters + REST + SPACE + BKSP");
check(BATCH_SETS.CMD.join() === "SPACE,BKSP,F,W", "CMD set holds the touch poses (F and W stay letters)");
check(batchGoal("A") === 30 && batchGoal("E") === 50 && batchGoal("R") === 50, "goal 30, 50 for FIST and VUR letters");
const plan = buildPromptPlan(BATCH_SETS.STARTER);
const rounds = [...new Set(plan.map((p) => p.round))];
check(rounds.length === 10 && plan.length === 100, "prompt plan: 10 rounds x 10 classes");
check(rounds.every((r) => new Set(plan.filter((p) => p.round === r).map((p) => p.label)).size === 10), "each round visits every class once");
check(plan.map((p) => p.posture).filter((x, i, a) => a.indexOf(x) === i).join("") === "NFPHL" &&
  [1, 5, 7, 9, 10].every((r, i) => plan.find((p) => p.round === r).posture === "NFPHL"[i]), "postures: 1-4 N, 5-6 F, 7-8 P, 9 H, 10 L");
check(batchFileName("FIST", 7, 123) === "handrig_batch_FIST_07_123.csv", "file name handrig_batch_<SET>_<NN>_<ts>.csv");

// export two rows with postures
const raw = Array(6).fill(0), q = [1, 0, 0, 0];
const sample = (label, idx, posture) => { const s = { label, idx, t: Date.now(), posture }; names.forEach((n) => { s[n] = { raw, relQuat: q }; }); return s; };
globalThis.batchRows = [sample("M", 1, "N"), sample("N", 1, "F")];
exportBatchCSV();
check(saved && /^handrig_batch_FIST_07_\d+\.csv$/.test(saved.name), "export file name is built automatically: " + (saved && saved.name));

const dir = mkdtempSync(join(tmpdir(), "bexp-"));
const file = join(dir, saved.name);
writeFileSync(file, saved.text);
const py = `
import sys, json
sys.path.insert(0, ${JSON.stringify(join(here))})
from batch_io import load_batch
bf = load_batch(sys.argv[1])
assert bf.session == "07", bf.session
assert bf.meta["session"]["set"] == "FIST" and bf.meta["session"]["number"] == "07", bf.meta["session"]
assert bf.meta["session"]["id"].endswith("-07"), bf.meta["session"]
assert bf.meta["posture"] == ["N", "F"], bf.meta["posture"]
assert bf.meta["device"]["flags"] == 3, bf.meta["device"]
assert not bf.bad_lines, bf.bad_lines
print("parsed", bf.session, bf.meta["session"]["id"], bf.meta["posture"])
`;
const r = spawnSync(process.platform === "win32" ? "python" : "python3", ["-c", py, file], { encoding: "utf8" });
check(r.status === 0, "batch_io.load_batch: session == \"07\", meta.session, meta.posture " + (r.status === 0 ? r.stdout.trim() : (r.stderr || "").trim().split("\n").pop()));
const labels = saved.text.split("\n").filter((l) => !l.startsWith("#") && !l.startsWith("label")).map((l) => l.split(",")[0]);
check(labels.join() === "M,N", "posture code is not in the label column");
process.exit(failed ? 1 : 0);
