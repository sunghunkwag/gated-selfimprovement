#!/usr/bin/env python3
"""
INTEGRATION TEST SUITE for the six uploaded files
=================================================
Question under test: "Do the six files integrate into ONE complete
model architecture?"

Files (renamed to importable module names in this directory):
    leapforge_unified.py     Expedition XV   -- substrate + 1D unigram prior engine
    leapforge_plasticity.py  Expedition XVI  -- 2D transition manifold + plasticity
    leapforge_gated.py       Expedition XVIII-- 3D state-gated manifold + macros
    leapforge_open.py        Expedition XIX  -- open-ended operator/gate synthesis
    leapforge_metarl.py      Expedition XV-RL-- meta-RL controller (imports leapforge_ladder)
    rsi_levels_metaforge_unified.py          -- separate MetaForge/RSI system (stack VM)

Integration layers exercised:
    T1  all six modules import
    T2  substrate identity across the four substrate-bearing modules
        (fingerprint + behavioural equivalence of run())
    T3  ONE shared ladder cache serves all four modules (fingerprint-gated)
    T4  tasks drawn by one module are solved by another module's engine
    T5  the SAME task is solved by all four search engines (one task format)
    T6  open's evolved-gate IR reproduces gated's hardcoded gate exactly
    T7  leapforge_metarl runs on the shim (its own 8-invariant selftest)
    T8  full stack end-to-end: substrate + plasticity + controller (HYBRID unit)
    T9  RSI system's own acceptance suite (subprocess, its own CLI)
    T10 negative control: RSI system shares NO substrate API with leapforge
    T11 cross-engine determinism (same seeds -> identical results)

All output in English. Results appended to integration_results.json.
"""
import json
import os
import re
import subprocess
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)

LADDER_DIR = os.path.join(HERE, "runs_shared")
EXPECTED_LEVEL_COUNTS = {1: 20, 2: 294, 3: 3858, 4: 47684}  # XIV's build
RESULTS_PATH = os.path.join(HERE, "integration_results.json")

RESULTS = []


def record(name, ok, dt, detail):
    RESULTS.append({"test": name, "pass": bool(ok),
                    "seconds": round(dt, 2), "detail": detail})
    print("%s  %-38s %7.2fs  %s" % ("PASS" if ok else "FAIL", name, dt,
                                    detail if isinstance(detail, str)
                                    else json.dumps(detail)[:300]))
    sys.stdout.flush()


def run_test(name, fn):
    t0 = time.time()
    try:
        detail = fn()
        record(name, True, time.time() - t0, detail or "ok")
    except Exception as e:
        record(name, False, time.time() - t0,
               "%s: %s" % (type(e).__name__, e))
        traceback.print_exc()


# ---------------------------------------------------------------------------
# T1  imports
# ---------------------------------------------------------------------------
U = P = G = O = None


def _ensure():
    """Import the four substrate modules (idempotent); every test may
    run standalone because the shell sandbox caps each call at 45 s."""
    global U, P, G, O
    if U is not None:
        return
    import leapforge_unified as U_
    import leapforge_plasticity as P_
    import leapforge_gated as G_
    import leapforge_open as O_
    U, P, G, O = U_, P_, G_, O_
    for m in (U, P, G, O):
        m.CONFIG["outdir"] = LADDER_DIR      # ONE shared cache for all four


def t1_imports():
    _ensure()
    # rsi module: import in a subprocess (49k lines; keep main process clean)
    t0 = time.time()
    r = subprocess.run(
        [sys.executable, "-c",
         "import rsi_levels_metaforge_unified as R; "
         "import json; print(json.dumps({'n_symbols': len(dir(R))}))"],
        capture_output=True, text=True, timeout=300, cwd=HERE)
    if r.returncode != 0:
        raise RuntimeError("rsi import failed: " + r.stderr[-300:])
    info = json.loads(r.stdout.strip().splitlines()[-1])
    return ("4 leapforge modules imported in-process; rsi imported in "
            "subprocess in %.1fs (%d top-level symbols)"
            % (time.time() - t0, info["n_symbols"]))


# ---------------------------------------------------------------------------
# T2  substrate identity
# ---------------------------------------------------------------------------
def t2_substrate_identity():
    _ensure()
    fps = {m.__name__: m.substrate_fingerprint() for m in (U, P, G, O)}
    assert len(set(fps.values())) == 1, "fingerprints differ: %s" % fps
    assert U.NAMES == P.NAMES == G.NAMES == O.NAMES, "primitive sets differ"
    assert len(U.NAMES) == 20, "expected 20 primitives"
    # behavioural equivalence: 300 random pipes x 4 random inputs
    prng = U.XorShift64Star("xmod-equiv")
    checked = 0
    for _ in range(300):
        d = 1 + prng.below(4)
        pipe = [prng.choice(U.NAMES) for _ in range(d)]
        for _ in range(4):
            xs = [prng.below(256) for _ in range(prng.below(9))]
            outs = [m.run(list(pipe), list(xs)) for m in (U, P, G, O)]
            assert outs.count(outs[0]) == 4, \
                "run() disagrees on pipe=%s xs=%s -> %s" % (pipe, xs, outs)
            checked += 1
    return ("fingerprint %s identical across 4 modules; run() agreed on "
            "%d pipe/input pairs" % (list(fps.values())[0], checked))


