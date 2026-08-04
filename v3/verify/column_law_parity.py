#!/usr/bin/env python3
"""column_law_parity — do the PORTED column-law bodies (`v3.control.cadence`, `v3.control.instrument`,
`v3.verify.hermetic`) decide the same way v2's did, at the pinned oracle commit?

    python3 -m v3.verify.column_law_parity                                    # the gate
    V3_COLUMN_LAW_PARITY_SABOTAGE=1 python3 -m v3.verify.column_law_parity   # the red side; must ALSO exit 0

WHY THIS ONE IS DIFFERENT FROM `eval_gate_parity`/`live_run_parity`. Those judge a CHECK BODY the
substrate spawns as its own subprocess — comparing EXIT CODES is the right instrument because that is
literally the interface the seed verifier observes. `cadence.debt/stop_block/edit_allowed/
required_workdir_rel`, `hermetic.preflight` and `instrument.target_of` are never spawned: they are
imported and their RETURN VALUES are branched on in-process by `.claude/hooks/*.py` (`gate_guard`,
`stop_proof`, `increment_guard`). So this module drives both sides through a tiny JSON-printing CLI
(`--drive <function> <json-args>`, itself embedded in this file's own `main`) and compares the printed
RESULT, not an exit code — the contract this slot was handed asks for exactly that. The KEY SPACE this
module pins is per FUNCTION×CASE (e.g. `edit_allowed:docs_md`), 37 entries across the 7 functions below
— never one entry per case-group, since seven functions run over five case groups.

PINNED, AND THE ORACLE HALF IS GONE (V3-EXTRACT-OBLIGATIONS phase 2). Phase 1 fossilised the oracle's 37
answers into the committed `v3/verify/pins/column_law_parity.json`, with the provenance proved WHILE the
ancestor still existed (see the increment doc's §Evidencia). This module never shells to `git`, and after
this phase it carries no code path that could any more: it loads the pin, checks its five laws
(`oracle_parity.pin_problems`), and compares v3's LIVE answers (`_live_answers`, driven the same
`--drive` way, over the real working tree) against it (`oracle_parity.compare_to_pin`). There is no
re-derivation flag left — a re-pin performed without the oracle would be exactly the undetectable
failure this increment exists to prevent. The accounting for the pin AS A SET (bijection with
`import_boundary._ORACLE_READERS`, provenance, the empty-population lock, and the travel probe that
proves no path back to the ancestor survives anywhere in this file) now lives in
`v3.verify.checks.pin_integrity`, not here — this module speaks only for its own 37 cases.

THE RELATIVE-IMPORT WRINKLE, SABOTAGE SIDE ONLY. `v3.control.cadence`/`v3.control.instrument`/
`v3.verify.hermetic` cannot be run as bare scripts (each opens with a package-relative import), so a
planted defect runs inside a SHADOW copy of the small `v3/` subtree those three depend on
(`_build_shadow_v3` below) rather than as a standalone file — a defect must be planted in a COPY, never
the real file.

WHAT THIS PROVES, AND WHAT IT DOES NOT. Result-equality over a matrix that demonstrably exercises
several DISTINCT oracle answers PER FUNCTION (LOCK below) is strong evidence the DECISION was
transcribed faithfully. LAW #3 (the slot contract): only the DECISION component of a tuple-shaped
answer is compared for `debt`/`stop_block`/`preflight` — the reason string is human-readable prose
`increment_guard`/`gate_guard`/`stop_proof` only ever print, and v2's `stop_block` reasons were Spanish
prose this port deliberately translated to English (LAW #3's own carve-out). `edit_allowed` (bool),
`required_workdir_rel` (str|None), `target_of` (str|None) and `is_subagent_spawn` (bool) are compared
whole — there is no prose component to discount. `target_of`'s ONE representation change is likewise
declared, not silent: v2 answered "no target" with `""`; this port's contract types it `str | None`, so
an oracle `""` is normalized to `None` before comparing (every known caller already does a truthy
check, so the two are behaviourally identical at every call site — see `v3/control/instrument.py`'s own
docstring).

LOCK: the PIN must hold at least `_MIN_DISTINCT_ANSWERS` distinct canonical decisions — the count
MEASURED at pin time — across its 37 answers; fewer would mean the comparison could pass by
coincidence. Enforced by `oracle_parity.pin_problems` (law 4), over the fossil rather than a live
oracle run.

SABOTAGE plants ONE defect per module, in a COPY of the ported body read off disk — never the real
file — and asserts its LIVE answers, run through that function's cases, no longer match the PIN:
  * `edit_allowed_invert` (cadence) — the delegation `return load_seed_lifecycle().edit_allowed(...)`
    becomes `return not load_seed_lifecycle().edit_allowed(...)`. This module's `edit_allowed` is a
    thin delegate to the shared seed law (never re-derived — see `v3/control/cadence.py`'s own
    docstring for why), so the plant inverts the WRAPPER's return, exactly the shape a stray `not`
    typo would take in a future edit.
  * `preflight_force_trust` (hermetic) — forces the FIRST line of `preflight` to
    `return "trust", "SABOTAGE: forced"`, unconditionally — "always return the trusting branch",
    per the slot contract.
  * `target_of_always_none` (instrument) — forces the first line of `target_of` to `return None`.
  * `pin_answer_corrupted` — an in-memory COPY of the pin gets ONE answer perturbed; `compare_to_pin`
    against v3's real (unpatched) live answers must report it.
  * `pin_case_dropped` — an in-memory COPY of the pin has ONE case's answer removed; `pin_problems` must
    report the bijection break.
A plant that finds nothing to perturb in the on-disk source raises `CannotPlant`, reported N/A beside
the caught/missed count, never folded into a catch (INC-5's law, INC-8's fix, re-used unchanged). The
sabotage side runs the PATCHED module inside a SHADOW copy of the small `v3/` subtree these three files
actually depend on (`control/{cadence,instrument}.py`, `memory/journal.py`, `economy/store.py`,
`seed_loader.py`, `verify/hermetic.py`, their `__init__.py`s) — copied from the WORKING TREE (never
git), exactly the "read off disk" convention every parity module in this package uses for the side
under test — plus a driver twin of this file's own `--drive` mode, since the patched copy has the same
relative-import wrinkle the real port does and cannot run as a bare script either. No oracle is built
for SABOTAGE any more: every plant's answers are compared against the committed pin.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import oracle_parity as harness
from ..kernel.report import Verdict

_V3 = harness.V3_DIR
_ROOT = harness.ROOT_DIR

#: the ported bodies this gate judges, and the files their source is read from for the sabotage plants.
_PORTED_CADENCE_PATH = _V3 / "control" / "cadence.py"
_PORTED_INSTRUMENT_PATH = _V3 / "control" / "instrument.py"
_PORTED_HERMETIC_PATH = _V3 / "verify" / "hermetic.py"

#: this gate's registered name — the pin file is `v3/verify/pins/<_PIN_GATE>.json`.
_PIN_GATE = "column_law_parity"

#: distinct canonical decisions the pin's 37 answers hold, MEASURED at pin time (V3-EXTRACT-OBLIGATIONS
#: §2.2 law 4) — fewer would mean the comparison could pass by coincidence.
_MIN_DISTINCT_ANSWERS = 13


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# THE DRIVER TEMPLATE — shared source for the SABOTAGE shadow's `_driver.py` (`_PORTED_DRIVER_SRC`
# below); there is no oracle side left to build any more (V3-EXTRACT-OBLIGATIONS phase 2)
# ══════════════════════════════════════════════════════════════════════════════════════════════════
_ORACLE_DRIVER_SRC = '''\
import json, sys
from pathlib import Path


def main(argv):
    which, args_json = argv[0], argv[1]
    args = json.loads(args_json)
    try:
        if which == "edit_allowed":
            from oraclepkg.memory import cadence
            result = cadence.edit_allowed(Path(args[0]), args[1])
        elif which == "required_workdir_rel":
            from oraclepkg.memory import cadence
            result = cadence.required_workdir_rel(Path(args[0]), args[1])
        elif which == "debt":
            from oraclepkg.memory import cadence
            result = list(cadence.debt(Path(args[0])))
        elif which == "stop_block":
            from oraclepkg.memory import cadence
            result = list(cadence.stop_block(Path(args[0])))
        elif which == "target_of":
            from oraclepkg.memory import instrument
            result = instrument.target_of(args[0], args[1])
        elif which == "is_subagent_spawn":
            from oraclepkg.memory import instrument
            result = instrument.is_subagent_spawn(args[0])
        elif which == "preflight":
            from oraclepkg.verify import hermetic
            ready = {"true": True, "false": False, "none": None}[args[1]]
            result = list(hermetic.preflight(Path(args[0]), ready=ready))
        else:
            print(json.dumps({"ok": False, "error": f"unknown case {which}"}))
            return 0
        print(json.dumps({"ok": True, "result": result}))
    except Exception as exc:  # the driver itself must never crash silently
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

# ══════════════════════════════════════════════════════════════════════════════════════════════════
# THE PORTED SIDE, NORMAL RUN: this file's own `--drive` mode, over the REAL working tree
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _drive(rest: list[str]) -> int:
    """`python3 -m v3.verify.column_law_parity --drive <function> <json-args>` — the tiny JSON-printing
    driver the slot contract asks for, embedded here so the NORMAL comparison needs no extra file (the
    sabotage side needs its own twin, `_PORTED_DRIVER_SRC` below, because a patched COPY cannot run as
    part of the real `v3` package)."""
    if len(rest) != 2:
        print(json.dumps({"ok": False, "error": f"--drive needs exactly 2 args, got {rest!r}"}))
        return 0
    which, args_json = rest
    try:
        args = json.loads(args_json)
        if which == "edit_allowed":
            from ..control import cadence
            result = cadence.edit_allowed(Path(args[0]), args[1])
        elif which == "required_workdir_rel":
            from ..control import cadence
            result = cadence.required_workdir_rel(Path(args[0]), args[1])
        elif which == "debt":
            from ..control import cadence
            result = list(cadence.debt(Path(args[0])))
        elif which == "stop_block":
            from ..control import cadence
            result = list(cadence.stop_block(Path(args[0])))
        elif which == "target_of":
            from ..control import instrument
            result = instrument.target_of(args[0], args[1])
        elif which == "is_subagent_spawn":
            from ..control import instrument
            result = instrument.is_subagent_spawn(args[0])
        elif which == "preflight":
            from . import hermetic
            ready = {"true": True, "false": False, "none": None}[args[1]]
            result = list(hermetic.preflight(Path(args[0]), ready=ready))
        else:
            print(json.dumps({"ok": False, "error": f"unknown case {which}"}))
            return 0
        print(json.dumps({"ok": True, "result": result}))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
    return 0


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# THE PORTED SIDE, SABOTAGE RUN: a shadow copy of the small subtree, one file patched
# ══════════════════════════════════════════════════════════════════════════════════════════════════
_PORTED_DRIVER_SRC = _ORACLE_DRIVER_SRC.replace("oraclepkg.memory", "v3.control") \
                                       .replace("oraclepkg.verify", "v3.verify")

#: relative path (under a shadow `v3/`) -> real file it is copied from, unless it is the ONE patched.
_SHADOW_FILES: dict[str, Path] = {
    "__init__.py": _V3 / "__init__.py",
    "seed_loader.py": _V3 / "seed_loader.py",
    "control/__init__.py": _V3 / "control" / "__init__.py",
    "control/cadence.py": _PORTED_CADENCE_PATH,
    "control/instrument.py": _PORTED_INSTRUMENT_PATH,
    "memory/__init__.py": _V3 / "memory" / "__init__.py",
    "memory/journal.py": _V3 / "memory" / "journal.py",
    "economy/__init__.py": _V3 / "economy" / "__init__.py",
    "economy/store.py": _V3 / "economy" / "store.py",
    "verify/__init__.py": _V3 / "verify" / "__init__.py",
    "verify/hermetic.py": _PORTED_HERMETIC_PATH,
}


def _build_shadow_v3(dest_root: Path, *, patched_rel: str, patched_src: str) -> Path:
    """A shadow copy of the subtree `cadence`/`instrument`/`hermetic` depend on, read off the WORKING
    TREE (never git — this is the sabotage convention, not an oracle read). `patched_rel`'s content is
    `patched_src` instead of a straight copy. Returns the `cwd` (the shadow's `v3/`'s PARENT) to run
    `-m v3.verify._driver` from."""
    root = dest_root / "v3"
    for rel, real_path in _SHADOW_FILES.items():
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = patched_src if rel == patched_rel else real_path.read_text(encoding="utf-8")
        dest.write_text(text, encoding="utf-8")
    (root / "verify" / "_driver.py").write_text(_PORTED_DRIVER_SRC, encoding="utf-8")
    return dest_root


def _plant_edit_allowed_invert(src: str) -> str:
    target = "    return load_seed_lifecycle().edit_allowed(Path(root), file_path)\n"
    if target not in src:
        raise harness.CannotPlant("edit_allowed's delegation return was not found in the ported "
                                  "body on disk")
    return src.replace(
        target, "    return not load_seed_lifecycle().edit_allowed(Path(root), file_path)\n", 1)


def _plant_preflight_force_trust(src: str) -> str:
    target = "    proof = _active_proof(Path(root))\n"
    if target not in src:
        raise harness.CannotPlant("preflight's proof lookup was not found in the ported body on disk")
    return src.replace(target, "    return \"trust\", \"SABOTAGE: forced\"\n" + target, 1)


def _plant_target_of_always_none(src: str) -> str:
    target = "    if not isinstance(tool_input, dict):\n"
    if target not in src:
        raise harness.CannotPlant("target_of's dict guard was not found in the ported body on disk")
    return src.replace(target, "    return None  # SABOTAGE: forced\n" + target, 1)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# THE MATRIX: fixture builders per function group
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _write_increment_doc(workdir: Path, *, status: str) -> None:
    """The level-aware sibling of `_open_increment_doc` (root-only, below): writes
    `<workdir>/<STATUS>.md` with a `Status: **OPEN**`/`Status: **CLOSED**` header. Lets a
    `_REAL_REPO_CASES` fixture control the open-increment state of a NON-root level's own
    `docs/work/` — the same header grammar `seed/lifecycle.py`'s `_OPEN_RE` parses."""
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / f"{status}.md").write_text(f"# Test increment\n\nStatus: **{status}**\n", encoding="utf-8")


