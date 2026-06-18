"""verdict — the re-derivable VERDICT LEVEL of a factory, and the domination law the
blast-radius gate enforces (Fase G, `SELF-IMPROVEMENT.md §4`).

A promotion (`meta promote`) re-pins a factory toward a better product. The danger is the
trusting-trust danger generalized to coverage: a change that "improves" one factory while
silently LOWERING another's verdict. The gate forbids exactly that — "regenerate-to-improve
replaces the pin only if it re-passes the gate WITHOUT lowering any downstream verdict."

The verdict LEVEL of a factory is a re-derivable quantity (never narrated):
  - `line_green`  : the product line rebuilds e2e from source on a clean tree.
  - `rtm_satisfied` / `rtm_total` : SATISFIED requirements over total (the evidence tree, C4).

This is distinct from CUSTODY (the pinned proof_sha that `meta ci` compares): a promotion
re-pins, so the SHAs legitimately change — what must NOT lower is the COVERAGE/CAPABILITY the
RTM measures and the fact the line still builds. The two concerns compose: `ci` catches a
tampered custody; `blast_radius` catches a lowered verdict.

The substrate names no tech and no factory (ADR-012): a verdict is `(line_green, rtm)` for any
domain; the sweep set is DATA the plan chooses.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path


def rederive_verdict(factory_root, meta_root, slug: str) -> dict:
    """Re-derive `slug`'s verdict on a THROWAWAY clone (custody is never the root of trust —
    replicability is; clean_runner doctrine). Rebuilds the product line from committed source
    and reads the evidence tree. The real factory's `.proof/` is never touched, so the gate
    composes without wiping anyone's state. Returns {line_green, rtm_satisfied, rtm_total}."""
    from ..cli import _run_product_line
    from ..engine import RunContext
    from ..spec.loader import load_spec
    from . import rtm

    factory_root = Path(factory_root).resolve()
    meta_root = Path(meta_root).resolve()
    tmp = Path(tempfile.mkdtemp(prefix=f"verdict_{slug}_"))
    try:
        clone = tmp / "factory"
        shutil.copytree(factory_root, clone,
                        ignore=shutil.ignore_patterns(".proof", "build", "__pycache__"))
        # Re-derive from source: wipe re-derivable state, rebuild the line e2e (hermetic — never
        # leaks into the meta active-station pointer or the journal).
        shutil.rmtree(clone / ".proof", ignore_errors=True)
        shutil.rmtree(clone / "build", ignore_errors=True)
        rc, _ = _run_product_line(clone, meta_root, slug, record_active=False)
        spec = load_spec(clone / "factory.spec.yml")
        v = RunContext(root=clone, meta_root=meta_root, slug=slug).verifier
        nodes = rtm.build_tree(spec, v, clone)
        return {
            "line_green": rc == 0,
            "rtm_satisfied": sum(1 for n in nodes if n.satisfied),
            "rtm_total": len(nodes),
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def dominates(candidate: dict, baseline: dict) -> tuple[bool, str]:
    """The domination law: a candidate verdict must NOT lower a baseline verdict. Returns
    (ok, reason). A regression is a HARD FACT (line broke, or coverage shrank) — never a
    judgment (SELF-IMPROVEMENT §6). Strict by design: this is a safety gate, so a dropped
    requirement is a regression even if the rest holds."""
    if not candidate.get("line_green", False):
        return False, "la línea de producto NO reconstruye verde (regresión de build)"
    if candidate.get("rtm_satisfied", 0) < baseline.get("rtm_satisfied", 0):
        return False, (f"rtm SATISFIED bajó {candidate.get('rtm_satisfied')}"
                       f"<{baseline.get('rtm_satisfied')} (cobertura perdida)")
    if candidate.get("rtm_total", 0) < baseline.get("rtm_total", 0):
        return False, (f"rtm TOTAL bajó {candidate.get('rtm_total')}"
                       f"<{baseline.get('rtm_total')} (requisito desaparecido)")
    return True, ""


def raised(candidate: dict, baseline: dict) -> bool:
    """True iff the candidate STRICTLY improves the baseline (more requirements SATISFIED on a
    green line). Used by `meta promote` to distinguish a real improvement from a hold/façade."""
    return (candidate.get("line_green", False)
            and candidate.get("rtm_satisfied", 0) > baseline.get("rtm_satisfied", 0))


def load_baseline(path) -> dict:
    """The committed downstream verdict register (the level a promotion must not lower)."""
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_baseline(path, verdicts: dict) -> None:
    Path(path).write_text(json.dumps(verdicts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
