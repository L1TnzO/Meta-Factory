#!/usr/bin/env python3
"""Where did each of v2's 23 gates go? — the count that has to add up.

    python3 -m v3.verify.gate_census                              # the gate
    V3_GATE_CENSUS_SABOTAGE=1 python3 -m v3.verify.gate_census    # the red side; must ALSO exit 0

THE FAILURE THIS EXISTS TO PREVENT. The recurring bug in this project has one shape: *something
looks green because nobody asked what was left out of the count*. A port is the richest possible
soil for it — twenty-three gates go in, nineteen come out, the suite reports nineteen greens, and
the four that were quietly not mentioned are indistinguishable from four that never existed.

So the list of v2 gates is NOT typed here. It is DERIVED from v2's own source read at
`oracle_ref` (ADR-031 §2.1: the oracle is a commit, never the working tree — v2 and v3 share a
tree, and a census measured against uncommitted state counts whatever was lying around). Every
derived gate must carry EXACTLY ONE disposition, and every disposition must name a gate that
really is in that list. Both directions, because each catches a different lie: the first catches
a gate that was dropped in silence, the second catches paperwork for a gate that never existed.

FOUR DISPOSITIONS, each verified against something re-derivable rather than asserted:

  PORTED      → the name is registered in v3's gate registry, which already refuses a gate with no
                red witness — so "ported" cannot quietly mean "copied without its tooth".
  ALREADY     → the named v3 module is on disk; the gate exists here under another shape.
  DROPPED     → the spec's own retirement clause is found AT THE ORACLE REF. If a future spec
                changes its mind, the census goes red instead of quietly agreeing with itself.
  DEFERRED    → the target increment is a real row in §11.3 at the ref, and the trigger is stated.

WHAT THIS GATE DOES NOT CLAIM. It counts dispositions; it does not judge the quality of a port.
"Registered" means the registry accepted it, which means it declared a reachable red witness — not
that the witness still bites. That is P2's job (§11.2), re-run per gate, and it is criterion 4 of
this increment rather than a line in this file. A census that also claimed to measure strength
would be the same over-claim it was written to catch.

It stays RED until INC-4 finishes, because it IS INC-4's acceptance test. The FAILURES tell the
two cases apart: `pending` is work remaining, anything else is a census that does not add up.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ..kernel.report import Verdict

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent
_ORACLE_REF = _V3 / "oracle_ref.json"
_V2_CLI = "src/metafactory/cli.py"
_BUILD_PLAN = "docs/spec/11-build-plan.md"

PORTED, ALREADY, DROPPED, DEFERRED = "ported", "already-in-v3", "dropped", "deferred"


@dataclass(frozen=True)
class Row:
    disposition: str
    evidence: str   # module path (ALREADY) · target increment (DEFERRED) · retirement phrase (DROPPED)
    why: str = ""


# The 23 rows. The KEYS are checked against v2's source; the VALUES are this increment's judgement.
DISPOSITIONS: dict[str, Row] = {
    # ── ported: 15 by INC-4, plus INC-5's corpus gates as each one LANDS ─────
    "compile": Row(PORTED, ""), "isolation": Row(PORTED, ""), "generality": Row(PORTED, ""),
    "quality": Row(PORTED, ""), "pbt": Row(PORTED, ""), "security": Row(PORTED, ""),
    "deferred": Row(PORTED, ""), "benchmark": Row(PORTED, ""), "dial": Row(PORTED, ""),
    "roles": Row(PORTED, ""), "kinds": Row(PORTED, ""), "codegen_freeze": Row(PORTED, ""),
    "plan": Row(PORTED, ""), "design_eval": Row(PORTED, ""), "suite": Row(PORTED, ""),

    # INC-5 Fase 2. This row moves out of the deferred block HERE and not a moment earlier: a row
    # that claims PORTED while its gate is unregistered is reported `pending` and turns this census
    # red, so the promise cannot be written before the landing.
    "docs": Row(PORTED, ""), "projection": Row(PORTED, ""), "evidence_liveness": Row(PORTED, ""),

    # ── already in v3 under another shape (2) ───────────────────────────────
    "least_priv": Row(ALREADY, "v3/verify/composition.py",
                      "INC-2 rebuilt it as a set assertion over one registry instead of a "
                      "comparison between copies"),
    "slot_footprint": Row(ALREADY, "v3/verify/slot_footprint.py", "INC-3, with its live-slot case"),

    # ── retired by the spec itself (1) ──────────────────────────────────────
    "column_parity": Row(DROPPED, "no copies left to compare",
                         "§11.4 retires it: under composition the column exists once, so a "
                         "parity check between copies has nothing to compare"),

    # ── deferred, with a trigger (2 left; the STATE teeth, INC-5 Fase 5) ────
    "state_snapshot": Row(DEFERRED, "INC-5", "§11.3 assigns the STATE teeth to INC-5; its subject "
                                             "is the doc corpus that is INC-5's fixture"),
    "state_fidelity": Row(DEFERRED, "INC-5", "same subject, and it reads STATE through "
                                             "state_snapshot"),
}


def _oracle() -> dict:
    return json.loads(_ORACLE_REF.read_text(encoding="utf-8"))


def _show(ref: str, path: str) -> str:
    out = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True, cwd=_ROOT)
    if out.returncode != 0:
        raise FileNotFoundError(f"{path} @ {ref}: {out.stderr.strip()}")
    return out.stdout


def v2_gates(ref: str) -> list[str]:
    """v2's gate list, read out of `cmd_check` at the oracle commit.

    Bounded to that function's body on purpose: a `{"name": ...}` literal elsewhere in a 2k-line
    CLI would inflate the census with something that was never a gate.
    """
    src = _show(ref, _V2_CLI)
    start = src.index("def cmd_check(")
    rest = src[start + 1:]
    end = rest.index("\ndef ") if "\ndef " in rest else len(rest)
    body = rest[:end]
    return re.findall(r'\{"name":\s*"([a-z_]+)"', body)


def _registered() -> tuple[set[str], str]:
    """The names v3's registry accepted. Absent suite ⇒ empty set, said out loud."""
    try:
        from .suite import build_registry   # noqa: PLC0415 — optional until phase 6 lands
    except ImportError:
        return set(), "v3/verify/suite.py does not exist yet: no gate is registered"
    return set(build_registry(_ROOT).names()), ""


