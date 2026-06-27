"""least_priv (ADR-018 §3 — least-privilege per level) — the inherited column of each factory is
EXACTLY the least-privilege subset of hooks it governs, declared single-source in `column_scope`, not
the whole meta column copied down by inertia. Two-sided diente, sibling of `column_parity`.

Division of labour with `column_parity`:
  - `column_parity` proves the factory column is BYTE-faithful to the M1 projection (no tampering/drift).
  - `least_priv` proves the SET of hooks is the right SCOPE: no meta-only hook leaked down (least-priv),
    no governed hook missing (complete), and the factory governs strictly LESS than the meta (⊊).
Together: the factory column is exactly the right files, byte-correct, with no more privilege than its level.

What it asserts:
  1. Declaration is sane vs reality: FACTORY_COLUMN ⊊ META_COLUMN (proper subset, not the whole column
     by inertia), and every META_COLUMN role is a real hook file in the meta `.claude/hooks/`.
  2. The projection SOURCE (`template/factory/harness/.claude/hooks/`) == FACTORY_COLUMN exactly.
  3. Every in-tree factory's `.claude/hooks/` == FACTORY_COLUMN exactly (over-priv = meta-only leaked
     down; incomplete = governed hook absent).
  4. Diente RED (synthetic): planting a meta-only hook → flagged over-priv; removing a governed hook →
     flagged incomplete. If the comparator does not bite, the gate is decorative → FAIL.

The scope is substrate CODE, not spec DATA (ADR-018 §4): a factory spec cannot widen its own privilege.

Argv: <meta_root>. Exit 0 = PASS, 1 = FAIL (problems listed)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from metafactory.column_scope import FACTORY_COLUMN, META_COLUMN, META_ONLY, META_ONLY_RATIONALE

_HOOKS_REL = ".claude/hooks"
_TEMPLATE_HOOKS_REL = "template/factory/harness/.claude/hooks"


def _hook_roles(hooks_dir: Path) -> set[str]:
    """The set of hook ROLES installed in a dir = the `*.py` basenames, minus `__pycache__`."""
    if not hooks_dir.is_dir():
        return set()
    return {p.stem for p in hooks_dir.glob("*.py") if "__pycache__" not in p.parts}


def _scope_problems(roles: set[str], expected: frozenset[str], where: str) -> list[str]:
    """Compare an installed role-set against the governed scope. [] = exact match.
    Over-privilege (a meta-only role present) is the least-privilege violation; incomplete (a governed
    role absent) is the completeness violation. Both block."""
    problems: list[str] = []
    for extra in sorted(roles - expected):
        why = META_ONLY_RATIONALE.get(extra, "not governed at this level")
        problems.append(f"{where}: over-privilege — '{extra}' leaked down ({why})")
    for missing in sorted(expected - roles):
        problems.append(f"{where}: incomplete — governed hook '{missing}' absent")
    return problems


def _declaration_problems(meta_root: Path) -> list[str]:
    """The declaration must be sane vs reality (assertion 1)."""
    problems: list[str] = []
    if not (FACTORY_COLUMN < META_COLUMN):  # proper subset
        problems.append(
            "declaration: FACTORY_COLUMN is not a PROPER subset of META_COLUMN "
            "(the factory would inherit the whole meta column by inertia — ADR-018 §3)")
    meta_roles = _hook_roles(meta_root / _HOOKS_REL)
    for phantom in sorted(META_COLUMN - meta_roles):
        problems.append(f"declaration: META_COLUMN role '{phantom}' has no hook file in meta {_HOOKS_REL}")
    return problems


def least_priv_problems(meta_root: Path) -> list[str]:
    """All scope problems across the declaration, the projection source, and every factory. [] = clean."""
    problems = _declaration_problems(meta_root)
    problems += _scope_problems(
        _hook_roles(meta_root / _TEMPLATE_HOOKS_REL), FACTORY_COLUMN, "template (projection source)")
    fdir = meta_root / "factories"
    factories = (sorted(p for p in fdir.iterdir() if (p / "factory.spec.yml").is_file())
                 if fdir.exists() else [])
    for froot in factories:
        problems += _scope_problems(
            _hook_roles(froot / _HOOKS_REL), FACTORY_COLUMN, f"factory '{froot.name}'")
    return problems


def _tooth_bites() -> bool:
    """Diente RED: the comparator MUST flag both an over-privileged and an incomplete factory tree."""
    meta_only_role = next(iter(META_ONLY))                  # e.g. 'session_start'
    governed_role = next(iter(FACTORY_COLUMN))              # e.g. 'proof_protect'

    over = (FACTORY_COLUMN | {meta_only_role})              # planted a meta-only hook
    under = FACTORY_COLUMN - {governed_role}                # removed a governed hook
    over_bites = any("over-privilege" in p for p in _scope_problems(set(over), FACTORY_COLUMN, "synthetic"))
    under_bites = any("incomplete" in p for p in _scope_problems(set(under), FACTORY_COLUMN, "synthetic"))
    return over_bites and under_bites


def main(argv: list[str]) -> int:
    meta_root = Path(argv[0]).resolve() if argv else Path.cwd()

    problems = least_priv_problems(meta_root)
    if problems:
        print("LEAST_PRIV ROJO — la columna de un nivel no respeta el alcance mínimo-privilegio (ADR-018 §3):")
        for p in problems:
            print(f"  ✗ {p}")
        print("  -> ajustá el árbol al alcance de `metafactory.column_scope` (FACTORY_COLUMN); "
              "el alcance es sustrato, no DATA de spec.")
        return 1

    if not _tooth_bites():
        print("LEAST_PRIV DECORATIVO — el comparador no marcó sobre-privilegio NI incompletitud → sin dientes")
        return 1

    fdir = meta_root / "factories"
    nf = len([p for p in fdir.iterdir() if (p / "factory.spec.yml").is_file()]) if fdir.exists() else 0
    print(f"OK least_priv: {nf} fábrica(s) heredan exactamente FACTORY_COLUMN "
          f"({len(FACTORY_COLUMN)} hooks) ⊊ META_COLUMN ({len(META_COLUMN)}); "
          f"{len(META_ONLY)} meta-only fuera; diente RED dos-lados vivo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
