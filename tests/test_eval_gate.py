"""MAT-4 — un scorer declarado MIDE el output del producto y el sustrato BLOQUEA bajo umbral (DES-7), por bloqueo.

Dos niveles, sin mocks:
  - el HELPER (`eval_gate.run`) corre el scorer con el output REAL (debe pasar los umbrales) y con el
    DEGRADADO (debe flipear el gate): pasa con un scorer que LEE su input y discrimina; bloquea un scorer
    DECORATIVO (ignora el output -> el degradado pasa igual, la falla de la legacy); bloquea bajo umbral;
    bloquea si el scorer omite una métrica gateada. El VERDICT (la comparación contra el umbral) vive en el
    sustrato, no en el scorer: el scorer mide, el sustrato juzga.
  - e2e por el MOTOR real (`run_station` + seed verifier + gate): una estación `eval_gate` GATEA — verde abre,
    un scorer decorativo SHUT, y el veredicto lo escribe `seed/verifier.py` (la raíz de confianza).

El sustrato no nombra tech: scorer/output/degraded/thresholds son DATA (ADR-012) — RAGAS, un pass-rate o un
scorer stdlib son la misma máquina con otra data. La co-validación 2-dominios (ASF faithfulness/recall +
Full-Stack pass-rate) vive en las fábricas (parity.yml), no acá.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from metafactory._seed import repo_root
from metafactory.engine.run_context import RunContext
from metafactory.engine.runner import run_station
from metafactory.engine.sequence import Sequence
from metafactory.engine.station import Station
from metafactory.verify.checks import eval_gate
from metafactory.verify.checks.registry import resolve_check

PY = sys.executable

# An HONEST scorer: it READS the output the substrate hands it (METAFACTORY_EVAL_OUTPUT) and measures two
# metrics from the content — critical_recall = fraction of required facts present; faithfulness = 0 if a
# forbidden hallucination token appears, else 1. It cannot pass without reading its input.
_SCORER = (
    "import os, sys\n"
    "path = os.environ['METAFACTORY_EVAL_OUTPUT']\n"
    "try:\n"
    "    text = open(path, encoding='utf-8').read()\n"
    "except OSError:\n"
    "    print('SCORE:faithfulness=0.0'); print('SCORE:critical_recall=0.0'); sys.exit(0)\n"
    "required = ['alpha', 'beta', 'gamma']\n"
    "recall = sum(1 for r in required if r in text) / len(required)\n"
    "faithful = 0.0 if 'HALLUCINATION' in text else 1.0\n"
    "print(f'SCORE:faithfulness={faithful}')\n"
    "print(f'SCORE:critical_recall={recall}')\n"
)
# A DECORATIVE scorer: ignores the output entirely and prints a perfect score always (the legacy's stub).
_DECORATIVE = "print('SCORE:faithfulness=1.0'); print('SCORE:critical_recall=1.0')\n"
# A PARTIAL scorer: only reports faithfulness, silently dropping a gated metric.
_PARTIAL = "print('SCORE:faithfulness=1.0')\n"

_THRESHOLDS = {"faithfulness": 0.7, "critical_recall": 0.9}
_GOOD = "alpha beta gamma — the grounded answer\n"   # recall 1.0, faithful 1.0 -> passes
_BAD = "HALLUCINATION: delta epsilon\n"               # recall 0.0, faithful 0.0 -> flips the gate


def _sandbox(tmp_path: Path, scorer_src: str = _SCORER, good: str = _GOOD, bad: str = _BAD) -> Path:
    """Materialize a scorer + a real (good) output + a degraded (bad) output in a workdir."""
    wd = tmp_path / "eval"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "scorer.py").write_text(scorer_src, encoding="utf-8")
    (wd / "output.txt").write_text(good, encoding="utf-8")
    (wd / "degraded.txt").write_text(bad, encoding="utf-8")
    return wd


_DEFAULT = object()


def _run(wd: Path, scorer=None, output="output.txt", degraded="degraded.txt",
         thresholds=_DEFAULT, bootstrap=None) -> int:
    return eval_gate.run(str(wd), scorer or [PY, "scorer.py"], output, degraded,
                         _THRESHOLDS if thresholds is _DEFAULT else thresholds, bootstrap=bootstrap)


# ── the trust chain at the helper level ─────────────────────────────────────────

def test_passes_when_real_output_clears_and_degraded_flips(tmp_path):
    """The honest scorer reads the real output (>= thresholds) and the degraded output (< threshold) -> 0."""
    assert _run(_sandbox(tmp_path)) == 0


def test_blocks_a_decorative_scorer(tmp_path):
    """A scorer that ignores its input scores the WRONG answer green too -> decorative -> red (MAT-4 crux)."""
    assert _run(_sandbox(tmp_path, scorer_src=_DECORATIVE)) == 1


def test_blocks_when_real_output_below_threshold(tmp_path):
    """A real output missing the critical facts scores below recall threshold -> the gate bit -> red."""
    wd = _sandbox(tmp_path, good="alpha is the only grounded fact here\n")  # recall 1/3 < 0.9
    assert _run(wd) == 1


def test_blocks_when_real_output_hallucinates(tmp_path):
    """A real output with the forbidden token tanks faithfulness -> red (faithfulness gate)."""
    wd = _sandbox(tmp_path, good="alpha beta gamma but also HALLUCINATION\n")
    assert _run(wd) == 1


def test_blocks_when_scorer_omits_a_gated_metric(tmp_path):
    """A scorer that does not report a declared threshold metric cannot silently drop a gate -> red."""
    assert _run(_sandbox(tmp_path, scorer_src=_PARTIAL)) == 1


def test_missing_workdir_is_red(tmp_path):
    assert _run(tmp_path / "nope") == 2


def test_missing_output_is_red(tmp_path):
    wd = _sandbox(tmp_path)
    (wd / "output.txt").unlink()
    assert _run(wd) == 2


def test_missing_degraded_is_red(tmp_path):
    """Without a degraded output there is no two-sided tooth — the gate would be unfalsifiable -> red."""
    wd = _sandbox(tmp_path)
    (wd / "degraded.txt").unlink()
    assert _run(wd) == 2


def test_empty_thresholds_is_red(tmp_path):
    assert _run(_sandbox(tmp_path), thresholds={}) == 2


def test_scorer_cannot_launch_is_red(tmp_path):
    assert _run(_sandbox(tmp_path), scorer=["__absent_scorer_binary__"]) == 127


def test_bootstrap_runs_before_scoring_and_can_materialize_output(tmp_path):
    """The optional bootstrap runs ONCE in the workdir (scrubbed env) before the scorer — it may produce the
    output the scorer then reads (the composition product_env ⊕ eval_gate)."""
    wd = tmp_path / "eval"
    wd.mkdir()
    (wd / "scorer.py").write_text(_SCORER, encoding="utf-8")
    (wd / "degraded.txt").write_text(_BAD, encoding="utf-8")
    boot = [PY, "-c", "open('output.txt','w').write('alpha beta gamma\\n')"]
    assert eval_gate.run(str(wd), [PY, "scorer.py"], "output.txt", "degraded.txt",
                         _THRESHOLDS, bootstrap=boot) == 0


def test_bootstrap_failure_blocks_before_scoring(tmp_path):
    rc = eval_gate.run(str(_sandbox(tmp_path)), [PY, "scorer.py"], "output.txt", "degraded.txt",
                       _THRESHOLDS, bootstrap=[PY, "-c", "import sys; sys.exit(3)"])
    assert rc == 3


# ── ADR-012: the registry is a PASS-THROUGH, it names no tech ───────────────────

def test_registry_passes_eval_argv_through_verbatim():
    """The registry resolves `eval_gate` WITHOUT recognizing any tech: scorer/output/degraded/thresholds
    ride through as data. A new scorer (RAGAS, a pass-rate counter) is new data, not an engine branch."""
    check = {"name": "e", "kind": "eval_gate", "workdir": "wd",
             "scorer": ["TECH_SCORE", "--gold", "g.json"], "output": "out.json", "degraded": "bad.json",
             "thresholds": {"faithfulness": 0.7}, "bootstrap": ["npm", "ci"]}
    argv = resolve_check(check, None, Station.from_dict({"id": "x"}), {})
    assert "wd" in argv
    assert json.dumps(["TECH_SCORE", "--gold", "g.json"]) in argv
    assert "out.json" in argv and "bad.json" in argv
    assert json.dumps({"faithfulness": 0.7}) in argv
    assert json.dumps(["npm", "ci"]) in argv


# ── e2e through the REAL engine: the station gates, verdict by the trust root ────

def _eval_station(scorer_src: str) -> Station:
    return Station.from_dict({
        "id": "ev", "name": "eval gate",
        "builds": [
            {"action": "write", "dest": "eval/scorer.py", "content": scorer_src},
            {"action": "write", "dest": "eval/output.txt", "content": _GOOD},
            {"action": "write", "dest": "eval/degraded.txt", "content": _BAD},
        ],
        "checks": [{"name": "eval", "kind": "eval_gate", "workdir": "eval",
                    "scorer": [PY, "scorer.py"], "output": "output.txt", "degraded": "degraded.txt",
                    "thresholds": _THRESHOLDS}],
    })


def _engine_run(tmp_path: Path, station: Station):
    ctx = RunContext(root=tmp_path, meta_root=repo_root())
    return run_station(ctx, station, Sequence([station]), {}, stations_dir=tmp_path,
                       spec_path=None, record_active=False)


def test_engine_eval_station_opens_when_scorer_discriminates(tmp_path):
    run = _engine_run(tmp_path, _eval_station(_SCORER))
    assert run.passed is True and run.gate.opened is True
    assert run.proof["writer"] == "seed/verifier.py"   # verdict by the trust root, not the model


def test_engine_eval_station_shuts_on_a_decorative_scorer(tmp_path):
    run = _engine_run(tmp_path, _eval_station(_DECORATIVE))
    assert run.passed is False and run.gate.opened is False
