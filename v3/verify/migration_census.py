#!/usr/bin/env python3
"""migration_census — what can v3 actually RUN, and what is still owed to which increment?

    python3 -m v3.verify.migration_census
    V3_MIGRATION_CENSUS_SABOTAGE=1 python3 -m v3.verify.migration_census   # red side; exits 0

THE FAILURE THIS PREVENTS is the one INC-7 is most exposed to. "Port what the migrated line needs"
is a correct policy and a perfect hiding place: the line goes green, the pin matches, and the twelve
kinds and seven build actions that were NOT ported are indistinguishable from kinds and actions that
do not exist. `gate_census` asks that question about v2's gates and `v3.economy.census` about v2's
economy; this one asks it about the migration itself.

NOTHING HERE IS A TYPED TABLE, and that is the design. Every fact is derived:

  * the KIND population  — `v3.verify.kinds.KINDS`, the frozen vocabulary itself;
  * a kind's EXECUTOR    — by resolving a REAL check declared in a REAL station YAML through
                           `resolve_check`, so the argv under test is the argv that would run;
  * the ACTION population— v2's own `apply_builds` read at the oracle commit (ADR-031 §2.1), the
                           same technique and the same reason as `gate_census`;
  * what v3 HANDLES      — parsed out of `v3.host.builds`'s own source, so a claim here cannot
                           outlive the `elif` it describes;
  * who OWES it          — the factories whose lines declare it, mapped to their migration
                           increment, so the answer re-computes itself as `MIGRATED` grows.

THE TOOTH, in one sentence: **anything a MIGRATED factory's line exercises must be ported.** A kind
or an action that a line v3 claims to run is still owed to a later increment is a contradiction, not
a deferral — the line either does not really run, or the census is fiction. That check is what turns
"we ported what dummy needed" from an assertion into a re-derivable fact, and it is what will go red
the moment INC-8 adds `iot` to `MIGRATED` before porting what `iot` uses.

FOUR DISPOSITIONS, none of them assigned by hand:
  ported       the executor module is on disk / the action appears in `apply_builds`
  no_body      the argv targets stdlib or carries no module at all (`py_compile`, `-c`, pass-through)
  deferred     not ported, and owed to the increment that migrates the earliest factory declaring it
  unexercised  in the vocabulary and declared by no FACTORY line — reported, never hidden

THE POPULATION IS THE CHASSIS, AND IT USED TO BE MORE THAN THAT (narrowed V3-INC9). The scan is
`factories/*/stations/*.yml` — one line per factory. It was `factories/*/**/stations/*.yml`, which
also swept each product instance's materialized `stations/`, and that was wrong twice over. It is
wrong about v3: every target's line, default or instance, is loaded from the CHASSIS (R1 — the
station structure belongs to the factory, only the blueprint differs), so the chassis stations are
the complete and only source of what v3 can be asked to execute. And it is wrong about EVIDENCE:
an instance's `stations/` is gitignored, written by v2's CLI before a run, so the recursive glob made
this gate's verdict depend on what a previous local run happened to leave behind.

That was not hypothetical. `full-stack-kotlin`'s chassis `s6.yml` declares `render`; the copy v2
materialized under `products/*/stations/s6.yml` declares `write` (the two are the same operation —
same `render_text` — under two names). With the recursive glob this gate reported that a MIGRATED
factory exercises an action `apply_builds` does not handle, and it reported it from an UNTRACKED
file, for a line v3 never loads. On a clean clone the same commit would have said something else —
which is the defect `N-0102` names for `evidence_liveness`, in a second instrument.

WHAT `unexercised` REALLY MEANS, because the word is doing a lot of work. It is not the whole story: v2 also
runs a META line (`m00`…`m07`) whose stations declare `column_full`, `docs_check`, `clean_runner`,
`rtm_*` and friends. That line has no v3 analogue yet (INC-4's `kind_hygiene` says the same thing
about the same files), so those kinds are unexercised BY A FACTORY and very much exercised by v2.
Reporting them apart rather than folding them into `deferred` keeps the two questions distinct: "who
still owes me an executor" and "what is not part of a product line at all".
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

from ..kernel.report import Verdict
from .kinds import KINDS, resolve_check
from .rederive import MIGRATED

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent
_ORACLE_REF = _V3 / "oracle_ref.json"
_V2_RENDERER = "src/metafactory/codegen/renderer.py"
_BUILD_PLAN = "docs/spec/11-build-plan.md"
_V3_BUILDS = _V3 / "host" / "builds.py"

PORTED, NO_BODY, DEFERRED, UNEXERCISED = "ported", "no_body", "deferred", "unexercised"

#: Which increment migrates which factory — §11.3's own assignment, and the only literal here. Each
#: target is verified to be a real row in the build plan at the oracle ref, so a typo becomes a red
#: rather than a deferral pointing at nothing.
OWNER: dict[str, str] = {
    "dummy": "INC-7", "iot": "INC-8", "full-stack-kotlin": "INC-9",
    "agent-systems-factory": "INC-10", "full-stack": "INC-10",
}
_ORDER = {"INC-7": 7, "INC-8": 8, "INC-9": 9, "INC-10": 10}


def _git(*args: str) -> str:
    out = subprocess.run(["git", *args], cwd=_ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        raise FileNotFoundError(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out.stdout


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


def declared_actions(root: Path) -> dict:
    """action -> set of factory slugs whose lines declare it."""
    found: dict = {}
    for path in sorted(root.glob("factories/*/stations/*.yml")):
        slug = path.relative_to(root).parts[1]
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        for build in data.get("builds") or ():
            action = str(build.get("action", ""))
            if action:
                found.setdefault(action, set()).add(slug)
    return found


def v2_actions(ref: str) -> set:
    """v2's build-action vocabulary, read out of `apply_builds` at the oracle commit."""
    src = _git("show", f"{ref}:{_V2_RENDERER}")
    start = src.index("def apply_builds(")
    body = src[start + 1:]
    body = body[:body.index("\ndef ")] if "\ndef " in body else body
    return set(re.findall(r'action == "([a-z_]+)"', body))


