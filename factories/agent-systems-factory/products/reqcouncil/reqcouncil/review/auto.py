"""Unattended reviewer for evaluation harness runs (eval e1, CI).

HONEST by construction: the checkpoint still FIRES (non-skippability is reachability,
not the presence of a human), and every decision lands in the trail labeled
engineer="auto-eval" / mode="auto" — an unattended run is visible as such in run.json,
draft.json and the review_decision table. Its catch-rate is 0 by definition; the human
measurement is the review drill (drill.py) / E-runs.
"""

from __future__ import annotations

AUTO_ENGINEER = "auto-eval"
AUTO_REASON = "auto-eval bulk accept (unattended evaluation-harness run)"


def auto_reviewer(payload: dict) -> dict:
    packet = payload["packet"]
    if payload.get("errors"):  # a validation loop with a canned payload cannot progress
        raise RuntimeError(f"auto reviewer produced invalid decisions: {payload['errors']}")
    return {
        "engineer": AUTO_ENGINEER,
        "mode": "auto",
        "decisions": {
            item["id"]: {"decision": "accept", "reason": AUTO_REASON}
            for item in packet["items"]
        },
    }
