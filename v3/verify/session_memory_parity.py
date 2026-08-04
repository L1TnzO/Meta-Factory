#!/usr/bin/env python3
"""session_memory_parity — do the PORTED session-memory bodies (`v3.memory.precompact`,
`v3.memory.rehydrate` — what the `PreCompact` and `SessionStart` hooks call) derive the same FACTS
v2's did, at the pinned oracle commit?

    python3 -m v3.verify.session_memory_parity                                    # the gate
    V3_SESSION_MEMORY_PARITY_SABOTAGE=1 python3 -m v3.verify.session_memory_parity  # red side; must ALSO exit 0

PINNED, AND THE ORACLE HALF IS GONE (V3-EXTRACT-OBLIGATIONS phase 2). Phase 1 fossilised the oracle's 13
fact-sets into the committed `v3/verify/pins/session_memory_parity.json`, with the provenance proved
WHILE the ancestor still existed (see the increment doc's §Evidencia). This module never shells to
`git`, and after this phase it carries no code path that could any more: it loads the pin, checks its
five laws (`oracle_parity.pin_problems`), and compares v3's LIVE fact-sets (`_live_answers`, driven the
same `--drive` way) against it (`oracle_parity.compare_to_pin`). There is no re-derivation flag left — a
re-pin performed without the oracle would be exactly the undetectable failure this increment exists to
prevent. The accounting for the pin AS A SET now lives in `v3.verify.checks.pin_integrity`, not here —
this module speaks only for its own 13 cases. The KEY SPACE is per FUNCTION×CASE (e.g.
`build_snapshot:open_increment`), 13 entries.

COMPARE FACTS, NOT PROSE. The port is English where v2 is Spanish (ADR-017) — `precompact.py` carries
no user-facing prose at all (it is pure structured data), but `rehydrate.build_payload` RETURNS a
rendered banner, section headers and an orientation line, and those are deliberately translated. A
literal string comparison of the two payloads would go RED for a perfectly correct port, for no reason
other than the language of a label — the wrong instrument for what this witness needs to prove. So for
every function this module derives a FACT-SET from each side's own answer and compares THAT:

  `build_snapshot`   the returned dict's KEYS, and the VALUE of every field except `ts` (a live
                     wall-clock stamp — `store.now()`/v2's own `journal.now()` — that cannot compare
                     equal between two separate calls even for an identical port; its PRESENCE as a key
                     is still checked, only its value is excluded).
  `write_snapshot`   the return contract (`None` vs a path, reduced to a bool) + whether bytes actually
                     LANDED on disk — checked directly against the filesystem after the call, not
                     inferred from the return value (that is precisely the shape SABOTAGE plant #2
                     exploits: a `write_snapshot` that returns success while writing nothing).
  `record`           that the call did not raise, plus the FACT the journal itself now carries (its own
                     last line, `ts` excluded) — read directly off `.metamem/journal.jsonl` after the
                     call, never inferred from `record`'s return value (`-> None` on both sides, so the
                     return contract alone would prove nothing).
  `build_payload`    five facts regex-extracted from the rendered string, tolerant of EITHER language:
                     does it name the same open increment (or the same absence)? the same SET of
                     "- "-prefixed projection lines (RTM + open-increment, as persisted in
                     `docs/STATE.md` — see the SCOPE note below for why this is safe to compare even
                     without re-deriving RTM live)? does the STATE «Ahora» section appear? the same
                     COUNT of journal-tail lines (structural: a 2-space-indented ISO timestamp, matched
                     by shape, never by the label above it)? and are the orientation pointers
                     (`` `meta check` ``, `` `meta checkpoint` ``, `grep -rn`) present — command names,
                     never translated, so this one fact IS safe to string-match directly.

SCOPE, and why the phase-1 oracle package was much smaller than it looked like it should be.
`precompact._gates()`'s `rtm` sub-field and `rehydrate.build_payload`'s projection lines BOTH ultimately
trace back to RTM, but through two DIFFERENT mechanisms with two different costs:
  - `rehydrate.current_block` only ever READS the projection block ALREADY PERSISTED in `docs/STATE.md`
    (a regex slice — `meta checkpoint` is what refreshes that block; `rehydrate` never re-derives RTM
    live). Since every fixture below writes the IDENTICAL `docs/STATE.md` text into BOTH the oracle's
    and the ported side's physical root, this fact is safe and cheap to exercise with real, non-trivial
    content, and needs nothing beyond a text file.
  - `precompact._gates()`'s `rtm_status(root)` call DOES re-derive RTM live — v2's `rtm_statuses` opens
    with `from ..engine.run_context import RunContext` and `from ..spec import load_spec`, BEFORE its
    own early return for a root with no `factories/` directory. Making that import resolve for real
    would drag in v2's `engine` package — `engine/__init__.py` re-exports `Station`/`Sequence`/
    `GateResult`/`run_station`, and `runner.py` alone imports `..verify.checks.registry.resolve_check`,
    which imports EVERY v2 check module including `memory.projection` itself. That is not a bounded
    oracle extraction for one function; it is most of v2's engine.
  So this witness never gives `build_snapshot` a root with a `factories/` directory. `_gates()` wraps
  its `rtm_status` call in `try/except Exception: rtm = []` (both v2's body and this port's, byte for
  byte) — so on every fixture here BOTH sides take that same branch, for the same underlying reason
  (v2's oracle hits the missing `engine` package and degrades; the port's `v3.spec.loader` import
  succeeds but returns `{}` immediately at the `facdir.exists()` check) and land on the identical `[]`.
  `build_snapshot`'s `rtm` field is still compared (empty == empty is still a real comparison — LAW #3
  below), it is simply never the field that carries this witness's diversity; `open_increment`,
  `plan.{objective,phases_done,phases_total}` and `gates.{active_station,recompute_green}` carry it
  instead (see the LOCK matrix). The one payload-side fact that DOES need real RTM content —
  `build_payload`'s "- "-prefixed projection lines — gets it for free from a fixture `docs/STATE.md`,
  without touching `rtm_statuses` at all.
  Symmetrically, `rehydrate.build_payload` is NEVER driven with `source="compact"`: that is the ONE
  branch that would call `precompact.surface_for_rehydrate` for something other than an early return,
  and this port's `precompact.py` deliberately does not carry that function (see
  `v3/memory/precompact.py`'s own docstring — the slot contract restricts it to what the `PreCompact`
  hook calls). Driving `source="compact"` would ask a fact of the port that the port was never asked to
  answer.
  Neither of these is a gap this witness hides: both are why every `build_payload` fixture below is a
  DISPOSABLE temp directory, never the live working tree — this module never risks writing a stray
  `session_start` journal event into this repo's own `.metamem/`.

ORACLE READERS, RETIRED. This module used to name six v2 substrate paths, read at `oracle_ref` via
`git show` inside an `_ORACLE_READERS` carve-out — that reading code, the carve-out, and the throwaway
package it built are gone (V3-EXTRACT-OBLIGATIONS phase 2). `v3.verify.checks.pin_integrity`'s travel
probe is what now certifies no path back to the ancestor survives anywhere in this file.

LOCK: the PIN must hold at least `_MIN_DISTINCT_ANSWERS` distinct canonical fact-sets — the count
MEASURED at pin time — across its 13 answers; fewer would mean the comparison could pass by
coincidence. Enforced by `oracle_parity.pin_problems` (law 4), over the fossil rather than a live
oracle run.

SABOTAGE plants ONE defect per function targeted, in a COPY of the ported body read off disk — never
the real file — and asserts its LIVE fact-set, over the SAME real matrix case that function's plant
targets, no longer matches the PIN:
  * `build_payload_drop_increment` (rehydrate) — the `lines.append(f"Open increment: ...")` line
    becomes a no-op. Caught by `build_payload:open_increment_no_state` (the fact goes from "found" to
    "not found").
  * `write_snapshot_fake_success` (precompact) — an unconditional `return p` is inserted right after
    `p = snapshot_path(root)`, before the actual write — "report success without writing", per the
    slot contract. Caught by `write_snapshot:valid_writable` because `landed` (checked against the
    filesystem, never the return value) stays False while the return value claims success.
  * `build_snapshot_drop_increment` (precompact) — `inc = open_increment(root)` becomes `inc = None`
    unconditionally. Caught by `build_snapshot:open_increment`.
  * `pin_answer_corrupted` — an in-memory COPY of the pin gets ONE answer perturbed; `compare_to_pin`
    against v3's real (unpatched) live answers must report it.
  * `pin_case_dropped` — an in-memory COPY of the pin has ONE case's answer removed; `pin_problems` must
    report the bijection break.
A plant that finds nothing to perturb in the on-disk source raises `CannotPlant`, reported N/A beside
the caught/missed count, never folded into a catch (INC-5's law, INC-8's fix, re-used unchanged). The
sabotage side runs the PATCHED module inside a SHADOW copy of the small `v3/` subtree these two files
depend on, copied from the WORKING TREE (never git) — `v3/spec/` is deliberately excluded from that
subtree for the identical reason the phase-1 oracle package excluded it (the SCOPE note above): every
sabotage fixture also has no `factories/` directory, so `_gates()`'s try/except degrades `rtm` to `[]`
on the shadow copy exactly as it does on the real one. No oracle is built for SABOTAGE any more: each
plant reuses the SAME case builder the real matrix (and therefore the pin) was measured over, so its
fixture's content genuinely matches the key `compare_to_pin` looks up.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from . import oracle_parity as harness
from ..kernel.report import Verdict
from ..memory.precompact import SCHEMA as _SCHEMA

_V3 = harness.V3_DIR
_ROOT = harness.ROOT_DIR

#: the ported bodies this gate judges, and the files their source is read from for the sabotage plants.
_PORTED_PRECOMPACT_PATH = _V3 / "memory" / "precompact.py"
_PORTED_REHYDRATE_PATH = _V3 / "memory" / "rehydrate.py"

#: `.metamem/precompact.json` — the SAME path both sides write (v2 unchanged on purpose; see
#: `v3/memory/precompact.py`'s own docstring).
_SNAP_REL = Path(".metamem") / "precompact.json"

#: this gate's registered name — the pin file is `v3/verify/pins/<_PIN_GATE>.json`.
_PIN_GATE = "session_memory_parity"

#: distinct canonical fact-sets the pin's 13 answers hold, MEASURED at pin time
#: (V3-EXTRACT-OBLIGATIONS §2.2 law 4) — fewer would mean the comparison could pass by coincidence.
_MIN_DISTINCT_ANSWERS = 12


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# THE DRIVER TEMPLATE — shared source for the SABOTAGE shadow's `_driver.py` (`_PORTED_DRIVER_SRC`
# below); there is no oracle side left to build any more (V3-EXTRACT-OBLIGATIONS phase 2)
# ══════════════════════════════════════════════════════════════════════════════════════════════════
_ORACLE_DRIVER_SRC = '''\
import json, sys
from pathlib import Path


def main(argv):
    which, args_json = argv[0], argv[1]
    args = json.loads(args_json)
    try:
        if which == "build_snapshot":
            from oraclepkg.memory import precompact
            result = precompact.build_snapshot(Path(args[0]), session=args[1], trigger=args[2])
        elif which == "write_snapshot":
            from oraclepkg.memory import precompact
            r = precompact.write_snapshot(Path(args[0]), args[1])
            result = {"is_none": r is None}
        elif which == "record":
            from oraclepkg.memory import precompact
            precompact.record(Path(args[0]), args[1], written=bool(args[2]))
            result = {"called": True}
        elif which == "build_payload":
            from oraclepkg.memory import rehydrate
            payload = rehydrate.build_payload(Path(args[0]), session=args[1], source=args[2])
            result = {"payload": payload}
        else:
            print(json.dumps({"ok": False, "error": f"unknown case {which}"}))
            return 0
        print(json.dumps({"ok": True, "result": result}))
    except Exception as exc:  # the driver itself must never crash silently
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

# ══════════════════════════════════════════════════════════════════════════════════════════════════
# THE PORTED SIDE, NORMAL RUN: this file's own `--drive` mode, over the REAL working tree
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _drive(rest: list[str]) -> int:
    """`python3 -m v3.verify.session_memory_parity --drive <function> <json-args>`."""
    if len(rest) != 2:
        print(json.dumps({"ok": False, "error": f"--drive needs exactly 2 args, got {rest!r}"}))
        return 0
    which, args_json = rest
    try:
        args = json.loads(args_json)
        if which == "build_snapshot":
            from ..memory import precompact
            result = precompact.build_snapshot(Path(args[0]), session=args[1], trigger=args[2])
        elif which == "write_snapshot":
            from ..memory import precompact
            r = precompact.write_snapshot(Path(args[0]), args[1])
            result = {"is_none": r is None}
        elif which == "record":
            from ..memory import precompact
            precompact.record(Path(args[0]), args[1], written=bool(args[2]))
            result = {"called": True}
        elif which == "build_payload":
            from ..memory import rehydrate
            payload = rehydrate.build_payload(Path(args[0]), session=args[1], source=args[2])
            result = {"payload": payload}
        else:
            print(json.dumps({"ok": False, "error": f"unknown case {which}"}))
            return 0
        print(json.dumps({"ok": True, "result": result}))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
    return 0


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# THE PORTED SIDE, SABOTAGE RUN: a shadow copy of the small subtree, one file patched
# ══════════════════════════════════════════════════════════════════════════════════════════════════
_PORTED_DRIVER_SRC = _ORACLE_DRIVER_SRC.replace("oraclepkg.memory", "v3.memory")

#: relative path (under a shadow `v3/`) -> real file it is copied from, unless it is the ONE patched.
#: `v3/spec/` is deliberately absent — see the module docstring's SCOPE section.
_SHADOW_FILES: dict[str, Path] = {
    "__init__.py": _V3 / "__init__.py",
    "seed_loader.py": _V3 / "seed_loader.py",
    "economy/__init__.py": _V3 / "economy" / "__init__.py",
    "economy/store.py": _V3 / "economy" / "store.py",
    "memory/__init__.py": _V3 / "memory" / "__init__.py",
    "memory/journal.py": _V3 / "memory" / "journal.py",
    "memory/projection.py": _V3 / "memory" / "projection.py",
    "memory/docs_manifest.py": _V3 / "memory" / "docs_manifest.py",
    "memory/precompact.py": _PORTED_PRECOMPACT_PATH,
    "memory/rehydrate.py": _PORTED_REHYDRATE_PATH,
    "verify/__init__.py": _V3 / "verify" / "__init__.py",
}


def _build_shadow_v3(dest_root: Path, *, patched_rel: str, patched_src: str) -> Path:
    root = dest_root / "v3"
    for rel, real_path in _SHADOW_FILES.items():
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = patched_src if rel == patched_rel else real_path.read_text(encoding="utf-8")
        dest.write_text(text, encoding="utf-8")
    (root / "verify" / "_driver.py").write_text(_PORTED_DRIVER_SRC, encoding="utf-8")
    return dest_root


def _plant_build_payload_drop_increment(src: str) -> str:
    target = '    lines.append(f"Open increment: {open_increment(root) or \'none\'}")\n'
    if target not in src:
        raise harness.CannotPlant("build_payload's open-increment line was not found in the ported "
                                  "body on disk")
    return src.replace(target, "    pass  # SABOTAGE: open-increment line dropped\n", 1)


def _plant_write_snapshot_fake_success(src: str) -> str:
    target = "    p = snapshot_path(root)\n    try:\n"
    if target not in src:
        raise harness.CannotPlant("write_snapshot's write body was not found in the ported body on disk")
    return src.replace(
        target, "    p = snapshot_path(root)\n    return p  # SABOTAGE: fake success, no write\n    try:\n", 1)


def _plant_build_snapshot_drop_increment(src: str) -> str:
    target = "        inc = open_increment(root)\n"
    if target not in src:
        raise harness.CannotPlant("build_snapshot's open_increment call was not found in the ported "
                                  "body on disk")
    return src.replace(target, "        inc = None  # SABOTAGE: forced\n", 1)


#: plant_name -> (patched_rel under shadow v3/, real path read for the source, plant fn, function judged)
_PLANTS: dict[str, tuple[str, Path, Callable[[str], str], str]] = {
    "build_payload_drop_increment": ("memory/rehydrate.py", _PORTED_REHYDRATE_PATH,
                                     _plant_build_payload_drop_increment, "build_payload"),
    "write_snapshot_fake_success": ("memory/precompact.py", _PORTED_PRECOMPACT_PATH,
                                    _plant_write_snapshot_fake_success, "write_snapshot"),
    "build_snapshot_drop_increment": ("memory/precompact.py", _PORTED_PRECOMPACT_PATH,
                                      _plant_build_snapshot_drop_increment, "build_snapshot"),
}


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# FIXTURES: shared builders
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _open_increment_doc(d: Path, *, phases_done: int = 1, phases_total: int = 2) -> str:
    """Writes `docs/work/OPEN.md` with an open header + `## Objetivo` + a `## Fases` table (the SAME
    Spanish section headers v2's `_increment_plan` regex targets — the doc corpus is not translated,
    CLAUDE.md's own rule). Returns the filename."""
    wd = d / "docs" / "work"
    wd.mkdir(parents=True, exist_ok=True)
    rows = [f"| {i + 1} | thing {i + 1} | gate | {'✅' if i < phases_done else ''} |"
            for i in range(phases_total)]
    text = (
        "# Test increment\n\n"
        "> Status: **OPEN**\n\n"
        "## Objetivo\n"
        "Do the fixture thing.\n\n"
        "## Fases\n"
        "| Fase | Contenido | Gate | Estado |\n"
        "| --- | --- | --- | --- |\n"
        + "\n".join(rows) + "\n\n"
        "## Criterio de cierre\n"
        "done\n"
    )
    (wd / "OPEN.md").write_text(text, encoding="utf-8")
    return "OPEN.md"


def _write_state_md(d: Path, *, inc_line: str, rtm_line: str) -> None:
    """A `docs/STATE.md` carrying BOTH a `## Ahora` section and a live `meta:projection` block —
    the SAME markers `v3.memory.projection.START`/`END` (and v2's own, byte-identical at oracle_ref)
    define, so `current_block` finds it regardless of which side reads this file."""
    text = (
        "# STATE\n\n"
        "<!-- meta:projection (generated from facts; do NOT hand-edit, refreshed by "
        "`meta checkpoint`) -->\n"
        "> Fact projection (Tier 0 -> STATE). Source: re-derivable artifacts; not narrative.\n"
        f"- Open increment: {inc_line}\n"
        f"- RTM by factory (re-derived from `.proof/`): {rtm_line}\n"
        "<!-- /meta:projection -->\n\n"
        "## Ahora — what is true today\n"
        "- fixture fact one\n"
        "- fixture fact two\n\n"
        "## Map\n"
        "- nothing else\n"
    )
    (d / "docs").mkdir(parents=True, exist_ok=True)
    (d / "docs" / "STATE.md").write_text(text, encoding="utf-8")


def _write_journal_entries(d: Path, *, n: int) -> None:
    p = d / ".metamem" / "journal.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"ts": f"2026-08-01T00:00:{i:02d}Z", "kind": "note", "text": f"fixture {i}"})
             for i in range(n)]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _proof_sha(station: str, checks: list[dict]) -> str:
    """Mirrors `seed/verifier.py.compute_proof_sha` — FIXTURE construction, not a re-derivation of the
    column's law: this witness needs a proof whose sha genuinely recomputes clean to exercise the
    "trust" branch at all."""
    canonical = {"station": station, "checks": sorted([(str(c["name"]), int(c["exit"])) for c in checks])}
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def _write_proof(proof_root: Path, station: str, checks: list[dict], *, tamper: bool = False) -> None:
    proof_dir = proof_root / ".proof"
    proof_dir.mkdir(parents=True, exist_ok=True)
    passed = len(checks) > 0 and all(int(c["exit"]) == 0 for c in checks)
    proof = {"station": station, "checks": checks, "passed": passed, "proof_sha": _proof_sha(station, checks)}
    if tamper:
        proof["proof_sha"] = "0" * 64  # deliberately wrong -> gate_recompute_ok must reject it
    (proof_dir / f"{station}.json").write_text(json.dumps(proof), encoding="utf-8")


