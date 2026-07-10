"""Consensus tally — deterministic, zero-LLM except the E0-calibrated judge
(docs/design/01 §3). A candidate's fate per round:

- owner DROP        -> removed, reason logged (never silent);
- owner REVISE      -> text/anchors replaced, grounding RESET, re-verified;
- owner SUPPORT     -> objection rebutted (anchor obligatorio came from rebuttal.py's
                       tooth); cited anchors are unioned and the candidate re-verified —
                       acceptance still runs through the judge, not through insistence.
                       EXCEPT duplicate/inflation: redundancy is NOT defeated by grounding
                       (measured hole, work/H4 §Resultado E1 red1 — 0 merges live while 26
                       candidates entered). A SUPPORT only defeats those when the defended
                       pair ends up citing DISJOINT anchor sets — distinct evidence proven,
                       resolved `overruled_by_distinct_evidence`;
- sustained duplicate/inflation -> MERGE (anchors unioned, proposers listed);
- sustained ungrounded/scope_creep -> judge decides: >=1 supported anchor overrules the
  objection; zero support = VETO -> demoted to flagged_inferred/0.0 (demotion, not
  deletion — recall-first, design/01 §3);
- sustained contradiction with both targets alive -> CONFLICT-STANDING: packaged for the
  human, the machine never invents the tiebreak.

Gap-hunter candidates enter through the SAME dedup (tau_dup) + verification as everyone.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .moderator import EmbedFn, merge_candidates
from .objection import Objection
from .rebuttal import RebuttalAnswer
from .schema import Candidate
from .verify import JudgeFn, verify_candidates

VETO_KINDS = ("ungrounded", "scope_creep")
MERGE_KINDS = ("duplicate", "inflation")


@dataclass(frozen=True)
class TallyResult:
    candidates: list[Candidate]   # blackboard v(k)
    resolutions: list[dict]       # for the append-only `resolutions` channel
    events: list[dict]            # round_log entries (schema-checked actions)
    deltas: dict[str, int]        # added/dropped/merged/revised/demoted/conflicts


def _merge_pair(a: Candidate, b: Candidate) -> Candidate:
    """MERGE per design/01 §3: representative = better-anchored; union anchors,
    list both proposers; explicit wins over inferred."""
    rep, absorbed = (a, b) if len(a.anchors) >= len(b.anchors) else (b, a)
    return replace(
        rep,
        anchors=tuple(sorted(set(rep.anchors) | set(absorbed.anchors))),
        proposers=tuple(sorted(set(rep.proposers) | set(absorbed.proposers))),
        stance="explicit" if "explicit" in (rep.stance, absorbed.stance) else "inferred",
    )


def tally_round(
    candidates: list[Candidate],
    open_objs: list[Objection],
    answers: dict[str, RebuttalAnswer],
    gap_candidates: list[Candidate],
    *,
    round_k: int,
    embed_fn: EmbedFn,
    judge_fn: JudgeFn,
    anchor_texts: dict[str, str],
    tau_dup: float,
    max_anchors_judged: int,
    workers: int = 8,
) -> TallyResult:
    board: dict[str, Candidate] = {c.cand_id: c for c in candidates}
    resolutions: list[dict] = []
    deltas = {"added": 0, "dropped": 0, "merged": 0, "revised": 0,
              "demoted": 0, "conflicts": 0}
    drops: list[dict] = []
    reverify: set[str] = set()
    supported: set[str] = set()  # candidates DEFENDED via SUPPORT this round

    def resolve(obj: Objection, how: str, **detail) -> None:
        resolutions.append({"obj_id": obj.obj_id, "resolution": how,
                            "round": round_k, **detail})

    # --- 1/2/3. Owner answers: DROP, REVISE, SUPPORT ------------------------------
    for cand_id, ans in answers.items():
        cand = board.get(cand_id)
        if cand is None:
            continue
        if ans.answer == "DROP":
            del board[cand_id]
            deltas["dropped"] += 1
            drops.append({"cand_id": cand_id, "reason": ans.reason or "owner drop"})
            for obj in open_objs:
                if cand_id in obj.targets:
                    resolve(obj, "owner_dropped", cand_id=cand_id)
        elif ans.answer == "REVISE":
            board[cand_id] = replace(
                cand,
                text=ans.text or cand.text,
                anchors=ans.anchors or cand.anchors,
                grounded=False, confidence=None, status="proposed", verdicts=(),
            )
            deltas["revised"] += 1
            reverify.add(cand_id)
            for obj in open_objs:
                if cand_id in obj.targets:
                    resolve(obj, "owner_revised", cand_id=cand_id)
        else:  # SUPPORT (>=1 anchor guaranteed by rebuttal.py's tooth)
            board[cand_id] = replace(
                cand, anchors=tuple(sorted(set(cand.anchors) | set(ans.anchors)))
            )
            reverify.add(cand_id)
            supported.add(cand_id)
            for obj in open_objs:
                # MERGE kinds stay open: grounding does not answer redundancy —
                # they fall through to step 4's distinct-evidence test.
                if cand_id in obj.targets and obj.kind not in MERGE_KINDS:
                    resolve(obj, "rebutted", cand_id=cand_id)

    answered = {r["obj_id"] for r in resolutions}
    still_open = [o for o in open_objs if o.obj_id not in answered]

    # --- 4. Sustained duplicate/inflation -> MERGE --------------------------------
    merge_log: list[dict] = []
    for obj in still_open:
        if obj.kind not in MERGE_KINDS:
            continue
        a, b = obj.targets
        if a not in board or b not in board:
            resolve(obj, "target_gone")
            continue
        # Escape hatch (proven-distinct evidence, work/H4 red1 decision): at least one
        # target was actively DEFENDED with SUPPORT this round AND, after the anchor
        # unions above, the pair cites fully disjoint anchor sets. Undefended pairs
        # merge regardless — sustained means sustained (design/01 §3).
        if (a in supported or b in supported) and not (
            set(board[a].anchors) & set(board[b].anchors)
        ):
            resolve(obj, "overruled_by_distinct_evidence", targets=[a, b])
            continue
        merged = _merge_pair(board[a], board[b])
        absorbed_id = b if merged.cand_id == a else a
        del board[absorbed_id]
        board[merged.cand_id] = merged
        deltas["merged"] += 1
        reverify.add(merged.cand_id)
        merge_log.append({"kept": merged.cand_id, "absorbed": absorbed_id,
                          "objection": obj.obj_id, "kind": obj.kind})
        resolve(obj, "sustained_merge", kept=merged.cand_id, absorbed=absorbed_id)

    # --- 5. Gap-hunter candidates: same dedup as everyone, then verification ------
    gap_events: list[dict] = []
    if gap_candidates:
        combined, merge_events = merge_candidates(
            list(board.values()) + gap_candidates, embed_fn, tau_dup
        )
        board = {c.cand_id: c for c in combined}
        gap_ids = {g.cand_id for g in gap_candidates}
        for gap in gap_candidates:
            if gap.cand_id in board:
                deltas["added"] += 1
                reverify.add(gap.cand_id)
        gap_events = [e.__dict__ for e in merge_events]
        # A merge that unioned a gap candidate's anchors changes the keeper's evidence.
        for e in merge_events:
            if e.absorbed in gap_ids and e.kept in board:
                reverify.add(e.kept)

    # --- 6. Judge pass over everything whose evidence changed ---------------------
    verify_events: list[dict] = []
    targets_pending = [o for o in still_open if o.kind in VETO_KINDS]
    reverify.update(t for o in targets_pending for t in o.targets if t in board)
    if reverify:
        ordered = [c for c in board.values() if c.cand_id in reverify]
        verified, verify_events = verify_candidates(
            ordered, judge_fn, anchor_texts,
            max_anchors_judged=max_anchors_judged, workers=workers,
        )
        for cand in verified:
            board[cand.cand_id] = cand

    # --- 7. Sustained ungrounded/scope_creep: the judge decides (VETO = demote) ---
    for obj in targets_pending:
        cand = board.get(obj.targets[0])
        if cand is None:
            resolve(obj, "target_gone")
            continue
        if cand.grounded:
            resolve(obj, "overruled_by_evidence", cand_id=cand.cand_id)
        else:
            board[cand.cand_id] = replace(
                cand, stance="inferred", status="flagged_inferred", confidence=0.0
            )
            deltas["demoted"] += 1
            resolve(obj, "sustained_veto", cand_id=cand.cand_id)

    # --- 8. Sustained contradictions -> CONFLICT-STANDING (human decides) ---------
    for obj in still_open:
        if obj.kind != "contradiction" or obj.obj_id in answered:
            continue
        if obj.obj_id in {r["obj_id"] for r in resolutions}:
            continue
        alive = [t for t in obj.targets if t in board]
        if len(alive) < 2:
            resolve(obj, "target_gone")
            continue
        for t in alive:
            board[t] = replace(board[t], status="conflict_standing")
        deltas["conflicts"] += 1
        resolve(obj, "conflict_standing", targets=list(alive))

    events: list[dict] = [{
        "round": round_k, "persona": "moderator", "action": "vote",
        "payload": {"resolutions": resolutions, "deltas": deltas},
    }]
    if drops:
        events.append({"round": round_k, "persona": "moderator", "action": "drop",
                       "payload": {"drops": drops}})
    if merge_log or gap_events:
        events.append({"round": round_k, "persona": "moderator", "action": "merge",
                       "payload": {"sustained": merge_log, "gap_dedup": gap_events}})
    if verify_events:
        events.append({"round": round_k, "persona": "moderator", "action": "verify",
                       "payload": {"candidates": verify_events}})
    return TallyResult(list(board.values()), resolutions, events, deltas)
