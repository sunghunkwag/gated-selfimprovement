# KAGGLE FULL-BUDGET RSI BATTERY -- consolidated report

wall time: 0.7 h; phases: {"A_seeds": 60, "B_seeds": 40, "C": {"adaptive": [[1, 19], [2, 21], [3, 22], [4, 23], [5, 23], [6, 23], [7, 23], [8, 23]], "frozen": [[1, 19], [2, 19], [3, 19], [4, 19], [5, 19], [6, 19], [7, 19], [8, 19]]}, "D": [{"seed": 1, "ledger": "runs_open/open_546486c354_s1.jsonl", "c1_lines": 1}, {"seed": 2, "ledger": "runs_open/open_546486c354_s2.jsonl", "c1_lines": 1}]}

## XV2 (upgraded recursive chain), Kaggle seeds 141-200
  R5PLUS - ROUND1_5X     mean +1.467 (n=60)  perm-p=0.00005
  R5PLUS - ROUND5        mean +1.667 (n=60)  perm-p=0.00005
  R5PLUS - COLD          mean -0.367 (n=60)  perm-p=0.14034
  R5PLUS - R5PLUS_NG     mean -0.150 (n=60)  perm-p=0.49458
  ROUND5 - COLD          mean -2.033 (n=60)  perm-p=0.00005
  GATED5 - ROUND5        mean +0.483 (n=60)  perm-p=0.09805

## META-RL FULL grid, seeds 1-40
  HYBRID - COLD          mean -0.0021 (n=40)  perm-p=0.82416
  LEARN - COLD           mean -0.0063 (n=40)  perm-p=0.46373
  PLAST - LEARN          mean +0.0146 (n=40)  perm-p=0.13494
  CTRL - LEARN           mean +0.0146 (n=40)  perm-p=0.22434
  HYBRID - LEARN         mean +0.0042 (n=40)  perm-p=0.66757
  COLD2 - COLD           mean -0.0083 (n=40)  perm-p=0.38183

## METAFORGE full counterfactual (per-wave solved)
  adaptive: [(1, 19), (2, 21), (3, 22), (4, 23), (5, 23), (6, 23), (7, 23), (8, 23)]
  frozen: [(1, 19), (2, 19), (3, 19), (4, 19), (5, 19), (6, 19), (7, 19), (8, 19)]

## EXPEDITION XIX: [{"seed": 1, "ledger": "runs_open/open_546486c354_s1.jsonl", "c1_lines": 1}, {"seed": 2, "ledger": "runs_open/open_546486c354_s2.jsonl", "c1_lines": 1}]
