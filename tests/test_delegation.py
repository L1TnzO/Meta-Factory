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
        "iteration_gate_cmd": ["python3", "-c", "pass"],
        "acceptance_gate_cmd": ["python3", "-m", "pytest", "-q"],
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
        "slot_id": "demo", "status": "green", "check": "pytest", "exit_code": 0,
        "acceptance_exit_code": 0}), encoding="utf-8")
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


# ── HARNESS-FAST-GATE: split gate (fast iteration / heavy acceptance) is REQUIRED ──
def test_manifest_requires_both_gates(tmp_path):
    # The measured worst case was a 79-min slot whose only gate was a minutes-long integration run. A manifest
    # that declares the OLD single `gate_cmd` (or nothing) but not the split gates is rejected.
    legacy = {"slot_id": "x", "allow_globs": ["src/a.py"], "verdict_path": ".gen/x.json",
              "gate_cmd": ["pytest"]}
    probs = delegation.manifest_problems(legacy)
    assert any("iteration_gate_cmd" in p for p in probs) and any("acceptance_gate_cmd" in p for p in probs)
    both = legacy | {"iteration_gate_cmd": ["python3", "-c", "pass"],
                     "acceptance_gate_cmd": ["python3", "-m", "pytest", "-q"]}
    assert delegation.manifest_problems(both) == []


@pytest.mark.parametrize("field,value,ok", [
    ("iteration_budget_s", 10, True),
    ("iteration_budget_s", 15, True),
    ("iteration_budget_s", 30, False),          # over the fast-gate ceiling
    ("iteration_budget_s", 0, False),
    ("iteration_budget_s", True, False),        # bool is not a budget
    ("max_wall_s", 1200, True),
    ("max_wall_s", 3600, False),                # a slot > 30 min must be split (D23)
    ("token_budget", 40000, True),
    ("token_budget", -5, False),
    ("token_budget", 1.5, False),
    ("file_budget", 800, True),
    ("file_budget", 0, False),
    ("file_budget", 1.5, False),                # LOC is an int, not a float
    ("file_budget", True, False),               # bool is not a budget
])
def test_slot_size_law_budgets(tmp_path, field, value, ok):
    slot = _slot(tmp_path) | {field: value}
    probs = [p for p in delegation.manifest_problems(slot) if field in p]
    assert (probs == []) == ok, probs


def test_verdict_requires_acceptance_green(tmp_path):
    slot = _slot(tmp_path)  # declares an acceptance_gate_cmd
    (tmp_path / ".gen").mkdir()
    vp = tmp_path / ".gen/demo.verdict.json"

    def _write(payload):
        vp.write_text(json.dumps(payload), encoding="utf-8")

    base = {"slot_id": "demo", "status": "green", "check": "iteration", "exit_code": 0}
    _write(base)                                          # green but no acceptance recorded
    ok, why = delegation.verdict_ok(tmp_path, slot)
    assert not ok and "acceptance" in why
    _write(base | {"acceptance_exit_code": 1})            # acceptance ran but FAILED
    ok, _ = delegation.verdict_ok(tmp_path, slot)
    assert not ok
    _write(base | {"acceptance_exit_code": 0})            # acceptance passed → real green
    ok, detail = delegation.verdict_ok(tmp_path, slot)
    assert ok and "green" in detail


