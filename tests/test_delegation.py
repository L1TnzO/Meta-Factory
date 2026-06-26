"""test_delegation — the verify-not-review loop core (ADR-017 §2, DELEGATION-HARNESS Fase 1).

Closure criterion #1 proven BY BLOCKING: the two machine teeth that make cheap delegation SAFE.
  - blast_radius:     a write INSIDE the slot is allowed (exit 0); OUTSIDE is blocked (exit 2); with no
                      active manifest the hook is INERT (exit 0) — the main session is untouched.
  - verdict_required: finishing WITH a well-formed verdict is allowed (exit 0); WITHOUT is blocked (exit 2);
                      with no active manifest, inert (exit 0).
The LAW (`metafactory.delegation`) is unit-tested on an isolated tmp root; the HOOKS are run as the harness
runs them — real subprocess, JSON on stdin — against the real repo with a torn-down manifest under `.gen/`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from metafactory import delegation

REPO = Path(__file__).resolve().parents[1]
HOOKS = REPO / ".claude" / "hooks"


# ── the LAW (isolated tmp root) ────────────────────────────────────────────────
def _slot(tmp: Path) -> dict:
    return {
        "slot_id": "demo",
        "contract": "def f(x: int) -> int",
        "allow_globs": ["src/pkg/target.py", "src/pkg/sub/*.py"],
        "gate_cmd": ["python3", "-c", "pass"],
        "verdict_path": ".gen/demo.verdict.json",
    }


def test_write_allowed_inside_slot(tmp_path):
    slot = _slot(tmp_path)
    assert delegation.write_allowed(tmp_path, slot, "src/pkg/target.py")
    assert delegation.write_allowed(tmp_path, slot, "src/pkg/sub/new.py")
    assert delegation.write_allowed(tmp_path, slot, str(tmp_path / "src/pkg/target.py"))  # abs ok


def test_write_denied_outside_slot(tmp_path):
    slot = _slot(tmp_path)
    assert not delegation.write_allowed(tmp_path, slot, "src/pkg/other.py")
    assert not delegation.write_allowed(tmp_path, slot, "seed/verifier.py")
    assert not delegation.write_allowed(tmp_path, slot, "../escape.py")  # escapes repo -> never


def test_write_allows_gen_scratch_and_verdict(tmp_path):
    slot = _slot(tmp_path)
    assert delegation.write_allowed(tmp_path, slot, ".gen/demo.verdict.json")  # declared verdict
    assert delegation.write_allowed(tmp_path, slot, ".gen/scratch/notes.txt")  # own gitignored scratch


def test_verdict_ok_well_formed(tmp_path):
    slot = _slot(tmp_path)
    (tmp_path / ".gen").mkdir()
    (tmp_path / ".gen/demo.verdict.json").write_text(json.dumps({
        "slot_id": "demo", "status": "green", "check": "pytest", "exit_code": 0}), encoding="utf-8")
    ok, detail = delegation.verdict_ok(tmp_path, slot)
    assert ok and "green" in detail


@pytest.mark.parametrize("payload,reason", [
    (None, "no verdict"),                                              # absent
    ('{"slot_id":"demo","status":"green"}', "incomplete"),            # missing check/exit_code
    ('{"slot_id":"demo","status":"maybe","check":"x","exit_code":0}', "status invalid"),  # bad status
    ("{not json", "malformed"),                                        # malformed
])
def test_verdict_ok_rejects_bad(tmp_path, payload, reason):
    slot = _slot(tmp_path)
    (tmp_path / ".gen").mkdir()
    if payload is not None:
        (tmp_path / ".gen/demo.verdict.json").write_text(payload, encoding="utf-8")
    ok, detail = delegation.verdict_ok(tmp_path, slot)
    assert not ok and reason in detail


def test_manifest_problems_shape(tmp_path):
    assert delegation.manifest_problems(_slot(tmp_path)) == []
    bad = {"slot_id": "x", "allow_globs": "not-a-list"}
    probs = delegation.manifest_problems(bad)
    assert any("verdict_path" in p for p in probs) and any("allow_globs` must be a list" in p for p in probs)


# ── WorkOrder vocab (PWF harvest): optional but validated against a closed set ──
def test_workorder_vocab_well_formed_passes(tmp_path):
    slot = _slot(tmp_path) | {
        "trust_level": "medium", "cost_class": "cheap", "side_effects": ["files"],
        "forbidden_tools": ["WebFetch"], "single_responsibility": "render the contract handler",
        "model_policy": {"temperature": 0, "seed": 7, "strict_json": True},
    }
    assert delegation.manifest_problems(slot) == []


def test_workorder_vocab_backward_compatible(tmp_path):
    assert delegation.manifest_problems(_slot(tmp_path)) == []  # no vocab declared -> still valid


@pytest.mark.parametrize("field,value,needle", [
    ("trust_level", "ultimate", "trust_level` invalid"),
    ("cost_class", "free", "cost_class` invalid"),
    ("side_effects", ["files", "gpu"], "side_effects` has unknown"),
    ("side_effects", "files", "side_effects` must be a list"),
    ("forbidden_tools", "Write", "forbidden_tools` must be a list"),
    ("single_responsibility", "  ", "single_responsibility` must be a non-empty"),
    ("model_policy", {"top_p": 1}, "model_policy` has unknown keys"),
    ("model_policy", "temp0", "model_policy` must be an object"),
])
def test_workorder_vocab_rejects_malformed(tmp_path, field, value, needle):
    slot = _slot(tmp_path) | {field: value}
    probs = delegation.manifest_problems(slot)
    assert any(needle in p for p in probs), probs


# ── the HOOKS (real subprocess, as the harness runs them) ──────────────────────
@pytest.fixture
def active_manifest():
    """Install a real slot manifest under the repo's .gen/, torn down after. Harmless to the session:
    the global hooks never read it (blast_radius/verdict_required live only in the generator frontmatter)."""
    p = delegation.manifest_path(REPO)
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "slot_id": "test-slot",
        "allow_globs": ["src/pkg/target.py"],
        "gate_cmd": ["true"],
        "verdict_path": ".gen/test-slot.verdict.json",
    }
    p.write_text(json.dumps(manifest), encoding="utf-8")
    try:
        yield manifest
    finally:
        p.unlink(missing_ok=True)
        (REPO / ".gen/test-slot.verdict.json").unlink(missing_ok=True)


def _run_hook(name: str, payload: dict) -> int:
    r = subprocess.run([sys.executable, str(HOOKS / name)],
                       input=json.dumps(payload), text=True, capture_output=True)
    return r.returncode


def test_blast_radius_blocks_outside_slot(active_manifest):
    payload = {"tool_name": "Write", "tool_input": {"file_path": "seed/verifier.py"}}
    assert _run_hook("blast_radius.py", payload) == 2  # outside slot -> blocked


def test_blast_radius_allows_inside_slot(active_manifest):
    payload = {"tool_name": "Write", "tool_input": {"file_path": "src/pkg/target.py"}}
    assert _run_hook("blast_radius.py", payload) == 0  # inside slot -> allowed


def test_blast_radius_inert_without_manifest():
    # No manifest installed -> the tooth must be invisible (main session / other agents untouched).
    delegation.manifest_path(REPO).unlink(missing_ok=True)
    payload = {"tool_name": "Write", "tool_input": {"file_path": "seed/verifier.py"}}
    assert _run_hook("blast_radius.py", payload) == 0


def test_verdict_required_blocks_without_verdict(active_manifest):
    assert _run_hook("verdict_required.py", {}) == 2  # no verdict at declared path -> cannot stop


def test_verdict_required_allows_with_verdict(active_manifest):
    (REPO / ".gen/test-slot.verdict.json").write_text(json.dumps({
        "slot_id": "test-slot", "status": "green", "check": "true", "exit_code": 0}), encoding="utf-8")
    assert _run_hook("verdict_required.py", {}) == 0  # well-formed verdict -> may stop


def test_verdict_required_inert_without_manifest():
    delegation.manifest_path(REPO).unlink(missing_ok=True)
    assert _run_hook("verdict_required.py", {}) == 0


def test_verdict_required_anti_loop_valve(active_manifest):
    # Even with no verdict, the stop_hook_active valve prevents an infinite re-block.
    assert _run_hook("verdict_required.py", {"stop_hook_active": True}) == 0
