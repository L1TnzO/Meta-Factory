"""verify — the verdict bus (I-7) and the deterministic checks.

Every check resolves to a subprocess command so the seed verifier only ever OBSERVES
exit codes (it cannot be fooled by an in-process object claiming success). `report.py`
formats the bounded verdict; raw logs go to disk, never to the orchestrator's context."""
from .report import Verdict, format_verdict

__all__ = ["Verdict", "format_verdict"]
