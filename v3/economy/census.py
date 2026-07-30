"""Where did v2's economy surface go? — the count that has to add up, and the promise that has teeth.

    python3 -m v3.verify.checks.economy_census      (the gate; this module is the law)

§11.3's INC-6 row promises "the transcript parser is DELETED". Taken literally that criterion is
VACUOUS and was so on the day it was written: v3 has no economy at all — `v3/graph/__init__.py`
lists the v2 billing modules as out of scope and there is no `v3/economy/`. A criterion satisfied by
never having built the thing is precisely the shape this project keeps catching itself in: green
because nobody asked what was left out of the count. So the promise is converted into two laws that
can actually fail.

LAW 1 — THE ECONOMY NEVER READS A TRANSCRIPT. A static scan over the modules that produce economic
numbers, refusing any reference to a session transcript: the word itself, a path under the CLI's own
project store, or the `transcript_path` payload key. This is a proxy and it is stated as one — it
cannot see an assembled path — but it converts "we decided not to" into "it does not, and a process
says so on every run".

LAW 2 — EVERY PIECE OF v2's ECONOMY CARRIES EXACTLY ONE DISPOSITION. The list is DERIVED from v2's
own source read at the oracle commit (ADR-031 §2.1: the oracle is a commit, never the working tree),
so a function nobody thought about shows up as a hole rather than as an absence. Both directions are
checked: a v2 function with no disposition is a silent drop, and a disposition naming a function
that does not exist is paperwork for something imaginary.

FIVE DISPOSITIONS, each verified against something re-derivable:

  PORTED    → the named v3 module is on disk and carries the behaviour.
  ALREADY   → the named v3 module is on disk; the thing exists here under another shape.
  REPLACED  → a TYPED SDK surface does the job, and the phrase naming it is found in §10 at the ref
              — so "the SDK gives us this" cannot be asserted by whoever is doing the removing.
  DROPPED   → the retirement clause is found in §11 at the ref. The six transcript readers land
              here, on the strength of §11.4's own "the transcript parser" entry.
  DEFERRED  → the target increment is a real row in §11.3 at the ref, and the reason is non-empty.

WHAT THIS DOES NOT CLAIM. It counts dispositions and checks each one against an artifact; it does
not judge whether a port is faithful. That is what the two-sided gates over `ledger`, `meter` and
`iteration` are for, and conflating the two would be the same over-claim this file exists to catch.
"""

from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass
from pathlib import Path

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent
_V2_MEMORY = "src/metafactory/memory"
_TARGET_SDK = "docs/spec/10-target-sdk.md"
_BUILD_PLAN = "docs/spec/11-build-plan.md"

PORTED, ALREADY, REPLACED, DROPPED, DEFERRED = ("ported", "already-in-v3", "replaced-by-typed",
                                                "dropped", "deferred")

#: Law 1's scope: everything that produces or records an economic number. Not the whole of v3 —
#: naming the scope is part of the claim, and a scope that quietly grew to "the files that pass"
#: would be the count not adding up in the other direction.
METERED_SOURCES = ("v3/economy/*.py", "v3/memory/journal.py", "v3/host/session.py",
                   "v3/host/runner.py", "v3/control/budget.py")

#: What a transcript reference looks like. This module necessarily spells them in order to look for
#: them, so it is exempt from law 1 ON ITSELF and only on itself — the same carve-out, for the same
#: reason, as `v3.verify.import_boundary`'s rule 3.
TRANSCRIPT_MARKERS = ("transcript", ".claude/projects", "transcript_path")


@dataclass(frozen=True)
class Row:
    disposition: str
    evidence: str
    why: str = ""


