#!/usr/bin/env python3
"""pin_integrity — the accounting for the pins AS A SET; each parity module can only speak for itself.

    python3 -m v3.verify.checks.pin_integrity
    V3_PIN_INTEGRITY_SABOTAGE=1 python3 -m v3.verify.checks.pin_integrity   # red side; ALSO exit 0

JOB 2 of the V3-EXTRACT-OBLIGATIONS phase-2 slot. Phase 1 fossilised the oracle's 93 answers into
`v3/verify/pins/*.json` while the ancestor still existed; phase 2 amputated the oracle-reading half
from the five pinned parity modules. Neither phase gave anyone a place to ask about the pins as a
POPULATION: is there a pin for every module that claims one, and vice versa? does every pin carry
where it came from? and — the one that matters — does the pinned module actually RUN without the
ancestor, in the tree that will actually travel? This gate is that place; no parity module owns this
accounting, and folding it into one of the five would make that one module speak for all of them.

FOUR LAWS, each able to go red on its own:
  1. BIJECTION — every `v3/verify/pins/*.json` has a module declaring that `_PIN_GATE`, and every
     module declaring a `_PIN_GATE` has a pin file. An orphan pin is paperwork for a gate that does
     not run; a pinned module with no pin is a gate with no expectation.
  2. LOCK #1 — zero pinned modules discovered => RED. An empty population is never vacuously true
     (the law `codegen_freeze` was missing; V3-EXTRACT-RETIREMENT-INCREMENT §5).
  3. PROVENANCE PRESENT — every pin carries a complete provenance block and its `oracle_ref` matches
     `v3/oracle_ref.json`. (The per-CASE laws — bijection with a module's own matrix, diversity,
     comparison — stay each module's own `oracle_parity.pin_problems`/`compare_to_pin`; this law
     checks only the provenance block, which is a property of the pin AS A FILE, not of any matrix.)
  4. THE TRAVEL PROBE — the one that matters. Build the repo that will actually be extracted: every
     git-TRACKED file `v3.extract_manifest.classify()` calls `"package"`, copied into a temp dir with
     NO `.git`. Run each pinned gate there and require exit 0. Tracked-only, not a bare filesystem
     walk, on purpose: `.claude/worktrees/` is gitignored scratch that can hold a stale checkout of
     the dead ancestor (measured, V3-EXTRACT-RETIREMENT-INCREMENT §2) and would otherwise ride along
     as if it belonged to the package it happens to sit under — a probe built from what would
     actually leave in a real extraction, not from whatever happens to be lying around on this
     machine. The git BINARY stays available (several cases build fixture repos with `git init` —
     that is the PLATFORM, not the SUBJECT); what is absent is THIS repo's history. This law already
     earned its place: phase 1.ter found two `column_law_parity` cases pinning a fact about this
     machine's git state that only a probe with no history could have caught (§Evidencia).

POPULATION, DISCOVERED not hand-counted: an AST sweep of every `v3/**/*.py` for a module-level
`_PIN_GATE = "<literal>"` assignment — never imported (I-3: this gate must not execute the platform
it audits, the same discipline `retirement_census`'s population derivation uses). The dotted module
name the travel probe runs is DERIVED from the declaring file's own path, never a hand list, so a
sixth pinned module years from now needs no edit here to be picked up — or missed here to be caught.

RED SIDE, `V3_PIN_INTEGRITY_SABOTAGE=1`, exits 0 reporting what it caught. Five plants (one per law
that can be gamed, and BIJECTION gets one per direction since gaming it from either side is a
distinct failure): an orphan pin file · a pinned module whose pin is hidden · an empty population ·
incomplete/stale provenance · a module that reaches for the ancestor (a `git show` at the pinned ref
planted into a COPY of a module inside a FRESH, disposable probe tree — never a real pin or a real
module on disk). Each plant is paired with a healthy case on the SAME law, so a law is never trusted
to reject without also being shown it does not reject a clean one.
"""
from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ...extract_manifest import classify
from ...kernel.report import Verdict
from ..oracle_parity import _PROVENANCE_FIELDS

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_PIN_INTEGRITY_SABOTAGE"
PY = sys.executable

#: how many failures a red verdict shows inline (mirrors `extract_package`/`retirement_census`).
_MAX_SHOWN = 10


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# POPULATION DERIVATION: pure law over an already-parsed tree + a thin IO gatherer
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def module_level_pin_gate(tree: ast.Module) -> str | None:
    """Pure: the STRING VALUE of a module-level `_PIN_GATE = "..."` assignment, or None.
    Module-level only (never inside a `def`/`class`) — a genuine declaration is a name the rest of
    the file's top-level code can see, the same restriction `retirement_census`'s own population
    derivation applies to its literal match, for the identical reason."""
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if (isinstance(target, ast.Name) and target.id == "_PIN_GATE"
                    and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str)):
                return stmt.value.value
    return None


