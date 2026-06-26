"""outcome — the per-increment OUTCOME instrument (ADR-017 §4, DELEGATION-HARNESS Fase 4).

ADR-017: `meta increment close` verifies process compliance (clean tree + green station), not whether the
promised SCOPE was delivered, and nothing made "was it worth it?" decidable. This re-derives the two outcome
quantities the engineer can reason with:
  - RTM coverage per factory (satisfied/total), re-derived from `.proof/` + specs (I-3) — the VALUE delivered.
  - deferral accumulation (tracked/total declared-deferred) — the DEBT, re-derived from specs.
plus a pointer to the increment's billing-ledger (the COST). A `baseline` snapshot turns these into Δ
("RTM +1, cost N tokens") so "done" and "worth it" stop being narrated and become a re-derivable card.

Snapshots are plain JSON (re-derivable, not the root of trust). Nothing here names a tech/domain (ADR-012).
"""
from __future__ import annotations

import json
from pathlib import Path


def factory_rtm_counts(meta_root: Path) -> dict[str, dict]:
    """{slug: {satisfied, total}} re-derived from each factory's evidence tree (`.proof/` + spec)."""
    from ..engine import RunContext
    from ..spec.loader import load_spec
    from . import rtm

    out: dict[str, dict] = {}
    for sp in sorted(meta_root.glob("factories/*/factory.spec.yml")):
        slug = sp.parent.name
        try:
            spec = load_spec(sp)
            ctx = RunContext(root=sp.parent, meta_root=meta_root, slug=slug)
            nodes = rtm.build_tree(spec, ctx.verifier, sp.parent)
            out[slug] = {"satisfied": sum(1 for n in nodes if n.satisfied), "total": len(nodes)}
        except Exception as e:  # an unbuildable factory is reported, never faked (SAFE-7)
            out[slug] = {"satisfied": 0, "total": 0, "error": str(e)[:80]}
    return out


def deferral_accumulation(meta_root: Path) -> dict[str, dict]:
    """{slug: {tracked, total}} of structural declared-deferred entries (the gateable debt signal)."""
    from ..spec.loader import load_spec
    from .checks.declared_deferred import count_deferrals

    out: dict[str, dict] = {}
    for sp in sorted(meta_root.glob("factories/*/factory.spec.yml")):
        try:
            total, tracked = count_deferrals(load_spec(sp))
            out[sp.parent.name] = {"tracked": tracked, "total": total}
        except Exception:
            continue
    return out


def snapshot(meta_root: Path) -> dict:
    return {"rtm": factory_rtm_counts(meta_root), "deferrals": deferral_accumulation(meta_root)}


def _rtm_totals(snap: dict) -> tuple[int, int]:
    rtm = snap.get("rtm", {})
    return sum(v.get("satisfied", 0) for v in rtm.values()), sum(v.get("total", 0) for v in rtm.values())


def render(snap: dict, baseline: dict | None = None, ledger_path: Path | None = None,
           ledger_digest: str | None = None) -> str:
    sat, tot = _rtm_totals(snap)
    lines = ["OUTCOME  (re-derivado de .proof/ + specs; no narrado)"]
    if baseline is not None:
        bsat, btot = _rtm_totals(baseline)
        lines.append(f"RTM      {sat}/{tot} requisitos SATISFIED  (Δ satisfechos {sat - bsat:+d} · "
                     f"Δ total {tot - btot:+d} vs baseline)")
    else:
        lines.append(f"RTM      {sat}/{tot} requisitos SATISFIED (todas las fábricas)")
    for slug, v in snap.get("rtm", {}).items():
        delta = ""
        if baseline:
            bv = baseline.get("rtm", {}).get(slug, {})
            d = v.get("satisfied", 0) - bv.get("satisfied", 0)
            delta = f"  (Δ {d:+d})" if d else ""
        err = f"  ⚠ {v['error']}" if v.get("error") else ""
        lines.append(f"  {slug:<24} {v.get('satisfied', 0)}/{v.get('total', 0)}{delta}{err}")

    dtot = sum(v["total"] for v in snap.get("deferrals", {}).values())
    dtr = sum(v["tracked"] for v in snap.get("deferrals", {}).values())
    lines.append(f"DEFERRALS {dtr}/{dtot} tracked (deuda estructural declared-deferred; el resto en prosa = invisible)")

    if ledger_digest:
        lines.append("COSTO    " + ledger_digest)
    elif ledger_path:
        lines.append(f"COSTO    billing-ledger: {ledger_path} (corré `meta billing {ledger_path}`)")
    else:
        lines.append("COSTO    (sin billing-ledger para este incremento; `meta billing <ledger.json>`)")
    return "\n".join(lines)


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(snap: dict, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
