"""R1 (ADR-015) — fábrica : N productos: el lifecycle de instancia de producto.

Sobre el motor REAL (sin mocks). Cuatro pruebas:
  - Fase 1: el `generate` resuelve el `via` relativo contra el CHASSIS — un generador que vive en el
    chasis escribe en un workdir (`root`) DISTINTO; el default (chassis == root) sigue funcionando.
  - Fase 2: una fábrica instancia ≥2 productos distintos desde sendos `product.yml`; cada uno con su
    PROPIA evidencia + pin; cada pin re-deriva en árbol limpio.
  - Fase 2 (isolation): borrar el `.proof/` del producto A NO toca el de B ni abre su gate.
  - Fase 3 (gate): `products_rederive` re-deriva cada instancia == su pin y un pin tampereado cae a rojo.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

from metafactory._seed import repo_root
from metafactory.engine import load_sequence
from metafactory.engine.run_context import RunContext
from metafactory.engine.runner import run_station
from metafactory.engine.sequence import Sequence
from metafactory.engine.station import Station

PY = sys.executable

# Un generador MÍNIMO que es METAFACTORY_ROOT-limpio (como iot/full-stack): lee el blueprint del spec en
# METAFACTORY_ROOT y escribe su producto bajo METAFACTORY_ROOT/build/product. No depende del cwd salvo para
# encontrarse a sí mismo (lo que R1 resuelve contra el chasis). Sin nombrar ninguna tech.
_GEN_SRC = textwrap.dedent("""
    import os, sys
    from pathlib import Path
    import yaml
    root = Path(os.environ["METAFACTORY_ROOT"]).resolve()
    bp = ((yaml.safe_load((root / "factory.spec.yml").read_text()) or {}).get("domain") or {}).get("product") or {}
    out = root / "build" / "product"
    out.mkdir(parents=True, exist_ok=True)
    (out / "PRODUCT.txt").write_text("PRODUCT name=" + str(bp.get("name", "?")) + "\\n")
    (out / "MANIFEST.txt").write_text("ok\\n")
""")


def _chassis(tmp: Path, *, product_name: str = "demo") -> Path:
    """Una fábrica chasis mínima: codegen METAFACTORY_ROOT-limpio + un factory.spec.yml con un blueprint."""
    fdir = tmp / "factory"
    (fdir / "codegen").mkdir(parents=True, exist_ok=True)
    (fdir / "codegen" / "gen.py").write_text(_GEN_SRC, encoding="utf-8")
    (fdir / "factory.spec.yml").write_text(textwrap.dedent(f"""
        factory: {{name: T, slug: t, maturity: bootstrap}}
        domain:
          produces: a product
          product: {{name: {product_name}}}
          station_sequence:
            - id: s0
              name: generate the product
              activation: always
              builds:
                - action: generate
                  dest: build/product/MANIFEST.txt
                  via: [{PY!r}, codegen/gen.py]
              checks:
                - {{name: produced, kind: artifact_contains, file: build/product/PRODUCT.txt, marker: PRODUCT}}
        substrate: {{}}
        requirements: []
    """), encoding="utf-8")
    return fdir


def _gen_station() -> Station:
    return Station.from_dict({
        "id": "s0", "name": "gen",
        "builds": [{"action": "generate", "dest": "build/product/MANIFEST.txt",
                    "via": [PY, "codegen/gen.py"]}],
        "checks": [{"name": "produced", "kind": "artifact_contains",
                    "file": "build/product/PRODUCT.txt", "marker": "PRODUCT"}],
    })


def _seq() -> Sequence:
    return Sequence([_gen_station()])


# ── Fase 1 — el generate resuelve el `via` relativo contra el chasis ───────────

def test_generate_resolves_via_against_chassis(tmp_path: Path):
    """El generador vive en el chasis; el producto se escribe en un workdir (root) DISTINTO."""
    chassis = _chassis(tmp_path, product_name="alpha")
    workdir = tmp_path / "products" / "p1"
    workdir.mkdir(parents=True)
    # el workdir lleva su PROPIO spec efectivo (METAFACTORY_ROOT) con OTRO blueprint
    (workdir / "factory.spec.yml").write_text(
        (chassis / "factory.spec.yml").read_text().replace("name: alpha", "name: beta"), encoding="utf-8")

    ctx = RunContext(root=workdir, chassis=chassis, meta_root=repo_root(), slug="t")
    run = run_station(ctx, _gen_station(), _seq(), {}, stations_dir=workdir, spec_path=None, record_active=False)

    assert run.passed and run.gate.opened
    # el producto + la evidencia viven en el WORKDIR, no en el chasis
    assert (workdir / "build" / "product" / "PRODUCT.txt").read_text().strip() == "PRODUCT name=beta"
    assert (workdir / ".proof" / "s0.json").exists()
    assert not (chassis / "build").exists()   # el chasis NO recibió el producto del workdir


def test_generate_default_product_chassis_equals_root(tmp_path: Path):
    """Default (chassis == root): byte-idéntico al 1:1 — el generador corre y produce in-place."""
    chassis = _chassis(tmp_path, product_name="alpha")
    ctx = RunContext(root=chassis, meta_root=repo_root(), slug="t")   # chassis default = root
    run = run_station(ctx, _gen_station(), _seq(), {}, stations_dir=chassis, spec_path=None, record_active=False)
    assert run.passed and run.gate.opened
    assert (chassis / "build" / "product" / "PRODUCT.txt").read_text().strip() == "PRODUCT name=alpha"
