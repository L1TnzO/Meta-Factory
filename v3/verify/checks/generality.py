#!/usr/bin/env python3
"""generality — ADR-014's tooth: NO substrate mechanism is promoted to `status: general` proven in
only one domain, PORTED from v2's `verify/checks/generality_parity.py` (V3-INC4-GATES-BATCH-C).

    python3 -m v3.verify.checks.generality
    V3_GENERALITY_SABOTAGE=1 python3 -m v3.verify.checks.generality   # red side; must ALSO exit 0

A *substrate mechanism* (a check `kind` or a build `action`) declares its promotion in
`docs/reference/parity.yml` (the promotion book — a SHARED file, not v2's; this gate reads it exactly
as `v3.verify.checks.deferred` reads a factory's `factory.spec.yml`, both committed data outside the
legacy substrate package). `status: prototype` is exploration in one domain (allowed) and never gates.
`status: general` is a PROMOTED claim, and THIS gate re-verifies it against re-derivable evidence
rather than trusting the prose: it falls red unless

  1. >=2 declared domains prove the mechanism green (a proof RECOMPUTED via the shared trust root,
     `v3.seed_loader.load_seed_verifier` — not a stale/hand-edited `passed: true`), AND
  2. at least one PAIR among those green domains is RADICALLY DISTINCT (ADR-014 §3): a DISJOINT
     product-language set (canon of each `product_env` proof_check's `toolchain:`) AND a different
     design-primitive mix (`capabilities[].primitive`).

R-10's forcing function. Unlike every other ported gate, v2's `generality_parity` shipped with NO red
witness at all (`04-verification.md §2` names it debt, not a design choice) — the real
`docs/reference/parity.yml` in this tree happens to hold up honestly (every `general` claim IS
supported), so there is no standing negative fact to point at the way `benchmark` points at snipeit.
So THIS port earns one: `audit_mechanism` below is a PURE function over already-parsed specs and an
already-decided green-set (no I/O — the same shape as `v3.verify.import_boundary.analyze` and
`v3.verify.composition.check`), and the registered `sabotage_env` witness calls that REAL function
directly with two synthetic, decorative scenarios (a `general` claim covered by only one green
domain; a `general` claim where the only two green domains are NOT radically distinct) and asserts
both are caught. Exercising the real checking function, not a reimplementation of it, is the point —
a reimplementation in the test would pass even if `audit_mechanism` itself rotted.

I/O SITS AT THE EDGE: `_load_spec_for`/`_green_domains` are the only functions here that touch the
filesystem or the shared trust root; they compute the inputs `audit_mechanism` needs (which spec goes
with which domain slug, which domains are green) and hand them to the pure law. The green run below is
just that edge, once, over the real repo.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import yaml

from ...kernel.report import Verdict
from ...seed_loader import load_seed_verifier
from ...spec.loader import load_spec
from ...spec.model import Capability, FactorySpec, ProofCheck, SpecStation

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_MANIFEST_REL = "docs/reference/parity.yml"
_SABOTAGE_VAR = "V3_GENERALITY_SABOTAGE"

# ADR-014 §3, operational: two domains are "radically distinct" iff they share NO product LANGUAGE.
# Each `toolchain:` token declared on a `product_env` proof_check canonizes to a language via this
# table (verification, not generation — a string map, not an import; ADR-012 is untouched by it).
_LANG = {
    "python": "python", "pytest": "python", "unittest": "python", "mypy": "python",
    "pip": "python", "venv": "python", "poetry": "python", "ruff": "python", "tox": "python",
    "typescript": "ts", "tsc": "ts", "ts": "ts", "vitest": "ts", "jest": "ts", "vite": "ts",
    "npm": "ts", "npx": "ts", "node": "ts", "eslint": "ts", "playwright": "ts", "pnpm": "ts",
    "go": "go", "gofmt": "go", "cargo": "rust", "rust": "rust", "rustc": "rust",
    "gradle": "jvm", "maven": "jvm", "kotlin": "jvm", "swift": "swift",
    "flutter": "dart", "dart": "dart", "protoc": "proto", "qemu": "embedded",
}


def _canon_lang(token: str) -> str:
    return _LANG.get(token.lower(), token.lower())


# ── THE LAW: pure, no I/O ────────────────────────────────────────────────────
def language_set(spec: FactorySpec) -> set[str]:
    """The factory's product LANGUAGES: canon of every `product_env` proof_check's `toolchain:`
    tokens. `factory_env` checks (the substrate's own toolchain) are excluded — §3 is about the
    PRODUCT's toolchain."""
    langs: set[str] = set()
    for st in spec.stations:
        for pc in st.proof_checks:
            if pc.runs_in != "product_env":
                continue
            for tok in re.split(r"[^A-Za-z0-9]+", pc.toolchain or ""):
                if tok:
                    langs.add(_canon_lang(tok))
    return langs


def primitive_set(spec: FactorySpec) -> set[str]:
    """The mix of design PRIMITIVES (DES-x) the factory exercises."""
    return {c.primitive for c in spec.capabilities if c.primitive}


def stations_using(spec: FactorySpec, mechanism: str) -> list[str]:
    """Ids of stations whose `checks[].kind` or `builds[].action` IS the mechanism (they exercise
    it)."""
    ids: list[str] = []
    for st in spec.stations:
        kinds = {c.get("kind") for c in st.checks}
        actions = {b.get("action") for b in st.builds}
        if mechanism in kinds or mechanism in actions:
            ids.append(st.id)
    return ids


def radically_distinct(spec_a: FactorySpec, spec_b: FactorySpec) -> tuple[bool, str]:
    """ADR-014 §3: DISJOINT product language AND a different primitive mix. Both conditions."""
    la, lb = language_set(spec_a), language_set(spec_b)
    if not la or not lb:
        return False, f"no declared product toolchain in at least one ({la or set()} / {lb or set()})"
    if la & lb:
        return False, f"same product language {sorted(la & lb)} (does not exercise generality, §3)"
    pa, pb = primitive_set(spec_a), primitive_set(spec_b)
    if pa == pb:
        return False, f"same primitive mix {sorted(pa) or set()} (§3 needs DISTINCT toolchain AND primitives)"
    return True, f"languages {sorted(la)}≠{sorted(lb)} and distinct primitives"


def audit_mechanism(mechanism: str, domains: list[str], specs: dict[str, FactorySpec],
                    green: set[str]) -> tuple[bool, str]:
    """THE checked claim: pure, no I/O. `green` is the already-decided set of domains that prove the
    mechanism green (computed at the edge, by re-running the trust root — see `_green_domains`); a
    domain absent from `green` is indistinguishable here from one whose proof did not survive
    recomputation, which is the point: this function only ever sees the post-recompute fact.

    Red unless >=2 domains are green AND some pair among them is radically distinct (ADR-014 §2/§3).
    This is exactly the function the `sabotage_env` witness below calls with synthetic data."""
    known_green = [d for d in domains if d in green and d in specs]
    if len(known_green) < 2:
        return False, (f"mechanism {mechanism!r} is `general` but only {known_green or 'no'} domain(s) "
                       f"prove it green (ADR-014 §2 requires >=2)")
    for i in range(len(known_green)):
        for j in range(i + 1, len(known_green)):
            ok, why = radically_distinct(specs[known_green[i]], specs[known_green[j]])
            if ok:
                return True, f"{mechanism!r}: {known_green[i]} ⟂ {known_green[j]} ({why})"
    return False, (f"mechanism {mechanism!r} is `general` but no pair among {known_green} is radically "
                   f"distinct (false green, ADR-014 §3): toolchain/primitives do not differ")


# ── I/O AT THE EDGE ──────────────────────────────────────────────────────────
def _load_spec_for(root: Path, slug: str) -> FactorySpec | None:
    """The AUTHORITATIVE spec of a factory is the REGISTERED one (`factories/<slug>/factory.spec.yml`)
    — the one that materialized the line whose `.proof/` this gate audits."""
    for rel in (f"factories/{slug}/factory.spec.yml", f"specs/{slug}.factory.spec.yml"):
        path = root / rel
        if path.exists():
            return load_spec(path)
    return None


def _proves_green(verifier, factory_root: Path, station_ids: list[str]) -> bool:
    """True iff any of these stations has a proof that RECOMPUTES green (Lock #2: a hand-edited
    `passed: true` does not count). Does not re-run commands (that is the external CI's job) — it
    recomputes the verdict from the proof's own stored checks."""
    for sid in station_ids:
        proof = verifier.load_proof(factory_root, sid)
        if proof is None:
            continue
        if verifier.gate_recompute_ok(proof)[0]:
            return True
    return False


def _green_domains(verifier, root: Path, mechanism: str, domains: list[str],
                   specs: dict[str, FactorySpec]) -> set[str]:
    green: set[str] = set()
    for slug in domains:
        spec = specs.get(slug)
        if spec is None:
            continue
        if _proves_green(verifier, root / "factories" / slug, stations_using(spec, mechanism)):
            green.add(slug)
    return green


# ── the sabotage witness: exercises the REAL law with synthetic, decorative data ────────────────
def _synthetic_spec(slug: str, *, toolchain: str, primitive: str) -> FactorySpec:
    station = SpecStation(id="s0", name="s0",
                         proof_checks=[ProofCheck(name="t0", runs_in="product_env", toolchain=toolchain)])
    return FactorySpec(name=slug, slug=slug, maturity="prototype", produces="thing",
                       stations=[station], substrate={}, requirements=[],
                       capabilities=[Capability(id="c0", primitive=primitive)])


def _run_sabotage() -> int:
    caught: list[str] = []

    # Scenario 1 — evidence covers only ONE domain (the 2nd's proof did not survive recomputation;
    # from `audit_mechanism`'s point of view a domain outside `green` looks identical either way).
    specs_1 = {"sabotage-solo-a": _synthetic_spec("sabotage-solo-a", toolchain="pytest", primitive="DES-1"),
               "sabotage-solo-b": _synthetic_spec("sabotage-solo-b", toolchain="node", primitive="DES-2")}
    ok1, why1 = audit_mechanism("fake_mechanism_solo", ["sabotage-solo-a", "sabotage-solo-b"], specs_1,
                                green={"sabotage-solo-a"})
    if not ok1:
        caught.append(f"single-domain claim caught: {why1}")

    # Scenario 2 — both domains report green, but NEITHER language nor primitive differs (a false
    # `general`: two proofs, zero generality actually exercised).
    specs_2 = {"sabotage-same-p": _synthetic_spec("sabotage-same-p", toolchain="pytest", primitive="DES-1"),
               "sabotage-same-q": _synthetic_spec("sabotage-same-q", toolchain="pytest", primitive="DES-1")}
    ok2, why2 = audit_mechanism("fake_mechanism_same", ["sabotage-same-p", "sabotage-same-q"], specs_2,
                                green={"sabotage-same-p", "sabotage-same-q"})
    if not ok2:
        caught.append(f"non-distinct-pair claim caught: {why2}")

    if len(caught) == 2:
        return Verdict("v3-generality (SABOTAGE)", 0,
                       f"both decorative `general` claims were caught: {'; '.join(caught)}").emit()
    return Verdict("v3-generality (SABOTAGE)", 1,
                   f"GATE DECORATIVO: only {len(caught)}/2 planted decorative claims were caught — "
                   f"no teeth").emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-generality", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage()

    manifest = _ROOT / _MANIFEST_REL
    if not manifest.exists():
        return Verdict("v3-generality", 0,
                       f"N/A: no {_MANIFEST_REL} in this tree — nothing to verify (honest, SAFE-7)"
                       ).emit()

    try:
        verifier = load_seed_verifier(str(_ROOT))
    except Exception as exc:  # noqa: BLE001 — the seed always exists; defensive
        return Verdict("v3-generality", 2,
                       f"could not load the seed verifier: {type(exc).__name__}: {exc}").emit()

    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    mechs = data.get("mechanisms") or []
    general = [m for m in mechs if m.get("status") == "general"]
    proto = [m for m in mechs if m.get("status") == "prototype"]

    problems: list[str] = []
    proven: list[str] = []
    for entry in general:
        mechanism = str(entry.get("mechanism"))
        domains = [str(d) for d in (entry.get("domains") or [])]
        specs = {slug: sp for slug in domains if (sp := _load_spec_for(_ROOT, slug)) is not None}
        green = _green_domains(verifier, _ROOT, mechanism, domains, specs)
        ok, why = audit_mechanism(mechanism, domains, specs, green)
        (proven if ok else problems).append(why)

    if problems:
        return Verdict("v3-generality", 1, f"{len(problems)} generality claim(s) without support",
                       failures=tuple(problems),
                       next_action="prove it in a 2nd radically distinct domain, or return it to "
                                   "`prototype` (ADR-014 §2)").emit()

    return Verdict("v3-generality", 0,
                   f"{len(general)} `general` mechanism(s) hold two-domain parity, {len(proto)} "
                   f"`prototype` (exploration, ADR-014 §2)").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
