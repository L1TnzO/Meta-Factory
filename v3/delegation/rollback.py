"""Undo what a red slot wrote — with git, because the SDK's own checkpoint could not be driven.

MEASURED 2026-07-28 (INC-3 phase 5). §10.8 proposes `enable_file_checkpointing=True` plus
`rewind_files(user_message_id)`. Checkpointing turns on and `rewind_files` exists, but **no message
id the stream exposes corresponds to a checkpoint**: fourteen candidates were tried — every
`UserMessage.uuid`, every `AssistantMessage.uuid` and `.message_id`, the `ResultMessage.uuid` — and
all fourteen returned `No file checkpoint found for this message`. The checkpoint lives somewhere the
stream does not name.

So v3 owns its rollback, and that is arguably where it belonged. The host owns the loop and the
footprint sweep already knows exactly which paths changed, so the undo is a deterministic git
operation rather than a feature we would have to keep hoping about:

  * tracked files that the slot modified  → `git checkout --` them
  * untracked files the slot created      → delete them
  * anything in `baseline_dirty`          → LEFT ALONE. It was not the slot's, and a rollback that
                                            eats the operator's uncommitted work is worse than none.

It is also auditable in a way the SDK's version would not have been: every path it touches is
reported, so an undo can be read afterwards instead of trusted.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .footprint import allowed_by, observed_paths
from .slot import Slot


def plan(slot: Slot, root: Path) -> tuple[list[str], list[str], list[str]]:
    """What an undo WOULD do: (restore, delete, spared). Pure enough to inspect before running."""
    paths, error = observed_paths(Path(root))
    if error:
        return [], [], []

    restore: list[str] = []
    delete: list[str] = []
    spared: list[str] = []
    for path in paths:
        if path in slot.baseline_dirty:
            spared.append(path)
            continue
        if not allowed_by(slot, path):
            # Outside the radius: the sweep already called this RED. Undoing it here would erase
            # the evidence of the violation before anyone saw it.
            spared.append(path)
            continue
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", path], cwd=root,
                                 capture_output=True, text=True).returncode == 0
        (restore if tracked else delete).append(path)
    return sorted(restore), sorted(delete), sorted(spared)


def rollback(slot: Slot, root: Path) -> dict:
    """Execute the plan. Returns exactly what it did — an undo you cannot read is an undo you cannot
    audit."""
    restore, delete, spared = plan(slot, Path(root))
    if restore:
        subprocess.run(["git", "checkout", "--", *restore], cwd=root, capture_output=True)
    for path in delete:
        target = Path(root) / path
        if target.is_file():
            target.unlink()
    return {"restored": restore, "deleted": delete, "spared": spared}
