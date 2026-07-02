"""test_pricing_ledger — the two-sided TOOTH for INC-1 PRICING-LEDGER (COST-DOWN, ADR-021).

This test is AUTHORED BY THE ORCHESTRATOR (Opus) and is OUTSIDE the generator's blast radius: it is the
gate that decides the slot, so the generator implements the modules to make it green but may never touch it.
It pins, with EXACT hand-computed dollars, that:
  - the price table is the dated §1.2 DATA (5 columns per model);
  - `price_tokens` and a recorded `LedgerEntry` agree to the cent (the GREEN side);
  - a mis-typed cache entry (bad ttl / negative token) is REJECTED (the RED side);
  - the expiration detector counts mid-session cache_creation spikes two-sided (spike→N, steady→0);
  - the cost block degrades HONESTLY (no transcript → "sin medir", never a fabricated number).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from metafactory.graph import pricing
from metafactory.graph.billing import BillingLedger, LedgerEntry


# ── §1.2 DATA: the dated 5-column table ──────────────────────────────────────────
def test_pricing_is_dated_5col_data():
    assert pricing.AS_OF == "2026-07-02"
    assert pricing.SONNET_PROMO_UNTIL == "2026-08-31"
    opus = pricing.PRICING["opus"]
    # base_input, write_5m, write_1h, hit_refresh, output (USD/MTok) — exactly §1.2
    assert (opus.base_input, opus.write_5m, opus.write_1h, opus.hit_refresh, opus.output) == (5.0, 6.25, 10.0, 0.50, 25.0)
    son = pricing.PRICING["sonnet"]
    assert (son.base_input, son.write_5m, son.write_1h, son.hit_refresh, son.output) == (2.0, 2.50, 4.0, 0.20, 10.0)
    hai = pricing.PRICING["haiku"]
    assert (hai.base_input, hai.write_5m, hai.write_1h, hai.hit_refresh, hai.output) == (1.0, 1.25, 2.0, 0.10, 5.0)


def test_tier_for():
    assert pricing.tier_for("claude-opus-4-8") == "opus"
    assert pricing.tier_for("claude-sonnet-5") == "sonnet"
    assert pricing.tier_for("claude-haiku-4-5") == "haiku"
    assert pricing.tier_for("gpt-4") == "sonnet"  # honest default, never crashes


# ── GREEN side: EXACT price of a known token bundle ──────────────────────────────
def test_exact_price_opus_5m():
    # in 10k·$5 + out 2k·$25 + cc 50k·$6.25(5m) + cr 500k·$0.50 = 0.05+0.05+0.3125+0.25
    usd = pricing.price_tokens("claude-opus-4-8", input_tokens=10_000, output_tokens=2_000,
                               cache_creation=50_000, cache_read=500_000, cache_ttl="5m")
    assert usd == 0.6625


def test_exact_price_sonnet():
    usd = pricing.price_tokens("claude-sonnet-5", input_tokens=100_000, output_tokens=5_000,
                               cache_creation=0, cache_read=50_000)
    assert usd == 0.26


def test_cache_creation_priced_5m_by_default_1h_when_asked():
    # cache_creation is UNTAGGED in the OTLP stream → default 5m (1.25×); 1h only on explicit request.
    five = pricing.price_tokens("claude-opus-4-8", cache_creation=1_000_000, cache_ttl="5m")
    one_h = pricing.price_tokens("claude-opus-4-8", cache_creation=1_000_000, cache_ttl="1h")
    assert five == 6.25 and one_h == 10.0


def test_ledger_entry_agrees_with_price_tokens():
    e = LedgerEntry("mod.py", "generate", "claude-sonnet-5", input_tokens=100_000, output_tokens=5_000,
                    cache_read=50_000)
    led = BillingLedger("run-x").record(e)
    assert e.est_cost_usd == 0.26
    assert led.totals()["est_cost_usd"] == 0.26


# ── RED side: a mis-typed cache entry is REJECTED ────────────────────────────────
def test_bad_cache_ttl_rejected():
    with pytest.raises(ValueError):
        LedgerEntry("m", "generate", "sonnet", cache_ttl="10m")


def test_negative_cache_token_rejected():
    with pytest.raises(ValueError):
        LedgerEntry("m", "generate", "sonnet", cache_creation=-1)


# ── Expiration detector: two-sided (spike → N, steady → 0) ───────────────────────
def test_detect_expirations_counts_spikes():
    from metafactory.memory.metrics import detect_expirations
    # per-turn (cache_creation, cache_read): warm-up write, then steady reads, then ONE mid-session spike.
    spike = [(100_000, 0), (2_000, 100_000), (2_000, 100_000), (90_000, 100_000), (2_000, 100_000)]
    assert detect_expirations(spike) == 1


def test_detect_expirations_steady_is_zero():
    from metafactory.memory.metrics import detect_expirations
    steady = [(100_000, 0), (2_000, 100_000), (2_000, 100_000), (2_000, 100_000)]
    assert detect_expirations(steady) == 0


# ── Cost block degrades HONESTLY (never fabricates an unmeasured number) ──────────
def test_cost_summary_unmeasured_is_none_not_zero(tmp_path: Path):
    from metafactory.verify.cost_report import cost_summary
    s = cost_summary(tmp_path)
    assert s["expirations"] is None          # no transcript → unmeasured, NOT a fake 0
    assert s["tools_per_turn"] is None
    assert s["compactions"] == 0             # re-derivable from an empty series → a real 0
    assert s["churn"] == 0
    assert s["total_usd"] == 0.0             # no ledger → a real 0


def test_cost_summary_totals_a_known_ledger(tmp_path: Path):
    from metafactory.verify.cost_report import cost_summary
    led = BillingLedger("run-x")
    led.record(LedgerEntry("a", "brain", "claude-opus-4-8", input_tokens=10_000, output_tokens=2_000,
                           cache_creation=50_000, cache_read=500_000))   # $0.6625
    led.record(LedgerEntry("b", "generate", "claude-sonnet-5", input_tokens=100_000, output_tokens=5_000,
                           cache_read=50_000))                            # $0.26
    p = led.save(tmp_path / "ledger.json")
    s = cost_summary(tmp_path, ledger=p)
    assert s["total_usd"] == pytest.approx(0.9225)
    # share by tier: opus 0.6625 / 0.9225 ≈ 71.8%, sonnet ≈ 28.2%
    assert s["share_by_tier"]["opus"] == pytest.approx(0.6625 / 0.9225 * 100, abs=0.1)
    assert s["share_by_tier"]["sonnet"] == pytest.approx(0.26 / 0.9225 * 100, abs=0.1)


def test_cost_block_renders_without_fabricating(tmp_path: Path):
    from metafactory.verify.cost_report import cost_block
    block = cost_block(tmp_path)  # no transcript, no ledger
    assert isinstance(block, list) and block
    joined = "\n".join(block).lower()
    assert "sin medir" in joined  # honest about the unmeasured axes