# ---------------------------------------------------------------------------
# T3  one ladder cache serves all four modules
# ---------------------------------------------------------------------------
def t3_shared_ladder():
    _ensure()
    t0 = time.time()
    _seen, lv_u = U.get_ladder()             # builds (or loads) the cache
    build_s = time.time() - t0
    cache = os.path.join(LADDER_DIR, "ladder_cache.json")
    assert os.path.exists(cache), "shared cache file missing"
    counts = {}
    for m in (U, P, G):                      # the three cache-bearing modules
        t1 = time.time()
        _s, lv = m.get_ladder()              # P/G must ACCEPT U's cache
        counts[m.__name__] = ({d: len(v) for d, v in lv.items()},
                              round(time.time() - t1, 2))
    tables = [c for c, _t in counts.values()]
    assert all(t == tables[0] for t in tables), "level counts differ"
    assert tables[0] == EXPECTED_LEVEL_COUNTS, \
        "counts %s != XIV expectation %s" % (tables[0], EXPECTED_LEVEL_COUNTS)
    # leapforge_open has no cache: it calls build() directly as its
    # inexpressibility judge. Verify its enumerator reproduces the same
    # ladder prefix (depth <= 3 is cheap; depth 4 identity follows from
    # T2's behavioural equivalence of the shared substrate).
    _s3, lv3 = O.build(max_depth=3)
    open_counts = {d: len(v) for d, v in lv3.items()}
    assert open_counts == {d: tables[0][d] for d in (1, 2, 3)}, \
        "open's enumerator disagrees with the shared cache: %s" % open_counts
    load_times = {k: v[1] for k, v in counts.items()}
    return ("ladder %s built/loaded by unified in %.1fs; plasticity+gated "
            "accepted the SAME fingerprint-validated cache (load times %s); "
            "open's judge enumerator reproduces the identical ladder prefix "
            "%s" % (tables[0], build_s, load_times, open_counts))


# ---------------------------------------------------------------------------
# T4  cross-module task exchange
# ---------------------------------------------------------------------------
def _solve_unified(task, budget, seed):
    prng = U.XorShift64Star(seed)
    prog, evals, _ = U.search_task(task, U.uniform_prior(), budget, prng)
    return (prog is not None and U.solves(prog, task)), evals


def _solve_gated(task, budget, seed):
    prng = G.XorShift64Star(seed)
    reg = {}
    W = G.uniform_manifold(reg, G.get_state_context)
    prog, evals, _ = G.search_task_gated(task, W, reg, budget, prng,
                                         G.get_state_context)
    return (prog is not None and G.solves_tokens(prog, reg, task)), evals


def t4_task_exchange():
    _ensure()
    # task drawn by GATED's machinery, solved by UNIFIED's engine
    tg = G.draw_task(2, 7, "source", "xchg-g")
    ok_a, ev_a = _solve_unified(tg, 20000, "xchg-a")
    assert ok_a, "unified engine failed on gated-drawn task"
    # task drawn by UNIFIED's machinery, solved by GATED's engine
    tu = U.draw_task(2, 7, "source", "xchg-u")
    ok_b, ev_b = _solve_gated(tu, 20000, "xchg-b")
    assert ok_b, "gated engine failed on unified-drawn task"
    return ("gated-drawn L2 task solved by unified engine (%d evals); "
            "unified-drawn L2 task solved by gated engine (%d evals); "
            "task dict format is interchangeable" % (ev_a, ev_b))


# ---------------------------------------------------------------------------
# T5  the SAME task through all four engines
# ---------------------------------------------------------------------------
def _four_engines(task, budget):
    out = {}
    # 1. unified: 1D unigram prior
    ok, ev = _solve_unified(task, budget, "4eng-u")
    out["unified(1D prior)"] = (ok, ev)
    # 2. plasticity: 2D transition manifold + trace
    prng = P.XorShift64Star("4eng-p")
    prog, ev, _ = P.search_task_plastic(task, P.uniform_manifold(),
                                        budget, prng)
    out["plasticity(2D manifold)"] = (
        prog is not None and P.solves(prog, task), ev)
    # 3. gated: 3D state-gated manifold
    ok, ev = _solve_gated(task, budget, "4eng-g")
    out["gated(3D manifold)"] = (ok, ev)
    # 4. open: gated engine generalized to evolvable ops/gates (gen-0 state)
    prng = O.XorShift64Star("4eng-o")
    ops = {}
    W = O.uniform_manifold_open(ops)
    prog, ev, _ = O.search_task_open(task, W, ops, budget, prng,
                                     O.gen0_gate_tree())
    out["open(gen0 IR)"] = (
        prog is not None and O.solves_open(prog, ops, task), ev)
    return out


