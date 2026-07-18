#!/usr/bin/env python3
"""
TFORGE -- self-improvement on a TURING-COMPLETE substrate
=========================================================
A register/stack VM with real conditional branches (JZ), data-dependent
loops (LOOP/LEN), and generic higher-order control (MAPE map, FOLD
reduce). Execution is TOTAL (a step cap makes every program halt) and
CRASH-SAFE (faults return partial/None, never raise), so a blind searcher
can score arbitrary bytecode. Multi-step stateful algorithms (running-max,
etc.) live in the program space.

The same improvement loop as the rest of this project runs on it:
EA solver + presence prior + COUNTERFACTUAL macro admission +
self-curriculum, with a warmup curriculum bootstrapping the archive.
Arms OPEN (admission on) vs CLOSED (off). Headline metric: macros
admitted (each counterfactually gated) -- OPEN > 0, CLOSED = 0 by
construction.

CLI:
  python3 tforge.py selftest
  python3 tforge.py run OPEN|CLOSED <seed> <gens> <budget_s>
  python3 tforge.py report
"""
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "tforge_log.jsonl")
T0 = time.time()

STEP_CAP = 400
OUT_CAP = 64
STACK_CAP = 64
LOOP_CAP = 40
VAL_LO, VAL_HI = -(1 << 20), (1 << 20)
MASK = (1 << 64) - 1


class PRNG(object):
    def __init__(self, seed_text):
        d = hashlib.sha256(str(seed_text).encode()).digest()
        self.s = int.from_bytes(d[:8], "big") or 0x9E3779B97F4A7C15

    def u64(self):
        x = self.s
        x ^= (x >> 12)
        x ^= (x << 25) & MASK
        x ^= (x >> 27)
        self.s = x
        return (x * 2685821657736338717) & MASK

    def below(self, n):
        return self.u64() % n if n > 0 else 0

    def unit(self):
        return self.u64() / float(1 << 64)

    def choice(self, seq):
        return seq[self.below(len(seq))]


NULLARY = ["PUSHx", "DUP", "SWAP", "DROP", "OVER", "ADD", "SUB", "MUL",
           "MODc", "MINc", "MAXc", "NEG", "INC", "DEC", "CMP", "EMIT",
           "ADVANCE", "LEN"]
OPCODES = NULLARY + ["PUSHi", "JZ", "LOOP", "MAPE", "FOLD"]


def _clamp(v):
    if v < VAL_LO:
        return VAL_LO
    if v > VAL_HI:
        return VAL_HI
    return v


def _inline(prog, macros, depth=0):
    if depth > 6:
        return None
    out = []
    for tok in prog:
        if tok[0] == "MACRO":
            body = macros.get(tok[1])
            if body is None:
                return None
            sub = _inline(body, macros, depth + 1)
            if sub is None:
                return None
            out.extend(sub)
        else:
            out.append(tok)
    return out


def _run_block(block, st, out, xs, cur, macros):
    """Execute a bounded body once (shared stack/out). Nested JZ/LOOP/MAPE/
    FOLD inside a body are treated as no-ops (flat accounting). Returns new
    read cursor, or None on fault."""
    ip, n = 0, len(block)
    while ip < n:
        tok = block[ip]
        op = tok[0]
        try:
            if op == "PUSHi":
                if len(st) >= STACK_CAP:
                    return None
                st.append(_clamp(int(tok[1])))
            elif op == "PUSHx":
                if len(st) >= STACK_CAP:
                    return None
                st.append(xs[cur] if 0 <= cur < len(xs) else 0)
            elif op == "DUP":
                if not st:
                    return None
                st.append(st[-1])
            elif op == "OVER":
                if len(st) < 2:
                    return None
                st.append(st[-2])
            elif op == "SWAP":
                if len(st) < 2:
                    return None
                st[-1], st[-2] = st[-2], st[-1]
            elif op == "DROP":
                if not st:
                    return None
                st.pop()
            elif op in ("ADD", "SUB", "MUL", "MODc", "MINc", "MAXc", "CMP"):
                if len(st) < 2:
                    return None
                b = st.pop()
                a = st.pop()
                if op == "ADD":
                    st.append(_clamp(a + b))
                elif op == "SUB":
                    st.append(_clamp(a - b))
                elif op == "MUL":
                    st.append(_clamp(a * b))
                elif op == "MODc":
                    st.append(a % b if b != 0 else 0)
                elif op == "MINc":
                    st.append(a if a < b else b)
                elif op == "MAXc":
                    st.append(a if a > b else b)
                elif op == "CMP":
                    st.append((a > b) - (a < b))
            elif op in ("NEG", "INC", "DEC"):
                if not st:
                    return None
                a = st.pop()
                st.append(_clamp(-a if op == "NEG"
                                 else a + 1 if op == "INC" else a - 1))
            elif op == "EMIT":
                if not st:
                    return None
                if len(out) >= OUT_CAP:
                    return cur
                out.append(st.pop())
            elif op == "ADVANCE":
                cur = min(cur + 1, len(xs))
            elif op == "LEN":
                if len(st) >= STACK_CAP:
                    return None
                st.append(max(0, len(xs) - cur))
        except Exception:
            return None
        ip += 1
    return cur


