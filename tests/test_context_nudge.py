"""Tests del hook context_nudge (INC-3 CONTEXT-LEAN-TEETH) — el nudge de higiene de contexto.

Advisory, NUNCA bloquea. Se prueba el núcleo puro `build_nudges` (decisión + mutación de estado) y el
estimador de tokens del transcript, los dos lados de cada diente:
  (a·C15) re-lectura: 1ª y 2ª Read NO nudgean; la 3ª SÍ (una sola vez, idempotente); Edit/Grep no cuentan.
  (e·B10) umbral: bajo el umbral NO nudgea; sobre el umbral SÍ (una sola vez).
El hook completo se invoca por stdin para confirmar exit 0 + additionalContext bien formado."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "context_nudge.py"


def _load():
    spec = importlib.util.spec_from_file_location("context_nudge_under_test", _HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()
build_nudges = mod.build_nudges
THRESH = mod.CONTEXT_NUDGE_THRESHOLD
AT = mod.REREAD_NUDGE_AT


# ── (a) anti-reread: 3rd Read of the SAME file trips exactly once ──────────────
def test_reread_nudges_only_on_third_read():
    state: dict = {}
    f = "src/metafactory/cli.py"
    # 1st and 2nd read: normal work, no nudge.
    assert build_nudges("Read", f, 0, state) == []
    assert build_nudges("Read", f, 0, state) == []
    # 3rd read: nudge, and it names the file.
    third = build_nudges("Read", f, 0, state)
    assert len(third) == 1 and f in third[0]
    # 4th read: idempotent — no repeat spam.
    assert build_nudges("Read", f, 0, state) == []
    assert state["reads"][f] == 4


def test_reread_is_per_file():
    state: dict = {}
    a, b = "a.py", "b.py"
    for _ in range(AT):
        build_nudges("Read", a, 0, state)
    # b has only been read twice → still silent while a already nudged.
    build_nudges("Read", b, 0, state)
    assert build_nudges("Read", b, 0, state) == []
    assert a in state["reread_nudged"] and b not in state["reread_nudged"]


def test_edit_and_grep_do_not_count_as_reread():
    state: dict = {}
    f = "x.py"
    for _ in range(5):
        assert build_nudges("Edit", f, 0, state) == []
        assert build_nudges("Grep", f, 0, state) == []
    assert state.get("reads", {}) == {}  # re-EDITING is normal; only Read is thrashing


# ── (e) context threshold: trips once when the estimate crosses the ceiling ────
def test_context_threshold_nudges_once_over_and_never_under():
    state: dict = {}
    # under threshold → silent
    assert build_nudges("Bash", "", THRESH - 1, state) == []
    assert not state.get("context_nudged")
    # over threshold → one nudge mentioning checkpoint
    over = build_nudges("Bash", "", THRESH + 5000, state)
    assert len(over) == 1 and "checkpoint" in over[0].lower()
    # subsequent calls over threshold → idempotent
    assert build_nudges("Bash", "", THRESH + 9000, state) == []


def test_est_transcript_tokens_small_file_is_zero(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text('{"message":{"content":"hi"}}\n', encoding="utf-8")
    assert mod._est_transcript_tokens(str(p)) == 0  # under the parse floor → 0 with certainty
    assert mod._est_transcript_tokens("") == 0
    assert mod._est_transcript_tokens("/nonexistent/x.jsonl") == 0


# ── full hook via stdin: never blocks, emits well-formed additionalContext ─────
def test_hook_process_exits_zero_and_emits_context():
    f = "seed/delegation.py"
    session = "test-ctx-nudge-proc"
    # isolate from any prior run's persisted state (idempotence would otherwise suppress the nudge)
    state_file = Path(mod._state_path(mod._repo_root(), session))
    state_file.unlink(missing_ok=True)
    proc = None
    for _ in range(AT):
        payload = {"session_id": session, "tool_name": "Read",
                   "tool_input": {"file_path": f}, "transcript_path": ""}
        proc = subprocess.run([sys.executable, str(_HOOK)], input=json.dumps(payload),
                              capture_output=True, text=True)
        assert proc.returncode == 0  # advisory: never blocks
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert f in out["hookSpecificOutput"]["additionalContext"]
