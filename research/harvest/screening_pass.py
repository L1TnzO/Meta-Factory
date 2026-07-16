#!/usr/bin/env python3
"""screening_pass.py — harness for the SMS-v2 full screening pass (2026-07-16).

Verify-not-review delegation (ADR-017/027, protocol §7.5.3): a cheap model scores
batches with the FROZEN rubric as data; THIS script is the deterministic gate that
accepts/rejects each verdict row by re-computing the decision arithmetic. The
orchestrator never reads abstracts; the engineer gets ready-made human queues.

Subcommands
  prompt              build corpus/screening/batches/PROMPT.md (rubric §7.5 verbatim + few-shot)
  slice STRATUM       emit chunk input files (PRE-OUT | PRE-IN | GRIS | PREFLIGHT)
  merge FILES...      validate verdict CSVs and apply to screening_full.csv (idempotent)
  compare FILES...    preflight: agreement vs the 50 frozen calibration decisions (no write)
  queues              regenerate human-verification queues from the sheet
  status              cursor: pending by stratum, chunk/verdict/merge state

State model: the committed sheet IS the state. Chunk partition is a pure function of
(triage column, key sort) → stable across sessions. merge skips already-decided rows
(idempotent) and rejects any row that violates the frozen rubric arithmetic.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # research/
SHEET = ROOT / "corpus/screening/screening_full.csv"
JSONL = ROOT / "corpus/merged/corpus.jsonl"
PROTOCOL = ROOT / "SMS-V2-PROTOCOL.md"
BATCHES = ROOT / "corpus/screening/batches"
QUEUES = ROOT / "corpus/screening/queues"

CHUNK_SIZE = 25
STRATA = ("PRE-OUT", "PRE-IN", "GRIS")

# Closed vocabularies (frozen rubric v2.3 — protocol §7.5).
DECISIONS_SCORED = {"INCLUIR", "EXCLUIR-CE1", "EXCLUIR-CE2", "EXCLUIR-RUBRICA", "GRIS"}
DECISIONS_CATEGORICAL = {"EXCLUIR-CE5", "CE3-SECUNDARIO", "EXCLUIR-CE4", "CE-4p"}
DECISIONS = DECISIONS_SCORED | DECISIONS_CATEGORICAL
FACETS = {
    "WRITE", "RETRIEVAL-MEDIDO", "DOCS-VERSIONADO", "FIDELIDAD", "CONSOLIDACION",
    "COSTO", "MULTIAGENTE", "SEGURIDAD", "NEGATIVO", "PROCEDIMENTAL",
}
VERDICT_FIELDS = ["key", "M", "T", "E", "F", "se", "selfpub", "artefacto", "decision", "notes"]
FEWSHOT_KEYS = [  # handoff §2 suggestions + the measured preflight miss (M=1 trap, 2026-07-16)
    "W4416611586", "W7129523991", "W7156942111", "W7117411283", "W4415524435",
    "2606.26721v1",
]


def read_sheet() -> tuple[list[dict], list[str]]:
    with SHEET.open() as fh:
        reader = csv.DictReader(fh)
        return list(reader), list(reader.fieldnames)


def write_sheet(rows: list[dict], fieldnames: list[str]) -> None:
    tmp = SHEET.with_suffix(".csv.tmp")
    with tmp.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(SHEET)


def read_corpus() -> dict[str, dict]:
    import re

    def record_key(rec: dict) -> str:  # mirrors harvest/download_pdfs.py
        for candidate in (rec.get("id"), rec.get("doi"), rec.get("arxiv_id"), rec.get("title")):
            if candidate:
                return re.sub(r"[^A-Za-z0-9._-]+", "_", str(candidate).split("/")[-1])[:120]
        return "unknown"

    out = {}
    with JSONL.open() as fh:
        for line in fh:
            rec = json.loads(line)
            out[record_key(rec)] = rec
    return out


# ---------------------------------------------------------------- rubric gate
def validate_row(row: dict, errors: list[str]) -> bool:
    """Re-compute the frozen decision arithmetic. Append reasons to errors; return ok."""
    key = row.get("key", "?")
    dec = (row.get("decision") or "").strip()
    if dec not in DECISIONS:
        errors.append(f"{key}: decision '{dec}' not in closed vocab")
        return False
    if not (row.get("notes") or "").strip():
        errors.append(f"{key}: empty notes (1-line reason is mandatory)")
        return False
    facets = [f for f in (row.get("F") or "").split(";") if f]
    bad = [f for f in facets if f not in FACETS]
    if bad:
        errors.append(f"{key}: unknown facet(s) {bad}")
        return False
    for flag in ("se", "selfpub", "artefacto"):
        if (row.get(flag) or "0") not in {"0", "1"}:
            errors.append(f"{key}: {flag} must be 0/1")
            return False
    if dec in DECISIONS_CATEGORICAL:
        return True  # no arithmetic for non-study / no-text / secondary records
    try:
        m, t, e = int(row["M"]), int(row["T"]), int(row["E"])
    except (KeyError, ValueError):
        errors.append(f"{key}: {dec} requires integer M/T/E")
        return False
    if m not in (0, 1, 3) or t not in (0, 1, 2) or e not in (0, 1):
        errors.append(f"{key}: M/T/E out of domain (M∈{{0,1,3}} T∈{{0,1,2}} E∈{{0,1}})")
        return False
    score, se, selfpub = m + t + e, row.get("se") == "1", row.get("selfpub") == "1"
    passes = score >= 4 and m >= 1 and (se or m == 3)
    gris_auto = e == 0 and selfpub and passes  # P3
    if dec == "INCLUIR":
        if not passes:
            errors.append(f"{key}: INCLUIR but threshold fails (s={score} M={m} se={int(se)})")
            return False
        if gris_auto:
            errors.append(f"{key}: INCLUIR violates P3 (E=0 ∧ selfpub → GRIS automático)")
            return False
    elif dec == "EXCLUIR-CE1" and m != 0:
        errors.append(f"{key}: EXCLUIR-CE1 requires M=0 (got M={m})")
        return False
    elif dec == "EXCLUIR-CE2" and t != 0:
        errors.append(f"{key}: EXCLUIR-CE2 requires T=0 (got T={t})")
        return False
    elif dec == "EXCLUIR-RUBRICA" and passes:
        errors.append(f"{key}: EXCLUIR-RUBRICA but threshold PASSES (s={score}) — INCLUIR/GRIS?")
        return False
    return True


# ---------------------------------------------------------------- subcommands
def stratum_chunks(rows: list[dict], stratum: str) -> list[list[dict]]:
    """Stable partition: ALL rows of the stratum (decided or not), sorted by key."""
    if stratum == "PREFLIGHT":
        members = sorted((r for r in rows if r["decision"]), key=lambda r: r["key"])
    else:
        members = sorted((r for r in rows if r["triage"] == stratum), key=lambda r: r["key"])
    return [members[i:i + CHUNK_SIZE] for i in range(0, len(members), CHUNK_SIZE)]


def cmd_slice(stratum: str) -> None:
    rows, _ = read_sheet()
    corpus = read_corpus()
    outdir = BATCHES / stratum
    outdir.mkdir(parents=True, exist_ok=True)
    for i, chunk in enumerate(stratum_chunks(rows, stratum)):
        pending = [r for r in chunk if stratum == "PREFLIGHT" or not r["decision"]]
        path = outdir / f"c{i:02d}.input.jsonl"
        if not pending:
            if path.exists():
                path.unlink()  # fully merged → no input needed
            continue
        with path.open("w") as fh:
            for r in pending:
                rec = corpus.get(r["key"], {})
                fh.write(json.dumps({
                    "key": r["key"],
                    "title": r["title"],
                    "abstract": rec.get("abstract") or "",
                    "year": r["year"],
                    "venue": r["venue"],
                    "sources": r["sources"],
                    "has_pdf": r["has_pdf"],
                    "pdf": f"corpus/pdf/{r['key']}.pdf" if r["has_pdf"] == "1" else "",
                }, ensure_ascii=False) + "\n")
        print(f"{path.relative_to(ROOT)}: {len(pending)} records")


def cmd_rescue(stratum: str) -> None:
    """Slice EXCLUIR-CE1 rows of a stratum for the adversarial second pass (M=1 trap).

    Rationale (preflight 2026-07-16): the one dangerous miss was a frozen-INCLUIR scored
    M=0 because the mechanism never calls itself 'memory'. A silent false-exclude is the
    only failure the human lanes cannot see; this lane makes it require TWO independent
    same-direction errors. Only CE1 rows outside PRE-OUT (triage-vs-model disagreement).
    """
    rows, _ = read_sheet()
    corpus = read_corpus()
    members = sorted(
        (r for r in rows if r["decision"] == "EXCLUIR-CE1" and r["triage"] == stratum),
        key=lambda r: r["key"],
    )
    outdir = BATCHES / f"RESCUE-{stratum}"
    outdir.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(members), CHUNK_SIZE):
        chunk = members[i:i + CHUNK_SIZE]
        path = outdir / f"c{i // CHUNK_SIZE:02d}.input.jsonl"
        with path.open("w") as fh:
            for r in chunk:
                rec = corpus.get(r["key"], {})
                fh.write(json.dumps({
                    "key": r["key"], "title": r["title"],
                    "abstract": rec.get("abstract") or "",
                    "year": r["year"], "venue": r["venue"], "sources": r["sources"],
                    "has_pdf": r["has_pdf"],
                    "pdf": f"corpus/pdf/{r['key']}.pdf" if r["has_pdf"] == "1" else "",
                    "first_pass_note": r["notes"],
                }, ensure_ascii=False) + "\n")
        print(f"{path.relative_to(ROOT)}: {len(chunk)} records")
    if not members:
        print(f"RESCUE-{stratum}: no EXCLUIR-CE1 rows — lane empty")


def load_verdicts(paths: list[str]) -> list[dict]:
    out = []
    for p in paths:
        with open(p, newline="") as fh:
            for row in csv.DictReader(fh):
                row["_src"] = p
                out.append(row)
    return out


def cmd_merge(paths: list[str], rescue: bool = False) -> int:
    rows, fieldnames = read_sheet()
    by_key = {r["key"]: r for r in rows}
    verdicts = load_verdicts(paths)
    errors: list[str] = []
    applied, skipped, rejected = 0, 0, 0
    dist: Counter = Counter()
    for v in verdicts:
        key = v.get("key", "?")
        target = by_key.get(key)
        if target is None:
            errors.append(f"{key}: unknown key (not in sheet)")
            rejected += 1
            continue
        if rescue:
            # Sole allowed transition: EXCLUIR-CE1 → GRIS (the border is ALWAYS human).
            if target["decision"] != "EXCLUIR-CE1":
                skipped += 1
                continue
            if v.get("decision") == "EXCLUIR-CE1":
                skipped += 1  # confirmed exclude — first pass stands untouched
                continue
            if v.get("decision") != "GRIS":
                errors.append(f"{key}: rescue may only flip CE1→GRIS (got {v.get('decision')})")
                rejected += 1
                continue
            if not validate_row(v, errors):
                rejected += 1
                continue
            for col in ("M", "T", "E", "F"):
                target[col] = (v.get(col) or "").strip()
            target["decision"] = "GRIS"
            target["notes"] = f"[rescate-CE1] {v.get('notes', '').strip()} | 1ª pasada: {target['notes']}"
            dist["CE1→GRIS"] += 1
            applied += 1
            continue
        if target["decision"]:
            skipped += 1  # idempotent re-merge
            continue
        if not validate_row(v, errors):
            rejected += 1
            continue
        for col in ("M", "T", "E", "F", "decision", "notes"):
            target[col] = (v.get(col) or "").strip()
        dist[v["decision"]] += 1
        applied += 1
    if applied:
        write_sheet(rows, fieldnames)
    empty = sum(1 for r in rows if not r["decision"])
    print(f"MERGE: applied={applied} skipped(already-decided)={skipped} rejected={rejected}")
    print(f"  distribution: {dict(dist)}")
    print(f"  sheet pending: {empty}/1069")
    if errors:
        print("  REJECTS (structured retry list for the generator):")
        for e in errors:
            print(f"   - {e}")
    cmd_queues(quiet=True)
    return 1 if errors else 0


def cmd_compare(paths: list[str]) -> int:
    rows, _ = read_sheet()
    frozen = {r["key"]: r for r in rows if r["decision"]}
    verdicts = load_verdicts(paths)
    errors: list[str] = []
    exact = collapsed = total = invalid = 0
    disagreements = []

    def bucket(d: str) -> str:
        if d == "INCLUIR":
            return "IN"
        if d in ("GRIS", "CE-4p"):
            return "HUMANO"
        return "OUT"

    for v in verdicts:
        f = frozen.get(v.get("key", "?"))
        if f is None:
            continue
        total += 1
        if not validate_row(v, errors):
            invalid += 1
            continue
        if v["decision"] == f["decision"]:
            exact += 1
        if bucket(v["decision"]) == bucket(f["decision"]):
            collapsed += 1
        else:
            disagreements.append(
                f"   - {v['key']}: frozen={f['decision']} model={v['decision']} "
                f"(model M/T/E {v['M']}/{v['T']}/{v['E']}) nota: {v['notes'][:110]}"
            )
    print(f"PREFLIGHT: n={total} exact={exact} ({100*exact/max(total,1):.0f}%) "
          f"IN/OUT/HUMANO-collapsed={collapsed} ({100*collapsed/max(total,1):.0f}%) "
          f"invalid-rows={invalid}")
    if disagreements:
        print("  collapsed disagreements (the residue to eyeball):")
        print("\n".join(disagreements))
    if errors:
        print("  invalid rows:")
        for e in errors:
            print(f"   - {e}")
    return 0


def cmd_queues(quiet: bool = False) -> None:
    rows, _ = read_sheet()
    QUEUES.mkdir(parents=True, exist_ok=True)
    frozen_50_cutoff = None  # calibration rows carry their own provenance (commit 4618c1c)
    decided = [r for r in rows if r["decision"]]

    def sample10(r: dict) -> bool:  # deterministic seeded ~10% sample
        return int(hashlib.sha1(r["key"].encode()).hexdigest(), 16) % 10 == 0

    queues = {
        "QUEUE-GRIS.md": [r for r in decided if r["decision"] in ("GRIS", "CE-4p")],
        "QUEUE-PREOUT-RESCATADOS.md": [
            r for r in decided if r["triage"] == "PRE-OUT" and r["decision"] == "INCLUIR"
        ],
        "QUEUE-MUESTRA-10PCT.md": [r for r in decided if sample10(r)],
        "QUEUE-ARTIFACTS-CE5.md": [
            r for r in decided if r["decision"] == "EXCLUIR-CE5" and "artefacto" in r["notes"].lower()
        ],
        "QUEUE-P12-PLAN-ESTADO.md": [r for r in decided if "P12" in r["notes"]],
    }
    for name, members in queues.items():
        path = QUEUES / name
        with path.open("w") as fh:
            fh.write(f"# {name[:-3]} — regenerated by screening_pass.py queues ({len(members)})\n\n")
            fh.write("Verificación humana (contrato §7.5 congelado). Marcar en la HOJA, no aquí.\n\n")
            for r in members:
                fh.write(f"- `{r['key']}` [{r['triage']}] {r['decision']} "
                         f"(M/T/E {r['M']}/{r['T']}/{r['E']}) — {r['title'][:90]}\n"
                         f"  nota: {r['notes'][:160]}\n")
    if not quiet:
        for name, members in queues.items():
            print(f"{name}: {len(members)}")


def cmd_status() -> None:
    rows, _ = read_sheet()
    pending = Counter(r["triage"] for r in rows if not r["decision"])
    print(f"pending: {sum(pending.values())}/1069  by stratum: {dict(pending)}")
    print(f"decided distribution: {dict(Counter(r['decision'] for r in rows if r['decision']))}")
    for d in sorted(p for p in BATCHES.iterdir() if p.is_dir()):
        stratum = d.name
        inputs = sorted(d.glob("c*.input.jsonl"))
        verdicts = sorted(d.glob("c*.verdict.csv"))
        print(f"{stratum}: {len(inputs)} input chunk(s) pending, {len(verdicts)} verdict file(s) on disk")


def cmd_prompt() -> None:
    # Extract the FROZEN rubric §7.5 verbatim (criteria + anchored rubric + facets),
    # stopping before **Proceso:** (process is orchestrator business, not the scorer's).
    lines = PROTOCOL.read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("### 7.5 "))
    end = next(i for i, l in enumerate(lines) if l.startswith("**Proceso:**"))
    rubric = "\n".join(lines[start:end]).strip()

    rows, _ = read_sheet()
    by_key = {r["key"]: r for r in rows}
    corpus = read_corpus()
    fewshot = []
    for k in FEWSHOT_KEYS:
        r, rec = by_key[k], corpus[k]
        abstract = (rec.get("abstract") or "")[:1600]
        fewshot.append(
            f"### Ejemplo resuelto: {k}\n"
            f"- title: {r['title']}\n- venue: {r['venue']} · sources: {r['sources']} · year: {r['year']}\n"
            f"- abstract: {abstract}\n"
            f"- **VEREDICTO CONGELADO** → M={r['M']} T={r['T']} E={r['E']} F={r['F'] or '—'} "
            f"decision={r['decision']}\n- nota: {r['notes']}\n"
        )

    prompt = f"""# PROMPT — cribado por lotes SMS v2 (contrato de delegación, CONGELADO 2026-07-16)

