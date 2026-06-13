"""checks — resolution of station check kinds to subprocess commands, plus the small
runnable check modules (artifact_contains, docs_check) invoked via `python -m`."""
from .registry import KINDS, resolve_check

__all__ = ["KINDS", "resolve_check"]
