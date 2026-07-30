"""The context meter — the instrument ADR-019 §6 has been missing since the day it was written.

The decision "no retrieval index, discarded by measurement" is defensible, and it carries an expiry
condition: *the corpus still fits the window, and what we inject is still what gets read*. That
condition has been measured by nothing. A decision with an expiry condition and no meter cannot
notice its own expiry (§09.4 A-1) — it just quietly becomes wrong.

TWO NUMBERS, and they are not the same kind of number:

  **(a) headroom — corpus vs window.** Static and computable at any moment from the tree alone. Does
  the pinned corpus still fit, with what margin. This one needs no model call and is emitted on
  every run.

  **(b) relevance ratio — at the LEAF.** §10.6 describes this as "combined with the `PostToolUse`
  read events already captured". Those events are precisely the ones that went silent for 17 days,
  and in v3 they will not come from a CLI hook at all: they come from the host's own typed stream.

  The version §10.6 imagines — how much of what is injected PER NODE is read — needs the node tree
  (§15.6), which is INC-12. So this measures the ratio a leaf at a time, in exactly those words:
  context injected into the leaf, against the leaf's read events and what they pulled back in. It
  is deliberately the smaller claim; promising the per-node version here would be describing an
  instrument nobody built.

THE UNITS, spelled out because a ratio with unstated units is how a meter starts lying:
  `injected_tokens`  the leaf's context total BEFORE its first turn (system prompt + tools + memory)
  `read_events`      how many read-class tool uses the leaf made
  `read_tokens`      how much the context GREW across the leaf — what reading dragged in
  `relevance_ratio`  read_tokens / injected_tokens — how much the leaf had to go and fetch relative
                     to what we pre-loaded for it. High means we injected the wrong things.
"""

from __future__ import annotations

from pathlib import Path

from . import store

SERIES = "meter"

#: The model's context window, in tokens. PINNED DATA with a validity window, in the shape §07.6
#: calls the one honest mechanism against stale numbers: value + when it was true + what re-opens it.
#: Value AS_OF 2026-07-30 (Claude Opus/Sonnet family). RE-MEASURE TRIGGER: the next model generation,
#: or the 2026-09-01 pricing re-pin of the assumption ledger — whichever comes first. Do not trust
#: this number past its trigger; a headroom computed against a stale window is worse than none.
CONTEXT_WINDOW_TOKENS = 200_000

#: Estimator, and it is named an ESTIMATOR rather than a measurement. 4 chars/token is the usual
#: English-prose approximation; the corpus is prose plus code fences, so this errs slightly high.
#: It is used only for a HEADROOM ratio, where a consistent bias cancels — never for billing.
CHARS_PER_TOKEN = 4

#: TWO corpora, and conflating them is how this meter over-claimed on its first run.
#:
#: ADR-019 §6 clause (a) is «el corpus RELEVANTE excede confiablemente la ventana USABLE». The ADR
#: had already measured the whole of `docs/` at ~269k tokens on 2026-07-08 and said so in the same
#: breath as its mitigation: it «ya se fetchea (Read/Grep), no se inyecta entero». So reporting the
#: full tree as if it were clause (a) would announce an expiry the decision explicitly priced in.
#:
#: What clause (a) is actually about is what a session carries BY CONSTRUCTION — the entry set every
#: session pays for whether it needs it or not. That is what must fit. The full corpus is reported
#: beside it as the GROWTH signal, which is the number that decides whether fetching stays viable.
ENTRY_GLOBS = ("CLAUDE.md", "docs/STATE.md")
CORPUS_GLOBS = ("CLAUDE.md", "docs/**/*.md")

#: The full-corpus measurement ADR-019 recorded, kept so growth is a delta rather than an
#: impression. Assumption-ledger shape: value + when it was true + what re-opens it. RE-MEASURE
#: TRIGGER: this gate, on every run — which is the point of building it.
CORPUS_BASELINE_TOKENS = 269_000
CORPUS_BASELINE_AS_OF = "2026-07-08"

#: Tool names that READ. Used for `read_events`; write/execute tools are counted separately by the
#: ledger's `tool_uses`, because a leaf that edits a lot and reads nothing is a different animal.
READ_TOOLS = ("Read", "Grep", "Glob", "NotebookRead", "WebFetch", "WebSearch")


