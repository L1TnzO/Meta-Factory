"""metrics — Tier 0 series de hechos (contadores, costos, frecuencias). Append-only JSONL,
gitignored, regenerable. CERO llamadas al modelo: todo es file-IO + aritmética (ADR-008).

Complementa journal.py (que captura *eventos*); este módulo captura *series*.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from metafactory.graph import pricing
from metafactory.memory import journal

MEMDIR = ".metamem"

# Precios por token (USD), DERIVADOS de `graph.pricing.PRICING` (ADR-021, PRICING-LEDGER INC-1) — ya NO es
# una segunda tabla de mano: single-source, así se mata la deriva (esta tabla antes cotizaba Opus a
# 15/75, un número de la era Opus-4.1, 3x sobre el precio real §1.2). `cache_write` toma `write_5m`
# (default honesto: el stream OTLP reporta un conteo sin etiqueta de TTL — ver graph/pricing.py).
PRICES: dict[str, dict[str, float]] = {
    tier: {
        "input":       p.base_input / 1_000_000,
        "output":      p.output / 1_000_000,
        "cache_write": p.write_5m / 1_000_000,
        "cache_read":  p.hit_refresh / 1_000_000,
    }
    for tier, p in pricing.PRICING.items()
}


def metrics_path(root: Path) -> Path:
    return Path(root) / MEMDIR / "metrics.jsonl"


def capture(root: Path, **fields: Any) -> dict:
    """Anexa una métrica. Best-effort: nunca levanta excepción (la captura no puede romper la línea).
    Devuelve el registro escrito (o parcial si falló el IO)."""
    rec = {"ts": journal.now(), **fields}
    try:
        p = metrics_path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return rec


def read(root: Path, limit: int | None = None) -> list[dict]:
    """Lee todas las métricas. Tolera líneas malformadas."""
    p = metrics_path(root)
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out[-limit:] if limit else out


def tier_for(model_id: str) -> str:
    """Mapea un model-id a una clave de PRICES por substring. Devuelve 'sonnet' como default.
    Delega a `graph.pricing.tier_for` (single-source): la misma lógica, un solo lugar (ADR-021)."""
    return pricing.tier_for(model_id)


def rollup_from_transcript(path: Path) -> dict[str, dict[str, int]]:
    """Parsea un transcript JSONL y acumula tokens por model_id.

    Cada línea es un objeto JSON. Los mensajes de asistente traen usage en:
    - top-level: `usage` + `model`
    - anidado: `message.usage` + `message.model`

    Claves de usage: input_tokens, output_tokens, cache_creation_input_tokens,
    cache_read_input_tokens. Cualquier clave faltante defaults a 0.
    """
    result: dict[str, dict[str, int]] = {}
    p = Path(path)
    if not p.exists():
        return result
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Intentar obtener usage + model tanto del top-level como de message.*
        usage = None
        model_id = ""
        if isinstance(obj.get("usage"), dict):
            usage = obj["usage"]
            model_id = str(obj.get("model", ""))
        elif isinstance(obj.get("message"), dict):
            msg = obj["message"]
            if isinstance(msg.get("usage"), dict):
                usage = msg["usage"]
                model_id = str(msg.get("model", ""))
        if usage is None or not model_id:
            continue
        entry = result.setdefault(model_id, {
            "input": 0, "output": 0,
            "cache_creation": 0, "cache_read": 0,
        })
        entry["input"]          += int(usage.get("input_tokens", 0))
        entry["output"]         += int(usage.get("output_tokens", 0))
        entry["cache_creation"] += int(usage.get("cache_creation_input_tokens", 0))
        entry["cache_read"]     += int(usage.get("cache_read_input_tokens", 0))
    return result


def cache_series(transcript: Path) -> list[tuple[int, int]]:
    """Serie ORDENADA por turno de `(cache_creation_input_tokens, cache_read_input_tokens)`, una tupla
    por mensaje de asistente (mismo shape de extracción que `rollup_from_transcript`, sin el requisito de
    `model_id` — acá el eje es el TURNO, no el modelo). Transcript ausente → serie vacía (re-derivable)."""
    out: list[tuple[int, int]] = []
    p = Path(transcript)
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = None
        if isinstance(obj.get("usage"), dict):
            usage = obj["usage"]
        elif isinstance(obj.get("message"), dict) and isinstance(obj["message"].get("usage"), dict):
            usage = obj["message"]["usage"]
        if usage is None:
            continue
        out.append((
            int(usage.get("cache_creation_input_tokens", 0)),
            int(usage.get("cache_read_input_tokens", 0)),
        ))
    return out


def detect_expirations(series: list[tuple[int, int]], fraction: float = 0.5) -> int:
    """Detecta expiraciones de cache a mitad de sesión: un turno `i>=1` cuenta como expiración cuando su
    `cache_creation` re-escribe una porción significativa (>= `fraction`) del cache-read PICO visto hasta
    ese turno inclusive — la señal de que el cache anterior venció y se re-escribió. Dos lados: un turno
    0 (warm-up) nunca cuenta (no hay pico previo); una serie ESTABLE (sin picos de cache_creation
    relativos al read-peak) cuenta 0."""
    count = 0
    max_read_so_far = 0
    for i, (cache_creation, cache_read) in enumerate(series):
        if cache_read > max_read_so_far:
            max_read_so_far = cache_read
        if i == 0:
            continue
        if max_read_so_far > 0 and cache_creation >= fraction * max_read_so_far:
            count += 1
    return count


def churn_cost_share(transcript: Path, fraction: float = 0.5) -> dict:
    """Fraction of session $ spent RE-WRITING expired/compacted cache (the INC-5 trigger metric).

    Self-contained: walks ONE transcript once (same per-message usage+model extraction as
    `rollup_from_transcript`/`cache_series`). A message i>=1 is a CHURN turn when its
    `cache_creation_input_tokens` re-writes >= `fraction` of the PEAK `cache_read_input_tokens` seen up
    to and including that message — the same expiration signal `detect_expirations` uses. Its
    cache_creation tokens are money spent because the prior cache expired or was compacted away.

    - Numerator `churn_usd` = sum over churn turns of `cache_creation / 1e6 * PRICING[tier_for(model)].write_5m`.
    - Denominator `session_usd` = full priced rollup of EVERY message (input*base_input + output*output +
      cache_creation*write_5m + cache_read*hit_refresh), same transcript.
    - `share` = churn_usd/session_usd, or 0.0 when session_usd == 0.
    Missing / empty transcript → {"churn_usd": 0.0, "session_usd": 0.0, "share": 0.0} (re-derivable, honest).

    Returns {"churn_usd": float, "session_usd": float, "share": float}.
    """
    p = Path(transcript)
    if not p.exists():
        return {"churn_usd": 0.0, "session_usd": 0.0, "share": 0.0}

    churn_usd = 0.0
    session_usd = 0.0
    max_read_so_far = 0
    turn = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = None
        model_id = ""
        if isinstance(obj.get("usage"), dict):
            usage = obj["usage"]
            model_id = str(obj.get("model", ""))
        elif isinstance(obj.get("message"), dict):
            msg = obj["message"]
            if isinstance(msg.get("usage"), dict):
                usage = msg["usage"]
                model_id = str(msg.get("model", ""))
        if usage is None:
            continue
        # A message with usage but no model id is priced at the sonnet default (tier_for("") → "sonnet")
        # — it is NOT skipped, its tokens are real spend even when the model field is absent/blank.

        input_tok = int(usage.get("input_tokens", 0))
        output_tok = int(usage.get("output_tokens", 0))
        cache_creation = int(usage.get("cache_creation_input_tokens", 0))
        cache_read = int(usage.get("cache_read_input_tokens", 0))

        session_usd += pricing.price_tokens(
            model_id, input_tokens=input_tok, output_tokens=output_tok,
            cache_creation=cache_creation, cache_read=cache_read,
        )

        if cache_read > max_read_so_far:
            max_read_so_far = cache_read
        if turn >= 1 and max_read_so_far > 0 and cache_creation >= fraction * max_read_so_far:
            churn_usd += pricing.price_tokens(model_id, cache_creation=cache_creation)
        turn += 1

    share = churn_usd / session_usd if session_usd > 0 else 0.0
    return {"churn_usd": churn_usd, "session_usd": session_usd, "share": share}


def _parse_ts(raw: str) -> datetime | None:
    """Best-effort ISO-8601 parse (accepts a trailing `Z`). Returns None on missing/malformed input —
    a turn with no parseable timestamp simply can't anchor a blocking-gap measurement."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_slot_spawn(content: Any) -> bool:
    """True when an assistant `content` list carries a `tool_use` block spawning a delegated slot
    (`Task` or `Agent` — the two tool names Claude Code has used for subagent spawns)."""
    if not isinstance(content, list):
        return False
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") in ("Task", "Agent"):
            return True
    return False


