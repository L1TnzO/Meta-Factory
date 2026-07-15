#!/usr/bin/env bash
# One-shot local harvest for SMS v2 (SMS-V2-PROTOCOL.md §7): metadata from
# OpenAlex + arXiv, merge/dedup, open-access PDFs, v1 sanity check.
# Resumable: re-running skips PDFs already downloaded.
#
# Usage: bash harvest_all.sh you@example.com
set -euo pipefail
MAILTO="${1:?usage: bash harvest_all.sh <your-email> (OpenAlex polite pool)}"
cd "$(dirname "$0")"

# SKIP_HARVEST=1 reuses the raw harvests already on disk (e.g. when you only
# added Lens exports): jumps straight to merge + PDFs + sanity. Saves ~40 min
# and OpenAlex/arXiv quota.
if [ "${SKIP_HARVEST:-0}" = "1" ]; then
    echo "[harvest_all] SKIP_HARVEST=1 — reusing existing raw harvests"
else
python3 openalex_harvest.py --query-file queries/openalex_core.txt \
    --mailto "$MAILTO" --out ../corpus/raw/openalex/openalex_core.jsonl

python3 arxiv_harvest.py --query-file queries/arxiv_core.txt \
    --out ../corpus/raw/arxiv/arxiv_core.jsonl

# Q2 general branch (SMS-V2-PROTOCOL.md §4.4): memory systems without an SE
# anchor in the abstract — screening decides transferability (CI2).
python3 openalex_harvest.py --query-file queries/openalex_general.txt --raw \
    --mailto "$MAILTO" --out ../corpus/raw/openalex/openalex_general.jsonl

python3 arxiv_harvest.py --query-file queries/arxiv_general.txt \
    --out ../corpus/raw/arxiv/arxiv_general.jsonl
fi

# Lens exports are optional drop-ins: place UI exports in ../corpus/raw/lens/
LENS_FILES=$(ls ../corpus/raw/lens/*.csv ../corpus/raw/lens/*.json 2>/dev/null || true)
# shellcheck disable=SC2086
python3 merge_dedup.py --out-dir ../corpus/merged \
    ../corpus/raw/openalex/openalex_core.jsonl \
    ../corpus/raw/arxiv/arxiv_core.jsonl \
    ../corpus/raw/openalex/openalex_general.jsonl \
    ../corpus/raw/arxiv/arxiv_general.jsonl $LENS_FILES

python3 download_pdfs.py --corpus ../corpus/merged/corpus.jsonl \
    --out-dir ../corpus/pdf --manifest ../corpus/pdf_manifest.csv

python3 sanity_check_v1.py --corpus ../corpus/merged/corpus.jsonl

echo "[harvest_all] done. Corpus in research/corpus/ (PDFs are gitignored; metadata + manifest are committed)."
