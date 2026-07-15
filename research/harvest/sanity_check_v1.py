#!/usr/bin/env python3
"""Sanity check: the v1 corpus systems should reappear in the v2 harvest
(SMS-V2-PROTOCOL.md §8). Heuristic title match — a miss means "investigate",
not "failure" (title styling differs, or the work entered v1 via a source
not yet harvested, e.g. Lens pending).

Usage: python3 sanity_check_v1.py --corpus ../corpus/merged/corpus.jsonl
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Distinctive system names from the v1 corpus (sms.tex appendix). Generic
# names (MAPLE, SMITH, Prometheus) are flagged: they may match unrelated works.
V1_SYSTEMS = {
    "SWE-Exp": r"swe[\s-]?exp\b",
    "ExpeRepair": r"experepair",
    "Prometheus (generic)": r"\bprometheus\b",
    "ContextWeaver": r"context\s?-?weaver",
    "ClawVM": r"clawvm",
    "Memanto": r"memanto",
    "Springdrift": r"springdrift",
    "MIRIX": r"\bmirix\b",
    "MAPLE (generic)": r"\bmaple\b",
    "TALM": r"\btalm\b",
    "AESP (generic)": r"\baesp\b",
    "SMITH (generic)": r"\bsmith\b",
    "Mem2Evolve": r"mem2evolve",
    "ParamMem": r"parammem",
    "MemCollab": r"memcollab",
    "MemTrack": r"memtrack",
    "LMEB": r"\blmeb\b",
    "CodeMem": r"codemem",
    "PYTHALAB-MERA": r"pythalab",
    "Dual-Cluster Memory": r"dual[\s-]?cluster",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", required=True, type=Path)
    args = ap.parse_args()

    titles = [
        json.loads(ln).get("title") or ""
        for ln in args.corpus.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    found, missing = [], []
    for name, pattern in V1_SYSTEMS.items():
        rx = re.compile(pattern, re.IGNORECASE)
        hits = [t for t in titles if rx.search(t)]
        (found if hits else missing).append((name, hits[:1]))

    print(f"[sanity] corpus titles: {len(titles)}")
    for name, hits in found:
        print(f"  FOUND   {name:24} e.g. {hits[0][:80]}")
    for name, _ in missing:
        print(f"  MISSING {name}")
    print(f"[sanity] {len(found)}/{len(V1_SYSTEMS)} v1 systems matched. "
          "Investigate MISSING before freezing the string (§8) — "
          "Lens/grey-lit pending can explain some.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
