"""H3 gate — store round-trip against a REAL ephemeral Postgres (no mocks).

Proves the property design/02 §3 promised: schema applies clean, every table
round-trips, and the backward trace requirement -> chunk -> transcript is one JOIN.
Requires postgresql binaries + the [council] extra (psycopg); both are hard H3 deps,
so absence is a SKIP with a loud reason, never a silent green.
"""

from __future__ import annotations

import pytest

psycopg = pytest.importorskip("psycopg", reason="[council] extra not installed")

from reqcouncil.store import binaries_available, ephemeral_postgres  # noqa: E402
from reqcouncil.store import dao  # noqa: E402

pytestmark = pytest.mark.skipif(
    not binaries_available(), reason="initdb/pg_ctl not on PATH (install postgresql)"
)


@pytest.fixture(scope="module")
def conn():
    with ephemeral_postgres() as dsn:
        with dao.connect(dsn) as c:
            dao.apply_schema(c)
            yield c


def test_full_roundtrip_and_one_join_trace(conn):
    tid = dao.upsert_transcript(conn, sha="a" * 64, source="int1")
    assert dao.upsert_transcript(conn, sha="a" * 64, source="int1") == tid  # idempotent

    chunks = [
        ("aaaaaaaaaaaa:0", 0, "Spk 0: hello\nSpk 1: we need login", 0.7),
        ("aaaaaaaaaaaa:1", 1, "Spk 1: we need login\nSpk 0: and reports", None),
    ]
    dao.insert_chunks(conn, tid, chunks)
    dao.insert_chunks(conn, tid, chunks)  # replay must not raise

    run_id = dao.create_run(conn, tid, model="deepseek-ai/DeepSeek-V4-Flash",
                            prompt_hashes={"functional": "abc123"})
    req_id = dao.insert_requirement(
        conn, run_id,
        text="As a user, I want to log in, so that my data is private.",
        category="functional", kind="FR", status="accepted",
        grounded=True, confidence=0.9, stance="explicit",
    )
    dao.insert_evidence(conn, req_id, "aaaaaaaaaaaa:0", "supported")
    dao.insert_evidence(conn, req_id, "aaaaaaaaaaaa:1", "partial")
    dao.insert_evidence(conn, req_id, "aaaaaaaaaaaa:1", "supported")  # upsert wins
    dao.log_event(conn, run_id, 0, "functional", "propose", {"n": 1})
    dao.log_event(conn, run_id, 0, "moderator", "verify", {"req": req_id})
    dao.log_event(conn, run_id, 0, "synthesizer", "synthesize", {"kept": 1})
    dao.finish_run(conn, run_id, {"prompt_tokens": 100, "completion_tokens": 20})

    trace = dao.trace_requirement(conn, req_id)
    assert [t["chunk_id"] for t in trace] == ["aaaaaaaaaaaa:0", "aaaaaaaaaaaa:1"]
    assert trace[0]["transcript_sha"] == "a" * 64
    assert trace[0]["verdict"] == "supported"
    assert trace[1]["verdict"] == "supported"  # the upsert replaced 'partial'
    assert "log in" in trace[0]["requirement"]

    reqs = dao.requirements_for_run(conn, run_id)
    assert len(reqs) == 1 and reqs[0]["grounded"] is True


def test_constraints_have_teeth(conn):
    tid = dao.upsert_transcript(conn, sha="b" * 64, source="t2")
    run_id = dao.create_run(conn, tid, model="m", prompt_hashes={})
    with pytest.raises(psycopg.errors.CheckViolation):
        dao.insert_requirement(
            conn, run_id, text="x", category="functional", kind="WISH",  # bad kind
            status="accepted", grounded=False, confidence=None, stance="explicit",
        )
    with pytest.raises(psycopg.errors.CheckViolation):
        dao.log_event(conn, run_id, 0, "moderator", "hallucinate", {})  # bad action
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        dao.insert_evidence(conn, 999999, "missing:0", "supported")
