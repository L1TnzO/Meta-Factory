"""Round-k rebuttals (docs/design/01 §2 steps 2-3): objections routed to their OWNER.

The Moderator groups open objections by the owning persona (`candidate.category`, the
proposing charter) — ONE call per owner covering all its objected candidates. The
anti-sycophancy tooth (design/01 §3): SUPPORT without a valid cited anchor counts as NO
ANSWER — logged, and the objection stays open for the consensus tally to act on. A
missing id is likewise an open objection, never a silent pass.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..llm import ChatClient
from .analyst import MAX_COMPLETION_TOKENS, format_chunks
from .critics import RETRY_REMINDER
from .objection import Objection
from .personas import Persona
from .schema import Candidate, CandidateParseError, extract_json_array

ANSWERS = ("SUPPORT", "REVISE", "DROP")


@dataclass(frozen=True)
class RebuttalAnswer:
    cand_id: str
    answer: str                 # SUPPORT | REVISE | DROP
    anchors: tuple[str, ...]    # SUPPORT: rebuttal evidence; REVISE: new full anchor set
    text: str                   # REVISE only ("" otherwise)
    reason: str


def group_by_owner(
    candidates: list[Candidate], objections: list[Objection]
) -> dict[str, list[str]]:
    """owner persona -> objected candidate ids (deterministic order)."""
    by_id = {c.cand_id: c for c in candidates}
    owners: dict[str, list[str]] = {}
    for obj in objections:
        for target in obj.targets:
            cand = by_id.get(target)
            if cand is None:
                continue  # target already gone this round; tally resolves it
            ids = owners.setdefault(cand.category, [])
            if target not in ids:
                ids.append(target)
    return owners


def parse_answers(
    content: str,
    expected_ids: list[str],
    tag_to_anchor: dict[str, str],
) -> tuple[dict[str, RebuttalAnswer], list[dict]]:
    """Validate one owner's reply. Non-JSON raises (caller retries once); item-level
    violations degrade WITH a log entry — a bad answer is an unanswered objection."""
    items = extract_json_array(content)
    expected = set(expected_ids)
    answers: dict[str, RebuttalAnswer] = {}
    log: list[dict] = []

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            log.append({"event": "rejected", "reason": "not an object", "index": i})
            continue
        cand_id = str(item.get("id") or "").strip()
        if cand_id not in expected:
            log.append({"event": "rejected", "reason": f"unexpected id {cand_id!r}",
                        "index": i})
            continue
        if cand_id in answers:
            log.append({"event": "rejected", "reason": f"duplicate answer for {cand_id}",
                        "index": i})
            continue
        answer = str(item.get("answer") or "").strip().upper()
        if answer not in ANSWERS:
            log.append({"event": "rejected", "reason": f"bad answer {item.get('answer')!r}",
                        "cand_id": cand_id})
            continue

        anchors: list[str] = []
        raw_anchors = item.get("anchors") if isinstance(item.get("anchors"), list) else []
        for raw in raw_anchors:
            tag = str(raw).strip().strip("[]").lower()
            anchor = tag_to_anchor.get(tag)
            if anchor is None:
                log.append({"event": "anchor_dropped", "tag": str(raw), "cand_id": cand_id})
            elif anchor not in anchors:
                anchors.append(anchor)

        if answer == "SUPPORT" and not anchors:
            # The tooth: you may not defend by insisting (design/01 §3).
            log.append({"event": "support_without_anchor", "cand_id": cand_id})
            continue
        text = str(item.get("text") or "").strip()
        if answer == "REVISE" and not text and not anchors:
            log.append({"event": "revise_without_change", "cand_id": cand_id})
            continue

        answers[cand_id] = RebuttalAnswer(
            cand_id=cand_id, answer=answer, anchors=tuple(anchors), text=text,
            reason=str(item.get("reason") or "").strip(),
        )

    for cand_id in expected - set(answers):
        log.append({"event": "unanswered", "cand_id": cand_id})
    return answers, log


def run_rebuttal(
    client: ChatClient,
    persona: Persona,                 # owner charter + rebuttal contract
    candidates: list[Candidate],
    objections: list[Objection],
    objected_ids: list[str],
    tagged_chunks: list[tuple[str, str]],
    tag_to_anchor: dict[str, str],
    *,
    temperature: float,
) -> tuple[dict[str, RebuttalAnswer], list[dict], dict[str, int]]:
    """One owner's answer call: its objected candidates + their pending objections."""
    by_id = {c.cand_id: c for c in candidates}
    payload = []
    for cand_id in objected_ids:
        cand = by_id[cand_id]
        pending = [
            {"kind": o.kind, "quote": o.quote, "rationale": o.rationale}
            for o in objections
            if cand_id in o.targets
        ]
        payload.append(
            {"id": cand_id, "text": cand.text, "kind": cand.kind,
             "anchors": [t for t, a in tag_to_anchor.items() if a in cand.anchors],
             "objections": pending}
        )
    user = (
        "Transcript chunks:\n\n"
        f"{format_chunks(tagged_chunks)}\n\n"
        "Your objected candidates (with pending objections):\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n\n"
        "Answer each candidate as the JSON array now."
    )
    messages = [
        {"role": "system", "content": persona.system_prompt},
        {"role": "user", "content": user},
    ]
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    last_error: CandidateParseError | None = None
    for _attempt in range(2):
        result = client.complete(
            messages, temperature=temperature, max_completion_tokens=MAX_COMPLETION_TOKENS
        )
        usage["prompt_tokens"] += result.prompt_tokens
        usage["completion_tokens"] += result.completion_tokens
        try:
            answers, log = parse_answers(result.content, objected_ids, tag_to_anchor)
            return answers, log, usage
        except CandidateParseError as e:
            last_error = e
            messages = messages + [
                {"role": "assistant", "content": result.content},
                {"role": "user", "content": RETRY_REMINDER},
            ]
    raise CandidateParseError(f"rebuttal by {persona.name!r} failed twice: {last_error}")
