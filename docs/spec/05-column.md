<!-- meta:doc sha=3a40e3401881dfa583b417521e3f1dfa04ce47fb updated=2026-07-27T21:41Z -->
# 05 — The column: hooks, agents, delegation harness (descriptive)

> The COLUMN is the trust chain. By doctrine it is written and reviewed with one's own eyes and is
> **never delegated** (`docs/reference/SELF-IMPROVEMENT.md §3`). Everything in this file is therefore
> hand-authored code today, and must stay hand-authored in v3.

## 1. Hook inventory (12 hooks)

| Hook | Event : matcher | Wiring | Blocks / writes | On failure |
| --- | --- | --- | --- | --- |
| `proof_protect.py` | PreToolUse: `Write\|Edit\|MultiEdit`, `Bash` | global (`settings.json:16,23`) | denies any write/read-through-Bash targeting `.proof/**` (`:37-56`); mirrored by `permissions.deny` (`settings.json:4-9`) | exit 2 deny |
| `increment_guard.py` | PreToolUse: `Write\|Edit\|MultiEdit` | global (`:17`) | blocks editing a NON-`.md` file when no increment is open at that level (`:21-40` → `cadence.edit_allowed`) | exit 2 deny; permits on doubt (best-effort) |
| `gate_guard.py` | PreToolUse: `Bash` | global (`:24`) | blocks `meta station mK` if the predecessor is not green, or is green with uncommitted cadence debt (`:56-69`) | exit 2 deny |
| `commit_guard.py` | PreToolUse: `Bash` | global (`:25`) | blocks `git commit` when the active station (`.proof/active.json`) is not green (`:29-41`) | exit 2 deny |
| `doc_stamp.py` | PostToolUse: `Write\|Edit\|MultiEdit` | global (`:32`) | on any `.md` write runs `meta doc-sync`: re-stamps the content sha and regenerates `INDEX.md` (`:16-21`) | never blocks |
| `mem_capture.py` | PostToolUse: `*` | global (`:37`) | records a `kind='tool'` metric on EVERY tool call (`:40-41`); appends a `delegation` journal event on subagent spawn (`:46-53`) | never blocks |
| `context_nudge.py` | PostToolUse: `*` | global (`:38`) | advisory only: anti-re-read nudge on the 3rd Read of the same target, and a ~120k-token checkpoint nudge (`:118-142`) | never blocks |
| `stop_proof.py` | Stop | global (`:45`) | `hermetic.preflight` → trust / block / rerun; re-runs `verify --rerun` unless trusted; blocks the turn if the station is non-green (`:42-57`); backstop blocks if a green gate is left uncommitted (`:58-68`) | exit 2 deny |
| `mem_rollup.py` | Stop | global (`:46`) | parses `transcript_path`, computes a token/cost rollup, records `kind='rollup'` (`:19-27`) | never blocks |
| `session_start.py` | SessionStart | global (`:52`) | prints `rehydrate.build_payload`: open increment + facts projection + STATE `Ahora` + latest facts + freshness (`:16-22`) | never blocks |
| `pre_compact.py` | PreCompact | global (`:57`) | writes a pre-compaction snapshot of live increment + gates + plan pointer (`:31-34`) | never blocks |
| `blast_radius.py` | PreToolUse: `Write\|Edit\|MultiEdit` | **per-agent** — only in `generator.md:6-11` | inert without a manifest; else denies writes outside `allow_globs` ∪ verdict ∪ `.gen/` (`:57-64`) | exit 2 deny; **fail-CLOSED** if the manifest exists but the law/manifest is broken (`:50-60`) |
| `verdict_required.py` | Stop → auto-converted to SubagentStop | **per-agent** — only in `generator.md:12-15` | inert without a manifest; else (1) the verdict must be well-formed (`:81-85`), (2) the git-observed footprint must be inside the slot (`:86-98`) | exit 2 deny; fail-CLOSED on any undecidable state |

