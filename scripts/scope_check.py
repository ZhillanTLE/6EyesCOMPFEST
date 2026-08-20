"""
scope_check.py — Mechanical pre-commit gate for the penyisihan scope rules.

    python scripts/scope_check.py

CLAUDE.md carries a pre-commit checklist. A checklist that only exists in a
document is a checklist nobody runs, and it already failed once: a loop over
the whole seed shipped as a bulk-testing script and was caught by review rather
than by process. This makes the checkable parts checkable.

It is not a substitute for reading the rules. Judgement questions -- is this a
dashboard? is this a second user input? -- stay human. What it catches is the
mechanical drift: a background thread, a write path, a second store, auth on
the recovery route, a seed sweep, a leaked key, a stray hex literal.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECOVERY = os.path.join(ROOT, "backend", "recovery")
ROUTES = os.path.join(ROOT, "backend", "routes")
FAILURES = []
NOTES = []

TRIPLE_D = '"' * 3
TRIPLE_S = "'" * 3


def walk(root, suffix=".py"):
    for base, _dirs, files in os.walk(root):
        if "__pycache__" in base:
            continue
        for f in files:
            if f.endswith(suffix):
                yield os.path.join(base, f)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def code_only(src):
    """Strip docstrings and comments before matching identifiers.

    A module whose docstring says "no Firestore here" is not a Firestore
    reference. Matching prose would train everyone to ignore the checker, which
    is worse than not having one at all.
    """
    src = re.sub(TRIPLE_D + r"(?:.|\n)*?" + TRIPLE_D, "", src)
    src = re.sub(TRIPLE_S + r"(?:.|\n)*?" + TRIPLE_S, "", src)
    src = re.sub(r"(?m)#.*$", "", src)
    return src


def rel(path):
    return os.path.relpath(path, ROOT).replace("\\", "/")


def fail(rule, detail):
    FAILURES.append("{}\n      {}".format(rule, detail))


# ── BE: nothing outside the request cycle ────────────────────────────────────
ASYNC_PATTERNS = [
    (r"\bthreading\.Thread\b", "background thread"),
    (r"\bmultiprocessing\b", "process pool"),
    (r"\bcelery\b", "task queue"),
    (r"\bapscheduler\b|\bschedule\.every\b", "scheduler"),
    (r"\bsocketio\.(emit|start_background_task)\b", "socket push"),
    (r"\basyncio\.create_task\b", "detached task"),
]
for path in list(walk(RECOVERY)) + list(walk(ROUTES)):
    src = code_only(read(path))
    for pattern, label in ASYNC_PATTERNS:
        if re.search(pattern, src):
            fail("BE: work outside the request cycle", "{} in {}".format(label, rel(path)))

# ── BE: no automated logging ─────────────────────────────────────────────────
# Runtime modules must not write to disk. Capture tools may; they are manual.
for path in walk(RECOVERY):
    if re.search(r"open\(\s*[^)]*?[\"'][wa]\+?[\"']", code_only(read(path))):
        fail("BE: automated data logging",
             "write-mode open() in runtime module {}".format(rel(path)))

# ── BE: no second store on the recovery path ─────────────────────────────────
STORE_PATTERNS = [
    (r"\bfirebase\b|\bfirestore\b", "Firestore"),
    (r"\bredis\b", "Redis"),
    (r"\bsqlite3\b", "SQLite"),
]
for path in list(walk(RECOVERY)) + list(walk(ROUTES)):
    src = code_only(read(path)).lower()
    for pattern, label in STORE_PATTERNS:
        if re.search(pattern, src):
            fail("BE: distributed database / second store",
                 "{} referenced in {}".format(label, rel(path)))

# ── FE: no auth on the recovery route ────────────────────────────────────────
for path in walk(ROUTES):
    if "require_auth" in code_only(read(path)):
        fail("FE: complex authentication", "require_auth in {}".format(rel(path)))

# ── AI: no bulk runner over the seed ─────────────────────────────────────────
for path in list(walk(os.path.join(ROOT, "backend", "tests"))) + list(
    walk(os.path.join(ROOT, "backend", "tools"))
):
    src = code_only(read(path))
    for m in re.finditer(r"for\s+\w+\s+in\s+.*all_travelers\(\)", src):
        fail("AI: bulk testing script",
             "loop over all_travelers() at {}:{}".format(
                 rel(path), src[: m.start()].count("\n") + 1))

# ── AI: nothing tunes at runtime ─────────────────────────────────────────────
for path in walk(RECOVERY):
    if re.search(r"\bconfig\.\w+\s*=\s*[^=]", code_only(read(path))):
        fail("AI: runtime parameter mutation",
             "assignment to a config constant in {}".format(rel(path)))

# ── Secrets ──────────────────────────────────────────────────────────────────
try:
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.splitlines()
    for f in tracked:
        base = os.path.basename(f)
        if (base == ".env" or base.startswith(".env.")) and not base.endswith(".example"):
            fail("Secrets", "{} is tracked in git".format(f))
    if not any(f.endswith(".env.example") for f in tracked):
        NOTES.append(".env.example is not tracked; judges cannot see the required keys")
except Exception as exc:
    NOTES.append("git check skipped: {}".format(exc))

# ── Design system: no stray hex ──────────────────────────────────────────────
ALLOWED_HEX = {"frontend/src/app/recovery/windfall.css"}
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
for sub in ("src/components/windfall", "src/lib/windfall", "src/app/recovery"):
    root = os.path.join(ROOT, "frontend", sub)
    if not os.path.isdir(root):
        continue
    for suffix in (".tsx", ".ts", ".css"):
        for path in walk(root, suffix):
            if rel(path) in ALLOWED_HEX:
                continue
            body = read(path)
            for m in HEX.finditer(body):
                fail("Design system: hardcoded hex",
                     "{} at {}:{}".format(m.group(0), rel(path),
                                          body[: m.start()].count("\n") + 1))

# ── Report ───────────────────────────────────────────────────────────────────
print("Windfall pre-commit scope check")
print("=" * 66)
for n in NOTES:
    print("  note   {}".format(n))
if FAILURES:
    for f in FAILURES:
        print("  FAIL   {}".format(f))
    print("\n{} violation(s). Stop and report before committing.".format(len(FAILURES)))
    sys.exit(1)

for line in (
    "no work outside the request cycle",
    "no automated logging in runtime modules",
    "no second store on the recovery path",
    "no auth on the recovery route",
    "no bulk runner over the seed",
    "no runtime parameter mutation",
    "no secrets tracked",
    "no hardcoded hex outside windfall.css",
):
    print("  ok     {}".format(line))

print("\nMechanical checks pass. Judgement questions still need a human:")
print("  - does this add a dashboard, history page, or second pre-AI input?")
print("  - does any copy state an unmeasured number?")
sys.exit(0)
