#!/usr/bin/env python3
"""codegen_freeze — deterministic shadow of the template-codegen FREEZE (ADR-023 §3; I-12), PORTED
from v2's `verify/checks/codegen_freeze.py`. Subject UNCHANGED (factories' own `codegen/` dirs and
their owning level's work-docs — never the platform), because the freeze this gate enforces has
always been about the factories, not about v2's or v3's own substrate.

    python3 -m v3.verify.checks.codegen_freeze
    V3_CODEGEN_FREEZE_SABOTAGE=1 python3 -m v3.verify.checks.codegen_freeze   # red side; ALSO exit 0

ADR-023 §3 froze the template codegen (`factories/*/codegen/**`): "feeding it again = a deliberate
act with a WRITTEN waiver". GREEN side — for every factory with a `codegen/` dir, the LIVE diff
window (working tree + commits since the owning level's open work-doc was added) touching
`factories/<f>/codegen/**` must be covered by a WAIVER declared in that open work-doc; a waiver with
NO diff is decorative -> also red. A HISTORICAL audit closes the "increment closed before the gate
ever ran" escape: every commit after THIS module's own add-commit (the epoch — everything earlier is
grandfathered) that touches a frozen path must carry, in its OWN tree, an open work-doc of the
owning factory with a valid waiver.

THE BOUNDARY (verbatim from v2, unchanged — this is DATA the check enforces, not v2 code): a waiver
is ONE line in the open work-doc of the owning level:

    Codegen-freeze-waiver: alcance=<verificacion|superficie> · motivo: <por que> · cita: ADR-NNN

  - alcance=verificacion — the diff feeds the EMITTED VERIFICATION (proofs/tests/coverage wiring:
    the part ADR-023 §1 keeps ALIVE). Cita `ADR-023` (§1) suffices.
  - alcance=superficie   — the diff evolves the emitted HUMAN SURFACE / templates (the part ADR-023
    §3 froze). Cita: a dedicated ADR (the deliberate act).

WHY THE WITNESS MOVED SHAPE (recorded, not silently changed — same reasoning as
`v3.verify.checks.pbt`'s docstring). v2 ran its 3 synthetic law-scenarios unconditionally, INSIDE
every green invocation, and reported "GATE DECORATIVO" if any came back soft. Under this registry a
witness that is asserted every run without a second process is a `fixture`/`pinned_data` shape
(`Witness.is_embedded`); this witness is registered as `sabotage_env` instead (`V3_CODEGEN_FREEZE_SABOTAGE`)
— the law-scenarios run ONLY under the sabotage flag, and the ordinary green run only checks the REAL
repo. `v3.verify.checks.suite_sweep` re-runs the sabotage side separately, exactly as it does for `pbt`.

WHERE `open_increment_in` COMES FROM: `seed/lifecycle.py` is loaded directly (`importlib`, no
package import) — it is part of the frozen Stage-0 seed, not v2's platform package, so this carries
no `v3.verify.import_boundary` exemption and needs none (same status as `v3.verify.kinds`'s own
"structural analogue, not an import" note about `_seed.repo_root()`).

Escape hatch, `registry.KINDS`-style: an irreparable historical red is legislated by adding the sha
to `WAIVED_COMMITS` (a governance act with eyes + written reason), never by weakening the gate.
Zero model; re-derived from git + docs (I-3); names no tech/domain (ADR-012).
"""
from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SELF_REL = "v3/verify/checks/codegen_freeze.py"
_SABOTAGE_VAR = "V3_CODEGEN_FREEZE_SABOTAGE"

# sha -> written reason. Editing this constant is a DELIBERATE governance act (like `registry.KINDS`):
# it grandfathers a specific historical commit that cannot carry an in-tree waiver anymore.
WAIVED_COMMITS: dict[str, str] = {}

_WAIVER_TOKEN = "codegen-freeze-waiver"
_OPEN_RE = re.compile(r"(?:Estado|Status):\s*\*\*(?:ABIERTO|OPEN)\*\*")
_ALCANCE_RE = re.compile(r"alcance\s*=\s*(verificacion|superficie)\b", re.IGNORECASE)
_MOTIVO_RE = re.compile(r"motivo\s*:\s*\S", re.IGNORECASE)
_CITA_RE = re.compile(r"cita\s*:.*?ADR-\d{3}", re.IGNORECASE)


