#!/usr/bin/env python3
"""
OPENFORGE -- an open-ended improvement loop on the omniforge substrate
======================================================================
Purpose: push the measured saturation points as far as the substrate
allows, and INSTRUMENT exactly where and why improvement stops. This is
explicitly NOT a claim of unbounded improvement -- no experiment can show
"infinite"; it can only show "kept improving for N generations, then
stopped because X".

The three open channels (design informed by: omniforge XIX's certified
operator admission; the user's Target_RSI_BOLD capacity-growth loop and
omega_engine's warmup curriculum found on the local PC; and the SDT-layer
findings on gate integrity):

  1. GROWING SUBSTRATE -- the vocabulary grows: synthesized operators
     (XIX IR trees, up to 12 nodes each) are admitted as new tokens.
     Pipes compose up to 4 tokens, so each admission multiplies the
     effective primitive-depth ceiling (4 base ops -> up to ~48 primitive
     applications per pipe, plus MAP/SCAN inner structure).
  2. SELF-CURRICULUM -- the system mints its own tasks from pipes over
     its CURRENT vocabulary (solvable by construction, POET-style), and
     keeps only those its current solver cannot quickly solve (minimal
     criterion). The frontier therefore moves with the solver.
  3. NON-COLLAPSING GATES -- admission is counterfactual (the op must
     enable a solve that fails without it, at equal budget and identical
     PRNG streams), and the certified-novelty metric is exact (below),
     so neither can be satisfied vacuously. (SDT lesson: closed targets
     go vacuous; self-editable gates wirehead. Here the gate's target set
     -- the frontier -- RENEWS itself, and the gate is not self-editable.)

HEADLINE METRIC (monotone, machine-certified): CERTIFIED NOVEL BEHAVIOURS
-- distinct probe-signatures reached by evolved pipes that are PROVABLY
inexpressible by ANY base pipe of depth <= 4, verified by exact membership
against the exhaustively enumerated 51,856-behaviour base catalog (the
substrate's own C1-style certificate, behaviour-level, zero heuristics).

ARMS (equal per-generation budgets, identical streams):
  OPEN    all three channels live
  CLOSED  identical loop with operator admission DISABLED (channel 1 cut;
          the fixed 20-token vocabulary bounds novel behaviours at 0 by
          definition of the certificate -- the arm measures how far the
          curriculum alone carries solves)

STOP DIAGNOSIS (reported per run): FRONTIER_EMPTY | NO_SOLVE_10 |
NO_ADMIT_15 | NOVELTY_STALL_15 | WALL_CLOCK. Deterministic, resumable
(checkpoint per generation; the 45 s shell cap slices long runs).

Usage:
  python3 openforge.py basesigs <budget_s>          # one-time catalog
  python3 openforge.py run <arm> <seed> <gens> <budget_s>
  python3 openforge.py report
"""
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)

import omniforge as OM  # noqa: E402

LOG = os.path.join(HERE, "experiments_log.jsonl")
BASE_SIGS = os.path.join(HERE, "base_sigs.json")
T0 = time.time()

# per-generation budgets (identical for both arms)
MINT_TRIES = 3
MINT_SCREEN = 300          # "too easy" screen budget (current vocab)
SOLVE_K = 4                # frontier tasks attempted per generation
SOLVE_BUDGET = 1500
MINE_CANDS = 24            # op candidates considered per generation
CF_BUDGET = 800            # counterfactual admission budget per arm
FRONTIER_CAP = 40
ARCHIVE_FIT = 24           # last-N archive solutions fed to manifold fit
MAX_ADMIT_PER_GEN = 1


def log(rec):
    with open(LOG, "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")


def sig_sha(pipe, ops):
    """Probe-signature sha of a token pipe; None if invalid anywhere."""
    out = []
    for xs in OM.lf_PROBES:
        o = OM.xix_run_tokens_open(list(pipe), ops, list(xs))
        if o is None:
            return None
        out.append(tuple(o))
    return hashlib.sha256(
        OM.lf_canon([list(t) for t in out]).encode()).hexdigest()


