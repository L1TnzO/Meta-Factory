#!/usr/bin/env python3
"""retirement_census — the tooth for `v3.verify.retirement`: every gate that depends on the dead
ancestor was DECIDED — retired with PROOF the subject is gone, or kept with an ARMED gate and a
counted obligation — never dropped, and never kept on a lie.

    python3 -m v3.verify.checks.retirement_census
    V3_RETIREMENT_SABOTAGE=1 python3 -m v3.verify.checks.retirement_census   # red side; ALSO exit 0

PASO 1 of `docs/work/V3-EXTRACT-RETIREMENT-INCREMENT.md`. §0/§1/§2/§4 of that doc are the WHY; this
module is the law over `v3.verify.retirement.RETIREMENT` (twelve authored `Row`s — do not edit that
table here, it is DATA, not generated). The split is the same one `extract_manifest`/`extract_package`
already use: the decisions are authored in `retirement.py`, the teeth live here.

POPULATION, DERIVED — never a literal list, or this census would be exactly the kind of prose table
the increment exists to replace. A `.py` path enters iff `extract_manifest.classify(path) == 'package'`
AND it depends on the dead ancestor, where "depends" is EITHER (i) a MODULE-LEVEL string literal naming
`retirement.V2_ROOT` (the dead ancestor's package root) or its non-trailing-slash form, OR (ii) `from
<M> import ...`
for some `M` already in the set — iterated to a fixpoint, which is what makes this the TRANSITIVE
closure `v3.verify.import_boundary._ORACLE_READERS` seeds (`verb_census` carries no literal of its own;
it enters ONLY one hop from `gate_census`, via `from .gate_census import _V2_CLI, _oracle, _show`).
Modules that name the ancestor WITHOUT depending on it — `import_boundary._NAMED_NOT_READ`'s two
grants plus `import_boundary.py` itself, which name it to DISPOSE of it or to SEARCH for it — are
excluded before the first pass, so they can never seed or receive population-hood either.

    THE MEASUREMENT THAT SHAPED TWO DESIGN CHOICES BELOW (2026-08-04) — both were found by actually
    running a first-draft derivation over the real tree, not by reasoning about it in the abstract.

    (1) SCAN ROOTS ARE `("v3", "seed", "tools")` — the SAME three `extract_package._SCAN_ROOTS` already
    uses for "sweep the platform's `.py` files" — NOT the full `classify()=='package'` universe
    (`factories/`, `tests/fixtures/`, `template/`, `.claude/` are ALSO package-classified). Measured
    reason: `.claude/worktrees/` is gitignored scratch — local git worktrees background delegation spins
    up — and at least one held an OLD checkout that still contained actual copies of the dead ancestor's
    own files. A gate whose verdict depends on whether a stale, untracked worktree happens to exist on
    THIS machine at THIS moment is not reproducible, which is precisely the property this census must
    have (see "must not read git", below). `tools/` is still in scope — that is the whole point of the
    increment's own population correction (`tools/corpus_parity.py`, PASO 1's twelfth row) — it is
    `.claude/`/`factories/`/`tests/fixtures/`/`template/` that are excluded, on the same "platform code,
    not products/fixtures/scratch" reasoning `extract_package` already applied.

    (2) THE LITERAL TEST IS WHOLE-STRING AND MODULE-LEVEL ONLY, not substring-anywhere over the whole
    file. Two more measured false positives, both real code in the real tree, ruled out two weaker
    designs:
      - Substring-anywhere would flag `factories/full-stack-kotlin/codegen/{gradle_vendor,
        scaffold_product}.py`, whose module DOCSTRINGS state the ADR-012 boundary in prose (the
        factory's own scaffolding names the dead ancestor's root only to say ADR-012 forbids it from
        ever reading Kotlin/Gradle/OpenAPI concerns, and vice versa) — mentioning the ancestor's name to
        say the FACTORY never reads it is the opposite of depending on it. Requiring the WHOLE literal
        to equal or start with the root fixes this: the docstring literal starts with the module's own
        filename, not with the ancestor's root.
      - Module-level-only rules out `tools/spec_conformance.py`, which builds a differential-test
        fixture list — a `cases = [...]` list LOCAL to a function body (`run_slotlaw_suite`) — using a
        plausible-looking, ancestor-rooted sample path as one of nine strings for a law that has nothing
        to do with this census (`seed.delegation`'s footprint predicate). Every REAL dependent — every
        oracle-reader's `_V2_XXX = <ancestor-rooted path>` constant, `retirement.V2_ROOT` itself,
        `corpus_parity.PAIRS`'s `v2_sources=` tuples — is bound at MODULE level, because that is what
        "this module's law depends on this path" looks like when the dependency is real: a name the
        rest of the file's top-level code can see, not a value manufactured three stack frames into an
        unrelated test's fixture data.
    Both false positives are STRUCTURALLY indistinguishable from a real dependent by string content
    alone (the same ancestor-rooted path string is byte-identical whether it is `gate_census._V2_CLI`
    or one of `spec_conformance`'s nine sample paths) — only SCOPE (which file, which AST depth) tells
    them apart, which is why both restrictions are load-bearing rather than decorative narrowing.

THE CENSUS MUST NOT READ GIT, anywhere, for anything — this is the gate that certifies the repo CAN
leave, so a census that only runs in a repo carrying the old history certifies nothing. Existence and
`classify()` are both deterministic against the working tree alone; that is the whole proof engine.
(This is also why `deletion_manifest.population()` is deliberately NOT reused here even though it
answers a related question — that population is built by reading v2's population OUT OF THE ORACLE, and
reusing it would make this census read the one thing it cannot depend on, failing its own law on its
first run in the destination.)

NINE LAWS (each a pure `*_problems` function, each able to go red alone):
  1 DECIDED           — every population member has a row.
  2 NO STALE ROW       — a row whose module is gone from BOTH the population and the tree is legal only
                          when `decision == RETIRE` (a retirement record outlives its module; a keep may
                          not go stale unnoticed).
  3 REASON             — every row carries a written reason. Reused VERBATIM from
                          `checks.extract_package.reason_problems` — one law, one source, per the
                          contract that wrote this module.
  4 PROOF OF ABSENCE    — `retire` only: every `row.subject` path must not exist AND must not classify
                          as `'package'`. No discharge required — a not-yet-discharged retire's SUBJECT
                          claim must already hold.
  5 DISCHARGE IS NOT PROSE — `retire` AND `row.discharged` only: the named gate must not be registered,
                          and the module file must be gone.
  6 KEEP MUST STILL BE ARMED — `keep` only: `row.gate` must be non-None and registered. An unregistered
                          keep is a retirement nobody decided.
  7 NO LYING ABOUT DISCHARGE — `row.discharged == True` while the module is STILL in the population is
                          red, regardless of decision.
  8 DECISION VOCABULARY — `decision` is closed; a present `obligation` is a real (non-blank) string; a
                          discharged row carries no obligation.
  9 NO STANDING ADDRESS — a `retire` row's module may be NAMED in prose forever, but nothing in any
                          scan-root `.py` file may still hold its ADDRESS: the stem reached through a
                          dot or a slash (`v3.verify.cli_parity`, `./cli_parity`), or carrying the
                          `.py` extension (`cli_parity.py`). A bare NAME with neither form present —
                          "cli_parity was retired" — is legal; that is the whole point of the
                          distinction, and it is why this is not the same law as "the word does not
                          appear".

                          THE MEASUREMENT THAT CHOSE THE PREDICATE (2026-08-04): three candidates were
                          run against the real tree. Naive substring-of-the-stem-anywhere matched 301
                          times — it flags the stem inside unrelated identifiers and prose sentences
                          that merely discuss the retirement, drowning the 20 real citations in noise.
                          Bare-stem-word-boundary-anywhere matched 37 — an improvement, but it still
                          flags every HONEST TOMBSTONE ("`corpus_parity` was registered here until
                          V3-EXTRACT-RETIREMENT retired it"), which is legal prose and must stay legal
                          or nobody could ever again explain what a retired module used to do.
                          Address-form (this law's predicate) matched exactly 20 — every one of them a
                          real address (an import path, a `.py` reference, a relative path segment),
                          none of them a tombstone. Adopted.

                          THE GRANT SET IS EXACTLY THREE FILES, closed (`_ADDRESS_GRANT`), because
                          exactly three files are the retirement RECORD itself and have to be able to
                          say what died: `retirement.py` KEYS every row by the retired module's own
                          relpath (an address, by construction — the table cannot exist without one),
                          `retirement_census.py` documents the population correction that FOUND
                          `tools/corpus_parity.py` (this very module docstring, a few lines up), and
                          `import_boundary.py` keeps the past-tense readers table
                          (`_NAMED_NOT_READ`/`_ORACLE_READERS`) that names retired modules as former
                          consumers. No fourth file earns the grant by argument alone — a citing site
                          that is not one of these three RECORDS the death; it does not still hold the
                          address, which is exactly the thing this law refuses.

                          EXPECTED ON THE CURRENT TREE: exactly 20 citations across 12 files
                          (`corpus_parity` 14, `cli_parity` 3, `gate_census` 2, `deletion_manifest` 1)
                          — the 20 subjects are DELIBERATELY still there; rewriting them into tombstones
                          is a separate, later slot. A law proven against a tree with no standing
                          addresses would prove nothing about whether the law can find one.
PLUS the population's own sanity law (direction doc §4): every `import_boundary._ORACLE_READERS` key
must land in the derived population, or the DERIVATION itself narrowed silently.

THE DERIVATION LOCK — a POSITIVE control, not the usual "empty population is red" Lock #1. After the
next slot's rewrite the real derived population is 0 BY DESIGN (nothing depends on the dead ancestor
anymore), which would make Lock #1 fire on the intended, correct outcome — false by construction here.
So instead `derivation_control_problems` re-runs `derive_population` over a FIXED synthetic candidate
set (`_CONTROL_CANDIDATES`: a direct namer, a one-hop transitive importer, a clean module importing a
non-member, and an excluded module that names the ancestor) with a KNOWN non-empty answer
(`_CONTROL_EXPECTED`), and checks the derivation still finds exactly it. A mismatch means the
derivation itself narrowed silently — the one failure mode an always-empty real population could never
by itself reveal.

SUMMARY always prints population size, row count, `citations=N` (law 9's standing-address count), and
`open_obligations=N` with the undischarged rows' names (omitted, parentheses and all, when N is 0).
**A green with `open_obligations > 0` is the DESIGNED state, not a defect** — eight of the twelve rows
carry a deliberate, counted obligation (§0 of the increment doc); what this gate refuses is SILENCE
about them, never their existence.

RED SIDE (`V3_RETIREMENT_SABOTAGE=1`, exits 0 reporting caught) — one plant per law (nine, plus the
population sanity law, plus the derivation Lock) fed straight to the REAL pure law over synthetic
facts, each paired with a healthy-side case so a law is never trusted to reject without also being
shown NOT to reject a clean row — the same discipline `extract_package`'s own red side uses. The Lock's
own pair is the mirror image of every other law's: it must FLAG the empty control population and stay
QUIET on the correct one, because here "empty" is the failure, not the success.

Zero model; every fact is re-derived from the tree (I-3). Names no domain (ADR-012).
"""
from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

