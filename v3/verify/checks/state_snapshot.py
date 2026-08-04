#!/usr/bin/env python3
"""state_snapshot (ADR-019 §3, M1) — ported from v2's STATE-snapshot law. The «## Ahora» section of
`docs/STATE.md` is a SNAPSHOT (bounded truth-as-of-today), never a log. It is the one OVERWRITE
artifact in the doc schema (ADR-007) and also the one surface where drift is cheapest: left to grow,
"read STATE" costs tens of thousands of tokens and accumulates stale claims nobody re-checks.

    python3 -m v3.verify.checks.state_snapshot
    V3_STATE_SNAPSHOT_SABOTAGE=1 python3 -m v3.verify.checks.state_snapshot   # red side; must ALSO exit 0

This docstring does not spell the legacy package's path, on purpose: `v3.verify.import_boundary`
rule 3 bans naming the v2 substrate under `v3/`, because a string is how a dynamic import or a path
injection hides. Describing what was ported costs nothing; naming the path it came from does.

THE LAW, two-sided, unchanged from what it ported (`extract_now_lines` / `snapshot_problems`, and the
policy constants `NOW_BUDGET_LINES` / `STALE_CLOSURE_DAYS` / `_CLOSURE_RE`): «Ahora» fails when it
  (a) EXCEEDS its line budget — closed history belongs in `docs/LOG.md`, not here; or
  (b) carries a CLOSURE MARK (✅/CERRADO/CLOSED/COMPLETE/DONE) whose most recent date on that line is
      older than the staleness threshold — a dated, old closure should already have DESCENDED to LOG.

It does NOT auto-rewrite (auto-rewriting is what causes drift): it FAILS and SIGNALS. The generated
fact-projection block (`meta:projection`, governed by the `projection` gate) is NOT «Ahora» and is out
of scope here — only the editable PROSE under the `## Ahora` heading is measured. The retired parity
oracle (`corpus_parity`, retired at V3-EXTRACT-CORPUS-PARITY) re-derived that this answer matched
v2's, on this same tree, every run during the rebuild — comparing the «Ahora» LINE COUNT together with
the problem list, not just the list (two laws could agree "no problems" while disagreeing about which
lines «Ahora» even contains, a hollow agreement).

WHY THE WITNESS IS BEHIND A `sabotage_env` HANDLE, and not embedded in the green run (v2's shape: a
private `_tooth_bites()` runs synthetic fixtures INSIDE the same process, so it can fail but cannot be
re-run independently). Under `v3.verify.registry`'s registration law a gate needs a re-runnable
handle; a private in-process helper carrying only Python literals is not one. So the same two synthetic
cases move behind `V3_STATE_SNAPSHOT_SABOTAGE=1`, unchanged in shape, and the green run stops asserting
them itself — two moments, declared apart, exactly as P2 (`docs/spec/11-build-plan.md §2`) asks for.

CONTRACT (`v3.verify.registry.Gate.red_run`'s docstring — the opposite of the obvious one): the
sabotage run exits **0** when it caught BOTH planted defects, printing what it caught; it exits **1**
with `GATE DECORATIVO` when either went unnoticed. Reported per-class so a partial catch is visible
rather than silently rounded up to green.

NO N/A BRANCH HERE. This law reads only `docs/STATE.md`; it needs no `.proof/` to answer, unlike its
sibling `state_fidelity` — see that module for why the N/A branch belongs there instead.

Argv: an optional single repo-root path, and an optional `--now YYYY-MM-DD` (decided, never observed
from the clock, so a comparison against this law is reproducible on any later day)."""
from __future__ import annotations

import os
import re
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_STATE_SNAPSHOT_SABOTAGE"

# ── budget (ADR-019 §3: «Ahora» stays a bounded snapshot of today's truth, not a log) ───────────
NOW_BUDGET_LINES = 45
STALE_CLOSURE_DAYS = 14

# Closure marks: the ✅ emoji or the UPPERCASE words as this project actually writes them (avoids a
# false positive on ordinary lowercase prose like "una solución completa"). `CLOSED` covers the
# English-forward header `Status: **CLOSED**` (ADR-026, dual-accept with the legacy `CERRADO`).
_CLOSURE_RE = re.compile(r"✅|\b(?:CERRAD[OA]|CLOSED|COMPLET[OAE]|DONE)\b")
_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_NOW_HEADING_RE = re.compile(r"^##\s+Ahora\b")


