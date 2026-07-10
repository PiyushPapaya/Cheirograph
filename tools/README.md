# tools/ — Python Utility Scripts

Python 3 scripts for interacting with the glove over serial during development.
None are implemented yet — this README documents what will land here.

---

## Planned scripts

### `plot_raw.py`
Live serial plotter for raw IMU data.
- Reads `millis,sensor_id,ax,ay,az,gx,gy,gz` lines.
- Plots the six channels (ax/ay/az/gx/gy/gz) per selected sensor_id.
- Dependency: `pyserial`, `matplotlib`.
- Added in Phase 4.

### `skeleton_viz.py`
3D hand-skeleton visualiser using relative quaternions.
- Reads `millis,sensor_id,qw,qx,qy,qz` lines (relative quaternions, Phases 6+).
- Renders a simplified 5-finger hand skeleton rotating in real time.
- Dependency: `pyserial`, `matplotlib` (3D).
- Added in Phase 6.

### `capture_data.py`
Labelled training-data capture tool.
- Prompts for a label (A–Z or custom), records N samples, saves to `data/<label>/`.
- Used in Phase 8 for Edge Impulse dataset collection.

---

## Serial data contract

Stable formats — do not change without updating the relevant parser in the same commit.

**Raw (Phases 1–4):**
```
millis,sensor_id,ax,ay,az,gx,gy,gz
```

**Fused / relative (Phases 5–):**
```
millis,sensor_id,qw,qx,qy,qz
```

`sensor_id`: 0 = hand (onboard XIAO), 1–5 = fingers (mux channels 0–4 = thumb–pinky).

---

## Setup

```bash
cd tools
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` will be committed alongside the first script.
