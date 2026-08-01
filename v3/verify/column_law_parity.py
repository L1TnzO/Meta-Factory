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
RESULT, not an exit code — the contract this slot was handed asks for exactly that.

THE RELATIVE-IMPORT WRINKLE, twice. v2's `cadence.py` opens with `from .._seed import
load_seed_lifecycle` and `from .journal import read as journal_read`; `hermetic.py` opens
`_seed_verifier()` with a deferred `from .._seed import load_seed_verifier`; `instrument.py` opens with
`from . import metrics`. None of these resolve when a file is run as a bare script (no package
context), so the oracle side is extracted as a throwaway PACKAGE (`oraclepkg/`) mirroring v2's own
shape closely enough for those imports to resolve: `_seed.py` and `journal.py` are extracted VERBATIM
(both are pure stdlib, no further cascade); `metrics.py` is a STUB (`target_of`/`is_subagent_spawn`
never read `metrics.*` — an unused sibling changes nothing observable about the two functions this
port carries, and the alternative, extracting the real one, drags in the legacy graph-pricing module,
a cascade with nothing to do with either function). `_seed.py`'s own `repo_root()` walks `parents[2]`
from its file location, so the extracted copy is placed at the SAME depth v2's real bridge module
sits at, two directories below the package root (`fsroot/src/oraclepkg/_seed.py`), and
`fsroot/seed/{lifecycle,verifier}.py` — read at the SAME `oracle_ref`, never the working tree — sit
where that `repo_root()` then looks for them. The ported side has the identical wrinkle in reverse for the SABOTAGE run only
(see below): `v3.control.cadence` cannot be run as a bare script either, and a defect must be planted
in a COPY, never the real file.

ORACLE READERS. `_V2_CADENCE`/`_V2_INSTRUMENT`/`_V2_HERMETIC`/`_V2_SEED_BRIDGE`/`_V2_JOURNAL` name v2
substrate paths read at `oracle_ref` via `git show` — never imported, never read from the working tree.
Needs its own line in `v3/verify/import_boundary.py`'s `_ORACLE_READERS`, the same as
`eval_gate_parity.py`'s and `live_run_parity.py`'s (the orchestrator's to add — see the slot contract;
`live_run_parity.py`'s own `_V2_PATH` comment documents the identical hand-off). `_SEED_LIFECYCLE`
("seed/lifecycle.py") and `_SEED_VERIFIER` ("seed/verifier.py") name no v2 substrate — they are the
column's OWN shared trust root, at the repo's ROOT, not inside the legacy package — so they need no
exemption (`v3.seed_loader`'s own docstring makes the same distinction for the working-tree read this
module's PORTED side takes via `..seed_loader`).

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

LOCK (copy `oracle_parity.diversity_problem`'s discipline, generalised from exit codes to DECISIONS):
a matrix where the oracle returned the same decision every time would compare equal and prove nothing.
`_MIN_DISTINCT` declares a floor PER FUNCTION; `check()` goes red under it.

SABOTAGE plants ONE defect per module, in a COPY of the ported body read off disk — never the real
file:
  * `edit_allowed_invert` (cadence) — the delegation `return load_seed_lifecycle().edit_allowed(...)`
    becomes `return not load_seed_lifecycle().edit_allowed(...)`. This module's `edit_allowed` is a
    thin delegate to the shared seed law (never re-derived — see `v3/control/cadence.py`'s own
    docstring for why), so the plant inverts the WRAPPER's return, exactly the shape a stray `not`
    typo would take in a future edit.
  * `preflight_force_trust` (hermetic) — forces the FIRST line of `preflight` to
    `return "trust", "SABOTAGE: forced"`, unconditionally — "always return the trusting branch",
    per the slot contract.
  * `target_of_always_none` (instrument) — forces the first line of `target_of` to `return None`.
A plant that finds nothing to perturb in the on-disk source raises `CannotPlant`, reported N/A beside
the caught/missed count, never folded into a catch (INC-5's law, INC-8's fix, re-used unchanged). The
sabotage side runs the PATCHED module inside a SHADOW copy of the small `v3/` subtree these three files
actually depend on (`control/{cadence,instrument}.py`, `memory/journal.py`, `economy/store.py`,
`seed_loader.py`, `verify/hermetic.py`, their `__init__.py`s) — copied from the WORKING TREE (never
git), exactly the "read off disk" convention every parity module in this package uses for the side
under test — plus a driver twin of this file's own `--drive` mode, since the patched copy has the same
relative-import wrinkle the real port does and cannot run as a bare script either.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import oracle_parity as harness
from ..kernel.report import Verdict

_V3 = harness.V3_DIR
_ROOT = harness.ROOT_DIR

# ── v2 paths read at `oracle_ref` via `git show` (never imported, never the working tree) ───────────
_V2_CADENCE = "src/metafactory/memory/cadence.py"
_V2_INSTRUMENT = "src/metafactory/memory/instrument.py"
_V2_HERMETIC = "src/metafactory/verify/hermetic.py"
_V2_SEED_BRIDGE = "src/metafactory/_seed.py"
_V2_JOURNAL = "src/metafactory/memory/journal.py"
#: the column's OWN shared trust root, at the repo ROOT — not v2 substrate, needs no exemption.
_SEED_LIFECYCLE = "seed/lifecycle.py"
_SEED_VERIFIER = "seed/verifier.py"

#: the ported bodies this gate judges, and the files their source is read from for the sabotage plants.
_PORTED_CADENCE_PATH = _V3 / "control" / "cadence.py"
_PORTED_INSTRUMENT_PATH = _V3 / "control" / "instrument.py"
_PORTED_HERMETIC_PATH = _V3 / "verify" / "hermetic.py"

#: fewer distinct ORACLE decisions than this, for a given function, over the whole matrix means that
#: function's rows prove nothing (LOCK above).
_MIN_DISTINCT: dict[str, int] = {
    "edit_allowed": 2,
    "required_workdir_rel": 3,
    "debt": 2,
    "stop_block": 2,
    "target_of": 4,
    "is_subagent_spawn": 2,
    "preflight": 3,
}


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# THE ORACLE SIDE: a throwaway package mirroring v2's own runtime shape
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

_METRICS_STUB_SRC = ('"""Stub sibling: `target_of`/`is_subagent_spawn` never reference `metrics.*` — '
                     'an unused sibling satisfies `instrument.py`\'s `from . import metrics` without '
                     'dragging in the pricing cascade the real module needs for its OTHER functions, '
                     'none of which this port carries."""\n')


def _build_oracle_tree(ref: str, base: Path) -> Path:
    """Reconstructs the throwaway package (module docstring). Returns the `cwd` to run
    `-m oraclepkg.driver` from (`fsroot/src`, so `import oraclepkg` resolves via cwd-on-sys.path,
    exactly as `-m v3....` resolves `v3` from the repo root elsewhere in this harness)."""
    fsroot = base / "fsroot"
    pkg = fsroot / "src" / "oraclepkg"
    (pkg / "memory").mkdir(parents=True, exist_ok=True)
    (pkg / "verify").mkdir(parents=True, exist_ok=True)
    (fsroot / "seed").mkdir(parents=True, exist_ok=True)

    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "memory" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "verify" / "__init__.py").write_text("", encoding="utf-8")

    harness.extract_oracle(ref, _V2_SEED_BRIDGE, pkg / "_seed.py")
    harness.extract_oracle(ref, _V2_CADENCE, pkg / "memory" / "cadence.py")
    harness.extract_oracle(ref, _V2_JOURNAL, pkg / "memory" / "journal.py")
    harness.extract_oracle(ref, _V2_INSTRUMENT, pkg / "memory" / "instrument.py")
    harness.extract_oracle(ref, _V2_HERMETIC, pkg / "verify" / "hermetic.py")
    harness.extract_oracle(ref, _SEED_LIFECYCLE, fsroot / "seed" / "lifecycle.py")
    harness.extract_oracle(ref, _SEED_VERIFIER, fsroot / "seed" / "verifier.py")
    (pkg / "memory" / "metrics.py").write_text(_METRICS_STUB_SRC, encoding="utf-8")
    (pkg / "driver.py").write_text(_ORACLE_DRIVER_SRC, encoding="utf-8")
    return fsroot / "src"


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
def _real_repo_cases() -> list[tuple[str, list]]:
    """`edit_allowed`/`required_workdir_rel` over REAL repo paths — every branch the level-aware
    placement law has. Both functions are driven over the SAME set on purpose: they answer the SAME
    question (does this path need an increment, and where)."""
    root = str(_ROOT)
    return [
        ("docs_md", [root, str(_ROOT / "docs" / "STATE.md")]),
        ("meta_path", [root, str(_ROOT / "v3" / "control" / "cadence.py")]),
        ("factory_path", [root, str(_ROOT / "factories" / "full-stack-kotlin" / "codegen" / "__init__.py")]),
        ("product_path", [root, str(_ROOT / "factories" / "full-stack-kotlin" / "products" / "snipeit"
                                    / "src" / "Placeholder.kt")]),
        ("no_open_increment", [root, str(_ROOT / "factories" / "definitely-not-a-real-factory-xyz"
                                         / "file.py")]),
        ("proof_path", [root, str(_ROOT / "factories" / "full-stack-kotlin" / "products" / "snipeit"
                                  / ".proof" / "s0.json")]),
        ("seed_column_path", [root, str(_ROOT / "seed" / "lifecycle.py")]),
    ]


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


@dataclass
class _Row:
    function: str
    name: str
    args: list
    oracle: dict
    ported: dict


def _run_group(rows: list[_Row], oracle_prefix, oracle_cwd, oracle_env,
               ported_prefix, ported_cwd, ported_env, fn: str, cases: list[tuple[str, list]]) -> None:
    for name, args in cases:
        o = _call(oracle_prefix, fn, args, oracle_cwd, oracle_env)
        p = _call(ported_prefix, fn, args, ported_cwd, ported_env)
        rows.append(_Row(fn, name, args, o, p))


def check(ref: str) -> tuple[list[str], dict]:
    problems: list[str] = []
    rows: list[_Row] = []
    with tempfile.TemporaryDirectory(prefix="v3-column-law-parity-") as tmp:
        base = Path(tmp)
        oracle_cwd = _build_oracle_tree(ref, base / "oracle")
        oracle_prefix = ["-m", "oraclepkg.driver"]
        oracle_env = dict(os.environ)
        ported_prefix = ["-m", "v3.verify.column_law_parity", "--drive"]
        ported_env = dict(os.environ)

        _run_group(rows, oracle_prefix, oracle_cwd, oracle_env, ported_prefix, _ROOT, ported_env,
                  "edit_allowed", _real_repo_cases())
        _run_group(rows, oracle_prefix, oracle_cwd, oracle_env, ported_prefix, _ROOT, ported_env,
                  "required_workdir_rel", _real_repo_cases())

        synth = base / "synth"
        synth.mkdir()
        debt_cases = [(name, build(synth)) for name, build in _DEBT_CASES]
        _run_group(rows, oracle_prefix, oracle_cwd, oracle_env, ported_prefix, _ROOT, ported_env,
                  "debt", debt_cases)
        _run_group(rows, oracle_prefix, oracle_cwd, oracle_env, ported_prefix, _ROOT, ported_env,
                  "stop_block", debt_cases)

        _run_group(rows, oracle_prefix, oracle_cwd, oracle_env, ported_prefix, _ROOT, ported_env,
                  "target_of", _target_cases())
        _run_group(rows, oracle_prefix, oracle_cwd, oracle_env, ported_prefix, _ROOT, ported_env,
                  "is_subagent_spawn", _spawn_cases())

        preflight_cases = [(name, build(synth / "preflight")) for name, build in _PREFLIGHT_CASES]
        _run_group(rows, oracle_prefix, oracle_cwd, oracle_env, ported_prefix, _ROOT, ported_env,
                  "preflight", preflight_cases)

    per_function: dict[str, list] = {}
    for row in rows:
        o_val = _comparable(row.function, row.oracle)
        p_val = _comparable(row.function, row.ported)
        per_function.setdefault(row.function, []).append(o_val)
        if o_val != p_val:
            problems.append(f"{row.function}/{row.name}: oracle {row.oracle!r} (~{o_val!r}) != "
                            f"ported {row.ported!r} (~{p_val!r}) over args {row.args!r}")

    for fn, floor in _MIN_DISTINCT.items():
        vals = per_function.get(fn, [])
        distinct = len(set(map(repr, vals)))
        if distinct < floor:
            problems.append(f"{fn}: only {distinct} distinct oracle decision(s) {vals} across "
                            f"{len(vals)} case(s) — fewer than {floor} means the comparison could "
                            f"pass by coincidence")

    counts = {"cases": len(rows), "functions": len(per_function),
             "distinct_by_function": {fn: len(set(map(repr, v))) for fn, v in per_function.items()},
             "mismatches": sum(1 for p in problems if ": oracle " in p)}
    return problems, counts


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
        return _real_repo_cases()
    if fn == "target_of":
        return _target_cases()
    if fn == "preflight":
        return [(name, build(base)) for name, build in _PREFLIGHT_CASES]
    raise AssertionError(f"no case builder wired for {fn!r}")


def _run_sabotage(ref: str) -> int:
    caught: list[str] = []
    na: list[str] = []
    missed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="v3-column-law-parity-sabotage-") as tmp:
        base = Path(tmp)
        oracle_cwd = _build_oracle_tree(ref, base / "oracle")
        oracle_prefix = ["-m", "oraclepkg.driver"]
        oracle_env = dict(os.environ)

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
            mismatch = False
            for name, args in cases:
                o = _call(oracle_prefix, fn, args, oracle_cwd, oracle_env)
                p = _call(ported_prefix, fn, args, shadow_cwd, ported_env)
                if _comparable(fn, o) != _comparable(fn, p):
                    mismatch = True
                    break
            (caught if mismatch else missed).append(plant_name)

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

    ref = harness.oracle_ref()

    if os.environ.get("V3_COLUMN_LAW_PARITY_SABOTAGE") == "1":
        return _run_sabotage(ref)

    problems, counts = check(ref)
    if problems:
        return Verdict("v3-column-law-parity", 1,
                       f"{len(problems)} deviation(s) over {counts['cases']} case(s) across "
                       f"{counts['functions']} function(s) @ {ref[:12]}",
                       counts=counts, failures=tuple(problems)).emit()
    return Verdict("v3-column-law-parity", 0,
                   f"{counts['cases']} case(s) across {counts['functions']} function(s) match between "
                   f"oracle and ported column law @ {ref[:12]} — decision parity only (LAW #3: reason "
                   f"prose is never compared)",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
