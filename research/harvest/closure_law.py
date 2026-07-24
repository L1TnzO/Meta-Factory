#!/usr/bin/env python3
"""Single-source law for the SMS v2 CLOSURE phase (protocol §9): the second independent pass (SPI).

Trust-chain: written and reviewed by hand, never delegated. Everything downstream (the sheet builder,
the gate, the agreement calculator) imports FROM here; nothing re-states a rule of its own.

Design notes that are law, not taste:

* **Single-source rubric.** Membership verdicts are validated by `screening_pass.validate_row` — the very
  same frozen arithmetic that decided pass 1 (protocol §7.5, rubric v2.3). The SPI is a second READER,
  not a second RUBRIC; if the rubric could drift between passes, the agreement number would measure the
  drift instead of the reliability.
* **Blindness is structural, not promised.** `BLIND_FORBIDDEN` names the pass-1 output columns that must
  never reach the second reader's input. The builder drops them and the gate re-checks the built inputs.
  `triage` is dropped too even though pass 1 had it: that makes the SPI *strictly less* informed than
  pass 1, which can only DEPRESS the measured agreement — an error in the honest direction.
* **κ only where two comparable verdicts exist.** Kinds are not decoration: a random sample re-decided
  blind (VERIFICACION) supports a reliability coefficient; a targeted set of risky flips (CONFIRMACION)
  or a set where pass 1 abstained (ADJUDICACION) does not. Pooling them would inflate κ by construction.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from screening_pass import DECISIONS, DECISIONS_CATEGORICAL, FACETS  # noqa: E402  (single source)
from screening_pass import validate_row as validate_membership_row  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent  # research/
SHEET_FULL = ROOT / "corpus/screening/screening_full.csv"
SHEET_SNOWBALL = ROOT / "corpus/screening/screening_snowball.csv"
SHEET_EXTRACTION = ROOT / "corpus/extraction/extraction.csv"
DIGEST = ROOT / "corpus/digestion/digest.jsonl"
DUPLICADOS = ROOT / "corpus/screening/queues/DUPLICADOS-INCLUIDOS.csv"
SPI_DIR = ROOT / "corpus/spi"
CHUNK_SIZE = 20

# --------------------------------------------------------------------------- kinds (§9.1)
KIND_VERIFICACION = "VERIFICACION"   # random sample, pass 1 decided firmly  -> κ
KIND_CONFIRMACION = "CONFIRMACION"   # targeted risky flips, pass 1 decided  -> no κ (not random)
KIND_ADJUDICACION = "ADJUDICACION"   # pass 1 abstained (GRIS/CE-4p)         -> no κ (nothing to compare)
KIND_CALIDAD = "CALIDAD"             # judges CONFIDENCE of a record, not membership
KIND_IDENTIDAD = "IDENTIDAD"         # judges whether two rows are one study
KINDS_MEMBERSHIP = (KIND_VERIFICACION, KIND_CONFIRMACION, KIND_ADJUDICACION)
KINDS_KAPPA = (KIND_VERIFICACION,)

# Pass-1 output that must never reach the blind second reader.
BLIND_FORBIDDEN = ("decision", "M", "T", "E", "F", "notes", "triage", "se", "selfpub", "artefacto")

# --------------------------------------------------------------------------- closed vocabularies (§9.2)
CALIDAD_VERDICTS = {"CONFIRMA-RECONSIDERAR", "DESCARTA-RECONSIDERAR", "DEGRADAR"}
IDENTIDAD_VERDICTS = {"FUSIONAR", "DISTINTOS"}
# An anchor makes the evidence checkable by a third party. Free assertions are not evidence.
EVIDENCE_ANCHORS = (
    "abstract", "resumen", "título", "titulo", "§", "sec.", "secc", "section", "tabla", "table",
    "fig", "p.", "pág", "pag.", "línea", "linea", "line", "apéndice", "apendice", "appendix",
)
EVIDENCE_MIN_CHARS = 40
NO_EVIDENCE_NEEDED = {"DESCARTA-RECONSIDERAR"}  # a false alarm has nothing to anchor

VERDICT_FIELDS = {
    KIND_VERIFICACION: ["key", "M", "T", "E", "F", "se", "selfpub", "artefacto", "decision", "evidencia", "notes"],
    KIND_CALIDAD: ["key", "veredicto", "evidencia", "notes"],
    KIND_IDENTIDAD: ["key", "pareja", "veredicto", "canonica", "evidencia", "notes"],
}
VERDICT_FIELDS[KIND_CONFIRMACION] = VERDICT_FIELDS[KIND_VERIFICACION]
VERDICT_FIELDS[KIND_ADJUDICACION] = VERDICT_FIELDS[KIND_VERIFICACION]


# --------------------------------------------------------------------------- citation keys (§9.5)
def bibkey(corpus_key: str) -> str:
    """corpus key -> BibTeX key, deterministically and reversibly enough to audit.

    The point is not aesthetics: if the citation key is a pure function of the corpus key, then a
    citation that does not correspond to a screened record cannot be written by accident, and the
    gate can check the correspondence mechanically. `W4387636003` -> `cW4387636003`;
    `2409.01344v2` -> `c240901344v2`.
    """
    import re as _re
    return "c" + _re.sub(r"[^A-Za-z0-9]", "", corpus_key)


# --------------------------------------------------------------------------- grey literature (§9.4 / §6.1)
# MANDATORY Tier-1 seeds: first-party technical documentation from the model providers. They are law,
# not a suggestion — RQ7 asks what the labs actually ship, and a grey corpus that quietly drops the
# inconvenient seed answers a different question. `key` is the stable filename stem.
GREY_TIER1: tuple[dict[str, str], ...] = (
    {"key": "anthropic-memory-tool", "org": "Anthropic", "tier": "1", "rqs": "RQ1;RQ2;RQ4",
     "title": "Memory tool (client-side files as agent memory)",
     "url": "https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool"},
    {"key": "anthropic-context-management", "org": "Anthropic", "tier": "1", "rqs": "RQ2;RQ5",
     "title": "Managing context on the Claude Developer Platform (context editing + memory)",
     "url": "https://www.anthropic.com/news/context-management"},
    {"key": "anthropic-context-engineering", "org": "Anthropic", "tier": "1", "rqs": "RQ2;RQ5",
     "title": "Effective context engineering for AI agents",
     "url": "https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents"},
    {"key": "anthropic-claude-code-memory", "org": "Anthropic", "tier": "1", "rqs": "RQ1;RQ2;RQ4",
     "title": "Claude Code memory (CLAUDE.md as versioned project memory)",
     "url": "https://code.claude.com/docs/en/memory"},
    {"key": "anthropic-long-running-harnesses", "org": "Anthropic", "tier": "1", "rqs": "RQ2;RQ4",
     "title": "Effective harnesses for long-running agents",
     "url": "https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents"},
    {"key": "anthropic-context-editing", "org": "Anthropic", "tier": "1", "rqs": "RQ2;RQ5",
     "title": "Context editing (platform docs)",
     "url": "https://platform.claude.com/docs/en/build-with-claude/context-editing"},
    {"key": "anthropic-compaction", "org": "Anthropic", "tier": "1", "rqs": "RQ2;RQ5",
     "title": "Compaction (platform docs)",
     "url": "https://platform.claude.com/docs/en/build-with-claude/compaction"},
    {"key": "openai-context-personalization", "org": "OpenAI", "tier": "1", "rqs": "RQ2;RQ4",
     "title": "Cookbook: context engineering for personalization — long-term memory notes",
     "url": "https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization"},
    {"key": "openai-session-memory", "org": "OpenAI", "tier": "1", "rqs": "RQ2;RQ5",
     "title": "Cookbook: short-term memory management with sessions",
     "url": "https://developers.openai.com/cookbook/examples/agents_sdk/session_memory"},
    {"key": "openai-agents-sdk-sessions", "org": "OpenAI", "tier": "1", "rqs": "RQ1;RQ4",
     "title": "Agents SDK — Sessions",
     "url": "https://openai.github.io/openai-agents-python/sessions/"},
    {"key": "google-gemini-long-context", "org": "Google DeepMind", "tier": "1", "rqs": "RQ5",
     "title": "Gemini API — long context (and context caching)",
     "url": "https://ai.google.dev/gemini-api/docs/long-context"},
)
GREY_FIELDS = ["key", "org", "tier", "title", "url", "doc_type", "retrieved_at", "sha256", "bytes",
               "chars", "rqs", "path"]
GREY_DOC_TYPES = {"platform-docs", "engineering-blog", "cookbook", "product-docs", "technical-report",
                  "model-card", "framework-docs"}
GREY_MIN_CHARS = 1500  # below this it is a nav shell or a paywall, not a technical document


# --------------------------------------------------------------------------- queue derivation (§9.1)
def sample10_full(key: str) -> bool:
    """The ~10% sample screening_pass designated for the MAIN sheet (sha1 % 10)."""
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % 10 == 0


def sample10_snowball(key: str) -> bool:
    """The ~10% sample snowball_screen designated for the SNOWBALL sheet (sha256 % 10).

    Two different hashes is not an inconsistency to be tidied away: each pass COMMITTED its sample
    before any verdict existed, and re-designating it now — with the decisions already visible — would
    turn a pre-registered sample into a post-hoc one. The sample is evidence; it is honored as found.
    """
    return int(hashlib.sha256(key.encode()).hexdigest(), 16) % 10 == 0


def _model_decided(row: dict) -> bool:
    """True only for rows a MODEL decided. Deterministic pre-decisions (FUERA-ALCANCE, DUPLICADO-INTRA,
    SIN-METADATOS) are rules, not judgements: re-deciding them would measure agreement with an if."""
    return (row.get("decision") or "").strip() in DECISIONS


@dataclass(frozen=True)
class Queue:
    name: str
    kind: str
    source: str                      # full | snowball | extraction | digest | duplicados
    predicate: Callable[[dict], bool]
    rationale: str


QUEUES: dict[str, Queue] = {
    q.name: q for q in (
        Queue("MUESTRA-10PCT", KIND_VERIFICACION, "full",
              lambda r: _model_decided(r) and sample10_full(r["key"]),
              "random 10% of the main pass — the reliability sample"),
        Queue("SNOWBALL-SAMPLE10", KIND_VERIFICACION, "snowball",
              lambda r: _model_decided(r) and r.get("origin") != "v1" and sample10_snowball(r["key"]),
              "random 10% of the snowball pass"),
        Queue("PREOUT-RESCATADOS", KIND_CONFIRMACION, "full",
              lambda r: r.get("triage") == "PRE-OUT" and (r.get("decision") or "") == "INCLUIR",
              "rows the deterministic triage sent OUT that the model pulled IN — targeted, high risk"),
        Queue("GRIS", KIND_ADJUDICACION, "full",
              lambda r: (r.get("decision") or "") in ("GRIS", "CE-4p"),
              "pass 1 abstained; the SPI decides with the PDF in hand"),
        Queue("SNOWBALL-GRIS", KIND_ADJUDICACION, "snowball",
              lambda r: (r.get("decision") or "") in ("GRIS", "CE-4p"),
              "same, snowball sheet"),
        Queue("RECONSIDERAR-EXT", KIND_CALIDAD, "extraction",
              lambda r: "RECONSIDERAR" in (r.get("notes") or ""),
              "extraction flagged the record's own quality"),
        Queue("RECONSIDERAR-DIG", KIND_CALIDAD, "digest",
              lambda r: "RECONSIDERAR" in (r.get("notes") or ""),
              "digestion flagged it after reading the full text"),
        Queue("DUPLICADOS", KIND_IDENTIDAD, "duplicados",
              lambda r: True,
              "near-duplicate pairs found by dup_scan (observer)"),
    )
}


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def source_rows(source: str) -> list[dict]:
    if source == "full":
        return _read_csv(SHEET_FULL)
    if source == "snowball":
        return _read_csv(SHEET_SNOWBALL)
    if source == "extraction":
        return _read_csv(SHEET_EXTRACTION)
    if source == "duplicados":
        return _read_csv(DUPLICADOS)
    if source == "digest":
        return [json.loads(line) for line in DIGEST.read_text(encoding="utf-8").splitlines() if line.strip()]
    raise ValueError(f"unknown source: {source}")


def queue_members(name: str) -> list[dict]:
    """Re-DERIVE a queue from the committed sheets. Never parse the rendered .md views: those are a
    projection, and a projection that drifts from its source is exactly the failure this study studies."""
    q = QUEUES[name]
    rows = [r for r in source_rows(q.source) if q.predicate(r)]
    if q.source == "duplicados":
        return rows
    return sorted(rows, key=lambda r: r["key"])


def queue_chunks(name: str) -> list[list[dict]]:
    members = queue_members(name)
    return [members[i:i + CHUNK_SIZE] for i in range(0, len(members), CHUNK_SIZE)]


# --------------------------------------------------------------------------- validation (§9.2)
def _evidence_problem(veredicto: str, evidencia: str) -> str | None:
    if veredicto in NO_EVIDENCE_NEEDED:
        return None
    ev = (evidencia or "").strip()
    if len(ev) < EVIDENCE_MIN_CHARS:
        return f"evidencia too short ({len(ev)} < {EVIDENCE_MIN_CHARS} chars)"
    low = ev.lower()
    if not any(a in low for a in EVIDENCE_ANCHORS):
        return "evidencia has no verifiable anchor (section/table/figure/page/line/abstract)"
    return None


def validate_verdict(row: dict, kind: str, errors: list[str]) -> bool:
    """Return True iff the row is a legal SPI verdict of this kind. Appends every reason to errors."""
    key = row.get("key", "?")
    missing = [f for f in VERDICT_FIELDS[kind] if f not in row]
    if missing:
        errors.append(f"{key}: missing field(s) {missing} for kind {kind}")
        return False

    if kind in KINDS_MEMBERSHIP:
        dec = (row.get("decision") or "").strip()
        if kind != KIND_ADJUDICACION and dec == "GRIS":
            errors.append(f"{key}: GRIS is only emittable in ADJUDICACION (elsewhere it dodges the call)")
            return False
        if not validate_membership_row(row, errors):
            return False
        problem = _evidence_problem(dec, row.get("evidencia", ""))
        if problem:
            errors.append(f"{key}: {problem}")
            return False
        return True

    if kind == KIND_CALIDAD:
        ver = (row.get("veredicto") or "").strip()
        if ver not in CALIDAD_VERDICTS:
            errors.append(f"{key}: veredicto '{ver}' not in {sorted(CALIDAD_VERDICTS)}")
            return False
    elif kind == KIND_IDENTIDAD:
        ver = (row.get("veredicto") or "").strip()
        if ver not in IDENTIDAD_VERDICTS:
            errors.append(f"{key}: veredicto '{ver}' not in {sorted(IDENTIDAD_VERDICTS)}")
            return False
        if not (row.get("pareja") or "").strip():
            errors.append(f"{key}: pareja (the other key of the pair) is mandatory")
            return False
        if ver == "FUSIONAR":
            canon = (row.get("canonica") or "").strip()
            if canon not in {key, (row.get("pareja") or "").strip()}:
                errors.append(f"{key}: FUSIONAR requires canonica to be one of the two keys (got '{canon}')")
                return False
    else:
        errors.append(f"{key}: unknown kind {kind}")
        return False

    if not (row.get("notes") or "").strip():
        errors.append(f"{key}: empty notes (1-line reason is mandatory)")
        return False
    problem = _evidence_problem(row.get("veredicto", ""), row.get("evidencia", ""))
    if problem:
        errors.append(f"{key}: {problem}")
        return False
    return True


# --------------------------------------------------------------------------- agreement (§9.1)
IN_LABELS = {"INCLUIR"}
HUMAN_LABELS = {"GRIS", "CE-4p"}


def collapse(decision: str) -> str:
    """IN / OUT / HUMANO — the SAME collapse the 2026-07-16 pre-flight used, so the numbers compare.
    The collapsed view is the one that matters for the corpus: which subtype of exclusion was written
    is bookkeeping, whether the paper is in the study is not."""
    dec = (decision or "").strip()
    if dec in IN_LABELS:
        return "IN"
    if dec in HUMAN_LABELS:
        return "HUMANO"
    return "OUT"


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    """Cohen's κ for two raters over a closed label set. Returns 0.0 for a degenerate (single-label) set,
    where κ is undefined — reporting a NaN as 1.0 would be the flattering lie."""
    n = len(pairs)
    if n == 0:
        return 0.0
    labels = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    if len(labels) < 2:
        return 0.0
    po = sum(1 for a, b in pairs if a == b) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum((ca[l] / n) * (cb[l] / n) for l in labels)
    if pe >= 1.0:
        return 0.0
    return (po - pe) / (1 - pe)


def interpret_kappa(k: float) -> str:
    """Landis & Koch (1977) bands — cited, not invented."""
    if k < 0.0:
        return "peor que el azar"
    if k < 0.20:
        return "leve"
    if k < 0.40:
        return "aceptable"
    if k < 0.60:
        return "moderado"
    if k < 0.80:
        return "sustancial"
    return "casi perfecto"


__all__ = [
    "QUEUES", "Queue", "queue_members", "queue_chunks", "source_rows", "sample10_full", "sample10_snowball",
    "KIND_VERIFICACION", "KIND_CONFIRMACION", "KIND_ADJUDICACION", "KIND_CALIDAD", "KIND_IDENTIDAD",
    "KINDS_MEMBERSHIP", "KINDS_KAPPA", "BLIND_FORBIDDEN", "VERDICT_FIELDS", "CHUNK_SIZE",
    "CALIDAD_VERDICTS", "IDENTIDAD_VERDICTS", "validate_verdict", "collapse", "cohen_kappa",
    "interpret_kappa", "DECISIONS", "DECISIONS_CATEGORICAL", "FACETS", "SPI_DIR",
]

if __name__ == "__main__":  # tiny self-report: the queue map, re-derived
    total = 0
    for name, q in QUEUES.items():
        n = len(queue_members(name))
        total += n
        print(f"{name:22s} {q.kind:13s} n={n:4d}  ({q.rationale})")
    print(f"{'TOTAL':22s} {'':13s} n={total:4d}")
