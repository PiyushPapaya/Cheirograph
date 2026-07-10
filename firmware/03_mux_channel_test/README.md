# 03 — PCA9548A Mux Channel Test

> *This folder's number is a flexible guide, not a permanent label. Rename or renumber as the real build dictates.*

**Phase:** 3

**Goal:** Bring up the PCA9548A I²C multiplexer (addr 0x70); select channels one at a time; confirm that two and then all five MPU-6050s are individually readable.

**"Done" looks like:**
- Writing a channel-select byte to 0x70, then reading 0x68 returns data from the expected sensor.
- All five channels confirmed working with no cross-talk.
- Channel switching does not hang the bus.

**What this is not:** No fusion; raw data only.

**Why it matters:** The entire glove depends on this switching loop. If the mux is unreliable, nothing else works. Debug it isolated before adding sensors.

**Gotcha to watch for:** You must write the channel byte to 0x70 *before* addressing 0x68. Writing 0x00 to 0x70 disables all channels (safe idle). Forgetting to switch first results in reading from whichever channel was last selected — which looks like plausible data and is hard to catch.
