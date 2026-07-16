#!/usr/bin/env python3
"""Gold-set sanity check (SMS-V2-PROTOCOL.md §4.6) — replaces v1-corpus authority.

The gold set is 12 community-validated memory works (citation-anchored, chosen
for the Meta-Factory needs they validate, independently of the v1 corpus).
For each: is it IN the corpus as a paper, and how often is it MENTIONED in
abstracts? Mentions without presence = reachable via backward snowballing
from the included set (the demonstrated path for the 2023-24 foundational
layer, which is out of string scope by design).

Usage: python3 sanity_check_gold.py --corpus ../corpus/merged/corpus.jsonl [--also-v1]
"""

import argparse
import json
import re
import sys
from pathlib import Path

# name -> (title regex, arXiv id, MF need it validates)
GOLD = {
    "MemGPT":            (r"memgpt",             "2310.08560", "tiers/OS-style core+archival (Tier 0/1/2)"),
    "Voyager":           (r"\bvoyager\b",        "2305.16291", "skill library = memoria procedimental"),
    "Reflexion":         (r"\breflexion\b",      "2303.11366", "escritura de lecciones (G-M1)"),
    "ExpeL":             (r"\bexpel\b",          "2308.10144", "extracción/consolidación de insights"),
    "Generative Agents": (r"generative agents.*simulacra|interactive simulacra", "2304.03442", "retrieval puntuado recency·importance·relevance (G-M2)"),
    "MemoryBank":        (r"memorybank",         "2305.10250", "olvido/curva de decaimiento"),
    "HippoRAG":          (r"hipporag",           "2405.14831", "índice semántico/KG (contra-evidencia ADR-019 §6)"),
    "A-Mem":             (r"\ba-mem\b",          "2502.12110", "organización dinámica de memoria agéntica"),
    "Mem0":              (r"\bmem0\b",           "2504.19413", "capa de memoria en producción; costo/latencia"),
    "AWM":               (r"agent workflow memory", "2409.07429", "inducción de workflows (procedimental/factory)"),
    "Titans":            (r"\btitans\b",         "2501.00663", "memoria paramétrica test-time (polo paramétrico)"),
    "Sleep-time":        (r"sleep-?time",        "2504.13171", "consolidación offline en checkpoints (G-M1)"),
}

V1_INFORMATIVE = [  # informational only — NO authority (protocol §7.3)
    "swe-exp", "experepair", "prometheus", "context\\s?-?weaver", "clawvm", "memanto",
    "springdrift", "\\bmirix\\b", "\\bmaple\\b", "\\btalm\\b", "\\baesp\\b", "\\bsmith\\b",
    "mem2evolve", "parammem", "memcollab", "memtrack", "\\blmeb\\b", "codemem",
    "pythalab", "dual[\\s-]?cluster",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", required=True, type=Path)
    ap.add_argument("--also-v1", action="store_true", help="also report v1-system overlap (informational)")
    args = ap.parse_args()

    records = [json.loads(ln) for ln in args.corpus.read_text(encoding="utf-8").splitlines() if ln.strip()]
    titles = [(r.get("title") or "") for r in records]
    absts = [(r.get("abstract") or "") for r in records]

    present, via_snowball = 0, 0
    print(f"[gold] corpus: {len(records)} records")
    for name, (pat, arxiv, need) in GOLD.items():
        rx = re.compile(pat, re.IGNORECASE)
        in_title = any(rx.search(t) for t in titles)
        mentions = sum(1 for a in absts if rx.search(a))
        if in_title:
            present += 1
            status = "IN-CORPUS"
        elif mentions:
            via_snowball += 1
            status = f"SNOWBALL-REACHABLE ({mentions} menciones)"
        else:
            status = "SOLO-SEMILLA-MANUAL"
        print(f"  {name:18s} {status:34s} arXiv:{arxiv}  valida: {need}")
    print(f"[gold] {present}/12 en corpus · {via_snowball}/12 citados por el corpus (snowball directo) "
          f"· {12 - present - via_snowball}/12 solo-semilla-manual — los 12 son semillas por §7.3; "
          "si 'solo-semilla' crece entre runs, la cadena está derivando del campo")

    if args.also_v1:
        hits = sum(1 for pat in V1_INFORMATIVE if any(re.search(pat, t, re.IGNORECASE) for t in titles))
        print(f"[v1-info] solape con sistemas v1: {hits}/{len(V1_INFORMATIVE)} (sin autoridad; §7.3)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