def extract_now_lines(text: str) -> list[str] | None:
    """The content lines under `## Ahora …` (without the heading), up to the next `## ` or EOF,
    trimming blank lines at both ends. None if there is no «Ahora» section. Robust to it being last."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if _NOW_HEADING_RE.match(ln)), None)
    if start is None:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    body = lines[start + 1:end]
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    return body


def _stale_closures(body: list[str], today: date) -> list[str]:
    """Lines carrying a closure mark whose most RECENT date is older than the threshold. A mark with
    no date is not flagged (staleness cannot be measured; the budget governs it instead)."""
    problems: list[str] = []
    for ln in body:
        if not _CLOSURE_RE.search(ln):
            continue
        dates = []
        for y, m, d in _DATE_RE.findall(ln):
            try:
                dates.append(date(int(y), int(m), int(d)))
            except ValueError:
                pass
        if not dates:
            continue
        newest = max(dates)
        age = (today - newest).days
        if age > STALE_CLOSURE_DAYS:
            snippet = ln.strip()[:80]
            problems.append(f"cierre rancio ({age}d > {STALE_CLOSURE_DAYS}d, {newest.isoformat()}): {snippet}")
    return problems


def snapshot_problems(state_path: Path, today: date) -> list[str]:
    """[] if «Ahora» is a bounded, fresh snapshot. A list of problems otherwise."""
    try:
        text = state_path.read_text(encoding="utf-8")
    except OSError as e:  # noqa: BLE001 — an unreadable STATE is reportable, not a crash
        return [f"no pude leer {state_path}: {e}"]
    body = extract_now_lines(text)
    if body is None:
        return ["no encontré la sección `## Ahora` en STATE.md (¿se renombró el encabezado?)"]
    problems: list[str] = []
    n = len(body)
    if n > NOW_BUDGET_LINES:
        problems.append(f"«Ahora» = {n} líneas > presupuesto {NOW_BUDGET_LINES} "
                        f"(bajá lo cerrado/histórico a LOG; el snapshot es verdad-de-HOY + punteros)")
    problems.extend(_stale_closures(body, today))
    return problems


# ── the sabotage witness (P2: re-runnable, not embedded) ────────────────────────────────────────
_OVER_BUDGET = "over_budget"
_STALE_CLOSURE = "stale_closure"
_CLASSES: tuple[str, ...] = (_OVER_BUDGET, _STALE_CLOSURE)


def _run_sabotage(today: date) -> int:
    """Two isolated synthetic `STATE.md` fixtures, one per defect class the law must catch. No git,
    no `.proof/` needed — this law only ever reads one file's text."""
    caught: list[str] = []
    with tempfile.TemporaryDirectory(prefix="v3-state-snapshot-sabotage-") as tmp:
        sp = Path(tmp) / "STATE.md"

        # (a) over-budget: «Ahora» with far more lines than the budget allows, no closures at all.
        over = "\n".join(f"- bullet {i}" for i in range(NOW_BUDGET_LINES + 10))
        sp.write_text(f"# S\n## Ahora\n{over}\n## Siguiente\n- x\n", encoding="utf-8")
        if any("presupuesto" in p for p in snapshot_problems(sp, today)):
            caught.append(_OVER_BUDGET)

        # (b) stale closure: well under budget, but a ✅ dated older than the threshold.
        old_iso = date.fromordinal(today.toordinal() - (STALE_CLOSURE_DAYS + 30)).isoformat()
        sp.write_text(f"# S\n## Ahora\n- algo viejo ✅ ({old_iso})\n## Siguiente\n- x\n", encoding="utf-8")
        if any("rancio" in p for p in snapshot_problems(sp, today)):
            caught.append(_STALE_CLOSURE)

    if len(caught) == len(_CLASSES):
        return Verdict("v3-state-snapshot (SABOTAGE)", 0,
                       f"{len(caught)}/{len(_CLASSES)} planted defect(s) caught "
                       f"({', '.join(caught)})").emit()

    missed = [name for name in _CLASSES if name not in caught]
    return Verdict("v3-state-snapshot (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {len(caught)}/{len(_CLASSES)} planted defect(s) caught "
                   f"({', '.join(caught) or 'none'}) — missed {missed}: no teeth on those classes"
                   ).emit()


def _parse_argv(argv: list[str]) -> tuple[list[str], date]:
    """Splits an optional single positional root path from `--now YYYY-MM-DD` (consumed wherever it
    appears, so its value is never mistaken for a root path)."""
    positionals: list[str] = []
    today = datetime.now(timezone.utc).date()
    i = 0
    while i < len(argv):
        if argv[i] == "--now" and i + 1 < len(argv):
            today = datetime.strptime(argv[i + 1], "%Y-%m-%d").date()
            i += 2
            continue
        if not argv[i].startswith("--"):
            positionals.append(argv[i])
        i += 1
    return positionals, today


def main(argv: list[str]) -> int:
    positionals, today = _parse_argv(argv)
    if len(positionals) > 1:
        return Verdict("v3-state-snapshot", 2, f"takes at most one path argument; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage(today)

    root = Path(positionals[0]).resolve() if positionals else _ROOT
    state_path = root / "docs" / "STATE.md"

    problems = snapshot_problems(state_path, today)
    if problems:
        return Verdict("v3-state-snapshot", 1,
                       f"«Ahora» stopped being a snapshot (ADR-019 §3): {len(problems)} problem(s)",
                       failures=tuple(problems),
                       next_action="trim «Ahora» to today's truth + pointers; move closed/historical "
                                   "content down to `docs/LOG.md` (append, never hand-rewritten here)"
                       ).emit()

    body = extract_now_lines(state_path.read_text(encoding="utf-8")) or []
    return Verdict("v3-state-snapshot", 0,
                   f"«Ahora» = {len(body)} line(s) <= {NOW_BUDGET_LINES}; no closure older than "
                   f"{STALE_CLOSURE_DAYS}d", counts={"now_lines": len(body)}).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
