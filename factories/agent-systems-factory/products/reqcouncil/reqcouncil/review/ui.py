"""Interactive + file reviewers (docs/design/02 §4).

`cli_reviewer` is the cognitive forcing function: MANDATORY items (buckets 1-4) are
walked ONE AT A TIME and each demands an explicit decision plus a typed one-line
reason — no enter-enter-enter path exists through them. Bucket-5 items may be
bulk-accepted, but that shortcut is RECORDED as such (reason = BULK_REASON), so
automation bias stays measurable in the trail instead of hiding inside ordinary
accepts.

`file_reviewer` replays a decisions JSON (batch mode / drills). It is static input:
if the graph RE-interrupts with validation errors, it raises loudly — a malformed
file must never spin the resume loop forever.

Both return payloads for `review.decisions.validate_decisions`; the graph, not the
UI, is the tooth.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

BULK_REASON = "bulk-accept (bucket 5, not individually reviewed)"
_PROMPT = "  decision [a]ccept / [e]dit / [r]eject: "
_DECISION_KEYS = {"a": "accept", "accept": "accept",
                  "e": "edit", "edit": "edit",
                  "r": "reject", "reject": "reject"}


def _show_item(item: dict, print_fn) -> None:
    tag = "MANDATORY" if item["mandatory"] else "review-optional"
    print_fn(f"\n[{item['order'] + 1}] {item['id']}  ({tag}, bucket {item['bucket']})")
    print_fn(f"  why here : {item['why']}")
    print_fn(f"  text     : {item['text']}")
    print_fn(f"  kind/status: {item['kind']} · {item['status']}"
             f" · confidence {item['confidence']}")
    print_fn(f"  evidence : {item['evidence']}")
    for exc in item["excerpts"]:
        print_fn(f"    [{exc['verdict']}] {exc['anchor']}: {exc['excerpt']}")
    if item["flags"]:
        print_fn(f"  flags    : {', '.join(item['flags'])}")


def _ask_decision(item: dict, input_fn, print_fn) -> dict:
    while True:
        verdict = _DECISION_KEYS.get(str(input_fn(_PROMPT)).strip().lower())
        if verdict is None:
            print_fn("  please answer a / e / r")
            continue
        entry: dict = {"decision": verdict}
        if verdict == "edit":
            edited = str(input_fn("  edited text: ")).strip()
            if not edited:
                print_fn("  edit requires non-empty text")
                continue
            entry["edited_text"] = edited
        reason = str(input_fn("  one-line reason (required): ")).strip()
        if not reason:
            print_fn("  a reason is required — that IS the checkpoint")
            continue
        entry["reason"] = reason
        return entry


def cli_reviewer(input_fn: Callable = input, print_fn: Callable = print):
    """Reviewer factory for the interactive CLI (injectable I/O => testable)."""

    def review(payload: dict) -> dict:
        packet = payload["packet"]
        print_fn(f"\n=== {packet['watermark']} ===")
        for warning in packet["warnings"]:
            print_fn(f"WARNING: {warning}")
        stats = packet["stats"]
        print_fn(f"{stats['total']} items — {stats['mandatory']} mandatory "
                 f"(by bucket: {stats['by_bucket']})")
        if payload.get("errors"):
            print_fn("\nprevious decisions were REJECTED by validation:")
            for err in payload["errors"]:
                print_fn(f"  - {err}")

        engineer = ""
        while not engineer:
            engineer = str(input_fn("engineer name: ")).strip()

        decisions: dict[str, dict] = {}
        rest: list[dict] = []
        for item in packet["items"]:
            if item["mandatory"]:
                _show_item(item, print_fn)
                decisions[item["id"]] = _ask_decision(item, input_fn, print_fn)
            else:
                rest.append(item)

        if rest:
            answer = str(input_fn(
                f"\nbulk-accept the remaining {len(rest)} council-accepted items? "
                "[y = accept all, recorded as bulk / n = review one by one]: "
            )).strip().lower()
            if answer in ("y", "yes"):
                for item in rest:
                    decisions[item["id"]] = {"decision": "accept", "reason": BULK_REASON}
            else:
                for item in rest:
                    _show_item(item, print_fn)
                    decisions[item["id"]] = _ask_decision(item, input_fn, print_fn)

        return {"engineer": engineer, "mode": "cli", "decisions": decisions}

    return review


def file_reviewer(path: str | Path):
    """Reviewer that replays a decisions JSON file (batch runs, drills)."""
    path = Path(path)

    def review(payload: dict) -> dict:
        if payload.get("errors"):
            raise RuntimeError(
                f"decisions file {path} was rejected by validation and cannot be "
                f"corrected mid-run: {payload['errors']}"
            )
        return json.loads(path.read_text(encoding="utf-8"))

    return review
