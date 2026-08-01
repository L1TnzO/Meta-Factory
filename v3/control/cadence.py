"""cadence — commit discipline (ADR-010), PORTED from v2's `memory/cadence.py` at the oracle commit.

Zero model: git + file-IO + arithmetic. Two deterministic questions, re-derivable from the working
tree + the open increment:
  - is there un-committed (non-`.md`) code INSIDE an open increment?                  -> debt()
  - was a station gate closed GREEN since the last commit, with the tree still dirty? -> stop_block()
Plus the placement law the `increment_guard` hook transports (not decides):
  - is a (non-`.md`) file open for edit with an increment open AT ITS LEVEL?          -> edit_allowed()
  - which `docs/work/` would AUTHORIZE that edit?                                    -> required_workdir_rel()

THE LAW ITSELF (open_increment / dirty_code / edit_allowed / debt / required_workdir_rel) lives in
`seed/lifecycle.py` — the single source the meta and every produced factory share (a produced
factory's own inherited `increment_guard` loads a byte-identical copy) — and this module DELEGATES to
it via `v3.seed_loader.load_seed_lifecycle`, exactly as v2's `memory/cadence.py` delegated via its own
`_seed.load_seed_lifecycle`. `debt`, `edit_allowed` and `required_workdir_rel` are therefore straight
pass-throughs: the decision, and its exact return SHAPE, is computed by the seed, never re-derived
here. Only `stop_block` carries logic OF ITS OWN: it is the meta's Tier-0 backstop, reading the
journal for a station gate that passed since the last commit — v2 kept this OUT of the seed on
purpose (the seed only knows increments and git status, never the journal), and this port keeps that
split.

LAW (this port, INC column-law): the return SHAPES and the exact decision VOCABULARY are UNCHANGED
from v2 — `gate_guard`/`stop_proof` branch on the booleans this module returns, and `increment_guard`
PARSES `required_workdir_rel`'s trailing `/docs/work` to name the owning level. Only human-readable
PROSE (the reason string in each returned tuple) becomes English; the decision itself never moves.

WIRING CHANGE FROM v2 (the law is unchanged, only how it reaches the journal): v2's `journal.read`
returned a bare `list[dict]`; the already-ported `v3.memory.journal.read` returns `(rows, exists)` —
an ABSENT journal is now distinguishable from an EMPTY one (see that module's own docstring). This
port unpacks `rows` and ignores `exists`: an absent journal simply has no rows to find a passed gate
in, which is exactly what `stop_block` needs it to mean.

Does NOT auto-commit: debt is surfaced and blocked, never silently fixed; the commit message (with
I-10 trailers) is written by the model. The cadence is an AID, not a security boundary (the anti-seal
column is that boundary); on any doubt, PERMIT.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ..memory import journal
from ..seed_loader import load_seed_lifecycle

_MIN = datetime.min.replace(tzinfo=timezone.utc)


def _git(root: Path, *args: str) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
        return out.stdout
    except OSError:
        return ""


# -- the LAW: delegated straight to the seed (single source shared with a produced factory) --------

def debt(root: Path) -> tuple[bool, str]:
    """Cadence debt: un-committed (non-`.md`) code inside an open increment. `gate_guard` branches on
    the bool; the reason string is prose only, never parsed."""
    return load_seed_lifecycle().debt(Path(root))


def edit_allowed(root: Path, file_path: str) -> bool:
    """Layer 1 (ADR-010 + ADR-016, level-aware placement law). `increment_guard` branches on this."""
    return load_seed_lifecycle().edit_allowed(Path(root), file_path)


def required_workdir_rel(root: Path, file_path: str) -> str | None:
    """The `docs/work/` (relative to `root`) whose open increment would authorize editing
    `file_path`, or None when none is needed. `increment_guard` PARSES this exact string
    (`.endswith("/docs/work")`) to name the owning level — the shape is load-bearing, which is why
    this stays a straight delegation to the seed rather than a re-derivation."""
    return load_seed_lifecycle().required_workdir_rel(Path(root), file_path)


# -- private helpers `stop_block` needs, and nothing else -------------------------------------------

def _open_increment(root: Path) -> str | None:
    """The META-level open increment. Private: `stop_block`'s own read of the seed law, not part of
    the four-function public contract this port carries."""
    return load_seed_lifecycle().open_increment(Path(root))


def _dirty_code(root: Path) -> list[str]:
    return load_seed_lifecycle().dirty_code(Path(root))


def _fmt(paths: list[str]) -> str:
    head = ", ".join(paths[:3])
    return head + (f" (+{len(paths) - 3} more)" if len(paths) > 3 else "")


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


def _passed_gate_since_commit(root: Path) -> bool:
    """Was a station gate closed GREEN since the last commit? A fact from the journal (Tier 0), not
    narrative — distinguishes "a proven gate passed" from "src is being edited" (WIP), so ordinary
    work-in-progress is never nagged."""
    since = _last_commit_dt(root)
    rows, _ = journal.read(Path(root), kinds={"station_run"})
    return any(
        r.get("passed") and _parse_journal_ts(str(r.get("ts", ""))) > since
        for r in rows
    )


def stop_block(root: Path) -> tuple[bool, str]:
    """Turn-close backstop: PROVEN progress (a station gate passed green since the last commit) sits
    in a dirty tree inside an open increment. Catches "passed the last gate and closed without
    committing". `stop_proof` branches on the bool; the reason string is prose only, never parsed."""
    inc = _open_increment(root)
    if inc is None:
        return False, "no open increment"
    if not _passed_gate_since_commit(root):
        return False, "no un-committed green gate (not a cadence backstop case)"
    dirty = _dirty_code(root)
    if not dirty:
        return False, "clean tree"
    return True, f"green gate un-committed (increment {inc}) — {_fmt(dirty)}"
