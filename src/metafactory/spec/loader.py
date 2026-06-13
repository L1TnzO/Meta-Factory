"""loader — parse a factory.spec.yml into a FactorySpec (tolerant parse; the VALIDATOR,
not the loader, is what refuses an incomplete spec, so M0 can report ALL problems)."""
from __future__ import annotations

from pathlib import Path

import yaml

from .model import FactorySpec, Requirement, SpecStation


def load_spec(path: str | Path) -> FactorySpec:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    factory = data.get("factory", {}) or {}
    domain = data.get("domain", {}) or {}

    stations = [
        SpecStation(id=str(s.get("id", "")), name=str(s.get("name", s.get("id", ""))),
                    activation=str(s.get("activation", "always")))
        for s in (domain.get("station_sequence", []) or [])
    ]

    reqs: list[Requirement] = []
    req_block = data.get("requirements", {}) or {}
    for kind in ("functional", "nonfunctional"):
        for r in (req_block.get(kind, []) or []):
            reqs.append(Requirement(
                id=str(r.get("id", "")),
                statement=str(r.get("statement", "")),
                satisfied_by=list(r.get("satisfied_by", []) or []),
                kind=kind,
            ))

    return FactorySpec(
        name=str(factory.get("name", "")),
        slug=str(factory.get("slug", "")),
        maturity=str(factory.get("maturity", "")),
        produces=str(domain.get("produces", "")),
        stations=stations,
        substrate=data.get("factory_substrate", {}) or {},
        requirements=reqs,
        raw=data,
        path=path,
    )
