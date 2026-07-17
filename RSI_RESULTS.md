# Baseline RSI Audit (before the upgrade)

Running the six original files' own pre-registered designs with
counterfactual controls, the answer to "is there meaningful recursive
self-improvement?" was, at first: **mostly no.**

- Expedition XV (n=12): ROUND5 − ROUND1_5X = +1.5 (p=0.054) but
  ROUND5 − COLD = **−1.5 (p=0.039)** — recursive prior-fitting lands BELOW
  no-learning (overfits source stats).
- Expedition XV-RL (n=20): every mechanism contrast smaller than the noise
  floor.
- MetaForge wave-1 counterfactual (capped): adaptive = frozen, delta 0.

This honest null motivated the diagnosis-and-repair in UPGRADE_RESULTS.md
and the full-budget re-runs in FINAL_RESULTS.md (where MetaForge, given full
budget, shows +21% adaptive vs frozen). Reproduce: `python3 experiments/rsi_experiments.py report`.
