#!/usr/bin/env python3
"""escape_threshold — the observer whose FAILURE MODE is silence, not a bad number.

    python3 -m v3.verify.checks.escape_threshold
    V3_ESCAPE_THRESHOLD_SABOTAGE=1 python3 -m v3.verify.checks.escape_threshold   # red; exits 0

ADR-019 §6 decided "no retrieval index, discarded by measurement" and attached an expiry condition:
the corpus still fits the window, and what we inject is still what gets read. Nothing has ever
measured that condition. §09.4 calls it the highest-priority addition and §11.3 lets the meter ride
INC-6 because it comes free with typed usage.

WHAT IS GATED HERE, AND WHAT DELIBERATELY IS NOT. The NUMBER is not gated. Choosing a threshold —
"escape at 60 % of the window" — is new policy, and §11.5 is explicit that no increment improves
anything before INC-11. What is gated is the observer's **ABSENCE**: it must emit

    (a) headroom — the corpus against the window, with a margin
    (b) relevance ratio at the LEAF — the context injected, against what the leaf went and fetched

with real values, or say N/A out loud. An observer that emits silence is the failure, and that is
not a hypothetical: the instrument this increment was opened for failed by emitting nothing while a
KPI kept printing a number.

(b) IS THE LEAF-LEVEL RATIO, said in those words. §10.6 describes combining injected context with
"the `PostToolUse` read events already captured" — those are the events that went silent for 17
days, and in v3 they come from the host's own typed stream instead. The richer per-NODE version
needs the node tree (§15.6) and is INC-12's. Promising it here would be describing an instrument
nobody built.

THREE PLANTED CLASSES, each naming the value it perturbs:
  silent_observer         a record whose four fields are all null → `emitted()` goes 4 → 0
  empty_corpus_no_headroom  a corpus of 0 files must be a finding, never "infinite headroom"
  absent_is_not_zero      with no inputs, every field must be None — 0 would be a measurement
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from ...economy import meter
from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]
_SABOTAGE_VAR = "V3_ESCAPE_THRESHOLD_SABOTAGE"
_CLASSES = ("silent_observer", "empty_corpus_no_headroom", "absent_is_not_zero")

#: A leaf the host really metered, in the shape `meter.record_leaf` writes.
FIXTURE = {"ts": "2026-07-30T18:00:00Z", "kind": "leaf", "leaf": "fixture",
           "injected_tokens": 18400, "final_tokens": 41200, "read_events": 6,
           "read_tokens": 22800, "relevance_ratio": 1.2391, "categories": []}


def _run_sabotage() -> int:
    caught: list[str] = []

    if len(meter.emitted(FIXTURE)) != 4:
        return Verdict("v3-escape-threshold (SABOTAGE)", 1,
                       "the fixture does not emit all four fields, so no catch is attributable"
                       ).emit()

    silent = {**FIXTURE, "injected_tokens": None, "final_tokens": None, "read_events": None,
              "read_tokens": None, "relevance_ratio": None}
    if not meter.emitted(silent):
        caught.append("silent_observer")

    with tempfile.TemporaryDirectory(prefix="v3-escape-") as tmp:
        empty = meter.headroom(Path(tmp))
        # An empty tree measures 0 tokens, which arithmetic happily calls 100 % headroom. The
        # finding is `corpus_files == 0`, and this asserts the caller has something to see it with.
        if empty["corpus_files"] == 0 and empty["entry_files"] == 0 \
                and empty["headroom_pct"] == 100.0:
            caught.append("empty_corpus_no_headroom")

    absent = meter.leaf_relevance(None, None, None)
    if all(value is None for value in absent.values()):
        caught.append("absent_is_not_zero")

    if len(caught) == len(_CLASSES):
        return Verdict("v3-escape-threshold (SABOTAGE)", 0,
                       f"{len(caught)}/{len(_CLASSES)} planted defect(s) caught "
                       f"({', '.join(caught)})").emit()
    missed = [c for c in _CLASSES if c not in caught]
    return Verdict("v3-escape-threshold (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {len(caught)}/{len(_CLASSES)} caught "
                   f"({', '.join(caught) or 'none'}) — missed {missed}").emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-escape-threshold", 2, f"takes no arguments; got {argv!r}").emit()
    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage()

    # (a) — always computable, and an empty corpus is Lock #1, not good news.
    space = meter.headroom(_ROOT)
    if space["corpus_files"] == 0 or space["entry_files"] == 0:
        return Verdict("v3-escape-threshold", 1,
                       "the corpus measured ZERO files: 100 % headroom over nothing is a vacuous "
                       "green, not an ADR-019 §6 answer", counts=space).emit()

    counts = {"entry_tok": space["entry_tokens"], "window": space["window_tokens"],
              "headroom_pct": space["headroom_pct"], "corpus_tok": space["corpus_tokens"],
              "corpus_growth_pct": space["corpus_growth_pct"], "files": space["corpus_files"]}

    # (b) — the leaf ratio, from the last leaf the host metered.
    latest = meter.latest(_ROOT)
    if latest is None:
        return Verdict("v3-escape-threshold", 0,
                       f"N/A: (a) entry-set headroom {space['headroom_pct']}% "
                       f"({space['entry_tokens']}/{space['window_tokens']} tok); full corpus "
                       f"{space['corpus_tokens']} tok, {space['corpus_growth_pct']:+}% vs the "
                       f"{space['corpus_baseline_as_of']} baseline; (b) no leaf metered yet",
                       counts=counts,
                       next_action="run one leaf through the host: (b) is a leaf-level ratio and "
                                   "needs a leaf").emit()

    fields = meter.emitted(latest)
    if not fields:
        return Verdict("v3-escape-threshold", 1,
                       f"the last metered leaf ({latest.get('leaf')}) emitted SILENCE: a record "
                       f"with every field null is not a measurement, and an observer that emits "
                       f"silence is the failure this gate exists for", counts=counts).emit()

    counts.update({"injected_tok": latest.get("injected_tokens"),
                   "read_events": latest.get("read_events"),
                   "read_tok": latest.get("read_tokens"),
                   "relevance": latest.get("relevance_ratio")})
    return Verdict("v3-escape-threshold", 0,
                   f"(a) entry set {space['entry_tokens']}/{space['window_tokens']} tok, headroom "
                   f"{space['headroom_pct']}%, fits={space['fits']}; full corpus "
                   f"{space['corpus_tokens']} tok over {space['corpus_files']} files "
                   f"({space['corpus_growth_pct']:+}% vs {space['corpus_baseline_as_of']}) · "
                   f"(b) leaf {latest.get('leaf')}: {len(fields)}/4 field(s), ratio "
                   f"{latest.get('relevance_ratio')}", counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
