"""role_hygiene (ADR-020, Fase D — DELEG-TOPOLOGY-HYGIENE) — the TOOTH for "specialize by ROLE,
never by domain". Scans every `.claude/agents/*.md` across the meta AND each factory and BLOCKS if any
agent's role name is NOT in the closed vocabulary (`agent_roles.ALLOWED`): a domain-named agent
(`kotlin-writer`, `frontend-generator`, `sql-verifier`) lands OUTSIDE the canonical set → red.

Why the NAME, not the description: the agent name is the role identity (it drives the router). A factory's
agents legitimately MENTION their factory in prose (the `orchestrator` serves one factory) — that is
residence, not role-by-domain. The gate checks the role name; the closed vocabulary is the law.

To add a genuinely new ROLE you edit `agent_roles.CANONICAL` (a deliberate, reviewed governance act + an
ADR). That deliberation is the teeth: an agent cannot smuggle in a domain by naming itself for one.

Two-sided (not decorative): a synthetic root carrying a domain-named agent (`kotlin-writer.md`) MUST flip
the gate red; if it does not, the rule is prose. Argv: <meta_root>."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from ...agent_roles import ALLOWED, role_of


def _agent_files(root: Path) -> list[Path]:
    """Every `.claude/agents/*.md` the levels that HAVE a column carry: the meta itself + each factory.
    Products have no column today (mirrors `column_scope`: 'Product has no column today')."""
    files: list[Path] = []
    meta_agents = root / ".claude" / "agents"
    if meta_agents.is_dir():
        files += sorted(meta_agents.glob("*.md"))
    for factory_agents in sorted(root.glob("factories/*/.claude/agents")):
        if factory_agents.is_dir():
            files += sorted(factory_agents.glob("*.md"))
    return files


def _role_name(agent_md: Path) -> str:
    """The role name = the frontmatter `name:` (authoritative — what the router registers); falls back to
    the filename stem if absent. Tiny hand parse (no yaml dep needed for one scalar field)."""
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
    """The gate's law (single source): every agent's role name must be in the closed vocabulary. Empty == green."""
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
    root = Path(argv[0]).resolve() if argv else Path.cwd()

    # 1. the law over the real repo: zero violations == green.
    problems = _violations(root)
    if problems:
        print(f"DOMAIN-NAMED AGENT(S) ({len(problems)}):")
        for p in problems[:8]:
            print(f"  - {p}")
        return 1

    # 2. NEGATIVE (not decorative): a synthetic root with a domain-named agent must flip the gate red.
    #    If it does not, the closed-vocabulary check has no teeth. Self-contained — no repo clone.
    tmp = Path(tempfile.mkdtemp(prefix="role_hygiene_"))
    try:
        synthetic = tmp / ".claude" / "agents"
        synthetic.mkdir(parents=True)
        (synthetic / "kotlin-writer.md").write_text(
            "---\nname: kotlin-writer\nmodel: sonnet\n---\nA domain-specialized agent (forbidden).\n",
            encoding="utf-8")
        if not _violations(tmp):
            print("GATE DECORATIVO: un agent nombrado por dominio (kotlin-writer) NO tiró el gate a rojo (sin dientes)")
            return 1
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    n = len(_agent_files(root))
    print(f"OK role hygiene: {n} agent(s), toda identidad de rol ∈ vocabulario canónico "
          f"{sorted(ALLOWED)}; un agent nombrado por dominio cae a rojo (ADR-020)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
