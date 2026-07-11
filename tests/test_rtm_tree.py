"""C4 — the build evidence tree (req → capability → station → proof → artifact), proven by blocking.

Three levels, no mocks beyond hand-writing valid proofs via the real seed verifier:
  - the MODEL (`verify/rtm.py`): a req is SATISFIED iff every edge holds; a broken capability/proof/artifact
    edge drops it to UNSATISFIED, and the renderer stays within the bounded verdict bus.
  - the GRAMMAR edge: M0 (`validate`) REFUSES a phantom capability (req.capability not declared).
  - the GATE (`verify/checks/rtm_tree.main`): re-derives the tree and blocks — corrupt a proof → UNSAT,
    delete the artifact a capability certifies → UNSAT (the stale-evidence tooth); a proxy with no artifact
    reports the artifact tooth as N/A (never faked) yet still passes on the proof tooth.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from metafactory._seed import load_seed_verifier, repo_root
from metafactory.spec.loader import load_spec
from metafactory.spec.model import Capability, FactorySpec, Requirement, SpecStation
from metafactory.spec.validator import validate
from metafactory.verify import rtm
from metafactory.verify.checks.rtm_tree import main

_REPO = repo_root()
sys.path.insert(0, str(_REPO / "src"))
_V = load_seed_verifier(str(_REPO))


# ── helpers: hand-write a valid proof through the real seed verifier ────────────

def _write_proof(root: Path, sid: str, exit_code: int = 0) -> None:
    checks = [{"name": "x", "cmd": ["true"], "exit": exit_code}]
    proof = {"station": sid, "passed": exit_code == 0, "checks": checks,
             "proof_sha": _V.compute_proof_sha(sid, checks), "writer": "test"}
    d = root / ".proof"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{sid}.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")


def _spec(reqs, caps=()) -> FactorySpec:
    return FactorySpec(
        name="T", slug="t", maturity="bootstrap", produces="x",
        stations=[SpecStation(id="s00", name="s00")],
        substrate={"anti_rubber_stamp_column": True, "verdict_bus": {"max_lines": 10}},
        requirements=list(reqs), capabilities=list(caps))


# ── the MODEL: edges of the tree ────────────────────────────────────────────────

def test_satisfied_when_every_edge_holds(tmp_path):
    _write_proof(tmp_path, "s00")
    (tmp_path / "art.txt").write_text("ok", encoding="utf-8")
    spec = _spec([Requirement("REQ-F-001", "s", ["s00"], capability="cap")],
                 [Capability(id="cap", artifact="art.txt")])
    nodes = rtm.build_tree(spec, _V, tmp_path)
    assert rtm.is_complete(nodes)
    assert nodes[0].satisfied


def test_unsatisfied_when_proof_shut(tmp_path):
    _write_proof(tmp_path, "s00", exit_code=9)   # red proof
    spec = _spec([Requirement("REQ-F-001", "s", ["s00"])])
    nodes = rtm.build_tree(spec, _V, tmp_path)
    assert not nodes[0].satisfied
    assert "proof SHUT" in nodes[0].broken_edge()


def test_unsatisfied_when_artifact_missing(tmp_path):
    """The C4 leaf: proof is OPEN but the artifact the capability certifies is gone → UNSATISFIED."""
    _write_proof(tmp_path, "s00")               # proof passes
    spec = _spec([Requirement("REQ-F-001", "s", ["s00"], capability="cap")],
                 [Capability(id="cap", artifact="vanished.txt")])
    nodes = rtm.build_tree(spec, _V, tmp_path)
    assert not nodes[0].satisfied
    assert "missing artifact" in nodes[0].broken_edge()


def test_no_artifact_declared_is_not_faked(tmp_path):
    """A capability with no artifact → the leaf is empty (no artifact assertion), SATISFIED on the proof."""
    _write_proof(tmp_path, "s00")
    spec = _spec([Requirement("REQ-F-001", "s", ["s00"], capability="cap")],
                 [Capability(id="cap")])
    nodes = rtm.build_tree(spec, _V, tmp_path)
    assert nodes[0].satisfied
    assert nodes[0].artifacts == []


def test_render_is_bounded_and_traces(tmp_path):
    _write_proof(tmp_path, "s00")
    (tmp_path / "art.txt").write_text("ok", encoding="utf-8")
    spec = _spec([Requirement("REQ-F-001", "s", ["s00"], capability="cap")],
                 [Capability(id="cap", artifact="art.txt")])
    text = rtm.render("t", rtm.build_tree(spec, _V, tmp_path))
    assert "COMPLETE" in text and "REQ-F-001 SATISFIED" in text
    assert "cap:" in text and "art.txt✓" in text
    assert len(text.splitlines()) <= 10        # bounded to the verdict bus (I-7)


# ── the GRAMMAR edge: M0 refuses a phantom capability ───────────────────────────

def test_m0_refuses_phantom_capability(tmp_path):
    spec = _spec([Requirement("REQ-F-001", "s", ["s00"], capability="ghost")],
                 [Capability(id="real")])
    problems = validate(spec)
    assert any("phantom capability" in p and "ghost" in p for p in problems)


def test_m0_accepts_real_capability(tmp_path):
    spec = _spec([Requirement("REQ-F-001", "s", ["s00"], capability="real")],
                 [Capability(id="real")])
    assert not any("capability" in p for p in validate(spec))


# ── the GATE: prove the tree by blocking (hermetic) ─────────────────────────────

def _gate_factory(tmp_path: Path, *, artifact: bool) -> Path:
    """A minimal factory: REQ-F-001 → capability cap (→ artifact) → station s00 (passing proof)."""
    f = tmp_path / "factory"
    f.mkdir()
    cap_artifact = "\n      artifact: art.txt" if artifact else ""
    (f / "factory.spec.yml").write_text(
        "factory: {name: T, slug: t, maturity: bootstrap}\n"
        "domain:\n  produces: x\n"
        "  capabilities:\n    - id: cap" + cap_artifact + "\n"
        "  station_sequence:\n    - {id: s00, name: s00, activation: always}\n"
        "factory_substrate: {anti_rubber_stamp_column: true, verdict_bus: {max_lines: 10}}\n"
        "requirements:\n  functional:\n"
        "    - {id: REQ-F-001, statement: s, satisfied_by: [s00], capability: cap}\n",
        encoding="utf-8")
    _write_proof(f, "s00")
    if artifact:
        (f / "art.txt").write_text("ok", encoding="utf-8")
    return f


def test_gate_passes_with_full_tree_and_proves_both_teeth(tmp_path):
    f = _gate_factory(tmp_path, artifact=True)
    assert main([str(f), str(_REPO), "factory.spec.yml"]) == 0


def test_gate_passes_proxy_reports_artifact_na(tmp_path, capsys):
    """A factory whose SATISFIED req declares no artifact: the proof tooth still proves the tree; the
    artifact tooth is reported N/A (not faked)."""
    f = _gate_factory(tmp_path, artifact=False)
    rc = main([str(f), str(_REPO), "factory.spec.yml"])
    assert rc == 0
    assert "N/A" in capsys.readouterr().out


def test_gate_red_when_no_satisfied_req(tmp_path):
    """No proofs on disk → nothing built → the gate refuses (cannot prove a drop)."""
    f = tmp_path / "factory"
    f.mkdir()
    (f / "factory.spec.yml").write_text(
        "factory: {name: T, slug: t, maturity: bootstrap}\n"
        "domain:\n  produces: x\n"
        "  station_sequence:\n    - {id: s00, name: s00, activation: always}\n"
        "factory_substrate: {anti_rubber_stamp_column: true, verdict_bus: {max_lines: 10}}\n"
        "requirements:\n  functional:\n    - {id: REQ-F-001, statement: s, satisfied_by: [s00]}\n",
        encoding="utf-8")
    assert main([str(f), str(_REPO), "factory.spec.yml"]) == 1


def test_gate_usage_error(tmp_path):
    assert main([]) == 2


# ── happy path against the real dummy factory ───────────────────────────────────

@pytest.mark.skipif(
    not (_REPO / "factories" / "dummy" / ".proof").exists(),
    reason="clean clone: the dummy is not BUILT here (.proof/ is gitignored evidence, not content); "
           "on the external runner this property is covered by the pin step (`meta ci --rederive`)")
def test_gate_against_real_dummy():
    """The dummy is the full-tree demonstrator (built in the repo): the gate passes against it."""
    fdir = _REPO / "factories" / "dummy"
    rc = main([str(fdir), str(_REPO), "factory.spec.yml"])
    assert rc == 0, "rtm_tree should pass against the real built dummy"
