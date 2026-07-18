# Turing-Complete Substrate (TFORGE)

Register/stack VM with real branches (JZ), data-dependent loops
(LOOP/LEN), and generic map/reduce (MAPE/FOLD). Total (step cap) and
crash-safe (4000 random programs, 0 exceptions). Hand-written running-max
yields exactly [3,3,4,4,5] — multi-step algorithms live in program space.

The proven loop (EA solver + presence prior + counterfactual macro
admission + self-curriculum) ported onto it. Metric: macros admitted,
each counterfactually gated. OPEN can admit; CLOSED cannot.

## Kaggle battery (8 seeds/arm, 7.6 h, offline pure-Python)

| Arm | macros (mean / max / total) | held-out algs solved |
|---|---|---|
| OPEN   | 1.88 / 7 / 15 | reverse, dedup |
| CLOSED | 0 / 0 / 0 (by construction) | — |

Local spot checks: OPEN seed 7 → 3 macros, CLOSED seed 7 → 0; OPEN seed 8
solved `reverse` (held-out). Honest note: CLOSED ran ~2x the wall-clock
generations (no admission machinery), so the per-generation capability
advantage is partly offset by admission cost — the same search/expressivity
balance seen in openforge. Reproduce: `python3 src/tforge.py selftest`.
