#!/usr/bin/env python3
"""Download open-access PDFs for the merged corpus (SMS-V2-PROTOCOL.md §7).

Reads corpus.jsonl, picks the best URL per record (arXiv mirror > pdf_url >
oa_url), downloads politely, verifies the %PDF magic bytes, and keeps a
resumable manifest. Re-running skips everything already fetched. Stdlib only.

Closed-access records are recorded with status=no_url — consistent with v1's
CE3 (only freely available literature enters the corpus).

Usage:
  python3 download_pdfs.py --corpus ../corpus/merged/corpus.jsonl \
      --out-dir ../corpus/pdf --manifest ../corpus/pdf_manifest.csv
"""

import argparse
import csv
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FIELDS = [
    "key", "arxiv_id", "doi", "title", "status", "url_used",
    "bytes", "sha256", "path", "fetched_at",
]
ARXIV_SLEEP = 1.5  # seconds between arXiv requests (politeness)
OTHER_SLEEP = 0.5


def record_key(rec: dict) -> str:
    for candidate in (rec.get("id"), rec.get("doi"), rec.get("arxiv_id"), rec.get("title")):
        if candidate:
            return re.sub(r"[^A-Za-z0-9._-]+", "_", str(candidate).split("/")[-1])[:120]
    return "unknown"


ARXIV_DOI = re.compile(r"10\.48550/arxiv\.([^\s]+)", re.IGNORECASE)
ARXIV_URL = re.compile(r"arxiv\.org/(?:abs|pdf)/([^\s?#]+?)(?:\.pdf)?$", re.IGNORECASE)


def pick_url(rec: dict) -> tuple[str, bool]:
    """Return (url, is_arxiv). Empty url means no candidate.

    Any arXiv identity (native id, 10.48550 DOI, abs/pdf URL) is normalized to
    the export mirror — landing pages are HTML and were the main not_pdf cause.
    """
    arxiv_id = (rec.get("arxiv_id") or "").strip()
    if not arxiv_id:
        m = ARXIV_DOI.search(rec.get("doi") or "")
        arxiv_id = m.group(1) if m else ""
    if not arxiv_id:
        for field in ("pdf_url", "oa_url"):
            m = ARXIV_URL.search((rec.get(field) or "").strip())
            if m:
                arxiv_id = m.group(1)
                break
    if arxiv_id:
        return f"https://export.arxiv.org/pdf/{arxiv_id}", True
    for field in ("pdf_url", "oa_url"):
        url = (rec.get(field) or "").strip()
        if url:
            return url, "arxiv.org" in url
    return "", False


def download(url: str, dest: Path) -> tuple[str, int, str]:
    url = urllib.parse.quote(url, safe="%:/?#[]@!$&'()*+,;=")  # non-ASCII URLs
    req = urllib.request.Request(url, headers={"User-Agent": "sms-v2-harvest (academic mapping study)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    if not data.startswith(b"%PDF"):
        return "not_pdf", len(data), ""
    dest.write_bytes(data)
    return "ok", len(data), hashlib.sha256(data).hexdigest()


def load_manifest(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        return {row["key"]: row for row in csv.DictReader(fh)}


def save_manifest(path: Path, rows: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for key in sorted(rows):
            writer.writerow({f: rows[key].get(f, "") for f in FIELDS})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--limit", type=int, default=0, help="stop after N downloads (0 = all)")
    ap.add_argument("--budget-seconds", type=int, default=0, help="stop after N seconds (0 = no budget)")
    args = ap.parse_args()

    records = [json.loads(ln) for ln in args.corpus.read_text(encoding="utf-8").splitlines() if ln.strip()]
    manifest = load_manifest(args.manifest)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    attempted = ok = 0
    try:
        for rec in records:
            key = record_key(rec)
            prev = manifest.get(key)
            if prev and prev.get("status") == "ok" and Path(prev.get("path", "")).exists():
                continue
            if args.budget_seconds and time.monotonic() - started > args.budget_seconds:
                print("[pdf] budget reached, resumable — run again to continue")
                break
            if args.limit and attempted >= args.limit:
                break

            url, is_arxiv = pick_url(rec)
            row = {
                "key": key,
                "arxiv_id": rec.get("arxiv_id") or "",
                "doi": rec.get("doi") or "",
                "title": (rec.get("title") or "")[:180],
                "url_used": url,
                "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                "bytes": "", "sha256": "", "path": "",
            }
            if not url:
                row["status"] = "no_url"
                manifest[key] = row
                continue

            attempted += 1
            dest = args.out_dir / f"{key}.pdf"
            try:
                status, size, digest = download(url, dest)
                row.update(status=status, bytes=str(size))
                if status == "ok":
                    row.update(sha256=digest, path=str(dest))
                    ok += 1
            except Exception as exc:  # noqa: BLE001 — record and continue
                row["status"] = f"error:{type(exc).__name__}"
            manifest[key] = row
            print(f"[pdf] {ok}/{attempted} ok — last: {row['status']} {key}", end="\r", flush=True)
            time.sleep(ARXIV_SLEEP if is_arxiv else OTHER_SLEEP)
    finally:
        save_manifest(args.manifest, manifest)

    statuses: dict[str, int] = {}
    for row in manifest.values():
        statuses[row.get("status", "?")] = statuses.get(row.get("status", "?"), 0) + 1
    print(f"\n[pdf] manifest: {args.manifest}")
    print(f"[pdf] totals by status: {statuses}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
