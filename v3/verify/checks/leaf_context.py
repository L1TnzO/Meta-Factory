#!/usr/bin/env python3
"""leaf_context — does what the host injects into a generation leaf (spec §15.6, D2 anti-drift)
actually stay DERIVED and BOUNDED, the way `v3.memory.rehydrate.leaf_context` promises?

    python3 -m v3.verify.checks.leaf_context
    V3_LEAF_CONTEXT_SABOTAGE=1 python3 -m v3.verify.checks.leaf_context   # red side; must ALSO exit 0

WHAT THIS GATE JUDGES. `v3.memory.rehydrate.leaf_context` (V3-INC12 P3, node `N-0086`) derives, for
ONE plan node, the three things D2 (anti-drift, `docs/spec/15-plan-and-memory.md §6`) requires travel
into every generation call: ancestry (why the task exists), the arc's still-open siblings (what else
it owes) and — the node schema carries NO `acceptance` field, §15.6's own gap — a DERIVED closure
statement that says so rather than inventing one. This module never re-derives `ancestry`/`open_set`
itself: every comparison below calls `v3.memory.plan_tree.algebra` a SECOND, independent time and
compares against what `leaf_context` returned (§15.7's `handoff_derived` shape, applied to the leaf).

HERMETIC. Every green assertion runs against SYNTHETIC trees built in a tmpdir — never the live
`plan/tree.json` (the contract's own rule: the live tree changes daily, and a gate that depends on
today's node set would go red for the wrong reason). Exactly ONE assertion
(`_live_dynamic_bound_check`) runs against the live tree, and it picks its subject DYNAMICALLY (the
open node under whichever increment's title names "INC-12" today, never a hardcoded id) so it stays
true as the tree moves — and when there is nothing to pick (the arc fully closed, or no tree at all)
it is silently a no-op, never a failure over a fact about today that is not this gate's to assert.

CORRECTION EARNED BY EXECUTION (same phase, same node — see `v3.memory.rehydrate`'s own module
docstring for the full finding). `arc` is no longer merely `ancestry(...)[0]` (the tree's single
root): it is the nearest ancestor, including the node itself, whose `kind` is `increment` or
`direction` (`rehydrate._resolve_arc`) — a caller-side choice of WHICH root `open_set` receives, never
a second copy of the algebra. `_independent` below recomputes that SAME resolution a second,
independent time (never by importing `_resolve_arc`), so a drift between the two is exactly what this
gate exists to catch.

RED, `V3_LEAF_CONTEXT_SABOTAGE=1` — six planted defects, one per law `leaf_context` must still
refuse, each planted on a COPY of the ported body's own source text (read off disk, the real file
never mutated) and exec'd as a throwaway block — the SUBJECT is sabotaged, never the checking law
(`_check_context` / `_check_no_body_leak` / `_check_raises_on_unknown` below, which is exactly what
the green run also calls):

  1. an open sibling dropped from the payload              — `_check_context` (open_siblings mismatch)
  2. a node BODY (`evidence`) leaked into a rendered title  — `_check_no_body_leak`
  3. ancestry stops short of the tree root                  — `_check_context` (ancestry mismatch)
  4. a fabricated id named in the payload                   — `_check_context` (fabricated id)
  5. an unknown node_id returns silently instead of raising — `_check_raises_on_unknown`
  6. arc resolves to the tree root instead of the nearest
     enclosing increment/direction                          — `_check_context` (arc mismatch)

Per `v3.verify.registry.Gate.red_run`'s contract (the opposite of the obvious one): this sabotage run
exits **0** when it caught all six, printing what it caught; it prints `GATE DECORATIVO` and exits
**1** when any slipped through.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import types
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ...kernel.report import Verdict
from ...memory import plan_tree
from ...memory.rehydrate import UnknownPlanNode, leaf_context
from ..oracle_parity import CannotPlant

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_LEAF_CONTEXT_SABOTAGE"
_REHYDRATE_PATH = _ROOT / "v3" / "memory" / "rehydrate.py"

#: the contract's own bounds (`.gen/CONTRACT-v3-leaf-context.md` "Bounds, enforced not intended") —
#: asserted against here directly rather than reflected off `rehydrate`'s private constants, so a
#: quiet change to those constants shows up as a gate failure rather than a moving target.
_TITLE_LIMIT = 100
_MAX_OPEN_SIBLINGS = 12
_MAX_RENDER_CHARS = 2000

#: the extraction anchor — the FIRST line of the comment block `rehydrate.py` opens the LeafContext
#: section with. Slicing from here to EOF gives a self-contained block (needs only `dataclass`,
#: `Path`, `plan_tree` — none of `journal`/`docs_manifest`/`projection`), the same "extract, don't
#: reimplement" shape `v3.memory.plan_tree.algebra` uses for the spec's own law.
_LEAF_MARKER = "# LeafContext — the SECOND payload (V3-INC12 P3, node"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# SYNTHETIC FIXTURES — built in a tmpdir; the live tree is never read for a green assertion
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _node(parent: str | None, title: str, *, kind: str = "task", state: str = "open",
         trigger: str | None = None, evidence: list[str] | None = None) -> dict:
    n = {"parent": parent, "title": title, "kind": kind, "state": state,
        "evidence": evidence or [], "origin": {"session": "fixture", "cause": "manual"}}
    if trigger is not None:
        n["trigger"] = trigger
    return n


def _build_overflow_tree() -> dict:
    """ROOT(direction) -> MID(increment) -> LEAF (the target, 3-level ancestry — MID is the ARC per
    `rehydrate._resolve_arc`'s nearest-enclosing-increment/direction law, not ROOT) plus 15 siblings
    under MID, not ROOT: the arc's own open siblings must actually live under the arc for the
    12-sibling-cap/overflow assertions below to keep exercising something real. Enough open nodes
    (16 under MID including MID itself, minus LEAF = 16 candidate open_siblings) to overflow the
    12-sibling cap, three siblings with a >100-char title (truncation), one `blocked` with a
    `trigger` (the one field besides id+title `leaf_context` is allowed to surface), and the LEAF
    itself carrying an `evidence` marker that must NEVER leak into a rendered ancestry title."""
    nodes = {
        "R-ROOT": _node(None, "Root direction node for the leaf-context gate fixture", kind="direction"),
        "R-MID": _node("R-ROOT", "Mid increment node", kind="increment"),
        "R-LEAF": _node("R-MID", "Leaf task under test", evidence=["EVIDENCE-SECRET-MARKER"]),
    }
    for i in range(15):
        long_title = f"Sibling task {i:02d} " + ("x" * 90) if i < 3 else f"Sibling task {i:02d}"
        if i == 5:
            nodes[f"R-SIB-{i:02d}"] = _node("R-MID", long_title, state="blocked",
                                            trigger="unblocks when the gate fixture says so")
        else:
            nodes[f"R-SIB-{i:02d}"] = _node("R-MID", long_title)
    return nodes


def _build_nested_arc_tree() -> dict:
    """`direction -> increment -> task -> task` — the correction fixture (found by executing this
    gate against the live project tree; see `v3.memory.rehydrate`'s own module docstring for the
    finding). Proves `arc` resolves to the nearest ENCLOSING increment/direction ancestor, never the
    tree root, on a tree deep enough that the two genuinely differ."""
    return {
        "X-DIR": _node(None, "Top direction node for the arc-resolution gate fixture", kind="direction"),
        "X-INC": _node("X-DIR", "Enclosing increment node", kind="increment"),
        "X-MID": _node("X-INC", "Intermediate task wrapper"),
        "X-DEEP": _node("X-MID", "Deep task under test"),
    }


def _build_deep_tree() -> dict:
    """A single 30-node chain (`D-000` -> ... -> `D-029`, the target) with ~90-char titles — deep
    enough that the ANCESTRY section alone exceeds `_MAX_RENDER_CHARS`, so the overall payload bound
    is genuinely exercised (enforced, not merely never hit)."""
    nodes: dict = {}
    parent = None
    pad = "d" * 60
    for i in range(30):
        nid = f"D-{i:03d}"
        nodes[nid] = _node(parent, f"Deep ancestor {i:03d} {pad}")
        parent = nid
    return nodes


def _fixture_root(root: Path, base: Path, nodes: dict, name: str) -> Path:
    """A tmp root carrying the REAL, unmodified `tools/spec_conformance.py` +
    `docs/spec/15-plan-and-memory.md` (so `plan_tree.algebra` execs the REAL law) plus a SYNTHETIC
    `plan/tree.json` — only the DATA is synthetic, never the law, the same split
    `v3/verify/checks/plan_tree.py`'s own `_run_sabotage` uses for its fixtures."""
    dest = base / name
    (dest / "tools").mkdir(parents=True, exist_ok=True)
    spec_dir = dest / "docs" / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "tools" / "spec_conformance.py", dest / "tools" / "spec_conformance.py")
    shutil.copy2(root / plan_tree.SPEC_DOC, spec_dir / Path(plan_tree.SPEC_DOC).name)
    plan_tree.save(dest, nodes)
    return dest