def _ref_binding_problems() -> list[str]:
    """The price of this module's rule-3 exemption in `import_boundary`: prove the read is a
    function of the COMMIT, not of the tree.

    A working-tree read would succeed whatever ref it was handed. This one must fail at a ref that
    does not exist — which is also why it survives INC-11 deleting v2: history does not move.
    """
    bogus = "0" * 40
    try:
        _show(bogus, _V2_CLI)
    except FileNotFoundError:
        return []
    return [f"{_V2_CLI} was readable at a nonexistent ref: the census is reading the working tree, "
            f"so its exemption from the v2-import boundary is not earned"]


def check(ref: str, *, sabotage: bool = False) -> tuple[list[str], dict]:
    problems: list[str] = []
    rows = dict(DISPOSITIONS)
    if sabotage:
        # v2's actual situation: the census lives in a documentation table. Stop mentioning one
        # gate, invent paperwork for another, and see whether anything notices.
        rows.pop("codegen_freeze", None)
        rows["phantom_gate"] = Row(PORTED, "")

    declared = v2_gates(ref)
    if len(declared) != len(set(declared)):
        problems.append("v2's own gate list has a duplicate name — the source of truth is ambiguous")
    v2 = set(declared)
    if not v2:
        problems.append(f"derived ZERO gates from {_V2_CLI} @ {ref[:8]}: an empty oracle is never "
                        f"vacuously true (Lock #1)")

    for name in sorted(v2 - set(rows)):
        problems.append(f"{name}: in v2's gate list and in NO disposition — this is the shape of "
                        f"the bug this gate exists to catch")
    for name in sorted(set(rows) - v2):
        problems.append(f"{name}: has a disposition but is not a v2 gate at {ref[:8]} — paperwork "
                        f"for something that does not exist")

    problems.extend(_ref_binding_problems())

    registered, note = _registered()
    counts = {"v2": len(v2), "declared": len(rows), "landed": 0, "pending": 0}
    plan = _show(ref, _BUILD_PLAN)

    for name in sorted(set(rows) & v2):
        row = rows[name]
        if row.disposition == PORTED:
            if name in registered:
                counts["landed"] += 1
            else:
                counts["pending"] += 1
        elif row.disposition == ALREADY:
            if not (_ROOT / row.evidence).exists():
                problems.append(f"{name}: declared already-in-v3 at {row.evidence}, which is not there")
        elif row.disposition == DROPPED:
            if row.evidence not in plan:
                problems.append(f"{name}: declared dropped on the strength of «{row.evidence}», a "
                                f"phrase absent from {_BUILD_PLAN} @ {ref[:8]}")
        elif row.disposition == DEFERRED:
            if f"**{row.evidence}**" not in plan:
                problems.append(f"{name}: deferred to {row.evidence}, which is not a row in the "
                                f"build plan @ {ref[:8]}")
            if not row.why.strip():
                problems.append(f"{name}: deferred with no reason — a deferral with no trigger is "
                                f"a drop that has not admitted it yet")
        else:
            problems.append(f"{name}: unknown disposition {row.disposition!r}")

    if counts["pending"] and note:
        problems.append(note)
    for name in sorted(n for n, r in rows.items() if r.disposition == PORTED and n not in registered):
        problems.append(f"{name}: pending — declared ported, not registered")

    return problems, counts


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-gate-census", 2, f"takes no arguments; got {argv!r}").emit()
    ref = _oracle()["oracle_ref"]

    if os.environ.get("V3_GATE_CENSUS_SABOTAGE") == "1":
        problems, _ = check(ref, sabotage=True)
        caught = [p for p in problems if "NO disposition" in p or "not a v2 gate" in p]
        if len(caught) >= 2:
            return Verdict("v3-gate-census (SABOTAGE)", 0,
                           "a dropped gate and an invented one were both caught").emit()
        return Verdict("v3-gate-census (SABOTAGE)", 1,
                       f"GATE DECORATIVO: the census did not notice ({len(caught)}/2 caught)").emit()

    problems, counts = check(ref)
    if problems:
        return Verdict("v3-gate-census", 1,
                       f"{counts['landed']}/{counts['landed'] + counts['pending']} ported gates "
                       f"landed; {len(problems)} open item(s)", counts=counts,
                       failures=tuple(problems),
                       next_action="pending = work remaining; anything else = the census does not add up"
                       ).emit()
    return Verdict("v3-gate-census", 0,
                   f"all {counts['v2']} of v2's gates accounted for: {counts['landed']} ported, "
                   f"and every other disposition verified against the oracle", counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
