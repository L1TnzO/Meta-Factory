"""E1 — la infra declarada levanta en el sandbox y un proof la USA (DES-9), probado por bloqueo.

Dos niveles, sin mocks:
  - el HELPER (`infra_up.run`) levanta `up` en background, reintenta `proof` contra el servicio VIVO y
    hace teardown SIEMPRE: pasa con un servicio que levanta + un proof que lo usa; bloquea si el servicio
    NO levanta; bloquea si el proof es DECORATIVO (pasa con la infra caída); y deja el recurso LIBRE
    (teardown verificado). El servicio del dummy es un socket Unix stdlib (sin puertos: race-free, re-derivable).
  - e2e por el MOTOR real (`run_station` + seed verifier + gate): una estación `infra_up` GATEA — verde
    abre, un servicio roto SHUT. Y el MISMO kind levanta un servicio TCP (otro transporte; principio #6).

El sustrato no nombra tech: `up`/`proof`/`down` son DATA (ADR-012) — un socket Unix, un TCP, o `docker
compose up` son la misma máquina con otra data.
"""
from __future__ import annotations

import json
import socket
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
from metafactory.verify.checks import infra_up
from metafactory.verify.checks.registry import resolve_check

PY = sys.executable

# A self-contained stdlib infra: a Unix-socket service that answers a marker, and a client proof that
# connects + asserts it. No ports == no collision across runs (the path lives under the sandbox workdir).
_UDS_SERVER = (
    "import os, socket, sys\n"
    "path = sys.argv[1]\n"
    "try:\n    os.unlink(path)\nexcept OSError:\n    pass\n"
    "s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)\n"
    "s.bind(path); s.listen()\n"
    "while True:\n"
    "    conn, _ = s.accept(); conn.sendall(b'INFRA_OK\\n'); conn.close()\n"
)
_UDS_CLIENT = (
    "import socket, sys\n"
    "path = sys.argv[1]\n"
    "try:\n"
    "    c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); c.settimeout(1)\n"
    "    c.connect(path); data = c.recv(64); c.close()\n"
    "except OSError:\n    sys.exit(1)\n"
    "sys.exit(0 if b'INFRA_OK' in data else 2)\n"
)


def _uds_sandbox(tmp_path: Path) -> tuple[Path, list, list]:
    """Materialize the UDS service + client in a workdir; return (workdir, up-argv, proof-argv)."""
    wd = tmp_path / "infra"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "server.py").write_text(_UDS_SERVER, encoding="utf-8")
    (wd / "client.py").write_text(_UDS_CLIENT, encoding="utf-8")
    return wd, [PY, "server.py", "infra.sock"], [PY, "client.py", "infra.sock"]


# ── the helper: up in background, proof against the live service, teardown always ───

def test_passes_when_infra_comes_up_and_proof_uses_it(tmp_path):
    """the service binds, the client proof connects + reads the marker -> exit 0."""
    wd, up, proof = _uds_sandbox(tmp_path)
    assert infra_up.run(str(wd), up, proof, []) == 0


def test_blocks_when_infra_never_comes_up(tmp_path):
    """`up` exits without binding anything -> the proof never connects -> red within the timeout.
    Render-green (a compose file on disk) is NOT enough: the service must actually stand up."""
    wd, _up, proof = _uds_sandbox(tmp_path)
    rc = infra_up.run(str(wd), [PY, "-c", "pass"], proof, [], ready_timeout=2.0)
    assert rc != 0


def test_blocks_a_decorative_proof(tmp_path):
    """a proof that passes WITHOUT the live service (here: `pass`, always exit 0) is caught by the
    embedded negative: with the infra down the proof still passes -> GATE DECORATIVO -> red."""
    wd, up, _proof = _uds_sandbox(tmp_path)
    assert infra_up.run(str(wd), up, [PY, "-c", "pass"], []) != 0


def test_teardown_frees_the_resource(tmp_path):
    """after a green run the service is GONE: connecting to the socket fails (no leaked process holding
    it). This is the cleanliness/DES-9 tooth — a leaked server would poison the next run."""
    wd, up, proof = _uds_sandbox(tmp_path)
    assert infra_up.run(str(wd), up, proof, []) == 0
    c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    c.settimeout(1)
    try:
        connected = True
        try:
            c.connect(str(wd / "infra.sock"))
        except OSError:
            connected = False
    finally:
        c.close()
    assert connected is False, "el servicio quedó vivo tras el teardown (recurso no liberado)"