def _case_real_docs_md(base: Path) -> list:
    """`.md` is always editable, independent of any increment state (`edit_allowed`'s own first check,
    before the level lookup even runs) — a bare fixture repo with no open increment anywhere proves
    this branch is taken on its own, not by accident of an open increment elsewhere."""
    d = base / "real_docs_md"
    _init_repo(d)
    target = d / "docs" / "STATE.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# fixture state doc\n", encoding="utf-8")
    _commit_all(d, "init")
    return [str(d), str(target)]


def _case_real_meta_path(base: Path) -> list:
    """A path OUTSIDE `factories/` (meta level) with the root `docs/work/` OPEN — the level lookup must
    resolve to the root, and the open increment there must permit the edit."""
    d = base / "real_meta_path"
    _init_repo(d)
    _write_increment_doc(d / "docs" / "work", status="OPEN")
    target = d / "v3" / "control" / "cadence.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# fixture meta-level source\n", encoding="utf-8")
    _commit_all(d, "init")
    return [str(d), str(target)]


def _case_real_factory_path(base: Path) -> list:
    """A path under `factories/<f>/` but not `products/` (factory level), with that factory's own
    `docs/work/` present but CLOSED — the level lookup must resolve to the factory (not the root), and
    a present-but-closed increment there must still block the edit."""
    d = base / "real_factory_path"
    _init_repo(d)
    _write_increment_doc(d / "factories" / "demo-factory" / "docs" / "work", status="CLOSED")
    target = d / "factories" / "demo-factory" / "codegen" / "__init__.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("", encoding="utf-8")
    _commit_all(d, "init")
    return [str(d), str(target)]


