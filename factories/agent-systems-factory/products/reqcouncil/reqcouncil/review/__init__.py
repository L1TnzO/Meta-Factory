"""HITL review layer (H5, docs/design/02 §4): packet builder, decision validation,
reviewers (interactive CLI / decisions file / unattended auto) and the catch-rate drill.

The checkpoint itself lives in the GRAPH (graph/topology.py: reverify -> hitl ->
finalize -> END, non-skippable by reachability); this package is everything the
checkpoint needs around it — all deterministic, zero-LLM.
"""

from .auto import AUTO_ENGINEER, auto_reviewer
from .decisions import DECISIONS, apply_decisions, validate_decisions
from .packet import build_packet
from .ui import cli_reviewer, file_reviewer

__all__ = [
    "AUTO_ENGINEER",
    "DECISIONS",
    "apply_decisions",
    "auto_reviewer",
    "build_packet",
    "cli_reviewer",
    "file_reviewer",
    "validate_decisions",
]
