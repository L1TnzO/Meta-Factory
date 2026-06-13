"""recall — Tier 2: recuperación dirigida MEDIDA (stdlib, cero modelo, SOTA sin embeddings).

Devuelve la REBANADA relevante (un episodio de LOG, un ADR, una sección de reference), no el
corpus — "recuperación al presupuesto de contexto". Scoring estilo Generative-Agents:
relevancia léxica (domina) · recencia · importancia (el conocimiento NEGATIVO —descartado,
lección— pesa más: es el que más se evapora y más evita re-litigar).

Mide: cada `recall` registra un evento en el journal (observador puro). Con la serie se decide
si el índice semántico (embeddings) se justifica — "medir antes de invertir". Hoy NO se construye
(postura SOTA: no invertir en retrieval no medido). El sello ADR-009 da el aid de frescura.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import journal
from ..docs_manifest import body_of

_TS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z")
_WORD = re.compile(r"[a-záéíóúñü0-9]{3,}", re.IGNORECASE)
_STOP = {
    "the", "and", "for", "que", "con", "los", "las", "del", "una", "por", "este", "esta",
    "como", "para", "más", "sin", "está", "son", "qué", "the", "are", "was", "with", "not",
}
_NEG = ("descartado", "descartada", "lección", "leccion", "negativ", "gotcha", "residual", "honest", "falló", "fallo")


@dataclass
class Unit:
    source: str          # "docs/LOG.md#2026-...", "decisions/007", "reference/MEMORY-ARCHITECTURE.md#§3"
    kind: str            # log | adr | ref
    title: str
    text: str
    ts: str | None = None
    _terms: set[str] = field(default_factory=set)


def _tok(s: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(s)} - _STOP


def _first_ts(text: str) -> str | None:
    m = _TS.search(text)
    return m.group(0) if m else None


def gather_units(root: Path) -> list[Unit]:
    root = Path(root)
    units: list[Unit] = []

    # LOG episodes (por `## `)
    log = root / "docs" / "LOG.md"
    if log.exists():
        body = body_of(log.read_text(encoding="utf-8"))
        for chunk in re.split(r"\n(?=## )", body):
            chunk = chunk.strip()
            if not chunk.startswith("## "):
                continue
            head = chunk.splitlines()[0][3:].strip()
            ts = _first_ts(head)
            anchor = (ts or head[:24]).replace(" ", "")
            units.append(Unit(f"docs/LOG.md#{anchor}", "log", head, chunk, ts))

    # ADRs (un doc cada uno)
    for p in sorted((root / "docs" / "decisions").glob("*.md")):
        text = body_of(p.read_text(encoding="utf-8"))
        title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), p.stem)
        units.append(Unit(f"docs/decisions/{p.name}", "adr", title, text, _first_ts(text)))

    # reference (por sección `## `)
    for p in sorted((root / "docs" / "reference").glob("*.md")):
        text = body_of(p.read_text(encoding="utf-8"))
        rel = f"docs/reference/{p.name}"
        for chunk in re.split(r"\n(?=## )", text):
            chunk = chunk.strip()
            if not chunk:
                continue
            head = chunk.splitlines()[0].lstrip("# ").strip() or p.stem
            units.append(Unit(f"{rel}#{head[:32]}", "ref", head, chunk, _first_ts(chunk)))

    for u in units:
        u._terms = _tok(u.title + " " + u.text)
    return units


def _recency(ts: str | None, now: datetime) -> float:
    if not ts:
        return 0.4  # neutral para lo no-datado (reference estable)
    m = _TS.search(ts)
    if not m:
        return 0.4
    raw = m.group(0)
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ"):
        try:
            dt = datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            break
        except ValueError:
            dt = None
    if dt is None:
        return 0.4
    days = max(0.0, (now - dt).total_seconds() / 86400.0)
    return 1.0 / (1.0 + days / 30.0)   # decae con vida media ~1 mes


def score(unit: Unit, q_terms: set[str], now: datetime) -> float:
    if not q_terms:
        return 0.0
    title_terms = _tok(unit.title)
    matched = unit._terms & q_terms
    if not matched:
        return 0.0  # retrieval DIRIGIDO: si no matchea la query, no se devuelve
    lexical = len(matched) / len(q_terms)
    title_boost = 0.5 * (len(title_terms & q_terms) / len(q_terms))
    importance = (0.5 if unit.kind == "adr" else 0.0) + (0.5 if any(n in unit.text.lower() for n in _NEG) else 0.0)
    return 2.0 * lexical + 0.6 * title_boost + 0.8 * _recency(unit.ts, now) + 0.4 * importance


def recall(root: Path, query: str, k: int = 5) -> list[tuple[Unit, float]]:
    now = datetime.now(timezone.utc)
    q = _tok(query)
    scored = [(u, score(u, q, now)) for u in gather_units(root)]
    hits = sorted([s for s in scored if s[1] > 0], key=lambda x: x[1], reverse=True)[:k]
    # MEDICIÓN: registrar el recall (observador puro, igual que el contador de delegaciones)
    journal.append(root, "recall", query=query, n=len(hits), refs=[u.source for u, _ in hits])
    return hits


def _snippet(unit: Unit, q_terms: set[str], maxlines: int = 2) -> list[str]:
    out = []
    for line in unit.text.splitlines()[1:]:
        s = line.strip(" -*#")
        if s and (_tok(s) & q_terms):
            out.append(s[:96])
            if len(out) >= maxlines:
                break
    return out or [unit.text.splitlines()[1].strip()[:96]] if len(unit.text.splitlines()) > 1 else []


def render(root: Path, query: str, hits: list[tuple[Unit, float]]) -> str:
    if not hits:
        return (f"VEREDICTO  recall — SIN COINCIDENCIAS   (exit 0)\n"
                f"RESUMEN    nada en memoria matchea «{query}» (re-derivá con `meta check` si dudás del estado)")
    q = _tok(query)
    lines = [f"VEREDICTO  recall «{query}» — {len(hits)} rebanada(s)   (exit 0)",
             "RESUMEN    rebanadas relevantes (no el corpus); abrí la fuente para DECIDIR — esto TRIAJA"]
    for u, sc in hits:
        lines.append(f"  [{sc:.2f}] {u.source}  ({u.ts or 'estable'})")
        for snip in _snippet(u, q):
            lines.append(f"        · {snip}")
    return "\n".join(lines)
