"""boundary_survives — M4's gate: the generated/domain boundary (I-5) is NOT decorative.

The boundary is the factory's DATA (`domain.product.boundary_*`, flowed through `subst`), not a
substrate template — the substrate names no language (ADR-012). Where a factory declares it, this
runs the REAL m04 station (`emit_boundary`) into a throwaway dir, then re-runs it after editing the
domain file by hand and clobbering the generated file. Exit 0 iff the domain edit SURVIVES the
re-scaffold (emitted with `skip_if_exists`) AND the generated file IS regenerated (emitted without).

Catches the three ways the boundary can rot: dropping `skip_if_exists` from the domain emit (the
edit would be eaten), adding it to the generated emit (stale generated code would persist), or a
renderer that ignores the flag. All three would let a re-scaffold silently overwrite human code.

A factory whose product is 100% generated (no human/generated split) declares no boundary: the gate
returns N/A (exit 0) HONESTLY — reported, not faked, not red.

Hermetic: only a temp dir is touched. Tied to the real station + spec DATA + renderer, so it is a
true gate, not a restatement of intent. Argv: <factory_root> <meta_root> <spec_path-rel>."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

_SENTINEL = "# BOUNDARY-SENTINEL: edición humana que DEBE sobrevivir el re-scaffold\n"
_GARBAGE = "# STALE-GARBAGE: NO debe sobrevivir (generated/ se regenera)\n"


def _boundary_dests(subst: dict) -> tuple[str | None, str | None]:
    """The boundary dests the factory declares as DATA (`domain.product.boundary_*_dest`, flowed
    through `subst`): the domain stub (human-owned) and the generated runner (chassis-owned).
    Returns (domain_rel, generated_rel) — either may be None: a factory whose product is fully
    generated declares neither, and the gate reports that honestly (N/A), not red and not faked."""
    from ...codegen.renderer import render_text
    dd = str(subst.get("boundary_domain_dest", "")).strip()
    gd = str(subst.get("boundary_generated_dest", "")).strip()
    return (render_text(dd, subst) if dd else None,
            render_text(gd, subst) if gd else None)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: boundary_survives <factory_root> <meta_root> [spec_path]", file=sys.stderr)
        return 2
    factory_root = Path(argv[0]).resolve()
    meta_root = Path(argv[1]).resolve()
    spec_rel = argv[2] if len(argv) > 2 else "factory.spec.yml"

    from ...codegen.renderer import apply_builds
    from ...engine import RunContext, load_sequence
    from ...spec.loader import load_spec

    spec = load_spec(factory_root / spec_rel)
    subst = dict(spec.subst)
    subst.update({"slug": spec.slug, "factory_root": str(factory_root),
                  "meta_root": str(meta_root), "spec_path": spec_rel})

    station = load_sequence(meta_root / "src" / "metafactory" / "stations").get("m04")
    if station is None:
        print("BOUNDARY ROTTEN: la meta-estación m04 no existe")
        return 1
    domain_rel, generated_rel = _boundary_dests(subst)
    if not domain_rel and not generated_rel:
        print("OK frontera N/A: la fábrica no declara split humano/generado (producto 100% generado)")
        return 0
    if not domain_rel or not generated_rel:
        print(f"BOUNDARY ROTTEN: declaración PARCIAL de la frontera (domain={domain_rel}, generated={generated_rel}) "
              f"— declarala entera o ninguna")
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="boundary_survives_"))
    try:
        ctx = RunContext(root=tmp, meta_root=meta_root, slug=spec.slug)
        apply_builds(ctx, station, subst)                 # primer scaffold
        domain_f, generated_f = tmp / domain_rel, tmp / generated_rel
        if not domain_f.exists() or not generated_f.exists():
            print(f"BOUNDARY ROTTEN: m04 no renderizó {domain_rel} y/o {generated_rel}")
            return 1
        domain_f.write_text(domain_f.read_text() + _SENTINEL, encoding="utf-8")   # edición humana
        gen_rendered = generated_f.read_text(encoding="utf-8")
        generated_f.write_text(_GARBAGE, encoding="utf-8")                        # clobber generated
        apply_builds(ctx, station, subst)                 # re-scaffold

        if _SENTINEL not in domain_f.read_text(encoding="utf-8"):
            print(f"BOUNDARY ROTTEN: el re-scaffold COMIÓ la edición de dominio en {domain_rel} "
                  f"(¿falta skip_if_exists?)")
            return 1
        if generated_f.read_text(encoding="utf-8") != gen_rendered:
            print(f"BOUNDARY ROTTEN: {generated_rel} NO se regeneró (¿tiene skip_if_exists de más?)")
            return 1
        print(f"OK frontera viva: {domain_rel} sobrevive el re-scaffold; {generated_rel} se regenera")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
