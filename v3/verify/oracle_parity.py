"""oracle_parity — the generic behavioural-parity harness, extracted from `eval_gate_parity` (the first
instrument of this shape) so the two check bodies ported after it — `live_run` and `eval_floor` — get the
same witness without re-deriving its plumbing.

WHAT LIVES HERE VS WHAT DOESN'T (the split the extracting increment had to get right). Generic: reading
the pinned ref (`oracle_ref`), extracting a v2 body at that ref via `git show` (`extract_oracle` — the v2
path is a PARAMETER, never a module constant, so this file itself never names the v2 substrate — see
`v3/verify/import_boundary.py`'s rule 3), running one case as a subprocess (`run_case`), running a whole
case matrix and collecting deviations (`run_matrix`), and the distinct-exit-code diversity guard
(`diversity_problem`) plus the `CannotPlant` exception the sabotage side of every parity module raises when
a plant finds nothing to perturb. Specific, and left in each parity module: the `_case_*` fixture builders
(they encode ONE check body's own input contract — scorer/property/evidence fixtures, argv shape), the
`_plant_*` functions (they encode that body's own source text), and the `main()`/Verdict prose (the message
differs per module by name).

Each module using this harness keeps its own `_V2_PATH` / `_PORTED_MODULE` / `_PORTED_PATH` constants —
this file is invoked BY them, parameterized, and never hardcodes which check it is judging.

PIN PRIMITIVES (V3-EXTRACT-OBLIGATIONS phase 1, §2 of the slot contract). The functions below are the
SECOND thing every parity module needs, added once here rather than five times: a `<gate>.json` fossil
of the oracle's answers, committed at `PINS_DIR`, so a gate can compare v3's live body against a
COMMITTED value instead of asking the dead ancestor at every run. `pin_problems` carries laws 1–5 of
§2.2 (well-formed · bijection with the matrix · LOCK #1 (an empty pin is never vacuously true) ·
diversity over the PINNED answers · ref binding); `compare_to_pin` carries law 6 (live vs pinned, per
case, canonicalised); `write_pin` is the `--repin`/`--verify-pin` body (§2.3/§2.4): it REFUSES to write
when two independent oracle derivations disagree (naming the unstable cases) or when the first is
empty, and `check_only=True` re-derives and diffs against the committed pin ignoring only
`provenance.derived_at` — the tooth that only means anything while the oracle still exists.

THE ONE THING THAT MUST NOT HAPPEN, restated here because this is where it would happen: every value
`write_pin` ever fossilises must come from `first`/`second`, and every caller of `write_pin` builds
those from a code path that RUNS the extracted oracle body — never from v3's own live answers. This
file cannot enforce that (it has no way to tell which side its caller measured); it is each module's
`--repin`/`--verify-pin` argv branch that must get it right, and it is `check_only=True` — re-deriving
independently and byte-comparing against the committed fossil — that is the check on that claim.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
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
    """The ref every parity module diffs against, from `v3/oracle_ref.json` — NEVER a hardcoded sha."""
    return json.loads(ORACLE_REF_PATH.read_text(encoding="utf-8"))["oracle_ref"]


def extract_oracle(ref: str, v2_path: str, dest: Path) -> None:
    """`git show <ref>:<v2_path>` into `dest`. Raises if the read fails or is empty — a silent empty
    oracle body would make every case compare "equal" (nothing to run) instead of proving anything.
    `v2_path` is a PARAMETER: this harness must stay free of any string naming the v2 substrate (a gate
    AST-scans `v3/` for exactly that — the caller's module carries the exemption, not this one)."""
    proc = subprocess.run(["git", "show", f"{ref}:{v2_path}"], cwd=ROOT_DIR, capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"git show {ref}:{v2_path} failed or returned nothing (exit {proc.returncode}): "
                           f"{proc.stderr.strip()}")
    dest.write_text(proc.stdout, encoding="utf-8")


@dataclass(frozen=True)
class Case:
    """One row of a case matrix: `build(base_dir)` builds whatever fixtures that case needs under a
    shared scratch directory and returns the argv the module-under-test's `main()` expects."""
    name: str
    build: Callable[[Path], list[str]]


def run_case(prefix: list[str], argv: list[str], cwd: Path, env: dict) -> int:
    """Run one case as a subprocess: `prefix` is the argv PREFIX that selects which body runs — a path to
    an extracted oracle script, `["-m", "dotted.module"]` for a package member, or a path to a patched
    copy for the sabotage side. Same argv, cwd and env for both sides of any one comparison."""
    proc = subprocess.run([sys.executable, *prefix, *argv], cwd=str(cwd), env=env,
                          capture_output=True, text=True)
    return proc.returncode


def run_matrix(oracle_prefix: list[str], ported_prefix: list[str], cwd: Path, env: dict, base: Path,
                matrix: tuple[Case, ...]) -> tuple[list[str], dict[str, int]]:
    """Run every case in `matrix` against both bodies over IDENTICAL argv/cwd/env; return (deviations,
    {case_name: oracle_exit_code})."""
    problems: list[str] = []
    codes: dict[str, int] = {}
    for case in matrix:
        argv = case.build(base)
        oracle_rc = run_case(oracle_prefix, argv, cwd, env)
        ported_rc = run_case(ported_prefix, argv, cwd, env)
        codes[case.name] = oracle_rc
        if oracle_rc != ported_rc:
            problems.append(f"{case.name}: oracle exit {oracle_rc} != ported exit {ported_rc}")
    return problems, codes


def diversity_problem(codes: dict[str, int], min_distinct: int) -> str | None:
    """LOCK #1 (see `eval_gate_parity` module docstring, the law this guard was born under): a matrix
    that never exercises more than a handful of oracle exit codes proves nothing — a matrix where every
    case happened to return the same code would compare equal without exercising any control flow."""
    distinct = sorted(set(codes.values()))
    if len(distinct) < min_distinct:
        return (f"the matrix exercised only {len(distinct)} distinct oracle exit code(s) {distinct} "
                f"across {len(codes)} case(s) — fewer than {min_distinct} means the comparison could "
                f"pass by coincidence")
    return None


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
        raise RuntimeError(f"no pin file at {path} — run `python3 -m v3.verify.{gate_name} --repin` "
                           f"while the oracle still exists (V3-EXTRACT-OBLIGATIONS §2.3)")
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


def write_pin(gate_name: str, *, oracle_ref: str, oracle_paths: dict, oracle_sha256: dict,
              derived_by: str, first: dict, second: dict, check_only: bool = False) -> list[str]:
    """The `--repin`/`--verify-pin` shared body (§2.3/§2.4). `first`/`second` are two INDEPENDENT
    derivations of the ORACLE's answers over the same matrix (never v3's live side — see this module's
    docstring). REFUSES to write — returns problems, writes nothing — when `first` is empty or when
    `first != second`, naming the unstable cases: a non-deterministic answer must never become a
    fossil. `check_only=True` builds the SAME payload and diffs it against the committed pin, ignoring
    ONLY `provenance.derived_at`; this is the provenance tooth, alive only while the ancestor still
    exists to re-derive from."""
    if not first:
        return [f"{gate_name}: the oracle derivation produced zero answers — refusing to write an "
               f"empty pin (LOCK #1)"]
    unstable = sorted(k for k in set(first) | set(second)
                      if canonical_key(first.get(k, "<absent-in-first-derivation>"))
                      != canonical_key(second.get(k, "<absent-in-second-derivation>")))
    if unstable:
        return [f"{gate_name}: two independent derivations of the oracle disagree on {len(unstable)} "
               f"case(s) — refusing to fossilise an unstable answer: {unstable}"]

    payload = {
        "pinned_gate": gate_name,
        "provenance": {
            "oracle_ref": oracle_ref,
            "oracle_paths": oracle_paths,
            "oracle_sha256": oracle_sha256,
            "derived_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "derived_by": derived_by,
            "harness": "v3.verify.oracle_parity",
        },
        "answers": {k: canonical(v) for k, v in first.items()},
    }

    if check_only:
        try:
            committed = load_pin(gate_name)
        except RuntimeError as exc:
            return [str(exc)]
        problems: list[str] = []
        for key in ("pinned_gate", "answers"):
            if payload[key] != committed.get(key):
                problems.append(f"{gate_name}: --verify-pin: {key!r} does not reproduce the committed "
                                f"pin")
        committed_provenance = committed.get("provenance") or {}
        for field_name in payload["provenance"]:
            if field_name == "derived_at":
                continue
            if payload["provenance"][field_name] != committed_provenance.get(field_name):
                problems.append(f"{gate_name}: --verify-pin: provenance.{field_name} does not "
                                f"reproduce the committed pin")
        return problems

    path = pin_path(gate_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return []


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
