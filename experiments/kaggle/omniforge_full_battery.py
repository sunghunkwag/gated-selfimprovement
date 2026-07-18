#!/usr/bin/env python3
"""
OMNIFORGE FULL-BUDGET RSI BATTERY -- Kaggle kernel
==================================================
Runs, at FULL budgets, everything the local sandbox's 45-second process
cap made impossible. Pure stdlib; no internet needed; deterministic under
fixed seeds. All raw records stream to /kaggle/working/kaggle_log.jsonl
and a consolidated report prints at the end and is saved to
/kaggle/working/KAGGLE_REPORT.md.

Phases (wall-clock-guarded; each phase skipped cleanly if time runs out):
  A  XV2 holdout EXTENSION: seeds 141-200 (n=60 fresh; combined with the
     local 101-140 gives n=100 total) -- upgraded recursive chain R5PLUS
     vs COLD / ROUND5 / ROUND1_5X / GATED5 / R5PLUS_NG. Frozen params.
  B  META-RL FULL grid (not the fast() shrink): CFG defaults
     (96 episodes, 300 search budget, 6 eval tasks/level, 3000 eval
     budget), 6 conditions x seeds 1-40.
  C  METAFORGE COUNTERFACTUAL at FULL knobs: RESTARTS_PER_TASK=6,
     GATE_TRIALS=8, CF_TRIALS=6, ALL 33 sealed tasks, 8 waves,
     adaptive vs frozen arm, per-wave trajectory logged.
  D  EXPEDITION XIX (open-ended structural self-modification with
     machine-checked C1 inexpressibility certificates), seeds 1-2.

Fairness guarantees are inherited from the embedded mechanisms (equal
compute asserted at runtime, disjoint source/target pools, identical
eval streams). Nothing here is tuned on results: parameters were frozen
before this kernel was written.
"""
import json
import os
import shutil
import sys
import time

T0 = time.time()
WALL_LIMIT_H = float(os.environ.get("WALL_LIMIT_H", "8.0"))


def hours_left():
    return WALL_LIMIT_H - (time.time() - T0) / 3600.0


def say(msg):
    print("[%6.1f min] %s" % ((time.time() - T0) / 60.0, msg))
    sys.stdout.flush()


# --- locate dataset & set up working dir -----------------------------------
CAND = ["/kaggle/input", "./input", "."]
src_dir = None
for root in CAND:
    for dirpath, _dirs, files in os.walk(root):
        if "omniforge.py" in files:
            src_dir = dirpath
            break
    if src_dir:
        break
assert src_dir, "omniforge.py not found under /kaggle/input"
WORK = "/kaggle/working" if os.path.isdir("/kaggle/working") else \
    os.path.abspath("./work")
os.makedirs(WORK, exist_ok=True)
for fn in ("omniforge.py", "rsi_upgrade.py"):
    shutil.copy(os.path.join(src_dir, fn), os.path.join(WORK, fn))
for sub in ("runs", "runs_shared", "runs_open"):
    os.makedirs(os.path.join(WORK, sub), exist_ok=True)
    shutil.copy(os.path.join(src_dir, "ladder_cache.json"),
                os.path.join(WORK, sub, "ladder_cache.json"))
os.chdir(WORK)
sys.path.insert(0, WORK)
say("workspace ready at %s (source: %s)" % (WORK, src_dir))

import omniforge as OM  # noqa: E402

LOG = os.path.join(WORK, "kaggle_log.jsonl")


def log(rec):
    with open(LOG, "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")


say("omniforge imported; substrate fingerprint %s"
    % OM.NS_UNIFIED.substrate_fingerprint())
assert OM.NS_UNIFIED.substrate_fingerprint() == "ccab00a723701e34"
_seen, lv = OM.NS_UNIFIED.get_ladder()
assert {d: len(v) for d, v in lv.items()} == \
    {1: 20, 2: 294, 3: 3858, 4: 47684}
say("certified ladder loaded from cache")

RESULTS = {}

# ===========================================================================
# PHASE A -- XV2 holdout extension, seeds 141-200 (frozen v1 mechanism)
# ===========================================================================
say("PHASE A: XV2 extension seeds 141-200")
import rsi_upgrade as UP  # noqa: E402  (frozen params inside)

