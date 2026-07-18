# Engineered Recursive Self-Improvement (RSI Upgrade)

The original Expedition-XV chain was measured to be *harmful*
(ROUND5 − COLD = −2.075, p<1e-4). Diagnosed (noisy partial-fitness pool;
occurrence counts collapse entropy; no step control) and repaired: M1
solved-only deduped credit, M2 presence-based level-stratified target, M3
trust-region + entropy floor, M4 generalization-gated acceptance + rollback.

## Confirmatory holdout (n=40 local + n=60 Kaggle = n=100), frozen params

| Contrast | Local n=40 | Kaggle n=60 |
|---|---|---|
| R5PLUS − ROUND1_5X (compounding) | +1.55, p<1e-4 | +1.47, p=5e-5 |
| R5PLUS − ROUND5 (vs original) | +2.18, p<1e-4 | +1.67, p=5e-5 |
| ROUND5 − COLD (original harm) | −2.08, p<1e-4 | −2.03, p=5e-5 |
| R5PLUS − COLD (absolute) | +0.10, ns | −0.37, ns |

Compounding recovered (pre-registered criterion, p≈1e-4, two environments);
the original self-harm eliminated. Not claimed: beating the untrained
baseline (unigram container ceiling). Meta-RL grid: null at full config.
Reproduce: `python3 src/rsi_upgrade.py report2`.