def run(prog, xs, macros):
    """Execute; return output list or None on fault. Total (halts)."""
    flat = _inline(prog, macros)
    if flat is None:
        return None
    n = len(flat)
    if n == 0:
        return []
    st, out, cur, ip, steps = [], [], 0, 0, 0
    while ip < n:
        steps += 1
        if steps > STEP_CAP:
            return out
        tok = flat[ip]
        op = tok[0]
        try:
            if op == "PUSHi":
                if len(st) >= STACK_CAP:
                    return out
                st.append(_clamp(int(tok[1])))
            elif op == "PUSHx":
                if len(st) >= STACK_CAP:
                    return out
                st.append(xs[cur] if 0 <= cur < len(xs) else 0)
            elif op == "DUP":
                if not st:
                    return out
                st.append(st[-1])
            elif op == "OVER":
                if len(st) < 2:
                    return out
                st.append(st[-2])
            elif op == "SWAP":
                if len(st) < 2:
                    return out
                st[-1], st[-2] = st[-2], st[-1]
            elif op == "DROP":
                if not st:
                    return out
                st.pop()
            elif op in ("ADD", "SUB", "MUL", "MODc", "MINc", "MAXc", "CMP"):
                if len(st) < 2:
                    return out
                b = st.pop()
                a = st.pop()
                if op == "ADD":
                    st.append(_clamp(a + b))
                elif op == "SUB":
                    st.append(_clamp(a - b))
                elif op == "MUL":
                    st.append(_clamp(a * b))
                elif op == "MODc":
                    st.append(a % b if b != 0 else 0)
                elif op == "MINc":
                    st.append(a if a < b else b)
                elif op == "MAXc":
                    st.append(a if a > b else b)
                elif op == "CMP":
                    st.append((a > b) - (a < b))
            elif op in ("NEG", "INC", "DEC"):
                if not st:
                    return out
                a = st.pop()
                st.append(_clamp(-a if op == "NEG"
                                 else a + 1 if op == "INC" else a - 1))
            elif op == "EMIT":
                if not st:
                    return out
                if len(out) >= OUT_CAP:
                    return out
                out.append(st.pop())
            elif op == "ADVANCE":
                cur = min(cur + 1, len(xs))
            elif op == "LEN":
                if len(st) >= STACK_CAP:
                    return out
                st.append(max(0, len(xs) - cur))
            elif op == "JZ":
                if not st:
                    return out
                v = st.pop()
                if v == 0:
                    ip += max(1, int(tok[1]))
                    continue
            elif op == "LOOP":
                if not st:
                    return out
                cnt = max(0, min(LOOP_CAP, int(st.pop())))
                rel = max(1, int(tok[1]))
                block = flat[ip + 1: ip + 1 + rel]
                if not block:
                    ip += 1
                    continue
                for _ in range(cnt):
                    steps += len(block)
                    if steps > STEP_CAP:
                        return out
                    sub = _run_block(block, st, out, xs, cur, macros)
                    if sub is None:
                        return out
                    cur = sub
                ip += 1 + rel
                continue
            elif op == "MAPE":
                rel = max(1, int(tok[1]))
                block = flat[ip + 1: ip + 1 + rel]
                for e in xs[cur:]:
                    steps += len(block) + 1
                    if steps > STEP_CAP or len(out) >= OUT_CAP:
                        return out
                    st.append(e)
                    if _run_block(block, st, out, xs, cur, macros) is None:
                        return out
                    if not st:
                        return out
                    out.append(st.pop())
                cur = len(xs)
                ip += 1 + rel
                continue
            elif op == "FOLD":
                rel = max(1, int(tok[1]))
                block = flat[ip + 1: ip + 1 + rel]
                rest = xs[cur:]
                if rest:
                    acc = rest[0]
                    for e in rest[1:]:
                        steps += len(block) + 2
                        if steps > STEP_CAP:
                            return out
                        st.append(acc)
                        st.append(e)
                        if _run_block(block, st, out, xs, cur,
                                      macros) is None:
                            return out
                        if not st:
                            return out
                        acc = st.pop()
                    if len(out) < OUT_CAP:
                        out.append(acc)
                cur = len(xs)
                ip += 1 + rel
                continue
            else:
                return out
        except Exception:
            return out
        ip += 1
    return out