def _case_real_product_path(base: Path) -> list:
    """A path under `factories/<f>/products/<p>/` (product level, the deepest resolution), with that
    product's own `docs/work/` OPEN — the level lookup must resolve past the factory to the product."""
    d = base / "real_product_path"
    _init_repo(d)
    _write_increment_doc(
        d / "factories" / "demo-factory" / "products" / "demo-product" / "docs" / "work", status="OPEN")
    target = d / "factories" / "demo-factory" / "products" / "demo-product" / "src" / "Placeholder.kt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("// fixture product source\n", encoding="utf-8")
    _commit_all(d, "init")
    return [str(d), str(target)]


def _case_real_no_open_increment(base: Path) -> list:
    """A factory that NEVER EXISTS in this fixture at all — its `docs/work/` dir is never created, so
    `open_increment_in` hits the "workdir does not exist" branch unconditionally. Guaranteed False by
    construction, not by luck of what happens to be open elsewhere."""
    d = base / "real_no_open_increment"
    _init_repo(d)
    (d / "README.md").write_text("no such factory in this fixture\n", encoding="utf-8")
    _commit_all(d, "init")
    target = d / "factories" / "definitely-not-a-real-factory-xyz" / "file.py"
    return [str(d), str(target)]


def _case_real_proof_path(base: Path) -> list:
    """A `.proof/` path — not `src/` — still under `factories/<f>/products/<p>/` (product level), paired
    with `product_path` on purpose: both must resolve to the SAME level, proving a `.proof/` path isn't
    misclassified just because it isn't source."""
    d = base / "real_proof_path"
    _init_repo(d)
    _write_increment_doc(
        d / "factories" / "demo-factory" / "products" / "demo-product" / "docs" / "work", status="OPEN")
    target = d / "factories" / "demo-factory" / "products" / "demo-product" / ".proof" / "s0.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}\n", encoding="utf-8")
    _commit_all(d, "init")
    return [str(d), str(target)]


