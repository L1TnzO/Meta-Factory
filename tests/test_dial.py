"""test_dial — the draft→harden DIAL (ADR-017 Fase 4, DRAFT-HARDEN-DIAL).

By blocking, on the REAL engine (real subprocess checks, real seed proofs — no mocks):
  - tier semantics: a `harden` station is deferred in draft, run in harden; `core` always runs.
  - two-sided VALUE: the same line with a FAILING harden gate is RED in harden (rigor has teeth) and GREEN
    in draft (the velocity loop skips rigor) — draft trades rigor for speed, HONESTLY (it skips, it does not
    fake the harden checks: the deferred station has no proof at all).
  - the fan-in fall-through: a core station that `depends_on` a deferred harden station still gates (the
    harden predecessor is transparent), so deferring rigor never wedges the spine.
  - harden mode is byte-identical to no dial (default), so existing pins/ci/`meta check` are untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

from metafactory._seed import repo_root
from metafactory.engine.run_context import RunContext
from metafactory.engine.runner import run_station
from metafactory.engine.sequence import Sequence
from metafactory.engine.station import Station

PY = sys.executable
PASS = [PY, "-c", "raise SystemExit(0)"]
FAIL = [PY, "-c", "raise SystemExit(1)"]


def _station(sid, tier="core", exit_ok=True, depends_on=None):
    return Station.from_dict({
        "id": sid, "name": sid, "tier": tier,
        "depends_on": depends_on or [],
        "checks": [{"name": f"{sid}_chk", "kind": "command", "cmd": PASS if exit_ok else FAIL}],
    })


def _apply_dial(seq: Sequence, dial: str) -> None:
    """The same rule `_run_product_line` applies: in draft, defer harden-tier stations (activation off)."""
    if dial == "draft":
        for s in seq.stations:
            if not s.active_in("draft"):
                s.activation = "off"


def _run(seq: Sequence, dial: str, tmp: Path):
    ctx = RunContext(root=tmp, meta_root=repo_root())
    _apply_dial(seq, dial)
    runs = {}
    for st in seq.active:
        runs[st.id] = run_station(ctx, st, seq, {}, stations_dir=tmp, spec_path=None, record_active=False)
    return ctx, runs


# ── tier semantics ────────────────────────────────────────────────────────────

def test_active_in_tier_semantics():
    assert _station("a", "core").active_in("draft") and _station("a", "core").active_in("harden")
    assert _station("b", "harden").active_in("harden")
    assert not _station("b", "harden").active_in("draft")   # rigor deferred in the fast loop


def test_default_tier_is_core():
    assert Station.from_dict({"id": "x", "name": "x"}).tier == "core"


# ── two-sided VALUE: failing rigor is caught in harden, skipped in draft ─────────

def test_harden_catches_failing_rigor(tmp_path):
    seq = Sequence([_station("spine", "core", True), _station("rigor", "harden", False, depends_on=["spine"])])
    _, runs = _run(seq, "harden", tmp_path)
    assert runs["spine"].passed and runs["spine"].gate.opened
    assert "rigor" in runs and not runs["rigor"].passed             # the harden gate has teeth


def test_draft_skips_rigor_and_is_green(tmp_path):
    seq = Sequence([_station("spine", "core", True), _station("rigor", "harden", False, depends_on=["spine"])])
    _, runs = _run(seq, "draft", tmp_path)
    assert "rigor" not in runs                                       # deferred — not run, not faked
    assert runs["spine"].passed and runs["spine"].gate.opened        # spine builds fast


def test_draft_proof_set_excludes_harden(tmp_path):
    # A draft run writes proofs ONLY for core stations → its proof set differs from harden → it can't
    # masquerade as a hardened pin (harden `ci --rederive` re-runs ALL stations and would mismatch).
    seq = Sequence([_station("spine", "core", True), _station("rigor", "harden", True)])
    ctx, runs = _run(seq, "draft", tmp_path)
    assert ctx.verifier.load_proof(tmp_path, "spine") is not None
    assert ctx.verifier.load_proof(tmp_path, "rigor") is None


# ── fan-in fall-through: deferring rigor never wedges a dependent core station ───

def test_core_depending_on_deferred_harden_falls_through():
    spine = _station("spine", "core", True)
    rigor = _station("rigor", "harden", True, depends_on=["spine"])
    tail = _station("tail", "core", True, depends_on=["rigor"])    # core depends on harden
    seq = Sequence([spine, rigor, tail])
    _apply_dial(seq, "draft")
    # tail's predecessor is the DEFERRED rigor → it falls through transparently to the spine.
    assert [s.id for s in seq.predecessors(tail)] == ["spine"]


def test_harden_keeps_full_fan_in():
    spine = _station("spine", "core", True)
    rigor = _station("rigor", "harden", True, depends_on=["spine"])
    tail = _station("tail", "core", True, depends_on=["rigor"])
    seq = Sequence([spine, rigor, tail])                            # no dial applied (harden)
    assert [s.id for s in seq.predecessors(tail)] == ["rigor"]      # byte-identical to before
