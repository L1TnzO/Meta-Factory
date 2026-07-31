"""Build actions: what a station WRITES before its checks decide.

A station is data (I-2) and its `builds` list is the part of that data which produces artifacts. The
substrate applies the action; it never knows what the artifact IS. `render` copies a template, and
whether that template is Python, Kotlin or a docker-compose file is not a branch here (ADR-012).

FOUR ACTIONS, because `dummy` exercises four. That is deliberate, and it is the same reasoning INC-5
used to defer `journal`: porting an action with no line that runs it produces a module nobody calls,
and a module nobody calls is not future-proofing — it is unverified code with a docstring. The rest
(`render_tree`, `copy_seed`, `materialize_line`, `emit_harness`, `emit_boundary`, `mkdir`, `write`)
arrive with the factory that needs them, each carried by a line that exercises it.

AN UNKNOWN ACTION RAISES. It is not skipped, not logged, not tolerated. A build that does not run and
does not complain leaves a station whose checks then run against whatever was already on disk — which
is precisely how a line reports green having built nothing. The `for` loop that would have quietly
`continue`d is the bug; the `raise` is the feature.

THE CREATIVE SLOT stays a seam, not a capability (ADR-013, I-3): `generate` writes a brief, hands the
generator its contract through the environment, and runs the argv the DATA declared. It writes neither
the artifact nor a verdict. If the generator fails, cannot launch, or produces nothing, `dest` is
absent and the station's checks render the honest red — the substrate does not get an opinion.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ..verify.kinds import _render_text as render_text


@dataclass(frozen=True)
class BuildContext:
    """Where a build reads from, where it writes to, and what it substitutes.

    `root` is the FACTORY (or product) directory being built; `meta_root` is the tree a `render`
    source path is relative to. They are separate because a re-derivation runs both of them out of a
    copy, and a builder that assumed `meta_root == root.parent.parent` would silently read the
    developer's working tree instead of the copy under test.
    """

    root: Path
    meta_root: Path
    subst: dict = field(default_factory=dict)
    #: Where the factory's GENERATOR lives (`codegen/`, the `generate` slot's `via`). For the DEFAULT
    #: product it IS `root`; for a product INSTANCE (R1, ADR-015) `root` is `products/<p>/` — its own
    #: evidence and its own pin — while the chassis stays `factories/<slug>/`, the shared generator.
    #: `None` means "same as root", which keeps the 1:1 line byte-identical.
    chassis: Path | None = None

    @property
    def generator_home(self) -> Path:
        return self.chassis if self.chassis is not None else self.root


def apply_builds(station: dict, ctx: BuildContext) -> list[str]:
    """Apply one station's `builds`, in order. Returns a message per artifact, for the log only —
    the messages are never evidence; the station's checks are."""
    messages: list[str] = []
    for build in station.get("builds") or ():
        action = build.get("action")
        if action == "render":
            messages.append(_render(build, ctx))
        elif action == "write":
            messages.append(_write(build, ctx))
        elif action == "generate":
            messages += _generate(build, ctx)
        elif action in ("emit_infra", "emit_mcp"):
            messages += _emit_glue(action.removeprefix("emit_"), ctx)
        else:
            raise ValueError(
                f"unknown build action {action!r} in station {station.get('id')!r}: v3 ports the "
                f"actions a migrated line exercises, and refuses the rest LOUDLY — silently skipping "
                f"it would leave the checks running against whatever was already on disk")
    return messages


def _render(build: dict, ctx: BuildContext) -> str:
    """One template file: `src` relative to `meta_root`, `dest` relative to `root`, `{{var}}` filled.

    `skip_if_exists` is the I-5 generated/domain boundary: a factory's `domain/` is rendered with the
    flag so human-owned code survives a re-scaffold, `generated/` without it because the chassis owns
    it and re-renders every time.
    """
    src = ctx.meta_root / build["src"]
    dest = ctx.root / render_text(str(build["dest"]), ctx.subst)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if build.get("skip_if_exists") and dest.exists():
        return f"skip(exists) {dest.relative_to(ctx.root)}"
    dest.write_text(render_text(src.read_text(encoding="utf-8"), ctx.subst), encoding="utf-8")
    return f"render {dest.relative_to(ctx.root)}"


def _write(build: dict, ctx: BuildContext) -> str:
    """One INLINE file: `content` from the build itself, `dest` relative to `root`, `{{var}}` filled.

    The sibling of `render` for content small enough to live in the spec instead of a template file, so
    it takes no `src` and no `meta_root`. PORTED when the line first exercised it (V3-INC9): the only
    caller today is `snipeit`'s `s6`, and it only became reachable once instances started deriving their
    line from their own spec (`N-0108`) — the chassis's older rendering of that station used `render`
    instead (`N-0109`). Before that, `apply_builds` refused it loudly, which is how it was found.

    `skip_if_exists` is deliberately NOT honoured: v2's `write` does not read that flag either (only its
    `render` does). Adding it here would be an improvement over the oracle, and an improvement is a
    divergence — the same discipline that keeps `resolve_check` passing `ctx=None`.
    """
    dest = ctx.root / render_text(str(build["dest"]), ctx.subst)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render_text(build.get("content", ""), ctx.subst), encoding="utf-8")
    return f"write {dest.relative_to(ctx.root)}"


