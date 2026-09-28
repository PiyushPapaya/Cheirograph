# data/phase8_labelled_gestures/ — Batch-captured static poses

Drop-in target for CSVs exported from the dashboard's **Export Batch CSV**
button (`tools/handrig_dashboard.html`, Batch Capture flow). Each file holds
one or more labelled reps: per-sensor median raw accel/gyro over a held-still
window plus the fused relative orientation quaternion at capture time — see
the header comment inside any exported CSV for the exact column layout.

---

## Naming convention

The dashboard downloads a generic `handrig_batch_<timestamp>.csv`. Before
dropping a file in here, rename it to:

```
handrig_batch_<letter>_<session#>_<timestamp>.csv
```

- `<letter>` — the fingerspelling label the session was mostly/entirely
  capturing (uppercase, matches the dashboard's `label` input and the A–Z
  coverage grid, e.g. `A`, `B`, `SPACE`).
- `<session#>` — which of the ~3 sessions-per-class this capture belongs to
  (`01`, `02`, `03`, …). Increment per distinct sitting, not per export.
- `<timestamp>` — the millisecond timestamp already in the downloaded
  filename; keep it as-is so exports within a session never collide.

Example: `handrig_batch_A_02_1755000000000.csv` — letter A, second session,
that session's export timestamp.

If a single export spans multiple labels (the batch label was switched
mid-session without stopping to export), rename with the primary/last label
captured and note the mix in DOCUMENTATION.md rather than trying to
represent multiple labels in the filename.

---

## Collection target

≥ 30 reps × 3 sessions per letter — matches the coverage goal shown by the
dashboard's A–Z grid (a cell turns green at 30 reps). Vary hand position and
re-seat the glove between sessions; diversity beats raw volume.

---

## Notes

- **Do not edit sample files by hand.** If a rep looks bad, recapture it
  rather than patching the CSV.
- `.csv` files in this folder are git-ignored (see `.gitignore`) — only this
  README and the directory itself are committed until the dataset is
  finalised and ready for the Phase 9 Edge Impulse export.
