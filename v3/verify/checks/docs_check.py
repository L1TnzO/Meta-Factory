#!/usr/bin/env python3
"""docs_check — the gate for ADR-009's docs-consistency law (`v3.memory.docs_manifest.check`),
PORTED from v2's `verify/checks/docs_check.py`.

    python3 -m v3.verify.checks.docs_check
    V3_DOCS_SABOTAGE=1 python3 -m v3.verify.checks.docs_check   # red side; must ALSO exit 0

GREEN — `check(root)` returns `[]`: every doc sealed & current, INDEX covers the set, no dangling
link, per-home STATE not stale. On THIS tree it does NOT return `[]`: full-stack-kotlin's
`docs/STATE.md` is older (by last commit) than a newer doc in its own level — real, pre-existing
debt this gate exists to surface, not launder. `v3.verify.corpus_parity --only docs` re-derives that
this answer matches v2's exactly, on this same tree, every run.

ROOT RESOLUTION mirrors every other v3 gate: default to the repo root
(`Path(__file__).resolve().parents[3]`), overridable by an optional positional path. v2 defaulted to
`Path.cwd()` instead — a CLI convenience `v3.memory.docs_manifest`'s own docstring records as CUT;
this gate's default matches the registered-gate convention so `meta check` never depends on cwd.

WHY THE WITNESS IS NEW — v2 has none. `check()` itself plainly has bite (a missing seal, a stale
sha, a drifted INDEX, a dangling link ARE real problems it reports on real trees), but v2's
`docs_check.py` module carries no sabotage of its own (`grep -ci sabotage` over it at the oracle ref
is 0) — under `v3.verify.registry`'s registration law a gate needs a *reachable* witness, not merely
a law that happens to bite today. So this port earns one: FOUR isolated synthetic corpora (a fresh
tempdir per class, `git init` + one commit each so the git-dependent freshness/log plumbing the real
law depends on actually runs), each planting exactly ONE of the defect classes `check()` is supposed
to catch — seal absent, sha stale, INDEX coverage gap, dangling link. The REAL
`v3.memory.docs_manifest.check` runs over each corpus; nothing here reimplements the law, only
builds fixtures for it (the same shape `generality`'s `_run_sabotage` uses over `audit_mechanism`).
Isolating each class in its OWN corpus (rather than one corpus with all four planted at once) is
what makes a catch — or a miss — attributable to exactly one class instead of rounded up.

CONTRACT (`v3.verify.registry.Gate.red_run`'s docstring — the opposite of the obvious one): the
sabotage run must exit 0 when it CAUGHT all four classes, printing the catch; it exits 1 with
`GATE DECORATIVO` when any class went unnoticed. A crash and a decorative pass both read as "not 0"
under the obvious convention and would be indistinguishable; this one forces the witness to REPORT
what it caught, so a partial catch (e.g. 1/4) is visible rather than silently rounded up to green.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

from ...kernel.report import Verdict
from ...memory import docs_manifest as manifest

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_DOCS_SABOTAGE"

_INDEX_HEADER = (
    "| Doc | sha (git blob, body) | updated | resumen |\n"
    "| --- | --- | --- | --- |\n"
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _seed_repo(root: Path) -> None:
    (root / "docs").mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "docs-sabotage@local")
    _git(root, "config", "user.name", "docs-sabotage")


def _commit_all(root: Path) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed")


def _index_row(state: Path) -> str:
    """A well-formed INDEX row for an already-stamped `state` doc (sha read back from its own seal —
    reuses the REAL law's regex, never a re-derivation of the hash)."""
    seal, _ = manifest.split_seal(state.read_text(encoding="utf-8"))
    sha = manifest.SEAL_RE.match(seal).group(1)
    return f"| `docs/{state.name}` | `{sha[:12]}` | 2026-01-01T00:00Z | {state.stem} |\n"


# ── the four isolated corpora — one class planted, nothing else ────────────────────────────────
def _corpus_seal_absent(tmp: Path) -> Path:
    """Class 1: a doc with NO `<!-- meta:doc … -->` header at all."""
    root = tmp / "seal_absent"
    _seed_repo(root)
    (root / "docs" / "STATE.md").write_text("# STATE\n\nnever sealed.\n", encoding="utf-8")
    (root / "INDEX.md").write_text(
        _INDEX_HEADER + "| `docs/STATE.md` | `unsealed0000` | 2026-01-01T00:00Z | STATE |\n",
        encoding="utf-8")
    _commit_all(root)
    return root


def _corpus_sha_stale(tmp: Path) -> Path:
    """Class 2: a doc whose seal sha does not match its body's blob sha (body edited, seal left)."""
    root = tmp / "sha_stale"
    _seed_repo(root)
    state = root / "docs" / "STATE.md"
    state.write_text("# STATE\n\noriginal body.\n", encoding="utf-8")
    manifest.stamp(state)                                  # seal now matches the original body
    seal, body = manifest.split_seal(state.read_text(encoding="utf-8"))
    state.write_text(f"{seal}\n{body}an edit the seal never saw.\n", encoding="utf-8")
    (root / "INDEX.md").write_text(_INDEX_HEADER + _index_row(state), encoding="utf-8")
    _commit_all(root)
    return root


def _corpus_index_gap(tmp: Path) -> Path:
    """Class 3: INDEX.md exists and is well-formed, but is missing a row for a doc that exists."""
    root = tmp / "index_gap"
    _seed_repo(root)
    state, other = root / "docs" / "STATE.md", root / "docs" / "OTHER.md"
    state.write_text("# STATE\n\nbody.\n", encoding="utf-8")
    other.write_text("# OTHER\n\nan un-indexed doc.\n", encoding="utf-8")
    manifest.stamp(state)
    manifest.stamp(other)
    (root / "INDEX.md").write_text(_INDEX_HEADER + _index_row(state), encoding="utf-8")  # OTHER.md omitted
    _commit_all(root)
    return root


def _corpus_dangling_link(tmp: Path) -> Path:
    """Class 4: a `.md` link in `docs/STATE.md` pointing at a file that is not there."""
    root = tmp / "dangling_link"
    _seed_repo(root)
    state = root / "docs" / "STATE.md"
    state.write_text("# STATE\n\nSee [the ghost](docs/GHOST.md) for detail.\n", encoding="utf-8")
    manifest.stamp(state)
    (root / "INDEX.md").write_text(_INDEX_HEADER + _index_row(state), encoding="utf-8")
    _commit_all(root)
    return root


# (class name, corpus builder, substring that must appear in `check()`'s output when this — and
# only this — class is planted)
_CLASSES: tuple[tuple[str, Callable[[Path], Path], str], ...] = (
    ("seal_absent", _corpus_seal_absent, "missing content-addressed seal"),
    ("sha_stale", _corpus_sha_stale, "stale seal (sha != body)"),
    ("index_gap", _corpus_index_gap, "does not list docs/OTHER.md"),
    ("dangling_link", _corpus_dangling_link, "dangling link -> docs/GHOST.md"),
)


def _run_sabotage() -> int:
    caught: list[str] = []
    with tempfile.TemporaryDirectory(prefix="v3-docs-sabotage-") as tmp:
        tmpdir = Path(tmp)
        for name, build, needle in _CLASSES:
            root = build(tmpdir)
            problems = manifest.check(root)
            if any(needle in p for p in problems):
                caught.append(name)

    if len(caught) == len(_CLASSES):
        return Verdict("v3-docs-check (SABOTAGE)", 0,
                       f"{len(caught)}/{len(_CLASSES)} planted defects caught "
                       f"({', '.join(name for name, _, _ in _CLASSES)})").emit()

    missed = [name for name, _, _ in _CLASSES if name not in caught]
    return Verdict("v3-docs-check (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {len(caught)}/{len(_CLASSES)} planted defects caught "
                   f"({', '.join(caught) or 'none'}) — missed {missed}: no teeth on those classes"
                   ).emit()


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        return Verdict("v3-docs-check", 2, f"takes at most one path argument; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage()

    root = Path(argv[0]) if argv else _ROOT
    problems = manifest.check(root)
    if problems:
        return Verdict("v3-docs-check", 1, f"{len(problems)} docs-consistency problem(s)",
                       failures=tuple(problems),
                       next_action="reseal via docs_manifest.sync, then fix any remaining INDEX "
                                   "drift / dangling link / stale-STATE by hand").emit()

    return Verdict("v3-docs-check", 0,
                   "docs consistent: every doc sealed & current, INDEX covers the set, no dangling "
                   f"link, STATE not stale; red tooth alive ({len(_CLASSES)} defect classes caught "
                   f"under {_SABOTAGE_VAR}=1)").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
