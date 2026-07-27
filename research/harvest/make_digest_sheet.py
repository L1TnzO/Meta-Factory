#!/usr/bin/env python3
"""make_digest_sheet.py — build/merge the §7.4 DIGEST sheet (SMS-v2).

Three subcommands (mirrors make_extraction_sheet.py one level down):
  build        read research/corpus/extraction/extraction.csv, keep the
               pdf_status == "ok" rows (the digest INPUT, §7.4), chunk them
               into research/corpus/digestion/batches/d<NN>.input.jsonl in a
               DETERMINISTIC priority order (rarest/most-MF-relevant facet
               first).
  add-external chunk digest INPUT records for externally-admitted keys (e.g.
               SPI-rescued keys) that were NOT part of `build`'s original
               pdf-ok universe when it last ran -- additive, never touches
               existing d<NN> chunks.
  merge        validate every batches/d*.verdict.jsonl record against
               digestion_law.validate_digest (abort — no writes — if ANY
               record is invalid) and write research/corpus/digestion/digest.jsonl.

Priority order (build): a paper's `priority_rank` is the index in
PRIORITY_FACETS of the FIRST priority facet present in its confirmed F (else
len(PRIORITY_FACETS)); ties break by `min_facet_scarcity` (the rarest of the
paper's confirmed F facets, measured as a global count over the pdf-ok rows
— rarer facet first); final tie-break by `key` (handoff 2026-07-18).

Paths are FIXED repo-relative constants (mirrors the extraction toolkit's
convention — no CLI path flags); tests monkeypatch these module attributes
to point at tmp_path fixtures instead of the real corpus.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import digestion_law  # noqa: E402  (frozen §7.4 law: schema + validate_digest)
import extraction_law  # noqa: E402  (frozen §7.6 law: VERDICT_COLUMNS, for add-external's completeness check)

ROOT = Path(__file__).resolve().parent.parent  # research/
EXTRACTION_CSV = ROOT / "corpus/extraction/extraction.csv"
DIGESTION_DIR = ROOT / "corpus/digestion"
BATCHES = DIGESTION_DIR / "batches"
DIGEST_JSONL = DIGESTION_DIR / "digest.jsonl"

CHUNK_SIZE = 6
# DATA constant (handoff 2026-07-18): these confirmed F facets are the MF
# differentiators — dig into them first regardless of global scarcity.
PRIORITY_FACETS = ["DOCS-VERSIONADO", "SEGURIDAD", "NEGATIVO"]

# Sentinel scarcity for a paper with an empty confirmed F (nothing to rank on).
_SCARCITY_SENTINEL = 10**9


# ---------------------------------------------------------------- helpers
def _facet_list(raw) -> list[str]:
    """Normalise a ';'-joined extraction cell (or a list already) to tokens,
    preserving first-seen order and dropping empties."""
    if isinstance(raw, list):
        tokens = [str(t).strip() for t in raw]
    else:
        tokens = str(raw or "").split(";")
    return [t for t in (tok.strip() for tok in tokens) if t]


def _global_facet_counts(rows: list[dict]) -> dict[str, int]:
    """A facet's count = # of `rows` whose confirmed F contains it."""
    counts: dict[str, int] = {}
    for r in rows:
        for f in set(_facet_list(r.get("F"))):
            counts[f] = counts.get(f, 0) + 1
    return counts


def _priority_rank(f_list: list[str]) -> int:
    fset = set(f_list)
    for i, p in enumerate(PRIORITY_FACETS):
        if p in fset:
            return i
    return len(PRIORITY_FACETS)


def _min_scarcity(f_list: list[str], counts: dict[str, int]) -> int:
    if not f_list:
        return _SCARCITY_SENTINEL
    return min(counts.get(f, _SCARCITY_SENTINEL) for f in f_list)


def _sort_key_fn(counts: dict[str, int]):
    def key(row: dict):
        f_list = _facet_list(row.get("F"))
        return (_priority_rank(f_list), _min_scarcity(f_list, counts), row["key"])
    return key