Eres un cribador de títulos/abstracts para un Systematic Mapping Study. Tu ÚNICA autoridad de
criterio es la rúbrica congelada de abajo (protocolo §7.5 v2.3). No inventes criterios; ante DUDA
real la decisión es GRIS (un humano la resuelve — nunca fuerces un borde).

## Entrada
Archivos `c*.input.jsonl` (uno por chunk): un registro JSON por línea con
`key,title,abstract,year,venue,sources,has_pdf,pdf`. El abstract es el COMPLETO del corpus;
si viene vacío y `has_pdf=1`, extrae ≤3 páginas con `pdftotext corpus/pdf/<key>.pdf - | head -c 6000`
(ejecutar desde `research/`); si no hay texto suficiente y el título ES pertinente → `CE-4p`
(rescate manual); si el título es claramente no pertinente → `EXCLUIR-CE4`.

## Salida (por chunk, OBLIGATORIA antes de pasar al siguiente)
Escribe `c<NN>.verdict.csv` JUNTO al input (mismo directorio), con el módulo csv de Python
(nunca a mano — las notas llevan comas). Columnas EXACTAS:
`key,M,T,E,F,se,selfpub,artefacto,decision,notes`
- `M,T,E`: enteros de la rúbrica (M∈{{0,1,3}}, T∈{{0,1,2}}, E∈{{0,1}}). Vacíos SOLO en
  decisiones categóricas (CE-3/CE-4/CE-4p/CE-5).
