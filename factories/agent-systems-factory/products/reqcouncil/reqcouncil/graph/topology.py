"""Council topology (docs/design/01 §2) — the full deliberation loop at H4:

    START -> 6 analysts (parallel fan-out) -> moderator -> verify
    verify -> [k_max == 0 ? synthesize : open_round]                  (E4 arm c compat)
    open_round -> 3 critics (parallel, barrier) -> rebuttal -> consensus -> convergence
    convergence -> (stop ? synthesize : open_round)
    synthesize -> reverify -> hitl -> finalize -> END

Dependencies (LLM clients, embedder, judge, prompts, chunks) are closed over at build
time via `CouncilDeps` — tests inject deterministic fakes and run the whole graph with
zero network. `PostgresSaver` is wired when a DSN is given (same database as the store,
design/02 §3).

`hitl` (H5) is the non-skippable checkpoint (design/00 property #2): it builds the
worst-first Review Packet, `interrupt()`s, and RE-interrupts until the resumed
decisions validate — non-skippable by REACHABILITY, because the only edge into END
leaves `finalize` and the only edge into `finalize` leaves `hitl`. `finalize` applies
the validated decisions to the board (edit = versioned, reject = demotion).

`reverify` (H3's declared residual): after the synthesizer's wording pass the anchors are
re-judged against the FINAL text — a grounded candidate that loses ALL support gets the
`normalization_drift` flag and a degraded status, so the fidelity the gate reports is
measured on the text the reviewer actually reads.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from ..council.analyst import format_chunks, run_analyst
from ..council.consensus import tally_round
from ..council.convergence import coverage, flag_unconverged, should_stop
from ..council.critics import run_gap_hunter, run_objection_critic
from ..council.moderator import cardinality_check, merge_candidates
from ..council.objection import open_objections
from ..council.personas import GAP_HUNTER, Persona
from ..council.rebuttal import group_by_owner, run_rebuttal
from ..council.synthesizer import synthesize, worst_first
from ..council.verify import verify_candidates
from ..llm import ChatClient
from ..review import apply_decisions, build_packet, validate_decisions
from .state import Blackboard

CONFLICT_STANDING = "conflict_standing"


@dataclass(frozen=True)
class CouncilDeps:
    chat: ChatClient
    embed_fn: Callable[[list[str]], list[list[float]]]
    judge_fn: Callable[[str, str], int]                  # E0-calibrated (or a test fake)
    analysts: list[Persona]
    synthesizer: Persona
    tagged_chunks: list[tuple[str, str]]                 # [("c0", chunk text), ...]
    tag_to_anchor: dict[str, str]                        # "c0" -> "sha12:turn"
    anchor_texts: dict[str, str]                         # anchor -> chunk text
    council_cfg: dict = field(default_factory=dict)
    thresholds: dict = field(default_factory=dict)       # cardinality band for the packet
    verify_workers: int = 8
    critics: list[Persona] = field(default_factory=list)          # H4 Round-k challengers
    rebuttal_personas: dict[str, Persona] = field(default_factory=dict)  # owner -> persona


def _rounds_cfg(deps: CouncilDeps) -> dict:
    return deps.council_cfg.get("rounds") or {}


def _critiquable(candidates: list) -> list:
    """conflict_standing candidates are packaged for the human — excluded from further
    critique (work-doc §2); everything else on the live board is fair game."""
    return [c for c in candidates if c.status != CONFLICT_STANDING]


def _analyst_node(deps: CouncilDeps, persona: Persona):
    temperature = float(deps.council_cfg["temperatures"]["analyst"])
    chunks_block = format_chunks(deps.tagged_chunks)

    def node(_state: Blackboard) -> Blackboard:
        res = run_analyst(
            deps.chat, persona.name, persona.system_prompt, chunks_block,
            deps.tag_to_anchor, temperature=temperature,
        )
        return {
            "candidates": res.candidates,
            "round_log": [
                {"round": 0, "persona": persona.name, "action": "propose",
                 "payload": {"proposed": len(res.candidates), "parse_log": res.parse_log}}
            ],
            "usage": {"prompt_tokens": res.prompt_tokens,
                      "completion_tokens": res.completion_tokens},
        }

    return node


def _moderator_node(deps: CouncilDeps):
    tau = float(deps.council_cfg["dedup"]["tau_dup"])

    def node(state: Blackboard) -> Blackboard:
        merged, events = merge_candidates(state["candidates"], deps.embed_fn, tau)
        return {
            "merged": merged,
            "round_log": [
                {"round": 0, "persona": "moderator", "action": "merge",
                 "payload": {"in": len(state["candidates"]), "out": len(merged),
                             "merges": [e.__dict__ for e in events]}}
            ],
        }

    return node


def _verify_node(deps: CouncilDeps):
    max_anchors = int(deps.council_cfg["verify"]["max_anchors_judged"])

    def node(state: Blackboard) -> Blackboard:
        verified, events = verify_candidates(
            state["merged"], deps.judge_fn, deps.anchor_texts,
            max_anchors_judged=max_anchors, workers=deps.verify_workers,
        )
        return {
            "merged": verified,
            "round_log": [
                {"round": 0, "persona": "moderator", "action": "verify",
                 "payload": {"candidates": events}}
            ],
        }

    return node


# --- Round-k deliberation nodes (H4, design/01 §2 CONVERGE) ---------------------------

def _open_round_node(deps: CouncilDeps):
    n_chunks = len(deps.tagged_chunks)

    def node(state: Blackboard) -> Blackboard:
        board = state["merged"]
        history = list(state.get("coverage_history") or [])
        if not history:  # Round-0 baseline, same metric as the draft report
            history = [coverage(board, n_chunks)]
        cited = {a for c in board for a in c.anchors}
        residue = [t for t, anchor in deps.tag_to_anchor.items() if anchor not in cited]
        return {
            "round": int(state.get("round", 0)) + 1,
            "coverage_history": history,
            "residue": residue,
            # per-round scratch RESET so round k never sees round k-1 leftovers:
            "round_gaps": [], "round_answers": {}, "round_deltas": {},
        }

    return node


def _critic_node(deps: CouncilDeps, persona: Persona):
    temperature = float(deps.council_cfg["temperatures"]["critic"])
    raw_budget = _rounds_cfg(deps).get("gap_budget")
    gap_budget = int(raw_budget) if raw_budget is not None else None

    def node(state: Blackboard) -> Blackboard:
        round_k = state["round"]
        if persona.name == GAP_HUNTER:
            res = run_gap_hunter(
                deps.chat, persona, round_k, state.get("residue", []),
                deps.tagged_chunks, deps.tag_to_anchor, temperature=temperature,
                budget=gap_budget,
            )
            update: Blackboard = {"round_gaps": res.gap_candidates}
            payload = {"proposed": len(res.gap_candidates),
                       "residue": len(state.get("residue", [])),
                       "parse_log": res.parse_log}
            action = "propose"
        else:
            res = run_objection_critic(
                deps.chat, persona, round_k, _critiquable(state["merged"]),
                deps.tagged_chunks, deps.tag_to_anchor, deps.anchor_texts,
                temperature=temperature,
            )
            update = {"objections": res.objections}
            payload = {"objections": [o.to_dict() for o in res.objections],
                       "parse_log": res.parse_log}
            action = "object"
        update["round_log"] = [
            {"round": round_k, "persona": persona.name, "action": action,
             "payload": payload}
        ]
        update["usage"] = {"prompt_tokens": res.prompt_tokens,
                           "completion_tokens": res.completion_tokens}
        return update

    return node


def _rebuttal_node(deps: CouncilDeps):
    temperature = float(deps.council_cfg["temperatures"]["rebuttal"])

    def node(state: Blackboard) -> Blackboard:
        round_k = state["round"]
        live = state["merged"]
        open_objs = open_objections(state.get("objections", []),
                                    state.get("resolutions", []))
        owners = group_by_owner(live, open_objs)
        answers: dict = {}
        events: list[dict] = []
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        for owner in sorted(owners):  # deterministic call order
            ans, log, use = run_rebuttal(
                deps.chat, deps.rebuttal_personas[owner], live, open_objs,
                owners[owner], deps.tagged_chunks, deps.tag_to_anchor,
                temperature=temperature,
            )
            answers.update(ans)
            for key, val in use.items():
                usage[key] += val
            events.append(
                {"round": round_k, "persona": owner, "action": "vote",
                 "payload": {"answers": {cid: {"answer": a.answer, "reason": a.reason}
                                         for cid, a in ans.items()},
                             "parse_log": log}}
            )
        return {"round_answers": answers, "round_log": events, "usage": usage}

    return node


def _consensus_node(deps: CouncilDeps):
    tau = float(deps.council_cfg["dedup"]["tau_dup"])
    max_anchors = int(deps.council_cfg["verify"]["max_anchors_judged"])

    def node(state: Blackboard) -> Blackboard:
        open_objs = open_objections(state.get("objections", []),
                                    state.get("resolutions", []))
        result = tally_round(
            state["merged"], open_objs, state.get("round_answers", {}),
            state.get("round_gaps", []), round_k=state["round"],
            embed_fn=deps.embed_fn, judge_fn=deps.judge_fn,
            anchor_texts=deps.anchor_texts, tau_dup=tau,
            max_anchors_judged=max_anchors, workers=deps.verify_workers,
        )
        return {"merged": result.candidates, "resolutions": result.resolutions,
                "round_log": result.events, "round_deltas": result.deltas}

    return node


def _convergence_node(deps: CouncilDeps):
    rounds = _rounds_cfg(deps)
    k_max = int(rounds.get("k_max", 0))
    epsilon = float(rounds.get("epsilon", 0.01))
    plateau_rounds = int(rounds.get("plateau_rounds", 2))
    n_chunks = len(deps.tagged_chunks)

    def node(state: Blackboard) -> Blackboard:
        round_k = state["round"]
        cov = coverage(state["merged"], n_chunks)
        history = list(state["coverage_history"]) + [cov]
        decision = should_stop(
            round_k, k_max, state.get("round_deltas", {}), history,
            epsilon=epsilon, plateau_rounds=plateau_rounds,
        )
        merged = state["merged"]
        flagged: list[str] = []
        open_objs = open_objections(state.get("objections", []),
                                    state.get("resolutions", []))
        if decision.stop:
            merged, flagged = flag_unconverged(merged, open_objs)
        return {
            "merged": merged,
            "coverage_history": history,
            "stop": decision.reason if decision.stop else "",
            "round_log": [
                {"round": round_k, "persona": "moderator", "action": "converge",
                 "payload": {"coverage": cov,
                             "deltas": dict(state.get("round_deltas", {})),
                             "decision": decision.reason if decision.stop else "continue",
                             "open_objections": len(open_objs),
                             "unconverged": flagged}}
            ],
        }

    return node


# --- COLLAPSE ---------------------------------------------------------------------------

def _synthesizer_node(deps: CouncilDeps):
    temperature = float(deps.council_cfg["temperatures"]["synthesizer"])

    def node(state: Blackboard) -> Blackboard:
        final, usage = synthesize(
            deps.chat, deps.synthesizer.system_prompt, state["merged"],
            temperature=temperature,
        )
        return {
            "final": final,
            "round_log": [
                {"round": state.get("round", 0), "persona": "synthesizer",
                 "action": "synthesize", "payload": {"final": len(final)}}
            ],
            "usage": usage,
        }

    return node


def _reverify_node(deps: CouncilDeps):
    max_anchors = int(deps.council_cfg["verify"]["max_anchors_judged"])

    def node(state: Blackboard) -> Blackboard:
        judged, events = verify_candidates(
            state["final"], deps.judge_fn, deps.anchor_texts,
            max_anchors_judged=max_anchors, workers=deps.verify_workers,
        )
        drifted: list[str] = []
        final = []
        for old, new in zip(state["final"], judged, strict=True):
            status, flags = new.status, new.flags
            if old.status == CONFLICT_STANDING:
                status = CONFLICT_STANDING  # the human decides; grounding re-measured only
            if old.grounded and not new.grounded:
                drifted.append(old.cand_id)
                if "normalization_drift" not in flags:
                    flags = flags + ("normalization_drift",)
            final.append(replace(new, status=status, flags=flags))
        return {
            "final": worst_first(final),
            "round_log": [
                {"round": state.get("round", 0), "persona": "moderator",
                 "action": "verify",
                 "payload": {"phase": "reverify_final_text", "candidates": events,
                             "normalization_drift": drifted}}
            ],
        }

    return node


# --- HITL checkpoint (H5, design/02 §4) -------------------------------------------------

def _hitl_node(deps: CouncilDeps):
    review_cfg = deps.council_cfg.get("review") or {}
    low_confidence = float(review_cfg.get("low_confidence", 0.6))
    n_chunks = len(deps.tagged_chunks)

    def node(state: Blackboard) -> Blackboard:
        final = state["final"]
        cardinality = None
        if deps.thresholds and "cardinality_band" in deps.council_cfg:
            cardinality = cardinality_check(
                len(final), n_chunks, deps.council_cfg, deps.thresholds
            )
        packet = build_packet(
            final, anchor_texts=deps.anchor_texts,
            low_confidence=low_confidence, cardinality=cardinality,
        )
        payload: dict = {"packet": packet}
        while True:  # RE-interrupt until the decisions validate — never finalize on
            decisions = interrupt(payload)  # malformed review input (design/02 §4)
            errors = validate_decisions(packet, decisions)
            if not errors:
                break
            payload = {"packet": packet, "errors": errors}
        return {
            "review": {"packet": packet, "decisions": decisions},
            "round_log": [
                {"round": state.get("round", 0), "persona": "engineer",
                 "action": "review",
                 "payload": {"phase": "packet", "stats": packet["stats"],
                             "warnings": packet["warnings"]}}
            ],
        }

    return node


def _finalize_node(deps: CouncilDeps):
    def node(state: Blackboard) -> Blackboard:
        decisions = state["review"]["decisions"]
        final, previous = apply_decisions(state["final"], decisions)
        counts: dict[str, int] = {}
        for entry in decisions["decisions"].values():
            verdict = str(entry["decision"]).strip().lower()
            counts[verdict] = counts.get(verdict, 0) + 1
        return {
            "final": final,
            "review": {**state["review"], "previous": previous},
            "round_log": [
                {"round": state.get("round", 0), "persona": "engineer",
                 "action": "review",
                 "payload": {"phase": "decisions",
                             "engineer": decisions["engineer"],
                             "mode": decisions.get("mode"),
                             "counts": counts,
                             "revised": sorted(previous)}}
            ],
        }

    return node


def build_council(deps: CouncilDeps, checkpointer=None):
    """Compile the council graph. k_max == 0 keeps the H3 arm (analysts -> moderator ->
    verify -> synthesize) — E4's council-without-critics baseline; k_max > 0 inserts the
    Round-k CONVERGE loop between verify and synthesize."""
    k_max = int(_rounds_cfg(deps).get("k_max", 0))
    g = StateGraph(Blackboard)
    names = []
    for persona in deps.analysts:
        node_name = f"analyst_{persona.name}"
        g.add_node(node_name, _analyst_node(deps, persona))
        g.add_edge(START, node_name)
        names.append(node_name)
    g.add_node("moderator", _moderator_node(deps))
    g.add_edge(names, "moderator")  # barrier: waits for ALL analysts
    g.add_node("verify", _verify_node(deps))
    g.add_edge("moderator", "verify")

    if k_max > 0:
        g.add_node("open_round", _open_round_node(deps))
        g.add_edge("verify", "open_round")
        critic_names = []
        for persona in deps.critics:
            node_name = f"critic_{persona.name}"
            g.add_node(node_name, _critic_node(deps, persona))
            g.add_edge("open_round", node_name)
            critic_names.append(node_name)
        g.add_node("rebuttal", _rebuttal_node(deps))
        g.add_edge(critic_names, "rebuttal")  # barrier: waits for ALL critics
        g.add_node("consensus", _consensus_node(deps))
        g.add_edge("rebuttal", "consensus")
        g.add_node("convergence", _convergence_node(deps))
        g.add_edge("consensus", "convergence")
        g.add_conditional_edges(
            "convergence",
            lambda state: "synthesize" if state["stop"] else "open_round",
            ["synthesize", "open_round"],
        )

    g.add_node("synthesize", _synthesizer_node(deps))
    if k_max == 0:
        g.add_edge("verify", "synthesize")
    g.add_node("reverify", _reverify_node(deps))
    g.add_edge("synthesize", "reverify")
    # H5 non-skippability is REACHABILITY (design/00 property #2), not convention: in
    # BOTH arms the only edge into END leaves `finalize` and the only edge into
    # `finalize` leaves `hitl` — no compiled path finalizes without the interrupt.
    g.add_node("hitl", _hitl_node(deps))
    g.add_edge("reverify", "hitl")
    g.add_node("finalize", _finalize_node(deps))
    g.add_edge("hitl", "finalize")
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)
