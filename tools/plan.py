"""plan — thin compatibility shim (V3-INC12 P2). This file no longer OWNS the plan-tree law:
`v3.memory.plan_tree` does, and `docs/spec/15-plan-and-memory.md §5` remains the ONLY source of the
algebra itself (extracted and exec'd there, never transcribed — see that module's docstring).

Two things keep working through this shim, on purpose:

1. Every already-written `python3 tools/plan.py <verb> …` line (the spec, the work-docs) — `main`
   below just forwards `argv` to the v3 verb (`v3.cli`, dispatching to `v3.memory.plan_tree`'s command
   bodies), so there is exactly ONE implementation of both the algebra and the command bodies (the
   §10.3 rule: the CLI is a transport, never a second copy).

2. `tools/plan_capture.py` and `tools/handoff_check.py` — both out of this slot's scope — `import plan
   as plan_tool` and call its ZERO-ARG functions directly (`algebra()`, `load()`, `save(nodes)`,
   `_new_id(nodes)`, `_now()`, `_session()`). Removing those would break two callers this slot must
   not touch, so they stay, each a one-line wrapper bound to this repo's ROOT and delegating straight
   to `v3.memory.plan_tree`'s root-parameterized equivalents — no logic of its own, so no second law.

Verbs (unchanged): show, next, add, done, drop, block, reopen, metrics, handoff, check.
See `docs/spec/15-plan-and-memory.md §5` / `v3 plan-tree --help` for arguments.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v3.memory import plan_tree as _pt  # noqa: E402 — needs ROOT on sys.path first

TREE = ROOT / _pt.TREE_PATH


def algebra() -> dict:
    return _pt.algebra(ROOT)


def load() -> dict:
    return _pt.load(ROOT)


def save(nodes: dict) -> None:
    _pt.save(ROOT, nodes)


def _new_id(nodes: dict) -> str:
    return _pt._new_id(nodes)


def _now() -> str:
    return _pt._now()


def _session() -> str:
    return _pt._session()


def main(argv: list[str]) -> int:
    from v3.cli import main as v3_main
    return v3_main(["plan-tree", *argv])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