> **Finding (asymmetry):** `evaluator.md` declares **no hooks at all** — unlike `generator.md`. Per-agent
> hook wiring lives in Markdown frontmatter, so an omission is invisible. Recorded as debt (§09.3).

## 2. The slot law (`seed/delegation.py`)

`.gen/active_slot.json`. **Required** (`MANIFEST_REQUIRED_KEYS`, `:42`):
`slot_id · allow_globs · verdict_path · iteration_gate_cmd · acceptance_gate_cmd`.

| Field | Constraint | Anchor |
| --- | --- | --- |
| `allow_globs` | list of path globs (fnmatch) | `:103-105,184` |
| `iteration_gate_cmd` / `acceptance_gate_cmd` | non-empty `list[str]` each — the **split gate**: fast on every retry, heavy once | `:107-110` |
| `iteration_budget_s` | number in `(0, 15]` | `:44,112-114` |
| `max_wall_s` | number in `(0, 1800]` | `:48,115-117` |
| `token_budget` | positive int | `:118-120` |
| `file_budget` | positive int (max LOC per file) | `:121-126` |
| `baseline_dirty` | `list[str]` — pre-existing dirty paths, exempted from the footprint check | `:148-151` |
| `trust_level` | enum `low\|medium\|high` | `:60,128-130` |
| `cost_class` | enum `cheap\|standard\|premium` | `:61,131-133` |
| `side_effects` | subset of `files\|network\|process` | `:62,134-141` |
| `forbidden_tools` | `list[str]` | `:142-144` |
| `single_responsibility` | non-empty string | `:145-147` |
| `model_policy` | dict, keys ⊆ `temperature, seed, strict_json` | `:63,152-159` |

Two pure functions carry the law:

```python
write_allowed(root, slot, fp)        # :174-185  → under .gen/, == verdict_path, or matches allow_globs
footprint_problems(slot, changed)    # :188-213  → every git-changed path ∈ allow_globs ∪ {verdict} ∪ .gen/** ∪ baseline_dirty
```

The closed-enum fields (`trust_level`, `cost_class`, `side_effects`, `forbidden_tools`,
`single_responsibility`, `model_policy`) were harvested from the Professor-Web-Factory `WorkOrder`
vocabulary and made VALIDATED rather than decorative: a malformed work order is rejected **before**
the spawn.

## 3. The verdict contract

`VERDICT_REQUIRED_KEYS = ("slot_id", "status", "check", "exit_code")` (`:34`);
`VERDICT_STATUSES = ("green", "red")` (`:35`).

`verdict_ok()` (`:250-281`) requires: the file exists, parses as a JSON dict, has all required keys, has
a valid status; and **if `status == "green"`**: `acceptance_exit_code == 0` when an acceptance gate was
declared (`:271-275`), and the file-size budget is respected (`:276-280`).
`generator.md:36-40` prescribes three further keys (`acceptance_exit_code`, `log_ref`, `summary`) that
are conventional, not enforced.

## 4. Blast radius vs footprint — why both exist

`blast_radius.py` intercepts a LIVE `Write`/`Edit`. It **cannot see Bash-mediated writes**
(`echo > file`, `sed -i`, a script that writes). `verdict_required.py` closes that hole at SubagentStop:
it runs `git status --porcelain --untracked-files=all` (staged + unstaged + untracked, both rename
sides, rebased through `git rev-parse --show-prefix` for factory subdirs) and applies
`footprint_problems` (`:37-62, 91-98`).

The `generate-slot` skill adds a third, belt-over-suspenders check after acceptance:
`python3 -m metafactory.verify.checks.slot_footprint . --live` (`SKILL.md:79-83`) — this catches a
generator killed mid-flight whose SubagentStop never fired.

> Three layers for one property, because the property is *"the agent changed only what it was allowed
> to change"* and each layer sees a different slice of reality. Keep all three in v3; the SDK changes
> how each is expressed, not how many are needed (§10.4).

## 5. Roles and column scope