XV2_CONDS = ["COLD", "ROUND5", "ROUND1_5X", "GATED5"]
a_done = 0
for seed in range(141, 201):
    if hours_left() < 6.0:      # keep room for B+C+D
        say("PHASE A stopped early at seed %d (time guard)" % seed)
        break
    ch = OM.xv_build_chains(seed)
    tasks = OM.xv_eval_tasks(seed)
    for cond in XV2_CONDS:
        r = OM.xv_run_unit(cond, seed, ch, tasks)
        log({"exp": "xv2", "battery": "kaggle", "seed": seed, "cond": cond,
             "solved": r["solved"], "by_level": r["by_level"],
             "cost": r["cost"]})
    for cond, gated in (("R5PLUS", True), ("R5PLUS_NG", False)):
        w, used, glog = UP.build_chain_plus(seed, gated=gated)
        r = UP.eval_unit(cond, w, seed, tasks)
        log({"exp": "xv2", "battery": "kaggle", "seed": seed, "cond": cond,
             "solved": r["solved"], "by_level": r["by_level"],
             "cost": r["cost"], "chain_evals": used})
    a_done += 1
say("PHASE A done: %d seeds" % a_done)
RESULTS["A_seeds"] = a_done

# ===========================================================================
# PHASE B -- META-RL FULL grid (CFG defaults), 6 conditions x seeds 1-40
# ===========================================================================
say("PHASE B: meta-RL FULL grid")
cfg_full = OM.mrl_CFG()
b_done = 0
for seed in range(1, 41):
    if hours_left() < 4.5:
        say("PHASE B stopped early at seed %d (time guard)" % seed)
        break
    for cond in ("COLD", "COLD2", "LEARN", "PLAST", "CTRL", "HYBRID"):
        r = OM.mrl_run_unit(cond, seed, cfg_full, write=False)
        log({"exp": "mrlfull", "battery": "kaggle", "seed": seed,
             "cond": cond, "ladder_score": r["ladder_score"],
             "frontier": r["frontier"],
             "train_solved": r["train_solved"],
             "eta_spread": r["eta_spread"], "tau": r["tau"]})
    b_done += 1
    if seed % 5 == 0:
        say("  B: seed %d/40 done" % seed)
say("PHASE B done: %d seeds" % b_done)
RESULTS["B_seeds"] = b_done

# ===========================================================================
# PHASE C -- METAFORGE counterfactual, FULL knobs, per-wave trajectory
# ===========================================================================
say("PHASE C: MetaForge adaptive-vs-frozen, FULL budgets, 33 tasks, 8 waves")
traj = {"adaptive": [], "frozen": []}
for arm in ("adaptive", "frozen"):
    if hours_left() < 1.5:
        say("PHASE C %s skipped (time guard)" % arm)
        continue
    rs = OM.RunState(adaptive=(arm == "adaptive"))
    rs.tasks = OM.build_sealed_tasks()          # ALL 33, full gates
    for w in range(8):
        if hours_left() < 0.8:
            say("  C %s stopped after wave %d (time guard)" % (arm, w))
            break
        t0 = time.time()
        rs = OM.run_system(adaptive=(arm == "adaptive"), waves=w + 1,
                           rs=rs, wave_start=w)
        solved, solved_gen = OM._solved_split(rs)
        rec = {"exp": "metaforge", "battery": "kaggle", "arm": arm,
               "wave": w + 1, "solved": solved,
               "solved_generated": solved_gen,
               "searcher_version": rs.searcher.version,
               "wave_seconds": round(time.time() - t0, 1)}
        traj[arm].append(rec)
        log(rec)
        say("  C %s wave %d: solved=%d gen=%d searcher_v%d (%.0fs)"
            % (arm, w + 1, solved, solved_gen, rs.searcher.version,
               time.time() - t0))
    try:
        log({"exp": "metaforge", "battery": "kaggle", "arm": arm,
             "final": True,
             "adoptions": OM.adoption_log_digest(rs),
             "events_tail": [str(e) for e in rs.events[-20:]]})
    except Exception as e:
        say("  C %s digest error: %s" % (arm, e))
RESULTS["C"] = {a: [(r["wave"], r["solved"]) for r in v]
                for a, v in traj.items()}

