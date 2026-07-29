#!/usr/bin/env python3
"""dial — the draft→harden DIAL as a MEASURED, re-derivable capability, with teeth (ADR-017 §4),
PORTED from v2's `verify/dial.py` (the measurement) + `verify/checks/dial_gate.py` (the gate) into
ONE module (V3-INC4-GATES-BATCH-C) — the same shape as `v3.verify.composition`/`import_boundary`:
a small, pure LAW plus the I/O that feeds it real committed state.

    python3 -m v3.verify.dial
    V3_DIAL_SABOTAGE=1 python3 -m v3.verify.dial   # red side; must ALSO exit 0

The dial (`Station.tier` — draft/harden, wired through `v3.spec.loader`/`model`) lets a draft loop
defer the rigor layer and run only the core spine. ADOPTION is DATA — a factory's `station_sequence`
declares which ACTIVE stations are `tier: harden`. This module measures that adoption from COMMITTED
state ONLY (the factory base spec; no `.proof/`, no line re-run — cheap, clean-clone-safe) and gives an
adopted dial teeth so it cannot silently rot back to decorative.

TWO-SIDED LAW — `_profile_problems`, pure over a `DialProfile` (no I/O, so it can be fed synthetic
data directly, same shape as `import_boundary.analyze`/`composition.check`):
  ADOPTED     — a factory that declares >=1 harden station MUST keep harden a NON-EMPTY PROPER subset
                of its ACTIVE stations: ``0 < |harden| < |active|``. All-harden -> draft builds NOTHING
                (decorative the other way) -> FAIL.
  NOT ADOPTED — 0 harden stations -> N/A (opt-in; not adopting is honest, not a failure — SAFE-7).

WHY THE WITNESS IS `sabotage_env`, not a committed fixture (recorded, same reasoning as `roles`/
`kind_hygiene`'s docstrings). v2 had no committed all-harden factory to serve as a permanent negative —
checking one in would mean shipping a factory whose OWN gate would then need an explicit carve-out
(the isolation gate's self-defeating-fixture problem). The registered witness plants a synthetic
`DialProfile` (harden == active, i.e. all-harden) and asserts `_profile_problems` — the REAL law, not a
reimplementation of it — flags it. `v3.verify.checks.suite_sweep` re-runs this side separately.

CUT vs v2 (recorded, not silently dropped): v2's `render()` (the `meta dial` display verb) is not
ported — v3 has no CLI surface to wire it to yet, and an unwired display function is dead code, not a
gate. The LAW (`_profile_problems`) is the part with a gate to serve; the two-sided tooth is identical.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ..kernel.report import Verdict
from ..spec.loader import load_spec

_ROOT = Path(__file__).resolve().parents[2]  # dial.py -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_DIAL_SABOTAGE"


@dataclass
class DialProfile:
    factory: str
    active: list[str] = field(default_factory=list)   # active station ids (all run in harden, the default)
    harden: list[str] = field(default_factory=list)    # active station ids with tier:harden (deferred in draft)

    @property
    def adopted(self) -> bool:
        """The factory declares the dial: >=1 active station is tier:harden."""
        return bool(self.harden)

    @property
    def core(self) -> list[str]:
        """Stations that run in BOTH modes — the draft spine (active minus harden)."""
        h = set(self.harden)
        return [s for s in self.active if s not in h]

    @property
    def proper_subset(self) -> bool:
        """harden is a non-empty PROPER subset of active (``0 < |harden| < |active|``) — a
        non-decorative dial: draft defers real rigor yet still builds a non-empty core spine."""
        return 0 < len(self.harden) < len(self.active)


def _profile_problems(profile: DialProfile) -> list[str]:
    """THE LAW: pure, no I/O — takes an already-measured profile and decides. An adopted dial must
    defer a non-empty PROPER subset (the two-sided structural tooth); a factory that has not adopted
    (0 harden) is N/A (empty list, no problems)."""
    if not profile.adopted:
        return []
    if not profile.proper_subset:
        return [f"{profile.factory}: the dial tags all {len(profile.active)} active stations as "
                f"harden -> draft builds nothing (decorative); leave >=1 core station (the spine a "
                f"running app needs)"]
    return []


def measure(meta_root: Path, factory: str) -> DialProfile:
    """Raw measurement from committed state (the factory base spec; no `.proof/`)."""
    spec = load_spec(Path(meta_root) / "factories" / factory / "factory.spec.yml")
    active = [s.id for s in spec.stations if s.active]
    harden = [s.id for s in spec.stations if s.active and s.tier == "harden"]
    return DialProfile(factory=factory, active=active, harden=harden)


def factories(meta_root: Path) -> list[str]:
    fdir = Path(meta_root) / "factories"
    if not fdir.is_dir():
        return []
    return sorted(p.name for p in fdir.iterdir() if (p / "factory.spec.yml").is_file())


def gate_problems(meta_root: Path, factory: str) -> list[str]:
    """I/O edge + the law: single source for the gate over one real factory."""
    return _profile_problems(measure(meta_root, factory))


#: A synthetic negative fed straight to the REAL law (`_profile_problems`), never a reimplementation
#: of it: a factory that tagged EVERY active station harden — draft would build nothing.
_SABOTAGE_PROFILE = DialProfile(factory="sabotage-all-harden", active=["s0", "s1", "s2"],
                                 harden=["s0", "s1", "s2"])


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-dial", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        planted = _profile_problems(_SABOTAGE_PROFILE)
        if planted:
            return Verdict("v3-dial (SABOTAGE)", 0,
                           f"an all-harden factory was caught: {len(planted)} problem(s)").emit()
        return Verdict("v3-dial (SABOTAGE)", 1,
                       "GATE DECORATIVO: an all-harden factory did NOT flip the gate red — "
                       "no teeth").emit()

    facs = factories(_ROOT)
    if not facs:
        return Verdict("v3-dial", 0,
                       "N/A: no factories in this tree — the dial does not apply (honest, SAFE-7)"
                       ).emit()

    problems: list[str] = []
    adopted: list[str] = []
    for f in facs:
        probs = gate_problems(_ROOT, f)
        problems.extend(probs)
        if not probs:
            p = measure(_ROOT, f)
            if p.adopted:
                adopted.append(f"{f} (core {len(p.core)}/harden {len(p.harden)})")

    if problems:
        return Verdict("v3-dial", 1, f"{len(problems)} dial violation(s)",
                       failures=tuple(problems)).emit()
    if adopted:
        return Verdict("v3-dial", 0,
                       f"{len(adopted)}/{len(facs)} factory/ies adopted the draft→harden dial "
                       f"(non-empty proper subset): {' · '.join(adopted)}").emit()
    return Verdict("v3-dial", 0,
                   f"N/A: none of the {len(facs)} factory/ies adopted the draft→harden dial "
                   f"(opt-in, honest)").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
