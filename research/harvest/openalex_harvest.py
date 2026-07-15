#!/usr/bin/env python3
"""Harvest OpenAlex works for the SMS v2 search (SMS-V2-PROTOCOL.md §5.1).

Runs the boolean string from a query file against the
`title_and_abstract.search` filter, pages with a cursor, and writes one
normalized JSON record per line. Stdlib only.

Usage:
  python3 openalex_harvest.py --query-file queries/openalex_core.txt \
      --mailto you@example.com --out ../corpus/raw/openalex/openalex_core.jsonl
  python3 openalex_harvest.py --query-file queries/openalex_core.txt \
      --mailto you@example.com --count-only
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.openalex.org/works"


def read_query(path: Path) -> str:
    lines = [
        ln.strip()
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    return " ".join(lines)


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "sms-v2-harvest"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def build_url(query: str, from_date: str, mailto: str, cursor: str, per_page: int) -> str:
    filt = f"title_and_abstract.search:{query},from_publication_date:{from_date}"
    params = {
        "filter": filt,
        "per-page": str(per_page),
        "cursor": cursor,
        "mailto": mailto,
    }
    return API + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


def reconstruct_abstract(inv_index: dict | None) -> str:
    if not inv_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inv_index.items():
        positions.extend((i, word) for i in idxs)
    return " ".join(w for _, w in sorted(positions))


def normalize(work: dict, retrieved_at: str) -> dict:
    primary = work.get("primary_location") or {}
    source = primary.get("source") or {}
    best_oa = work.get("best_oa_location") or {}
    ids = work.get("ids") or {}
    landing = primary.get("landing_page_url") or ""
    arxiv_id = ""
    if "arxiv.org" in landing:
        arxiv_id = landing.rstrip("/").split("/")[-1]
    return {
        "id": work.get("id"),
        "doi": (work.get("doi") or "").replace("https://doi.org/", ""),
        "arxiv_id": arxiv_id,
        "title": work.get("display_name") or "",
        "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
        "year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "venue": source.get("display_name") or "",
        "authors": [
            (a.get("author") or {}).get("display_name")
            for a in work.get("authorships") or []
        ],
        "type": work.get("type"),
        "is_oa": (work.get("open_access") or {}).get("is_oa"),
        "oa_url": best_oa.get("landing_page_url") or "",
        "pdf_url": best_oa.get("pdf_url") or "",
        "cited_by_count": work.get("cited_by_count"),
        "referenced_works": work.get("referenced_works") or [],
        "ids": ids,
        "sources": ["openalex"],
        "source_type": "academic",
        "retrieved_at": retrieved_at,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query-file", required=True, type=Path)
    ap.add_argument("--out", type=Path, help="output JSONL path")
    ap.add_argument("--from-date", default="2022-01-01")
    ap.add_argument("--mailto", required=True, help="contact email (OpenAlex polite pool)")
    ap.add_argument("--count-only", action="store_true")
    ap.add_argument("--per-page", type=int, default=200)
    args = ap.parse_args()

    query = read_query(args.query_file)
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

    first = fetch(build_url(query, args.from_date, args.mailto, "*", 1))
    count = first.get("meta", {}).get("count")
    print(f"[openalex] count={count} from_date={args.from_date} query_file={args.query_file}")
    if args.count_only:
        return 0
    if not args.out:
        print("error: --out is required unless --count-only", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    cursor, written = "*", 0
    with args.out.open("w", encoding="utf-8") as fh:
        while cursor:
            page = fetch(build_url(query, args.from_date, args.mailto, cursor, args.per_page))
            for work in page.get("results", []):
                fh.write(json.dumps(normalize(work, retrieved_at), ensure_ascii=False) + "\n")
                written += 1
            cursor = page.get("meta", {}).get("next_cursor")
            print(f"[openalex] written={written}", end="\r", flush=True)
            time.sleep(0.15)
    print(f"\n[openalex] done: {written} records -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