def _case_real_seed_column_path(base: Path) -> list:
    """A `seed/` path — not `v3/` — still outside `factories/` (meta level), paired with `meta_path` on
    purpose: both must resolve to the root, proving the column's own path isn't misclassified either."""
    d = base / "real_seed_column_path"
    _init_repo(d)
    _write_increment_doc(d / "docs" / "work", status="OPEN")
    target = d / "seed" / "lifecycle.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# fixture seed column source\n", encoding="utf-8")
    _commit_all(d, "init")
    return [str(d), str(target)]


#: `edit_allowed`/`required_workdir_rel` over every branch the level-aware placement law has — HERMETIC
#: (V3-EXTRACT-OBLIGATIONS phase 1.ter): each case builds its OWN fixture repo, the same
#: `_init_repo`/`_commit_all` pattern `_DEBT_CASES` uses below, rather than reading this repo's actual
#: `docs/work/` — whose open/closed state drifts as real increments open and close, which is exactly
#: what made two of these seven cases pin a fact about THIS machine's git state instead of about v3
#: (found by the acceptance gate's LAW G travel probe). Both functions are driven over the SAME set on
#: purpose: they answer the SAME question (does this path need an increment, and where).
_REAL_REPO_CASES: tuple[tuple[str, Callable[[Path], list]], ...] = (
    ("docs_md", _case_real_docs_md),
    ("meta_path", _case_real_meta_path),
    ("factory_path", _case_real_factory_path),
    ("product_path", _case_real_product_path),
    ("no_open_increment", _case_real_no_open_increment),
    ("proof_path", _case_real_proof_path),
    ("seed_column_path", _case_real_seed_column_path),
)