- `F`: facetas separadas por `;` del vocabulario CERRADO de 10 (solo INCLUIR/GRIS; puede ir vacío).
- `se`: 1 si hay señal SE juzgada por CONTENIDO (no por hints — `sig_se` trae ~1/3 espurios).
- `selfpub`: 1 SOLO para depósitos autopublicados sin revisión (Zenodo/SSRN/similar).
  **arXiv NO cuenta** (práctica congelada de la calibración: W4385970259 y W7161204348 son
  INCLUIR con E=0 desde arXiv; el GRIS-P3 fue Zenodo).
- `artefacto`: 1 si es CE-5 subtipo HERRAMIENTA (depósito de software útil) — incluye la palabra
  «artefacto» en notes (alimenta artifacts.csv).
- `decision` (vocabulario CERRADO): INCLUIR · EXCLUIR-CE1 · EXCLUIR-CE2 · EXCLUIR-RUBRICA ·
  EXCLUIR-CE4 · CE-4p · EXCLUIR-CE5 · CE3-SECUNDARIO · GRIS.
- `notes`: 1 línea con la RAZÓN (en español). Si el paper toca estado-de-plan/progreso o traspaso
  entre sesiones/agentes, añade el token `P12` (regla activa del protocolo).

## Reglas duras (el validador determinista rechaza la fila si las violas)
1. INCLUIR ⇔ M+T+E ≥ 4 ∧ M ≥ 1 ∧ (se=1 ∨ M=3). Sin señal SE se exige M=3 (rama Q2).
2. E=0 ∧ selfpub=1 (y el corte pasa) → GRIS automático (P3). NUNCA INCLUIR.
3. EXCLUIR-CE1 exige M=0 · EXCLUIR-CE2 exige T=0 · EXCLUIR-RUBRICA exige que el corte NO pase.
4. Surveys/mapeos/reviews → CE3-SECUNDARIO (no se puntúan; vocabulario+snowball).
5. Registros no-estudio (depósitos, fichas de versión, front-matter, demos, manifiestos sin
   sistema) → EXCLUIR-CE5 aunque «la letra» del corte los incluya.
