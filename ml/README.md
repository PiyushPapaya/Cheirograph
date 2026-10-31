# ml/

Everything for the classifier: the dataset, Edge Impulse exports, and model notes. This is Phases 8 to 10. No real data or model exists yet.

## What's here now

- [`future-data-collection-plan.md`](future-data-collection-plan.md): how data gets recorded, named and checked.

## What will land here

| Path | Contents |
|---|---|
| `ml/dataset/` | Renamed batch exports from the dashboard (CSVs gitignored) |
| `ml/model_notes.md` | Features, model architecture, accuracy, confusion matrix |
| `ml/edge_impulse_export/` | Arduino library exported from Edge Impulse |

## Pipeline

1. Collect data with the dashboard and run [`tools/check_dataset.py`](../tools/check_dataset.py) on every export.
2. Get a baseline first with [`tools/train_baseline.py`](../tools/train_baseline.py) (kNN). It compares three feature sets:
   - `quat`: 5 relative quaternions, 20 numbers
   - `dir`: the direction each finger points in the hand frame, 15 numbers
   - `curl`: only the palm-ward part, 5 numbers, immune to yaw drift
   
   Trust the leave-one-session-out score, not the random split.
3. Upload to Edge Impulse. Static shapes don't need windowing.
4. Train a small dense network (2–3 layers, roughly 1k parameters). The nRF52840 has 256 kB RAM.
5. Check the confusion matrix. For confused pairs, collect more data before trying a bigger model.
6. Export as an Arduino library and run inference on the XIAO (Phase 10).

## Notes

- Model files (`*.tflite`, `*.zip`, `*.h`) and data files are gitignored. Regenerate them from the Edge Impulse project.
- Pin the Edge Impulse CLI version in `ml/requirements.txt` once it's in use.
