"""cadence — disciplina de commit (ADR-010). Cero modelo: git + file-IO + aritmética.

Dos preguntas deterministas, re-derivables del working tree + el incremento abierto:
- ¿hay código (no-`.md`) sin commitear dentro de un incremento abierto?        → debt()
- ¿se cerró un gate de estación VERDE desde el último commit con el árbol sucio? → stop_block()

La VERDAD es git (el árbol) + docs (el incremento, vía `projection.open_increment`); esto sólo la LEE
y la proyecta. NO auto-commitea: la deuda se SURFACE-ea y se BLOQUEA; el mensaje (con trailers I-10)
lo escribe el modelo. Fuera de un incremento no hay deuda — esa frontera la cubre el increment-gate.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .journal import read as journal_read
from .projection import open_increment

_MIN = datetime.min.replace(tzinfo=timezone.utc)


def _git(root: Path, *args: str) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
        return out.stdout
    except OSError:
        return ""


def dirty_code(root: Path) -> list[str]:
    """Rutas con cambios sin commitear que NO son `.md`. `git status --porcelain` ya excluye lo
    gitignored (`.proof/`, `.metamem/`, `build/`, `__pycache__`), así que esto ve sólo código real."""
    paths: list[str] = []
    # --untracked-files=all expande dirs sin trackear a archivos: si no, git colapsa 'docs/' y el
    # filtro `.md` no aplicaría. Lo gitignored sigue excluido (no pasamos --ignored).
    for ln in _git(root, "status", "--porcelain", "--untracked-files=all").splitlines():
        if not ln.strip():
            continue
        path = ln[3:]                       # formato porcelain: 'XY <path>'
        if " -> " in path:                  # rename: 'orig -> new'
            path = path.split(" -> ", 1)[1]
        path = path.strip().strip('"')
        if path and not path.endswith(".md"):
            paths.append(path)
    return paths


def _fmt(paths: list[str]) -> str:
    head = ", ".join(paths[:3])
    return head + (f" (+{len(paths) - 3} más)" if len(paths) > 3 else "")


def debt(root: Path) -> tuple[bool, str]:
    """Deuda de cadencia: dentro de un incremento abierto hay código (no-`.md`) sin commitear.
    Es la señal del cierre-de-incremento y del surface de `meta check`."""
    inc = open_increment(root)
    if inc is None:
        return False, "sin incremento abierto"
    dirty = dirty_code(root)
    if not dirty:
        return False, f"incremento {inc}: árbol limpio"
    return True, f"incremento {inc}: código sin commitear — {_fmt(dirty)}"


def _last_commit_dt(root: Path) -> datetime:
    iso = _git(root, "log", "-1", "--format=%cI").strip()
    if not iso:
        return _MIN
    try:
        return datetime.fromisoformat(iso).astimezone(timezone.utc)
    except ValueError:
        return _MIN


def _parse_journal_ts(s: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return _MIN


def passed_gate_since_commit(root: Path) -> bool:
    """¿Se cerró un gate de estación VERDE desde el último commit? Hecho del journal (Tier 0), no
    narrativa: distingue 'pasé un gate probado' de 'estoy editando src' (WIP) para no molestar el WIP."""
    since = _last_commit_dt(root)
    return any(
        e.get("passed") and _parse_journal_ts(e.get("ts", "")) > since
        for e in journal_read(root, kinds={"station_run"})
    )


def stop_block(root: Path) -> tuple[bool, str]:
    """Backstop de cierre de turno: hay progreso PROBADO (gate verde desde el último commit) con el
    árbol sucio dentro de un incremento. Atrapa 'pasé el último gate y cerré sin commitear'."""
    inc = open_increment(root)
    if inc is None:
        return False, "sin incremento abierto"
    if not passed_gate_since_commit(root):
        return False, "sin gate verde sin commitear (no es backstop de cadencia)"
    dirty = dirty_code(root)
    if not dirty:
        return False, "árbol limpio"
    return True, f"gate verde sin commitear (incremento {inc}) — {_fmt(dirty)}"
