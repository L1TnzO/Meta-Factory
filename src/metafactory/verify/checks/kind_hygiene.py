"""kind_hygiene (D-3, COUNCIL-360 §5 — freeze the check-kind vocabulary, mirror of `role_hygiene`
ADR-020). Measurement: the ~32 check kinds are INVERTED — `product_env` carries 72/~130 uses, most
kinds appear once. The fix is NOT pruning (one-shot kinds sustain the meta line): it is FREEZING the
vocabulary with the SAME rule as agent roles: a new kind is a DELIBERATE act (edit `registry.KINDS` +
an ADR), and the bar is «doesn't `product_env` + a script suffice?».

This gate scans every check-kind surface the repo declares (station YAMLs' `checks[].kind` and
factory-specs' `station_sequence[].proof_checks[].kind`) and blocks any kind that landed OUTSIDE the
closed vocabulary — `registry.KINDS` is the single source, imported here, never copied.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

from .registry import KINDS

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


def used_kinds(meta_root: Path) -> list[tuple[str, str]]:
    """Every (source_file_relpath, kind) declared across the repo's check surfaces:
    - station YAMLs: src/metafactory/stations/*.yml and factories/*/stations/*.yml
      -> top-level `checks: [{kind: ...}]` entries (missing/empty checks -> no entries)
    - factory specs: factories/*/factory.spec.yml
      -> domain.station_sequence[].proof_checks[].kind
    Parse with yaml.safe_load; a malformed YAML contributes ("<path>", "<unparseable>")."""
    pairs: list[tuple[str, str]] = []
    station_paths = (
        sorted(meta_root.glob("src/metafactory/stations/*.yml"))
        + sorted(meta_root.glob("factories/*/stations/*.yml"))
    )
    for path in station_paths:
        pairs.extend(_station_kinds(path, str(path.relative_to(meta_root))))
    for path in sorted(meta_root.glob("factories/*/factory.spec.yml")):
        pairs.extend(_spec_kinds(path, str(path.relative_to(meta_root))))
    return pairs


def main(argv: list[str]) -> int:
    """argv = [meta_root]. GREEN (0): every used kind is in `registry.KINDS` (the CLOSED vocabulary,
    single source). RED (1): print one line per violation + a remedy line. Usage error (no argv) -> 2.
    Bounded output (<=20 violation lines + summary)."""
    if not argv:
        print("usage: kind_hygiene <meta_root>")
        return 2

    meta_root = Path(argv[0]).resolve()
    pairs = used_kinds(meta_root)
    violations = [(src, kind) for src, kind in pairs if kind not in KINDS]

    if violations:
        for src, kind in violations[:20]:
            print(f"✗ {src}: kind '{kind}' fuera del vocabulario CERRADO (D-3: kind nuevo = acto "
                  f"deliberado — editá registry.KINDS + ADR; la vara: ¿no alcanza product_env + un script?)")
            print(f"  -> reusá un kind existente en registry.KINDS o abrí una ADR para agregar '{kind}'")
        if len(violations) > 20:
            print(f"  ... y {len(violations) - 20} violación(es) más (no mostradas)")
        print(f"KIND HYGIENE: {len(violations)} violación(es) fuera del vocabulario cerrado "
              f"({len(KINDS)} kinds en registry.KINDS)")
        return 1

    print(f"OK kind hygiene: {len(pairs)} declaración(es) de kind, todas ∈ vocabulario cerrado "
          f"registry.KINDS ({len(KINDS)} kinds); un kind nuevo = acto deliberado (D-3, mirror ADR-020)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
