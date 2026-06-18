"""scenario_corpus — G2's gate: the engine still BEHAVES across a DIVERSE corpus of spec shapes.

> G-8 root (`ASF-LESSONS §G-8`): "tested in few spec shapes; new forms almost surely uncover cascade."
> The closure (`SELF-IMPROVEMENT.md §4`, ECC 2.0 meta-harness/autocontext): a corpus of scenario-specs
> that exercise the engine over diverse shapes BEFORE promoting.

A scenario is a spec SHAPE + the engine verdict it must produce (the meta-harness pattern: input +
expected output). The harness RE-DERIVES the engine's deterministic M0 decision (`validate`, plus
`design_review` when the scenario declares the design gate) over every scenario and compares it to the
declared expectation. This is a HARD FACT — the engine produces the declared outcome or it does not —
never a judgment (`SELF-IMPROVEMENT.md §6`). Running the validator in-process IS re-derivation from
source (the validator code is the source under test); no custody is involved.

It composes with `blast_radius` (G1): blast_radius protects the downstream factories' VERDICTS; this
protects the engine's BEHAVIOR across spec shapes. Together they gate `meta promote`.

The negative is NON-decorative (clean_runner doctrine) and TWO-SIDED:
  - a `valid` shape the engine REJECTS  → a cascade broke a valid form (red);
  - a `reject` shape the engine ACCEPTS → a tooth was lost (red).
And the DIVERSITY tooth closes G-8 at root: a corpus with too few distinct shapes, or only one
polarity, is itself the regression G-8 names → red.

The substrate names no tech and no factory (ADR-012): the corpus is DATA (the manifest + fixtures).

Argv: <meta_root> [corpus_path]."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

# How diverse must a corpus be before it may gate a promotion (closes G-8 "few spec shapes").
MIN_VALID_SHAPES = 3   # distinct STRUCTURAL signatures among the accepted shapes
MIN_REJECT_TEETH = 3   # distinct validator FAMILIES the rejected shapes trip


def load_corpus(corpus_path) -> tuple[Path, list[dict]]:
    """Read the manifest (DATA). Each entry: {spec, expect: valid|reject, [problem], [gate], [family]}."""
    p = Path(corpus_path)
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return p.parent, list(data.get("scenarios", []) or [])


def run_engine(spec_path: Path, gate: str = "") -> list[str]:
    """The engine's deterministic M0 decision over one spec: `validate` (all 4 families), plus
    `design_review` when the scenario declares the design gate (B2). Pure re-derivation from source."""
    from ...spec.loader import load_spec
    from ...spec.validator import validate
    from ...spec.design import design_review

    spec = load_spec(spec_path)
    problems = list(validate(spec))
    if gate == "design_review":
        problems += [f"design: {x}" for x in design_review(spec)]
    return problems


def evaluate_scenario(entry: dict, corpus_dir: Path) -> tuple[bool, str]:
    """Run the engine over a scenario and compare to its declared expectation. Returns (ok, reason)."""
    spec_rel = entry.get("spec", "")
    spec_path = corpus_dir / spec_rel
    if not spec_path.exists():
        return False, f"{spec_rel}: scenario spec no existe"
    expect = entry.get("expect", "")
    problems = run_engine(spec_path, entry.get("gate", ""))
    if expect == "valid":
        if problems:
            return False, (f"{spec_rel}: forma VÁLIDA rechazada por el motor (regresión) "
                           f"— {problems[0]}")
        return True, ""
    if expect == "reject":
        if not problems:
            return False, (f"{spec_rel}: forma INVÁLIDA aceptada por el motor "
                           f"(tooth perdido: el motor dejó de rechazarla)")
        needle = str(entry.get("problem", "")).strip()
        if needle and not any(needle in p for p in problems):
            return False, (f"{spec_rel}: rechazada, pero por otra razón "
                           f"(esperaba {needle!r}; vi {problems[0]!r})")
        return True, ""
    return False, f"{spec_rel}: expect inválido {expect!r} (esperaba valid|reject)"


def shape_signature(spec) -> tuple:
    """A STRUCTURAL signature of an accepted shape — derived from the spec, not the declared tags, so
    diversity cannot be gamed by relabeling. (station-count bucket, topology class, layers present)."""
    n = len(spec.active_station_ids)
    bucket = "1" if n <= 1 else ("2-3" if n <= 3 else "4+")
    ids = set(spec.active_station_ids)
    indeg: dict[str, int] = {}
    branching = False
    for s in spec.stations:
        deps = [d for d in s.depends_on if d in ids]
        if len(deps) > 1:
            branching = True
        for d in deps:
            indeg[d] = indeg.get(d, 0) + 1
    if any(v > 1 for v in indeg.values()):
        branching = True
    has_dep = any(s.depends_on for s in spec.stations)
    topology = "branching" if branching else ("linear" if has_dep else "flat")
    layers = []
    if spec.capabilities:
        layers.append("caps")
    if isinstance(spec.machinery.raw, dict) and spec.machinery.raw:
        layers.append("machinery")
    if spec.required_primitives:
        layers.append("design")
    return (bucket, topology, frozenset(layers))


def diversity(entries: list[dict], corpus_dir: Path) -> tuple[bool, str]:
    """The DIVERSITY tooth (closes G-8 at root). The corpus must span ENOUGH distinct shapes and trip
    ENOUGH distinct validator families, with BOTH polarities present — otherwise "few spec shapes" is
    itself the regression. Signatures are STRUCTURAL (valid) / declared-family (reject, each verified
    to actually fire by evaluate_scenario), so a degenerate corpus cannot pass."""
    from ...spec.loader import load_spec

    valid_sigs: set[tuple] = set()
    reject_families: set[str] = set()
    for e in entries:
        if e.get("expect") == "valid":
            sp = corpus_dir / e.get("spec", "")
            if sp.exists():
                valid_sigs.add(shape_signature(load_spec(sp)))
        elif e.get("expect") == "reject":
            reject_families.add(str(e.get("family", e.get("problem", "?"))))
    if len(valid_sigs) < MIN_VALID_SHAPES:
        return False, (f"corpus poco diverso: {len(valid_sigs)} formas VÁLIDAS distintas "
                       f"< {MIN_VALID_SHAPES} (G-8: pocas formas de spec)")
    if len(reject_families) < MIN_REJECT_TEETH:
        return False, (f"corpus poco diverso: {len(reject_families)} familias de tooth distintas "
                       f"< {MIN_REJECT_TEETH} (G-8: pocos negativos)")
    return True, f"{len(valid_sigs)} formas válidas distintas · {len(reject_families)} familias de tooth"


def decide(corpus_dir: Path, entries: list[dict]) -> tuple[str, object]:
    """The PURE corpus decision (no I/O beyond reading the fixtures), so `meta promote` and the tests
    share one law. Returns (action, detail) where action is:
      - "empty"      : the corpus has no scenarios (nothing exercising the engine — refuse to gate);
      - "mismatch"   : the engine diverged on a scenario (a cascade — valid rejected or tooth lost);
      - "thin"       : the corpus is too narrow to close G-8 ("few spec shapes");
      - "ok"         : the engine behaves across N diverse scenarios — safe to promote.
    Every branch is a HARD FACT over the re-derived engine verdict — never a judgment (§6)."""
    if not entries:
        return "empty", "corpus vacío (ningún scenario ejercita el motor)"
    mismatches = []
    for e in entries:
        ok, reason = evaluate_scenario(e, corpus_dir)
        if not ok:
            mismatches.append(reason)
    if mismatches:
        return "mismatch", mismatches
    div_ok, div_reason = diversity(entries, corpus_dir)
    if not div_ok:
        return "thin", div_reason
    return "ok", div_reason


def _default_corpus(meta_root: Path) -> Path:
    return Path(meta_root).resolve() / "scenarios" / "corpus.yml"


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: scenario_corpus <meta_root> [corpus_path]", file=sys.stderr)
        return 2
    meta_root = Path(argv[0]).resolve()
    corpus_path = Path(argv[1]) if len(argv) > 1 else _default_corpus(meta_root)
    if not corpus_path.exists():
        print(f"SIN CORPUS: {corpus_path} no existe (nada que ejercitar)")
        return 1
    corpus_dir, entries = load_corpus(corpus_path)
    action, detail = decide(corpus_dir, entries)
    if action == "empty":
        print(f"CORPUS VACÍO: {detail}")
        return 1
    if action == "mismatch":
        print("SCENARIO-CORPUS ROJO: el motor regresó en una forma del corpus:")
        for r in detail[:8]:
            print(f"           {r}")
        return 1
    if action == "thin":
        print(f"CORPUS POCO DIVERSO: {detail}")
        return 1
    n = len(entries)
    print(f"OK scenario-corpus: {n} scenarios diversos, el motor produjo el veredicto declarado en "
          f"cada uno [{detail}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
