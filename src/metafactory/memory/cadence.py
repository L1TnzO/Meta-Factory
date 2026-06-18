"""cadence — disciplina de commit (ADR-010). Cero modelo: git + file-IO + aritmética.

Dos preguntas deterministas, re-derivables del working tree + el incremento abierto:
- ¿hay código (no-`.md`) sin commitear dentro de un incremento abierto?        → debt()
- ¿se cerró un gate de estación VERDE desde el último commit con el árbol sucio? → stop_block()

La LEY del lifecycle (open_increment/dirty_code/edit_allowed/debt) vive en `seed/lifecycle.py` — single
source que la fábrica hereda y este módulo DELEGA (sin divergencia). Acá vive sólo el backstop que usa el
journal (Tier-0, propio del meta): `stop_block`/`passed_gate_since_commit`. NO auto-commitea: la deuda se
SURFACE-ea y se BLOQUEA; el mensaje (trailers I-10) lo escribe el modelo. La cadencia es un AID, no una
frontera de seguridad (esa es la columna anti-sello); ante la duda, PERMITE.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .._seed import load_seed_lifecycle
from .journal import read as journal_read

_MIN = datetime.min.replace(tzinfo=timezone.utc)


def _git(root: Path, *args: str) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
        return out.stdout
    except OSError:
        return ""


# ── la LEY del lifecycle: delegada al seed (single source con la fábrica heredera) ──

def open_increment(root: Path) -> str | None:
    return load_seed_lifecycle().open_increment(Path(root))


def dirty_code(root: Path) -> list[str]:
    return load_seed_lifecycle().dirty_code(Path(root))


def debt(root: Path) -> tuple[bool, str]:
    return load_seed_lifecycle().debt(Path(root))


def edit_allowed(root: Path, file_path: str) -> bool:
    return load_seed_lifecycle().edit_allowed(Path(root), file_path)


def _fmt(paths: list[str]) -> str:
    head = ", ".join(paths[:3])
    return head + (f" (+{len(paths) - 3} más)" if len(paths) > 3 else "")


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
