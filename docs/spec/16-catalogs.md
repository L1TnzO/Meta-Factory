<!-- meta:doc sha=3cecab082c3741175af0f68fcb84151a4f8828ed updated=2026-07-28T19:08Z -->
# 16 — Catalogues: the gates of `meta check` and the check-kind vocabulary (reference)

Complete, not a summary of `04-verification.md`/`03-engine.md` — those cite anchors and narrate; this
page enumerates every row those sections gesture at. Every witness cell below was confirmed by reading
the cited module directly (not copied from prior narration); where 04-verification.md's census differs
from what the code shows today, this page is the corrected source (§1.3).

## 1. Gate catalogue — `meta check`'s 23 gates

Source of truth: the `checks` list built in `cmd_check()`, `src/metafactory/cli.py:147-192`. Extracted
by `tools/spec_doc_check.py:gate_names()` via `ast` over that function — this table cannot silently
drop a gate the tool would still see.

### 1.1 The table

| Gate | Proves | Red-side witness | Scope | Vacuous-true (N/A) |
| --- | --- | --- | --- | --- |
| `compile` | `python -m compileall` over `src/metafactory` + `seed` exits 0 (repo-wide syntax validity of the substrate) — `cli.py:148-149` | one-sided | repo-wide | no |
| `docs` | The doc corpus is internally consistent: every doc's content-addressed seal is current, `INDEX.md` covers exactly the doc set, the entry doc(s) carry no dangling relative links, and no doc is older (by last commit) than a newer doc in its home — `src/metafactory/docs_manifest.py:208-259`, transported by `verify/checks/docs_check.py:12-18` | NONE — DEBT (no synthetic negative wired into `docs_manifest.check()` or `docs_check.main()`; a real broken doc goes red, but the detector's own correctness is unproven) | repo-wide (every doc home, ADR-016 §2/3; INDEX + entry-link checks meta-only) | no |
| `projection` | The generated `<!-- meta:projection -->` block inside `docs/STATE.md` is not stale relative to the facts (open increment, per-factory RTM) it summarizes — `src/metafactory/memory/projection.py:134-141` (`is_stale`, called by `_main("check")`) | NONE — DEBT (no synthetic stale-block fixture; `_main` only evaluates the real `docs/STATE.md`) | repo-wide (meta `STATE.md` only) | no |
| `isolation` | `pytest -q tests/test_isolation.py` proves the substrate never statically imports a factory and carries zero generation-tech tokens (ADR-012) — `tests/test_isolation.py:12-40` | one-sided | repo-wide | no |
| `generality` | ADR-014: no substrate mechanism declared `status: general` in `docs/reference/parity.yml` is promoted on single-domain proof; a `general` claim needs ≥2 factories green on RADICALLY DISTINCT domains (disjoint toolchain language ∧ differing primitive mix) — `src/metafactory/verify/checks/generality_parity.py:146-181` (`_audit_general`) | NONE — DEBT (confirmed: `main()`, lines 146-181, runs ONLY the green-side audit over the real manifest; no `_tooth_bites`/synthetic-negative call exists in this module, unlike its 14 siblings below. `tests/test_generality_parity.py` unit-tests the pure `_audit_general` logic with red cases, but that suite is reached only through the `suite` gate, not through `generality` itself — a regression here would not flip `generality` red) | opt-in (gates only entries with `status: general`; `status: prototype` never gates, ADR-014 §2) | YES — no `docs/reference/parity.yml` → green N/A (`generality_parity.py:149-151`); 0 `general` entries is also a vacuous "OK … 0 mecanismo(s)" pass |
| `quality` | The live substrate graph (`src/metafactory` + `seed`) AND every factory's authored codegen (`factories/*/codegen/**`) carry no file/function-count/import-cycle violation past the deterministic thresholds — `src/metafactory/verify/checks/quality_gate.py:49-71` | `tests/fixtures/quality/monolith_shaped.py` — embedded, `quality_gate.py:73-84` (fails the check if the fixture doesn't trip a violation) | repo-wide + per-factory sweep (codegen glob, no factory named) | RED-tooth branch only: N/A if the fixture is absent from the tree — `quality_gate.py:75-76` (SAFE-7, never faked green) |
| `pbt` | The declared property-based command (default: the graph property suite) holds over its inputs with a fixed seed — `src/metafactory/verify/checks/pbt_gate.py:44-50` | embedded self-rerun under `METAFACTORY_PBT_SABOTAGE=1` (no separate fixture file — the SAME command corrupts the code-under-test via the env var) — `pbt_gate.py:28-56` | repo-wide | no explicit N/A branch |
| `evidence_liveness` | Every non-exempt LIVING doc's `CITES`-shaped references (relative `.md` paths, bare `ADR-NNN`) resolve to something real — `src/metafactory/verify/checks/evidence_liveness.py:29-43` | `tests/fixtures/docs/dangling_reference.md` — embedded, `evidence_liveness.py:45-61` (outside every `doc_homes()` home, so invisible to the green scan) | repo-wide (doc corpus) | RED-tooth N/A if the fixture is absent — `evidence_liveness.py:47-48` |
| `security` | The shipped substrate (`src/metafactory`,`seed`,`.claude/hooks`,`.claude/agents`) carries zero hardcoded-credential-format or high-entropy-string matches, and every declared build dependency is inside the committed allowlist (anti-slopsquatting, H-4) — `src/metafactory/verify/checks/security_scan.py:157-186` | `tests/fixtures/security/planted_secrets.txt` — embedded, `security_scan.py:166-175` | repo-wide (green dirs) + opt-in sub-check (dep-allowlist, opts in via presence of `docs/reference/dep-allowlist.yml`) | RED-tooth N/A if the planted fixture is absent — `security_scan.py:168-169`; allowlist sub-check independently N/A if `dep-allowlist.yml` is absent — `security_scan.py:184-185` |
| `deferred` | Every committed factory spec is clean of deferral problems; a spec that opted into `governance.deferral_tracking: strict` carries `deferral{trigger,since}` on every `declared-deferred` entry; the accumulation (total vs tracked) is printed as a re-derived metric — `src/metafactory/verify/checks/declared_deferred.py:46-64` | `tests/fixtures/governance/strict_untracked.factory.spec.yml` — embedded, `declared_deferred.py:72-81` | opt-in per spec (`governance.deferral_tracking: strict`); scan itself is a repo-wide sweep of `factories/*/factory.spec.yml` | RED-tooth N/A if the fixture is absent — `declared_deferred.py:74-75` |
| `benchmark` | Every product a benchmark file declares `sweet_spot` MEETS the target (entity-count band ∧ every required capability's station pinned green); every product declared `ceiling` must NOT meet it | `benchmarks/sweet-spot-crud.yml:29-31` — live committed DATA (the `snipeit` `expect: ceiling` entry), re-evaluated on every real run of `gate_problems` (`src/metafactory/verify/benchmark.py:156-176`, called from `verify/checks/benchmark_gate.py:41-51`); NOT an embedded synthetic — the module's `main()` only evaluates real `benchmarks/*.yml`. Logic-level red case also pinned at `tests/test_benchmark.py:48` (`test_decorative_ceiling_is_caught`) | opt-in per product (`benchmarks/*.yml` glob + a product's `expect:` entry) | YES — no `benchmarks/*.yml` in the tree → N/A green — `verify/checks/benchmark_gate.py:35-37` |
| `dial` | Every factory that adopted the draft→harden dial (≥1 active `tier: harden` station) keeps `harden` a non-empty PROPER subset of its active stations (`0 < \|harden\| < \|active\|`) — `src/metafactory/verify/dial.py:73-79` (`gate_problems`) | `tests/test_dial_measure.py:79-85` (`test_gate_red_on_all_harden`) — calls the REAL `dial_gate.main()` against a synthetic all-harden factory tree under `tmp_path` and asserts exit 1; NOT embedded inside `dial_gate.py`'s own `main()` (`verify/checks/dial_gate.py:26-52`), which only audits the real in-tree factories (none of which is all-harden) | opt-in per factory (`tier: harden` declared in `station_sequence`) | YES — no factories at all → N/A — `verify/checks/dial_gate.py:29-31`; 0 factories adopted (all 0-harden) also prints an explicit "N/A: ninguna … adoptó" pass — `dial_gate.py:50-51` |
| `column_parity` | Each factory's inherited column (`seed/*`, `.claude/hooks/*`, `.claude/settings.json`) is byte-identical to a fresh re-materialization of M1's real renderer (`apply_builds` on station `m01`) — `src/metafactory/verify/checks/column_parity.py:59-71` (`parity_problems`) | embedded, `column_parity.py:74-83` (`_tooth_bites` — plants a byte-level drift in a synthetic scratch pair) | per-factory sweep | no |
| `least_priv` | Each factory's inherited column is EXACTLY `FACTORY_COLUMN` (`src/metafactory/column_scope.py:60-64`) — a proper subset of `META_COLUMN` (`column_scope.py:49`), no meta-only hook leaked down, no governed hook missing | embedded, `least_priv.py:82-91` (`_tooth_bites` — plants both an over-privileged and an incomplete synthetic role-set) | per-factory sweep + the projection source (`template/factory/harness/.claude/hooks/`) | no |
| `roles` | Every `.claude/agents/*.md` (meta + every factory) declares a role name inside the closed vocabulary `agent_roles.ALLOWED` — agents specialize by ROLE, never by domain (ADR-020) — `src/metafactory/verify/checks/role_hygiene.py:54-64` | embedded, `role_hygiene.py:78-92` (plants a synthetic domain-named agent, `kotlin-writer`, in memory — no such file exists, which is the point; prints `GATE DECORATIVO` if it doesn't flip red) | repo-wide (meta + every factory's `.claude/agents`) | no |
| `kinds` | Every check-kind declared across station YAMLs (`checks[].kind`) and factory-spec `station_sequence[].proof_checks[].kind` is inside the frozen `registry.KINDS` vocabulary (D-3) — `src/metafactory/verify/checks/kind_hygiene.py:58-74`, gated at `:87` | `tests/test_kind_hygiene.py:38-47` (`test_red_domain_named_kind_in_station_yml`) — calls the REAL `kind_hygiene.main()` against a synthetic tree with a made-up kind and asserts exit 1; NOT embedded inside `kind_hygiene.py`'s own `main()` (`:77-102`), which only scans the real in-tree YAML | repo-wide sweep (`src/metafactory/stations/*.yml` + `factories/*/stations/*.yml` + `factories/*/factory.spec.yml`) | no |
| `codegen_freeze` | For every factory with a `codegen/` dir, the live diff window since the owning level's open work-doc — PLUS the full post-epoch git history — touching `factories/<f>/codegen/**` is covered by a well-formed `Codegen-freeze-waiver: alcance=… · motivo: … · cita: ADR-NNN` line (ADR-023 §3) — `src/metafactory/verify/checks/codegen_freeze.py:81-94` (`evaluate`), `:128-144` (`_audit_history`) | embedded, `codegen_freeze.py:153-161` (`_tooth_alive` — 3 synthetic scenarios: diff-without-waiver, waiver-without-diff, diff-with-valid-waiver) | repo-wide sweep, triggered only by factories carrying a `codegen/` dir | implicit vacuous-true if 0 factories carry `codegen/` (no explicit "N/A" string; `problems`/`report` just stay empty) |
| `plan` | `.gen/plan.json` (if present) is well-formed — every WorkOrder carries a gate, no dependency cycle, no dangling dep, every `deferred` WorkOrder carries a reason — and every `.gen/escalations/*.json` is shape-valid — `src/metafactory/verify/checks/plan_gate.py:54-79`, `src/metafactory/plan.py:plan_problems` | embedded, `plan_gate.py:26-51` (`_RED_FIXTURES` — 4 synthetic malformed plans, one per defect class, evaluated directly in `main()`) | opt-in (`.gen/plan.json` presence) | YES — no plan file → N/A green — `plan_gate.py:55-58` |
| `slot_footprint` | The delegation footprint law holds: the observed git change footprint of an active slot stays ⊆ `allow_globs ∪ {verdict_path} ∪ .gen/** ∪ baseline_dirty`, AND the real transport hooks (`.claude/hooks/{blast_radius,verdict_required}.py`) fail CLOSED (exit 2) when the manifest is present but the law is unloadable, staying inert (exit 0) with no manifest — `src/metafactory/verify/checks/slot_footprint.py:63-112` | embedded, `slot_footprint.py:63-74` (`synthetic_two_sided`) + `:83-112` (`transports_fail_closed`, runs the REAL hook scripts as subprocesses against a synthetic root) | repo-wide (default mode) + live-slot mode (`--live`, opt-in — only meaningful while a slot is active) | `--live` mode: no active slot → inert OK — `slot_footprint.py:117-119`; default mode has no N/A (always runs the synthetic law + the hook subprocess check) |
| `design_eval` | Every factory that published `design/criteria.yml` has a well-shaped criteria file, a standing negative witness (`design/critiques/template-witness.json`) that fails ≥1 axis, and every `covered` product's pinned `critique.json` meets every axis threshold (ADR-027) — `src/metafactory/verify/checks/design_eval.py:171-197` (`_violations`) | embedded, `design_eval.py:211-231` (plants a synthetic criteria file whose witness PASSES every axis; `GATE DECORATIVO` if `_violations` doesn't flip red) | opt-in per factory (`factories/*/design/criteria.yml` publication) | implicit vacuous-true: a root with no criteria file anywhere is green with 0 factories opted in (no explicit "N/A" string) — `design_eval.py:173-174`, `:233-235` |
| `state_snapshot` | `docs/STATE.md`'s `## Ahora` section stays within its line budget (`NOW_BUDGET_LINES = 45`) and carries no closure mark (✅/CERRADO/CLOSED/COMPLETE/DONE) whose newest embedded date is older than `STALE_CLOSURE_DAYS = 14` (ADR-019 §3) — `src/metafactory/verify/checks/state_snapshot.py:78-93` (`snapshot_problems`) | embedded, `state_snapshot.py:96-111` (`_tooth_bites` — an over-budget synthetic `STATE.md` + a stale-closure synthetic `STATE.md`) | repo-wide (meta `docs/STATE.md` only) | no |
| `state_fidelity` | The editable prose of `## Ahora` never contradicts the RTM re-derived from `.proof/` — a claim that a factory slug is COMPLETE/INCOMPLETE must match the deterministic oracle within a `WINDOW_CHARS = 60` attribution window (ADR-019 §4) — `src/metafactory/verify/checks/state_fidelity.py:72-104` (`fidelity_problems`) | embedded, `state_fidelity.py:107-120` (`_tooth_bites` — both contradiction directions must bite, true prose and an out-of-window token must NOT) | repo-wide (meta `docs/STATE.md` vs re-derived RTM) | no |
| `suite` | `pytest -q tests` — the ~70-module test corpus (including the pytest-level red-side tests for `dial` and `kinds` above) exits 0 — `cli.py:191-192` | one-sided | repo-wide | no |

### 1.2 Two-sidedness census (verified 2026-07-27, this page)

**14 gates embed their own synthetic red-side witness, run inside the gate's own `main()`** (so a
regression flips `meta check` red directly, with no dependency on the `suite` gate also running):
`quality`, `pbt`, `evidence_liveness`, `security`, `deferred`, `column_parity`, `least_priv`, `roles`,
`codegen_freeze`, `plan`, `slot_footprint`, `design_eval`, `state_snapshot`, `state_fidelity`.