Canonical roles (`agent_roles.py:25-34`): `orchestrator · generator · verifier · reviewer · evaluator`.
Legacy synonyms (`:39-42`): `writer→generator`, `triage→verifier`. `ALLOWED = CANONICAL ∪ LEGACY` (`:46`);
the `roles` gate enforces the closed set over every `.claude/agents/*.md` in meta and in all factories.

Column scope (`column_scope.py`):

```
_ENFORCEMENT = {proof_protect, increment_guard, commit_guard, stop_proof, gate_guard}   # :23-29
_DELEGATION  = {blast_radius, verdict_required}                                          # :32-35
_MEMORY      = {doc_stamp, mem_capture, mem_rollup, session_start, pre_compact}          # :38-44
META_COLUMN    = ENFORCEMENT ∪ DELEGATION ∪ MEMORY     # 11 roles  :49
FACTORY_COLUMN = {proof_protect, increment_guard, commit_guard, stop_proof} ∪ DELEGATION # 6 roles  :60-62
META_ONLY      = META_COLUMN − FACTORY_COLUMN          # each with a rationale string   :65-76
```

`least_priv` proves the on-disk factory projection equals `FACTORY_COLUMN` exactly.

## 6. Increment lifecycle (`seed/lifecycle.py`)

An **increment** = a `.md` in a level's `docs/work/` whose header says `Status: **OPEN**` (or legacy
`Estado: **ABIERTO**` — dual-accept, `_OPEN_RE:33`, `open_increment_in:37-52`).

- Level is resolved by path arithmetic (`level_workdir:86-102`).
- `edit_allowed(root, fp)` (`:105-118`): a NON-`.md` file requires an open increment at ITS level; `.md` is always allowed.
- `debt(root)` (`:141-150`): an open increment **plus** uncommitted non-`.md` files ⇒ debt.
- Truth is the git tree plus the doc header; the module **never auto-commits** (`:17-23`).
- Placement of the doc is DERIVED, not chosen: `meta increment open --parent … --type …` computes `docs/work/<root-arc-slug>/NN-<SLUG>-INCREMENT.md` (ADR-030), and the `lineage` gate enforces path↔header agreement.

## 7. Session lifecycle (the non-discretionary memory trigger)

| Moment | Hook | Effect |
| --- | --- | --- |
| session start | `session_start` | injects the rehydrate payload into context |
| every tool call | `mem_capture` | writes a `tool` metric **unconditionally**; on an `Agent` spawn also appends a `delegation` journal event |
| pre-compaction | `pre_compact` | writes a non-destructive snapshot of increment + gates + plan pointer, re-injected on the next `SessionStart(source=compact)` |
| turn close | `mem_rollup` | parses the transcript, writes a `rollup` metric (tokens, cost) |
| turn close | `stop_proof` | `preflight` → `block` (exit 2) / `trust` (clean pin, skip live re-run) / `rerun` (`verify --rerun`); then a cadence backstop blocks if a green gate is left uncommitted. Anti-loop valve: `stop_hook_active` short-circuits to 0 |

**The write trigger is the hook wiring, never the model's judgment.** This is the system's answer to
"when does memory get written", and it places it in the majority position of the literature
(§09.5: only 9.3 % of studied systems leave the write to model discretion alone).

## 8. Known fragilities of the current mechanism (facts, not opinions)

| Fragility | Evidence |
| --- | --- |
| cwd sensitivity | mutation guards were fixed with absolute `sys.path` anchoring, but `stop_proof`/`session_start`/`doc_stamp`/`mem_rollup` remain cwd-relative; a leaked Bash cwd into a subdirectory can block turn close with a false red |
| per-agent wiring is invisible | hooks live in Markdown frontmatter; `evaluator` silently has none |
| metrics by text parsing | `mem_rollup` parses a transcript; the delegation metric once read 0.0 % for weeks because the emitter matched the OLD tool name (`Task` → `Agent`, renamed in CLI v2.1.63) |
| 12 processes per turn | every hook is a fresh Python process that re-imports the package |
| new agent needs a restart | an on-disk agent file is registered at session start only |
