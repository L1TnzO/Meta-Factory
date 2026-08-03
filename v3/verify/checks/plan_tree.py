#!/usr/bin/env python3
"""plan_tree — the gate node `N-0112` predicted and nobody wired: `plan/tree.json`'s law
(`docs/spec/15-plan-and-memory.md §5`) is executed by `v3.memory.plan_tree`, but until this module
nothing in the registered suite ever asked whether the LIVE tree still obeys it.

    python3 -m v3.verify.checks.plan_tree
    V3_PLAN_TREE_SABOTAGE=1 python3 -m v3.verify.checks.plan_tree   # red side; must ALSO exit 0

THE HIDING PLACE THIS CLOSES. `meta check` already registers a gate named `plan` — it validates
`.gen/plan.json` (delegation WorkOrders) and reports N/A on a tree with no active planning. A reader
scanning the gate list sees `plan` and reasonably concludes the PROJECT's plan is covered; it is a
different artifact wearing the same word. This gate is named `plan_tree` on purpose, so the two
cannot be confused by name again, and it is what actually re-derives `plan_problems` over the
committed `plan/tree.json`.

GREEN, over the LIVE tree:
  - `plan/tree.json` parses and is non-empty;
  - `plan_problems(nodes) == []` (`v3.memory.plan_tree.problems`, which IS `algebra()["plan_problems"]`
    — the function the spec normatively defines, never a local copy);
  - EXTRACTION PARITY: the block `v3.memory.plan_tree.extracted_source` returns is byte-identical to a
    SEPARATE, freshly-imported call to `tools/spec_conformance.py::extract`. The algebra itself cannot
    drift between the two call sites — both exec the SAME extracted text — so the only thing left that
    COULD drift is the extraction step; this is the INC-10 law (porting an executor obliges its parity
    witness) applied to the one seam a later edit could quietly change.

N/A only when there is no `plan/tree.json` at all (the node tree is meta-only, N-0059) — never folded
into PASS (R-12).

RED, `V3_PLAN_TREE_SABOTAGE=1` — five planted defects, one per law this port must still refuse, each
planted on an in-memory / tmpdir COPY (the LIVE `plan/tree.json` is never touched by a sabotage run):

  1. a node marked `done` over an open descendant             (D3 / CONF-P3)
  2. a `done` node with no evidence                            (CONF-P4)
  3. a `blocked` node with no trigger                          (CONF-P4)
  4. an `origin.cause` outside the closed vocabulary           (the capture law)
  5. the extraction marker removed from a disposable spec copy (the algebra is single-source)

Defects 1-4 run the REAL, spec-extracted `plan_problems` (from the REAL, untouched spec document)
against a synthetic malformed tree — only the SUBJECT is sabotaged, never the law, matching every
other gate in this suite (`checks/plan.py`'s own `_RED_FIXTURES` is the sibling pattern). Defect 5
sabotages the DOCUMENT instead (a disposable tmp copy of `docs/spec/15-plan-and-memory.md` with the
marker stripped) and asserts `algebra()` refuses to run rather than silently executing nothing — a
missing law must never look like an empty one.

Per `v3.verify.registry.Gate.red_run`'s contract (the opposite of the obvious one): this sabotage run
exits **0** when it caught all five, printing what it caught; it prints `GATE DECORATIVO` and exits
**1** when any slipped through.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

from ...kernel.report import Verdict
from ...memory import plan_tree
from ...spec.blocks import load_extract

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_PLAN_TREE_SABOTAGE"

# One synthetic tree per CONF-P* law, fed to the REAL `plan_problems` — never a fixture on disk (the
# defect is a Python literal, exactly like `checks/plan.py`'s own witness has none to commit either).
_FIXTURES: dict[str, dict] = {
    "done-over-open-descendant": {
        "R": {"parent": None, "title": "r", "kind": "task", "state": "done", "evidence": ["x"],
             "origin": {"cause": "manual"}},
        "C": {"parent": "R", "title": "c", "kind": "task", "state": "open",
             "origin": {"cause": "manual"}},
    },
    "done-without-evidence": {
        "X": {"parent": None, "title": "x", "kind": "task", "state": "done",
             "origin": {"cause": "manual"}},
    },
    "blocked-without-trigger": {
        "X": {"parent": None, "title": "x", "kind": "task", "state": "blocked",
             "origin": {"cause": "manual"}},
    },
    "cause-outside-vocabulary": {
        "X": {"parent": None, "title": "x", "kind": "task", "state": "open",
             "origin": {"cause": "not-a-real-cause"}},
    },
}
_CLASSES: tuple[str, ...] = (*_FIXTURES, "marker-removed")


def _oracle_extract(root: Path, module: str) -> tuple[str, list[str]]:
    """A SEPARATE call to `v3.spec.blocks.load_extract` — the SAME shared helper
    `v3.memory.plan_tree.extracted_source` also calls, but a fresh, independent module load of its
    own, so this witness does not depend on that module's own import path staying correct (if it did,
    a broken import there would silently make this check vacuous). No `sys.path` mutation either way
    (`v3.verify.import_boundary` rule 2)."""
    extract = load_extract(root)
    return extract(root, module)


def _extraction_parity(root: Path) -> str | None:
    """None when v3's extraction equals the oracle's, byte for byte; otherwise the mismatch."""
    v3_source, _ = plan_tree.extracted_source(root)
    oracle_source, _ = _oracle_extract(root, "plan")
    if v3_source != oracle_source:
        return ("extraction parity broken: v3.memory.plan_tree extracted a DIFFERENT block than "
                "tools/spec_conformance.py::extract — the algebra is single-source; one side stopped "
                "calling the shared extractor")
    return None


def _green(root: Path) -> Verdict:
    tree_path = root / plan_tree.TREE_PATH
    if not tree_path.is_file():
        return Verdict("plan-tree", 0, f"N/A: no `{plan_tree.TREE_PATH}` in this tree — the node "
                       "tree is meta-only (N-0059)")
    nodes = plan_tree.load(root)
    if not nodes:
        return Verdict("plan-tree", 1, f"`{plan_tree.TREE_PATH}` exists but carries zero nodes — "
                       "an empty tree is not a plan")
    probs = plan_tree.problems(root)
    if probs:
        return Verdict("plan-tree", 1, f"{len(probs)} problem(s) in the live tree",
                       failures=tuple(probs))
    mismatch = _extraction_parity(root)
    if mismatch:
        return Verdict("plan-tree", 1, mismatch)
    return Verdict("plan-tree", 0, f"{len(nodes)} node(s) obey the algebra of "
                   f"{plan_tree.SPEC_DOC}; extraction parity with tools/spec_conformance.py holds",
                   counts={"nodes": len(nodes)})


def _run_sabotage(root: Path) -> int:
    ns = plan_tree.algebra(root)   # the REAL law, from the REAL untouched spec — only the fixtures
                                    # below (and the tmp doc copy) are synthetic
    caught: list[str] = []
    for name, fixture in _FIXTURES.items():
        if ns["plan_problems"](fixture):
            caught.append(name)

    with tempfile.TemporaryDirectory(prefix="v3-plan-tree-sabotage-") as tmp:
        tmp_root = Path(tmp)
        (tmp_root / "tools").mkdir(parents=True)
        shutil.copy2(root / "tools" / "spec_conformance.py",
                    tmp_root / "tools" / "spec_conformance.py")
        spec_dir = tmp_root / "docs" / "spec"
        spec_dir.mkdir(parents=True)
        real_text = (root / plan_tree.SPEC_DOC).read_text(encoding="utf-8")
        (spec_dir / Path(plan_tree.SPEC_DOC).name).write_text(
            real_text.replace(plan_tree.MARKER, ""), encoding="utf-8")
        try:
            plan_tree.algebra(tmp_root)
        except Exception:                                          # noqa: BLE001 — any raise IS the catch
            caught.append("marker-removed")

    if len(caught) == len(_CLASSES):
        return Verdict("plan-tree (SABOTAGE)", 0,
                       f"all {len(_CLASSES)} planted defect(s) caught: {sorted(caught)}").emit()
    missed = sorted(set(_CLASSES) - set(caught))
    return Verdict("plan-tree (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {missed} slipped through uncaught").emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("plan-tree", 2, f"takes no arguments; got {argv!r}").emit()
    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage(_ROOT)
    return _green(_ROOT).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
