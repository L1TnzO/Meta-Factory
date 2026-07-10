"""codegen_freeze — deterministic shadow of the template-codegen FREEZE (ADR-023 §3; I-12).

ADR-023 §3 froze the template codegen (`factories/*/codegen/**`): "feeding it again = a deliberate
act with a WRITTEN waiver". That prohibition was PROSE — and it was already pierced twice with no
waiver (`FSK-COVERAGE-FULL[-100]`, commits 5b96696 · 43f295d). This check is the missing shadow:

  GREEN side — for every factory with a `codegen/` dir, the LIVE diff window (working tree + commits
               since the owning level's open work-doc was added) touching `factories/<f>/codegen/**`
               must be covered by a WAIVER declared in that open work-doc; a waiver with NO diff is
               decorative → also red. A HISTORICAL audit closes the "increment closed before
               `meta check` ever ran" escape: every commit after this file's own add-commit (the
               epoch — everything earlier is grandfathered, already legislated in HONEST-STATE §7)
               that touches a frozen path must carry, in its OWN tree, an ABIERTO work-doc of the
               owning factory with a valid waiver.
  RED side   — three synthetic scenarios prove the law itself bites (diff-without-waiver MUST flag,
               waiver-without-diff MUST flag, diff+valid-waiver MUST pass); if the detector goes
               soft the check FAILS (two-sided, anti-decorative).

THE BOUNDARY, legislated (closes the 2026-07-10 gray zone, HONEST-STATE §7). The waiver is ONE line
in the open work-doc of the owning level (`factories/<f>/docs/work/*-INCREMENT.md`):

    Codegen-freeze-waiver: alcance=<verificacion|superficie> · motivo: <por qué> · cita: ADR-NNN

  - alcance=verificacion — the diff feeds the EMITTED VERIFICATION (proofs/tests/coverage wiring:
    the verification profile, the part ADR-023 §1 keeps ALIVE). Cita `ADR-023` (§1) suffices.
  - alcance=superficie   — the diff evolves the emitted HUMAN SURFACE / templates (the part
    ADR-023 §3 froze). Cita: a dedicated ADR (the deliberate act).
The check verifies the FORM (alcance+motivo+cita) deterministically; the honesty of the declared
`alcance` is judged by eyes at review — the irreducible residue, like every gate here. Declare the
waiver IN THE SAME tree state that introduces the diff (waiver-sin-diff = red; diff-sin-waiver = red).

Escape hatch, `registry.KINDS`-style: an irreparable historical red is legislated by adding the sha
to `WAIVED_COMMITS` (a governance act with eyes + written reason), never by weakening the gate.
Zero model; re-derived from git + docs (I-3); names no tech/domain (ADR-012).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# sha -> written reason. Editing this constant is a DELIBERATE governance act (like registry.KINDS):
# it grandfathers a specific historical commit that cannot carry an in-tree waiver anymore.
WAIVED_COMMITS: dict[str, str] = {}

_SELF_REL = "src/metafactory/verify/checks/codegen_freeze.py"
_WAIVER_TOKEN = "codegen-freeze-waiver"
_OPEN_RE = re.compile(r"Estado:\s*\*\*ABIERTO\*\*")          # mirror of seed/lifecycle.py's law
_ALCANCE_RE = re.compile(r"alcance\s*=\s*(verificacion|superficie)\b", re.IGNORECASE)
_MOTIVO_RE = re.compile(r"motivo\s*:\s*\S", re.IGNORECASE)
_CITA_RE = re.compile(r"cita\s*:.*?ADR-\d{3}", re.IGNORECASE)


def _git(root: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True).stdout
    except OSError:
        return ""


# ── the pure LAW (unit-tested + exercised by the RED side) ───────────────────
def parse_waivers(text: str) -> tuple[int, list[str]]:
    """(count of WELL-FORMED waiver lines, problems for malformed ones). A line that names the
    token but lacks alcance/motivo/cita is a malformed waiver — flagged, never silently ignored."""
    valid, problems = 0, []
    for ln in text.splitlines():
        if _WAIVER_TOKEN not in ln.lower():
            continue
        missing = [label for label, rx in
                   (("alcance=<verificacion|superficie>", _ALCANCE_RE),
                    ("motivo:", _MOTIVO_RE), ("cita: ADR-NNN", _CITA_RE))
                   if not rx.search(ln)]
        if missing:
            problems.append(f"waiver MALFORMADO (falta {', '.join(missing)}): {ln.strip()[:120]}")
        else:
            valid += 1
    return valid, problems


def evaluate(diff_paths: list[str], workdoc_name: str | None, workdoc_text: str | None) -> list[str]:
    """The freeze law over one factory's live window. Pure: no git, no IO."""
    valid, problems = parse_waivers(workdoc_text or "")
    if problems:
        return problems
    if diff_paths and workdoc_text is None:
        return [f"codegen tocado SIN incremento abierto en el nivel dueño: {', '.join(diff_paths[:5])}"]
    if diff_paths and not valid:
        return [f"diff en codegen congelado SIN waiver en {workdoc_name} (ADR-023 §3): "
                f"{', '.join(diff_paths[:5])}" + (f" (+{len(diff_paths) - 5})" if len(diff_paths) > 5 else "")]
    if not diff_paths and valid:
        return [f"waiver SIN diff en {workdoc_name} — decorativo/preautorización: declaralo en el "
                f"mismo estado de árbol que introduce el diff"]
    return []


