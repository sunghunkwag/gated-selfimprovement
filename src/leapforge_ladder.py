#!/usr/bin/env python3
"""
leapforge_ladder -- ADAPTER SHIM (integration deliverable)
==========================================================
`leapforge_metarl.py` (Expedition XV meta-RL) imports a module named
`leapforge_ladder` -- the Expedition XIV substrate -- which was NOT among
the six uploaded files. This shim reconstructs that module's public API
from `leapforge_unified.py`, which carries a verbatim copy of the XIV
substrate (substrate fingerprint ccab00a723701e34, identical across
leapforge_unified / _plasticity / _gated / _open).

API required by leapforge_metarl (verified by static scan of its source):
    NAMES              -- sorted list of the 20 primitive names
    PRNG(seed_text)    -- deterministic PRNG; metarl calls .n(k)
    run(pipe, xs)      -- execute a pipeline of primitive names
    get_ladder()       -- (seen, levels) certified difficulty ladder
    tasks_at(lv, n, seed=...) -- n certified tasks at ladder level lv
(`L.solve` appears only inside a comment in leapforge_metarl; it is not
an attribute access and is intentionally not provided.)
"""
import leapforge_unified as _U

NAMES = _U.NAMES
run = _U.run
get_ladder = _U.get_ladder
substrate_fingerprint = _U.substrate_fingerprint


class PRNG(_U.XorShift64Star):
    """XorShift64Star with the `.n(k)` alias leapforge_metarl expects."""

    def n(self, k):
        return self.below(k)


_POOL_MEMO = {}


def tasks_at(level, n, seed=0):
    """n certified tasks at ladder level `level`, deterministic in
    (level, n, seed). Uses the substrate's own draw_task machinery:
    every task is certified (no shallower pipeline fits its train set).
    Memoized per (level, n, seed): draw_task is deterministic in those
    arguments, so caching changes nothing observable."""
    k = (int(level), int(n), int(seed))
    if k not in _POOL_MEMO:
        _POOL_MEMO[k] = [_U.draw_task(k[0], k[2], "source", "mrl%d" % i)
                         for i in range(k[1])]
    return _POOL_MEMO[k]