def slot_residency_share(transcript: Path, gap_min: float = 2.0, fraction: float = 0.5) -> dict:
    """USD share of the increment spent on orchestrator cache-RESIDENCY across delegated-slot boundaries
    (the cost INC-6's headless `claude -p` would eliminate; the delegation twin of `churn_cost_share`).

    A delegated slot blocks the orchestrator synchronously while the subagent's own turns live in a
    SEPARATE (sidechain) transcript, so the orchestrator emits no billed turns while the slot runs — the
    only slot-attributable orchestrator cost is the RESUME turn re-writing a prefix that expired while it
    was blocked. Self-contained: walks ONE transcript once (same per-message usage+model extraction as
    `rollup_from_transcript`/`cache_series`), skipping `isSidechain: true` turns entirely (the subagent's
    own cost — excluded from both numerator and denominator).

    A turn is a slot-spawn when its assistant `content` carries a `tool_use` block named `Task`/`Agent`.
    For each slot-spawn S, the resume turn R is the first LATER orchestrator turn whose timestamp is
    `>= gap_min` minutes after S's (a blocking gap); no such turn -> that slot contributes 0. R is an
    EXPIRATION when its `cache_creation_input_tokens >= fraction * peak_read` (peak `cache_read_input_
    tokens` seen so far, inclusive of R — the same expiration signal `detect_expirations` uses). Only
    expirations add residency, priced at `write_5m` (same convention `churn_cost_share`'s numerator uses).

    - `residency_usd` = sum over expiring resumes of `pricing.price_tokens(model, cache_creation=...)`.
    - `session_usd` = full priced rollup of every (non-sidechain) orchestrator turn.
    - `share` = residency_usd/session_usd, or 0.0 when session_usd == 0.
    - `slots` = count of slot-spawn turns (regardless of whether their resume expired).
    Missing / empty transcript -> {"residency_usd": 0.0, "session_usd": 0.0, "share": 0.0, "slots": 0}
    (re-derivable, honest).

    Returns {"residency_usd": float, "session_usd": float, "share": float, "slots": int}.
    """
    p = Path(transcript)
    if not p.exists():
        return {"residency_usd": 0.0, "session_usd": 0.0, "share": 0.0, "slots": 0}

    turns: list[dict[str, Any]] = []
    peak_so_far = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("isSidechain") is True:
            continue  # the subagent's own cost — excluded from both numerator and denominator

        usage = None
        model_id = ""
        content: Any = None
        if isinstance(obj.get("usage"), dict):
            usage = obj["usage"]
            model_id = str(obj.get("model", ""))
            content = obj.get("content")
        elif isinstance(obj.get("message"), dict):
            msg = obj["message"]
            if isinstance(msg.get("usage"), dict):
                usage = msg["usage"]
                model_id = str(msg.get("model", ""))
                content = msg.get("content")
        if usage is None:
            continue

        cache_read = int(usage.get("cache_read_input_tokens", 0))
        if cache_read > peak_so_far:
            peak_so_far = cache_read

        turns.append({
            "ts": _parse_ts(str(obj.get("timestamp", ""))),
            "model": model_id,
            "input": int(usage.get("input_tokens", 0)),
            "output": int(usage.get("output_tokens", 0)),
            "cache_creation": int(usage.get("cache_creation_input_tokens", 0)),
            "cache_read": cache_read,
            "is_spawn": _is_slot_spawn(content),
            "peak": peak_so_far,  # cache_read peak seen so far, inclusive of this turn
        })

    session_usd = 0.0
    for t in turns:
        session_usd += pricing.price_tokens(
            t["model"], input_tokens=t["input"], output_tokens=t["output"],
            cache_creation=t["cache_creation"], cache_read=t["cache_read"],
        )

    residency_usd = 0.0
    slots = 0
    gap = timedelta(minutes=gap_min)
    for i, t in enumerate(turns):
        if not t["is_spawn"]:
            continue
        slots += 1
        if t["ts"] is None:
            continue
        resume = None
        for later in turns[i + 1:]:
            if later["ts"] is None:
                continue
            if later["ts"] - t["ts"] >= gap:
                resume = later
                break
        if resume is None:
            continue
        if resume["peak"] > 0 and resume["cache_creation"] >= fraction * resume["peak"]:
            residency_usd += pricing.price_tokens(resume["model"], cache_creation=resume["cache_creation"])

    share = residency_usd / session_usd if session_usd > 0 else 0.0
    return {"residency_usd": residency_usd, "session_usd": session_usd, "share": share, "slots": slots}


