"""H6 §4/§5 runners replayed OFFLINE: fake council outcome + fake matchers, REAL gold.

Only `execute_run` and the embed/judge calls are stubbed — the oracle loading (real
committed xlsx), the metric math, the run.json contract (the keys `eval gates` reads)
and E3's resume discipline are exercised for real.
"""

from __future__ import annotations

import json
import re

import pytest

from reqcouncil.council.pipeline import RunOutcome
from reqcouncil.council.schema import Candidate
from reqcouncil.eval.e2 import run_e2
from reqcouncil.eval.e3 import run_e3
from reqcouncil.eval.wepgcomp import load_oracle

THRESHOLDS = {
    "gates": {
        "judge_agreement": {"min": 0.8},
        "fidelity": {"min": 0.7},
        "critical_nfr_recall": {"min": 0.9},
        "cci_band": {"min": 0.6, "max": 1.6},
        "no_regression": {"max_drop_pts": 2},
    }
}


def _fake_embed(texts):
    toks = [re.findall(r"\w+", t.lower()) for t in texts]
    vocab = sorted({w for ts in toks for w in ts})
    idx = {w: i for i, w in enumerate(vocab)}
    out = []
    for ts in toks:
        v = [0.0] * len(vocab)
        for w in ts:
            v[idx[w]] += 1.0
        out.append(v)
    return out


def _cand(i: int, text: str, grounded: bool) -> Candidate:
    return Candidate(
        cand_id=f"functional-{i}", text=text, category="functional", kind="FR",
        anchors=("sha:1",), stance="explicit", rationale="r",
        proposers=("functional",), grounded=grounded, status="accepted",
    )


def _fake_outcome(produced: list[Candidate]) -> RunOutcome:
    return RunOutcome(
        transcript_sha="f" * 12,
        n_chunks=5,
        final=produced,
        draft={
            "model": "fake-model",
            "cardinality": {"produced": len(produced), "expected": 10.0,
                            "band": [6.0, 16.0], "in_band": False, "source": "inter2us"},
            "citation_coverage": 0.5,
        },
        usage={"prompt_tokens": 10, "completion_tokens": 5},
        round_log=[],
        prompt_shas={"functional": "abc"},
        store=None,
        rounds={"rounds_run": 0, "stop_reason": None, "deltas": [],
                "coverage_history": [0.5]},
        review={"engineer": "auto", "mode": "auto"},
    )


def test_e2_offline_metrics_and_contract(tmp_path, monkeypatch):
    gold = load_oracle("wepgcomp")  # the REAL committed oracle (46 items)
    produced = [
        _cand(0, gold[0].text, True),        # exact gold text -> top-1 cosine + judge YES
        _cand(1, "totally unrelated thing about llamas", True),
        _cand(2, "another unmatched requirement", False),
    ]
    monkeypatch.setattr("reqcouncil.eval.e2.execute_run",
                        lambda *a, **k: _fake_outcome(produced))

    r = run_e2(
        {}, {}, THRESHOLDS, corpus="wepgcomp", runs_dir=tmp_path / "e2",
        use_store=False,
        embed_fn=_fake_embed, judge_fn=lambda g, c: int(g == c),
    )
    assert r.n_requirements == 3
    assert r.fidelity == pytest.approx(2 / 3)
    assert r.oracle_recall == round(1 / 46, 4)
    assert r.oracle_precision == round(1 / 3, 4)
    assert r.critical_nfr_recall == 0.0    # the 6 NOTF gold went unmatched
    assert r.cci == round(3 / 46, 4)
    assert not r.green                     # nfr + cci band both red

    run = json.loads((tmp_path / "e2" / "run.json").read_text())
    # exactly the keys the gates evaluator reads (H6 §7 contract)
    for key in ("fidelity", "critical_nfr_recall", "cci", "citation_coverage",
                "oracle_recall", "oracle_precision", "green"):
        assert key in run, key
    assert run["oracle_size"] == 46
    assert run["cardinality"]["in_band"] is False  # runtime band recorded, not fatal
    assert (tmp_path / "e2" / "oracle-matches.json").is_file()
    assert (tmp_path / "e2" / "audit-sample.json").is_file()
    matches = json.loads((tmp_path / "e2" / "oracle-matches.json").read_text())
    assert len(matches["matches"]) == 46   # full per-item table, auditable


def test_e2_green_when_all_gates_pass(tmp_path, monkeypatch):
    gold = load_oracle("wepgcomp")
    # produce EVERY gold text verbatim -> recall 1.0 (incl. NFR), cci 46/46 = 1.0
    produced = [_cand(i, g.text, True) for i, g in enumerate(gold)]
    monkeypatch.setattr("reqcouncil.eval.e2.execute_run",
                        lambda *a, **k: _fake_outcome(produced))
    r = run_e2({}, {}, THRESHOLDS, corpus="wepgcomp", runs_dir=tmp_path / "e2",
               use_store=False, embed_fn=_fake_embed, judge_fn=lambda g, c: int(g == c))
    assert r.green and r.critical_nfr_recall == 1.0 and r.cci == 1.0


def test_e3_offline_summary_and_resume(tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake_execute_run(text, source, **kwargs):
        calls["n"] += 1
        return _fake_outcome([_cand(0, "req one", True), _cand(1, "req two", False)])

    monkeypatch.setattr("reqcouncil.eval.e3.execute_run", fake_execute_run)
    kw = dict(runs_dir=tmp_path / "e3", n=3, seed=7, use_store=False,
              embed_fn=_fake_embed, judge_fn=lambda g, c: 1)  # judge: everything matches

    r = run_e3({}, {}, THRESHOLDS, **kw)
    assert calls["n"] == 3
    assert r.mean_oracle_recall == 1.0        # judge said YES to everything
    assert r.mean_implicit_yield == 1.0
    assert len(r.summary["task_ids"]) == 3
    assert r.summary["usage_total"]["prompt_tokens"] == 30
    for task_id in r.summary["task_ids"]:
        d = tmp_path / "e3" / task_id
        assert (d / "run.json").is_file() and (d / "oracle-matches.json").is_file()
    assert (tmp_path / "e3" / "summary.json").is_file()

    # resume: everything already on disk -> zero new council runs, same summary
    r2 = run_e3({}, {}, THRESHOLDS, **kw)
    assert calls["n"] == 3                    # unchanged: nothing re-paid
    assert r2.summary["task_ids"] == r.summary["task_ids"]
    assert r2.mean_oracle_recall == r.mean_oracle_recall


def test_e3_sample_is_deterministic_and_stratified(tmp_path, monkeypatch):
    seen: list[str] = []

    def fake_execute_run(text, source, **kwargs):
        seen.append(source)
        return _fake_outcome([_cand(0, "req", True)])

    monkeypatch.setattr("reqcouncil.eval.e3.execute_run", fake_execute_run)
    run_e3({}, {}, THRESHOLDS, runs_dir=tmp_path / "a", n=5, seed=7, use_store=False,
           embed_fn=_fake_embed, judge_fn=lambda g, c: 1)
    first = list(seen)
    seen.clear()
    run_e3({}, {}, THRESHOLDS, runs_dir=tmp_path / "b", n=5, seed=7, use_store=False,
           embed_fn=_fake_embed, judge_fn=lambda g, c: 1)
    assert seen == first                      # same sample, byte-stable order
