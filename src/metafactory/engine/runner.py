"""runner — execute one station: BUILD (codegen) -> VERIFY (seed) -> GATE (read-side).

The verdict is computed only by the seed verifier from real exit codes; the runner
never sets `passed`. It records the active station (for the Stop hook, Lock #3) before
verifying, so a turn that ends mid-station is re-verified at close."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from ..verify.checks.registry import resolve_check
from .gate import GateResult, open_gate
from .run_context import RunContext
from .sequence import Sequence
from .station import Station


@dataclass
class StationRun:
    station: Station
    proof: dict
    gate: GateResult
    build_msgs: list[str]

    @property
    def passed(self) -> bool:
        return bool(self.proof.get("passed"))


def write_active(ctx: RunContext, station: Station, stations_dir: Path, spec_path: Path | None) -> None:
    """Record the active {root, station, stations_dir, spec} at the META root so the
    Stop hook can re-run verify regardless of which factory's line is being driven."""
    active = {
        "root": str(ctx.root),
        "slug": ctx.slug,
        "station": station.id,
        "stations_dir": str(stations_dir),
        "spec": str(spec_path) if spec_path else "",
        "at": ctx.verifier.utc_now(),
    }
    meta_active = ctx.verifier.active_path_for(ctx.meta_root)  # canonical slot, defined by the seed
    meta_active.parent.mkdir(parents=True, exist_ok=True)
    tmp = meta_active.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(active, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, meta_active)


def run_station(
    ctx: RunContext,
    station: Station,
    seq: Sequence,
    subst: dict,
    *,
    stations_dir: Path,
    spec_path: Path | None = None,
    build: bool = True,
) -> StationRun:
    from ..codegen import apply_builds

    build_msgs: list[str] = []
    if build:
        build_msgs = apply_builds(ctx, station, subst)

    write_active(ctx, station, stations_dir, spec_path)

    cmds = [{"name": c["name"], "cmd": resolve_check(c, ctx, station, subst)} for c in station.checks]
    proof = ctx.verifier.verify_station(station.id, cmds, ctx.root, pythonpath=ctx.pythonpath)
    gate = open_gate(ctx, station, seq)

    # Tier 0 capture at-source (continua, no checkpoint discrecional): el hecho queda aunque
    # la generación se corte. Best-effort: nunca rompe la línea.
    from ..memory import journal
    journal.append(ctx.meta_root, "station_run", station=station.id, slug=ctx.slug,
                   passed=bool(proof.get("passed")), gate_open=gate.opened,
                   proof_sha=proof.get("proof_sha", ""))
    return StationRun(station, proof, gate, build_msgs)
