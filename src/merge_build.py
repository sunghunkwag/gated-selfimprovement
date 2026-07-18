#!/usr/bin/env python3
"""
merge_build.py -- generates omniforge.py, ONE runnable file unifying the
six uploaded modules.

Strategy
--------
* The five leapforge files are merged via scope-aware AST renaming:
  - top-level symbols that are AST-IDENTICAL across every file defining
    them AND reference only other shared symbols/builtins are emitted
    ONCE with prefix `lf_` (the deduplicated substrate: 3 verbatim
    copies deleted);
  - every other top-level symbol is prefixed per section (xv_, xvi_,
    gx_, xix_, mrl_), which resolves all same-name/different-semantics
    collisions mechanically;
  - comments are dropped by ast.unparse (docstrings survive) -- diet;
  - each section's __main__ block is removed; a single dispatcher
    routes `python3 omniforge.py <section> ...` to the section's main;
  - leapforge_metarl's missing `import leapforge_ladder as L` is
    replaced by an in-file shim bound to the shared substrate;
  - each section's source self-audit keeps working: per-section
    _self_source() returns just that section's line span.
* rsi_levels_metaforge_unified is appended VERBATIM (minus its
  `from __future__` line, hoisted to line 1, and its __main__ block).
  Its embedded source archives are KEPT: test_capacity_defaults... and
  the organic modes consume them, and the user chose "keep everything
  runnable".
* SimpleNamespace facades (NS_UNIFIED, NS_PLASTICITY, NS_GATED,
  NS_OPEN, NS_METARL, NS_LADDER) expose every section under its
  ORIGINAL names for verification and downstream use.
"""
import ast
import builtins
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

SECTIONS = [("xv", "leapforge_unified.py"),
            ("xvi", "leapforge_plasticity.py"),
            ("gx", "leapforge_gated.py"),
            ("xix", "leapforge_open.py"),
            ("mrl", "leapforge_metarl.py")]
RSI_FILE = "rsi_levels_metaforge_unified.py"
OUT = "omniforge.py"

BUILTIN_NAMES = set(dir(builtins))
HOISTED_IMPORTS = ["import ast", "import hashlib", "import json",
                   "import math", "import os", "import sys", "import time"]
HOISTED_NAMES = {"ast", "hashlib", "json", "math", "os", "sys", "time"}
FORCE_EXCLUDE_SHARED = {"_self_source", "cfg_sha", "audit_sources",
                        "main", "selftest", "report", "battery", "replay"}


# ---------------------------------------------------------------------------
# parse + inventory
# ---------------------------------------------------------------------------
def target_names(t):
    """Names BOUND by an assignment target. Attribute/Subscript targets
    (obj.attr = x, d[k] = v) bind nothing."""
    out = []

    def rec(x):
        if isinstance(x, ast.Name):
            out.append(x.id)
        elif isinstance(x, (ast.Tuple, ast.List)):
            for e in x.elts:
                rec(e)
        elif isinstance(x, ast.Starred):
            rec(x.value)

    rec(t)
    return out


def top_bindings(tree):
    names = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                names.extend(target_names(t))
        elif isinstance(node, ast.AnnAssign):
            names.extend(target_names(node.target))
    return names


def def_node(tree, name):
    """Last top-level node binding `name` (matches runtime semantics)."""
    found = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)) and node.name == name:
            found = node
        elif isinstance(node, ast.Assign):
            if any(isinstance(n, ast.Name) and n.id == name
                   for t in node.targets for n in ast.walk(t)):
                found = node
    return found


trees, sources = {}, {}
for sec, fn in SECTIONS:
    sources[sec] = open(fn, encoding="utf-8").read()
    trees[sec] = ast.parse(sources[sec])
tops = {sec: top_bindings(trees[sec]) for sec, _ in SECTIONS}
topsets = {sec: set(v) for sec, v in tops.items()}

# ---------------------------------------------------------------------------
# shared substrate: AST-identical across ALL definers + closure rule
# ---------------------------------------------------------------------------
all_names = set().union(*topsets.values())
candidates = set()
for nm in all_names:
    if nm in FORCE_EXCLUDE_SHARED:
        continue
    definers = [s for s in topsets if nm in topsets[s]]
    if len(definers) < 2:
        continue
    dumps = set()
    for s in definers:
        node = def_node(trees[s], nm)
        dumps.add(ast.dump(node) if node is not None else "<none>")
    if len(dumps) == 1 and "<none>" not in dumps:
        candidates.add(nm)


