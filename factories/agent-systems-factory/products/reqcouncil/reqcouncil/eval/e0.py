"""E0 — judge calibration against the 760 human-annotated pairs (docs/design/03 §2).

Blocking gate: `judge_agreement` (config/thresholds.yml) over POOLED agreement with the
human Score across both corpora. Per-corpus numbers are reported next to the paper's
published SAME-model references (Qwen3-32B local: 0.8222 interview / 0.9138 system-desc).

Runs are resumable: every verdict is appended to `verdicts.jsonl` keyed by a content
hash of (model + system prompt + user message), so an interrupted run (rate limits,
network) re-pays nothing on retry. Every run pins model id + prompt hashes (design/03 §2).
"""

from __future__ import annotations

import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..attribution.judge import USER_TEMPLATE, AlignmentJudge
from ..llm import ChatClient
from .golden import CORPORA, Pair, load_pairs, system_prompt_path
from .metrics import Confusion, report_text

# Published same-model references (datasets/inter2us/.../Qwen3-32B_report.txt).
PAPER_REFERENCE = {"interview": 0.8222, "system_desc": 0.9138}


def pair_key(model: str, system_prompt: str, pair: Pair) -> str:
    user = USER_TEMPLATE.format(story=pair.story, chunk=pair.chunk)
    digest = hashlib.sha256(f"{model}\x00{system_prompt}\x00{user}".encode()).hexdigest()
    return digest[:16]


@dataclass(frozen=True)
class E0Result:
    pooled: Confusion
    per_corpus: dict[str, Confusion]
    agreement: float
    gate_min: float
    green: bool
    report: str


def _load_cache(path: Path) -> dict[str, int]:
    cache: dict[str, int] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                cache[entry["key"]] = int(entry["pred"])
    return cache


def run_e0(
    client: ChatClient,
    models_cfg: dict,
    thresholds: dict,
    *,
    runs_dir: Path,
    corpora: tuple[str, ...] = CORPORA,
    limit: int | None = None,
    data_root: Path | None = None,
    workers: int = 8,
) -> E0Result:
    runs_dir.mkdir(parents=True, exist_ok=True)
    cache_path = runs_dir / "verdicts.jsonl"
    cache = _load_cache(cache_path)

    per_corpus: dict[str, Confusion] = {}
    prompt_shas: dict[str, str] = {}
    t0 = time.perf_counter()

    with cache_path.open("a", encoding="utf-8") as cache_file:
        for corpus in corpora:
            system_prompt = system_prompt_path(corpus, data_root).read_text(encoding="utf-8")
            prompt_shas[corpus] = hashlib.sha256(system_prompt.encode()).hexdigest()[:12]
            judge = AlignmentJudge.from_config(client, system_prompt, models_cfg)
            pairs = load_pairs(corpus, data_root)
            if limit is not None:
                pairs = pairs[:limit]

            # Parallel judging (rate limits are the ceiling, per-request latency was:
            # sequential ~3.4s/pair used ~18 of SiliconFlow's 500 RPM — measured).
            # The JSONL cache stays append-only under a lock; result order is the
            # PAIR order (keyed dict), so metrics are identical to a sequential run.
            lock = threading.Lock()
            done_count = [0]
            keys = [pair_key(client.model, system_prompt, p) for p in pairs]

            def judge_one(pair: Pair, key: str) -> int:
                if key not in cache:
                    verdict = judge.judge(pair.story, pair.chunk)
                    with lock:
                        cache[key] = verdict.pred
                        cache_file.write(
                            json.dumps(
                                {
                                    "key": key,
                                    "corpus": corpus,
                                    "index": pair.index,
                                    "human": pair.human,
                                    "pred": verdict.pred,
                                    "raw": verdict.raw[:80],
                                    "prompt_tokens": verdict.prompt_tokens,
                                }
                            )
                            + "\n"
                        )
                        cache_file.flush()
                with lock:
                    done_count[0] += 1
                    if done_count[0] % 25 == 0 or done_count[0] == len(pairs):
                        print(
                            f"[e0] {corpus}: {done_count[0]}/{len(pairs)}",
                            file=sys.stderr,
                            flush=True,
                        )
                return cache[key]

            with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
                y_pred = list(pool.map(judge_one, pairs, keys))
            y_true = [p.human for p in pairs]

            per_corpus[corpus] = Confusion.from_labels(y_true, y_pred)

    pooled = Confusion(0, 0, 0, 0)
    for cm in per_corpus.values():
        pooled = pooled + cm
    gate_min = float(thresholds["gates"]["judge_agreement"]["min"])
    agreement = pooled.accuracy
    green = agreement >= gate_min

    report = _render_report(client.model, per_corpus, pooled, agreement, gate_min, green, limit)
    (runs_dir / "report.txt").write_text(report + "\n", encoding="utf-8")
    (runs_dir / "run.json").write_text(
        json.dumps(
            {
                "experiment": "E0",
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                "model": client.model,
                "api_base": client.api_base,
                "system_prompt_sha": prompt_shas,
                "limit": limit,
                "pairs_judged": pooled.total,
                "agreement": round(agreement, 4),
                "gate_judge_agreement_min": gate_min,
                "green": green,
                "elapsed_s": round(time.perf_counter() - t0, 1),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return E0Result(pooled, per_corpus, agreement, gate_min, green, report)


def _render_report(
    model: str,
    per_corpus: dict[str, Confusion],
    pooled: Confusion,
    agreement: float,
    gate_min: float,
    green: bool,
    limit: int | None,
) -> str:
    lines = [f"=== E0 Judge Calibration === model: {model}"]
    if limit is not None:
        lines.append(f"!! PARTIAL RUN (--limit {limit}) — not gate evidence !!")
    for corpus, cm in per_corpus.items():
        ref = PAPER_REFERENCE.get(corpus)
        # Same-model only for the qwen arm; for alternates it is a cross-model baseline.
        ref_txt = f"  (paper Qwen3-32B ref: {ref:.4f})" if ref is not None else ""
        lines += [f"", f"--- {corpus} (n={cm.total}){ref_txt}", report_text(cm)]
    lines += [
        "",
        f"--- POOLED (n={pooled.total})",
        report_text(pooled),
        "",
        f"judge_agreement = {agreement:.4f}  gate >= {gate_min}  ->  "
        + ("GREEN" if green else "RED"),
    ]
    return "\n".join(lines)
