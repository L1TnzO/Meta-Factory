"""design_eval (ADR-027, EVALUATOR-ROLE F3) — the TOOTH that an adopted design-critique evaluator actually
discriminates, opt-in, 0-model (mirrors `eval_floor`'s real/degraded idea, one level up: PINNED critiques
instead of a pinned eval harness).

A factory opts in by publishing `design/criteria.yml` (axes + weights + thresholds + slop penalties +
the list of `covered` products). The gate never scores anything itself — it re-verifies PINNED evidence:

  1. SHAPE — `criteria.yml` must declare a non-empty `axes` mapping (each axis a numeric
     `{threshold, weight}`), a non-empty `slop_penalties` list, a `covered` key (a list, may be empty), and
     a `scale` string of the form "MIN-MAX" (e.g. "0-10"). Malformed -> red (never a traceback).
  2. NEGATIVE (standing witness) — `design/critiques/template-witness.json` MUST exist and score below
     threshold on >=1 axis. A missing witness OR one that passes every axis means the evaluator distinguishes
     nothing (decorative) -> red. This is the same two-sided doctrine as `eval_floor`'s degraded run, except
     the "degraded" fixture here is a STANDING artifact (the frozen template UI), not a substrate-controlled
     re-run.
  3. POSITIVE — every product named in `covered` must carry `products/<p>/frontend/critique.json` (relative
     to the FACTORY, i.e. `factories/<f>/products/<p>/frontend/critique.json`) whose `axes` match the
     criteria's axes EXACTLY (no missing, no extra), every score numeric and within `scale`, and ALL axes
     >= their threshold. Any deviation -> red, naming the product and the offending axis.

`main` re-verifies the real root, THEN runs an embedded synthetic self-test (the `role_hygiene` idiom): a
synthetic root whose witness PASSES every axis must flip `_violations` red; if it doesn't, the law has no
teeth ("GATE DECORATIVO") -> exit 1. A root with NO factory opted in is green on the real check (opt-in),
but the embedded synthetic negative still must bite — a root that never opts in still proves the LAW works.

Interface (fixed, the test contract): `_violations(root: Path) -> list[str]` (empty == green) and
`main(argv: list[str]) -> int` (argv = [<meta_root>]).
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

_SCALE_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)\s*$")


def _is_numeric(value) -> bool:
    """True for int/float, explicitly excluding bool (a bool IS an int in Python — a sneaky `true` must
    never pass as a numeric threshold/weight/score)."""
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
    """Load one YAML file, fail-safe: any read/parse error returns None (never a traceback) — the caller
    reports it as a shape violation, exactly like a missing `axes` mapping."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None


def _load_json(path: Path):
    """Load one JSON file, fail-safe: any read/parse error returns None (never a traceback)."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _criteria_shape_problems(slug: str, raw) -> list[str]:
    """Rule (1): the criteria SHAPE law. Returns shape problems only — callers must NOT trust `axes` /
    `scale` / `covered` for further checks unless this list is empty (a malformed criteria file is not a
    safe foundation to build a witness/product check on top of)."""
    if not isinstance(raw, dict):
        return [f"{slug}: criteria.yml is not a valid YAML mapping"]

    problems: list[str] = []
    axes = raw.get("axes")
    if not isinstance(axes, dict) or not axes:
        problems.append(f"{slug}: criteria.yml `axes` must be a non-empty mapping")
    else:
        for axis, spec in axes.items():
            if not isinstance(spec, dict) or not _is_numeric(spec.get("threshold")) or not _is_numeric(spec.get("weight")):
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
    """Rule (2): the standing witness. Missing, unreadable, malformed, or all-axes-passing -> a violation
    NAMING 'witness' (the test contract greps for that substring)."""
    if not witness_path.exists():
        return [f"{slug}: standing witness design/critiques/template-witness.json is missing "
                f"(the evaluator must prove it can fail something)"]

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

    return [f"{slug}: standing witness template-witness.json passes every axis — a decorative evaluator "
            f"(it must score below threshold on at least one axis)"]


def _product_problems(slug: str, product: str, critique_path: Path, axes: dict,
                       scale: tuple[float, float]) -> list[str]:
    """Rule (3): one covered product's pinned critique. Any deviation names the product + (when
    identifiable) the offending axis; malformed JSON is a violation, never a traceback."""
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
    """The gate's law (single source), opt-in: every `factories/*/design/criteria.yml` re-verified against
    its standing witness (negative) and its covered products' pinned critiques (positive). A root with NO
    criteria file anywhere is green — opt-in, exactly like `design_floor`/`eval_floor`."""
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
    root = Path(argv[0]).resolve() if argv else Path.cwd()

    # 1. the law over the real repo: zero violations == green (opt-in — no factory need have adopted yet).
    problems = _violations(root)
    if problems:
        print(f"DESIGN-EVAL VIOLATION(S) ({len(problems)}):")
        for p in problems[:8]:
            print(f"  - {p}")
        return 1

    # 2. NEGATIVE (not decorative): a synthetic root whose witness PASSES every axis must flip `_violations`
    #    red. If it does not, the standing-witness law has no teeth. Self-contained — no repo clone.
    tmp = Path(tempfile.mkdtemp(prefix="design_eval_"))
    try:
        fdir = tmp / "factories" / "synthetic"
        (fdir / "design" / "critiques").mkdir(parents=True)
        (fdir / "design" / "criteria.yml").write_text(
            "scale: 0-10\n"
            "axes:\n"
            "  design_quality: {threshold: 7, weight: 1}\n"
            "slop_penalties: [purple-gradient-over-white-cards]\n"
            "covered: []\n",
            encoding="utf-8")
        (fdir / "design" / "critiques" / "template-witness.json").write_text(
            json.dumps({"axes": {"design_quality": {"score": 9}}}), encoding="utf-8")
        if not _violations(tmp):
            print("GATE DECORATIVO: un witness que aprueba TODOS los ejes no tiró _violations a rojo "
                  "(sin dientes)")
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    n = len(list(root.glob("factories/*/design/criteria.yml")))
    print(f"OK design_eval: {n} factory/ies opted in; standing witness must fail >=1 axis, covered products "
          f"must meet every threshold (ADR-027)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
