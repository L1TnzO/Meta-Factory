<!-- meta:doc sha=c03e7a44d8043eff3c2e78239570264df024bfdc updated=2026-07-28T03:03Z -->
# 13 — Schemas: the complete data-schema reference (NORMATIVE, closes L2)

Method (per §12.2): the union of keys REALLY present in committed artifacts — `.proof/*.json`,
`stations/*.yml`, `factory.spec.yml`, `products/*/product.yml`, `seed/delegation.py`'s slot-law
constants, `.gen/*slot*.json`, `pinned_verdict.json` — documented field-by-field, grouped by
artifact. `tools/spec_schema_cover.py` collects that union mechanically (never from prose) and
requires each term to appear literally below; a phantom term injected under
`SPEC_SCHEMA_SABOTAGE=1` must fail it. This file does not repeat the trust-kernel algorithm
(`compute_proof_sha`/`recompute_passed`/`gate_recompute_ok`) — that is normative in
`14-kernel-reference.md §2-3` and is only cited here.

## 1. Proof record (`.proof/<station>.json`)

| Key | Type | Req/Opt (default) | Meaning | Anchor |
| --- | --- | --- | --- | --- |
| `station` | string | required | the station id this proof belongs to (`m00`, `s3`, …). | `seed/verifier.py:126-133` |
| `checks` | list of `{name, cmd, exit}` | required (may be `[]`) | one entry per check that ran, in run order. | `seed/verifier.py:110-121` |
| `checks[].name` | string | required | the check's declared name (from the station YAML). | `seed/verifier.py:121` |
| `checks[].cmd` | list of string | required | the resolved argv actually executed (recorded, not hashed — §14 §3 rule 2). | `seed/verifier.py:121` |
| `checks[].exit` | int | required | the real OS exit code (or `127` if the process could not launch — fail-safe, never absent). | `seed/verifier.py:113-121` |
| `passed` | bool | required (computed) | `recompute_passed(checks)`; never asserted independently. | `seed/verifier.py:127`, kernel `14-kernel-reference.md §2` |
| `proof_sha` | hex string | required (computed) | the digest; see §14 for what participates. | `seed/verifier.py:130`, kernel `14-kernel-reference.md §2` |
| `computed_at` | ISO-8601 UTC string (`YYYY-MM-DDTHH:MMZ`) | required | when this proof was written; provenance only. | `seed/verifier.py:129`, `utc_now()` `:29-30` |
| `writer` | string | required (constant `"seed/verifier.py"`) | which verifier wrote it — always the frozen trust root, never a factory or generated module. | `seed/verifier.py:131` |

**`proof_sha` participation** (do not restate the algorithm, see `14-kernel-reference.md §2-3`): only
`station` and the sorted `(checks[].name, checks[].exit)` pairs feed the digest. `checks[].cmd`,
`passed`, `computed_at`, `writer` are deliberately EXCLUDED — recorded for provenance/audit but never
hashed, which is what lets the machinery behind a check change without breaking a pin.

**Residual — `log_path` is NOT in the persisted file.** `verify_station()` writes the JSON to disk at
`seed/verifier.py:137` — a snapshot of the `proof` dict *before* `log_path` is added at `:142`. The
returned in-memory dict (consumed immediately by `cli._copy_metacheck_log()`, `cli.py:130-138`) carries
`log_path`; the committed/re-derivable `.proof/<station>.json` file on disk does not. A re-implementer
who assumes the two are the same dict will silently diverge from real behaviour.

**Out of L2 scope (excluded by the collector on purpose, `tools/spec_schema_cover.py:56-58`):**
`.proof/active.json` (`{root, slug, station, stations_dir, spec, at}` — the pointer the Stop hook reads
to know which station is in flight, `engine/runner.py:37-44`) and `.proof/ledger.json`
(`{"gates": [{station, proof_sha, at}, …]}` — an append-only record of opened gates, `seed/verifier.py:146-158`).
Neither is domain-structural in the same sense as a proof record; they are re-derivable pointers.

## 2. Station YAML (`src/metafactory/stations/*.yml`, `factories/*/stations/*.yml`)

A materialized station file is the EXECUTABLE realization the engine consumes verbatim (I-2: stations
are data). Loaded by `Station.from_dict()`.

### 2.1 Top-level keys

| Key | Type | Req/Opt (default) | Meaning | Anchor |
| --- | --- | --- | --- | --- |
| `id` | string | required | the station's stable id; drives natural-key ordering (`s9 < s10`). | `engine/station.py:14`, `engine/sequence.py:16-22` |
| `name` | string | optional (default = `id`) | a human label; carries no machine semantics. | `engine/station.py:15`, `station.py:29` |
| `activation` | string, effectively `"always"` \| `"off"` | optional (default `"always"`) | `!= "off"` ⇒ active. See the enum residual below. | `engine/station.py:16`, `.active` property `:42-43` |
| `builds` | list of dict | optional (default `[]`) | build actions applied before checks (§2.2). | `engine/station.py:17` |
| `checks` | list of dict | optional (default `[]`) | checks resolved to subprocess argv (§2.3). | `engine/station.py:18` |
| `requires_prev` | string \| null | optional (default `None`) | explicit single predecessor id; if unset AND `depends_on` is empty, the predecessor is "the previous active station in file order" (transparent through deferred ones). | `engine/station.py:19`, `engine/sequence.py:54-62,72-81`, `03-engine.md §4` |
| `depends_on` | list of string | optional (default `[]`) | explicit fan-in predecessors; ALL must be green (a DAG, cycle-checked at spec level — §3.4). | `engine/station.py:20` |
| `tier` | string, closed enum `"core"` \| `"harden"` | optional (default `"core"`) | the draft→harden DIAL: a `harden` station is deferred (skipped) under `product-run --mode draft`. | `engine/station.py:21-24`, `.active_in(dial)` `:45-49` |

