"""blast_radius — the gate of Fase G's improvement loop (`SELF-IMPROVEMENT.md §4`).

> *"promote only after a verifier proves improvement without widening blast radius"* (autocontext).

A promotion to one factory must not degrade another. This gate RE-DERIVES the verdict of every
factory in the committed baseline (the downstream register) and BLOCKS if ANY falls below its
baseline. The comparison is a HARD FACT (the domination law in `verify.verdict`), never a
judgment — so forcing it is not theatre (SELF-IMPROVEMENT §6).

It reuses the ONE verdict law (`verify.verdict`) so the gate cannot drift from `meta promote`,
and the ONE re-derivation (clean clone, two-verifier doctrine) so custody is never the root of
trust. The negative is NON-decorative (clean_runner doctrine): a baseline demanding MORE than
reality MUST be reported as a regression — if it is not, the comparison has no teeth and the
verdict is prosa (red).

The substrate names no tech and no factory (ADR-012): the sweep set is DATA (the baseline keys).

Argv: <meta_root> <baseline_path>."""
from __future__ import annotations

import sys
from pathlib import Path

from .. import verdict as V


def sweep(meta_root, baseline: dict, verdict_fn=None) -> dict:
    """Re-derive the candidate verdict of every factory in the baseline (the downstream set)."""
    verdict_fn = verdict_fn or V.rederive_verdict
    meta_root = Path(meta_root).resolve()
    out = {}
    for slug in baseline:
        fdir = meta_root / "factories" / slug
        out[slug] = verdict_fn(fdir, meta_root, slug)
    return out


def evaluate(candidates: dict, baseline: dict) -> tuple[bool, list[str]]:
    """The blast-radius law: every baseline factory must still dominate its committed verdict."""
    regressions = []
    for slug, base in baseline.items():
        cand = candidates.get(slug)
        if cand is None:
            regressions.append(f"{slug}: sin verdict candidato (no se pudo re-derivar)")
            continue
        ok, reason = V.dominates(cand, base)
        if not ok:
            regressions.append(f"{slug}: {reason}")
    return (not regressions), regressions


def tooth_ok(candidates: dict, baseline: dict) -> bool:
    """NON-decorative negative: against the freshly re-derived candidates, a baseline that demands
    ONE MORE satisfied requirement than reality MUST be reported as a regression. If it is not, the
    domination law has no teeth and the gate would be prosa."""
    if not baseline:
        return False
    slug0 = next(iter(baseline))
    cand0 = candidates.get(slug0)
    if cand0 is None:
        return False
    harder = dict(baseline[slug0])
    harder["rtm_satisfied"] = cand0.get("rtm_satisfied", 0) + 1
    ok, _ = V.dominates(cand0, harder)
    return ok is False


def decide(candidates: dict, baseline: dict, slug: str, allow_hold: bool = False) -> tuple[str, object]:
    """The PURE promote decision (no I/O), so `meta promote` and its tests share one law. Returns
    (action, detail) where action is:
      - "facade"      : the target did not actually improve (a hold is nothing to promote, §4);
      - "blast"       : a downstream factory would lower its verdict (the blast radius);
      - "decorative"  : the domination law has no teeth (a +1 baseline did not regress);
      - "promote"     : safe to re-pin the target and bump the baseline.
    Every branch is a HARD FACT over re-derived verdicts — never a judgment (SELF-IMPROVEMENT §6)."""
    cand = candidates.get(slug)
    if cand is None:
        return "facade", "sin verdict candidato (no se pudo re-derivar)"
    improved = V.raised(cand, baseline[slug])
    held, hold_reason = V.dominates(cand, baseline[slug])
    if not improved and not (allow_hold and held):
        return "facade", (hold_reason if not held else "el candidato no superó la baseline (hold, no mejora)")
    ok, regressions = evaluate(candidates, baseline)
    if not ok:
        return "blast", regressions
    if not tooth_ok(candidates, baseline):
        return "decorative", None
    return "promote", improved


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: blast_radius <meta_root> <baseline_path>", file=sys.stderr)
        return 2
    meta_root = Path(argv[0]).resolve()
    baseline = V.load_baseline(argv[1])
    if not baseline:
        print(f"SIN BASELINE: {argv[1]} no registra ningún veredicto downstream (nada que proteger)")
        return 1

    candidates = sweep(meta_root, baseline)
    ok, regressions = evaluate(candidates, baseline)
    if not ok:
        print("BLAST-RADIUS ROJO: una promoción bajaría el veredicto de una fábrica downstream:")
        for r in regressions[:8]:
            print(f"           {r}")
        return 1
    if not tooth_ok(candidates, baseline):
        print("GATE DECORATIVO: una baseline que exige +1 SATISFIED NO produjo regresión "
              "(la ley de dominación no tiene dientes; el veredicto sería prosa)")
        return 1

    held = ", ".join(f"{s}={baseline[s].get('rtm_satisfied')}/{baseline[s].get('rtm_total')}"
                     for s in baseline)
    print(f"OK blast-radius: {len(baseline)} fábricas re-derivadas, ninguna bajó su veredicto "
          f"[{held}]; una baseline +1 cae a rojo (la ley tiene dientes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