# ══════════════════════════════════════════════════════════════════════════════════════════════
# THE CHECKING LAW — shared verbatim by the green run and the sabotage run
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _independent(nodes: dict, ns: dict, node_id: str) -> tuple[list[str], str, list[str]]:
    """Recompute ancestry / arc / open_set INDEPENDENTLY from the algebra — never through
    `leaf_context` — so there is something honest to compare its answer against (§15.7's
    `handoff_derived` shape, applied to the leaf). `arc` is resolved by the SAME
    nearest-enclosing-increment/direction law `rehydrate._resolve_arc` applies — written again here,
    not imported, so a drift between the two (the correction's own defect #6) is exactly what this
    duplication exists to catch."""
    chain_ids = ns["ancestry"](nodes, node_id)
    is_arc_kind = lambda nid: nodes[nid].get("kind") in ("increment", "direction")  # noqa: E731
    arc_id = next((nid for nid in reversed(chain_ids) if is_arc_kind(nid)),
                 chain_ids[0] if chain_ids else node_id)
    open_arc_ids = ns["open_set"](nodes, arc_id)
    return chain_ids, arc_id, [n for n in open_arc_ids if n != node_id]


def _check_context(ctx, nodes: dict, chain_ids: list[str], arc_id: str,
                   open_expected: list[str]) -> list[str]:
    """The DERIVED-and-bounded law: ancestry/open_set must equal the independent recomputation, the
    ancestry must reach the actual TREE root (unaffected by the arc-resolution correction — that is
    `ancestry`'s own law, unchanged), `ctx.arc` must equal the independently-resolved ARC (the
    nearest enclosing increment/direction, defect #6's law), no id may be fabricated, and no title
    may exceed the bound. Reused unchanged by the sabotage run — only the `LeafContext` fed in
    differs."""
    problems: list[str] = []
    got_ancestry_ids = [nid for nid, _ in ctx.ancestry]
    if got_ancestry_ids != chain_ids:
        problems.append(f"ancestry ids {got_ancestry_ids} != independently-recomputed {chain_ids}")
    if not got_ancestry_ids or got_ancestry_ids[0] != chain_ids[0]:
        problems.append(f"ancestry does not reach the tree root {chain_ids[0]!r}: {got_ancestry_ids}")
    if ctx.arc != arc_id:
        problems.append(f"ctx.arc {ctx.arc!r} != independently-recomputed arc {arc_id!r}")
    got_sibling_ids = sorted(nid for nid, _ in ctx.open_siblings)
    if got_sibling_ids != sorted(open_expected):
        problems.append(f"open_siblings ids {got_sibling_ids} != independently-recomputed "
                        f"{sorted(open_expected)}")
    fabricated = sorted((set(got_ancestry_ids) | set(got_sibling_ids)) - set(nodes))
    if fabricated:
        problems.append(f"fabricated id(s) not in the tree: {fabricated}")
    for nid, title in (*ctx.ancestry, *ctx.open_siblings):
        if len(title) > _TITLE_LIMIT:
            problems.append(f"{nid}: title exceeds {_TITLE_LIMIT} chars ({len(title)})")
    return problems