# ---------------------------------------------------------------------------
# one-time: exact base catalog (all behaviours expressible at depth <= 4)
# ---------------------------------------------------------------------------
def cmd_basesigs(budget):
    st = {"idx": 0, "sigs": []}
    if os.path.exists(BASE_SIGS):
        st = json.load(open(BASE_SIGS))
        if st.get("done"):
            print(json.dumps({"basesigs": "done", "n": len(st["sigs"])}))
            return
    OM.NS_UNIFIED.CONFIG["outdir"] = "runs"
    _s, levels = OM.xv_get_ladder()
    pipes = [p for d in sorted(levels) for _x, p in levels[d]]
    sigs = set(st["sigs"])
    i = st["idx"]
    while i < len(pipes) and budget - (time.time() - T0) > 3:
        s = OM.lf_sig(pipes[i])
        if s is not None:
            sigs.add(hashlib.sha256(
                OM.lf_canon([list(t) for t in s]).encode()).hexdigest())
        i += 1
    done = i >= len(pipes)
    json.dump({"idx": i, "sigs": sorted(sigs), "done": done},
              open(BASE_SIGS, "w"))
    print(json.dumps({"basesigs": ("done" if done else "progress"),
                      "idx": i, "of": len(pipes), "n_sigs": len(sigs)}))


# ---------------------------------------------------------------------------
# task minting (self-curriculum; solvable by construction)
# ---------------------------------------------------------------------------
def mint_task(arm, seed, gen, k, ops, W, gtree):
    prng = OM.lf_XorShift64Star("of-mint|%s|%d|%d|%d" % (arm, seed, gen, k))
    toks = OM.xix_token_space_open(ops)
    admitted = sorted(ops)
    length = 2 + prng.below(3)
    pipe = [prng.choice(toks) for _ in range(length)]
    if admitted and not any(t in ops for t in pipe):
        pipe[prng.below(len(pipe))] = prng.choice(admitted)

    def mk(lo, hi, n):
        out = []
        for _ in range(n):
            ln = lo + prng.below(hi - lo + 1)
            out.append([prng.below(256) for _ in range(ln)])
        return out
    tr_in, te_in = mk(3, 6, 4), mk(7, 11, 4)
    tr = [(x, OM.xix_run_tokens_open(pipe, ops, x)) for x in tr_in]
    te = [(x, OM.xix_run_tokens_open(pipe, ops, x)) for x in te_in]
    if any(y is None for _x, y in tr + te):
        return None
    if all(len(y) == 0 for _x, y in tr) or all(y == x for x, y in tr):
        return None
    task = {"train": tr, "test": te, "pipe": list(pipe),
            "level": min(4, len(pipe))}
    # minimal criterion: reject if the CURRENT solver cracks it instantly
    prog, _ev, _e = OM.xix_search_task_open(
        task, W, ops, MINT_SCREEN,
        OM.lf_XorShift64Star("of-screen|%s|%d|%d|%d" % (arm, seed, gen, k)),
        gtree)
    if prog is not None and OM.xix_solves_open(prog, ops, task):
        return None                      # too easy for the current system
    return task


# ---------------------------------------------------------------------------
# state (deterministic, resumable)
# ---------------------------------------------------------------------------
def state_path(arm, seed):
    return os.path.join(HERE, "openforge_state_%s_%d.json" % (arm, seed))


def fresh_state():
    return {"gen": 0, "ops": {}, "frontier": [], "archive": [],
            "novel": [], "metrics": [], "op_seq": 0,
            "last_admit_gen": 0, "last_solve_gen": 0,
            "last_novel_gen": 0}


def load_state(arm, seed):
    p = state_path(arm, seed)
    if os.path.exists(p):
        return json.load(open(p))
    return fresh_state()


def save_state(arm, seed, st):
    tmp = state_path(arm, seed) + ".tmp"
    json.dump(st, open(tmp, "w"))
    os.replace(tmp, state_path(arm, seed))


