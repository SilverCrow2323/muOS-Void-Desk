#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VoidDesk - Build Integrity Check v2
Run from the app root before packaging:   python3 BUILDCHECK.py [--smoke]

Compared to v1 it checks ALL .py files (not just desk/*.py), has no hard-coded
version, and catches the classes of bugs found in the 10.5.1 audit:
undefined names, duplicate methods, modules shadowed by a same-name package,
scripts called by the launcher but missing, hub -> App references to attributes
that do not exist, unprotected tar extraction, stale artifacts in the repo.
--smoke: starts the app headless for 8s in a temporary copy (SDL dummy) and looks for
         tracebacks / "intro non riuscita" / "main loop error" in the output.
Exit code: 0 = ok (warnings allowed), 1 = errors.
"""
import ast
import glob
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
errors, warnings = [], []


def head(t):
    print("\n[%s]" % t)


def ok(m):
    print("  OK   " + m)


def err(m):
    print("  FAIL " + m)
    errors.append(m)


def warn(m):
    print("  WARN " + m)
    warnings.append(m)


def py_files():
    out = []
    for dp, dn, fn in os.walk("."):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__", "runtime")]
        out += [os.path.join(dp, f)[2:] for f in fn if f.endswith(".py")]
    return sorted(out)


def read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


print("=" * 72)
print("VOIDDESK BUILD INTEGRITY CHECK v2")
print("=" * 72)
PY = py_files()

head("1 critical files")
for f in ("desk/main.py", "desk/nexus.py", "desk/intro.py", "desk/const.py",
          "bin/debug_main.py", "mux_launch.sh", "glyph", "assets"):
    if os.path.exists(f):
        ok(f)
    else:
        err("missing: " + f)

head("2 syntax (%d .py files)" % len(PY))
bad = 0
for f in PY:
    try:
        ast.parse(read(f), f)
    except SyntaxError as e:
        err("%s:%s %s" % (f, e.lineno, e.msg))
        bad += 1
if not bad:
    ok("all files compile")

head("3 undefined names (pyflakes)")
try:
    import pyflakes.api
    from pyflakes.reporter import Reporter
    n_undef = 0
    for f in PY:
        b = io.StringIO()
        pyflakes.api.check(read(f), f, Reporter(b, b))
        for ln in b.getvalue().splitlines():
            if "undefined name" in ln:
                err(ln)
                n_undef += 1
    if not n_undef:
        ok("no undefined names")
except ImportError:
    warn("pyflakes not installed: skipping (pip install pyflakes)")

head("4 duplicate methods in the same class")
dups = 0
for f in PY:
    try:
        tree = ast.parse(read(f))
    except SyntaxError:
        continue
    for c in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        seen = {}
        for m in c.body:
            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                deco = [ast.unparse(d) for d in m.decorator_list]
                if any(("setter" in d or "overload" in d or "getter" in d) for d in deco):
                    continue
                if m.name in seen:
                    err("%s: %s.%s defined at lines %d and %d (the last one wins)"
                        % (f, c.name, m.name, seen[m.name], m.lineno))
                    dups += 1
                seen[m.name] = m.lineno
if not dups:
    ok("no duplicates")

head("5 modules shadowed by a same-name package")
shadow = 0
for f in PY:
    stem = f[:-3]
    if os.path.isfile(os.path.join(stem, "__init__.py")):
        err("%s and %s/ coexist: the package shadows the module (dead code)" % (f, stem))
        shadow += 1
if not shadow:
    ok("no module/package conflicts")

head("6 scripts called by the launcher")
la = read("mux_launch.sh")
missing = set()
for m in re.finditer(r'\$APP_DIR/([A-Za-z0-9_./-]+)', la):
    rel = m.group(1).rstrip(".")
    if rel and not os.path.exists(rel):
        missing.add(rel)
for rel in sorted(missing):
    soft = rel.startswith(("sgrub", "runtime", "assets/logos"))
    if soft:
        warn("called by the launcher but missing: %s (optional, the launcher has a guard)" % rel)
    else:
        err("called by the launcher but missing: " + rel)
if not missing:
    ok("all paths exist")

head("7 shell syntax")
sh = shutil.which("sh")
for f in glob.glob("*.sh") + glob.glob("bin/*.sh") + glob.glob("lib/*.sh"):
    if sh:
        r = subprocess.run([sh, "-n", f], capture_output=True, text=True)
        if r.returncode == 0:
            ok(f)
        else:
            err("%s: %s" % (f, r.stderr.strip()))

head("8 version consistency")
vs = {}
for f in ("desk/const.py", "desk/main.py"):
    m = re.search(r'^VERSION\s*=\s*"([^"]+)"', read(f), re.M)
    vs[f] = m.group(1) if m else None
m = re.search(r'VOIDDESK v([0-9.]+)', la)
vs["mux_launch.sh"] = m.group(1) if m else None
if len(set(vs.values())) == 1 and None not in vs.values():
    ok("version %s everywhere" % list(vs.values())[0])
else:
    err("mismatched versions: %s" % vs)

head("9 hub -> App: attributes referenced but never defined")
try:
    mt = ast.parse(read("desk/main.py"))
    app = [n for n in mt.body if isinstance(n, ast.ClassDef) and n.name == "App"][0]
    defined = set()
    for n in app.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined.add(n.name)
        elif isinstance(n, ast.Assign):
            defined |= {t.id for t in n.targets if isinstance(t, ast.Name)}
    for n in ast.walk(app):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                and n.value.id == "self" and isinstance(n.ctx, (ast.Store, ast.Del)):
            defined.add(n.attr)
    others = [f for f in PY if f.startswith("desk/") and f != "desk/main.py"]
    for f in others:
        for n in ast.walk(ast.parse(read(f))):
            if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store):
                v = n.value
                if (isinstance(v, ast.Attribute) and v.attr == "app") or \
                        (isinstance(v, ast.Name) and v.id == "app"):
                    defined.add(n.attr)
    unresolved = {}
    for f in others:
        src = read(f)
        guard = set(re.findall(r'(?:hasattr|getattr)\((?:self\.)?app,\s*"(\w+)"', src))
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load):
                v = n.value
                if (isinstance(v, ast.Attribute) and v.attr == "app" and isinstance(v.value, ast.Name)
                        and v.value.id == "self") and n.attr not in defined and n.attr not in guard \
                        and not n.attr.startswith("__"):
                    unresolved.setdefault(n.attr, set()).add(f)
    for a, fs in sorted(unresolved.items()):
        warn("app.%s used in %s but never defined in App" % (a, ", ".join(sorted(fs))))
    if not unresolved:
        ok("all references resolved")
except Exception as e:  # the check must never break the build
    warn("hub->App check skipped: %s" % e)

head("9b App: self.X used in methods but never defined")
try:
    msrc = read("desk/main.py")
    mt2 = ast.parse(msrc)
    app2 = [n for n in mt2.body if isinstance(n, ast.ClassDef) and n.name == "App"][0]
    defd = set()
    for n in app2.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defd.add(n.name)
        elif isinstance(n, ast.Assign):
            defd |= {t.id for t in n.targets if isinstance(t, ast.Name)}

    def _walk(node):  # do not descend into nested classes (e.g. HTTP Handler)
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, ast.ClassDef):
                continue
            yield ch
            yield from _walk(ch)
    uses = {}
    for m in app2.body:
        if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for n in _walk(m):
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "self":
                    if isinstance(n.ctx, (ast.Store, ast.Del)):
                        defd.add(n.attr)
                    else:
                        uses.setdefault(n.attr, []).append(n.lineno)
    for n in ast.walk(mt2):  # setattr(self, "x", ...) and attributes set by other modules
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "setattr" \
                and len(n.args) >= 2 and isinstance(n.args[1], ast.Constant):
            defd.add(n.args[1].value)
    for f in PY:
        if f.startswith("desk/") and f != "desk/main.py":
            for n in ast.walk(ast.parse(read(f))):
                if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store):
                    v = n.value
                    if (isinstance(v, ast.Attribute) and v.attr == "app") or (isinstance(v, ast.Name) and v.id == "app"):
                        defd.add(n.attr)
    guarded = set(re.findall(r'(?:hasattr|getattr)\(self,\s*"(\w+)"', msrc))
    miss = {k: v for k, v in uses.items() if k not in defd and k not in guarded and not k.startswith("__")}
    for k, v in sorted(miss.items()):
        err("App.%s used (line %s) but never defined/assigned" % (k, ", ".join(map(str, v[:3]))))
    if not miss:
        ok("all App self.X attributes are defined")
except Exception as e:
    warn("self.X check skipped: %s" % e)

head("10 unprotected tar extractions")
bare = 0
for f in PY:
    if f.endswith("safe_extract.py"):
        continue
    for i, ln in enumerate(read(f).splitlines(), 1):
        if re.search(r'\b(tf|t|tar|tarf)\.extractall\(', ln) and 'members=' not in ln:
            warn("%s:%d direct tar.extractall (use safe_tar_extractall)" % (f, i))
            bare += 1
if not bare:
    ok("all tar extractions go through the helper")

head("11 stale artifacts")
stale = []
if os.path.exists("main.py"):
    stale.append("main.py in root (v10.x lives in desk/main.py)")
if os.path.exists(".git"):
    r = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    n = sum(1 for p in r.stdout.splitlines() if "__pycache__" in p or p.endswith(".pyc"))
    if n:
        stale.append("%d .pyc files tracked by git (git rm -r --cached)" % n)
if not os.path.exists(".gitignore"):
    stale.append("missing .gitignore")
for s in stale:
    warn(s)
if not stale:
    ok("no stale artifacts")

head("12 FD heuristics (as in v1)")
for f in ("desk/intro.py", "desk/main.py"):
    c = read(f)
    unclosed = c.count("open(") - c.count("with open(")
    if unclosed > 40:
        warn("%s: %d open() outside with" % (f, unclosed))
    else:
        ok("%s: %d open() outside with" % (f, unclosed))

if "--smoke" in sys.argv:
    head("13 headless smoke test (8s, temporary copy)")
    try:
        import pygame  # noqa: F401
        tmp = tempfile.mkdtemp(prefix="vd_smoke_")
        dst = os.path.join(tmp, "app")
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy",
                   PYGAME_HIDE_SUPPORT_PROMPT="1", VOIDDESK_NOINTRO="")
        bad_pat = ("Traceback", "intro non riuscita", "main loop error", "[ERROR]")

        def _s(x):
            return x.decode("utf-8", "replace") if isinstance(x, bytes) else (x or "")
        try:
            r = subprocess.run([sys.executable, os.path.join(dst, "bin", "debug_main.py")],
                               capture_output=True, text=True, timeout=8, env=env, cwd=dst)
            out, alive = _s(r.stdout) + _s(r.stderr), False
        except subprocess.TimeoutExpired as e:
            out, alive = _s(e.stdout) + _s(e.stderr), True
        shutil.rmtree(tmp, ignore_errors=True)
        hit = [p for p in bad_pat if p in out]
        for p in hit:
            err("smoke: found '%s' in the output" % p)
        if not alive:
            err("smoke: the app exited before 8s")
        elif not hit:
            ok("app alive after 8s, no startup errors (intro enabled)")
    except ImportError:
        warn("pygame not available: smoke test skipped")

print("\n" + "=" * 72)
if errors:
    print("FAILED: %d errors, %d warnings" % (len(errors), len(warnings)))
    sys.exit(1)
print("PASSED (%d warnings)" % len(warnings))
sys.exit(0)
