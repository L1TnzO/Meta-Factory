"""Oracle matching protocol (docs/design/03 §4, H6 §3): the deferral declared since H3.

Match each produced requirement to a gold oracle item by **blocking top-K on embeddings
+ an LLM equivalence judge**. For each gold item we embed-rank the produced requirements,
take the top-K candidates, and ask the judge (binary "same need?") in similarity order;
the first YES is the match. Metrics: `oracle_recall` (gold covered), `oracle_precision`
(produced that matched some gold), `critical_nfr_recall` (recall restricted to NFR gold).

HONESTY (design/03 §4): this equivalence judge is NOT E0-calibrated (E0 calibrated
chunk<->story grounding, a different task). We emit `audit_sample` — the borderline
decisions (lowest-cosine YES + highest-cosine NO) — for manual audit, and the report
carries this as a named limitation (§4.5). Everything network-touching is injected
(`embed_fn`, `judge_fn`) so the whole protocol is replayed offline in tests.
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from pathlib import Path

from ..attribution.judge import parse_verdict
from ..embeddings import cosine

ORACLE_MATCH_PROMPT = Path(__file__).with_name("oracle_match.md")
_USER_TEMPLATE = (
    "GOLD REQUIREMENT:\n{gold}\n\nCANDIDATE REQUIREMENT:\n{candidate}\n\n"
    "Do they express the same underlying requirement? Answer 1 or 0.\nAnswer:"
)


@dataclass(frozen=True)
class GoldenReq:
    id: str
    text: str
    is_nfr: bool


def stories_to_golden(stories: list[str], *, prefix: str = "S", is_nfr: bool = False) -> list[GoldenReq]:
    return [GoldenReq(id=f"{prefix}{i}", text=s, is_nfr=is_nfr) for i, s in enumerate(stories)]


def oracle_to_golden(items) -> list[GoldenReq]:
    """Adapt wepgcomp.OracleItem (or any .id/.text/.is_nfr) to GoldenReq."""
    return [GoldenReq(id=it.id, text=it.text, is_nfr=bool(it.is_nfr)) for it in items]


@dataclass(frozen=True)
class MatchResult:
    recall: float
    precision: float
    critical_nfr_recall: float | None
    n_gold: int
    n_produced: int
    n_gold_matched: int
    n_produced_matched: int
    matches: list[dict]        # one row per gold item (re-derivable, auditable)
    audit_sample: dict         # {"borderline_yes": [...], "borderline_no": [...]}


def _top_k_indices(sims: list[float], k: int) -> list[int]:
    """Indices of the k largest sims, ties broken by index (stable, deterministic)."""
    order = sorted(range(len(sims)), key=lambda j: (-sims[j], j))
    return order[:k]


def match_requirements(
    produced: list[str],
    golden: list[GoldenReq],
    *,
    embed_fn,
    judge_fn,
    top_k: int = 5,
    audit_frac: float = 0.10,
) -> MatchResult:
    """Blocking top-K + equivalence-judge matching. `embed_fn(list[str])->list[list]`,
    `judge_fn(gold_text, candidate_text)->int` (1=same need)."""
    n_gold, n_prod = len(golden), len(produced)
    if n_gold == 0:
        return MatchResult(0.0, 0.0, None, 0, n_prod, 0, 0, [], {"borderline_yes": [], "borderline_no": []})

    matches: list[dict] = []
    matched_produced: set[int] = set()

    if n_prod > 0:
        vectors = embed_fn([g.text for g in golden] + list(produced))
        gv = vectors[:n_gold]
        pv = vectors[n_gold:]
    else:
        gv, pv = [[] for _ in golden], []

    for gi, g in enumerate(golden):
        cands: list[dict] = []
        matched_at: int | None = None
        if n_prod > 0:
            sims = [cosine(gv[gi], pv[pj]) for pj in range(n_prod)]
            for pj in _top_k_indices(sims, min(top_k, n_prod)):
                verdict: int | None = None
                if matched_at is None:
                    verdict = int(judge_fn(g.text, produced[pj]))
                cands.append({"produced": pj, "cosine": round(sims[pj], 4), "verdict": verdict})
                if matched_at is None and verdict == 1:
                    matched_at = pj
        if matched_at is not None:
            matched_produced.add(matched_at)
        matches.append({
            "gold_id": g.id,
            "gold_text": g.text[:160],
            "is_nfr": g.is_nfr,
            "matched": matched_at is not None,
            "matched_produced": matched_at,
            "matched_text": (produced[matched_at][:160] if matched_at is not None else None),
            "candidates": cands,
        })

    n_gold_matched = sum(1 for m in matches if m["matched"])
    nfr = [m for m in matches if m["is_nfr"]]
    critical = (sum(1 for m in nfr if m["matched"]) / len(nfr)) if nfr else None

    return MatchResult(
        recall=round(n_gold_matched / n_gold, 4),
        precision=round(len(matched_produced) / n_prod, 4) if n_prod else 0.0,
        critical_nfr_recall=round(critical, 4) if critical is not None else None,
        n_gold=n_gold,
        n_produced=n_prod,
        n_gold_matched=n_gold_matched,
        n_produced_matched=len(matched_produced),
        matches=matches,
        audit_sample=_audit_sample(matches, audit_frac),
    )


def _audit_sample(matches: list[dict], audit_frac: float) -> dict:
    """Borderline decisions for manual audit: the lowest-cosine YES + highest-cosine NO."""
    k = max(1, round(audit_frac * len(matches))) if matches else 0
    yes, no = [], []
    for m in matches:
        if m["matched"]:
            win = next(c for c in m["candidates"] if c["produced"] == m["matched_produced"])
            yes.append({"gold_id": m["gold_id"], "cosine": win["cosine"],
                        "gold_text": m["gold_text"], "matched_text": m["matched_text"]})
        elif m["candidates"]:
            top = m["candidates"][0]  # highest-cosine candidate (judged NO)
            no.append({"gold_id": m["gold_id"], "cosine": top["cosine"],
                       "gold_text": m["gold_text"]})
    yes.sort(key=lambda r: r["cosine"])              # lowest-similarity YES first
    no.sort(key=lambda r: r["cosine"], reverse=True)  # highest-similarity NO first
    return {"borderline_yes": yes[:k], "borderline_no": no[:k]}


def build_oracle_judge(chat, models_cfg: dict, cache_path: Path | None = None):
    """Wire the equivalence judge over the pinned chat client (LLM path).

    Returns (judge_fn, usage, prompt_sha). Decoding mirrors the E0 judge knobs
    (greedy, thinking off, short output) with the equivalence persona. A JSONL cache
    keyed by (model, prompt, gold, candidate) makes interrupted runs re-pay nothing.
    """
    system = ORACLE_MATCH_PROMPT.read_text(encoding="utf-8")
    prompt_sha = hashlib.sha256(system.encode()).hexdigest()[:12]
    judge_cfg = models_cfg.get("judge") or {}
    temperature = float(judge_cfg.get("temperature", 0.0))
    max_tokens = int(judge_cfg.get("max_completion_tokens", 16))
    effort = judge_cfg.get("reasoning_effort")
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    lock = threading.Lock()

    cache: dict[str, int] = {}
    if cache_path and cache_path.is_file():
        import json
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                e = json.loads(line)
                cache[e["key"]] = int(e["pred"])

    def judge_fn(gold: str, candidate: str) -> int:
        key = hashlib.sha256(
            f"{chat.model}\x00{prompt_sha}\x00{gold}\x00{candidate}".encode()
        ).hexdigest()[:16]
        with lock:
            if key in cache:
                return cache[key]
        result = chat.complete(
            [{"role": "system", "content": system},
             {"role": "user", "content": _USER_TEMPLATE.format(gold=gold, candidate=candidate)}],
            temperature=temperature,
            max_completion_tokens=max_tokens,
            reasoning_effort=str(effort) if effort is not None else None,
        )
        pred = parse_verdict(result.content)
        with lock:
            cache[key] = pred
            usage["prompt_tokens"] += result.prompt_tokens
            usage["completion_tokens"] += result.completion_tokens
            if cache_path:
                import json
                with cache_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"key": key, "pred": pred, "gold": gold[:60]}) + "\n")
        return pred

    return judge_fn, usage, prompt_sha


__all__ = ["GoldenReq", "MatchResult", "match_requirements", "stories_to_golden",
           "oracle_to_golden", "build_oracle_judge", "ORACLE_MATCH_PROMPT"]