**3 gates are two-sided through a genuine but INDIRECT witness** — either committed DATA re-evaluated
on every real run (`benchmark`) or the real `main()` called by a pytest test against a synthetic tree
(`dial`, `kinds`); a regression in the pure logic here is caught only if the `suite` gate also runs.

**3 gates are inherently one-sided** (test runners: `compile`, `isolation`, `suite`).

**3 gates have NO red-side witness found — real debt, not a design choice**: `docs`, `projection`,
`generality`. This UPDATES 04-verification.md §2's "14/23 … `docs`/`projection` not confirmed" — direct
reading of every module (this page) resolves the "not confirmed" cases to a confirmed absence, and finds
2 more embedded witnesses than that section's older count credited (`design_eval`, `state_snapshot`,
`state_fidelity`, `slot_footprint`, `plan`, `codegen_freeze`, `roles`, `least_priv`, `column_parity`,
`kinds`, `dial`, `benchmark` post-date or were undercounted by that narration).

14 + 3 + 3 + 3 = 23.

## 2. Check-kind catalogue — the frozen vocabulary (29 kinds)

Single source: `KINDS`, `src/metafactory/verify/checks/registry.py:21-28`. Resolved to an argv by
`resolve_check(check, ctx, station, subst)`, `registry.py:40-192` (an unknown kind raises `ValueError`
naming `KINDS`, `:192` — a construction-time guard, distinct from the `kinds` runtime gate above that
scans committed YAML). `PY = sys.executable` (`:15`); `_s()` substitutes `{{var}}` via `subst` before
argv assembly (`:31-37`).