# ---------------------------------------------------------------------------
# the loop
# ---------------------------------------------------------------------------
def cmd_run(arm, seed, gens_target, budget):
    assert arm in ("OPEN", "CLOSED")
    assert os.path.exists(BASE_SIGS) and json.load(
        open(BASE_SIGS)).get("done"), "run `basesigs` to completion first"
    base = set(json.load(open(BASE_SIGS))["sigs"])
    OM.NS_UNIFIED.CONFIG["outdir"] = "runs"
    OM.xv_get_ladder()
    st = load_state(arm, seed)
    ops = {name: {"ir": rec["ir"]} for name, rec in st["ops"].items()}
    gtree = OM.xix_gen0_gate_tree()
    W = OM.xix_uniform_manifold_open(ops)
    scored = [(1.0, list(e["pipe"]), list(e["ref"]))
              for e in st["archive"][-ARCHIVE_FIT:]]
    if scored:
        W = OM.xix_fit_manifold_open(scored, ops, gtree)
    novel = set(st["novel"])

    while st["gen"] < gens_target and budget - (time.time() - T0) > 8:
        st["gen"] += 1
        gen = st["gen"]
        evals = 0
        # 1. mint ------------------------------------------------------
        for k in range(MINT_TRIES):
            if len(st["frontier"]) >= FRONTIER_CAP:
                break
            t = mint_task(arm, seed, gen, k, ops, W, gtree)
            evals += MINT_SCREEN
            if t is not None:
                st["frontier"].append(t)
        # 2. solve -----------------------------------------------------
        solved_now = 0
        still = []
        for j, task in enumerate(st["frontier"]):
            if j < SOLVE_K:
                prog, ev, _e = OM.xix_search_task_open(
                    task, W, ops, SOLVE_BUDGET,
                    OM.lf_XorShift64Star("of-solve|%s|%d|%d|%d"
                                         % (arm, seed, gen, j)), gtree)
                evals += ev
                if prog is not None and OM.xix_solves_open(prog, ops, task):
                    solved_now += 1
                    ref = sorted(task["train"],
                                 key=lambda e: len(e[0]))[0][0]
                    st["archive"].append({"pipe": list(prog),
                                          "ref": list(ref)})
                    st["last_solve_gen"] = gen
                    sh = sig_sha(prog, ops)
                    if sh is not None and sh not in base and sh not in novel:
                        novel.add(sh)
                        st["last_novel_gen"] = gen
                    continue
            still.append(task)
        st["frontier"] = still
        # also harvest novelty from the minted generators themselves
        for task in st["frontier"][-MINT_TRIES:]:
            sh = sig_sha(task["pipe"], ops)
            if sh is not None and sh not in base and sh not in novel:
                novel.add(sh)
                st["last_novel_gen"] = gen
        # 3. mine + counterfactual admission (OPEN only) ----------------
        admitted_now = 0
        if arm == "OPEN" and st["frontier"]:
            prng_m = OM.lf_XorShift64Star("of-mine|%s|%d|%d"
                                          % (arm, seed, gen))
            target = st["frontier"][0]      # hardest-waiting frontier task
            for c in range(MINE_CANDS):
                if admitted_now >= MAX_ADMIT_PER_GEN:
                    break
                ir = OM.xix_grow_op(prng_m, 12)
                if not OM.xix_check_op(ir):
                    continue
                name = "o%02d" % (st["op_seq"] + 1)
                trial_ops = dict(ops)
                trial_ops[name] = {"ir": ir}
                W_t = OM.xix_uniform_manifold_open(trial_ops)
                p_with, ev_w, _ = OM.xix_search_task_open(
                    target, W_t, trial_ops, CF_BUDGET,
                    OM.lf_XorShift64Star("of-cf|%s|%d|%d|%d|w"
                                         % (arm, seed, gen, c)), gtree)
                evals += ev_w
                ok_with = (p_with is not None
                           and OM.xix_solves_open(p_with, trial_ops, target))
                if not ok_with:
                    continue
                p_wo, ev_o, _ = OM.xix_search_task_open(
                    target, W, ops, CF_BUDGET,
                    OM.lf_XorShift64Star("of-cf|%s|%d|%d|%d|o"
                                         % (arm, seed, gen, c)), gtree)
                evals += ev_o
                ok_wo = (p_wo is not None
                         and OM.xix_solves_open(p_wo, ops, target))
                if ok_wo:
                    continue                 # not counterfactually needed
                # ADMIT
                st["op_seq"] += 1
                ops[name] = {"ir": ir}
                st["ops"][name] = {"ir": ir, "gen": gen,
                                   "sha": OM.xix_op_sha(ir)}
                st["last_admit_gen"] = gen
                admitted_now += 1
                W = OM.xix_uniform_manifold_open(ops)
        # 4. prior/manifold refit --------------------------------------
        scored = [(1.0, list(e["pipe"]), list(e["ref"]))
                  for e in st["archive"][-ARCHIVE_FIT:]]
        if scored:
            W = OM.xix_fit_manifold_open(scored, ops, gtree)
        # 5. metrics ----------------------------------------------------
        rec = {"exp": "openforge", "arm": arm, "seed": seed, "gen": gen,
               "vocab": len(ops), "frontier": len(st["frontier"]),
               "solved_now": solved_now, "solved_total": len(st["archive"]),
               "novel_behaviours": len(novel), "admitted_now": admitted_now,
               "gen_evals": evals}
        st["metrics"].append(rec)
        log(rec)
        st["novel"] = sorted(novel)
        save_state(arm, seed, st)

    # stop diagnosis
    gen = st["gen"]
    diag = []
    if not st["frontier"]:
        diag.append("FRONTIER_EMPTY")
    if gen - st["last_solve_gen"] >= 10:
        diag.append("NO_SOLVE_10")
    if arm == "OPEN" and gen - st["last_admit_gen"] >= 15:
        diag.append("NO_ADMIT_15")
    if gen - st["last_novel_gen"] >= 15:
        diag.append("NOVELTY_STALL_15")
    if gen < gens_target:
        diag.append("WALL_CLOCK")
    print(json.dumps({"arm": arm, "seed": seed, "gen": gen,
                      "target": gens_target, "vocab": len(ops),
                      "solved_total": len(st["archive"]),
                      "novel_behaviours": len(novel),
                      "diagnosis": diag or ["STILL_IMPROVING"],
                      "elapsed": round(time.time() - T0, 1)}))


