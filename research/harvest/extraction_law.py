#!/usr/bin/env python3
"""extraction_law.py — single source of the §7.6 extraction law (SMS-v2).

Formulario CONGELADO 2026-07-16 (protocol §7.6); vocabulary AUTHORITY is
research/corpus/extraction/PROMPT.md. Defines the sheet schema
(IDENTITY_COLUMNS + VERDICT_COLUMNS), the closed vocabularies per field
(VOCAB), and validate_row(row) -> list[str] returning EVERY violation of the
frozen rules (never just the first one). The F facet vocabulary is imported
from screening_pass.FACETS, never duplicated (rule 7: F ties to the same
10-facet closed set that already gates F_screening upstream).

Both make_extraction_sheet.py and verify_extraction_verdicts.py import this
module and never re-derive the law.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import screening_pass as sp  # noqa: E402  (frozen 10-facet vocabulary: FACETS)

# ---------------------------------------------------------------- schema
IDENTITY_COLUMNS = ["key", "source", "year", "title", "pdf_status", "F_screening"]

VERDICT_COLUMNS = [
    "key", "mem_tipos", "representacion", "operaciones", "trigger", "retrieval",
    "mide_lectura", "alcance", "multiagente", "fidelidad_procedencia", "benchmarks",
    "metricas", "fallos_mitigaciones", "evidencia_tipo", "F", "handoff",
    "plan_estado", "cita", "notes",
]

# ---------------------------------------------------------------- vocab
VOCAB: dict[str, frozenset] = {
    "mem_tipos": frozenset({
        "TRABAJO", "EPISODICA", "SEMANTICA", "PROCEDIMENTAL", "PARAMETRICA",
        "MULTIMODAL", "NA",
    }),
    "representacion": frozenset({
        "DOCS-ARCHIVOS", "VECTOR", "GRAFO", "PARAMETROS", "HIBRIDA", "NA",
    }),
    "operaciones": frozenset({
        "WRITE", "ADMISION", "CONSOLIDACION", "OLVIDO", "ACTUALIZACION", "NA",
    }),
    "trigger": frozenset({
        "DISCRECIONAL-LLM", "EVENTO-DETERMINISTA", "CHECKPOINT", "PRESUPUESTO", "NA",
    }),
    "retrieval": frozenset({
        "GREP-ARCHIVOS", "RANKING", "EMBEDDINGS", "GRAFO", "NA",
    }),
    "alcance": frozenset({
        "TAREA", "SESION", "PROYECTO", "ORGANIZACION", "NA",
    }),
    "metricas": frozenset({
        "EXITO", "ITERACION", "COSTO-TOKENS", "LATENCIA", "OTRA", "NINGUNA",
    }),
    "evidencia_tipo": frozenset({
        "ABLATION", "BENCHMARK-E2E", "MEDICION-COSTO", "CUALITATIVA",
    }),
    "handoff": frozenset({"PUNTEROS", "CONTENIDO", "CONTRATO"}),
    "F": frozenset(sp.FACETS),
}

ALONE = frozenset({"NA", "NINGUNO", "NINGUNA"})
SINO_FIELDS = ["mide_lectura", "multiagente", "fidelidad_procedencia", "plan_estado"]
FREE_TEXT_REQUIRED = ["benchmarks", "fallos_mitigaciones", "cita", "notes"]
# Closed multi-label fields checked generically via VOCAB (handoff excluded:
# it has the sui-generis 'NO alone XOR subset' rule, checked separately).
MULTI_VOCAB_FIELDS = [
    "mem_tipos", "representacion", "operaciones", "trigger", "retrieval",
    "alcance", "metricas", "evidencia_tipo", "F",
]


# ---------------------------------------------------------------- helpers
def _split_tokens(raw: str) -> list[str]:
    return raw.split(";")


def _check_multi_field(field: str, raw: str, errors: list[str], key: str) -> None:
    vocab = VOCAB[field]
    tokens = _split_tokens(raw)
    if any(t != t.strip() or not t for t in tokens):
        errors.append(f"{key}: {field} malformed tokens ({raw!r})")
        return
    unknown = [t for t in tokens if t not in vocab]
    if unknown:
        errors.append(f"{key}: {field} unknown token(s) {unknown} (raw={raw!r})")
        return
    alone_hits = [t for t in tokens if t in ALONE]
    if alone_hits and len(tokens) > 1:
        errors.append(f"{key}: {field} ALONE token {alone_hits} must appear alone (raw={raw!r})")


def _check_handoff(raw: str, errors: list[str], key: str) -> None:
    if raw == "NO":
        return
    tokens = _split_tokens(raw)
    if any(t != t.strip() or not t for t in tokens):
        errors.append(f"{key}: handoff malformed tokens ({raw!r})")
        return
    unknown = [t for t in tokens if t not in VOCAB["handoff"]]
    if unknown:
        errors.append(
            f"{key}: handoff must be NO alone or a subset of {sorted(VOCAB['handoff'])} (raw={raw!r})"
        )


# ---------------------------------------------------------------- the gate
def validate_row(row: dict) -> list[str]:
    """Return every violation of protocol §7.6's frozen extraction law (empty == valid).

    Defensive against a malformed/short row (uses .get() throughout) so a
    column-set mismatch still surfaces alongside whatever else is checkable,
    instead of raising.
    """
    errors: list[str] = []
    key = (row.get("key") or "?").strip() or "?"

    actual, expected = set(row.keys()), set(VERDICT_COLUMNS)
    if actual != expected:
        missing, extra = sorted(expected - actual), sorted(actual - expected)
        detail = []
        if missing:
            detail.append(f"missing {missing}")
        if extra:
            detail.append(f"extra {extra}")
        errors.append(f"{key}: column set mismatch ({'; '.join(detail)})")

    def field(name: str) -> str:
        return (row.get(name) or "").strip()

    for f in MULTI_VOCAB_FIELDS:
        _check_multi_field(f, field(f), errors, key)

    _check_handoff(field("handoff"), errors, key)

    for f in SINO_FIELDS:
        val = field(f)
        if val not in {"SI", "NO"}:
            errors.append(f"{key}: {f} must be SI/NO (got {val!r})")

    for f in FREE_TEXT_REQUIRED:
        if not field(f):
            errors.append(f"{key}: {f} is empty")

    if field("mide_lectura") == "SI":
        f_tokens = _split_tokens(field("F"))
        if "RETRIEVAL-MEDIDO" not in f_tokens:
            errors.append(f"{key}: mide_lectura=SI requires RETRIEVAL-MEDIDO in F")

    return errors
