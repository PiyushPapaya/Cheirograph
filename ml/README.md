# ml/ — Machine Learning Artefacts

This directory holds everything related to the TinyML classifier: Edge Impulse exports, model weights, and deployment artefacts.
It is populated during Phases 9 and 10.

---

## What lands here

| Path | Contents |
|---|---|
| `ml/edge_impulse_export/` | Arduino library exported from Edge Impulse (`.zip` → unpacked) |
| `ml/model_notes.md` | DSP block config, neural net architecture, accuracy results, confusion matrix |
| `ml/*.tflite` | Exported TFLite model (gitignored — regenerate from Edge Impulse) |

---

## Pipeline overview

1. Upload `data/` samples to Edge Impulse (via CLI or web).
2. Design DSP block: input = 5 × 4 = 20 floats (five relative quaternions); no windowing needed for static gestures.
3. Train a small dense neural net (2–3 layers, ~1 k parameters — nRF52840 has 256 kB RAM).
4. Validate: check confusion matrix, look for letter pairs with high confusion, collect more data for those.
5. Export as Arduino library; drop into `ml/edge_impulse_export/`.
6. In Phase 10: include in the firmware sketch and run inference on-device.

---

## Notes

- Model files (`*.tflite`, `*.zip`, `*.h`) are gitignored; regenerate from Edge Impulse project.
- Pin the Edge Impulse CLI version in `ml/requirements.txt` once you start using it.
- If two letters consistently confuse the model, the fix is almost always more data for that pair — not a bigger model.
