#!/usr/bin/env python3
"""product_env — run a proof in the PRODUCT's OWN toolchain (DES-8, C3), isolated from the factory.

PORTED (V3-INC7-MIGRATE-DUMMY) — the body behind the argv INC-4 resolved.

The substrate ORCHESTRATES, it does NOT verify (the same doctrine as the `generate` slot, ADR-013):
this helper runs a DECLARED `bootstrap` (deps/env setup — uv venv ↔ npm ci ↔ python -m venv) and then a
DECLARED proof `cmd` (pytest ↔ tsc ↔ vitest ↔ node), both as raw argv passed in as DATA. The substrate
NAMES NO TECH (ADR-012); a new product toolchain is new data (another argv), never an engine branch.

Two non-negotiables make this an honest realization of `runs_in: product_env` and not a façade:

  1. cwd == the product `workdir` (where the product's manifest/lockfile/sources live), so the proof runs
     where the product's toolchain expects to run.
  2. the env is SCRUBBED of the platform's PYTHONPATH / VIRTUAL_ENV / PYTHONHOME before the product
     commands run. This is the heart of DES-8/SAFE-2: the product cannot "pass" by borrowing the
     factory's interpreter or its installed packages — it must stand on its OWN toolchain.

Exit 0 iff bootstrap AND proof both exit 0. It never raises past the verdict (fail-safe, like the seed
verifier): a workdir that does not exist is exit 2 (nothing was built to prove), a command that cannot even
launch is exit 127. The COLUMN (the seed verifier observing THIS process's exit code) is the sole árbitro.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

#: env keys that would leak the platform's toolchain into the product's proof (DES-8).
_LEAKY_ENV = ("PYTHONPATH", "VIRTUAL_ENV", "PYTHONHOME")


def _product_env() -> dict:
    """The factory's environment MINUS anything that would let the product borrow the factory's
    toolchain. Nothing tech-specific is added — the product's own bootstrap installs what it needs."""
    env = dict(os.environ)
    for leak in _LEAKY_ENV:
        env.pop(leak, None)
    return env


def run(workdir: str, bootstrap: list, cmd: list) -> int:
    wd = Path(workdir).resolve()
    if not wd.is_dir():
        print(f"product_env: workdir {wd} does not exist (nothing built to prove)", file=sys.stderr)
        return 2
    env = _product_env()
    for phase, argv in (("bootstrap", bootstrap), ("proof", cmd)):
        if not argv:
            continue  # bootstrap is optional (a product with no deps to install)
        try:
            proc = subprocess.run(list(argv), cwd=str(wd), env=env, capture_output=True, text=True)
        except OSError as exc:
            print(f"product_env: {phase} could not launch ({argv[0] if argv else '?'}): "
                  f"{type(exc).__name__}: {exc}", file=sys.stderr)
            return 127  # cannot launch == not exit-0 (fail-safe, never raise past the verdict)
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        if proc.returncode != 0:
            print(f"product_env: {phase} exited {proc.returncode}", file=sys.stderr)
            return proc.returncode
    return 0


def main(argv: list[str]) -> int:
    # argv: <workdir> <bootstrap-json-argv> <proof-json-argv>. bootstrap/cmd arrive JSON-encoded so
    # arbitrary argv (spaces, flags) survive transport unambiguously; they are free DATA the plan chose.
    if len(argv) != 3:
        print("usage: product_env <workdir> <bootstrap-json> <cmd-json>", file=sys.stderr)
        return 2
    return run(argv[0], json.loads(argv[1]), json.loads(argv[2]))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
