"""engine — domain-agnostic line runner (I-2: stations as data, not code branches)."""
from .run_context import RunContext
from .station import Station
from .sequence import Sequence, load_sequence
from .gate import GateResult, open_gate
from .runner import StationRun, run_station

__all__ = [
    "RunContext", "Station", "Sequence", "load_sequence",
    "GateResult", "open_gate", "StationRun", "run_station",
]
