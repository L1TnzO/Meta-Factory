"""registry — pure mapping from a station check (data) to a subprocess argv.

A check is `{name, kind, ...}`. `resolve_check` returns the argv the seed verifier will
run with cwd == ctx.root. Every kind is subprocess-shaped: exit 0 == pass. New domains
add data (a new check entry), not engine branches (I-2).
"""
from __future__ import annotations

import json
import sys

from ...codegen.renderer import render_text
from ..._seed import repo_root

PY = sys.executable
KINDS = (
    "py_compile", "import_runs", "artifact_contains", "spec_validate",
    "rtm_closure", "design_review", "pytest", "isolation", "docs_check", "command",
    "column_selftest", "column_full", "bus_bounded", "product_run", "boundary_survives",
    "rtm_rederive", "rtm_tree", "clean_runner", "agent_shadow", "product_env", "command_runs",
    "infra_up",
)


def _s(value, subst):
    """Substitute {{var}} in a string, a list of strings, recursively."""
    if isinstance(value, str):
        return render_text(value, subst)
    if isinstance(value, (list, tuple)):
        return [_s(v, subst) for v in value]
    return value


def resolve_check(check: dict, ctx, station, subst: dict) -> list[str]:
    kind = check.get("kind")
    if kind == "py_compile":
        files = _s(check["files"], subst)
        return [PY, "-m", "py_compile", *files]
    if kind == "import_runs":
        return [PY, "-c", _s(check["code"], subst)]
    if kind == "artifact_contains":
        return [PY, "-m", "metafactory.verify.checks.artifact_contains",
                _s(check["file"], subst), _s(check["marker"], subst)]
    if kind == "spec_validate":
        return [PY, "-m", "metafactory.spec.cli", "validate", _s(check["spec"], subst)]
    if kind == "rtm_closure":
        return [PY, "-m", "metafactory.spec.cli", "rtm-closure", _s(check["spec"], subst)]
    if kind == "design_review":
        return [PY, "-m", "metafactory.spec.cli", "design-review", _s(check["spec"], subst)]
    if kind == "pytest":
        return [PY, "-m", "pytest", "-q", _s(check["path"], subst)]
    if kind == "isolation":
        return [PY, "-m", "pytest", "-q", _s(check.get("path", "tests/test_isolation.py"), subst)]
    if kind == "docs_check":
        return [PY, "-m", "metafactory.verify.checks.docs_check", str(repo_root())]
    if kind == "command":
        return _s(check["cmd"], subst)
    if kind == "column_selftest":
        return [PY, "-m", "metafactory.verify.checks.column_selftest", str(subst.get("factory_root", "."))]
    if kind == "column_full":
        return [PY, "-m", "metafactory.verify.checks.column_full", str(subst.get("factory_root", "."))]
    if kind == "command_runs":
        return [PY, "-m", "metafactory.verify.checks.command_runs", str(subst.get("factory_root", "."))]
    if kind == "bus_bounded":
        return [PY, "-m", "metafactory.verify.checks.bus_bounded", str(subst.get("max_lines", 10))]
    if kind == "product_run":
        return [PY, "-m", "metafactory.cli", "product-run", "--factory", str(subst.get("slug", ""))]
    if kind == "boundary_survives":
        return [PY, "-m", "metafactory.verify.checks.boundary_survives",
                str(subst.get("factory_root", ".")), str(subst.get("meta_root", "")),
                str(subst.get("spec_path", "factory.spec.yml"))]
    if kind == "rtm_rederive":
        return [PY, "-m", "metafactory.verify.checks.rtm_rederive",
                str(subst.get("factory_root", ".")), str(subst.get("meta_root", "")),
                str(subst.get("spec_path", "factory.spec.yml"))]
    if kind == "rtm_tree":
        return [PY, "-m", "metafactory.verify.checks.rtm_tree",
                str(subst.get("factory_root", ".")), str(subst.get("meta_root", "")),
                str(subst.get("spec_path", "factory.spec.yml"))]
    if kind == "clean_runner":
        return [PY, "-m", "metafactory.verify.checks.clean_runner",
                str(subst.get("factory_root", ".")), str(subst.get("meta_root", "")),
                str(subst.get("spec_path", "factory.spec.yml"))]
    if kind == "agent_shadow":
        return [PY, "-m", "metafactory.verify.checks.agent_shadow",
                str(subst.get("factory_root", ".")), str(subst.get("meta_root", "")),
                str(subst.get("spec_path", "factory.spec.yml"))]
    if kind == "product_env":
        # C3 — proof en el toolchain DEL producto (runs_in: product_env, DES-8). `workdir`/`bootstrap`/`cmd`
        # son DATA (argv); el sustrato no nombra tech (ADR-012). El helper corre bootstrap->proof en el env
        # del producto (PYTHONPATH/venv de la fábrica scrubbed). JSON encode: argv arbitrario sin ambigüedad.
        return [PY, "-m", "metafactory.verify.checks.product_env",
                _s(check.get("workdir", "."), subst),
                json.dumps(_s(check.get("bootstrap", []), subst)),
                json.dumps(_s(check["cmd"], subst))]
    if kind == "infra_up":
        # E1 — la infra declarada levanta en el sandbox y un proof la usa (DES-9). `workdir`/`up`/`proof`/
        # `down` son DATA (argv); el sustrato no nombra tech (ADR-012). El helper levanta `up` en background,
        # reintenta `proof` contra el servicio vivo y hace teardown SIEMPRE. JSON encode: argv arbitrario.
        argv = [PY, "-m", "metafactory.verify.checks.infra_up",
                _s(check.get("workdir", "."), subst),
                json.dumps(_s(check.get("up", []), subst)),
                json.dumps(_s(check["proof"], subst)),
                json.dumps(_s(check.get("down", []), subst))]
        if check.get("timeout"):   # optional readiness window (DATA the plan chose; slow infra boots slow)
            argv.append(str(check["timeout"]))
        return argv
    raise ValueError(f"unknown check kind {kind!r} in station {station.id} (known: {KINDS})")