| Kind | Argv (`resolve_check`) | Check-entry keys | Purpose |
| --- | --- | --- | --- |
| `py_compile` | `[PY, -m, py_compile, *files]` — `registry.py:42-44` | required: `files` (list) | Byte-compiles the listed files (syntax validity) |
| `import_runs` | `[PY, -c, code]` — `:45-46` | required: `code` (string) | Runs arbitrary Python in-process; the code's own `assert`/exception decides pass/fail — the generic "run and let it assert" kind |
| `artifact_contains` | `[PY, -m, metafactory.verify.checks.artifact_contains, file, marker]` — `:47-49` | required: `file`, `marker` | A rendered artifact contains a literal marker string |
| `spec_validate` | `[PY, -m, metafactory.spec.cli, validate, spec]` — `:50-51` | required: `spec` | The factory-spec passes SDD validation (`spec/validator.py`) |
| `rtm_closure` | `[PY, -m, metafactory.spec.cli, rtm-closure, spec]` — `:52-53` | required: `spec` | Every requirement's `satisfied_by` is non-empty and points at an active station |
| `design_review` | `[PY, -m, metafactory.spec.cli, design-review, spec]` — `:54-55` | required: `spec` | The spec's design-review pass (tech⇒primitive shape checks) |
| `pytest` | `[PY, -m, pytest, -q, path]` — `:56-57` | required: `path` | A pytest module/dir passes |
| `isolation` | `[PY, -m, pytest, -q, path or "tests/test_isolation.py"]` — `:58-59` | optional: `path` (default `tests/test_isolation.py`) | The isolation-guard suite passes — a specialisation of `pytest` with a hardcoded default target |
| `docs_check` | `[PY, -m, metafactory.verify.checks.docs_check, repo_root()]` — `:60-61` | none beyond `kind` | The doc-consistency check (gate `docs`, §1), usable from any station's `checks:` list |
| `command` | the literal `cmd` list, substituted — `:62-63` | required: `cmd` (list) | The escape hatch: an arbitrary argv IS the check (used by `meta check`'s own gate roster) |
| `column_selftest` | `[PY, -m, …column_selftest, factory_root]` — `:64-65` | none beyond `kind` (uses `subst.factory_root`) | The newly-installed seed library rejects a tampered verdict (M1's miniature blocking proof, library level) |
| `column_full` | `[PY, -m, …column_full, factory_root]` — `:66-67` | none beyond `kind` | The wired hooks (`commit_guard` + `stop_proof`) actually BLOCK a tampered verdict when invoked as the harness invokes them (M1's proof, hook level) |
| `command_runs` | `[PY, -m, …command_runs, factory_root]` — `:68-69` | none beyond `kind` | Every generated Claude Code `command` actually runs (exit 0), not a dead file |
| `bus_bounded` | `[PY, -m, …bus_bounded, max_lines]` — `:70-71` | none beyond `kind` (uses `subst.max_lines`, default 10) | A synthetic FAILING 3-check proof's formatted verdict stays ≤ `max_lines` |
| `product_run` | `[PY, -m, metafactory.cli, product-run, --factory, slug]` — `:72-73` | none beyond `kind` (uses `subst.slug`) | The factory's own product line builds and passes end-to-end (M8's façade-trap) |
| `boundary_survives` | `[PY, -m, …boundary_survives, factory_root, meta_root, spec_path]` — `:74-77` | none beyond `kind` | The domain/generated boundary (I-5) is non-decorative: a domain edit survives a re-scaffold, `generated/` always re-renders |
| `rtm_rederive` | `[PY, -m, …rtm_rederive, factory_root, meta_root, spec_path]` — `:78-81` | none beyond `kind` | Corrupting, in a hermetic copy, the proof of a station that satisfies a requirement makes the RTM fall to UNSATISFIED |
| `rtm_tree` | `[PY, -m, …rtm_tree, factory_root, meta_root, spec_path]` — `:82-85` | none beyond `kind` | The dynamic RTM tree (requirement→capability→station→artifact) is fully satisfied for every requirement |
| `clean_runner` | `[PY, -m, …clean_runner, factory_root, meta_root, spec_path]` — `:86-89` | none beyond `kind` | The product line rebuilds in a hermetic clone and every re-derived `proof_sha` equals the committed pin (M6, two-verifier doctrine) |
| `products_rederive` | `[PY, -m, …products_rederive, factory_root, meta_root]` — `:90-94` | none beyond `kind` | Every named product instance re-derives == its own pin in an isolated clean clone (R1, ADR-015); N/A if the factory has no instances |
| `agent_shadow` | `[PY, -m, …agent_shadow, factory_root, meta_root, spec_path]` — `:95-98` | none beyond `kind` | Every agent's declared prohibition (`shadows[]`) names a deterministic shadow that EXISTS and, if a hook, is WIRED (I-12) |
| `product_env` | `[PY, -m, …product_env, workdir, bootstrap-json, cmd-json]` — `:99-106` | required: `cmd`; optional: `workdir` (default `.`), `bootstrap` (default `[]`) | A proof command runs INSIDE the product's own toolchain (bootstrap creates a scrubbed env, DES-8), not the factory's |
| `infra_up` | `[PY, -m, …infra_up, workdir, up-json, proof-json, down-json, bootstrap-json, [timeout]]` — `:107-120` | required: `proof`; optional: `workdir`, `up`, `down`, `bootstrap`, `timeout` | Declared infra LEVANTA in the sandbox, a live proof uses it, teardown always runs (DES-9) |
| `mcp_tools` | `[PY, -m, …mcp_tools, workdir, prove-json, tools-json]` — `:121-128` | required: `prove`; optional: `workdir`, `tools` (default `[]`) | The generated MCP server exposes the declared tools and the prover invokes them over real JSON-RPC/stdio (DES-6) |
| `eval_gate` | `[PY, -m, …eval_gate, workdir, scorer-json, output, degraded, thresholds-json, bootstrap-json]` — `:129-141` | required: `scorer`, `output`, `degraded`, `thresholds`; optional: `workdir`, `bootstrap` | A declared scorer passes the REAL output against thresholds and FAILS the degraded output (MAT-4/DES-7) |
| `eval_floor` | `[PY, -m, …eval_floor, workdir, command-json, evidence, degraded, thresholds, bootstrap-json]` — `:142-156` | required: `command`, `evidence`, `degraded`, `thresholds`; optional: `workdir`, `bootstrap` | An adopted product's PINNED evidence re-verifies against its own floor; swapping in degraded evidence flips the gate (ADR-025 §3, opt-in, 0-model) |
| `live_run` | `[PY, -m, …live_run, workdir, run-json, output, degraded, properties-json, scorer-json, thresholds-json, provider_env, bootstrap-json]` — `:157-173` | required: `output`, `degraded`; optional: `workdir`, `run`, `properties`, `scorer`, `thresholds`, `provider_env`, `bootstrap` | The product runs against a REAL provider and is gated by declared properties+thresholds on the real AND the degraded output (MAT-5/DES-7/8) |
| `blast_radius` | `[PY, -m, …blast_radius, meta_root, baseline]` — `:174-181` | optional: `baseline` (default `baseline_verdicts.json`) | A promotion does not lower any downstream factory's verdict vs the committed baseline |
| `scenario_corpus` | `[PY, -m, …scenario_corpus, meta_root, [corpus]]` — `:182-191` | optional: `corpus` | A diverse corpus of scenario-specs exercises the engine before a promotion and none regresses |

### 2.1 Measured usage distribution (2026-07-27, re-derived by this page)

Two independent, reproducible sweeps — they disagree because they cover different YAML SURFACES, and
the disagreement is itself informative:

**(a) Repo-wide, line-anchored:** `grep -rn '^\s*kind:' --include='*.yml' --include='*.yaml' .` excluding
`.claude/worktrees/` (ephemeral agent clones, not canonical content) → **155 declarations in 51 files**.
This matches `04-verification.md §3` exactly and is reproduced here independently. Per-kind breakdown:
`product_env` **94**, `infra_up` **32**, `eval_gate` **10**, `live_run` **5**, `import_runs` **4**,
`command` **3**, `artifact_contains` **3**, `mcp_tools` **2**, `py_compile` **1**, `eval_floor` **1** — 10
distinct kinds, summing to 155. This method is block-style-only (`kind:` alone on its own line, under a
sibling `name:`); it does not see the flow-style `{ name: x, kind: y }` entries the meta engine's own
`src/metafactory/stations/*.yml` uses, so `isolation`, `docs_check`, `pytest`, `blast_radius`,
`scenario_corpus`, `spec_validate`, `rtm_closure`, `design_review`, `bus_bounded`, `column_selftest`,
`column_full`, `command_runs`, `product_run`, `boundary_survives`, `rtm_rederive`, `rtm_tree`,
`clean_runner`, `products_rederive`, `agent_shadow` show **zero** matches under this method alone —
mostly a blind spot of the regex, not real disuse (see (b)).

**(b) YAML-parsed, the `kinds` gate's own scan surface:** `kind_hygiene.used_kinds()`
(`verify/checks/kind_hygiene.py:58-74`) over `src/metafactory/stations/*.yml` +
`factories/*/stations/*.yml` + `factories/*/factory.spec.yml` (both YAML styles, real parse, not
regex) → **82 declarations across 24 of the 29 kinds**: `product_env` 37, `infra_up` 14,
`artifact_contains` 5, `eval_gate` 4, `import_runs` 2, `live_run` 2, and 18 kinds appearing exactly once
each (`spec_validate`, `rtm_closure`, `design_review`, `column_selftest`, `column_full`, `bus_bounded`,
`boundary_survives`, `rtm_rederive`, `rtm_tree`, `clean_runner`, `products_rederive`, `agent_shadow`,
`command_runs`, `product_run`, `eval_floor`, `py_compile`, `mcp_tools`, `command`). This scope excludes
`factories/*/products/*/product.yml` (where most of (a)'s `product_env`/`infra_up` volume actually
lives) by design — the `kinds` gate only needs to police the surfaces where a NEW kind could be
introduced (station templates + the spec), not every rendered product instance.

**Kinds with zero matches under BOTH methods:** `isolation`, `docs_check`, `pytest`, `blast_radius`,
`scenario_corpus` — five of the 29 frozen kinds have no committed YAML declaration anywhere in this
repo today (they exist for a factory that would need them; the vocabulary is closed by governance act,
not by measured demand — `registry.py:16-20`). This is an honest observation, not a defect: the closed
vocabulary is deliberately wider than today's usage (D-3, VOCAB-FREEZE).

The measured inversion the freeze exists to explain: `product_env` alone accounts for 60-70% of every
kind declaration in the repo (94/155 in (a), 37/82 in (b)); most of the remaining kinds are used once or
twice, and the freeze's bar for adding a 30th is explicitly "doesn't `product_env` + a script suffice?"
(`kind_hygiene.py:1-5`).
