#!/usr/bin/env python3
"""projection — the gate for the STATE fact-projection law (`v3.memory.projection.is_stale`),
PORTED from v2's `verify/checks/projection.py` (V3-INC5-MEMORY-DOCS, Fase 3).

    python3 -m v3.verify.checks.projection
    V3_PROJECTION_SABOTAGE=1 python3 -m v3.verify.checks.projection   # red side; must ALSO exit 0

GREEN — `is_stale(root)` returns `(False, "ok")`: the projection block committed in `docs/STATE.md`
agrees, byte for byte, with what `build_block(root)` re-derives from the open increment + the
per-factory RTM. The retired parity oracle (`corpus_parity`, retired at V3-EXTRACT-CORPUS-PARITY)
re-derived that this answer matched v2's exactly, on this same tree, every run during the rebuild —
comparing the RTM map AND the rendered block AND the staleness verdict together, not just the bool
(two laws could agree "not stale" while disagreeing about every factory's status, which was the
hollow-agreement shape that oracle existed to catch).

ROOT RESOLUTION mirrors every other v3 gate: default to the repo root
(`Path(__file__).resolve().parents[3]`), overridable by an optional positional path.

THE N/A BRANCH, and why it belongs HERE and not in the ported law. `.proof/` is gitignored
(`.gitignore:10-11`). Measured in a clean clone of this repo: the RTM re-derives to INCOMPLETE for
all five factories (no proof to recompute), which disagrees with whatever RTM line happens to be
committed in `docs/STATE.md` — and v2's gate reports that disagreement as "stale vs. the facts". That
verdict is a false positive on such a tree: it is not that the projection is WRONG, it is that the
FACTS have not been DERIVED yet (`ci --rederive` produces them). Reporting "stale" there would blame
the projection for a fact that has nothing to do with it.

The fix is NOT to soften `is_stale` — that function must keep answering exactly what v2's answers
(the corpus-parity oracle imports both and compares them; folding this decision into the law would
break parity and, worse, would silently change what the law MEANS: "is the committed block wrong?"
would quietly become "is the committed block wrong, except sometimes?"). So the branch lives here,
at the edge, ahead of calling the law at all: when NO factory directory in this tree carries a
`.proof/` at all, this gate reports N/A (SUMMARY `N/A: …`, exit 0, R-12 — never a shade of green,
never a shade of red) and names the remedy. The moment even one factory has re-derived, the branch
does not trigger and the real law runs unmodified.

WHY THE WITNESS IS NEW — v2 has none (`grep -ci sabotage` over `memory/projection.py` at the oracle
ref is 0), exactly the `docs`/`generality` shape: the law plainly has bite (a missing block, a
hand-edited one, a stray duplicate ARE real defects it is supposed to catch) but carries no reachable
red witness of its own. Under `v3.verify.registry`'s registration law a gate needs one to register, so
this port earns one: THREE isolated synthetic trees (a fresh tempdir subtree per class — no git
needed, unlike `docs`'s witness, because nothing in this law shells out to git), each planting exactly
ONE of the defect classes the law is supposed to catch:

  1. block missing      — a `docs/STATE.md` with no projection block at all.
  2. block hand-edited  — a block present, but whose content disagrees with what `build_block`
                           derives for that same tree (the "do NOT hand-edit" rule, with teeth).
  3. legacy marker still replaced — a block written with the LEGACY Spanish START marker (the
                           pre-ADR-026 grammar) must still be FOUND by `refresh()` and replaced IN
                           PLACE, never left stranded while a second, fresh-marker block is appended
                           alongside it. `refresh()` on it must leave EXACTLY one block behind.

The REAL `v3.memory.projection.is_stale` / `refresh` run over each tree; nothing here reimplements
the law, only builds fixtures for it (the same shape `docs`'s `_run_sabotage` uses over
`docs_manifest.check`, and `generality`'s over `audit_mechanism`).

CONTRACT (`v3.verify.registry.Gate.red_run`'s docstring — the opposite of the obvious one): the
sabotage run must exit 0 when it CAUGHT all three classes, printing the catch; it exits 1 with `GATE
DECORATIVO` when any class went unnoticed. Report per-class (`3/3 …`) so a partial catch is visible
rather than silently rounded up to green.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from ...kernel.report import Verdict
from ...memory import projection

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_PROJECTION_SABOTAGE"

_BLOCK_MISSING = "block_missing"
_BLOCK_HAND_EDITED = "block_hand_edited"
_LEGACY_MARKER_REPLACED = "legacy_marker_replaced"
_CLASSES: tuple[str, ...] = (_BLOCK_MISSING, _BLOCK_HAND_EDITED, _LEGACY_MARKER_REPLACED)


def _no_proof_anywhere(root: Path) -> bool:
    """True iff not a single factory directory in this tree carries a `.proof/` — i.e. `ci
    --rederive` has never run here (a fresh clone, `.proof/` is gitignored). On such a tree the RTM
    re-derives INCOMPLETE for every factory and disagrees with whatever RTM line is committed in
    STATE — a real disagreement about DERIVATION, never about the projection law itself."""
    facdir = Path(root) / "factories"
    if not facdir.is_dir():
        return True
    return not any((f / ".proof").is_dir() for f in facdir.iterdir() if f.is_dir())


# ── the three isolated corpora — one class planted, nothing else ───────────────────────────────
def _corpus_block_missing(tmp: Path) -> Path:
    """Class 1: a `docs/STATE.md` with NO projection block at all."""
    root = tmp / _BLOCK_MISSING
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "STATE.md").write_text(
        "# STATE\n\nno projection block anywhere in this doc.\n", encoding="utf-8")
    return root


def _corpus_block_hand_edited(tmp: Path) -> Path:
    """Class 2: a well-formed block present, but its content disagrees with what `build_block`
    derives for this same tree — the "do NOT hand-edit" rule, with teeth."""
    root = tmp / _BLOCK_HAND_EDITED
    (root / "docs").mkdir(parents=True, exist_ok=True)
    bogus = "\n".join([
        projection.START,
        "> Fact projection (Tier 0 → STATE). Source: re-derivable artifacts; not narrative.",
        "- Open increment: a-hand-edited-lie.md",
        "- RTM by factory (re-derived from `.proof/`): nonsense: COMPLETE (999/999)",
        projection.END,
    ])
    (root / "docs" / "STATE.md").write_text(f"# STATE\n\n{bogus}\n\n## Ahora\n", encoding="utf-8")
    return root


def _corpus_legacy_marker(tmp: Path) -> Path:
    """Class 3: a block written with the LEGACY Spanish START marker (pre-ADR-026). `refresh()` must
    FIND it (dual-accept `BLOCK_RE`) and replace it in place, never leave it stranded while a second
    fresh-marker block gets appended alongside it."""
    root = tmp / _LEGACY_MARKER_REPLACED
    (root / "docs").mkdir(parents=True, exist_ok=True)
    legacy = "\n".join([
        projection._LEGACY_START,
        "> Fact projection (Tier 0 → STATE). Source: re-derivable artifacts; not narrative.",
        "- Open increment: none",
        "- RTM by factory (re-derived from `.proof/`): no factories",
        projection.END,
    ])
    (root / "docs" / "STATE.md").write_text(f"# STATE\n\n{legacy}\n\n## Ahora\n", encoding="utf-8")
    return root


def _run_sabotage() -> int:
    caught: list[str] = []
    with tempfile.TemporaryDirectory(prefix="v3-projection-sabotage-") as tmp:
        tmpdir = Path(tmp)

        stale, reason = projection.is_stale(_corpus_block_missing(tmpdir))
        if stale and "missing the projection block" in reason:
            caught.append(_BLOCK_MISSING)

        stale, reason = projection.is_stale(_corpus_block_hand_edited(tmpdir))
        if stale and "stale vs. the facts" in reason:
            caught.append(_BLOCK_HAND_EDITED)

        legacy_root = _corpus_legacy_marker(tmpdir)
        state = legacy_root / "docs" / "STATE.md"
        changed = projection.refresh(legacy_root)
        after = state.read_text(encoding="utf-8")
        n_blocks = len(projection.BLOCK_RE.findall(after))
        if (changed and n_blocks == 1 and projection.START in after
                and projection._LEGACY_START not in after):
            caught.append(_LEGACY_MARKER_REPLACED)

    if len(caught) == len(_CLASSES):
        return Verdict("v3-projection (SABOTAGE)", 0,
                       f"{len(caught)}/{len(_CLASSES)} planted defects caught "
                       f"({', '.join(_CLASSES)})").emit()

    missed = [name for name in _CLASSES if name not in caught]
    return Verdict("v3-projection (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {len(caught)}/{len(_CLASSES)} planted defects caught "
                   f"({', '.join(caught) or 'none'}) — missed {missed}: no teeth on those classes"
                   ).emit()


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        return Verdict("v3-projection", 2, f"takes at most one path argument; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage()

    root = Path(argv[0]) if argv else _ROOT

    if _no_proof_anywhere(root):
        return Verdict("v3-projection", 0,
                       "N/A: no factory in this tree carries a `.proof/` directory — the facts have "
                       "not been derived yet (run `ci --rederive` to derive them first); reporting "
                       "the projection as stale here would be a false positive, not a real one "
                       "(R-12)").emit()

    stale, reason = projection.is_stale(root)
    if stale:
        return Verdict("v3-projection", 1, reason,
                       next_action="run `meta checkpoint` to regenerate the block").emit()

    return Verdict("v3-projection", 0,
                   f"projection fresh ({reason}); red tooth alive ({len(_CLASSES)} defect classes "
                   f"caught under {_SABOTAGE_VAR}=1)").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
