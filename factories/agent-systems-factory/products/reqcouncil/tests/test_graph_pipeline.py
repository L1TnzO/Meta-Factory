"""H3/H4 gate — the WHOLE pipeline offline: ingest -> LangGraph -> draft + store.

Zero network: FakeChat serves canned analyst JSON + an id-echoing synthesizer; the
embedder is one-hot-by-first-seen-text (identical text => cos 1, distinct => 0); the
judge grounds anything mentioning "log in". The store leg runs on a REAL ephemeral
Postgres (skip only if binaries are missing).

H4 adds the multi-round deliberation arm: a STATEFUL MultiRoundChat serves critics and
rebuttals per round — round 1 objects + fills the coverage residue, round 2 is quiet, so
the run must stop on `fixed_point` (and the gap hunter must NOT be called on an empty
residue — asserted by call counter). The k_max=0 tests above ARE the H3 regression.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("langgraph", reason="[council] extra not installed")

from reqcouncil.council.pipeline import execute_run  # noqa: E402
from reqcouncil.llm import ChatResult  # noqa: E402
from reqcouncil.review import auto_reviewer  # noqa: E402  (H5: hitl is non-skippable)

TRANSCRIPT = (
    "[0:00:00] spk_0: We need members to log in with a password.\n"
    "[0:00:05] spk_1: Also we want monthly reports for the board.\n"
)
# 2 merged turns -> chunks c0 (both turns) and c1 (tail turn).

FUNCTIONAL_JSON = json.dumps([
    {"text": "As a member, I want to log in with a password, so that my data is protected.",
     "kind": "FR", "anchors": ["c0"], "stance": "explicit", "rationale": "stated"},
    {"text": "As a board member, I want monthly reports, so that I can track the club.",
     "kind": "FR", "anchors": ["c1"], "stance": "explicit", "rationale": "stated"},
])
DATA_JSON = json.dumps([
    # Byte-identical to functional's first candidate -> MUST dedup-merge.
    {"text": "As a member, I want to log in with a password, so that my data is protected.",
     "kind": "FR", "anchors": ["c0", "c1"], "stance": "explicit", "rationale": "dup"},
    {"text": "The system stores member records with contact details.",
     "kind": "NFR", "anchors": [], "stance": "inferred", "rationale": "implied"},
])


class FakeChat:
    model = "fake-model"
    api_base = "local"

    def complete(self, messages, *, temperature, max_completion_tokens=None,
                 reasoning_effort=None):
        system = messages[0]["content"]
        if "Synthesizer" in system:
            payload = messages[1]["content"].split("\n", 1)[1]
            items = json.loads(payload)
            echo = [{"id": it["id"], "text": "NORM " + it["text"], "kind": it["kind"]}
                    for it in items]
            return ChatResult(json.dumps(echo), "stop", 10, 5)
        if "Functional Analyst" in system:
            return ChatResult(FUNCTIONAL_JSON, "stop", 10, 5)
        if "Data Analyst" in system:
            return ChatResult(DATA_JSON, "stop", 10, 5)
        raise AssertionError(f"unexpected persona: {system[:60]}")


def one_hot_embed():
    seen: dict[str, int] = {}

    def embed(texts):
        vecs = []
        for t in texts:
            idx = seen.setdefault(t, len(seen))
            vec = [0.0] * 16
            vec[idx % 16] = 1.0
            vecs.append(vec)
        return vecs

    return embed


def fake_judge(story: str, chunk: str) -> int:
    return 1 if "log in" in story else 0


COUNCIL_CFG = {
    "analysts": ["functional", "data"],
    "temperatures": {"analyst": 0.7, "synthesizer": 0.2},
    "dedup": {"tau_dup": 0.88},
    "verify": {"max_anchors_judged": 3},
    "cardinality_band": {"source": "inter2us", "golden_stories": 37, "golden_chunks": 132},
}
THRESHOLDS = {"gates": {"cci_band": {"min": 0.6, "max": 1.6}, "fidelity": {"min": 0.7}}}


def _run(tmp_path, dsn=None, reviewer=auto_reviewer):
    # H5: hitl is zero-LLM, so passing the unattended reviewer keeps every H3/H4
    # assertion (usage, events, store rows) byte-for-byte valid.
    return execute_run(
        TRANSCRIPT, "tiny", models_cfg={}, council_cfg=COUNCIL_CFG,
        thresholds=THRESHOLDS, runs_dir=tmp_path / "run", dsn=dsn,
        chat=FakeChat(), embed_fn=one_hot_embed(), judge_fn=fake_judge,
        reviewer=reviewer,
    )


def test_offline_end_to_end(tmp_path):
    out = _run(tmp_path)
    assert out.n_chunks == 2
    # 4 proposals, 1 exact duplicate -> 3 final.
    assert len(out.final) == 3
    dup = next(c for c in out.final if "log in" in c.text)
    assert set(dup.proposers) == {"functional", "data"}
    assert len(dup.anchors) == 2  # union of c0 + (c0,c1)
    assert dup.grounded and dup.status == "accepted"
    # Judge fake refuses everything else -> statuses split.
    reports = next(c for c in out.final if "reports" in c.text)
    assert not reports.grounded and reports.status == "unsupported"
    inferred = next(c for c in out.final if "records" in c.text)
    assert inferred.status == "flagged_inferred" and inferred.confidence == 0.0
    # Worst-first: accepted goes LAST.
    assert out.final[-1].cand_id == dup.cand_id
    # Synthesizer normalization applied, ids preserved.
    assert all(c.text.startswith("NORM ") for c in out.final)
    # Usage accounted: 3 LLM calls x (10, 5).
    assert out.usage == {"prompt_tokens": 30, "completion_tokens": 15}
    # Events: 2 propose + merge + verify + synthesize.
    actions = [e["action"] for e in out.round_log]
    assert actions.count("propose") == 2
    for action in ("merge", "verify", "synthesize"):
        assert action in actions
    # Draft on disk with the run-report self-checks.
    draft = json.loads((tmp_path / "run" / "draft.json").read_text())
    assert draft["citation_coverage"] == 1.0 and len(draft["requirements"]) == 3
    assert draft["prompt_shas"].keys() >= {"functional", "data", "synthesizer"}


def test_offline_end_to_end_with_store(tmp_path):
    from reqcouncil.store import binaries_available, ephemeral_postgres
    if not binaries_available():
        pytest.skip("initdb/pg_ctl not on PATH")
    from reqcouncil.store import dao

    with ephemeral_postgres() as dsn:
        out = _run(tmp_path, dsn=dsn)
        assert out.store is not None and out.store["requirements"] == 3
        with dao.connect(dsn) as conn:
            reqs = dao.requirements_for_run(conn, out.store["run_id"])
            assert len(reqs) == 3
            grounded = [r for r in reqs if r["grounded"]]
            assert len(grounded) == 1
            trace = dao.trace_requirement(conn, grounded[0]["req_id"])
            assert len(trace) == 2  # both judged anchors persisted as evidence
            assert {t["verdict"] for t in trace} == {"supported"}
            assert trace[0]["source"] == "tiny"


# --- H4: the multi-round deliberation arm (work/H4 §Gates) ---------------------------

# Round 0 cites ONLY c0 -> the coverage residue is [c1] for the gap hunter to fill.
MR_FUNCTIONAL_JSON = json.dumps([
    {"text": "As a member, I want to log in with a password, so that my data is protected.",
     "kind": "FR", "anchors": ["c0"], "stance": "explicit", "rationale": "stated"},
])
MR_DATA_JSON = json.dumps([
    {"text": "The system stores member records with contact details.",
     "kind": "FR", "anchors": ["c0"], "stance": "explicit", "rationale": "implied"},
])
GAP_JSON = json.dumps([
    {"text": "As a board member, I want monthly reports, so that I can track the club.",
     "kind": "FR", "anchors": ["c1"], "stance": "explicit", "rationale": "residue"},
])
SKEPTIC_R1_JSON = json.dumps([
    {"kind": "ungrounded", "targets": ["data-0"], "anchors": ["c0"],
     "quote": "log in with a password",
     "rationale": "the cited chunk never mentions member records"},
])
DATA_REBUTTAL_JSON = json.dumps([
    {"id": "data-0", "answer": "DROP", "reason": "conceded, not in the transcript"},
])


class MultiRoundChat:
    """Stateful fake: analysts round 0, then per-round critic/rebuttal scripts.

    Round 1: skeptic objects `ungrounded` at data-0 (verbatim c0 quote), the gap hunter
    proposes the missing c1 requirement, the data owner concedes (DROP). Round 2: both
    objection critics return [] and the residue is empty, so the ONLY correct behavior
    is gap_hunter staying uncalled and the controller stopping on fixed_point.
    """

    model = "fake-model"
    api_base = "local"

    def __init__(self):
        self.calls = {"functional": 0, "data": 0, "gap_hunter": 0,
                      "conflict_detector": 0, "evidence_skeptic": 0,
                      "rebuttal": 0, "synthesizer": 0}

    def _hit(self, name):
        self.calls[name] += 1
        return self.calls[name]

    def complete(self, messages, *, temperature, max_completion_tokens=None,
                 reasoning_effort=None):
        system = messages[0]["content"]
        # Dispatch on each persona's OPENING line, not a bare substring: the skeptic's
        # charter mentions "the Synthesizer owns wording", which a loose `"Synthesizer"
        # in system` match mis-routed to the synthesizer branch (latent, caught red).
        if "You are the **Synthesizer**" in system:
            self._hit("synthesizer")
            payload = messages[1]["content"].split("\n", 1)[1]
            echo = [{"id": it["id"], "text": "NORM " + it["text"], "kind": it["kind"]}
                    for it in json.loads(payload)]
            return ChatResult(json.dumps(echo), "stop", 10, 5)
        if "Rebuttal contract" in system:  # BEFORE analysts: charter + rebuttal contract
            self._hit("rebuttal")
            assert "Data Analyst" in system  # only data owns an objected candidate
            return ChatResult(DATA_REBUTTAL_JSON, "stop", 10, 5)
        if "Gap Hunter" in system:
            n = self._hit("gap_hunter")
            return ChatResult(GAP_JSON if n == 1 else "[]", "stop", 10, 5)
        if "Conflict Detector" in system:
            self._hit("conflict_detector")
            return ChatResult("[]", "stop", 10, 5)
        if "Evidence Skeptic" in system:
            n = self._hit("evidence_skeptic")
            return ChatResult(SKEPTIC_R1_JSON if n == 1 else "[]", "stop", 10, 5)
        if "Functional Analyst" in system:
            self._hit("functional")
            return ChatResult(MR_FUNCTIONAL_JSON, "stop", 10, 5)
        if "Data Analyst" in system:
            self._hit("data")
            return ChatResult(MR_DATA_JSON, "stop", 10, 5)
        raise AssertionError(f"unexpected persona: {system[:60]}")


def mr_judge(story: str, chunk: str) -> int:
    return 1 if ("log in" in story or "reports" in story) else 0


MR_COUNCIL_CFG = {
    **COUNCIL_CFG,
    "critics": ["gap_hunter", "conflict_detector", "evidence_skeptic"],
    "temperatures": {**COUNCIL_CFG["temperatures"], "critic": 0.3, "rebuttal": 0.3},
    "rounds": {"k_max": 4, "epsilon": 0.01, "plateau_rounds": 2},
}


def _run_multiround(tmp_path, dsn=None):
    chat = MultiRoundChat()
    out = execute_run(
        TRANSCRIPT, "tiny", models_cfg={}, council_cfg=MR_COUNCIL_CFG,
        thresholds=THRESHOLDS, runs_dir=tmp_path / "run", dsn=dsn,
        chat=chat, embed_fn=one_hot_embed(), judge_fn=mr_judge,
        reviewer=auto_reviewer,
    )
    return out, chat


def test_multiround_deliberation_to_fixed_point(tmp_path):
    out, chat = _run_multiround(tmp_path)

    # Round 1 acted (gap added + data-0 dropped), round 2 was a fixed point.
    assert out.rounds["rounds_run"] == 2
    assert out.rounds["stop_reason"] == "fixed_point"
    zero = {"added": 0, "dropped": 0, "merged": 0, "revised": 0,
            "demoted": 0, "conflicts": 0}
    assert out.rounds["deltas"] == [{**zero, "added": 1, "dropped": 1}, zero]
    # Baseline (c0 only) -> full coverage after the gap hunter -> flat.
    assert out.rounds["coverage_history"] == [0.5, 1.0, 1.0]

    # The board: data-0 conceded away, the gap candidate entered and got verified.
    ids = {c.cand_id for c in out.final}
    assert ids == {"functional-0", "gap_hunter-r1-0"}
    assert all(c.grounded and c.status == "accepted" for c in out.final)
    assert all(c.text.startswith("NORM ") for c in out.final)

    # The teeth: empty residue => the gap hunter is NOT called in round 2.
    assert chat.calls["gap_hunter"] == 1
    assert chat.calls["evidence_skeptic"] == 2 and chat.calls["conflict_detector"] == 2
    assert chat.calls["rebuttal"] == 1  # round 2 has no open objections -> no call
    assert chat.calls["synthesizer"] == 1
    # 2 analysts + 3 critics(r1) + 1 rebuttal + 2 critics(r2) + 1 synth = 9 x (10, 5).
    assert out.usage == {"prompt_tokens": 90, "completion_tokens": 45}

    # The trail: objections and per-round convergence decisions are first-class events.
    actions = [(e["round"], e["action"]) for e in out.round_log]
    assert (1, "object") in actions
    assert (1, "converge") in actions and (2, "converge") in actions
    resolutions = [e for e in out.round_log if e["action"] == "vote"
                   and e["persona"] == "moderator"]
    assert resolutions[0]["payload"]["resolutions"][0]["resolution"] == "owner_dropped"

    # The draft self-reports the deliberation.
    draft = json.loads((tmp_path / "run" / "draft.json").read_text())
    assert draft["rounds"]["rounds_run"] == 2
    assert draft["rounds"]["stop_reason"] == "fixed_point"
    assert draft["citation_coverage"] == 1.0
    assert draft["prompt_shas"].keys() >= {
        "gap_hunter", "conflict_detector", "evidence_skeptic",
        "functional:rebuttal", "data:rebuttal", "gap_hunter:rebuttal",
    }


def test_multiround_with_store_persists_object_and_converge(tmp_path):
    from reqcouncil.store import binaries_available, ephemeral_postgres
    if not binaries_available():
        pytest.skip("initdb/pg_ctl not on PATH")
    from reqcouncil.store import dao

    with ephemeral_postgres() as dsn:
        out, _chat = _run_multiround(tmp_path, dsn=dsn)
        assert out.store is not None and out.store["requirements"] == 2
        with dao.connect(dsn) as conn:
            rows = conn.execute(
                "SELECT round, action FROM council_event WHERE run_id = %s",
                (out.store["run_id"],),
            ).fetchall()
        events = {(r[0], r[1]) for r in rows}
        # H4 actions survive the schema CHECK and land with their REAL round number.
        assert (1, "object") in events
        assert (1, "converge") in events and (2, "converge") in events
        assert (1, "vote") in events and (1, "drop") in events
