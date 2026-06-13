"""metrics — Tier 0 series de hechos (contadores, costos, frecuencias). Append-only JSONL,
gitignored, regenerable. CERO llamadas al modelo: todo es file-IO + aritmética (ADR-008).

Complementa journal.py (que captura *eventos*); este módulo captura *series*.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from metafactory.memory import journal

MEMDIR = ".metamem"

# Precios por token (USD) derivados de precios por millón de tokens / 1e6.
# Verificar contra pricing oficial; actualizable por diff (ADR-008 §5).
# Fuente de valores base (por MTok): opus 15/75/18.75/1.50 · sonnet 3/15/3.75/0.30 · haiku 1/5/1.25/0.10
PRICES: dict[str, dict[str, float]] = {
    "opus": {
        "input":       15.00 / 1_000_000,
        "output":      75.00 / 1_000_000,
        "cache_write": 18.75 / 1_000_000,
        "cache_read":   1.50 / 1_000_000,
    },
    "sonnet": {
        "input":        3.00 / 1_000_000,
        "output":      15.00 / 1_000_000,
        "cache_write":  3.75 / 1_000_000,
        "cache_read":   0.30 / 1_000_000,
    },
    "haiku": {
        "input":        1.00 / 1_000_000,
        "output":       5.00 / 1_000_000,
        "cache_write":  1.25 / 1_000_000,
        "cache_read":   0.10 / 1_000_000,
    },
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
    """Mapea un model-id a una clave de PRICES por substring. Devuelve 'sonnet' como default."""
    model_lower = model_id.lower()
    for tier in ("opus", "haiku", "sonnet"):
        if tier in model_lower:
            return tier
    return "sonnet"


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

    metrics = read(root)
    tool_freq: Counter[str] = Counter()
    for m in metrics:
        t = m.get("tool")
        if t:
            tool_freq[t] += 1

    return {
        "delegation_rate": delegation_rate,
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

    # Delegación
    pct_d = agg["delegation_rate"] * 100
    lines.append(f"DELEGACION tasa {pct_d:.1f}%")

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
