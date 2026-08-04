"""oracle_parity — the generic behavioural-parity harness, extracted from `eval_gate_parity` (the first
instrument of this shape) so the two check bodies ported after it — `live_run` and `eval_floor` — get the
same witness without re-deriving its plumbing.

WHAT LIVES HERE VS WHAT DOESN'T (the split the extracting increment had to get right). Generic: running
one case as a subprocess (`run_case`) and the `CannotPlant` exception the sabotage side of every parity
module raises when a plant finds nothing to perturb. Specific, and left in each parity module: the
`_case_*` fixture builders (they encode ONE check body's own input contract — scorer/property/evidence
fixtures, argv shape), the `_plant_*` functions (they encode that body's own source text), and the
`main()`/Verdict prose (the message differs per module by name).

Each module using this harness keeps its own `_PORTED_MODULE` / `_PORTED_PATH` constants — this file is
invoked BY them, parameterized, and never hardcodes which check it is judging.

PIN PRIMITIVES (V3-EXTRACT-OBLIGATIONS §2 of the slot contract). The functions below are the SECOND
thing every parity module needs: a `<gate>.json` fossil of the oracle's answers, committed at
`PINS_DIR`, so a gate can compare v3's live body against a COMMITTED value instead of asking the dead
ancestor at every run. `pin_problems` carries laws 1–5 of §2.2 (well-formed · bijection with the matrix ·
LOCK #1 (an empty pin is never vacuously true) · diversity over the PINNED answers · ref binding);
`compare_to_pin` carries law 6 (live vs pinned, per case, canonicalised). The pin derivation itself —
extracting the oracle, running it TWICE, refusing to fossilise a disagreement, writing the committed
JSON — lived here too through phase 1; it is GONE now (V3-EXTRACT-OBLIGATIONS phase 2), along with
every module's re-derivation argv branch that called it. The five committed pins under
`PINS_DIR` are the only trace that derivation ever ran, and they are proven byte-identical to what phase
1 wrote (the increment's LAW B) — this file, after the amputation, carries no path back to the ancestor
for `v3.verify.checks.pin_integrity`'s travel probe to catch.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

#: this module lives at `v3/verify/oracle_parity.py`; `V3_DIR` is `v3/`, `ROOT_DIR` the repo root — the
#: same two directories every parity module needs (as `cwd` for `git show` and for running the ported
#: module via `-m`), computed once here instead of re-derived per module.
_HERE = Path(__file__).resolve().parent
V3_DIR = _HERE.parent
ROOT_DIR = V3_DIR.parent
#: the single source of the pinned commit every parity witness measures against (ADR-031 §2.1) — read
#: fresh every call, never cached at import time, so a mid-process re-pin cannot be missed.
ORACLE_REF_PATH = V3_DIR / "oracle_ref.json"


def oracle_ref() -> str:
    """The ref every parity module diffs against, from `v3/oracle_ref.json` — NEVER a hardcoded sha.
    Still read: `pin_problems`' REF BINDING law (§2.2 law 5) checks a pin's provenance against it, and
    `v3.verify.checks.pin_integrity` checks a pin's `oracle_ref` against it too."""
    return json.loads(ORACLE_REF_PATH.read_text(encoding="utf-8"))["oracle_ref"]


@dataclass(frozen=True)
class Case:
    """One row of a case matrix: `build(base_dir)` builds whatever fixtures that case needs under a
    shared scratch directory and returns the argv the module-under-test's `main()` expects."""
    name: str
    build: Callable[[Path], list[str]]


def run_case(prefix: list[str], argv: list[str], cwd: Path, env: dict) -> int:
    """Run one case as a subprocess: `prefix` is the argv PREFIX that selects which body runs —
    `["-m", "dotted.module"]` for a package member, or a path to a patched copy for the sabotage side.
    Same argv, cwd and env for both sides of any one comparison."""
    proc = subprocess.run([sys.executable, *prefix, *argv], cwd=str(cwd), env=env,
                          capture_output=True, text=True)
    return proc.returncode


