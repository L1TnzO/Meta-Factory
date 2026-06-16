"""mcp_tools — the generated MCP EXPOSES the declared tools and the orchestrator INVOKES them (E2, DES-6).

The substrate ORCHESTRATES, it does NOT verify (the doctrine of `generate`/`product_env`/`infra_up`,
ADR-013/012): this helper runs a DECLARED `prove` command — the prover IS the orchestrator: it speaks the
MCP protocol (JSON-RPC over stdio) to the GENERATED server, runs `tools/list`, calls the declared tools,
and prints the discovered tool names as `TOOLS:<csv>`. All of `prove` is raw argv passed in as DATA; the
substrate NAMES NO TECH — a full MCP SDK or a stdlib JSON-RPC impl are the same machine, other data.

This makes `machinery.mcp` executable instead of descriptive, the MCP analogue of M8's façade-trap: a
`tools.json` manifest on disk does NOT pass — the server must actually answer `tools/list` and `tools/call`.
The gate has access to BOTH the DECLARED tool set (passed as DATA from the spec) and what the live server
discovers, so it cross-checks two facts:

  1. EXPOSES — every declared tool name appears in the live `tools/list` (the prover's `TOOLS:` line). A
     tool the spec promises but the server does not serve is red (the manifest lied).
  2. INVOKES — the prover exits 0, which it does iff every declared tool was CALLABLE and returned its
     expected result. A tool that lists but errors on call (or returns the wrong thing) is red.

An EMBEDDED, two-sided negative (like command_runs / infra_up) keeps the gate from being decorative:
re-running the prover asked to call a tool name that CANNOT exist (a fresh uuid) must FAIL. If calling a
phantom tool "succeeds", the prover is not really reaching the server's dispatch — the gate is prose.

Exit 0 iff the declared tools are exposed AND invokable AND a phantom call fails. It never raises past the
verdict (fail-safe): a workdir that does not exist is exit 2, a prover that cannot launch is exit 127. The
COLUMN (the seed verifier observing THIS process's exit code) is the sole árbitro.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

#: env keys that would let the MCP server borrow the Meta-Factory's toolchain (DES-9, same as product_env).
_LEAKY_ENV = ("PYTHONPATH", "VIRTUAL_ENV", "PYTHONHOME")


def _mcp_env() -> dict:
    env = dict(os.environ)
    for leak in _LEAKY_ENV:
        env.pop(leak, None)
    return env


def _run(argv: list, cwd: Path, env: dict) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(list(argv), cwd=str(cwd), env=env, capture_output=True, text=True)
    except OSError as exc:
        print(f"mcp_tools: no pudo lanzar {argv[0] if argv else '?'}: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return None


def _discovered(stdout: str) -> set[str]:
    """Parse the prover's `TOOLS:<csv>` line — the tool names the LIVE server reported via tools/list."""
    for line in stdout.splitlines():
        if line.startswith("TOOLS:"):
            return {t.strip() for t in line[len("TOOLS:"):].split(",") if t.strip()}
    return set()


def run(workdir: str, prove: list, expected: list) -> int:
    wd = Path(workdir).resolve()
    if not wd.is_dir():
        print(f"mcp_tools: workdir {wd} does not exist (nothing built to expose tools)", file=sys.stderr)
        return 2
    if not prove:
        print("mcp_tools: no `prove` argv (the orchestrator must call the MCP)", file=sys.stderr)
        return 2
    env = _mcp_env()

    # 1. EXPOSES + INVOKES: run the prover (the orchestrator) against the generated server.
    proc = _run(prove, wd, env)
    if proc is None:
        return 127
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        print(f"mcp_tools: el prover (orquestador) salió {proc.returncode} — una tool declarada no es "
              f"invocable", file=sys.stderr)
        return proc.returncode
    discovered = _discovered(proc.stdout)
    missing = [t for t in expected if t not in discovered]
    if missing:
        print(f"mcp_tools: tool(s) declarada(s) NO expuesta(s) por el server vivo: {missing} "
              f"(tools/list = {sorted(discovered)})", file=sys.stderr)
        return 1

    # 2. NEGATIVO embebido (no decorativo): llamar a una tool que NO puede existir debe FALLAR. Si "pasa",
    #    el prover no alcanza el dispatch del server (sería prosa).
    phantom = f"__absent__{uuid.uuid4().hex}"
    neg = _run([*prove, phantom], wd, env)
    if neg is not None and neg.returncode == 0:
        print(f"mcp_tools: GATE DECORATIVO — llamar a la tool inexistente {phantom!r} NO falló "
              f"(el prover no invoca de verdad el server)", file=sys.stderr)
        return 1

    print(f"OK mcp_tools: el MCP generado expone las tools declaradas {sorted(expected)} y el orquestador "
          f"las invoca (exit 0); llamar a una tool inexistente cae a rojo (no decorativo)")
    return 0


def main(argv: list[str]) -> int:
    # argv: <workdir> <prove-json> <expected-tools-json>. prove arrives JSON-encoded so arbitrary argv
    # survive transport unambiguously; expected is the DECLARED tool contract from the spec (free DATA).
    if len(argv) != 3:
        print("usage: mcp_tools <workdir> <prove-json> <expected-tools-json>", file=sys.stderr)
        return 2
    return run(argv[0], json.loads(argv[1]), json.loads(argv[2]))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
