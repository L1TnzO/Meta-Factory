#!/usr/bin/env python3
"""make_spi_sheet.py -- build the SPI (second independent pass) BLIND inputs, protocol §9.

One subcommand:
  build   for every queue in closure_law.QUEUES (or just --queue NAME), re-derive its members via
          closure_law.queue_members() and chunk them by closure_law.CHUNK_SIZE into
          research/corpus/spi/batches/<QUEUE>/q<NN>.input.jsonl (NN zero-padded from 01).

Blindness is enforced by CONSTRUCTION, not by filtering: each row builder below whitelists the exact
handful of fields the reader needs (never `dict(row)` then delete the bad ones), so a pass-1 output
column can only reach the input if someone deliberately adds it to a whitelist -- and the assertion in
`_assert_blind()` (imported check against `closure_law.BLIND_FORBIDDEN`, never restated) catches even
that. `verify_spi_verdicts.py --inputs-only` re-checks the same thing from the outside, on disk.

Per KIND (never per queue -- the queues that share a kind share a row shape, §9.1):
  MEMBERSHIP (VERIFICACION/CONFIRMACION/ADJUDICACION): {key, title, abstract, year, pdf?}
  CALIDAD:    {key, title, senal_calidad, pdf?} -- senal_calidad is the source row's own `notes`
              (extraction/digestion already wrote the RECONSIDERAR flag + its reasoning there; this
              queue's whole job is to adjudicate that text, so it travels renamed, never as `notes`).
  IDENTIDAD:  {key(=key_a), pareja(=key_b), title_a, title_b, year_a, year_b, similarity, pdf_a?, pdf_b?}

`pdf`/`pdf_a`/`pdf_b` are included ONLY when `corpus/pdf/<key>.pdf` exists on disk -- never a dangling
reference.

Idempotent-safe by default: a queue whose batches already exist is left alone (protects a reader who has
already started answering some chunks from a silent re-chunking); pass --force to rebuild it (this NEVER
touches `*.verdict.jsonl`, the reader's deliverable).

Paths are FIXED repo-relative constants (mirrors make_digest_sheet.py's convention -- no CLI path
flags); tests monkeypatch these module attributes (and closure_law's own source-sheet constants) to
point at tmp_path fixtures instead of the real corpus/sheets.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import closure_law  # noqa: E402  (single-source law: queues, kinds, CHUNK_SIZE, BLIND_FORBIDDEN, ROOT)

PDF_DIR = closure_law.ROOT / "corpus/pdf"
BATCHES = closure_law.SPI_DIR / "batches"


# --------------------------------------------------------------------------- I/O (atomic, mirrors snowball.py)
def _atomic_write_text(path: Path, text: str) -> None:
    """Write a tmp file in the same dir, then os.replace -- no partial file is ever visible under the
    target path, and no tmp file survives a crash mid-write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.tmp"
    tmp.write_text(text, encoding="utf-8")
    os.replace(str(tmp), str(path))


def _atomic_write_jsonl(path: Path, rows: list[dict]) -> None:
    import json
    buf = io.StringIO()
    for r in rows:
        buf.write(json.dumps(r, ensure_ascii=False))
        buf.write("\n")
    _atomic_write_text(path, buf.getvalue())


# --------------------------------------------------------------------------- row builders (per KIND)
def _pdf_rel(key: str) -> str | None:
    if not key or not (PDF_DIR / f"{key}.pdf").exists():
        return None
    return f"corpus/pdf/{key}.pdf"


def _row_membership(r: dict) -> dict:
    key = r["key"]
    out = {"key": key, "title": r.get("title", ""), "abstract": r.get("abstract_400", ""),
           "year": r.get("year", "")}
    pdf = _pdf_rel(key)
    if pdf:
        out["pdf"] = pdf
    return out


def _row_calidad(r: dict) -> dict:
    key = r["key"]
    # Extraction rows carry `title`; digest rows don't (they carry `cita` instead) -- fall back to it
    # rather than special-case by source, since the KIND (not the queue) determines the row shape.
    title = r.get("title") or r.get("cita", "")
    out = {"key": key, "title": title, "senal_calidad": r.get("notes", "")}
    pdf = _pdf_rel(key)
    if pdf:
        out["pdf"] = pdf
    return out


