# lib/

Shared firmware code. Empty on purpose for now.

Code only moves here once it's:
1. stable, and
2. actually used by two or more milestone sketches.

Until then each stage folder keeps its own copy. That costs some duplication, but every old stage stays a self-contained snapshot you can open and flash as it was. Moving code out too early breaks that.

Likely candidates later: the Madgwick filter, the mux helper, the raw-register clone IMU driver, and the I²C bus recovery.