# ===========================================================================
# PHASE D -- Expedition XIX (C1 certificates), seeds 1-2
# ===========================================================================
say("PHASE D: Expedition XIX (open-ended, C1 certificates)")
d_out = []
for seed in (1, 2):
    if hours_left() < 0.5:
        say("PHASE D seed %d skipped (time guard)" % seed)
        break
    try:
        path = OM.xix_ledger_path(seed)
        if os.path.exists(path):
            os.remove(path)
        led = OM.lf_Ledger(path)
        t0 = time.time()
        OM.xix_expedition_core(seed, led)
        say("  D seed %d finished in %.0f min" % (seed,
                                                  (time.time() - t0) / 60))
        c1 = 0
        with open(path) as f:
            for line in f:
                rec = json.loads(line)
                body = json.dumps(rec)
                if "C1" in body:
                    c1 += 1
        d_out.append({"seed": seed, "ledger": path, "c1_lines": c1})
        log({"exp": "xix", "battery": "kaggle", "seed": seed,
             "c1_lines": c1})
    except BaseException as e:
        say("  D seed %d error: %s: %s" % (seed, type(e).__name__,
                                           str(e)[:200]))
        d_out.append({"seed": seed, "error": str(e)[:200]})
RESULTS["D"] = d_out

# ===========================================================================
# REPORT
# ===========================================================================
say("building consolidated report")


def paired(exp, a, b, field):
    A, B = {}, {}
    if not os.path.exists(LOG):
        return []
    for line in open(LOG):
        r = json.loads(line)
        if r.get("exp") == exp:
            if r.get("cond") == a:
                A[r["seed"]] = r[field]
            if r.get("cond") == b:
                B[r["seed"]] = r[field]
    seeds = sorted(set(A) & set(B))
    return [A[s] - B[s] for s in seeds]


lines = ["# KAGGLE FULL-BUDGET RSI BATTERY -- consolidated report", ""]
lines.append("wall time: %.1f h; phases: %s" % ((time.time() - T0) / 3600.0,
                                                json.dumps(RESULTS)[:400]))
lines.append("")
lines.append("## XV2 (upgraded recursive chain), Kaggle seeds 141-%d"
             % (140 + RESULTS.get("A_seeds", 0)))
for a, b in (("R5PLUS", "ROUND1_5X"), ("R5PLUS", "ROUND5"),
             ("R5PLUS", "COLD"), ("R5PLUS", "R5PLUS_NG"),
             ("ROUND5", "COLD"), ("GATED5", "ROUND5")):
    d = paired("xv2", a, b, "solved")
    if not d:
        continue
    mean = sum(d) / len(d)
    p = OM.lf_perm_p(d, "kx|%s-%s" % (a, b), n_perm=20000)[0]
    lines.append("  %-22s mean %+0.3f (n=%d)  perm-p=%.5f"
                 % ("%s - %s" % (a, b), mean, len(d), p))
lines.append("")
lines.append("## META-RL FULL grid, seeds 1-%d" % RESULTS.get("B_seeds", 0))
for a, b in (("HYBRID", "COLD"), ("LEARN", "COLD"), ("PLAST", "LEARN"),
             ("CTRL", "LEARN"), ("HYBRID", "LEARN"), ("COLD2", "COLD")):
    d = paired("mrlfull", a, b, "ladder_score")
    if not d:
        continue
    mean = sum(d) / len(d)
    p = OM.lf_perm_p(d, "km|%s-%s" % (a, b), n_perm=20000)[0]
    lines.append("  %-22s mean %+0.4f (n=%d)  perm-p=%.5f"
                 % ("%s - %s" % (a, b), mean, len(d), p))
lines.append("")
lines.append("## METAFORGE full counterfactual (per-wave solved)")
for arm, tr in RESULTS.get("C", {}).items():
    lines.append("  %s: %s" % (arm, tr))
lines.append("")
lines.append("## EXPEDITION XIX: %s" % json.dumps(RESULTS.get("D", [])))
report = "\n".join(lines)
print("\n" + "=" * 74 + "\n" + report + "\n" + "=" * 74)
with open(os.path.join(WORK, "KAGGLE_REPORT.md"), "w") as f:
    f.write(report + "\n")
say("DONE")