# ── the live window (git-derived) ────────────────────────────────────────────
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
    """Does the commit's OWN tree hold an ABIERTO work-doc of `factory` with a valid waiver?"""
    workdir = f"factories/{factory}/docs/work"
    for path in _git(root, "ls-tree", "-r", "--name-only", commit, workdir).splitlines():
        if not path.endswith(".md"):
            continue
        text = _git(root, "show", f"{commit}:{path}")
        if _OPEN_RE.search(text) and parse_waivers(text)[0]:
            return True
    return False


def _audit_history(root: Path, factories: list[str]) -> tuple[list[str], str]:
    """Every post-epoch commit touching a frozen path must carry an in-tree open waiver."""
    epoch = _git(root, "log", "--diff-filter=A", "-1", "--format=%H", "--", _SELF_REL).strip()
    if not epoch:
        return [], "auditoría histórica N/A (diente aún sin committear — epoch auto-referencial)"
    problems, audited = [], 0
    for f in factories:
        shas = [s for s in _git(root, "log", "--format=%H", f"{epoch}..HEAD",
                                "--", f"factories/{f}/codegen").splitlines() if s.strip()]
        for sha in shas:
            if sha in WAIVED_COMMITS:
                continue
            audited += 1
            if not _tree_has_waiver(root, sha, f):
                problems.append(f"{f}: commit {sha[:9]} alimentó codegen/ SIN waiver ABIERTO en su árbol "
                                f"(post-freeze; legislá en WAIVED_COMMITS sólo como acto de gobierno)")
    return problems, f"auditoría histórica: {audited} commit(s) post-epoch {epoch[:9]} auditado(s)"


# ── RED side: the law itself must bite (anti-decorative) ─────────────────────
_SYN_DIFF = ["factories/x/codegen/emit.py"]
_SYN_WAIVER = ("Codegen-freeze-waiver: alcance=verificacion · motivo: escenario sintético del diente · "
               "cita: ADR-023 §1")


def _tooth_alive() -> list[str]:
    dead = []
    if not evaluate(_SYN_DIFF, "X-INCREMENT.md", "# doc sin waiver"):
        dead.append("diff-sin-waiver NO se marcó")
    if not evaluate([], "X-INCREMENT.md", _SYN_WAIVER):
        dead.append("waiver-sin-diff NO se marcó")
    if evaluate(_SYN_DIFF, "X-INCREMENT.md", _SYN_WAIVER):
        dead.append("diff+waiver-válido NO pasó (bloquearía todo waiver legítimo)")
    return dead


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve() if argv else Path.cwd()
    from ..._seed import load_seed_lifecycle
    lifecycle = load_seed_lifecycle()

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
        report.append(f"  {f:<24} diff vivo: {len(diff)} · incremento: {inc or '—'}")

    hist_problems, hist_note = _audit_history(root, factories)
    problems += hist_problems

    if problems:
        print("CODEGEN_FREEZE ROJO — el codegen congelado (ADR-023 §3) se alimentó sin waiver declarado:")
        for p in problems:
            print(f"  ✗ {p}")
        print(f"  ley: línea `Codegen-freeze-waiver: alcance=<verificacion|superficie> · motivo: … · "
              f"cita: ADR-NNN` en el work-doc ABIERTO del nivel dueño")
        return 1

    dead = _tooth_alive()
    if dead:
        print("CODEGEN_FREEZE DECORATIVO — la ley no muerde en escenarios sintéticos:")
        for d in dead:
            print(f"  ✗ {d}")
        return 1

    print(f"OK codegen_freeze: {len(factories)} fábrica(s) con codegen/ congelado (ADR-023 §3) sin "
          f"alimentación no-waivereada; {hist_note}; diente RED vivo (3 escenarios sintéticos)")
    for line in report:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