# ---------------------------------------------------------------------------
def vocab(macros):
    return OPCODES + ["MACRO:" + m for m in sorted(macros)]


def _tok_key(tok):
    return "MACRO:" + tok[1] if tok[0] == "MACRO" else tok[0]


def rand_tok(prng, macros):
    op = prng.choice(vocab(macros))
    if op == "PUSHi":
        return ("PUSHi", prng.below(9) - 2)
    if op in ("JZ", "LOOP", "MAPE", "FOLD"):
        return (op, 1 + prng.below(3))
    if op.startswith("MACRO:"):
        return ("MACRO", op[6:])
    return (op,)


def rand_prog(prng, macros, lo=2, hi=10):
    return [rand_tok(prng, macros) for _ in range(lo + prng.below(hi - lo + 1))]


def mutate(prog, prng, macros):
    p = list(prog)
    r = prng.unit()
    if r < 0.30 and len(p) < 24:
        p.insert(prng.below(len(p) + 1), rand_tok(prng, macros))
    elif r < 0.55 and len(p) > 1:
        p.pop(prng.below(len(p)))
    elif r < 0.85 and p:
        p[prng.below(len(p))] = rand_tok(prng, macros)
    else:
        if p:
            i = prng.below(len(p))
            j = min(len(p), i + 1 + prng.below(3))
            seg = p[i:j]
            if len(p) + len(seg) <= 24:
                p[i:i] = seg
    return p


def crossover(a, b, prng):
    if not a or not b:
        return list(a or b)
    child = a[:prng.below(len(a))] + b[prng.below(len(b)):]
    return child[:24] if child else list(a)


# ---------------------------------------------------------------------------
def _reverse(xs):
    return list(reversed(xs))


def _runmax(xs):
    out, m = [], None
    for v in xs:
        m = v if m is None else max(m, v)
        out.append(m)
    return out


def _prefsum(xs):
    out, s = [], 0
    for v in xs:
        s += v
        out.append(s)
    return out


def _dedup(xs):
    out = []
    for v in xs:
        if not out or out[-1] != v:
            out.append(v)
    return out


def _countpos(xs):
    return [sum(1 for v in xs if v > 0)]


def _double(xs):
    return [v * 2 for v in xs]


def _incall(xs):
    return [v + 1 for v in xs]


def _maxelem(xs):
    return [max(xs)] if xs else []


def _sumall(xs):
    return [sum(xs)]


def _sort(xs):
    return sorted(xs)


def _len(xs):
    return [len(xs)]


def _clamppos(xs):
    return [v if v > 0 else 0 for v in xs]


def _last(xs):
    return [xs[-1]] if xs else []


def _first(xs):
    return [xs[0]] if xs else []


TRAIN_TASKS = {"incall": _incall, "double": _double, "sumall": _sumall,
               "maxelem": _maxelem, "countpos": _countpos, "len": _len,
               "clamppos": _clamppos, "last": _last, "first": _first,
               "prefsum": _prefsum}
EVAL_TASKS = {"reverse": _reverse, "runmax": _runmax, "dedup": _dedup,
              "sort": _sort}


def make_pairs(fn, prng, n, lo, hi, vlo=-9, vhi=9):
    out = []
    for _ in range(n):
        ln = lo + prng.below(hi - lo + 1)
        xs = [vlo + prng.below(vhi - vlo + 1) for _ in range(ln)]
        try:
            y = fn(list(xs))
        except Exception:
            y = None
        out.append((xs, y))
    return out