class CannotPlant(Exception):
    """A plant found nothing to perturb in the ON-DISK ported body. Raised rather than returning a bool,
    so a refusal to plant can never be mistaken for a catch (INC-5's law, applied by INC-8 to a red
    side, and re-used unchanged by every parity module built on this harness)."""


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# PIN PRIMITIVES — the fossil every parity module compares its live body against (module docstring)
# ══════════════════════════════════════════════════════════════════════════════════════════════════
#: one committed JSON per gate, `PINS_DIR / f"{gate_name}.json"` — `classify()` puts it under `package`
#: so it travels with the substrate, the same way `oracle_ref.json` does.
PINS_DIR = V3_DIR / "verify" / "pins"

#: every field the provenance block must carry (law 1, §2.2) — the same set `.gen/accept_phase1.sh`'s
#: LAW C checks for on the committed file, so a drift between the two would be caught there too.
_PROVENANCE_FIELDS = ("oracle_ref", "oracle_paths", "oracle_sha256", "derived_at", "derived_by", "harness")


def pin_path(gate_name: str) -> Path:
    """Where `gate_name`'s committed fossil lives."""
    return PINS_DIR / f"{gate_name}.json"


def canonical(value):
    """`tuple` -> `list`, RECURSIVELY. Nothing else — dict values and list items are recursed into,
    dict KEYS are left alone, and list/tuple CONTENTS are never reordered: order is information here
    (§2.5 of the slot contract; `session_memory_parity`'s facts carry tuples like `projection_lines`)."""
    if isinstance(value, tuple):
        return [canonical(v) for v in value]
    if isinstance(value, list):
        return [canonical(v) for v in value]
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items()}
    return value


def canonical_key(value) -> str:
    """A stable string identity for one answer: `canonical` first, then `json.dumps(sort_keys=True)` —
    `sort_keys` only orders dict KEYS for a deterministic string; it never touches list ORDER."""
    return json.dumps(canonical(value), sort_keys=True)


def load_pin(gate_name: str) -> dict:
    """The committed fossil for `gate_name`. Raises `RuntimeError` NAMING THE FILE on missing or
    unparsable — never a silent `{}` (law 1, §2.2: an unloadable pin is red, not vacuously green)."""
    path = pin_path(gate_name)
    if not path.exists():
        raise RuntimeError(f"no pin file at {path} — {gate_name} was amputated in "
                           f"V3-EXTRACT-OBLIGATIONS phase 2; a missing pin can no longer be re-derived, "
                           f"only restored from git history")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"pin file at {path} could not be read: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"pin file at {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"pin file at {path} does not hold a JSON object")
    return data


def _truncate(value, limit: int = 200) -> str:
    """Law 6's own rule: a verdict must never dump a fixture. Each side of a mismatch is shown, never
    in full."""
    text = repr(canonical(value))
    return text if len(text) <= limit else text[:limit] + "...<truncated>"


