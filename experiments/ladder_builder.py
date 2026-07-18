#!/usr/bin/env python3
"""Checkpointed ladder builder.

Replicates leapforge_unified.build() EXACTLY (same enumeration order, same
observational-equivalence pruning, using the module's own sig/NAMES/IDENT),
but resumable across processes: the sandbox caps each shell call at 45 s,
while a full depth-4 build may exceed it. When finished it writes the cache
file in leapforge_unified.get_ladder()'s exact format, so all four
substrate modules load it (fingerprint + sha validated).

Usage: python3 ladder_builder.py [budget_seconds]
Prints PROGRESS or DONE.
"""
import json
import hashlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)

import leapforge_unified as U  # noqa: E402

CKPT = os.path.join(HERE, "ladder_checkpoint.json")
OUTDIR = os.path.join(HERE, "runs_shared")
BUDGET = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
T0 = time.time()


def key(s):
    return json.dumps([list(t) for t in s])


def load():
    if os.path.exists(CKPT):
        with open(CKPT) as f:
            return json.load(f)
    return None


def save(st):
    tmp = CKPT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f)
    os.replace(tmp, CKPT)


st = load()
if st is None:
    # depths 1..3 in one shot (cheap), depth-4 frontier saved for chunking
    seen = {key(U.IDENT)}
    frontier = [[]]
    levels = {}
    for d in (1, 2, 3):
        nxt, new = [], []
        for p in frontier:
            for nm in U.NAMES:
                q = p + [nm]
                s = U.sig(q)
                if s is None:
                    continue
                k = key(s)
                if k in seen:
                    continue
                seen.add(k)
                new.append(q)
                nxt.append(q)
        frontier = nxt
        levels[str(d)] = new
        print("  depth %d: %d new behaviours (%.1fs)"
              % (d, len(new), time.time() - T0))
    st = {"seen": sorted(seen), "levels": levels, "idx": 0, "l4": []}
    save(st)

seen = set(st["seen"])
frontier = st["levels"]["3"]
idx, l4 = st["idx"], st["l4"]
n = len(frontier)
while idx < n and time.time() - T0 < BUDGET:
    p = frontier[idx]
    for nm in U.NAMES:
        q = p + [nm]
        s = U.sig(q)
        if s is None:
            continue
        k = key(s)
        if k in seen:
            continue
        seen.add(k)
        l4.append(q)
    idx += 1

if idx < n:
    st.update({"seen": sorted(seen), "idx": idx, "l4": l4})
    save(st)
    print("PROGRESS depth4 %d/%d (%.0f%%), %.1fs"
          % (idx, n, 100.0 * idx / n, time.time() - T0))
    sys.exit(0)

# finished: write the official cache in get_ladder()'s exact format
body = {d: st["levels"][d] for d in ("1", "2", "3")}
body["4"] = l4
fp = U.substrate_fingerprint()
c = {"fingerprint": fp, "max_depth": U.MAX_DEPTH, "levels": body,
     "sha": hashlib.sha256(U.canon(body).encode()).hexdigest()}
os.makedirs(OUTDIR, exist_ok=True)
with open(os.path.join(OUTDIR, "ladder_cache.json"), "w") as f:
    f.write(U.canon(c))
try:
    os.remove(CKPT)
except OSError:
    with open(CKPT, "w") as f:      # mounted folder may forbid deletion
        json.dump({"done": True}, f)
print("DONE counts=%s cache=%s (%.1fs)"
      % ({d: len(v) for d, v in body.items()},
         os.path.join(OUTDIR, "ladder_cache.json"), time.time() - T0))
