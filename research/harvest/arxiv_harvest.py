#!/usr/bin/env python3
"""Harvest arXiv entries for the SMS v2 search (SMS-V2-PROTOCOL.md §5.3).

Runs the query file against the arXiv Atom API, pages politely (3 s between
requests per arXiv ToS), and writes one normalized JSON record per line.
Stdlib only.

Usage:
  python3 arxiv_harvest.py --query-file queries/arxiv_core.txt \
      --out ../corpus/raw/arxiv/arxiv_core.jsonl
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

API = "https://export.arxiv.org/api/query"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def read_query(path: Path) -> str:
    lines = [
        ln.strip()
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    return " ".join(lines)


def build_url(query: str, start: int, page_size: int) -> str:
    params = {
        "search_query": query,
        "start": str(start),
        "max_results": str(page_size),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    # quote_plus: spaces as '+' — the %20 form pushed the v2.1 core query past
    # the API's ~2k URL limit and produced HTTP 500 (observed 2026-07-15).
    return API + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote_plus)


def fetch(query: str, start: int, page_size: int) -> ET.Element:
    url = build_url(query, start, page_size)
    if len(url) > 2000:
        print(f"[arxiv] warning: url length {len(url)} — consider splitting block A "
              "into two runs (dedup absorbs the overlap)", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": "sms-v2-harvest"})
    last: Exception | None = None
    for attempt in range(3):  # arXiv API throws transient 5xx
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return ET.fromstring(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                raise
            last = exc
            time.sleep(5 * (attempt + 1))
    raise last  # type: ignore[misc]


def text(el: ET.Element | None) -> str:
    return " ".join((el.text or "").split()) if el is not None else ""


def normalize(entry: ET.Element, retrieved_at: str) -> dict:
    arxiv_url = text(entry.find("atom:id", NS))
    arxiv_id = arxiv_url.rstrip("/").split("/abs/")[-1]
    pdf_url = ""
    for link in entry.findall("atom:link", NS):
        if link.get("title") == "pdf":
            pdf_url = link.get("href") or ""
    published = text(entry.find("atom:published", NS))
    primary = entry.find("arxiv:primary_category", NS)
    return {
        "id": arxiv_url,
        "doi": text(entry.find("arxiv:doi", NS)),
        "arxiv_id": arxiv_id,
        "title": text(entry.find("atom:title", NS)),
        "abstract": text(entry.find("atom:summary", NS)),
        "year": int(published[:4]) if published[:4].isdigit() else None,
        "publication_date": published[:10],
        "venue": "arXiv",
        "authors": [
            text(a.find("atom:name", NS)) for a in entry.findall("atom:author", NS)
        ],
        "type": "preprint",
        "is_oa": True,
        "oa_url": arxiv_url,
        "pdf_url": pdf_url,
        "cited_by_count": None,
        "referenced_works": [],
        "categories": [
            c.get("term") for c in entry.findall("atom:category", NS)
        ],
        "primary_category": primary.get("term") if primary is not None else "",
        "sources": ["arxiv"],
        "source_type": "academic",
        "retrieved_at": retrieved_at,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query-file", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--max", type=int, default=5000, help="safety cap on records")
    args = ap.parse_args()

    query = read_query(args.query_file)
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    args.out.parent.mkdir(parents=True, exist_ok=True)

    start, written, total = 0, 0, None
    with args.out.open("w", encoding="utf-8") as fh:
        while True:
            root = fetch(query, start, args.page_size)
            if total is None:
                total = int(text(root.find("opensearch:totalResults", NS)) or 0)
                print(f"[arxiv] totalResults={total} query_file={args.query_file}")
            entries = root.findall("atom:entry", NS)
            if not entries:
                break
            for entry in entries:
                fh.write(json.dumps(normalize(entry, retrieved_at), ensure_ascii=False) + "\n")
                written += 1
                if written >= args.max:
                    break
            if written >= args.max or written >= total:
                break
            start += args.page_size
            print(f"[arxiv] written={written}/{total}", end="\r", flush=True)
            time.sleep(3)  # arXiv API ToS
    print(f"\n[arxiv] done: {written} records -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