def cmd_report():
    recs = [json.loads(l) for l in open(LOG) if '"exp": "openforge"' in l]
    arms = {}
    for r in recs:
        arms.setdefault((r["arm"], r["seed"]), []).append(r)
    print("=" * 74)
    print("OPENFORGE trajectories (cumulative; certified novel behaviours "
          "are exact)")
    print("=" * 74)
    for (arm, seed), rows in sorted(arms.items()):
        rows.sort(key=lambda r: r["gen"])
        gens = [r["gen"] for r in rows]
        marks = [g for g in (1, 5, 10, 20, 30, 40, 60, 80, 100)
                 if g <= gens[-1]]
        tr = [(g, next(r for r in rows if r["gen"] == g)) for g in marks]
        print("%s seed %d (gen %d): vocab %d, solved %d, novel %d"
              % (arm, seed, gens[-1], rows[-1]["vocab"],
               rows[-1]["solved_total"], rows[-1]["novel_behaviours"]))
        print("   gen:    " + "".join("%6d" % g for g, _ in tr))
        print("   vocab:  " + "".join("%6d" % r["vocab"] for _, r in tr))
        print("   solved: " + "".join("%6d" % r["solved_total"]
                                      for _, r in tr))
        print("   novel:  " + "".join("%6d" % r["novel_behaviours"]
                                      for _, r in tr))


if __name__ == "__main__":
    if sys.argv[1] == "basesigs":
        cmd_basesigs(float(sys.argv[2]) if len(sys.argv) > 2 else 30.0)
    elif sys.argv[1] == "run":
        cmd_run(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]),
                float(sys.argv[5]) if len(sys.argv) > 5 else 30.0)
    elif sys.argv[1] == "report":
        cmd_report()