def _resolve_via_against_chassis(arg: str, ctx: BuildContext) -> str:
    """Resolve a relative `via` file-arg (the generator script) against the CHASSIS.

    A product INSTANCE runs with `cwd == root == products/<p>/`, but the factory's generator lives in
    the chassis — so the argv `python codegen/scaffold_product.py`, taken literally from the instance's
    workdir, names a file that does not exist. The generator then fails to launch, `dest` stays absent
    and the station goes red for a reason that has nothing to do with the product (measured on
    `iot/fleet` before this existed).

    ONLY a relative arg that names an existing file under the chassis is rewritten, to its absolute
    path. Interpreters, flags and inline code (`python`, `-c`, `…`) are left verbatim — the substrate
    names no tech (ADR-012); `arg` is free DATA the plan chose. For the default product (chassis ==
    root) this rewrites the same file to an absolute path, which is functionally identical: the
    generate slot is build-time and argv never enters the exit-code-based `proof_sha`.
    """
    if os.path.isabs(arg):
        return arg
    cand = ctx.generator_home / arg
    return str(cand.resolve()) if cand.is_file() else arg


def _generate(build: dict, ctx: BuildContext) -> list[str]:
    """The creative slot (C1, ADR-013): orchestrate a generator declared in DATA; verify nothing.

    The generator is the SOLE writer of `dest`, and `dest` is removed first: a failing generator must
    never pass on a stale artifact left by the previous run. That deletion is the whole no-fake
    invariant of this action — without it a green station could be reporting on yesterday's output.
    """
    dest = ctx.root / render_text(str(build["dest"]), ctx.subst)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if build.get("skip_if_exists") and dest.exists():
        return [f"skip(exists) {dest.relative_to(ctx.root)}"]
    if dest.exists():
        dest.unlink()

    env = dict(os.environ)
    env["METAFACTORY_DEST"] = str(dest)
    env["METAFACTORY_ROOT"] = str(ctx.root)
    messages: list[str] = []
    if "brief" in build:
        rel = build.get("brief_dest") or f".gen/{dest.name}.brief.md"
        brief = ctx.root / render_text(str(rel), ctx.subst)
        brief.parent.mkdir(parents=True, exist_ok=True)
        brief.write_text(render_text(build["brief"], ctx.subst), encoding="utf-8")
        env["METAFACTORY_BRIEF"] = str(brief)
        messages.append(f"brief {brief.relative_to(ctx.root)}")

    via = [_resolve_via_against_chassis(render_text(str(a), ctx.subst), ctx) for a in build["via"]]
    try:
        rc = subprocess.run(via, cwd=str(ctx.root), env=env, capture_output=True,
                            text=True).returncode
    except OSError as exc:
        rc = 127  # the generator could not even launch — never raise past the verdict (fail-safe)
        messages.append(f"generate-launch-error via={via[0] if via else '?'}: {type(exc).__name__}")
    messages.append(f"generate {dest.relative_to(ctx.root)} via={via[0] if via else '?'} "
                    f"rc={rc} produced={dest.exists()}")
    return messages


def _emit_glue(section: str, ctx: BuildContext) -> list[str]:
    """E1/E2 — write the L3 machinery glue the downstream gate stands up: `machinery.<section>.emit`.

    The substrate enumerates NOTHING. Each entry's `dest`/`content` is free DATA the plan chose: a
    socket server, a docker-compose.yml and an MCP server are the same action with different data.
    The LIFECYCLE (up/proof/down, prove/tools) rides in the station's CHECK, not here — this action
    only writes the files those argv will invoke.
    """
    from ..spec.loader import load_spec   # local: the builder is not a spec consumer at import time

    spec = load_spec(ctx.root / "factory.spec.yml")
    emit = (getattr(spec.machinery, section) or {}).get("emit", []) or []
    messages: list[str] = []
    for item in emit:
        if not isinstance(item, dict) or not str(item.get("dest", "")).strip():
            continue  # the M0 validator already flagged it; skip defensively rather than crash here
        dest = ctx.root / render_text(str(item["dest"]), ctx.subst)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(render_text(str(item.get("content", "")), ctx.subst), encoding="utf-8")
        messages.append(f"emit {section} {dest.relative_to(ctx.root)}")
    return messages
