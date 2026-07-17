# gated-selfimprovement — Wiki

A measurement-first study of recursive self-improvement (RSI). Every gain is
**counterfactually gated**: credited only if a matched control, denied the one
mechanism under test, does worse at equal budget. LLM-free, pure-Python stdlib,
deterministic.

## Pages
- [Architecture](Architecture) — the substrates, engines, and the unified model
- [Methodology](Methodology) — counterfactual gates, held-out eval, certificates
- [Experiments](Experiments) — what each battery tests and how to run it
- [Results](Results) — headline numbers and the honest nulls
- [Reproducing](Reproducing) — commands, seeds, Kaggle kernels
- [FAQ](FAQ) — "is this AGI?", "why no LLM?", "is it a toy?"

## 30-second version
Two arms run the same loop; one may admit self-discovered building blocks (GATED),
one may not (FROZEN). The gap is the evidence. Positive results: compounding RSI
(p<1e-4, n=100), searcher-improves-searcher (+21% vs frozen), certified open-ended
expansion (189 vs 0), Turing-complete port (15 vs 0 macros), cross-substrate
transfer (+2.00, p=0.0008). Reported nulls: no absolute lift over untrained
baseline; meta-RL grid flat; growth linear not accelerating.
