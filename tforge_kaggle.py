#!/usr/bin/env python3
"""
TFORGE ON KAGGLE -- self-improvement on a Turing-complete substrate
===================================================================
Offline pure-Python (no LLM, no net, no GPU). Runs the ported
improvement loop -- EA solver + presence prior + COUNTERFACTUAL macro
admission + self-curriculum -- on a register/stack VM with real
conditional branches (JZ) and data-dependent loops (LOOP/MAPE/FOLD), so
the question "does the self-improvement show up on genuine multi-step
algorithms" is answered at scale.

Headline (counterfactually certified, discriminating by construction):
  MACROS ADMITTED. Every admitted macro passed a counterfactual gate --
  it flipped a frontier task from unsolvable to solvable at EQUAL budget
  and identical PRNG streams. OPEN can admit; CLOSED cannot (channel
  cut). So OPEN's macro count is certified compounding; CLOSED's is 0.
Secondary probe:
  EVAL-SOLVED -- held-out human-named algorithms (reverse, runmax,
  dedup, sort) the grown vocabulary can solve within a fixed budget.

Design: seeds 1..N per arm, each driven for many generations under a
wall budget; per-generation records streamed to tforge_kaggle_log.jsonl;
consolidated report at the end.
"""
import json
import os
import shutil
import subprocess
import sys
import time

T0 = time.time()
WALL_H = float(os.environ.get("WALL_LIMIT_H", "7.8"))
SEEDS = list(range(1, 9))          # 8 seeds per arm
GENS = 100000                      # effectively "until the wall / stall"


def hleft():
    return WALL_H - (time.time() - T0) / 3600.0


def say(m):
    print("[%7.1f min] %s" % ((time.time() - T0) / 60.0, m))
    sys.stdout.flush()


src_dir = None
for root in ("/kaggle/input", "./input", "."):
    for dp, _d, files in os.walk(root):
        if "tforge.py" in files:
            src_dir = dp
            break
    if src_dir:
        break
assert src_dir, "tforge.py not found in dataset"
WORK = "/kaggle/working" if os.path.isdir("/kaggle/working") \
    else os.path.abspath("./work")
os.makedirs(WORK, exist_ok=True)
shutil.copy(os.path.join(src_dir, "tforge.py"),
            os.path.join(WORK, "tforge.py"))
os.chdir(WORK)
say("workspace ready (%s); offline pure-Python Turing-complete substrate"
    % src_dir)

# selftest gate: refuse to run experiments on a broken VM
r = subprocess.run([sys.executable, "tforge.py", "selftest"],
                   capture_output=True, text=True, cwd=WORK, timeout=120)
assert "OK -- VM" in r.stdout, "VM selftest failed:\n" + r.stdout[-800:]
say("VM selftest passed (branches, data-dep loops, halting, crash-safe)")

LOG = os.path.join(WORK, "tforge_log.jsonl")


def drive(arm, seed, hours_budget):
    t_start = time.time()
    last = {}
    while (time.time() - t_start) / 3600.0 < hours_budget and hleft() > 0.2:
        slice_s = max(20, min(300.0, hleft() * 3600 - 60))
        r = subprocess.run(
            [sys.executable, "tforge.py", "run", arm, str(seed),
             str(GENS), str(slice_s)],
            capture_output=True, text=True, cwd=WORK, timeout=slice_s + 120)
        line = (r.stdout.strip().splitlines() or ["{}"])[-1]
        try:
            last = json.loads(line)
        except ValueError:
            say("  parse err s%d: %s" % (seed, r.stderr[-200:]))
            break
        if last.get("gen", 0) >= GENS:
            break
        d = set(last.get("diagnosis", []))
        if d and "WALL_CLOCK" not in d and "STILL_IMPROVING" not in d:
            break                          # real (non-clock) stall
    return last


# time split: OPEN gets 55%, CLOSED 45% (CLOSED is a touch cheaper/gen)
per_seed_open = (WALL_H * 0.55) / len(SEEDS)
per_seed_closed = (WALL_H * 0.42) / len(SEEDS)
results = {"OPEN": {}, "CLOSED": {}}
for seed in SEEDS:
    if hleft() < 0.3:
        break
    results["OPEN"][seed] = drive("OPEN", seed, per_seed_open)
    r = results["OPEN"][seed]
    say("OPEN s%d: gen %s macros %s archive %s eval %s %s"
        % (seed, r.get("gen"), r.get("macros"), r.get("archive"),
           r.get("eval_solved"), r.get("diagnosis")))
for seed in SEEDS:
    if hleft() < 0.2:
        break
    results["CLOSED"][seed] = drive("CLOSED", seed, per_seed_closed)
    r = results["CLOSED"][seed]
    say("CLOSED s%d: gen %s macros %s archive %s eval %s %s"
        % (seed, r.get("gen"), r.get("macros"), r.get("archive"),
           r.get("eval_solved"), r.get("diagnosis")))

# ---------------------------------------------------------------------------
say("building report")


def agg(arm):
    rs = [v for v in results[arm].values() if v]
    if not rs:
        return {}
    macros = [r.get("macros", 0) for r in rs]
    arch = [r.get("archive", 0) for r in rs]
    nev = [r.get("n_eval_solved", 0) for r in rs]
    evset = set()
    for r in rs:
        evset |= set(r.get("eval_solved", []))
    return {"n_seeds": len(rs),
            "macros_mean": round(sum(macros) / len(macros), 2),
            "macros_max": max(macros), "macros_total": sum(macros),
            "archive_mean": round(sum(arch) / len(arch), 1),
            "eval_solved_mean": round(sum(nev) / len(nev), 2),
            "eval_union": sorted(evset),
            "gens_mean": round(sum(r.get("gen", 0) for r in rs) / len(rs))}


rep = {"wall_h": round((time.time() - T0) / 3600.0, 2),
       "OPEN": agg("OPEN"), "CLOSED": agg("CLOSED")}
lines = ["# TFORGE -- Kaggle report (Turing-complete RSI)", ""]
lines.append("```")
lines.append(json.dumps(rep, indent=1))
lines.append("```")
o, c = rep["OPEN"], rep["CLOSED"]
if o and c:
    lines.append("")
    lines.append("## Certified compounding (macros admitted; each "
                 "counterfactually gated)")
    lines.append("  OPEN   mean %.2f  max %d  total %d  (across %d seeds)"
                 % (o["macros_mean"], o["macros_max"], o["macros_total"],
                    o["n_seeds"]))
    lines.append("  CLOSED mean %.2f  max %d  total %d  (admission "
                 "disabled -> 0 by construction)"
                 % (c["macros_mean"], c["macros_max"], c["macros_total"]))
    lines.append("")
    lines.append("## Held-out algorithms solved (reverse/runmax/dedup/sort)")
    lines.append("  OPEN   union %s  (mean %.2f/4)"
                 % (o["eval_union"], o["eval_solved_mean"]))
    lines.append("  CLOSED union %s  (mean %.2f/4)"
                 % (c["eval_union"], c["eval_solved_mean"]))
report = "\n".join(lines)
print("\n" + "=" * 74 + "\n" + report + "\n" + "=" * 74)
open(os.path.join(WORK, "TFORGE_KAGGLE_REPORT.md"), "w").write(report + "\n")
if os.path.exists(LOG):
    shutil.copy(LOG, os.path.join(WORK, "tforge_kaggle_log.jsonl"))
say("DONE")
