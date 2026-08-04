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
says so on every run". LOCK #1: an empty scan is never vacuously true — `scanned == 0` is RED.

LAW 2 — EVERY DECLARED `ported`/`already-in-v3` ROW POINTS AT A REAL v3 FILE. `MODULES`/`FUNCTIONS`
below are the AUTHORED historical record of what happened to v2's memory package and its three
economy modules — no longer diffed against a freshly-derived v2 population (V3-EXTRACT-OBLIGATIONS
phase 3 cut that half: comparing the list against v2's own source, read at the oracle commit, plus
the `replaced-by-typed`/`dropped`/`deferred` phrase checks against §10/§11 of the spec at the same
ref). Two directions used to be checked; one remains, and it needs nothing from the ancestor:

  PORTED    → the named v3 module is on disk and carries the behaviour.
  ALREADY   → the named v3 module is on disk; the thing exists here under another shape.

`replaced-by-typed`/`dropped`/`deferred` rows are kept as data — the record of what happened — but
verified by nothing now: the artifact each one pointed at (a phrase in the target-SDK or build-plan
prose, at a pinned commit) is exactly the ancestor-facing half this file no longer reads.

WHAT THIS DOES NOT CLAIM. It checks a PORTED/ALREADY row against the tree; it does not judge whether
a port is faithful. That is what the two-sided gates over `ledger`, `meter` and `iteration` are for,
and conflating the two would be the same over-claim this file exists to catch.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent

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


#: The nine modules of v2's memory package, as an AUTHORED historical record — no longer diffed
#: against a freshly-derived v2 population (that half retired with V3-EXTRACT-OBLIGATIONS phase 3).
#: Only `ported`/`already-in-v3` rows carry a live check below (law 2).
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


# ── law 2: every declared PORTED/ALREADY row points at a real file ──────────────────────────
def _evidence_problems(kind: str, declared: dict, root: Path) -> list[str]:
    """Only `ported`/`already-in-v3` rows are checked — the other three dispositions used to be
    verified against a phrase at the oracle commit, and that reading died with the ancestor
    (V3-EXTRACT-OBLIGATIONS phase 3). They are still DATA (the record of what happened), just no
    longer independently proven each run."""
    problems: list[str] = []
    for name, row in sorted(declared.items()):
        if row.disposition in (PORTED, ALREADY) and not (root / row.evidence).exists():
            problems.append(f"{kind} {name}: declared {row.disposition} at {row.evidence}, which "
                            f"is not there")
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


def check(root: Path = _ROOT, *, sabotage: str = "") -> tuple[list[str], dict]:
    """Both laws. `sabotage` plants one named defect class and is used only by the red side."""
    modules, functions = dict(MODULES), dict(FUNCTIONS)
    if sabotage == "missing_evidence":
        functions = dict(functions)
        functions["metrics.metrics_path"] = Row(PORTED, "v3/economy/__sabotage_missing__.py")

    if sabotage == "transcript_leak":
        problems, scanned = analyze(SABOTAGE_SOURCE, "<sabotage>"), 1
    elif sabotage == "empty_scan":
        problems, scanned = [], 0
    else:
        problems, scanned = transcript_problems(root, METERED_SOURCES)
    if scanned == 0:
        problems.append("law 1 scanned ZERO metered sources; a green would be vacuous (Lock #1)")

    problems += _evidence_problems("module", modules, root)
    problems += _evidence_problems("function", functions, root)
    return problems, {"modules": len(modules), "functions": len(functions), "scanned": scanned}
