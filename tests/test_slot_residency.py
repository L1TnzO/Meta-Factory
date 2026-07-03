"""test_slot_residency — the two-sided TOOTH for the INC-6 HEADLESS-SLOTS observer (`slot_residency_share`).

Authored to `.gen/slot-residency.contract.md`'s measured semantics: `slot_residency_share` is the
delegation-axis twin of `churn_cost_share` (INC-5) — the USD share of an increment spent on orchestrator
cache-RESIDENCY across delegated-slot boundaries (the resume turn re-writing a prefix that expired while
the orchestrator was blocked on a synchronous subagent spawn). Pins, two-sided:
  - a missing transcript is an honest re-derivable zero (no fabricated number);
  - no Task/Agent tool_use -> zero slots, zero residency, but a real (nonzero) session_usd;
  - a slot-spawn whose resume is a cache HIT (small cache_creation vs the read-peak) -> zero residency;
  - a slot-spawn whose resume is an EXPIRATION (cache_creation >= fraction*peak) -> nonzero residency;
  - `isSidechain: true` turns are excluded from the denominator (the subagent's own cost);
  - the return shape always carries the four typed keys.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metafactory.memory.metrics import slot_residency_share


def _write_transcript(path: Path, turns: list[dict]) -> Path:
    """One JSONL line per turn, shaped like the real stream: top-level `timestamp`/`isSidechain` +
    `message: {model, usage: {...}, content: [...]}` — the exact shape the contract specifies."""
    lines = []
    for t in turns:
        obj: dict = {
            "timestamp": t.get("timestamp", ""),
            "message": {
                "model": t.get("model", "claude-sonnet-5"),
                "usage": {
                    "input_tokens": t.get("input", 0),
                    "output_tokens": t.get("output", 0),
                    "cache_creation_input_tokens": t.get("cache_creation", 0),
                    "cache_read_input_tokens": t.get("cache_read", 0),
                },
                "content": t.get("content", []),
            },
        }
        if "is_sidechain" in t:
            obj["isSidechain"] = t["is_sidechain"]
        lines.append(json.dumps(obj))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _task_spawn(**overrides) -> dict:
    """A turn that emits a `Task` tool_use block (the slot-spawn signal)."""
    turn = {"content": [{"type": "tool_use", "name": "Task", "id": "t1", "input": {}}]}
    turn.update(overrides)
    return turn


# ── 1. missing transcript -> all zeros, slots 0 (re-derivable, honest) ──────────────────────────
def test_missing_transcript_is_honest_zero(tmp_path: Path):
    result = slot_residency_share(tmp_path / "does-not-exist.jsonl")
    assert result == {"residency_usd": 0.0, "session_usd": 0.0, "share": 0.0, "slots": 0}


# ── 2. valid transcript, no Task/Agent tool_use -> slots 0, residency 0.0, real session_usd ─────
def test_no_slot_spawn_zero_slots_but_real_session_cost(tmp_path: Path):
    transcript = _write_transcript(tmp_path / "no_spawn.jsonl", [
        {"timestamp": "2026-07-03T12:00:00Z", "input": 500, "output": 100, "cache_read": 10_000},
        {"timestamp": "2026-07-03T12:05:00Z", "input": 500, "output": 100, "cache_read": 10_000},
    ])
    result = slot_residency_share(transcript)
    assert result["slots"] == 0
    assert result["residency_usd"] == 0.0
    assert result["session_usd"] > 0
    assert result["share"] == 0.0


# ── 3. slot-spawn + resume that is a cache HIT -> slots 1, residency 0.0, share 0.0 ─────────────
def test_slot_spawn_resume_cache_hit_zero_residency(tmp_path: Path):
    transcript = _write_transcript(tmp_path / "hit.jsonl", [
        {"timestamp": "2026-07-03T12:00:00Z", "cache_read": 100_000},                    # sets peak 100k
        _task_spawn(timestamp="2026-07-03T12:00:05Z", input=200, output=50),             # spawn turn
        {"timestamp": "2026-07-03T12:03:10Z",                                             # gap >= 2min
         "cache_creation": 1_000, "cache_read": 90_000},                                  # HIT: 1k << 0.5*100k
    ])
    result = slot_residency_share(transcript)
    assert result["slots"] == 1
    assert result["residency_usd"] == 0.0
    assert result["share"] == 0.0
    assert result["session_usd"] > 0


# ── 4. slot-spawn + resume that is an EXPIRATION -> slots 1, residency > 0, share > 0 ────────────
def test_slot_spawn_resume_expiration_nonzero_residency(tmp_path: Path):
    transcript = _write_transcript(tmp_path / "expire.jsonl", [
        {"timestamp": "2026-07-03T12:00:00Z", "cache_read": 100_000},                    # sets peak 100k
        _task_spawn(timestamp="2026-07-03T12:00:05Z", input=200, output=50),             # spawn turn
        {"timestamp": "2026-07-03T12:03:10Z",                                             # gap >= 2min
         "cache_creation": 60_000, "cache_read": 5_000},                                  # EXPIRE: 60k >= 0.5*100k
    ])
    result = slot_residency_share(transcript)
    assert result["slots"] == 1
    # hand-computed (sonnet §1.2: write_5m 2.50 USD/MTok): 60_000 * 2.50 / 1e6 = 0.15
    assert result["residency_usd"] == pytest.approx(0.15)
    assert result["share"] > 0
    assert result["share"] == pytest.approx(result["residency_usd"] / result["session_usd"])


# ── 5. an isSidechain turn is excluded from session_usd (must not move the denominator) ─────────
def test_sidechain_turn_excluded_from_session_usd(tmp_path: Path):
    baseline = _write_transcript(tmp_path / "baseline.jsonl", [
        {"timestamp": "2026-07-03T12:00:00Z", "input": 500, "output": 100, "cache_read": 10_000},
    ])
    baseline_usd = slot_residency_share(baseline)["session_usd"]

    with_sidechain = _write_transcript(tmp_path / "with_sidechain.jsonl", [
        {"timestamp": "2026-07-03T12:00:00Z", "input": 500, "output": 100, "cache_read": 10_000},
        {"timestamp": "2026-07-03T12:00:30Z", "input": 999_999, "output": 999_999,
         "cache_creation": 999_999, "cache_read": 999_999, "is_sidechain": True},
    ])
    with_sidechain_usd = slot_residency_share(with_sidechain)["session_usd"]

    assert with_sidechain_usd == pytest.approx(baseline_usd)


# ── 6. return-shape: the four keys exist with the right types ───────────────────────────────────
def test_return_shape_types(tmp_path: Path):
    transcript = _write_transcript(tmp_path / "shape.jsonl", [
        {"timestamp": "2026-07-03T12:00:00Z", "input": 500, "output": 100, "cache_read": 10_000},
    ])
    result = slot_residency_share(transcript)
    assert set(result.keys()) == {"residency_usd", "session_usd", "share", "slots"}
    assert isinstance(result["residency_usd"], float)
    assert isinstance(result["session_usd"], float)
    assert isinstance(result["share"], float)
    assert isinstance(result["slots"], int)