def cost(rollup: dict[str, dict[str, int]], prices: dict[str, dict[str, float]] = PRICES) -> dict[str, Any]:
    """Calcula costo en USD por model_id + total.

    rollup: {model_id: {input, output, cache_creation, cache_read}} (conteos de tokens)
    Devuelve: {model_id: usd, ..., 'total': usd}
    """
    out: dict[str, Any] = {}
    total = 0.0
    for model_id, tokens in rollup.items():
        tier = tier_for(model_id)
        p = prices.get(tier, prices["sonnet"])
        usd = (
            tokens.get("input", 0) * p["input"]
            + tokens.get("output", 0) * p["output"]
            + tokens.get("cache_creation", 0) * p["cache_write"]
            + tokens.get("cache_read", 0) * p["cache_read"]
        )
        out[model_id] = usd
        total += usd
    out["total"] = total
    return out


# ── token split por modelo (el KPI de costo de DELEGATION-ACTIVATION) ─────────
# El verdadero medidor de "¿se delega lo barato?" no es delegation_rate (cuenta SPAWNS) sino el SPLIT
# de tokens entre tiers: si Opus hace el bulk, el split es ~100% opus aunque haya delegaciones. Fuente:
# `~/.claude/stats-cache.json` (lo computa Claude Code; `modelUsage` VERIFICADO presente, OBSERVABILITY-
# METRICS §1). Es MÁQUINA-GLOBAL (todos los proyectos) → señal de split, NO billing del proyecto (para eso,
# el transcript vía rollup_from_transcript). Best-effort: archivo ausente → {} (clon limpio/CI portable).