def corpus_tokens(root: Path, globs=CORPUS_GLOBS) -> tuple[int, int, int]:
    """(estimated tokens, chars, files) over `globs`. Pure file-IO."""
    chars = 0
    files = 0
    for pattern in globs:
        for path in sorted(Path(root).glob(pattern)):
            if not path.is_file():
                continue
            try:
                chars += len(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
            files += 1
    return chars // CHARS_PER_TOKEN, chars, files


def headroom(root: Path) -> dict:
    """(a) of the escape rule, decided on the ENTRY set and reported beside the growth signal.

    `fits` answers clause (a) about the corpus a session carries by construction. `corpus_tokens`
    and `corpus_growth_pct` answer the question clause (a) does NOT ask but that decides whether
    the fetch-don't-inject mitigation stays viable: how fast the documentary memory is growing
    against the number the decision was made on.

    `entry_files == 0` or `corpus_files == 0` is reported as such and never as infinite headroom —
    an empty measurement is the Lock #1 shape, and the caller must treat it as a failure rather
    than as good news.
    """
    entry, _, entry_files = corpus_tokens(root, ENTRY_GLOBS)
    total, chars, files = corpus_tokens(root, CORPUS_GLOBS)
    return {
        "entry_tokens": entry, "entry_files": entry_files,
        "corpus_tokens": total, "corpus_chars": chars, "corpus_files": files,
        "window_tokens": CONTEXT_WINDOW_TOKENS,
        "headroom_tokens": CONTEXT_WINDOW_TOKENS - entry,
        "headroom_pct": round(100.0 * (CONTEXT_WINDOW_TOKENS - entry) / CONTEXT_WINDOW_TOKENS, 2),
        "fits": entry < CONTEXT_WINDOW_TOKENS,
        "corpus_baseline_tokens": CORPUS_BASELINE_TOKENS,
        "corpus_baseline_as_of": CORPUS_BASELINE_AS_OF,
        "corpus_growth_pct": round(100.0 * (total - CORPUS_BASELINE_TOKENS)
                                   / CORPUS_BASELINE_TOKENS, 1),
    }


def leaf_relevance(injected_tokens: int | None, final_tokens: int | None,
                   tool_uses: dict | None) -> dict:
    """(b) of the escape rule, for ONE leaf. Every field is `None` when its input was absent —
    never 0, because "the leaf read nothing" and "the host was never told" are different facts and
    this whole increment exists because they were once the same number."""
    uses = tool_uses or {}
    events = sum(count for name, count in uses.items() if name in READ_TOOLS) if uses else None
    grew = (final_tokens - injected_tokens
            if injected_tokens is not None and final_tokens is not None else None)
    ratio = (round(grew / injected_tokens, 4)
             if grew is not None and injected_tokens else None)
    return {"injected_tokens": injected_tokens, "final_tokens": final_tokens,
            "read_events": events, "read_tokens": grew, "relevance_ratio": ratio}


def emitted(record: dict) -> list[str]:
    """Which of (b)'s fields a meter record actually carries a value for.

    The gate is on ABSENCE: an observer that emits silence is the failure (§the increment's own
    gate design). So the law needs to name what "emitting" means, and it means a non-None value —
    a key that is present and null is silence wearing a schema.
    """
    return [k for k in ("injected_tokens", "read_events", "read_tokens", "relevance_ratio")
            if record.get(k) is not None]


def record_leaf(root: Path, *, leaf: str, injected_tokens: int | None, final_tokens: int | None,
                tool_uses: dict | None, categories: list | None = None) -> tuple[dict, bool]:
    """Append one leaf's (b) measurement. `categories` is `ContextUsageResponse.categories` verbatim
    when the host got one — kept raw so a later reader can re-derive without trusting this fold."""
    entry = {"ts": store.now(), "kind": "leaf", "leaf": leaf,
             **leaf_relevance(injected_tokens, final_tokens, tool_uses),
             "categories": categories or []}
    return entry, store.append(root, SERIES, entry)


def read(root: Path, *, since: str = "", until: str = "") -> tuple[list[dict], bool]:
    return store.read(root, SERIES, since=since, until=until)


def latest(root: Path) -> dict | None:
    rows, _ = read(root)
    return rows[-1] if rows else None
