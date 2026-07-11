"""report — the verdict bus (I-7). Turns a proof into a BOUNDED verdict (≤10 lines) +
a pointer to the full log on disk. The raw log NEVER enters the orchestrator's context;
on failure we mine the on-disk log for `file:line` so red is actionable without a dump.

Format (CONTEXT-ECONOMY §2):
    VERDICT    <verb> — <PASS|FAIL>   (exit <code>)
    SUMMARY    <one line>
    COUNTS     <per check>
    FAILURES   <≤N as file:line — msg>     (omitted if PASS)
    ARTIFACT   <log path on disk>
    NEXT       <actionable next step>
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_FILELINE = re.compile(r'([\w./\-]+\.[A-Za-z]\w*):(\d+)')
_PYC = re.compile(r'File "([^"]+)", line (\d+)')


@dataclass
class Verdict:
    verb: str
    status: str          # PASS | FAIL | PROVISIONAL
    exit_code: int
    summary: str
    counts: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    artifact: str = ""
    next_action: str = ""


def _extract_fileline(log_text: str, check_name: str) -> str | None:
    """Pull the most relevant `file:line` from the failing check's log section. Prefers a
    real source path (skips Python's `<frozen ...>`/`<string>` pseudo-frames) and the
    DEEPEST frame (the actual error site), not the runpy bootstrap frame."""
    marker = f"## check={check_name} "
    start = log_text.find(marker)
    if start == -1:
        return None
    nxt = log_text.find("\n## check=", start + 1)
    section = log_text[start: nxt if nxt != -1 else len(log_text)]
    candidates = [(m.group(1), m.group(2)) for m in _PYC.finditer(section)]
    candidates += [(m.group(1), m.group(2)) for m in _FILELINE.finditer(section)]
    real = [c for c in candidates if not c[0].startswith("<")]
    if real:
        f, ln = real[-1]
        return f"{f}:{ln}"
    for line in reversed([l.strip() for l in section.splitlines() if l.strip()]):
        if not line.startswith(("---", "##", "#")) and not line.startswith("<"):
            return line[:80]
    return None


def from_proof(verb: str, proof: dict, *, next_pass: str = "", next_fail: str = "", max_fail: int = 5) -> Verdict:
    checks = proof.get("checks", [])
    passed = bool(proof.get("passed"))
    counts = [f"{c['name']} {'ok' if int(c['exit']) == 0 else 'FAIL(' + str(c['exit']) + ')'}" for c in checks]
    failures: list[str] = []
    log_path = proof.get("log_path", "")
    log_text = ""
    if log_path and Path(log_path).exists():
        log_text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    for c in checks:
        if int(c["exit"]) != 0:
            loc = _extract_fileline(log_text, c["name"]) or f"exit {c['exit']}"
            failures.append(f"{c['name']}: {loc}")
    n_fail = sum(1 for c in checks if int(c["exit"]) != 0)
    summary = (
        f"{len(checks)} checks all green" if passed
        else f"{n_fail}/{len(checks)} checks red"
    )
    return Verdict(
        verb=verb,
        status="PASS" if passed else "FAIL",
        exit_code=0 if passed else 1,
        summary=summary,
        counts=counts,
        failures=failures[:max_fail],
        artifact=log_path,
        next_action=(next_pass if passed else next_fail),
    )


def format_verdict(v: Verdict) -> str:
    lines = [
        f"VERDICT    {v.verb} — {v.status}   (exit {v.exit_code})",
        f"SUMMARY    {v.summary}",
        f"COUNTS     {' · '.join(v.counts) if v.counts else '—'}",
    ]
    if v.status != "PASS" and v.failures:
        lines.append(f"FAILURES   {v.failures[0]}")
        for f in v.failures[1:]:
            lines.append(f"           {f}")
    if v.artifact:
        lines.append(f"ARTIFACT   {v.artifact}")
    if v.next_action:
        lines.append(f"NEXT       {v.next_action}")
    return "\n".join(lines)
