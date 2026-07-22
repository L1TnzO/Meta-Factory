#!/usr/bin/env python3
"""Near-duplicate scanner for the SMS-v2 corpus (SMS-V2-PROTOCOL.md §7.1
dedup: DOI normalizado -> arXiv id -> titulo normalizado, in merge_dedup.py).

MEASURED FINDING (2026-07-18): that DOI/arXiv/title-equality chain let 5
near-duplicate pairs through into the 487 INCLUIR records — 4 with
byte-identical normalized titles (W7119235481~W7118792438,
W4416895257~W4415428439, W4400434708~W4414360988,
2409.01344v2~W4402954570) and 1 title-EXTENSION pair the equality rule
cannot catch at all (W7147524247 'SNT-MEM: Operator-Structured Memory
Management Framework For Self-Regulating AI Systems' ~ W7141308334
'SNT-MEM: Operator-Structured Memory Management Framework'). This tool is
an OBSERVER, not a gate: it scans a sheet, flags near-duplicate title pairs
(IDENTICO / PREFIJO / SIMILAR) into a human queue for adjudication, and
always exits 0 on a successful scan — it must never fail a build.

Blocking (tractability, NOT a naive O(n^2) over 487): records are bucketed
by the first normalized title token, and separately by the full normalized
title. Every pair sharing a bucket is compared. This cannot miss an
IDENTICO pair (equal normalized titles trivially share both the first
token and the full-title bucket) nor a PREFIJO pair (if A is a strict
character-prefix of B, A's leading token is either identical to B's
leading token or a prefix of it that empirically always is, for this
corpus's word-boundary-respecting titles — the SNT-MEM regression case is
exactly this: both share the leading token 'snt').

Usage:
  python3 dup_scan.py scan --sheet ../corpus/extraction/extraction.csv \
      --out ../corpus/screening/queues/DUPLICADOS-INCLUIDOS.csv [--threshold 0.85]
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

QUEUE_COLUMNS = [
    "key_a", "key_b", "similarity", "kind", "title_a", "title_b",
    "year_a", "year_b", "source_a", "source_b",
]

_KIND_RANK = {"IDENTICO": 0, "PREFIJO": 1, "SIMILAR": 2}
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_title(title: str) -> str:
    """Lowercase; collapse runs of non-alphanumeric chars to one space; strip."""
    return _NON_ALNUM_RE.sub(" ", (title or "").lower()).strip()


def _bucket_pairs(indices: list[int]) -> list[tuple[int, int]]:
    return list(combinations(indices, 2))


def find_near_duplicates(records, threshold: float = 0.85) -> list[dict]:
    """Detect near-duplicate titles among `records` (dicts with key/title/
    year/source). Returns unordered pairs reported once (key_a < key_b),
    deterministically sorted (kind rank IDENTICO<PREFIJO<SIMILAR, then
    similarity desc, then key_a, key_b)."""
    recs = list(records)
    normed = [normalize_title(r.get("title") or "") for r in recs]

    first_token: dict[str, list[int]] = {}
    full_title: dict[str, list[int]] = {}
    for i, norm in enumerate(normed):
        if not norm:
            continue
        first_token.setdefault(norm.split(" ", 1)[0], []).append(i)
        full_title.setdefault(norm, []).append(i)

    candidates: set[tuple[int, int]] = set()
    for bucket in first_token.values():
        candidates.update(_bucket_pairs(bucket))
    for bucket in full_title.values():
        candidates.update(_bucket_pairs(bucket))

    results: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for i, j in candidates:
        ra, rb, ta, tb = recs[i], recs[j], normed[i], normed[j]
        ka, kb = str(ra.get("key", "")), str(rb.get("key", ""))
        if not ta or not tb or ka == kb:
            continue
        if kb < ka:
            ka, kb, ra, rb, ta, tb = kb, ka, rb, ra, tb, ta
        if (ka, kb) in seen:
            continue

        if ta == tb:
            kind = "IDENTICO"
        elif ta.startswith(tb) or tb.startswith(ta):
            kind = "PREFIJO"
        else:
            kind = None

        similarity = round(SequenceMatcher(None, ta, tb).ratio(), 3)
        if kind is None:
            if similarity < threshold:
                continue
            kind = "SIMILAR"

        seen.add((ka, kb))
        results.append({
            "key_a": ka, "key_b": kb, "similarity": similarity, "kind": kind,
            "title_a": ra.get("title") or "", "title_b": rb.get("title") or "",
        })

    results.sort(key=lambda r: (_KIND_RANK[r["kind"]], -r["similarity"], r["key_a"], r["key_b"]))
    return results


def load_sheet_records(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def run_scan(sheet: Path, out: Path, threshold: float = 0.85) -> list[dict]:
    records = load_sheet_records(sheet)
    pairs = find_near_duplicates(records, threshold=threshold)
    by_key = {r.get("key"): r for r in records}

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=QUEUE_COLUMNS)
        writer.writeheader()
        for pair in pairs:
            rec_a = by_key.get(pair["key_a"], {})
            rec_b = by_key.get(pair["key_b"], {})
            writer.writerow({
                **pair,
                "year_a": rec_a.get("year", ""), "year_b": rec_b.get("year", ""),
                "source_a": rec_a.get("source", ""), "source_b": rec_b.get("source", ""),
            })

    counts = {k: sum(1 for p in pairs if p["kind"] == k) for k in _KIND_RANK}
    print(
        f"dup_scan: {len(pairs)} pares "
        f"(IDENTICO {counts['IDENTICO']}, PREFIJO {counts['PREFIJO']}, SIMILAR {counts['SIMILAR']})"
    )
    return pairs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    scan_p = sub.add_parser("scan", help="scan a corpus sheet for near-duplicate INCLUIR titles")
    scan_p.add_argument("--sheet", required=True, type=Path)
    scan_p.add_argument("--out", required=True, type=Path)
    scan_p.add_argument("--threshold", type=float, default=0.85)

    args = ap.parse_args(argv)
    if args.command == "scan":
        run_scan(args.sheet, args.out, args.threshold)
    return 0


if __name__ == "__main__":
    sys.exit(main())
