"""Tests de la GENERACIÓN DE HARNESS POR SPEC (D2): la acción `emit_harness` escribe agents/commands/
skills desde `machinery.harness` del spec (L3), y el validator rechaza un harness malformado (M0).

La invariante: el harness L3 es 100% derivable del spec (ADR-011); el sustrato no enumera roles ni tech
(ADR-012). La columna (hooks+settings, L4) NO se toca acá — sigue heredada (D1)."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import yaml

from metafactory.codegen import apply_builds
from metafactory.engine import RunContext
from metafactory.spec.loader import load_spec
from metafactory.spec.validator import validate, validate_grammar_v2

_REPO_ROOT = Path(__file__).resolve().parents[1]

_BASE_SPEC = {
    "factory": {"name": "Harness Test", "slug": "htest", "maturity": "bootstrap"},
    "domain": {
        "produces": "nada — sólo ejercita el harness L3",
        "station_sequence": [{"id": "s00", "name": "noop", "activation": "always"}],
    },
    "factory_substrate": {"anti_rubber_stamp_column": True, "verdict_bus": {"max_lines": 10}},
    "requirements": {"functional": [
        {"id": "REQ-F-001", "statement": "x", "satisfied_by": ["s00"]}]},
}


def _write_spec(root: Path, harness: dict) -> None:
    spec = dict(_BASE_SPEC)
    spec["machinery"] = {"harness": harness}
    (root / "factory.spec.yml").write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")


def _emit(root: Path) -> list[str]:
    spec = load_spec(root / "factory.spec.yml")
    ctx = RunContext(root=root, meta_root=_REPO_ROOT, slug=spec.slug)
    station = SimpleNamespace(id="m07", builds=[{"action": "emit_harness"}])
    return apply_builds(ctx, station, {**spec.subst, "slug": spec.slug})


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} sin frontmatter"
    end = text.find("\n---", 3)
    return yaml.safe_load(text[4:end])


# ── emisión: agents / commands / skills desde dato ────────────────────────────

class TestEmit:
    def test_emits_agent_with_frontmatter(self, tmp_path):
        _write_spec(tmp_path, {"agents": [
            {"name": "writer", "model": "sonnet", "description": "escribe", "tools": ["Read", "Bash"],
             "shadows": [{"prohibits": "no toca .proof/", "shadow": ".claude/hooks/proof_protect.py"}],
             "body": "# writer\nimplementa."}]})
        _emit(tmp_path)
        agent = tmp_path / ".claude" / "agents" / "writer.md"
        assert agent.exists()
        fm = _frontmatter(agent)
        assert fm["name"] == "writer" and fm["model"] == "sonnet"
        assert fm["shadows"][0]["shadow"] == ".claude/hooks/proof_protect.py"
        assert "# writer" in agent.read_text(encoding="utf-8")

    def test_emits_command_with_run_in_frontmatter(self, tmp_path):
        _write_spec(tmp_path, {"commands": [
            {"name": "greet", "description": "saluda", "run": ["python", "-c", "print(1)"],
             "body": "Corré el saludo."}]})
        _emit(tmp_path)
        cmd = tmp_path / ".claude" / "commands" / "greet.md"
        assert cmd.exists()
        fm = _frontmatter(cmd)
        assert fm["run"] == ["python", "-c", "print(1)"]
        assert fm["description"] == "saluda"

    def test_emits_skill_as_dir(self, tmp_path):
        _write_spec(tmp_path, {"skills": [
            {"name": "triage-rojo", "description": "diagnostica", "body": "# triage\nleé el log."}]})
        _emit(tmp_path)
        skill = tmp_path / ".claude" / "skills" / "triage-rojo" / "SKILL.md"
        assert skill.exists()
        assert _frontmatter(skill)["name"] == "triage-rojo"

    def test_subst_in_body_and_fields(self, tmp_path):
        _write_spec(tmp_path, {"agents": [
            {"name": "writer", "description": "rol de {{slug}}", "body": "fábrica {{slug}}"}]})
        _emit(tmp_path)
        text = (tmp_path / ".claude" / "agents" / "writer.md").read_text(encoding="utf-8")
        assert "htest" in text and "{{slug}}" not in text


# ── stale-removal: el dir iguala el spec EXACTAMENTE ──────────────────────────

class TestStaleRemoval:
    def test_dropped_agent_disappears(self, tmp_path):
        _write_spec(tmp_path, {"agents": [{"name": "writer", "body": "a"}, {"name": "reviewer", "body": "b"}]})
        _emit(tmp_path)
        assert (tmp_path / ".claude" / "agents" / "reviewer.md").exists()
        # re-emitir con la spec SIN reviewer → desaparece
        _write_spec(tmp_path, {"agents": [{"name": "writer", "body": "a"}]})
        _emit(tmp_path)
        assert (tmp_path / ".claude" / "agents" / "writer.md").exists()
        assert not (tmp_path / ".claude" / "agents" / "reviewer.md").exists()

    def test_dropped_skill_dir_disappears(self, tmp_path):
        _write_spec(tmp_path, {"skills": [{"name": "alpha", "body": "a"}, {"name": "beta", "body": "b"}]})
        _emit(tmp_path)
        assert (tmp_path / ".claude" / "skills" / "beta").exists()
        _write_spec(tmp_path, {"skills": [{"name": "alpha", "body": "a"}]})
        _emit(tmp_path)
        assert not (tmp_path / ".claude" / "skills" / "beta").exists()


# ── columna intacta: emit_harness NO toca L4 (hooks/settings) ──────────────────

class TestColumnUntouched:
    def test_does_not_write_hooks_or_settings(self, tmp_path):
        _write_spec(tmp_path, {"agents": [{"name": "writer", "body": "a"}],
                               "commands": [{"name": "c", "run": ["true"], "body": "x"}]})
        _emit(tmp_path)
        assert not (tmp_path / ".claude" / "hooks").exists()
        assert not (tmp_path / ".claude" / "settings.json").exists()


# ── validator: M0 rechaza un harness malformado (shape-only, sin tech) ─────────

class TestValidatorTeeth:
    def _spec_with(self, tmp_path, harness):
        _write_spec(tmp_path, harness)
        return load_spec(tmp_path / "factory.spec.yml")

    def test_command_without_run_is_rejected(self, tmp_path):
        spec = self._spec_with(tmp_path, {"commands": [{"name": "dead", "body": "x"}]})
        probs = validate_grammar_v2(spec)
        assert any("command" in p and "run" in p for p in probs), probs

    def test_command_empty_run_is_rejected(self, tmp_path):
        spec = self._spec_with(tmp_path, {"commands": [{"name": "dead", "run": [], "body": "x"}]})
        assert any("run" in p for p in validate_grammar_v2(spec))

    def test_agent_without_name_is_rejected(self, tmp_path):
        spec = self._spec_with(tmp_path, {"agents": [{"model": "sonnet", "body": "x"}]})
        assert any("agents" in p and "name" in p for p in validate_grammar_v2(spec))

    def test_skill_without_name_is_rejected(self, tmp_path):
        spec = self._spec_with(tmp_path, {"skills": [{"description": "x"}]})
        assert any("skills" in p and "name" in p for p in validate_grammar_v2(spec))

    def test_wellformed_harness_has_no_machinery_problems(self, tmp_path):
        spec = self._spec_with(tmp_path, {
            "agents": [{"name": "writer", "body": "a"}],
            "commands": [{"name": "greet", "run": ["python", "-c", "print(1)"], "body": "x"}],
            "skills": [{"name": "triage", "body": "y"}]})
        probs = [p for p in validate(spec) if "machinery.harness" in p]
        assert probs == [], probs
