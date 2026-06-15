"""renderer — applies a station's `builds` actions to render the factory chassis.

Build actions (declared as data in the station YAML):
  - {action: mkdir, path}
  - {action: write, dest, content}                 inline content (substituted)
  - {action: render, src, dest}                    one template file (src rel meta_root)
  - {action: render_tree, src, dest}               a template subtree (paths + content)
  - {action: copy_seed}                            install the inherited column (M1)
  - {action: generate, dest, via, brief?}          the CREATIVE SLOT (C1, ADR-013)

`render`/`render_tree`/`generate` accept `skip_if_exists: true`: if the dest already exists it
is LEFT UNTOUCHED. For render this is the generated/domain boundary (I-5, M4): the factory's
`domain/` is rendered with the flag (human-owned code survives a re-scaffold); `generated/` is
rendered without it (the chassis owns it, re-rendered every time). For `generate` the flag means
"don't re-invoke the generator if the slot is already filled" (e.g. a non-deterministic LLM).

`generate` is the seam that keeps generation OUT of the substrate (ADR-012, I-3): the substrate
ORCHESTRATES a generator DECLARED IN DATA and VERIFIES nothing itself — see `_generate`.

Placeholders use `{{var}}` and are filled from `subst` (derived from the factory-spec).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid a runtime cycle: codegen must not import the engine package
    from ..engine.run_context import RunContext
    from ..engine.station import Station

_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def render_text(text: str, subst: dict) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1)
        if key not in subst:
            raise KeyError(f"template placeholder {{{{{key}}}}} has no value in subst")
        return str(subst[key])

    return _PLACEHOLDER.sub(repl, text)


def _render_path(path_str: str, subst: dict) -> str:
    return render_text(path_str, subst)


def apply_builds(ctx: RunContext, station: Station, subst: dict) -> list[str]:
    msgs: list[str] = []
    for b in station.builds:
        action = b.get("action")
        if action == "mkdir":
            dest = ctx.root / _render_path(b["path"], subst)
            dest.mkdir(parents=True, exist_ok=True)
            msgs.append(f"mkdir {dest.relative_to(ctx.root)}")
        elif action == "write":
            dest = ctx.root / _render_path(b["dest"], subst)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(render_text(b.get("content", ""), subst), encoding="utf-8")
            msgs.append(f"write {dest.relative_to(ctx.root)}")
        elif action == "render":
            src = ctx.meta_root / b["src"]
            dest = ctx.root / _render_path(b["dest"], subst)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if b.get("skip_if_exists") and dest.exists():
                msgs.append(f"skip(exists) {dest.relative_to(ctx.root)}")
            else:
                dest.write_text(render_text(src.read_text(encoding="utf-8"), subst), encoding="utf-8")
                msgs.append(f"render {dest.relative_to(ctx.root)}")
        elif action == "render_tree":
            msgs += _render_tree(ctx.meta_root / b["src"], ctx.root / _render_path(b["dest"], subst),
                                 subst, ctx.root, skip_if_exists=bool(b.get("skip_if_exists")))
        elif action == "copy_seed":
            msgs += _copy_seed(ctx)
        elif action == "generate":
            msgs += _generate(ctx, b, subst)
        else:
            raise ValueError(f"unknown build action {action!r} in station {station.id}")
    return msgs


def _generate(ctx: RunContext, b: dict, subst: dict) -> list[str]:
    """The CREATIVE SLOT (C1, ADR-013) — the substrate ORCHESTRATES, it does NOT generate.

    Steps: (1) write the blueprint BRIEF (the contract the generator works against — derived
    deterministically from spec data, it is INPUT not the artifact); (2) run the generator
    DECLARED IN DATA (`via` argv — the substrate names no tech, ADR-012); the generator is the
    sole writer of `dest`. The substrate writes NEITHER the artifact NOR a verdict: if the
    generator fails, can't launch, or produces nothing, `dest` is absent/wrong and the COLUMN
    (the station's checks) renders the honest red. Determinism lives in verification, not here (I-3).

    `via` may be a deterministic scaffolder OR a live `claude -p "<brief>"` — same seam, different
    data. The generator reads its contract from env: METAFACTORY_BRIEF (path), METAFACTORY_DEST
    (path it must write), METAFACTORY_ROOT (factory root). `via` argv also gets `{{var}}` subst.
    """
    dest = ctx.root / _render_path(b["dest"], subst)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if b.get("skip_if_exists") and dest.exists():
        return [f"skip(exists) {dest.relative_to(ctx.root)}"]
    # Start each generation from absent: a failing generator must NOT pass on a stale artifact
    # (the no-fake invariant — each run's gate reflects exactly what THIS generation produced).
    if dest.exists():
        dest.unlink()

    env = dict(os.environ)
    env["METAFACTORY_DEST"] = str(dest)
    env["METAFACTORY_ROOT"] = str(ctx.root)
    msgs: list[str] = []
    if "brief" in b:
        rel = b.get("brief_dest") or f".gen/{dest.name}.brief.md"
        brief = ctx.root / _render_path(rel, subst)
        brief.parent.mkdir(parents=True, exist_ok=True)
        brief.write_text(render_text(b["brief"], subst), encoding="utf-8")
        env["METAFACTORY_BRIEF"] = str(brief)
        msgs.append(f"brief {brief.relative_to(ctx.root)}")

    via = [render_text(str(a), subst) for a in b["via"]]
    try:
        rc = subprocess.run(via, cwd=ctx.root, env=env, capture_output=True, text=True).returncode
    except OSError as exc:
        rc = 127  # generator could not even launch — never raise past the verdict (fail-safe)
        msgs.append(f"generate-launch-error via={via[0] if via else '?'}: {type(exc).__name__}")
    msgs.append(f"generate {dest.relative_to(ctx.root)} via={via[0] if via else '?'} "
                f"rc={rc} produced={dest.exists()}")
    return msgs


def _render_tree(src_root: Path, dest_root: Path, subst: dict, root: Path,
                 skip_if_exists: bool = False) -> list[str]:
    msgs: list[str] = []
    for src in sorted(src_root.rglob("*")):
        if src.is_dir() or "__pycache__" in src.parts:
            continue
        rel = src.relative_to(src_root)
        dest = dest_root / _render_path(str(rel), subst)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if skip_if_exists and dest.exists():
            msgs.append(f"skip(exists) {dest.relative_to(root)}")
            continue
        try:
            content = src.read_text(encoding="utf-8")
            dest.write_text(render_text(content, subst), encoding="utf-8")
        except UnicodeDecodeError:
            shutil.copy2(src, dest)  # binary asset: copy verbatim
        msgs.append(f"render {dest.relative_to(root)}")
    return msgs


def _copy_seed(ctx: RunContext) -> list[str]:
    """M1: install the inherited column — copy the frozen seed verbatim into the factory.
    The factory's trust root IS the Meta-Factory's seed (same doctrine, same code)."""
    src = ctx.meta_root / "seed"
    dest = ctx.root / "seed"
    dest.mkdir(parents=True, exist_ok=True)
    msgs: list[str] = []
    for f in sorted(src.iterdir()):
        if f.is_file():
            shutil.copy2(f, dest / f.name)
            msgs.append(f"copy_seed seed/{f.name}")
    return msgs