def _target_cases() -> list[tuple[str, list]]:
    return [
        ("read", ["Read", {"file_path": "/a/read.py"}]),
        ("write", ["Write", {"file_path": "/a/write.py"}]),
        ("edit", ["Edit", {"file_path": "/a/edit.py"}]),
        ("bash", ["Bash", {"command": "ls -la"}]),
        ("agent", ["Agent", {"subagent_type": "verifier", "description": "digest"}]),
        ("malformed", ["Read", "not-a-dict"]),
    ]


def _spawn_cases() -> list[tuple[str, list]]:
    return [("agent", ["Agent"]), ("task_alias", ["Task"]), ("bash", ["Bash"])]


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def _init_repo(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    _git(d, "init", "-q")
    _git(d, "config", "user.email", "column-law-parity@example.test")
    _git(d, "config", "user.name", "Column Law Parity")


def _commit_all(d: Path, msg: str) -> datetime:
    _git(d, "add", "-A")
    _git(d, "commit", "-q", "--no-gpg-sign", "-m", msg)
    iso = _git(d, "log", "-1", "--format=%cI").stdout.strip()
    return datetime.fromisoformat(iso).astimezone(timezone.utc)


def _write_journal(root: Path, *, passed: bool, ts: datetime) -> None:
    p = root / ".metamem" / "journal.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "kind": "station_run", "station": "s0",
           "passed": passed}
    p.write_text(json.dumps(rec) + "\n", encoding="utf-8")


def _open_increment_doc(d: Path) -> None:
    wd = d / "docs" / "work"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "OPEN.md").write_text("# Test increment\n\nStatus: **OPEN**\n", encoding="utf-8")


def _case_no_increment(base: Path) -> list:
    d = base / "no_increment"
    _init_repo(d)
    (d / "README.md").write_text("no increment here\n", encoding="utf-8")
    _commit_all(d, "init")
    return [str(d)]


def _case_open_clean(base: Path) -> list:
    d = base / "open_clean"
    _init_repo(d)
    _open_increment_doc(d)
    _commit_all(d, "open increment, clean")
    return [str(d)]


def _case_open_dirty_no_gate(base: Path) -> list:
    d = base / "open_dirty_no_gate"
    _init_repo(d)
    _open_increment_doc(d)
    (d / ".gitignore").write_text(".metamem/\n", encoding="utf-8")
    _commit_all(d, "open increment")
    (d / "src.py").write_text("x = 1\n", encoding="utf-8")  # uncommitted, non-.md
    return [str(d)]


