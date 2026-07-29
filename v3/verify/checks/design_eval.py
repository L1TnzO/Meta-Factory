#!/usr/bin/env python3
"""design_eval — the TOOTH that an adopted design-critique evaluator actually discriminates
(ADR-027, EVALUATOR-ROLE F3), PORTED from v2's `verify/checks/design_eval.py`. Subject UNCHANGED
(`factories/*/design/criteria.yml` — the factories, never the platform): opt-in, 0-model, mirrors
`eval_floor`'s real/degraded idea one level up — PINNED critiques instead of a pinned eval harness.

    python3 -m v3.verify.checks.design_eval

A factory opts in by publishing `design/criteria.yml` (axes + weights + thresholds + slop penalties +
the list of `covered` products). This gate never scores anything itself — it re-verifies PINNED
evidence:

  1. SHAPE — `criteria.yml` must declare a non-empty `axes` mapping (each axis a numeric
     `{threshold, weight}`), a non-empty `slop_penalties` list, a `covered` key (a list, may be
     empty), and a `scale` string of the form "MIN-MAX" (e.g. "0-10"). Malformed -> red.
  2. NEGATIVE (embedded PINNED-DATA witness) — `design/critiques/template-witness.json` MUST exist
     and score below threshold on >=1 axis. A missing witness OR one that passes every axis means the
     evaluator distinguishes nothing (decorative) -> red. Registered `witness=Witness("pinned_data",
     "factories/full-stack-kotlin/design/critiques/template-witness.json")`: FSK's real, committed
     negative witness (frozen template UI, all 4 axes below threshold) IS this gate's red tooth,
     asserted INSIDE every green run — no separate re-run needed (`Witness.is_embedded`).
  3. POSITIVE — every product named in `covered` must carry `products/<p>/frontend/critique.json`
     (relative to the factory) whose `axes` match the criteria's axes EXACTLY, every score numeric
     and within `scale`, and ALL axes >= threshold. Any deviation -> red, naming the product + axis.

IF THE PINNED WITNESS IS MISSING OR DECORATIVE AT RUN TIME: unlike v2 (which ALSO embeds an
unconditional synthetic self-test — a tempdir witness that passes every axis, asserted to flip
`_violations` red), this gate leans entirely on the REAL committed FSK witness as the registered
tooth: a root with no factory opted in is still green (opt-in, exactly like `design_floor`/
`eval_floor`), but THIS repo already has one opted-in factory (FSK) with a real negative witness, so
the tooth is never vacuous here — the v2-style synthetic tempdir self-test is not reproduced (it
would be redundant with a real, pinned, already-committed negative witness rather than a fabricated
one, and `v3.verify.registry`'s `pinned_data` kind exists precisely so a PORT can point at committed
data instead of manufacturing a scenario at run time).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_WITNESS_REL = "factories/full-stack-kotlin/design/critiques/template-witness.json"
_SCALE_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)\s*$")


def _is_numeric(value) -> bool:
    """True for int/float, explicitly excluding bool (a bool IS an int in Python — a sneaky `true`
    must never pass as a numeric threshold/weight/score)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_scale(text) -> tuple[float, float] | None:
    """Parse a 'MIN-MAX' scale string (e.g. '0-10') into (lo, hi). None if malformed or degenerate
    (hi <= lo) — the caller reports that as a shape violation."""
    if not isinstance(text, str):
        return None
    m = _SCALE_RE.match(text)
    if not m:
        return None
    lo, hi = float(m.group(1)), float(m.group(2))
    if hi <= lo:
        return None
    return lo, hi


def _load_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _criteria_shape_problems(slug: str, raw) -> list[str]:
    """Rule (1): the criteria SHAPE law. Callers must NOT trust `axes`/`scale`/`covered` for further
    checks unless this list is empty."""
    if not isinstance(raw, dict):
        return [f"{slug}: criteria.yml is not a valid YAML mapping"]

    problems: list[str] = []
    axes = raw.get("axes")
    if not isinstance(axes, dict) or not axes:
        problems.append(f"{slug}: criteria.yml `axes` must be a non-empty mapping")
    else:
        for axis, spec in axes.items():
            if (not isinstance(spec, dict) or not _is_numeric(spec.get("threshold"))
                    or not _is_numeric(spec.get("weight"))):
                problems.append(f"{slug}: axis '{axis}' must declare a numeric threshold and weight")

    slop = raw.get("slop_penalties")
    if not isinstance(slop, list) or not slop:
        problems.append(f"{slug}: criteria.yml `slop_penalties` must be a non-empty list")

    if "covered" not in raw or not isinstance(raw.get("covered"), list):
        problems.append(f"{slug}: criteria.yml `covered` must be present as a list (may be empty)")

    if _parse_scale(raw.get("scale")) is None:
        problems.append(f"{slug}: criteria.yml `scale` must be a 'MIN-MAX' string (e.g. '0-10')")

    return problems