from ...extract_manifest import classify
from ...kernel.report import Verdict
from ..import_boundary import _NAMED_NOT_READ, _ORACLE_READERS
from ..retirement import DECISIONS, KEEP, RETIRE, RETIREMENT, Row, V2_ROOT
from ..suite import build_registry
from .extract_package import reason_problems

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_RETIREMENT_SABOTAGE"

#: platform scan roots — deliberately the SAME set `extract_package._SCAN_ROOTS` uses, and deliberately
#: NOT the whole `classify()=='package'` universe. See module docstring §SCAN ROOTS for the measured
#: reason (a gitignored worktree scratch directory, `.claude/worktrees/`, held a stale copy of the dead
#: ancestor and would otherwise make this gate's verdict depend on this machine's local scratch state).
_SCAN_ROOTS: tuple[str, ...] = ("v3", "seed", "tools")

#: modules allowed to NAME the ancestor without being counted as depending on it — the successor grant
#: table plus its own module, per the contract this census is built to (they dispose of the path or
#: search for it, never read it).
_EXCLUDE: frozenset[str] = frozenset(_NAMED_NOT_READ) | {"v3/verify/import_boundary.py"}

#: files allowed to hold a retired module's ADDRESS: the retirement RECORD itself. `retirement.py`
#: KEYS its rows by relpath, `retirement_census.py` documents the population correction that found
#: `tools/corpus_parity.py`, and `import_boundary.py` keeps the past-tense readers table. A record of
#: a death has to be able to say what died; nothing else does.
_ADDRESS_GRANT: frozenset[str] = frozenset({
    "v3/verify/retirement.py",
    "v3/verify/checks/retirement_census.py",
    "v3/verify/import_boundary.py",
})

