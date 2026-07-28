"""handoff_check — the `handoff_derived` tooth (§15.7): a handoff may not disagree with the plan.

Pathology being closed: a handoff document is written by hand, the next session reads it, and the
work it forgot to mention is gone. Prose handoff is the field's default (296 of 301 studies pass
CONTENT) and it is precisely what decayed here.

Mechanism: a document opts in by carrying a marker block

    <!-- plan:handoff root=N-0001 -->
    ```
    …the projection…
    ```
    <!-- /plan:handoff -->

The block's body must equal `render_handoff(plan, root)` — the NORMATIVE projection in
`docs/spec/15-plan-and-memory.md`. Rendering is law and lives in the spec; scanning files is I/O and
lives here.

Opt-in by construction (SAFE-7 doctrine): a document with no marker is not judged; a document WITH a
marker is enforced. So adopting the mechanism is a deliberate act, and once adopted it cannot rot.

Modes:
    (default)   GATE  — exit 1 if any marked block disagrees with the tree
    --fix       rewrite every marked block from the live tree

Two-sided: HANDOFF_SABOTAGE=1 perturbs the rendered projection; the gate MUST go red.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCK = re.compile(
    r"(<!--\s*plan:handoff(?P<attrs>[^>]*)-->\s*\n```\n)(?P<body>.*?)(\n```\s*\n<!--\s*/plan:handoff\s*-->)",
    re.DOTALL)
SCAN = ("docs/**/*.md", "research/*.md", "factories/*/docs/**/*.md")


def _root_attr(attrs: str) -> str | None:
    m = re.search(r"root=([A-Za-z0-9_-]+)", attrs or "")
    return m.group(1) if m else None


def documents(root: Path) -> list[Path]:
    seen: list[Path] = []
    for pat in SCAN:
        for p in sorted(root.glob(pat)):
            if p.is_file() and p not in seen:
                seen.append(p)
    return seen


def main(argv: list[str]) -> int:
    sys.path.insert(0, str(ROOT / "tools"))
    import plan as plan_tool

    ns = plan_tool.algebra()
    nodes = plan_tool.load()
    sabotage = os.environ.get("HANDOFF_SABOTAGE") == "1"
    fix = "--fix" in argv

    checked = 0
    stale: list[str] = []
    for doc in documents(ROOT):
        try:
            text = doc.read_text(encoding="utf-8")
        except OSError:
            continue
        if "plan:handoff" not in text:
            continue
        new_text, changed = text, False
        for m in BLOCK.finditer(text):
            checked += 1
            expected = ns["render_handoff"](nodes, _root_attr(m.group("attrs")))
            if sabotage:
                expected += "\n[ ] N-9999  a node that does not exist"
            if m.group("body") != expected:
                stale.append(f"{doc.relative_to(ROOT)}: block "
                             f"root={_root_attr(m.group('attrs'))} disagrees with the plan")
                if fix:
                    new_text = new_text.replace(m.group(0),
                                                m.group(1) + expected + m.group(4))
                    changed = True
        if changed:
            doc.write_text(new_text, encoding="utf-8")

    if sabotage:
        if stale:
            print("VERDICT    handoff-derived (SABOTAGE) — PASS   (exit 0)")
            print(f"SUMMARY    the perturbed projection was detected in {len(stale)} block(s)")
            return 0
        print("VERDICT    handoff-derived (SABOTAGE) — FAIL   (exit 1)")
        print("SUMMARY    GATE DECORATIVO: a perturbed projection passed as current")
        return 1

    if not checked:
        print("VERDICT    handoff-derived — N/A   (exit 0)")
        print("SUMMARY    no document carries a `plan:handoff` block (opt-in, SAFE-7)")
        return 0
    if fix:
        print("VERDICT    handoff-derived --fix — PASS   (exit 0)")
        print(f"SUMMARY    {len(stale)} block(s) re-derived from the live tree, {checked} checked")
        return 0
    if stale:
        print("VERDICT    handoff-derived — FAIL   (exit 1)")
        print(f"SUMMARY    {len(stale)} handoff block(s) contradict the plan")
        for s in stale[:5]:
            print(f"FAILURES   {s}")
        print("NEXT       python3 tools/handoff_check.py --fix")
        return 1
    print("VERDICT    handoff-derived — PASS   (exit 0)")
    print(f"SUMMARY    {checked} handoff block(s) equal the tree projection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