def _row_identidad(r: dict) -> dict:
    key, pareja = r["key_a"], r["key_b"]
    out = {
        "key": key, "pareja": pareja,
        "title_a": r.get("title_a", ""), "title_b": r.get("title_b", ""),
        "year_a": r.get("year_a", ""), "year_b": r.get("year_b", ""),
        "similarity": r.get("similarity", ""),
    }
    pdf_a = _pdf_rel(key)
    if pdf_a:
        out["pdf_a"] = pdf_a
    pdf_b = _pdf_rel(pareja)
    if pdf_b:
        out["pdf_b"] = pdf_b
    return out


_ROW_BUILDERS = {
    closure_law.KIND_VERIFICACION: _row_membership,
    closure_law.KIND_CONFIRMACION: _row_membership,
    closure_law.KIND_ADJUDICACION: _row_membership,
    closure_law.KIND_CALIDAD: _row_calidad,
    closure_law.KIND_IDENTIDAD: _row_identidad,
}


def _assert_blind(name: str, row: dict) -> None:
    leaked = set(row) & set(closure_law.BLIND_FORBIDDEN)
    if leaked:
        raise AssertionError(f"{name}: builder leaked forbidden column(s) {sorted(leaked)} -- refusing to write")


# --------------------------------------------------------------------------- build
def build_queue(name: str, force: bool) -> tuple[int, int, bool]:
    """Returns (n_members, n_chunks, skipped). `skipped` is True iff the queue already had batches on
    disk and `force` was not given (the queue is left untouched)."""
    q = closure_law.QUEUES[name]
    builder = _ROW_BUILDERS[q.kind]
    qdir = BATCHES / name

    already = sorted(qdir.glob("q*.input.jsonl")) if qdir.exists() else []
    if already and not force:
        print(f"[make_spi_sheet] {name}: {len(already)} chunk(s) already built, "
              f"refusing to overwrite (use --force)")
        return (0, 0, True)

    qdir.mkdir(parents=True, exist_ok=True)
    for old in already:  # deterministic rebuild; NEVER touches *.verdict.jsonl
        old.unlink()

    chunks = closure_law.queue_chunks(name)
    for idx, chunk in enumerate(chunks, start=1):
        rows = [builder(r) for r in chunk]
        for row in rows:
            _assert_blind(name, row)
        _atomic_write_jsonl(qdir / f"q{idx:02d}.input.jsonl", rows)

    n_members = sum(len(c) for c in chunks)
    print(f"[make_spi_sheet] {name} ({q.kind}): {n_members} row(s) -> {len(chunks)} chunk(s) in {qdir}")
    return (n_members, len(chunks), False)


def cmd_build(args) -> int:
    if args.queue:
        if args.queue not in closure_law.QUEUES:
            print(f"[make_spi_sheet] unknown queue: {args.queue!r} (known: {sorted(closure_law.QUEUES)})")
            return 1
        names = [args.queue]
    else:
        names = list(closure_law.QUEUES)

    total_rows = total_chunks = 0
    any_skipped = False
    for name in names:
        n_rows, n_chunks, skipped = build_queue(name, args.force)
        total_rows += n_rows
        total_chunks += n_chunks
        any_skipped = any_skipped or skipped

    print(f"[make_spi_sheet] build complete: {len(names)} queue(s) targeted, "
          f"{total_rows} row(s) in {total_chunks} chunk(s)")
    return 1 if any_skipped else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build", help="chunk every queue's members into corpus/spi/batches/<QUEUE>/q<NN>.input.jsonl")
    p.add_argument("--queue", default="", help="build only this queue (default: every queue in closure_law.QUEUES)")
    p.add_argument("--force", action="store_true",
                    help="rebuild even if q*.input.jsonl already exist (never touches *.verdict.jsonl)")
    p.set_defaults(func=cmd_build)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
