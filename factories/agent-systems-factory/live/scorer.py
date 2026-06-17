#!/usr/bin/env python3
"""scorer.py — eval scorer del output VIVO de Agent_RE (MAT-6, DES-7). stdlib (re-derivable sin venv ni red).

Lee METAFACTORY_EVAL_OUTPUT (live_output.json) y carga gold.json del MISMO dir. El producto recupera, desde
una transcripción de entrevista REAL (dataset/example_conversation.txt), los requisitos funcionales del sistema
IFA. El gold es la lista de 28 requisitos que los EXPERTOS HUMANOS recuperaron de esa misma transcripción
(dataset/experts_final_requirements.txt) — un ground truth REAL, no los bytes de una corrida.

El output es de un modelo REAL, VERBOSO y no-determinista (puede responder en inglés o español): se mide por
COBERTURA por substring (robusta a inflexión/idioma), discriminante (la pasa una recuperación fiel, la flipea
una respuesta off-topic — el degradado):

  critical_recall    = fracción de los 28 requisitos-experto que el answer CUBRE. Un requisito está cubierto si
                       el answer contiene ALGUNO de sus anchors `any` (los hechos de dominio que lo identifican).
                       Es el RECALL real de requisitos contra el oráculo humano (el RQ2 del dataset RECOVER).
  key_term_coverage  = fracción de los CONCEPTOS de dominio (`key_concepts`) cubiertos por el answer. Cada
                       concepto es un grupo de sinónimos (EN/ES); está cubierto si ALGUNO aparece — robusto al
                       idioma (no penaliza una respuesta monolingüe correcta como haría una lista plana bilingüe).

El scorer MIDE; el sustrato (live_run) JUZGA contra los umbrales. Imprime SCORE:<metric>=<float>.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _covers(answer_low: str, anchors: list) -> bool:
    return any(str(a).lower() in answer_low for a in anchors)


def main() -> int:
    out_path = os.environ.get("METAFACTORY_EVAL_OUTPUT", "")
    if not out_path:
        print("scorer: METAFACTORY_EVAL_OUTPUT no está definido", file=sys.stderr)
        return 1
    outputs = json.loads(Path(out_path).read_text(encoding="utf-8"))
    gold = json.loads((Path(out_path).parent / "gold.json").read_text(encoding="utf-8"))
    answers = {str(o["case_id"]): str(o.get("answer", "")).lower() for o in outputs}

    recalls: list[float] = []
    coverages: list[float] = []
    for case in gold:
        ans = answers.get(str(case["case_id"]), "")
        reqs = case.get("requirements", [])
        if reqs:
            covered = sum(1 for r in reqs if _covers(ans, r.get("any", [])))
            recalls.append(covered / len(reqs))
        concepts = case.get("key_concepts", [])
        if concepts:
            covered_c = sum(1 for grp in concepts if _covers(ans, grp))
            coverages.append(covered_c / len(concepts))

    if not recalls:
        print("scorer: no cases scored (gold sin requirements)", file=sys.stderr)
        return 1
    print(f"SCORE:critical_recall={sum(recalls) / len(recalls):.4f}")
    print(f"SCORE:key_term_coverage={sum(coverages) / len(coverages):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