def t5_four_engines_one_task():
    _ensure()
    task = U.draw_task(2, 11, "source", "quad")
    res = _four_engines(task, 30000)
    failed = [k for k, (ok, _e) in res.items() if not ok]
    assert not failed, "engines failed on the shared task: %s" % failed
    evals = {k: e for k, (_ok, e) in res.items()}
    return ("ONE certified L2 task (pipe %s) solved by all 4 engines; "
            "evals used: %s" % (task["pipe"], evals))


# ---------------------------------------------------------------------------
# T6  open's gen-0 gate IR == gated's hardcoded gate (semantic equivalence)
# ---------------------------------------------------------------------------
def t6_gate_equivalence():
    _ensure()
    tree = O.gen0_gate_tree()
    assert O.check_gate(tree), "gen0 gate tree fails open's own validator"
    prng = U.XorShift64Star("gate-fuzz")
    cases = [[], [0], [255], [1, 2, 3], [3, 2, 1], [7] * 6]
    for _ in range(3000):
        n = prng.below(13)
        cases.append([prng.below(256) for _ in range(n)])
    for lst in cases:
        a = O.classify(tree, lst)
        b = G.get_state_context(lst)
        c = O.get_state_context(lst)
        assert a == b == c, "gate mismatch on %s: open-IR=%s gated=%s" \
            % (lst, a, b)
    return ("open's evolvable gate IR (gen 0) == gated's hardcoded gate on "
            "%d lists (incl. edge cases) -- the open layer is a strict "
            "structural generalization of the gated layer" % len(cases))


# ---------------------------------------------------------------------------
# T7  metarl on the shim: its own selftest (8 invariants)
# ---------------------------------------------------------------------------
MR = None


def t7_metarl_selftest():
    _ensure()
    global MR
    import leapforge_ladder as L               # the shim (this directory)
    assert L.substrate_fingerprint() == U.substrate_fingerprint()
    import leapforge_metarl as MR_
    MR = MR_
    MR.selftest()                              # asserts internally; 8 checks
    return ("leapforge_metarl imported via leapforge_ladder SHIM over "
            "leapforge_unified and passed its own 8-invariant selftest "
            "(ladder counts, uniform-sampling, determinism, stream "
            "divergence, gains-zero, eta contrast, pool disjointness, "
            "compute cap)")


# ---------------------------------------------------------------------------
# T8  full stack: substrate + plasticity + nonlinear controller
# ---------------------------------------------------------------------------
def t8_full_stack_hybrid():
    _ensure()
    cfg = MR.CFG().fast()
    rec = MR.run_unit("HYBRID", 2, cfg, write=False)
    caps = (cfg.EPISODES * cfg.SEARCH_BUDGET
            + cfg.K * cfg.EVAL_TASKS * cfg.EVAL_BUDGET)
    assert 0.0 <= rec["ladder_score"] <= 1.0
    assert rec["train_consumed"] + rec["eval_consumed"] <= caps
    assert set(rec["occupancy"]) == {1, 2, 3, 4}
    assert rec["frontier"] >= 1, "stack solved nothing at any level"
    return ("HYBRID unit (plasticity + metaplasticity + controller) ran on "
            "the shimmed substrate: ladder_score=%.3f frontier=L%d "
            "train_solved=%d occupancy=%s compute<=cap(%d)"
            % (rec["ladder_score"], rec["frontier"], rec["train_solved"],
               rec["occupancy"], caps))


# ---------------------------------------------------------------------------
# T9  RSI system's own acceptance suite (separate architecture, own CLI)
# ---------------------------------------------------------------------------
def t9_rsi_acceptance():
    """Light probe: manifest + acceptance-test inventory. The full
    318-test acceptance suite is executed by rsi_shard_runner.py across
    several shell calls (sandbox caps each call at 45 s) and merged into
    the results file as T9full_rsi_acceptance_suite."""
    man = subprocess.run(
        [sys.executable, "rsi_levels_metaforge_unified.py",
         "--mode", "manifest"],
        capture_output=True, text=True, timeout=40, cwd=HERE)
    assert man.returncode == 0, man.stderr[-300:]
    n_embedded = len(re.findall(r"\.py", man.stdout))
    probe = subprocess.run(
        [sys.executable, "-c",
         "import rsi_levels_metaforge_unified as R; print(len(R.TESTS))"],
        capture_output=True, text=True, timeout=40, cwd=HERE)
    n_tests = int(probe.stdout.strip().splitlines()[-1])
    assert n_tests > 200, "unexpectedly small internal test inventory"
    return ("rsi CLI healthy: manifest lists %d embedded source archive "
            "references; internal acceptance inventory = %d tests "
            "(executed separately in shards, see "
            "T9full_rsi_acceptance_suite)" % (n_embedded, n_tests))


