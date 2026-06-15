"""loader — parse a factory.spec.yml into a FactorySpec (tolerant parse; the VALIDATOR,
not the loader, is what refuses an incomplete spec, so M0 can report ALL problems).

v2 (A1) adds L1 capabilities, L2 station depends_on/proof_checks, L3 machinery and L5
verified_by/acceptance — all OPTIONAL, so v1 specs (dummy, ASF) load unchanged. The `capabilities`
key is preferred; the legacy `product_capabilities` is accepted as a fallback."""
from __future__ import annotations

from pathlib import Path

import yaml

from .model import Capability, FactorySpec, Machinery, ProofCheck, Requirement, SpecStation


def _str(v) -> str:
    return "" if v is None else str(v)


def _proof_check(d: dict) -> ProofCheck:
    return ProofCheck(
        name=_str(d.get("name", d.get("kind", ""))),
        cmd=_str(d.get("cmd", d.get("kind", ""))),
        runs_in=_str(d.get("runs_in", "")),
        toolchain=_str(d.get("toolchain", "")),
        status=_str(d.get("status", "")),
    )


def _station(d: dict) -> SpecStation:
    return SpecStation(
        id=_str(d.get("id", "")),
        name=_str(d.get("name", d.get("id", ""))),
        activation=_str(d.get("activation", "always")) or "always",
        depends_on=[_str(x) for x in (d.get("depends_on", []) or [])],
        proof_checks=[_proof_check(pc) for pc in (d.get("proof_checks", []) or [])],
        status=_str(d.get("status", "")),
        builds=list(d.get("builds", []) or []),   # C2: executable realization, consumed verbatim
        checks=list(d.get("checks", []) or []),
    )


def _capability(d: dict) -> Capability:
    return Capability(
        id=_str(d.get("id", "")),
        # accept legacy `statement` as the invariant text (v1 ASF specs used `statement`)
        invariant=_str(d.get("invariant", d.get("statement", ""))),
        artifact=_str(d.get("artifact", "")),
        proof=_str(d.get("proof", "")),
        primitive=_str(d.get("primitive", "")),
        tech=_str(d.get("tech", "")),
        status=_str(d.get("status", "")),
    )


def load_spec(path: str | Path) -> FactorySpec:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    factory = data.get("factory", {}) or {}
    domain = data.get("domain", {}) or {}

    stations = [_station(s) for s in (domain.get("station_sequence", []) or [])]

    caps_block = domain.get("capabilities", domain.get("product_capabilities", [])) or []
    capabilities = [_capability(c) for c in caps_block]

    mach_block = data.get("machinery", {}) or {}
    machinery = Machinery(
        harness=mach_block.get("harness", {}) or {},
        mcp=mach_block.get("mcp", {}) or {},
        infra=mach_block.get("infra", {}) or {},
        raw=mach_block,
    )

    reqs: list[Requirement] = []
    req_block = data.get("requirements", {}) or {}
    for kind in ("functional", "nonfunctional"):
        for r in (req_block.get(kind, []) or []):
            reqs.append(Requirement(
                id=_str(r.get("id", "")),
                statement=_str(r.get("statement", "")),
                satisfied_by=[_str(x) for x in (r.get("satisfied_by", []) or [])],
                verified_by=[_str(x) for x in (r.get("verified_by", []) or [])],
                acceptance=_str(r.get("acceptance", "")),
                kind=kind,
            ))

    return FactorySpec(
        name=_str(factory.get("name", "")),
        slug=_str(factory.get("slug", "")),
        maturity=_str(factory.get("maturity", "")),
        produces=_str(domain.get("produces", "")),
        stations=stations,
        substrate=data.get("factory_substrate", {}) or {},
        requirements=reqs,
        capabilities=capabilities,
        machinery=machinery,
        required_primitives=[_str(x) for x in (domain.get("required_primitives", []) or [])],
        raw=data,
        path=path,
    )
