"""plan — the dynamic plan tree, operated from the command line.

The point of this file, and the reason it is short: **it does not implement the plan algebra.** The
algebra is NORMATIVE and lives inside `docs/spec/15-plan-and-memory.md`, in the `<!-- spec-impl: plan -->`
block. This tool EXTRACTS that block and executes it. There is exactly one implementation and it
lives in the specification, so the document cannot drift from the tool — the tool IS the document,
running.

That is the strongest available demonstration of the corpus's claim (§12): the first consumer of the
spec is the system itself.

Honest tradeoff, recorded rather than hidden: executing a Markdown block at runtime is unusual. In
v3 the block is transcribed into a real module and `tools/spec_conformance.py` keeps the two equal —
the conformance suite is what makes transcription safe. Until then, extraction removes the drift
risk entirely at the cost of a slightly odd import path.

Storage: `plan/tree.json` — committed, diff-friendly, greppable (invariant I-8: memory is a repo
artifact; cloning the repo clones the memory).

Verbs:
    show [--root ID]         the column: what is open, what is done, with structure
    next [--root ID]         the deterministic next actionable leaf
    add --title T [--parent ID] [--kind K] [--cause C] [--ref R]
    done ID --evidence E [E …]      (no evidence, no done)
    drop ID --reason R              (abandonment is a decision, not a disappearance)
    block ID --trigger T            (what would unblock it?)
    reopen ID
    metrics [--root ID]
    check                    the gate: exit 1 if the tree breaks its own law
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT / "plan" / "tree.json"
SPEC = ROOT / "docs" / "spec"
MARK = {"open": "○", "blocked": "◍", "done": "●", "dropped": "⊘"}


def algebra() -> dict:
    """Load the NORMATIVE plan algebra out of the specification document."""
    sys.path.insert(0, str(ROOT / "tools"))
    from spec_conformance import extract  # one extractor, shared with the conformance gate

    source, files = extract(ROOT, "plan")
    if not source.strip():
        raise SystemExit("FATAL: no `<!-- spec-impl: plan -->` block in docs/spec/ — the algebra is "
                         "specified there, not here")
    ns: dict = {"__name__": "spec_plan", "__spec_files__": files}
    exec(compile(source, "<spec:plan>", "exec"), ns)
    return ns


def load() -> dict:
    if not TREE.exists():
        return {}
    return json.loads(TREE.read_text(encoding="utf-8")).get("nodes", {})


def save(nodes: dict) -> None:
    TREE.parent.mkdir(parents=True, exist_ok=True)
    TREE.write_text(json.dumps({
        "_doc": "The plan tree. Law and algebra: docs/spec/15-plan-and-memory.md (normative). "
                "Operated by tools/plan.py. Ids are append-only and never renumbered.",
        "nodes": dict(sorted(nodes.items())),
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _new_id(nodes: dict) -> str:
    used = [int(k.split("-")[1]) for k in nodes if k.startswith("N-") and k.split("-")[1].isdigit()]
    return f"N-{max(used, default=0) + 1:04d}"


def _session() -> str:
    return _now()[:10]


# ── verbs ────────────────────────────────────────────────────────────────────
def cmd_show(a, ns, nodes) -> int:
    roots = [a.root] if a.root else sorted(k for k, n in nodes.items() if n.get("parent") is None)
    lines: list[str] = []

    def walk(nid: str, depth: int) -> None:
        n = nodes[nid]
        eff = ns["effective_state"](nodes, nid)
        own = n.get("state")
        mark = MARK.get(own, "?")
        flag = "" if own == eff else f"  [effective: {eff}]"
        note = ""
        if own == "blocked":
            note = f"  ⟵ trigger: {n.get('trigger')}"
        elif own == "dropped":
            note = f"  ⟵ dropped: {n.get('drop_reason')}"
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
    print("\n".join(lines) if lines else "(empty plan)")
    print(f"\nSUMMARY    {open_n} open · {done_n} done · {drop_n} dropped · {total} total")
    nxt = ns["next_actionable"](nodes, a.root)
    print(f"NEXT       {nxt or '— nothing actionable'}"
          + (f"  ({nodes[nxt]['title']})" if nxt else ""))
    return 0


def cmd_next(a, ns, nodes) -> int:
    nid = ns["next_actionable"](nodes, a.root)
    if not nid:
        print("VERDICT    plan next — NONE   (exit 0)\nSUMMARY    nothing actionable in scope")
        return 0
    chain = ns["ancestry"](nodes, nid)
    print(f"VERDICT    plan next — {nid}   (exit 0)")
    print(f"SUMMARY    {nodes[nid]['title']}")
    print("WHY        " + " → ".join(f"{c}:{nodes[c]['title']}" for c in chain))
    siblings = [s for s in ns["open_set"](nodes, chain[0]) if s != nid]
    print(f"ARC-OWES   {len(siblings)} other open node(s) in this arc: {', '.join(siblings[:6])}"
          + (" …" if len(siblings) > 6 else ""))
    return 0


def cmd_add(a, ns, nodes) -> int:
    if a.parent and a.parent not in nodes:
        print(f"VERDICT    plan add — FAIL   (exit 1)\nSUMMARY    parent {a.parent} does not exist")
        return 1
    nid = _new_id(nodes)
    nodes[nid] = {
        "parent": a.parent, "title": a.title, "kind": a.kind, "state": "open",
        "evidence": [], "opened_at": _now(),
        "origin": {"session": _session(), "cause": a.cause, **({"ref": a.ref} if a.ref else {})},
    }
    save(nodes)
    print(f"VERDICT    plan add — {nid}   (exit 0)\nSUMMARY    {a.kind}: {a.title}")
    return 0


def _mutate(nid: str, nodes: dict, **fields) -> int:
    if nid not in nodes:
        print(f"VERDICT    plan — FAIL   (exit 1)\nSUMMARY    node {nid} does not exist")
        return 1
    nodes[nid].update(fields)
    return 0


def cmd_done(a, ns, nodes) -> int:
    rc = _mutate(a.id, nodes, state="done", evidence=list(a.evidence), closed_at=_now())
    if rc:
        return rc
    problems = ns["node_problems"](nodes, a.id) + ns["structure_problems"](nodes)
    if problems:
        print("VERDICT    plan done — FAIL   (exit 1)")
        print(f"SUMMARY    refused: {problems[0]}")
        print("NEXT       close the open descendants first, or drop them with a reason")
        return 1
    save(nodes)
    print(f"VERDICT    plan done — {a.id}   (exit 0)\nSUMMARY    {nodes[a.id]['title']}")
    return 0


def cmd_drop(a, ns, nodes) -> int:
    rc = _mutate(a.id, nodes, state="dropped", drop_reason=a.reason, closed_at=_now())
    if rc:
        return rc
    save(nodes)
    print(f"VERDICT    plan drop — {a.id}   (exit 0)\nSUMMARY    {a.reason}")
    return 0


def cmd_block(a, ns, nodes) -> int:
    rc = _mutate(a.id, nodes, state="blocked", trigger=a.trigger)
    if rc:
        return rc
    save(nodes)
    print(f"VERDICT    plan block — {a.id}   (exit 0)\nSUMMARY    reopens when: {a.trigger}")
    return 0


def cmd_reopen(a, ns, nodes) -> int:
    rc = _mutate(a.id, nodes, state="open")
    if rc:
        return rc
    save(nodes)
    print(f"VERDICT    plan reopen — {a.id}   (exit 0)")
    return 0


def cmd_metrics(a, ns, nodes) -> int:
    m = ns["drift_metrics"](nodes, a.root)
    print("VERDICT    plan metrics — OK   (exit 0)")
    for k in sorted(m):
        print(f"COUNTS     {k}: {m[k]}")
    if m.get("capture_ratio", 0) < 0.3:
        print("NEXT       capture_ratio is low — discovery is still memory, not machinery (§15.4)")
    return 0


def cmd_handoff(a, ns, nodes) -> int:
    """Print the NORMATIVE handoff projection, ready to paste inside a `plan:handoff` block."""
    root = a.root
    print(f"<!-- plan:handoff{f' root={root}' if root else ''} -->")
    print("```")
    print(ns["render_handoff"](nodes, root))
    print("```")
    print("<!-- /plan:handoff -->")
    return 0


def cmd_check(a, ns, nodes) -> int:
    problems = ns["plan_problems"](nodes)
    if problems:
        print(f"VERDICT    plan check — FAIL   (exit 1)\nSUMMARY    {len(problems)} problem(s)")
        for p in problems[:5]:
            print(f"FAILURES   {p}")
        return 1
    print("VERDICT    plan check — PASS   (exit 0)")
    print(f"SUMMARY    {len(nodes)} node(s) obey the algebra of docs/spec/15-plan-and-memory.md")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="plan", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show"); s.add_argument("--root"); s.set_defaults(func=cmd_show)
    s = sub.add_parser("next"); s.add_argument("--root"); s.set_defaults(func=cmd_next)
    s = sub.add_parser("add")
    s.add_argument("--title", required=True); s.add_argument("--parent")
    s.add_argument("--kind", default="task",
                   choices=["direction", "increment", "task", "residual", "question"])
    s.add_argument("--cause", default="manual",
                   choices=["manual", "gate_red", "deferral", "escalation", "handoff"])
    s.add_argument("--ref"); s.set_defaults(func=cmd_add)
    s = sub.add_parser("done"); s.add_argument("id"); s.add_argument("--evidence", nargs="+", default=[])
    s.set_defaults(func=cmd_done)
    s = sub.add_parser("drop"); s.add_argument("id"); s.add_argument("--reason", required=True)
    s.set_defaults(func=cmd_drop)
    s = sub.add_parser("block"); s.add_argument("id"); s.add_argument("--trigger", required=True)
    s.set_defaults(func=cmd_block)
    s = sub.add_parser("reopen"); s.add_argument("id"); s.set_defaults(func=cmd_reopen)
    s = sub.add_parser("metrics"); s.add_argument("--root"); s.set_defaults(func=cmd_metrics)
    s = sub.add_parser("handoff"); s.add_argument("--root"); s.set_defaults(func=cmd_handoff)
    sub.add_parser("check").set_defaults(func=cmd_check, root=None)
    a = p.parse_args(argv)
    return a.func(a, algebra(), load())


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
