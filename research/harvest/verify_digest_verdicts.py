#!/usr/bin/env python3
"""Deterministic gate for SMS-v2 DIGEST verdicts (protocol §7.4 FROZEN).

Mirrors verify_extraction_verdicts.py's structure, one level down but JSONL
instead of CSV: checks EVERY research/corpus/digestion/batches/d*.verdict.jsonl
chunk (or an explicit --require list, where a required-but-absent verdict
FAILS) against the frozen law imported from digestion_law (never duplicated):
the verdict key set equals its matching d<NN>.input.jsonl key set, and every
record passes validate_digest against its matching extraction.csv row (ground
truth). Exit 0 iff every checked chunk is green. Read-only; safe to re-run.

Usage: python3 verify_digest_verdicts.py [--require d01,d02,...]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import digestion_law  # noqa: E402  (frozen law: DIGEST_FIELDS + validate_digest)

ROOT = Path(__file__).resolve().parent.parent  # research/
BATCHES = ROOT / "corpus/digestion/batches"
EXTRACTION_CSV = ROOT / "corpus/extraction/extraction.csv"


def _load_extraction() -> dict[str, dict]:
    if not EXTRACTION_CSV.exists():
        return {}
    with EXTRACTION_CSV.open(newline="", encoding="utf-8") as fh:
        return {r["key"]: r for r in csv.DictReader(fh)}


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def _load_input_keys(ip: Path) -> set:
    return {r.get("key") for r in _read_jsonl(ip)}


def _check_chunk(name: str, ext_by_key: dict) -> tuple[list[str], int]:
    """Return (violations, record_count) for chunk `name` (empty errors == PASS)."""
    errors: list[str] = []
    vp, ip = BATCHES / f"{name}.verdict.jsonl", BATCHES / f"{name}.input.jsonl"
    if not vp.exists():
        return [f"{name}: verdict MISSING"], 0

    rows = _read_jsonl(vp)

    if not ip.exists():
        errors.append(f"{name}: no matching input {ip.name}")
    else:
        in_keys, out_keys = _load_input_keys(ip), {r.get("key") for r in rows}
        if in_keys != out_keys:
            errors.append(
                f"{name}: key mismatch (missing {sorted(in_keys - out_keys)[:5]}, "
                f"extra {sorted(out_keys - in_keys)[:5]})"
            )

    for row in rows:
        row_errors = digestion_law.validate_digest(row, ext_by_key.get(row.get("key"), {}))
        errors.extend(f"{name}:{row.get('key')}: {e}" for e in row_errors)
    return errors, len(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require", default="", help="comma-separated chunk names whose verdicts must exist")
    args = ap.parse_args(argv)

    ext_by_key = _load_extraction()

    required = [n.strip() for n in args.require.split(",") if n.strip()]
    if required:
        names = required
    else:
        names = sorted(p.name[: -len(".verdict.jsonl")] for p in BATCHES.glob("d*.verdict.jsonl"))

    bad = False
    for name in names:
        errors, n_rows = _check_chunk(name, ext_by_key)
        if errors:
            bad = True
            print(f"[gate] {name} FAIL:")
            for e in errors[:5]:
                print(f"  {e}")
        else:
            print(f"[gate] {name} PASS ({n_rows} rows)")
    if not names:
        print("[gate] no chunks to check")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
