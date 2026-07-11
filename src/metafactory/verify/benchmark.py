"""benchmark — Fase 4 (ADR-017 §4, REAIM-SWEET-SPOT): a VERIFIABLE definition of a product-CLASS target.

"Done" for a product-class stops being prose. A *sweet-spot CRUD app* is a product that is SMALL
(`entity_count` in range) AND exercises the core capability set (every required capability's station is
pinned green). The SAME target, applied to an over-large product (the too-hard benchmark, e.g. 19
entities), MUST fail — so demoting it to a regression CEILING is a HARD, two-sided fact (see
`checks/benchmark_gate`), not a sentence in a doc.

Re-derived ONLY from COMMITTED state — the factory base spec (capability -> station, via requirements,
the same edge `rtm.py` walks), the instance's `product.yml` (entity count) and its `pinned_verdict.json`
(which stations are pinned green). No `.proof/`, no line re-run: the gate is cheap and works in a clean
clone. A `product.yml` never redefines requirements/capabilities (only `domain.product`), so the base
spec's edges apply to every instance.

The substrate names no product/factory/tech (ADR-012); the benchmark FILE is DATA — it may name instances,
like `parity.yml` names factories or `scenarios/` name spec shapes. Single source for `meta benchmark`
(display, bus-bounded) and the `benchmark` gate (block) — one law, no duplication (ADR-005 §4)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SWEET_SPOT = "sweet_spot"
CEILING = "ceiling"
_EXPECT = {SWEET_SPOT, CEILING}


@dataclass
class Target:
    entity_min: int
    entity_max: int
    required_capabilities: list[str] = field(default_factory=list)


@dataclass
class ProductRef:
    factory: str
    product: str
    expect: str          # SWEET_SPOT | CEILING


@dataclass
class Benchmark:
    id: str
    title: str
    target: Target
    products: list[ProductRef] = field(default_factory=list)


@dataclass
class Profile:
    found: bool                       # the instance exists on disk (product.yml + pin)
    entity_count: int = 0
    satisfied_caps: set[str] = field(default_factory=set)
    missing_caps: list[str] = field(default_factory=list)
    pinned_stations: set[str] = field(default_factory=set)
    note: str = ""


@dataclass
class Result:
    ref: ProductRef
    profile: Profile
    meets: bool                       # the profile satisfies the target (small AND all required caps)
    reasons: list[str]                # why it does NOT meet (empty when meets)

    @property
    def ok(self) -> bool:
        """The MEASURED classification matches the EXPECTED one. A sweet_spot must meet the target; a
        ceiling must NOT (else the target has no upper bound — decorative)."""
        if not self.profile.found:
            return False
        return self.meets == (self.ref.expect == SWEET_SPOT)


def load_benchmark(path: Path) -> Benchmark:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    t = data.get("target") or {}
    ec = t.get("entity_count") or {}
    target = Target(
        entity_min=int(ec.get("min", 0)),
        entity_max=int(ec.get("max", 10 ** 9)),
        required_capabilities=list(t.get("required_capabilities") or []),
    )
    prods = []
    for p in data.get("products") or []:
        exp = p.get("expect")
        if exp not in _EXPECT:
            raise ValueError(f"benchmark {path}: product {p!r} with invalid expect {exp!r} "
                             f"(expected {sorted(_EXPECT)})")
        prods.append(ProductRef(factory=p["factory"], product=p["product"], expect=exp))
    return Benchmark(id=str(data.get("id", path.stem)), title=str(data.get("title", "")),
                     target=target, products=prods)


def _cap_stations(meta_root: Path, factory: str) -> dict[str, set[str]]:
    """capability id -> the set of stations that satisfy it, from the factory BASE spec (the same
    requirement edge `rtm.build_tree` walks: req.capability -> req.satisfied_by)."""
    from ..spec.loader import load_spec
    spec = load_spec(meta_root / "factories" / factory / "factory.spec.yml")
    out: dict[str, set[str]] = {}
    for req in spec.requirements:
        if req.capability:
            out.setdefault(req.capability, set()).update(req.satisfied_by)
    return out


def measure(meta_root: Path, ref: ProductRef) -> Profile:
    """Raw measurement of a product from committed state (no `.proof/`): entity count + pinned stations."""
    pdir = Path(meta_root) / "factories" / ref.factory / "products" / ref.product
    bp_path, pin_path = pdir / "product.yml", pdir / "pinned_verdict.json"
    if not bp_path.is_file() or not pin_path.is_file():
        return Profile(found=False, note=f"missing product.yml or pin under products/{ref.product}/")
    bp = yaml.safe_load(bp_path.read_text(encoding="utf-8")) or {}
    pinned = set(json.loads(pin_path.read_text(encoding="utf-8")).keys())
    return Profile(found=True, entity_count=len(bp.get("entities") or []), pinned_stations=pinned)


def _assess(profile: Profile, target: Target, cap2st: dict[str, set[str]]) -> tuple[bool, list[str]]:
    """Does the profile MEET the target? Populates the profile's satisfied/missing caps; returns
    (meets, reasons-it-does-not). A cap is satisfied iff EVERY station that satisfies it is pinned green."""
    reasons: list[str] = []
    if not (target.entity_min <= profile.entity_count <= target.entity_max):
        reasons.append(f"entity_count {profile.entity_count} outside [{target.entity_min},{target.entity_max}]")
    for cap in target.required_capabilities:
        stations = cap2st.get(cap)
        if not stations:                                   # the cap isn't declared by the factory at all
            profile.missing_caps.append(cap)
            reasons.append(f"capability unknown to the factory: {cap}")
        elif stations <= profile.pinned_stations:          # every station of the cap is pinned green
            profile.satisfied_caps.add(cap)
        else:
            profile.missing_caps.append(cap)
            reasons.append(f"capability {cap} has no green pin (stations {sorted(stations - profile.pinned_stations)})")
    return (not reasons), reasons


def evaluate(meta_root: Path, bench: Benchmark) -> list[Result]:
    meta_root = Path(meta_root)
    cap2st_by_factory: dict[str, dict[str, set[str]]] = {}
    results: list[Result] = []
    for ref in bench.products:
        profile = measure(meta_root, ref)
        if not profile.found:
            results.append(Result(ref, profile, meets=False, reasons=[profile.note]))
            continue
        cap2st = cap2st_by_factory.setdefault(ref.factory, _cap_stations(meta_root, ref.factory))
        meets, reasons = _assess(profile, bench.target, cap2st)
        results.append(Result(ref, profile, meets=meets, reasons=reasons))
    return results


def gate_problems(meta_root: Path, bench: Benchmark) -> list[str]:
    """The benchmark's verdict as a list of problems (empty = PASS) — single source for the gate.
    Two-sided: a benchmark needs BOTH a `sweet_spot` candidate and a `ceiling` witness (else no teeth);
    every sweet_spot must MEET the target and every ceiling must NOT (a ceiling that meets it ⇒ the bound
    is decorative)."""
    results = evaluate(meta_root, bench)
    expects = {r.ref.expect for r in results}
    problems: list[str] = []
    if not ({SWEET_SPOT, CEILING} <= expects):
        problems.append(f"{bench.id}: not two-sided (missing {sorted({SWEET_SPOT, CEILING} - expects)}); "
                        f"a target with no ceiling is decorative")
    for r in results:
        if r.ok:
            continue
        if r.ref.expect == SWEET_SPOT:
            problems.append(f"{bench.id}: the sweet-spot product {r.ref.factory}/{r.ref.product} does not meet "
                            f"the target: {'; '.join(r.reasons) or 'not found'}")
        else:
            problems.append(f"{bench.id}: the ceiling {r.ref.factory}/{r.ref.product} MEETS the sweet-spot target "
                            f"({r.profile.entity_count} entities) → the bound is decorative")
    return problems


def render(bench: Benchmark, results: list[Result]) -> str:
    """Bus-bounded render (I-7): one line per product with its measured profile vs the target."""
    nok = sum(1 for r in results if r.ok)
    all_ok = bool(results) and all(r.ok for r in results)
    t = bench.target
    out = [f"VERDICT    benchmark {bench.id} — {'PASS' if all_ok else 'FAIL'}   (exit {0 if all_ok else 1})",
           f"SUMMARY    {nok}/{len(results)} products in their expected class · target: {t.entity_min}-{t.entity_max} "
           f"entities + {len(t.required_capabilities)} core capabilities"]
    for r in results:
        verdict = "ok" if r.ok else "MISMATCH"
        cls = "MEETS" if r.meets else "below/over"
        head = f"           {r.ref.factory}/{r.ref.product} [{r.ref.expect}] — {verdict}: "
        if not r.profile.found:
            out.append(head + r.profile.note)
            continue
        out.append(head + f"{r.profile.entity_count} entities, {cls} sweet-spot "
                          f"(caps {len(r.profile.satisfied_caps)}/{len(bench.target.required_capabilities)})"
                   + (f" — {'; '.join(r.reasons)}" if r.reasons else ""))
    return "\n".join(out)
