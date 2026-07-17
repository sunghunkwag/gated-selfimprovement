# Methodology

## Counterfactual gating
A mechanism (a macro, an operator, a criterion update) is admitted only if an
otherwise-identical search **without** it fails the same task at equal budget and
identical PRNG streams. The control arm is not a different run — it is the same run
minus one channel.

## Held-out evaluation
Source/target pool splits; the improver trains on the source half and is scored on
the target half. Eval tasks, budgets, and random-stream tags are identical across
all conditions and paired by seed.

## Certificates and determinism
- Novelty = exact set-membership of a behaviour signature against the enumerated
  base catalog (no heuristics).
- Ledgers are hash-chained (tamper-evident).
- All randomness flows through a seeded XorShift64*; re-running any unit reproduces
  it bit-for-bit; long runs are checkpointed and resumable.

## Honesty discipline
Predictions are written before runs. Negative results, noise floors, and the exact
boundary of each claim are reported alongside the positives.
