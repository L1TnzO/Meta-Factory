"""delegation — the slot LAW for the verify-not-review delegation loop (ADR-017 §2), part of the
frozen Stage-0 seed.

Single source of the two machine teeth that make cheap delegation SAFE:
  - blast-radius:     a generator subagent may Write ONLY inside its declared slot (PreToolUse exit 2).
  - verdict-required: the generator may not finish without a well-formed verdict file (SubagentStop exit 2).

Zero model, zero `metafactory.*`: pure path/JSON arithmetic — DATA-agnostic (ADR-012), it names no tech,
domain or factory. COPIED VERBATIM into every produced factory (like `verifier.py`/`lifecycle.py`, ADR-018)
so a factory can delegate to a cheap worker with the IDENTICAL teeth: its inherited `blast_radius`/
`verdict_required` hooks load THIS file by path, and the Meta-Factory's own `metafactory.delegation` module
re-exports it through `_seed.load_seed_delegation`, so the factory and the meta enforce the SAME law (no
divergence — the trust-chain single-source principle).

The orchestrator (Opus, via the `generate-slot` skill) writes the slot manifest BEFORE spawning the
generator; this module reads it. Manifest and verdict live under `.gen/` (gitignored — re-derivable
INPUT/verdict, never trust).

A manifest is ACTIVE only while a generation is in flight. With NO manifest both teeth are INERT (exit 0),
so the main session and every other subagent (Explore, etc.) are untouched. Within an active generation the
blast-radius tooth is FAIL-CLOSED: a write it cannot prove is in-slot is blocked — the point is bounding an
autonomous generator, so ambiguity must deny, not allow.
"""
from __future__ import annotations

import fnmatch
import json
from pathlib import Path

SLOT_MANIFEST = ".gen/active_slot.json"
#: a verdict the generator leaves behind: status + which gate it ran + that gate's exit code, by slot.
VERDICT_REQUIRED_KEYS = ("slot_id", "status", "check", "exit_code")
VERDICT_STATUSES = ("green", "red")
#: keys the orchestrator must declare in the manifest before spawning the generator. The gate is SPLIT
#: (HARNESS-FAST-GATE / ADR-021): a FAST `iteration_gate_cmd` re-run EVERY retry (compile + static + the
#: blast-radius-affected tests, budget ≤ ITERATION_BUDGET_MAX_S) and a HEAVY `acceptance_gate_cmd` run ONCE at
#: the end. A manifest without BOTH is rejected here — the measured worst case was a 79-min slot whose only
#: gate was a minutes-long integration run. The verdict's `status: green` requires the acceptance gate to have
#: actually exited 0 (see `verdict_ok`).
MANIFEST_REQUIRED_KEYS = ("slot_id", "allow_globs", "verdict_path", "iteration_gate_cmd", "acceptance_gate_cmd")

#: Slot-size law (D23): DECLARED ceilings the manifest is validated against so the delegation loop stays SHORT.
#: They bound the CONTRACT up front; telemetry compares the actual wall/tokens post-hoc (the full dep-graph
#: test selection is INC-4). A slot that cannot fit these must be split — change-scope == verification-scope.
ITERATION_BUDGET_MAX_S = 15     # the per-retry gate must be quick — re-run every iteration, never minutes.
SLOT_WALL_MAX_S = 1800          # ~30 min wall: a slot that needs longer is too big.

# ── WorkOrder vocab (PWF harvest, ADR-017 Fase 4 PWF-VOCAB-HARVEST) ───────────────────────────────────
# The slot manifest IS a WorkOrder: a bounded unit of delegated work with a governance contract. Professor
# Web Factory had a rich WorkOrder/AgentSpec ontology but NO teeth (its gates passed by construction). We
# harvest the ONTOLOGY and give it teeth: these fields are OPTIONAL (a bare manifest stays valid, backward-
# compatible) but VALIDATED against a CLOSED set when present, so a malformed WorkOrder is rejected BEFORE the
# generator is spawned. They are DATA the orchestrator declares; the substrate names no tech/domain (ADR-012).
#   trust_level   — how much autonomy the slot grants (gates the human/Opus review depth).
#   cost_class    — which model tier should take it (ties to routing-as-data + the billing-ledger).
#   side_effects  — the blast surface BEYOND file writes (network/process), declared up front.
#   model_policy  — determinism knobs for the worker (temperature/seed/strict_json).
TRUST_LEVELS = ("low", "medium", "high")
COST_CLASSES = ("cheap", "standard", "premium")
SIDE_EFFECTS = ("files", "network", "process")
_MODEL_POLICY_KEYS = ("temperature", "seed", "strict_json")


