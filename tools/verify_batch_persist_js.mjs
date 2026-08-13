#!/usr/bin/env node
// verify_batch_persist_js.mjs - throwaway-style verification for the Batch
// Capture localStorage crash-resilience helpers and the A-Z coverage grid
// math ported into tools/handrig_dashboard.html. Same idea as
// verify_batch_gate_js.mjs: eval just the pure logic slices (stubbed
// localStorage / document, no real DOM/BLE) and drive them through the
// documented behaviors.
//
// Usage: node tools/verify_batch_persist_js.mjs

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "handrig_dashboard.html"), "utf8");
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];

let failures = 0;
function check(name, cond) {
  console.log(`${cond ? "PASS" : "FAIL"} - ${name}`);
  if (!cond) failures++;
}

// ===== 1) persist / restore / clear =====
{
  const start = script.indexOf("// ===== batch-capture crash resilience =====");
  const end = script.indexOf("// ===== batch-capture gate:");
  if (start < 0 || end < 0) {
    console.error("could not locate the batch-capture crash-resilience section");
    process.exit(1);
  }

  // minimal in-memory localStorage stub
  function makeStorage() {
    const store = new Map();
    return {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => store.set(k, String(v)),
      removeItem: (k) => store.delete(k),
      _store: store,
    };
  }

  globalThis.localStorage = makeStorage();
  let batchRows = [];
  let batchRepCounts = {};
  globalThis.batchRows = batchRows;
  globalThis.batchRepCounts = batchRepCounts;
  // eslint-disable-next-line no-eval
  (0, eval)(script.slice(start, end));
  // BATCH_STORAGE_KEY is a `const` inside the eval'd slice -- indirect eval's
  // block-scoped bindings aren't visible as bare identifiers from this
  // module's own scope, so pull the literal straight out of the source
  // instead of relying on the binding leaking out.
  const BATCH_STORAGE_KEY = script.match(/BATCH_STORAGE_KEY\s*=\s*"([^"]+)"/)[1];

  // fresh load, nothing saved yet -> restore is a no-op
  restoreBatchRows();
  check("restore with empty storage leaves batchRows empty", batchRows.length === 0);

  // simulate two captures
  batchRows.push({ label: "A", idx: 1, t: 1 });
  batchRepCounts.A = 1;
  persistBatchRows();
  batchRows.push({ label: "A", idx: 2, t: 2 });
  batchRepCounts.A = 2;
  persistBatchRows();

  check("persist wrote to localStorage", localStorage.getItem(BATCH_STORAGE_KEY) !== null);

  // simulate a reload: fresh in-memory vars, same localStorage backing
  batchRows = [];
  batchRepCounts = {};
  globalThis.batchRows = batchRows;
  globalThis.batchRepCounts = batchRepCounts;
  restoreBatchRows();
  check("restore after 'reload' recovers both reps", globalThis.batchRows.length === 2);
  check("restore after 'reload' recovers rep counts", globalThis.batchRepCounts.A === 2);

  // export clears the backup so a finished session doesn't reappear later
  clearPersistedBatchRows();
  check("clear removes the backup", localStorage.getItem(BATCH_STORAGE_KEY) === null);
  globalThis.batchRows = [];
  globalThis.batchRepCounts = {};
  restoreBatchRows();
  check("restore after clear stays empty", globalThis.batchRows.length === 0);

  // corrupt/old-shape data must not throw and must be ignored
  localStorage.setItem(BATCH_STORAGE_KEY, "{not json");
  let threw = false;
  try {
    restoreBatchRows();
  } catch (e) {
    threw = true;
  }
  check("restore tolerates corrupt JSON without throwing", threw === false);
}

// ===== 2) per-letter coverage grid math =====
{
  const start = script.indexOf("// ===== per-letter coverage grid =====");
  const end = script.indexOf("function exportBatchCSV(){");
  if (start < 0 || end < 0) {
    console.error("could not locate the per-letter coverage grid section");
    process.exit(1);
  }

  // minimal document stub: getElementById("bg-<L>") returns a cell object
  // with a settable textContent-backed <b> and a classList.toggle we can
  // inspect, matching what buildBatchGrid()'s real innerHTML would produce.
  const cells = new Map();
  function makeCell() {
    const b = { textContent: "" };
    const classes = new Set();
    return {
      querySelector: () => b,
      classList: { toggle: (name, on) => (on ? classes.add(name) : classes.delete(name)) },
      _b: b,
      _classes: classes,
    };
  }
  "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").forEach((l) => cells.set("bg-" + l, makeCell()));
  globalThis.document = { getElementById: (id) => cells.get(id) || null };
  globalThis.batchRepCounts = { A: 30, B: 29, C: 0 };
  // eslint-disable-next-line no-eval
  (0, eval)(script.slice(start, end));

  updateBatchGrid();
  check("letter at goal (30) is marked done", cells.get("bg-A")._classes.has("done") === true);
  check("letter one under goal (29) is not done", cells.get("bg-B")._classes.has("done") === false);
  check("uncaptured letter (0) renders 0, not done",
    cells.get("bg-C")._b.textContent === 0 && !cells.get("bg-C")._classes.has("done"));
  check("count text matches batchRepCounts", cells.get("bg-A")._b.textContent === 30);
  check("every letter A-Z got a rendered count (no gaps in the grid)",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").every((l) => cells.get("bg-" + l)._b.textContent !== ""));
}

process.exit(failures === 0 ? 0 : 1);
