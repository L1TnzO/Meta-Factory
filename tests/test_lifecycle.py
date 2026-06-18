"""Tests de la LEY del lifecycle de incrementos (`seed/lifecycle.py`, ADR-010, H1).

La ley es el single-source que el Meta-Factory DELEGA y que una fábrica generada HEREDA (su
`increment_guard` la carga por path). Se prueba cargándola POR PATH (como la carga la fábrica, no
`import metafactory`), en un repo git hermético en tmp_path — los dos lados de cada decisión."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_LIFECYCLE = _REPO_ROOT / "seed" / "lifecycle.py"


def _load():
    spec = importlib.util.spec_from_file_location("seed_lifecycle_under_test", _LIFECYCLE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lc = _load()


def test_self_contained_no_metafactory_import():
    """La ley vive en el seed: cero `import metafactory` (la fábrica no lo tiene)."""
    src = _LIFECYCLE.read_text(encoding="utf-8")
    assert "import metafactory" not in src and "from metafactory" not in src


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "docs" / "work").mkdir(parents=True)
    return tmp_path


def _open_inc(root: Path, name: str = "X-INCREMENT.md", status: str = "ABIERTO") -> None:
    (root / "docs" / "work" / name).write_text(
        f"# Incremento X\n> Estado: **{status}**\n", encoding="utf-8")


# ── open_increment: dos lados ─────────────────────────────────────────────────

def test_open_increment_none_when_no_docs_work(tmp_path):
    assert lc.open_increment(tmp_path) is None            # ni docs/work existe (cold start)


def test_open_increment_detects_abierto(repo):
    _open_inc(repo)
    assert lc.open_increment(repo) == "X-INCREMENT.md"


def test_open_increment_ignores_cerrado(repo):
    _open_inc(repo, status="CERRADO")
    assert lc.open_increment(repo) is None


# ── edit_allowed: la Capa 1 de ADR-010, dos lados ─────────────────────────────

def test_edit_md_always_allowed(repo):
    """Un `.md` siempre se permite — es como se ABRE un incremento (auto-bootstrap)."""
    assert lc.edit_allowed(repo, str(repo / "docs" / "work" / "NEW-INCREMENT.md")) is True


def test_edit_code_denied_without_increment(repo):
    assert lc.edit_allowed(repo, str(repo / "src" / "x.py")) is False


def test_edit_code_allowed_with_increment(repo):
    _open_inc(repo)
    assert lc.edit_allowed(repo, str(repo / "src" / "x.py")) is True


def test_edit_outside_repo_allowed(repo):
    assert lc.edit_allowed(repo, "/tmp/elsewhere.py") is True


# ── dirty_code / debt ─────────────────────────────────────────────────────────

def test_dirty_code_excludes_md(repo):
    _open_inc(repo)
    (repo / "a.py").write_text("x=1\n", encoding="utf-8")
    (repo / "b.md").write_text("# doc\n", encoding="utf-8")
    dirty = lc.dirty_code(repo)
    assert "a.py" in dirty and not any(p.endswith(".md") for p in dirty)


def test_debt_false_without_increment(repo):
    (repo / "a.py").write_text("x=1\n", encoding="utf-8")
    assert lc.debt(repo)[0] is False                       # sin incremento no hay deuda


def test_debt_true_with_uncommitted_code_in_increment(repo):
    _open_inc(repo)
    (repo / "a.py").write_text("x=1\n", encoding="utf-8")
    has_debt, reason = lc.debt(repo)
    assert has_debt is True and "a.py" in reason


def test_debt_false_when_clean(repo):
    _open_inc(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "all in")
    assert lc.debt(repo)[0] is False                       # árbol limpio dentro del incremento