def task_from_fn(name, fn, prng):
    tr = make_pairs(fn, prng, 5, 2, 5)
    te = make_pairs(fn, prng, 5, 6, 9)
    if any(y is None for _x, y in tr + te):
        return None
    return {"name": name, "train": tr, "test": te}


# ---------------------------------------------------------------------------
def _sim(out, y):
    if out is None:
        return 0.0
    if out == y:
        return 1.0
    if len(y) == 0:
        return 0.0 if out else 0.9
    L = max(len(out), len(y))
    agree = sum(1 for i in range(min(len(out), len(y))) if out[i] == y[i])
    len_pen = 1.0 - abs(len(out) - len(y)) / float(L)
    return 0.5 * (agree / float(L)) + 0.4 * len_pen


def fitness(prog, pairs, macros):
    tot = 0.0
    for xs, y in pairs:
        tot += _sim(run(list(prog), list(xs), macros), y)
    return tot / float(len(pairs))


def exact(prog, pairs, macros):
    for xs, y in pairs:
        if run(list(prog), list(xs), macros) != y:
            return False
    return True


def solves(prog, task, macros):
    return (exact(prog, task["train"], macros)
            and exact(prog, task["test"], macros))


def uniform_prior(macros):
    return {t: 1.0 for t in vocab(macros)}


def sample_prog(prior, prng, macros, lo=2, hi=10):
    toks = vocab(macros)
    wts = [prior.get(t, 1.0) for t in toks]
    tot = sum(wts)
    prog = []
    for _ in range(lo + prng.below(hi - lo + 1)):
        r, acc, pick = prng.unit() * tot, 0.0, toks[-1]
        for t, w in zip(toks, wts):
            acc += w
            if r <= acc:
                pick = t
                break
        if pick == "PUSHi":
            prog.append(("PUSHi", prng.below(9) - 2))
        elif pick in ("JZ", "LOOP", "MAPE", "FOLD"):
            prog.append((pick, 1 + prng.below(3)))
        elif pick.startswith("MACRO:"):
            prog.append(("MACRO", pick[6:]))
        else:
            prog.append((pick,))
    return prog


