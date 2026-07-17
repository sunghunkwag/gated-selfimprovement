# SDT Gate-Integrity / Reflective-Endorsement Experiment

Which of three conditions of a self-modifying loop collapses first when
broken: (1) non-arbitrary anchor, (2) open satisfaction path, (3)
criterion-updating reflection. Holdout n=40 (seeds 101–140), frozen design.

| Arm (condition broken) | Collapse | Round | Signature |
|---|---|---|---|
| SDT_CLOSED (open path) | 40/40 | 3 | ANCHOR_VACUITY (anchor pinned ~0.03) |
| SDT_WIRE (fixed anchor) | 9/40 | ~4 | WIREHEAD ramp 0.75→0.97 |
| SDT_ARB (non-arbitrary) | 0/40 | — | drifts; worst eval competence |
| SDT_FULL (all hold) | 0/40 | — | survives, endorsed churn 4/5 |

Domain-independent result about self-modification safety: closed goals go
vacuous; self-editable anchors wirehead; only the fixed-anchor + open-path +
criterion-update triple keeps endorsement doing non-trivial work.
Reproduce: `python3 src/sdt_layer.py run 101 140 9999 holdout`.
