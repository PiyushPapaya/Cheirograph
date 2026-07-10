# 06 — Relative Orientation + Skeleton Visualiser

> *This folder's number is a flexible guide, not a permanent label. Rename or renumber as the real build dictates.*

**Phase:** 6

**Goal:** Compute each finger's orientation *relative to the hand*, and add a Python 3D skeleton visualiser.

**The core math:**
```
q_rel = conj(q_hand) ⊗ q_finger
```
`conj(q_hand)` is the conjugate of the hand quaternion (negate x, y, z; keep w).  
`⊗` is quaternion multiplication.  
The result expresses `q_finger` in the hand's own coordinate frame — waving the arm in space produces no change; curling a finger produces the full signal.

**"Done" looks like:**
- Five relative-quaternion streams on serial.
- `tools/skeleton_viz.py` renders a 3D hand that mirrors your actual hand pose.
- Rotating the wrist 90° changes nothing in the visualiser. Curling a finger changes it clearly.

**Why this milestone matters:** This is the last signal-processing step before data collection. If relative orientation is wrong here, every labelled sample and the entire classifier will be wrong. Verify carefully.
