"""G2 — the scenario-corpus gate, proven by blocking (`SELF-IMPROVEMENT.md §4`; closes G-8 at root).

Levels (mirroring test_blast_radius's structure — pure law here, the heavy promote wiring is LIVE):
  - the per-scenario LAW (`evaluate_scenario`): a `valid` shape must validate clean; a `reject` shape
    must be refused FOR the declared reason. TWO-SIDED — a valid REJECTED or a reject ACCEPTED is a
    cascade (the engine regressed on a spec shape).
  - the DIVERSITY tooth (`diversity`): too few distinct shapes, or only one polarity, means the corpus
    cannot close G-8 ("few spec shapes") → red.
  - the DECISION (`decide`): the law `meta promote` dispatches on (empty/mismatch/thin/ok).
  - the REAL shipped corpus stays green AND diverse (regression guard, like the real-spec tests).
  - the NON-DECORATIVE tooth: if the engine LOSES a validator tooth, a `reject` scenario is accepted →
    the corpus reports a mismatch (the gate has teeth — it is not prosa).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from metafactory.spec.loader import load_spec
from metafactory.verify.checks import scenario_corpus as SC

_SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"


# ── fixtures: tiny specs of known shape, written into a tmp corpus ───────────────

def _valid(slug: str, n_stations: int = 1) -> dict:
    stations = [{"id": f"s{i}", "name": f"st{i}", "activation": "always",
                 **({"depends_on": [f"s{i-1}"]} if i else {})} for i in range(n_stations)]
    return {
        "factory": {"name": slug, "slug": slug, "maturity": "bootstrap"},
        "domain": {"produces": "a widget", "station_sequence": stations},
        "factory_substrate": {"anti_rubber_stamp_column": True, "verdict_bus": {"max_lines": 10}},
        "requirements": {"functional": [
            {"id": "REQ-F-001", "statement": "x", "satisfied_by": ["s0"]}]},
    }


def _reject_orphan(slug: str) -> dict:
    d = _valid(slug)
    d["requirements"]["functional"][0]["satisfied_by"] = ["ghost"]
    return d


def _write_corpus(tmp: Path, entries: list[dict], specs: dict[str, dict]) -> Path:
    for name, data in specs.items():
        (tmp / name).write_text(yaml.dump(data), encoding="utf-8")
    corpus = tmp / "corpus.yml"
    corpus.write_text(yaml.dump({"scenarios": entries}), encoding="utf-8")
    return corpus


# ── the per-scenario law ─────────────────────────────────────────────────────────

def test_valid_clean_passes(tmp_path):
    _write_corpus(tmp_path, [], {"a.yml": _valid("a")})
    ok, reason = SC.evaluate_scenario({"spec": "a.yml", "expect": "valid"}, tmp_path)
    assert ok and reason == ""


def test_valid_rejected_is_a_cascade(tmp_path):
    # a shape declared valid that the engine refuses = a regression that broke a valid form.
    _write_corpus(tmp_path, [], {"bad.yml": _reject_orphan("badvalid")})
    ok, reason = SC.evaluate_scenario({"spec": "bad.yml", "expect": "valid"}, tmp_path)
    assert not ok and "VÁLIDA rechazada" in reason


def test_reject_with_right_reason_passes(tmp_path):
    _write_corpus(tmp_path, [], {"r.yml": _reject_orphan("rj")})
    ok, reason = SC.evaluate_scenario(
        {"spec": "r.yml", "expect": "reject", "problem": "is not an active station"}, tmp_path)
    assert ok and reason == ""


def test_reject_accepted_is_lost_tooth(tmp_path):
    # a shape declared reject that the engine ACCEPTS = a tooth was lost.
    _write_corpus(tmp_path, [], {"v.yml": _valid("vv")})
    ok, reason = SC.evaluate_scenario({"spec": "v.yml", "expect": "reject", "problem": "x"}, tmp_path)
    assert not ok and "tooth perdido" in reason


def test_reject_for_wrong_reason_fails(tmp_path):
    _write_corpus(tmp_path, [], {"r.yml": _reject_orphan("rj2")})
    ok, reason = SC.evaluate_scenario(
        {"spec": "r.yml", "expect": "reject", "problem": "duplicate station id"}, tmp_path)
    assert not ok and "por otra razón" in reason


def test_missing_spec_fails(tmp_path):
    _write_corpus(tmp_path, [], {})
    ok, reason = SC.evaluate_scenario({"spec": "nope.yml", "expect": "valid"}, tmp_path)
    assert not ok and "no existe" in reason


# ── the diversity tooth ──────────────────────────────────────────────────────────

def _diverse_entries() -> tuple[list[dict], dict[str, dict]]:
    specs = {
        "v1.yml": _valid("v1", 1),                 # (1, flat, {})
        "v2.yml": _valid("v2", 2),                 # (2-3, linear, {})
        "v3.yml": _valid("v3", 4),                 # (4+, linear, {})
        "r1.yml": _reject_orphan("r1"),
        "r2.yml": _reject_orphan("r2"),
        "r3.yml": _reject_orphan("r3"),
    }
    entries = [
        {"spec": "v1.yml", "expect": "valid"},
        {"spec": "v2.yml", "expect": "valid"},
        {"spec": "v3.yml", "expect": "valid"},
        {"spec": "r1.yml", "expect": "reject", "problem": "is not an active station", "family": "rtm"},
        {"spec": "r2.yml", "expect": "reject", "problem": "is not an active station", "family": "schema"},
        {"spec": "r3.yml", "expect": "reject", "problem": "is not an active station", "family": "design"},
    ]
    return entries, specs


def test_diverse_corpus_passes_diversity(tmp_path):
    entries, specs = _diverse_entries()
    _write_corpus(tmp_path, entries, specs)
    ok, _ = SC.diversity(entries, tmp_path)
    assert ok


def test_too_few_valid_shapes_is_thin(tmp_path):
    entries, specs = _diverse_entries()
    # collapse the 3 valid shapes to a SINGLE structural signature → below MIN_VALID_SHAPES.
    for name in ("v2.yml", "v3.yml"):
        specs[name] = _valid(name.split(".")[0], 1)  # all (1, flat, {})
    _write_corpus(tmp_path, entries, specs)
    ok, reason = SC.diversity(entries, tmp_path)
    assert not ok and "formas VÁLIDAS distintas" in reason


def test_too_few_reject_families_is_thin(tmp_path):
    entries, specs = _diverse_entries()
    for e in entries:
        if e["expect"] == "reject":
            e["family"] = "rtm"   # one family for all → below MIN_REJECT_TEETH
    _write_corpus(tmp_path, entries, specs)
    ok, reason = SC.diversity(entries, tmp_path)
    assert not ok and "familias de tooth" in reason


def test_single_polarity_is_thin(tmp_path):
    # all-valid corpus → zero reject families → thin (an engine that accepts everything would pass).
    entries, specs = _diverse_entries()
    valid_only = [e for e in entries if e["expect"] == "valid"]
    _write_corpus(tmp_path, valid_only, {k: v for k, v in specs.items() if k.startswith("v")})
    ok, reason = SC.diversity(valid_only, tmp_path)
    assert not ok and "familias de tooth" in reason


# ── the decision ─────────────────────────────────────────────────────────────────

def test_decide_ok_on_diverse_green_corpus(tmp_path):
    entries, specs = _diverse_entries()
    _write_corpus(tmp_path, entries, specs)
    action, _ = SC.decide(tmp_path, entries)
    assert action == "ok"


def test_decide_mismatch_on_cascade(tmp_path):
    entries, specs = _diverse_entries()
    specs["v2.yml"] = _reject_orphan("v2")   # a "valid" entry the engine now refuses
    _write_corpus(tmp_path, entries, specs)
    action, detail = SC.decide(tmp_path, entries)
    assert action == "mismatch" and any("v2.yml" in d for d in detail)


def test_decide_thin_on_narrow_corpus(tmp_path):
    specs = {"v1.yml": _valid("v1"), "r1.yml": _reject_orphan("r1")}
    entries = [{"spec": "v1.yml", "expect": "valid"},
               {"spec": "r1.yml", "expect": "reject", "problem": "is not an active station", "family": "rtm"}]
    _write_corpus(tmp_path, entries, specs)
    action, _ = SC.decide(tmp_path, entries)
    assert action == "thin"


def test_decide_empty_on_empty_corpus(tmp_path):
    action, _ = SC.decide(tmp_path, [])
    assert action == "empty"


# ── the REAL shipped corpus stays green AND diverse (regression guard) ───────────

def test_real_corpus_is_green_and_diverse():
    corpus_dir, entries = SC.load_corpus(_SCENARIOS / "corpus.yml")
    action, detail = SC.decide(corpus_dir, entries)
    assert action == "ok", f"shipped corpus must be green & diverse: {action} {detail}"
    assert len(entries) >= 2 * SC.MIN_VALID_SHAPES


def test_real_corpus_spans_all_validator_families():
    _, entries = SC.load_corpus(_SCENARIOS / "corpus.yml")
    fams = {e.get("family") for e in entries if e.get("expect") == "reject"}
    assert {"schema", "substrate", "rtm", "grammar_v2", "design"} <= fams


def test_real_corpus_valid_shapes_are_structurally_distinct():
    corpus_dir, entries = SC.load_corpus(_SCENARIOS / "corpus.yml")
    sigs = {SC.shape_signature(load_spec(corpus_dir / e["spec"]))
            for e in entries if e.get("expect") == "valid"}
    valids = [e for e in entries if e.get("expect") == "valid"]
    assert len(sigs) == len(valids), f"valid scenarios must each be a distinct shape: {sigs}"


# ── the non-decorative tooth: if the engine loses a tooth, the corpus catches it ──

def test_engine_losing_a_tooth_is_caught(tmp_path, monkeypatch):
    # If `validate` became a no-op (a real cascade), a reject scenario would be ACCEPTED → mismatch.
    import metafactory.spec.validator as validator
    _write_corpus(tmp_path, [], {"r.yml": _reject_orphan("rj")})
    monkeypatch.setattr(validator, "validate", lambda spec: [])
    ok, reason = SC.evaluate_scenario(
        {"spec": "r.yml", "expect": "reject", "problem": "is not an active station"}, tmp_path)
    assert not ok and "tooth perdido" in reason
