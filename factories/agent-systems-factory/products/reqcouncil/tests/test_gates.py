"""H6 §7 gates evaluator — the CI tooth (real pins) + fake green/red/waived/n-a cases.

`test_real_pins` IS the exit-gate semantics of design/04 §3 running in CI: every gate over
the COMMITTED `runs/pinned/**` must be green, waived-with-reason, or explicitly-pending
n/a — a silent red in the repo fails the suite. The fake cases pin each verdict path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from reqcouncil.config import load_thresholds
from reqcouncil.eval.gates import evaluate_gates, load_waivers, parse_index

THRESHOLDS = {
    "gates": {
        "judge_agreement": {"min": 0.8},
        "fidelity": {"min": 0.7},
        "critical_nfr_recall": {"min": 0.9},
        "cci_band": {"min": 0.6, "max": 1.6},
        "no_regression": {"max_drop_pts": 2},
    }
}

INDEX = """\
| experiment | pin | previous_green | gated | note |
|---|---|---|---|---|
| E0 | e0 | - | yes | calibration |
| E1 | e1 | e1-base | yes | council |
| E2-wepgcomp | - | - | yes | pending: E2 not yet run |
| E2-maislugar | - | - | yes | pending: E2 not yet run |
"""


def _pin(root: Path, name: str, payload: dict) -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "run.json").write_text(json.dumps(payload), encoding="utf-8")


def _fixture(tmp_path: Path, *, e1_fidelity=0.95, e1_cci=1.1, index: str = INDEX) -> Path:
    root = tmp_path / "pinned"
    root.mkdir(parents=True)
    (root / "INDEX.md").write_text(index, encoding="utf-8")
    _pin(root, "e0", {"agreement": 0.9, "green": True})
    _pin(root, "e1", {"fidelity": e1_fidelity, "cci_vs_37_golden": e1_cci,
                      "citation_coverage": 0.6, "green": True})
    _pin(root, "e1-base", {"fidelity": 0.96, "cci_vs_37_golden": 1.5,
                           "citation_coverage": 0.55, "green": True})
    return root


# --- the CI tooth: committed pins must satisfy the exit contract -----------------------

def test_real_pins_no_silent_red():
    result = evaluate_gates(load_thresholds())
    assert result.green, result.report
    for v in result.verdicts:
        assert v.verdict in {"green", "waived", "n/a"}, result.report
        if v.verdict in {"waived", "n/a"}:
            assert v.reason  # written reason, never a silent hole
    by = {(v.gate, v.target): v.verdict for v in result.verdicts}
    assert by[("judge_agreement", "E0")] == "green"
    assert by[("fidelity", "E1")] == "green"
    assert by[("cci_band", "E1")] == "green"
    assert by[("no_regression", "E1")] == "green"   # vs e1-dsv4flash, drop <= 2pts
    # E2 pinned 2026-07-06 (H6): fidelity green on both corpora; the measured reds
    # (nfr_recall x2, cci_band wepgcomp) are WAIVED with written reasons in
    # thresholds.yml — first-class, never silent.
    assert by[("fidelity", "E2-wepgcomp")] == "green"
    assert by[("fidelity", "E2-maislugar")] == "green"
    assert by[("critical_nfr_recall", "E2-wepgcomp")] == "waived"
    assert by[("critical_nfr_recall", "E2-maislugar")] == "waived"
    assert by[("cci_band", "E2-wepgcomp")] == "waived"
    assert by[("cci_band", "E2-maislugar")] == "green"
    assert by[("no_regression", "E2-wepgcomp")] == "n/a"  # first pin, no base yet


# --- verdict paths over the synthetic fixture -------------------------------------------

def test_fake_all_green_and_pending_na(tmp_path):
    r = evaluate_gates(THRESHOLDS, pinned_dir=_fixture(tmp_path))
    assert r.green
    by = {(v.gate, v.target): v for v in r.verdicts}
    assert by[("fidelity", "E1")].verdict == "green"
    assert by[("no_regression", "E0")].verdict == "n/a"  # no previous_green registered
    na = by[("critical_nfr_recall", "E2-maislugar")]
    assert na.verdict == "n/a" and "pending" in na.reason


def test_fake_red_blocks(tmp_path):
    r = evaluate_gates(THRESHOLDS, pinned_dir=_fixture(tmp_path, e1_fidelity=0.5))
    assert not r.green
    by = {(v.gate, v.target): v.verdict for v in r.verdicts}
    assert by[("fidelity", "E1")] == "red"


def test_fake_waiver_turns_red_into_waived_with_reason(tmp_path):
    # e1_fidelity=0.5 trips BOTH fidelity and no_regression: each red needs its OWN
    # written reason — one waiver does not blanket the experiment.
    one_waiver = {
        **THRESHOLDS,
        "waivers": [{"gate": "fidelity", "corpus": "E1",
                     "reason": "known judge blind spot", "date": "2026-07-06"}],
    }
    r = evaluate_gates(one_waiver, pinned_dir=_fixture(tmp_path / "a", e1_fidelity=0.5))
    assert not r.green  # no_regression E1 is still an unwaived red
    v = next(v for v in r.verdicts if (v.gate, v.target) == ("fidelity", "E1"))
    assert v.verdict == "waived" and "known judge blind spot" in v.reason

    both = {
        **THRESHOLDS,
        "waivers": [
            {"gate": "fidelity", "corpus": "E1",
             "reason": "known judge blind spot", "date": "2026-07-06"},
            {"gate": "no_regression", "corpus": "E1",
             "reason": "accepted reset after judge change", "date": "2026-07-06"},
        ],
    }
    r = evaluate_gates(both, pinned_dir=_fixture(tmp_path / "b", e1_fidelity=0.5))
    assert r.green  # waived does not block
    assert r.unused_waivers == []


def test_fake_stale_waiver_is_surfaced(tmp_path):
    thresholds = {
        **THRESHOLDS,
        "waivers": [{"gate": "fidelity", "corpus": "E1",
                     "reason": "stale", "date": "2026-07-06"}],
    }
    r = evaluate_gates(thresholds, pinned_dir=_fixture(tmp_path))  # E1 is green
    assert r.unused_waivers and "STALE WAIVER" in r.report


def test_fake_cci_band_two_sided(tmp_path):
    r = evaluate_gates(THRESHOLDS, pinned_dir=_fixture(tmp_path, e1_cci=2.1))
    v = next(v for v in r.verdicts if (v.gate, v.target) == ("cci_band", "E1"))
    assert v.verdict == "red"


def test_fake_no_regression_red_names_the_metric(tmp_path):
    # base fidelity 0.96 -> current 0.90: drop 6pts > 2pts
    r = evaluate_gates(THRESHOLDS, pinned_dir=_fixture(tmp_path, e1_fidelity=0.90))
    v = next(v for v in r.verdicts if (v.gate, v.target) == ("no_regression", "E1"))
    assert v.verdict == "red" and "fidelity" in v.reason


# --- the registry and the waiver block REFUSE malformed data ----------------------------

def test_index_missing_gated_experiment_raises(tmp_path):
    bad = INDEX.replace("| E2-maislugar | - | - | yes | pending: E2 not yet run |\n", "")
    root = _fixture(tmp_path, index=bad)
    with pytest.raises(ValueError, match="gated experiments"):
        evaluate_gates(THRESHOLDS, pinned_dir=root)


def test_index_registered_pin_must_exist_on_disk(tmp_path):
    root = _fixture(tmp_path)
    (root / "e1" / "run.json").unlink()
    with pytest.raises(ValueError, match="missing"):
        evaluate_gates(THRESHOLDS, pinned_dir=root)


def test_index_previous_green_must_be_green(tmp_path):
    root = _fixture(tmp_path)
    base = root / "e1-base" / "run.json"
    payload = json.loads(base.read_text())
    payload["green"] = False
    base.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="not a green pin"):
        evaluate_gates(THRESHOLDS, pinned_dir=root)


def test_index_bad_header_raises(tmp_path):
    root = _fixture(tmp_path, index=INDEX.replace("previous_green", "prev"))
    with pytest.raises(ValueError, match="header"):
        parse_index(root / "INDEX.md")


def test_waiver_unknown_gate_or_corpus_raises():
    with pytest.raises(ValueError, match="unknown gate"):
        load_waivers({"waivers": [{"gate": "typo", "corpus": "E1",
                                   "reason": "r", "date": "d"}]})
    with pytest.raises(ValueError, match="unknown corpus"):
        load_waivers({"waivers": [{"gate": "fidelity", "corpus": "E9",
                                   "reason": "r", "date": "d"}]})
    with pytest.raises(ValueError, match="non-empty"):
        load_waivers({"waivers": [{"gate": "fidelity", "corpus": "E1", "reason": ""}]})
