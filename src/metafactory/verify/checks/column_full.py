"""column_full — D1's blocking-proof for the WIRED column (not just the seed library).

`column_selftest` proves the inherited SEED rejects a tampered verdict (Lock #2 as a library function).
`column_full` proves the inherited HOOKS — the column an agent actually operates under — BLOCK a tampered
verdict when invoked exactly as the harness invokes them: `commit_guard.py` (Cerrojo 2, on `git commit`)
and `stop_proof.py` (Cerrojo 3, at turn close). The proof is two-sided and therefore non-decorative:

  - a TAMPERED active proof (passed=true pegado a mano over a failing check) → BOTH hooks exit 2, and
  - a CLEAN-GREEN active proof → BOTH hooks exit 0 (a column that always-allowed fails the first, one
    that always-blocked fails the second).

Runs against a hermetic CLONE of the factory (so the real `.proof/` is never touched), mirroring
agent_shadow/clean_runner. The hooks are self-contained (they load the clone's `seed/verifier.py`), so
this also exercises that the factory defends itself ALONE — without the Meta-Factory's hooks or substrate.

Exit 0 iff the wired column blocks the lie and passes the truth. Exit 1 means the column is hollow.
Argv: <factory_root>."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_HOOKS = ("commit_guard.py", "stop_proof.py")
_COMMIT_EVENT = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}})
_STOP_EVENT = json.dumps({})


def _load_inherited_verifier(root: Path):
    path = root / "seed" / "verifier.py"
    spec = importlib.util.spec_from_file_location("inherited_verifier_colfull", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _set_active(root: Path, station: str) -> None:
    (root / ".proof").mkdir(parents=True, exist_ok=True)
    (root / ".proof" / "active.json").write_text(
        json.dumps({"station": station, "root": str(root)}) + "\n", encoding="utf-8")


def _run_hook(root: Path, hook: str, event: str) -> int:
    return subprocess.run(
        [sys.executable, str(root / ".claude" / "hooks" / hook)],
        input=event, capture_output=True, text=True,
    ).returncode


def _green_proof(v, root: Path, station: str) -> None:
    v.verify_station(station, [{"name": "ok", "cmd": [sys.executable, "-c", "import sys; sys.exit(0)"]}], root)
    _set_active(root, station)


def _tampered_proof(v, root: Path, station: str) -> None:
    """Un proof GENUINAMENTE rojo con `passed` pegado a mano en true (los exits guardados siguen
    diciendo la verdad → el recompute del seed lo atrapa). El fraude clásico de sello de goma."""
    v.verify_station(station, [{"name": "must_fail", "cmd": [sys.executable, "-c", "import sys; sys.exit(1)"]}], root)
    p = root / ".proof" / f"{station}.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["passed"] = True
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    _set_active(root, station)


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: column_full <factory_root>", file=sys.stderr)
        return 2
    src = Path(argv[0]).resolve()
    tmp = Path(tempfile.mkdtemp(prefix="column_full_"))
    try:
        clone = tmp / "f"
        shutil.copytree(src, clone, ignore=shutil.ignore_patterns(".proof", "build", "__pycache__"))

        missing = [h for h in _HOOKS if not (clone / ".claude" / "hooks" / h).exists()]
        if missing:
            print(f"COLUMN HOLLOW: faltan hooks heredados: {', '.join(missing)}")
            return 1

        v = _load_inherited_verifier(clone)

        # 1. TAMPER: ambos hooks deben BLOQUEAR (exit 2).
        _tampered_proof(v, clone, "colfull")
        rc_c = _run_hook(clone, "commit_guard.py", _COMMIT_EVENT)
        rc_s = _run_hook(clone, "stop_proof.py", _STOP_EVENT)
        if rc_c != 2:
            print(f"COLUMN HOLLOW: commit_guard NO bloqueó un veredicto tampereado (exit {rc_c})")
            return 1
        if rc_s != 2:
            print(f"COLUMN HOLLOW: stop_proof NO bloqueó un veredicto tampereado (exit {rc_s})")
            return 1

        # 2. VERDE-LIMPIO: ambos hooks deben PERMITIR (exit 0) — una columna que siempre bloquea
        #    fallaría acá (la prueba es de dos lados, por eso no es decorativa).
        shutil.rmtree(clone / ".proof", ignore_errors=True)
        _green_proof(v, clone, "colfull")
        gc = _run_hook(clone, "commit_guard.py", _COMMIT_EVENT)
        gs = _run_hook(clone, "stop_proof.py", _STOP_EVENT)
        if gc != 0 or gs != 0:
            print(f"COLUMN SOBRE-BLOQUEA: verde-limpio rechazado (commit_guard {gc}, stop_proof {gs})")
            return 1

        print("OK columna heredada COMPLETA: commit_guard (C2) + stop_proof (C3) bloquean el veredicto "
              "tampereado y pasan el verde-limpio, autocontenidos en el seed de la fábrica")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
