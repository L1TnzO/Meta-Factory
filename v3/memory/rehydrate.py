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

V3-INC12 P3 (node `N-0086`) ADDS a SECOND payload, `leaf_context` / `LeafContext`, below
`build_payload` and does not touch it (the parity witness above stays green because nothing it
exercises changed). The two payloads address two different readers and are shaped accordingly:
`build_payload` addresses an OPERATOR opening a session — prose, a banner, orientation pointers,
because a human benefits from being oriented. `leaf_context` addresses a bounded generation LEAF the
host (`v3.host.session.generate`) is about to call — no banner, no orientation, nothing beyond what
`docs/spec/15-plan-and-memory.md §6` (D2, anti-drift) says must travel into every call: why the task
exists (ancestry), what else its arc still owes (open siblings) and how the arc will be known done
(acceptance, derived — see `leaf_context`'s own docstring for the gap the node schema leaves here).
Bounded by construction (I-7) to ids and one-line titles, never node bodies — content-shaped handoff
is precisely what `docs/spec/15-plan-and-memory.md §2` measured decaying across sessions here.

THE FACTS THIS FUNCTION DERIVES (unchanged from v2, and what the parity witness compares): the open
increment (or its absence) — `v3.memory.projection.open_increment`; the persisted projection of RTM +
open increment — `v3.memory.projection.current_block` (a read of the block ALREADY in `docs/STATE.md`,
never a live re-derivation — `meta checkpoint` is what refreshes it); the STATE «Ahora» slice — a
regex slice of `docs/STATE.md`'s own `## Ahora` section, reusing `v3.memory.docs_manifest.body_of` to
strip the doc's content-address seal first; the journal's tail — `v3.memory.journal.read`, sliced to
the last 5 records (v3's `journal.read` has no `limit=` keyword the way v2's did, so the slice is taken
here instead); which docs are freshest — `v3.memory.docs_manifest.doc_set` + `split_seal` + `SEAL_RE`,
reused rather than re-implemented, exactly per this slot's contract.

CORRECTION EARNED BY EXECUTION, not by re-reading the spec (ADR-032 A5) — same phase, same node.
§15.6 clause 2 names the scope `root_of_current`, and the first draft of `leaf_context` below read
that literally as the TREE root (`ancestry(...)[0]`). Rendering the live payload for `N-0086` made the
gap visible: this project's plan is a SINGLE-ROOTED tree, so "root of current" degenerates to "the
entire backlog" — a 59-node "Open in this arc" section for one leaf, the exact drift §15.6 exists to
stop. The fix lives in the CALLER, not the algebra: `LeafContext.arc` now resolves to the nearest
ancestor (including the node itself) whose `kind` is `increment` or `direction` — see `_resolve_arc`
below — falling back to the tree root only when no such ancestor exists. `open_set` itself is
untouched; it already takes any root, and choosing WHICH root was always the caller's decision to make.

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
from dataclasses import dataclass
from pathlib import Path

from . import journal, plan_tree
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


# ══════════════════════════════════════════════════════════════════════════════════════════════
# LeafContext — the SECOND payload (V3-INC12 P3, node `N-0086`); see the module docstring's
# "V3-INC12 P3 ADDS" paragraph for why it is shaped so differently from `build_payload` above.
# ══════════════════════════════════════════════════════════════════════════════════════════════

#: one-line-per-node bound (I-7): a title longer than this is cut with an explicit ellipsis, never
#: silently — a hidden truncation is how a bounded bus stops being evidence.
_TITLE_LIMIT = 100
#: `open_siblings` beyond this many are summarised, never enumerated (spec §15.6's own bound).
_MAX_OPEN_SIBLINGS = 12
#: the whole rendered payload never exceeds this (spec §15.6's own bound).
_MAX_RENDER_CHARS = 2000

_HEADING = ("=== plan context (host-injected, spec 15.6 D2 anti-drift) — pointers only: why this "
           "task exists and what its arc still owes, never the node bodies ===")


class UnknownPlanNode(LookupError):
    """Raised by `leaf_context`, never swallowed there — see that function's own docstring for why a
    raise, and not an empty context, is the honest answer to an id absent from the tree."""


def _truncate(text: str, limit: int = _TITLE_LIMIT) -> str:
    """Collapse to one line and cut at `limit` chars with an explicit `…` — never silently: a
    truncation nobody can see is indistinguishable from a title that was simply short."""
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)] + "…"


def _sibling_label(node: dict) -> str:
    """The one-line label for an OPEN SIBLING. A `blocked` sibling's `trigger` rides along here —
    it IS the reopening condition, the one exception §15.6's gap note carves out of "title only":
    every OTHER node field (`evidence`/`reason`/`origin`) never appears, blocked or not."""
    title = str(node.get("title") or "")
    if node.get("state") == "blocked":
        trigger = " ".join(str(node.get("trigger") or "").split())
        if trigger:
            title = f"{title}  (blocked — unblocks when: {trigger})"
    return _truncate(title)


