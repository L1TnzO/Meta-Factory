#!/usr/bin/env python3
"""Deterministic gate for the PDF rescue of protocol §9.3 (the 65 INCLUIR without local PDF).

Trust-chain: written by the orchestrator, NOT by the slot it judges. A rescue is only real if the
claimed file is ON DISK, is a genuine PDF, hashes to what the manifest says, and yields enough
extractable text to be digestible. Anything else is a claim, not a rescue.

Usage:
    python3 harvest/verify_rescue.py --manifest .gen/rescue/rescued.csv [--min N]

Exit 0 only if every claimed row verifies AND at least --min rows are claimed.
Read-only: it never writes, downloads or repairs anything.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import closure_law  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent  # research/
PDF_DIR = ROOT / "corpus/pdf"
MIN_CHARS = 2000  # a scanned/paywalled stub extracts far less; the digestor needs real text
REQUIRED = ["key", "url", "strategy", "sha256", "bytes", "chars"]


def eligible_keys() -> set[str]:
    """The ONLY keys a rescue may claim: INCLUIR rows that had no local PDF (re-derived, not trusted)."""
    keys: set[str] = set()
    for sheet in ("corpus/screening/screening_full.csv", "corpus/screening/screening_snowball.csv"):
        with (ROOT / sheet).open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                if (row.get("decision") or "").strip().upper().startswith("INCLUIR"):
                    keys.add(row["key"])
    return keys


def missing_at_open() -> set[str]:
    """Keys that were pdf_status=missing in the FROZEN extraction sheet (the rescue's universe)."""
    out: set[str] = set()
    with (ROOT / "corpus/extraction/extraction.csv").open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("pdf_status") != "ok":
                out.add(row["key"])
    return out


def spi_admitted() -> set[str]:
    """Second universe (§9.2): studies the SPI ADMITTED where pass 1 had abstained.

    These are INCLUIR rows that by construction never reached extraction.csv, so `missing_at_open()`
    cannot see them — yet they are exactly the papers whose full text the corpus now needs. The set is
    derived ONLY from committed verdicts in adjudication queues, never from what is on disk: a universe
    that shrank as the rescue succeeded would make this gate vacuous on its own second run.
    """
    out: set[str] = set()
    batches = ROOT / "corpus/spi/batches"
    if not batches.exists():
        return out
    for qdir in sorted(p for p in batches.iterdir() if p.is_dir()):
        if closure_law.QUEUES.get(qdir.name, None) is None:
            continue
        if closure_law.QUEUES[qdir.name].kind != closure_law.KIND_ADJUDICACION:
            continue
        for f in sorted(qdir.glob("q*.verdict.jsonl")):
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if (row.get("decision") or "").strip() in closure_law.IN_LABELS:
                    out.add(row["key"])
    return out


def pdf_chars(path: Path) -> int:
    try:
        res = subprocess.run(
            ["pdftotext", "-q", str(path), "-"], capture_output=True, timeout=120, check=False
        )
        return len(res.stdout.decode("utf-8", "replace").strip())
    except Exception:  # noqa: BLE001 — any failure means "not extractable", which is the verdict
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--min", type=int, default=0)
    args = ap.parse_args()

    if not args.manifest.exists():
        print(f"RED: manifest not found: {args.manifest}")
        return 1

    with args.manifest.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        rows = list(reader)

    errors: list[str] = []
    for col in REQUIRED:
        if col not in header:
            errors.append(f"manifest header missing column: {col}")
    if errors:
        for e in errors:
            print(f"RED: {e}")
        return 1

    universe = (eligible_keys() & missing_at_open()) | spi_admitted()
    seen: set[str] = set()
    ok = 0

    for i, row in enumerate(rows, 1):
        key = (row.get("key") or "").strip()
        where = f"row {i} (key={key or '?'})"
        if not key:
            errors.append(f"{where}: empty key")
            continue
        if key in seen:
            errors.append(f"{where}: duplicated key in manifest")
            continue
        seen.add(key)
        if key not in universe:
            errors.append(f"{where}: key is not an INCLUIR that was missing a PDF (out of universe)")
            continue

        path = PDF_DIR / f"{key}.pdf"
        if not path.exists():
            errors.append(f"{where}: claimed rescued but {path.name} is not on disk")
            continue
        blob = path.read_bytes()
        if not blob.startswith(b"%PDF"):
            errors.append(f"{where}: {path.name} is not a PDF (bad magic — landing page?)")
            continue
        digest = hashlib.sha256(blob).hexdigest()
        if digest != (row.get("sha256") or "").strip():
            errors.append(f"{where}: sha256 mismatch (manifest lies about the bytes on disk)")
            continue
        if str(len(blob)) != (row.get("bytes") or "").strip():
            errors.append(f"{where}: byte count mismatch")
            continue
        chars = pdf_chars(path)
        if chars < MIN_CHARS:
            errors.append(f"{where}: only {chars} extractable chars (< {MIN_CHARS}) — not digestible")
            continue
        ok += 1

    for e in errors:
        print(f"RED: {e}")
    if errors:
        print(f"RESCUE GATE: RED — {len(errors)} problem(s), {ok} verified")
        return 1
    if ok < args.min:
        print(f"RESCUE GATE: RED — only {ok} verified rescues, floor is {args.min}")
        return 1
    print(f"RESCUE GATE: PASS — {ok} rescued PDF(s) verified on disk (sha256 + text >= {MIN_CHARS} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
