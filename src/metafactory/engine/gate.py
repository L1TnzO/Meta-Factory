"""Gate — the read-side guard (Lock #2 + predecessor ordering).

The gate NEVER writes `passed`; it reads the proof the seed verifier wrote and decides
whether the gate may open. Opening requires: (a) the proof recomputes clean and passed
(Lock #2, via the seed's `gate_recompute_ok`), and (b) EVERY predecessor's gate is open —
the linear chain, or the full fan-in `depends_on` DAG (any shut upstream keeps this one shut).
"""
from __future__ import annotations

from dataclasses import dataclass

from .run_context import RunContext
from .sequence import Sequence
from .station import Station


@dataclass
class GateResult:
    station: str
    opened: bool
    reason: str

    def line(self) -> str:
        mark = "OPEN" if self.opened else "SHUT"
        return f"gate {self.station}: {mark} — {self.reason}"


def _proof_ok(ctx: RunContext, station_id: str) -> tuple[bool, str]:
    proof = ctx.verifier.load_proof(ctx.root, station_id)
    if proof is None:
        return False, f"no proof for {station_id} (never verified)"
    return ctx.verifier.gate_recompute_ok(proof)  # Lock #2


def open_gate(ctx: RunContext, station: Station, seq: Sequence) -> GateResult:
    ok, why = _proof_ok(ctx, station.id)
    if not ok:
        return GateResult(station.id, False, why)
    # DAG ordering: EVERY predecessor (fan-in `depends_on`, or the single linear one) must be open.
    # A fan-in station stays SHUT if ANY upstream gate is shut — the line cannot skip an unproven branch.
    for prev in seq.predecessors(station):
        prev_ok, prev_why = _proof_ok(ctx, prev.id)
        if not prev_ok:
            return GateResult(station.id, False, f"predecessor {prev.id} gate shut ({prev_why})")
    return GateResult(station.id, True, "ok")
