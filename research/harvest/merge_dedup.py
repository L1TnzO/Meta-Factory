#!/usr/bin/env python3
"""Merge per-source harvests into one deduplicated corpus (SMS-V2-PROTOCOL.md §7).

Inputs: any mix of
  - normalized JSONL from openalex_harvest.py / arxiv_harvest.py
  - Lens.org UI exports (.csv or .json), mapped defensively by column name

Dedup key priority: normalized DOI -> arXiv id -> normalized title.
On duplicates the record with more filled fields wins; `sources` accumulates.

Usage:
  python3 merge_dedup.py --out-dir ../corpus/merged \
      ../corpus/raw/openalex/openalex_core.jsonl \
      ../corpus/raw/arxiv/arxiv_core.jsonl \
      ../corpus/raw/lens/lens_core.csv
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

CSV_FIELDS = [
    "id", "doi", "arxiv_id", "title", "year", "venue", "type",
    "cited_by_count", "oa_url", "pdf_url", "sources",
]

ARXIV_DOI_RE = re.compile(r"10\.48550/arxiv\.(.+)", re.IGNORECASE)


def norm_doi(doi: str) -> str:
    doi = (doi or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        doi = doi.removeprefix(prefix)
    return doi


def norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())


def norm_arxiv(record: dict) -> str:
    raw = (record.get("arxiv_id") or "").strip().lower()
    raw = re.sub(r"v\d+$", "", raw)
    if raw:
        return raw
    m = ARXIV_DOI_RE.match(norm_doi(record.get("doi") or ""))
    return m.group(1) if m else ""


def lens_pick(row: dict, *candidates: str) -> str:
    lowered = {k.strip().lower(): (v or "") for k, v in row.items() if k}
    for cand in candidates:
        if cand in lowered and str(lowered[cand]).strip():
            return str(lowered[cand]).strip()
    return ""


def from_lens(row: dict) -> dict:
    year = lens_pick(row, "publication year", "year published", "year")
    return {
        "id": lens_pick(row, "lens id", "lens_id"),
        "doi": norm_doi(lens_pick(row, "doi")),
        "arxiv_id": "",
        "title": lens_pick(row, "title"),
        "abstract": lens_pick(row, "abstract"),
        "year": int(year) if year.isdigit() else None,
        "venue": lens_pick(row, "source title", "source_title", "source"),
        "authors": [a.strip() for a in lens_pick(row, "author/s", "authors").split(";") if a.strip()],
        "type": lens_pick(row, "publication type", "publication_type"),
        "oa_url": lens_pick(row, "open access url", "source urls", "external url"),
        "pdf_url": "",
        "cited_by_count": None,
        "referenced_works": [],
        "sources": ["lens"],
        "source_type": "academic",
    }


def load(path: Path) -> list[dict]:
    if path.suffix == ".jsonl":
        return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if path.suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as fh:
            return [from_lens(row) for row in csv.DictReader(fh)]
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else data.get("data") or data.get("results") or []
        return [from_lens(row) for row in rows]
    raise ValueError(f"unsupported input: {path}")


def filled(record: dict) -> int:
    return sum(1 for v in record.values() if v not in (None, "", [], {}))


def keys_for(record: dict) -> list[str]:
    keys = []
    if norm_doi(record.get("doi") or ""):
        keys.append("doi:" + norm_doi(record["doi"]))
    if norm_arxiv(record):
        keys.append("arxiv:" + norm_arxiv(record))
    if norm_title(record.get("title") or ""):
        keys.append("title:" + norm_title(record["title"]))
    return keys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    canonical: list[dict] = []
    index: dict[str, int] = {}
    per_source: dict[str, int] = {}

    for path in args.inputs:
        records = load(path)
        for rec in records:
            for src in rec.get("sources", ["?"]):
                per_source[src] = per_source.get(src, 0) + 1
            hit = next((index[k] for k in keys_for(rec) if k in index), None)
            if hit is None:
                canonical.append(rec)
                hit = len(canonical) - 1
            else:
                old = canonical[hit]
                merged_sources = sorted(set(old.get("sources", [])) | set(rec.get("sources", [])))
                winner = rec if filled(rec) > filled(old) else old
                winner = dict(winner, sources=merged_sources)
                canonical[hit] = winner
            for k in keys_for(canonical[hit]):
                index[k] = hit
        print(f"[merge] loaded {len(records):>5} from {path}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_jsonl = args.out_dir / "corpus.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as fh:
        for rec in canonical:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    out_csv = args.out_dir / "corpus.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for rec in canonical:
            row = dict(rec, sources="|".join(rec.get("sources", [])))
            writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})

    multi = sum(1 for r in canonical if len(r.get("sources", [])) > 1)
    print(f"[merge] per-source inputs: {per_source}")
    print(f"[merge] unique records: {len(canonical)} (in >=2 sources: {multi})")
    print(f"[merge] wrote {out_jsonl} and {out_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