**Residual — the `activation` enum is looser in practice than it looks.** `src/metafactory/spec/factory.schema.json:40`
declares `enum: [always, optional, off]`, and `engine/station.py:16`'s own comment still says
`# always | optional`. Neither is enforced: `validator.py` has no `_status_problem`-style check for
`activation`, `_norm_activation()` (`cli.py:61-69`) only special-cases the string forms of `off`/`false`/`no`/`0`
→ `"off"` and `on`/`always`/`true`/`yes`/`1` → `"always"`, passing any other string through verbatim (which
`Station.active` then reads as active, since it only tests `!= "off"`). A grep of every committed
`activation:` line in the repo (`src/metafactory/stations/*.yml`, `factories/*/stations/*.yml`,
`factories/*/factory.spec.yml`, `specs/*.yml`) finds exactly two values in the wild: `always` and `off`.
`optional` is dead vocabulary — declared in the schema and in a stale comment, never used, never enforced.

### 2.2 `builds[]` — build-action entries

`apply_builds()` dispatches on `action` (a closed enum enforced by an `else: raise ValueError` —
`codegen/renderer.py:60-97`); an unknown action is a construction-time error, not a runtime check.

| `action` | Extra keys (req unless noted) | Meaning | Anchor |
| --- | --- | --- | --- |
| `mkdir` | `path` | create a directory (and parents). | `renderer.py:4,61-64` |
| `write` | `dest`, `content` (optional, default `""`) | write `content` (after `{{var}}` substitution) verbatim to `dest`. | `renderer.py:5,65-69` |
| `render` | `src`, `dest`, `skip_if_exists` (optional, default `false`) | render ONE template file (`src` relative to `meta_root`) into `dest`. | `renderer.py:6,70-78` |
| `render_tree` | `src`, `dest`, `skip_if_exists` (optional) | render a whole template subtree (paths + content). | `renderer.py:7,79-81` |
| `copy_seed` | — | install the inherited column (verifier.py/column.md/etc — M1). | `renderer.py:8,82-83` |
| `generate` | `dest`, `via` (list of string, argv), `brief` (optional), `skip_if_exists` (optional) | the CREATIVE SLOT (C1, ADR-013): run `via` as a subprocess; it is the sole writer of `dest`. Never writes a verdict — a failing/absent-output generator leaves `dest` absent, and the station's own checks render the honest red. | `renderer.py:9,84-85,353-396` |
| `materialize_line` | `dest` | write the product line (`stations/<id>.yml` per `SpecStation`) from the spec — C2, I-2. | `renderer.py:10,86-87,129+` |
| `emit_harness` | — | write `.claude/{agents,commands,skills}` from `machinery.harness` (D2). | `renderer.py:11,88-89,238-264` |
| `emit_infra` | — | write the infra glue from `machinery.infra` (E1). | `renderer.py:12,90-91,267+` |
| `emit_mcp` | — | write the MCP glue from `machinery.mcp` (E2). | `renderer.py:13,92-93,267+` |
| `emit_boundary` | — | write the I-5 generated/domain boundary from spec DATA (M4). | `renderer.py:14,94-95,101+` |

Notes on the extra keys themselves:

| Key | Type | Req/Opt (default) | Meaning | Anchor |
| --- | --- | --- | --- | --- |
| `action` | string, closed enum (11 values above) | required | which build primitive to run. | `renderer.py:60` |
| `dest` | string (`{{var}}`-substituted) | required for `write`/`render`/`render_tree`/`generate`/`materialize_line` | the path (root-relative) the action writes to. Note the asymmetry: `mkdir` uses `path`, not `dest`. | `renderer.py:53-55` (`_render_path`) |
| `path` | string (`{{var}}`-substituted) | required for `mkdir` only | the directory to create. | `renderer.py:62` |
| `src` | string (relative to `meta_root`) | required for `render`/`render_tree` | the template source. | `renderer.py:71,80` |
| `content` | string (`{{var}}`-substituted) | optional (default `""`) | inline content for `write`. | `renderer.py:68` |
| `via` | list of string (each `{{var}}`-substituted, resolved against the chassis) | required for `generate` | the generator's argv — free DATA the plan chose (a deterministic scaffolder or `claude -p "<brief>"`, same seam, ADR-012). | `renderer.py:388` |
| `brief` | string (`{{var}}`-substituted) | optional | written to `.gen/<dest-name>.brief.md` (or `brief_dest` if given — not itself in any committed YAML today) and exposed to the generator as `METAFACTORY_BRIEF`. | `renderer.py:363-365,380-386` |
| `skip_if_exists` | bool | optional (default `false`) | for `render`/`render_tree`: leave an existing `dest` untouched (protects human-owned `domain/` code, I-5/M4). For `generate`: don't re-invoke a non-deterministic generator if the slot is already filled. | `renderer.py:16-20,74,369-370` |

### 2.3 `checks[]` — check entries

Every entry is `{name, kind, ...}` (`registry.py:3`); `resolve_check()` maps it to a subprocess argv,
dispatching on the closed `kind` vocabulary (29 entries — enumerated and cross-referenced against its
red-side witness in `04-verification.md §2-3`; not re-listed here to avoid a second source of truth).

| Key | Type | Req/Opt (default) | Meaning | Anchor |
| --- | --- | --- | --- | --- |
| `name` | string | required | the check's stable name; what the proof record and a requirement's `verified_by` address. | `registry.py:3` |
| `kind` | string, closed enum (29, `registry.KINDS`) | required | which resolver builds the argv. An unknown kind raises `ValueError` at construction time. | `registry.py:32-192` |
| `cmd` | list of string \| string | required for `kind: command` only | the literal argv to run (the only kind whose command is pure DATA with no resolver logic). | `registry.py:62-63` |
| `when` | dict (flat `key -> value`) | optional | a DATA-only guard: the check runs only if every `subst[key] == value`. A non-matching guarded check is skipped ENTIRELY — never enters the proof's `checks`, so an un-adopted product's `proof_sha` stays byte-identical. The per-check analogue of `station_activation` (§4.8). | `engine/runner.py:56-66` |

`resolve_check()`'s per-kind extra argv keys (the vocabulary a re-implementer needs to reproduce every
kind's subprocess call):

