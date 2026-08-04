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
#
# THE HATCH IS ITSELF AUDITED (`evaluate_waivers`, red-side-exercised). Before V3-EXTRACT-STEP0 this
# constant was the one un-toothed surface in the module: any key with any value silently suppressed a
# red, and — measured, not supposed — an ABBREVIATED key was a silent NO-OP, because `_audit_history`
# matches the full 40-char `%H`. The first use of an escape hatch is exactly when it must start being
# audited, so keys are now RESOLVED through git (abbreviations work) and every row must prove it names
# a real, post-epoch commit that actually fed a frozen path, with a written reason.
WAIVED_COMMITS: dict[str, str] = {
    "ba05918d203f9ef7f4021c7320cb62c04673e714":
        "FSK 2026-07-13 `fix(FSK-CODEGEN): escape quotes/backslashes/newlines in jsonVal`. ONE file "
        "(codegen/scaffold/data_layer.py), ONE line: jsonVal wrapped strings in quotes with zero "
        "escaping, so any field holding a raw quote/backslash/newline emitted INVALID JSON on every "
        "list/detail read of every entity of every product this codegen builds. It is a CORRECTNESS "
        "repair of already-frozen emission — it evolves no human surface (ADR-023 §3 alcance="
        "superficie) and wires no new verification (§1 alcance=verificacion), so the two-value "
        "alcance vocabulary has no honest slot for it and forcing one would demand a dedicated ADR "
        "for a quote-escaping bug. Waived here with eyes, three weeks after the fact, because the "
        "commit is already in history and cannot grow an in-tree waiver anymore. Cita: ADR-023 §3.",
}

#: A reason must be a written SENTENCE, not a token. Below this, a row is treated as unreasoned —
#: the same law the in-tree waiver applies with `motivo:` (`_MOTIVO_RE`), expressed as a length.
_MIN_REASON_CHARS = 40

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


def evaluate_waivers(facts: list[tuple[str, str, str | None, bool, bool]]) -> list[str]:
    """The law over the ESCAPE HATCH itself. Pure: no git, no IO — so the red side can exercise it.

    Each fact is (key, reason, resolved_sha_or_None, touches_frozen, post_epoch). A row earns its
    suppression only by proving all four: it resolves to a real commit, that commit actually fed a
    frozen path, it is post-epoch (pre-epoch is already grandfathered, so waiving it is decorative —
    the same shape as this module's `waiver with NO diff`), and it carries a written reason.
    """
    problems = []
    for key, reason, resolved, touches_frozen, post_epoch in facts:
        if resolved is None:
            problems.append(f"WAIVED_COMMITS[{key}] does not resolve to a commit in this clone — a "
                            f"waiver that names nothing suppresses nothing (and an abbreviated key "
                            f"that cannot be resolved would be a SILENT no-op)")
            continue
        if len(reason.strip()) < _MIN_REASON_CHARS:
            problems.append(f"WAIVED_COMMITS[{key}] has no written reason ({len(reason.strip())} "
                            f"chars < {_MIN_REASON_CHARS}): a governance act records WHY, or it is "
                            f"just a suppressed red")
        if not post_epoch:
            problems.append(f"WAIVED_COMMITS[{key}] is PRE-epoch — already grandfathered, so the "
                            f"row suppresses nothing and reads as if it did (decorative)")
        elif not touches_frozen:
            problems.append(f"WAIVED_COMMITS[{key}] names a commit that never fed "
                            f"factories/*/codegen/** — decorative waiver")
    return problems


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


def _resolve(root: Path, rev: str) -> str | None:
    """Full 40-char sha for `rev`, or None if this clone cannot resolve it to a commit."""
    sha = _git(root, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}").strip()
    return sha or None


def _waiver_facts(root: Path, epoch: str) -> tuple[dict[str, str], list[str]]:
    """(resolved sha -> key, problems). Resolves every hatch row and audits it (`evaluate_waivers`)."""
    facts, resolved_map = [], {}
    for key, reason in WAIVED_COMMITS.items():
        sha = _resolve(root, key)
        touches, post = False, False
        if sha:
            resolved_map[sha] = key
            touches = any(ln.startswith("factories/") and "/codegen/" in ln
                          for ln in _git(root, "show", "--name-only", "--format=", sha).splitlines())
            post = subprocess.run(["git", "merge-base", "--is-ancestor", epoch, sha],
                                  cwd=root, capture_output=True).returncode == 0
        facts.append((key, reason, sha, touches, post))
    return resolved_map, evaluate_waivers(facts)


def _audit_history(root: Path, factories: list[str]) -> tuple[list[str], str]:
    """Every post-epoch commit touching a frozen path must carry an in-tree open waiver."""
    epoch = FREEZE_EPOCH if _git(root, "cat-file", "-t", FREEZE_EPOCH).strip() == "commit" else ""
    if not epoch:
        # N-0122: a shallow clone cannot audit history it does not have. Say what went UNMEASURED —
        # an un-audited hatch row must never read as an audited-and-clean one (not measured != zero).
        return [], (f"historical audit N/A (pinned epoch {FREEZE_EPOCH[:9]} not in this clone — "
                    f"a shallow clone cannot audit history it does not have); "
                    f"{len(WAIVED_COMMITS)} WAIVED_COMMITS row(s) also UNAUDITED here")
    waived, problems = _waiver_facts(root, epoch)
    audited, suppressed = 0, 0
    for f in factories:
        shas = [s for s in _git(root, "log", "--format=%H", f"{epoch}..HEAD",
                                "--", f"factories/{f}/codegen").splitlines() if s.strip()]
        for sha in shas:
            if sha in waived:
                suppressed += 1
                continue
            audited += 1
            if not _tree_has_waiver(root, sha, f):
                problems.append(f"{f}: commit {sha[:9]} fed codegen/ with NO open waiver in its own "
                                f"tree (post-freeze; legislate in WAIVED_COMMITS only as a governance act)")
    return problems, (f"historical audit: {audited} post-epoch {epoch[:9]} commit(s) audited, "
                      f"{suppressed} suppressed by {len(WAIVED_COMMITS)} audited WAIVED_COMMITS row(s)")


