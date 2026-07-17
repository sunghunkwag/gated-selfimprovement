# Architecture

## Substrates (computational media the engines search over)
- **leapforge pipes** — straight-line compositions of 20 list→list primitives;
  a difficulty ladder of 51,856 behaviours enumerated and certified.
- **tforge VM** — a Turing-complete register/stack machine with conditional
  branches (`JZ`), data-dependent loops (`LOOP`/`LEN`), and generic map/reduce
  (`MAPE`/`FOLD`). Total (step cap) and crash-safe.
- **stack-VM RSI system** (inside `omniforge.py`) — a typed bytecode VM with
  sealed tasks, a meta-gated searcher, and a real-file `repo_repair` layer that
  patches actual Python modules and grades by executing them against hidden tests.

## omniforge.py — the unified model
Six originally-separate files merged into one runnable module by scope-aware AST
renaming: a single shared substrate (deduplicated), four search engines
(1D prior → 2D manifold → 3D gated manifold → evolvable-operator IR), a meta-RL
controller, the repaired RSI upgrade, and the separate stack-VM system. Verified
equivalent to the originals (11/11 integration tests).

## The improvement loop (shared across engines)
propose → evaluate → **counterfactual gate** → admit/reject → persist → iterate,
with a self-minted curriculum that moves with the solver and a presence-prior that
is trust-region updated with an entropy floor.