| Key | Used by kind(s) | Type | Req/Opt (default) | Meaning | Anchor |
| --- | --- | --- | --- | --- | --- |
| `workdir` | `product_env`, `infra_up`, `mcp_tools`, `eval_gate`, `eval_floor`, `live_run` | string | optional (default `"."`) | cwd for the check, relative to the factory/product root — the PRODUCT's own toolchain (DES-8). | `registry.py:99-105` (repeats per kind) |
| `bootstrap` | `product_env`, `infra_up`, `eval_gate`, `eval_floor`, `live_run` | list of string (argv) | optional (default `[]`) | a setup command run once before the proof command (e.g. `npm install`). | `registry.py:99-186` (repeats per kind) |
| `files` | `py_compile` | list of string | required | the files to `python -m py_compile`. | `registry.py:42-44` |
| `code` | `import_runs` | string | required | a Python snippet run via `python -c`. | `registry.py:45-46` |
| `file` | `artifact_contains` | string | required | the artifact path to grep. | `registry.py:47-49` |
| `marker` | `artifact_contains` | string | required | the literal string that must be present in `file`. | `registry.py:47-49` |
| `spec` | `spec_validate`, `rtm_closure`, `design_review` | string | required | the `factory.spec.yml` path to check. | `registry.py:50-55` |
| `path` | `pytest`, `isolation` | string | required for `pytest`; optional for `isolation` (default `"tests/test_isolation.py"`) | the pytest target. Not present in any committed station YAML today (both usages rely on the default / are hardcoded elsewhere) — declared in the resolver, unexercised as a literal key in the corpus. | `registry.py:56-59` |
| `up` | `infra_up` | list of string (argv) | optional (default `[]`) | the command that starts the infra in the background. | `registry.py:107-119` |
| `proof` | `infra_up` | JSON-able argv | required | the readiness/health-check command, retried until the infra is reachable. NOT the proof-record concept — same word, unrelated meaning (see §7 naming collisions). | `registry.py:107-119` |
| `down` | `infra_up` | list of string (argv) | optional (default `[]`) | teardown, always run. | `registry.py:107-119` |
| `timeout` | `infra_up` | int (seconds) | optional (only appended to argv if truthy) | the readiness retry window. | `registry.py:118-119` |
| `tools` | `mcp_tools` | list | optional (default `[]`) | the declared MCP tool contract, cross-checked against the live `tools/list`. | `registry.py:121-127` |
| `prove` | `mcp_tools` | JSON-able argv | required | the prober that speaks MCP to the generated server. | `registry.py:121-127` |
| `output` | `eval_gate`, `live_run` | string (path) | required (both kinds) | the real output to score. | `registry.py:129-172` |
| `degraded` | `eval_gate`, `live_run` | string (path) | required (both kinds) | a deliberately-bad output that MUST flip the gate red (the two-sided witness). | `registry.py:129-172` |
| `scorer` | `eval_gate`, `live_run` | JSON-able argv | required for `eval_gate`; optional for `live_run` (default `[]`) | the scorer command. | `registry.py:129-172` |
| `thresholds` | `eval_gate`, `live_run` | dict `{metric: float}` | required for `eval_gate`; optional for `live_run` (default `{}`) | the metric floors the scorer's output must clear. | `registry.py:129-172` |
| `evidence` | `eval_floor` | string (path) | required | the PINNED real evidence to re-verify against its own floor (ADR-025 §3, 0-model). | `registry.py:142-156` |
| `command` | `eval_floor` | JSON-able argv | required | the auto-gating driver command (a DIFFERENT key from `cmd`, and a different check kind than `kind: command` — see §7). | `registry.py:142-156` |
| `run` | `live_run` | list of string (argv) | optional (default `[]`) | the driver that produces a fresh live pin; run only if no pin exists yet (MAT-5). | `registry.py:157-172` |
| `properties` | `live_run` | JSON-able list | optional (default `[]`) | structural properties gated on the real output. | `registry.py:157-172` |
| `provider_env` | `live_run` | string | optional (default `""`) | the NAME of the env var whose presence signals a live provider is configured — the substrate never names the provider itself (ADR-012). | `registry.py:157-172` |
| `corpus` | `scenario_corpus` | string (path, relative to `meta_root`) | optional | the scenario manifest. Declared in the resolver (`registry.py:182-192`) but not set as a literal key in any committed station YAML today — every adopter relies on the resolver's implicit default path. | `registry.py:182-192` |
| `baseline` | `blast_radius` | string (path, relative to `meta_root`, default `"baseline_verdicts.json"`) | optional | the committed downstream-verdict baseline. Same status as `corpus`: declared, unexercised as an explicit key in the corpus. | `registry.py:174-181` |

## 3. Factory spec (`factory.spec.yml`, `specs/*.yml`)

Parsed by `load_spec()` (`spec/loader.py:60-107`) into a `FactorySpec` (`spec/model.py:106-151`);
refused by `validate()` (`spec/validator.py:307-309`) when incomplete.

### 3.1 Top-level keys

| Key | Type | Req/Opt (default) | Meaning | Anchor |
| --- | --- | --- | --- | --- |
| `factory` | dict `{name, slug, maturity}` | required | L0 identity. | `validator.py:29-46` |
| `domain` | dict (§3.3) | required | L1 domain + L2 line. | `validator.py:29-46` |
| `machinery` | dict `{harness, mcp, infra}` | optional | L3 — pure DATA the plan chose (ADR-012), only shape-checked. | `validator.py:210-226` |
| `factory_substrate` | dict (§3.5) | required | L4 — the 13 BOOTSTRAP invariants as DATA; only 3 sub-keys are hard-enforced. | `validator.py:49-59` |
| `requirements` | dict `{functional: [...], nonfunctional: [...]}` | required (≥1 total) | L5 — the SDD spine (RTM closure, `validator.py:62-81`). | `loader.py:79-91` |
| `governance` | dict `{deferral_tracking: "strict"}` | optional | opt-in policy. **Adopted by 0 of the 5 committed factory specs** — every real spec relies on the default (non-strict) deferral tracking; only test fixtures exercise `strict`. | `spec/model.py:118,123-126` |