def _check_no_body_leak(ctx, forbidden: list[str]) -> list[str]:
    """No node field beyond id/title (and a blocked sibling's own `trigger`) may ever reach the
    render — checked here by NEGATIVE example: a marker planted in a field `leaf_context` must never
    read (`evidence`) must never show up in the rendered text."""
    text = ctx.render()
    return [f"forbidden marker {m!r} leaked into the rendered payload" for m in forbidden if m in text]


def _check_raises_on_unknown(fn: Callable, exc_type: type, root: Path, missing_id: str) -> list[str]:
    try:
        result = fn(root, missing_id)
    except exc_type:
        return []
    except Exception as exc:  # noqa: BLE001 — the WRONG exception is still a miss, name it
        return [f"raised {type(exc).__name__} instead of {exc_type.__name__}: {exc}"]
    return [f"calling leaf_context on absent id {missing_id!r} did not raise "
            f"{exc_type.__name__}; returned {result!r} instead"]


# ══════════════════════════════════════════════════════════════════════════════════════════════
# GREEN
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _live_dynamic_bound_check(root: Path) -> list[str]:
    """The ONE assertion the contract allows against the LIVE tree: find whichever open node sits
    under today's "INC-12" increment — never a hardcoded id — and assert its render stays within
    bound. Nothing to pick (arc closed, or no live tree at all) is a silent no-op: it is a fact about
    today's tree, not a defect this gate exists to report."""
    if not (root / plan_tree.TREE_PATH).is_file():
        return []
    nodes = plan_tree.load(root)
    if not nodes:
        return []
    arc = next((nid for nid, n in nodes.items()
               if n.get("kind") == "increment" and "INC-12" in (n.get("title") or "")), None)
    if arc is None:
        return []
    ns = plan_tree.algebra(root)
    open_ids = ns["open_set"](nodes, arc)
    candidates = [n for n in open_ids if n != arc] or open_ids
    if not candidates:
        return []
    rendered = leaf_context(root, candidates[0]).render()
    if len(rendered) > _MAX_RENDER_CHARS:
        return [f"live node {candidates[0]!r}: render exceeded {_MAX_RENDER_CHARS} chars "
                f"({len(rendered)})"]
    return []


