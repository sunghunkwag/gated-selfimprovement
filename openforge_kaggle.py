#!/usr/bin/env python3
"""
OPENFORGE LONG-TRAJECTORY RUN -- Kaggle kernel (LLM-free, offline)
==================================================================
The engine is pure Python stdlib: no LLM, no network, no GPU. This
kernel simply gives the open-ended loop a long horizon (~8 h CPU) to
answer one measurable question: WHERE IS THE NEXT WALL, and what is its
diagnosis code?

Local 100-generation result (for reference): OPEN grew vocabulary 1->12
ops, accumulated 48 certified beyond-base behaviours, still climbing at
cutoff; an admission plateau at vocab 8 SELF-HEALED when the moving
curriculum caught up. CLOSED (admission disabled): novel = 0 forever.

Phases (wall-guarded):
  P1  OPEN  seed 1: run until ~55%% of the wall budget (thousands of
      generations), checkpointing every generation.
  P2  CLOSED seed 1: same generation horizon as P1 reached, capped at
      ~15%% of wall (it is much cheaper per generation).
  P3  OPEN  seed 2: remaining time (replication arm).

Outputs: openforge trajectories in kaggle_of_log.jsonl (one line per
generation), state snapshots, and OPENFORGE_KAGGLE_REPORT.md.
"""
import json
import os
import shutil
import subprocess
import sys
import time

T0 = time.time()
WALL_H = float(os.environ.get("WALL_LIMIT_H", "7.8"))


def hleft():
    return WALL_H - (time.time() - T0) / 3600.0


def say(msg):
    print("[%7.1f min] %s" % ((time.time() - T0) / 60.0, msg))
    sys.stdout.flush()


# --- workspace --------------------------------------------------------------
src_dir = None
for root in ("/kaggle/input", "./input", "."):
    for dirpath, _d, files in os.walk(root):
        if "omniforge.py" in files and "openforge.py" in files:
            src_dir = dirpath
            break
    if src_dir:
        break
assert src_dir, "dataset with omniforge.py + openforge.py not found"
WORK = "/kaggle/working" if os.path.isdir("/kaggle/working") \
    else os.path.abspath("./work")
os.makedirs(WORK, exist_ok=True)
for fn in ("omniforge.py", "openforge.py", "base_sigs.json"):
    shutil.copy(os.path.join(src_dir, fn), os.path.join(WORK, fn))
for sub in ("runs", "runs_shared", "runs_open"):
    os.makedirs(os.path.join(WORK, sub), exist_ok=True)
    shutil.copy(os.path.join(src_dir, "ladder_cache.json"),
                os.path.join(WORK, sub, "ladder_cache.json"))
os.chdir(WORK)
say("workspace ready (source %s); engine is offline pure-Python" % src_dir)


def run_slice(arm, seed, gens, budget_s):
    """One openforge slice as a subprocess (fresh T0 per slice; state
    persists in openforge_state_*.json exactly like the local runs)."""
    r = subprocess.run(
        [sys.executable, "openforge.py", "run", arm, str(seed),
         str(gens), str(budget_s)],
        capture_output=True, text=True, cwd=WORK, timeout=budget_s + 120)
    line = (r.stdout.strip().splitlines() or ["{}"])[-1]
    try:
        return json.loads(line)
    except ValueError:
        say("slice parse error; stderr tail: %s" % r.stderr[-300:])
        return {}


def drive(arm, seed, gens_target, hours_budget, tag):
    say("%s: driving %s seed %d toward %d generations (%.1f h budget)"
        % (tag, arm, seed, gens_target, hours_budget))
    t_start = time.time()
    last = {}
    while (time.time() - t_start) / 3600.0 < hours_budget \
            and hleft() > 0.3:
        slice_s = max(30, min(
            600.0,
            (hours_budget - (time.time() - t_start) / 3600.0) * 3600 - 10,
            hleft() * 3600 - 120))
        last = run_slice(arm, seed, gens_target, slice_s)
        say("  %s s%d gen %s vocab %s solved %s novel %s diag %s"
            % (arm, seed, last.get("gen"), last.get("vocab"),
               last.get("solved_total"), last.get("novel_behaviours"),
               ",".join(last.get("diagnosis", []))))
        if last.get("gen", 0) >= gens_target:
            break
        d = set(last.get("diagnosis", []))
        if d and "WALL_CLOCK" not in d and "STILL_IMPROVING" not in d:
            # a real (non-clock) stop condition fired twice in a row?
            confirm = run_slice(arm, seed, gens_target, 120)
            d2 = set(confirm.get("diagnosis", []))
            if confirm.get("gen") == last.get("gen") and \
                    d2 and "WALL_CLOCK" not in d2:
                say("  %s s%d TERMINAL at gen %s: %s"
                    % (arm, seed, confirm.get("gen"), sorted(d2)))
                return confirm
            last = confirm
    return last


results = {}
GENS_TARGET = 100000                     # effectively "until the wall"
results["OPEN_1"] = drive("OPEN", 1, GENS_TARGET, WALL_H * 0.55, "P1")
open1_gens = results["OPEN_1"].get("gen", 0)
results["CLOSED_1"] = drive("CLOSED", 1, open1_gens or 1000,
                            WALL_H * 0.15, "P2")
results["OPEN_2"] = drive("OPEN", 2, GENS_TARGET,
                          max(0.2, hleft() - 0.3), "P3")

# ---------------------------------------------------------------------------
say("writing report")
lines = ["# OPENFORGE LONG RUN -- Kaggle report", ""]
lines.append("wall: %.2f h of %.1f h budget" % ((time.time() - T0) / 3600.0,
                                                WALL_H))
for k, v in results.items():
    lines.append("## %s" % k)
    lines.append("```")
    lines.append(json.dumps(v, indent=1, sort_keys=True))
    lines.append("```")
# trajectory tables from the per-generation log
try:
    recs = [json.loads(l) for l in open("experiments_log.jsonl")
            if '"exp": "openforge"' in l]
    arms = {}
    for r in recs:
        arms.setdefault((r["arm"], r["seed"]), []).append(r)
    for (arm, seed), rows in sorted(arms.items()):
        rows.sort(key=lambda r: r["gen"])
        gmax = rows[-1]["gen"]
        marks = sorted({1, 10, 50, 100, 250, 500, 1000, 2000, 4000,
                        8000, gmax} & set(range(1, gmax + 1)))
        lines.append("### %s seed %d trajectory" % (arm, seed))
        for g in marks:
            r = max((x for x in rows if x["gen"] <= g),
                    key=lambda x: x["gen"])
            lines.append("  gen %6d: vocab %3d solved %5d novel %5d"
                         % (g, r["vocab"], r["solved_total"],
                            r["novel_behaviours"]))
except Exception as e:
    lines.append("(trajectory table error: %s)" % e)
report = "\n".join(lines)
print("\n" + "=" * 74 + "\n" + report + "\n" + "=" * 74)
with open("OPENFORGE_KAGGLE_REPORT.md", "w") as f:
    f.write(report + "\n")
# keep per-gen log under the kernel's output
if os.path.exists("experiments_log.jsonl"):
    shutil.copy("experiments_log.jsonl", "kaggle_of_log.jsonl")
say("DONE")