#: The nine modules of v2's memory package. Every one carries a disposition, including the four that
#: are not economy — naming them OUT is what keeps the scope from being chosen after the fact.
MODULES: dict[str, Row] = {
    "__init__.py": Row(ALREADY, "v3/economy/__init__.py"),
    "metrics.py": Row(PORTED, "v3/economy/ledger.py"),
    "journal.py": Row(PORTED, "v3/memory/journal.py"),
    "precompact.py": Row(PORTED, "v3/control/hooks.py",
                         "the COUNTING half (`record`) lands here as the PreCompact callback; the "
                         "snapshot-for-rehydrate half is deferred per function below"),
    "instrument.py": Row(ALREADY, "v3/host/session.py",
                         "it existed to decide which TOOL NAME counted as a subagent spawn — the "
                         "exact matching that read 0.0 % for weeks after a rename (§05.8). The host "
                         "does not match a name: it records the delegation because it performed it"),
    "projection.py": Row(ALREADY, "v3/memory/projection.py", "ported by INC-5 with the corpus"),
    "cadence.py": Row(DEFERRED, "INC-11",
                      "cadence is the CLI's turn-boundary law; under the inversion the host owns "
                      "the turn, so it lands with the shell that replaces the v2 verbs, not with "
                      "the economy"),
    "overlap.py": Row(DEFERRED, "INC-11",
                      "an out-of-tree observer over the three memories (M6), not an economy series; "
                      "it has no v3 caller until `meta` becomes the thin shell"),
    "rehydrate.py": Row(DEFERRED, "INC-12",
                        "under the inversion this becomes «what the host injects per leaf» and "
                        "needs the node tree (§15.6, node N-0086)"),
}

#: Function-level dispositions for the three ECONOMY modules. `metrics.py`'s six transcript readers
#: are the rows §11.3's INC-6 row was really about, and they are all DROPPED with the plan's own
#: retirement clause plus the typed surface that made each one unnecessary.
FUNCTIONS: dict[str, Row] = {
    # ── metrics.py ──────────────────────────────────────────────────────────────────────────
    "metrics.metrics_path": Row(PORTED, "v3/economy/store.py"),
    "metrics.capture": Row(PORTED, "v3/economy/store.py",
                           "ported WITH a change: `append` returns whether the bytes landed, so a "
                           "failed write is reportable instead of indistinguishable from no work"),
    "metrics.read": Row(PORTED, "v3/economy/store.py"),
    "metrics.aggregate": Row(PORTED, "v3/economy/ledger.py"),
    "metrics.tier_for": Row(REPLACED, "model_usage",
                            "a tier guessed from a model-id string; the typed result names the "
                            "models and their spend itself"),
    "metrics.cost": Row(REPLACED, "total_cost_usd",
                        "a local price table times token counts; the price now arrives typed, so "
                        "the ledger stops carrying a copy of Anthropic's price list"),
    "metrics.model_split": Row(REPLACED, "model_usage",
                               "read the CLI's own private stats cache — another program's file, "
                               "with no contract and no version"),
    "metrics.stats_cache_path": Row(REPLACED, "model_usage",
                                    "the path to that private stats cache; nothing to point at"),
    "metrics.rollup_from_transcript": Row(DROPPED, "the transcript parser",
                                          "replaced by `ResultMessage.usage`/`model_usage`, which "
                                          "the host already receives and used to discard"),
    "metrics.cache_series": Row(DROPPED, "the transcript parser",
                                "cache reads arrive per result in `usage`; a series scraped out of "
                                "a file was a reconstruction of what the wire already said"),
    "metrics.detect_expirations": Row(DROPPED, "the transcript parser",
                                      "its only input was `cache_series`; with that gone it has no "
                                      "subject. The keep-warm rule it fed is §07.2 (b) and stays "
                                      "prose until a session-level series exists (INC-12)"),
    "metrics.churn_cost_share": Row(DROPPED, "the transcript parser",
                                    "per-leaf `tool_uses` is recorded now, but CROSS-leaf churn — "
                                    "the 776-re-read number — needs the node tree (INC-12). Dropped "
                                    "honestly rather than half-ported into something weaker"),
    "metrics.slot_residency_share": Row(DROPPED, "the transcript parser",
                                        "inferred residency from gaps between transcript entries; "
                                        "the host now holds the leaf's own wall time directly"),
    "metrics.transcript_model_split": Row(DROPPED, "the transcript parser",
                                          "replaced field-for-field by `model_usage`"),
    "metrics.wall_clock_hours": Row(DROPPED, "the transcript parser",
                                    "first and last transcript timestamp; the host times its own "
                                    "leaves and the runner its own stations"),
    "metrics.render_model_split": Row(ALREADY, "v3/kernel/report.py", "the bounded verdict bus"),
    "metrics.render": Row(ALREADY, "v3/kernel/report.py", "the bounded verdict bus"),
    # ── journal.py ──────────────────────────────────────────────────────────────────────────
    "journal.now": Row(PORTED, "v3/economy/store.py"),
    "journal.journal_path": Row(ALREADY, "v3/economy/store.py", "`series_path` generalises it"),
    "journal.append": Row(PORTED, "v3/memory/journal.py"),
    "journal.read": Row(PORTED, "v3/memory/journal.py"),
    "journal.latest": Row(PORTED, "v3/memory/journal.py"),
    # ── precompact.py ───────────────────────────────────────────────────────────────────────
    "precompact.record": Row(PORTED, "v3/control/hooks.py",
                             "the `compact` event, now written BY the PreCompact hook rather than "
                             "counted by hand afterwards (§07.2 rule c)"),
    "precompact.snapshot_path": Row(DEFERRED, "INC-12", "part of the rehydrate snapshot (N-0086)"),
    "precompact.build_snapshot": Row(DEFERRED, "INC-12", "part of the rehydrate snapshot (N-0086)"),
    "precompact.is_valid": Row(DEFERRED, "INC-12", "part of the rehydrate snapshot (N-0086)"),
    "precompact.write_snapshot": Row(DEFERRED, "INC-12", "part of the rehydrate snapshot (N-0086)"),
    "precompact.read_snapshot": Row(DEFERRED, "INC-12", "part of the rehydrate snapshot (N-0086)"),
    "precompact.render_for_rehydrate": Row(DEFERRED, "INC-12", "the rehydrate surface (N-0086)"),
    "precompact.surface_for_rehydrate": Row(DEFERRED, "INC-12", "the rehydrate surface (N-0086)"),
}

