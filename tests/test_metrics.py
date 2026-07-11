"""tests/test_metrics.py — suite Tier 0 para metafactory.memory.metrics.

Invariante: CERO llamadas al modelo. Todo file-IO + aritmética (ADR-008).
Usa tmp_path para nunca escribir en el árbol real del repo.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import pytest

from metafactory.memory import journal, metrics
from metafactory.memory.metrics import (
    PRICES,
    aggregate,
    capture,
    cost,
    metrics_path,
    read,
    render,
    rollup_from_transcript,
    tier_for,
)


# ---------------------------------------------------------------------------
# tier_for
# ---------------------------------------------------------------------------

class TestTierFor:
    def test_opus_model(self):
        assert tier_for("claude-opus-4") == "opus"

    def test_sonnet_model(self):
        assert tier_for("claude-sonnet-4-5") == "sonnet"

    def test_haiku_model(self):
        assert tier_for("claude-haiku-3") == "haiku"

    def test_unknown_defaults_to_sonnet(self):
        assert tier_for("gpt-4") == "sonnet"

    def test_case_insensitive(self):
        assert tier_for("CLAUDE-OPUS-4") == "opus"

    def test_haiku_before_sonnet_in_logic(self):
        # haiku is checked before sonnet so a model with both substrings picks haiku
        # (edge case, not a real model — just ensures precedence is deterministic)
        assert tier_for("haiku-sonnet") == "haiku"


# ---------------------------------------------------------------------------
# cost
# ---------------------------------------------------------------------------

class TestCost:
    """Sample rollup with known token counts → assert exact USD amounts.

    Recomputed from the single-source dated table (`graph.pricing.PRICING`, ADR-021 §1.2): opus
    5/25/6.25(write_5m)/0.50(hit_refresh) · sonnet 2/10/2.50/0.20 (USD/MTok). `cache_write` in
    `PRICES` derives from `write_5m` (the honest default — see `graph/pricing.py`).

    opus (claude-opus-4):
      1000 input  × 5.00/1e6  = 0.00500
       500 output × 25.00/1e6 = 0.01250
       200 cache_creation × 6.25/1e6 = 0.00125
       100 cache_read × 0.50/1e6 = 0.00005
       subtotal = 0.01880

    sonnet (claude-sonnet-4-5):
      2000 input  × 2.00/1e6  = 0.00400
       300 output × 10.00/1e6 = 0.00300
         0 cache_creation = 0
        50 cache_read × 0.20/1e6 = 0.00001
       subtotal = 0.00701

    total = 0.02581
    """
    ROLLUP = {
        "claude-opus-4": {
            "input": 1000,
            "output": 500,
            "cache_creation": 200,
            "cache_read": 100,
        },
        "claude-sonnet-4-5": {
            "input": 2000,
            "output": 300,
            "cache_creation": 0,
            "cache_read": 50,
        },
    }

    def test_opus_cost(self):
        c = cost(self.ROLLUP)
        assert math.isclose(c["claude-opus-4"], 0.0188, rel_tol=1e-9)

    def test_sonnet_cost(self):
        c = cost(self.ROLLUP)
        assert math.isclose(c["claude-sonnet-4-5"], 0.00701, rel_tol=1e-9)

    def test_total(self):
        c = cost(self.ROLLUP)
        assert math.isclose(c["total"], 0.02581, rel_tol=1e-9)

    def test_empty_rollup(self):
        c = cost({})
        assert c == {"total": 0.0}

    def test_zero_tokens(self):
        rollup = {"claude-opus-4": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}}
        c = cost(rollup)
        assert c["claude-opus-4"] == 0.0
        assert c["total"] == 0.0

    def test_custom_prices(self):
        custom = {"sonnet": {"input": 1/1e6, "output": 1/1e6, "cache_write": 0.0, "cache_read": 0.0}}
        rollup = {"claude-sonnet-4-5": {"input": 1_000_000, "output": 0, "cache_creation": 0, "cache_read": 0}}
        c = cost(rollup, prices=custom)
        assert math.isclose(c["claude-sonnet-4-5"], 1.0, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# rollup_from_transcript
# ---------------------------------------------------------------------------

class TestRollupFromTranscript:
    def _write_transcript(self, path: Path, lines: list[dict]) -> Path:
        path.write_text(
            "\n".join(json.dumps(obj) for obj in lines) + "\n",
            encoding="utf-8",
        )
        return path

    def test_sums_two_opus_messages(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        self._write_transcript(t, [
            # message-nested format
            {"message": {
                "model": "claude-opus-4",
                "usage": {
                    "input_tokens": 500,
                    "output_tokens": 200,
                    "cache_creation_input_tokens": 50,
                    "cache_read_input_tokens": 10,
                },
            }},
            # second opus message
            {"message": {
                "model": "claude-opus-4",
                "usage": {
                    "input_tokens": 300,
                    "output_tokens": 100,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 20,
                },
            }},
        ])
        r = rollup_from_transcript(t)
        assert "claude-opus-4" in r
        assert r["claude-opus-4"]["input"] == 800
        assert r["claude-opus-4"]["output"] == 300
        assert r["claude-opus-4"]["cache_creation"] == 50
        assert r["claude-opus-4"]["cache_read"] == 30

    def test_two_different_models(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        self._write_transcript(t, [
            # top-level format
            {
                "model": "claude-opus-4",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            },
            {
                "model": "claude-sonnet-4-5",
                "usage": {
                    "input_tokens": 200,
                    "output_tokens": 80,
                    "cache_creation_input_tokens": 10,
                    "cache_read_input_tokens": 5,
                },
            },
        ])
        r = rollup_from_transcript(t)
        assert r["claude-opus-4"]["input"] == 100
        assert r["claude-sonnet-4-5"]["input"] == 200
        assert r["claude-sonnet-4-5"]["cache_creation"] == 10

    def test_skips_lines_without_usage(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        self._write_transcript(t, [
            {"type": "human", "content": "hello"},
            {"message": {"model": "claude-opus-4", "usage": {"input_tokens": 10, "output_tokens": 5, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}},
        ])
        r = rollup_from_transcript(t)
        assert len(r) == 1
        assert r["claude-opus-4"]["input"] == 10

    def test_tolerates_missing_keys_defaults_zero(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        # usage dict with only input_tokens present
        self._write_transcript(t, [
            {"model": "claude-opus-4", "usage": {"input_tokens": 42}},
        ])
        r = rollup_from_transcript(t)
        assert r["claude-opus-4"]["input"] == 42
        assert r["claude-opus-4"]["output"] == 0
        assert r["claude-opus-4"]["cache_creation"] == 0
        assert r["claude-opus-4"]["cache_read"] == 0

    def test_tolerates_bad_json_lines(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        t.write_text(
            'not-json\n'
            + json.dumps({"model": "claude-opus-4", "usage": {"input_tokens": 7, "output_tokens": 3, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}})
            + '\n',
            encoding="utf-8",
        )
        r = rollup_from_transcript(t)
        assert r["claude-opus-4"]["input"] == 7

    def test_nonexistent_file(self, tmp_path):
        r = rollup_from_transcript(tmp_path / "does_not_exist.jsonl")
        assert r == {}


# ---------------------------------------------------------------------------
# capture / read / metrics_path
# ---------------------------------------------------------------------------

class TestCaptureRead:
    def test_metrics_path(self, tmp_path):
        p = metrics_path(tmp_path)
        assert p == tmp_path / ".metamem" / "metrics.jsonl"

    def test_capture_creates_file(self, tmp_path):
        rec = capture(tmp_path, kind="tool", tool="Bash", session="s1")
        assert metrics_path(tmp_path).exists()
        assert rec["kind"] == "tool"
        assert rec["tool"] == "Bash"

    def test_read_returns_records(self, tmp_path):
        capture(tmp_path, kind="tool", tool="Read", session="s1")
        capture(tmp_path, kind="tool", tool="Edit", session="s1")
        recs = read(tmp_path)
        assert len(recs) == 2
        assert recs[0]["tool"] == "Read"

    def test_read_empty_when_no_file(self, tmp_path):
        assert read(tmp_path) == []

    def test_read_tolerates_bad_lines(self, tmp_path):
        p = metrics_path(tmp_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('garbage\n{"ts":"x","kind":"tool"}\n', encoding="utf-8")
        recs = read(tmp_path)
        assert len(recs) == 1

    def test_read_with_limit(self, tmp_path):
        for i in range(5):
            capture(tmp_path, kind="tool", tool=f"T{i}", session="s")
        assert len(read(tmp_path, limit=3)) == 3

    def test_capture_best_effort_bad_root(self):
        # capture to a path that can't be written (no exception should propagate)
        rec = capture(Path("/dev/null/impossible"), kind="tool", tool="X", session="s")
        assert rec["kind"] == "tool"


# ---------------------------------------------------------------------------
# aggregate
# ---------------------------------------------------------------------------

class TestAggregate:
    def test_delegation_rate(self, tmp_path):
        journal.append(tmp_path, "station_run", station="M0", slug="s", passed=True, gate_open=True, proof_sha="")
        journal.append(tmp_path, "station_run", station="M1", slug="s", passed=True, gate_open=True, proof_sha="")
        journal.append(tmp_path, "delegation", subagent_type="claude", model="", description="test")
        agg = aggregate(tmp_path)
        # 1 delegation / 2 station_run = 0.5
        assert math.isclose(agg["delegation_rate"], 0.5, rel_tol=1e-9)

    def test_delegation_rate_no_station_run(self, tmp_path):
        # Guard div0: no station_run events
        journal.append(tmp_path, "delegation", subagent_type="claude", model="", description="x")
        agg = aggregate(tmp_path)
        assert agg["delegation_rate"] == 0.0

    def test_delegation_count_visible_despite_diluted_rate(self, tmp_path):
        # The DELEG-MEASURE fix: a single delegation against many station_runs must remain VISIBLE as a
        # count even though the rate rounds toward 0 (the bug was the metric "lying" 0.0%).
        for i in range(100):
            journal.append(tmp_path, "station_run", station=f"M{i}", slug="s", passed=True, gate_open=True, proof_sha="")
        journal.append(tmp_path, "delegation", subagent_type="verifier", model="haiku", description="read")
        agg = aggregate(tmp_path)
        assert agg["n_delegations"] == 1
        assert agg["n_station_runs"] == 100
        assert agg["delegation_rate"] < 0.02  # diluted toward 0...
        assert agg["delegation_by_tier"]["haiku"] == 1  # ...but the count is honest

    def test_delegation_by_tier_groups_models(self, tmp_path):
        journal.append(tmp_path, "delegation", subagent_type="verifier", model="claude-haiku-4-5", description="r")
        journal.append(tmp_path, "delegation", subagent_type="generator", model="claude-sonnet-4-6", description="w")
        journal.append(tmp_path, "delegation", subagent_type="generator", model="claude-sonnet-4-6", description="w2")
        agg = aggregate(tmp_path)
        assert agg["delegation_by_tier"]["haiku"] == 1
        assert agg["delegation_by_tier"]["sonnet"] == 2

    def test_gate_streak(self, tmp_path):
        # 2 passes, 1 fail, 3 passes → streak = 3
        journal.append(tmp_path, "station_run", station="M0", slug="s", passed=True, gate_open=True, proof_sha="")
        journal.append(tmp_path, "station_run", station="M1", slug="s", passed=True, gate_open=True, proof_sha="")
        journal.append(tmp_path, "station_run", station="M2", slug="s", passed=False, gate_open=False, proof_sha="")
        journal.append(tmp_path, "station_run", station="M3", slug="s", passed=True, gate_open=True, proof_sha="")
        journal.append(tmp_path, "station_run", station="M4", slug="s", passed=True, gate_open=True, proof_sha="")
        journal.append(tmp_path, "station_run", station="M5", slug="s", passed=True, gate_open=True, proof_sha="")
        agg = aggregate(tmp_path)
        assert agg["gate_streak"] == 3

    def test_gate_pass_fail_counts(self, tmp_path):
        journal.append(tmp_path, "station_run", station="M0", slug="s", passed=True, gate_open=True, proof_sha="")
        journal.append(tmp_path, "station_run", station="M1", slug="s", passed=False, gate_open=False, proof_sha="")
        journal.append(tmp_path, "station_run", station="M2", slug="s", passed=False, gate_open=False, proof_sha="")
        agg = aggregate(tmp_path)
        assert agg["gate_pass"] == 1
        assert agg["gate_fail"] == 2

    def test_tool_freq(self, tmp_path):
        capture(tmp_path, kind="tool", tool="Bash", session="s")
        capture(tmp_path, kind="tool", tool="Bash", session="s")
        capture(tmp_path, kind="tool", tool="Read", session="s")
        agg = aggregate(tmp_path)
        assert agg["tool_freq"]["Bash"] == 2
        assert agg["tool_freq"]["Read"] == 1

    def test_empty_root(self, tmp_path):
        agg = aggregate(tmp_path)
        assert agg["delegation_rate"] == 0.0
        assert agg["gate_streak"] == 0
        assert agg["gate_pass"] == 0
        assert agg["gate_fail"] == 0
        assert agg["tool_freq"] == Counter()


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

class TestRender:
    def test_returns_string(self, tmp_path):
        result = render(tmp_path)
        assert isinstance(result, str)

    def test_bounded_12_lines(self, tmp_path):
        # Set up enough data to exercise all sections
        journal.append(tmp_path, "station_run", station="M0", slug="s", passed=True, gate_open=True, proof_sha="")
        journal.append(tmp_path, "delegation", subagent_type="claude", model="", description="d")
        for tool in ["Bash", "Read", "Edit", "Write", "Agent", "Agent", "Bash", "Bash"]:
            capture(tmp_path, kind="tool", tool=tool, session="s")

        # With a transcript
        t = tmp_path / "t.jsonl"
        t.write_text(
            json.dumps({
                "model": "claude-opus-4",
                "usage": {"input_tokens": 100, "output_tokens": 50,
                          "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
            }) + "\n",
            encoding="utf-8",
        )
        result = render(tmp_path, transcript=t)
        lines = result.splitlines()
        assert len(lines) <= 12, f"Expected <=12 lines, got {len(lines)}: {result!r}"

    def test_bounded_12_lines_no_transcript(self, tmp_path):
        result = render(tmp_path)
        lines = result.splitlines()
        assert len(lines) <= 12

    def test_no_raw_series_dump(self, tmp_path):
        # Populate many metric records; the render must NOT include individual ts values
        for i in range(20):
            capture(tmp_path, kind="tool", tool="Bash", session="s")
        result = render(tmp_path)
        # Raw ts like "2026-" should not appear multiple times (only in ARTIFACT line maybe 0)
        # The key invariant: output stays bounded, not raw series
        assert len(result.splitlines()) <= 12

    def test_contains_veredicto_header(self, tmp_path):
        result = render(tmp_path)
        assert result.startswith("VERDICT")

    def test_contains_gates_line(self, tmp_path):
        result = render(tmp_path)
        assert "GATES" in result

    def test_contains_delegacion_line(self, tmp_path):
        result = render(tmp_path)
        assert "DELEGATION" in result

    def test_contains_artefacto_line(self, tmp_path):
        result = render(tmp_path)
        assert "ARTIFACT" in result


# ---------------------------------------------------------------------------
# model_split / render_model_split (B2 — el KPI de costo de DELEG-MEASURE)
# ---------------------------------------------------------------------------

class TestModelSplit:
    from metafactory.memory.metrics import model_split, render_model_split

    def _write_cache(self, path: Path, model_usage: dict) -> Path:
        path.write_text(json.dumps({"modelUsage": model_usage}), encoding="utf-8")
        return path

    def test_normalizes_stats_cache_shape(self, tmp_path):
        from metafactory.memory.metrics import model_split
        c = self._write_cache(tmp_path / "stats.json", {
            "claude-opus-4-8": {"inputTokens": 10, "outputTokens": 20,
                                "cacheCreationInputTokens": 5, "cacheReadInputTokens": 100},
        })
        split = model_split(c)
        assert split["claude-opus-4-8"] == {"input": 10, "output": 20, "cache_creation": 5, "cache_read": 100}

    def test_missing_file_returns_empty(self, tmp_path):
        from metafactory.memory.metrics import model_split
        assert model_split(tmp_path / "nope.json") == {}

    def test_malformed_file_returns_empty(self, tmp_path):
        from metafactory.memory.metrics import model_split
        p = tmp_path / "bad.json"
        p.write_text("not json", encoding="utf-8")
        assert model_split(p) == {}

    def test_render_empty_is_honest_oneliner(self):
        from metafactory.memory.metrics import render_model_split
        out = render_model_split({})
        assert out.startswith("SPLIT")
        assert "absent" in out

    def test_render_aggregates_opus_models_into_one_tier(self):
        from metafactory.memory.metrics import render_model_split
        # two distinct opus model-ids must collapse to a single 'opus' tier share
        split = {
            "claude-opus-4-7": {"input": 0, "output": 1_000_000, "cache_creation": 0, "cache_read": 0},
            "claude-opus-4-8": {"input": 0, "output": 1_000_000, "cache_creation": 0, "cache_read": 0},
        }
        out = render_model_split(split)
        shares = out.split("(")[0]  # the tier-share list, before the explanatory parenthetical
        assert "opus 100%" in shares
        assert "sonnet" not in shares  # no sonnet usage → tier omitted from the shares

    def test_render_shows_tier_split(self):
        from metafactory.memory.metrics import render_model_split
        # opus output cost dominates sonnet → opus share > sonnet share, both present
        split = {
            "claude-opus-4-8": {"input": 0, "output": 1_000_000, "cache_creation": 0, "cache_read": 0},
            "claude-sonnet-4-6": {"input": 0, "output": 1_000_000, "cache_creation": 0, "cache_read": 0},
        }
        out = render_model_split(split)
        assert "opus" in out and "sonnet" in out
        assert out.startswith("SPLIT")