def _write_active(root: Path, proof_root: Path, station: str) -> None:
    proof_dir = root / ".proof"
    proof_dir.mkdir(parents=True, exist_ok=True)
    (proof_dir / "active.json").write_text(
        json.dumps({"root": str(proof_root), "station": station}), encoding="utf-8")


def _fixture_snap(*, session: str = "s1", trigger: str = "manual", increment: str | None = "OPEN.md") -> dict:
    """A well-formed `precompact/1` snapshot, built directly (not via `build_snapshot`) so
    `write_snapshot`/`record` cases can drive them with EXACT, controlled content."""
    return {
        "schema": _SCHEMA,
        "ts": "2026-08-01T00:00:00Z",
        "session": session,
        "trigger": trigger,
        "increment": increment,
        "plan": {"doc": (f"docs/work/{increment}" if increment else None), "objective": "fixture",
                 "phases_done": 1, "phases_total": 2},
        "gates": {"active_station": None, "recompute_green": None, "rtm": []},
    }


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# `build_snapshot` cases — synthetic roots, deliberately WITHOUT a `factories/` dir (SCOPE note)
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _case_bs_empty(base: Path) -> Path:
    d = base / "empty"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _case_bs_open_increment(base: Path) -> Path:
    d = base / "open_increment"
    d.mkdir(parents=True, exist_ok=True)
    _open_increment_doc(d, phases_done=1, phases_total=3)
    return d