ECONOMY_MODULES = ("metrics", "journal", "precompact")


# ── the oracle: v2's surface, read AT A COMMIT ──────────────────────────────────────────────
def _show(ref: str, path: str) -> str:
    out = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True, cwd=_ROOT)
    if out.returncode != 0:
        raise FileNotFoundError(f"{path} @ {ref}: {out.stderr.strip()}")
    return out.stdout


def v2_modules(ref: str) -> list[str]:
    out = subprocess.run(["git", "ls-tree", "-r", "--name-only", ref, _V2_MEMORY],
                         capture_output=True, text=True, cwd=_ROOT)
    return sorted(Path(line).name for line in out.stdout.splitlines()
                  if line.strip().endswith(".py"))


def v2_functions(ref: str) -> list[str]:
    """`module.function` for every PUBLIC top-level function of the three economy modules."""
    names: list[str] = []
    for module in ECONOMY_MODULES:
        tree = ast.parse(_show(ref, f"{_V2_MEMORY}/{module}.py"))
        names += [f"{module}.{node.name}" for node in tree.body
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and not node.name.startswith("_")]
    return sorted(names)


def ref_binding_problems(ref_reader=_show) -> list[str]:
    """The price of this module's rule-3 exemption in `import_boundary`: prove the read is a
    function of the COMMIT, not of the tree. A working-tree read would succeed at any ref."""
    try:
        ref_reader("0" * 40, f"{_V2_MEMORY}/metrics.py")
    except FileNotFoundError:
        return []
    return [f"{_V2_MEMORY}/metrics.py was readable at a nonexistent ref: the census is reading the "
            f"working tree, so its exemption from the v2-import boundary is not earned"]


