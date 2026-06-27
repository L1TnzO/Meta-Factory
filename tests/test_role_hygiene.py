"""test_role_hygiene — the tooth for "specialize by ROLE, never by domain" (ADR-020, Fase D).

Proves the `roles` gate BY BLOCKING:
  - the closed vocabulary (`agent_roles`) maps the canonical names and the grandfathered legacy synonyms,
    and ONLY those;
  - `_violations` is green over the real repo's 24 agents (meta + 5 factories);
  - a synthetic root carrying a domain-named agent (`kotlin-writer`) is RED — the negative has teeth;
  - the full check `main` exits 0 on the real repo (positive AND its own internal negative pass).
"""
from __future__ import annotations

import sys
from pathlib import Path

from metafactory import agent_roles
from metafactory.verify.checks import role_hygiene

REPO = Path(__file__).resolve().parents[1]


# ── the closed vocabulary ──────────────────────────────────────────────────────
def test_canonical_roles_resolve_to_themselves():
    for role in agent_roles.CANONICAL:
        assert agent_roles.role_of(role) == role


def test_legacy_synonyms_map_to_canonical():
    assert agent_roles.role_of("writer") == agent_roles.GENERATOR
    assert agent_roles.role_of("triage") == agent_roles.VERIFIER


def test_domain_name_is_not_a_role():
    for name in ("kotlin-writer", "frontend-generator", "sql-verifier", "snipeit-orchestrator"):
        assert agent_roles.role_of(name) is None


def test_allowed_is_exactly_canonical_plus_legacy():
    assert agent_roles.ALLOWED == agent_roles.CANONICAL | frozenset(agent_roles.LEGACY_SYNONYMS)


# ── the gate over the real repo ────────────────────────────────────────────────
def test_real_repo_has_no_domain_named_agents():
    assert role_hygiene._violations(REPO) == []


def test_real_repo_scans_meta_plus_five_factories():
    # 4 meta agents + 4 each across 5 factories = 24; a regression in the glob would change this.
    assert len(role_hygiene._agent_files(REPO)) == 24


# ── the negative has teeth ─────────────────────────────────────────────────────
def test_domain_named_agent_trips_red(tmp_path):
    agents = tmp_path / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "kotlin-writer.md").write_text(
        "---\nname: kotlin-writer\nmodel: sonnet\n---\nbody\n", encoding="utf-8")
    problems = role_hygiene._violations(tmp_path)
    assert problems and "kotlin-writer" in problems[0]


def test_role_name_reads_frontmatter_not_filename(tmp_path):
    # the role identity is the frontmatter `name:`, even when the filename differs.
    agents = tmp_path / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "misnamed.md").write_text(
        "---\nname: generator\nmodel: sonnet\n---\nbody\n", encoding="utf-8")
    assert role_hygiene._violations(tmp_path) == []


# ── the full check (positive + its own embedded negative) ──────────────────────
def test_main_green_on_real_repo(capsys):
    assert role_hygiene.main([str(REPO)]) == 0
