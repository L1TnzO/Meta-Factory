#!/usr/bin/env python3
"""Build the title/abstract screening sheet for SMS v2.2 (protocol §7.5).

Annotates every corpus record with TRANSPARENT deterministic signals and a
triage bucket. The triage does NOT decide inclusion — it orders the review
and gives denominators; every rule is data in this file, reviewable in diff.

Triage:
  PRE-OUT : divergent-domain signal present and no SE signal
  PRE-IN  : memory term in TITLE and (SE signal or agent signal)
  GRIS    : everything else (human judgment zone)

Also emits a stratified calibration sample (default n=50: half with SE
signal, half without — the Q2 general branch) to calibrate the M/T/E rubric
before the full pass.

Usage:
  python3 make_screening_sheet.py --corpus ../corpus/merged/corpus.jsonl \
      --manifest ../corpus/pdf_manifest.csv --out-dir ../corpus/screening \
      --sample 50 --seed 42
"""

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from download_pdfs import record_key  # noqa: E402  (same key as the PDF manifest)

MEM_TERMS = [
    "semantic memory", "episodic memory", "working memory", "procedural memory",
    "memory-augmented", "persistent memory", "long-term memory", "external memory",
    "memory mechanism", "memory module", "cross-session", "context retention",
    "agent memory", "agentic memory", "memory architecture", "memory system",
    "memory management", "memory bank", "memory consolidation", "context engineering",
    "context management", "skill library", "experience reuse", "experience bank",
    "experience-driven", "memory operating system",
]
SE_TERMS = [
    "debugging", "program repair", "software development", "code generation",
    "issue resolution", "software engineering", "software maintenance", "code review",
    "refactoring", "repository-level", "swe-bench", "repository", "codebase",
    "developer", "pull request", "unit test", "code agent", "coding agent",
]
AGENT_TERMS = [
    "llm agent", "ai agent", "language model agent", "coding agent",
    "software engineering agent", "agentic", "autonomous agent", "code agent",
    "software agent", "multi-agent", "llm-based",
]
DIVERGENT_TERMS = [  # domain-application flags; conservative on purpose
    "clinical", "healthcare", "medical", "patient", "hospital", "disease",
    "robot", "robotic", "drone", "uav", "autonomous driving", "self-driving",
    "classroom", "tutoring", "psychiatric", "psychotherapy", "mental health",
    "eeg", "fmri", "neuroimaging", "recommendation system", "recommender",
    "e-commerce", "advertising", "wireless", "smart grid", "battery",
    "protein", "molecule", "stock market", "trading strategy",
    # P7 (calibration 2026-07-16): reached GRIS/PRE-IN while being clear PRE-OUTs
    "embodied", "humanoid", "egocentric",
]
# WARNING (calibration 2026-07-16): re-running this script REGENERATES both
# sheets with EMPTY decision columns. Once screening decisions exist in
# corpus/screening/*.csv, do NOT re-run over them — the P7 terms above only
# apply to future regenerations/reproducibility.

# MF facets (protocol §7.5): multi-label HINTS mapped to Meta-Factory needs.
# They do not gate inclusion — they drive digestion PRIORITY (§7.4). The
# reviewer confirms/corrects them in the F column.
MF_FACETS = {
    "WRITE": r"when to (write|store)|write polic|admission|what to (store|remember)",
    "RETRIEVAL-MEDIDO": r"retrieval (accuracy|quality|utility)|abstention|hit rate",
    "DOCS-VERSIONADO": r"\bgit\b|version control|versioned|markdown|file-based|filesystem|file system",
    "FIDELIDAD": r"provenance|trust|verif|staleness|stale\b|outdated|audit",
    "CONSOLIDACION": r"consolidat|forgett|decay|garbage collect|compaction|prun",
    "COSTO": r"token (budget|cost|usage)|context budget|cost-aware|budget-aware|kv cache|prompt cach",
    "MULTIAGENTE": r"shared memory|cross-agent|memory (sharing|exchange)|collaborative memor|multi-agent memor",
    "SEGURIDAD": r"poison|inject|adversarial|secure|privacy",
    "NEGATIVO": r"negative knowledge|failed (trajector|attempt|experience)|rejected approach|learn from failure",
    "PROCEDIMENTAL": r"skill librar|procedural memor|workflow (memor|induction)|reusable (skill|workflow)",
}
MF_RX = {k: re.compile(v) for k, v in MF_FACETS.items()}