6. M exige mecanismo PERSISTENTE (cross-tarea/sesión) o COMPARTIDO (cross-agente): scratchpad /
   compresión de ventana intra-tarea de un solo agente → M=0 (P1).
7. Demos, tests de humo o «validación» por ejemplos NO puntúan E.
8. DUDA que el abstract (y ≤3 págs de PDF si existe) no resuelve → GRIS con la duda en notes.
9. **Trampa MEDIDA en el pre-flight (no la repitas)**: M=1 SÍ aplica cuando el sistema
   admite/gobierna/destila conocimiento PERSISTENTE del proyecto (admisión con gate, PRs de
   conocimiento, destilación a artefactos del repo) aunque el paper jamás use la palabra
   «memoria» (ancla 2606.26721v1). Antes de puntuar M=0 pregúntate: ¿algo persiste
   cross-tarea/sesión o cross-agente en artefactos del proyecto?

## Rúbrica congelada (§7.5 — autoridad única)

{rubric}

## Few-shot (5 de la calibración de 50 — anclas de cada tipo de decisión)

{chr(10).join(fewshot)}
## Disciplina de proceso
- Procesa los chunks EN ORDEN; escribe cada verdict ANTES de abrir el siguiente input
  (checkpoint: si la sesión muere, lo escrito sobrevive).
- No leas el protocolo entero ni otros archivos del repo: este prompt es autosuficiente.
- Al terminar, reporta SOLO: chunks completados, nº por decisión, nº de GRIS, nº de dudas-PDF
  consultadas. NUNCA pegues abstracts ni el contenido de los CSV en tu reporte.
"""
    BATCHES.mkdir(parents=True, exist_ok=True)
    out = BATCHES / "PROMPT.md"
    out.write_text(prompt)
    print(f"{out.relative_to(ROOT)}: {len(prompt)} chars, rubric lines {start+1}-{end} verbatim")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "prompt":
        cmd_prompt()
    elif cmd == "slice":
        cmd_slice(args[0])
    elif cmd == "rescue":
        cmd_rescue(args[0])
    elif cmd == "merge":
        if args and args[0] == "--rescue":
            return cmd_merge(args[1:], rescue=True)
        return cmd_merge(args)
    elif cmd == "compare":
        return cmd_compare(args)
    elif cmd == "queues":
        cmd_queues()
    elif cmd == "status":
        cmd_status()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
