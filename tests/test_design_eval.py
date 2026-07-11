"""test_design_eval — the CONTRACT for the `design_eval` gate (ADR-027, EVALUATOR-ROLE F3).

Written by the brain FIRST; the generator implements `metafactory.verify.checks.design_eval` to satisfy it.

The law (two-sided, 0-model, deterministic over PINNED artifacts — mirrors `eval_floor`'s real/degraded idea):
  - opt-in discovery: `factories/<f>/design/criteria.yml`; a root with NO criteria file is green (the gate
    still self-proves via its embedded synthetic negative in `main`);
  - criteria SHAPE: non-empty `axes` (each `{threshold, weight}` numeric), non-empty `slop_penalties` list,
    `covered` list PRESENT (may be empty), `scale` as "MIN-MAX" — malformed → red;
  - NEGATIVE (standing witness): `design/critiques/template-witness.json` MUST exist and score ≥1 axis
    BELOW its threshold; a missing witness OR a witness that PASSES every axis = decorative evaluator → red;
  - POSITIVE: every product in `covered` has `products/<p>/frontend/critique.json` whose `axes` EXACTLY
    match the criteria axes, every score numeric within scale, and ALL axes ≥ threshold — else red;
  - `main` embeds a synthetic self-test (role_hygiene idiom): a synthetic root whose witness passes all
    thresholds must flip `_violations` red, else «GATE DECORATIVO» → exit 1.

Interface (fixed): `_violations(root: Path) -> list[str]` (empty == green) and `main(argv) -> int`
(argv = [<meta_root>]).
"""
from __future__ import annotations

import json
from pathlib import Path

from metafactory.verify.checks import design_eval

REPO = Path(__file__).resolve().parents[1]

CRITERIA = """\
scale: 0-10
axes:
  design_quality: {threshold: 7, weight: 3}
  originality: {threshold: 6, weight: 3}
  craft: {threshold: 7, weight: 1}
  functionality: {threshold: 8, weight: 1}
slop_penalties:
  - purple-gradient-over-white-cards
  - default-framework-look
covered: []
"""


def _factory(tmp_path: Path, slug: str = "demo") -> Path:
    fdir = tmp_path / "factories" / slug
    (fdir / "design" / "critiques").mkdir(parents=True)
    return fdir


def _write_criteria(fdir: Path, text: str = CRITERIA) -> Path:
    p = fdir / "design" / "criteria.yml"
    p.write_text(text, encoding="utf-8")
    return p


def _critique(scores: dict[str, float]) -> str:
    return json.dumps({"axes": {axis: {"score": s} for axis, s in scores.items()}})


FAILING_WITNESS = _critique({"design_quality": 2, "originality": 1, "craft": 6, "functionality": 8})
PASSING_WITNESS = _critique({"design_quality": 9, "originality": 9, "craft": 9, "functionality": 9})


def _write_witness(fdir: Path, payload: str = FAILING_WITNESS) -> Path:
    p = fdir / "design" / "critiques" / "template-witness.json"
    p.write_text(payload, encoding="utf-8")
    return p


def _write_product_critique(fdir: Path, product: str, payload: str) -> Path:
    pdir = fdir / "products" / product / "frontend"
    pdir.mkdir(parents=True)
    p = pdir / "critique.json"
    p.write_text(payload, encoding="utf-8")
    return p


# ── opt-in discovery ───────────────────────────────────────────────────────────
def test_root_with_no_criteria_is_green(tmp_path):
    (tmp_path / "factories" / "bare").mkdir(parents=True)
    assert design_eval._violations(tmp_path) == []


def test_real_repo_main_green(capsys):
    # No factory has opted in yet (meta closes before FSK adopts) — green rides the embedded synthetic
    # negative, which must still prove the law bites.
    assert design_eval.main([str(REPO)]) == 0


# ── criteria shape ─────────────────────────────────────────────────────────────
def test_criteria_empty_axes_red(tmp_path):
    fdir = _factory(tmp_path)
    _write_criteria(fdir, "scale: 0-10\naxes: {}\nslop_penalties: [x]\ncovered: []\n")
    _write_witness(fdir)
    assert design_eval._violations(tmp_path)


def test_criteria_nonnumeric_threshold_red(tmp_path):
    fdir = _factory(tmp_path)
    _write_criteria(fdir, "scale: 0-10\naxes:\n  a: {threshold: high, weight: 1}\n"
                          "slop_penalties: [x]\ncovered: []\n")
    _write_witness(fdir, _critique({"a": 0}))
    assert design_eval._violations(tmp_path)


def test_criteria_empty_slop_penalties_red(tmp_path):
    fdir = _factory(tmp_path)
    _write_criteria(fdir, "scale: 0-10\naxes:\n  a: {threshold: 5, weight: 1}\n"
                          "slop_penalties: []\ncovered: []\n")
    _write_witness(fdir, _critique({"a": 0}))
    assert design_eval._violations(tmp_path)


