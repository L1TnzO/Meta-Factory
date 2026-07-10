"""Catch-rate drill (report §4.3.d) — measure the reviewer, zero LLM.

Rebuilds the Review Packet from a SAVED draft.json (anchor texts re-derived from the
transcript by the deterministic ingest — same sha or refuse), injects N SEEDED decoys
and scores the collected decisions:

    catch_rate  = decoys caught (reject|edit) / decoys present
    false_alarm = real items rejected

A decoy is an in-place corruption: requirement A keeps its text/status/confidence but
receives requirement B's evidence (anchors + verdicts) — text and evidence no longer
support each other, while the row still LOOKS like an ordinary accepted item (bucket
5). That placement is deliberate: it probes automation bias exactly where bulk-accept
is allowed (design/02 §4). status/grounded are NOT touched — a decoy that jumped to a
mandatory bucket would be caught by the packet, not by the human.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from ..council.schema import Candidate, replace
from ..ingest import chunk_anchor, chunk_turns, parse_transcript, transcript_sha
from .decisions import validate_decisions
from .packet import build_packet

CATCHING = ("reject", "edit")


def candidates_from_draft(draft: dict) -> list[Candidate]:
    """Rehydrate the final board from a saved draft.json (Candidate.to_dict inverse)."""
    out = []
    for d in draft["requirements"]:
        out.append(Candidate(
            cand_id=d["id"], text=d["text"], category=d["category"], kind=d["kind"],
            anchors=tuple(d["anchors"]), stance=d["stance"], rationale=d["rationale"],
            proposers=tuple(d["proposers"]), grounded=d["grounded"],
            confidence=d["confidence"], status=d["status"],
            verdicts=tuple(d["verdicts"].items()), flags=tuple(d["flags"]),
        ))
    return out


def anchor_texts_for(draft: dict, transcript_text: str) -> dict[str, str]:
    """Re-derive anchor -> chunk text via the deterministic ingest; sha must match."""
    sha = transcript_sha(transcript_text)
    if sha != draft["transcript_sha"]:
        raise ValueError(
            f"transcript sha {sha[:12]} does not match draft {draft['transcript_sha'][:12]} "
            "— the drill refuses to show evidence from a different transcript"
        )
    chunks = chunk_turns(parse_transcript(transcript_text))
    return {chunk_anchor(sha, c.window_start_turn): c.text for c in chunks}


def inject_decoys(
    candidates: list[Candidate], n: int, seed: int
) -> tuple[list[Candidate], list[dict]]:
    """Corrupt up to n victims in place (seeded, deterministic). Returns (board, decoys)
    where each decoy records {"id": victim, "donor": donor} for scoring."""
    if n <= 0:
        return list(candidates), []
    pool = sorted(
        (c for c in candidates if c.status == "accepted" and c.grounded and c.anchors),
        key=lambda c: c.cand_id,
    )
    rng = random.Random(seed)
    order = pool[:]
    rng.shuffle(order)

    used: set[str] = set()
    pairs: list[tuple[str, str]] = []
    by_id = {c.cand_id: c for c in pool}
    for victim in order:
        if len(pairs) == n:
            break
        if victim.cand_id in used:
            continue
        donor = next(
            (d for d in order
             if d.cand_id != victim.cand_id and d.cand_id not in used
             and not set(d.anchors) & set(victim.anchors)),
            None,
        )
        if donor is None:
            continue
        used.update((victim.cand_id, donor.cand_id))
        pairs.append((victim.cand_id, donor.cand_id))

    board = []
    victims = {v: d for v, d in pairs}
    for cand in candidates:
        donor_id = victims.get(cand.cand_id)
        if donor_id is None:
            board.append(cand)
        else:
            donor = by_id[donor_id]
            board.append(replace(cand, anchors=donor.anchors, verdicts=donor.verdicts))
    return board, [{"id": v, "donor": d} for v, d in pairs]


def run_drill(
    draft: dict,
    transcript_text: str,
    *,
    low_confidence: float,
    decoys: int,
    seed: int,
    reviewer,
    out_dir: Path,
) -> dict:
    """Packet -> decisions -> score -> <out_dir>/review-report.json. Zero LLM."""
    anchor_texts = anchor_texts_for(draft, transcript_text)
    board, decoy_list = inject_decoys(candidates_from_draft(draft), decoys, seed)

    packet = build_packet(
        board, anchor_texts=anchor_texts, low_confidence=low_confidence,
        cardinality=draft.get("cardinality"), source=draft.get("source"),
        transcript_sha=draft["transcript_sha"],
    )
    payload = {"packet": packet}
    while True:
        decisions = reviewer(payload)
        errors = validate_decisions(packet, decisions)
        if not errors:
            break
        payload = {"packet": packet, "errors": errors}

    entries = decisions["decisions"]
    decoy_ids = {d["id"] for d in decoy_list}
    caught = sorted(
        cid for cid in decoy_ids if entries[cid]["decision"] in CATCHING
    )
    false_alarms = sorted(
        cid for cid, e in entries.items()
        if cid not in decoy_ids and e["decision"] == "reject"
    )
    counts: dict[str, int] = {}
    for entry in entries.values():
        counts[entry["decision"]] = counts.get(entry["decision"], 0) + 1

    report = {
        "source": draft.get("source"),
        "transcript_sha": draft["transcript_sha"],
        "seed": seed,
        "decoys_requested": decoys,
        "decoys_present": len(decoy_list),
        "decoys": decoy_list,
        "caught": caught,
        "catch_rate": (round(len(caught) / len(decoy_list), 4) if decoy_list else None),
        "false_alarms": false_alarms,
        "engineer": decisions["engineer"],
        "mode": decisions.get("mode"),
        "decision_counts": counts,
        "packet_stats": packet["stats"],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "review-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
