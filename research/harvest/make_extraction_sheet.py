#!/usr/bin/env python3
"""make_extraction_sheet.py — build/merge the §7.6 EXTRACTION sheet (SMS-v2).

Two subcommands:
  build   read the INCLUIR rows of both screening sheets (main + snowball),
          write research/corpus/extraction/extraction.csv (identity columns
          filled, verdict columns empty) in a DETERMINISTIC priority order,
          then chunk the pdf_status=ok rows into
          research/corpus/extraction/batches/e<NN>.input.jsonl.
  merge   validate every batches/e*.verdict.csv row against extraction_law
          (abort — no writes — if ANY row is invalid) and fill the matching
          extraction.csv rows' verdict columns by key. Idempotent; refuses to
          silently overwrite an already-filled DIFFERING cell without
          --force. NEVER writes/deletes *.verdict.csv (those are the human/
          model deliverable, read-only from this tool's point of view).

Priority order (build): pdf_status=ok rows before missing ones, then by
SCARCITY_RANK (min rank over the row's F_screening facets — measured
2026-07-18 over the 487 confirmed INCLUIR rows: scarcer facets go first so
the rarest evidence gets extracted earliest), ties by year desc then key asc.

Paths are FIXED repo-relative constants (mirrors screening_pass.py's
convention — no CLI path flags); tests monkeypatch these module attributes
to point at tmp_path fixtures instead of the real corpus/sheets.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extraction_law  # noqa: E402  (frozen §7.6 law: schema + validate_row)

ROOT = Path(__file__).resolve().parent.parent  # research/
SCREENING_FULL = ROOT / "corpus/screening/screening_full.csv"
SCREENING_SNOWBALL = ROOT / "corpus/screening/screening_snowball.csv"
PDF_DIR = ROOT / "corpus/pdf"
CORPUS_JSONL = ROOT / "corpus/merged/corpus.jsonl"
SEEDS_JSONL = ROOT / "corpus/seeds/snowball-enriched.jsonl"
EXTRACTION_DIR = ROOT / "corpus/extraction"
EXTRACTION_CSV = EXTRACTION_DIR / "extraction.csv"
BATCHES = EXTRACTION_DIR / "batches"

CHUNK_SIZE = 6
# DATA constant (measured 2026-07-18 over the 487 confirmed INCLUIR rows):
# scarcer F_screening facets are dug into first.
SCARCITY_RANK = {
    "DOCS-VERSIONADO": 0, "SEGURIDAD": 1, "NEGATIVO": 2, "PROCEDIMENTAL": 3,
    "MULTIAGENTE": 4, "COSTO": 5, "FIDELIDAD": 6, "CONSOLIDACION": 7,
    "WRITE": 8, "RETRIEVAL-MEDIDO": 9, "no-facet": 99,
}


def record_key(rec: dict) -> str:
    """Mirrors download_pdfs.record_key / screening_pass.read_corpus's local
    re-implementation — the SAME identity scheme keys corpus.jsonl, the PDF
    manifest, and the screening sheets; never re-derive it differently."""
    for candidate in (rec.get("id"), rec.get("doi"), rec.get("arxiv_id"), rec.get("title")):
        if candidate:
            return re.sub(r"[^A-Za-z0-9._-]+", "_", str(candidate).split("/")[-1])[:120]
    return "unknown"


def _pdf_status(key: str) -> str:
    return "ok" if (PDF_DIR / f"{key}.pdf").exists() else "missing"


def _priority(f_screening: str) -> int:
    facets = [t for t in (f_screening or "").split(";") if t]
    if not facets:
        return SCARCITY_RANK["no-facet"]
    return min(SCARCITY_RANK.get(f, SCARCITY_RANK["no-facet"]) for f in facets)


def _read_inclusions() -> list[dict]:
    """Every INCLUIR* row of both screening sheets, tagged with its source."""
    rows: list[dict] = []
    for path, source in ((SCREENING_FULL, "main"), (SCREENING_SNOWBALL, "snowball")):
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if (row.get("decision") or "").startswith("INCLUIR"):
                    r = dict(row)
                    r["_source"] = source
                    rows.append(r)
    return rows


def _sheet_row(row: dict) -> dict:
    key = row.get("key", "")
    out = {
        "key": key, "source": row["_source"], "year": row.get("year", ""),
        "title": row.get("title", ""), "pdf_status": _pdf_status(key),
        "F_screening": row.get("F", ""),
    }
    for col in extraction_law.VERDICT_COLUMNS[1:]:
        out[col] = ""
    return out


def _load_corpus_abstracts() -> dict[str, str]:
    out: dict[str, str] = {}
    if not CORPUS_JSONL.exists():
        return out
    with CORPUS_JSONL.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            out[record_key(rec)] = rec.get("abstract") or ""
    return out


def _load_seed_abstracts() -> dict[str, str]:
    out: dict[str, str] = {}
    if not SEEDS_JSONL.exists():
        return out
    with SEEDS_JSONL.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            k = rec.get("key")
            if k:
                out[k] = rec.get("abstract") or ""
    return out


def _sort_key(row: dict):
    pdf_rank = 0 if row["pdf_status"] == "ok" else 1
    priority = _priority(row["F_screening"])
    try:
        year = int(row["year"] or 0)
    except ValueError:
        year = 0
    return (pdf_rank, priority, -year, row["key"])


def cmd_build(force: bool = False) -> int:
    if EXTRACTION_CSV.exists() and not force:
        print(f"[build] refusing to overwrite existing {EXTRACTION_CSV} (use --force)")
        return 1

    inclusions = _read_inclusions()
    incl_by_key = {r["key"]: r for r in inclusions}
    sheet_rows = sorted((_sheet_row(r) for r in inclusions), key=_sort_key)

    fieldnames = extraction_law.IDENTITY_COLUMNS + extraction_law.VERDICT_COLUMNS[1:]
    EXTRACTION_DIR.mkdir(parents=True, exist_ok=True)
    with EXTRACTION_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(sheet_rows)

    ok_rows = [r for r in sheet_rows if r["pdf_status"] == "ok"]
    corpus_abs = _load_corpus_abstracts()
    seed_abs = _load_seed_abstracts()

    BATCHES.mkdir(parents=True, exist_ok=True)
    for old in BATCHES.glob("e*.input.jsonl"):  # deterministic rebuild; NEVER touches *.verdict.csv
        old.unlink()

    n_chunks = 0
    for idx in range(0, len(ok_rows), CHUNK_SIZE):
        chunk = ok_rows[idx:idx + CHUNK_SIZE]
        n_chunks += 1
        path = BATCHES / f"e{n_chunks:02d}.input.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for r in chunk:
                key = r["key"]
                abstract = (
                    corpus_abs.get(key)
                    or seed_abs.get(key)
                    or incl_by_key.get(key, {}).get("abstract_400", "")
                )
                fh.write(json.dumps({
                    "key": key, "title": r["title"], "year": r["year"],
                    "abstract": abstract, "F_screening": r["F_screening"],
                    "pdf": f"corpus/pdf/{key}.pdf",
                }, ensure_ascii=False) + "\n")

    print(f"[build] {len(sheet_rows)} rows -> {EXTRACTION_CSV} "
          f"({len(ok_rows)} pdf-ok chunked into {n_chunks} batch(es))")
    return 0


def cmd_merge(force: bool = False) -> int:
    if not EXTRACTION_CSV.exists():
        print(f"[merge] {EXTRACTION_CSV} does not exist -- run build first")
        return 1

    verdict_paths = sorted(BATCHES.glob("e*.verdict.csv"))
    if not verdict_paths:
        print("[merge] no e*.verdict.csv files found -- nothing to merge")
        return 0

    verdict_rows: list[dict] = []
    errors: list[str] = []
    for vp in verdict_paths:
        with vp.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                row_errors = extraction_law.validate_row(row)
                if row_errors:
                    errors.extend(f"{vp.name}: {e}" for e in row_errors)
                else:
                    verdict_rows.append(row)
    if errors:
        print(f"[merge] ABORT: {len(errors)} invalid verdict row(s), 0 applied")
        for e in errors[:20]:
            print(f"  {e}")
        return 1

    with EXTRACTION_CSV.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        sheet_rows = list(reader)
    by_key = {r["key"]: r for r in sheet_rows}
    verdict_cols = extraction_law.VERDICT_COLUMNS[1:]

    unknown: list[str] = []
    conflicts: list[str] = []
    for v in verdict_rows:
        target = by_key.get(v["key"])
        if target is None:
            unknown.append(v["key"])
            continue
        for col in verdict_cols:
            new_val, old_val = v.get(col, ""), target.get(col, "")
            if old_val and old_val != new_val and not force:
                conflicts.append(f"{v['key']}.{col}: existing {old_val!r} != new {new_val!r}")

    if unknown:
        print(f"[merge] ABORT: {len(unknown)} verdict row(s) with unknown key: {unknown[:10]}")
        return 1
    if conflicts:
        print(f"[merge] ABORT: {len(conflicts)} conflicting cell(s) (use --force to override)")
        for c in conflicts[:20]:
            print(f"  {c}")
        return 1

    for v in verdict_rows:
        target = by_key[v["key"]]
        for col in verdict_cols:
            target[col] = v.get(col, "")

    with EXTRACTION_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(sheet_rows)

    filled = sum(1 for r in sheet_rows if all((r.get(c) or "").strip() for c in verdict_cols))
    print(f"[merge] filled {filled}/{len(sheet_rows)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_build = sub.add_parser("build", help="build extraction.csv + input chunks from INCLUIR rows")
    p_build.add_argument("--force", action="store_true", help="overwrite an existing extraction.csv")
    p_merge = sub.add_parser("merge", help="validate + apply e*.verdict.csv into extraction.csv")
    p_merge.add_argument("--force", action="store_true", help="overwrite an already-filled differing cell")
    args = ap.parse_args(argv)
    if args.cmd == "build":
        return cmd_build(force=args.force)
    return cmd_merge(force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