_V2_NONTRAILING = V2_ROOT.rstrip("/")

#: how many failures a red verdict shows inline (mirrors `extract_package._MAX_SHOWN`).
_MAX_SHOWN = 10


# -- the pure LAWS (unit-exercised by the RED side) ---------------------------------------------------
def decided_problems(population: frozenset[str], decided: frozenset[str]) -> list[str]:
    """Law 1: every population member has a row. Pure over two precomputed sets — no `Row` needed,
    membership is the only question this law asks."""
    return sorted(f"{module!r} depends on the dead ancestor (derived population member) but has no "
                 f"row in v3.verify.retirement.RETIREMENT — a decision (retire or keep) is owed"
                 for module in population if module not in decided)


def stale_row_problems(facts: tuple[tuple[str, str, bool, bool], ...]) -> list[str]:
    """Law 2 over precomputed (module, decision, in_population, exists_in_tree) facts. A row whose
    module is neither a live population member nor present on disk may only be `retire` — a retirement
    record is meant to outlive its module; a `keep` going stale unnoticed is exactly what this catches."""
    problems = []
    for module, decision, in_population, exists in facts:
        if not in_population and not exists and decision != RETIRE:
            problems.append(f"{module!r} is neither in the derived population nor in the tree, but its "
                            f"decision is {decision!r} — only a 'retire' row may outlive its module")
    return problems


