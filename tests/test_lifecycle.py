"""Tests de la LEY del lifecycle de incrementos (`seed/lifecycle.py`, ADR-010, H1).

La ley es el single-source que el Meta-Factory DELEGA y que una fábrica generada HEREDA (su
`increment_guard` la carga por path). Se prueba cargándola POR PATH (como la carga la fábrica, no
`import metafactory`), en un repo git hermético en tmp_path — los dos lados de cada decisión."""
from __future__ import annotations

import importlib.util
import subprocess
import types
from pathlib import Path

import pytest

from metafactory import cli

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


# ── dual-accept grammar (ADR-026): English forward, Spanish history forever ──

def test_open_increment_detects_english_open(repo):
    (repo / "docs" / "work" / "X-INCREMENT.md").write_text(
        "# Increment X\n> Status: **OPEN**\n", encoding="utf-8")
    assert lc.open_increment(repo) == "X-INCREMENT.md"


def test_open_increment_ignores_english_closed(repo):
    (repo / "docs" / "work" / "X-INCREMENT.md").write_text(
        "# Increment X\n> Status: **CLOSED** (2026-01-01T00:00Z)\n", encoding="utf-8")
    assert lc.open_increment(repo) is None


def test_mixed_grammars_coexist(repo):
    """A repo mid-transition: Spanish CLOSED history + one English OPEN doc."""
    _open_inc(repo, name="OLD-INCREMENT.md", status="CERRADO")
    (repo / "docs" / "work" / "NEW-INCREMENT.md").write_text(
        "# Increment NEW\n> Status: **OPEN**\n", encoding="utf-8")
    assert lc.open_increment(repo) == "NEW-INCREMENT.md"


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


# ── edit_allowed level-aware (ADR-016): el nivel se resuelve por la RUTA ───────

def _meta_code(repo: Path) -> str:
    return str(repo / "src" / "x.py")


def _factory_code(repo: Path) -> str:
    return str(repo / "factories" / "f" / "codegen" / "x.py")


def _product_code(repo: Path) -> str:
    return str(repo / "factories" / "f" / "products" / "p" / "product.yml")


def _open_at(repo: Path, *parts: str, name: str = "I.md", status: str = "ABIERTO") -> None:
    wd = repo.joinpath(*parts)
    wd.mkdir(parents=True, exist_ok=True)
    (wd / name).write_text(f"# I\n> Estado: **{status}**\n", encoding="utf-8")


def test_level_workdir_resolves_three_levels(repo):
    assert lc.level_workdir(repo, _meta_code(repo)).relative_to(repo) == Path("docs/work")
    assert lc.level_workdir(repo, _factory_code(repo)).relative_to(repo) == Path("factories/f/docs/work")
    assert lc.level_workdir(repo, _product_code(repo)).relative_to(repo) == Path(
        "factories/f/products/p/docs/work")


def test_edit_gate_isolates_levels(repo):
    """Un incremento META abierto NO autoriza editar código de fábrica/producto (la ley de ADR-016)."""
    _open_inc(repo)                                            # docs/work (meta)
    assert lc.edit_allowed(repo, _meta_code(repo)) is True
    assert lc.edit_allowed(repo, _factory_code(repo)) is False
    assert lc.edit_allowed(repo, _product_code(repo)) is False


def test_edit_gate_product_level(repo):
    pc = _product_code(repo)
    assert lc.edit_allowed(repo, pc) is False                  # sin incremento de producto
    _open_at(repo, "factories", "f", "products", "p", "docs", "work")
    assert lc.edit_allowed(repo, pc) is True                   # con el incremento del producto
    assert lc.edit_allowed(repo, _meta_code(repo)) is False    # pero NO autoriza el meta (aislamiento)


def test_edit_gate_factory_level(repo):
    fc = _factory_code(repo)
    assert lc.edit_allowed(repo, fc) is False                  # sin incremento de fábrica
    _open_at(repo, "factories", "f", "docs", "work")
    assert lc.edit_allowed(repo, fc) is True                   # con el incremento de la fábrica
    assert lc.edit_allowed(repo, _product_code(repo)) is False  # no derrama al producto


def test_required_workdir_rel_names_level(repo):
    assert lc.required_workdir_rel(repo, _meta_code(repo)) == "docs/work"
    assert lc.required_workdir_rel(repo, _factory_code(repo)) == "factories/f/docs/work"
    assert lc.required_workdir_rel(repo, _product_code(repo)) == "factories/f/products/p/docs/work"
    assert lc.required_workdir_rel(repo, str(repo / "x.md")) is None       # un .md no necesita incremento
    assert lc.required_workdir_rel(repo, "/tmp/z.py") is None              # fuera del repo


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


# ── cli.py `increment close` — dual-accept close-flip (ADR-026), two grammars ──

@pytest.fixture
def cli_repo(tmp_path: Path, monkeypatch) -> Path:
    """A hermetic repo wired so `cli.cmd_increment` operates on tmp_path (not the real Meta-Factory
    root): git-init + `docs/work/` + a minimal `docs/STATE.md` (required by `projection.refresh`)."""
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "docs" / "work").mkdir(parents=True)
    (tmp_path / "docs" / "STATE.md").write_text("# STATE\n\n## Ahora\n- x\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_meta_root", lambda: tmp_path)
    return tmp_path


def test_cli_close_flips_english_open_header_to_closed(cli_repo):
    """The CLI now EMITS `Status: **OPEN**` forward (English), and its close-flip recognizes it."""
    rc = cli.cmd_increment(types.SimpleNamespace(inc_cmd="open", slug="foo"))
    assert rc == 0
    path = cli_repo / "docs" / "work" / "FOO-INCREMENT.md"
    assert "Status: **OPEN**" in path.read_text(encoding="utf-8")

    rc = cli.cmd_increment(types.SimpleNamespace(inc_cmd="close"))
    assert rc == 0
    text = path.read_text(encoding="utf-8")
    assert "Status: **CLOSED**" in text
    assert "Status: **OPEN**" not in text


def test_cli_close_flips_legacy_spanish_open_header_to_closed(cli_repo):
    """A pre-existing legacy `Estado: **ABIERTO**` work-doc (immutable history's grammar) ALSO flips to
    the English `Status: **CLOSED**` marker — dual-accept on read, English-forward on write."""
    path = cli_repo / "docs" / "work" / "X-INCREMENT.md"
    path.write_text("# Incremento X\n\n> Estado: **ABIERTO** (creado 2026-01-01T00:00Z)\n", encoding="utf-8")

    rc = cli.cmd_increment(types.SimpleNamespace(inc_cmd="close"))
    assert rc == 0
    text = path.read_text(encoding="utf-8")
    assert "Status: **CLOSED**" in text
    assert "Estado: **ABIERTO**" not in text
