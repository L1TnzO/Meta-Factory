"""The footprint sweep: what GIT saw, compared to what the slot allowed.

This is the tooth that catches what neither permission layer can. INC-0 measured the hole directly:
a `deny` is per-TOOL, not per-EFFECT — the model was refused a `Write` and reached the same result
through `Bash`. Both the hook and `can_use_tool` see TOOL CALLS; git sees CONSEQUENCES.

So the acceptance of a delegated slot is not "no denial was recorded". It is:

    the git-observed change footprint  ⊆  allow_globs ∪ {verdict_path} ∪ .gen/** ∪ baseline_dirty

`baseline_dirty` is not a courtesy. Without it the sweep blames the generator for whatever was
already uncommitted when the slot opened, and a sweep that cries wolf is a sweep that gets disabled —
which is a worse outcome than not having one.

FAIL-CLOSED, and this is where it earns its name: if the manifest is broken, if git cannot be
observed, if anything is ambiguous — the answer is REFUSE. The alternative is a sweep that opens when
confused, and confusion is precisely the state an adversary arranges.
"""

from __future__ import annotations

import subprocess
from fnmatch import fnmatch
from pathlib import Path

from .slot import Slot, load

#: Always permitted: the slot's own scratch space. It is evidence, not product.
_SCRATCH = ".gen/"


def observed_paths(root: Path) -> tuple[list[str], str | None]:
    """Root-relative paths git reports as changed. Returns (paths, error) — never raises.

    `--porcelain` with `-uall` so that a NEW directory is reported file by file: `git status` would
    otherwise collapse an untracked directory into one entry, and a slot that wrote fifty files
    outside its radius would look like one deviation.
    """
    try:
        out = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=root,
                             capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return [], f"git could not be observed: {exc}"
    if out.returncode != 0:
        return [], f"git status failed: {out.stderr.strip()}"

    paths: list[str] = []
    for line in out.stdout.splitlines():
        if len(line) < 4:
            continue
        entry = line[3:]
        if " -> " in entry:  # a rename touches BOTH sides; a slot may not smuggle via renaming
            before, after = entry.split(" -> ", 1)
            paths.extend([before.strip().strip('"'), after.strip().strip('"')])
        else:
            paths.append(entry.strip().strip('"'))
    return paths, None


def allowed_by(slot: Slot, path: str) -> bool:
    if path.startswith(_SCRATCH) or path == slot.verdict_path or path in slot.baseline_dirty:
        return True
    return any(fnmatch(path, pattern) for pattern in slot.allow_globs)


def sweep(root: Path) -> tuple[str, list[str], dict]:
    """Returns (status, problems, facts) where status is GREEN | RED | FAIL-CLOSED.

    Three states rather than two, because they mean different things to whoever is on the other end:
    RED is "the slot went outside its radius" — a fact about the work. FAIL-CLOSED is "this cannot be
    decided" — a fact about the machinery. Reporting the second as the first would send someone to
    debug a generator when the manifest is what is broken.
    """
    slot, problems_found = load(Path(root))
    if problems_found:
        return "FAIL-CLOSED", problems_found, {"reason": "manifest"}
    if slot is None:
        # No manifest: nothing is being bounded, so there is nothing to accept or refuse.
        return "GREEN", [], {"reason": "no active slot", "observed": 0}

    paths, error = observed_paths(Path(root))
    if error:
        return "FAIL-CLOSED", [error], {"reason": "git"}

    outside = sorted(p for p in paths if not allowed_by(slot, p))
    facts = {"slot_id": slot.slot_id, "observed": len(paths), "outside": len(outside),
             "allow_globs": list(slot.allow_globs), "baseline_dirty": len(slot.baseline_dirty)}
    if outside:
        return "RED", [f"{p}: outside the slot's footprint" for p in outside], facts
    return "GREEN", [], facts