def discover_population(root: Path) -> dict[str, str]:
    """Every `v3/**/*.py` module declaring `_PIN_GATE` at module level -> `{gate_name: dotted_module}`.
    AST-parsed, never imported (I-3). The dotted module is derived from the declaring FILE's own
    repo-relative path, so the travel probe below runs exactly the module that made the claim."""
    population: dict[str, str] = {}
    base = root / "v3"
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except (SyntaxError, UnicodeDecodeError):
            continue
        gate = module_level_pin_gate(tree)
        if gate is not None:
            population[gate] = rel[:-3].replace("/", ".")
    return population


def discover_pins(root: Path) -> list[str]:
    """Gate names named by committed `v3/verify/pins/*.json` — the stem of each pin file."""
    pins_dir = root / "v3" / "verify" / "pins"
    if not pins_dir.is_dir():
        return []
    return sorted(p.stem for p in pins_dir.glob("*.json"))


def this_oracle_ref(root: Path) -> str:
    """The ref THIS repo declares, from `v3/oracle_ref.json` — never a hardcoded sha, the same
    single source every parity module's `oracle_parity.oracle_ref()` reads."""
    return json.loads((root / "v3" / "oracle_ref.json").read_text(encoding="utf-8"))["oracle_ref"]


def load_pin_raw(root: Path, gate_name: str) -> tuple[dict | None, str]:
    """`(pin_dict, "")` or `(None, reason)` — never raises. A pin file this census reads is read for
    ITS OWN SET-LEVEL shape (provenance), never for a matrix's cases, so a parse failure is a fact to
    report, not an exception to propagate."""
    path = root / "v3" / "verify" / "pins" / f"{gate_name}.json"
    if not path.exists():
        return None, f"no file at {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "pin file does not hold a JSON object"
    return data, ""


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# THE PURE LAWS (unit-exercised by the RED side, fed synthetic facts — never the real tree)
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def bijection_problems(pin_names: frozenset[str], population: dict[str, str]) -> list[str]:
    """Law 1: pins and declaring modules must name EXACTLY the same set, both directions."""
    declared = frozenset(population)
    orphan_pins = sorted(pin_names - declared)
    ungated = sorted(declared - pin_names)
    problems = [f"v3/verify/pins/{name}.json is an orphan pin — no module declares _PIN_GATE "
               f"{name!r}" for name in orphan_pins]
    problems += [f"{population[name]} declares _PIN_GATE {name!r} but v3/verify/pins/{name}.json "
                f"does not exist" for name in ungated]
    return problems


def population_lock_problems(population: dict[str, str]) -> list[str]:
    """Law 2, LOCK #1: zero pinned modules discovered is never vacuously true (the law
    `codegen_freeze` was missing; V3-EXTRACT-RETIREMENT-INCREMENT §5)."""
    if not population:
        return ["LOCK #1: zero modules declare _PIN_GATE — an empty population is never vacuously "
                "true"]
    return []


def provenance_problems(facts: tuple[tuple[str, dict | None, str, str], ...]) -> list[str]:
    """Law 3 over precomputed `(gate_name, pin_dict_or_None, load_error, this_repo_oracle_ref)`
    facts. `pin_dict` is None when the file could not be loaded at all — `load_error` names why. A
    pin with every field present but a STALE `oracle_ref` is a fossil of a different repo state than
    the one this tree declares, which is exactly as unusable as a missing field."""
    problems = []
    for gate_name, pin, load_error, this_ref in facts:
        if pin is None:
            problems.append(f"{gate_name}: pin could not be loaded — {load_error}")
            continue
        provenance = pin.get("provenance")
        if not isinstance(provenance, dict):
            problems.append(f"{gate_name}: pin carries no provenance object")
            continue
        for field_name in _PROVENANCE_FIELDS:
            if not provenance.get(field_name):
                problems.append(f"{gate_name}: provenance.{field_name} missing/empty")
        if provenance.get("oracle_ref") != this_ref:
            problems.append(f"{gate_name}: provenance.oracle_ref {provenance.get('oracle_ref')!r} "
                            f"!= this repo's v3/oracle_ref.json {this_ref!r}")
    return problems


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# LAW 4, THE TRAVEL PROBE: build the repo that will actually be extracted, run each pinned gate there
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def tracked_files(root: Path) -> list[str]:
    proc = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True)
    return [line for line in proc.stdout.splitlines() if line.strip()]


