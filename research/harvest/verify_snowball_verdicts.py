#!/usr/bin/env python3
"""Deterministic gate for SNOWBALL screening verdicts (wave slots).

Checks, against the frozen law imported from screening_pass (never duplicated):
  1. every row of every batches/SNOWBALL/c*.verdict.csv passes validate_row;
  2. for every chunk named on --require, the verdict file EXISTS and its key
     set EXACTLY matches its input's key set (order-insensitive).
Exit 0 iff all green. Read-only; safe to re-run.

Usage: python3 verify_snowball_verdicts.py [--require c05,c06,...]
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import screening_pass as sp  # frozen law: validate_row + closed vocabularies

BATCHES = Path(__file__).resolve().parent.parent / "corpus/screening/batches/SNOWBALL"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require", default="", help="comma-separated chunk names whose verdicts must exist")
    args = ap.parse_args()

    bad: list[str] = []
    for vp in sorted(BATCHES.glob("c*.verdict.csv")):
        with vp.open() as fh:
            for row in csv.DictReader(fh):
                errs: list[str] = []
                if not sp.validate_row(row, errs):
                    bad.append(f"{vp.name}:{row.get('key')}: {'; '.join(errs)}")

    for name in [n.strip() for n in args.require.split(",") if n.strip()]:
        vp, ip = BATCHES / f"{name}.verdict.csv", BATCHES / f"{name}.input.jsonl"
        if not vp.exists():
            bad.append(f"{name}: verdict MISSING")
            continue
        with ip.open() as fh:
            in_keys = {json.loads(l)["key"] for l in fh if l.strip()}
        with vp.open() as fh:
            out_keys = {r["key"] for r in csv.DictReader(fh)}
        if in_keys != out_keys:
            bad.append(f"{name}: key mismatch (missing {sorted(in_keys - out_keys)[:5]}, "
                       f"extra {sorted(out_keys - in_keys)[:5]})")

    print(f"[verify_snowball_verdicts] invalid: {len(bad)}")
    for b in bad[:20]:
        print(f"  {b}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