def manifest_path(root: Path) -> Path:
    return Path(root) / SLOT_MANIFEST


def load_slot(root: Path) -> dict | None:
    """The active slot manifest, or None when no generation is in flight."""
    p = manifest_path(root)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def write_slot(root: Path, manifest: dict) -> Path:
    p = manifest_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def clear_slot(root: Path) -> None:
    manifest_path(root).unlink(missing_ok=True)


def manifest_problems(manifest: dict) -> list[str]:
    """Shape teeth for the orchestrator's manifest (so the contract is well-formed before any spawn).
    Required keys must be present; the WorkOrder vocab (PWF harvest) is OPTIONAL but, when declared, must be
    well-formed — a closed enum / right type. An ill-formed WorkOrder is rejected before any generator runs."""
    out = [f"missing `{k}`" for k in MANIFEST_REQUIRED_KEYS if not manifest.get(k)]
    globs = manifest.get("allow_globs")
    if globs is not None and not isinstance(globs, list):
        out.append("`allow_globs` must be a list of path globs")
    # Split gate (HARNESS-FAST-GATE): each declared gate must be a non-empty argv list.
    for gk in ("iteration_gate_cmd", "acceptance_gate_cmd"):
        g = manifest.get(gk)
        if g is not None and not (isinstance(g, list) and g and all(isinstance(t, str) for t in g)):
            out.append(f"`{gk}` must be a non-empty list of command tokens")
    # Slot-size law (D23): declared budgets, validated against the ceilings when present.
    ib = manifest.get("iteration_budget_s")
    if ib is not None and not (isinstance(ib, (int, float)) and not isinstance(ib, bool) and 0 < ib <= ITERATION_BUDGET_MAX_S):
        out.append(f"`iteration_budget_s` must be a number in (0, {ITERATION_BUDGET_MAX_S}] — the iteration gate must stay fast")
    mw = manifest.get("max_wall_s")
    if mw is not None and not (isinstance(mw, (int, float)) and not isinstance(mw, bool) and 0 < mw <= SLOT_WALL_MAX_S):
        out.append(f"`max_wall_s` must be a number in (0, {SLOT_WALL_MAX_S}] — a bigger slot must be split (D23)")
    tb = manifest.get("token_budget")
    if tb is not None and not (isinstance(tb, int) and not isinstance(tb, bool) and tb > 0):
        out.append("`token_budget` must be a positive integer")
    # WorkOrder vocab — validated only when present (backward-compatible).
    tl = manifest.get("trust_level")
    if tl is not None and tl not in TRUST_LEVELS:
        out.append(f"`trust_level` invalid: {tl!r} (expected one of {TRUST_LEVELS})")
    cc = manifest.get("cost_class")
    if cc is not None and cc not in COST_CLASSES:
        out.append(f"`cost_class` invalid: {cc!r} (expected one of {COST_CLASSES})")
    se = manifest.get("side_effects")
    if se is not None:
        if not isinstance(se, list):
            out.append("`side_effects` must be a list")
        else:
            bad = [e for e in se if e not in SIDE_EFFECTS]
            if bad:
                out.append(f"`side_effects` has unknown {bad} (expected a subset of {SIDE_EFFECTS})")
    ft = manifest.get("forbidden_tools")
    if ft is not None and not (isinstance(ft, list) and all(isinstance(t, str) for t in ft)):
        out.append("`forbidden_tools` must be a list of tool names")
    sr = manifest.get("single_responsibility")
    if sr is not None and not (isinstance(sr, str) and sr.strip()):
        out.append("`single_responsibility` must be a non-empty string")
    mp = manifest.get("model_policy")
    if mp is not None:
        if not isinstance(mp, dict):
            out.append("`model_policy` must be an object")
        else:
            unknown = [k for k in mp if k not in _MODEL_POLICY_KEYS]
            if unknown:
                out.append(f"`model_policy` has unknown keys {unknown} (expected a subset of {_MODEL_POLICY_KEYS})")
    return out


