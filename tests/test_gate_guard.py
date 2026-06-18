"""Tests del hook gate_guard (sombra del orden de la línea, ADR-010) — acota el over-match de STATE.

Antes el hook matcheaba la frase `station … --factory …` EN CUALQUIER PARTE del comando Bash —
incluido un `echo` o un `git commit -m "…"` que la nombra como TEXTO (el over-match que `STATE.md`
pedía acotar). El fix liga el match a una INVOCACIÓN real de `meta station … --factory …` en un borde
de comando. Se prueba el matcher puro (`match_station_cmd`) cargado del hook REAL — los dos lados:
prosa/texto → None (no dispara), invocación real → (id, slug) (la sombra sigue con dientes). La lógica
de bloqueo (predecesor verde + cadencia) NO cambió y la sigue garantizando el engine."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "gate_guard.py"


def _load():
    spec = importlib.util.spec_from_file_location("gate_guard_under_test", _HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


match = _load().match_station_cmd


# ── NO dispara: la frase como TEXTO / prosa (el over-match acotado) ───────────

NO_MATCH = [
    'git commit -m "ran meta station m02 --factory iot earlier"',  # mensaje de commit
    'echo "meta station m05 --factory dummy"',                     # echo citado
    "echo run meta station m05 --factory dummy first",             # echo sin comillas
    'grep -rn "station m02 --factory iot" docs/',                  # buscar la frase (sin `meta`)
    "python -c \"print('meta station m0 --factory x')\"",          # dentro de un intérprete
    "./meta ci --rederive --factory dummy",                        # otro subcomando de meta
    "meta checkpoint",                                             # sin station/--factory
    "meta station m05",                                            # station sin --factory
]


@pytest.mark.parametrize("cmd", NO_MATCH)
def test_prose_does_not_match(cmd):
    assert match(cmd) is None, f"no debería disparar (es texto/prosa, no una invocación): {cmd!r}"


# ── SÍ dispara: la invocación REAL (la sombra defense-in-depth sigue con dientes) ──

MATCH = [
    ("meta station m05 --factory dummy", ("m05", "dummy")),
    ("./meta station m04 --factory iot", ("m04", "iot")),
    ("FOO=1 meta station m02 --factory full-stack", ("m02", "full-stack")),
    ("git add -A && meta station m05 --factory dummy", ("m05", "dummy")),
    ("meta station m05 --some-flag x --factory agent-systems-factory", ("m05", "agent-systems-factory")),
]


@pytest.mark.parametrize("cmd,expected", MATCH)
def test_real_invocation_matches(cmd, expected):
    assert match(cmd) == expected, f"debería disparar (invocación real de meta station): {cmd!r}"
