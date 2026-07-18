# Experiments

| # | Battery | Question | Command |
|---|---|---|---|
| 1 | RSI audit | Is there any RSI in the original files? (baseline: mostly no) | `python3 experiments/rsi_experiments.py report` |
| 2 | RSI upgrade (xv2) | Does the repaired mechanism compound? | `python3 src/rsi_upgrade.py report2` |
| 3 | MetaForge counterfactual | Does the searcher improve the searcher? | `python3 src/omniforge.py rsi --mode file-battery` |
| 4 | Open-ended loop | How long does gated expansion last, and why does it stop? | `python3 src/openforge.py report` |
| 5 | Turing-complete | Does self-improvement port to branches+loops? | `python3 src/tforge.py selftest` |
| 6 | Cross-substrate transfer | Do learned skills generalize across media? | `python3 src/transferforge.py run 1 11 300` |
| 7 | SDT gate integrity | Which gate designs resist wireheading? | `python3 src/sdt_layer.py report` |

Long-horizon versions live in `experiments/kaggle/` (offline CPU kernels).