def absence_problems(facts: tuple[tuple[str, str, bool, str | None], ...]) -> list[str]:
    """Law 4 over precomputed (module, subject_path, exists, classify()'s answer) facts, `retire` rows
    only. No discharge condition: a not-yet-discharged retirement's PROOF that its subject is gone must
    already hold, or the row is a retirement extracted without proof (P7 of INC-12)."""
    problems = []
    for module, subject, exists, classification in facts:
        if exists:
            problems.append(f"{module!r} retires but its subject {subject!r} still exists in the tree")
        if classification == "package":
            problems.append(f"{module!r} retires but its subject {subject!r} still classifies as "
                            f"'package' — it would travel into the destination repo")
    return problems


def discharge_problems(facts: tuple[tuple[str, str | None, bool, bool], ...]) -> list[str]:
    """Law 5 over precomputed (module, gate, gate_still_registered, module_file_exists) facts,
    `retire and discharged` rows only. `discharged=True` is a CLAIM this checks, never trusted as a
    note — a gate still in the registry or a module file still on disk means the claim is false."""
    problems = []
    for module, gate, gate_registered, file_exists in facts:
        if gate is not None and gate_registered:
            problems.append(f"{module!r} claims discharged=True but its gate {gate!r} is still "
                            f"registered")
        if file_exists:
            problems.append(f"{module!r} claims discharged=True but its module file is still in the "
                            f"tree")
    return problems


def keep_armed_problems(facts: tuple[tuple[str, str | None, bool], ...]) -> list[str]:
    """Law 6 over precomputed (module, gate, gate_registered) facts, `keep` rows only. A keep names a
    gate and that gate must be armed — a keep with no gate, or one whose gate the suite no longer
    registers, is a retirement that happened without anybody deciding it."""
    problems = []
    for module, gate, gate_registered in facts:
        if gate is None:
            problems.append(f"{module!r} is kept but names no gate — nothing is armed on its behalf")
        elif not gate_registered:
            problems.append(f"{module!r} is kept but its gate {gate!r} is not registered — an "
                            f"unregistered keep is a retirement nobody decided")
    return problems


def discharge_lie_problems(facts: tuple[tuple[str, bool, bool], ...]) -> list[str]:
    """Law 7 over precomputed (module, discharged, in_population) facts, ALL rows. `discharged=True`
    while the module is still live in the derived population means the dependency the row claims gone
    is still there — the census's one hard line against a claim outrunning the fact."""
    return [f"{module!r} claims discharged=True but is still in the derived population — the "
           f"dependency it claims resolved is still live"
           for module, discharged, in_population in facts if discharged and in_population]


def vocabulary_problems(facts: tuple[tuple[str, str, str | None, bool], ...]) -> list[str]:
    """Law 8 over precomputed (module, decision, obligation, discharged) facts, ALL rows. Closed
    decision vocabulary; an `obligation` that is present must be an actual sentence, not a blank string
    standing in for one; a discharged row owes nothing, by construction."""
    problems = []
    for module, decision, obligation, discharged in facts:
        if decision not in DECISIONS:
            problems.append(f"{module!r} decision {decision!r} is not in retirement.DECISIONS")
        if obligation is not None and not obligation.strip():
            problems.append(f"{module!r} obligation is a blank string, not None — say nothing owed "
                            f"with None, never with silence dressed as text")
        if discharged and obligation is not None:
            problems.append(f"{module!r} is discharged=True but still carries an obligation "
                            f"({obligation[:40]!r}…) — a discharge that still owes something is a "
                            f"claim, not a fact")
    return problems


def address_pattern(stem: str) -> re.Pattern[str]:
    """Pure: the ADDRESS predicate for a retired module's `stem`, measured against three alternatives
    (module docstring §ADDRESS vs NAME) — the stem reached through a dot or a slash (`v3.verify.
    cli_parity`, `./cli_parity`), or carrying the `.py` extension (`cli_parity.py`). A bare stem with
    neither — the module's NAME alone, in prose — is deliberately NOT matched: that is the one legal
    way to still talk about a retired module."""
    return re.compile(r'(?:[./]' + re.escape(stem) + r'\b)|(?:\b' + re.escape(stem) + r'\.py\b)')


def standing_address_problems(facts: tuple[tuple[str, int, str, str], ...]) -> list[str]:
    """Law 9: NO STANDING ADDRESS. Pure over precomputed (citing_file, line_no, retired_module,
    line_excerpt) facts — one problem per fact, no filtering left to do here (every exemption, grant
    and self-citation, is already applied by `_address_facts` before a fact ever reaches this law)."""
    return [
        f"{citing_file}:{line_no}: still holds an ADDRESS for retired module {retired_module!r} "
        f"({line_excerpt.strip()!r}) — rewrite it as a past-tense tombstone that keeps the module's "
        f"NAME and drops the address; only retirement.py, retirement_census.py and import_boundary.py "
        f"may keep one"
        for citing_file, line_no, retired_module, line_excerpt in facts
    ]