def _case_open_dirty_gate_before_commit(base: Path) -> list:
    d = base / "open_dirty_gate_before"
    _init_repo(d)
    _open_increment_doc(d)
    (d / ".gitignore").write_text(".metamem/\n", encoding="utf-8")
    commit_dt = _commit_all(d, "open increment")
    (d / "src.py").write_text("x = 1\n", encoding="utf-8")
    _write_journal(d, passed=True, ts=commit_dt - timedelta(seconds=30))
    return [str(d)]


def _case_open_dirty_gate_after_commit(base: Path) -> list:
    d = base / "open_dirty_gate_after"
    _init_repo(d)
    _open_increment_doc(d)
    (d / ".gitignore").write_text(".metamem/\n", encoding="utf-8")
    commit_dt = _commit_all(d, "open increment")
    (d / "src.py").write_text("x = 1\n", encoding="utf-8")
    _write_journal(d, passed=True, ts=commit_dt + timedelta(seconds=30))
    return [str(d)]


_DEBT_CASES: tuple[tuple[str, Callable[[Path], list]], ...] = (
    ("no_increment", _case_no_increment),
    ("open_clean", _case_open_clean),
    ("open_dirty_no_gate", _case_open_dirty_no_gate),
    ("open_dirty_gate_before_commit", _case_open_dirty_gate_before_commit),
    ("open_dirty_gate_after_commit", _case_open_dirty_gate_after_commit),
)


def _proof_sha(station: str, checks: list[dict]) -> str:
    """Mirrors `seed/verifier.py.compute_proof_sha` — FIXTURE construction, not a re-derivation of the
    column's law: this witness needs a proof whose sha genuinely recomputes clean to exercise the
    "trust" branch at all."""
    canonical = {"station": station, "checks": sorted([(str(c["name"]), int(c["exit"])) for c in checks])}
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def _write_proof_pin(proof_root: Path, station: str, checks: list[dict], *, tamper: bool = False) -> None:
    proof_dir = proof_root / ".proof"
    proof_dir.mkdir(parents=True, exist_ok=True)
    passed = len(checks) > 0 and all(int(c["exit"]) == 0 for c in checks)
    proof = {"station": station, "checks": checks, "passed": passed,
             "proof_sha": _proof_sha(station, checks)}
    if tamper:
        proof["passed"] = True
        proof["proof_sha"] = "0" * 64  # deliberately wrong -> gate_recompute_ok must reject it
    (proof_dir / f"{station}.json").write_text(json.dumps(proof), encoding="utf-8")


def _write_active(root: Path, proof_root: Path, station: str) -> None:
    proof_dir = root / ".proof"
    proof_dir.mkdir(parents=True, exist_ok=True)
    (proof_dir / "active.json").write_text(
        json.dumps({"root": str(proof_root), "station": station}), encoding="utf-8")


def _case_preflight_no_pin(base: Path) -> list:
    d = base / "preflight_no_pin"
    d.mkdir(parents=True, exist_ok=True)
    return [str(d), "none"]


def _case_preflight_trust(base: Path) -> list:
    d = base / "preflight_trust"
    d.mkdir(parents=True, exist_ok=True)
    _write_active(d, d, "s0")
    _write_proof_pin(d, "s0", [{"name": "compile", "exit": 0}])
    return [str(d), "false"]


def _case_preflight_block(base: Path) -> list:
    d = base / "preflight_block"
    d.mkdir(parents=True, exist_ok=True)
    _write_active(d, d, "s0")
    _write_proof_pin(d, "s0", [{"name": "compile", "exit": 0}], tamper=True)
    return [str(d), "false"]


def _case_preflight_rerun_capable(base: Path) -> list:
    d = base / "preflight_rerun_capable"
    d.mkdir(parents=True, exist_ok=True)
    _write_active(d, d, "s0")
    _write_proof_pin(d, "s0", [{"name": "compile", "exit": 0}])
    return [str(d), "true"]


_PREFLIGHT_CASES: tuple[tuple[str, Callable[[Path], list]], ...] = (
    ("no_pin", _case_preflight_no_pin),
    ("trust", _case_preflight_trust),
    ("block", _case_preflight_block),
    ("rerun_capable", _case_preflight_rerun_capable),
)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# RUN + COMPARE
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _call(prefix: list[str], which: str, args: list, cwd: Path, env: dict) -> dict:
    proc = subprocess.run([sys.executable, *prefix, which, json.dumps(args)], cwd=str(cwd), env=env,
                          capture_output=True, text=True)
    out = proc.stdout.strip()
    if not out:
        return {"ok": False, "error": f"no stdout (exit {proc.returncode}): {proc.stderr[-400:]}"}
    try:
        return json.loads(out.splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"ok": False, "error": f"non-JSON stdout (exit {proc.returncode}): {out[-300:]!r} "
                                       f"stderr={proc.stderr[-300:]!r}"}