def _load_extraction() -> dict[str, dict]:
    if not EXTRACTION_CSV.exists():
        return {}
    with EXTRACTION_CSV.open(newline="", encoding="utf-8") as fh:
        return {r["key"]: r for r in csv.DictReader(fh)}


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


# ---------------------------------------------------------------- build
def cmd_build() -> int:
    if not EXTRACTION_CSV.exists():
        print(f"[build] {EXTRACTION_CSV} does not exist")
        return 1

    with EXTRACTION_CSV.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    ok_rows = [r for r in rows if r.get("pdf_status") == "ok"]

    counts = _global_facet_counts(ok_rows)
    ordered = sorted(ok_rows, key=_sort_key_fn(counts))

    BATCHES.mkdir(parents=True, exist_ok=True)
    for old in BATCHES.glob("d*.input.jsonl"):  # deterministic rebuild; NEVER touches *.verdict.jsonl
        old.unlink()

    n_chunks = 0
    for idx in range(0, len(ordered), CHUNK_SIZE):
        chunk = ordered[idx:idx + CHUNK_SIZE]
        n_chunks += 1
        path = BATCHES / f"d{n_chunks:02d}.input.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for r in chunk:
                key = r["key"]
                rec = {
                    "key": key,
                    "cita": r.get("cita", ""),
                    "operaciones": _facet_list(r.get("operaciones")),
                    "representacion": _facet_list(r.get("representacion")),
                    "F": _facet_list(r.get("F")),
                    "evidencia_tipo": _facet_list(r.get("evidencia_tipo")),
                    "plan_estado": r.get("plan_estado", ""),
                    "pdf": f"corpus/pdf/{key}.pdf",
                }
                assert set(rec.keys()) == set(digestion_law.INPUT_FIELDS)
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[build] {len(ok_rows)} pdf-ok row(s) -> {n_chunks} batch(es) in {BATCHES}")
    return 0


# ---------------------------------------------------------------- add-external
def _existing_input_chunk_numbers() -> list[int]:
    nums = []
    for p in BATCHES.glob("d*.input.jsonl"):
        stem = p.name[len("d"):-len(".input.jsonl")]
        if stem.isdigit():
            nums.append(int(stem))
    return nums


