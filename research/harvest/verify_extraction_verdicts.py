#!/usr/bin/env python3
"""Deterministic gate for SMS-v2 EXTRACTION verdicts (protocol §7.6 FROZEN).

Mirrors verify_snowball_verdicts.py's structure, one level down: checks EVERY
research/corpus/extraction/batches/e*.verdict.csv chunk (or an explicit
--require list, where a required-but-absent verdict FAILS) against the
frozen law imported from extraction_law (never duplicated): the header is
EXACTLY VERDICT_COLUMNS, the verdict key set equals its matching
e<NN>.input.jsonl key set, and every row passes validate_row. Exit 0 iff
every checked chunk is green. Read-only; safe to re-run.

Usage: python3 verify_extraction_verdicts.py [--require e01,e02,...]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extraction_law  # noqa: E402  (frozen law: VERDICT_COLUMNS + validate_row)

BATCHES = Path(__file__).resolve().parent.parent / "corpus/extraction/batches"


def _load_input_keys(ip: Path) -> set:
    with ip.open(encoding="utf-8") as fh:
        return {json.loads(ln)["key"] for ln in fh if ln.strip()}


def _check_chunk(name: str) -> tuple[list[str], int]:
    """Return (violations, row_count) for chunk `name` (empty errors == PASS)."""
    errors: list[str] = []
    vp, ip = BATCHES / f"{name}.verdict.csv", BATCHES / f"{name}.input.jsonl"
    if not vp.exists():
        return [f"{name}: verdict MISSING"], 0

    with vp.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        rows = list(reader)

    if header != extraction_law.VERDICT_COLUMNS:
        errors.append(f"{name}: header mismatch (got {header})")

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
        row_errors = extraction_law.validate_row(row)
        errors.extend(f"{name}:{row.get('key')}: {e}" for e in row_errors)
    return errors, len(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require", default="", help="comma-separated chunk names whose verdicts must exist")
    args = ap.parse_args(argv)

    required = [n.strip() for n in args.require.split(",") if n.strip()]
    if required:
        names = required
    else:
        names = sorted(p.name[: -len(".verdict.csv")] for p in BATCHES.glob("e*.verdict.csv"))

    bad = False
    for name in names:
        errors, n_rows = _check_chunk(name)
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
