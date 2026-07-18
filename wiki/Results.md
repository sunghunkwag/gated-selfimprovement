# Results

## Positive (counterfactually controlled)
- **Compounding RSI:** R5PLUS − ROUND1_5X = +1.55 tasks, p<1e-4, n=100 (local n=40 + Kaggle n=60).
- **MetaForge:** adaptive 19→23 vs frozen flat-19 over 8 waves (+21%), searcher v0→v3.
- **Open-ended:** 189 certified novel behaviours (OPEN) vs 0 (CLOSED) over 4,444 generations.
- **Turing-complete:** 15 gated macros (OPEN) vs 0 (CLOSED), 8 seeds; held-out `reverse` solved.
- **Cross-substrate transfer:** +2.00 tasks (p=0.0008); learning premium +1.00 (p=0.014).
- **Real-file repair:** frozen 0.204 → adaptive 1.000 on file-world families (incl. repo_repair).

## Null / negative (reported, not hidden)
- Repaired chain does **not** beat the untrained baseline (unigram container ceiling).
- Original chain was **harmful** (ROUND5 − COLD = −2.08, p<1e-4) before repair.
- Meta-RL grid: flat at full config (all contrasts within noise floor).
- Open-ended growth is linear, not accelerating; hits a search-dilution wall.
- Compositional transfer limited by skill I/O interface.

See per-experiment files in `results/`.
