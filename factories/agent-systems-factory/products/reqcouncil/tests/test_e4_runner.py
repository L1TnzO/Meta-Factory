"""H6 §6 E4 runner replayed OFFLINE: fake chat/judges, REAL gold, real chunking.

Only the network is stubbed (chat + judges + embeddings). The int1 gold loader, the
anchored single-pass parse (STRICT: malformed twice = loud error), the Layer-2 metric
math, the (c) k_max=0 config stripping, the (d) reuse/pending discipline, the resume
rule (a written cell is never re-paid) and the table/report artifacts run for real.
"""

from __future__ import annotations

import json
import re
from types import SimpleNamespace

import pytest

from reqcouncil.council.schema import CandidateParseError
from reqcouncil.eval.e4 import (
    load_interview_golden,
    run_e4,
    run_single_pass,
    strip_rounds,
)

COUNCIL_CFG = {"rounds": {"k_max": 4}, "temperatures": {"analyst": 0.7},
               "verify": {"max_anchors_judged": 3}}


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


class FakeChat:
    """Scripted chat: replays `replies` in order (last one repeats), counts calls."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0
        self.model = "fake-model"

    def complete(self, messages, **kwargs):
        self.calls += 1
        content = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return SimpleNamespace(content=content, prompt_tokens=100, completion_tokens=20)


def _single_pass_kwargs(tmp_path, chat, match_judge=None):
    return dict(
        arm="a", corpus="interview", runs_dir=tmp_path / "a-interview",
        chat=chat, ground_judge_fn=lambda story, chunk: 1,
        embed_fn=_fake_embed,
        match_judge_fn=match_judge or (lambda g, c: int(g == c)),
    )


def test_interview_golden_loads_the_37_stories():
    gold = load_interview_golden()  # the REAL committed user_stories.csv
    assert len(gold) == 37
    assert all(not g.is_nfr for g in gold)          # no NFR labels in this gold
    assert gold[0].id == "US0" and gold[0].text


def test_interview_golden_refuses_wrong_count(tmp_path):
    d = tmp_path / "public_interview"
    d.mkdir(parents=True)
    (d / "user_stories.csv").write_text(
        '"User Story"\n"one"\n"two"\n"three"\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="expected 37"):
        load_interview_golden(tmp_path)


def test_single_pass_offline_metrics_and_contract(tmp_path):
    gold = load_interview_golden()
    reply = json.dumps([
        {"text": gold[0].text, "kind": "FR", "stance": "explicit",
         "anchors": ["c0"], "rationale": "r"},
        {"text": "totally unrelated llama requirement", "kind": "NFR",
         "stance": "explicit", "anchors": [], "rationale": "r"},  # -> demoted, ungrounded
    ])
    chat = FakeChat([reply])
    row = run_single_pass({}, COUNCIL_CFG, **_single_pass_kwargs(tmp_path, chat))

    assert chat.calls == 1                          # ONE call: the whole point of (a)
    assert row["n_requirements"] == 2
    assert row["n_chunks"] == 132                   # real int1 chunking (E1 parity)
    assert row["fidelity"] == 0.5                   # c0 supported; no-anchor cand isn't
    assert row["coverage"] == round(1 / 132, 4)     # cited chunks / chunks
    assert row["oracle_recall"] == round(1 / 37, 4)
    assert row["oracle_precision"] == 0.5
    assert row["critical_nfr_recall"] is None       # interview gold carries no NFR flag
    assert row["cci"] == round(2 / 37, 4) and row["oracle_size"] == 37
    assert row["usage"] == {"prompt_tokens": 100, "completion_tokens": 20}
    assert any(e["event"] == "demoted_to_inferred" for e in row["parse_log"])

    cell = tmp_path / "a-interview"
    run = json.loads((cell / "run.json").read_text())
    for key in ("arm", "corpus", "status", "fidelity", "coverage", "oracle_recall",
                "oracle_precision", "critical_nfr_recall", "cci", "usage"):
        assert key in run, key
    assert (cell / "oracle-matches.json").is_file()
    assert (cell / "audit-sample.json").is_file()


def test_single_pass_malformed_twice_raises_loudly(tmp_path):
    chat = FakeChat(["this is not json at all"])
    with pytest.raises(CandidateParseError):
        run_single_pass({}, COUNCIL_CFG, **_single_pass_kwargs(tmp_path, chat))
    assert chat.calls == 2                          # 1 call + 1 corrective retry, no cope
    assert not (tmp_path / "a-interview" / "run.json").exists()  # nothing fake persisted


def test_single_pass_resume_never_repays(tmp_path):
    gold = load_interview_golden()
    reply = json.dumps([{"text": gold[0].text, "kind": "FR", "stance": "explicit",
                         "anchors": ["c0"], "rationale": "r"}])
    first = FakeChat([reply])
    row = run_single_pass({}, COUNCIL_CFG, **_single_pass_kwargs(tmp_path, first))
    assert first.calls == 1

    second = FakeChat([reply])
    row2 = run_single_pass({}, COUNCIL_CFG, **_single_pass_kwargs(tmp_path, second))
    assert second.calls == 0                        # a written cell is never re-paid
    assert row2 == row

    # killed AFTER generation, BEFORE the cell closed: the checkpointed board resumes —
    # the generation call (and its T=0.7 re-roll) is never re-paid either
    cell = tmp_path / "a-interview"
    (cell / "run.json").unlink()
    assert (cell / "generation.json").is_file()
    third = FakeChat(["would not parse"])           # would explode if actually called
    row3 = run_single_pass({}, COUNCIL_CFG, **_single_pass_kwargs(tmp_path, third))
    assert third.calls == 0                         # board rebuilt from the checkpoint
    assert row3["oracle_recall"] == row["oracle_recall"]
    assert row3["usage"] == row["usage"]            # generation cost pinned, not re-paid


def test_run_e4_reuse_pending_and_kmax_sensitivity(tmp_path):
    gold = load_interview_golden()
    pin = tmp_path / "pin-e1"
    pin.mkdir()
    (pin / "run.json").write_text(json.dumps({
        "model": "pin-model", "n_chunks": 132, "fidelity": 0.9,
        "citation_coverage": 0.6,
        "usage": {"prompt_tokens": 1000, "completion_tokens": 50},
        "rounds": {"rounds_run": 2, "stop_reason": "coverage_plateau",
                   "coverage_history": [0.4, 0.6, 0.6]},
    }))
    (pin / "draft.json").write_text(json.dumps({"requirements": [
        {"text": gold[0].text, "grounded": True},
        {"text": "an unmatched requirement", "grounded": False},
    ]}))
    judge_calls = {"n": 0}

    def match_judge(g, c):
        judge_calls["n"] += 1
        return int(g == c)

    kwargs = dict(
        runs_dir=tmp_path / "e4", arms=("d",),
        corpora=("interview", "wepgcomp", "maislugar"),
        embed_fn=_fake_embed, match_judge_fn=match_judge,
        sources={("d", "interview"): pin,
                 ("d", "wepgcomp"): tmp_path / "missing-w",
                 ("d", "maislugar"): tmp_path / "missing-m"},
    )
    r = run_e4({}, COUNCIL_CFG, {}, **kwargs)

    by_cell = {(row["arm"], row["corpus"]): row for row in r.rows}
    reused = by_cell[("d", "interview")]
    assert reused["status"] == "reused" and reused["source"] == str(pin)
    assert reused["n_requirements"] == 2
    assert reused["fidelity"] == 0.9 and reused["coverage"] == 0.6  # from the pin
    assert reused["oracle_recall"] == round(1 / 37, 4)              # post-hoc matching
    assert reused["cci"] == round(2 / 37, 4)
    assert reused["usage"]["prompt_tokens"] == 1000  # what the condition cost WHEN run
    assert by_cell[("d", "wepgcomp")]["status"] == "pending"
    assert by_cell[("d", "maislugar")]["status"] == "pending"
    assert r.pending == 2

    s = r.table["kmax_sensitivity"]
    assert s["early_stop_observed"] and s["early_stop_cells"] == ["d-interview"]
    assert (tmp_path / "e4" / "e4-table.json").is_file()
    report = (tmp_path / "e4" / "report.txt").read_text()
    assert "pending" in report and "EARLY STOP" in report

    # resume: the reused cell's matching is cached on disk, never re-paid
    paid = judge_calls["n"]
    r2 = run_e4({}, COUNCIL_CFG, {}, **kwargs)
    assert judge_calls["n"] == paid
    assert r2.rows[0]["oracle_recall"] == reused["oracle_recall"]


def test_arm_c_strips_rounds_and_adapts_e2_run(tmp_path, monkeypatch):
    captured = {}

    def fake_run_e2(models_cfg, council_cfg, thresholds, *, corpus, runs_dir, **kw):
        captured["cfg"] = council_cfg
        runs_dir.mkdir(parents=True, exist_ok=True)
        (runs_dir / "run.json").write_text(json.dumps({
            "model": "m", "n_chunks": 5, "n_requirements": 3, "fidelity": 0.8,
            "citation_coverage": 0.4, "oracle_recall": 0.1, "oracle_precision": 0.2,
            "critical_nfr_recall": 0.0, "cci": 0.5, "oracle_size": 46,
            "usage": {"prompt_tokens": 1, "completion_tokens": 2},
            "rounds": {"rounds_run": 0, "stop_reason": None, "deltas": [],
                       "coverage_history": [0.4]},
        }))

    monkeypatch.setattr("reqcouncil.eval.e4.run_e2", fake_run_e2)
    r = run_e4({}, COUNCIL_CFG, {}, runs_dir=tmp_path / "e4", arms=("c",),
               corpora=("wepgcomp",), embed_fn=_fake_embed,
               match_judge_fn=lambda g, c: 1)

    assert "rounds" not in captured["cfg"]          # k_max=0 spelled as the missing key
    assert "rounds" in COUNCIL_CFG                  # the caller's config is untouched
    assert strip_rounds(COUNCIL_CFG)["temperatures"] == COUNCIL_CFG["temperatures"]
    row = r.rows[0]
    assert row["status"] == "measured" and row["coverage"] == 0.4
    assert row["arm_label"].startswith("council w/o critics")
    assert r.table["kmax_sensitivity"]["cells"] == []  # rounds_run 0: not deliberating