#: functions whose result is a `[decision, reason]` pair — only the DECISION (index 0) is compared
#: (LAW #3: the reason is prose, and v2's `stop_block` prose was Spanish this port translated).
_TUPLE_SHAPED = {"debt", "stop_block", "preflight"}


def _comparable(fn: str, resp: dict) -> object:
    if not resp.get("ok"):
        return ("<error>", resp.get("error"))
    result = resp.get("result")
    if fn in _TUPLE_SHAPED:
        return result[0] if isinstance(result, list) and result else result
    if fn == "target_of" and result == "":
        return None  # v2's "" == this port's None (declared representation adapter)
    return result


def _all_case_names() -> list[str]:
    """The 37 `function:case` keys this module's matrix drives — the case-name space `pin_problems`'s
    bijection law (§2.2 law 2) checks the pin against."""
    return (
        [f"edit_allowed:{name}" for name, _ in _REAL_REPO_CASES]
        + [f"required_workdir_rel:{name}" for name, _ in _REAL_REPO_CASES]
        + [f"debt:{name}" for name, _ in _DEBT_CASES]
        + [f"stop_block:{name}" for name, _ in _DEBT_CASES]
        + [f"target_of:{name}" for name, _ in _target_cases()]
        + [f"is_subagent_spawn:{name}" for name, _ in _spawn_cases()]
        + [f"preflight:{name}" for name, _ in _PREFLIGHT_CASES]
    )


def _run_answers(prefix: list[str], cwd: Path, env: dict, synth: Path) -> dict[str, object]:
    """Run the whole 37-case matrix through ONE side (`prefix`/`cwd`/`env`) and return
    `{f"{function}:{case}": comparable_value}`. Only `_live_answers` (the port) calls this any more, but
    the `prefix`/`cwd`/`env` parameterization stays: it is what let the pin's provenance be proven by
    running the SAME matrix over the oracle in phase 1, before that call site was amputated here."""
    answers: dict[str, object] = {}

    def run_group(fn: str, cases: list[tuple[str, list]]) -> None:
        for name, args in cases:
            resp = _call(prefix, fn, args, cwd, env)
            answers[f"{fn}:{name}"] = _comparable(fn, resp)

    real_cases = [(name, build(synth)) for name, build in _REAL_REPO_CASES]
    run_group("edit_allowed", real_cases)
    run_group("required_workdir_rel", real_cases)
    debt_cases = [(name, build(synth)) for name, build in _DEBT_CASES]
    run_group("debt", debt_cases)
    run_group("stop_block", debt_cases)
    run_group("target_of", _target_cases())
    run_group("is_subagent_spawn", _spawn_cases())
    preflight_cases = [(name, build(synth / "preflight")) for name, build in _PREFLIGHT_CASES]
    run_group("preflight", preflight_cases)
    return answers


def _live_answers() -> dict[str, object]:
    """v3's port, driven alone (via `--drive`) over the whole matrix — the LIVE side of law 6's
    comparison against the pin. Never touches the oracle."""
    ported_prefix = ["-m", "v3.verify.column_law_parity", "--drive"]
    ported_env = dict(os.environ)
    with tempfile.TemporaryDirectory(prefix="v3-column-law-parity-live-") as tmp:
        synth = Path(tmp) / "synth"
        synth.mkdir()
        return _run_answers(ported_prefix, _ROOT, ported_env, synth)


def check() -> tuple[list[str], dict]:
    """The gate: v3's LIVE answers against the COMMITTED pin. Never shells to `git` — this module carries
    no code path that could any more (V3-EXTRACT-OBLIGATIONS phase 2)."""
    ref = harness.oracle_ref()
    case_names = _all_case_names()
    problems, pin = harness.pin_problems(_PIN_GATE, case_names, min_distinct=_MIN_DISTINCT_ANSWERS,
                                         oracle_ref=ref)
    if problems:
        return problems, {"cases": len(case_names)}
    mismatches = harness.compare_to_pin(_live_answers(), pin)
    counts = {"cases": len(case_names), "mismatches": len(mismatches)}
    return mismatches, counts


