#!/usr/bin/env python3
"""digestion_law.py — single source of the §7.4 digestion law (SMS-v2).

The digest is the DESTINATION of the corpus (§7.4): one typed record per
INCLUDED pdf-ok paper, shaped to be directly ingestible by the prototype's
memory. It is a SYNTHESIS layer on top of the FROZEN extraction verdict
(§7.6, extraction.csv), never a re-derivation: the typed facets
(operaciones/representacion/F) are carried forward IDENTICALLY from the
extraction row — this module BINDS them by set-equality so a digest cannot
silently drift from the measured facet table. What is NEW (the judgment the
digest adds) is prose (`problema`, `mecanismo`, `evaluacion`), the key
numbers (`numeros_clave`), and the Meta-Factory lens (`mf_aplicabilidad`):
each digest tags which MF memory anchor it touches and with what STANCE,
from CLOSED vocabularies — that is what makes this gate deterministic.

Authority for the vocabulary is research/corpus/digestion/PROMPT.md and
protocol §7.4. The 10-facet F vocabulary is imported from
screening_pass.FACETS (via extraction_law), never duplicated.

Both make_digest_sheet.py and verify_digest_verdicts.py import this module
and never re-derive the law. `validate_digest(record, extraction_row)`
returns EVERY violation (never just the first), given the digest record and
its matching frozen extraction row as ground truth.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extraction_law as xl  # noqa: E402  (frozen §7.6 law + F vocabulary)

# ---------------------------------------------------------------- schema
# Facets carried into the digest input from the frozen extraction row.
INPUT_FIELDS = [
    "key", "cita", "operaciones", "representacion", "F", "evidencia_tipo",
    "plan_estado", "pdf",
]

# The digest record itself (order is canonical; the gate checks the set).
DIGEST_FIELDS = [
    "key", "cita", "problema", "mecanismo", "operaciones", "representacion",
    "evaluacion", "numeros_clave", "F", "mf_aplicabilidad", "notes",
]

# Facets that MUST equal (as a set) the frozen extraction verdict — a digest
# carries the measured facets forward, it does not re-invent them.
BOUND_FACETS = ["operaciones", "representacion", "F"]

# ---------------------------------------------------------------- MF lens vocab
# Closed set of Meta-Factory memory anchors (protocol §2 / §3 RQ↔need map).
MF_ANCLAS = frozenset({
    "G-M1",          # discretionary write trigger (RQ2)
    "G-M2",          # measured retrieval layer (RQ3, ADR-019)
    "TIER-DOCS",     # Tier-1 typed narrative / docs = truth (RQ1)
    "TIER-INDICE",   # Tier-3 derived index = cache (RQ1/RQ3)
    "FIDELIDAD",     # anti-drift: provenance, staleness, poisoning (RQ4/RQ6)
    "COSTURAS",      # single-source-per-fact / multi-store seams (§8.2 MEM-ARCH)
    "NEGATIVO",      # negative knowledge / re-derivation over recall (§7 MEM-ARCH)
    "CONSOLIDACION", # promotion of transient gotchas to durable recipes (§8.3)
    "PLAN-ESTADO",   # plan-state as first-class memory (P13)
    "COSTO",         # context economy: tokens/cache/latency/compaction (RQ5)
})

# Closed set of stances a digest may take toward an MF anchor.
POSTURAS = frozenset({
    "CONFIRMA",   # external evidence supports the current MF decision
    "REFUTA",     # external evidence challenges the current MF decision
    "EXTIENDE",   # offers a mechanism/pattern MF could adopt
    "NEUTRAL",    # relevant context, no directional force
})

# Evidence types (from extraction) that imply the paper reports numbers.
NUMERIC_EVIDENCE = frozenset({"ABLATION", "BENCHMARK-E2E", "MEDICION-COSTO"})

# The empty token for a prose field that legitimately has nothing to report.
NONE_TOKEN = "NINGUNO"

# Minimum non-whitespace length for a required prose field (rejects stubs).
PROSE_MIN = {"problema": 20, "mecanismo": 30, "evaluacion": 20, "notes": 15}

# A confirmed F facet that OBLIGES the digest to take a stance on a specific
# MF anchor (the whole reason digestion is prioritised by scarce facet: these
# are the MF differentiators — a DOCS-VERSIONADO paper MUST say something
# about Tier-1, a NEGATIVO paper about negative knowledge). The stance itself
# is free (CONFIRMA/REFUTA/EXTIENDE/NEUTRAL); only the anchor is obliged.
FACET_REQUIRES_ANCLA = {
    "DOCS-VERSIONADO": "TIER-DOCS",
    "NEGATIVO": "NEGATIVO",
}


# ---------------------------------------------------------------- helpers
def _facet_set(raw) -> set[str]:
    """Normalise a facet field (list or ';'-joined str) to a token set."""
    if isinstance(raw, list):
        return {str(t).strip() for t in raw if str(t).strip()}
    return {t.strip() for t in str(raw or "").split(";") if t.strip()}


def _nonempty(v) -> bool:
    return bool(str(v or "").strip())


# ---------------------------------------------------------------- the gate
def validate_digest(rec: dict, ext: dict) -> list[str]:
    """Return every violation of protocol §7.4's digest law (empty == valid).

    `rec` is the digest record; `ext` is its matching FROZEN extraction row
    (the ground truth). Defensive against malformed input (uses .get()) so a
    field-set mismatch surfaces alongside whatever else is checkable.
    """
    errors: list[str] = []
    key = str(rec.get("key") or "?").strip() or "?"

    # -- field set is exactly DIGEST_FIELDS
    actual, expected = set(rec.keys()), set(DIGEST_FIELDS)
    if actual != expected:
        missing, extra = sorted(expected - actual), sorted(actual - expected)
        detail = []
        if missing:
            detail.append(f"missing {missing}")
        if extra:
            detail.append(f"extra {extra}")
        errors.append(f"{key}: field set mismatch ({'; '.join(detail)})")

    # -- identity binding: key + cita must match the frozen extraction row
    if not ext:
        errors.append(f"{key}: no matching extraction row (unknown key)")
        return errors  # nothing else is groundable without the ground truth
    if str(rec.get("cita") or "").strip() != str(ext.get("cita") or "").strip():
        errors.append(f"{key}: cita drifts from extraction verdict")

    # -- carried facets must equal the frozen extraction facets (set-equality)
    for f in BOUND_FACETS:
        if _facet_set(rec.get(f)) != _facet_set(ext.get(f)):
            errors.append(
                f"{key}: {f} drifts from extraction "
                f"(digest={sorted(_facet_set(rec.get(f)))}, "
                f"ext={sorted(_facet_set(ext.get(f)))})"
            )

    # -- required prose is present and not a stub
    for f, lo in PROSE_MIN.items():
        val = str(rec.get(f) or "").strip()
        if len(val) < lo:
            errors.append(f"{key}: {f} too short/empty (<{lo} chars)")

    # -- numeros_clave: if the paper reports numeric evidence, it must cite some
    ev = _facet_set(ext.get("evidencia_tipo"))
    nums = str(rec.get("numeros_clave") or "").strip()
    if ev & NUMERIC_EVIDENCE:
        if not nums or nums == NONE_TOKEN:
            errors.append(
                f"{key}: numeros_clave empty but evidencia_tipo has "
                f"{sorted(ev & NUMERIC_EVIDENCE)} (must cite a number)"
            )
    elif not nums:
        errors.append(f"{key}: numeros_clave empty (use {NONE_TOKEN!r} if none)")

    # -- mf_aplicabilidad: >=1 well-formed {ancla, postura, nota} entry
    apps = rec.get("mf_aplicabilidad")
    anclas_seen: set[str] = set()
    if not isinstance(apps, list) or not apps:
        errors.append(f"{key}: mf_aplicabilidad must be a non-empty list")
    else:
        for i, e in enumerate(apps):
            if not isinstance(e, dict):
                errors.append(f"{key}: mf_aplicabilidad[{i}] not an object")
                continue
            anc, pos, nota = e.get("ancla"), e.get("postura"), e.get("nota")
            if anc not in MF_ANCLAS:
                errors.append(f"{key}: mf_aplicabilidad[{i}] unknown ancla {anc!r}")
            else:
                anclas_seen.add(anc)
            if pos not in POSTURAS:
                errors.append(f"{key}: mf_aplicabilidad[{i}] unknown postura {pos!r}")
            if not _nonempty(nota):
                errors.append(f"{key}: mf_aplicabilidad[{i}] nota empty")

    # -- facet -> obliged MF anchor (the differentiator teeth)
    f_conf = _facet_set(ext.get("F"))
    for facet, anc in FACET_REQUIRES_ANCLA.items():
        if facet in f_conf and anc not in anclas_seen:
            errors.append(
                f"{key}: F has {facet} => mf_aplicabilidad must take a stance on {anc}"
            )
    if str(ext.get("plan_estado") or "").strip() == "SI" and "PLAN-ESTADO" not in anclas_seen:
        errors.append(f"{key}: plan_estado=SI => mf_aplicabilidad must take a stance on PLAN-ESTADO")

    return errors


# Re-export so downstream tooling has one import for the whole law.
FACETS = xl.VOCAB["F"]