def oracle_coverage_problems(oracle_reader_keys: frozenset[str], population: frozenset[str]) -> list[str]:
    """The population derivation's own sanity law (direction doc §4): every enumerated
    `import_boundary._ORACLE_READERS` key must land in the derived population. If one does not, the
    DERIVATION narrowed silently — the exact failure mode this census exists to make impossible, one
    level below the rows it decides over."""
    return sorted(f"{key!r} is an enumerated import_boundary._ORACLE_READERS key but the derivation "
                 f"does not place it in the population — the derivation itself narrowed, silently"
                 for key in oracle_reader_keys if key not in population)


# -- population derivation: pure fixpoint law + I/O gatherer, same split as `extract_package` ---------
def names_v2_root(literal: str) -> bool:
    """Pure: does `literal`, taken WHOLE, name the dead ancestor's root — exactly (with or without the
    trailing slash) or as the prefix of a longer path under it? See module docstring §2 for why this is
    whole-string rather than substring-anywhere (two real docstrings in the tree mention the root in
    prose without depending on it)."""
    return literal == V2_ROOT or literal == _V2_NONTRAILING or literal.startswith(V2_ROOT)


def _module_level_literal_match(tree: ast.Module) -> bool:
    """Pure over an already-parsed tree: does a MODULE-LEVEL statement (never inside a
    `def`/`async def`/`class`) contain a string constant naming the v2 root? See module docstring §2 for
    why this is module-level only (a real function-local fixture in the tree names a v2-shaped path as
    unrelated sample data; every genuine dependent binds the path at module level)."""
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for node in ast.walk(stmt):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and names_v2_root(node.value)):
                return True
    return False


def _import_edges(tree: ast.Module) -> tuple[tuple[str | None, int], ...]:
    """Pure over an already-parsed tree: every `from <module> import ...` statement's (module, level)
    pair, anywhere in the file. Unlike the literal test, imports are not restricted to module level —
    an import is a real dependency wherever it is written, never manufactured sample data."""
    return tuple((node.module, node.level) for node in ast.walk(tree) if isinstance(node, ast.ImportFrom))


def resolve_import(file_relpath: str, module: str | None, level: int) -> str | None:
    """Pure: where would `from <module> import ...` (written inside `file_relpath`, `level` leading
    dots) resolve to as a repo-relative `.py` path — or None if it cannot be one (a third-party absolute
    import, or a relative import reaching above the repo root). Standard relative-import arithmetic
    (PEP 328): level 1 is "this file's own package"; each further level strips one more component."""
    parts = file_relpath.split("/")
    pkg = parts[:-1]
    if level == 0:
        if not module:
            return None
        mod_components = module.split(".")
    else:
        if level - 1 > len(pkg):
            return None
        base = pkg[: len(pkg) - (level - 1)]
        mod_components = base + (module.split(".") if module else [])
    if not mod_components:
        return None
    return "/".join(mod_components) + ".py"


def derive_population(candidates: dict[str, tuple[bool, tuple[tuple[str | None, int], ...]]],
                      excluded: frozenset[str]) -> frozenset[str]:
    """THE POPULATION LAW: pure fixpoint over precomputed per-file facts (`_candidate_facts`'s output,
    module-level literal match + import-from edges) — no filesystem or AST touch of its own, the same
    split `extract_package` draws between a `*_facts` gatherer and the law that consumes it.

    A module enters two ways: (i) it names the ancestor's root directly (folded into the boolean each
    candidate carries), or (ii) it does `from <M> import ...` for some `M` ALREADY in the growing set —
    iterated to a fixpoint, which is what makes this the TRANSITIVE closure `verb_census` needs (it
    carries no literal of its own; it enters ONLY one hop from `gate_census`). `excluded` members can
    never seed OR receive membership, checked before the first pass, so a module holding a
    naming-without-depending grant can never leak population-hood to whatever imports from it either."""
    population = {path for path, (literal, _edges) in candidates.items()
                  if literal and path not in excluded}
    changed = True
    while changed:
        changed = False
        for path, (_literal, edges) in candidates.items():
            if path in population or path in excluded:
                continue
            for module, level in edges:
                if resolve_import(path, module, level) in population:
                    population.add(path)
                    changed = True
                    break
    return frozenset(population)


#: the synthetic candidate set the derivation control runs over: a direct namer, a transitive
#: importer one hop away, a clean module importing a non-member, and an excluded module that names
#: the ancestor (a grant may never seed the population, nor leak it to whoever imports it).
_CONTROL_CANDIDATES: dict[str, tuple[bool, tuple[tuple[str | None, int], ...]]] = {
    "ctl/namer.py":    (True,  ()),
    "ctl/importer.py": (False, (("ctl.namer", 0),)),
    "ctl/clean.py":    (False, (("ctl.absent", 0),)),
    "ctl/granted.py":  (True,  ()),
}
_CONTROL_EXCLUDED: frozenset[str] = frozenset({"ctl/granted.py"})
_CONTROL_EXPECTED: frozenset[str] = frozenset({"ctl/namer.py", "ctl/importer.py"})


