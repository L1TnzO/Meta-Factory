"""lifecycle — the increment-cadence LAW (ADR-010), part of the frozen Stage-0 seed.

Zero model, zero `metafactory.*`: git + file-IO + a docs scan. This is the single source of the
commit-discipline law, COPIED VERBATIM into every produced factory (like `verifier.py`) so a factory
governs its OWN increment lifecycle ALONE — its inherited `increment_guard` hook loads THIS file by
path, and the Meta-Factory's own `memory.cadence`/`memory.projection` DELEGATE here, so the factory
and the meta enforce the IDENTICAL law (no divergence, the trust-chain single-source principle).

Two deterministic questions, re-derivable from the working tree + the open increment:
  - is a (non-`.md`) file open for edit with NO increment open AT ITS LEVEL?     → edit_allowed()
  - is there un-committed (non-`.md`) code INSIDE an open increment?             → debt()

The edit-gate is LEVEL-AWARE (ADR-016): the level of a file is the MOST SPECIFIC of meta / factory /
product that contains it, and editing it needs the open increment of THAT level's `docs/work/`. The
resolution is pure path arithmetic — DATA-agnostic, no factory/product slug is hardcoded.

The TRUTH is git (the tree) + docs (the increment, `Status: **OPEN**` — legacy Spanish grammar
`Estado: **ABIERTO**` is accepted forever: closed history is immutable, ADR-026); this only READS and
projects it. It NEVER auto-commits: the debt is surfaced and blocked; the message (with I-10 trailers)
is written by the model. Outside an increment there is no debt — that frontier is the edit-gate.

The cadence is an AID, not a security boundary (the rubber-stamp column is): on any doubt, PERMIT —
never brick an edit/commit. The security root is the verdict re-derivation (`verifier.py`), not this.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

# Dual-accept grammar (ADR-026): English forward (`Status: **OPEN/CLOSED**`), Spanish accepted
# forever (`Estado: **ABIERTO/CERRADO**`) — closed work docs are immutable history.
_OPEN_RE = re.compile(r"(?:Estado|Status):\s*\*\*(ABIERTO|CERRADO|OPEN|CLOSED)\*\*")
_OPEN_MARKS = {"ABIERTO", "OPEN"}


def open_increment_in(workdir: Path) -> str | None:
    """The filename of the single open increment (`*.md` with `Status: **OPEN**`, or the legacy
    `Estado: **ABIERTO**`) inside a given `docs/work/` directory, or None. A level OPENS one by
    writing such a `.md` (an `.md` is always editable, so this self-bootstraps); CLOSES it by
    flipping the header to `**CLOSED**`."""
    workdir = Path(workdir)
    if not workdir.exists():
        return None
    for p in sorted(workdir.glob("*.md")):
        try:
            m = _OPEN_RE.search(p.read_text(encoding="utf-8"))
        except OSError:
            continue
        if m and m.group(1) in _OPEN_MARKS:
            return p.name
    return None


def open_increment(root: Path) -> str | None:
    """The META-level open increment (`docs/work/*.md` with an open header), or None. The
    projection/rehydrate banner and the cadence backstop read THIS (meta) level; the level-aware
    edit-gate uses `open_increment_in(level_workdir(...))`."""
    return open_increment_in(Path(root) / "docs" / "work")


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


def level_workdir(root: Path, file_path: str) -> Path:
    """The `docs/work/` of the MOST SPECIFIC level that contains `file_path` (ADR-016, level-aware
    edit-gate). Pure path arithmetic — DATA-agnostic, no factory/product slug is hardcoded:
      - `factories/<f>/products/<p>/**`  → that product's `docs/work/`
      - `factories/<f>/**` (not products) → that factory's `docs/work/`
      - everything else (`src/`, `seed/`, `stations/`, root) → the meta `docs/work/`
    `file_path` is assumed inside `root` (the caller checks); on any doubt, returns the meta dir."""
    root = Path(root).resolve()
    try:
        parts = Path(file_path).resolve().relative_to(root).parts
    except (ValueError, OSError):
        return root / "docs" / "work"
    if len(parts) >= 5 and parts[0] == "factories" and parts[2] == "products":
        return root / "factories" / parts[1] / "products" / parts[3] / "docs" / "work"
    if len(parts) >= 3 and parts[0] == "factories":
        return root / "factories" / parts[1] / "docs" / "work"
    return root / "docs" / "work"


def edit_allowed(root: Path, file_path: str) -> bool:
    """Layer 1 (ADR-010 + ADR-016, level-aware): editing a NON-`.md` file requires an open increment
    in the `docs/work/` of the file's LEVEL (meta / factory / product — the most specific that contains
    it). `.md` (it is how an increment is OPENED) and files outside the repo are always allowed. Pure
    function — the decision lives HERE; the `increment_guard` hook is only transport (placement law)."""
    try:
        rootp = Path(root).resolve()
        target = Path(file_path).resolve()
        target.relative_to(rootp)
    except (ValueError, OSError):
        return True   # outside the repo: not project code
    if target.suffix == ".md":
        return True
    return open_increment_in(level_workdir(rootp, str(target))) is not None


def required_workdir_rel(root: Path, file_path: str) -> str | None:
    """The `docs/work/` (relative to `root`) whose open increment would AUTHORIZE editing `file_path`,
    or None when no increment is needed (`.md` / outside the repo). For the guard's error message —
    so it names the LEVEL the edit belongs to, not a generic 'open an increment'."""
    try:
        rootp = Path(root).resolve()
        target = Path(file_path).resolve()
        target.relative_to(rootp)
    except (ValueError, OSError):
        return None
    if target.suffix == ".md":
        return None
    return str(level_workdir(rootp, str(target)).relative_to(rootp))


def _fmt(paths: list[str]) -> str:
    head = ", ".join(paths[:3])
    return head + (f" (+{len(paths) - 3} more)" if len(paths) > 3 else "")


def debt(root: Path) -> tuple[bool, str]:
    """Cadence debt: inside an open increment there is un-committed (non-`.md`) code. The
    increment-close signal and the `meta check` surface."""
    inc = open_increment(root)
    if inc is None:
        return False, "no open increment"
    dirty = dirty_code(root)
    if not dirty:
        return False, f"increment {inc}: clean tree"
    return True, f"increment {inc}: un-committed code — {_fmt(dirty)}"
