"""End-to-end council run over ONE transcript (shared by `reqcouncil run` and E1).

ingest (deterministic) -> Round-0 graph (LangGraph) -> draft JSON [+ traceability store].
Every LLM surface is injectable (chat / embed_fn / judge_fn) so tests replay the whole
pipeline offline; production wires the pinned clients from config. Judge verdicts go
through a JSONL cache (the E0 lesson: interrupted runs re-pay nothing).

H5: the graph interrupts at the HITL checkpoint, so `reviewer` (payload -> decisions)
is MANDATORY — there is no unattended path that finalizes silently; the unattended
evaluation harness passes `review.auto_reviewer`, which labels itself in the trail.
`interrupt()` requires a checkpointer, so DSN-less runs get an InMemorySaver.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from ..attribution.judge import USER_TEMPLATE, AlignmentJudge
from ..embeddings import EmbeddingsClient
from ..ingest import chunk_anchor, chunk_turns, parse_transcript, transcript_sha
from ..llm import ChatClient
from ..graph import CouncilDeps, build_council
from .moderator import cardinality_check
from .personas import GAP_HUNTER, load_analysts, load_critics, load_rebuttal, load_synthesizer

RECURSION_LIMIT = 100  # LangGraph supersteps: analysts + K_max deliberation loops + collapse


@dataclass(frozen=True)
class RunOutcome:
    transcript_sha: str
    n_chunks: int
    final: list          # worst-first Candidates
    draft: dict[str, Any]
    usage: dict[str, int]
    round_log: list[dict]
    prompt_shas: dict[str, str]
    store: dict[str, Any] | None  # {"run_id":…, "requirements":…} when persisted
    rounds: dict[str, Any]        # {"rounds_run", "stop_reason", "deltas", "coverage_history"}
    review: dict[str, Any] | None = None  # {"engineer", "mode", "stats", "revised"} (H5)


def batched_embed_fn(client: EmbeddingsClient, batch: int = 64):
    def embed(texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), batch):
            out.extend(client.embed(texts[i : i + batch]))
        return out
    return embed


def make_cached_judge(
    judge: AlignmentJudge, cache_path: Path
) -> tuple[Callable[[str, str], int], dict[str, int]]:
    """Thread-safe judge_fn with an append-only JSONL verdict cache + token accounting."""
    cache: dict[str, int] = {}
    if cache_path.is_file():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                cache[entry["key"]] = int(entry["pred"])
    lock = threading.Lock()
    usage = {"prompt_tokens": 0, "completion_tokens": 0}

    def judge_fn(story: str, chunk: str) -> int:
        user = USER_TEMPLATE.format(story=story, chunk=chunk)
        key = hashlib.sha256(
            f"{judge.client.model}\x00{judge.system_prompt}\x00{user}".encode()
        ).hexdigest()[:16]
        with lock:
            if key in cache:
                return cache[key]
        verdict = judge.judge(story, chunk)
        with lock:
            cache[key] = verdict.pred
            usage["prompt_tokens"] += verdict.prompt_tokens
            usage["completion_tokens"] += verdict.completion_tokens
            with cache_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"key": key, "pred": verdict.pred,
                                    "story": story[:80], "raw": verdict.raw[:40]}) + "\n")
        return cache[key]

    return judge_fn, usage


def _persist(dsn: str, outcome_parts: dict) -> dict[str, Any]:
    from ..store import dao  # lazy: psycopg is a [council]-extra dep

    # H5 versioned persistence (design/02 §3): the v1 row is the MACHINE's claim
    # (pre-review snapshot when the human revised it); evidence and the review decision
    # hang off v1; a human edit adds a v2 row with `supersedes` — never an overwrite.
    review = outcome_parts.get("review") or {}
    previous = review.get("previous") or {}
    payload = review.get("decisions") or {}
    engineer = payload.get("engineer")
    decisions = payload.get("decisions") or {}

    with dao.connect(dsn) as conn:
        dao.apply_schema(conn)
        tid = dao.upsert_transcript(conn, outcome_parts["sha"], outcome_parts["source"])
        dao.insert_chunks(conn, tid, outcome_parts["chunk_rows"])
        run_id = dao.create_run(
            conn, tid, model=outcome_parts["model"],
            prompt_hashes=outcome_parts["prompt_shas"],
        )
        n_req = 0
        for cand in outcome_parts["final"]:
            prev = previous.get(cand.cand_id)
            req_id = dao.insert_requirement(
                conn, run_id,
                text=prev["text"] if prev else cand.text,
                category=cand.category, kind=cand.kind,
                status=prev["status"] if prev else cand.status,
                grounded=cand.grounded,
                confidence=prev["confidence"] if prev else cand.confidence,
                stance=cand.stance,
            )
            n_req += 1
            for anchor, verdict in cand.verdicts:
                dao.insert_evidence(conn, req_id, anchor, verdict)
            entry = decisions.get(cand.cand_id)
            if entry and engineer:
                dao.insert_review_decision(
                    conn, req_id, engineer=engineer,
                    decision=str(entry["decision"]).strip().lower(),
                    reason=entry["reason"], edited_text=entry.get("edited_text"),
                )
                if str(entry["decision"]).strip().lower() == "edit":
                    dao.insert_requirement(
                        conn, run_id, text=cand.text, category=cand.category,
                        kind=cand.kind, status=cand.status, grounded=cand.grounded,
                        confidence=cand.confidence, stance=cand.stance,
                        version=2, supersedes=req_id,
                    )
        for event in outcome_parts["round_log"]:
            dao.log_event(conn, run_id, event["round"], event["persona"],
                          event["action"], event["payload"])
        dao.finish_run(conn, run_id, outcome_parts["usage"])
        return {"run_id": run_id, "requirements": n_req}


def _resume_loop(app, initial: dict, config: dict, reviewer) -> dict:
    """Run the graph to completion through the HITL interrupt(s): every pause hands
    the payload to `reviewer` and resumes with its decisions (H5 checkpoint loop)."""
    state = app.invoke(initial, config=config)
    while state.get("__interrupt__"):
        payload = state["__interrupt__"][0].value
        state = app.invoke(Command(resume=reviewer(payload)), config=config)
    return state


def execute_run(
    transcript_text: str,
    source: str,
    *,
    models_cfg: dict,
    council_cfg: dict,
    thresholds: dict,
    runs_dir: Path,
    dsn: str | None = None,
    chat: ChatClient | None = None,
    embed_fn=None,
    judge_fn=None,
    judge_prompt_path: Path | None = None,
    verify_workers: int = 8,
    reviewer: Callable[[dict], dict] | None = None,
) -> RunOutcome:
    # H5 fail-fast: the checkpoint is non-skippable, so a run without a reviewer cannot
    # even START — an unattended run must pass review.auto_reviewer and thereby SAY so.
    if reviewer is None:
        raise ValueError(
            "execute_run requires a reviewer (payload -> decisions): use "
            "review.cli_reviewer()/file_reviewer(path) for humans or "
            "review.auto_reviewer for unattended evaluation runs (recorded as such)"
        )
    runs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Deterministic ingest (H1 machinery).
    turns = parse_transcript(transcript_text)
    chunks = chunk_turns(turns)
    sha = transcript_sha(transcript_text)
    tagged = [(f"c{c.chunk_id}", c.text) for c in chunks]
    tag_to_anchor = {
        f"c{c.chunk_id}": chunk_anchor(sha, c.window_start_turn) for c in chunks
    }
    anchor_texts = {tag_to_anchor[tag]: text for tag, text in tagged}

    # 2. Personas + clients (pinned by config unless injected by tests).
    analysts = load_analysts(list(council_cfg["analysts"]))
    synthesizer = load_synthesizer()
    prompt_shas = {p.name: p.sha for p in analysts} | {"synthesizer": synthesizer.sha}
    # H4: critics + per-owner rebuttal personas, only when the deliberation loop is on
    # (config without `rounds` => k_max=0, the H3-compatible arm).
    k_max = int((council_cfg.get("rounds") or {}).get("k_max", 0))
    critics: list = []
    rebuttal_personas: dict = {}
    if k_max > 0:
        critics = load_critics(list(council_cfg["critics"]))
        owners = [p.name for p in analysts] + [GAP_HUNTER]
        rebuttal_personas = {name: load_rebuttal(name) for name in owners}
        prompt_shas |= {p.name: p.sha for p in critics}
        prompt_shas |= {p.name: p.sha for p in rebuttal_personas.values()}
    chat = chat or ChatClient.from_config(models_cfg)
    if embed_fn is None:
        embed_fn = batched_embed_fn(EmbeddingsClient.from_config(models_cfg))
    if judge_fn is None:
        if judge_prompt_path is None:
            from ..eval.golden import INTERVIEW, system_prompt_path
            judge_prompt_path = system_prompt_path(INTERVIEW)
        judge_prompt = judge_prompt_path.read_text(encoding="utf-8")
        prompt_shas["judge"] = hashlib.sha256(judge_prompt.encode()).hexdigest()[:12]
        judge = AlignmentJudge.from_config(chat, judge_prompt, models_cfg)
        judge_fn, judge_usage = make_cached_judge(judge, runs_dir / "verdicts.jsonl")
    else:
        judge_usage = {}

    # 3. Council graph (Round 0 + the H4 deliberation loop when k_max > 0).
    deps = CouncilDeps(
        chat=chat, embed_fn=embed_fn, judge_fn=judge_fn,
        analysts=analysts, synthesizer=synthesizer,
        tagged_chunks=tagged, tag_to_anchor=tag_to_anchor, anchor_texts=anchor_texts,
        council_cfg=council_cfg, thresholds=thresholds,
        verify_workers=verify_workers,
        critics=critics, rebuttal_personas=rebuttal_personas,
    )
    initial = {"candidates": [], "round_log": [], "usage": {},
               "objections": [], "resolutions": [], "round": 0,
               "coverage_history": [], "stop": ""}
    config = {"configurable": {"thread_id": f"{source}:{sha[:12]}"},
              "recursion_limit": RECURSION_LIMIT}
    if dsn:
        from langgraph.checkpoint.postgres import PostgresSaver
        with PostgresSaver.from_conn_string(dsn) as saver:
            saver.setup()
            app = build_council(deps, checkpointer=saver)
            state = _resume_loop(app, initial, config, reviewer)
    else:
        # interrupt() requires a checkpointer even without persistence (H5).
        app = build_council(deps, checkpointer=InMemorySaver())
        state = _resume_loop(app, initial, config, reviewer)

    final = state["final"]
    usage = dict(state["usage"])
    for key, val in judge_usage.items():
        usage[key] = usage.get(key, 0) + val

    # 4. Draft + run report payload (design/02 §5).
    rounds_info = {
        "rounds_run": int(state.get("round", 0)),
        "stop_reason": state.get("stop") or None,
        "deltas": [e["payload"]["deltas"] for e in state["round_log"]
                   if e.get("action") == "converge"],
        "coverage_history": state.get("coverage_history", []),
    }
    review_state = state.get("review") or {}
    review_payload = review_state.get("decisions") or {}
    counts: dict[str, int] = {}
    for entry in (review_payload.get("decisions") or {}).values():
        verdict = str(entry["decision"]).strip().lower()
        counts[verdict] = counts.get(verdict, 0) + 1
    review_info = {
        "engineer": review_payload.get("engineer"),
        "mode": review_payload.get("mode"),
        "stats": {
            "decided": sum(counts.values()),
            "counts": counts,
            "mandatory": (review_state.get("packet") or {}).get("stats", {}).get("mandatory"),
        },
        "revised": sorted(review_state.get("previous") or {}),
    }

    cardinality = cardinality_check(len(final), len(chunks), council_cfg, thresholds)
    cited = {a for c in final for a in c.anchors}
    draft = {
        "source": source,
        "transcript_sha": sha,
        "model": chat.model,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "prompt_shas": prompt_shas,
        "n_chunks": len(chunks),
        "cardinality": cardinality,
        "citation_coverage": round(len(cited) / len(chunks), 4) if chunks else 0.0,
        "rounds": rounds_info,
        "review": review_info,
        "usage": usage,
        "requirements": [c.to_dict() for c in final],
    }

    # 5. Optional traceability store (the pinned E1 run persists for real).
    store_info = None
    if dsn:
        store_info = _persist(
            dsn,
            {
                "sha": sha, "source": source, "model": chat.model,
                "prompt_shas": prompt_shas, "final": final,
                "review": review_state,
                "round_log": state["round_log"], "usage": usage,
                "chunk_rows": [
                    (tag_to_anchor[tag], c.window_start_turn, c.text, None)
                    for (tag, _), c in zip(tagged, chunks, strict=True)
                ],
            },
        )
        draft["store"] = store_info

    (runs_dir / "draft.json").write_text(
        json.dumps(draft, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return RunOutcome(
        transcript_sha=sha, n_chunks=len(chunks), final=final, draft=draft,
        usage=usage, round_log=state["round_log"], prompt_shas=prompt_shas,
        store=store_info, rounds=rounds_info, review=review_info,
    )