# ── the red side ──────────────────────────────────────────────────────────────────────────────────
_PLANTS: dict[str, tuple[str, Path, Callable[[str], str], str]] = {
    "edit_allowed_invert": ("control/cadence.py", _PORTED_CADENCE_PATH, _plant_edit_allowed_invert,
                            "edit_allowed"),
    "preflight_force_trust": ("verify/hermetic.py", _PORTED_HERMETIC_PATH, _plant_preflight_force_trust,
                              "preflight"),
    "target_of_always_none": ("control/instrument.py", _PORTED_INSTRUMENT_PATH,
                              _plant_target_of_always_none, "target_of"),
}


def _plant_cases(fn: str, base: Path) -> list[tuple[str, list]]:
    if fn == "edit_allowed":
        return [(name, build(base)) for name, build in _REAL_REPO_CASES]
    if fn == "target_of":
        return _target_cases()
    if fn == "preflight":
        return [(name, build(base)) for name, build in _PREFLIGHT_CASES]
    raise AssertionError(f"no case builder wired for {fn!r}")


def _run_sabotage() -> int:
    """Retargeted (V3-EXTRACT-OBLIGATIONS phase 1): every plant's LIVE answers (over its own function's
    cases) are compared against the PIN, never against a live oracle run — no oracle is built here at
    all any more. The two NEW plants (`pin_answer_corrupted`/`pin_case_dropped`) perturb an in-memory
    COPY of the pin itself and never touch a real pin file on disk."""
    ref = harness.oracle_ref()
    case_names = _all_case_names()
    caught: list[str] = []
    na: list[str] = []
    missed: list[str] = []

    try:
        pin = harness.load_pin(_PIN_GATE)
    except RuntimeError as exc:
        return Verdict("v3-column-law-parity (SABOTAGE)", 1, f"cannot run: {exc}").emit()

    with tempfile.TemporaryDirectory(prefix="v3-column-law-parity-sabotage-") as tmp:
        base = Path(tmp)
        for plant_name, (rel, real_path, plant_fn, fn) in _PLANTS.items():
            real_src = real_path.read_text(encoding="utf-8")
            try:
                patched_src = plant_fn(real_src)
            except harness.CannotPlant as exc:
                na.append(f"{plant_name}: {exc}")
                continue
            shadow_cwd = _build_shadow_v3(base / f"shadow_{plant_name}", patched_rel=rel,
                                          patched_src=patched_src)
            ported_prefix = ["-m", "v3.verify._driver"]
            ported_env = dict(os.environ)

            cases = _plant_cases(fn, base / f"fixtures_{plant_name}")
            answers = {f"{fn}:{name}": _comparable(fn, _call(ported_prefix, fn, args, shadow_cwd,
                                                              ported_env))
                      for name, args in cases}
            (caught if harness.compare_to_pin(answers, pin) else missed).append(plant_name)

    live = _live_answers()
    corrupted = harness.pin_answer_corrupted(pin)
    (caught if harness.compare_to_pin(live, corrupted) else missed).append("pin_answer_corrupted")

    dropped = harness.pin_case_dropped(pin)
    drop_problems, _ = harness.pin_problems(_PIN_GATE, case_names, min_distinct=_MIN_DISTINCT_ANSWERS,
                                            oracle_ref=ref, pin=dropped)
    (caught if drop_problems else missed).append("pin_case_dropped")

    print(f"PLANTS caught={caught} na={na} missed={missed}")

    if missed:
        return Verdict("v3-column-law-parity (SABOTAGE)", 1,
                       f"GATE DECORATIVO: {len(caught)} caught · {len(na)} n/a · {len(missed)} MISSED "
                       f"{missed}").emit()
    if not caught:
        return Verdict("v3-column-law-parity (SABOTAGE)", 1,
                       f"GATE DECORATIVO: every plant is N/A ({na}) — no witness caught anything").emit()
    return Verdict("v3-column-law-parity (SABOTAGE)", 0,
                   f"{len(caught)} planted defect(s) caught ({', '.join(caught)}) · {len(na)} n/a "
                   f"({', '.join(na) or 'none'})",
                   counts={"caught": len(caught), "na": len(na)}).emit()


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--drive":
        return _drive(argv[1:])
    if argv:
        return Verdict("v3-column-law-parity", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get("V3_COLUMN_LAW_PARITY_SABOTAGE") == "1":
        return _run_sabotage()

    problems, counts = check()
    if problems:
        return Verdict("v3-column-law-parity", 1,
                       f"{len(problems)} deviation(s) over {counts['cases']} case(s) against the "
                       f"committed pin",
                       counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-column-law-parity", 0,
                   f"{counts['cases']} case(s) match between the committed pin and the ported column "
                   f"law — decision parity only (LAW #3: reason prose is never compared)",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
