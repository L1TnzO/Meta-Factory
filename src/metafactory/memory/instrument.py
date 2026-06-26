"""instrument (ADR-019 §5, M5) — the OBSERVER of the context INJECTION path.

Measures three series, all file-IO + arithmetic, ZERO model calls (ADR-008), best-effort (capture
must never break the line — telemetry can't fail generation). They land in `.metamem/metrics.jsonl`
(gitignored, regenerable) each under its own `kind`; the memory-v2 bets (M3 fidelity gate, M4
PreCompact, M6 three-memory dedup) are READ against these series — without them we'd build blind
(the measured mistake of `recall`, retired in M2).

Series:
  footprint  {kind="footprint", session, payload_chars, payload_tokens, lines, now_lines}
             ← the cost FIXED when the session starts (what `rehydrate` injects). ADR-019 §5(1).
  tool/read  {kind="tool", tool, session, target}
             ← the `target` (file/pattern) per tool-use; `mem_capture` enriches it. THRASHING
               (re-reading the SAME file within a session) is re-derived from this. ADR-019 §5(2).
  fidelity   {kind="fidelity", check, passed, exit}
             ← the result of the FIDELITY gates over time (today `state_snapshot`; tomorrow M3's
               `state_fidelity` flows in untouched). ADR-019 §5(3).
  compact    {kind="compact", session, trigger, increment, written}
             ← one sample per COMPACTION boundary (M4): how often we compact, with what trigger, and
               whether the live-state snapshot was preserved. The PAYOFF (fewer post-compaction
               re-reads) is read by correlating this with the `thrashing` series above. ADR-019 §5, M4.

It does NOT model, decide, or gate: it records and summarizes (ADR-008, the shape `recall` had
before it was retired). The summary is bounded (CONTEXT-ECONOMY §2): never dumps the raw series.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from . import metrics

# Token heuristic without a model: ~4 chars/token (standard for en/es prose). This is a footprint
# ESTIMATE, not billing — real billing comes from the transcript (metrics.cost).
CHARS_PER_TOKEN = 4

# Tools whose target is a re-readable file: thrashing is re-READING, not re-editing (editing a file
# repeatedly is normal work; re-reading it after losing context is the symptom we want to catch).
READ_TOOLS = {"Read"}

# Checks whose pass/fail series IS the fidelity signal. `state_snapshot` (M1) already exists;
# `state_fidelity` (M3) flows into the same series when it lands — without touching this module.
FIDELITY_CHECKS = {"state_snapshot", "state_fidelity"}


def est_tokens(text: str) -> int:
    """Model-free token estimate (~4 chars/token). A footprint gauge, not billing."""
    return len(text) // CHARS_PER_TOKEN


# ── recorders (best-effort via metrics.capture, which never raises) ───────────
def record_session_footprint(root: Path, session: str, payload: str, *, lines: int, now_lines: int) -> dict:
    """Series (1): the footprint `rehydrate` FIXES at session start. Called by build_payload."""
    return metrics.capture(
        root, kind="footprint", session=session,
        payload_chars=len(payload), payload_tokens=est_tokens(payload),
        lines=lines, now_lines=now_lines,
    )


def target_of(tool_name: str, tool_input: Any) -> str:
    """The re-readable 'target' of a tool-use, for series (2): file_path for Read/Edit/Write,
    pattern for Grep, path for Glob. '' if none applies (no target recorded)."""
    if not isinstance(tool_input, dict):
        return ""
    for key in ("file_path", "path", "pattern", "notebook_path"):
        val = tool_input.get(key)
        if isinstance(val, str) and val:
            return val
    return ""


def record_fidelity_from_proof(root: Path, proof: dict) -> list[dict]:
    """Series (3): one {check, passed, exit} sample per FIDELITY check in a `meta check` proof.
    Today `state_snapshot`; tomorrow `state_fidelity` (M3) flows in by name, no code change here."""
    out: list[dict] = []
    for chk in proof.get("checks", []):
        name = chk.get("name", "")
        if name in FIDELITY_CHECKS:
            exit_code = int(chk.get("exit", 1))
            out.append(metrics.capture(root, kind="fidelity", check=name,
                                       passed=(exit_code == 0), exit=exit_code))
    return out


def record_compaction(root: Path, *, session: str, trigger: str, increment: str | None,
                      written: bool) -> dict:
    """Series (4): one sample per COMPACTION boundary (M4). The PreCompact hook calls this so the bet
    is READ against the observer (correlate with `thrashing` to see if the snapshot reduced re-reads)."""
    return metrics.capture(root, kind="compact", session=session, trigger=trigger,
                           increment=increment, written=bool(written))


# ── readers / rollups (re-derive the series; never dump raw) ──────────────────
def footprint_series(root: Path) -> list[dict]:
    return [m for m in metrics.read(root) if m.get("kind") == "footprint"]


def compact_series(root: Path) -> list[dict]:
    return [m for m in metrics.read(root) if m.get("kind") == "compact"]


def thrashing_rollup(root: Path) -> dict[str, Any]:
    """Re-derive THRASHING: re-reads of the SAME file within a session. Group READ_TOOLS tool-uses
    by (session, target) and count; a (session, target) with count>1 is a re-read. Returns bounded
    totals + worst offenders — never the raw series."""
    per: dict[tuple[str, str], int] = defaultdict(int)
    for m in metrics.read(root):
        if m.get("kind") != "tool" or m.get("tool") not in READ_TOOLS:
            continue
        target = m.get("target") or ""
        if not target:
            continue
        per[(m.get("session", ""), target)] += 1
    rereads = {k: c for k, c in per.items() if c > 1}
    extra = sum(c - 1 for c in rereads.values())  # reads beyond the first
    worst = sorted(rereads.items(), key=lambda kv: kv[1], reverse=True)[:3]
    return {
        "distinct_reads": len(per),
        "reread_files": len(rereads),
        "extra_reads": extra,
        "worst": [(target, c, sess[:8]) for (sess, target), c in worst],
    }


def fidelity_series(root: Path) -> list[dict]:
    return [m for m in metrics.read(root) if m.get("kind") == "fidelity"]


def summarize(root: Path) -> list[str]:
    """Bounded summary (≤4 lines) of the 4 series, for `meta metrics`. Never dumps the raw series."""
    lines: list[str] = []

    fps = footprint_series(root)
    if fps:
        last = fps[-1]
        avg_tok = sum(f.get("payload_tokens", 0) for f in fps) // len(fps)
        lines.append(
            f"FOOTPRINT  {len(fps)} sesión(es) · último {last.get('payload_tokens', 0)} tok "
            f"(≈{last.get('payload_chars', 0)} ch · «Ahora» {last.get('now_lines', 0)} ln) · prom {avg_tok} tok"
        )
    else:
        lines.append("FOOTPRINT  sin sesiones registradas")

    thr = thrashing_rollup(root)
    worst = thr["worst"]
    worst_str = " · ".join(f"{Path(t).name}×{c}" for t, c, _ in worst) if worst else "—"
    lines.append(
        f"THRASHING  {thr['reread_files']} archivo(s) re-leído(s) · "
        f"{thr['extra_reads']} re-lectura(s) extra · top {worst_str}"
    )

    fids = fidelity_series(root)
    if fids:
        npass = sum(1 for f in fids if f.get("passed"))
        last = fids[-1]
        lines.append(
            f"FIDELIDAD  {npass}/{len(fids)} muestra(s) OK · última {last.get('check', '?')} "
            f"{'OK' if last.get('passed') else 'ROJO'}"
        )
    else:
        lines.append("FIDELIDAD  sin muestras (corré `meta check`)")

    cps = compact_series(root)
    if cps:
        last = cps[-1]
        kept = sum(1 for c in cps if c.get("written"))
        lines.append(
            f"COMPACTACIÓN  {len(cps)} evento(s) · {kept} con snapshot preservado · "
            f"último {last.get('trigger', '?')} → incremento {last.get('increment') or 'ninguno'}"
        )
    else:
        lines.append("COMPACTACIÓN  sin eventos (aún no se compactó esta serie)")

    return lines
