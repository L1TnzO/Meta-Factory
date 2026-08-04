#!/usr/bin/env python3
"""migration_census — what can v3 actually RUN, and what is still owed to which increment?

    python3 -m v3.verify.migration_census
    V3_MIGRATION_CENSUS_SABOTAGE=1 python3 -m v3.verify.migration_census   # red side; exits 0

THE FAILURE THIS PREVENTS is the one INC-7 is most exposed to. "Port what the migrated line needs"
is a correct policy and a perfect hiding place: the line goes green, the pin matches, and a kind that
was NOT ported is indistinguishable from a kind that does not exist. This census asks that question
about the migration itself.

THE KIND POPULATION IS DERIVED, never a typed table:

  * the KIND population  — `v3.verify.kinds.KINDS`, the frozen vocabulary itself;
  * a kind's EXECUTOR    — by resolving a REAL check declared in a REAL station YAML through
                           `resolve_check`, so the argv under test is the argv that would run.

THE TOOTH, in one sentence: **anything a MIGRATED factory's line exercises must be ported.** A kind
that a line v3 claims to run is still owed to a later increment is a contradiction, not a deferral —
the line either does not really run, or the census is fiction. That check is what turns "we ported
what dummy needed" from an assertion into a re-derivable fact, and it is what will go red the moment
a future factory is added to `MIGRATED` before porting what it uses.

RETIRED (V3-EXTRACT-OBLIGATIONS phase 3): the ACTION side — v2's own `apply_builds` build-action
vocabulary, read at the oracle commit (ADR-031 §2.1) and diffed against what `v3.host.builds`
handles and what factory lines declare, plus the "owed to an increment that is a real build-plan
row" check that leaned on the same oracle read. `check()` no longer takes a `ref` or shells to `git`
at all, and this module's `_ORACLE_READERS` exemption in `import_boundary` is gone with it.

FOUR DISPOSITIONS, none of them assigned by hand:
  ported       the executor module is on disk
  no_body      the argv targets stdlib or carries no module at all (`py_compile`, `-c`, pass-through)
  deferred     not ported
  unexercised  in the vocabulary and declared by no FACTORY line — reported, never hidden

THE POPULATION IS THE CHASSIS, AND IT USED TO BE MORE THAN THAT (narrowed V3-INC9). The scan is
`factories/*/stations/*.yml` — one line per factory. It was `factories/*/**/stations/*.yml`, which
also swept each product instance's materialized `stations/`, and that was wrong twice over. It is
wrong about v3: every target's line, default or instance, is loaded from the CHASSIS (R1 — the
station structure belongs to the factory, only the blueprint differs), so the chassis stations are
the complete and only source of what v3 can be asked to execute. And it is wrong about EVIDENCE:
an instance's `stations/` is gitignored, written by v2's CLI before a run, so the recursive glob made
this gate's verdict depend on what a previous local run happened to leave behind.

That was not hypothetical: an earlier draft of this census also scanned the ACTION side this way
(the recursive glob picking up an UNTRACKED materialized `stations/` from a previous local run) and
reported a false contradiction from a file no line v3 loads — the defect `N-0102` names for
`evidence_liveness`, in a second instrument. The action side itself retired with V3-EXTRACT-OBLIGATIONS
phase 3 (see above); the scan-root lesson stays, because `declared_checks` below still uses it.

WHAT `unexercised` REALLY MEANS, because the word is doing a lot of work. It is not the whole story: v2 also
runs a META line (`m00`…`m07`) whose stations declare `column_full`, `docs_check`, `clean_runner`,
`rtm_*` and friends. That line has no v3 analogue yet (INC-4's `kind_hygiene` says the same thing
about the same files), so those kinds are unexercised BY A FACTORY and very much exercised by v2.
Reporting them apart rather than folding them into `deferred` keeps the two questions distinct: "who
still owes me an executor" and "what is not part of a product line at all".
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

from ..kernel.report import Verdict
from .kinds import KINDS, resolve_check
from .rederive import MIGRATED

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent

PORTED, NO_BODY, DEFERRED, UNEXERCISED = "ported", "no_body", "deferred", "unexercised"


def declared_checks(root: Path) -> dict:
    """kind -> {factory slug -> one real check dict}. The population every resolution is made from."""
    found: dict = {}
    for path in sorted(root.glob("factories/*/stations/*.yml")):
        slug = path.relative_to(root).parts[1]
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        for check in data.get("checks") or ():
            kind = str(check.get("kind", ""))
            if kind:
                found.setdefault(kind, {}).setdefault(slug, (check, data))
    return found


def _executor(kind: str, sample) -> tuple[str, str]:
    """(disposition, evidence) for one kind, from the argv its REAL declared check resolves to."""
    check, station = sample
    argv = resolve_check(check, None, station, {"slug": "dummy"})
    target = argv[2] if len(argv) > 2 and argv[1] == "-m" else ""
    if not target.startswith("v3."):
        return NO_BODY, target or "no module target (-c / pass-through)"
    module = Path(target.replace(".", "/") + ".py")
    return (PORTED if (_ROOT / module).exists() else DEFERRED), module.as_posix()


def check(*, sabotage: str = "") -> tuple[list[str], dict]:
    """B2 (a kind a MIGRATED factory's line really exercises must have a real executor) and B5
    (Lock #1 over the kind population). `sabotage` plants one named defect class, used only by the
    red side — every plant moves a value that is NON-EMPTY in the clean run (INC-5)."""
    problems: list[str] = []
    checks = declared_checks(_ROOT)
    migrated = set(MIGRATED)

    if sabotage == "empty_population":
        # Lock #1: a census over zero declared checks must be RED, never vacuously true. Perturbs the
        # population itself: N kinds -> 0. Dropping ONE kind (the first draft) does not bite — it
        # just moves that kind to `unexercised`, which is a legitimate disposition.
        checks = {}

    counts = {"kinds": len(KINDS), PORTED: 0, NO_BODY: 0, DEFERRED: 0, UNEXERCISED: 0}
    for kind in sorted(KINDS):
        where = checks.get(kind) or {}
        if not where:
            counts[UNEXERCISED] += 1
            continue
        disposition, evidence = _executor(kind, next(iter(where.values())))
        exercised_by_migrated = sorted(migrated & set(where))
        if sabotage == "kind_executor_missing" and exercised_by_migrated and disposition == PORTED:
            # THE MISSING-EXECUTOR PLANT: take a kind a MIGRATED factory's line really declares and
            # whose executor really exists, and force its computed disposition to `deferred` — the
            # contradiction under test is "a line v3 claims to run needs something v3 does not have",
            # reached in-memory, never by touching a file on disk.
            disposition = DEFERRED
        counts[disposition] += 1
        if disposition == DEFERRED and exercised_by_migrated:
            problems.append(f"kind {kind}: exercised by MIGRATED factory/factories "
                            f"{exercised_by_migrated} and its executor {evidence} does not "
                            f"exist — the line cannot really be running")

    if not checks:
        problems.append("ZERO checks declared across the repo's station YAMLs: an empty population "
                        "is never vacuously true (Lock #1)")
    return problems, counts


_CLASSES = ("kind_executor_missing", "empty_population")
_SIGNATURE = {"kind_executor_missing": "does not exist", "empty_population": "Lock #1"}


def _run_sabotage() -> int:
    control, _ = check()
    if control:
        return Verdict("v3-migration-census (SABOTAGE)", 1,
                       f"the census is not clean, so no catch is attributable: {control[0]}").emit()
    caught: list[str] = []
    missed: list[str] = []
    for name in _CLASSES:
        problems, _ = check(sabotage=name)
        (caught if any(_SIGNATURE[name] in p for p in problems) else missed).append(name)

    print(f"PLANTS caught={caught} na=[] missed={missed}")
    if missed:
        return Verdict("v3-migration-census (SABOTAGE)", 1,
                       f"GATE DECORATIVO: {len(caught)}/{len(_CLASSES)} caught "
                       f"({', '.join(caught) or 'none'}) — missed {missed}").emit()
    return Verdict("v3-migration-census (SABOTAGE)", 0,
                   f"{len(caught)}/{len(_CLASSES)} planted defect(s) caught "
                   f"({', '.join(caught)})").emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-migration-census", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get("V3_MIGRATION_CENSUS_SABOTAGE") == "1":
        return _run_sabotage()

    problems, counts = check()
    if problems:
        return Verdict("v3-migration-census", 1,
                       f"{len(problems)} contradiction(s) between what v3 claims to run and what it "
                       f"has ported", counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-migration-census", 0,
                   f"kinds {counts[PORTED]} ported · {counts[NO_BODY]} no-body · {counts[DEFERRED]} "
                   f"deferred · {counts[UNEXERCISED]} in no FACTORY line", counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
