# DOCUMENTATION.md — Cheirograph

The **dated ledger** of planned vs. actually achieved, session by session.

Rules:
- One block per work session, newest at the top.
- Include failures — the honesty is the value.
- Update in the **same commit** as the code it describes.
- Never edit a past entry to look better than it was.

---

## Block template

```
---

### YYYY-MM-DD | Phase N — <short name>

**Plan:** What I intended to accomplish this session.

**Achieved:** What I actually got working (be specific — serial output, test result, video evidence).

**Problems & blockers:** What went wrong, what surprised me, what I had to look up.

**Next:** The very first thing to do at the start of the next session.
```

---

## Entries

*(Newest entry goes here, above this line.)*

---

### YYYY-MM-DD | Phase 0 — Repo scaffold *(example — replace with your first real session)*

**Plan:** Scaffold the repository structure and documentation before any hardware work.

**Achieved:** Created `README.md`, `GENERAL_PLAN.md`, `DECISIONS.md`, `DOCUMENTATION.md`, all firmware milestone stubs, `hardware/BOM.md`, `hardware/WIRING.md`, `tools/README.md`, `data/README.md`, `ml/README.md`, and `docs/log/` templates. Made initial scaffold commit.

**Problems & blockers:** None — this was a pure documentation pass.

**Next:** Start Phase 1: connect XIAO to laptop, install PlatformIO, verify LSM6DS3 responds on internal I²C, and stream raw accel + gyro to serial.