def bound_in(node):
    """Names bound anywhere inside `node` (params, assigns, for/with/
    except targets, comprehension targets, nested def/class names)."""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef)):
            out.add(n.name)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                a = n.args
                for arg in (a.posonlyargs + a.args + a.kwonlyargs
                            + ([a.vararg] if a.vararg else [])
                            + ([a.kwarg] if a.kwarg else [])):
                    out.add(arg.arg)
        elif isinstance(n, ast.Lambda):
            a = n.args
            for arg in (a.posonlyargs + a.args + a.kwonlyargs
                        + ([a.vararg] if a.vararg else [])
                        + ([a.kwarg] if a.kwarg else [])):
                out.add(arg.arg)
        elif isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            tgts = n.targets if isinstance(n, ast.Assign) else [n.target]
            for t in tgts:
                out.update(target_names(t))
        elif isinstance(n, ast.For):
            out.update(target_names(n.target))
        elif isinstance(n, ast.withitem) and n.optional_vars is not None:
            out.update(target_names(n.optional_vars))
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, ast.comprehension):
            out.update(target_names(n.target))
        elif isinstance(n, ast.NamedExpr):
            out.add(n.target.id)
    return out


def free_names(node):
    loads = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    return loads - bound_in(node) - BUILTIN_NAMES - HOISTED_NAMES


changed = True
while changed:
    changed = False
    for nm in sorted(candidates):
        s = next(x for x in topsets if nm in topsets[x])
        node = def_node(trees[s], nm)
        if not free_names(node) <= candidates:
            candidates.discard(nm)
            changed = True
shared = candidates
sys.stderr.write("shared substrate symbols (%d): %s\n"
                 % (len(shared), sorted(shared)))

# ---------------------------------------------------------------------------
# scope-aware renamer
# ---------------------------------------------------------------------------
class Renamer(ast.NodeTransformer):
    """Renames module-scope names per `mapping`, honouring shadowing.
    Scope chain for name lookup skips class scopes (Python semantics)."""

    def __init__(self, mapping):
        self.map = mapping
        self.stack = []          # list of (kind, locals)

    def _lookup_is_local(self, name):
        for kind, loc in reversed(self.stack):
            if kind == "class":
                continue         # class scope invisible to nested lookups
            if name in loc:
                return True
        return False

    def _function_scope(self, node):
        a = node.args
        loc = set()
        for arg in (a.posonlyargs + a.args + a.kwonlyargs
                    + ([a.vararg] if a.vararg else [])
                    + ([a.kwarg] if a.kwarg else [])):
            loc.add(arg.arg)
        loc |= self._assigned_shallow(node)
        return loc

    @staticmethod
    def _assigned_shallow(fn_node):
        """Names bound in fn_node's own body, NOT descending into nested
        function/class bodies (their names DO bind here though)."""
        out = set()

        def scan(stmts):
            for st in stmts:
                if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef,
                                   ast.ClassDef)):
                    out.add(st.name)
                    continue
                for n in ast.walk(st):
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                      ast.ClassDef, ast.Lambda)):
                        continue
                    if isinstance(n, ast.Assign):
                        for t in n.targets:
                            out.update(target_names(t))
                    elif isinstance(n, (ast.AugAssign, ast.AnnAssign)):
                        out.update(target_names(n.target))
                    elif isinstance(n, ast.For):
                        out.update(target_names(n.target))
                    elif isinstance(n, ast.withitem) and n.optional_vars:
                        out.update(target_names(n.optional_vars))
                    elif isinstance(n, ast.ExceptHandler) and n.name:
                        out.add(n.name)
                    elif isinstance(n, ast.NamedExpr):
                        out.add(n.target.id)
                    elif isinstance(n, (ast.Import, ast.ImportFrom)):
                        for al in n.names:
                            out.add((al.asname or al.name).split(".")[0])

        scan(fn_node.body)
        return out

    def visit_FunctionDef(self, node):
        if not self.stack:       # module level: rename the def name
            if node.name in self.map:
                node.name = self.map[node.name]
        node.args = self.visit(node.args)
        node.decorator_list = [self.visit(d) for d in node.decorator_list]
        self.stack.append(("function", self._function_scope(node)))
        node.body = [self.visit(st) for st in node.body]
        self.stack.pop()
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        a = node.args
        loc = set()
        for arg in (a.posonlyargs + a.args + a.kwonlyargs
                    + ([a.vararg] if a.vararg else [])
                    + ([a.kwarg] if a.kwarg else [])):
            loc.add(arg.arg)
        self.stack.append(("function", loc))
        node.body = self.visit(node.body)
        self.stack.pop()
        return node

    def visit_ClassDef(self, node):
        if not self.stack and node.name in self.map:
            node.name = self.map[node.name]
        node.bases = [self.visit(b) for b in node.bases]
        node.decorator_list = [self.visit(d) for d in node.decorator_list]
        cls_locals = set()
        for st in node.body:
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef,
                               ast.ClassDef)):
                cls_locals.add(st.name)
            elif isinstance(st, ast.Assign):
                for t in st.targets:
                    cls_locals.update(target_names(t))
            elif isinstance(st, ast.AnnAssign):
                cls_locals.update(target_names(st.target))
        self.stack.append(("class", cls_locals))
        node.body = [self.visit(st) for st in node.body]
        self.stack.pop()
        return node

    def _comp(self, node):
        loc = set()
        for gen in node.generators:
            for x in ast.walk(gen.target):
                if isinstance(x, ast.Name):
                    loc.add(x.id)
        self.stack.append(("function", loc))
        node = self.generic_visit(node)
        self.stack.pop()
        return node

    visit_ListComp = visit_SetComp = visit_DictComp = visit_GeneratorExp \
        = _comp

    def visit_Name(self, node):
        if node.id in self.map and not self._lookup_is_local(node.id):
            node.id = self.map[node.id]
        return node

    def visit_Global(self, node):
        node.names = [self.map.get(n, n) for n in node.names]
        return node