def stats_cache_path() -> Path:
    """El cache de stats per-máquina de Claude Code (totales de tokens por modelo). Fuera del repo."""
    import os
    return Path(os.path.expanduser("~/.claude/stats-cache.json"))


def model_split(path: Path | None = None) -> dict[str, dict[str, int]]:
    """Totales de tokens por model_id desde `stats-cache.json` (`modelUsage`), normalizados al shape de
    `cost()`. Best-effort: {} si el archivo falta o está malformado. Tokens MÁQUINA-GLOBALES."""
    p = path or stats_cache_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, dict[str, int]] = {}
    for model_id, u in (data.get("modelUsage") or {}).items():
        if not isinstance(u, dict):
            continue
        out[model_id] = {
            "input":          int(u.get("inputTokens", 0)),
            "output":         int(u.get("outputTokens", 0)),
            "cache_creation": int(u.get("cacheCreationInputTokens", 0)),
            "cache_read":     int(u.get("cacheReadInputTokens", 0)),
        }
    return out


def render_model_split(split: dict[str, dict[str, int]]) -> str:
    """Una línea acotada: la cuota de COSTO por tier (opus/sonnet/haiku) — 'a dónde van los tokens'. El
    objetivo de DELEGATION-ACTIVATION es mover el bulk a tiers baratos → bajar la cuota de opus. Split
    vacío → línea honesta (sin stats-cache)."""
    if not split:
        return "SPLIT      sin stats-cache (~/.claude/stats-cache.json ausente)"
    c = cost(split)
    total = c.pop("total", 0.0)
    by_tier: dict[str, float] = {}
    for model_id, usd in c.items():
        by_tier[tier_for(model_id)] = by_tier.get(tier_for(model_id), 0.0) + usd
    parts = [f"{t} {(by_tier[t] / total * 100) if total > 0 else 0:.0f}%"
             for t in ("opus", "sonnet", "haiku") if t in by_tier]
    return (f"SPLIT      costo/máquina-global por tier: {' · '.join(parts)} "
            f"(total ${total:.2f}; meta = bajar opus moviendo el bulk a sonnet/haiku)")