def _green(root: Path) -> Verdict:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="v3-leaf-context-") as tmp:
        base = Path(tmp)

        overflow_nodes = _build_overflow_tree()
        overflow_root = _fixture_root(root, base, overflow_nodes, "overflow")
        ns = plan_tree.algebra(overflow_root)
        chain_ids, arc_id, open_expected = _independent(overflow_nodes, ns, "R-LEAF")
        ctx = leaf_context(overflow_root, "R-LEAF")
        problems += [f"overflow tree: {p}"
                    for p in _check_context(ctx, overflow_nodes, chain_ids, arc_id, open_expected)]
        problems += [f"overflow tree: {p}"
                    for p in _check_no_body_leak(ctx, ["EVIDENCE-SECRET-MARKER"])]

        rendered = ctx.render()
        sib_ids = [nid for nid, _ in ctx.open_siblings if nid.startswith("R-SIB-")]
        shown_sib = [nid for nid, _ in ctx.open_siblings[:_MAX_OPEN_SIBLINGS] if nid in sib_ids]
        hidden_sib = [nid for nid, _ in ctx.open_siblings[_MAX_OPEN_SIBLINGS:] if nid in sib_ids]
        if not hidden_sib:
            problems.append("overflow fixture is too small to exercise the 12-sibling cap — "
                            "tighten the fixture")
        if not all(f"  {nid}  " in rendered for nid in shown_sib):
            problems.append("a sibling within the 12-cap is missing from the render")
        if any(f"  {nid}  " in rendered for nid in hidden_sib):
            problems.append("a sibling beyond the 12-cap leaked into the render")
        overflow_count = len(ctx.open_siblings) - _MAX_OPEN_SIBLINGS
        if overflow_count > 0 and f"and {overflow_count} more open in this arc" not in rendered:
            problems.append(f"render did not summarise the {overflow_count} sibling(s) past the "
                            f"12-cap")
        if "blocked — unblocks when:" not in rendered:
            problems.append("a blocked sibling's trigger did not travel into the open-set line")
        if "no declared acceptance condition" not in ctx.acceptance:
            problems.append("acceptance did not explicitly refuse to assert an undeclared condition")
        if any(nid in ctx.acceptance for nid in sib_ids):
            problems.append("acceptance re-lists sibling ids already printed directly above it in "
                            "the 'Open in this arc' section")
        if len(rendered) > _MAX_RENDER_CHARS:
            problems.append(f"overflow tree: render exceeded {_MAX_RENDER_CHARS} chars")

        problems += [f"overflow tree: {p}" for p in
                    _check_raises_on_unknown(leaf_context, UnknownPlanNode, overflow_root,
                                             "N-DOES-NOT-EXIST")]

        deep_nodes = _build_deep_tree()
        deep_root = _fixture_root(root, base, deep_nodes, "deep")
        deep_rendered = leaf_context(deep_root, "D-029").render()
        if len(deep_rendered) > _MAX_RENDER_CHARS:
            problems.append(f"deep tree: render exceeded {_MAX_RENDER_CHARS} chars "
                            f"({len(deep_rendered)})")
        if "payload bound reached" not in deep_rendered:
            problems.append("deep tree: the 2000-char bound was never actually exercised — the "
                            "fixture must overflow it to prove it is enforced, not merely intended")

        # The correction fixture (found by executing this gate against the live tree — see
        # `v3.memory.rehydrate`'s module docstring): on a `direction -> increment -> task -> task`
        # tree, the deep task's arc must be the enclosing INCREMENT, never the tree root.
        nested_nodes = _build_nested_arc_tree()
        nested_root = _fixture_root(root, base, nested_nodes, "nested-arc")
        nested_ctx = leaf_context(nested_root, "X-DEEP")
        if nested_ctx.arc != "X-INC":
            problems.append(f"nested tree: arc resolved to {nested_ctx.arc!r}, expected the "
                            f"enclosing increment 'X-INC' — NOT the tree root 'X-DIR'")

    problems += _live_dynamic_bound_check(root)

    if problems:
        return Verdict("leaf-context", 1, f"{len(problems)} problem(s)", failures=tuple(problems))
    return Verdict("leaf-context", 0,
                   "derived, bounded and non-fabricating over a synthetic 16-sibling overflow tree, "
                   "a synthetic 30-level ancestry overflow tree, a synthetic nested "
                   "direction->increment->task arc-resolution tree, and (dynamically) the live "
                   "INC-12 arc when one is open",
                   counts={"fixtures": 3})