def render(nodes, mapping):
    mod = ast.Module(body=[Renamer(mapping).visit(n) for n in nodes],
                     type_ignores=[])
    ast.fix_missing_locations(mod)
    return ast.unparse(mod)


# ---------------------------------------------------------------------------
# emit shared substrate (from the first definer, original order)
# ---------------------------------------------------------------------------
shared_map = {nm: "lf_" + nm for nm in shared}
emitted, shared_nodes = set(), []
for sec, _fn in SECTIONS:
    for node in trees[sec].body:
        nm = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            nm = node.name
        elif isinstance(node, ast.Assign):
            ids = [n.id for t in node.targets for n in ast.walk(t)
                   if isinstance(n, ast.Name)]
            nm = ids[0] if ids else None
        if nm in shared and nm not in emitted:
            emitted.add(nm)
            shared_nodes.append(node)
shared_src = render(shared_nodes, dict(shared_map))

# ---------------------------------------------------------------------------
# per-section render
# ---------------------------------------------------------------------------
section_src, section_maps = {}, {}
for sec, fn in SECTIONS:
    mapping = dict(shared_map)
    for nm in topsets[sec]:
        if nm not in shared:
            mapping[nm] = "%s_%s" % (sec, nm)
    if sec == "mrl":
        mapping["L"] = "mrl_L"
    body = []
    for node in trees[sec].body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue                                  # hoisted / shimmed
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
                and isinstance(node.test.left, ast.Name) \
                and node.test.left.id == "__name__":
            continue                                  # per-file __main__
        nm = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            nm = node.name
        elif isinstance(node, ast.Assign):
            ids = [n.id for t in node.targets for n in ast.walk(t)
                   if isinstance(n, ast.Name)]
            nm = ids[0] if ids else None
        if nm in shared:
            continue                                  # deduplicated
        if isinstance(node, ast.FunctionDef) and node.name == "_self_source":
            # the source self-audit must see THIS SECTION only, not the
            # whole merged file (rsi legitimately contains tokens the
            # leapforge audits ban, e.g. `import random`)
            stub = ast.parse(
                'def _self_source():\n'
                '    """Merged-file adaptation: returns this SECTION\'s '
                'source span only, so the per-expedition source audit '
                'keeps auditing exactly the code it shipped with."""\n'
                '    with open(os.path.abspath(__file__), "r", '
                'encoding="utf-8") as f:\n'
                '        src = f.read()\n'
                '    a, b = _OMNI_SECTION_SPANS[%r]\n'
                '    return "\\n".join(src.split("\\n")[a:b + 1])\n' % sec
            ).body[0]
            body.append(stub)
            continue
        body.append(node)
    section_src[sec] = render(body, mapping)
    section_maps[sec] = mapping

# ---------------------------------------------------------------------------
# upgrade section (rsi_upgrade.py, if present): embedded with up_ prefix.
# Its `OM.` module references become direct globals inside the merged file.
# ---------------------------------------------------------------------------
up_src_text = None
if os.path.exists("rsi_upgrade.py"):
    up_raw = open("rsi_upgrade.py", encoding="utf-8").read()
    up_raw = up_raw.replace("OM.", "")          # omniforge globals directly
    up_tree = ast.parse(up_raw)
    up_tops = set(top_bindings(up_tree))
    up_map = {nm: "up_" + nm for nm in up_tops}
    up_body = []
    for node in up_tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue                             # hoisted; OM import gone
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
                and isinstance(node.test.left, ast.Name) \
                and node.test.left.id == "__name__":
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) \
                and isinstance(node.value.func, ast.Attribute):
            f = node.value.func
            # drop module-level os.chdir(...) / sys.path.insert(...)
            base = f.value
            if isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name) and base.id in ("os", "sys"):
                continue
        up_body.append(node)
    up_src_text = render(up_body, up_map)

