# Integration Test Report — Six Uploaded Files

**Question:** Do the six files integrate into ONE complete model architecture?

**Verdict:** Five of the six (the `leapforge_*` lineage) genuinely integrate into **one** coherent model architecture, and this was proven executably: 11/11 integration tests pass. The sixth file (`rsi_levels_metaforge_unified (9).py`) is a **separate, self-contained architecture** with zero API overlap with the other five — it can run beside the leapforge model, but not inside it. So the honest answer is: **6 files → 1 unified model + 1 independent system, not 1 monolith.**

## The unified architecture (proven, not assumed)

```
┌──────────────────────────────────────────────────────────────────┐
│  META-CONTROL LAYER          leapforge_metarl.py                 │
│  metaplastic per-primitive weights + nonlinear feedback          │
│  controller (temperature + curriculum level)                     │
│  · imports the substrate as a module — dependency was MISSING,   │
│    reconstructed here as leapforge_ladder.py (shim, deliverable) │
├──────────────────────────────────────────────────────────────────┤
│  SEARCH-POLICY LAYER (4 engines, one task format, swappable)     │
│  · leapforge_unified.py    1D unigram prior            (Exp XV)  │
│  · leapforge_plasticity.py 2D transition manifold      (Exp XVI) │
│  · leapforge_gated.py      3D state-gated manifold     (Exp XVIII)│
│  · leapforge_open.py       evolvable ops + gate IR     (Exp XIX) │
│    (its gen-0 state reproduces the gated layer EXACTLY — T6)     │
├──────────────────────────────────────────────────────────────────┤
│  SUBSTRATE LAYER (verbatim-shared core in all four files)        │
│  20 list→list primitives · deterministic PRNG · exhaustively     │
│  enumerated & certified difficulty ladder {L1:20, L2:294,        │
│  L3:3858, L4:47684} · fingerprint ccab00a723701e34 — IDENTICAL   │
│  across all four modules (T2) · one cache file serves all (T3)   │
└──────────────────────────────────────────────────────────────────┘

   SEPARATE SYSTEM: rsi_levels_metaforge_unified (9).py
   Typed stack-VM bytecode substrate, sealed tasks, meta-gated
   searcher self-improvement with a frozen counterfactual arm.
   Zero leapforge API overlap, zero textual references (T10).
   Itself a bundle: embeds 5 further programs as source archives.
```

## Test results (leapforge integration suite — 11/11 PASS)

| # | Test | Result | Key evidence |
|---|------|--------|--------------|
| T1 | All six modules import | PASS | rsi (49k lines) imports in ~1.6 s in subprocess |
| T2 | Substrate identity across 4 modules | PASS | identical fingerprint `ccab00a723701e34`; `run()` agreed on 1,200 random pipe/input pairs |
| T3 | One ladder cache serves all | PASS | unified/plasticity/gated accept the same fingerprint+sha-validated cache; open's judge enumerator reproduces the identical ladder prefix |
| T4 | Cross-module task exchange | PASS | gated-drawn task solved by unified engine (293 evals) and vice versa (264 evals) |
| T5 | Same task through all 4 engines | PASS | one certified L2 task solved by all engines — evals: unified 964, plasticity 489, gated 596, open 274 |
| T6 | open's gate IR ≡ gated's hardcoded gate | PASS | equal on 3,006 fuzz + edge-case lists |
| T7 | metarl's own selftest on the shim | PASS | all 8 invariants, incl. its hardcoded ladder counts {20, 294, 3858, 47684} |
| T8 | Full stack end-to-end (HYBRID unit) | PASS | substrate + plasticity + controller: ladder_score 0.333, 20 train solves, compute ≤ cap |
| T9 | RSI CLI health + test inventory | PASS | manifest OK; 286 internal acceptance tests found |
| T10 | RSI/leapforge isolation (negative control) | PASS | zero shared API; own VM substrate (`VMCrash`, `SealedTask`) |
| T11 | Cross-engine determinism | PASS | byte-identical repeat runs for all 4 engines |

## RSI system's own 286-test acceptance suite (executed in shards)

150 verified PASS · 62 blocked on artifacts of the original repository that were not uploaded (`docs/` specs, run ledgers, battery outputs — preconditions, not code failures) · 74 unresolved because a single test exceeds the sandbox's 45-second shell cap (they launch wave-scale system runs) · **0 genuine code failures observed.** Detail: `rsi_acceptance_detail.json`.

## What was missing, and what was added

The only real integration gap in the leapforge lineage was `leapforge_ladder` — the Expedition XIV substrate module that `leapforge_metarl.py` imports, absent from the upload. Since the other four files carry a fingerprint-identical verbatim copy of that substrate, the gap was closed with a 40-line adapter, `leapforge_ladder.py` (exposes `NAMES / PRNG / run / get_ladder / tasks_at` over `leapforge_unified`). metarl then passes its own 8-invariant selftest unmodified — the strongest possible evidence that the layers belong to one architecture.

Note the files are not "six modules of one program": the four substrate-bearing files each duplicate the ~400-line substrate rather than importing it (by design — each is a self-auditing, self-contained experiment harness). A production refactor would extract the substrate into one module; behaviourally this changes nothing, as T2/T3 prove.

## Limitations

The 74 unresolved RSI tests are slow, not shown broken; running them needs an environment without the 45 s process cap. The 62 precondition-blocked tests need the original repo's `docs/` folder and battery artifacts. Engine comparisons here are smoke-scale (the files themselves insist n ≥ 40 seeds for scientific claims).

## Files in this folder

`integration_test.py` (suite) · `leapforge_ladder.py` (shim, the integration deliverable) · `ladder_builder.py` (checkpointed ladder builder) · `rsi_shard_runner.py` (sharded acceptance runner) · `integration_results.json` (machine-readable results) · `rsi_acceptance_detail.json` (per-test RSI detail) · `runs_shared/ladder_cache.json` (the shared certified ladder) · the six modules under importable names.

Reproduce with: `python3 experiments/integration_test.py` (all tests) or `python3 experiments/integration_test.py T5 T7` (subset).
