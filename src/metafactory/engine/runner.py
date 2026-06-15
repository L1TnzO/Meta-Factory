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
    """Record the active {root, station, stations_dir, spec} at the META root so the meta Stop hook can
    re-run verify regardless of which factory's line is being driven, AND a factory-local copy at the
    FACTORY root so the factory's OWN inherited column (commit_guard/stop_proof, D1) can recompute its
    active station with its own seed — defending itself alone, without the Meta-Factory's hooks."""
    active = {
        "root": str(ctx.root),
        "slug": ctx.slug,
        "station": station.id,
        "stations_dir": str(stations_dir),
        "spec": str(spec_path) if spec_path else "",
        "at": ctx.verifier.utc_now(),
    }
    blob = json.dumps(active, indent=2) + "\n"
    # canonical slot defined by the seed; write the meta pointer and the factory-local one (idempotent
    # if they coincide). The factory-local pointer is what the inherited column reads (only `station`).
    targets = {ctx.verifier.active_path_for(ctx.meta_root), ctx.verifier.active_path_for(ctx.root)}
    for dest in targets:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".json.tmp")
        tmp.write_text(blob, encoding="utf-8")
        os.replace(tmp, dest)


def run_station(
    ctx: RunContext,
    station: Station,
    seq: Sequence,
    subst: dict,
    *,
    stations_dir: Path,
    spec_path: Path | None = None,
    build: bool = True,
    record_active: bool = True,
) -> StationRun:
    """Run one station. `record_active=False` makes a HERMETIC run: it neither records the
    meta active-station pointer (Lock #3) nor journals the run — used when a gate re-derives a
    line in a throwaway clone (clean_runner, M6) so the re-derivation never leaks into the real
    active.json/journal. Real advances always record (the default)."""
    from ..codegen import apply_builds

    build_msgs: list[str] = []
    if build:
        build_msgs = apply_builds(ctx, station, subst)

    if record_active:
        write_active(ctx, station, stations_dir, spec_path)

    cmds = [{"name": c["name"], "cmd": resolve_check(c, ctx, station, subst)} for c in station.checks]
    proof = ctx.verifier.verify_station(station.id, cmds, ctx.root, pythonpath=ctx.pythonpath)
    gate = open_gate(ctx, station, seq)

    # Tier 0 capture at-source (continua, no checkpoint discrecional): el hecho queda aunque
    # la generación se corte. Best-effort: nunca rompe la línea. Una re-derivación hermética
    # (record_active=False) NO es un avance real -> no se journaliza.
    if record_active:
        from ..memory import journal
        journal.append(ctx.meta_root, "station_run", station=station.id, slug=ctx.slug,
                       passed=bool(proof.get("passed")), gate_open=gate.opened,
                       proof_sha=proof.get("proof_sha", ""))
    return StationRun(station, proof, gate, build_msgs)
