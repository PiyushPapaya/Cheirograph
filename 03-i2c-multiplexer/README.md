# 03 — PCA9548A Mux Channel Test

> *This folder's number is a flexible guide, not a permanent label. Rename or renumber as the real build dictates.*

**Phase:** 3
**Status:** ✅ mux bring-up confirmed — see below. No standalone sketch was flashed for this folder; the mux got proven directly by the Phase 4 sketch's `scanChannels()` boot routine instead (all five channels ACKed 0x68, see `firmware/04_all_imus_raw/README.md`).

**Goal:** Bring up the PCA9548A I²C multiplexer (addr 0x70); select channels one at a time; confirm that two and then all five MPU-6050s are individually readable.

**"Done" looks like:**
- Writing a channel-select byte to 0x70, then reading 0x68 returns data from the expected sensor.
- All five channels confirmed working with no cross-talk.
- Channel switching does not hang the bus.

**What this is not:** No fusion; raw data only.

**Why it matters:** The entire glove depends on this switching loop. If the mux is unreliable, nothing else works. Debug it isolated before adding sensors.

**Gotcha to watch for:** You must write the channel byte to 0x70 *before* addressing 0x68. Writing 0x00 to 0x70 disables all channels (safe idle). Forgetting to switch first results in reading from whichever channel was last selected — which looks like plausible data and is hard to catch.

---

## Bench result (2026-07-16)

`firmware/04_all_imus_raw/04_all_imus_raw.ino`'s boot-time `scanChannels()`
swept all 8 mux channels and found `0x68` on exactly channels 0–4, nothing on
5–7 (unused), and no cross-talk — the "done" criteria above are satisfied by
that run. No dedicated `03_*.ino` was written since the all-five-sensor
sketch subsumed this test; if a channel ever misbehaves in isolation, use the
`tcaSelect()` + `scanChannels()` pattern from that sketch as the starting
point for a focused re-test.
