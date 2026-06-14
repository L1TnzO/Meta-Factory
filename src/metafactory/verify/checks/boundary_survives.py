"""boundary_survives — M4's gate: the generated/domain boundary (I-5) is NOT decorative.

Renders the REAL m04 station into a throwaway dir, then re-renders it after editing a domain
file by hand and clobbering a generated file. Exit 0 iff the domain edit SURVIVES the re-scaffold
(rendered with `skip_if_exists`) AND the generated file IS regenerated (rendered without it).

Catches the three ways the boundary can rot: dropping `skip_if_exists` from a domain build (the
edit would be eaten), adding it to a generated build (stale generated code would persist), or a
renderer that ignores the flag. All three would let a re-scaffold silently overwrite human code.

Hermetic: only a temp dir is touched. Tied to the real station + templates + renderer, so it is
a true gate, not a restatement of intent. Argv: <factory_root> <meta_root> <spec_path-rel>."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

_SENTINEL = "# BOUNDARY-SENTINEL: edición humana que DEBE sobrevivir el re-scaffold\n"
_GARBAGE = "# STALE-GARBAGE: NO debe sobrevivir (generated/ se regenera)\n"


def _boundary_dests(station, subst: dict) -> tuple[str | None, str | None]:
    """Read the station's render builds: the one with skip_if_exists is domain, the plain one
    is generated. Returns (domain_rel, generated_rel) — dests relative to the factory root."""
    from ...codegen.renderer import render_text
    domain = generated = None
    for b in station.builds:
        if b.get("action") not in ("render", "render_tree"):
            continue
        dest = render_text(b["dest"], subst)
        if b.get("skip_if_exists"):
            domain = domain or dest
        else:
            generated = generated or dest
    return domain, generated


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
    domain_rel, generated_rel = _boundary_dests(station, subst)
    if not domain_rel or not generated_rel:
        print(f"BOUNDARY ROTTEN: m04 no declara la frontera (domain={domain_rel}, generated={generated_rel})")
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