def v3_actions() -> set:
    """What `v3.host.builds` really handles — parsed from its own source, so the census cannot
    describe an `elif` that is not there."""
    src = _V3_BUILDS.read_text(encoding="utf-8")
    single = set(re.findall(r'action == "([a-z_]+)"', src))
    tupled = re.findall(r'action in \(([^)]*)\)', src)
    for group in tupled:
        single |= set(re.findall(r'"([a-z_]+)"', group))
    return single


def _executor(kind: str, sample) -> tuple[str, str]:
    """(disposition, evidence) for one kind, from the argv its REAL declared check resolves to."""
    check, station = sample
    argv = resolve_check(check, None, station, {"slug": "dummy"})
    target = argv[2] if len(argv) > 2 and argv[1] == "-m" else ""
    if not target.startswith("v3."):
        return NO_BODY, target or "no module target (-c / pass-through)"
    module = Path(target.replace(".", "/") + ".py")
    return (PORTED if (_ROOT / module).exists() else DEFERRED), module.as_posix()


def _owed_to(slugs) -> str:
    """The increment that owes this: the EARLIEST migration among the factories that declare it."""
    targets = [OWNER[s] for s in slugs if s in OWNER]
    return min(targets, key=lambda t: _ORDER.get(t, 99)) if targets else ""


