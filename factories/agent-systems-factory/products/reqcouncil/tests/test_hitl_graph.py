"""H5 gate — the non-skippable HITL checkpoint (design/00 property #2, design/02 §4).

STRUCTURAL: in BOTH arms (k_max=0 and k_max>0) the only compiled edge into END leaves
`finalize` and the only edge into `finalize` leaves `hitl` — no path finalizes without
the interrupt. BEHAVIORAL: no resume => interrupted, nothing finalized; reviewer=None
=> execute_run refuses BEFORE running; invalid decisions => RE-interrupt with errors;
edit/reject land on the board and (with a real ephemeral Postgres) as VERSIONED rows —
v1 = the machine's claim, v2 supersedes it, evidence + review_decision hang off v1.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("langgraph", reason="[council] extra not installed")

from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.types import Command  # noqa: E402

from reqcouncil.council.personas import load_analysts, load_critics, load_synthesizer  # noqa: E402
from reqcouncil.council.pipeline import execute_run  # noqa: E402
from reqcouncil.graph import CouncilDeps, build_council  # noqa: E402
from reqcouncil.review.decisions import HUMAN_EDITED  # noqa: E402

from .test_graph_pipeline import (  # noqa: E402
    COUNCIL_CFG, MR_COUNCIL_CFG, THRESHOLDS, TRANSCRIPT,
    FakeChat, fake_judge, one_hot_embed,
)

END = "__end__"
TAGGED = [("c0", "We need members to log in with a password."),
          ("c1", "Also we want monthly reports for the board.")]
TAG_TO_ANCHOR = {"c0": "sha0:0", "c1": "sha0:1"}
ANCHOR_TEXTS = {"sha0:0": TAGGED[0][1], "sha0:1": TAGGED[1][1]}
INITIAL = {"candidates": [], "round_log": [], "usage": {},
           "objections": [], "resolutions": [], "round": 0,
           "coverage_history": [], "stop": ""}


def _deps(council_cfg, critics=()):
    return CouncilDeps(
        chat=FakeChat(), embed_fn=one_hot_embed(), judge_fn=fake_judge,
        analysts=load_analysts(["functional", "data"]), synthesizer=load_synthesizer(),
        tagged_chunks=TAGGED, tag_to_anchor=TAG_TO_ANCHOR, anchor_texts=ANCHOR_TEXTS,
        council_cfg=council_cfg, thresholds=THRESHOLDS,
        critics=list(critics),
    )


def _accept_all(packet, engineer="enzo", mode="scripted"):
    return {"engineer": engineer, "mode": mode,
            "decisions": {item["id"]: {"decision": "accept", "reason": "checked"}
                          for item in packet["items"]}}


# --- STRUCTURAL non-skippability (reachability, not convention) ------------------------

@pytest.mark.parametrize("arm", ["k0", "kN"])
def test_only_path_to_end_is_hitl_finalize(arm):
    if arm == "k0":
        app = build_council(_deps(COUNCIL_CFG))
    else:
        app = build_council(_deps(
            MR_COUNCIL_CFG,
            critics=load_critics(["gap_hunter", "conflict_detector", "evidence_skeptic"]),
        ))
    edges = app.get_graph().edges
    into_end = [e for e in edges if e.target == END]
    assert [e.source for e in into_end] == ["finalize"]
    into_finalize = [e for e in edges if e.target == "finalize"]
    assert [e.source for e in into_finalize] == ["hitl"]
    into_hitl = [e for e in edges if e.target == "hitl"]
    assert [e.source for e in into_hitl] == ["reverify"]


# --- BEHAVIORAL non-skippability --------------------------------------------------------

def test_invoke_without_resume_interrupts_and_finalizes_nothing():
    app = build_council(_deps(COUNCIL_CFG), checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "t-hitl"}}
    state = app.invoke(INITIAL, config=config)
    interrupts = state.get("__interrupt__")
    assert interrupts, "the checkpoint must fire"
    payload = interrupts[0].value
    assert payload["packet"]["items"] and payload["packet"]["watermark"]
    assert not state.get("review"), "nothing finalized without a human resume"

    # A valid resume completes the run through finalize.
    done = app.invoke(Command(resume=_accept_all(payload["packet"])), config=config)
    assert not done.get("__interrupt__")
    assert done["review"]["decisions"]["engineer"] == "enzo"
    assert done["review"]["previous"] == {}  # accept-all edits nothing


def test_execute_run_refuses_without_reviewer(tmp_path):
    runs_dir = tmp_path / "run"
    with pytest.raises(ValueError, match="requires a reviewer"):
        execute_run(
            TRANSCRIPT, "tiny", models_cfg={}, council_cfg=COUNCIL_CFG,
            thresholds=THRESHOLDS, runs_dir=runs_dir,
            chat=FakeChat(), embed_fn=one_hot_embed(), judge_fn=fake_judge,
        )
    assert not runs_dir.exists(), "fail-fast: it must refuse BEFORE running anything"


def test_invalid_decisions_reinterrupt_with_errors(tmp_path):
    calls: list[dict] = []

    def reviewer(payload):
        calls.append(payload)
        if len(calls) == 1:  # malformed on purpose: nothing decided
            return {"engineer": "enzo", "mode": "scripted", "decisions": {}}
        return _accept_all(payload["packet"])

    out = execute_run(
        TRANSCRIPT, "tiny", models_cfg={}, council_cfg=COUNCIL_CFG,
        thresholds=THRESHOLDS, runs_dir=tmp_path / "run",
        chat=FakeChat(), embed_fn=one_hot_embed(), judge_fn=fake_judge,
        reviewer=reviewer,
    )
    assert len(calls) == 2, "the graph must RE-interrupt until decisions validate"
    assert "errors" not in calls[0]
    assert any("no decision" in e for e in calls[1]["errors"])
    assert out.review["stats"]["decided"] == 3


# --- edit/reject on the board + versioned persistence -----------------------------------

def _edit_reject_reviewer(payload):
    """Edit the login item (bucket 5), reject the reports item, accept the rest."""
    decisions = {}
    for item in payload["packet"]["items"]:
        if "log in" in item["text"]:
            decisions[item["id"]] = {
                "decision": "edit", "reason": "tighten wording",
                "edited_text": "As a member, I want to log in with 2FA.",
            }
        elif "reports" in item["text"]:
            decisions[item["id"]] = {"decision": "reject",
                                     "reason": "not supported by the transcript"}
        else:
            decisions[item["id"]] = {"decision": "accept", "reason": "checked"}
    return {"engineer": "enzo", "mode": "scripted", "decisions": decisions}


def _run_edit_reject(tmp_path, dsn=None):
    return execute_run(
        TRANSCRIPT, "tiny", models_cfg={}, council_cfg=COUNCIL_CFG,
        thresholds=THRESHOLDS, runs_dir=tmp_path / "run", dsn=dsn,
        chat=FakeChat(), embed_fn=one_hot_embed(), judge_fn=fake_judge,
        reviewer=_edit_reject_reviewer,
    )


def test_edit_and_reject_reach_the_final_board(tmp_path):
    out = _run_edit_reject(tmp_path)
    edited = next(c for c in out.final if "2FA" in c.text)
    assert HUMAN_EDITED in edited.flags
    rejected = next(c for c in out.final if "reports" in c.text)
    assert rejected.status == "rejected" and rejected.confidence == 0.0
    assert len(out.final) == 3  # reject demotes, never deletes

    assert out.review["engineer"] == "enzo" and out.review["mode"] == "scripted"
    assert out.review["stats"]["counts"] == {"accept": 1, "edit": 1, "reject": 1}
    assert out.review["revised"] == sorted([edited.cand_id, rejected.cand_id])

    # The trail: packet emission + decisions are first-class events.
    review_events = [e for e in out.round_log
                     if e["action"] == "review" and e["persona"] == "engineer"]
    assert [e["payload"]["phase"] for e in review_events] == ["packet", "decisions"]
    assert review_events[1]["payload"]["counts"] == {"accept": 1, "edit": 1, "reject": 1}

    # The draft self-reports the review block.
    draft = json.loads((tmp_path / "run" / "draft.json").read_text())
    assert draft["review"] == out.review


def test_versioned_persistence_v1_machine_v2_human(tmp_path):
    from reqcouncil.store import binaries_available, ephemeral_postgres
    if not binaries_available():
        pytest.skip("initdb/pg_ctl not on PATH")
    from reqcouncil.store import dao

    with ephemeral_postgres() as dsn:
        out = _run_edit_reject(tmp_path, dsn=dsn)
        assert out.store is not None and out.store["requirements"] == 3
        with dao.connect(dsn) as conn:
            rows = dao.requirements_for_run(conn, out.store["run_id"])
            assert len(rows) == 4  # 3 machine v1 rows + 1 human v2 row
            v2 = [r for r in rows if r["version"] == 2]
            assert len(v2) == 1
            v2 = v2[0]
            v1 = next(r for r in rows if r["req_id"] == v2["supersedes_req_id"])
            # v1 = the MACHINE's claim (pre-review snapshot); v2 = the human's text.
            assert v1["version"] == 1 and "log in" in v1["text"]
            assert "2FA" in v2["text"]
            # The rejected item's v1 row keeps its machine status.
            assert any(r["version"] == 1 and r["status"] == "unsupported"
                       for r in rows)
            # Evidence hangs off v1, never off the human's v2 row.
            assert dao.trace_requirement(conn, v1["req_id"])
            assert dao.trace_requirement(conn, v2["req_id"]) == []
            # Every decision persisted — accept included (a human SAW it).
            decisions = dao.review_decisions_for_run(conn, out.store["run_id"])
            assert len(decisions) == 3
            assert {d["decision"] for d in decisions} == {"accept", "edit", "reject"}
            assert all(d["engineer"] == "enzo" and d["reason"] for d in decisions)
            edit = next(d for d in decisions if d["decision"] == "edit")
            assert "2FA" in edit["edited_text"]
            assert edit["req_id"] == v1["req_id"]


# --- the unattended arm is HONEST ------------------------------------------------------

def test_unattended_auto_reviewer_is_recorded_as_such(tmp_path):
    from reqcouncil.review import auto_reviewer

    out = execute_run(
        TRANSCRIPT, "tiny", models_cfg={}, council_cfg=COUNCIL_CFG,
        thresholds=THRESHOLDS, runs_dir=tmp_path / "run",
        chat=FakeChat(), embed_fn=one_hot_embed(), judge_fn=fake_judge,
        reviewer=auto_reviewer,
    )
    assert out.review["engineer"] == "auto-eval" and out.review["mode"] == "auto"
    assert out.review["stats"]["counts"] == {"accept": 3}
    assert out.review["revised"] == []
    draft = json.loads((tmp_path / "run" / "draft.json").read_text())
    assert draft["review"]["engineer"] == "auto-eval"