def population_problems(factories: list[str]) -> list[str]:
    """LOCK #1 — an EMPTY population is RED, never a vacuous green.

    Measured 2026-08-04 (V3-EXTRACT-RETIREMENT §5): with no `factories/*/codegen/` in the tree this
    gate's loop never ran, `_audit_history` was handed nothing, and it exited 0 printing "0 factory/ies
    with frozen codegen/". Every other census in this repo carries this lock — `migration_census` and
    `verb_census` each refuse an empty population by name — and this one did not, which mattered
    exactly nowhere HERE (the subject is non-empty, so the green is earned) and mattered a great deal
    THERE: `factories/` travels with the extraction package, and this is the one ancestor-independent
    gate that keeps its teeth on the other side. A gate whose green means "I found nothing to check"
    is indistinguishable from one that means "I checked and it was clean" — and the second is what
    anybody reading the verdict will assume."""
    if not factories:
        return ["no factory with a frozen `codegen/` was found — this gate would be passing by never "
                "being asked anything (LOCK #1). Either the population moved, or the tree this ran "
                "against is not the one that owns the frozen codegen"]
    return []


def _real_report(root: Path) -> tuple[list[str], list[str]]:
    """The GREEN side over the real repo. Returns (problems, human-readable report lines)."""
    lifecycle = _load_lifecycle()
    factories = sorted(p.parent.name for p in root.glob("factories/*/codegen") if p.is_dir())
    if lock := population_problems(factories):
        return lock, ["0 factory/ies with frozen codegen/ — refused as vacuous (LOCK #1)"]
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


_SYN_SHA = "0" * 40
_SYN_REASON = "synthetic tooth scenario: a written reason long enough to be a sentence, not a token"


def _tooth_alive() -> tuple[list[str], int]:
    """(dead scenarios, scenarios run). The hatch scenarios were added by V3-EXTRACT-STEP0: the moment
    WAIVED_COMMITS stopped being empty is the moment its law had to start biting."""
    dead, scenarios = [], 0

    for name, condition in (
        # the in-tree waiver law (unchanged since v2)
        ("diff-without-waiver was NOT flagged",
         not evaluate(_SYN_DIFF, "X-INCREMENT.md", "# doc without a waiver")),
        ("waiver-without-diff was NOT flagged",
         not evaluate([], "X-INCREMENT.md", _SYN_WAIVER)),
        ("diff+valid-waiver did NOT pass (would block every legitimate waiver)",
         bool(evaluate(_SYN_DIFF, "X-INCREMENT.md", _SYN_WAIVER))),
        # the ESCAPE HATCH law
        ("hatch: unresolvable key was NOT flagged (an abbreviation that git cannot resolve would be "
         "a silent no-op)",
         not evaluate_waivers([("deadbeef", _SYN_REASON, None, True, True)])),
        ("hatch: row with no written reason was NOT flagged",
         not evaluate_waivers([(_SYN_SHA, "ok", _SYN_SHA, True, True)])),
        ("hatch: row naming a commit that never fed codegen/ was NOT flagged",
         not evaluate_waivers([(_SYN_SHA, _SYN_REASON, _SYN_SHA, False, True)])),
        ("hatch: PRE-epoch (already grandfathered) row was NOT flagged",
         not evaluate_waivers([(_SYN_SHA, _SYN_REASON, _SYN_SHA, True, False)])),
        ("hatch: a fully-justified row did NOT pass (would block every legitimate governance act)",
         bool(evaluate_waivers([(_SYN_SHA, _SYN_REASON, _SYN_SHA, True, True)]))),
        # LOCK #1 — the empty population must be refused, not celebrated
        ("lock1: an EMPTY factory population was NOT flagged — the gate would pass by never being "
         "asked anything",
         not population_problems([])),
        ("lock1: a NON-empty population was flagged (would redden every honest tree)",
         bool(population_problems(["full-stack-kotlin"]))),
    ):
        scenarios += 1
        if condition:
            dead.append(name)
    return dead, scenarios


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-codegen-freeze", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        dead, scenarios = _tooth_alive()
        if dead:
            return Verdict("v3-codegen-freeze (SABOTAGE)", 1,
                           f"GATE DECORATIVO: the law does not bite in {len(dead)}/{scenarios} "
                           f"synthetic scenario(s)", failures=tuple(dead)).emit()
        return Verdict("v3-codegen-freeze (SABOTAGE)", 0,
                       f"all {scenarios} synthetic scenarios (in-tree waiver law + the "
                       f"WAIVED_COMMITS escape hatch + LOCK #1) resolved as the law requires",
                       counts={"scenarios": scenarios}).emit()

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
