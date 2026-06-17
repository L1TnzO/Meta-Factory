"""MAT-5 — el PRODUCTO corre contra un provider REAL y el sustrato GATEA por PROPIEDADES + umbrales (DES-7/8),
por bloqueo. Sin mocks de provider: un driver/propiedades/scorer FAKE deterministas ejercen el mecanismo (la
corrida viva REAL vs DeepSeek vive en las fábricas, no en la suite — sería no-determinista y costaría tokens).

Dos niveles:
  - el HELPER (`live_run.run`): el pin (§7) — si el output ya existe, RE-VERIFICA sin correr el driver; si no
    y `provider_env` está en el entorno, corre el driver; si no y no está, DEFERRED visible (no finge verde).
    El gate combinado (propiedades∧umbrales) pasa sobre el real y FLIPEA sobre el degradado (diente de dos
    lados); un verificador decorativo (ignora el input) cae a rojo. fail-safe 2/127/1.
  - e2e por el MOTOR real (`run_station` + seed verifier + gate): una estación `live_run` GATEA — con el pin
    presente abre; un pin corrompido SHUT; el veredicto lo escribe `seed/verifier.py` (la raíz de confianza).

El sustrato no nombra tech (ADR-012): run/properties/scorer/provider_env son DATA. La co-validación VIVA en
2 dominios (ASF LangGraph/DeepSeek ⟂ Full-Stack node/DeepSeek) vive en las fábricas (parity.yml), no acá.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from metafactory._seed import repo_root
from metafactory.engine.run_context import RunContext
from metafactory.engine.runner import run_station
from metafactory.engine.sequence import Sequence
from metafactory.engine.station import Station
from metafactory.verify.checks import live_run
from metafactory.verify.checks.registry import resolve_check

PY = sys.executable
_FAKE_KEY = "MAT5_FAKE_PROVIDER_KEY"   # un env var de juguete: su PRESENCIA simula "hay provider" (DATA)

# Un DRIVER vivo de juguete: lee METAFACTORY_LIVE_OUTPUT, escribe un draft canónico, y deja un sentinel para
# PROBAR si corrió (así verificamos que con el pin presente NO se vuelve a llamar al provider — §7).
_DRIVER = (
    "import os\n"
    "out = os.environ['METAFACTORY_LIVE_OUTPUT']\n"
    "open(os.path.join(os.path.dirname(out), 'driver_ran.sentinel'), 'w').write('ran')\n"
    "open(out, 'w', encoding='utf-8').write('alpha beta gamma — DRAFT FOR VALIDATION\\n')\n"
)
# Una PROPIEDAD honesta: el output es un DRAFT (estructural). Lee METAFACTORY_LIVE_OUTPUT; exit 0 si se sostiene.
_PROP = (
    "import os, sys\n"
    "text = open(os.environ['METAFACTORY_LIVE_OUTPUT'], encoding='utf-8').read()\n"
    "sys.exit(0 if 'DRAFT' in text else 1)\n"
)
# Una PROPIEDAD decorativa: ignora el input, siempre se sostiene (la trampa que el diente de dos lados atrapa).
_PROP_DECOR = "import sys; sys.exit(0)\n"
# Un SCORER honesto (como el de eval_gate): recall de los hechos críticos en el output.
_SCORER = (
    "import os, sys\n"
    "text = open(os.environ['METAFACTORY_EVAL_OUTPUT'], encoding='utf-8').read()\n"
    "req = ['alpha', 'beta', 'gamma']\n"
    "recall = sum(1 for r in req if r in text) / len(req)\n"
    "print(f'SCORE:critical_recall={recall}')\n"
)
_SCORER_DECOR = "print('SCORE:critical_recall=1.0')\n"

_THRESHOLDS = {"critical_recall": 0.9}
_GOOD = "alpha beta gamma — DRAFT FOR VALIDATION\n"   # prop holds, recall 1.0 -> passes
_BAD = "AUTO-APPROVED: delta epsilon\n"               # no DRAFT (prop fails) AND recall 0.0 -> flips the gate


def _sandbox(tmp_path: Path, *, driver=_DRIVER, prop=_PROP, scorer=_SCORER,
             good: str | None = _GOOD, bad: str = _BAD) -> dict:
    """A workdir with the driver/property/scorer, plus the pin (`output`) + `degraded` in a TRACKED dir
    OUTSIDE the workdir (mirrors the real design: the pin lives at the factory root, not under build/).
    `good=None` leaves the pin ABSENT (to exercise the produce / deferred paths)."""
    wd = tmp_path / "product"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "run_live.py").write_text(driver, encoding="utf-8")
    (wd / "prop.py").write_text(prop, encoding="utf-8")
    (wd / "scorer.py").write_text(scorer, encoding="utf-8")
    live = tmp_path / "live"
    live.mkdir(parents=True, exist_ok=True)
    (live / "degraded.txt").write_text(bad, encoding="utf-8")
    if good is not None:
        (live / "output.txt").write_text(good, encoding="utf-8")
    return {"wd": wd, "out": live / "output.txt", "bad": live / "degraded.txt"}


def _run(sb: dict, *, properties=None, scorer=None, thresholds=_THRESHOLDS, provider_env="",
         bootstrap=None) -> int:
    return live_run.run(
        str(sb["wd"]), [PY, "run_live.py"], str(sb["out"]), str(sb["bad"]),
        [[PY, "prop.py"]] if properties is None else properties,
        [PY, "scorer.py"] if scorer is None else scorer,
        thresholds, provider_env=provider_env, bootstrap=bootstrap)


# ── el pin (§7): re-verificación sin re-llamar al provider ──────────────────────

def test_pin_present_reverifies_without_running_the_driver(tmp_path):
    """Con el pin committeado, live_run RE-VERIFICA y NUNCA corre el driver (la corrida ci --rederive)."""
    sb = _sandbox(tmp_path)
    assert _run(sb) == 0
    assert not (sb["out"].parent / "driver_ran.sentinel").exists(), "el driver NO debió correr con pin presente"


def test_pin_absent_with_provider_runs_the_driver_then_gates(tmp_path):
    """Sin pin pero con provider presente: corre el driver (produce el output) y gatea -> verde + pin escrito."""
    sb = _sandbox(tmp_path, good=None)
    os.environ[_FAKE_KEY] = "present"
    try:
        assert _run(sb, provider_env=_FAKE_KEY) == 0
    finally:
        os.environ.pop(_FAKE_KEY, None)
    assert (sb["out"].parent / "driver_ran.sentinel").exists(), "el driver DEBIÓ correr sin pin + provider"
    assert sb["out"].exists(), "el output vivo quedó pineado"


def test_pin_absent_without_provider_is_deferred_visible(tmp_path):
    """Sin pin Y sin provider: DEFERRED visible (exit 2), no se finge verde (tier solo-CI)."""
    sb = _sandbox(tmp_path, good=None)
    os.environ.pop(_FAKE_KEY, None)
    assert _run(sb, provider_env=_FAKE_KEY) == 2


# ── el diente de dos lados: propiedades ∧ umbrales, y el degradado debe flipear ──

def test_passes_when_real_holds_and_degraded_flips(tmp_path):
    assert _run(_sandbox(tmp_path)) == 0


def test_blocks_when_a_property_fails_on_real(tmp_path):
    """Un output real que NO es un DRAFT viola la propiedad estructural -> rojo (aunque el recall pase)."""
    assert _run(_sandbox(tmp_path, good="alpha beta gamma — AUTO-APPROVED\n")) == 1


def test_blocks_when_a_threshold_fails_on_real(tmp_path):
    """Un output real DRAFT pero sin los hechos críticos cae bajo el umbral de recall -> rojo."""
    assert _run(_sandbox(tmp_path, good="only alpha here — DRAFT FOR VALIDATION\n")) == 1


def test_blocks_a_decorative_gate(tmp_path):
    """Propiedad + scorer que ignoran su input: el degradado pasa igual -> decorativo -> rojo (el crux MAT-5)."""
    assert _run(_sandbox(tmp_path, prop=_PROP_DECOR, scorer=_SCORER_DECOR)) == 1


def test_property_only_gate_passes_and_flips(tmp_path):
    """Sin scorer/umbrales: un gate SOLO de propiedades es válido (la propiedad flipea sobre el degradado)."""
    assert _run(_sandbox(tmp_path), scorer=[], thresholds={}) == 0


def test_property_only_decorative_is_red(tmp_path):
    """Sin scorer, una propiedad decorativa: el degradado pasa -> rojo (no hay diente)."""
    assert _run(_sandbox(tmp_path, prop=_PROP_DECOR), scorer=[], thresholds={}) == 1


# ── fail-safe (como el seed verifier) ───────────────────────────────────────────

def test_missing_workdir_is_red(tmp_path):
    sb = _sandbox(tmp_path)
    assert live_run.run(str(tmp_path / "nope"), [PY, "run_live.py"], str(sb["out"]), str(sb["bad"]),
                        [[PY, "prop.py"]], [PY, "scorer.py"], _THRESHOLDS) == 2


def test_missing_degraded_is_red(tmp_path):
    sb = _sandbox(tmp_path)
    sb["bad"].unlink()
    assert _run(sb) == 2


def test_no_property_and_no_thresholds_is_red(tmp_path):
    assert _run(_sandbox(tmp_path), properties=[], scorer=[], thresholds={}) == 2


def test_driver_failure_is_red(tmp_path):
    """Sin pin + provider presente, pero el driver vivo falla: rojo con su exit code (no produce el output)."""
    sb = _sandbox(tmp_path, good=None, driver="import sys; sys.exit(5)\n")
    os.environ[_FAKE_KEY] = "present"
    try:
        assert _run(sb, provider_env=_FAKE_KEY) == 5
    finally:
        os.environ.pop(_FAKE_KEY, None)


def test_scorer_cannot_launch_is_red(tmp_path):
    assert _run(_sandbox(tmp_path), scorer=["__absent_scorer_binary__"]) == 1


def test_bootstrap_failure_blocks(tmp_path):
    assert _run(_sandbox(tmp_path), bootstrap=[PY, "-c", "import sys; sys.exit(3)"]) == 3


# ── ADR-012: el registry es PASS-THROUGH, no nombra tech ────────────────────────

def test_registry_passes_live_argv_through_verbatim():
    check = {"name": "lr", "kind": "live_run", "workdir": "wd", "run": ["DRIVE", "--live"],
             "output": "live/o.json", "degraded": "live/bad.json",
             "properties": [["PROP", "--check"]], "scorer": ["SCORE"], "thresholds": {"r": 0.5},
             "provider_env": "SOME_KEY", "bootstrap": ["npm", "ci"]}
    argv = resolve_check(check, None, Station.from_dict({"id": "x"}), {})
    assert "wd" in argv
    assert json.dumps(["DRIVE", "--live"]) in argv
    assert "live/o.json" in argv and "live/bad.json" in argv
    assert json.dumps([["PROP", "--check"]]) in argv
    assert json.dumps(["SCORE"]) in argv and json.dumps({"r": 0.5}) in argv
    assert "SOME_KEY" in argv and json.dumps(["npm", "ci"]) in argv


# ── e2e por el MOTOR real: la estación gatea, veredicto por la raíz de confianza ─

def _live_station(pin: str) -> Station:
    """Una estación live_run con el pin escrito por un build (presente -> no corre driver). El driver es un
    no-op fail (probaría que NO se llama). properties+scorer son stdlib inline; output/degraded en live/."""
    return Station.from_dict({
        "id": "lr", "name": "live run",
        "builds": [
            {"action": "write", "dest": "product/prop.py", "content": _PROP},
            {"action": "write", "dest": "product/scorer.py", "content": _SCORER},
            {"action": "write", "dest": "live/output.txt", "content": pin},
            {"action": "write", "dest": "live/degraded.txt", "content": _BAD},
        ],
        "checks": [{"name": "live", "kind": "live_run", "workdir": "product",
                    "run": [PY, "-c", "import sys; sys.exit(1)"],   # nunca debe llamarse (hay pin)
                    "output": "live/output.txt", "degraded": "live/degraded.txt",
                    "properties": [[PY, "prop.py"]], "scorer": [PY, "scorer.py"],
                    "thresholds": _THRESHOLDS}],
    })


def _engine_run(tmp_path: Path, station: Station):
    ctx = RunContext(root=tmp_path, meta_root=repo_root())
    return run_station(ctx, station, Sequence([station]), {}, stations_dir=tmp_path,
                       spec_path=None, record_active=False)


def test_engine_live_station_opens_on_a_good_pin(tmp_path):
    run = _engine_run(tmp_path, _live_station(_GOOD))
    assert run.passed is True and run.gate.opened is True
    assert run.proof["writer"] == "seed/verifier.py"   # veredicto por la raíz de confianza, no el modelo


def test_engine_live_station_shuts_on_a_corrupt_pin(tmp_path):
    run = _engine_run(tmp_path, _live_station("AUTO-APPROVED: not a draft, no facts\n"))
    assert run.passed is False and run.gate.opened is False
