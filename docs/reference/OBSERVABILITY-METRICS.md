<!-- meta:doc sha=af68e85597ba79d1d618ee5f3a82e6e797fce907 updated=2026-07-11T16:01Z -->
# Observability and metrics — absolutely free capture (zero model calls)

| Field | Value |
| --- | --- |
| Document | Design of the Meta-Factory's metrics subsystem and of the factories it produces |
| Status | **Living draft / proposal** (not ratified) |
| Origin | Conversation 2026-06-13: "empezar a medir muchas cosas… QUE SEA ABSOLUTAMENTE GRATIS, no se debe llamar a un modelo. Lo que no se mide, no se mejora." |
| Inherits | the Tier 0 facts memory (`MEMORY-ARCHITECTURE.md §2`), the verdict bus (`CONTEXT-ECONOMY.md`), ASF/ADR-019 (deterministic journal), ADR-023 (delegation counter) |
| Inviolable MUST | **No metric costs a model call. Everything is file-IO + deterministic arithmetic.** |

> This is the instrument that replaces "I can tell something isn't working by vibes". It is the
> facts half of memory (Tier 0): where the journal captures *events*, this subsystem captures
> *series* (counters, durations, costs, rates). Both are free, deterministic, written by hooks.
> This doc is the authority on the mechanism; `MEMORY-ARCHITECTURE.md` only points here.

---

## 1. The principle and its boundary

**We measure only what is mechanically derivable**: counters, durations, tokens, costs, pass/fail,
frequencies, rates. That comes from files the harness already writes + arithmetic. Zero model.

**We do NOT measure what requires judgment** (was this turn productive? is this a good decision?).
That would mean spending a model to interpret — it violates the MUST. If ever wanted, it goes as a
separate, opt-in layer, outside this subsystem. The boundary is exactly the deterministic shadow's
boundary (ADR-023): fact detection → free; meaning → something else.

---

## 2. The free sources (verified in the environment, 2026-06-13)

Everything below exists TODAY and is readable without a model:

| Source (already on disk) | Metrics it gives | How (free) |
| --- | --- | --- |
| **`~/.claude/<proj>/<session>.jsonl`** (transcript) | tokens per turn (`input`, `output`, `cache_creation`, `cache_read`), **cost**, **cache-hit-rate**, model per message, tool-call count, `server_tool_use` (web search/fetch) | parse the JSONL; every assistant msg carries `"usage":{...}`. VERIFIED present |
| **`~/.claude/stats-cache.json`** (computed by Claude Code) | per day: `messageCount`, `sessionCount`, `toolCallCount`, **`tokensByModel`** | read the JSON. VERIFIED: already shows the Opus/Sonnet/Haiku split |
| **hooks** (PreToolUse, PostToolUse, Stop, SessionStart, PreCompact, SessionEnd) | **how many times each hook fires and after which tool**, tool duration (Pre/Post bracketing), compaction events, sessions | the hook appends a line to `metrics.jsonl` when it fires. Zero model (ASF already proves a hook writes for free: `session_journal.py`) |
| **`gates.ledger.json` / `journal.jsonl`** | gate pass/fail per station, station duration, **delegation rate** (`delegation` event, ADR-023), check red→green | derive from the line's artifacts (already deterministic) |
| **`.meta_check/<ts>.log` + verdicts** | `meta check` duration, ruff/mypy/pytest counts, green/red streak | parse the verdict (already bounded) or the log |
| **`~/.claude/telemetry/*.json`** | internal harness events (version, env, event names) — PARTIAL: they are `1p_failed_events` (telemetry that failed to send) | secondary source; useful for env/version, not reliable as a primary series |

**Immediate finding (from `stats-cache.json`, free, already available)**: on the heavy days of
building ASF, Opus dominated spend — 2026-05-31: 79% · 2026-06-05: 87% · 2026-06-07: 98% of tokens
were Opus, with Sonnet/Haiku marginal. Sub-delegation (G-3) was measured; it just wasn't looked at.
This is use case #1 of the subsystem.

---

## 3. Capture: `metrics.jsonl` (append-only, written by hooks, free)

- Every hook, when it fires, appends ONE structured line to `.claude/metrics/metrics.jsonl`
  (or extends the journal with `kind: metric`). Minimum fields:
  `{ts, hook, tool, session, run, station?, dur_ms?, exit?}`. Deterministic, no model,
  ~microseconds.
