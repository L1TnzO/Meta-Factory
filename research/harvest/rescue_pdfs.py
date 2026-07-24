#!/usr/bin/env python3
"""Rescue open-access PDFs for the SMS-V2 INCLUIR papers with no local copy.

Per-host resolution, in priority order per record: zenodo/figshare file APIs
(fast, no scraping), arXiv direct mirror, OSF file download, then a generic
"landing-page scrape" (citation_pdf_url meta tag, else first .pdf href) that
covers OJS/AAAI, MDPI, preprints.org, techrxiv and most other publishers —
applied both to the record's own pdf_url/oa_url and to a fresh doi.org
resolution, with an Unpaywall best_oa_location lookup as the final fallback
(the highest-yield source for records with no working url at all).

Only claims a row after the bytes are ON DISK, start with %PDF, and
`pdftotext` extracts >= MIN_CHARS characters — a landing page or a stub is
deleted, never claimed. Resumable (skips keys already in --out or already a
verified corpus/pdf/<key>.pdf) and stdlib-only, one dead host never aborts
the run.

Usage:
  python3 harvest/rescue_pdfs.py --in .gen/rescue/missing.jsonl \
      --out .gen/rescue/rescued.csv [--only KEY]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # research/
PDF_DIR = ROOT / "corpus/pdf"
FIELDS = ["key", "url", "strategy", "sha256", "bytes", "chars"]
MIN_CHARS = 2000  # mirrors harvest/verify_rescue.py's digestibility floor

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)  # a real browser UA — a plain urllib default is what triggers most 403s (zenodo/OJS/IJCAI/
# arxiv all need this). Measured exception: figshare's ndownloader redirector treats a full
# Chrome UA as suspicious and parks the request in an async 202-forever staging state, while
# a bare "Mozilla/5.0" gets the normal 302->S3 redirect — so that ONE host gets a minimal UA.
HOST_UA_OVERRIDE = {"ndownloader.figshare.com": "Mozilla/5.0"}
TIMEOUT = 30
HOST_SLEEP = 1.0  # politeness floor: ~1 req/s per host
UNPAYWALL_EMAIL = "catalinalazolocky@gmail.com"
MAX_ATTEMPTS_PER_RECORD = 8  # bounds worst-case wall time on a fully-dead record

ZENODO_DOI = re.compile(r"10\.5281/zenodo\.(\d+)", re.IGNORECASE)
FIGSHARE_DOI = re.compile(r"10\.6084/m9\.figshare\.(\d+)", re.IGNORECASE)
ARXIV_DOI = re.compile(r"10\.48550/arxiv\.([^\s/]+)", re.IGNORECASE)
ARXIV_URL = re.compile(r"arxiv\.org/(?:abs|pdf)/([^\s?#]+?)(?:\.pdf)?(?:[?#].*)?$", re.IGNORECASE)
OSF_DOI = re.compile(r"10\.17605/osf\.io/([A-Za-z0-9]+)", re.IGNORECASE)
OSF_URL = re.compile(r"osf\.io/([A-Za-z0-9]+)", re.IGNORECASE)
META_TAG = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
CONTENT_ATTR = re.compile(r'content=["\']([^"\']*)["\']', re.IGNORECASE)
PDF_HREF = re.compile(r'href=["\']([^"\']*\.pdf(?:[^"\']*)?)["\']', re.IGNORECASE)

_last_req: dict[str, float] = {}


class Failed(Exception):
    """A candidate URL did not yield a real, extractable PDF. Carries the reason."""


def _throttle(host: str) -> None:
    now = time.monotonic()
    wait = HOST_SLEEP - (now - _last_req.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last_req[host] = time.monotonic()


def _get(url: str, retries: int = 3) -> tuple[str, bytes]:
    """Polite GET with a browser UA. Returns (final_url, body). Raises on network error.

    Some file-hosting APIs (figshare's ndownloader) reply 202 + empty body while the
    file is being staged behind a short-lived signed S3 redirect — a couple of retries
    with backoff turns that into the real 302->200, not a false negative."""
    host = urllib.parse.urlparse(url).netloc
    ua = HOST_UA_OVERRIDE.get(host, UA)
    final_url, body, status = url, b"", 200
    for attempt in range(retries):
        _throttle(host)
        req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            final_url, body, status = resp.geturl(), resp.read(), resp.status
        if status == 202 and not body and attempt < retries - 1:
            time.sleep(2.0)
            continue
        break
    return final_url, body


def _get_json(url: str) -> dict:
    _throttle(urllib.parse.urlparse(url).netloc)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def find_pdf_link(html: bytes, base_url: str) -> str:
    """citation_pdf_url meta tag first (covers MDPI/OJS/preprints.org/most publishers),
    else the first <a href> ending in .pdf."""
    text = html.decode("utf-8", "replace")
    for tag in META_TAG.findall(text):
        if "citation_pdf_url" in tag.lower():
            m = CONTENT_ATTR.search(tag)
            if m and m.group(1):
                return urllib.parse.urljoin(base_url, m.group(1))
    m = PDF_HREF.search(text)
    if m:
        return urllib.parse.urljoin(base_url, m.group(1))
    return ""


def fetch_pdf_bytes(url: str, hops: int = 2) -> bytes:
    """GET url; if it's a real PDF return the bytes. If it's HTML, scrape one pdf
    link and retry (bounded hops). Raise Failed for anything else — never guesses."""
    seen: set[str] = set()
    for _ in range(hops + 1):
        if url in seen:
            raise Failed(f"redirect/scrape loop at {url}")
        seen.add(url)
        final_url, body = _get(url)
        if body.startswith(b"%PDF"):
            return body
        nxt = find_pdf_link(body, final_url)
        if not nxt or nxt in seen:
            raise Failed(f"no PDF and no citation_pdf_url/.pdf link at {final_url}")
        url = nxt
    raise Failed(f"exceeded scrape hops at {url}")


# --- per-host candidate resolvers -------------------------------------------------

def arxiv_id_of(rec: dict) -> str:
    aid = (rec.get("arxiv_id") or "").strip()
    if aid:
        return aid
    m = ARXIV_DOI.search(rec.get("doi") or "")
    if m:
        return m.group(1)
    for field in ("pdf_url", "oa_url"):
        m = ARXIV_URL.search((rec.get(field) or "").strip())
        if m:
            return m.group(1)
    return ""


def zenodo_candidates(doi: str) -> list[str]:
    m = ZENODO_DOI.search(doi)
    if not m:
        return []
    try:
        rec = _get_json(f"https://zenodo.org/api/records/{m.group(1)}")
    except Exception:
        return []
    out = []
    for f in rec.get("files", []) or []:
        name = f.get("key") or f.get("filename") or ""
        link = (f.get("links") or {}).get("self") or (f.get("links") or {}).get("download")
        if link and name.lower().endswith(".pdf"):
            out.append(link)
    return out


def figshare_candidates(doi: str) -> list[str]:
    m = FIGSHARE_DOI.search(doi)
    if not m:
        return []
    try:
        rec = _get_json(f"https://api.figshare.com/v2/articles/{m.group(1)}")
    except Exception:
        return []
    out = []
    for f in rec.get("files", []) or []:
        name = f.get("name") or ""
        link = f.get("download_url")
        if link and name.lower().endswith(".pdf"):
            out.append(link)
    return out


def osf_candidates(rec: dict) -> list[str]:
    doi = rec.get("doi") or ""
    m = OSF_DOI.search(doi) or OSF_URL.search(rec.get("oa_url") or "")
    if not m:
        return []
    return [f"https://osf.io/{m.group(1)}/download"]


def unpaywall_candidates(doi: str) -> list[str]:
    if not doi:
        return []
    url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi, safe='/')}?email={UNPAYWALL_EMAIL}"
    try:
        data = _get_json(url)
    except Exception:
        return []
    out: list[str] = []
    locs = [data.get("best_oa_location") or {}] + list(data.get("oa_locations") or [])
    for loc in locs:
        for key in ("url_for_pdf", "url"):
            v = loc.get(key)
            if v and v not in out:
                out.append(v)
    return out


def build_attempts(rec: dict) -> list[tuple[str, str]]:
    """Ordered (strategy, url) candidates: cheap/high-confidence APIs first, generic
    scrape and Unpaywall (highest yield for no-url records) last."""
    doi = (rec.get("doi") or "").strip()
    attempts: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    def add(strategy: str, url: str) -> None:
        url = (url or "").strip()
        if url and url not in seen_urls:
            seen_urls.add(url)
            attempts.append((strategy, url))

    arxiv_id = arxiv_id_of(rec)
    if arxiv_id:
        add("arxiv", f"https://arxiv.org/pdf/{arxiv_id}")
        if not re.search(r"v\d+$", arxiv_id):
            # the version-less alias occasionally 404s on a stale CDN edge for very
            # recent postings; the explicit v1/v2 mirror is the same PDF and cheap to try
            add("arxiv", f"https://arxiv.org/pdf/{arxiv_id}v1")
            add("arxiv", f"https://arxiv.org/pdf/{arxiv_id}v2")
    for url in zenodo_candidates(doi):
        add("zenodo", url)
    for url in figshare_candidates(doi):
        add("figshare", url)
    for url in osf_candidates(rec):
        add("osf", url)
    add("direct", rec.get("pdf_url") or "")
    add("doi_scrape", rec.get("oa_url") or "")
    if doi:
        add("doi_scrape", f"https://doi.org/{urllib.parse.quote(doi, safe='/')}")
    for url in unpaywall_candidates(doi):
        add("unpaywall", url)
    return attempts[:MAX_ATTEMPTS_PER_RECORD]


def rescue_one(rec: dict) -> tuple[str, str, bytes] | None:
    """Try every candidate in order; return (strategy, url, pdf_bytes) on first
    real PDF, else None. Any single-candidate/network failure is swallowed and
    logged — one dead host never aborts the record, let alone the run."""
    last_err = "no_candidates"
    for strategy, url in build_attempts(rec):
        try:
            data = fetch_pdf_bytes(url)
        except Failed as e:
            last_err = f"{strategy} {url} -> {e}"
            continue
        except urllib.error.HTTPError as e:
            last_err = f"{strategy} {url} -> HTTP {e.code}"
            continue
        except urllib.error.URLError as e:
            last_err = f"{strategy} {url} -> {e.reason}"
            continue
        except Exception as e:  # noqa: BLE001 — record and keep going
            last_err = f"{strategy} {url} -> {type(e).__name__}: {e}"
            continue
        return strategy, url, data
    rescue_one.last_error = last_err  # type: ignore[attr-defined]
    return None


# --- verification + persistence (never claims what it hasn't checked) -------------

def pdf_chars(path: Path) -> int:
    try:
        res = subprocess.run(
            ["pdftotext", "-q", str(path), "-"], capture_output=True, timeout=120, check=False
        )
        return len(res.stdout.decode("utf-8", "replace").strip())
    except Exception:  # noqa: BLE001 — unreadable means "not extractable"
        return 0


def verify_and_write(key: str, blob: bytes) -> dict | None:
    """Write blob to corpus/pdf/<key>.pdf ONLY if it verifies; else clean up and
    return None (never leaves a bogus claim on disk)."""
    if not blob.startswith(b"%PDF"):
        return None
    dest = PDF_DIR / f"{key}.pdf"
    dest.write_bytes(blob)
    chars = pdf_chars(dest)
    if chars < MIN_CHARS:
        dest.unlink(missing_ok=True)
        return None
    return {"sha256": hashlib.sha256(blob).hexdigest(), "bytes": str(len(blob)), "chars": str(chars)}


def load_done(out_path: Path) -> dict[str, dict]:
    if not out_path.exists():
        return {}
    with out_path.open(encoding="utf-8", newline="") as fh:
        return {row["key"]: row for row in csv.DictReader(fh)}


def save(out_path: Path, rows: dict[str, dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for key in sorted(rows):
            writer.writerow({f: rows[key].get(f, "") for f in FIELDS})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="in_path", type=Path, default=Path(".gen/rescue/missing.jsonl"))
    ap.add_argument("--out", dest="out_path", type=Path, default=Path(".gen/rescue/rescued.csv"))
    ap.add_argument("--only", default=None, help="debug: rescue a single key")
    args = ap.parse_args()

    records = [json.loads(ln) for ln in args.in_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if args.only:
        records = [r for r in records if r.get("id") == args.only]
        if not records:
            print(f"[rescue] --only {args.only}: not found in {args.in_path}")
            return 1

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    done = load_done(args.out_path)
    residue: dict[str, str] = {}
    new_ok = 0

    for rec in records:
        key = rec["id"]
        if key in done:
            continue  # resumable: already claimed and on disk

        dest = PDF_DIR / f"{key}.pdf"
        if dest.exists():
            # leftover from an interrupted prior run: re-verify, don't re-download
            info = verify_and_write(key, dest.read_bytes())
            if info:
                row = {"key": key, "url": "(resumed: file already on disk)", "strategy": "resumed", **info}
                done[key] = row
                save(args.out_path, done)
                new_ok += 1
                print(f"[rescue] OK {key} via resumed (file already on disk)")
                continue
            # invalid leftover — fall through and re-attempt a fresh download

        result = rescue_one(rec)
        if result is None:
            reason = getattr(rescue_one, "last_error", "no_candidates")
            residue[key] = reason
            print(f"[rescue] MISS {key}: {reason}")
            continue

        strategy, url, data = result
        info = verify_and_write(key, data)
        if info is None:
            residue[key] = f"{strategy} {url} -> downloaded but failed verification (not PDF or < {MIN_CHARS} chars)"
            print(f"[rescue] MISS {key}: {residue[key]}")
            continue

        row = {"key": key, "url": url, "strategy": strategy, **info}
        done[key] = row
        save(args.out_path, done)  # incremental: crash-safe, keeps the run resumable
        new_ok += 1
        print(f"[rescue] OK {key} via {strategy}")

    print(f"[rescue] {new_ok} newly rescued this run, {len(done)} total claimed in {args.out_path}")
    if residue:
        print(f"[rescue] {len(residue)} unresolved this run:")
        for k, reason in residue.items():
            print(f"[rescue]   {k}: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
