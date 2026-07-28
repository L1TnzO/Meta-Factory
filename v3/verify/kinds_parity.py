#!/usr/bin/env python3
"""Does the PORTED kind-argv mapping (`v3.verify.kinds`) reproduce v2's, at a pinned commit?

    python3 -m v3.verify.kinds_parity                              # the gate
    V3_KINDS_PARITY_SABOTAGE=1 python3 -m v3.verify.kinds_parity   # the red side; must ALSO exit 0

THE OUTER ORACLE IS READ AT A COMMIT (ADR-031 §2.1): `v3/oracle_ref.json` names the pinned ref v2
was walked at, read the same plain way `v3.verify.parity._oracle()` reads it. This gate's INNER
fixture (`docs/spec/fixtures/check-argv-vectors.json`) is different from that gate's: it is generated
BY this increment (`tools/gen_check_argv_vectors.py`), so — unlike `proof-sha-vectors.json`, which
predates the increment that reads it and so has real history at the ref — it has no existence at
`oracle_ref` to `git show` (that commit predates it by construction). Reading it from disk is the
honest move for THIS artifact, and the ref-binding law (ADR-031 §2.1) is enforced a different way:
the fixture's own `oracle_ref` field must equal `v3/oracle_ref.json`'s pinned value, so a fixture
regenerated against the wrong ref — or left stale after the ref moves on — goes red rather than
silently comparing against the wrong past. `_ref_binding_problems` below proves that check actually
binds to the ref it is handed, not merely to "whatever is on disk" — see LOCK #2.

WHAT IS COMPARED. For every recorded vector, `kinds.resolve_check` is called with the vector's own
`check`/`subst_keys`, and the result must equal the vector's `argv` EXACTLY after normalisation.
NOTHING is masked or blanked — every argv position, for every kind, is compared byte-for-byte,
including the executor position that names which module runs the kind's check (24 of the 29 kinds
carry one; see `v3.verify.kinds`'s "THE PORT RULE"). Two normalisations apply, both to BOTH sides:
  (a) the interpreter (`sys.executable`) and this repo's own absolute root are environment-dependent
      (they differ by machine) and are replaced by `<PY>` / `<ROOT>` — the same rule the fixture
      generator applies when it records a vector (`tools/gen_check_argv_vectors.py`).
  (b) the ORACLE side's argv is HEAD-SWAPPED before comparing: any token whose first dotted segment
      equals the fixture's own `v2_package` field (never a string hardcoded in this module — see
      LAW below) has that segment replaced with `v3`. `kinds.resolve_check` already emits the
      swapped form directly (it hardcodes `v3.verify.checks.<name>` / `v3.spec.cli` / `v3.cli`), so
      after this swap the two sides are compared as plain equal strings — proving the mapping
      "which v3 module runs kind X" is exactly what the port rule says it must be, not a masked
      region that would stay green under ANY routing.

LAW (why this needs no import-boundary exemption). `_swap_head` reads `v2_package` out of the
fixture's own JSON — a VALUE it compares tokens against, never a string this module writes down or
dereferences (no `importlib`, no dynamic `__import__`, no path built from it). `v3.verify.import_boundary`
rule 3 exists to catch a string that could hide an import or a path injection; a value read from data
purely to decide "does this token's head match, and if so rewrite it" does neither. So this module
carries no `_ORACLE_READERS` exemption and needs none — `import_boundary` (and its sabotage side)
stay green over it unmodified.

LOCK #1: zero vectors at the oracle ref is RED, never a vacuous green — an empty fixture would let
every kind pass by never being asked to prove anything.

LOCK #2 (REF-BINDING): reading the fixture at a nonexistent ref (40 zeros) must FAIL. A read that
merely opened whatever file happens to be on disk would succeed no matter which ref it was asked
for; this gate's honesty depends on the read being a function of the ref, not of the tree, so this
case is exercised on every run (not only under sabotage).

COVERAGE, reported apart from correctness: every one of the 29 KINDS must have >=1 vector (real or
synthetic), and the synthetic count is a COUNTS field, never folded into "real" silently.

An unknown kind must raise ValueError (construction-time guard, `kinds.py:` last line) — checked
directly here, since a truncated fixture would otherwise never exercise that branch.

SABOTAGE: reroutes ONE kind's check to a DIFFERENT kind's executor module — the exact failure mode
the masked version of this gate could not have caught (a routing bug hiding behind a blanked
position). It finds two vectors whose swapped argv name two DIFFERENT `v3.*` executors, and
overwrites the first vector's raw executor token with the second's, so after the (correct) swap is
applied the tampered vector claims kind A's check runs kind B's module. If the comparison still
passed, it would be measuring nothing over the one position that matters most.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from ..kernel.report import Verdict
from .kinds import KINDS, resolve_check

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent
_ORACLE_REF = _V3 / "oracle_ref.json"
_FIXTURE = _ROOT / "docs" / "spec" / "fixtures" / "check-argv-vectors.json"

_BOGUS_REF = "0" * 40


def _oracle() -> dict:
    return json.loads(_ORACLE_REF.read_text(encoding="utf-8"))


def _load_fixture(ref: str) -> dict:
    """Read the fixture from disk (it has no history at `ref` to `git show` — see module docstring)
    and enforce the ref-binding the other way round: its OWN provenance stamp must name the SAME
    pinned commit, so a fixture built against a different or now-stale ref is caught rather than
    silently compared against the wrong past."""
    if not _FIXTURE.exists():
        raise FileNotFoundError(f"{_FIXTURE}: not generated yet (tools/gen_check_argv_vectors.py)")
    fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    stamped = fixture.get("oracle_ref")
    if stamped != ref:
        raise ValueError(f"fixture stamps oracle_ref={stamped!r}, pinned ref is {ref!r} — "
                         f"regenerate with tools/gen_check_argv_vectors.py")
    return fixture


def _ref_binding_problems() -> list[str]:
    """LOCK #2. A working-tree read would succeed at any ref; this one must fail at a ref that
    cannot be the pinned commit (40 zeros), proving the fixture read is bound to the ref it is
    handed, not to "whatever is on disk"."""
    try:
        _load_fixture(_BOGUS_REF)
    except (FileNotFoundError, ValueError):
        return []
    return ["_load_fixture succeeded at a nonexistent ref (40 zeros) — the fixture read is not "
            "ref-bound, it just opens whatever is on disk"]


def _normalize(argv: list) -> list[str]:
    """The same two environment-dependent substitutions the generator applies when recording a
    vector: this process's own interpreter, and this repo's own absolute root (same file-depth trick
    as `kinds._this_repo_root`, so both sides agree on what "root" means without either naming v2)."""
    py = sys.executable
    root = str(Path(__file__).resolve().parents[2])
    out = []
    for tok in argv:
        tok = str(tok)
        tok = tok.replace(py, "<PY>")
        tok = tok.replace(root, "<ROOT>")
        out.append(tok)
    return out


def _swap_head(token: str, v2_package: str) -> str:
    """Head-segment swap: v2's package name, first dotted segment, becomes `v3` — see module
    docstring's LAW and `kinds.py`'s "THE PORT RULE". `v2_package` is always a VALUE read from the
    fixture's own provenance, never a literal this module writes down."""
    if token == v2_package:
        return "v3"
    prefix = v2_package + "."
    if token.startswith(prefix):
        return "v3." + token[len(prefix):]
    return token


