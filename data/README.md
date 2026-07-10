# data/ — Labelled Training Samples

This directory holds the raw labelled data collected from the glove for the TinyML classifier.
It is populated during Phase 8.

---

## Structure

```
data/
├── README.md
├── A/           — samples for letter A
│   ├── session_01_001.csv
│   ├── session_01_002.csv
│   └── ...
├── B/
└── ...
```

Each sample file: one CSV of relative quaternions for a held gesture (five `qw,qx,qy,qz` rows, one per finger). Format matches the fused serial output from `firmware/06_relative_orientation/` onward.

---

## Collection target

≥ 30 samples × 3 separate sessions per class. Varied hand positions, lighting, and time of day — anything that keeps the glove seated slightly differently. Diversity beats volume for a 5-feature classifier.

---

## Export to Edge Impulse

Data collected here will be formatted for upload to Edge Impulse in Phase 9. Tooling for this export lives in `tools/capture_data.py` once implemented.

---

## Notes

- **Do not edit sample files by hand.** If a sample is bad, delete it and recollect.
- Large `.csv` and `.npy` files are excluded from git by `.gitignore`; commit only the directory structure and this README until the dataset is finalised.