def derivation_control_problems(derived: frozenset[str]) -> list[str]:
    """THE LOCK, a POSITIVE control (module docstring §THE DERIVATION LOCK): after the next slot the
    real derived population is 0 BY DESIGN, so the usual "empty population is red" Lock is false here —
    it would fire on the intended, correct outcome. This Lock instead re-runs `derive_population` over
    a FIXED synthetic candidate set with a known non-empty answer and checks the derivation still finds
    it: a direct namer and a one-hop transitive importer must both enter, and the excluded grant must
    neither seed nor leak population-hood to its own importer. A mismatch means the derivation itself
    narrowed silently, and a real population of 0 can no longer be read as 'nothing depends on the dead
    ancestor' — it could just as well mean nobody is looking anymore."""
    if derived == _CONTROL_EXPECTED:
        return []
    return [f"the population derivation's synthetic control produced {sorted(derived)!r}, expected "
           f"{sorted(_CONTROL_EXPECTED)!r} — the derivation itself stopped working, so a real "
           f"population of 0 can no longer be read as 'nothing depends on the dead ancestor'"]


# -- IO gatherers: every filesystem/AST touch lives here, never inside a `*_problems` law or the fixpoint
def _candidate_facts(root: Path, scan_roots: tuple[str, ...]
                     ) -> dict[str, tuple[bool, tuple[tuple[str | None, int], ...]]]:
    """Every platform `.py` file under `scan_roots` that classifies as `'package'`: its (module-level
    literal match, import-from edges) facts. No git anywhere — existence and `classify()` are both
    deterministic against the working tree alone."""
    facts: dict[str, tuple[bool, tuple[tuple[str | None, int], ...]]] = {}
    for scan_root in scan_roots:
        base = root / scan_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(root).as_posix()
            if classify(rel) != "package":
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
            except (SyntaxError, UnicodeDecodeError):
                continue
            facts[rel] = (_module_level_literal_match(tree), _import_edges(tree))
    return facts


def _address_facts(root: Path, scan_roots: tuple[str, ...], retired_modules: dict[str, str],
                   grants: frozenset[str]) -> tuple[tuple[str, int, str, str], ...]:
    """Every filesystem/text touch for law 9 lives here. Same `scan_roots` and `classify(rel) ==
    'package'` filter the population derivation already uses, `__pycache__` skipped; a file in `grants`
    is skipped whole (it may hold ANY retired module's address). The scan is over RAW TEXT, line by
    line — NOT the AST — because a comment carries an address too ("# see v3.verify.cli_parity's
    docstring"), and the AST would never see it. `retired_modules` maps each retired module's `stem` to
    its OWN relpath, so that relpath is exempt from matching its own stem (an undischarged row's module
    may still exist on disk and legitimately name itself) while still being scanned for every OTHER
    retired module's address."""
    patterns = {stem: address_pattern(stem) for stem in retired_modules}
    facts: list[tuple[str, int, str, str]] = []
    for scan_root in scan_roots:
        base = root / scan_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(root).as_posix()
            if classify(rel) != "package" or rel in grants:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for stem, own_module in sorted(retired_modules.items()):
                if rel == own_module:
                    continue
                pattern = patterns[stem]
                for line_no, line in enumerate(lines, start=1):
                    if pattern.search(line):
                        facts.append((rel, line_no, stem, line))
    return tuple(facts)