### 3.2 `factory.{...}`

| Key | Type | Req/Opt | Meaning | Anchor |
| --- | --- | --- | --- | --- |
| `name` | string | required | the factory's display name. | `validator.py:31-32` |
| `slug` | string, pattern `^[a-z][a-z0-9-]*$` | required | the directory name under `factories/`. | `validator.py:33-34` |
| `maturity` | string | optional | free-text status label (e.g. `skeleton`); not machine-enforced. | `spec/model.py:110` |

### 3.3 `domain.{...}`

| Key | Type | Req/Opt (default) | Meaning | Anchor |
| --- | --- | --- | --- | --- |
| `produces` | string | required | what the factory builds (free text). | `validator.py:35-36` |
| `station_sequence` | list of dict (§3.4) | required (≥1) | the L2 line. | `validator.py:37-38` |
| `product` | dict | optional | the domain payload for codegen substitution — the factory-root DEFAULT blueprint, same shape as `products/<p>/product.yml` (§4). | `spec/model.py:147-150` (`FactorySpec.subst`) |
| `capabilities` (or legacy `product_capabilities`) | list of dict `{id, invariant, artifact, proof, primitive, tech, status, deferral}` | optional | L1 capabilities: invariant + evidence + (optionally) the DES primitive + tech the plan chose. | `spec/loader.py:46-57,68-69`, `spec/model.py:25-37` |
| `required_primitives` | list of string, pattern `^DES-\d+$` | optional (default `[]`) | the DES-x primitives this domain declares it needs; drives `design_review` (B1/B2). | `spec/design.py:18-46`, `loader.py:103` |
| `target_framework` | dict `{name, provider_agnostic}` | optional | **DEAD**: declared in the (also-dead) `factory.schema.json:23`, never read by `loader.py` or any validator — not even carried into `FactorySpec` (which has no such field). Sits inertly in `spec.raw`. | grep of `src/metafactory/**` for `target_framework`: 0 hits outside `factory.schema.json` |
| `provision_modes` | list | optional | **DEAD** by the same measure as `target_framework` — schema-declared, code-unreferenced. | `factory.schema.json:49`; 0 hits in `src/metafactory/**` |
| `proof_check_types` | list | optional | **DEAD** by the same measure. | `factory.schema.json:50`; 0 hits in `src/metafactory/**` |
| `constraints` | dict, e.g. `{excluded_domains: [...], affirmative_fit: "..."}` | optional | **DEAD and not even schema-declared** — pure narrative prose (what this factory explicitly does NOT cover, and why) that no code, not even `factory.schema.json`, ever reads. | 0 hits for `"constraints"` anywhere in `src/metafactory/` or `seed/` |
| `hitl` | dict, e.g. `{non_skippable_interrupt: true}` | optional | **DEAD** — appears once, in `agent-systems-factory`'s spec (a sibling of `provision_modes`), never read by any loader/validator/check. | 0 hits for `"hitl"` in `src/metafactory/` or `seed/` |

Half of `domain`'s optional keys (`target_framework`, `provision_modes`, `proof_check_types`,
`constraints`, `hitl`) are committed, real, and inert — declared intent with no machine teeth. This is
recorded once here rather than per-row: a re-implementer should NOT spend effort making these load-
bearing unless a future ADR gives them one.

### 3.4 `domain.station_sequence[]` — SpecStation entries

Parsed by `_station()` (`spec/loader.py:31-43`) into a `SpecStation` (`spec/model.py:53-78`).

| Key | Type | Req/Opt (default) | Meaning | Anchor |
| --- | --- | --- | --- | --- |
| `id` | string | required, unique | the station id. | `validator.py:40-45` |
| `name` | string | optional (default = `id`) | human label. | `loader.py:34` |
| `activation` | string | optional (default `"always"`) | same shape/looseness as the materialized station's (§2.1 residual). | `loader.py:35` |
| `depends_on` | list of string | optional (default `[]`) | must point at real, ACTIVE stations; the graph is cycle-checked. | `validator.py:151-157,168-191` |
| `proof_checks` | list of dict (§3.4.1) | optional (default `[]`) | the SDD-DESCRIPTIVE contract — what a requirement's `verified_by` addresses. | `spec/model.py:57-58` |
| `status` | string, closed enum `built`\|`declared-deferred`\|`planned` | optional | SAFE-7 honesty: aspiration is never confused with reality. | `spec/model.py:20`, `validator.py:86-90` |
| `builds` | list of dict | optional (default `[]`) | the EXECUTABLE realization — consumed verbatim, same shape as §2.2. | `spec/model.py:68` |
| `checks` | list of dict | optional (default `[]`) | the EXECUTABLE realization — consumed verbatim, same shape as §2.3. | `spec/model.py:69` |
| `tier` | string, closed enum `core`\|`harden` | optional (default `"core"`) | same DIAL semantics as §2.1. | `loader.py:42` |
| `deferral` | dict `{trigger, since}` | optional | deferred-debt-with-teeth (ADR-017 §4); under `governance.deferral_tracking: strict`, a `declared-deferred` status without one is M0-red. Not itself a required vocabulary term (no committed `station_sequence` entry sets it — every real deferral in the corpus is a legacy bare `declared-deferred`), documented here for completeness. | `validator.py:96-111` |

#### 3.4.1 `proof_checks[]` entries (not separately gate-required; documented for completeness)

