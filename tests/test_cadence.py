"""Tests de la disciplina de commit (ADR-010): la señal de cadencia y los rechazos del lifecycle.

La señal es determinista y re-derivable del working tree (git) + el incremento abierto (docs/work).
Probamos por exit-code / valor de verdad, no por prosa.
"""
from __future__ import annotations

import json
import subprocess
import types
from pathlib import Path

import pytest

from metafactory import cli
from metafactory.memory import cadence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _commit_all(root: Path, msg: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", msg)


def _open_increment(root: Path, name: str = "INC.md") -> None:
    (root / "docs" / "work" / name).write_text(
        "# Incremento de prueba\n\nEstado: **ABIERTO**\n", encoding="utf-8")


def _close_increment(root: Path, name: str = "INC.md") -> None:
    (root / "docs" / "work" / name).write_text(
        "# Incremento de prueba\n\nEstado: **CERRADO** (2026-01-01T00:00Z)\n", encoding="utf-8")


def _add_event(root: Path, kind: str, ts: str, **fields) -> None:
    """Escribe un evento crudo al journal con un ts controlado (para ordenar vs el commit)."""
    p = root / ".metamem" / "journal.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": ts, "kind": kind, **fields}) + "\n")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "docs" / "work").mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------------------
# dirty_code — el árbol es la autoridad; .md no cuenta como código
# ---------------------------------------------------------------------------
class TestDirtyCode:
    def test_sees_py_ignores_md(self, repo: Path):
        (repo / "foo.py").write_text("x = 1\n", encoding="utf-8")
        (repo / "notes.md").write_text("# nota\n", encoding="utf-8")
        dirty = cadence.dirty_code(repo)
        assert "foo.py" in dirty
        assert "notes.md" not in dirty

    def test_clean_tree_is_empty(self, repo: Path):
        (repo / "foo.py").write_text("x = 1\n", encoding="utf-8")
        _commit_all(repo, "init")
        assert cadence.dirty_code(repo) == []

    def test_modified_tracked_py_is_dirty(self, repo: Path):
        (repo / "foo.py").write_text("x = 1\n", encoding="utf-8")
        _commit_all(repo, "init")
        (repo / "foo.py").write_text("x = 2\n", encoding="utf-8")
        assert "foo.py" in cadence.dirty_code(repo)


# ---------------------------------------------------------------------------
# debt — incremento abierto + código sin commitear
# ---------------------------------------------------------------------------
class TestDebt:
    def test_debt_when_open_and_dirty(self, repo: Path):
        _open_increment(repo)
        (repo / "foo.py").write_text("x = 1\n", encoding="utf-8")
        has, reason = cadence.debt(repo)
        assert has is True
        assert "foo.py" in reason

    def test_no_debt_when_clean(self, repo: Path):
        _open_increment(repo)
        (repo / "foo.py").write_text("x = 1\n", encoding="utf-8")
        _commit_all(repo, "init")
        has, _ = cadence.debt(repo)
        assert has is False

    def test_no_debt_without_open_increment(self, repo: Path):
        _close_increment(repo)  # CERRADO, no abierto
        (repo / "foo.py").write_text("x = 1\n", encoding="utf-8")
        has, reason = cadence.debt(repo)
        assert has is False
        assert "sin incremento abierto" in reason

    def test_md_only_changes_are_not_debt(self, repo: Path):
        _open_increment(repo)
        (repo / "docs" / "STATE.md").write_text("# estado\n", encoding="utf-8")
        has, _ = cadence.debt(repo)
        assert has is False


# ---------------------------------------------------------------------------
# stop_block — backstop: gate verde sin commitear desde el último commit
# ---------------------------------------------------------------------------
class TestStopBlock:
    def test_blocks_on_proven_uncommitted(self, repo: Path):
        (repo / "seed.py").write_text("x = 1\n", encoding="utf-8")
        _commit_all(repo, "base")
        _open_increment(repo)
        _add_event(repo, "station_run", "2999-01-01T00:00:00Z", passed=True, station="m08")
        (repo / "foo.py").write_text("y = 2\n", encoding="utf-8")  # sucio post-gate
        has, reason = cadence.stop_block(repo)
        assert has is True
        assert "foo.py" in reason

    def test_no_block_without_new_gate(self, repo: Path):
        (repo / "seed.py").write_text("x = 1\n", encoding="utf-8")
        _commit_all(repo, "base")
        _open_increment(repo)
        _add_event(repo, "station_run", "2000-01-01T00:00:00Z", passed=True, station="old")  # viejo
        (repo / "foo.py").write_text("y = 2\n", encoding="utf-8")
        has, _ = cadence.stop_block(repo)
        assert has is False  # WIP de desarrollo: sin gate nuevo, no es backstop de cadencia

    def test_no_block_when_clean(self, repo: Path):
        _open_increment(repo)
        _add_event(repo, "station_run", "2999-01-01T00:00:00Z", passed=True, station="m08")
        _commit_all(repo, "todo limpio")
        has, _ = cadence.stop_block(repo)
        assert has is False


# ---------------------------------------------------------------------------
# Lifecycle — los RECHAZOS (las teeth); los success-paths los ejerce el dogfood
# ---------------------------------------------------------------------------
class TestLifecycleRefusals:
    def test_open_refuses_when_one_already_open(self, repo: Path, monkeypatch):
        monkeypatch.setattr(cli, "_meta_root", lambda: repo)
        _open_increment(repo)
        rc = cli.cmd_increment(types.SimpleNamespace(inc_cmd="open", slug="otro"))
        assert rc == 1

    def test_close_refuses_with_debt(self, repo: Path, monkeypatch):
        monkeypatch.setattr(cli, "_meta_root", lambda: repo)
        _open_increment(repo)
        (repo / "foo.py").write_text("x = 1\n", encoding="utf-8")  # deuda
        rc = cli.cmd_increment(types.SimpleNamespace(inc_cmd="close"))
        assert rc == 1

    def test_status_runs_clean(self, repo: Path, monkeypatch):
        monkeypatch.setattr(cli, "_meta_root", lambda: repo)
        _open_increment(repo)
        rc = cli.cmd_increment(types.SimpleNamespace(inc_cmd="status"))
        assert rc == 0