# ---------------------------------------------------------------------------
# rsi verbatim (minus __future__ line and __main__ block)
# ---------------------------------------------------------------------------
rsi_src = open(RSI_FILE, encoding="utf-8").read()
rsi_tree = ast.parse(rsi_src)
rsi_lines = rsi_src.split("\n")
drop = set()
for node in rsi_tree.body:
    if isinstance(node, ast.ImportFrom) and node.module == "__future__":
        drop.update(range(node.lineno - 1, node.end_lineno))
    if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
            and isinstance(node.test.left, ast.Name) \
            and node.test.left.id == "__name__":
        drop.update(range(node.lineno - 1, node.end_lineno))
rsi_body = "\n".join(l for i, l in enumerate(rsi_lines) if i not in drop)

# ---------------------------------------------------------------------------
# glue: header, shim, spans, facades, dispatcher
# ---------------------------------------------------------------------------
HEADER = '''#!/usr/bin/env python3
"""
OMNIFORGE -- six uploaded files unified into ONE runnable file
==============================================================
Sections (all preserved runnable; see dispatcher at the bottom):
  lf_*   shared leapforge substrate  (ONE copy; was duplicated verbatim in
         4 files -- fingerprint ccab00a723701e34, proven identical)
  xv_*   Expedition XV    leapforge_unified     (1D unigram prior engine)
  xvi_*  Expedition XVI   leapforge_plasticity  (2D manifold + plasticity)
  gx_*   Expedition XVIII leapforge_gated       (3D state-gated manifold)
  xix_*  Expedition XIX   leapforge_open        (evolvable ops + gate IR)
  mrl_*  Expedition XV-RL leapforge_metarl      (meta-RL controller; its
         missing `leapforge_ladder` import is satisfied by an in-file shim)
  rsi    rsi_levels_metaforge_unified, VERBATIM (own namespace, unprefixed;
         zero API overlap with leapforge -- separate architecture kept
         runnable side-by-side, incl. its embedded source archives, which
         its capacity test and organic modes consume)

Diet applied: 3 duplicated substrate copies removed; leapforge comments
stripped (docstrings kept); per-file __main__ blocks replaced by one
dispatcher. NOT removed: engine variants, batteries, statistics, reports,
selftests, RSI archives (user chose "keep everything runnable").

CLI:
  python3 omniforge.py unified|plasticity|gated|open|metarl <args...>
  python3 omniforge.py rsi --mode test|demo|...
  python3 omniforge.py selftest        (cross-section integration checks)

Facades: NS_UNIFIED, NS_PLASTICITY, NS_GATED, NS_OPEN, NS_METARL,
NS_LADDER expose each section under its original names.
"""
from __future__ import annotations
'''

SHIM = '''
# ===== leapforge_ladder shim (satisfies mrl section) =====================
class _OmniPRNG(lf_XorShift64Star):
    def n(self, k):
        return self.below(k)


class _OmniLadderShim(object):
    NAMES = property(lambda self: lf_NAMES)
    PRNG = _OmniPRNG

    @staticmethod
    def run(pipe, xs):
        return lf_run(pipe, xs)

    @staticmethod
    def get_ladder():
        return xv_get_ladder()

    _memo = {}

    @classmethod
    def tasks_at(cls, level, n, seed=0):
        k = (int(level), int(n), int(seed))
        if k not in cls._memo:
            cls._memo[k] = [xv_draw_task(k[0], k[2], "source", "mrl%d" % i)
                            for i in range(k[1])]
        return cls._memo[k]


mrl_L = _OmniLadderShim()
'''

parts = []
parts.append(HEADER)
parts.append("\n".join(HOISTED_IMPORTS) + "\n")
spans, cursor = {}, sum(p.count("\n") for p in parts)


def add(tag, text):
    global cursor
    marker = "\n# ===== BEGIN SECTION: %s =====\n" % tag
    endm = "\n# ===== END SECTION: %s =====\n" % tag
    block = marker + text + endm
    start = cursor + marker.count("\n")
    parts.append(block)
    cursor += block.count("\n")
    spans[tag] = (start, cursor - 1)