def test_missing_workdir_is_red(tmp_path):
    """no sandbox == nothing was built to stand up -> red (never a spurious pass)."""
    assert infra_up.run(str(tmp_path / "absent"), [], [PY, "-c", "pass"], []) == 2


def test_up_cannot_launch_is_red(tmp_path):
    """an `up` binary that does not exist == not exit-0 (fail-safe, never raises past the verdict)."""
    wd, _up, proof = _uds_sandbox(tmp_path)
    assert infra_up.run(str(wd), ["this_binary_does_not_exist_xyz"], proof, []) == 127


def test_down_runs_on_teardown(tmp_path):
    """the declared `down` is executed on teardown (here it drops a sentinel file we then observe)."""
    wd, up, proof = _uds_sandbox(tmp_path)
    sentinel = wd / "torn_down"
    down = [PY, "-c", f"open({str(sentinel)!r}, 'w').write('x')"]
    assert infra_up.run(str(wd), up, proof, down) == 0
    assert sentinel.exists(), "el `down` declarado no corrió en el teardown"


# ── ADR-012: the substrate is a PASS-THROUGH, it names no tech ──────────────────

def test_registry_passes_infra_argv_through_verbatim():
    """The registry resolves `infra_up` WITHOUT recognizing any tech: opaque up/proof/down ride through
    as data (ADR-012). A new infra (docker, a socket server, pg_ctl) is new data, not an engine branch."""
    check = {"name": "i", "kind": "infra_up", "workdir": "wd",
             "up": ["TECH_UP", "start"], "proof": ["TECH_PROOF", "--check"], "down": ["TECH_DOWN"],
             "timeout": 30}
    argv = resolve_check(check, None, Station.from_dict({"id": "x"}), {})
    assert "wd" in argv
    assert json.dumps(["TECH_UP", "start"]) in argv
    assert json.dumps(["TECH_PROOF", "--check"]) in argv
    assert json.dumps(["TECH_DOWN"]) in argv
    assert "30" in argv   # the readiness window rides through as data too


# ── e2e through the REAL engine: the station gates, and a broken service blocks ──

def _infra_station(up: list, proof: list) -> Station:
    return Station.from_dict({
        "id": "inf", "name": "infra sandbox",
        "builds": [
            {"action": "write", "dest": "infra/server.py", "content": _UDS_SERVER},
            {"action": "write", "dest": "infra/client.py", "content": _UDS_CLIENT},
        ],
        "checks": [{"name": "infra_proof", "kind": "infra_up", "workdir": "infra",
                    "up": up, "proof": proof, "down": [], "timeout": 4}],
    })


def _run(tmp_path: Path, station: Station):
    ctx = RunContext(root=tmp_path, meta_root=repo_root())
    return run_station(ctx, station, Sequence([station]), {}, stations_dir=tmp_path,
                       spec_path=None, record_active=False)


def test_engine_infra_station_opens_when_green(tmp_path):
    run = _run(tmp_path, _infra_station([PY, "server.py", "infra.sock"], [PY, "client.py", "infra.sock"]))
    assert run.passed is True and run.gate.opened is True
    assert run.proof["writer"] == "seed/verifier.py"   # verdict by the trust root, not the model


def test_engine_infra_station_shuts_when_service_broken(tmp_path):
    """`up` does not bind -> the proof never reaches a service -> the station SHUTs (gate closed)."""
    run = _run(tmp_path, _infra_station([PY, "-c", "pass"], [PY, "client.py", "infra.sock"]))
    assert run.passed is False and run.gate.opened is False


# ── principle #6: the SAME kind stands up a TCP service (another transport), no per-tech branch ──