def _apply_swap(argv: list, v2_package: str) -> list[str]:
    return [_swap_head(str(tok), v2_package) for tok in argv]


def _executor_pos(argv: list, v2_package: str) -> int | None:
    """Where, if anywhere, this vector's RAW argv names a v2-package-rooted executor. Derived, not
    assumed at a fixed index — some kinds carry none at all (`py_compile`, `command`, ...)."""
    prefix = v2_package + "."
    for i, tok in enumerate(argv):
        s = str(tok)
        if s == v2_package or s.startswith(prefix):
            return i
    return None


def _sabotage_reroute(vectors: list[dict], v2_package: str) -> str | None:
    """Corrupt ONE vector in place: overwrite its raw executor token with a DIFFERENT kind's raw
    executor token, so after the (correct) swap the tampered vector claims its check runs the WRONG
    module. Returns a description of what was done, or None if the fixture has fewer than two
    distinct executor-bearing kinds to reroute between (a precondition failure, reported as a
    problem by the caller — not silently skipped)."""
    executors: list[tuple[int, int, str]] = []  # (vector_index, raw_pos, swapped_value)
    for vi, vector in enumerate(vectors):
        raw = list(vector["argv"])
        pos = _executor_pos(raw, v2_package)
        if pos is None:
            continue
        executors.append((vi, pos, _swap_head(str(raw[pos]), v2_package)))

    distinct_values = {swapped for _, _, swapped in executors}
    if len(distinct_values) < 2:
        return None

    victim_vi, victim_pos, victim_val = executors[0]
    donor_vi = donor_pos = None
    for vi, pos, swapped in executors:
        if swapped != victim_val:
            donor_vi, donor_pos = vi, pos
            break
    assert donor_vi is not None  # guaranteed by the len(distinct_values) >= 2 check above

    victim = dict(vectors[victim_vi])
    victim_argv = list(victim["argv"])
    donor_argv = vectors[donor_vi]["argv"]
    victim_argv[victim_pos] = donor_argv[donor_pos]
    victim["argv"] = victim_argv
    vectors[victim_vi] = victim
    return (f"rerouted {vector_kind(vectors[victim_vi])!r}'s executor to "
            f"{vector_kind(vectors[donor_vi])!r}'s module")