- A `Stop`/`SessionEnd` hook parses the `transcript_path` (already provided in the payload) and
  appends the session's token/cost/cache-hit rollup. Parsing a JSONL is file-IO: free.
- `metrics.jsonl` is **gitignored** (ephemeral development evidence, like `.meta_check/`), unless
  it is decided to version rollups (open decision §7).
- It is Tier 0 (facts): partially regenerable from transcripts + stats-cache; it is not the
  authority for meaning, it is a series of facts.

---

## 4. Aggregation and view: `meta metrics` (verdict bus, no model)

A CLI command reads `metrics.jsonl` (+ stats-cache + transcripts) and emits a **bounded verdict**
— the same bus doctrine: summary to context, raw series to disk. Sample output (all arithmetic):

```
VEREDICTO  metrics — sesión actual + últimos 7 días
COSTO      sesión: $X.XX (opus 98% · sonnet 2% · haiku 0%) · 7d: $YY.YY
DELEGACIÓN tasa 7d: 3% de turnos → subagente   ⚠ (objetivo informal ≥X%)
HOOKS      proof_protect 1.2k · gate_guard 340 · stop_proof 210 · post_edit_quality 180
TOOLS      Bash 41% · Edit 22% · Read 19% · Agent 3%   (p50 dur: Bash 800ms · Edit 40ms)
CACHE      hit-rate 92% (cache_read / input)   ← señal de costo
GATES      pass 47 · fail 6 · racha verde actual: 12
ARTEFACTO  .claude/metrics/metrics.jsonl
```

- **No model**: aggregates with stdlib (`json`, optional `sqlite3` for rollups, arithmetic).
- For heavy queries, an optional **SQLite** rollup (all stdlib, free) maintained by the CLI:
  "station duration p95", "cost per station", "delegation rate per increment".
- The same command feeds your visibility and mine: when I (or any orchestrator) need to know if
  something is wrong, I run `meta metrics`, I do NOT guess.

---

## 5. Cost model (free): price table × tokens

Cost is computed with a **static price table** (config, not a model) per model×token-type
(input/output/cache-write/cache-read) multiplied by the tokens captured from the transcript. It is
arithmetic. The table is updated by a reviewed diff when prices change. That way "cost" stops
being an unknown: it is a column of the verdict.

---

## 6. Bootstrap metrics (the first ones that matter, all free)

1. **Token/cost split by model** (Opus/Sonnet/Haiku) — measures G-3 (sub-delegation) directly.
2. **Delegation rate** (turns with a `delegation` event / total turns) — ADR-023's shadow, now
   with a denominator.
3. **Hook frequency and duration** — "cuántas veces se ejecutan y tras qué" (your literal
   request).
4. **Cache-hit-rate** — a cheap proxy for cost health; it drops when context gets messy.
5. **Cost per station / per increment** — "was this factory cheap?" made measurable.
6. **Green/red gate streak + time-to-green** — line health.
7. **Compaction events per session** (PreCompact) — context pressure, anti-economy.

---

## 7. Open decisions (need your input → crystallize into ADR-008)

- **Version rollups or leave everything gitignored?** Proposal: `metrics.jsonl` ephemeral
  (gitignored); a rollup curated per increment (e.g. total increment cost) can go to `work/` or to
  a versioned `metrics/SUMMARY` (proposed doc, not created — open decision) — that way historical
  cost survives without the raw stream's churn.
- **Alerting thresholds (WARN/BLOCK) or pure display?** Initial proposal: **pure display**
  (an observer, like the delegation counter). Forcing with BLOCK repeats the theater mistake
  (ADR-023). If a metric deserves a gate (e.g. cost per station > X), it is decided explicitly,
  after having the series — measure before forcing.
- **SQLite from day 1 or JSONL until it hurts?** Proposal: JSONL first (zero-dep); SQLite when a
  query justifies it. Measure before investing (same rule as retrieval).

---

## 8. Born in M5; relationship to memory

The metrics subsystem is part of the meta-station **M5 (memory & RTM)**: every factory is born
instrumented (capture hooks + `meta metrics`), it is never retrofitted. It is the *series* half of
the facts memory (Tier 0); `MEMORY-ARCHITECTURE.md §2` names it and points here. Honest caveat:
the exact payload fields of each hook must be verified against the live harness
(ASF/session_journal already does it — proof that it works); the transcript and stats-cache are
already verified (§2).