# ── CONTEXT-LEAN-TEETH: file-size budget validated at the verdict (C17b) ───────
def test_verdict_size_budget_two_sided(tmp_path):
    """A green verdict on an oversized generated file is not real: `file_budget` (max LOC per file inside the
    blast radius) is validated against the ACTUAL produced artifact. Both sides: within budget → green;
    a file over budget → demoted to red naming the file. No budget declared → size is not policed."""
    (tmp_path / ".gen").mkdir()
    (tmp_path / "src/pkg").mkdir(parents=True)
    gen = tmp_path / "src/pkg/gen.py"
    slot = _slot(tmp_path) | {"allow_globs": ["src/pkg/gen.py"], "file_budget": 5}
    (tmp_path / ".gen/demo.verdict.json").write_text(json.dumps(
        {"slot_id": "demo", "status": "green", "check": "iteration", "exit_code": 0,
         "acceptance_exit_code": 0}), encoding="utf-8")

    # within budget → real green
    gen.write_text("a = 1\nb = 2\n", encoding="utf-8")
    assert delegation.verdict_size_problems(tmp_path, slot) == []
    ok, detail = delegation.verdict_ok(tmp_path, slot)
    assert ok and "green" in detail

    # over budget → green verdict demoted to red, naming the file
    gen.write_text("\n".join(f"x{i} = {i}" for i in range(20)) + "\n", encoding="utf-8")
    probs = delegation.verdict_size_problems(tmp_path, slot)
    assert probs and "src/pkg/gen.py" in probs[0] and "file_budget" in probs[0]
    ok, detail = delegation.verdict_ok(tmp_path, slot)
    assert not ok and "file_budget" in detail

    # no budget declared → size is not policed (backward-compatible)
    assert delegation.verdict_size_problems(tmp_path, _slot(tmp_path)) == []


def test_affected_tests_selects_by_blast_radius():
    # Against the real repo tests/: a slot writing graph/pricing.py must select the pricing tests (not the whole
    # suite), and a non-matching path selects nothing → the caller falls back to the module's own gate.
    hits = delegation.affected_tests(REPO, ["src/metafactory/graph/pricing.py"])
    assert any("test_pricing" in h for h in hits)
    assert all(h.startswith("tests/") and h.endswith(".py") for h in hits)
    assert delegation.affected_tests(REPO, ["src/metafactory/zzz_nonexistent_module.py"]) == []


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


# ── SLOT-FOOTPRINT-TOOTH (SOTA-PARITY INC-1): acceptance on the OBSERVED footprint ──
def test_footprint_clean_inside_slot(tmp_path):
    slot = _slot(tmp_path) | {"baseline_dirty": ["docs/notes.md"]}
    changed = ["src/pkg/target.py", "src/pkg/sub/new.py", ".gen/demo.verdict.json",
               ".gen/scratch/x.txt", "docs/notes.md"]
    assert delegation.footprint_problems(slot, changed) == []


def test_footprint_flags_out_of_slot(tmp_path):
    probs = delegation.footprint_problems(_slot(tmp_path), ["seed/verifier.py", "src/pkg/target.py"])
    assert len(probs) == 1 and "seed/verifier.py" in probs[0]


def test_footprint_baseline_exempts_only_recorded(tmp_path):
    slot = _slot(tmp_path) | {"baseline_dirty": ["docs/notes.md"]}
    probs = delegation.footprint_problems(slot, ["docs/notes.md", "docs/other.md"])
    assert len(probs) == 1 and "docs/other.md" in probs[0]


def test_write_slot_records_baseline_dirty(tmp_path):
    p = delegation.write_slot(tmp_path, {"slot_id": "x"}, baseline_dirty=["b.md", "a.md", "a.md"])
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["baseline_dirty"] == ["a.md", "b.md"]      # sorted + deduped
    p2 = delegation.write_slot(tmp_path, {"slot_id": "x"})  # backward-compatible: no baseline recorded
    assert "baseline_dirty" not in json.loads(p2.read_text(encoding="utf-8"))


def test_manifest_problems_baseline_dirty_shape(tmp_path):
    bad = _slot(tmp_path) | {"baseline_dirty": "a.md"}
    assert any("baseline_dirty" in p for p in delegation.manifest_problems(bad))
    good = _slot(tmp_path) | {"baseline_dirty": ["a.md"]}
    assert delegation.manifest_problems(good) == []


# ── the HOOKS (real subprocess, as the harness runs them) ──────────────────────
def _git_dirty_now() -> list[str]:
    """The repo's CURRENT dirty paths (test-time baseline, so a dirty working tree can't false-red)."""
    r = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                       cwd=REPO, capture_output=True, text=True)
    out = []
    for line in r.stdout.splitlines():
        for part in line[3:].split(" -> "):
            p = part.strip().strip('"')
            if p:
                out.append(p)
    return out


