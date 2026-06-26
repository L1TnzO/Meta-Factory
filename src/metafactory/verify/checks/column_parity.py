"""column_parity (ADR-018) — la columna heredada de la fábrica es una PROYECCIÓN fiel de su único source
canónico, no una copia mantenida a mano. Diente dos-lados, espejo de `ci --rederive == pin`.

NO re-implementa la proyección (eso podría divergir, ADR-005 §4): re-materializa la columna de la fábrica
con el RENDERER REAL de M1 (`apply_builds` de los builds de `m01`: `copy_seed` + `render_tree(harness)` +
`render(external_ci por-fábrica)`) en un dir scratch, y compara byte a byte contra la columna in-tree. Por
construcción cubre exactamente lo que M1 produce —`seed/*`, `.claude/hooks/*`, `.claude/settings.json`— y
NADA de lo que M7 emite desde el spec (`.claude/agents|commands|skills`), que no es la columna.

  Drift / ausencia = ROJO. Re-materializar la columna (`meta station m00→m01 --factory <f>`) lo pone verde.
  Diente RED: un drift plantado en un par sintético DEBE marcarse; si el comparador no muerde, el check FALLA.

La columna es la frontera de seguridad (NO spec-driven, ADR-018 §4): este gate no la DECLARA en DATA, sólo
prueba que la proyección determinista del sustrato se sostiene. Single-source intacto (H1): la ley vive en
`seed/`, el meta DELEGA, la fábrica HEREDA por proyección checkeada.

Argv: <meta_root>. Exit 0 = PASS (toda fábrica fiel + diente vivo), 1 = FAIL (drift listado)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from metafactory.codegen.renderer import apply_builds
from metafactory.engine.run_context import RunContext
from metafactory.engine.sequence import load_sequence
from metafactory.spec import load_spec

_STATIONS_REL = "src/metafactory/stations"
_COLUMN_STATION = "m01"   # «Seed & columna anti-sello»: el único que materializa la columna heredada.


def _materialize_column(meta_root: Path, slug: str, subst: dict, scratch: Path) -> None:
    """Re-materializa la columna de M1 en `scratch` con el renderer real (la misma proyección que la
    generación → no puede divergir). Los builds de m01 sólo escriben bajo `scratch` (seed/ + .claude/),
    no tocan el verifier ni `.proof/`."""
    seq = load_sequence(meta_root / _STATIONS_REL)
    m01 = next(s for s in seq.stations if s.id == _COLUMN_STATION)
    ctx = RunContext(root=scratch, meta_root=meta_root, slug=slug)
    apply_builds(ctx, m01, subst)


def _tree_drift(canonical: Path, intree: Path) -> list[str]:
    """Cada archivo de la proyección canónica DEBE existir byte-idéntico in-tree. Salta `__pycache__`.
    Recorre sólo la canónica (lo que M1 produce), así nunca marca lo que M7 emite. [] = fiel."""
    problems: list[str] = []
    for cf in sorted(canonical.rglob("*")):
        if cf.is_dir() or "__pycache__" in cf.parts:
            continue
        rel = cf.relative_to(canonical)
        tf = intree / rel
        if not tf.is_file():
            problems.append(f"{rel.as_posix()}: ausente in-tree (la proyección no se materializó)")
        elif tf.read_bytes() != cf.read_bytes():
            problems.append(f"{rel.as_posix()}: drift vs proyección canónica (tampering o columna rancia)")
    return problems


def parity_problems(meta_root: Path, factory_root: Path) -> list[str]:
    """Drift entre la columna in-tree de la fábrica y su proyección canónica re-materializada. [] = fiel."""
    spec_path = factory_root / "factory.spec.yml"
    if not spec_path.is_file():
        return [f"factory.spec.yml ausente — no puedo re-derivar la columna de {factory_root.name}"]
    try:
        subst = load_spec(spec_path).subst
    except Exception as e:  # noqa: BLE001 — un spec roto es un problema reportable, no un crash
        return [f"spec ilegible ({e})"]
    with tempfile.TemporaryDirectory() as td:
        scratch = Path(td)
        _materialize_column(meta_root, factory_root.name, subst, scratch)
        return _tree_drift(scratch, factory_root)


def _tooth_bites() -> bool:
    """Diente RED: el comparador DEBE marcar un drift plantado (no decorativo)."""
    with tempfile.TemporaryDirectory() as td:
        canon = Path(td) / "canon"
        intree = Path(td) / "intree"
        (canon / "seed").mkdir(parents=True)
        (intree / "seed").mkdir(parents=True)
        (canon / "seed" / "law.py").write_text("CANON\n", encoding="utf-8")
        (intree / "seed" / "law.py").write_text("TAMPERED\n", encoding="utf-8")  # drift plantado
        return any("law.py" in p for p in _tree_drift(canon, intree))


def main(argv: list[str]) -> int:
    meta_root = Path(argv[0]).resolve() if argv else Path.cwd()
    fdir = meta_root / "factories"
    factories = (sorted(p for p in fdir.iterdir() if (p / "factory.spec.yml").is_file())
                 if fdir.exists() else [])

    drift: dict[str, list[str]] = {}
    for froot in factories:
        probs = parity_problems(meta_root, froot)
        if probs:
            drift[froot.name] = probs

    if drift:
        print("COLUMN_PARITY ROJO — la columna de una fábrica driftó de su proyección canónica (ADR-018):")
        for slug, probs in sorted(drift.items()):
            for p in probs:
                print(f"  ✗ {slug}: {p}")
        print("  -> re-materializá la columna con `meta station m00 --factory <f>` y luego `m01 --factory <f>`.")
        return 1

    if not _tooth_bites():
        print("COLUMN_PARITY DECORATIVO — el comparador no marcó un drift plantado → sin dientes")
        return 1

    nf = len(factories)
    print(f"OK column_parity: {nf} fábrica(s), columna ≡ proyección canónica de M1 "
          f"(seed + hooks + settings + external_ci); diente RED vivo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
