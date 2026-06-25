"""billing — Fase 5: a per-run / per-work-item token+cost+time ledger. The first instrument of REAL
outcome (cost), and the dogfood of "verificar-no-revisar": it records WHICH model did WHICH work, so
the Opus(brain)/Sonnet(generate)/Haiku(read) split is a measured artifact, not a slogan (ADR-017, VISION §4).

FORM harvested from Professor-Web-Factory's `billing-ledger.json` (per-phase entries with model + token +
cost + latency, plus run totals). We add `role` (brain|generate|read) — the delegation axis this project
cares about — and `source` (harness|estimate) so the ledger is HONEST about which numbers are measured.

Pricing is DATA (ADR-012 spirit): a {model: (usd_per_mtok_in, usd_per_mtok_out)} table passed in. No table
=> cost 0 and `pricing="TBD-no-pricing-config"` (exactly PWF's stance). The estimate is labeled, never faked.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROLES = ("brain", "generate", "read")


@dataclass
class LedgerEntry:
    item: str                 # the work-item (cycle): which module/task
    role: str                 # brain | generate | read
    model: str                # opus | sonnet | haiku | <id>
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0     # harness-reported total when available (else input+output)
    est_cost_usd: float = 0.0
    latency_ms: int = 0
    source: str = "estimate"  # harness | estimate — provenance of the token numbers
    status: str = "complete"

    def __post_init__(self) -> None:
        if self.role not in ROLES:
            raise ValueError(f"role must be one of {ROLES}, got {self.role!r}")
        if not self.total_tokens:
            self.total_tokens = self.input_tokens + self.output_tokens


def _cost(entry: LedgerEntry, pricing: dict | None) -> float:
    if not pricing or entry.model not in pricing:
        return 0.0
    cin, cout = pricing[entry.model]
    return round(entry.input_tokens / 1e6 * cin + entry.output_tokens / 1e6 * cout, 6)


class BillingLedger:
    def __init__(self, run_id: str, currency: str = "USD", pricing: dict | None = None) -> None:
        self.run_id = run_id
        self.currency = currency
        self.pricing = pricing
        self.entries: list[LedgerEntry] = []

    def record(self, entry: LedgerEntry) -> "BillingLedger":
        entry.est_cost_usd = _cost(entry, self.pricing)
        self.entries.append(entry)
        return self

    # ── aggregation ───────────────────────────────────────────────────────────
    def totals(self) -> dict:
        return _sum(self.entries)

    def split_by_model(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for model in sorted({e.model for e in self.entries}):
            sub = [e for e in self.entries if e.model == model]
            agg = _sum(sub)
            agg["items"] = len(sub)
            agg["roles"] = sorted({e.role for e in sub})
            out[model] = agg
        return out

    def split_by_role(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for role in ROLES:
            sub = [e for e in self.entries if e.role == role]
            if sub:
                out[role] = {**_sum(sub), "items": len(sub), "models": sorted({e.model for e in sub})}
        return out

    # ── serde ─────────────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "currency": self.currency,
            "pricing": "TBD-no-pricing-config" if not self.pricing else "estimate-usd-per-mtok",
            "entries": [asdict(e) for e in self.entries],
            "totals": self.totals(),
            "split_by_model": self.split_by_model(),
            "split_by_role": self.split_by_role(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @staticmethod
    def load(path: Path) -> "BillingLedger":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        led = BillingLedger(d.get("run_id", "?"), d.get("currency", "USD"))
        for e in d.get("entries", []):
            led.entries.append(LedgerEntry(**{k: e[k] for k in e if k in LedgerEntry.__dataclass_fields__}))
        return led


def _sum(entries: list[LedgerEntry]) -> dict:
    return {
        "input_tokens": sum(e.input_tokens for e in entries),
        "output_tokens": sum(e.output_tokens for e in entries),
        "total_tokens": sum(e.total_tokens for e in entries),
        "est_cost_usd": round(sum(e.est_cost_usd for e in entries), 6),
        "latency_ms": sum(e.latency_ms for e in entries),
    }


def render_split(led: BillingLedger) -> str:
    """A bounded, human-readable digest of the delegation split (for `meta billing`)."""
    t = led.totals()
    priced = bool(led.pricing) or t["est_cost_usd"] > 0
    lines = [f"BILLING  run {led.run_id} ({led.currency}; pricing={'estimate' if priced else 'TBD'})"]
    lines.append(f"TOTAL    {t['total_tokens']} tok ({t['input_tokens']} in / {t['output_tokens']} out) "
                 f"· ${t['est_cost_usd']} · {len(led.entries)} item(s)")
    for model, agg in led.split_by_model().items():
        lines.append(f"  {model:<8} {agg['total_tokens']:>8} tok · {agg['items']} item(s) · "
                     f"roles={','.join(agg['roles'])} · ${agg['est_cost_usd']}")
    for role, agg in led.split_by_role().items():
        lines.append(f"  [{role:<8}] {agg['total_tokens']:>8} tok · models={','.join(agg['models'])}")
    return "\n".join(lines)
