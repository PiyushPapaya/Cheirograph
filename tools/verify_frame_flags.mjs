#!/usr/bin/env node
// verify_frame_flags.mjs - firmware v6 mask bits seen by parseFrame().
// bit 6 = gyro is +-2000 dps. Clear (v5, 0x3F): banner "firmware v5 detected, flash v6", one
//   "firmware scale" black-box event for the whole stream, and no filter quaternion changes.
// 0x7F: normal, no banner. bit 7 (0xFF): watchdog notice, set once.
// Usage: node tools/verify_frame_flags.mjs [page.html]
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { loadPage, frameOf } from "./selftest_replay_lib.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const page = process.argv[2] ? resolve(process.argv[2]) : undefined;
const cal = JSON.parse(readFileSync(join(here, "..", "10-touch-detection", "calibration_2026-11-07_v3.json"), "utf8"));
const rows = cal.raw.rows;
let failed = 0;
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) failed++; };

function feed(mask, n = 60) {
  const L = loadPage(page);
  L.BB.length = 0;
  // warm the filters with normal frames first, so "no change" is meaningful
  for (let i = 0; i < 20; i++) { L.T.now = i * 20; L.parseFrame(frameOf(rows[i], i)); }
  const q0 = L.S.map(st => { const q = st.fil.three(); return [q.w, q.x, q.y, q.z]; });
  L.BB.length = 0;
  for (let i = 20; i < 20 + n; i++) {
    const f = frameOf(rows[i], i); f[6] = mask;
    L.T.now = i * 20; L.parseFrame(f);
  }
  const q1 = L.S.map(st => { const q = st.fil.three(); return [q.w, q.x, q.y, q.z]; });
  const same = q0.every((a, k) => a.every((v, j) => v === q1[k][j]));
  return { L, same, banner: L.els.fwbanner };
}

{
  const { L, same, banner } = feed(0x3F);
  check(banner && banner.textContent === "firmware v5 detected, flash v6" && banner.classList.on, "0x3F: banner shows the exact text");
  check(L.BB.filter(e => e[0] === "firmware scale").length === 1 && L.BB.length === 1, "0x3F: exactly one firmware scale event over 60 frames");
  check(same, "0x3F: no filter quaternion changed");
}
{
  const { L, same, banner } = feed(0x7F);
  check(!banner || !banner.classList.on, "0x7F: no banner");
  check(L.BB.length === 0 && !same, "0x7F: no events, filters run");
}
{
  const { L } = feed(0xFF);
  check(L.BB.filter(e => e[0] === "watchdog reset").length === 1, "0xFF: watchdog notice logged once");
  check(L.STATUS.filter(t => t.startsWith("glove rebooted by its watchdog")).length === 1, "0xFF: watchdog status set once");
  check(L.flags().lastMask === 0xFF, "0xFF: last mask kept for session facts (flags = 3)");
}
process.exit(failed ? 1 : 0);
