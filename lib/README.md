# firmware/lib — Shared Library Code

This directory stays **empty until shared code stabilises**.

The rule: copy-paste code between milestone folders early; factor it here only when it is:
1. Stable and unlikely to change per-milestone, and
2. Genuinely reused by two or more milestone sketches.

Premature factoring makes it impossible to look at an old milestone folder and see a self-contained, runnable snapshot of that point in the build. Keep each milestone self-contained longer than feels comfortable; extract here later.

Candidates that will eventually land here: Madgwick implementation, mux-channel helper, serial format writer.
