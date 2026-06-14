"""Unit tests for metafactory.verify.checks.rtm_rederive (M5 gate, criterio 2).

rtm_rederive.main() verifica que el RTM (Requirements Traceability Matrix) se RE-DERIVA de
`.proof/`, no de prosa: un requisito está SATISFIED iff toda estación en su `satisfied_by`
tiene un proof con la gate recomputable-OK. La prueba NO es decorativa: en una copia HERMÉTICA
del `.proof/`, corromper el proof de una estación que satisface un requisito SATISFIED debe
tirarlo a UNSATISFIED. Si no cambia, el RTM sería prosa (rojo).

Estrategia (espejo de test_boundary.py): el happy path invoca main() contra el dummy-fábrica
real (el artefacto existe en el repo). Los tests herméticos construyen una mini-fábrica en
tmp_path — copiando el seed/ real para que load_seed_verifier() funcione — y verifican las
ramas de error sin depender del estado del disco."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from metafactory.verify.checks.rtm_rederive import main

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FACTORY_ROOT = _REPO_ROOT / "factories" / "dummy"
_SPEC_PATH = "factory.spec.yml"

# El verifier del seed es la única autoridad del formato de proof/sha (lock #2). Lo cargamos
# vía el bridge oficial, igual que la máquina, para fabricar proofs válidos a mano.
sys.path.insert(0, str(_REPO_ROOT / "src"))
from metafactory._seed import load_seed_verifier  # noqa: E402

_VERIFIER = load_seed_verifier(str(_REPO_ROOT))


# ── happy path contra el dummy real ──────────────────────────────────────────

class TestRtmRederiveHappyPath:
    def test_main_passes_against_real_dummy(self):
        """El check devuelve 0 contra el dummy-fábrica real (el path de producción):
        REQ-F-001 es SATISFIED por s00, corromper s00 lo tira a UNSATISFIED, ledger consistente."""
        rc = main([str(_FACTORY_ROOT), str(_REPO_ROOT), _SPEC_PATH])
        assert rc == 0, "rtm_rederive debería pasar contra el dummy-fábrica real"

    def test_main_returns_int(self):
        """main() devuelve siempre un int (exit code)."""
        rc = main([str(_FACTORY_ROOT), str(_REPO_ROOT), _SPEC_PATH])
        assert isinstance(rc, int)


# ── casos de error / argumentos incorrectos ──────────────────────────────────

class TestRtmRederiveErrors:
    def test_main_no_args_returns_2(self):
        """Sin argumentos debe devolver 2 (usage error)."""
        rc = main([])
        assert rc == 2

    def test_main_one_arg_returns_2(self):
        """Con sólo factory_root, sin meta_root, también devuelve 2 (usage error)."""
        rc = main([str(_FACTORY_ROOT)])
        assert rc == 2


# ── comportamiento hermético: ramas del RTM en mini-fábrica aislada ───────────

class TestRtmRederiveHermetic:
    """Construye una mini-fábrica hermética en tmp_path (con el seed real copiado) para
    aislar el check de cualquier estado residual del repo y ejercer sus ramas de salida."""

    def _make_meta_root(self, tmp_path: Path) -> Path:
        """Arma un meta_root mínimo: sólo necesita el seed/ real para load_seed_verifier()."""
        meta = tmp_path / "meta"
        meta.mkdir()
        import shutil
        shutil.copytree(_REPO_ROOT / "seed", meta / "seed")
        return meta

    def _make_factory_root(self, tmp_path: Path, satisfied_by: list[str]) -> Path:
        """Arma un factory_root mínimo con una spec válida parseable. `satisfied_by` define
        a qué estaciones mapea el único requisito funcional (REQ-F-001)."""
        factory = tmp_path / "factory"
        factory.mkdir()
        sb = "[" + ", ".join(satisfied_by) + "]"
        (factory / "factory.spec.yml").write_text(
            "factory:\n  name: Test\n  slug: test\n  maturity: bootstrap\n"
            "domain:\n  produces: test\n  target_framework: {name: none, provider_agnostic: true}\n"
            "  product_capabilities: []\n"
            "  station_sequence: []\n"
            "  provision_modes: []\n"
            "  proof_check_types: []\n"
            "  product:\n    product_module: product\n    greet_fn: greet\n    marker: TEST_OK\n"
            "factory_substrate:\n  anti_rubber_stamp_column: false\n  verdict_bus: {max_lines: 10}\n"
            "  generated_domain_boundary: false\n  memory_schema: adr021\n"
            "  rtm: {required: false}\n  two_verifier_ci: {rederive: false, pinned_verdict: false}\n"
            "  placement_law: false\n  context_budget: {claude_md_max_lines: 120}\n"
            "requirements:\n  functional:\n"
            "    - id: REQ-F-001\n      statement: \"x\"\n      satisfied_by: " + sb + "\n",
            encoding="utf-8",
        )
        return factory

    def _write_valid_proof(self, factory: Path, sid: str) -> str:
        """Escribe a mano un proof VÁLIDO (gate recomputable-OK) para `sid` y devuelve su sha."""
        checks = [{"name": "x", "cmd": ["true"], "exit": 0}]
        sha = _VERIFIER.compute_proof_sha(sid, checks)
        proof = {"station": sid, "passed": True, "checks": checks,
                 "proof_sha": sha, "writer": "test"}
        proof_dir = factory / ".proof"
        proof_dir.mkdir(parents=True, exist_ok=True)
        (proof_dir / f"{sid}.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
        return sha

    def test_rtm_vacio_when_no_satisfied_by(self, tmp_path):
        """Spec con el requisito mapeando satisfied_by: [] → "RTM VACÍO" → exit 1."""
        meta = self._make_meta_root(tmp_path)
        factory = self._make_factory_root(tmp_path, satisfied_by=[])
        rc = main([str(factory), str(meta), "factory.spec.yml"])
        assert rc == 1, "sin ningún requisito con satisfied_by, el RTM está vacío"

    def test_rtm_sin_cobertura_when_proof_dir_empty(self, tmp_path):
        """Spec mapea REQ-F-001 a [s00] pero `.proof/` no tiene s00.json (fábrica no construida)
        → ningún requisito SATISFIED → "RTM SIN COBERTURA" → exit 1."""
        meta = self._make_meta_root(tmp_path)
        factory = self._make_factory_root(tmp_path, satisfied_by=["s00"])
        # No escribimos ningún proof: el .proof/ está vacío (ni siquiera existe).
        rc = main([str(factory), str(meta), "factory.spec.yml"])
        assert rc == 1, "sin proofs, ningún requisito está SATISFIED (RTM sin cobertura)"

    def test_evidencia_inconsistente_when_ledger_sha_mismatch(self, tmp_path):
        """Proof VÁLIDO a mano para s00 (REQ-F-001 SATISFIED, corromper lo tira a UNSATISFIED),
        pero un ledger.json cuyo gate s00 tiene un proof_sha que NO recomputa igual
        → "EVIDENCIA INCONSISTENTE" → exit 1."""
        meta = self._make_meta_root(tmp_path)
        factory = self._make_factory_root(tmp_path, satisfied_by=["s00"])
        self._write_valid_proof(factory, "s00")
        # Ledger inconsistente: el proof_sha citado no coincide con el recomputado del proof.
        ledger = factory / ".proof" / "ledger.json"
        ledger.write_text(
            json.dumps({"gates": [
                {"station": "s00", "proof_sha": "deadbeef" * 8, "opened_at": "2026-01-01T00:00Z"}
            ]}, indent=2) + "\n",
            encoding="utf-8",
        )
        rc = main([str(factory), str(meta), "factory.spec.yml"])
        assert rc == 1, "un gate del ledger con proof_sha que no recomputa es evidencia inconsistente"
