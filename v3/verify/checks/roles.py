#!/usr/bin/env python3
"""roles — the TOOTH for "specialize by ROLE, never by domain" (ADR-020, Fase D), PORTED from v2's
`verify/checks/role_hygiene.py`. Subject UNCHANGED (`.claude/agents/*.md` across the meta AND each
factory — the same surface v2 scanned): a domain-named agent (`kotlin-writer`, `frontend-generator`,
`sql-verifier`) lands OUTSIDE the closed vocabulary and turns this gate RED.

    python3 -m v3.verify.checks.roles
    V3_ROLES_SABOTAGE=1 python3 -m v3.verify.checks.roles   # red side; must ALSO exit 0

WHY THE NAME, not the description: the agent name is the role identity (it drives the router). A
factory's agents legitimately MENTION their factory in prose (the `orchestrator` serves one
factory) — that is residence, not role-by-domain. This gate checks the role NAME; the closed
vocabulary (`v3.control.agent_roles.ALLOWED`) is the law, single-sourced from `v3.control.column`
(the same constants `v3.verify.composition` already reads for the projection's OWN vocabulary
assertion — no second, driftable copy).

WHY THE WITNESS MOVED SHAPE (recorded, not silently changed — same reasoning as
`v3.verify.checks.pbt`/`codegen_freeze`'s docstrings). v2 ran its synthetic negative
(a `kotlin-writer.md` planted in a tempdir) unconditionally INSIDE every green invocation. Under
this registry that shape is `fixture`/`pinned_data` (`Witness.is_embedded`); this witness is
registered `sabotage_env` instead (`V3_ROLES_SABOTAGE`) — the synthetic negative runs ONLY under the
sabotage flag, and the ordinary green run only checks the real repo.
`v3.verify.checks.suite_sweep` re-runs the sabotage side separately, exactly as it does for `pbt`.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from ...control.agent_roles import ALLOWED, role_of
from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_ROLES_SABOTAGE"


def _agent_files(root: Path) -> list[Path]:
    """Every `.claude/agents/*.md` the levels that HAVE a column carry: the meta itself + each
    factory. Products have no column today (mirrors `v3.control.column`: no product-level entry)."""
    files: list[Path] = []
    meta_agents = root / ".claude" / "agents"
    if meta_agents.is_dir():
        files += sorted(meta_agents.glob("*.md"))
    for factory_agents in sorted(root.glob("factories/*/.claude/agents")):
        if factory_agents.is_dir():
            files += sorted(factory_agents.glob("*.md"))
    return files


def _role_name(agent_md: Path) -> str:
    """The role name = the frontmatter `name:` (authoritative — what the router registers); falls
    back to the filename stem if absent. Tiny hand parse (no yaml dep needed for one scalar field)."""
    try:
        text = agent_md.read_text(encoding="utf-8")
    except OSError:
        return agent_md.stem
    if text.startswith("---"):
        end = text.find("\n---", 3)
        block = text[3:end] if end != -1 else text[3:]
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith("name:"):
                return stripped[len("name:"):].strip().strip("'\"")
    return agent_md.stem


def _violations(root: Path) -> list[str]:
    """The gate's law (single source): every agent's role name must be in the closed vocabulary.
    Empty == green."""
    problems: list[str] = []
    for agent in _agent_files(root):
        name = _role_name(agent)
        if role_of(name) is None:
            rel = agent.relative_to(root)
            problems.append(
                f"{rel}: agent role '{name}' is not in the canonical vocabulary {sorted(ALLOWED)} — "
                f"agents specialize by ROLE, not domain (the domain rides the slot manifest; ADR-020)")
    return problems


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-roles", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        tmp = Path(tempfile.mkdtemp(prefix="v3_roles_sabotage_"))
        try:
            synthetic = tmp / ".claude" / "agents"
            synthetic.mkdir(parents=True)
            (synthetic / "kotlin-writer.md").write_text(
                "---\nname: kotlin-writer\nmodel: sonnet\n---\nA domain-specialized agent (forbidden).\n",
                encoding="utf-8")
            problems = _violations(tmp)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        if not problems:
            return Verdict("v3-roles (SABOTAGE)", 1,
                           "GATE DECORATIVO: a domain-named agent (kotlin-writer) did NOT flip the "
                           "gate red — no teeth").emit()
        return Verdict("v3-roles (SABOTAGE)", 0,
                       f"a domain-named agent was caught: {len(problems)} violation(s)").emit()

    problems = _violations(_ROOT)
    if problems:
        return Verdict("v3-roles", 1, f"{len(problems)} domain-named agent(s)",
                       failures=tuple(problems)).emit()

    n = len(_agent_files(_ROOT))
    return Verdict("v3-roles", 0,
                   f"{n} agent(s), every role identity in the canonical vocabulary {sorted(ALLOWED)}"
                   ).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
