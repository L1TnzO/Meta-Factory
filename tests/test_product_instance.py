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


# ── Fase 2 — el lifecycle de instancia: 1 fábrica → N productos, pin propio ─────

def _instantiate(chassis: Path, name: str, product_name: str):
    """Crear products/<name>/product.yml, materializar, correr la línea y pinear. Devuelve (root, ok)."""
    import yaml

    from metafactory.cli import _pin_from_proofs, _run_product_line, ensure_product_instance
    product_root = chassis / "products" / name
    product_root.mkdir(parents=True, exist_ok=True)
    (product_root / "product.yml").write_text(yaml.safe_dump({"name": product_name}), encoding="utf-8")
    ensure_product_instance(chassis, product_root, repo_root(), "t")
    rc, _ = _run_product_line(product_root, repo_root(), "t", record_active=False, chassis=chassis)
    pin_ok, _ = _pin_from_proofs(product_root, repo_root(), "t", chassis=chassis)
    return product_root, (rc == 0 and pin_ok)


def test_one_factory_n_products_each_with_own_pin(tmp_path: Path):
    """Una fábrica instancia DOS productos distintos; cada uno con su propia evidencia + pin que re-deriva."""
    from metafactory.cli import rederive_pinned
    chassis = _chassis(tmp_path, product_name="alpha")   # el demo/default
    a, ok_a = _instantiate(chassis, "pa", "aaa")
    b, ok_b = _instantiate(chassis, "pb", "bbb")
    assert ok_a and ok_b

    # productos DISTINTOS (el blueprint varió el output) y evidencia/pin SEPARADOS
    assert (a / "build" / "product" / "PRODUCT.txt").read_text().strip() == "PRODUCT name=aaa"
    assert (b / "build" / "product" / "PRODUCT.txt").read_text().strip() == "PRODUCT name=bbb"
    assert (a / ".proof").resolve() != (b / ".proof").resolve()
    assert (a / "pinned_verdict.json").is_file() and (b / "pinned_verdict.json").is_file()

    # cada pin re-deriva en árbol limpio (wipe .proof+build, reconstruir desde product.yml)
    ok, mism, _, has = rederive_pinned(a, repo_root(), "t", record_active=False, chassis=chassis)
    assert has and ok and not mism
    ok, mism, _, has = rederive_pinned(b, repo_root(), "t", record_active=False, chassis=chassis)
    assert has and ok and not mism


def test_products_are_isolated(tmp_path: Path):
    """Borrar el `.proof/` del producto A NO toca el de B ni abre/altera su gate (raíces separadas)."""
    import shutil

    from metafactory.cli import rederive_pinned
    chassis = _chassis(tmp_path, product_name="alpha")
    a, _ = _instantiate(chassis, "pa", "aaa")
    b, _ = _instantiate(chassis, "pb", "bbb")

    shutil.rmtree(a / ".proof")                     # demoler la evidencia de A
    assert not (a / ".proof").exists()
    assert (b / ".proof" / "s0.json").exists()      # la de B intacta

    # B re-deriva verde con total independencia del estado de A
    ok, mism, _, has = rederive_pinned(b, repo_root(), "t", record_active=False, chassis=chassis)
    assert has and ok and not mism


# ── Fase 3 — el gate `products_rederive`: cada instancia == su pin, con diente ──

def test_products_rederive_gate(tmp_path: Path):
    """El gate re-deriva CADA instancia == su pin en clon limpio; un pin tampereado lo pone rojo."""
    import json

    from metafactory.verify.checks import products_rederive as PR
    chassis = _chassis(tmp_path, product_name="alpha")
    _instantiate(chassis, "pa", "aaa")
    _instantiate(chassis, "pb", "bbb")

    # verde: dos instancias re-derivan == su pin
    assert PR.main([str(chassis), str(repo_root())]) == 0

    # rojo: un pin corrupto en una instancia bloquea (desvío re-derivado != pineado)
    pin = chassis / "products" / "pa" / "pinned_verdict.json"
    data = json.loads(pin.read_text())
    sid = next(iter(data)); data[sid] = "deadbeef" + str(data[sid])[8:]
    pin.write_text(json.dumps(data))
    assert PR.main([str(chassis), str(repo_root())]) == 1


def test_products_rederive_na_without_instances(tmp_path: Path):
    """Sin instancias (products/) el gate reporta N/A honesto (no finge verde) — opt-out como boundary."""
    from metafactory.verify.checks import products_rederive as PR
    chassis = _chassis(tmp_path, product_name="alpha")
    assert PR.main([str(chassis), str(repo_root())]) == 0   # N/A → exit 0 (no aplica)