FIELDS = [
    "key", "id", "doi", "arxiv_id", "year", "venue", "sources", "has_pdf",
    "sig_mem_title", "sig_se", "sig_agent", "sig_divergent", "sig_mf_facets", "triage",
    "M", "T", "E", "F", "decision", "notes", "title", "abstract_400",
]


def any_term(text: str, terms: list[str]) -> str:
    return ";".join(t for t in terms if t in text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--sample", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    with args.manifest.open(encoding="utf-8", newline="") as fh:
        pdf_ok = {r["key"] for r in csv.DictReader(fh) if r["status"] == "ok"}

    rows = []
    for ln in args.corpus.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        rec = json.loads(ln)
        title = (rec.get("title") or "")
        abstract = (rec.get("abstract") or "")
        tl, al = title.lower(), (title + " " + abstract).lower()
        sig_mem_t = any_term(tl, MEM_TERMS)
        sig_se = any_term(al, SE_TERMS)
        sig_agent = any_term(al, AGENT_TERMS)
        sig_div = any_term(al, DIVERGENT_TERMS)
        sig_facets = ";".join(name for name, rx in MF_RX.items() if rx.search(al))
        if sig_div and not sig_se:
            triage = "PRE-OUT"
        elif sig_mem_t and (sig_se or sig_agent):
            triage = "PRE-IN"
        else:
            triage = "GRIS"
        key = record_key(rec)
        rows.append({
            "key": key, "id": rec.get("id") or "", "doi": rec.get("doi") or "",
            "arxiv_id": rec.get("arxiv_id") or "", "year": rec.get("year") or "",
            "venue": rec.get("venue") or "", "sources": "|".join(rec.get("sources") or []),
            "has_pdf": "1" if key in pdf_ok else "0",
            "sig_mem_title": sig_mem_t, "sig_se": sig_se, "sig_agent": sig_agent,
            "sig_divergent": sig_div, "sig_mf_facets": sig_facets, "triage": triage,
            "M": "", "T": "", "E": "", "F": "", "decision": "", "notes": "",
            "title": title, "abstract_400": re.sub(r"\s+", " ", abstract)[:400],
        })

    args.out_dir.mkdir(parents=True, exist_ok=True)
    full = args.out_dir / "screening_full.csv"
    with full.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    rng = random.Random(args.seed)
    with_se = [r for r in rows if r["sig_se"]]
    without_se = [r for r in rows if not r["sig_se"]]
    half = args.sample // 2
    sample = (rng.sample(with_se, min(half, len(with_se)))
              + rng.sample(without_se, min(args.sample - half, len(without_se))))
    rng.shuffle(sample)
    cal = args.out_dir / f"calibration_sample_{args.sample}_seed{args.seed}.csv"
    with cal.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(sample)

    stats = {}
    for r in rows:
        stats[r["triage"]] = stats.get(r["triage"], 0) + 1
    fstats = {name: sum(1 for r in rows if name in r["sig_mf_facets"]) for name in MF_FACETS}
    print(f"[screening] {len(rows)} registros -> {full}")
    print(f"[screening] triage: {stats}")
    print(f"[screening] facetas MF (hints): {dict(sorted(fstats.items(), key=lambda x: x[1]))}")
    print(f"[screening] calibración: {len(sample)} -> {cal} "
          f"({min(half, len(with_se))} con señal SE, resto rama general)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
