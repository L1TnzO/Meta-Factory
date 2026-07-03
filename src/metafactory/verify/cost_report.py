"""cost_report — the cost BLOCK for `meta outcome` (ADR-021, PRICING-LEDGER INC-1).

Re-derives the "what did this cost?" summary from three ALREADY-EXISTING re-derivable sources: a saved
`BillingLedger` (dollars, tier split), a session transcript (cache-expiration spikes), and the
`.metamem/metrics.jsonl` series (compactions, thrashing/churn, delegation split, tools/turn). It composes,
never re-measures — `cost_summary` is pure aggregation over what the other modules already capture.

Honest-degradation law (ADR-021, the same one `pricing.py` follows): an axis with no measurement is `None`,
never a fabricated `0`. A `total_usd` of `0.0` with NO ledger is a legitimate re-derivable zero (zero
entries, zero cost) — but `expirations`/`tools_per_turn` require a transcript/turn-structure to be
MEANINGFUL at all, so their absence is `None`, not an invented number.
"""
from __future__ import annotations

from pathlib import Path

from ..graph import pricing
from ..graph.billing import BillingLedger
from ..memory import instrument, metrics


def cost_summary(root: Path, transcript: Path | None = None, ledger: Path | None = None) -> dict:
    """The composed cost summary. `root` is the project root (for the `.metamem/` series);
    `transcript` and `ledger` are optional paths — each missing axis degrades HONESTLY (see module doc)."""
    root = Path(root)

    # ── dollars + tier share, from the billing ledger (a real 0.0 with no ledger — zero entries) ──────
    total_usd = 0.0
    share_by_tier: dict[str, float] = {}
    if ledger is not None and Path(ledger).exists():
        led = BillingLedger.load(ledger)
        total_usd = led.totals()["est_cost_usd"]
        by_tier: dict[str, float] = {}
        for e in led.entries:
            by_tier[pricing.tier_for(e.model)] = by_tier.get(pricing.tier_for(e.model), 0.0) + e.est_cost_usd
        if total_usd > 0:
            share_by_tier = {tier: usd / total_usd * 100 for tier, usd in by_tier.items()}

    # ── expirations: meaningless without a transcript → None, not a fake 0 ─────────────────────────────
    expirations: int | None = None
    if transcript is not None:
        expirations = metrics.detect_expirations(metrics.cache_series(transcript))

    # ── churn_share: the INC-5 trigger metric ($ spent re-writing expired/compacted cache), meaningless
    # without a transcript → None, not a fake 0 (same honest-degradation law as `expirations` above).
    churn_share: float | None = None
    if transcript is not None:
        churn_share = metrics.churn_cost_share(transcript)["share"]

    # ── compactions / churn, from the .metamem series (a real 0 with an empty series) ──────────────────
    compactions = len(instrument.compact_series(root))
    churn = instrument.thrashing_rollup(root)["extra_reads"]

    # ── delegated_pct: same ratio convention as `metrics.aggregate` (0.0 with no station_runs is a real,
    # vacuous zero — not "unmeasured"); tools_per_turn NEEDS a turn count to mean anything → None w/o one.
    agg = metrics.aggregate(root)
    delegated_pct = agg["delegation_rate"] * 100
    n_turns = agg["n_station_runs"]
    tools_per_turn: float | None = None
    if n_turns > 0:
        total_tools = sum(agg["tool_freq"].values())
        tools_per_turn = total_tools / n_turns

    return {
        "total_usd": total_usd,
        "share_by_tier": share_by_tier,
        "expirations": expirations,
        "churn_share": churn_share,
        "compactions": compactions,
        "churn": churn,
        "delegated_pct": delegated_pct,
        "tools_per_turn": tools_per_turn,
    }


def cost_block(root: Path, transcript: Path | None = None, ledger: Path | None = None) -> list[str]:
    """A bounded, human-readable rendering of `cost_summary` (for `meta outcome`'s E30 block). Unmeasured
    axes print "sin medir" — never a fabricated number (see module doc)."""
    s = cost_summary(root, transcript=transcript, ledger=ledger)

    lines: list[str] = []
    if s["share_by_tier"]:
        share_str = " · ".join(f"{tier} {pct:.1f}%" for tier, pct in sorted(s["share_by_tier"].items()))
        lines.append(f"COSTO      ${s['total_usd']:.4f} total ({share_str})")
    else:
        lines.append(f"COSTO      ${s['total_usd']:.4f} total" + ("" if s["total_usd"] else " (sin ledger)"))

    exp_str = "sin medir (sin transcript)" if s["expirations"] is None else str(s["expirations"])
    if s["churn_share"] is not None:
        exp_str = f"{exp_str} (cache-churn {s['churn_share'] * 100:.1f}% del gasto)"
    lines.append(f"EXPIRACIONES  {exp_str} · COMPACTACIONES {s['compactions']} · CHURN {s['churn']} re-lectura(s) extra")

    tpt_str = "sin medir" if s["tools_per_turn"] is None else f"{s['tools_per_turn']:.2f}"
    lines.append(f"DELEGADO   {s['delegated_pct']:.1f}% · TOOLS/TURNO {tpt_str}")

    return lines
