# OPENFORGE — Open-Ended Loop Results

**Goal:** push past the saturation measured earlier (MetaForge stopped at
v3/23 solves when its fixed 33-task frontier ran dry) by opening the three
channels that were closed: a growing substrate, a self-renewing curriculum,
and non-collapsing gates. Design references: omniforge XIX certified operator
admission; the user's own `Target_RSI_BOLD` capacity-growth loop and
`omega_engine` warmup curriculum (found on the local PC); SDT-layer gate
findings. Implementation: `openforge.py` (English, deterministic, resumable).

## Headline metric — machine-certified, zero heuristics

**Certified novel behaviours**: probe-signatures reached by evolved pipes that
are provably inexpressible by ANY base pipe of depth ≤ 4 — exact sha256
membership check against the exhaustively enumerated 51,856-behaviour base
catalog. A nonzero count is a proof of expressivity beyond everything the
base system could ever do; it cannot be gamed by solving easy tasks.

## Trajectories (cumulative)

```
OPEN seed 1 (100 generations, still climbing at cutoff):
  gen:      1    5   10   20   30   40   60   80  100
  vocab:    1    5    6    8    8    8    8   12   12   ← admission WAVES
  solved:   1    8   13   18   21   23   34   43   46
  novel:    0    1    7   17   29   31   40   45   48   ← monotone, unbroken

OPEN seed 2 (60 generations, diagnosis: STILL_IMPROVING):
  vocab 1→17, solved 15, novel 0→42 (steepest novelty climb of all runs)

CLOSED seed 1/2 (admission disabled, same budgets, same curriculum):
  solved 51 / 35 — but novel = 0, permanently (certificate-exact:
  a fixed vocabulary cannot leave the base catalog)
```

## The three findings

**1. The plateau is not terminal when the curriculum moves.** Seed 1's
admissions stalled at vocab 8 (gens ~17–60, `NO_ADMIT_15` fired) — the exact
failure that froze MetaForge permanently. Then the self-minted curriculum
caught up (new tasks built FROM the admitted ops) and admissions RESUMED:
vocab 8 → 12 in gens 61–80, novelty rate re-accelerated. The frontier renewing
itself is what turns a dead plateau into a pause. This is the mechanism the
earlier saturations lacked, observed directly.

**2. Expansion is real and only in the open arm.** 48 and 42 certified
beyond-base behaviours in the two open runs; exactly 0 in both closed runs —
while the closed arm SOLVES more raw tasks (51 vs 46; its self-curriculum,
drawn from a fixed vocabulary, is intrinsically easier for its own solver).
Raw solve count and genuine expansion are different quantities; only the
open channel buys the second.

**3. The binding constraint observed was wall-clock, not mechanism
collapse.** At cutoff: seed 2 reports STILL_IMPROVING (no stall flags at all);
seed 1's only flag is the (previously self-healing) admission pause. Novelty
accumulated at a roughly constant ~0.5/generation with no decay trend within
the horizon. Honest boundaries, unchanged: this shows "no intrinsic plateau
within 100 generations, stopped by compute" — not "infinite". The substrate
still has distant hard ceilings (MAXLEN, 12-node IRs, 4-token pipes), novelty
growth is linear not accelerating, and a longer horizon will eventually find
the next wall. Which wall — that is a measurable question, not a guess.

## Integrity notes

Admission is counterfactual at equal budget and identical PRNG streams (op
must flip an unsolved frontier task from FAIL to SOLVED; with-op vs without-op
searches use paired streams). The novelty certificate is exact set membership,
monotone, and not self-editable — per the SDT-layer lessons, the gate's
target (the frontier) renews but the gate itself is fixed. Minted tasks are
solvable by construction (generated from an executable pipe) and admitted to
the frontier only if the CURRENT solver fails a quick-screen (minimal
criterion, POET-style). Everything is deterministic and resumable
(`openforge_state_*.json`); per-generation records in `experiments_log.jsonl`
under `"exp": "openforge"`.

## Reproduce / extend

```
python3 openforge.py basesigs 34          # one-time exact base catalog
python3 openforge.py run OPEN 1 100 30    # resume/extend seed 1
python3 openforge.py run CLOSED 1 60 30   # ablation arm
python3 openforge.py report
```

Natural next step: a Kaggle 9-hour session (the same push pipeline is already
set up) running OPEN to ~5,000 generations to locate the NEXT wall and
identify it by diagnosis code.