def _case_bs_active_trust(base: Path) -> Path:
    d = base / "active_trust"
    d.mkdir(parents=True, exist_ok=True)
    _open_increment_doc(d, phases_done=2, phases_total=2)
    _write_proof(d, "s0", [{"name": "compile", "exit": 0}])
    _write_active(d, d, "s0")
    return d


def _case_bs_active_block(base: Path) -> Path:
    d = base / "active_block"
    d.mkdir(parents=True, exist_ok=True)
    _open_increment_doc(d, phases_done=0, phases_total=1)
    _write_proof(d, "s0", [{"name": "compile", "exit": 0}], tamper=True)
    _write_active(d, d, "s0")
    return d


_BS_CASES: tuple[tuple[str, Callable[[Path], Path]], ...] = (
    ("empty", _case_bs_empty),
    ("open_increment", _case_bs_open_increment),
    ("active_trust", _case_bs_active_trust),
    ("active_block", _case_bs_active_block),
)

# ── `write_snapshot` cases (name, snap, make_root_unwritable) ────────────────────────────────────────
_WRITE_SNAPSHOT_CASES: tuple[tuple[str, dict, bool], ...] = (
    ("valid_writable", _fixture_snap(), False),
    ("malformed_snap", {"foo": "bar"}, False),
    ("unwritable_root", _fixture_snap(trigger="manual2"), True),
)

