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

#: What "the corpus" means for the escape rule: the documentary memory a session would actually
#: carry. Not the whole tree — code is read on demand and is not injected.
CORPUS_GLOBS = ("CLAUDE.md", "docs/**/*.md")

#: Tool names that READ. Used for `read_events`; write/execute tools are counted separately by the
#: ledger's `tool_uses`, because a leaf that edits a lot and reads nothing is a different animal.
READ_TOOLS = ("Read", "Grep", "Glob", "NotebookRead", "WebFetch", "WebSearch")


def corpus_tokens(root: Path) -> tuple[int, int, int]:
    """(estimated tokens, chars, files) over `CORPUS_GLOBS`. Pure file-IO."""
    chars = 0
    files = 0
    for pattern in CORPUS_GLOBS:
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
    """(a) of the escape rule. `fits` is the clause ADR-019 §6 hangs on.

    `files == 0` is reported as such and never as infinite headroom — an empty measurement is the
    Lock #1 shape, and the caller is expected to treat it as a failure rather than as good news.
    """
    tokens, chars, files = corpus_tokens(root)
    return {
        "corpus_tokens": tokens, "corpus_chars": chars, "corpus_files": files,
        "window_tokens": CONTEXT_WINDOW_TOKENS,
        "headroom_tokens": CONTEXT_WINDOW_TOKENS - tokens,
        "headroom_pct": round(100.0 * (CONTEXT_WINDOW_TOKENS - tokens) / CONTEXT_WINDOW_TOKENS, 2),
        "fits": tokens < CONTEXT_WINDOW_TOKENS,
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
