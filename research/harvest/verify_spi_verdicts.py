#!/usr/bin/env python3
"""Deterministic gate for the second independent pass, SPI (protocol §9.1/§9.2).

Trust-chain: written by the orchestrator, never by the slot it judges. It decides GREEN/RED; it never
repairs, never writes, never downloads. Mirror of `verify_digest_verdicts.py`, one phase across.

What it holds the second reader to:
  1. **Coverage** — the verdict's key set is exactly the input chunk's key set (no drops, no smuggling).
  2. **Law** — every row passes `closure_law.validate_verdict` for its queue's KIND (which, for
     membership queues, is the frozen §7.5 rubric arithmetic itself, imported not restated).
  3. **Blindness** — the INPUT the reader was given carries no pass-1 output column. This is checked on
     the inputs, not promised by a prompt: if the builder ever leaked `decision`, every agreement number
     computed afterwards would be worthless, and it would be worthless SILENTLY.

Usage:
    python3 harvest/verify_spi_verdicts.py                     # sweep every verdict on disk
    python3 harvest/verify_spi_verdicts.py --require q03,q04   # demand these chunks exist AND pass
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from closure_law import QUEUES, SPI_DIR, BLIND_FORBIDDEN, validate_verdict  # noqa: E402

BATCHES = SPI_DIR / "batches"


def read_jsonl(path: Path) -> list[dict]:
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name}:{n}: malformed JSON ({exc})") from exc
    return out


def check_chunk(inp: Path, verdict: Path, kind: str, errors: list[str]) -> int:
    try:
        inputs = read_jsonl(inp)
        rows = read_jsonl(verdict)
    except ValueError as exc:
        errors.append(str(exc))
        return 0

    leaked = sorted({c for r in inputs for c in r if c in BLIND_FORBIDDEN})
    if leaked:
        errors.append(f"{inp.name}: BLINDNESS BROKEN — input carries pass-1 output column(s) {leaked}")
        return 0

    want = {r["key"] for r in inputs}
    got = [r.get("key", "?") for r in rows]
    if len(got) != len(set(got)):
        errors.append(f"{verdict.name}: duplicated key(s) in verdict")
        return 0
    if set(got) != want:
        missing, extra = sorted(want - set(got)), sorted(set(got) - want)
        errors.append(f"{verdict.name}: key set != input ({len(missing)} missing, {len(extra)} extra)"
                      + (f" missing={missing[:5]}" if missing else "")
                      + (f" extra={extra[:5]}" if extra else ""))
        return 0

    before = len(errors)
    for row in rows:
        validate_verdict(row, kind, errors)
    if len(errors) > before:
        return 0
    return len(rows)


def check_inputs() -> int:
    """Judge the built inputs on their own: every queue chunked, every row present exactly once, and
    NO pass-1 output column anywhere. Blindness has to be checkable before the reading starts — after
    the fact it is unfixable, because a contaminated verdict cannot be un-contaminated."""
    errors: list[str] = []
    if not BATCHES.exists():
        print(f"RED: no batches directory at {BATCHES}")
        return 1

    from closure_law import queue_members  # local import: keeps the module cheap for the verdict path

    for name in QUEUES:
        qdir = BATCHES / name
        expected = {r["key"] for r in queue_members(name) if "key" in r}
        if not expected:                      # DUPLICADOS keys live in key_a/key_b
            expected = {r["key_a"] for r in queue_members(name)}
        if not qdir.exists():
            errors.append(f"{name}: queue has no batches directory (all {len(expected)} rows unbuilt)")
            continue
        seen: list[str] = []
        for inp in sorted(qdir.glob("*.input.jsonl")):
            try:
                rows = read_jsonl(inp)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            leaked = sorted({c for r in rows for c in r if c in BLIND_FORBIDDEN})
            if leaked:
                errors.append(f"{inp.name}: BLINDNESS BROKEN — carries pass-1 column(s) {leaked}")
            seen.extend(r.get("key", "?") for r in rows)
        if len(seen) != len(set(seen)):
            errors.append(f"{name}: a key appears in more than one chunk")
        missing, extra = expected - set(seen), set(seen) - expected
        if missing:
            errors.append(f"{name}: {len(missing)} row(s) of the queue were never chunked "
                          f"e.g. {sorted(missing)[:3]}")
        if extra:
            errors.append(f"{name}: {len(extra)} key(s) not in the queue were smuggled in "
                          f"e.g. {sorted(extra)[:3]}")

    for e in errors:
        print(f"RED: {e}")
    if errors:
        print(f"SPI INPUTS: RED — {len(errors)} problem(s)")
        return 1
    total = sum(len(read_jsonl(p)) for q in QUEUES for p in (BATCHES / q).glob("*.input.jsonl"))
    print(f"SPI INPUTS: PASS — {len(QUEUES)} queue(s) fully chunked, {total} row(s), no pass-1 leakage")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require", default="", help="comma-separated chunk ids that MUST exist and pass")
    ap.add_argument("--inputs-only", action="store_true",
                    help="judge the BUILT INPUTS alone (blindness + full queue coverage), before any "
                         "verdict exists — this is what makes the builder verifiable by blocking")
    args = ap.parse_args()
    required = {c.strip() for c in args.require.split(",") if c.strip()}

    if args.inputs_only:
        return check_inputs()

    errors: list[str] = []
    seen: set[str] = set()
    total = 0
    per_queue: dict[str, int] = {}

    if not BATCHES.exists():
        print(f"RED: no batches directory at {BATCHES}")
        return 1

    for qdir in sorted(p for p in BATCHES.iterdir() if p.is_dir()):
        if qdir.name not in QUEUES:
            errors.append(f"{qdir.name}: not a queue in the closure law (§9.1)")
            continue
        kind = QUEUES[qdir.name].kind
        for verdict in sorted(qdir.glob("*.verdict.jsonl")):
            chunk = verdict.name.split(".")[0]
            inp = qdir / f"{chunk}.input.jsonl"
            if not inp.exists():
                errors.append(f"{verdict.name}: no matching input chunk ({inp.name})")
                continue
            seen.add(chunk)
            n = check_chunk(inp, verdict, kind, errors)
            total += n
            per_queue[qdir.name] = per_queue.get(qdir.name, 0) + n

    for chunk in sorted(required - seen):
        errors.append(f"{chunk}: REQUIRED chunk has no verdict on disk")

    for e in errors:
        print(f"RED: {e}")
    if errors:
        print(f"SPI GATE: RED — {len(errors)} problem(s)")
        return 1
    if not seen:
        print("SPI GATE: RED — no verdicts found (nothing to verify is not the same as green)")
        return 1
    detail = " · ".join(f"{q}={n}" for q, n in sorted(per_queue.items()))
    print(f"SPI GATE: PASS — {len(seen)} chunk(s), {total} verdict row(s) [{detail}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
