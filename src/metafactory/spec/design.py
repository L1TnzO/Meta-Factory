"""design — the DESIGN-TIME coverage check (B1). Separate from validator.py (the M0 gate) so the
M0 gate stays catalog-independent (A1's decoupling) and the ADR-012 guard over validator.py is untouched.

`design_coverage` is the teeth of the design-primitives skill: given a spec that declares which DES
primitives the domain requires (`domain.required_primitives`), it confirms the design is HONEST and
COMPLETE — every required primitive exists in the catalog and is provided by a capability that declares
a tech. A required primitive with no tech is an INCOMPLETE design (the skill must finish its job).

B1 leaves this CALLABLE (CLI `spec.cli design-coverage`); B2 wires it into the M0 gate (refuse incomplete
designs). It names no technology — only DES ids — so ADR-012 holds. Shape only, like the rest of the spine.
"""
from __future__ import annotations

from .model import FactorySpec
from .primitives import catalog_ids


def design_coverage(spec: FactorySpec, known: set[str] | None = None) -> list[str]:
    """Return problems as `field: reason`. Empty == the design covers every required primitive.

    known: the catalog ids to check membership against (defaults to the shipped catalog).
    """
    if known is None:
        known = catalog_ids()
    p: list[str] = []

    # (a) every required primitive is a real catalog id
    for prim in spec.required_primitives:
        if prim not in known:
            p.append(f"required_primitives: {prim!r} is not in the design-primitive catalog")

    # (b) every capability that names a primitive names a real one, and (track) which carry a tech
    covered: dict[str, bool] = {}
    for c in spec.capabilities:
        if not c.primitive:
            continue
        if c.primitive not in known:
            p.append(f"capabilities[{c.id or '?'}].primitive {c.primitive!r} is not in the catalog")
        covered[c.primitive] = covered.get(c.primitive, False) or bool(c.tech)

    # (c) every required primitive is provided by a capability that declares a tech
    for prim in spec.required_primitives:
        if not covered.get(prim, False):
            p.append(f"design incomplete: required primitive {prim} has no capability declaring a tech")

    return p


def design_review(spec: FactorySpec, known: set[str] | None = None) -> list[str]:
    """The multi-phase SDD design gate (B2): is this a COMPLETE design blueprint? M0 wires this in.

    ACTIVE only when the spec declares `domain.required_primitives` — that declaration is the spec
    asserting it went through the design-primitive flow (B1). A bootstrap/proxy spec that declares
    none is NOT a design blueprint, so the gate is a no-op: the live dummy/ASF lines stay green, and
    nothing forces a stub to pretend it was designed. It is not a hole — to BUILD (phase C) you need a
    design-complete blueprint, and a real domain always requires primitives.

    Two phases (spec & tareas are already gated by `validate`, A1):
      plan      — every required primitive is real and provided by a capability that declares a tech
                  (`design_coverage`, B1: the PLAN chose the tech, ADR-012).
      criterios — every requirement cites a verifier. A requirement with no `verified_by` is an
                  unfinished design (SDD's verification-criteria phase, SAFE-4/7). That the named
                  verifier is REAL (no phantom) is grammar_v2's job (`validate`); the two run together
                  in M0, so a complete blueprint has every requirement citing a real proof_check.

    Problems are phase-labeled (`plan:` / `criterios:`) so the output reads as the blueprint review.
    Names no technology — only DES ids and proof_check names — so the ADR-012 guard holds. Empty ==
    a complete blueprint (or: not a design-flow spec, nothing to review)."""
    if not spec.required_primitives:
        return []
    problems = [f"plan: {p}" for p in design_coverage(spec, known)]
    for r in spec.requirements:
        if not r.verified_by:
            problems.append(
                f"criterios: {r.id} has no verifier "
                "(a requirement must cite the proof_check that verifies it, SAFE-4/7)")
    return problems