def test_criteria_missing_covered_red(tmp_path):
    fdir = _factory(tmp_path)
    _write_criteria(fdir, "scale: 0-10\naxes:\n  a: {threshold: 5, weight: 1}\nslop_penalties: [x]\n")
    _write_witness(fdir, _critique({"a": 0}))
    assert design_eval._violations(tmp_path)


# ── the standing witness (NEGATIVE side) ───────────────────────────────────────
def test_missing_witness_red(tmp_path):
    fdir = _factory(tmp_path)
    _write_criteria(fdir)
    problems = design_eval._violations(tmp_path)
    assert problems and any("witness" in p for p in problems)


def test_passing_witness_is_decorative_red(tmp_path):
    # The frozen-template UI must score below threshold somewhere; a witness that passes everything
    # means the evaluator distinguishes nothing.
    fdir = _factory(tmp_path)
    _write_criteria(fdir)
    _write_witness(fdir, PASSING_WITNESS)
    problems = design_eval._violations(tmp_path)
    assert problems and any("witness" in p for p in problems)


def test_failing_witness_green(tmp_path):
    fdir = _factory(tmp_path)
    _write_criteria(fdir)
    _write_witness(fdir)  # design_quality 2 < 7 → the witness fails ≥1 axis → healthy
    assert design_eval._violations(tmp_path) == []


# ── covered products (POSITIVE side) ───────────────────────────────────────────
def _covered_factory(tmp_path) -> Path:
    fdir = _factory(tmp_path)
    _write_criteria(fdir, CRITERIA.replace("covered: []", "covered: [helpdesk]"))
    _write_witness(fdir)
    return fdir


def test_covered_product_missing_critique_red(tmp_path):
    _covered_factory(tmp_path)
    problems = design_eval._violations(tmp_path)
    assert problems and any("helpdesk" in p for p in problems)


def test_covered_product_all_axes_at_threshold_green(tmp_path):
    fdir = _covered_factory(tmp_path)
    _write_product_critique(
        fdir, "helpdesk",
        _critique({"design_quality": 7, "originality": 6, "craft": 7, "functionality": 8}))
    assert design_eval._violations(tmp_path) == []


def test_covered_product_below_threshold_red(tmp_path):
    fdir = _covered_factory(tmp_path)
    _write_product_critique(
        fdir, "helpdesk",
        _critique({"design_quality": 6.9, "originality": 6, "craft": 7, "functionality": 8}))
    problems = design_eval._violations(tmp_path)
    assert problems and any("design_quality" in p for p in problems)


def test_covered_product_axes_mismatch_red(tmp_path):
    # missing an axis AND smuggling an extra one — the axes must match the criteria EXACTLY.
    fdir = _covered_factory(tmp_path)
    _write_product_critique(
        fdir, "helpdesk",
        _critique({"design_quality": 9, "originality": 9, "craft": 9, "invented_axis": 9}))
    assert design_eval._violations(tmp_path)


def test_covered_product_score_out_of_scale_red(tmp_path):
    fdir = _covered_factory(tmp_path)
    _write_product_critique(
        fdir, "helpdesk",
        _critique({"design_quality": 11, "originality": 6, "craft": 7, "functionality": 8}))
    assert design_eval._violations(tmp_path)


def test_covered_product_nonnumeric_score_red(tmp_path):
    fdir = _covered_factory(tmp_path)
    _write_product_critique(
        fdir, "helpdesk",
        json.dumps({"axes": {"design_quality": {"score": "great"}, "originality": {"score": 6},
                             "craft": {"score": 7}, "functionality": {"score": 8}}}))
    assert design_eval._violations(tmp_path)


def test_covered_product_malformed_json_red(tmp_path):
    fdir = _covered_factory(tmp_path)
    pdir = fdir / "products" / "helpdesk" / "frontend"
    pdir.mkdir(parents=True)
    (pdir / "critique.json").write_text("not json {", encoding="utf-8")
    assert design_eval._violations(tmp_path)


# ── the full check: positive + its own embedded negative ──────────────────────
def test_main_green_on_healthy_synthetic_root(tmp_path):
    fdir = _covered_factory(tmp_path)
    _write_product_critique(
        fdir, "helpdesk",
        _critique({"design_quality": 8, "originality": 7, "craft": 8, "functionality": 9}))
    assert design_eval.main([str(tmp_path)]) == 0


def test_main_red_on_decorative_witness(tmp_path):
    fdir = _factory(tmp_path)
    _write_criteria(fdir)
    _write_witness(fdir, PASSING_WITNESS)
    assert design_eval.main([str(tmp_path)]) == 1
