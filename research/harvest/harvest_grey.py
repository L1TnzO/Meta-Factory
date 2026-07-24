#!/usr/bin/env python3
"""harvest_grey.py -- snapshot the MANDATORY Tier-1 grey-literature seeds (closure_law.GREY_TIER1, §9.4/§6.1).

Grey literature is the one part of this corpus that CANNOT be re-derived later: the blogs mutate and the
docs get rewritten -- so the SNAPSHOT is the evidence, not the link. For every seed this fetches the raw
bytes and writes them UNCHANGED to `corpus/grey/<key>.html` (that file plus its recorded sha256 IS the
citable artifact), extracts readable text to `corpus/grey/<key>.txt`, and appends a row to
`corpus/grey/manifest.csv` with EXACTLY `closure_law.GREY_FIELDS` as header. `verify_grey.py` re-hashes
the file on disk against the manifest's sha256, so nothing here is trusted on the tool's word alone.

Network etiquette (mirrors snowball.py's documented convention): a real browser User-Agent (this is
first-party documentation the labs publish for humans, not an API), Accept-Encoding: identity (avoids
needing a decompressor -- these hosts honor it), ~1s between requests, 30s timeout, one retry after a 5s
backoff on 429/5xx.

Resumable: a seed already on disk whose recorded sha256 matches the current bytes is skipped (no
re-fetch, no re-request) unless --force. A seed that cannot be fetched is NEVER fabricated or silently
dropped -- it is reported on stderr and the tool exits non-zero; a missing mandatory seed is a real
finding about lab documentation availability, and `verify_grey.py` will (correctly) stay red until it is
resolved.

Usage: python3 harvest_grey.py [--force]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from closure_law import GREY_TIER1, GREY_FIELDS, ROOT  # noqa: E402  (law: seeds + manifest schema)

GREY_DIR = ROOT / "corpus/grey"
MANIFEST = GREY_DIR / "manifest.csv"

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
SLEEP_S = 1.0
TIMEOUT_S = 30
RETRY_BACKOFF_S = 5
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# doc_type inference from the URL (a HARVEST decision, not part of the frozen law) -- first match wins.
_DOC_TYPE_RULES: tuple[tuple[str, str], ...] = (
    ("platform.claude.com", "platform-docs"),
    ("ai.google.dev", "platform-docs"),
    ("anthropic.com/engineering", "engineering-blog"),
    ("anthropic.com/news", "engineering-blog"),
    ("developers.openai.com/cookbook", "cookbook"),
    ("code.claude.com", "product-docs"),
    ("openai.github.io", "framework-docs"),
)


def infer_doc_type(url: str) -> str:
    for needle, doc_type in _DOC_TYPE_RULES:
        if needle in url:
            return doc_type
    raise ValueError(f"no doc_type rule matches url: {url!r} (extend _DOC_TYPE_RULES)")


# --------------------------------------------------------------------------- HTML -> readable text (stdlib only)
_SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "head", "iframe"}
_BLOCK_TAGS = {
    "p", "div", "section", "article", "li", "ul", "ol", "br", "h1", "h2", "h3", "h4", "h5", "h6",
    "tr", "table", "pre", "blockquote", "header", "footer", "nav", "main", "aside", "dt", "dd",
}
_WS_RE = re.compile(r"[ \t]+")
_CHARSET_HEADER_RE = re.compile(r"charset=([\w-]+)", re.IGNORECASE)
_CHARSET_META_RE = re.compile(rb'charset=["\']?([\w-]+)', re.IGNORECASE)


class _TextExtractor(HTMLParser):
    """A deliberately dumb text extractor: drop <script>/<style>/<head>/... subtrees, insert a newline
    around block-level tags, keep everything else. Good enough to tell a technical document (thousands
    of characters of prose) from a nav shell -- which is all `verify_grey.py`'s GREY_MIN_CHARS floor
    needs -- without a third-party HTML parsing dependency (stdlib only, mirrors the rest of harvest/)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_stack: list[str] = []
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _SKIP_TAGS:
            self._skip_stack.append(tag)
        if tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_startendtag(self, tag: str, attrs) -> None:
        if tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._skip_stack and self._skip_stack[-1] == tag:
            self._skip_stack.pop()
        if tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_stack:
            return
        self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        lines = (_WS_RE.sub(" ", ln).strip() for ln in raw.splitlines())
        return "\n".join(ln for ln in lines if ln)


def _decode_html(blob: bytes, content_type: str) -> str:
    m = _CHARSET_HEADER_RE.search(content_type or "")
    charset = m.group(1) if m else None
    if not charset:
        m2 = _CHARSET_META_RE.search(blob[:4096])
        charset = m2.group(1).decode("ascii", "ignore") if m2 else None
    try:
        return blob.decode(charset or "utf-8", errors="replace")
    except LookupError:
        return blob.decode("utf-8", errors="replace")


