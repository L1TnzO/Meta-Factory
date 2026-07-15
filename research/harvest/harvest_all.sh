#!/usr/bin/env bash
# One-shot local harvest for SMS v2 (SMS-V2-PROTOCOL.md §7): metadata from
# OpenAlex + arXiv, merge/dedup, open-access PDFs, v1 sanity check.
# Resumable: re-running skips PDFs already downloaded.
#
# Usage: bash harvest_all.sh you@example.com
set -euo pipefail
MAILTO="${1:?usage: bash harvest_all.sh <your-email> (OpenAlex polite pool)}"
cd "$(dirname "$0")"

python3 openalex_harvest.py --query-file queries/openalex_core.txt \
    --mailto "$MAILTO" --out ../corpus/raw/openalex/openalex_core.jsonl

python3 arxiv_harvest.py --query-file queries/arxiv_core.txt \
    --out ../corpus/raw/arxiv/arxiv_core.jsonl

# Lens exports are optional drop-ins: place UI exports in ../corpus/raw/lens/
LENS_FILES=$(ls ../corpus/raw/lens/*.csv ../corpus/raw/lens/*.json 2>/dev/null || true)
# shellcheck disable=SC2086
python3 merge_dedup.py --out-dir ../corpus/merged \
    ../corpus/raw/openalex/openalex_core.jsonl \
    ../corpus/raw/arxiv/arxiv_core.jsonl $LENS_FILES

python3 download_pdfs.py --corpus ../corpus/merged/corpus.jsonl \
    --out-dir ../corpus/pdf --manifest ../corpus/pdf_manifest.csv

python3 sanity_check_v1.py --corpus ../corpus/merged/corpus.jsonl

echo "[harvest_all] done. Corpus in research/corpus/ (PDFs are gitignored; metadata + manifest are committed)."