def check(ref: str, *, sabotage: str = "") -> tuple[list[str], dict]:
    problems: list[str] = []
    plan = _git("show", f"{ref}:{_BUILD_PLAN}")
    checks, actions = declared_checks(_ROOT), declared_actions(_ROOT)
    handled, v2set = v3_actions(), v2_actions(ref)
    migrated = set(MIGRATED)

    # The three plants, and what each perturbs — every one moves a value that is NON-EMPTY in the
    # clean run, because a sabotage that empties something already empty proves nothing (INC-5).
    if sabotage == "phantom_action":
        # `v3.host.builds` claims an action v2 never had. Perturbs `handled - v2set`: 0 -> 1.
        handled = handled | {"emit_hologram"}
    if sabotage == "unported_but_migrated":
        # Claim a factory is migrated whose line needs things v3 has not ported. `iot` is the WRONG
        # choice here and trying it is how this was found: iot declares only `infra_up`/`product_env`
        # /`generate`, all of which INC-7 already ported, so the plant changed nothing. FSK declares
        # `write` (no handler) and `eval_gate` (no executor). Perturbs the contradiction count: 0 -> 2.
        migrated = migrated | {"full-stack-kotlin"}
    if sabotage == "empty_population":
        # Lock #1: a census over zero declared checks must be RED, never vacuously true. Perturbs the
        # population itself: 10 kinds -> 0. Dropping ONE kind (the first draft) does not bite — it
        # just moves that kind to `unexercised`, which is a legitimate disposition.
        checks = {}

    counts = {"kinds": len(KINDS), "actions": len(v2set), PORTED: 0, NO_BODY: 0,
              DEFERRED: 0, UNEXERCISED: 0}
    for kind in sorted(KINDS):
        where = checks.get(kind) or {}
        if not where:
            counts[UNEXERCISED] += 1
            continue
        disposition, evidence = _executor(kind, next(iter(where.values())))
        counts[disposition] += 1
        exercised_by_migrated = sorted(migrated & set(where))
        if disposition == DEFERRED:
            owed = _owed_to(where)
            if not owed:
                problems.append(f"kind {kind}: not ported ({evidence} absent) and declared by no "
                                f"factory with a migration increment — owed to nobody")
            elif f"**{owed}**" not in plan:
                problems.append(f"kind {kind}: owed to {owed}, which is not a row in the build plan")
            if exercised_by_migrated:
                problems.append(f"kind {kind}: exercised by MIGRATED factory/factories "
                                f"{exercised_by_migrated} and its executor {evidence} does not "
                                f"exist — the line cannot really be running")

    for action in sorted(v2set):
        where = actions.get(action) or set()
        if action in handled:
            continue
        exercised_by_migrated = sorted(migrated & where)
        if exercised_by_migrated:
            problems.append(f"build action {action!r}: exercised by MIGRATED factory/factories "
                            f"{exercised_by_migrated} and `v3.host.builds` does not handle it")
        owed = _owed_to(where)
        if where and not owed:
            problems.append(f"build action {action!r}: declared by {sorted(where)} and owed to nobody")
        if owed and f"**{owed}**" not in plan:
            problems.append(f"build action {action!r}: owed to {owed}, not a row in the build plan")

    for action in sorted(handled - v2set):
        problems.append(f"build action {action!r}: handled by `v3.host.builds` but absent from v2's "
                        f"vocabulary at {ref[:8]} — paperwork for something that never existed")

    if not checks:
        problems.append("ZERO checks declared across the repo's station YAMLs: an empty population "
                        "is never vacuously true (Lock #1)")
    counts["handled_actions"] = len(handled)
    counts["factory_actions"] = len(set(actions) & v2set)
    return problems, counts


_CLASSES = ("phantom_action", "unported_but_migrated", "empty_population")
_SIGNATURE = {"phantom_action": "never existed",
              "unported_but_migrated": "does not handle it",
              "empty_population": "Lock #1"}


def _run_sabotage(ref: str) -> int:
    control, _ = check(ref)
    if control:
        return Verdict("v3-migration-census (SABOTAGE)", 1,
                       f"the census is not clean, so no catch is attributable: {control[0]}").emit()
    caught = []
    for name in _CLASSES:
        problems, _ = check(ref, sabotage=name)
        if any(_SIGNATURE[name] in p for p in problems):
            caught.append(name)
    if len(caught) == len(_CLASSES):
        return Verdict("v3-migration-census (SABOTAGE)", 0,
                       f"{len(caught)}/{len(_CLASSES)} planted defect(s) caught "
                       f"({', '.join(caught)})").emit()
    missed = [c for c in _CLASSES if c not in caught]
    return Verdict("v3-migration-census (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {len(caught)}/{len(_CLASSES)} caught "
                   f"({', '.join(caught) or 'none'}) — missed {missed}").emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-migration-census", 2, f"takes no arguments; got {argv!r}").emit()
    import json
    ref = json.loads(_ORACLE_REF.read_text(encoding="utf-8"))["oracle_ref"]

    if os.environ.get("V3_MIGRATION_CENSUS_SABOTAGE") == "1":
        return _run_sabotage(ref)

    problems, counts = check(ref)
    if problems:
        return Verdict("v3-migration-census", 1,
                       f"{len(problems)} contradiction(s) between what v3 claims to run and what it "
                       f"has ported", counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-migration-census", 0,
                   f"kinds {counts[PORTED]} ported · {counts[NO_BODY]} no-body · {counts[DEFERRED]} "
                   f"owed to a later migration · {counts[UNEXERCISED]} in no FACTORY line; build "
                   f"actions {counts['handled_actions']} handled of {counts['factory_actions']} that "
                   f"factory lines declare ({counts['actions']} in v2's vocabulary); everything "
                   f"{sorted(MIGRATED)} exercises is ported", counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