def html_to_text(blob: bytes, content_type: str = "") -> str:
    parser = _TextExtractor()
    parser.feed(_decode_html(blob, content_type))
    parser.close()
    return parser.text()


# --------------------------------------------------------------------------- network (real HTTP, mocked in tests)
def _fetch(url: str) -> tuple[bytes, str]:
    """GET url politely; returns (raw_bytes_as_received, Content-Type header). One retry after a 5s
    backoff on 429/5xx; any other error propagates to the caller, which records the failure and moves on
    to the next seed (a partial harvest is honest; a fabricated row is not)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "identity",
        "Accept-Language": "en-US,en;q=0.9",
    })
    attempt = 0
    while True:
        attempt += 1
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return resp.read(), resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            if exc.code in RETRYABLE_STATUS and attempt < 2:
                time.sleep(RETRY_BACKOFF_S)
                continue
            raise


# --------------------------------------------------------------------------- I/O (atomic, mirrors snowball.py)
def _atomic_write_bytes(path: Path, blob: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.tmp"
    tmp.write_bytes(blob)
    os.replace(str(tmp), str(path))


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.tmp"
    tmp.write_text(text, encoding="utf-8")
    os.replace(str(tmp), str(path))


def _atomic_write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for row in rows:
        w.writerow({k: row.get(k, "") for k in fieldnames})
    _atomic_write_text(path, buf.getvalue())


def _load_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    with MANIFEST.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _is_fresh(row: dict, key: str) -> bool:
    """A manifest row counts as already-snapshotted only if BOTH files are on disk AND the html file's
    sha256 still matches the recorded one -- an interrupted run must not be trusted at face value."""
    html_path = GREY_DIR / f"{key}.html"
    txt_path = GREY_DIR / f"{key}.txt"
    if not (html_path.exists() and txt_path.exists()):
        return False
    try:
        blob = html_path.read_bytes()
    except OSError:
        return False
    return hashlib.sha256(blob).hexdigest() == (row.get("sha256") or "").strip()


def fetch_one(seed: dict, retrieved_at: str) -> dict:
    blob, content_type = _fetch(seed["url"])
    _atomic_write_bytes(GREY_DIR / f"{seed['key']}.html", blob)  # raw bytes AS FETCHED -- the evidence
    text = html_to_text(blob, content_type)
    _atomic_write_text(GREY_DIR / f"{seed['key']}.txt", text)
    return {
        "key": seed["key"], "org": seed["org"], "tier": seed["tier"], "title": seed["title"],
        "url": seed["url"], "doc_type": infer_doc_type(seed["url"]), "retrieved_at": retrieved_at,
        "sha256": hashlib.sha256(blob).hexdigest(), "bytes": str(len(blob)), "chars": str(len(text)),
        "rqs": seed["rqs"], "path": f"corpus/grey/{seed['key']}.html",
    }


def cmd_fetch(args) -> int:
    GREY_DIR.mkdir(parents=True, exist_ok=True)
    by_key = {r["key"]: r for r in _load_manifest() if r.get("key")}
    tier1_keys = {s["key"] for s in GREY_TIER1}

    fetched = skipped = 0
    failed: list[tuple[str, str, str]] = []
    for seed in GREY_TIER1:
        key = seed["key"]
        if not args.force and key in by_key and _is_fresh(by_key[key], key):
            skipped += 1
            continue
        try:
            row = fetch_one(seed, _utc_today())
        except Exception as exc:  # noqa: BLE001 -- record and continue; a gap here is a real finding
            failed.append((key, seed["url"], str(exc)))
            print(f"[harvest_grey] FAILED {key} ({seed['url']}): {exc}", file=sys.stderr)
            time.sleep(SLEEP_S)
            continue
        by_key[key] = row
        fetched += 1
        print(f"[harvest_grey] fetched {key}: {row['bytes']} bytes, {row['chars']} chars, "
              f"doc_type={row['doc_type']}")
        time.sleep(SLEEP_S)

    # Declared TIER1 order first (diffable + matches the law's own order), then any legacy extra rows
    # (future-proofing: a prior run's rows for seeds no longer in GREY_TIER1 are kept, not silently lost).
    ordered = [by_key[s["key"]] for s in GREY_TIER1 if s["key"] in by_key]
    extra = [r for k, r in by_key.items() if k not in tier1_keys]
    _atomic_write_csv(MANIFEST, GREY_FIELDS, ordered + extra)

    print(f"[harvest_grey] {fetched} fetched, {skipped} already-fresh, {len(failed)} failed "
          f"(of {len(GREY_TIER1)} mandatory Tier-1 seed(s))")
    if failed:
        print("[harvest_grey] FAILED mandatory seed(s) -- report to the orchestrator, do not fabricate:",
              file=sys.stderr)
        for key, url, reason in failed:
            print(f"  - {key}: {url} :: {reason}", file=sys.stderr)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="re-fetch even seeds already snapshotted on disk")
    args = ap.parse_args(argv)
    return cmd_fetch(args)


if __name__ == "__main__":
    raise SystemExit(main())