def pin_problems(gate_name: str, case_names, *, min_distinct: int, oracle_ref: str,
                  pin: dict | None = None) -> tuple[list[str], dict]:
    """Laws 1–5 of §2.2, over the COMMITTED pin — or, for the red side's `pin_case_dropped`/
    `pin_answer_corrupted` plants, an in-memory `pin` override handed in directly (never a second file
    written to disk). Returns `(problems, pin)`; `pin={}` only when `load_pin` itself raised (missing or
    unparsable — the on-disk half of law 1)."""
    if pin is None:
        try:
            pin = load_pin(gate_name)
        except RuntimeError as exc:
            return [str(exc)], {}

    problems: list[str] = []

    # law 1, the half `load_pin`'s raise does not cover: every provenance field present and non-empty.
    if pin.get("pinned_gate") != gate_name:
        problems.append(f"{gate_name}: pin's pinned_gate={pin.get('pinned_gate')!r}, expected "
                        f"{gate_name!r}")
    provenance = pin.get("provenance")
    if not isinstance(provenance, dict):
        problems.append(f"{gate_name}: pin carries no provenance object")
        provenance = {}
    for field_name in _PROVENANCE_FIELDS:
        if not provenance.get(field_name):
            problems.append(f"{gate_name}: provenance.{field_name} missing/empty")

    answers = pin.get("answers")
    if not isinstance(answers, dict):
        problems.append(f"{gate_name}: pin carries no answers object")
        answers = {}

    # law 2: bijection between the pin's cases and the matrix's, BOTH directions — a case with no
    # pinned answer is "left out of the count"; a pinned answer for a case that no longer exists is
    # paperwork for something that does not run.
    case_set = set(case_names)
    answer_set = set(answers)
    missing = sorted(case_set - answer_set)
    orphaned = sorted(answer_set - case_set)
    if missing:
        problems.append(f"{gate_name}: {len(missing)} case(s) in the matrix have no pinned answer: "
                        f"{missing}")
    if orphaned:
        problems.append(f"{gate_name}: {len(orphaned)} pinned answer(s) name a case no longer in the "
                        f"matrix: {orphaned}")

    # law 3: LOCK #1 — an empty pin is never vacuously true.
    if not answers:
        problems.append(f"{gate_name}: LOCK #1 — the pin holds zero answers")

    # law 4: diversity, over the PINNED answers (moved from the oracle's live exit codes to the fossil).
    if answers:
        distinct = len({canonical_key(v) for v in answers.values()})
        if distinct < min_distinct:
            problems.append(f"{gate_name}: the pin holds only {distinct} distinct answer value(s) "
                            f"across {len(answers)} case(s) — fewer than {min_distinct} means the "
                            f"comparison could pass by coincidence")

    # law 5: ref binding — a pin derived against a different commit than this repo declares is not
    # this repo's fossil.
    if provenance.get("oracle_ref") != oracle_ref:
        problems.append(f"{gate_name}: pin provenance.oracle_ref {provenance.get('oracle_ref')!r} != "
                        f"this repo's v3/oracle_ref.json {oracle_ref!r}")

    return problems, pin


def compare_to_pin(answers: dict, pin: dict) -> list[str]:
    """Law 6: for every case both sides know about, v3's LIVE answer (canonicalised) must equal the
    PINNED one. A case missing on either side is law 2's problem (`pin_problems`) — this function never
    raises on a keyset mismatch, it only reports value drift, one line per differing case, each side
    truncated to ~200 chars (a verdict must never dump a fixture)."""
    problems: list[str] = []
    pin_answers = pin.get("answers") or {}
    for case in sorted(set(answers) & set(pin_answers)):
        if canonical_key(answers[case]) != canonical_key(pin_answers[case]):
            problems.append(f"{case}: live {_truncate(answers[case])} != pinned "
                            f"{_truncate(pin_answers[case])}")
    return problems


#: a JSON-string value no real answer this harness's modules ever pin (exit codes, decision scalars,
#: fact dicts) could plausibly equal — the perturbation `pin_answer_corrupted` applies below.
_FOREIGN_VALUE = "\x00__V3_PIN_ANSWER_CORRUPTED__\x00"


def pin_answer_corrupted(pin: dict) -> dict:
    """An in-memory COPY of `pin` with ONE answer perturbed to a value distinct from the one it had —
    the fixture every pinned module's red side builds for its `pin_answer_corrupted` plant (§C of the
    slot contract: `compare_to_pin` must report >=1 problem against it). Never mutates `pin` itself,
    and never writes anything to disk."""
    copy = json.loads(json.dumps(pin))
    answers = copy.get("answers") or {}
    if answers:
        answers[sorted(answers)[0]] = _FOREIGN_VALUE
    return copy


def pin_case_dropped(pin: dict) -> dict:
    """An in-memory COPY of `pin` with ONE case removed from `answers` — the fixture every pinned
    module's red side builds for its `pin_case_dropped` plant (`pin_problems` must report >=1 problem
    against it). Never mutates `pin` itself, never writes anything to disk."""
    copy = json.loads(json.dumps(pin))
    answers = copy.get("answers") or {}
    if answers:
        del answers[sorted(answers)[0]]
    return copy
