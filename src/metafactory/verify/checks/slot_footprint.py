"""slot_footprint — the delegation boundary is HONEST (SOTA-PARITY INC-1, SLOT-FOOTPRINT-TOOTH).

Slot acceptance is deterministic on the OBSERVED change footprint: git-observed changes must be
⊆ allow_globs ∪ {verdict_path} ∪ .gen/** ∪ baseline_dirty. This closes GAP-1 (SOTA-PARITY §3): a generator
with Bash could write outside its slot without the PreToolUse Write-hook firing; the footprint is enforced
at SubagentStop (transport: `.claude/hooks/verdict_required.py`) and re-checked at acceptance
(`generate-slot` skill → `--live` mode here), all through ONE pure law: `delegation.footprint_problems`.

Two-sided + fail-closed witness (default mode, wired into `meta check`):
  GREEN side  — the law returns [] on a clean synthetic fixture (in-slot + verdict + .gen + baseline paths).
  RED side    — a synthetic out-of-slot path MUST be flagged; a silent law is decorative → FAIL.
  FAIL-CLOSED — the REAL hook transports (`.claude/hooks/{blast_radius,verdict_required}.py`), run against a
                synthetic root whose manifest is PRESENT but whose law is BROKEN, must exit 2 (the pre-INC-1
                behavior was fail-OPEN, exit 0); with the manifest ABSENT they must stay inert (exit 0).

`--live` mode (the generate-slot acceptance step, belt over suspenders — catches a generator killed
mid-flight before its SubagentStop fired): checks the REAL active slot (if any) against the REAL
`git status` footprint; violations → exit 1 naming the offending paths; no active slot → inert OK.

Argv: <root> [--live]. Exit 0 = PASS, 1 = FAIL.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ... import delegation

_HOOKS = (".claude/hooks/blast_radius.py", ".claude/hooks/verdict_required.py")


def _changed_paths(root: Path) -> list[str] | None:
    """Root-relative changed paths (staged+unstaged+untracked, both rename sides). Duplicated from the
    `verdict_required` transport ON PURPOSE: the hook is clone-robust (zero `metafactory.*`) so it cannot
    share this collector; both feed the SAME pure law. None → git undecidable (caller fails closed)."""
    try:
        st = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", "."],
                            cwd=root, capture_output=True, text=True, timeout=60)
        pre = subprocess.run(["git", "rev-parse", "--show-prefix"],
                             cwd=root, capture_output=True, text=True, timeout=60)
    except Exception:
        return None
    if st.returncode != 0 or pre.returncode != 0:
        return None
    prefix = pre.stdout.strip()
    out: list[str] = []
    for line in st.stdout.splitlines():
        if len(line) < 4:
            continue
        for part in line[3:].split(" -> "):
            p = part.strip().strip('"')
            if prefix and p.startswith(prefix):
                p = p[len(prefix):]
            if p:
                out.append(p)
    return out


def synthetic_two_sided() -> tuple[bool, str]:
    """GREEN: a clean fixture passes. RED: an out-of-slot path MUST be flagged (else decorative)."""
    slot = {"slot_id": "synthetic", "allow_globs": ["src/pkg/*.py"],
            "verdict_path": ".gen/synthetic.verdict.json", "baseline_dirty": ["docs/notes.md"]}
    green = delegation.footprint_problems(
        slot, ["src/pkg/target.py", ".gen/synthetic.verdict.json", ".gen/scratch/x.txt", "docs/notes.md"])
    if green:
        return False, f"GREEN side broken: clean fixture flagged {green}"
    red = delegation.footprint_problems(slot, ["seed/verifier.py", "src/pkg/ok.py"])
    if not (len(red) == 1 and "seed/verifier.py" in red[0]):
        return False, f"RED side decorative: out-of-slot path not (exactly) flagged → {red}"
    return True, "law two-sided (clean fixture → [] · out-of-slot path → flagged)"


def _run_hook(hook: Path, payload: dict) -> int:
    r = subprocess.run([sys.executable, str(hook)], input=json.dumps(payload),
                       text=True, capture_output=True, timeout=120)
    return r.returncode


def transports_fail_closed(root: Path) -> tuple[bool, str]:
    """The REAL hooks, on a synthetic root: manifest PRESENT + law BROKEN → both exit 2 (fail closed);
    manifest ABSENT → both exit 0 (inert). Hooks resolve their root by script location (parents[2]),
    so copying them into <tmp>/.claude/hooks/ points them at the synthetic root."""
    payloads = {"blast_radius.py": {"tool_name": "Write", "tool_input": {"file_path": "anything.py"}},
                "verdict_required.py": {}}
    with tempfile.TemporaryDirectory(prefix="slot_footprint_") as td:
        tmp = Path(td)
        hooks_dir = tmp / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True)
        for rel in _HOOKS:
            src = root / rel
            if not src.exists():
                return False, f"missing transport {rel} (nothing to witness)"
            shutil.copy2(src, hooks_dir / src.name)
        (tmp / "seed").mkdir()
        (tmp / "seed" / "delegation.py").write_text("def broken(:\n", encoding="utf-8")  # unloadable law
        (tmp / ".gen").mkdir()
        manifest = tmp / ".gen" / "active_slot.json"
        manifest.write_text('{"slot_id": "witness", "allow_globs": ["x"]}', encoding="utf-8")
        for name, payload in payloads.items():
            rc = _run_hook(hooks_dir / name, payload)
            if rc != 2:
                return False, f"{name}: manifest present + broken law → exit {rc}, expected 2 (FAIL-OPEN!)"
        manifest.unlink()
        for name, payload in payloads.items():
            rc = _run_hook(hooks_dir / name, payload)
            if rc != 0:
                return False, f"{name}: no manifest → exit {rc}, expected 0 (inert)"
    return True, "hooks fail CLOSED with a broken law (exit 2) and stay inert without a manifest (exit 0)"


def live(root: Path) -> int:
    """Acceptance-time re-check of the REAL active slot against the REAL git footprint."""
    if not delegation.manifest_path(root).exists():
        print("OK slot_footprint --live: no active slot (inert)")
        return 0
    slot = delegation.load_slot(root)
    if slot is None:
        print("SLOT_FOOTPRINT RED — .gen/active_slot.json exists but is not a valid manifest (fail closed)")
        return 1
    changed = _changed_paths(root)
    if changed is None:
        print("SLOT_FOOTPRINT RED — `git status` undecidable; cannot prove the footprint (fail closed)")
        return 1
    problems = delegation.footprint_problems(slot, changed)
    if problems:
        print(f"SLOT_FOOTPRINT RED — slot `{slot.get('slot_id', '?')}` has out-of-slot changes:")
        for p in problems[:20]:
            print(f"  ✗ {p}")
        return 1
    print(f"OK slot_footprint --live: slot `{slot.get('slot_id', '?')}` footprint ⊆ contract "
          f"({len(changed)} changed path(s) observed)")
    return 0


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve() if argv else Path.cwd()
    if "--live" in argv:
        return live(root)
    ok_law, law_note = synthetic_two_sided()
    if not ok_law:
        print(f"SLOT_FOOTPRINT RED — {law_note}")
        return 1
    ok_tr, tr_note = transports_fail_closed(root)
    if not ok_tr:
        print(f"SLOT_FOOTPRINT RED — {tr_note}")
        return 1
    print(f"OK slot_footprint: {law_note}; {tr_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