def _real_report(root: Path) -> tuple[list[str], dict[str, int], list[str]]:
    """The GREEN side over the real repo. Returns (sorted problems, summary counts, open-obligation row
    names)."""
    candidates = _candidate_facts(root, _SCAN_ROOTS)
    population = derive_population(candidates, _EXCLUDE)

    rows: dict[str, Row] = RETIREMENT
    decided_names = frozenset(rows)
    registered = frozenset(build_registry(root).names())

    reason_rows = tuple((module, row.reason) for module, row in sorted(rows.items()))
    stale_facts = tuple((module, row.decision, module in population, (root / module).exists())
                        for module, row in sorted(rows.items()))
    absence_facts = tuple(
        (module, subject, (root / subject).exists(), classify(subject))
        for module, row in sorted(rows.items()) if row.decision == RETIRE
        for subject in row.subject)
    discharge_facts = tuple(
        (module, row.gate, (row.gate in registered) if row.gate else False, (root / module).exists())
        for module, row in sorted(rows.items()) if row.decision == RETIRE and row.discharged)
    keep_facts = tuple(
        (module, row.gate, (row.gate in registered) if row.gate else False)
        for module, row in sorted(rows.items()) if row.decision == KEEP)
    lie_facts = tuple((module, row.discharged, module in population) for module, row in sorted(rows.items()))
    vocab_facts = tuple((module, row.decision, row.obligation, row.discharged)
                        for module, row in sorted(rows.items()))
    retired_modules = {Path(module).stem: module for module, row in rows.items() if row.decision == RETIRE}
    address_facts = _address_facts(root, _SCAN_ROOTS, retired_modules, _ADDRESS_GRANT)
    control_population = derive_population(_CONTROL_CANDIDATES, _CONTROL_EXCLUDED)

    problems = sorted(
        decided_problems(population, decided_names)
        + stale_row_problems(stale_facts)
        + reason_problems(reason_rows, "RETIREMENT")
        + absence_problems(absence_facts)
        + discharge_problems(discharge_facts)
        + keep_armed_problems(keep_facts)
        + discharge_lie_problems(lie_facts)
        + vocabulary_problems(vocab_facts)
        + standing_address_problems(address_facts)
        + oracle_coverage_problems(frozenset(_ORACLE_READERS), population)
        + derivation_control_problems(control_population)
    )

    open_rows = sorted(module for module, row in rows.items() if not row.discharged)
    counts = {"population": len(population), "rows": len(rows), "open_obligations": len(open_rows),
              "citations": len(address_facts)}
    return problems, counts, open_rows


# -- RED side (sabotage_env): every law must bite, and none may reject a healthy row ------------------
_SYN_REASON = "synthetic tooth scenario: a written reason long enough to be treated as a real sentence"