def cmd_add_external(keys_path: Path) -> int:
    """Chunk digest INPUT records for externally-admitted keys (e.g. the 13 SPI-rescued keys
    from extraction wave B) that were NOT part of cmd_build's original pdf-ok universe when it
    last ran. All-or-nothing; NEVER touches/deletes d01..d<max> (additive only). See module
    docstring + the digestion_law.INPUT_FIELDS shape for details."""
    try:
        keys = json.loads(keys_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[add-external] cannot read {keys_path}: {exc}")
        return 1
    if not isinstance(keys, list) or not all(isinstance(k, str) and k for k in keys):
        print(f"[add-external] {keys_path} must hold a flat JSON list of non-empty string keys")
        return 1

    ext_by_key = _load_extraction()

    not_ready = [k for k in keys if k not in ext_by_key or ext_by_key[k].get("pdf_status") != "ok"]
    if not_ready:
        print(f"[add-external] ABORT: {len(not_ready)} key(s) not pdf_status=ok in "
              f"{EXTRACTION_CSV}, 0 chunks written: {not_ready}")
        return 1

    incomplete = [
        k for k in keys
        if any(not str(ext_by_key[k].get(col, "")).strip() for col in extraction_law.VERDICT_COLUMNS[1:])
    ]
    if incomplete:
        print(f"[add-external] ABORT: {len(incomplete)} key(s) have an incomplete (un-verdicted) "
              f"extraction row, 0 chunks written: {incomplete}")
        return 1

    already_chunked: set[str] = set()
    for ip in BATCHES.glob("d*.input.jsonl"):
        already_chunked.update(r.get("key") for r in _read_jsonl(ip))
    collisions = [k for k in keys if k in already_chunked]
    if collisions:
        print(f"[add-external] ABORT: {len(collisions)} key(s) already chunked in an existing "
              f"d*.input.jsonl under {BATCHES}, 0 chunks written: {collisions}")
        return 1

    rows = [ext_by_key[k] for k in keys]
    counts = _global_facet_counts(rows)  # scoped to just these keys' own rows, not the full corpus
    ordered = sorted(rows, key=_sort_key_fn(counts))

    BATCHES.mkdir(parents=True, exist_ok=True)
    next_n = max(_existing_input_chunk_numbers(), default=0) + 1

    n_chunks = 0
    written: list[str] = []
    for idx in range(0, len(ordered), CHUNK_SIZE):
        chunk = ordered[idx:idx + CHUNK_SIZE]
        n = next_n + n_chunks
        n_chunks += 1
        path = BATCHES / f"d{n:02d}.input.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for r in chunk:
                key = r["key"]
                rec = {
                    "key": key,
                    "cita": r.get("cita", ""),
                    "operaciones": _facet_list(r.get("operaciones")),
                    "representacion": _facet_list(r.get("representacion")),
                    "F": _facet_list(r.get("F")),
                    "evidencia_tipo": _facet_list(r.get("evidencia_tipo")),
                    "plan_estado": r.get("plan_estado", ""),
                    "pdf": f"corpus/pdf/{key}.pdf",
                }
                assert set(rec.keys()) == set(digestion_law.INPUT_FIELDS)
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        written.append(path.name)

    print(f"[add-external] {len(rows)} key(s) -> {n_chunks} new batch(es) in {BATCHES}: {written}")
    return 0


# ---------------------------------------------------------------- merge
def cmd_merge() -> int:
    ext_by_key = _load_extraction()

    verdict_paths = sorted(BATCHES.glob("d*.verdict.jsonl"))
    if not verdict_paths:
        print("[merge] no d*.verdict.jsonl files found -- nothing to merge")
        return 0

    all_records: list[dict] = []
    errors: list[str] = []
    for vp in verdict_paths:
        chunk = vp.name[: -len(".verdict.jsonl")]
        records = _read_jsonl(vp)

        ip = BATCHES / f"{chunk}.input.jsonl"
        order: dict[str, int] = {}
        if ip.exists():
            order = {r.get("key"): i for i, r in enumerate(_read_jsonl(ip))}
        records.sort(key=lambda r: order.get(r.get("key"), len(order)))

        for rec in records:
            ext = ext_by_key.get(rec.get("key"), {})
            row_errors = digestion_law.validate_digest(rec, ext)
            if row_errors:
                errors.extend(f"{vp.name}: {e}" for e in row_errors)
        all_records.extend(records)

    if errors:
        print(f"[merge] ABORT: {len(errors)} violation(s), 0 written")
        for e in errors[:20]:
            print(f"  {e}")
        return 1

    DIGEST_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with DIGEST_JSONL.open("w", encoding="utf-8") as fh:
        for rec in all_records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[merge] wrote {len(all_records)} record(s) -> {DIGEST_JSONL}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="build digestion/batches/d<NN>.input.jsonl from pdf-ok extraction rows")
    p_add_external = sub.add_parser(
        "add-external",
        help="additively chunk digest input records for externally-admitted keys (e.g. SPI-rescued)",
    )
    p_add_external.add_argument("--keys", required=True, type=Path,
                                 help="JSON file holding a flat list of string keys")
    sub.add_parser("merge", help="validate + write digestion/digest.jsonl from d*.verdict.jsonl")
    args = ap.parse_args(argv)
    if args.cmd == "build":
        return cmd_build()
    if args.cmd == "add-external":
        return cmd_add_external(args.keys)
    return cmd_merge()


if __name__ == "__main__":
    raise SystemExit(main())