_TCP_SERVER = (
    "import socket, sys\n"
    "port = int(sys.argv[1])\n"
    "s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
    "s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
    "s.bind(('127.0.0.1', port)); s.listen()\n"
    "while True:\n"
    "    conn, _ = s.accept(); conn.sendall(b'INFRA_OK\\n'); conn.close()\n"
)
_TCP_CLIENT = (
    "import socket, sys\n"
    "port = int(sys.argv[1])\n"
    "try:\n"
    "    c = socket.create_connection(('127.0.0.1', port), timeout=1); data = c.recv(64); c.close()\n"
    "except OSError:\n    sys.exit(1)\n"
    "sys.exit(0 if b'INFRA_OK' in data else 2)\n"
)


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_same_kind_stands_up_a_tcp_service(tmp_path):
    """A second, radically different transport (TCP on a port, not a Unix socket) through the IDENTICAL
    mechanism: the substrate has no per-transport branch (ADR-012, principle #6)."""
    wd = tmp_path / "tcp"
    wd.mkdir()
    (wd / "server.py").write_text(_TCP_SERVER, encoding="utf-8")
    (wd / "client.py").write_text(_TCP_CLIENT, encoding="utf-8")
    port = str(_free_port())
    assert infra_up.run(str(wd), [PY, "server.py", port], [PY, "client.py", port], []) == 0
    # and a proof against a port nobody serves is red (the proof genuinely depends on the live service).
    assert infra_up.run(str(wd), [PY, "-c", "pass"], [PY, "client.py", str(_free_port())], [],
                        ready_timeout=2.0) != 0


# ── emit_infra: the infra glue is GENERATED from L3 machinery.infra (ADR-011/012) ──

_INFRA_SPEC = """\
factory: {{name: Infra Probe, slug: {slug}, maturity: bootstrap}}
domain:
  produces: "una infra de sandbox declarada"
  station_sequence:
    - {{id: s00, name: infra, builds: [{{action: emit_infra}}], checks: []}}
machinery:
  infra:
    tech: "socket Unix stdlib en el sandbox"
    primitive: DES-9
    status: built
    services: [{{name: sandbox-svc, kind: socket-service}}]
    emit:
      - {{dest: build/infra/marker.txt, content: "INFRA_OK for {{{{slug}}}}"}}
requirements:
  functional:
    - {{id: REQ-F-001, statement: la infra levanta, satisfied_by: [s00]}}
"""


def test_emit_infra_writes_declared_glue(tmp_path):
    """emit_infra writes each `machinery.infra.emit` entry from DATA, with {{var}} substituted — the
    substrate names no tech (ADR-012), a socket server or a compose.yml are the same action, other data."""
    (tmp_path / "factory.spec.yml").write_text(_INFRA_SPEC.format(slug="probe"), encoding="utf-8")
    spec = load_spec(tmp_path / "factory.spec.yml")
    ctx = RunContext(root=tmp_path, meta_root=repo_root())
    station = Station.from_dict({"id": "s00", "builds": [{"action": "emit_infra"}], "checks": []})
    apply_builds(ctx, station, spec.subst)
    glue = tmp_path / "build" / "infra" / "marker.txt"
    assert glue.exists() and glue.read_text(encoding="utf-8") == "INFRA_OK for probe"


# ── M0 shape-teeth: an infra that can't be emitted/stood up honestly is refused (no tech named) ──

def _infra_problems(infra: dict) -> list[str]:
    spec = FactorySpec(name="X", slug="x", maturity="m", produces="p", stations=[],
                       substrate={}, requirements=[], machinery=Machinery(infra=infra))
    return [p for p in validate_grammar_v2(spec) if "machinery.infra" in p]


def test_validator_accepts_wellformed_infra():
    assert _infra_problems({
        "tech": "t", "primitive": "DES-9", "status": "built",
        "services": [{"name": "svc"}],
        "emit": [{"dest": "build/infra/server.py", "content": "..."}],
    }) == []


def test_validator_rejects_emit_without_dest():
    probs = _infra_problems({"emit": [{"content": "no dest"}]})
    assert any("needs a dest" in p for p in probs)


def test_validator_rejects_service_without_name():
    probs = _infra_problems({"services": [{"kind": "db"}]})
    assert any("needs a name" in p for p in probs)


def test_validator_rejects_nonstring_content():
    probs = _infra_problems({"emit": [{"dest": "x", "content": 123}]})
    assert any("content must be a string" in p for p in probs)
