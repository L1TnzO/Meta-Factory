"""test_outcome_judges — the two-sided TOOTH for OUTCOME-JUDGES (COUNCIL-360 §6.0.2 + H-9).

Pins the per-SESSION transcript split (`transcript_model_split`, distinct from the machine-global
`model_split`), the wall-clock-hours observer (`wall_clock_hours`), and their wiring into
`cost_summary`/`cost_block` (opus-share + $shadow labeling + horas-humano line), all honest-degradation:
unmeasured axes are `None`/`{}`, never a fabricated number.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metafactory.graph import pricing
from metafactory.memory.metrics import transcript_model_split, wall_clock_hours


def _write_jsonl(path: Path, lines: list) -> Path:
    """Write raw JSONL: each item is either a dict (json-dumped) or a literal string (garbage line)."""
    out = []
    for item in lines:
        out.append(item if isinstance(item, str) else json.dumps(item))
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


# ── transcript_model_split ────────────────────────────────────────────────────────
def test_transcript_model_split_dedups_by_message_id(tmp_path: Path):
    transcript = _write_jsonl(tmp_path / "t.jsonl", [
        # (a) same opus message.id repeated 3x with CUMULATIVE usage — only the LAST occurrence counts
        {"message": {"id": "msg_1", "model": "claude-opus-4-8",
                     "usage": {"input_tokens": 1000, "output_tokens": 100}}},
        {"message": {"id": "msg_1", "model": "claude-opus-4-8",
                     "usage": {"input_tokens": 2000, "output_tokens": 200}}},
        {"message": {"id": "msg_1", "model": "claude-opus-4-8",
                     "usage": {"input_tokens": 3000, "output_tokens": 300,
                               "cache_creation_input_tokens": 5000, "cache_read_input_tokens": 10000}}},
        # (b) a sonnet message with a DIFFERENT id
        {"message": {"id": "msg_2", "model": "claude-sonnet-5",
                     "usage": {"input_tokens": 4000, "output_tokens": 400}}},
        # (d) a non-JSON garbage line — skipped
        "not valid json {{{",
        # (c) a usage line WITHOUT any id — counts individually (top-level usage+model)
        {"model": "claude-sonnet-5", "usage": {"input_tokens": 500, "output_tokens": 50}},
    ])

    result = transcript_model_split(transcript)

    expected_opus = pricing.price_tokens(
        "claude-opus-4-8", input_tokens=3000, output_tokens=300,
        cache_creation=5000, cache_read=10000,
    )
    expected_sonnet = (
        pricing.price_tokens("claude-sonnet-5", input_tokens=4000, output_tokens=400)
        + pricing.price_tokens("claude-sonnet-5", input_tokens=500, output_tokens=50)
    )
    expected_total = expected_opus + expected_sonnet

    assert set(result["usd_by_tier"].keys()) == {"opus", "sonnet"}
    assert result["usd_by_tier"]["opus"] == pytest.approx(expected_opus)
    assert result["usd_by_tier"]["sonnet"] == pytest.approx(expected_sonnet)
    assert result["total_usd"] == pytest.approx(expected_total)
    assert result["opus_share"] == pytest.approx(expected_opus / expected_total)


def test_transcript_model_split_missing_file_is_honest(tmp_path: Path):
    result = transcript_model_split(tmp_path / "does-not-exist.jsonl")
    assert result == {"usd_by_tier": {}, "total_usd": 0.0, "opus_share": None}


# ── wall_clock_hours ───────────────────────────────────────────────────────────────
def test_wall_clock_hours_90min_apart(tmp_path: Path):
    transcript = _write_jsonl(tmp_path / "t.jsonl", [
        {"timestamp": "2026-07-04T10:00:00Z"},
        {"timestamp": "2026-07-04T11:30:00Z"},
    ])
    assert wall_clock_hours(transcript) == pytest.approx(1.5)


def test_wall_clock_hours_single_timestamp_is_none(tmp_path: Path):
    transcript = _write_jsonl(tmp_path / "t.jsonl", [{"timestamp": "2026-07-04T10:00:00Z"}])
    assert wall_clock_hours(transcript) is None


def test_wall_clock_hours_zero_timestamps_is_none(tmp_path: Path):
    transcript = _write_jsonl(tmp_path / "t.jsonl", [{"no_timestamp_here": True}])
    assert wall_clock_hours(transcript) is None


def test_wall_clock_hours_missing_file_is_none(tmp_path: Path):
    assert wall_clock_hours(tmp_path / "does-not-exist.jsonl") is None


# ── cost_summary degrades honestly without a transcript ─────────────────────────────
def test_cost_summary_no_transcript_degrades(tmp_path: Path):
    from metafactory.verify.cost_report import cost_summary
    s = cost_summary(tmp_path)
    assert s["usd_by_model"] == {}
    assert s["opus_share"] is None
    assert s["wall_clock_h"] is None


# ── cost_block renders the new lines only when a transcript is given ────────────────
def test_cost_block_with_transcript_has_modelo_and_horas(tmp_path: Path):
    from metafactory.verify.cost_report import cost_block
    transcript = _write_jsonl(tmp_path / "t.jsonl", [
        {"message": {"id": "msg_1", "model": "claude-opus-4-8", "timestamp": "2026-07-04T10:00:00Z",
                     "usage": {"input_tokens": 10_000, "output_tokens": 1_000}},
         "timestamp": "2026-07-04T10:00:00Z"},
        {"message": {"id": "msg_2", "model": "claude-sonnet-5", "timestamp": "2026-07-04T10:30:00Z",
                     "usage": {"input_tokens": 10_000, "output_tokens": 1_000}},
         "timestamp": "2026-07-04T10:30:00Z"},
    ])
    block = cost_block(tmp_path, transcript=transcript)
    joined = "\n".join(block)

    costo_line = next(l for l in block if l.startswith("COSTO"))
    assert "shadow-total" in costo_line

    modelo_line = next(l for l in block if l.startswith("MODELO"))
    assert "opus" in modelo_line and "%" in modelo_line

    horas_line = next(l for l in block if l.startswith("HORAS"))
    assert horas_line  # present at all is the assertion; exact value covered by wall_clock_hours tests
    assert "MODELO" in joined and "HORAS" in joined


def test_cost_block_no_transcript_omits_modelo_and_horas(tmp_path: Path):
    from metafactory.verify.cost_report import cost_block
    block = cost_block(tmp_path)  # no transcript, no ledger
    assert not any(l.startswith("MODELO") for l in block)
    assert not any(l.startswith("HORAS") for l in block)
    costo_line = next(l for l in block if l.startswith("COSTO"))
    assert "shadow-total" in costo_line
