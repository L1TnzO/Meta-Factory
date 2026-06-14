"""Tests del hook proof_protect (Cerrojo 1 de la columna) — afina el over-block de la sesión 2.

Antes el hook deniega un Bash si `.proof/` aparece EN CUALQUIER PARTE junto a un token de escritura
EN CUALQUIER PARTE — un OR laxo que disparaba con redirecciones de solo lectura (`2>&1`,
`2>/dev/null`) y con `.proof/` mencionado como argumento o como texto (un mensaje de commit con
flechas `->`). El fix liga cada operador de escritura a un TARGET dentro de `.proof/`.

Se prueba el hook REAL como subproceso (el contrato que el harness ejecuta: JSON por stdin -> exit
code), no una reimplementación. exit 2 = deny; exit 0 = allow."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "proof_protect.py"


def _run(payload: dict) -> int:
    proc = subprocess.run([sys.executable, str(_HOOK)],
                          input=json.dumps(payload), capture_output=True, text=True)
    return proc.returncode


def _bash(cmd: str) -> int:
    return _run({"tool_name": "Bash", "tool_input": {"command": cmd}})


# ── DENY: escrituras reales a .proof/ (Cerrojo 1 sigue con dientes) ───────────

DENY_BASH = [
    "echo x > .proof/s00.json",                                   # redirección directa
    "echo x >> .proof/ledger.json",                              # append
    "echo x > factories/dummy/.proof/s00.json",                  # redirección a .proof/ anidado
    'echo x > "$D/.proof/s00.json"',                            # target citado/variable
    "tee .proof/s00.json",                                       # tee
    "tee -a .proof/s00.json",                                    # tee -a
    "cp /tmp/fake.json .proof/s00.json",                         # cp destino
    "mv /tmp/fake.json .proof/s00.json",                         # mv destino
    "sed -i s/a/b/ .proof/s00.json",                             # sed -i in-place
    "ln -s /tmp/fake .proof/s00.json",                           # symlink
    "python -c \"import json; json.dump({}, open('.proof/s00.json','w'))\"",  # intérprete
]


@pytest.mark.parametrize("cmd", DENY_BASH)
def test_bash_write_to_proof_is_denied(cmd):
    assert _bash(cmd) == 2, f"debería DENEGAR (escribe en .proof/): {cmd!r}"


def test_write_tool_to_proof_is_denied():
    assert _run({"tool_name": "Write",
                 "tool_input": {"file_path": "factories/dummy/.proof/s00.json"}}) == 2


def test_edit_tool_to_proof_is_denied():
    assert _run({"tool_name": "Edit",
                 "tool_input": {"file_path": ".proof/ledger.json"}}) == 2


# ── ALLOW: lecturas y menciones (los falsos positivos que motivaron el fix) ───

ALLOW_BASH = [
    "ls -1 .proof/ 2>&1",                                        # redirección de SOLO LECTURA
    "cat .proof/s00.json 2>/dev/null",                          # leer un proof
    "grep foo .proof/ledger.json",                              # grep sobre .proof/
    "ls .proof/ && echo ok > /tmp/x",                          # escribe FUERA de .proof/
    'git commit -m "fix .proof/ over-block -> rojo"',          # mención + flecha en mensaje
    "diff .claude/hooks/proof_protect.py /tmp/old && echo same > /tmp/r",  # .proof/ ausente
    "echo 'ver .proof/s00.json' > /tmp/notes.txt",             # .proof/ como texto, target /tmp
    # Regresión del 1er intento de este fix: un verbo de escritura en PROSA multilínea (un mensaje
    # de commit que nombra cp/mv/tee y, en OTRA línea, .proof/) NO debe alcanzar ese .proof/.
    "git commit -m 'uso cp, mv y tee aca\n y en otra linea reviso .proof/ledger.json'",
]


@pytest.mark.parametrize("cmd", ALLOW_BASH)
def test_bash_readonly_or_mention_is_allowed(cmd):
    assert _bash(cmd) == 0, f"debería PERMITIR (no escribe en .proof/): {cmd!r}"


def test_write_tool_to_normal_path_is_allowed():
    assert _run({"tool_name": "Write",
                 "tool_input": {"file_path": "src/metafactory/foo.py"}}) == 0


def test_malformed_stdin_does_not_block():
    """Entrada ilegible -> no bloquea (fail-open SOLO para input corrupto; el verifier es la
    autoridad real, no este hook de conveniencia)."""
    proc = subprocess.run([sys.executable, str(_HOOK)],
                          input="not json", capture_output=True, text=True)
    assert proc.returncode == 0
