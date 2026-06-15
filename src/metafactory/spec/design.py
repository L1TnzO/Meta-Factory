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
