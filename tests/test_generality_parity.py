"""MAT-0 — `generality_parity` (ADR-014): ningún mecanismo de sustrato se promueve (`status: general`)
probado en un solo dominio. Teeth deterministas por bloqueo, sobre fixtures herméticos (una fábrica
Python ⟂ una TypeScript) — el caso verde de un `general` no existe aún entre las fábricas reales (dummy +
ASF son ambos Python), así que se construye acá. Cubre las dos caras de la compuerta:

  verde: `general` con 2 dominios radicalmente distintos (lenguaje disjunto Y primitivas distintas).
  rojo : <2 dominios verdes · mismo lenguaje (§3) · misma mezcla de primitivas (§3) · proof rancio.
  verde: `prototype` en un dominio (exploración permitida, §2) NO gatea.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from metafactory._seed import load_seed_verifier, repo_root
from metafactory.verify.checks import generality_parity as gp

_V = load_seed_verifier()  # el seed REAL: recompone proofs (compute_proof_sha / recompute_passed)


def _meta(tmp_path: Path) -> Path:
    """Un meta_root hermético: `seed/` symlinkeado al real (para que el check recompute) + carpetas."""
    (tmp_path / "seed").symlink_to(repo_root() / "seed", target_is_directory=True)
    (tmp_path / "docs" / "reference").mkdir(parents=True)
    return tmp_path


def _factory(meta: Path, slug: str, *, toolchain: str, primitive: str,
             mechanism: str = "product_env", station: str = "s0") -> None:
    """Escribe una fábrica fixture: una estación que EJERCE `mechanism`, su toolchain de producto y su
    primitiva — más un proof VERDE (recompone) para esa estación."""
    spec = {
        "factory": {"slug": slug},
        "domain": {
            "capabilities": [{"id": "c1", "primitive": primitive}],
            "station_sequence": [{
                "id": station,
                "checks": [{"name": "m", "kind": mechanism}],
                "proof_checks": [{"name": "m", "runs_in": "product_env", "toolchain": toolchain}],
            }],
        },
    }
    fdir = meta / "factories" / slug
    fdir.mkdir(parents=True, exist_ok=True)
    (fdir / "factory.spec.yml").write_text(yaml.safe_dump(spec), encoding="utf-8")
    _green_proof(fdir, station)


def _green_proof(fdir: Path, station: str) -> None:
    checks = [{"name": "m", "exit": 0}]
    proof = {"station": station, "passed": True, "checks": checks,
             "proof_sha": _V.compute_proof_sha(station, checks)}
    (fdir / ".proof").mkdir(parents=True, exist_ok=True)
    (fdir / ".proof" / f"{station}.json").write_text(json.dumps(proof), encoding="utf-8")


def _manifest(meta: Path, mechanism: str, status: str, domains: list[str]) -> Path:
    path = meta / "docs" / "reference" / "parity.yml"
    path.write_text(yaml.safe_dump({"mechanisms": [
        {"mechanism": mechanism, "status": status, "domains": domains}]}), encoding="utf-8")
    return path


def _run(meta: Path, manifest: Path) -> int:
    return gp.main([str(meta), str(manifest)])


# ── VERDE: el caso legítimo (lo único que abre la compuerta) ──────────────────────────────────────────
def test_general_two_distinct_domains_is_green(tmp_path):
    meta = _meta(tmp_path)
    _factory(meta, "fpy", toolchain="pytest", primitive="DES-6")        # python
    _factory(meta, "fts", toolchain="vitest", primitive="DES-2")        # typescript
    m = _manifest(meta, "product_env", "general", ["fpy", "fts"])
    assert _run(meta, m) == 0


# ── ROJO: las cuatro maneras de NO sostener un claim `general` ────────────────────────────────────────
def test_general_missing_second_proof_is_red(tmp_path):
    meta = _meta(tmp_path)
    _factory(meta, "fpy", toolchain="pytest", primitive="DES-6")
    _factory(meta, "fts", toolchain="vitest", primitive="DES-2")
    (meta / "factories" / "fts" / ".proof" / "s0.json").unlink()        # borrar la proof del 2º dominio
    m = _manifest(meta, "product_env", "general", ["fpy", "fts"])
    assert _run(meta, m) == 1


def test_general_same_language_is_red(tmp_path):
    """Dos fábricas Python (pytest ↔ unittest) NO son dos dominios: mismo lenguaje (§3) -> falso verde."""
    meta = _meta(tmp_path)
    _factory(meta, "fa", toolchain="pytest", primitive="DES-6")
    _factory(meta, "fb", toolchain="unittest", primitive="DES-2")       # distinto runner, MISMO lenguaje
    m = _manifest(meta, "product_env", "general", ["fa", "fb"])
    assert _run(meta, m) == 1


def test_general_same_primitive_mix_is_red(tmp_path):
    """Lenguajes distintos pero MISMA mezcla de primitivas: §3 exige toolchain Y primitivas distintas."""
    meta = _meta(tmp_path)
    _factory(meta, "fpy", toolchain="pytest", primitive="DES-6")
    _factory(meta, "fts", toolchain="vitest", primitive="DES-6")        # misma primitiva
    m = _manifest(meta, "product_env", "general", ["fpy", "fts"])
    assert _run(meta, m) == 1


def test_general_stale_green_is_red(tmp_path):
    """Un `passed:true` rancio/editado (proof_sha no recompone) NO cuenta como verde -> <2 -> rojo."""
    meta = _meta(tmp_path)
    _factory(meta, "fpy", toolchain="pytest", primitive="DES-6")
    _factory(meta, "fts", toolchain="vitest", primitive="DES-2")
    proof = json.loads((meta / "factories" / "fts" / ".proof" / "s0.json").read_text())
    proof["proof_sha"] = "0" * 64                                       # sha mentido -> recompute falla
    (meta / "factories" / "fts" / ".proof" / "s0.json").write_text(json.dumps(proof), encoding="utf-8")
    m = _manifest(meta, "product_env", "general", ["fpy", "fts"])
    assert _run(meta, m) == 1


# ── VERDE: la exploración no gatea (ADR-014 §2) ───────────────────────────────────────────────────────
def test_prototype_single_domain_is_green(tmp_path):
    meta = _meta(tmp_path)
    _factory(meta, "fpy", toolchain="pytest", primitive="DES-6")
    m = _manifest(meta, "product_env", "prototype", ["fpy"])           # un dominio, prototype -> OK
    assert _run(meta, m) == 0


def test_no_manifest_is_na_green(tmp_path):
    meta = _meta(tmp_path)
    assert gp.main([str(meta), str(meta / "docs" / "reference" / "nope.yml")]) == 0


# ── el manifiesto REAL del repo está honesto (todo prototype) -> verde ────────────────────────────────
def test_real_manifest_is_honest_green():
    assert gp.main([str(repo_root())]) == 0
