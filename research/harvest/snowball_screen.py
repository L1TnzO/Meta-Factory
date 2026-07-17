#!/usr/bin/env python3
"""snowball_screen.py — screening driver for SMS-v2 snowball candidates.

Composes ONE screening sheet from three inputs: the ranked snowball candidate
list (backward/forward citation harvest), the OpenAlex enrichment (title/doi/
year/abstract fill), and the 9 v1 records that were manually screened before
v2 existed (their frozen v1 verdicts are pre-merged, re-validated against the
CURRENT frozen rubric so they can never silently drift out of the closed
vocabulary). Three deterministic PRE-DECISIONS (duplicate title, out-of-scope
year, dead/merged OpenAlex id) are applied so the model never wastes a verdict
on rows a human wouldn't want to see either. Everything else follows the same
slice -> merge -> queues -> status shape as sibling screening_pass.py, reusing
its FROZEN validate_row gate instead of duplicating the rubric arithmetic.

Subcommands
  build [--force] [--dry-run]   compose the sheet (refuses to clobber decisions)
  slice                         emit BATCHES/cNN.input.jsonl chunks for pending rows
  merge [paths...]              validate verdict CSVs and apply to the sheet (idempotent)
  queues [--quiet]              regenerate GRIS + 10% sample human-verification queues
  status                        pending rows, chunks awaiting a verdict, decided distribution

State model: the committed SHEET is the state. All writes are ATOMIC (tmp file
in the same directory + os.replace). All paths are derived from
ROOT = Path(__file__).resolve().parent.parent (research/), never from cwd.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from screening_pass import (  # noqa: E402  (frozen law — never duplicate)
    DECISIONS,
    DECISIONS_CATEGORICAL,
    DECISIONS_SCORED,
    FACETS,
    VERDICT_FIELDS,
    validate_row,
)

ROOT = Path(__file__).resolve().parent.parent  # research/
SHEET = ROOT / "corpus/screening/screening_snowball.csv"
BATCHES = ROOT / "corpus/screening/batches/SNOWBALL"
QUEUES = ROOT / "corpus/screening/queues"
CANDIDATES = ROOT / "corpus/seeds/snowball-candidates.csv"
ENRICHED = ROOT / "corpus/seeds/snowball-enriched.jsonl"
V1SCREEN = ROOT / "corpus/seeds/v1-manual-screen.jsonl"
V1VERDICT = ROOT / "corpus/screening/batches/V1/c00.verdict.csv"
CHUNK_SIZE = 25

SHEET_FIELDS = [
    "key", "origin", "backward_n", "forward_n", "total", "year", "doi", "title",
    "abstract_400", "M", "T", "E", "F", "se", "selfpub", "artefacto", "decision", "notes",
]
QUEUE_FIELDS = ["key", "origin", "total", "year", "title", "abstract_400", "decision", "notes"]

# The three synthetic pre-decision labels this driver mints itself — never
# part of the frozen rubric vocabulary (screening_pass.DECISIONS), so a
# GRIS/CE-4p/etc. row can never be mistaken for one and vice versa.
PRE_DECISIONS = {"DUPLICADO-INTRA", "FUERA-ALCANCE", "SIN-METADATOS"}
assert not PRE_DECISIONS & DECISIONS, "pre-decision labels collide with the frozen rubric vocabulary"

NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
NEWLINE_RE = re.compile(r"[\r\n]+")
GOLD_MANUAL_PREFIX = "gold-manual:"


# --------------------------------------------------------------------------
# Pure helpers
# --------------------------------------------------------------------------

def normalize_title(title: str) -> str:
    return NON_ALNUM_RE.sub(" ", (title or "").lower()).strip()


def collapse_abstract_400(abstract: str) -> str:
    """First 400 chars of the abstract, newlines collapsed to spaces."""
    return NEWLINE_RE.sub(" ", abstract or "")[:400]


# --------------------------------------------------------------------------
# I/O helpers (atomic writes — no partial file is ever visible)
# --------------------------------------------------------------------------

def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.tmp"
    tmp.write_text(text, encoding="utf-8")
    os.replace(str(tmp), str(path))


def atomic_write_csv(path: Path, fieldnames: list, rows: list) -> None:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    atomic_write_text(path, buf.getvalue())


def read_sheet() -> list[dict]:
    with SHEET.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_sheet(rows: list[dict]) -> None:
    atomic_write_csv(SHEET, SHEET_FIELDS, rows)


def _load_enriched() -> dict:
    out = {}
    if not ENRICHED.exists():
        return out
    with ENRICHED.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            out[rec["key"]] = rec
    return out


def _load_v1_screen() -> list[dict]:
    out = []
    with V1SCREEN.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _load_v1_verdicts() -> dict:
    with V1VERDICT.open(newline="", encoding="utf-8") as fh:
        return {row["key"]: row for row in csv.DictReader(fh)}


def full_abstracts() -> dict:
    """key -> FULL abstract text (never the 400-char cut), from ENRICHED +
    V1SCREEN. Used by slice — the sheet only carries abstract_400."""
    out = {key: (rec.get("abstract") or "") for key, rec in _load_enriched().items()}
    for rec in _load_v1_screen():
        out[rec["key"]] = rec.get("abstract") or ""
    return out


def _new_row(key: str, origin: str, backward_n: str, forward_n: str, total: str,
             year: str, doi: str, title: str, abstract: str) -> dict:
    return {
        "key": key, "origin": origin,
        "backward_n": backward_n, "forward_n": forward_n, "total": total,
        "year": year, "doi": doi, "title": title,
        "abstract_400": collapse_abstract_400(abstract),
        "M": "", "T": "", "E": "", "F": "", "se": "", "selfpub": "", "artefacto": "",
        "decision": "", "notes": "",
    }


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------

def apply_pre_decisions(rows: list[dict]) -> None:
    """Mutates rows in place, in the frozen order: intra-duplicate title ->
    out-of-scope year -> no title/no abstract. Only touches rows still
    undecided (v1 rows are already decided by the time this runs)."""
    # (1) intra-candidate duplicate by normalized title.
    groups: dict[str, list[dict]] = {}
    for r in rows:
        if r["decision"]:
            continue
        nt = normalize_title(r["title"])
        if not nt:
            continue
        groups.setdefault(nt, []).append(r)
    for group in groups.values():
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda r: (-int(r["total"] or 0), r["key"]))
        keep = ordered[0]
        for r in ordered[1:]:
            r["decision"] = "DUPLICADO-INTRA"
            r["notes"] = f"duplicado de {keep['key']}"

    # (2) out-of-scope year.
    for r in rows:
        if r["decision"]:
            continue
        y = (r["year"] or "").strip()
        if not y:
            continue
        try:
            yi = int(y)
        except ValueError:
            continue
        if yi < 2022:
            r["decision"] = "FUERA-ALCANCE"
            r["notes"] = "fuera de alcance de busqueda congelado (2022+)"

    # (3) no title AND no abstract (enrich miss / dead-or-merged id).
    for r in rows:
        if r["decision"]:
            continue
        if not (r["title"] or "").strip() and not (r["abstract_400"] or "").strip():
            r["decision"] = "SIN-METADATOS"
            r["notes"] = "OpenAlex sin metadatos (id muerto/fusionado)"


def build_rows() -> tuple[list[dict], int]:
    """Assemble sheet rows (candidates + v1) and apply the deterministic
    pre-decisions. Pure w.r.t. the sheet — reads CANDIDATES/ENRICHED/
    V1SCREEN/V1VERDICT only, never touches SHEET. Returns (rows, v1_premerged)."""
    enriched = _load_enriched()

    rows: list[dict] = []
    with CANDIDATES.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            seeds = r.get("seeds_sample") or ""
            origin = "gold-manual" if seeds.startswith(GOLD_MANUAL_PREFIX) else "snowball"
            key = r["wid"]
            enr = enriched.get(key, {})
            title = (r.get("title") or "").strip() or (enr.get("title") or "")
            doi = (r.get("doi") or "").strip() or (enr.get("doi") or "")
            year = (r.get("year") or "").strip()
            if not year and enr.get("year"):
                year = str(enr["year"])
            abstract = enr.get("abstract") or ""
            rows.append(_new_row(
                key, origin, r.get("backward_n") or "", r.get("forward_n") or "",
                r.get("total") or "", year, doi, title, abstract,
            ))

    v1_verdicts = _load_v1_verdicts()
    v1_premerged = 0
    for rec in _load_v1_screen():
        key = rec["key"]
        row = _new_row(
            key, "v1", "", "", "",
            str(rec.get("year") or ""), "", rec.get("title") or "", rec.get("abstract") or "",
        )
        verdict = v1_verdicts.get(key)
        if verdict is None:
            raise SystemExit(f"snowball_screen build: missing V1 verdict for v1 key {key!r}")
        errors: list[str] = []
        if not validate_row(verdict, errors):
            raise SystemExit(f"snowball_screen build: invalid V1 verdict for {key!r}: {errors}")
        for col in VERDICT_FIELDS:
            if col == "key":
                continue
            row[col] = (verdict.get(col) or "").strip()
        v1_premerged += 1
        rows.append(row)

    apply_pre_decisions(rows)
    return rows, v1_premerged


def cmd_build(force: bool = False, dry_run: bool = False) -> int:
    if SHEET.exists() and not dry_run:
        existing = list(csv.DictReader(SHEET.open(newline="", encoding="utf-8")))
        if any((r.get("decision") or "").strip() for r in existing) and not force:
            print(f"[snowball_screen] REFUSE: {SHEET} already has decisions "
                  "— pass --force to overwrite", file=sys.stderr)
            return 2

    rows, v1_premerged = build_rows()
    pre_counts = Counter(r["decision"] for r in rows if r["decision"] in PRE_DECISIONS)
    pending = sum(1 for r in rows if not r["decision"])

    print(f"[snowball_screen] build: total={len(rows)} rows")
    for name in ("DUPLICADO-INTRA", "FUERA-ALCANCE", "SIN-METADATOS"):
        print(f"  {name}: {pre_counts.get(name, 0)}")
    print(f"  v1 pre-merged: {v1_premerged}")
    print(f"  pending: {pending}")

    if dry_run:
        print("[snowball_screen] --dry-run: no write")
        return 0

    write_sheet(rows)
    print(f"[snowball_screen] wrote {SHEET}")
    return 0


# --------------------------------------------------------------------------
# slice
# --------------------------------------------------------------------------

def cmd_slice() -> int:
    rows = read_sheet()
    pending = [r for r in rows if not (r.get("decision") or "").strip()]
    # Stable multi-pass sort: total desc (primary), year desc/empty-last
    # (secondary), key asc (tertiary) — each pass stable-preserves the prior.
    pending.sort(key=lambda r: r["key"])
    pending.sort(key=lambda r: r.get("year") or "", reverse=True)
    pending.sort(key=lambda r: int(r.get("total") or 0), reverse=True)

    abstracts = full_abstracts()
    BATCHES.mkdir(parents=True, exist_ok=True)
    n_chunks = 0
    n_records = 0
    for i in range(0, len(pending), CHUNK_SIZE):
        chunk = pending[i:i + CHUNK_SIZE]
        path = BATCHES / f"c{i // CHUNK_SIZE:02d}.input.jsonl"
        n_chunks += 1
        n_records += len(chunk)
        if path.exists():
            continue  # stable chunking across re-runs — never rewrite
        lines = []
        for r in chunk:
            lines.append(json.dumps({
                "key": r["key"],
                "title": r.get("title") or "",
                "abstract": abstracts.get(r["key"], ""),
                "year": r.get("year") or "",
                "venue": "",
                "sources": r.get("origin") or "",
                "has_pdf": 0,
                "pdf": "",
            }, ensure_ascii=False))
        atomic_write_text(path, "".join(ln + "\n" for ln in lines))

    print(f"[snowball_screen] slice: {n_chunks} chunks, {n_records} records")
    return 0


# --------------------------------------------------------------------------
# merge
# --------------------------------------------------------------------------

def cmd_merge(paths: list[str] | None = None) -> int:
    rows = read_sheet()
    by_key = {r["key"]: r for r in rows}

    verdict_paths = [Path(p) for p in paths] if paths else sorted(BATCHES.glob("c*.verdict.csv"))

    verdicts = []
    for p in verdict_paths:
        with Path(p).open(newline="", encoding="utf-8") as fh:
            verdicts.extend(csv.DictReader(fh))

    merged = skipped = rejected = 0
    errors: list[str] = []
    for v in verdicts:
        key = v.get("key", "?")
        target = by_key.get(key)
        if target is None:
            errors.append(f"{key}: unknown key (not in sheet)")
            rejected += 1
            continue
        if (target.get("decision") or "").strip():
            skipped += 1
            continue
        row_errors: list[str] = []
        if not validate_row(v, row_errors):
            errors.extend(row_errors)
            rejected += 1
            continue
        for col in VERDICT_FIELDS:
            if col == "key":
                continue
            target[col] = (v.get(col) or "").strip()
        merged += 1

    if merged:
        write_sheet(rows)

    dist = Counter(r["decision"] for r in rows if r["decision"])
    print(f"[snowball_screen] merge: merged={merged} skipped(already-decided)={skipped} "
          f"rejected={rejected}")
    if errors:
        print("  REJECTS:")
        for e in errors:
            print(f"   - {e}")
    print(f"  distribution: {dict(dist)}")
    return 1 if rejected else 0


# --------------------------------------------------------------------------
# queues
# --------------------------------------------------------------------------

def cmd_queues(quiet: bool = False) -> int:
    rows = read_sheet()
    QUEUES.mkdir(parents=True, exist_ok=True)

    gris_rows = [r for r in rows if r.get("decision") in ("GRIS", "CE-4p")]

    def in_sample10(r: dict) -> bool:
        dec = (r.get("decision") or "").strip()
        if not dec or dec in PRE_DECISIONS or r.get("origin") == "v1":
            return False
        return int(hashlib.sha256(r["key"].encode()).hexdigest(), 16) % 10 == 0

    sample_rows = [r for r in rows if in_sample10(r)]

    atomic_write_csv(QUEUES / "SNOWBALL-GRIS.csv", QUEUE_FIELDS, gris_rows)
    atomic_write_csv(QUEUES / "SNOWBALL-SAMPLE10.csv", QUEUE_FIELDS, sample_rows)

    if not quiet:
        print(f"[snowball_screen] queues: SNOWBALL-GRIS.csv={len(gris_rows)} "
              f"SNOWBALL-SAMPLE10.csv={len(sample_rows)}")
    return 0


# --------------------------------------------------------------------------
# status
# --------------------------------------------------------------------------

def cmd_status() -> int:
    rows = read_sheet()
    pending = sum(1 for r in rows if not (r.get("decision") or "").strip())
    dist = Counter(r["decision"] for r in rows if r.get("decision"))
    print(f"[snowball_screen] pending: {pending}/{len(rows)}")
    print(f"  decided distribution: {dict(dist)}")

    if BATCHES.exists():
        inputs = sorted(BATCHES.glob("c*.input.jsonl"))
        verdict_stems = {p.name[:-len(".verdict.csv")] for p in BATCHES.glob("c*.verdict.csv")}
        missing = [p for p in inputs if p.name[:-len(".input.jsonl")] not in verdict_stems]
        print(f"  chunks with input but no verdict: {len(missing)}")
        for p in missing:
            print(f"   - {p.name}")
    else:
        print("  chunks with input but no verdict: 0")
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="snowball_screen.py", description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    p_build = sub.add_parser("build")
    p_build.add_argument("--force", action="store_true")
    p_build.add_argument("--dry-run", action="store_true")

    sub.add_parser("slice")

    p_merge = sub.add_parser("merge")
    p_merge.add_argument("paths", nargs="*")

    p_queues = sub.add_parser("queues")
    p_queues.add_argument("--quiet", action="store_true")

    sub.add_parser("status")
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_arg_parser()
    args = ap.parse_args(argv)
    if args.cmd == "build":
        return cmd_build(force=args.force, dry_run=args.dry_run)
    if args.cmd == "slice":
        return cmd_slice()
    if args.cmd == "merge":
        return cmd_merge(args.paths)
    if args.cmd == "queues":
        return cmd_queues(quiet=args.quiet)
    if args.cmd == "status":
        return cmd_status()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