def _derive_acceptance(arc_id: str, open_count: int) -> str:
    """The node schema carries NO `acceptance` field — `docs/spec/15-plan-and-memory.md §6`'s own
    "a gap this phase must NOT paper over" note. This is not silence about it: it REFUSES to invent
    one (INC-5's law — refusing to assert is a valid answer), states that refusal in the string
    itself, and then gives the one condition the algebra CAN actually derive: closure is structural
    (§15.3 rule 1, the D3 mechanism) — the arc is done once none of its own descendants, nor itself,
    are `open` or `blocked`. A richer notion of "done" is not decidable from this data; claiming one
    would be exactly the fabrication `leaf_context` refuses elsewhere in this module.

    Takes a COUNT, not the id list: the ids are already printed one per line directly above, in
    `render()`'s "Open in this arc" section — re-listing them here would be the same node twice on a
    bus that is bounded precisely so nothing rides it twice."""
    if not open_count:
        return (f"no declared acceptance condition (the node schema carries none); besides this "
                f"leaf, the algebra finds no other open or blocked node under arc {arc_id} — "
                f"nothing else left to derive")
    return (f"no declared acceptance condition (the node schema carries none); derived from "
            f"structural closure (spec 15.3 rule 1): arc {arc_id} is done once the {open_count} "
            f"open node(s) listed above close")


@dataclass(frozen=True)
class LeafContext:
    """The pointer-shaped context of ONE leaf. Every field is ids + one-line titles (I-7) — no
    `evidence`, no `reason`, no `origin`, and no node body beyond a blocked sibling's one-line
    `trigger` (`_sibling_label`'s own docstring names that one exception)."""

    node: str
    ancestry: tuple[tuple[str, str], ...]
    open_siblings: tuple[tuple[str, str], ...]
    arc: str
    acceptance: str

    def render(self) -> str:
        """The text `v3.host.session.generate` prepends to a leaf's prompt when `Slot.plan_node` is
        set. Pure — everything it needs already lives on `self` — and bounded (I-7): at most
        `_MAX_OPEN_SIBLINGS` sibling lines (then a count of the rest) and `_MAX_RENDER_CHARS` total,
        enforced here rather than merely intended, because a synthetic tree built to overflow both
        is exactly what this module's gate (`v3/verify/checks/leaf_context.py`) asserts against."""
        lines = [_HEADING, "", f"Ancestry (why this task exists), root -> current [{self.arc}]:"]
        for nid, title in self.ancestry:
            lines.append(f"  {nid}  {title}")
        shown = self.open_siblings[:_MAX_OPEN_SIBLINGS]
        lines.append(f"Open in this arc (what else it still owes), "
                     f"{len(self.open_siblings)} node(s):")
        if not self.open_siblings:
            lines.append("  (none — no other open node in this arc)")
        for nid, title in shown:
            lines.append(f"  {nid}  {title}")
        overflow = len(self.open_siblings) - len(shown)
        if overflow > 0:
            lines.append(f"  … and {overflow} more open in this arc")
        lines.append(f"Acceptance: {self.acceptance}")
        text = "\n".join(lines)
        if len(text) <= _MAX_RENDER_CHARS:
            return text
        marker = "\n… [payload bound reached, remainder withheld]"
        return text[: _MAX_RENDER_CHARS - len(marker)] + marker


def _resolve_arc(nodes: dict, chain_ids: list[str], node_id: str) -> str:
    """WHICH root `open_set` receives — a caller-side decision, never the spec algebra's (see the
    module docstring's "CORRECTION EARNED BY EXECUTION" paragraph for why the first draft got this
    wrong). Walk `chain_ids` (root -> ... -> current, the algebra's own `ancestry`) from the END —
    i.e. from `node_id` itself upward — and return the nearest node whose `kind` is `increment` or
    `direction`: the nearest enclosing ARC, not merely the tree's single root. Falls back to the tree
    root (`chain_ids[0]`) only when no such ancestor exists anywhere up the chain — the same shape
    as this project's own top-level directions, which have no `increment`/`direction` parent."""
    for nid in reversed(chain_ids):
        if nodes[nid].get("kind") in ("increment", "direction"):
            return nid
    return chain_ids[0] if chain_ids else node_id


def leaf_context(root: Path, node_id: str) -> LeafContext:
    """Derive ONE leaf's pointer-shaped plan context from `plan/tree.json`, through the spec's
    algebra (`v3.memory.plan_tree.algebra`, which execs `docs/spec/15-plan-and-memory.md`'s own
    `<!-- spec-impl: plan -->` block) — never a second copy of `ancestry` / `open_set`. `arc` (which
    root `open_set` is asked about) is resolved by `_resolve_arc` above, ALSO never a second copy of
    the algebra: it only picks a root already inside `ancestry`'s own chain.

    REFUSES (raises `UnknownPlanNode`) rather than returning an empty context when `node_id` is not
    in the tree: telling a leaf "you have no ancestry" when the truth is "that node does not exist"
    would read as completeness where there is none — the same "not measured must never read as
    zero" law INC-6 carries elsewhere in this project. `v3.host.session.Slot.problems()` turns this
    raise into a pre-spawn refusal, never a silently empty preamble.
    """
    root = Path(root)
    nodes = plan_tree.load(root)
    if node_id not in nodes:
        raise UnknownPlanNode(
            f"node {node_id!r} is not in the plan tree at {root} — refusing to fabricate an empty "
            f"context: 'no ancestry' would be a lie about a node that does not exist")
    ns = plan_tree.algebra(root)
    chain_ids = ns["ancestry"](nodes, node_id)
    arc_id = _resolve_arc(nodes, chain_ids, node_id)
    ancestry = tuple((nid, _truncate(str(nodes[nid].get("title") or ""))) for nid in chain_ids)
    open_arc_ids = ns["open_set"](nodes, arc_id)
    open_siblings = tuple((nid, _sibling_label(nodes[nid]))
                          for nid in open_arc_ids if nid != node_id)
    return LeafContext(node=node_id, ancestry=ancestry, open_siblings=open_siblings, arc=arc_id,
                       acceptance=_derive_acceptance(arc_id, len(open_siblings)))