# ══════════════════════════════════════════════════════════════════════════════════════════════
# RED — patch a COPY of the ported body's own source, exec it, run the SAME checking law over it
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _extract_leaf_block(source: str) -> str:
    idx = source.find(_LEAF_MARKER)
    if idx == -1:
        raise RuntimeError(f"{_LEAF_MARKER!r} not found in {_REHYDRATE_PATH} — the extraction "
                           f"anchor moved; update this gate alongside that edit")
    return source[idx:]


def _exec_leaf_block(source_slice: str) -> dict:
    """The extracted block needs only `dataclass` / `Path` / `plan_tree` (never `journal` /
    `docs_manifest` / `projection`) — seeded here rather than resolved through package-relative
    imports, since a throwaway `exec`'d slice has no package to resolve `from . import ...` against.

    Registered in `sys.modules` for the duration of the `exec` (and popped right after): Python's own
    `@dataclass` processing resolves `cls.__module__` through `sys.modules` while decorating
    `LeafContext`, so a namespace whose `__name__` is not actually THERE raises inside `dataclasses`
    itself, before this gate ever gets a chance to run its own checks — a throwaway module is still a
    module as far as that decorator is concerned."""
    module_name = "v3_sabotage_leaf_context"
    ns: dict = {"__name__": module_name, "dataclass": dataclass, "Path": Path, "plan_tree": plan_tree}
    fake = types.ModuleType(module_name)
    fake.__dict__.update(ns)
    sys.modules[module_name] = fake
    try:
        exec(compile(source_slice, "<leaf_context_block>", "exec"), fake.__dict__)
    finally:
        sys.modules.pop(module_name, None)
    return fake.__dict__


def _replace_lines(src: str, anchor: str, replacement_lines: list[str], span: int) -> str:
    """Replace `span` consecutive physical lines starting at the one whose STRIPPED content equals
    `anchor` — matched by stripped content (never exact original indentation) so the plant functions
    below do not have to hand-reproduce this file's continuation-line whitespace to the column."""
    lines = src.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.strip() == anchor:
            return "".join(lines[:i] + [rl + "\n" for rl in replacement_lines] + lines[i + span:])
    raise CannotPlant(f"anchor {anchor!r} not found in the ported body on disk")


def _plant_sibling_dropped(src: str) -> str:
    return _replace_lines(
        src, "open_siblings = tuple((nid, _sibling_label(nodes[nid]))",
        ['    open_siblings = ()  # SABOTAGE: siblings dropped'], span=2)


def _plant_body_leaked(src: str) -> str:
    return _replace_lines(
        src, 'ancestry = tuple((nid, _truncate(str(nodes[nid].get("title") or ""))) '
             'for nid in chain_ids)',
        ['    ancestry = tuple((nid, _truncate(str(nodes[nid].get("title") or "") + " " + '
         'str(nodes[nid].get("evidence") or ""))) for nid in chain_ids)  # SABOTAGE: body leaked'],
        span=1)


