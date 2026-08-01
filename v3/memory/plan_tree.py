#!/usr/bin/env python3
"""plan_tree — the PROJECT's node tree (`plan/tree.json`), executing the spec's algebra rather than
copying it (V3-INC12 P2, node `N-0112`).

WHY THIS FILE OWNS NO LAW OF ITS OWN. `docs/spec/15-plan-and-memory.md §5` carries the block marked
`<!-- spec-impl: plan -->` and states it is the ONLY implementation. Before this increment,
`tools/plan.py` extracted that block and executed it, and nothing inside `v3/` did the same — the
tree's verb and its `check` sat outside the substrate, invoked by no gate (worse: `meta check`
registers a DIFFERENT gate also named `plan`, over `.gen/plan.json` WorkOrders, and reports N/A here —
the name is the hiding place `v3.verify.checks.plan_tree` closes). This module is the port: storage,
access to the algebra, and the ten command bodies — all delegating the LAW itself to the spec document
every time. Transcribing `effective_state` / `open_set` / `next_actionable` / `ancestry` /
`node_problems` / `structure_problems` / `plan_problems` / `drift_metrics` / `render_handoff` into this
file would create a second copy that drifts silently — the exact defect this phase exists to remove.
Duplicating the short CALL to the shared extractor (`tools/spec_conformance.py::extract`) is fine — a
transport is not a law — and `v3.verify.checks.plan_tree`'s extraction-parity witness is what proves
this file still only transports.

`tools/plan.py` is now a thin compatibility shim over this module: it forwards CLI argv to `v3.cli`
and re-exports the handful of zero-arg functions `tools/plan_capture.py` / `tools/handoff_check.py`
still import directly (both out of this slot's scope). `v3/cli.py` dispatches `meta plan-tree <verb>` here.

Bounded output (I-7): every `cmd_*` below returns a `Verdict` whose summary/counts stay short — a
125-node tree must never ride in a Verdict. `render_tree_text` / `render_handoff_text` return the
FULL, unbounded text `v3.cli` prints straight to stdout for `show`/`handoff` — the caller's own text,
never the bus.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from ..kernel.report import Verdict

TREE_PATH = "plan/tree.json"
SPEC_DOC = "docs/spec/15-plan-and-memory.md"
MARKER = "<!-- spec-impl: plan -->"

#: state -> one-character mark, shared by both text renderers below.
_MARK = {"open": "○", "blocked": "◍", "done": "●", "dropped": "⊘"}


# ── the algebra: extracted from the spec, never copied ──────────────────────────────────────────
def extracted_source(root: Path) -> tuple[str, list[str]]:
    """The raw `<!-- spec-impl: plan -->` block(s), concatenated in filename/document order — exactly
    what `algebra()` execs, and exactly what `v3.verify.checks.plan_tree`'s extraction-parity witness
    compares against a SEPARATE, freshly-imported call to `tools/spec_conformance.py::extract` (the
    parity is true by construction today; the witness is what keeps it true after a later edit)."""
    root = Path(root)
    tools_dir = str(root / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    from spec_conformance import extract  # the ONE extractor, shared with the conformance gate
    return extract(root, "plan")


def algebra(root: Path) -> dict:
    """Load the NORMATIVE plan algebra out of the specification document and exec it into a fresh
    namespace. Raises if the marker or the block is missing — a missing law is never an empty law."""
    source, files = extracted_source(root)
    if not source.strip():
        raise RuntimeError(f"no `{MARKER}` block in {SPEC_DOC} — the algebra is specified there, "
                           f"not transcribed here")
    ns: dict = {"__name__": "spec_plan", "__spec_files__": files}
    exec(compile(source, "<spec:plan>", "exec"), ns)
    return ns


# ── storage (I-8: memory is a repo artifact; committed, diff-friendly) ──────────────────────────
def load(root: Path) -> dict:
    p = Path(root) / TREE_PATH
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get("nodes", {})


def save(root: Path, nodes: dict) -> None:
    p = Path(root) / TREE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "_doc": "The plan tree. Law and algebra: docs/spec/15-plan-and-memory.md (normative). "
                "Operated by v3.memory.plan_tree (`v3 plan-tree …` / `tools/plan.py`, a thin shim over it). "
                "Ids are append-only and never renumbered.",
        "nodes": dict(sorted(nodes.items())),
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def problems(root: Path) -> list[str]:
    return algebra(root)["plan_problems"](load(root))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _session() -> str:
    return _now()[:10]


def _new_id(nodes: dict) -> str:
    used = [int(k.split("-")[1]) for k in nodes if k.startswith("N-") and k.split("-")[1].isdigit()]
    return f"N-{max(used, default=0) + 1:04d}"


def _missing(nodes: dict, node_id: str, verb: str) -> Verdict | None:
    if node_id not in nodes:
        return Verdict(verb, 1, f"node {node_id} does not exist")
    return None


# ── command bodies — PORTED from tools/plan.py; only the return shape changes (Verdict, never a
# print + sys.exit). Same id allocation, same origin vocabulary, same refusals. ─────────────────
def cmd_show(root: Path, node_root: str | None) -> Verdict:
    root = Path(root)
    nodes = load(root)
    if not nodes:
        return Verdict("plan show", 0, "empty plan — no node in `plan/tree.json`", counts={"total": 0})
    ns = algebra(root)
    open_n = len(ns["open_set"](nodes, None))
    done_n = len([k for k, n in nodes.items() if n.get("state") == "done"])
    drop_n = len([k for k, n in nodes.items() if n.get("state") == "dropped"])
    nxt = ns["next_actionable"](nodes, node_root)
    return Verdict("plan show", 0,
                   f"{len(nodes)} node(s) — {open_n} open, {done_n} done, {drop_n} dropped",
                   counts={"open": open_n, "done": done_n, "dropped": drop_n, "total": len(nodes)},
                   next_action=(f"next: {nxt}  ({nodes[nxt]['title']})" if nxt
                                else "nothing actionable"))


def render_tree_text(root: Path, node_root: str | None) -> str:
    """The FULL structural render `v3.cli` prints to stdout for `plan show` — never routed through a
    Verdict (I-7: a 125-node tree must not ride the bounded bus)."""
    root = Path(root)
    nodes = load(root)
    if not nodes:
        return "(empty plan)"
    ns = algebra(root)
    roots = ([node_root] if node_root else
            sorted(k for k, n in nodes.items() if n.get("parent") is None))
    lines: list[str] = []

    def walk(nid: str, depth: int) -> None:
        n = nodes[nid]
        eff = ns["effective_state"](nodes, nid)
        own = n.get("state")
        mark = _MARK.get(own, "?")
        flag = "" if own == eff else f"  [effective: {eff}]"
        note = ""
        if own == "blocked":
            note = f"  <- trigger: {n.get('trigger')}"
        elif own == "dropped":
            note = f"  <- dropped: {n.get('drop_reason')}"
        lines.append(f"{'  ' * depth}{mark} {nid}  {n.get('title')}{flag}{note}")
        for c in ns["children_of"](nodes, nid):
            walk(c, depth + 1)

    for r in roots:
        if r in nodes:
            walk(r, 0)
    total = len(nodes)
    open_n = len(ns["open_set"](nodes, None))
    done_n = len([k for k, n in nodes.items() if n.get("state") == "done"])
    drop_n = len([k for k, n in nodes.items() if n.get("state") == "dropped"])
    nxt = ns["next_actionable"](nodes, node_root)
    lines.append(f"\nSUMMARY    {open_n} open · {done_n} done · {drop_n} dropped · "
                f"{total} total")
    lines.append(f"NEXT       {nxt or '— nothing actionable'}"
                + (f"  ({nodes[nxt]['title']})" if nxt else ""))
    return "\n".join(lines)


def cmd_next(root: Path, node_root: str | None) -> Verdict:
    root = Path(root)
    nodes = load(root)
    ns = algebra(root)
    nid = ns["next_actionable"](nodes, node_root)
    if not nid:
        return Verdict("plan next", 0, "nothing actionable in scope")
    chain = ns["ancestry"](nodes, nid)
    why = " -> ".join(f"{c}:{nodes[c]['title']}" for c in chain)
    siblings = [s for s in ns["open_set"](nodes, chain[0]) if s != nid]
    return Verdict("plan next", 0, f"{nid}: {nodes[nid]['title']}",
                   counts={"arc_open_siblings": len(siblings)}, next_action=f"why: {why}")


def cmd_add(root: Path, *, title: str, parent: str | None, kind: str, cause: str,
           ref: str | None) -> Verdict:
    root = Path(root)
    nodes = load(root)
    if parent and parent not in nodes:
        return Verdict("plan add", 1, f"parent {parent} does not exist")
    nid = _new_id(nodes)
    nodes[nid] = {
        "parent": parent, "title": title, "kind": kind, "state": "open",
        "evidence": [], "opened_at": _now(),
        "origin": {"session": _session(), "cause": cause, **({"ref": ref} if ref else {})},
    }
    save(root, nodes)
    return Verdict("plan add", 0, f"{nid}: {kind}: {title}")


def cmd_done(root: Path, node_id: str, evidence: list[str]) -> Verdict:
    root = Path(root)
    nodes = load(root)
    err = _missing(nodes, node_id, "plan done")
    if err:
        return err
    nodes[node_id] = {**nodes[node_id], "state": "done", "evidence": list(evidence),
                      "closed_at": _now()}
    ns = algebra(root)
    probs = ns["node_problems"](nodes, node_id) + ns["structure_problems"](nodes)
    if probs:
        return Verdict("plan done", 1, f"refused: {probs[0]}", failures=tuple(probs),
                       next_action="close the open descendants first, or drop them with a reason")
    save(root, nodes)
    return Verdict("plan done", 0, f"{node_id}: {nodes[node_id]['title']}")


def cmd_drop(root: Path, node_id: str, reason: str) -> Verdict:
    root = Path(root)
    nodes = load(root)
    err = _missing(nodes, node_id, "plan drop")
    if err:
        return err
    nodes[node_id] = {**nodes[node_id], "state": "dropped", "drop_reason": reason,
                      "closed_at": _now()}
    save(root, nodes)
    return Verdict("plan drop", 0, f"{node_id}: {reason}")


def cmd_block(root: Path, node_id: str, trigger: str) -> Verdict:
    root = Path(root)
    nodes = load(root)
    err = _missing(nodes, node_id, "plan block")
    if err:
        return err
    nodes[node_id] = {**nodes[node_id], "state": "blocked", "trigger": trigger}
    save(root, nodes)
    return Verdict("plan block", 0, f"{node_id}: reopens when: {trigger}")


def cmd_reopen(root: Path, node_id: str) -> Verdict:
    root = Path(root)
    nodes = load(root)
    err = _missing(nodes, node_id, "plan reopen")
    if err:
        return err
    nodes[node_id] = {**nodes[node_id], "state": "open"}
    save(root, nodes)
    return Verdict("plan reopen", 0, f"{node_id}")


def cmd_metrics(root: Path, node_root: str | None) -> Verdict:
    root = Path(root)
    nodes = load(root)
    ns = algebra(root)
    m = ns["drift_metrics"](nodes, node_root)
    next_action = ("capture_ratio is low — discovery is still memory, not machinery (§15.4)"
                  if m.get("capture_ratio", 0) < 0.3 else None)
    return Verdict("plan metrics", 0, f"{len(nodes)} node(s) measured", counts=m,
                   next_action=next_action)


def render_handoff_text(root: Path, node_root: str | None) -> str:
    """The FULL `<!-- plan:handoff --> … <!-- /plan:handoff -->` block `v3.cli` prints for
    `plan handoff` — the projection itself (§7), never bounded through a Verdict."""
    root = Path(root)
    ns = algebra(root)
    nodes = load(root)
    header = f"<!-- plan:handoff{f' root={node_root}' if node_root else ''} -->"
    return f"{header}\n```\n{ns['render_handoff'](nodes, node_root)}\n```\n<!-- /plan:handoff -->"


def cmd_handoff(root: Path, node_root: str | None) -> Verdict:
    root = Path(root)
    nodes = load(root)
    if node_root is not None and node_root not in nodes:
        return Verdict("plan handoff", 1, f"root {node_root} does not exist")
    ns = algebra(root)
    open_n = len(ns["open_set"](nodes, node_root))
    scope = f" under {node_root}" if node_root else ""
    return Verdict("plan handoff", 0, f"{open_n} open node(s) projected{scope}",
                   counts={"open": open_n})


def cmd_check(root: Path) -> Verdict:
    root = Path(root)
    nodes = load(root)
    probs = problems(root)
    if probs:
        return Verdict("plan check", 1, f"{len(probs)} problem(s)", failures=tuple(probs))
    return Verdict("plan check", 0, f"{len(nodes)} node(s) obey the algebra of {SPEC_DOC}",
                   counts={"total": len(nodes)})
