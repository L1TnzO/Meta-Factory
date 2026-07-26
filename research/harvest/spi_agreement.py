#!/usr/bin/env python3
"""Agreement between pass 1 and the second independent pass — the reliability number of the SMS (§9.1).

Trust-chain: this is the measurement instrument, so it is written by hand and it is deliberately dumb.
It joins verdicts to the committed sheets, counts, and writes two artifacts:

  * `corpus/spi/AGREEMENT.md`  — the reportable numbers (raw agreement, Cohen's κ, confusion matrix).
  * `corpus/spi/CONFLICTOS.csv` — every row where the two readers disagree. THIS is the human queue:
    the point of the SPI is not to replace the engineer's judgement but to aim it.

Honesty rules baked in (they are not options):
  * κ is computed ONLY over kind VERIFICACION — a random, pre-registered sample where pass 1 had already
    committed a firm decision. Targeted sets (CONFIRMACION) and abstentions (ADJUDICACION) are reported
    as counts, never folded into κ.
  * Both an EXACT-label and a COLLAPSED (IN/OUT/HUMANO) figure are reported. Reporting only the flattering
    one is the standard way this statistic gets abused; the collapsed number answers "is the paper in the
    study?", the exact one answers "did they write the same exclusion subtype?", and they are not the same
    claim.

Usage: python3 harvest/spi_agreement.py [--write]   (without --write it prints and touches nothing)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from closure_law import (  # noqa: E402
    QUEUES, SPI_DIR, KIND_VERIFICACION, KIND_CONFIRMACION, KIND_ADJUDICACION,
    KIND_CALIDAD, KIND_IDENTIDAD, collapse, cohen_kappa, interpret_kappa, queue_members,
    HUMAN_LABELS, SPI_BLINDNESS_BREACHES,
)

BATCHES = SPI_DIR / "batches"


def load_verdicts(queue: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    qdir = BATCHES / queue
    if not qdir.exists():
        return out
    for path in sorted(qdir.glob("*.verdict.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                out[row["key"]] = row
    return out


def pass1_index(queue: str) -> dict[str, dict]:
    return {r["key"]: r for r in queue_members(queue) if "key" in r}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    lines: list[str] = ["# SPI — acuerdo entre la pasada 1 y la segunda pasada independiente", ""]
    lines.append("> Generado por `harvest/spi_agreement.py` desde los veredictos committeados. "
                 "**Dos revisores-MODELO independientes, no dos humanos** (§9.1): la adjudicación humana "
                 "se aplica sólo sobre los conflictos listados en `CONFLICTOS.csv`.")
    lines.append("")

    conflicts: list[dict] = []
    kappa_pairs_exact: list[tuple[str, str]] = []
    kappa_pairs_collapsed: list[tuple[str, str]] = []
    covered = 0

    for name, q in QUEUES.items():
        verdicts = load_verdicts(name)
        if not verdicts:
            continue
        covered += len(verdicts)
        p1 = pass1_index(name)
        lines.append(f"## {name} ({q.kind}) — n={len(verdicts)}/{len(p1) or len(queue_members(name))}")
        lines.append("")

        if q.kind in (KIND_VERIFICACION, KIND_CONFIRMACION):
            exact_hit = coll_hit = 0
            abstained = 0          # pass 1 declined to decide: NOT verifiable, see below
            breached = 0           # second reader self-disclosed seeing pass-1's output: NOT independent
            confusion: dict[tuple[str, str], int] = defaultdict(int)
            for key, v in sorted(verdicts.items()):
                a = (p1.get(key, {}).get("decision") or "").strip()
                b = (v.get("decision") or "").strip()
                # A row where pass 1 ABSTAINED (GRIS/CE-4p) cannot be verified: there is no firm
                # decision to agree or disagree with, and the second reader is forbidden from
                # abstaining in this stratum, so the pair is a guaranteed mismatch BY CONSTRUCTION.
                # Counting it would depress the coefficient with an artefact of the design. It is
                # excluded from the coefficient and reported separately — the second reader did
                # resolve it, which is an adjudication result, just not a reliability one.
                if a in HUMAN_LABELS:
                    abstained += 1
                    continue
                # A row named in SPI_BLINDNESS_BREACHES had its blindness broken IN PRACTICE (the second
                # reader saw pass-1's output, self-disclosed, before writing their own verdict) even
                # though the INPUT file never carried the forbidden column. It is not a disagreement
                # signal either way — reliability was never measured on this pair — so it is excluded
                # from κ the same way an abstention is: visibly, never in silence.
                if (name, key) in SPI_BLINDNESS_BREACHES:
                    breached += 1
                    continue
                confusion[(collapse(a), collapse(b))] += 1
                if a == b:
                    exact_hit += 1
                if collapse(a) == collapse(b):
                    coll_hit += 1
                else:
                    conflicts.append({
                        "queue": name, "kind": q.kind, "key": key,
                        "pasada1": a, "spi": b,
                        "colapsado1": collapse(a), "colapsado2": collapse(b),
                        "evidencia_spi": (v.get("evidencia") or "").replace("\n", " ")[:400],
                    })
                if q.kind == KIND_VERIFICACION:
                    kappa_pairs_exact.append((a, b))
                    kappa_pairs_collapsed.append((collapse(a), collapse(b)))
            n = len(verdicts) - abstained - breached
            if n <= 0:
                lines.append("- sin filas comparables (la pasada 1 se abstuvo en todas, o brecha)")
                lines.append("")
                continue
            lines.append(f"- filas comparables: {n} (se excluyen {abstained} donde la pasada 1 se "
                         f"ABSTUVO: no son verificables y el segundo lector no puede abstenerse aquí, "
                         f"así que contarlas sería penalizar el coeficiente con un artefacto del diseño)"
                         + (f"; se excluyen {breached} por BRECHA DE CEGUERA auto-reportada por el "
                            f"segundo lector (no es desacuerdo ni acuerdo: la medición de fiabilidad "
                            f"nunca ocurrió en ese par)" if breached else ""))
            if breached:
                for (bq, bk), why in sorted(SPI_BLINDNESS_BREACHES.items()):
                    if bq == name:
                        lines.append(f"  - `{bk}`: {why}")
            lines.append(f"- acuerdo EXACTO: {exact_hit}/{n} = {100 * exact_hit / n:.1f}%")
            lines.append(f"- acuerdo COLAPSADO (IN/OUT/HUMANO): {coll_hit}/{n} = {100 * coll_hit / n:.1f}%")
            if q.kind == KIND_CONFIRMACION:
                lines.append("- (muestra DIRIGIDA, no aleatoria → no entra en κ)")
            lines.append("")
            lines.append("| pasada 1 \\ SPI | IN | OUT | HUMANO |")
            lines.append("| --- | ---: | ---: | ---: |")
            for a in ("IN", "OUT", "HUMANO"):
                cells = " | ".join(str(confusion.get((a, b), 0)) for b in ("IN", "OUT", "HUMANO"))
                lines.append(f"| **{a}** | {cells} |")
            lines.append("")

        elif q.kind == KIND_ADJUDICACION:
            dist = Counter((v.get("decision") or "").strip() for v in verdicts.values())
            lines.append("La pasada 1 se abstuvo en estas filas; la SPI decide con el PDF a la vista. "
                         "No hay κ: no hay dos decisiones que comparar.")
            lines.append("")
            for dec, cnt in dist.most_common():
                lines.append(f"- `{dec}`: {cnt}")
            persist = dist.get("GRIS", 0)
            if persist:
                lines.append(f"- **{persist} siguen GRIS con el texto completo a la vista → cola humana real.**")
                for key, v in sorted(verdicts.items()):
                    if (v.get("decision") or "").strip() == "GRIS":
                        conflicts.append({
                            "queue": name, "kind": q.kind, "key": key,
                            "pasada1": (p1.get(key, {}).get("decision") or ""), "spi": "GRIS",
                            "colapsado1": "HUMANO", "colapsado2": "HUMANO",
                            "evidencia_spi": (v.get("evidencia") or "").replace("\n", " ")[:400],
                        })
            lines.append("")

        elif q.kind == KIND_CALIDAD:
            dist = Counter((v.get("veredicto") or "").strip() for v in verdicts.values())
            for ver, cnt in dist.most_common():
                lines.append(f"- `{ver}`: {cnt}")
            for key, v in sorted(verdicts.items()):
                if (v.get("veredicto") or "").strip() == "DEGRADAR":
                    conflicts.append({
                        "queue": name, "kind": q.kind, "key": key,
                        "pasada1": "INCLUIR", "spi": "DEGRADAR",
                        "colapsado1": "IN", "colapsado2": "OUT",
                        "evidencia_spi": (v.get("evidencia") or "").replace("\n", " ")[:400],
                    })
            lines.append("")

        elif q.kind == KIND_IDENTIDAD:
            dist = Counter((v.get("veredicto") or "").strip() for v in verdicts.values())
            for ver, cnt in dist.most_common():
                lines.append(f"- `{ver}`: {cnt}")
            for key, v in sorted(verdicts.items()):
                if (v.get("veredicto") or "").strip() == "FUSIONAR":
                    conflicts.append({
                        "queue": name, "kind": q.kind, "key": key,
                        "pasada1": "dos filas", "spi": f"FUSIONAR→{v.get('canonica', '')}",
                        "colapsado1": "IN", "colapsado2": "IN",
                        "evidencia_spi": (v.get("evidencia") or "").replace("\n", " ")[:400],
                    })
            lines.append("")

    if kappa_pairs_collapsed:
        k_exact = cohen_kappa(kappa_pairs_exact)
        k_coll = cohen_kappa(kappa_pairs_collapsed)
        n = len(kappa_pairs_collapsed)
        agree_coll = sum(1 for a, b in kappa_pairs_collapsed if a == b)
        agree_exact = sum(1 for a, b in kappa_pairs_exact if a == b)
        head = [
            "## Fiabilidad global (sólo estratos VERIFICACION — muestras aleatorias pre-registradas)", "",
            f"- n = {n} registros con doble veredicto ciego",
            f"- acuerdo bruto COLAPSADO = {100 * agree_coll / n:.1f}% · **Cohen κ = {k_coll:.3f}** "
            f"({interpret_kappa(k_coll)}, Landis & Koch 1977)",
            f"- acuerdo bruto EXACTO = {100 * agree_exact / n:.1f}% · Cohen κ = {k_exact:.3f} "
            f"({interpret_kappa(k_exact)})",
            "", "El κ colapsado es el que responde «¿el paper entra al estudio?»; el exacto también exige "
            "coincidir en el subtipo de exclusión, distinción que no cambia el corpus.", "",
        ]
        lines[2:2] = head

    lines.append("## Cola humana resultante")
    lines.append("")
    lines.append(f"- **{len(conflicts)} filas** en `CONFLICTOS.csv` (de {covered} revisadas por la SPI): "
                 "desacuerdos de membresía, GRIS que persisten con texto completo, degradaciones y fusiones. "
                 "Todo lo demás quedó CONSOLIDADO por coincidencia de dos lectores independientes.")

    report = "\n".join(lines) + "\n"
    if args.write:
        SPI_DIR.mkdir(parents=True, exist_ok=True)
        (SPI_DIR / "AGREEMENT.md").write_text(report, encoding="utf-8")
        with (SPI_DIR / "CONFLICTOS.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=[
                "queue", "kind", "key", "pasada1", "spi", "colapsado1", "colapsado2", "evidencia_spi"])
            w.writeheader()
            for row in sorted(conflicts, key=lambda r: (r["queue"], r["key"])):
                w.writerow(row)
        print(f"[spi] wrote {SPI_DIR/'AGREEMENT.md'} and {SPI_DIR/'CONFLICTOS.csv'} ({len(conflicts)} conflicts)")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