def _load_lifecycle() -> ModuleType:
    """Load `seed/lifecycle.py` by path — frozen Stage-0 seed, not v2's platform package."""
    path = _ROOT / "seed" / "lifecycle.py"
    spec = importlib.util.spec_from_file_location("seed_lifecycle_for_codegen_freeze", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git(root: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True).stdout
    except OSError:
        return ""


# -- the pure LAW (unit-exercised by the RED side) ---------------------------------------------------
def parse_waivers(text: str) -> tuple[int, list[str]]:
    """(count of WELL-FORMED waiver lines, problems for malformed ones). A line that names the token
    but lacks alcance/motivo/cita is a malformed waiver — flagged, never silently ignored."""
    valid, problems = 0, []
    for ln in text.splitlines():
        if _WAIVER_TOKEN not in ln.lower():
            continue
        missing = [label for label, rx in
                   (("alcance=<verificacion|superficie>", _ALCANCE_RE),
                    ("motivo:", _MOTIVO_RE), ("cita: ADR-NNN", _CITA_RE))
                   if not rx.search(ln)]
        if missing:
            problems.append(f"malformed waiver (missing {', '.join(missing)}): {ln.strip()[:120]}")
        else:
            valid += 1
    return valid, problems


def evaluate(diff_paths: list[str], workdoc_name: str | None, workdoc_text: str | None) -> list[str]:
    """The freeze law over one factory's live window. Pure: no git, no IO."""
    valid, problems = parse_waivers(workdoc_text or "")
    if problems:
        return problems
    if diff_paths and workdoc_text is None:
        return [f"codegen touched with NO open increment at the owning level: {', '.join(diff_paths[:5])}"]
    if diff_paths and not valid:
        return [f"diff in frozen codegen with NO waiver in {workdoc_name} (ADR-023 §3): "
                f"{', '.join(diff_paths[:5])}" + (f" (+{len(diff_paths) - 5})" if len(diff_paths) > 5 else "")]
    if not diff_paths and valid:
        return [f"waiver with NO diff in {workdoc_name} — decorative/pre-authorization: declare it in "
                f"the SAME tree state that introduces the diff"]
    return []


# -- the live window (git-derived) -------------------------------------------------------------------
def _workdoc_base(root: Path, workdoc_rel: str | None) -> str:
    """Commit that ADDED the open work-doc (the increment's opening baseline), else HEAD."""
    if workdoc_rel:
        sha = _git(root, "log", "--diff-filter=A", "-1", "--format=%H", "--", workdoc_rel).strip()
        if sha:
            return sha
    return "HEAD"


def _live_diff(root: Path, scope: str, base: str) -> list[str]:
    """Paths under `scope` that differ between the base TREE and the working tree (+ untracked)."""
    paths = {p for p in _git(root, "diff", "--name-only", base, "--", scope).splitlines() if p.strip()}
    for ln in _git(root, "status", "--porcelain", "--untracked-files=all", "--", scope).splitlines():
        if ln.startswith("??"):
            paths.add(ln[3:].strip().strip('"'))
    return sorted(paths)


def _tree_has_waiver(root: Path, commit: str, factory: str) -> bool:
    """Does the commit's OWN tree hold an open work-doc of `factory` with a valid waiver?"""
    workdir = f"factories/{factory}/docs/work"
    for path in _git(root, "ls-tree", "-r", "--name-only", commit, workdir).splitlines():
        if not path.endswith(".md"):
            continue
        text = _git(root, "show", f"{commit}:{path}")
        if _OPEN_RE.search(text) and parse_waivers(text)[0]:
            return True
    return False


#: When the freeze came into force — a property of the LAW (ADR-023 §3), not of the file that
#: happens to implement it. v2 derived this from its own module's add-commit, and porting the
#: implementation therefore MOVED the start date: a fresh file has a fresh epoch, so every commit
#: the gate had already caught becomes grandfathered the moment someone re-implements it. Measured
#: here: v2 reports 2 problems on this tree, the port reported 1, and the missing one was a real
#: commit that fed `codegen/` with no open waiver. Porting a gate must never launder its history,
#: so the epoch is pinned as DATA and moving it is a visible edit with a reason.
FREEZE_EPOCH = "4bd9835c5e5099b16eec7f8e16ab78ee2194f7d8"   # 2026-07-10, CODEGEN-FREEZE-TOOTH


def _audit_history(root: Path, factories: list[str]) -> tuple[list[str], str]:
    """Every post-epoch commit touching a frozen path must carry an in-tree open waiver."""
    epoch = FREEZE_EPOCH if _git(root, "cat-file", "-t", FREEZE_EPOCH).strip() == "commit" else ""
    if not epoch:
        return [], (f"historical audit N/A (pinned epoch {FREEZE_EPOCH[:9]} not in this clone — "
                    f"a shallow clone cannot audit history it does not have)")
    problems, audited = [], 0
    for f in factories:
        shas = [s for s in _git(root, "log", "--format=%H", f"{epoch}..HEAD",
                                "--", f"factories/{f}/codegen").splitlines() if s.strip()]
        for sha in shas:
            if sha in WAIVED_COMMITS:
                continue
            audited += 1
            if not _tree_has_waiver(root, sha, f):
                problems.append(f"{f}: commit {sha[:9]} fed codegen/ with NO open waiver in its own "
                                f"tree (post-freeze; legislate in WAIVED_COMMITS only as a governance act)")
    return problems, f"historical audit: {audited} post-epoch {epoch[:9]} commit(s) audited"


def _real_report(root: Path) -> tuple[list[str], list[str]]:
    """The GREEN side over the real repo. Returns (problems, human-readable report lines)."""
    lifecycle = _load_lifecycle()
    factories = sorted(p.parent.name for p in root.glob("factories/*/codegen") if p.is_dir())
    problems, report = [], []
    for f in factories:
        workdir = root / "factories" / f / "docs" / "work"
        inc = lifecycle.open_increment_in(workdir)
        workdoc_rel = f"factories/{f}/docs/work/{inc}" if inc else None
        text = (workdir / inc).read_text(encoding="utf-8") if inc else None
        diff = _live_diff(root, f"factories/{f}/codegen", _workdoc_base(root, workdoc_rel))
        probs = evaluate(diff, inc, text)
        problems += [f"{f}: {p}" for p in probs]
        report.append(f"{f}: live diff {len(diff)} · increment {inc or '(none)'}")

    hist_problems, hist_note = _audit_history(root, factories)
    problems += hist_problems
    report.append(hist_note)
    return problems, report


# -- RED side (sabotage_env): the law itself must bite (anti-decorative) -----------------------------
_SYN_DIFF = ["factories/x/codegen/emit.py"]
_SYN_WAIVER = ("Codegen-freeze-waiver: alcance=verificacion · motivo: synthetic tooth scenario · "
               "cita: ADR-023 §1")


def _tooth_alive() -> list[str]:
    dead = []
    if not evaluate(_SYN_DIFF, "X-INCREMENT.md", "# doc without a waiver"):
        dead.append("diff-without-waiver was NOT flagged")
    if not evaluate([], "X-INCREMENT.md", _SYN_WAIVER):
        dead.append("waiver-without-diff was NOT flagged")
    if evaluate(_SYN_DIFF, "X-INCREMENT.md", _SYN_WAIVER):
        dead.append("diff+valid-waiver did NOT pass (would block every legitimate waiver)")
    return dead


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-codegen-freeze", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        dead = _tooth_alive()
        if dead:
            return Verdict("v3-codegen-freeze (SABOTAGE)", 1,
                           f"GATE DECORATIVO: the law does not bite in {len(dead)} synthetic "
                           f"scenario(s)", failures=tuple(dead)).emit()
        return Verdict("v3-codegen-freeze (SABOTAGE)", 0,
                       "all 3 synthetic scenarios (diff-without-waiver, waiver-without-diff, "
                       "diff+valid-waiver) resolved as the law requires").emit()

    problems, report = _real_report(_ROOT)
    if problems:
        return Verdict("v3-codegen-freeze", 1,
                       f"frozen codegen (ADR-023 §3) fed without a declared waiver: {len(problems)} "
                       f"problem(s)", failures=tuple(problems),
                       next_action="declare `Codegen-freeze-waiver: alcance=<verificacion|superficie> "
                                   "· motivo: … · cita: ADR-NNN` in the owning level's open work-doc"
                       ).emit()

    nfact = len([ln for ln in report if not ln.startswith("historical audit")])
    return Verdict("v3-codegen-freeze", 0,
                   f"{nfact} factory/ies with frozen codegen/, none fed without a waiver; "
                   f"{report[-1]}", counts={"factories": nfact}).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