def aggregate(root: Path) -> dict[str, Any]:
    """Agrega hechos de journal + metrics en métricas de alto nivel:
    - delegation_rate: eventos 'delegation' / eventos 'station_run' (0.0 si sin station_run)
    - gate_streak: racha final consecutiva de station_run con gate_open=True
    - gate_pass / gate_fail: conteos totales de station_run por gate_open
    - tool_freq: Counter del campo 'tool' en las métricas
    """
    j_events = journal.read(root)
    station_runs = [e for e in j_events if e.get("kind") == "station_run"]
    delegations = [e for e in j_events if e.get("kind") == "delegation"]

    n_station = len(station_runs)
    n_delegation = len(delegations)
    delegation_rate = n_delegation / n_station if n_station > 0 else 0.0

    gate_pass = sum(1 for e in station_runs if e.get("gate_open") is True)
    gate_fail = sum(1 for e in station_runs if e.get("gate_open") is not True)

    # Racha final consecutiva de gate_open=True
    gate_streak = 0
    for e in reversed(station_runs):
        if e.get("gate_open") is True:
            gate_streak += 1
        else:
            break

    # Delegaciones por TIER del subagente (opus/sonnet/haiku): el objetivo de la activación es que el
    # bulk vaya a tiers baratos — esta es la lectura honesta de "¿a quién delegamos?". Vacío hasta que
    # el hook (arreglado en DELEG-MEASURE) empiece a emitir el evento por cada spawn.
    delegation_by_tier: Counter[str] = Counter()
    for d in delegations:
        delegation_by_tier[tier_for(str(d.get("model", "")))] += 1

    metrics = read(root)
    tool_freq: Counter[str] = Counter()
    for m in metrics:
        t = m.get("tool")
        if t:
            tool_freq[t] += 1

    return {
        "delegation_rate": delegation_rate,
        "n_delegations": n_delegation,
        "n_station_runs": n_station,
        "delegation_by_tier": delegation_by_tier,
        "gate_streak": gate_streak,
        "gate_pass": gate_pass,
        "gate_fail": gate_fail,
        "tool_freq": tool_freq,
    }


def render(root: Path, transcript: Path | None = None) -> str:
    """Produce un veredicto acotado (<=12 líneas) con el mismo estilo que report.format_verdict.

    Nunca vuelca series crudas al contexto: solo resúmenes y conteos (CONTEXT-ECONOMY §2).
    """
    agg = aggregate(root)
    lines: list[str] = []

    # Línea 1: encabezado
    lines.append("VEREDICTO  metrics — resumen de hechos")

    # Costo (solo si se pasa transcript)
    if transcript is not None:
        rollup = rollup_from_transcript(transcript)
        if rollup:
            c = cost(rollup)
            total_usd = c.pop("total", 0.0)
            parts = []
            for model_id, usd in c.items():
                pct = (usd / total_usd * 100) if total_usd > 0 else 0
                parts.append(f"{model_id} ${usd:.4f} ({pct:.0f}%)")
            lines.append(f"COSTO      {' · '.join(parts)} · total ${total_usd:.4f}")
        else:
            lines.append("COSTO      sin datos de transcript")

    # Delegación — el CONTEO lidera (lo que prueba la activación); la tasa vs station_runs se diluye en
    # la historia (lifetime) y redondearía a 0.0% con pocas delegaciones, así que va con 2 decimales y de
    # contexto. El desglose por tier muestra a QUIÉN delegamos (el objetivo: bulk a tiers baratos).
    by_tier = agg.get("delegation_by_tier") or Counter()
    tier_str = (" [" + " · ".join(f"{t} {by_tier[t]}" for t in ("opus", "sonnet", "haiku") if by_tier.get(t))
                + "]") if by_tier else ""
    pct_d = agg["delegation_rate"] * 100
    lines.append(
        f"DELEGACION {agg.get('n_delegations', 0)} evento(s){tier_str}"
        f" · {pct_d:.2f}% vs {agg.get('n_station_runs', 0)} station_run"
    )

    # Tools top-5
    freq = agg["tool_freq"]
    if freq:
        top5 = " · ".join(f"{t} {n}" for t, n in freq.most_common(5))
    else:
        top5 = "—"
    lines.append(f"TOOLS      top-5: {top5}")

    # Gates
    lines.append(
        f"GATES      pass {agg['gate_pass']} · fail {agg['gate_fail']}"
        f" · racha {agg['gate_streak']}"
    )

    # Artefacto
    lines.append(f"ARTEFACTO  {MEMDIR}/metrics.jsonl")

    # Garantía de cota (<=12 líneas)
    return "\n".join(lines[:12])
