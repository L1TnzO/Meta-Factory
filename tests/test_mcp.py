"""E2 — el MCP generado EXPONE las tools declaradas y el orquestador las INVOCA (DES-6), por bloqueo.

Dos niveles, sin mocks (server + prover MCP stdlib REALES: JSON-RPC 2.0 sobre stdio con
initialize/tools/list/tools/call):
  - el HELPER (`mcp_tools.run`) corre el prover (el orquestador) contra el server generado: pasa cuando
    las tools declaradas están en `tools/list` y son invocables; bloquea si una tool declarada NO se expone;
    bloquea si una tool listada NO es invocable; y bloquea un server PROMISCUO (responde a cualquier tool)
    vía el negativo embebido (llamar a una tool inexistente debe fallar).
  - e2e por el MOTOR real (`run_station` + seed verifier + gate): una estación `mcp_tools` GATEA — verde
    abre, un server roto SHUT. Y el MISMO kind prueba otro toolset (principio #6).

El sustrato no nombra tech: `prove`/`tools` son DATA (ADR-012) — un SDK MCP o este impl stdlib son la misma
máquina con otra data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from metafactory._seed import repo_root
from metafactory.codegen.renderer import apply_builds
from metafactory.engine.run_context import RunContext
from metafactory.engine.runner import run_station
from metafactory.engine.sequence import Sequence
from metafactory.engine.station import Station
from metafactory.spec.loader import load_spec
from metafactory.spec.model import FactorySpec, Machinery
from metafactory.spec.validator import validate_grammar_v2
from metafactory.verify.checks import mcp_tools
from metafactory.verify.checks.registry import resolve_check

PY = sys.executable

# A minimal but GENUINE MCP server: JSON-RPC 2.0 over stdio, initialize / tools/list / tools/call. The
# TOOLS map is the body the spec would emit; an unknown tool returns a proper JSON-RPC error (-32602).
_SERVER = '''\
import json, sys
TOOLS = {
    "greet": ("devuelve el marcador invariante", lambda a: "DUMMY_OK"),
    "echo":  ("devuelve el argumento text",       lambda a: str(a.get("text", ""))),
}
def handle(req):
    m = req.get("method"); i = req.get("id")
    if m == "initialize":
        return {"jsonrpc":"2.0","id":i,"result":{"protocolVersion":"2024-11-05",
                "capabilities":{"tools":{}},"serverInfo":{"name":"dummy-mcp","version":"0"}}}
    if m == "tools/list":
        tools = [{"name":n,"description":d,"inputSchema":{"type":"object"}} for n,(d,_) in TOOLS.items()]
        return {"jsonrpc":"2.0","id":i,"result":{"tools":tools}}
    if m == "tools/call":
        p = req.get("params") or {}; name = p.get("name"); args = p.get("arguments") or {}
        if name not in TOOLS:
            return {"jsonrpc":"2.0","id":i,"error":{"code":-32602,"message":"unknown tool"}}
        return {"jsonrpc":"2.0","id":i,"result":{"content":[{"type":"text","text":TOOLS[name][1](args)}]}}
    if isinstance(m, str) and m.startswith("notifications/"):
        return None
    return {"jsonrpc":"2.0","id":i,"error":{"code":-32601,"message":"method not found"}}
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try: req = json.loads(line)
    except Exception: continue
    resp = handle(req)
    if resp is not None:
        sys.stdout.write(json.dumps(resp) + "\\n"); sys.stdout.flush()
'''

# The prover IS the orchestrator: it speaks MCP to `server.py`. No arg -> list (print TOOLS:<csv>) + call
# every discovered tool, exit 0 iff none errors. One arg -> call ONLY that tool, exit 0 iff no error (the
# phantom-probe the gate's embedded negative uses). 100% protocol; no factory-specific knowledge.
_PROVER = '''\
import json, subprocess, sys
def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    proc = subprocess.Popen([sys.executable, "server.py"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, text=True)
    nid = [0]
    def request(method, params=None):
        nid[0] += 1
        msg = {"jsonrpc":"2.0","id":nid[0],"method":method}
        if params is not None: msg["params"] = params
        proc.stdin.write(json.dumps(msg) + "\\n"); proc.stdin.flush()
        return json.loads(proc.stdout.readline())
    def notify(method):
        proc.stdin.write(json.dumps({"jsonrpc":"2.0","method":method}) + "\\n"); proc.stdin.flush()
    try:
        request("initialize", {"protocolVersion":"2024-11-05","capabilities":{}})
        notify("notifications/initialized")
        if target is not None:
            r = request("tools/call", {"name": target, "arguments": {}})
            sys.exit(3 if "error" in r else 0)
        names = [t["name"] for t in request("tools/list", {})["result"]["tools"]]
        print("TOOLS:" + ",".join(names))
        for n in names:
            if "error" in request("tools/call", {"name": n, "arguments": {"text":"x"}}):
                sys.exit(4)
        sys.exit(0)
    finally:
        try: proc.stdin.close()
        except Exception: pass
        try: proc.wait(timeout=3)
        except Exception: proc.kill()
main()
'''

# A server that LISTS greet but ERRORS on every call -> "exposes" but is NOT invokable (the prover exits 4).
_SERVER_UNCALLABLE = _SERVER.replace(
    'return {"jsonrpc":"2.0","id":i,"result":{"content":[{"type":"text","text":TOOLS[name][1](args)}]}}',
    'return {"jsonrpc":"2.0","id":i,"error":{"code":-32000,"message":"tool broken"}}')

# A PROMISCUOUS server that returns success for ANY tool name (never errors, no KeyError) -> a phantom call
# "succeeds" -> the embedded negative must catch it (the prover does not reach a dispatch that rejects fakes).
_SERVER_PROMISCUOUS = _SERVER.replace(
    '        if name not in TOOLS:\n'
    '            return {"jsonrpc":"2.0","id":i,"error":{"code":-32602,"message":"unknown tool"}}\n'
    '        return {"jsonrpc":"2.0","id":i,"result":{"content":[{"type":"text","text":TOOLS[name][1](args)}]}}',
    '        return {"jsonrpc":"2.0","id":i,"result":{"content":[{"type":"text","text":"ok"}]}}')
assert _SERVER_PROMISCUOUS != _SERVER, "el server promiscuo no se construyó (replace no matcheó)"


def _mcp_sandbox(tmp_path: Path, server_src: str = _SERVER) -> tuple[Path, list]:
    wd = tmp_path / "mcp"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "server.py").write_text(server_src, encoding="utf-8")
    (wd / "prove.py").write_text(_PROVER, encoding="utf-8")
    return wd, [PY, "prove.py"]


# ── the helper: the orchestrator speaks MCP to the generated server ─────────────

def test_passes_when_tools_exposed_and_invokable(tmp_path):
    """the declared tools are in the live tools/list AND callable -> exit 0."""
    wd, prove = _mcp_sandbox(tmp_path)
    assert mcp_tools.run(str(wd), prove, ["greet", "echo"]) == 0


def test_blocks_when_declared_tool_not_exposed(tmp_path):
    """a tool the spec declares but the server does NOT serve -> red (the manifest lied)."""
    wd, prove = _mcp_sandbox(tmp_path)
    assert mcp_tools.run(str(wd), prove, ["greet", "nonexistent_tool"]) != 0


def test_blocks_when_listed_tool_not_invokable(tmp_path):
    """a server that LISTS a tool but ERRORS on call -> the prover exits non-zero -> red (invokes tooth)."""
    wd, prove = _mcp_sandbox(tmp_path, _SERVER_UNCALLABLE)
    assert mcp_tools.run(str(wd), prove, ["greet"]) != 0


def test_blocks_a_promiscuous_server(tmp_path):
    """a server that returns success for ANY tool name is caught by the embedded negative: calling a
    phantom tool 'succeeds' -> GATE DECORATIVO -> red."""
    wd, prove = _mcp_sandbox(tmp_path, _SERVER_PROMISCUOUS)
    assert mcp_tools.run(str(wd), prove, ["greet"]) != 0


def test_missing_workdir_is_red(tmp_path):
    assert mcp_tools.run(str(tmp_path / "absent"), [PY, "prove.py"], ["greet"]) == 2


def test_prover_cannot_launch_is_red(tmp_path):
    wd, _prove = _mcp_sandbox(tmp_path)
    assert mcp_tools.run(str(wd), ["this_binary_does_not_exist_xyz"], ["greet"]) == 127


# ── ADR-012: the substrate is a PASS-THROUGH, it names no tech ──────────────────

def test_registry_passes_mcp_argv_through_verbatim():
    """The registry resolves `mcp_tools` WITHOUT recognizing any tech: opaque prove/tools ride through as
    data (ADR-012). A real MCP SDK or a stdlib impl is new data, not an engine branch."""
    check = {"name": "m", "kind": "mcp_tools", "workdir": "wd",
             "prove": ["TECH_PROVER", "--mcp"], "tools": ["alpha", "beta"]}
    argv = resolve_check(check, None, Station.from_dict({"id": "x"}), {})
    assert "wd" in argv
    assert json.dumps(["TECH_PROVER", "--mcp"]) in argv
    assert json.dumps(["alpha", "beta"]) in argv


# ── e2e through the REAL engine: the station gates, and a broken server blocks ──

def _mcp_station(server_src: str, tools: list) -> Station:
    return Station.from_dict({
        "id": "mcp", "name": "mcp tools",
        "builds": [
            {"action": "write", "dest": "mcp/server.py", "content": server_src},
            {"action": "write", "dest": "mcp/prove.py", "content": _PROVER},
        ],
        "checks": [{"name": "mcp_proof", "kind": "mcp_tools", "workdir": "mcp",
                    "prove": [PY, "prove.py"], "tools": tools}],
    })


def _run(tmp_path: Path, station: Station):
    ctx = RunContext(root=tmp_path, meta_root=repo_root())
    return run_station(ctx, station, Sequence([station]), {}, stations_dir=tmp_path,
                       spec_path=None, record_active=False)


def test_engine_mcp_station_opens_when_green(tmp_path):
    run = _run(tmp_path, _mcp_station(_SERVER, ["greet", "echo"]))
    assert run.passed is True and run.gate.opened is True
    assert run.proof["writer"] == "seed/verifier.py"   # verdict by the trust root, not the model


def test_engine_mcp_station_shuts_when_tool_not_invokable(tmp_path):
    run = _run(tmp_path, _mcp_station(_SERVER_UNCALLABLE, ["greet"]))
    assert run.passed is False and run.gate.opened is False


# ── principle #6: the SAME kind proves a different toolset, no per-tech branch ──

_SERVER_ARITH = _SERVER.replace(
    '"greet": ("devuelve el marcador invariante", lambda a: "DUMMY_OK"),\n    '
    '"echo":  ("devuelve el argumento text",       lambda a: str(a.get("text", ""))),',
    '"add": ("suma a+b", lambda a: str(int(a.get("a", 0)) + int(a.get("b", 0)))),\n    '
    '"ping": ("responde pong", lambda a: "pong"),')


def test_same_kind_proves_a_different_toolset(tmp_path):
    """A second, different MCP (arithmetic tools, not greeting) through the IDENTICAL mechanism: the
    substrate has no per-toolset branch (ADR-012, principle #6)."""
    wd, prove = _mcp_sandbox(tmp_path, _SERVER_ARITH)
    assert mcp_tools.run(str(wd), prove, ["add", "ping"]) == 0
    # and a tool this MCP does not expose is still red (the cross-check is real, not overfit).
    assert mcp_tools.run(str(wd), prove, ["add", "greet"]) != 0


# ── emit_mcp: the MCP glue is GENERATED from L3 machinery.mcp (ADR-011/012) ─────

_MCP_SPEC = """\
factory: {{name: MCP Probe, slug: {slug}, maturity: bootstrap}}
domain:
  produces: "un MCP de fábrica declarado"
  station_sequence:
    - {{id: s00, name: mcp, builds: [{{action: emit_mcp}}], checks: []}}
machinery:
  mcp:
    tech: "servidor MCP stdlib (JSON-RPC sobre stdio); el plan lo eligió"
    primitive: DES-6
    status: built
    tools: [{{name: greet, description: saluda}}, {{name: echo, description: eco}}]
    emit:
      - {{dest: build/mcp/marker.txt, content: "MCP_OK for {{{{slug}}}}"}}
requirements:
  functional:
    - {{id: REQ-F-001, statement: el mcp expone tools, satisfied_by: [s00]}}
"""


def test_emit_mcp_writes_declared_glue(tmp_path):
    """emit_mcp writes each `machinery.mcp.emit` entry from DATA, with {{var}} substituted — the substrate
    names no tech (ADR-012); shares the `_emit_glue` helper with emit_infra (other section, same machine)."""
    (tmp_path / "factory.spec.yml").write_text(_MCP_SPEC.format(slug="probe"), encoding="utf-8")
    spec = load_spec(tmp_path / "factory.spec.yml")
    ctx = RunContext(root=tmp_path, meta_root=repo_root())
    station = Station.from_dict({"id": "s00", "builds": [{"action": "emit_mcp"}], "checks": []})
    apply_builds(ctx, station, spec.subst)
    glue = tmp_path / "build" / "mcp" / "marker.txt"
    assert glue.exists() and glue.read_text(encoding="utf-8") == "MCP_OK for probe"


# ── M0 shape-teeth: an MCP that can't be emitted/proved honestly is refused (no tech named) ──

def _mcp_problems(mcp: dict) -> list[str]:
    spec = FactorySpec(name="X", slug="x", maturity="m", produces="p", stations=[],
                       substrate={}, requirements=[], machinery=Machinery(mcp=mcp))
    return [p for p in validate_grammar_v2(spec) if "machinery.mcp" in p]


def test_validator_accepts_wellformed_mcp():
    assert _mcp_problems({
        "tech": "t", "primitive": "DES-6", "status": "built",
        "tools": [{"name": "greet"}, {"name": "echo"}],
        "emit": [{"dest": "build/mcp/server.py", "content": "..."}],
    }) == []


def test_validator_rejects_tool_without_name():
    assert any("needs a name" in p for p in _mcp_problems({"tools": [{"description": "no name"}]}))


def test_validator_rejects_mcp_emit_without_dest():
    assert any("needs a dest" in p for p in _mcp_problems({"emit": [{"content": "no dest"}]}))