`{name, cmd, runs_in, toolchain, status, deferral}` — `name`/`cmd` free strings (a human-readable
description of the check, NOT an argv — the EXECUTABLE argv lives in the sibling `checks[]`, §2.3);
`runs_in` is a closed enum `factory_env`\|`product_env` (DES-8: proof in the product's own toolchain);
`toolchain` is free DATA (`pytest`, `tsc`, …, never whitelisted, ADR-012). A `verified_by` in a
requirement (§3.4 sibling `requirements`) that names a `proof_checks[].name` outside the declared set is
a phantom verifier — M0-red. `spec/model.py:40-50`, `spec/loader.py:20-28`, `validator.py:194-207`.

### 3.5 `factory_substrate.{...}`

Only 3 of the 8 sub-keys carry independent machine enforcement; the rest exist because BOOTSTRAP's 13
invariants require EXISTENCE (params may vary) — `validate_substrate()` checks only the first two.

| Key | Type | Req/Opt (default) | Enforced? | Meaning | Anchor |
| --- | --- | --- | --- | --- | --- |
| `anti_rubber_stamp_column` | bool | required, must be `true` | **yes** | I-1: the column exists. | `validator.py:54-55` |
| `verdict_bus` | dict `{max_lines: int > 0}` | required | **yes** (`max_lines`) | I-7: the bounded-verdict contract; `max_lines` also flows into `_subst_for()`'s `max_lines` substitution key. | `validator.py:56-58`, `cli.py:121` |
| `context_budget` | dict `{claude_md_max_lines: int}` | optional (default `120` if absent) | **yes**, via the `agent_shadow` check kind | the ceiling `CLAUDE.md`'s line count must stay under. | `verify/checks/agent_shadow.py:140` |
| `generated_domain_boundary` | bool | optional | no — declarative only | whether the factory's product has a human/generated split (I-5). `boundary_survives` derives its OWN signal from `domain.product.boundary_domain_dest`/`boundary_generated_dest` (a different key pair, in `product`, not here); this flag itself is never read. | 0 hits for `"generated_domain_boundary"` in `src/metafactory/**` |
| `memory_schema` | string (e.g. `"adr021"`) | optional | no | which memory-doc schema version the factory targets; a version tag, not machine-checked. | 0 hits in `src/metafactory/**` |
| `rtm` | dict `{required: bool}` | optional | no | declares intent to keep an RTM; `meta rtm`/the `rtm_tree`/`rtm_rederive`/`rtm_closure` kinds run regardless of this flag. | 0 hits in `src/metafactory/**` |
| `two_verifier_ci` | dict `{rederive: bool, pinned_verdict: bool}` | optional | no | declares intent to run the two-verifier CI (ADR-005); `ci --rederive` runs regardless. | 0 hits in `src/metafactory/**` |
| `placement_law` | bool | optional | no | declares adherence to the doc placement law; not machine-checked here (the `docs` gate checks doc structure independently, not this flag). | 0 hits in `src/metafactory/**` |

## 4. Product blueprint (`products/<p>/product.yml`; `factory.spec.yml`'s `domain.product`)

**The substrate never validates a product blueprint's shape** — `domain.product`/`product.yml` is
opaque DATA to `src/metafactory` (ADR-012/013, I-2): it is read verbatim by `FactorySpec.subst`
(`spec/model.py:144-151`) for `{{var}}` substitution and, for named instances, has `station_activation`
popped by `cli.py` before merge (§4.8). ALL other structure below is validated and consumed entirely
inside each FACTORY's own `codegen/`, per factory, per plan (ADR-012: a floating `tech`/schema is never
baked into the substrate). Three of the five factories currently have committed products with distinct
blueprint shapes; each is documented as its own sub-section.

### 4.1 Top-level blueprint keys observed across all committed products

