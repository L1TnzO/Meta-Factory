"""Gap-hunter budget (config `rounds.gap_budget`, work/H4 red1 decision):
at most N candidates KEPT per round, emission order preserved (the persona emits
most-important-first), truncation LOGGED never silent, ids re-scoped 0..N-1.
None = unlimited (H3-era config compat).
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("numpy", reason="[council] extra not installed")

from reqcouncil.council.critics import run_gap_hunter  # noqa: E402
from reqcouncil.council.personas import Persona  # noqa: E402
from reqcouncil.llm import ChatResult  # noqa: E402

SIX_CANDIDATES = json.dumps([
    {"text": f"As a member, I want feature {i}, so that I benefit.",
     "kind": "FR", "anchors": ["c0"], "stance": "explicit", "rationale": "gap"}
    for i in range(6)
])

PERSONA = Persona(name="gap_hunter", system_prompt="You are the Gap Hunter.", sha="x" * 12)
TAGGED = [("c0", "We need the missing features.")]
TAG_TO_ANCHOR = {"c0": "sha1:0"}


class SixChat:
    model = "fake-model"
    api_base = "local"

    def complete(self, messages, *, temperature, max_completion_tokens=None,
                 reasoning_effort=None):
        return ChatResult(SIX_CANDIDATES, "stop", 10, 5)


def hunt(budget):
    return run_gap_hunter(
        SixChat(), PERSONA, 1, ["c0"], TAGGED, TAG_TO_ANCHOR,
        temperature=0.3, budget=budget,
    )


def test_budget_truncates_in_emission_order_and_logs():
    res = hunt(4)
    assert len(res.gap_candidates) == 4
    # emission order kept (model priority) + round-scoped ids re-numbered 0..3
    assert [c.cand_id for c in res.gap_candidates] == [
        f"gap_hunter-r1-{i}" for i in range(4)]
    assert [c.text for c in res.gap_candidates] == [
        f"As a member, I want feature {i}, so that I benefit." for i in range(4)]
    assert {"event": "gap_budget_truncated", "proposed": 6, "kept": 4} in res.parse_log


def test_no_budget_keeps_everything():
    res = hunt(None)
    assert len(res.gap_candidates) == 6
    assert not any(e.get("event") == "gap_budget_truncated" for e in res.parse_log)


def test_budget_not_exceeded_is_untouched_and_unlogged():
    res = hunt(6)
    assert len(res.gap_candidates) == 6
    assert not any(e.get("event") == "gap_budget_truncated" for e in res.parse_log)
