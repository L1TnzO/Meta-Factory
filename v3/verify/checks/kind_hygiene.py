#!/usr/bin/env python3
"""kind_hygiene — freezes the check-KIND vocabulary (D-3, COUNCIL-360 §5), PORTED from v2's
`verify/checks/kind_hygiene.py`. Subject UNCHANGED where it can be: `factories/*/stations/*.yml` and
`factories/*/factory.spec.yml` — the factories, never the platform.

    python3 -m v3.verify.checks.kind_hygiene
    V3_KIND_HYGIENE_SABOTAGE=1 python3 -m v3.verify.checks.kind_hygiene   # red side; ALSO exit 0

CUT vs v2 (recorded, not silently dropped): v2 ALSO scanned its own platform's station YAMLs
(a `stations/*.yml` directory inside v2's own substrate package) for `checks[].kind` — v3 has no
such directory (v3 is the Claude-Agent-SDK harness; the m00-m08 station-YAML shape is v2's, not
carried over), so that half of the subject has no v3 analogue and is not silently re-pointed at
anything. Only the factories' `stations/*.yml` + `factory.spec.yml` are scanned — the whole subject
that DOES still exist.

THE FROZEN SOURCE MOVED (per the brief): v2's single source was `verify.checks.registry.KINDS`. In
v3 the frozen check-kind vocabulary is `v3.verify.kinds.KINDS` — the PORTED 29-kind mapping
(`V3-INC4-KINDS-PORT`), imported here, never copied. A new kind is still a DELIBERATE act (edit that
constant + an ADR); the bar is still «doesn't `product_env` + a script suffice?».

WHY THE WITNESS MOVED SHAPE (recorded, same reasoning as `roles`/`pbt`/`codegen_freeze`'s
docstrings): v2 had no committed negative fixture for this gate at all — its two-sidedness is not
ported here as a `fixture`, because doing so would mean CHECKING IN a station YAML with an
out-of-vocabulary kind, i.e. an artifact the platform's OWN `kind_hygiene` run over the real repo
would then have to explicitly carve out (the same category of self-defeating fixture
`v3.verify.checks.isolation`'s docstring explains for its OWN one-sided exemption). Registered
`sabotage_env` instead (`V3_KIND_HYGIENE_SABOTAGE`): plants an unknown kind in a SYNTHETIC in-memory
tree and asserts it is caught. `v3.verify.checks.suite_sweep` re-runs this side separately.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import yaml

from ..kinds import KINDS
from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_KIND_HYGIENE_SABOTAGE"
UNPARSEABLE = "<unparseable>"


def _load(path: Path) -> dict | None:
    """Parse a YAML file; a malformed file yields None (the caller records it as unparseable)."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def _station_kinds(path: Path, rel: str) -> list[tuple[str, str]]:
    """Top-level `checks: [{kind: ...}]` entries of one station YAML."""
    data = _load(path)
    if data is None:
        return [(rel, UNPARSEABLE)]
    return [(rel, str(check["kind"]))
            for check in (data.get("checks") or [])
            if isinstance(check, dict) and "kind" in check]


def _spec_kinds(path: Path, rel: str) -> list[tuple[str, str]]:
    """`domain.station_sequence[].proof_checks[].kind` entries of one factory-spec."""
    data = _load(path)
    if data is None:
        return [(rel, UNPARSEABLE)]
    pairs: list[tuple[str, str]] = []
    domain = data.get("domain") or {}
    for station in domain.get("station_sequence") or []:
        if not isinstance(station, dict):
            continue
        for check in station.get("proof_checks") or []:
            if isinstance(check, dict) and "kind" in check:
                pairs.append((rel, str(check["kind"])))
    return pairs


def used_kinds(root: Path) -> list[tuple[str, str]]:
    """Every (source_file_relpath, kind) declared across the repo's factory check surfaces:
    - factory station YAMLs: factories/*/stations/*.yml -> top-level `checks: [{kind: ...}]`
    - factory specs: factories/*/factory.spec.yml -> domain.station_sequence[].proof_checks[].kind
    Parse with yaml.safe_load; a malformed YAML contributes (path, UNPARSEABLE)."""
    pairs: list[tuple[str, str]] = []
    for path in sorted(root.glob("factories/*/stations/*.yml")):
        pairs.extend(_station_kinds(path, str(path.relative_to(root))))
    for path in sorted(root.glob("factories/*/factory.spec.yml")):
        pairs.extend(_spec_kinds(path, str(path.relative_to(root))))
    return pairs


def _violations(root: Path) -> list[str]:
    pairs = used_kinds(root)
    return [f"{src}: kind '{kind}' is OUTSIDE the CLOSED vocabulary (D-3: a new kind is a deliberate "
            f"act — edit v3.verify.kinds.KINDS + an ADR; the bar: doesn't product_env + a script suffice?)"
            for src, kind in pairs if kind not in KINDS]


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-kind-hygiene", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        tmp = Path(tempfile.mkdtemp(prefix="v3_kind_hygiene_sabotage_"))
        try:
            stations = tmp / "factories" / "synthetic" / "stations"
            stations.mkdir(parents=True)
            (stations / "s00.yml").write_text(
                "checks:\n  - kind: totally_unknown_kind_xyz\n", encoding="utf-8")
            problems = _violations(tmp)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        if not problems:
            return Verdict("v3-kind-hygiene (SABOTAGE)", 1,
                           "GATE DECORATIVO: an unknown kind planted in a station YAML did NOT flip "
                           "the gate red — no teeth").emit()
        return Verdict("v3-kind-hygiene (SABOTAGE)", 0,
                       f"an out-of-vocabulary kind was caught: {len(problems)} violation(s)").emit()

    pairs = used_kinds(_ROOT)
    problems = _violations(_ROOT)
    if problems:
        return Verdict("v3-kind-hygiene", 1, f"{len(problems)} kind(s) outside the closed vocabulary",
                       failures=tuple(problems)).emit()

    return Verdict("v3-kind-hygiene", 0,
                   f"{len(pairs)} kind declaration(s), all in the closed vocabulary "
                   f"({len(KINDS)} kinds, v3.verify.kinds.KINDS)").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
