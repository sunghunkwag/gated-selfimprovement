# TFORGE -- Kaggle report (Turing-complete RSI)

```
{
 "wall_h": 7.6,
 "OPEN": {
  "n_seeds": 8,
  "macros_mean": 1.88,
  "macros_max": 7,
  "macros_total": 15,
  "archive_mean": 175.4,
  "eval_solved_mean": 0.88,
  "eval_union": [
   "dedup",
   "reverse"
  ],
  "gens_mean": 1686
 },
 "CLOSED": {
  "n_seeds": 7,
  "macros_mean": 0.0,
  "macros_max": 0,
  "macros_total": 0,
  "archive_mean": 207.1,
  "eval_solved_mean": 0.57,
  "eval_union": [
   "dedup",
   "reverse",
   "runmax"
  ],
  "gens_mean": 3434
 }
}
```

## Certified compounding (macros admitted; each counterfactually gated)
  OPEN   mean 1.88  max 7  total 15  (across 8 seeds)
  CLOSED mean 0.00  max 0  total 0  (admission disabled -> 0 by construction)

## Held-out algorithms solved (reverse/runmax/dedup/sort)
  OPEN   union ['dedup', 'reverse']  (mean 0.88/4)
  CLOSED union ['dedup', 'reverse', 'runmax']  (mean 0.57/4)
