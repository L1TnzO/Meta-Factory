-- Traceability Store (docs/design/02 §3) — single Postgres substrate.
-- H1 deliverable: schema as spec-derived DDL. Its tooth (dao.py + live PG round-trip
-- tests) arrives with H3; LangGraph PostgresSaver checkpoints share this database.

CREATE TABLE IF NOT EXISTS transcript (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sha         TEXT NOT NULL UNIQUE,          -- content address (basis of chunk anchors)
    source      TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunk (
    chunk_id          TEXT PRIMARY KEY,        -- anchor: {transcript_sha[:12]}:{window_start_turn}
    transcript_id     BIGINT NOT NULL REFERENCES transcript(id),
    window_start_turn INT  NOT NULL,
    text              TEXT NOT NULL,
    tfidf_flag        REAL,                    -- requirement-bearing likelihood (feature, never a filter)
    UNIQUE (transcript_id, window_start_turn)
);

CREATE TABLE IF NOT EXISTS run (
    run_id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transcript_id      BIGINT NOT NULL REFERENCES transcript(id),
    model              TEXT NOT NULL,          -- pinned model id (docs/design/03 §2)
    prompt_hashes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    token_usage_json   JSONB
);

CREATE TABLE IF NOT EXISTS requirement (
    req_id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id            BIGINT NOT NULL REFERENCES run(run_id),
    text              TEXT NOT NULL,
    category          TEXT NOT NULL,           -- analyst category (Functional · Data · NFR · ...)
    kind              TEXT NOT NULL CHECK (kind IN ('FR', 'NFR')),
    status            TEXT NOT NULL,
    grounded          BOOLEAN NOT NULL DEFAULT FALSE,
    confidence        REAL CHECK (confidence BETWEEN 0 AND 1),
    stance            TEXT NOT NULL CHECK (stance IN ('explicit', 'inferred')),
    version           INT  NOT NULL DEFAULT 1,
    supersedes_req_id BIGINT REFERENCES requirement(req_id)  -- human edits are versioned rows
);

CREATE TABLE IF NOT EXISTS evidence_link (
    req_id   BIGINT NOT NULL REFERENCES requirement(req_id),
    chunk_id TEXT   NOT NULL REFERENCES chunk(chunk_id),
    verdict  TEXT   NOT NULL CHECK (verdict IN ('supported', 'partial', 'unsupported')),
    PRIMARY KEY (req_id, chunk_id)
);

CREATE TABLE IF NOT EXISTS council_event (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id       BIGINT NOT NULL REFERENCES run(run_id),
    round        INT    NOT NULL,
    persona      TEXT   NOT NULL,
    -- H3 extends the design/02 §3 action set (+verify, +synthesize): the Round-0 trail
    -- records Layer-2 grounding verdicts and the Synthesizer pass as first-class events.
    -- H4 adds 'converge': the Convergence Controller's per-round stop/continue decision.
    -- H5 adds 'review': the HITL packet emission + the engineer's decision summary.
    action       TEXT   NOT NULL CHECK (action IN ('propose', 'object', 'vote', 'merge',
                                                   'drop', 'verify', 'synthesize',
                                                   'converge', 'review')),
    payload_json JSONB  NOT NULL DEFAULT '{}'::jsonb,
    ts           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS review_decision (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    req_id      BIGINT NOT NULL REFERENCES requirement(req_id),
    engineer    TEXT   NOT NULL,
    decision    TEXT   NOT NULL CHECK (decision IN ('accept', 'edit', 'reject')),
    reason      TEXT   NOT NULL,               -- cognitive forcing function: one-line reason required
    edited_text TEXT,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now()
);