def _rel(root: Path, file_path: str) -> str | None:
    """`file_path` (abs or rel) → POSIX path relative to root, or None if it escapes the repo."""
    root = Path(root).resolve()
    fp = Path(file_path)
    fp = fp if fp.is_absolute() else root / fp
    try:
        return fp.resolve().relative_to(root).as_posix()
    except ValueError:
        return None


def write_allowed(root: Path, slot: dict, file_path: str) -> bool:
    """Is writing `file_path` permitted under the active slot? Fail-closed within a generation."""
    rel = _rel(root, file_path)
    if rel is None:
        return False  # escapes the repo → never
    if rel.startswith(".gen/"):
        return True  # the worker's own gitignored scratch + verdict area
    verdict = slot.get("verdict_path", "")
    if verdict and rel == _rel(root, verdict):
        return True
    globs = slot.get("allow_globs") or []
    return any(fnmatch.fnmatch(rel, g) for g in globs)


def verdict_ok(root: Path, slot: dict) -> tuple[bool, str]:
    """Did the generator leave a well-formed verdict at the declared path? (status + gate + exit code)."""
    vp = slot.get("verdict_path", "")
    if not vp:
        return False, "the slot manifest declares no `verdict_path`"
    p = Path(root) / vp
    if not p.exists():
        return False, f"no verdict at {vp} (write it before finishing)"
    try:
        v = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"malformed verdict at {vp}: {e}"
    if not isinstance(v, dict):
        return False, f"verdict at {vp} must be a JSON object"
    missing = [k for k in VERDICT_REQUIRED_KEYS if k not in v]
    if missing:
        return False, f"incomplete verdict at {vp}: missing {missing}"
    if v.get("status") not in VERDICT_STATUSES:
        return False, f"verdict.status invalid: {v.get('status')!r} (expected one of {VERDICT_STATUSES})"
    # A green verdict on a split-gate slot is only real if the HEAVY acceptance gate actually exited 0 — the
    # fast iteration gate passing every retry is necessary but not sufficient (HARNESS-FAST-GATE).
    if v.get("status") == "green" and slot.get("acceptance_gate_cmd"):
        ae = v.get("acceptance_exit_code")
        if ae != 0:
            return (False, f"green verdict but the acceptance gate did not pass (acceptance_exit_code={ae!r}); "
                           f"run `acceptance_gate_cmd` ONCE at the end and record its exit 0")
    return True, f"verdict {v['status']} ({v.get('check', '?')} exit {v.get('exit_code')})"


def affected_tests(root: Path, allow_globs: list[str], tests_dir: str = "tests") -> list[str]:
    """Minimal blast-radius → tests selection (D25): the test files whose name relates to any path the slot may
    write, so the FAST `iteration_gate_cmd` runs only the affected tests, not the whole suite. Deterministic and
    dependency-free (the full dep-graph selection is INC-4). Returns existing `<tests_dir>/test_*.py` paths
    (POSIX, sorted+deduped); an empty result means 'no name-matched test — fall back to the module's own gate'.
    Over-selection is safe (a fast gate that runs one extra test); under-selection is the only real risk."""
    root = Path(root)
    # Generic package/dir names carry no signal — using them as a stem would select the whole suite.
    _GENERIC = {"src", "metafactory", "tests", "test", "seed", "lib", "app", "codegen", "verify"}
    stems: set[str] = set()
    for g in allow_globs or []:
        g = str(g)
        base = Path(g).name.replace("*", "").replace("?", "")
        base = base[:-3] if base.endswith(".py") else base
        parent = Path(g.replace("*", "x").replace("?", "x")).parent.name  # coarse: the module's directory
        for s in (base, parent):
            s = s.strip("_")
            if len(s) >= 3 and s not in _GENERIC:
                stems.add(s)
    tdir = root / tests_dir
    if not stems or not tdir.is_dir():
        return []
    hits: set[str] = set()
    for tf in tdir.glob("test_*.py"):
        tname = tf.stem[len("test_"):]
        if any(s in tname or tname in s for s in stems):
            hits.add(tf.resolve().relative_to(root.resolve()).as_posix())
    return sorted(hits)
