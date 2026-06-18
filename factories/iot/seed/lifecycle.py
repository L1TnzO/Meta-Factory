"""lifecycle — the increment-cadence LAW (ADR-010), part of the frozen Stage-0 seed.

Zero model, zero `metafactory.*`: git + file-IO + a docs scan. This is the single source of the
commit-discipline law, COPIED VERBATIM into every produced factory (like `verifier.py`) so a factory
governs its OWN increment lifecycle ALONE — its inherited `increment_guard` hook loads THIS file by
path, and the Meta-Factory's own `memory.cadence`/`memory.projection` DELEGATE here, so the factory
and the meta enforce the IDENTICAL law (no divergence, the trust-chain single-source principle).

Two deterministic questions, re-derivable from the working tree + the open increment:
  - is there a (non-`.md`) file open for edit with NO increment open?            → edit_allowed()
  - is there un-committed (non-`.md`) code INSIDE an open increment?             → debt()

The TRUTH is git (the tree) + docs (the increment, `Estado: **ABIERTO**`); this only READS and
projects it. It NEVER auto-commits: the debt is surfaced and blocked; the message (with I-10 trailers)
is written by the model. Outside an increment there is no debt — that frontier is the edit-gate.

The cadence is an AID, not a security boundary (the rubber-stamp column is): on any doubt, PERMIT —
never brick an edit/commit. The security root is the verdict re-derivation (`verifier.py`), not this.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

_OPEN_RE = re.compile(r"Estado:\s*\*\*(ABIERTO|CERRADO)\*\*")


def open_increment(root: Path) -> str | None:
    """The filename of the single open increment (`docs/work/*.md` with `Estado: **ABIERTO**`), or
    None. A factory OPENS one by writing such a `.md` (an `.md` is always editable, so this
    self-bootstraps); CLOSES it by flipping the header to `**CERRADO**`."""
    workdir = Path(root) / "docs" / "work"
    if not workdir.exists():
        return None
    for p in sorted(workdir.glob("*.md")):
        try:
            m = _OPEN_RE.search(p.read_text(encoding="utf-8"))
        except OSError:
            continue
        if m and m.group(1) == "ABIERTO":
            return p.name
    return None


def dirty_code(root: Path) -> list[str]:
    """Un-committed paths that are NOT `.md`. `git status --porcelain` already excludes gitignored
    state (`.proof/`, `build/`, `__pycache__`), so this sees only real code. `--untracked-files=all`
    expands untracked dirs to files (else git collapses `docs/` and the `.md` filter wouldn't apply)."""
    paths: list[str] = []
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root, capture_output=True, text=True,
        ).stdout
    except OSError:
        return paths
    for ln in out.splitlines():
        if not ln.strip():
            continue
        path = ln[3:]                       # porcelain format: 'XY <path>'
        if " -> " in path:                  # rename: 'orig -> new'
            path = path.split(" -> ", 1)[1]
        path = path.strip().strip('"')
        if path and not path.endswith(".md"):
            paths.append(path)
    return paths


def edit_allowed(root: Path, file_path: str) -> bool:
    """Layer 1 (ADR-010): editing a NON-`.md` file under the repo requires an open increment. `.md`
    (it is how an increment is OPENED) and files outside the repo are always allowed. Pure function —
    the decision lives HERE; the `increment_guard` hook is only transport (the placement law)."""
    try:
        target = Path(file_path).resolve()
        target.relative_to(Path(root).resolve())
    except (ValueError, OSError):
        return True   # outside the repo: not project code
    if target.suffix == ".md":
        return True
    return open_increment(root) is not None


def _fmt(paths: list[str]) -> str:
    head = ", ".join(paths[:3])
    return head + (f" (+{len(paths) - 3} más)" if len(paths) > 3 else "")


def debt(root: Path) -> tuple[bool, str]:
    """Cadence debt: inside an open increment there is un-committed (non-`.md`) code. The
    increment-close signal and the `meta check` surface."""
    inc = open_increment(root)
    if inc is None:
        return False, "sin incremento abierto"
    dirty = dirty_code(root)
    if not dirty:
        return False, f"incremento {inc}: árbol limpio"
    return True, f"incremento {inc}: código sin commitear — {_fmt(dirty)}"