# ---------------------------------------------------------------------------
# T10 negative control: rsi shares no substrate API with leapforge
# ---------------------------------------------------------------------------
def t10_rsi_isolation():
    probe = (
        "import rsi_levels_metaforge_unified as R, json\n"
        "api = set(dir(R))\n"
        "lf = {'NAMES','PRIMS','get_ladder','substrate_fingerprint',"
        "'XorShift64Star','draw_task','make_task','search_task'}\n"
        "print(json.dumps({'overlap': sorted(api & lf),"
        " 'has_own_vm': ('VMCrash' in api),"
        " 'has_sealed_task': ('SealedTask' in api)}))\n")
    r = subprocess.run([sys.executable, "-c", probe],
                       capture_output=True, text=True, timeout=300, cwd=HERE)
    assert r.returncode == 0, r.stderr[-300:]
    info = json.loads(r.stdout.strip().splitlines()[-1])
    assert info["overlap"] == [], \
        "unexpected shared API with leapforge: %s" % info["overlap"]
    assert info["has_own_vm"] and info["has_sealed_task"]
    src = open(os.path.join(HERE, "rsi_levels_metaforge_unified.py"),
               encoding="utf-8").read()
    assert "leapforge" not in src.lower(), "rsi references leapforge?!"
    return ("CONFIRMED SEPARATE: rsi exposes its own stack-VM substrate "
            "(VMCrash, SealedTask), has ZERO leapforge API overlap and "
            "zero textual references to leapforge -- it composes beside, "
            "not inside, the leapforge model")


# ---------------------------------------------------------------------------
# T11 determinism end-to-end
# ---------------------------------------------------------------------------
def t11_determinism():
    _ensure()
    task = U.draw_task(2, 5, "source", "det")
    a = _four_engines(task, 8000)
    b = _four_engines(task, 8000)
    assert a == b, "engines are not deterministic under fixed seeds"
    return ("all four engines byte-identical across repeated runs on the "
            "same task and seeds: %s"
            % {k: v for k, v in a.items()})


# ---------------------------------------------------------------------------
TESTS = [
    ("T1_import_all_six_modules", t1_imports),
    ("T2_substrate_identity_4_modules", t2_substrate_identity),
    ("T3_one_ladder_cache_serves_all", t3_shared_ladder),
    ("T4_cross_module_task_exchange", t4_task_exchange),
    ("T5_four_engines_one_task", t5_four_engines_one_task),
    ("T6_open_gate_IR_equals_gated_gate", t6_gate_equivalence),
    ("T7_metarl_selftest_on_shim", t7_metarl_selftest),
    ("T8_full_stack_hybrid_unit", t8_full_stack_hybrid),
    ("T9_rsi_own_acceptance_suite", t9_rsi_acceptance),
    ("T10_rsi_leapforge_isolation", t10_rsi_isolation),
    ("T11_cross_engine_determinism", t11_determinism),
]


def main():
    only = set(a.split("_")[0] for a in sys.argv[1:])
    print("=" * 78)
    print("INTEGRATION TEST SUITE -- six uploaded files")
    print("=" * 78)
    t0 = time.time()
    for name, fn in TESTS:
        if only and name.split("_")[0] not in only:
            continue
        run_test(name, fn)
    total = time.time() - t0
    n_pass = sum(1 for r in RESULTS if r["pass"])
    print("-" * 78)
    print("RESULT: %d/%d passed in %.1fs" % (n_pass, len(RESULTS), total))
    # merge into results file
    prev = []
    if os.path.exists(RESULTS_PATH):
        try:
            prev = json.load(open(RESULTS_PATH))
        except ValueError:
            prev = []
    seen = {r["test"] for r in RESULTS}
    merged = [r for r in prev if r["test"] not in seen] + RESULTS
    order = {name: i for i, (name, _f) in enumerate(TESTS)}
    merged.sort(key=lambda r: order.get(r["test"], 99))
    with open(RESULTS_PATH, "w") as f:
        json.dump(merged, f, indent=2)
    print("results written to", RESULTS_PATH)
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
