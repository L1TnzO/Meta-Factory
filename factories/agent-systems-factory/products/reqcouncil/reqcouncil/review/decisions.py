"""Decision contract + teeth (docs/design/02 §4).

A decisions payload:

    {"engineer": "name", "mode": "cli|file|auto|scripted",
     "decisions": {"<item id>": {"decision": "accept|edit|reject",
                                 "reason": "one line", "edited_text": "..."}}}

`validate_decisions` returns a list of ERRORS (empty = valid); the hitl node
RE-interrupts with those errors attached until the payload is valid — a run can never
finalize on malformed review input. `apply_decisions` is recall-first: reject DEMOTES
(status `rejected`, confidence 0.0), never deletes; edit keeps the machine's text as the
version-1 snapshot (the store persists it as a superseded row, design/02 §3).
"""

from __future__ import annotations

from ..council.schema import Candidate, replace

DECISIONS = ("accept", "edit", "reject")
HUMAN_EDITED = "human_edited"


def validate_decisions(packet: dict, payload) -> list[str]:
    if not isinstance(payload, dict):
        return ["decisions payload must be an object"]
    errors: list[str] = []
    if not str(payload.get("engineer") or "").strip():
        errors.append("engineer must be non-empty")
    decisions = payload.get("decisions")
    if not isinstance(decisions, dict):
        return errors + ["'decisions' must be an object keyed by item id"]

    ids = {item["id"] for item in packet["items"]}
    for cid in sorted(set(decisions) - ids):
        errors.append(f"{cid}: not an item of this packet")
    for cid in sorted(ids - set(decisions)):
        errors.append(f"{cid}: no decision (every packet item must be decided)")

    for cid in sorted(set(decisions) & ids):
        entry = decisions[cid]
        if not isinstance(entry, dict):
            errors.append(f"{cid}: decision entry must be an object")
            continue
        verdict = str(entry.get("decision") or "").strip().lower()
        if verdict not in DECISIONS:
            errors.append(f"{cid}: decision must be one of {'|'.join(DECISIONS)}")
        if not str(entry.get("reason") or "").strip():
            errors.append(f"{cid}: a one-line reason is required")
        if verdict == "edit" and not str(entry.get("edited_text") or "").strip():
            errors.append(f"{cid}: edit requires non-empty edited_text")
    return errors


def apply_decisions(
    candidates: list[Candidate], payload: dict
) -> tuple[list[Candidate], dict[str, dict]]:
    """Apply a VALIDATED payload to the board.

    Returns (new board, previous) where `previous` snapshots the machine's
    text/status/confidence for every edited or rejected item — the version-1 rows the
    store persists (human edits are versioned rows, never overwrites).
    """
    decisions = payload["decisions"]
    out: list[Candidate] = []
    previous: dict[str, dict] = {}
    for cand in candidates:
        entry = decisions.get(cand.cand_id)
        verdict = str(entry.get("decision", "")).strip().lower() if entry else "accept"
        if entry is None or verdict == "accept":
            out.append(cand)
            continue
        previous[cand.cand_id] = {
            "text": cand.text, "status": cand.status, "confidence": cand.confidence,
        }
        if verdict == "edit":
            # tuple() also normalizes the checkpointer's serde round-trip, which
            # rehydrates the dataclass's tuples as lists after interrupt/resume.
            flags = tuple(cand.flags)
            if HUMAN_EDITED not in flags:
                flags = flags + (HUMAN_EDITED,)
            out.append(replace(cand, text=str(entry["edited_text"]).strip(), flags=flags))
        else:  # reject -> demotion, never deletion (recall-first, design/01 §3)
            out.append(replace(cand, status="rejected", confidence=0.0))
    return out, previous
