#!/usr/bin/env python3
"""scorer.py — eval scorer del output VIVO de ASF (MAT-5, DES-7). stdlib (re-derivable sin venv ni red).

Lee METAFACTORY_EVAL_OUTPUT (live_output.json) y carga gold.json del MISMO dir. El output es de un modelo
REAL, VERBOSO y no-determinista (acá, en español: el producto instruye en español): la métrica de
faithfulness-como-precisión de s8 (pensada para el fake-LLM que devuelve el expected verbatim) tankearía con
una respuesta larga aunque CORRECTA. Por eso el régimen LIVE usa dos métricas de COBERTURA por substring
(robustas a inflexión/idioma), ambas las pasa una respuesta on-topic y las flipea una off-topic (el degradado):

  critical_recall    = fracción de los términos `must_cite` (los hechos críticos) presentes en el answer.
  key_term_coverage  = fracción de los `key_terms` (el set conceptual de dominio que una respuesta fiel cubre)
                       presentes en el answer.

El scorer MIDE; el sustrato (live_run) JUZGA contra los umbrales. Imprime SCORE:<metric>=<float>.
El gold codifica los hechos de dominio correctos (no los bytes de una corrida): un answer faithful los cubre.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _coverage(answer_low: str, terms: list) -> float:
    terms = [str(t).lower() for t in terms]
    return (sum(1 for t in terms if t in answer_low) / len(terms)) if terms else 1.0


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
        recalls.append(_coverage(ans, case.get("must_cite", [])))
        coverages.append(_coverage(ans, case.get("key_terms", [])))

    if not recalls:
        print("scorer: no cases scored", file=sys.stderr)
        return 1
    print(f"SCORE:critical_recall={sum(recalls) / len(recalls):.4f}")
    print(f"SCORE:key_term_coverage={sum(coverages) / len(coverages):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