def vector_kind(vector: dict) -> str:
    return str(vector.get("kind", "?"))


def check(ref: str, *, sabotage: bool = False) -> tuple[list[str], dict]:
    """The LAW: recompute every vector with the ported `resolve_check`, compare to the oracle."""
    problems: list[str] = []
    problems.extend(_ref_binding_problems())

    fixture = _load_fixture(ref)
    vectors = [dict(v) for v in fixture.get("vectors", [])]
    v2_package = fixture.get("v2_package")
    counts = {"vectors": len(vectors), "real": 0, "synthetic": 0, "kinds_covered": 0}

    if not vectors:
        problems.append("zero vectors at the oracle ref — a green here would be vacuous (Lock #1)")
        return problems, counts

    if not v2_package:
        problems.append("fixture has no v2_package provenance — cannot apply the head-segment swap "
                        "(regenerate with tools/gen_check_argv_vectors.py)")
        return problems, counts

    if sabotage:
        done = _sabotage_reroute(vectors, v2_package)
        if done is None:
            problems.append("sabotage precondition failed: fewer than 2 distinct executor-bearing "
                            "kinds in the fixture to reroute between")
            return problems, counts

    seen_kinds: set[str] = set()
    for vector in vectors:
        kind = vector.get("kind")
        seen_kinds.add(kind)
        counts["synthetic" if vector.get("synthetic") else "real"] += 1

        station = SimpleNamespace(id=vector.get("station", "?"))
        try:
            got = resolve_check(dict(vector["check"]), None, station, dict(vector["subst_keys"]))
        except Exception as exc:  # noqa: BLE001 — any failure to resolve is a parity failure, not a crash
            problems.append(f"{vector.get('origin', '?')}/{kind}: resolve_check raised {exc!r}")
            continue

        got_n = _normalize(list(got))
        want_n = _normalize(_apply_swap(list(vector["argv"]), v2_package))
        if got_n != want_n:
            problems.append(f"{vector.get('origin', '?')}/{kind}: argv mismatch\n"
                            f"    got:  {got_n}\n    want: {want_n}")

    missing = sorted(set(KINDS) - seen_kinds)
    if missing:
        problems.append(f"{len(missing)} kind(s) with zero vectors in the fixture: {', '.join(missing)}")
    counts["kinds_covered"] = len(seen_kinds & set(KINDS))

    # Construction-time guard: an unknown kind must raise ValueError naming KINDS.
    try:
        resolve_check({"kind": "totally_unknown_kind_xyz"}, None, SimpleNamespace(id="probe"), {})
        problems.append("resolve_check accepted an unknown kind instead of raising ValueError")
    except ValueError:
        pass

    return problems, counts


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-kinds-parity", 2, f"takes no arguments; got {argv!r}").emit()

    ref = _oracle()["oracle_ref"]

    if os.environ.get("V3_KINDS_PARITY_SABOTAGE") == "1":
        problems, counts = check(ref, sabotage=True)
        if problems:
            return Verdict("v3-kinds-parity (SABOTAGE)", 0,
                           f"the rerouted executor was detected: {len(problems)} deviation(s)",
                           counts=counts).emit()
        return Verdict("v3-kinds-parity (SABOTAGE)", 1,
                       "GATE DECORATIVO: an executor rerouted to a different kind's module still "
                       "matched", counts=counts).emit()

    problems, counts = check(ref)
    if problems:
        return Verdict("v3-kinds-parity", 1,
                       f"{len(problems)} deviation(s) over {counts['vectors']} vector(s) @ {ref[:12]}",
                       counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-kinds-parity", 0,
                   f"{counts['vectors']} vector(s) ({counts['real']} real, {counts['synthetic']} "
                   f"synthetic) reproduce v2's argv across all {len(KINDS)} kinds @ {ref[:12]}, "
                   f"executors included (no masked positions)",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