# ── law 1: the economy never reads a transcript ─────────────────────────────────────────────
def _docstring_nodes(tree: ast.AST) -> set:
    """The id()s of the string Constants that ARE docstrings.

    Excluded from law 1 deliberately, and the reason is not leniency. Prose explaining that this
    package does not read a transcript necessarily contains the word; a scan that flagged it would
    make the honest documentation of a decision indistinguishable from breaking it, and the usual
    repair for that is to stop writing the documentation. Comments never reach the AST at all, so
    they are excluded by the same logic without needing a rule.
    """
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        first = (getattr(node, "body", None) or [None])[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                and isinstance(first.value.value, str):
            out.add(id(first.value))
    return out


def analyze(source: str, label: str) -> list[str]:
    """The LAW: pure, no I/O, so the red side can feed it synthetic source (§12 rule 2).

    Flags a transcript marker appearing in EXECUTABLE code — a string literal that is not a
    docstring, an identifier, or an attribute name. That covers a path, a payload key, and an
    imported helper; it does not cover an assembled path, and that limit is stated rather than
    discovered later.
    """
    try:
        tree = ast.parse(source, filename=label)
    except SyntaxError as exc:
        return [f"{label}: does not parse ({exc.msg}, line {exc.lineno})"]

    skip = _docstring_nodes(tree)
    problems: list[str] = []
    for node in ast.walk(tree):
        hit = ""
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            hit = next((m for m in TRANSCRIPT_MARKERS if m in node.value.lower()), "")
        elif isinstance(node, ast.Name):
            hit = next((m for m in TRANSCRIPT_MARKERS if m in node.id.lower()), "")
        elif isinstance(node, ast.Attribute):
            hit = next((m for m in TRANSCRIPT_MARKERS if m in node.attr.lower()), "")
        if hit:
            problems.append(f"{label}:{getattr(node, 'lineno', 0)}: executable code names {hit!r} — "
                            f"the economy is derived from typed usage, and a transcript reference "
                            f"is how it quietly stops being")
    return problems


def transcript_problems(root: Path, sources=METERED_SOURCES) -> tuple[list[str], int]:
    """I/O at the edge: collect the metered sources, hand each to the law.

    Lock #1: the caller must treat `scanned == 0` as RED. An empty scan proves nothing, and this
    repo has already shipped one check that selected zero inputs and printed a pass (`N-0062`).
    """
    problems: list[str] = []
    scanned = 0
    self_path = Path(__file__).resolve()
    for pattern in sources:
        for path in sorted(Path(root).glob(pattern)):
            if not path.is_file() or path.resolve() == self_path:
                continue
            scanned += 1
            problems += analyze(path.read_text(encoding="utf-8", errors="replace"),
                                path.relative_to(root).as_posix())
    return problems, scanned


# ── law 2: every piece carries exactly one verified disposition ─────────────────────────────
def _plan_names(plan: str, target: str) -> bool:
    """Does the build plan name `target` as an increment, in either form it actually uses?

    §11.3's table writes a row as `**INC-n**`; §11.5bis introduces INC-12 in prose as
    `` `INC-12 INTERACTIVE-MODE` `` — a real, argued, non-optional increment that simply never got a
    table row. This law was written expecting only the first form and it caught that on its first
    run, which is the useful outcome and also the awkward one: the plan is read AT THE ORACLE
    COMMIT, so the gap cannot be repaired by editing today's spec. Accepting both forms is the
    honest resolution, not a weakening — an invented `INC-99` still appears in neither, and the
    missing row is recorded as a finding rather than papered over by a laxer substring test.
    """
    return f"**{target}**" in plan or f"`{target} " in plan


def _verify_row(label: str, row: Row, root: Path, sdk: str, plan: str, ref: str) -> list[str]:
    if row.disposition in (PORTED, ALREADY):
        if not (root / row.evidence).exists():
            return [f"{label}: declared {row.disposition} at {row.evidence}, which is not there"]
    elif row.disposition == REPLACED:
        if row.evidence not in sdk:
            return [f"{label}: declared replaced by «{row.evidence}», a phrase absent from "
                    f"{_TARGET_SDK} @ {ref[:8]} — the SDK cannot be said to cover it by whoever "
                    f"is removing it"]
        if not row.why.strip():
            return [f"{label}: replaced with no reason — a typed field is not self-explanatory"]
    elif row.disposition == DROPPED:
        if row.evidence not in plan:
            return [f"{label}: declared dropped on «{row.evidence}», a phrase absent from "
                    f"{_BUILD_PLAN} @ {ref[:8]}"]
        if not row.why.strip():
            return [f"{label}: dropped with no reason"]
    elif row.disposition == DEFERRED:
        if not _plan_names(plan, row.evidence):
            return [f"{label}: deferred to {row.evidence}, which the build plan @ {ref[:8]} does "
                    f"not name as an increment"]
        if not row.why.strip():
            return [f"{label}: deferred with no reason — a deferral with no trigger is a drop that "
                    f"has not admitted it yet"]
    else:
        return [f"{label}: unknown disposition {row.disposition!r}"]
    return []


def _census(kind: str, declared: dict, actual: list, root: Path, sdk: str, plan: str,
            ref: str) -> list[str]:
    problems: list[str] = []
    if not actual:
        problems.append(f"derived ZERO {kind} from the oracle @ {ref[:8]}: an empty oracle is never "
                        f"vacuously true (Lock #1)")
    for name in sorted(set(actual) - set(declared)):
        problems.append(f"{kind[:-1]} {name}: exists in v2 and carries NO disposition — this is the "
                        f"shape of the bug this census exists to catch")
    for name in sorted(set(declared) - set(actual)):
        problems.append(f"{kind[:-1]} {name}: has a disposition but does not exist at {ref[:8]} — "
                        f"paperwork for something imaginary")
    for name in sorted(set(declared) & set(actual)):
        problems.extend(_verify_row(f"{kind[:-1]} {name}", declared[name], root, sdk, plan, ref))
    return problems


#: A module that breaks law 1 three ways: a payload key, a store path, and an imported helper. The
#: red side runs the real LAW over this, so the witness cannot rot out of sync with the checker —
#: there is no fixture file to forget to update.
SABOTAGE_SOURCE = '''
"""A module that says it does not read transcripts — and then does."""
from pathlib import Path


def rollup(payload):
    path = payload["transcript_path"]
    home = Path.home() / ".claude/projects"
    transcript_lines = (home / path).read_text().splitlines()
    return len(transcript_lines)
'''


def check(ref: str, root: Path = _ROOT, *, sabotage: str = "") -> tuple[list[str], dict]:
    """Both laws. `sabotage` plants one named defect class and is used only by the red side."""
    modules, functions = dict(MODULES), dict(FUNCTIONS)
    if sabotage == "dropped_row":
        functions.pop("metrics.wall_clock_hours", None)
    elif sabotage == "phantom_row":
        functions["metrics.imaginary_helper"] = Row(PORTED, "v3/economy/ledger.py")

    if sabotage == "transcript_leak":
        problems, scanned = analyze(SABOTAGE_SOURCE, "<sabotage>"), 1
    else:
        problems, scanned = transcript_problems(root, METERED_SOURCES)
    if scanned == 0:
        problems.append("law 1 scanned ZERO metered sources; a green would be vacuous (Lock #1)")
    problems.extend(ref_binding_problems())

    sdk, plan = _show(ref, _TARGET_SDK), _show(ref, _BUILD_PLAN)
    problems += _census("modules", modules, v2_modules(ref), root, sdk, plan, ref)
    problems += _census("functions", functions, v2_functions(ref), root, sdk, plan, ref)
    return problems, {"modules": len(modules), "functions": len(functions), "scanned": scanned}
