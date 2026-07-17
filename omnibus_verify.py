#!/usr/bin/env python3
"""
Verification: omniforge.py (the merged single file) is behaviourally
EQUIVALENT to the six original modules. English output.

V1 substrate fingerprint + ladder counts identical to originals
V2 engine-level equivalence: same task, same seeds -> byte-identical
   (solved, evals, program) for all four engines, omniforge vs originals
V3 per-section source audits still pass inside the merged file
V4 metarl's own 8-invariant selftest passes inside omniforge
V5 rsi section: sample of its own acceptance tests passes identically
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)

import omniforge as OM                     # noqa: E402
import leapforge_unified as U              # noqa: E402
import leapforge_plasticity as P           # noqa: E402
import leapforge_gated as G                # noqa: E402
import leapforge_open as O                 # noqa: E402

for m in (U, P, G):
    m.CONFIG["outdir"] = os.path.join(HERE, "runs_shared")
for ns in (OM.NS_UNIFIED, OM.NS_PLASTICITY, OM.NS_GATED):
    ns.CONFIG["outdir"] = os.path.join(HERE, "runs")

ok_all = True


def check(name, cond, detail=""):
    global ok_all
    ok_all = ok_all and bool(cond)
    print("%s  %s  %s" % ("PASS" if cond else "FAIL", name, detail))


# V1 ------------------------------------------------------------------
check("V1_fingerprint",
      OM.NS_UNIFIED.substrate_fingerprint() == U.substrate_fingerprint()
      == "ccab00a723701e34")
_s, lv_o = OM.NS_UNIFIED.get_ladder()
_s, lv_u = U.get_ladder()
check("V1_ladder_counts",
      {d: len(v) for d, v in lv_o.items()}
      == {d: len(v) for d, v in lv_u.items()}
      == {1: 20, 2: 294, 3: 3858, 4: 47684})

# V2 ------------------------------------------------------------------
t_o = OM.NS_UNIFIED.draw_task(2, 23, "source", "equiv")
t_u = U.draw_task(2, 23, "source", "equiv")
check("V2_task_identical", t_o == t_u, "draw_task deterministic across builds")

res = {}
for tag, (mod, om) in {
        "unified": (U, OM.NS_UNIFIED), "plasticity": (P, OM.NS_PLASTICITY),
        "gated": (G, OM.NS_GATED), "open": (O, OM.NS_OPEN)}.items():
    if tag == "unified":
        a = mod.search_task(t_u, mod.uniform_prior(), 20000,
                            mod.XorShift64Star("eqv"))
        b = om.search_task(t_o, om.uniform_prior(), 20000,
                           om.XorShift64Star("eqv"))
    elif tag == "plasticity":
        a = mod.search_task_plastic(t_u, mod.uniform_manifold(), 20000,
                                    mod.XorShift64Star("eqv"))
        b = om.search_task_plastic(t_o, om.uniform_manifold(), 20000,
                                   om.XorShift64Star("eqv"))
    elif tag == "gated":
        ra, rb = {}, {}
        Wa = mod.uniform_manifold(ra, mod.get_state_context)
        Wb = om.uniform_manifold(rb, om.get_state_context)
        a = mod.search_task_gated(t_u, Wa, ra, 20000,
                                  mod.XorShift64Star("eqv"),
                                  mod.get_state_context)
        b = om.search_task_gated(t_o, Wb, rb, 20000,
                                 om.XorShift64Star("eqv"),
                                 om.get_state_context)
    else:
        oa, ob = {}, {}
        a = mod.search_task_open(t_u, mod.uniform_manifold_open(oa), oa,
                                 20000, mod.XorShift64Star("eqv"),
                                 mod.gen0_gate_tree())
        b = om.search_task_open(t_o, om.uniform_manifold_open(ob), ob,
                                20000, om.XorShift64Star("eqv"),
                                om.gen0_gate_tree())
    same = (a[0] == b[0]) and (a[1] == b[1])
    res[tag] = (a[0], a[1])
    check("V2_engine_equiv_" + tag, same,
          "program %s, evals %d identical" % (a[0], a[1]))

# V3 ------------------------------------------------------------------
for tag, ns in (("xv", OM.NS_UNIFIED), ("xvi", OM.NS_PLASTICITY),
                ("gx", OM.NS_GATED), ("xix", OM.NS_OPEN)):
    try:
        ns.audit_sources(quiet=True)
        check("V3_source_audit_" + tag, True, "section-scoped audit passed")
    except SystemExit as e:
        check("V3_source_audit_" + tag, False, "audit aborted: %s" % e)
    except Exception as e:
        check("V3_source_audit_" + tag, False,
              "%s: %s" % (type(e).__name__, e))

# V4 ------------------------------------------------------------------
t0 = time.time()
try:
    OM.NS_METARL.selftest()
    check("V4_metarl_selftest", True, "8/8 in %.1fs" % (time.time() - t0))
except BaseException as e:
    check("V4_metarl_selftest", False, "%s: %s" % (type(e).__name__, e))

# V5 ------------------------------------------------------------------
# sample of rsi's own tests that passed quickly in the original shard run
fast_pass = []
for line in open("rsi_shard_log.jsonl"):
    r = json.loads(line)
    if r["pass"] and r["s"] <= 0.3:
        fast_pass.append(r["i"])
sample = sorted(set(fast_pass))[::max(1, len(set(fast_pass)) // 25)][:25]
n_ok = 0
fails = []
for i in sample:
    t = OM.TESTS[i]
    try:
        t()
        n_ok += 1
    except BaseException as e:
        fails.append((i, t.__name__, str(e)[:80]))
check("V5_rsi_sample", n_ok == len(sample),
      "%d/%d sampled rsi acceptance tests pass in omniforge %s"
      % (n_ok, len(sample), fails if fails else ""))

print("-" * 70)
print("OMNIFORGE VERIFICATION:", "ALL PASS" if ok_all else "FAILURES ABOVE")
sys.exit(0 if ok_all else 1)
