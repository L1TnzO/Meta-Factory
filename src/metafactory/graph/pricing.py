"""pricing — the SINGLE-SOURCE, dated 5-column price table (ADR-021 §1.2, PRICING-LEDGER INC-1).

Every other module that needs a USD number (the billing ledger, the metrics rollup, the cost report)
derives from `PRICING` here — no second table, no drift. Previously `memory/metrics.py` carried its own
stale 2-column table (opus 15/75, an Opus-4.1-era number, 3x over the real Opus price); this module is
the fix: one dated table, everything else derives.

Honest modeling law: the OTLP usage stream reports ONE untagged `cache_creation_input_tokens` count per
message — it does NOT tell us whether that write requested a 5-minute or 1-hour TTL. So `cache_creation`
is priced at `write_5m` by DEFAULT; `write_1h` only applies when the caller explicitly says `cache_ttl=
"1h"` (e.g. a known long-lived cache configuration). `write_1h` is DATA for the §2.3 what-if analysis, not
a default inference — inferring it silently would fabricate a number the stream doesn't support.
"""
from __future__ import annotations

from dataclasses import dataclass

# The date this table was priced (git is authority; bump on re-price). Sonnet's promo pricing (2/10 base/
# output instead of the eventual list price) is time-boxed — SONNET_PROMO_UNTIL marks when to re-check.
AS_OF = "2026-07-02"
SONNET_PROMO_UNTIL = "2026-08-31"


@dataclass(frozen=True)
class ModelPricing:
    """USD per MTok (million tokens), the 5 columns §1.2 prices independently."""
    base_input: float   # a fresh (non-cached) input token
    write_5m: float      # cache_creation, 5-minute TTL (the OTLP-stream default — untagged)
    write_1h: float       # cache_creation, 1-hour TTL (only when explicitly requested)
    hit_refresh: float    # cache_read (a cache hit also refreshes the TTL)
    output: float          # a generated output token


# §1.2 DATA — the dated table. Do not hand-edit a derived number elsewhere; edit HERE and let it flow.
PRICING: dict[str, ModelPricing] = {
    "opus":   ModelPricing(base_input=5.0, write_5m=6.25, write_1h=10.0, hit_refresh=0.50, output=25.0),
    "sonnet": ModelPricing(base_input=2.0, write_5m=2.50, write_1h=4.0, hit_refresh=0.20, output=10.0),
    "haiku":  ModelPricing(base_input=1.0, write_5m=1.25, write_1h=2.0, hit_refresh=0.10, output=5.0),
}

# Tier-detection order matters: a model id may contain both substrings in synthetic/test ids (e.g.
# "haiku-sonnet"); haiku is checked first so precedence is deterministic. Unknown ids default to sonnet
# (the honest middle tier — never crashes on an unrecognized model id).
_TIER_ORDER = ("opus", "haiku", "sonnet")


def tier_for(model_id: str) -> str:
    """Map a model-id (any casing, any vendor string) to a `PRICING` key by substring. Defaults to
    'sonnet' when no known tier substring is present — an honest default, never a crash."""
    lowered = model_id.lower()
    for tier in _TIER_ORDER:
        if tier in lowered:
            return tier
    return "sonnet"


def price_tokens(
    model_id: str,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_creation: int = 0,
    cache_read: int = 0,
    cache_ttl: str = "5m",
) -> float:
    """The EXACT USD cost of a token bundle, rounded to 6 decimal places (cent-fraction precision for
    small per-item entries). `cache_creation` prices at `write_5m` unless `cache_ttl == "1h"`."""
    p = PRICING[tier_for(model_id)]
    write_price = p.write_1h if cache_ttl == "1h" else p.write_5m
    usd = (
        input_tokens / 1e6 * p.base_input
        + output_tokens / 1e6 * p.output
        + cache_creation / 1e6 * write_price
        + cache_read / 1e6 * p.hit_refresh
    )
    return round(usd, 6)
