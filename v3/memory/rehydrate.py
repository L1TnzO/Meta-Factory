"""rehydrate — SessionStart: injects the minimum-value-density context when a session starts, PORTED
from v2's `memory/rehydrate.py` at the oracle commit, for the `SessionStart` hook
(`.claude/hooks/session_start.py`):

    print(build_payload(repo_root(), session=data.get("session_id", ""), source=data.get("source", "")))

Closes the problem this project LIVED: restarting used to lose all resident context, and the next
orchestrator started in the dark. It injects: the open increment + the persisted projection of facts
+ STATE's «Ahora» slice + the journal's tail + which docs are freshest (ADR-009 seal) + orientation
pointers. It does NOT replace reading: it triages and points at `meta check` / Grep / Read
(re-verify > recall).

ONLY `build_payload` — the slot contract's restriction, and the reason the post-compaction
"preserved live state" section (`precompact.surface_for_rehydrate` in v2) is NOT reproduced here: this
port only ever calls `build_payload` with `source=""` (the ordinary, overwhelmingly common session
start), `v3.memory.precompact` itself only carries the WRITE half (`build_snapshot` / `write_snapshot`
/ `record`), and the witness (`v3/verify/session_memory_parity.py`) documents the same boundary from
its own side — it never drives `source="compact"`. The day the read half is needed it is ported on its
own terms, not smuggled in here as a side effect of porting this function.

THE FACTS THIS FUNCTION DERIVES (unchanged from v2, and what the parity witness compares): the open
increment (or its absence) — `v3.memory.projection.open_increment`; the persisted projection of RTM +
open increment — `v3.memory.projection.current_block` (a read of the block ALREADY in `docs/STATE.md`,
never a live re-derivation — `meta checkpoint` is what refreshes it); the STATE «Ahora» slice — a
regex slice of `docs/STATE.md`'s own `## Ahora` section, reusing `v3.memory.docs_manifest.body_of` to
strip the doc's content-address seal first; the journal's tail — `v3.memory.journal.read`, sliced to
the last 5 records (v3's `journal.read` has no `limit=` keyword the way v2's did, so the slice is taken
here instead); which docs are freshest — `v3.memory.docs_manifest.doc_set` + `split_seal` + `SEAL_RE`,
reused rather than re-implemented, exactly per this slot's contract.

WHAT CHANGED FROM v2, and why — this port moves the WIRING and the LANGUAGE, never the law:
  - English prose (ADR-017): v2's banner/labels/orientation line are Spanish; this port's are English.
    The parity witness derives FACTS from each side's own payload text and compares those, never the
    prose itself (its own docstring states this explicitly) — a string comparison would fail a
    perfectly correct port for exactly this reason.
  - the «Ahora» label is kept LITERAL (`STATE «Ahora»:`, not translated to `STATE «Now»:`): it names
    the actual `## Ahora` heading `docs/STATE.md` carries on disk today, so translating the label would
    make it a false pointer to a heading that does not exist under that name.
  - `journal.read(root)[-5:]` replaces v2's `journal.read(root, limit=5)` — v3's `journal.read` never
    grew a `limit=` keyword (it returns `(rows, exists)`), so the last-5 slice is taken by the caller.
  - CUT: the trailing `instrument.record_session_footprint(...)` call — v2's M5 footprint-observer
    series has no v3 successor yet (unlike `record_compaction`, which `v3.memory.precompact.record`
    already redirects to `v3.economy.store`); nothing in `build_payload`'s return value or FACTS
    depended on that call's result even in v2 (its return value was discarded there too), so cutting it
    changes no observable behaviour of this function.
  - nothing else. `_state_now`, `_fresh_docs` and the section-assembly order are the same law, moved.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import journal
from .docs_manifest import SEAL_RE, body_of, doc_set, split_seal
from .projection import current_block, open_increment


def _state_now(root: Path) -> list[str]:
    state = Path(root) / "docs" / "STATE.md"
    if not state.exists():
        return []
    body = body_of(state.read_text(encoding="utf-8"))
    m = re.search(r"^## Ahora.*?(?=\n## )", body, re.DOTALL | re.MULTILINE)
    sect = m.group(0) if m else ""
    return [ln for ln in sect.splitlines() if ln.strip()][:11]


def _fresh_docs(root: Path, n: int = 4) -> list[str]:
    items: list[tuple[str, str]] = []
    for d in doc_set(Path(root)):
        seal, _ = split_seal(d.read_text(encoding="utf-8"))
        m = SEAL_RE.match(seal) if seal else None
        if m:
            items.append((m.group(2), str(d.relative_to(root))))
    items.sort(reverse=True)
    return [f"{rel} ({ts})" for ts, rel in items[:n]]


def build_payload(root: Path, *, session: str = "", source: str = "") -> str:
    root = Path(root)
    lines = ["=== Meta-Factory · memory rehydration (SessionStart) ==="]
    lines.append(f"Open increment: {open_increment(root) or 'none'}")
    blk = current_block(root)
    if blk:
        lines += ["Projection " + ln for ln in blk.splitlines() if ln.startswith("- ")]
    now = _state_now(root)
    if now:
        lines.append("STATE «Ahora»:")
        lines += ["  " + ln for ln in now]
    evs, _ = journal.read(root)
    tail = evs[-5:]
    if tail:
        lines.append("Latest facts (journal):")
        for e in tail:
            tag = e.get("station") or e.get("query") or e.get("subagent_type") or ""
            lines.append(f"  {e.get('ts', '')} {e.get('kind', '')} {tag}")
    fresh = _fresh_docs(root)
    if fresh:
        lines.append("Fresh docs (ADR-009 seal): " + " · ".join(fresh))
    lines.append("Orientation: `meta check` (re-verify > recall) · "
                 "`grep -rn <topic> docs/` (the slice — direct retrieval) · "
                 "`meta checkpoint` (project facts without narrating)")
    payload = "\n".join(lines)
    journal.append(root, "session_start", session=session, injected=len(lines))
    return payload