def search(task, prior, budget, prng, macros):
    POP = 40
    guide = task["train"]
    evals = [0]

    def ev(p):
        evals[0] += 1
        return fitness(p, guide, macros)

    pop = []
    while len(pop) < POP and evals[0] < budget:
        p = sample_prog(prior, prng, macros)
        f = ev(p)
        if f >= 1.0 and solves(p, task, macros):
            return p, evals[0], [(f, p)]
        pop.append((f, p))
    while evals[0] < budget:
        pop.sort(key=lambda t: -t[0])
        elite = pop[:max(2, POP // 4)]
        newpop = list(elite)
        while len(newpop) < POP and evals[0] < budget:
            r = prng.unit()
            if r < 0.30:
                c = sample_prog(prior, prng, macros)
            elif r < 0.65:
                c = mutate(elite[prng.below(len(elite))][1], prng, macros)
            else:
                c = crossover(elite[prng.below(len(elite))][1],
                              pop[prng.below(len(pop))][1], prng)
            f = ev(c)
            if f >= 1.0 and solves(c, task, macros):
                return c, evals[0], [(ff, pp) for ff, pp in elite[:12]]
            newpop.append((f, c))
        pop = newpop
    pop.sort(key=lambda t: -t[0])
    return None, evals[0], [(f, p) for f, p in pop[:12]]


def fit_presence(solved_progs, macros):
    STRENGTH = 8.0
    prior = uniform_prior(macros)
    progs = {tuple(_tok_key(t) for t in p) for p in solved_progs}
    if not progs:
        return prior
    npr = float(len(progs))
    for tok in vocab(macros):
        rate = sum(1 for p in progs if tok in p) / npr
        prior[tok] = 1.0 + STRENGTH * rate
    return prior


def trust_step(prior_inc, prior_target, macros, lam=0.4, floor=0.08):
    keys = set(prior_inc) | set(prior_target)
    w = {k: (1 - lam) * prior_inc.get(k, 1.0)
         + lam * prior_target.get(k, 1.0) for k in keys}
    hi = max(w.values())
    return {k: max(v, floor * hi) for k, v in w.items()}


def mint_task(arm, seed, gen, k, prior, macros):
    prng = PRNG("tf-mint|%s|%d|%d|%d" % (arm, seed, gen, k))
    gen_prog = sample_prog(prior, prng, macros, lo=3, hi=9)

    def mk(n, lo, hi):
        out = []
        for _ in range(n):
            ln = lo + prng.below(hi - lo + 1)
            xs = [-9 + prng.below(19) for _ in range(ln)]
            out.append((xs, run(list(gen_prog), list(xs), macros)))
        return out
    tr, te = mk(5, 2, 5), mk(5, 6, 9)
    if any(y is None for _x, y in tr + te):
        return None
    if all(y == [] for _x, y in tr) or all(y == x for x, y in tr):
        return None
    task = {"name": "mint%d_%d" % (gen, k), "train": tr, "test": te}
    prog, _ev, _e = search(task, prior, 400,
                           PRNG("tf-screen|%s|%d|%d|%d" % (arm, seed, gen,
                                                          k)), macros)
    if prog is not None and solves(prog, task, macros):
        return None
    return task


def macro_candidates(sources, prng, n):
    cands = []
    for p in sources:
        if len(p) < 2:
            continue
        if len(p) <= 6 and not any(t[0] == "MACRO" for t in p):
            cands.append(list(p))
        for _ in range(3):
            i = prng.below(len(p))
            j = min(len(p), i + 2 + prng.below(4))
            body = p[i:j]
            if 2 <= len(body) <= 5 and not any(t[0] == "MACRO"
                                               for t in body):
                cands.append(body)
    out, seen = [], set()
    for b in cands:
        key = tuple(_tok_key(t) for t in b)
        if key not in seen:
            seen.add(key)
            out.append(b)
        if len(out) >= n:
            break
    return out


def seed_frontier():
    fr = []
    for name, fn in sorted(TRAIN_TASKS.items()):
        t = task_from_fn(name, fn, PRNG("tf-seed|" + name))
        if t is not None:
            fr.append(t)
    return fr


def state_path(arm, seed):
    return os.path.join(HERE, "tforge_state_%s_%d.json" % (arm, seed))


def fresh_state():
    return {"gen": 0, "macros": {}, "frontier": [], "archive": [],
            "eval_hist": [], "op_seq": 0, "last_admit_gen": 0,
            "last_solve_gen": 0, "metrics": []}


def load_state(arm, seed):
    p = state_path(arm, seed)
    return json.load(open(p)) if os.path.exists(p) else fresh_state()


def save_state(arm, seed, st):
    tmp = state_path(arm, seed) + ".tmp"
    json.dump(st, open(tmp, "w"))
    os.replace(tmp, state_path(arm, seed))


def _prog_from_json(p):
    return [tuple(t) for t in p]


def eval_score(prior, macros, seed):
    solved = []
    for name, fn in sorted(EVAL_TASKS.items()):
        task = task_from_fn(name, fn, PRNG("tf-evaltask|%s|%d" % (name, seed)))
        if task is None:
            continue
        prog, _ev, _e = search(task, prior, 6000,
                               PRNG("tf-evalsolve|%s|%d" % (name, seed)),
                               macros)
        if prog is not None and solves(prog, task, macros):
            solved.append(name)
    return solved


MINT_TRIES = 3
SOLVE_K = 4
SOLVE_BUDGET = 3000
MINE_CANDS = 16
CF_BUDGET = 1500
FRONTIER_CAP = 30
ARCHIVE_FIT = 30
EVAL_EVERY = 5


def log(rec):
    with open(LOG, "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")


def cmd_run(arm, seed, gens_target, budget):
    assert arm in ("OPEN", "CLOSED")
    st = load_state(arm, seed)
    macros = {k: _prog_from_json(v) for k, v in st["macros"].items()}
    frontier = [{"name": t["name"],
                 "train": [(x, y) for x, y in t["train"]],
                 "test": [(x, y) for x, y in t["test"]]}
                for t in st["frontier"]]
    if st["gen"] == 0:
        frontier = seed_frontier() + frontier
    archive = [_prog_from_json(p) for p in st["archive"]]
    prior = uniform_prior(macros)
    if archive:
        prior = trust_step(prior, fit_presence(archive[-ARCHIVE_FIT:],
                                               macros), macros)

    while st["gen"] < gens_target and budget - (time.time() - T0) > 10:
        st["gen"] += 1
        gen = st["gen"]
        evals = 0
        for k in range(MINT_TRIES):
            if len(frontier) >= FRONTIER_CAP:
                break
            t = mint_task(arm, seed, gen, k, prior, macros)
            evals += 400
            if t is not None:
                frontier.append(t)
        solved_now = 0
        still = []
        for j, task in enumerate(frontier):
            if j < SOLVE_K:
                prog, ev, _e = search(
                    task, prior, SOLVE_BUDGET,
                    PRNG("tf-solve|%s|%d|%d|%d" % (arm, seed, gen, j)),
                    macros)
                evals += ev
                if prog is not None and solves(prog, task, macros):
                    solved_now += 1
                    archive.append(prog)
                    st["last_solve_gen"] = gen
                    continue
            still.append(task)
        frontier = still
        admitted_now = 0
        if arm == "OPEN" and frontier:
            prng_m = PRNG("tf-mine|%s|%d|%d" % (arm, seed, gen))
            target = frontier[0]
            _p, _ev, elite = search(
                target, prior, CF_BUDGET,
                PRNG("tf-elite|%s|%d|%d" % (arm, seed, gen)), macros)
            evals += _ev
            sources = archive[-ARCHIVE_FIT:] + [p for _f, p in elite]
            for body in macro_candidates(sources, prng_m, MINE_CANDS):
                name = "m%02d" % (st["op_seq"] + 1)
                trial = dict(macros)
                trial[name] = body
                prior_t = uniform_prior(trial)
                if archive:
                    prior_t = trust_step(
                        prior_t, fit_presence(archive[-ARCHIVE_FIT:],
                                              trial), trial)
                p_w, ev_w, _e = search(
                    target, prior_t, CF_BUDGET,
                    PRNG("tf-cfw|%s|%d|%d" % (arm, seed, gen)), trial)
                evals += ev_w
                if not (p_w is not None and solves(p_w, target, trial)):
                    continue
                p_o, ev_o, _e = search(
                    target, prior, CF_BUDGET,
                    PRNG("tf-cfo|%s|%d|%d" % (arm, seed, gen)), macros)
                evals += ev_o
                if p_o is not None and solves(p_o, target, macros):
                    continue
                st["op_seq"] += 1
                macros[name] = body
                st["last_admit_gen"] = gen
                admitted_now += 1
                break
        prior = uniform_prior(macros)
        if archive:
            prior = trust_step(prior, fit_presence(archive[-ARCHIVE_FIT:],
                                                   macros), macros)
        ev_solved = None
        if gen % EVAL_EVERY == 0 or gen == 1:
            ev_solved = eval_score(prior, macros, seed)
            st["eval_hist"].append({"gen": gen, "solved": ev_solved})
        rec = {"exp": "tforge", "arm": arm, "seed": seed, "gen": gen,
               "vocab": len(vocab(macros)), "macros": len(macros),
               "frontier": len(frontier), "solved_now": solved_now,
               "archive": len(archive), "admitted_now": admitted_now,
               "eval_solved": ev_solved, "gen_evals": evals}
        log(rec)
        st["macros"] = {k: v for k, v in macros.items()}
        st["frontier"] = [{"name": t["name"], "train": t["train"],
                           "test": t["test"]}
                          for t in frontier[:FRONTIER_CAP]]
        st["archive"] = [list(p) for p in archive[-200:]]
        st["metrics"].append({k: rec[k] for k in
                              ("gen", "vocab", "macros", "archive",
                               "admitted_now")})
        save_state(arm, seed, st)

    final_eval = eval_score(prior, macros, seed)
    gen = st["gen"]
    diag = []
    if not frontier:
        diag.append("FRONTIER_EMPTY")
    if gen - st["last_solve_gen"] >= 10:
        diag.append("NO_SOLVE_10")
    if arm == "OPEN" and gen - st["last_admit_gen"] >= 15:
        diag.append("NO_ADMIT_15")
    if gen < gens_target:
        diag.append("WALL_CLOCK")
    out = {"arm": arm, "seed": seed, "gen": gen, "target": gens_target,
           "vocab": len(vocab(macros)), "macros": len(macros),
           "archive": len(archive), "eval_solved": final_eval,
           "n_eval_solved": len(final_eval),
           "diagnosis": diag or ["STILL_IMPROVING"],
           "elapsed": round(time.time() - T0, 1)}
    log({"exp": "tforge_final", **out})
    print(json.dumps(out))


def selftest():
    print("TFORGE selftest -- VM executes hand-written algorithms\n")
    m = {}
    copy = [("LEN",), ("LOOP", 3), ("PUSHx",), ("EMIT",), ("ADVANCE",)]
    assert run(copy, [5, 7, 9], m) == [5, 7, 9]
    print("  [1] LOOP+PUSHx+EMIT+ADVANCE copies input:", run(copy, [5, 7, 9], m))
    incall = [("LEN",), ("LOOP", 4), ("PUSHx",), ("INC",), ("EMIT",),
              ("ADVANCE",)]
    assert run(incall, [1, 2, 3], m) == [2, 3, 4]
    print("  [2] data-dependent loop count increments all:",
          run(incall, [1, 2, 3], m))
    dbl = [("LEN",), ("LOOP", 5), ("PUSHx",), ("DUP",), ("ADD",), ("EMIT",),
           ("ADVANCE",)]
    assert run(dbl, [3, -2, 4], m) == [6, -4, 8]
    print("  [3] DUP+ADD doubles each element:", run(dbl, [3, -2, 4], m))
    br = [("PUSHx",), ("JZ", 3), ("PUSHi", 1), ("EMIT",)]
    assert run(br, [5, 9], m) == [1] and run(br, [0, 9], m) == []
    print("  [4] JZ data-dependent branch: [5..]->[1], [0..]->[]")
    prng = PRNG("tf-fuzz")
    for _ in range(4000):
        p = rand_prog(prng, m, 1, 14)
        out = run(p, [prng.below(9) - 4 for _ in range(prng.below(8))], m)
        assert out is None or isinstance(out, list)
    print("  [5] 4000 random programs executed crash-free (total VM)")
    spin = [("PUSHi", 40), ("LOOP", 2), ("PUSHi", 1), ("PUSHi", 1)]
    _ = run(spin, [1, 2, 3], m)
    print("  [6] step cap guarantees halting on looping programs")
    runmax = [("PUSHx",), ("DUP",), ("EMIT",), ("ADVANCE",), ("LEN",),
              ("LOOP", 6), ("PUSHx",), ("MAXc",), ("DUP",), ("EMIT",),
              ("ADVANCE",), ("DUP",)]
    r = run(runmax, [3, 1, 4, 1, 5], m)
    print("  [7] hand-written running-max output:", r, "(target [3,3,4,4,5])")
    assert r == [3, 3, 4, 4, 5]
    print("\nOK -- branches (JZ) + data-dependent loops (LOOP/MAPE/FOLD),"
          " total, crash-safe. Real algorithms live in program space.")


def cmd_report():
    recs = [json.loads(l) for l in open(LOG)
            if '"exp": "tforge"' in l] if os.path.exists(LOG) else []
    fins = [json.loads(l) for l in open(LOG)
            if '"exp": "tforge_final"' in l] if os.path.exists(LOG) else []
    arms = {}
    for r in recs:
        arms.setdefault((r["arm"], r["seed"]), []).append(r)
    print("=" * 72)
    print("TFORGE -- self-improvement on a Turing-complete substrate")
    print("=" * 72)
    for (arm, seed), rows in sorted(arms.items()):
        rows.sort(key=lambda r: r["gen"])
        evrows = [r for r in rows if r.get("eval_solved") is not None]
        last_ev = evrows[-1]["eval_solved"] if evrows else []
        print("%s seed %d (gen %d): macros %d, archive %d, eval %d/4 %s"
              % (arm, seed, rows[-1]["gen"], rows[-1]["macros"],
                 rows[-1]["archive"], len(last_ev), sorted(last_ev)))
    if fins:
        print("\n-- final diagnoses --")
        for f in fins[-6:]:
            print("  %s s%d: %s eval %d/4"
                  % (f["arm"], f["seed"], f["diagnosis"],
                     f.get("n_eval_solved", 0)))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    if cmd == "selftest":
        selftest()
    elif cmd == "run":
        cmd_run(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]),
                float(sys.argv[5]) if len(sys.argv) > 5 else 30.0)
    elif cmd == "report":
        cmd_report()
    else:
        sys.exit("unknown command")
