#!/usr/bin/env python3
"""Deterministic gate for the grey-literature corpus, RQ7 (protocol §9.4 / §6.3).

Trust-chain: written by the orchestrator, not by the slot it judges. Read-only.

Grey literature is the one part of this corpus that CANNOT be re-derived later: the blogs mutate and
the docs get rewritten (§6.3). So the gate holds the snapshot, not the link:

  1. every MANDATORY Tier-1 seed is present (a grey corpus that drops the inconvenient lab answers a
     different question than the one RQ7 asks);
  2. every row's file exists and hashes to the recorded sha256 — the snapshot is the evidence;
  3. every snapshot carries enough text to be a technical document rather than a nav shell;
  4. `doc_type` and `retrieved_at` are present and well-formed, because an undated snapshot of a
     mutating page is not evidence of anything.

Usage: python3 harvest/verify_grey.py [--manifest corpus/grey/manifest.csv]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from closure_law import GREY_TIER1, GREY_FIELDS, GREY_DOC_TYPES, GREY_MIN_CHARS, ROOT  # noqa: E402

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}Z)?$")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=ROOT / "corpus/grey/manifest.csv")
    args = ap.parse_args()

    if not args.manifest.exists():
        print(f"RED: no grey manifest at {args.manifest}")
        return 1

    with args.manifest.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        rows = list(reader)

    errors: list[str] = []
    if header != GREY_FIELDS:
        errors.append(f"header != law GREY_FIELDS\n     got: {header}\n     want: {GREY_FIELDS}")
        for e in errors:
            print(f"RED: {e}")
        return 1

    seen: set[str] = set()
    for i, row in enumerate(rows, 1):
        key = (row.get("key") or "").strip()
        where = f"row {i} (key={key or '?'})"
        if not key:
            errors.append(f"{where}: empty key")
            continue
        if key in seen:
            errors.append(f"{where}: duplicated key")
            continue
        seen.add(key)

        if (row.get("doc_type") or "").strip() not in GREY_DOC_TYPES:
            errors.append(f"{where}: doc_type '{row.get('doc_type')}' not in {sorted(GREY_DOC_TYPES)}")
        if not DATE_RE.match((row.get("retrieved_at") or "").strip()):
            errors.append(f"{where}: retrieved_at must be YYYY-MM-DD[THH:MMZ] (an undated snapshot of a "
                          f"mutating page proves nothing)")
        if not (row.get("url") or "").startswith("http"):
            errors.append(f"{where}: url missing")

        rel = (row.get("path") or "").strip()
        if not rel:
            errors.append(f"{where}: empty path")
            continue
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{where}: snapshot not on disk ({rel})")
            continue
        blob = path.read_bytes()
        if hashlib.sha256(blob).hexdigest() != (row.get("sha256") or "").strip():
            errors.append(f"{where}: sha256 mismatch — the manifest does not describe the bytes on disk")
            continue
        if str(len(blob)) != (row.get("bytes") or "").strip():
            errors.append(f"{where}: byte count mismatch")
        try:
            chars = int((row.get("chars") or "0").strip())
        except ValueError:
            errors.append(f"{where}: chars is not an integer")
            continue
        if chars < GREY_MIN_CHARS:
            errors.append(f"{where}: only {chars} chars (< {GREY_MIN_CHARS}) — nav shell, not a document")

    missing_seeds = [s["key"] for s in GREY_TIER1 if s["key"] not in seen]
    if missing_seeds:
        errors.append(f"MANDATORY Tier-1 seed(s) absent: {missing_seeds}")

    for e in errors:
        print(f"RED: {e}")
    if errors:
        print(f"GREY GATE: RED — {len(errors)} problem(s)")
        return 1
    tier1 = sum(1 for r in rows if (r.get("tier") or "").strip() == "1")
    print(f"GREY GATE: PASS — {len(rows)} snapshot(s) verified ({tier1} Tier-1, all {len(GREY_TIER1)} "
          f"mandatory seeds present, sha256 + text >= {GREY_MIN_CHARS} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