| Key | Type | Req/Opt | Factory(ies) that read it | Meaning | Anchor |
| --- | --- | --- | --- | --- | --- |
| `package_name` | string | required (all factories) | full-stack-kotlin, iot, full-stack | the codegen's root package/module name. | `scaffold/blueprint.py:68-69` (FSK), `iot/codegen/scaffold_product.py:42-44`, `full-stack/codegen/scaffold_product.py:39-40` |
| `entities` | list of dict (§4.2) | required | full-stack-kotlin | the entity model (plural — one product, many entities). | `scaffold/blueprint.py:70-72` |
| `entity` | dict `{name, fields}` | required | full-stack | the entity model (singular — this factory's product carries exactly ONE entity). Because the schema collector only descends into an `entities` LIST, a singular `entity` dict's inner keys (`title`, `done`, …) never leak into the required vocabulary — by construction, not by omission. | `full-stack/codegen/scaffold_product.py:41-43,388-389` |
| `roles` | list of string (lowercase identifiers, no dups) | optional | full-stack-kotlin | the RBAC role universe (R2/FSK-S13); opt-in — without it the product is auth-only. | `scaffold/blueprint.py:188-195` |
| `write_roles` (per-entity, see §4.2) | — | — | — | — | — |
| `owner_bypass_roles` | list of string ⊆ `roles` | optional | full-stack-kotlin | roles that ignore row-ownership (R2/FSK-S14); requires `roles`. | `scaffold/blueprint.py:213-221` |
| `company_scope_bypass_roles` | list of string ⊆ `roles` | optional | full-stack-kotlin | roles that ignore company/tenant scope (FSK-COMPANY-SCOPING); requires `roles`. | `scaffold/blueprint.py:240-248` |
| `api_title` | string | optional (default = `package_name`) | full-stack-kotlin | the OpenAPI `info.title`. | `scaffold/contract.py:13`, `scaffold/frontend.py:298` |
| `frontend_surface` | string, closed enum `{"model-native"}` | optional | full-stack-kotlin | opt-in to a pinned, model-generated `frontend/{app.ts,app.css}` override (ADR-024) instead of the mechanical template; loading FAILS CLOSED if declared but the override files are missing. | `scaffold/blueprint.py:346-364` |
| `station_activation` | dict `{station_id: bool\|"off"\|"always"\|...}` | optional | ALL (popped generically before it reaches any factory codegen) | RESERVED — see §4.8. | `cli.py:92-101` |
| `marker` | string | optional | **none** — declared in `iot`'s `fleet` product AND `full-stack`'s `tasks` product, read by NEITHER factory's codegen. Dead data (see §7). | 0 hits for `bp.get("marker"`/`bp["marker"]` in `factories/iot/**`, `factories/full-stack/**` |
| `module_path` | string | required | iot | the Go module path (`module_path` in `go.mod`). | `iot/codegen/scaffold_product.py:42-44,718` |
| `message` | dict (§4.6) | required | iot | the typed telemetry message contract. | `iot/codegen/scaffold_product.py:45-53,717` |
| `topology` | dict `{root, topics: [...]}` | required | iot | the pub/sub graph (§4.6). | `iot/codegen/scaffold_product.py:54-55` |
| `provenance` | dict `{join_key: [...]}` | required | iot | the audit-trail join-key fields (§4.6). | `iot/codegen/scaffold_product.py:59-60` |
| `ota` | dict, e.g. `{require_signature: true}` | optional | **none** — declared in the `fleet` product, read by no code in `factories/iot/`. Dead data (see §7). | 0 hits for `"ota"` in `factories/iot/**` (outside `products/fleet/product.yml` itself) |

### 4.2 `entities[]` entries (full-stack-kotlin)

| Key | Type | Req/Opt (default) | Meaning | Anchor |
| --- | --- | --- | --- | --- |
| `name` | string | required | the entity name (PascalCase by convention). | `scaffold/blueprint.py:76-77` |
| `fields` | list of dict (§4.3) | required, non-empty | the field model. | `scaffold/blueprint.py:76-77` |
| `write_roles` | list of string ⊆ `roles` | optional | who may POST this entity; requires top-level `roles`. | `scaffold/blueprint.py:196-207` |
| `owned_by` | string (must name a `ref`-typed field of this entity) | optional | row-level ownership (R2/FSK-S14): the FK to the owning principal; requires top-level `roles`. May itself be a POLYMORPHIC `ref` (FSK-OWNER-POLY). | `scaffold/blueprint.py:222-232`, `scaffold/base.py:53-58` |
| `company_scoped` | string (must name a `ref`-typed field) | optional | tenant scoping (FSK-COMPANY-SCOPING): the FK to the tenant; requires top-level `roles`; composes over `owned_by`. | `scaffold/blueprint.py:249-259` |
| `soft_delete` | bool | optional (default `false`) | DELETE becomes `UPDATE deleted_at=now()` + a read-filter + an implicit `restore` verb, instead of a permanent delete. | `scaffold/blueprint.py:78-82`, `scaffold/base.py:73-83` |
| `audited` | bool | optional (default `false`); requires `owned_by` when `true` | mutation paths (create/update/delete/verbs) are logged with the token principal as actor. | `scaffold/blueprint.py:83-93` |
| `mutable_when` | dict `{field, in\|not_in}` (§4.5) | optional | freeze-by-state: this entity is mutable only while its workflow field holds one of a declared set of values. | `scaffold/base.py:497-529` |
| `operations` | list of dict (§4.4) | optional, non-empty when present | named domain verbs beyond CRUD (workflow transitions or qty/stock decrements). | `scaffold/blueprint.py:273-345` |

### 4.3 `fields[]` entries (full-stack-kotlin)

| Key | Type | Req/Opt (default) | Meaning | Anchor |
| --- | --- | --- | --- | --- |
| `name` | string | required | the field name (snake_case by convention; openapi-generator camelCases it). | `scaffold/base.py:11-13` |
| `type` | string, closed enum: `string`, `boolean`, `int`, `number`, `date`, `ref`, `enum` | required | the field's data type; `enum` is handled specially (no fixed OpenAPI mapping — depends on `values`). | `scaffold/constants.py:116-123`, `scaffold/blueprint.py:95-99` |
| `required` | bool | optional (default `true`) | whether the field must be present on write. A forward `ref` (target declared later in the file) MUST be `required: false` — no seed order exists for a cycle with a required side. | `scaffold/blueprint.py:124-131` |
| `unique` | bool | optional (default `false`) | emits a SQL `UNIQUE` column constraint; in the committed corpus only ever set on `string` fields (not fail-closed to that type). | `scaffold/data_layer.py:256-260` |
| `values` | list of string | required when `type: enum` | the closed set of admissible values. | `scaffold/blueprint.py:98-99` |
| `to` | string (an entity name) \| list of string (≥2 entity names, a UNION) | required when `type: ref` | the target entity(ies). A list makes the ref POLYMORPHIC (FSK-POLYMORPHIC-REFS): materialized as `<field>_type` (discriminator) + `<field>_id` (no FK — no referential integrity to a union), not a single FK column. `to` also names a workflow-operation's target STATE in `operations[]` — an unrelated, overloaded use of the same word (§7). | `scaffold/base.py:22-29`, `scaffold/blueprint.py:100-131` |
| `format` | string, closed enum: `numeric`, `alpha`, `email`, `url`, `ip`, `mac` | optional; only on `type: string` | a request-body validation regex (FSK-CUSTOM-FIELDS), emitted as a Kotlin `Regex` constant. | `scaffold/constants.py:144-151`, `scaffold/blueprint.py:134-143`, `scaffold/server.py:287` |
| `computed` | number \| field-name string \| cross-entity `"<ref>[.<ref>...].<field>"` string \| `{op, args}` AST | optional; only on `type: int`/`number`, never the `owned_by` field | a derived value computed at READ time (never stored — zero columns). `op` ∈ closed set `{+, -, *, /, min, max}` (binary-only: `-`,`/`) plus the unary time op `months_since`. | `scaffold/constants.py:154-160`, `scaffold/base.py:61-71`, `scaffold/blueprint.py:13-62,144-162` |
| `initial` | string, must ∈ `values` | optional; only on `type: enum` | the workflow's starting state (R2/FSK-S12). | `scaffold/blueprint.py:163-170` |
| `transitions` | dict `{from_state: [to_state, ...]}`, every key/value ∈ `values` | optional; only on `type: enum` | the declared state machine (fail-closed: no phantom states). | `scaffold/blueprint.py:171-182` |

### 4.4 `operations[]` entries (full-stack-kotlin, opt-in domain verbs — not separately gate-required, documented for rebuild completeness)

Two mutually-exclusive KINDs, detected by the presence of `decrements`:

| Key | KIND | Type | Meaning | Anchor |
| --- | --- | --- | --- | --- |
| `name` | both | string, lowercase identifier | the verb's name (unique per entity). | `scaffold/blueprint.py:282-287` |
| `decrements` | qty | string (a `type: int` field name) | the stock field this verb decrements; requires the entity to declare `write_roles`. | `scaffold/blueprint.py:288-301` |
| `creates` | qty (optional) | string (an entity name) | a pivot entity to insert a row into alongside the decrement (FSK-CREATES-PIVOT); the pivot needs a `ref` back to the verb's subject entity + ≥1 required body field. | `scaffold/blueprint.py:302-321` |
| `field` | workflow | string (an `enum` field with `transitions`) | which workflow field this verb transitions; requires the entity to declare `owned_by`. | `scaffold/blueprint.py:326-332` |
| `from` / `to` | workflow | string, both ∈ the field's `values` AND `to` ∈ `transitions[from]` | the declared transition this verb performs. | `scaffold/blueprint.py:333-339` |
| `assigns` / `clears` | workflow (optional, mutually exclusive) | string (a `ref` field name) | a side-effect: set or null a reference field as part of the transition (e.g. checkout/checkin). | `scaffold/blueprint.py:340-345` |

### 4.5 `mutable_when` shape (full-stack-kotlin)

`{field: <enum field name>, in: [...]}` or `{field: ..., not_in: [...]}` (exactly one of `in`/`not_in`);
every listed value must be ∈ the field's `values`. `scaffold/base.py:497-518`.

### 4.6 IoT (`iot` factory) blueprint sub-shapes

| Key | Shape | Meaning | Anchor |
| --- | --- | --- | --- |
| `message.name` | string | the telemetry message struct's Go name. | `iot/codegen/scaffold_product.py:46` |
| `message.fields[]` | `{name, type, values?}`; `type` ∈ `{string, float\|float64, int\|int64, bool, enum}` | the message's typed fields; `enum` requires non-empty `values`. | `iot/codegen/scaffold_product.py:47-52` |
| `message.required` | list of string (field names) | which fields are mandatory on ingest. | `factories/iot/products/fleet/product.yml:17` (usage site; loader reads it as part of the `message` dict, no separate guard beyond the fields it names existing) |
| `topology.root` | string | the hub/root node of the pub/sub graph. | `iot/codegen/scaffold_product.py:54-55` |
| `topology.topics[]` | `{name, publisher, subscriber}` | one pub/sub edge. | `factories/iot/products/fleet/product.yml:18-23` |
| `provenance.join_key` | list of string (field names) | the composite key the append-only audit trail joins metrics back to raw readings by; also the idempotency key for re-delivered readings. | `iot/codegen/scaffold_product.py:59-60,389,497` |

### 4.7 full-stack (`full-stack` factory) blueprint sub-shape

`entity: {name, fields: [{name, type}, ...]}` — a single entity, TS types only (`_TS_TYPE`, not the FSK
`_OAPI_TYPE` closed set); parsed by `full-stack/codegen/scaffold_product.py:35-44`. The station `s3`
generator slot (`claude -p`) synthesizes fresh domain logic for this one entity per product instance.

### 4.8 Reserved instance keys — popped before merge

**`station_activation`** (dict `{station_id: activation-override}`) is the ONLY key in the whole
codebase that is deliberately popped from a product blueprint before it reaches any factory codegen.
`ensure_product_instance()` (`cli.py:72-107`) pops it at `cli.py:96`, normalizes each value through
`_norm_activation()` (`cli.py:61-69`, same off/always canonicalization as §2.1), and applies it as a
per-instance `activation:` override on the matching `station_sequence` entry — general and visible (it
lives in the COMMITTED `product.yml`, not a side file). Grep of every `.pop(` call across `cli.py`,
`codegen/*.py`, `spec/*.py` and every FSK `scaffold/*.py` confirms it is the sole reserved key.

A related SYNTHETIC key: `_frontend_surface` (dict `{app_ts, app_css}`) is not read FROM the YAML — it
is COMPUTED and injected into the in-memory blueprint by `_load_blueprint()` when `frontend_surface:
model-native` is set, by reading `frontend/app.ts`+`frontend/app.css` off disk (`scaffold/blueprint.py:353-363`).
It never appears in a committed `product.yml`; a re-implementer scanning YAML for it will not find it.

## 5. Slot manifest and slot verdict

Single source `seed/delegation.py` — "the constants ARE the schema" (frozen Stage-0 seed, copied
verbatim into every factory).

### 5.1 Manifest — required keys

| Key | Type | Meaning | Anchor |
| --- | --- | --- | --- |
| `slot_id` | non-empty string | the slot's stable name. | `seed/delegation.py:34,89` |
| `allow_globs` | list of string (fnmatch globs, root-relative) | the ONLY paths the generator may Write/Edit — the blast radius. | `seed/delegation.py:34,91-92,183-193` |
| `verdict_path` | string (root-relative path) | where the generator must leave its verdict. | `seed/delegation.py:34` |
| `iteration_gate_cmd` | non-empty list of string (argv) | the FAST gate, re-run every retry; must fit `ITERATION_BUDGET_MAX_S = 15`s if `iteration_budget_s` is declared. | `seed/delegation.py:34,94-96,37` |
| `acceptance_gate_cmd` | non-empty list of string (argv) | the HEAVY gate, run once at the end; its exit code is what a `status: green` verdict is actually judged against. | `seed/delegation.py:34,94-96` |

### 5.2 Manifest — process/size budgets (optional)

| Key | Type | Req/Opt (default) | Meaning | Anchor |
| --- | --- | --- | --- | --- |
| `iteration_budget_s` | number, `(0, 15]` | optional | declared ceiling for the fast gate's wall time. | `seed/delegation.py:37,98-99` |
| `max_wall_s` | number, `(0, 1800]` | optional | declared ceiling for the WHOLE slot's wall time (`SLOT_WALL_MAX_S = 1800`); a slot needing more must be split. | `seed/delegation.py:38,100-101` |
| `token_budget` | positive int | optional | declared ceiling for tokens spent in the slot. Not set in any committed manifest today (present in the law, unexercised in the corpus — like `corpus`/`baseline` in §2.3). | `seed/delegation.py:102-103` |
| `file_budget` | positive int | optional | max LOC per generated file inside `allow_globs`; validated post-hoc at verdict time — a `green` verdict on an oversized file is demoted. | `seed/delegation.py:104-108,192-193,254-259,285-288` |

### 5.3 Manifest — WorkOrder vocabulary (optional, PWF harvest, ADR-017 Fase 4)

Backward-compatible: a bare manifest with only the §5.1 keys stays valid. When present, each is
validated against a closed set — a malformed WorkOrder is rejected before any generator spawns.

| Key | Type / closed enum | Req/Opt (default) | Meaning | Anchor |
| --- | --- | --- | --- | --- |
| `trust_level` | string ∈ `("low", "medium", "high")` | optional | how much autonomy the slot grants (gates review depth). | `seed/delegation.py:42,48,140-141` |
| `cost_class` | string ∈ `("cheap", "standard", "premium")` | optional | which model tier should take the slot. | `seed/delegation.py:43,49,142-143` |
| `side_effects` | list, each ∈ `("files", "network", "process")` | optional | the blast surface beyond file writes, declared up front. | `seed/delegation.py:44,50,144-150` |
| `forbidden_tools` | list of string | optional | tool names the generator must not use. | `seed/delegation.py:151-152` |
| `single_responsibility` | non-empty string | optional | the one-sentence scope statement (this document's own manifest carries one). | `seed/delegation.py:153-154` |
| `baseline_dirty` | list of string (root-relative paths) | optional (auto-recorded by `write_slot()` at slot-open) | paths already dirty BEFORE the slot opened, exempted from the footprint check so a pre-dirty tree can't false-red it. | `seed/delegation.py:80-86,156-157,197-198,213` |
| `model_policy` | dict, keys ⊆ `("temperature", "seed", "strict_json")` | optional | determinism knobs for the worker. | `seed/delegation.py:51,159-165` |

### 5.4 Verdict — required keys

| Key | Type | Meaning | Anchor |
| --- | --- | --- | --- |
| `slot_id` | string | must match the manifest's `slot_id`. | `seed/delegation.py:31,266` |
| `status` | string, closed enum `("green", "red")` | the generator's self-reported outcome — only trustworthy in combination with `acceptance_exit_code` (below). | `seed/delegation.py:32,268-269` |
| `check` | string | which gate was run (free text, e.g. the acceptance command). | `seed/delegation.py:31` |
| `exit_code` | int | that gate's exit code. | `seed/delegation.py:31` |

### 5.5 Verdict — conventional extra keys (not individually law-enforced)

| Key | Type | Meaning | Anchor |
| --- | --- | --- | --- |
| `acceptance_exit_code` | int | the HEAVY gate's exit code; a `status: green` verdict is DEMOTED (`verdict_ok` returns `False`) if this is not `0` when `acceptance_gate_cmd` is declared. The one extra key that IS cross-checked. | `seed/delegation.py:271-276` |
| `log_ref` | string | a pointer to the full log/output (never the log itself — I-7 discipline echoed at slot scale). | convention only (this file's own §0 verdict-writing instructions use it) |
| `summary` | string | one-line human summary. | convention only |
| `notes` | string | free-form extra context a generator chooses to leave. | convention only (observed in `.gen/docs-en-slot2.verdict.json`) |

## 6. Pinned verdict (`pinned_verdict.json`)

`{station_id: proof_sha}` — one entry per ACTIVE station in the line, written by `_pin_from_proofs()`
from the CURRENT, honest, all-passed proofs (refuses to pin if any active station's proof is missing or
failed). `cli.py:498-509`.

```
{
  "s00": "c84e1f26d64fdeb31c3d2727a6e682c532c1fec1dc3b381bcc79b2cc313cb477",
  "s01": "47361a92dcd14c6e3a704cca75ab279c1eb936537e70c0b32f6f4e7806f0b85a"
}
```

`ci --rederive` wipes `.proof/`+`build/`, re-runs the line, recomputes this same shape, and calls
`pin_matches()` (`14-kernel-reference.md §2`) — a station present in one side and absent from the other
is a deviation, never a tolerance (`14-kernel-reference.md §2`, `pin_matches` docstring).

## 7. Cross-bucket naming collisions (honest, not fixed)

The same identifier means unrelated things in different tables above — a re-implementer who globally
renames "for clarity" will silently break something. Recorded once, in the spirit of
`01-vocabulary.md §5`:

| Identifier | Meaning A | Meaning B |
| --- | --- | --- |
| `proof` | the check-record CONCEPT (`.proof/<station>.json`, §1) | the `infra_up` check's readiness/health-check argv key (§2.3) |
| `prove` | — | the `mcp_tools` check's prober argv key (§2.3); NOT the same key as `proof` above, on a different kind |
| `command` | one of the 29 closed `kind` values (a literal argv, §2.3) | the `eval_floor` kind's OWN extra key, itself a DIFFERENT argv than the check's `cmd` |
| `to` | a `ref` field's target entity/entities (§4.3) | a workflow operation's target STATE (`operations[].to`, §4.4) |
| `activation` | station-level (`always`\|`off`, §2.1/§3.4) | (unrelated) not reused elsewhere in this corpus, listed here only to note its own internal looseness |

## 8. Residual summary (for anyone re-implementing from this file alone)

Confirmed-dead-in-code keys, each independently grep-verified against `src/metafactory/**` and/or the
owning factory's `codegen/` (zero hits beyond their own declaration/comment):
`domain.target_framework`, `domain.provision_modes`, `domain.proof_check_types`, `domain.constraints`,
`domain.hitl` (§3.3); `factory_substrate.generated_domain_boundary`, `.memory_schema`, `.rtm`,
`.two_verifier_ci`, `.placement_law` (§3.5, existence-only per BOOTSTRAP, no independent check);
`marker`, `ota` on product blueprints (§4.1). `governance` is not dead code but IS unadopted: 0 of 5
committed factory specs set it. `station.activation`'s `"optional"` enum value (§2.1/§3.4) is declared
in two places and used nowhere. None of these were invented for this document — each is grep-confirmed
above with its own anchor; do not port them into a v3 substrate as if they had teeth today.