# ── `record` cases (name, snap, written) ──────────────────────────────────────────────────────────────
_RECORD_CASES: tuple[tuple[str, dict, bool], ...] = (
    ("written_true", _fixture_snap(session="rs1", trigger="manual", increment="OPEN.md"), True),
    ("written_false", _fixture_snap(session="rs2", trigger="compact", increment=None), False),
)


# ── `build_payload` cases (each populates ONE destination dir; called twice, once per side) ──────────
def _bp_case_minimal(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)


def _bp_case_open_increment(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    _open_increment_doc(d, phases_done=1, phases_total=2)


def _bp_case_state_present(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    _open_increment_doc(d, phases_done=2, phases_total=2)
    _write_state_md(d, inc_line="OPEN.md",
                    rtm_line="fakefac: COMPLETE (1/1) · otherfac: INCOMPLETE (0/2)")


def _bp_case_journal_entries(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    _write_journal_entries(d, n=8)


_BP_CASES: tuple[tuple[str, Callable[[Path], None]], ...] = (
    ("minimal_no_state_no_journal", _bp_case_minimal),
    ("open_increment_no_state", _bp_case_open_increment),
    ("state_present_with_projection", _bp_case_state_present),
    ("journal_entries_tail_truncated", _bp_case_journal_entries),
)


def _sabotage_fixture(fn: str, base: Path) -> tuple[str, list, Path | None]:
    """One REAL matrix case per plant-targeted function, built with the SAME case builder the pin
    itself was measured over (never a one-off reimplementation) — so the fixture's content, and
    therefore its pinned answer, genuinely matches the key `compare_to_pin` looks up. Returns
    (case_name, args, root_for_landed_check)."""
    if fn == "build_payload":
        root = base / "root"
        _bp_case_open_increment(root)
        return "open_increment_no_state", [str(root), "s1", ""], None
    if fn == "write_snapshot":
        root = base / "root"
        root.mkdir(parents=True, exist_ok=True)
        return "valid_writable", [str(root), _fixture_snap()], root
    if fn == "build_snapshot":
        root = _case_bs_open_increment(base)
        return "open_increment", [str(root), "s1", "manual"], None
    raise AssertionError(f"no fixture wired for {fn!r}")


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# FACT EXTRACTION — derive a fact-set from each side's own answer, compare THAT
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _facts_snapshot(resp: dict) -> dict:
    """The dict's KEYS + every non-`ts` field's VALUE (module docstring's opening list)."""
    if not resp.get("ok"):
        return {"<error>": resp.get("error")}
    snap = resp.get("result")
    if not isinstance(snap, dict):
        return {"<not-a-dict>": repr(snap)}
    out = {k: v for k, v in snap.items() if k != "ts"}
    out["<keys>"] = sorted(snap.keys())
    return out


def _facts_write(resp: dict, landed: bool) -> dict:
    if not resp.get("ok"):
        return {"<error>": resp.get("error")}
    r = resp.get("result") or {}
    return {"is_none": r.get("is_none"), "landed": landed}


def _facts_record(resp: dict, journal_fact: dict | None) -> dict:
    if not resp.get("ok"):
        return {"<error>": resp.get("error")}
    return {"called_ok": bool((resp.get("result") or {}).get("called")), "journal": journal_fact}


_OPEN_INC_RE = re.compile(r"^(?:Incremento abierto|Open increment):\s*(.*)$", re.MULTILINE)
_ABSENT_MARKERS = {"ninguno", "none"}
_PROJ_LINE_RE = re.compile(r"^(?:Proyecci[oó]n|Projection) (-.*)$", re.MULTILINE)
_AHORA_HDR_RE = re.compile(r"^STATE\s*[«\"]?Ahora[»\"]?\s*:", re.MULTILINE)
_JOURNAL_TAIL_LINE_RE = re.compile(r"^ {2}\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z ", re.MULTILINE)
_ORIENT_MARKERS = ("`meta check`", "`meta checkpoint`", "grep -rn")


def _facts_payload(resp: dict) -> dict:
    """Five facts, regex-derived, tolerant of either language (module docstring's opening list)."""
    if not resp.get("ok"):
        return {"<error>": resp.get("error")}
    payload = (resp.get("result") or {}).get("payload")
    if not isinstance(payload, str):
        return {"<not-a-string>": repr(payload)}
    m = _OPEN_INC_RE.search(payload)
    inc_raw = m.group(1).strip() if m else None
    inc_absent = inc_raw is None or inc_raw.lower() in _ABSENT_MARKERS
    proj_lines = tuple(sorted(pm.group(1) for pm in _PROJ_LINE_RE.finditer(payload)))
    return {
        "open_increment_found": (m is not None) and not inc_absent,
        "open_increment": None if inc_absent else inc_raw,
        "projection_lines": proj_lines,
        "state_ahora_present": bool(_AHORA_HDR_RE.search(payload)),
        "journal_tail_count": len(_JOURNAL_TAIL_LINE_RE.findall(payload)),
        "orientation_markers_present": all(mk in payload for mk in _ORIENT_MARKERS),
    }


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# RUN + COMPARE
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _call(prefix: list[str], which: str, args: list, cwd: Path, env: dict) -> dict:
    proc = subprocess.run([sys.executable, *prefix, which, json.dumps(args)], cwd=str(cwd), env=env,
                          capture_output=True, text=True)
    out = proc.stdout.strip()
    if not out:
        return {"ok": False, "error": f"no stdout (exit {proc.returncode}): {proc.stderr[-400:]}"}
    try:
        return json.loads(out.splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"ok": False, "error": f"non-JSON stdout (exit {proc.returncode}): {out[-300:]!r} "
                                       f"stderr={proc.stderr[-300:]!r}"}


def _read_last_journal_record(root: Path) -> dict | None:
    p = root / ".metamem" / "journal.jsonl"
    if not p.exists():
        return None
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return None
    try:
        rec = json.loads(lines[-1])
    except json.JSONDecodeError:
        return None
    rec.pop("ts", None)
    return rec


def _all_case_names() -> list[str]:
    """The 13 `function:case` keys this module's matrix drives — the case-name space `pin_problems`'s
    bijection law (§2.2 law 2) checks the pin against."""
    return (
        [f"build_snapshot:{name}" for name, _ in _BS_CASES]
        + [f"write_snapshot:{name}" for name, _, _ in _WRITE_SNAPSHOT_CASES]
        + [f"record:{name}" for name, _, _ in _RECORD_CASES]
        + [f"build_payload:{name}" for name, _ in _BP_CASES]
    )


def _run_answers(prefix: list[str], cwd: Path, env: dict, base: Path) -> dict[str, object]:
    """Run the whole 13-case matrix through ONE side (`prefix`/`cwd`/`env`) and return
    `{f"{function}:{case}": fact}`. Only `_live_answers` (the port) calls this any more, but the
    `prefix`/`cwd`/`env` parameterization stays: it is what let the pin's provenance be proven by
    running the SAME matrix over the oracle in phase 1, before that call site was amputated here."""
    answers: dict[str, object] = {}

    bs_dir = base / "bs"
    for name, build in _BS_CASES:
        root = build(bs_dir)
        resp = _call(prefix, "build_snapshot", [str(root), "s1", "manual"], cwd, env)
        answers[f"build_snapshot:{name}"] = _facts_snapshot(resp)

    ws_dir = base / "ws"
    for name, snap, unwritable in _WRITE_SNAPSHOT_CASES:
        root = ws_dir / name
        root.mkdir(parents=True, exist_ok=True)
        try:
            if unwritable:
                os.chmod(root, 0o555)
            resp = _call(prefix, "write_snapshot", [str(root), snap], cwd, env)
        finally:
            if unwritable:
                os.chmod(root, 0o755)
        landed = (root / _SNAP_REL).exists()
        answers[f"write_snapshot:{name}"] = _facts_write(resp, landed)

    rec_dir = base / "rec"
    for name, snap, written in _RECORD_CASES:
        root = rec_dir / name
        root.mkdir(parents=True, exist_ok=True)
        resp = _call(prefix, "record", [str(root), snap, written], cwd, env)
        answers[f"record:{name}"] = _facts_record(resp, _read_last_journal_record(root))

    bp_dir = base / "bp"
    for name, build in _BP_CASES:
        root = bp_dir / name
        build(root)
        resp = _call(prefix, "build_payload", [str(root), "s1", ""], cwd, env)
        answers[f"build_payload:{name}"] = _facts_payload(resp)

    return answers


def _live_answers() -> dict[str, object]:
    """v3's port, driven alone (via `--drive`) over the whole matrix — the LIVE side of law 6's
    comparison against the pin. Never touches the oracle."""
    ported_prefix = ["-m", "v3.verify.session_memory_parity", "--drive"]
    ported_env = dict(os.environ)
    with tempfile.TemporaryDirectory(prefix="v3-session-memory-parity-live-") as tmp:
        return _run_answers(ported_prefix, _ROOT, ported_env, Path(tmp))


def check() -> tuple[list[str], dict]:
    """The gate: v3's LIVE fact-sets against the COMMITTED pin. Never shells to `git` — this module
    carries no code path that could any more (V3-EXTRACT-OBLIGATIONS phase 2)."""
    ref = harness.oracle_ref()
    case_names = _all_case_names()
    problems, pin = harness.pin_problems(_PIN_GATE, case_names, min_distinct=_MIN_DISTINCT_ANSWERS,
                                         oracle_ref=ref)
    if problems:
        return problems, {"cases": len(case_names)}
    mismatches = harness.compare_to_pin(_live_answers(), pin)
    counts = {"cases": len(case_names), "mismatches": len(mismatches)}
    return mismatches, counts


# ── the red side ──────────────────────────────────────────────────────────────────────────────────
def _fact_for(fn: str, resp: dict, root: Path | None) -> object:
    if fn == "build_payload":
        return _facts_payload(resp)
    if fn == "write_snapshot":
        return _facts_write(resp, (root / _SNAP_REL).exists() if root else False)
    if fn == "build_snapshot":
        return _facts_snapshot(resp)
    raise AssertionError(f"no fact extractor wired for {fn!r}")


def _run_sabotage() -> int:
    """Retargeted (V3-EXTRACT-OBLIGATIONS phase 1): every plant's LIVE fact (over the REAL matrix case
    its function targets) is compared against the PIN, never against a live oracle run — no oracle is
    built here at all any more. The two NEW plants (`pin_answer_corrupted`/`pin_case_dropped`) perturb
    an in-memory COPY of the pin itself and never touch a real pin file on disk."""
    ref = harness.oracle_ref()
    case_names = _all_case_names()
    caught: list[str] = []
    na: list[str] = []
    missed: list[str] = []

    try:
        pin = harness.load_pin(_PIN_GATE)
    except RuntimeError as exc:
        return Verdict("v3-session-memory-parity (SABOTAGE)", 1, f"cannot run: {exc}").emit()

    with tempfile.TemporaryDirectory(prefix="v3-session-memory-parity-sabotage-") as tmp:
        base = Path(tmp)
        for plant_name, (rel, real_path, plant_fn, fn) in _PLANTS.items():
            real_src = real_path.read_text(encoding="utf-8")
            try:
                patched_src = plant_fn(real_src)
            except harness.CannotPlant as exc:
                na.append(f"{plant_name}: {exc}")
                continue
            shadow_cwd = _build_shadow_v3(base / f"shadow_{plant_name}", patched_rel=rel,
                                          patched_src=patched_src)
            ported_prefix = ["-m", "v3.verify._driver"]
            ported_env = dict(os.environ)

            name, args, landed_root = _sabotage_fixture(fn, base / f"fixtures_{plant_name}")
            resp = _call(ported_prefix, fn, args, shadow_cwd, ported_env)
            answers = {f"{fn}:{name}": _fact_for(fn, resp, landed_root)}
            (caught if harness.compare_to_pin(answers, pin) else missed).append(plant_name)

    live = _live_answers()
    corrupted = harness.pin_answer_corrupted(pin)
    (caught if harness.compare_to_pin(live, corrupted) else missed).append("pin_answer_corrupted")

    dropped = harness.pin_case_dropped(pin)
    drop_problems, _ = harness.pin_problems(_PIN_GATE, case_names, min_distinct=_MIN_DISTINCT_ANSWERS,
                                            oracle_ref=ref, pin=dropped)
    (caught if drop_problems else missed).append("pin_case_dropped")

    print(f"PLANTS caught={caught} na={na} missed={missed}")

    if missed:
        return Verdict("v3-session-memory-parity (SABOTAGE)", 1,
                       f"GATE DECORATIVO: {len(caught)} caught · {len(na)} n/a · {len(missed)} MISSED "
                       f"{missed}").emit()
    if not caught:
        return Verdict("v3-session-memory-parity (SABOTAGE)", 1,
                       f"GATE DECORATIVO: every plant is N/A ({na}) — no witness caught anything").emit()
    return Verdict("v3-session-memory-parity (SABOTAGE)", 0,
                   f"{len(caught)} planted defect(s) caught ({', '.join(caught)}) · {len(na)} n/a "
                   f"({', '.join(na) or 'none'})",
                   counts={"caught": len(caught), "na": len(na)}).emit()


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--drive":
        return _drive(argv[1:])
    if argv:
        return Verdict("v3-session-memory-parity", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get("V3_SESSION_MEMORY_PARITY_SABOTAGE") == "1":
        return _run_sabotage()

    problems, counts = check()
    if problems:
        return Verdict("v3-session-memory-parity", 1,
                       f"{len(problems)} deviation(s) over {counts['cases']} case(s) against the "
                       f"committed pin",
                       counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-session-memory-parity", 0,
                   f"{counts['cases']} case(s) match between the committed pin and the ported session "
                   f"memory — fact parity only (module docstring: prose is never compared)",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