def _witness_problems(slug: str, witness_path: Path, axes: dict) -> list[str]:
    """Rule (2): the standing witness. Missing, unreadable, malformed, or all-axes-passing -> a
    violation naming 'witness'."""
    if not witness_path.exists():
        return [f"{slug}: standing witness design/critiques/template-witness.json is missing (the "
                f"evaluator must prove it can fail something)"]

    payload = _load_json(witness_path)
    if not isinstance(payload, dict) or not isinstance(payload.get("axes"), dict):
        return [f"{slug}: standing witness template-witness.json is missing a valid `axes` mapping"]

    witness_axes = payload["axes"]
    for axis, spec in axes.items():
        entry = witness_axes.get(axis)
        if not isinstance(entry, dict):
            continue
        score = entry.get("score")
        if _is_numeric(score) and score < spec["threshold"]:
            return []  # >=1 axis below threshold — the witness is healthy (non-decorative)

    return [f"{slug}: standing witness template-witness.json passes every axis — a decorative "
            f"evaluator (it must score below threshold on at least one axis)"]


def _product_problems(slug: str, product: str, critique_path: Path, axes: dict,
                       scale: tuple[float, float]) -> list[str]:
    """Rule (3): one covered product's pinned critique."""
    prefix = f"{slug}/{product}"
    if not critique_path.exists():
        return [f"{prefix}: covered product is missing products/{product}/frontend/critique.json"]

    payload = _load_json(critique_path)
    if not isinstance(payload, dict) or not isinstance(payload.get("axes"), dict):
        return [f"{prefix}: critique.json is not valid JSON / missing an `axes` mapping"]

    critique_axes = payload["axes"]
    crit_keys, given_keys = set(axes.keys()), set(critique_axes.keys())
    if crit_keys != given_keys:
        missing, extra = sorted(crit_keys - given_keys), sorted(given_keys - crit_keys)
        return [f"{prefix}: critique.json axes must match criteria exactly "
                f"(missing {missing}, extra {extra})"]

    lo, hi = scale
    problems: list[str] = []
    for axis, spec in axes.items():
        entry = critique_axes[axis]
        if not isinstance(entry, dict) or "score" not in entry:
            problems.append(f"{prefix}/{axis}: critique.json entry has no `score`")
            continue
        score = entry["score"]
        if not _is_numeric(score):
            problems.append(f"{prefix}/{axis}: score {score!r} is not numeric")
            continue
        if not (lo <= score <= hi):
            problems.append(f"{prefix}/{axis}: score {score} is out of scale [{lo}-{hi}]")
            continue
        if score < spec["threshold"]:
            problems.append(f"{prefix}/{axis}: score {score} is below threshold {spec['threshold']}")
    return problems


def _violations(root: Path) -> list[str]:
    """The gate's law (single source), opt-in: every `factories/*/design/criteria.yml` re-verified
    against its standing witness (negative) and its covered products' pinned critiques (positive). A
    root with NO factory opted in is green — opt-in, exactly like `design_floor`/`eval_floor`."""
    problems: list[str] = []
    for criteria_path in sorted(root.glob("factories/*/design/criteria.yml")):
        factory_dir = criteria_path.parent.parent
        slug = factory_dir.name
        raw = _load_yaml(criteria_path)

        shape_problems = _criteria_shape_problems(slug, raw)
        if shape_problems:
            problems.extend(shape_problems)
            continue  # a malformed criteria file is not a safe base for the witness/product checks

        axes = raw["axes"]
        scale = _parse_scale(raw["scale"])
        covered = raw["covered"]

        witness_path = factory_dir / "design" / "critiques" / "template-witness.json"
        problems.extend(_witness_problems(slug, witness_path, axes))

        for product in covered:
            critique_path = factory_dir / "products" / str(product) / "frontend" / "critique.json"
            problems.extend(_product_problems(slug, str(product), critique_path, axes, scale))

    return problems


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-design-eval", 2, f"takes no arguments; got {argv!r}").emit()

    # 1. the law over the real repo: zero violations == green (opt-in — no factory need have adopted).
    problems = _violations(_ROOT)
    if problems:
        return Verdict("v3-design-eval", 1, f"{len(problems)} design-eval violation(s)",
                       failures=tuple(problems)).emit()

    # 2. the registered `pinned_data` witness: it must be IN THE TREE and must have failed >=1 axis —
    #    both already implied by `problems == []` above (a missing/decorative witness would have
    #    produced a violation there), asserted explicitly here so the tooth is never accidental.
    witness = _ROOT / _WITNESS_REL
    if not witness.exists():
        return Verdict("v3-design-eval", 1,
                       f"{_WITNESS_REL} is not in the tree — the red witness is missing").emit()

    n = len(list(_ROOT.glob("factories/*/design/criteria.yml")))
    return Verdict("v3-design-eval", 0,
                   f"{n} factory/ies opted in; standing witness fails >=1 axis "
                   f"({_WITNESS_REL}); covered products meet every threshold (ADR-027)").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