def _plant_ancestry_truncated(src: str) -> str:
    return _replace_lines(
        src, 'ancestry = tuple((nid, _truncate(str(nodes[nid].get("title") or ""))) '
             'for nid in chain_ids)',
        ['    ancestry = tuple((nid, _truncate(str(nodes[nid].get("title") or ""))) '
         'for nid in chain_ids[1:])  # SABOTAGE: root dropped'],
        span=1)


def _plant_fabricated_id(src: str) -> str:
    return _replace_lines(
        src, "open_siblings = tuple((nid, _sibling_label(nodes[nid]))",
        ['    open_siblings = tuple((nid, _sibling_label(nodes[nid])) for nid in open_arc_ids '
         'if nid != node_id) + (("N-FABRICATED-9999", "not real"),)  # SABOTAGE: fabricated id'],
        span=2)


def _plant_unknown_silent(src: str) -> str:
    return _replace_lines(
        src, "if node_id not in nodes:",
        ['    if node_id not in nodes:',
         '        return LeafContext(node=node_id, ancestry=(), open_siblings=(), arc=node_id, '
         'acceptance="")  # SABOTAGE: silent empty context'],
        span=4)


def _plant_arc_is_root(src: str) -> str:
    """Defect #6, the correction's own regression test: revert `arc` to the pre-correction law
    (`chain_ids[0]`, the tree's single root) instead of `_resolve_arc`'s nearest enclosing
    increment/direction — exactly the N-0086 defect this phase found by executing the payload."""
    return _replace_lines(
        src, "arc_id = _resolve_arc(nodes, chain_ids, node_id)",
        ['    arc_id = chain_ids[0] if chain_ids else node_id  # SABOTAGE: root, not enclosing arc'],
        span=1)


_PLANTS: dict[str, Callable[[str], str]] = {
    "sibling-dropped": _plant_sibling_dropped,
    "body-leaked": _plant_body_leaked,
    "ancestry-truncated": _plant_ancestry_truncated,
    "fabricated-id": _plant_fabricated_id,
    "unknown-silent": _plant_unknown_silent,
    "arc-is-root": _plant_arc_is_root,
}


def _run_sabotage(root: Path) -> int:
    caught: list[str] = []
    missed: list[str] = []
    na: list[str] = []
    with tempfile.TemporaryDirectory(prefix="v3-leaf-context-sabotage-") as tmp:
        base = Path(tmp)
        nodes = _build_overflow_tree()
        tmp_root = _fixture_root(root, base, nodes, "sabotage")
        ns = plan_tree.algebra(tmp_root)
        chain_ids, arc_id, open_expected = _independent(nodes, ns, "R-LEAF")
        real_source = _REHYDRATE_PATH.read_text(encoding="utf-8")
        block = _extract_leaf_block(real_source)

        for name, plant_fn in _PLANTS.items():
            try:
                patched = plant_fn(block)
            except CannotPlant as exc:
                na.append(f"{name}: {exc}")
                continue
            sandbox = _exec_leaf_block(patched)
            sabotaged_leaf_context = sandbox["leaf_context"]

            if name == "unknown-silent":
                problems = _check_raises_on_unknown(sabotaged_leaf_context,
                                                     sandbox["UnknownPlanNode"], tmp_root,
                                                     "N-DOES-NOT-EXIST")
            elif name == "body-leaked":
                ctx = sabotaged_leaf_context(tmp_root, "R-LEAF")
                problems = _check_no_body_leak(ctx, ["EVIDENCE-SECRET-MARKER"])
            else:
                ctx = sabotaged_leaf_context(tmp_root, "R-LEAF")
                problems = _check_context(ctx, nodes, chain_ids, arc_id, open_expected)
            (caught if problems else missed).append(name)

    if missed:
        return Verdict("leaf-context (SABOTAGE)", 1,
                       f"GATE DECORATIVO: {len(caught)} caught · {len(na)} n/a · "
                       f"{len(missed)} MISSED {missed}").emit()
    if not caught:
        return Verdict("leaf-context (SABOTAGE)", 1,
                       f"GATE DECORATIVO: every plant is N/A ({na}) — no witness caught anything"
                       ).emit()
    return Verdict("leaf-context (SABOTAGE)", 0,
                   f"{len(caught)} planted defect(s) caught ({', '.join(sorted(caught))}) · "
                   f"{len(na)} n/a ({', '.join(na) or 'none'})",
                   counts={"caught": len(caught), "na": len(na)}).emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("leaf-context", 2, f"takes no arguments; got {argv!r}").emit()
    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage(_ROOT)
    return _green(_ROOT).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
