"""Traceability-store DAO (docs/design/02 §3) — thin psycopg3 functions over schema.sql.

Deliberately boring: every function takes an open connection, does ONE thing, and the
backward trace (requirement -> chunk -> transcript) is a single JOIN — the property the
design promised. No ORM: the schema IS the contract, tests round-trip it on a real
ephemeral Postgres (pgtemp.py).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import psycopg

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(dsn: str) -> psycopg.Connection:
    return psycopg.connect(dsn, autocommit=True)


def apply_schema(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def upsert_transcript(conn: psycopg.Connection, sha: str, source: str) -> int:
    row = conn.execute(
        """
        INSERT INTO transcript (sha, source) VALUES (%s, %s)
        ON CONFLICT (sha) DO UPDATE SET source = EXCLUDED.source
        RETURNING id
        """,
        (sha, source),
    ).fetchone()
    return int(row[0])


def insert_chunks(
    conn: psycopg.Connection,
    transcript_id: int,
    chunks: list[tuple[str, int, str, float | None]],
) -> None:
    """chunks = [(anchor_id, window_start_turn, text, tfidf_flag)]; idempotent replay."""
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO chunk (chunk_id, transcript_id, window_start_turn, text, tfidf_flag)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO NOTHING
            """,
            [(cid, transcript_id, start, text, flag) for cid, start, text, flag in chunks],
        )


def create_run(
    conn: psycopg.Connection, transcript_id: int, model: str, prompt_hashes: dict[str, str]
) -> int:
    row = conn.execute(
        """
        INSERT INTO run (transcript_id, model, prompt_hashes_json)
        VALUES (%s, %s, %s) RETURNING run_id
        """,
        (transcript_id, model, json.dumps(prompt_hashes)),
    ).fetchone()
    return int(row[0])


def finish_run(conn: psycopg.Connection, run_id: int, token_usage: dict[str, int]) -> None:
    conn.execute(
        "UPDATE run SET token_usage_json = %s WHERE run_id = %s",
        (json.dumps(token_usage), run_id),
    )


def insert_requirement(
    conn: psycopg.Connection,
    run_id: int,
    *,
    text: str,
    category: str,
    kind: str,
    status: str,
    grounded: bool,
    confidence: float | None,
    stance: str,
    version: int = 1,
    supersedes: int | None = None,
) -> int:
    """version/supersedes (H5): a human edit inserts a v2 row pointing at the machine's
    v1 row — versioned rows, never overwrites (design/02 §3)."""
    row = conn.execute(
        """
        INSERT INTO requirement (run_id, text, category, kind, status, grounded,
                                 confidence, stance, version, supersedes_req_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING req_id
        """,
        (run_id, text, category, kind, status, grounded, confidence, stance,
         version, supersedes),
    ).fetchone()
    return int(row[0])


def insert_review_decision(
    conn: psycopg.Connection,
    req_id: int,
    *,
    engineer: str,
    decision: str,
    reason: str,
    edited_text: str | None = None,
) -> int:
    """One engineer decision on the MACHINE's row (v1) — accept included: the trail
    records that a human saw it, not only that a human changed it."""
    row = conn.execute(
        """
        INSERT INTO review_decision (req_id, engineer, decision, reason, edited_text)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
        """,
        (req_id, engineer, decision, reason, edited_text),
    ).fetchone()
    return int(row[0])


def review_decisions_for_run(conn: psycopg.Connection, run_id: int) -> list[dict[str, Any]]:
    """All review decisions of one run (the base of the per-run catch-rate)."""
    rows = conn.execute(
        """
        SELECT rd.id, rd.req_id, rd.engineer, rd.decision, rd.reason, rd.edited_text
        FROM review_decision rd
        JOIN requirement r ON r.req_id = rd.req_id
        WHERE r.run_id = %s
        ORDER BY rd.id
        """,
        (run_id,),
    ).fetchall()
    cols = ("id", "req_id", "engineer", "decision", "reason", "edited_text")
    return [dict(zip(cols, row)) for row in rows]


def insert_evidence(
    conn: psycopg.Connection, req_id: int, chunk_id: str, verdict: str
) -> None:
    conn.execute(
        """
        INSERT INTO evidence_link (req_id, chunk_id, verdict) VALUES (%s, %s, %s)
        ON CONFLICT (req_id, chunk_id) DO UPDATE SET verdict = EXCLUDED.verdict
        """,
        (req_id, chunk_id, verdict),
    )


def log_event(
    conn: psycopg.Connection,
    run_id: int,
    round_: int,
    persona: str,
    action: str,
    payload: dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT INTO council_event (run_id, round, persona, action, payload_json)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (run_id, round_, persona, action, json.dumps(payload)),
    )


def trace_requirement(conn: psycopg.Connection, req_id: int) -> list[dict[str, Any]]:
    """The promised backward trace, ONE join chain: requirement -> chunk -> transcript."""
    rows = conn.execute(
        """
        SELECT r.req_id, r.text AS requirement, e.verdict,
               c.chunk_id, c.window_start_turn, c.text AS chunk_text,
               t.sha AS transcript_sha, t.source
        FROM requirement r
        JOIN evidence_link e ON e.req_id = r.req_id
        JOIN chunk c         ON c.chunk_id = e.chunk_id
        JOIN transcript t    ON t.id = c.transcript_id
        WHERE r.req_id = %s
        ORDER BY c.window_start_turn
        """,
        (req_id,),
    ).fetchall()
    cols = (
        "req_id", "requirement", "verdict", "chunk_id",
        "window_start_turn", "chunk_text", "transcript_sha", "source",
    )
    return [dict(zip(cols, row)) for row in rows]


def requirements_for_run(conn: psycopg.Connection, run_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT req_id, text, category, kind, status, grounded, confidence, stance,
               version, supersedes_req_id
        FROM requirement WHERE run_id = %s ORDER BY req_id
        """,
        (run_id,),
    ).fetchall()
    cols = ("req_id", "text", "category", "kind", "status", "grounded", "confidence",
            "stance", "version", "supersedes_req_id")
    return [dict(zip(cols, row)) for row in rows]