def _tooth_alive() -> tuple[list[str], int]:
    """(dead scenarios, scenarios run). One plant per law that can be gamed (the nine of the census's
    own contract plus the population's oracle-coverage sanity law), each paired with a healthy-side case
    — the same discipline `extract_package`'s red side uses: a law is never trusted to reject without
    also being shown it does not reject a clean row. Plus the derivation Lock's own pair (a positive
    control, so it is proven both to flag an empty derived population AND to stay quiet on the correct
    one — see `derivation_control_problems`)."""
    dead, scenarios = [], 0

    for name, condition in (
        # law 1 — DECIDED
        ("law1: a population member with no row was NOT flagged",
         not decided_problems(frozenset({"x/mod.py"}), frozenset())),
        ("law1: a decided population member WAS flagged (blocks every legitimate row)",
         bool(decided_problems(frozenset({"x/mod.py"}), frozenset({"x/mod.py"})))),
        # law 2 — NO STALE ROW
        ("law2: a stale KEEP row (module gone, decision not retire) was NOT flagged",
         not stale_row_problems((("x/mod.py", KEEP, False, False),))),
        ("law2: a stale RETIRE row (legal — a retirement outlives its module) WAS flagged",
         bool(stale_row_problems((("x/mod.py", RETIRE, False, False),)))),
        ("law2: a LIVE row (still in the population and the tree) WAS flagged",
         bool(stale_row_problems((("x/mod.py", KEEP, True, True),)))),
        # law 3 — REASON, reused verbatim from extract_package
        ("law3: a vacuous reason was NOT flagged",
         not reason_problems((("x/mod.py", "too short"),), "RETIREMENT")),
        ("law3: a properly-written reason WAS flagged (blocks every legitimate row)",
         bool(reason_problems((("x/mod.py", _SYN_REASON),), "RETIREMENT"))),
        # law 4 — PROOF OF ABSENCE
        ("law4: a retire whose subject STILL EXISTS was NOT flagged",
         not absence_problems((("x/mod.py", "dead-ancestor/subject.py", True, None),))),
        ("law4: a retire whose subject still classifies as 'package' was NOT flagged",
         not absence_problems((("x/mod.py", "dead-ancestor/subject.py", False, "package"),))),
        ("law4: a genuinely absent, non-package subject WAS flagged (blocks every real retirement)",
         bool(absence_problems((("x/mod.py", "dead-ancestor/subject.py", False, None),)))),
        # law 5 — DISCHARGE IS NOT PROSE
        ("law5: a discharged retire whose gate is STILL REGISTERED was NOT flagged",
         not discharge_problems((("x/mod.py", "some_gate", True, False),))),
        ("law5: a discharged retire whose module file STILL EXISTS was NOT flagged",
         not discharge_problems((("x/mod.py", None, False, True),))),
        ("law5: a genuinely discharged retire (gate gone, file gone) WAS flagged",
         bool(discharge_problems((("x/mod.py", "some_gate", False, False),)))),
        # law 6 — KEEP MUST STILL BE ARMED
        ("law6: a keep whose gate is NOT REGISTERED was NOT flagged",
         not keep_armed_problems((("x/mod.py", "some_gate", False),))),
        ("law6: a keep naming NO GATE AT ALL was NOT flagged",
         not keep_armed_problems((("x/mod.py", None, False),))),
        ("law6: a keep whose gate IS registered WAS flagged",
         bool(keep_armed_problems((("x/mod.py", "some_gate", True),)))),
        # law 7 — NO LYING ABOUT DISCHARGE
        ("law7: a discharged row STILL IN THE POPULATION was NOT flagged",
         not discharge_lie_problems((("x/mod.py", True, True),))),
        ("law7: an honestly discharged row (gone from the population) WAS flagged",
         bool(discharge_lie_problems((("x/mod.py", True, False),)))),
        # law 8 — DECISION VOCABULARY
        ("law8: an unknown decision word was NOT flagged",
         not vocabulary_problems((("x/mod.py", "delete", None, False),))),
        ("law8: a blank-string obligation (not None) was NOT flagged",
         not vocabulary_problems((("x/mod.py", RETIRE, "   ", False),))),
        ("law8: a discharged row STILL CARRYING AN OBLIGATION was NOT flagged",
         not vocabulary_problems((("x/mod.py", RETIRE, "still owed", True),))),
        # law 9 — NO STANDING ADDRESS
        ("law9: a standing-address citation in a non-granted file was NOT flagged",
         not standing_address_problems(
             (("x/citer.py", 1, "cli_parity", "see v3.verify.cli_parity's docstring"),))),
        ("law9: a clean (empty) fact tuple WAS flagged (a law that rejects everything blocks every "
         "file)",
         bool(standing_address_problems(()))),
        # the population derivation's own sanity assertion
        ("oracle-coverage: a missing oracle-reader key was NOT flagged",
         not oracle_coverage_problems(frozenset({"x/mod.py"}), frozenset())),
        ("oracle-coverage: a covered oracle-reader key WAS flagged",
         bool(oracle_coverage_problems(frozenset({"x/mod.py"}), frozenset({"x/mod.py"})))),
        # the derivation Lock — a POSITIVE control, so it must fire on empty and stay quiet on correct
        ("lock: an EMPTY control-derived population was NOT flagged (an empty real population would "
         "then be unreadable as evidence of anything)",
         not derivation_control_problems(frozenset())),
        ("lock: the CORRECT control-derived population WAS flagged (blocks every real run)",
         bool(derivation_control_problems(_CONTROL_EXPECTED))),
        # the increment's own close criterion, combined: a fully sane row is never marked by anything
        ("healthy: a fully sane row was flagged by SOMETHING (blocks every legitimate census)",
         bool(decided_problems(frozenset({"x/mod.py"}), frozenset({"x/mod.py"}))
             + stale_row_problems((("x/mod.py", RETIRE, True, True),))
             + reason_problems((("x/mod.py", _SYN_REASON),), "RETIREMENT")
             + absence_problems((("x/mod.py", "dead-ancestor/subject.py", False, None),))
             + discharge_problems((("x/mod.py", "some_gate", False, False),))
             + keep_armed_problems((("x/mod.py", "some_gate", True),))
             + discharge_lie_problems((("x/mod.py", True, False),))
             + vocabulary_problems((("x/mod.py", RETIRE, None, True),))
             + standing_address_problems(())
             + derivation_control_problems(_CONTROL_EXPECTED))),
    ):
        scenarios += 1
        if condition:
            dead.append(name)
    return dead, scenarios


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-retirement-census", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        dead, scenarios = _tooth_alive()
        if dead:
            return Verdict("v3-retirement-census (SABOTAGE)", 1,
                           f"GATE DECORATIVO: the law does not bite in {len(dead)}/{scenarios} "
                           f"synthetic scenario(s)", failures=tuple(dead)).emit()
        return Verdict("v3-retirement-census (SABOTAGE)", 0,
                       f"all {scenarios} synthetic scenarios (one plant per law, hole side and "
                       f"healthy side) resolved as the law requires",
                       counts={"scenarios": scenarios}).emit()

    problems, counts, open_rows = _real_report(_ROOT)
    if problems:
        return Verdict("v3-retirement-census", 1,
                       f"{len(problems)} retirement-census problem(s) over {counts['population']} "
                       f"population module(s) and {counts['rows']} decided row(s)",
                       failures=tuple(problems[:_MAX_SHOWN]), counts=counts,
                       next_action="decide the undecided module in v3/verify/retirement.py — retire "
                                   "it with proof of absence, or keep it with an armed gate; and for "
                                   "any standing-address citation, rewrite the citing site as a "
                                   "past-tense tombstone that keeps the retired module's NAME and "
                                   "drops its address — never loosen a law, and never widen the grant "
                                   "set, to make either kind of problem disappear").emit()

    open_obligations = f"open_obligations={counts['open_obligations']}"
    if open_rows:
        open_obligations += f" ({', '.join(open_rows)})"
    return Verdict("v3-retirement-census", 0,
                   f"{counts['population']} population module(s), {counts['rows']} decided row(s), "
                   f"citations={counts['citations']}, {open_obligations}",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