add("substrate", shared_src)
add("xv", section_src["xv"])
add("xvi", section_src["xvi"])
add("gx", section_src["gx"])
add("xix", section_src["xix"])
parts.append(SHIM)
cursor += SHIM.count("\n")
add("mrl", section_src["mrl"])
if up_src_text is not None:
    add("upgrade", up_src_text)
add("rsi", rsi_body)

TAIL = "\n# ===== omniforge glue =====================================\n"
TAIL += "_OMNI_SECTION_SPANS = %r\n" % (spans,)
TAIL += "import types as _omni_types\n"
FACADE_NAMES = {"xv": "NS_UNIFIED", "xvi": "NS_PLASTICITY", "gx": "NS_GATED",
                "xix": "NS_OPEN", "mrl": "NS_METARL"}
for sec, ns in FACADE_NAMES.items():
    m = section_maps[sec]
    TAIL += "%s = _omni_types.SimpleNamespace(**{\n" % ns
    for orig in sorted(m):
        if orig == "L":
            continue
        TAIL += "    %r: %s,\n" % (orig, m[orig])
    TAIL += "})\n"
TAIL += "NS_LADDER = mrl_L\n"
TAIL += '''

def _omni_selftest():
    for _ns in (xv_CONFIG, xvi_CONFIG, gx_CONFIG):
        _ns["outdir"] = "runs"           # share one ladder cache
    a = xv_substrate_fingerprint()
    b = xvi_substrate_fingerprint()
    c = gx_substrate_fingerprint()
    d = xix_substrate_fingerprint()
    assert a == b == c == d, "substrate fingerprints diverged in merge"
    print("substrate fingerprint (all four sections):", a)
    t = xv_draw_task(2, 11, "source", "omni")
    engines = {}
    p, e, _ = xv_search_task(t, xv_uniform_prior(), 30000,
                             lf_XorShift64Star("omni-xv"))
    engines["xv"] = (lf_solves(p, t), e)
    p, e, _ = xvi_search_task_plastic(t, xvi_uniform_manifold(), 30000,
                                      lf_XorShift64Star("omni-xvi"))
    engines["xvi"] = (lf_solves(p, t), e)
    reg = {}
    W = gx_uniform_manifold(reg, gx_get_state_context)
    p, e, _ = gx_search_task_gated(t, W, reg, 30000,
                                   lf_XorShift64Star("omni-gx"),
                                   gx_get_state_context)
    engines["gx"] = (gx_solves_tokens(p, reg, t), e)
    ops = {}
    Wo = xix_uniform_manifold_open(ops)
    p, e, _ = xix_search_task_open(t, Wo, ops, 30000,
                                   lf_XorShift64Star("omni-xix"),
                                   xix_gen0_gate_tree())
    engines["xix"] = (xix_solves_open(p, ops, t), e)
    assert all(ok for ok, _e in engines.values()), engines
    print("one certified L2 task solved by all four engines:", engines)
    prng = lf_XorShift64Star("omni-gate")
    for _ in range(500):
        lst = [prng.below(256) for _ in range(prng.below(13))]
        assert xix_classify(xix_gen0_gate_tree(), lst) \\
            == gx_get_state_context(lst)
    print("open gate IR == gated gate on 500 fuzz lists")
    n = len(TESTS)
    assert n > 200, "rsi TESTS list missing"
    print("rsi section intact: %d acceptance tests registered" % n)
    print("OMNIFORGE SELFTEST OK")


def _omni_main():
    usage = ("usage: python3 omniforge.py "
             "{unified|plasticity|gated|open|metarl|rsi|upgrade|selftest} ...")
    if len(sys.argv) < 2:
        print(usage)
        return 2
    sec = sys.argv.pop(1)
    if sec == "selftest":
        _omni_selftest()
        return 0
    mains = {"unified": xv_main, "plasticity": xvi_main, "gated": gx_main,
             "open": xix_main, "metarl": mrl_main, "rsi": main,
             "upgrade": up_cli}
    if sec not in mains:
        print(usage)
        return 2
    return mains[sec]()


if __name__ == "__main__":
    sys.exit(_omni_main())
'''
parts.append(TAIL)

out = "".join(parts)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(out)
n_lines = out.count("\n") + 1
orig = sum(len(sources[s].split("\n")) for s, _ in SECTIONS) \
    + len(rsi_lines)
print("wrote %s: %d lines (originals: %d lines in 6 files; "
      "reduction %d lines)" % (OUT, n_lines, orig, orig - n_lines))
print("sections:", {k: v for k, v in spans.items()})
