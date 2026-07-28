"""The bounded verdict bus (invariant I-7): what a verb tells its caller, and nothing more.

The bus exists because an agent that reads raw stdout drowns in it. A verdict is a STRUCT with a
bounded rendering: the status comes from an exit code, never from prose, and the payload never
carries a log — if the detail matters, it is behind `artifact`.

In v3 this stops being a text format and becomes a return TYPE. The rendering is kept because humans
and CI still read lines, but the bound moves from "please keep it short" to a function that cannot
emit more than `MAX_LINES`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_LINES = 10
MAX_FAILURES = 5


@dataclass(frozen=True)
class Verdict:
    """status is DERIVED from exit_code — never set independently, so the two cannot disagree."""

    verb: str
    exit_code: int
    summary: str
    counts: dict = field(default_factory=dict)
    failures: tuple[str, ...] = ()
    artifact: str | None = None
    next_action: str | None = None

    @property
    def status(self) -> str:
        return "PASS" if self.exit_code == 0 else "FAIL"

    def render(self) -> list[str]:
        """At most MAX_LINES. Truncation is REPORTED, never silent — a hidden truncation is how a
        bus stops being evidence and becomes a summary of itself."""
        lines = [f"VERDICT    {self.verb} — {self.status}   (exit {self.exit_code})",
                 f"SUMMARY    {self.summary}"]
        if self.counts:
            lines.append("COUNTS     " + " · ".join(f"{k}={v}" for k, v in self.counts.items()))
        shown = self.failures[:MAX_FAILURES]
        lines.extend(f"FAILURES   {f}" for f in shown)
        if len(self.failures) > len(shown):
            lines.append(f"FAILURES   … and {len(self.failures) - len(shown)} more")
        if self.artifact:
            lines.append(f"ARTIFACT   {self.artifact}")
        if self.next_action:
            lines.append(f"NEXT       {self.next_action}")
        if len(lines) > MAX_LINES:
            lines = lines[:MAX_LINES - 1] + [f"NEXT       … {len(lines) - MAX_LINES + 1} line(s) "
                                             f"withheld by the bus bound (I-7)"]
        return lines

    def emit(self) -> int:
        for line in self.render():
            print(line)
        return self.exit_code