@pytest.fixture
def active_manifest():
    """Install a real slot manifest under the repo's .gen/, torn down after. Harmless to the session:
    the global hooks never read it (blast_radius/verdict_required live only in the generator frontmatter).
    `baseline_dirty` records the CURRENT dirty tree (SLOT-FOOTPRINT-TOOTH) so in-progress work never
    false-reds the footprint check."""
    p = delegation.manifest_path(REPO)
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "slot_id": "test-slot",
        "allow_globs": ["src/pkg/target.py"],
        "gate_cmd": ["true"],
        "verdict_path": ".gen/test-slot.verdict.json",
        "baseline_dirty": sorted(set(_git_dirty_now())),
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


def test_verdict_required_blocks_out_of_slot_footprint(active_manifest):
    """SLOT-FOOTPRINT-TOOTH: a well-formed green verdict is NOT enough — a persisted change outside
    allow_globs ∪ verdict ∪ .gen/ ∪ baseline_dirty (e.g. a Bash write that bypassed the PreToolUse hook)
    blocks the stop (exit 2); removing it unblocks (exit 0)."""
    (REPO / ".gen/test-slot.verdict.json").write_text(json.dumps({
        "slot_id": "test-slot", "status": "green", "check": "true", "exit_code": 0}), encoding="utf-8")
    escape = REPO / "zz_footprint_escape.tmp"
    try:
        escape.write_text("out-of-slot persisted change\n", encoding="utf-8")
        assert _run_hook("verdict_required.py", {}) == 2   # footprint violation → cannot stop
    finally:
        escape.unlink(missing_ok=True)
    assert _run_hook("verdict_required.py", {}) == 0        # clean footprint → may stop


def _synthetic_root(tmp_path: Path, law: str | None, manifest: str | None) -> Path:
    """A fake factory root for the FAIL-CLOSED witness: real hooks copied in (they resolve their root by
    script location, parents[2]), a seed law and a manifest as given."""
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    for name in ("blast_radius.py", "verdict_required.py"):
        (hooks / name).write_text((HOOKS / name).read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "seed").mkdir()
    if law is not None:
        (tmp_path / "seed" / "delegation.py").write_text(law, encoding="utf-8")
    if manifest is not None:
        (tmp_path / ".gen").mkdir()
        (tmp_path / ".gen" / "active_slot.json").write_text(manifest, encoding="utf-8")
    return tmp_path


def _run_hook_at(root: Path, name: str, payload: dict) -> int:
    r = subprocess.run([sys.executable, str(root / ".claude" / "hooks" / name)],
                       input=json.dumps(payload), text=True, capture_output=True)
    return r.returncode


_WRITE_PAYLOAD = {"tool_name": "Write", "tool_input": {"file_path": "anything.py"}}


def test_hooks_fail_closed_when_law_broken(tmp_path):
    """GAP-1 fix: manifest PRESENT + unloadable law → both hooks exit 2 (the old `except: return 0`
    was fail-OPEN while a slot was active)."""
    root = _synthetic_root(tmp_path, law="def broken(:\n", manifest='{"slot_id": "w", "allow_globs": ["x"]}')
    assert _run_hook_at(root, "blast_radius.py", _WRITE_PAYLOAD) == 2
    assert _run_hook_at(root, "verdict_required.py", {}) == 2


def test_hooks_fail_closed_on_malformed_manifest(tmp_path):
    """Manifest file PRESENT but not a valid JSON object → undecidable slot → fail closed (exit 2)."""
    root = _synthetic_root(tmp_path, law=(REPO / "seed" / "delegation.py").read_text(encoding="utf-8"),
                           manifest="{not json")
    assert _run_hook_at(root, "blast_radius.py", _WRITE_PAYLOAD) == 2
    assert _run_hook_at(root, "verdict_required.py", {}) == 2


def test_hooks_inert_without_manifest_even_if_law_broken(tmp_path):
    """No manifest on disk → inert (exit 0) regardless of the law's state: the main session and other
    subagents stay untouched."""
    root = _synthetic_root(tmp_path, law="def broken(:\n", manifest=None)
    assert _run_hook_at(root, "blast_radius.py", _WRITE_PAYLOAD) == 0
    assert _run_hook_at(root, "verdict_required.py", {}) == 0