def build_probe_tree(root: Path, dest: Path) -> int:
    """Copies every git-TRACKED file `classify()` calls `'package'` into `dest`, preserving
    repo-relative paths, and nothing else — `dest` never gets a `.git` directory, so a module that
    reaches for this repo's history finds none there. Tracked-only, never a bare filesystem walk
    (module docstring's §4 note on `.claude/worktrees/`). Returns the count copied."""
    n = 0
    for rel in tracked_files(root):
        if classify(rel) != "package":
            continue
        src = root / rel
        if not src.is_file():
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        n += 1
    return n


def run_probe_module(dotted: str, cwd: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run([PY, "-m", dotted], cwd=str(cwd), env=env, capture_output=True, text=True)


def travel_problems(population: dict[str, str], probe_root: Path, env: dict) -> list[str]:
    """Law 4: every pinned gate, run inside the probe tree (no `.git`), must exit 0. The run target
    is the SAME `population` dict BIJECTION already checked, never a hand list — a sixth pinned
    module is probed the moment it declares `_PIN_GATE`, not the moment someone remembers to add it
    here."""
    problems = []
    for gate_name, dotted in sorted(population.items()):
        proc = run_probe_module(dotted, probe_root, env)
        if proc.returncode != 0:
            lines = proc.stdout.strip().splitlines() or proc.stderr.strip().splitlines() or [""]
            problems.append(f"{gate_name} ({dotted}): exit {proc.returncode} in the travel probe "
                            f"(no .git) — {lines[-1][:160]}")
    return problems


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# GREEN SIDE
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _real_report(root: Path) -> tuple[list[str], dict, int]:
    population = discover_population(root)
    pin_names = frozenset(discover_pins(root))
    this_ref = this_oracle_ref(root)

    problems = list(bijection_problems(pin_names, population))
    problems += population_lock_problems(population)

    prov_facts = tuple(
        (gate_name, *load_pin_raw(root, gate_name), this_ref) for gate_name in sorted(pin_names))
    problems += provenance_problems(prov_facts)

    n_copied = 0
    if population:
        with tempfile.TemporaryDirectory(prefix="v3-pin-integrity-probe-") as tmp:
            dest = Path(tmp)
            n_copied = build_probe_tree(root, dest)
            problems += travel_problems(population, dest, dict(os.environ))

    counts = {"population": len(population), "pins": len(pin_names), "probe_files": n_copied}
    return sorted(problems), counts, n_copied


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# RED SIDE (sabotage_env): five plants, each paired with a healthy case on the SAME law
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _plant_reaches_for_ancestor(root: Path, population: dict[str, str], this_ref: str
                                ) -> tuple[bool, str]:
    """Builds a FRESH, disposable probe tree (never the real gate's own run, never a file on disk
    outside a temp dir), picks ONE pinned module deterministically, and inserts a module-level
    statement into that module's COPY that shells `git show <oracle_ref>:seed/lifecycle.py` and
    exits 1 if it fails — simulating a module that reaches for the ancestor. The insertion anchors on
    `from __future__ import annotations`, present verbatim in every pinned module, so the injected
    code runs at import time (before `main()`), executing top to bottom exactly like the real file.
    Since the probe tree carries no `.git`, the `git show` fails and the plant exits 1 — the travel
    probe must then report it. Returns `(caught, detail)`; `detail` starts with `CANNOT_PLANT` if the
    anchor is missing (reported N/A, never folded into a catch — INC-5's law)."""
    if not population:
        return False, "CANNOT_PLANT: no pinned module available to plant into"
    gate_name = sorted(population)[0]
    dotted = population[gate_name]
    rel = Path(dotted.replace(".", "/") + ".py")
    anchor = "from __future__ import annotations\n"
    injected = (
        "import subprocess as _v3_sab_subprocess\n"
        f"_v3_sab_proc = _v3_sab_subprocess.run(['git', 'show', {this_ref!r} + ':seed/lifecycle.py'], "
        "capture_output=True)\n"
        "if _v3_sab_proc.returncode != 0:\n"
        "    import sys as _v3_sab_sys\n"
        "    _v3_sab_sys.exit(1)\n"
    )
    with tempfile.TemporaryDirectory(prefix="v3-pin-integrity-sabotage-probe-") as tmp:
        dest = Path(tmp)
        build_probe_tree(root, dest)
        target = dest / rel
        if not target.exists():
            return False, f"CANNOT_PLANT: {rel} not found in the probe tree"
        original = target.read_text(encoding="utf-8")
        if anchor not in original:
            return False, f"CANNOT_PLANT: anchor not found in {rel}"
        target.write_text(original.replace(anchor, anchor + injected, 1), encoding="utf-8")
        proc = run_probe_module(dotted, dest, dict(os.environ))
        caught = proc.returncode != 0
        return caught, f"{gate_name} ({dotted}) exit {proc.returncode} after the ancestor-reaching plant"


def _run_sabotage() -> int:
    root = _ROOT
    population = discover_population(root)
    this_ref = this_oracle_ref(root)
    caught: list[str] = []
    na: list[str] = []
    missed: list[str] = []

    # -- plant 1: an orphan pin file (BIJECTION, direction A) -----------------------------------
    hole = bool(bijection_problems(frozenset({"__sabotage_orphan_pin__"}), {}))
    healthy = not bijection_problems(frozenset(), {})
    (caught if hole and healthy else missed).append("orphan_pin")

    # -- plant 2: a pinned module whose pin is hidden (BIJECTION, direction B) ------------------
    hole = bool(bijection_problems(
        frozenset(), {"__sabotage_ghost_gate__": "v3.verify.__sabotage_ghost_gate__"}))
    healthy = not bijection_problems(frozenset({"real_gate"}), {"real_gate": "v3.verify.real_gate"})
    (caught if hole and healthy else missed).append("pin_hidden")

    # -- plant 3: an empty population (LOCK #1) --------------------------------------------------
    hole = bool(population_lock_problems({}))
    healthy = not population_lock_problems({"real_gate": "v3.verify.real_gate"})
    (caught if hole and healthy else missed).append("empty_population")

    # -- plant 4: incomplete / stale provenance (PROVENANCE PRESENT) ----------------------------
    good_provenance = {f: "x" for f in _PROVENANCE_FIELDS} | {"oracle_ref": this_ref}
    missing_field = {f: "x" for f in _PROVENANCE_FIELDS if f != "derived_at"} | {"oracle_ref": this_ref}
    stale_ref = dict(good_provenance) | {"oracle_ref": "0" * 40}
    hole = (bool(provenance_problems((("__sab__", {"provenance": missing_field}, "", this_ref),)))
           and bool(provenance_problems((("__sab__", {"provenance": stale_ref}, "", this_ref),))))
    healthy = not provenance_problems((("__sab__", {"provenance": good_provenance}, "", this_ref),))
    (caught if hole and healthy else missed).append("bad_provenance")

    # -- plant 5: a module that reaches for the ancestor (THE TRAVEL PROBE) ---------------------
    reaches_caught, detail = _plant_reaches_for_ancestor(root, population, this_ref)
    if detail.startswith("CANNOT_PLANT"):
        na.append(f"reaches_for_ancestor: {detail}")
    elif reaches_caught:
        caught.append("reaches_for_ancestor")
    else:
        missed.append("reaches_for_ancestor")

    print(f"PLANTS caught={caught} na={na} missed={missed}")

    if missed:
        return Verdict("v3-pin-integrity (SABOTAGE)", 1,
                       f"GATE DECORATIVO: {len(caught)} caught · {len(na)} n/a · {len(missed)} MISSED "
                       f"{missed}").emit()
    if not caught:
        return Verdict("v3-pin-integrity (SABOTAGE)", 1,
                       f"GATE DECORATIVO: every plant is N/A ({na}) — no witness caught anything").emit()
    return Verdict("v3-pin-integrity (SABOTAGE)", 0,
                   f"{len(caught)} planted defect(s) caught ({', '.join(caught)}) · {len(na)} n/a "
                   f"({', '.join(na) or 'none'})",
                   counts={"caught": len(caught), "na": len(na)}).emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-pin-integrity", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage()

    problems, counts, _ = _real_report(_ROOT)
    if problems:
        return Verdict("v3-pin-integrity", 1,
                       f"{len(problems)} pin-accounting problem(s) over {counts['population']} "
                       f"pinned module(s) and {counts['pins']} committed pin(s)",
                       failures=tuple(problems[:_MAX_SHOWN]), counts=counts,
                       next_action="fix the pin/module mismatch, the provenance block, or the "
                                   "module that still reaches for the ancestor — never weaken this "
                                   "gate to make the mismatch disappear").emit()
    return Verdict("v3-pin-integrity", 0,
                   f"{counts['population']} pinned module(s) bijection-matched to "
                   f"{counts['pins']} committed pin(s), provenance sane, and every pinned gate ran "
                   f"clean in a probe tree ({counts['probe_files']} file(s)) carrying no .git",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
