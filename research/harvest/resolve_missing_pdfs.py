#!/usr/bin/env python3
"""Build the download input for INCLUIR records that still lack a local PDF.

Scope (SMS-V2-PROTOCOL.md §7 handoff 2026-07-17): the extraction corpus is the
487 INCLUIR (main pass + snowball). This tool finds every INCLUIR key without
`corpus/pdf/<key>.pdf`, re-resolves fresh OA URLs (OpenAlex best_oa_location;
Zenodo file API for 10.5281 DOIs whose landing pages are HTML), and writes a
jsonl in the exact schema `download_pdfs.py` consumes — `id` is set to the
SHEET key so the manifest and pdf filename stay aligned with screening keys.

It never decides inclusion and never touches the sheets: read-only over
screening CSVs, write-only to the output jsonl. Stdlib only; network used
solely for resolution (the actual download stays in download_pdfs.py).

Usage:
  python3 resolve_missing_pdfs.py --research-dir .. \
      --out ../corpus/seeds/missing-pdfs.jsonl [--mailto you@example.org]
"""

import argparse
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OPENALEX_BATCH = 50
SLEEP = 0.4  # politeness between API calls

ZENODO_DOI = re.compile(r"10\.5281/zenodo\.(\d+)", re.IGNORECASE)
ARXIV_KEY = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "sms-v2-harvest (academic mapping study)"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def collect_missing(research: Path) -> list[dict]:
    """One record per INCLUIR key without a local PDF: {key, openalex_id, doi, arxiv_id, title}."""
    pdfdir = {p.name for p in (research / "corpus/pdf").glob("*.pdf")}
    enriched: dict[str, dict] = {}
    enr_path = research / "corpus/seeds/snowball-enriched.jsonl"
    if enr_path.exists():
        for line in enr_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                enriched[d["key"]] = d

    out: list[dict] = []

    def included(decision: str) -> bool:
        return decision.strip().upper().startswith("INCLUIR")

    with (research / "corpus/screening/screening_full.csv").open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if not included(row.get("decision", "")) or f"{row['key']}.pdf" in pdfdir:
                continue
            oid = (row.get("id") or "").rsplit("/", 1)[-1]
            out.append({
                "key": row["key"],
                "openalex_id": oid if oid.startswith("W") else "",
                "doi": (row.get("doi") or "").strip(),
                "arxiv_id": (row.get("arxiv_id") or "").strip(),
                "title": row.get("title") or "",
            })

    with (research / "corpus/screening/screening_snowball.csv").open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if not included(row.get("decision", "")) or f"{row['key']}.pdf" in pdfdir:
                continue
            key = row["key"]
            meta = enriched.get(key, {})
            doi = (row.get("doi") or meta.get("doi") or "").replace("https://doi.org/", "").strip()
            out.append({
                "key": key,
                "openalex_id": key if key.startswith("W") else "",
                "doi": doi,
                "arxiv_id": key if ARXIV_KEY.match(key) else "",
                "title": row.get("title") or meta.get("title") or "",
            })
    return out


def resolve_openalex(records: list[dict], mailto: str) -> None:
    """Fill pdf_url/oa_url in place from OpenAlex best_oa_location (batched)."""
    by_id = {r["openalex_id"]: r for r in records if r["openalex_id"]}
    ids = sorted(by_id)
    for i in range(0, len(ids), OPENALEX_BATCH):
        chunk = ids[i:i + OPENALEX_BATCH]
        params = {
            "filter": "ids.openalex:" + "|".join(chunk),
            "select": "id,doi,best_oa_location,locations",
            "per-page": str(len(chunk)),
        }
        if mailto:
            params["mailto"] = mailto
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
        try:
            data = _get_json(url)
        except Exception as exc:  # noqa: BLE001 — record and continue; downloader handles no_url
            print(f"[resolve] openalex batch {i // OPENALEX_BATCH}: {type(exc).__name__}", file=sys.stderr)
            continue
        for work in data.get("results", []):
            wid = (work.get("id") or "").rsplit("/", 1)[-1]
            rec = by_id.get(wid)
            if rec is None:
                continue
            best = work.get("best_oa_location") or {}
            pdf = best.get("pdf_url") or ""
            if not pdf:
                for loc in work.get("locations") or []:
                    if loc and loc.get("pdf_url"):
                        pdf = loc["pdf_url"]
                        break
            rec["pdf_url"] = pdf
            rec["oa_url"] = best.get("landing_page_url") or ""
            if not rec["doi"]:
                rec["doi"] = (work.get("doi") or "").replace("https://doi.org/", "")
        time.sleep(SLEEP)


def resolve_zenodo(records: list[dict]) -> None:
    """Zenodo landing pages are HTML (the not_pdf cause); the file API has the real PDF."""
    for rec in records:
        if rec.get("pdf_url"):
            continue
        m = ZENODO_DOI.search(rec.get("doi") or "")
        if not m:
            continue
        try:
            data = _get_json(f"https://zenodo.org/api/records/{m.group(1)}")
        except Exception as exc:  # noqa: BLE001
            print(f"[resolve] zenodo {m.group(1)}: {type(exc).__name__}", file=sys.stderr)
            continue
        for f in data.get("files") or []:
            name = (f.get("key") or "").lower()
            link = (f.get("links") or {}).get("self") or ""
            if name.endswith(".pdf") and link:
                rec["pdf_url"] = link
                break
        time.sleep(SLEEP)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--research-dir", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--mailto", default="")
    ap.add_argument("--offline", action="store_true", help="collect + report only, no network")
    args = ap.parse_args()

    records = collect_missing(args.research_dir)
    print(f"[resolve] INCLUIR without local PDF: {len(records)}")
    if not args.offline:
        resolve_openalex(records, args.mailto)
        resolve_zenodo(records)

    with args.out.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps({
                "id": rec["key"],  # keeps manifest/pdf filename == screening key
                "doi": rec.get("doi", ""),
                "arxiv_id": rec.get("arxiv_id", ""),
                "title": rec.get("title", ""),
                "pdf_url": rec.get("pdf_url", ""),
                "oa_url": rec.get("oa_url", ""),
            }, ensure_ascii=False) + "\n")

    resolved = sum(1 for r in records if r.get("pdf_url") or r.get("arxiv_id"))
    print(f"[resolve] wrote {args.out} — with a concrete pdf/arXiv candidate: {resolved}/{len(records)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
