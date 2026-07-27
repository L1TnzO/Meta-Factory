<!-- meta:doc sha=6698d42bc3fe0617bbee37a97c535afce1dfe0c1 updated=2026-07-27T21:41Z -->
# 03 — The engine: spec → factory → product (descriptive)

## 1. The pipeline, stage by stage

| Stage | Function | Writes |
| --- | --- | --- |
| Parse | `load_spec()` `spec/loader.py:60` | in-memory `FactorySpec` |
| Register a factory | `cmd_new()` `cli.py:227` (copies spec, runs `validate()`) | `factories/<slug>/factory.spec.yml` + `.metafactory.json` (`cli.py:236`) |
| Run the META line `m00→m08` | `cmd_station()` `cli.py:261` → `run_station()` `engine/runner.py:69`; sequence from `src/metafactory/stations/*.yml` | `.proof/<station>.json`, `.proof/active.json`, `.proof/ledger.json` |
| Materialize the PRODUCT line | `_materialize_line()` `codegen/renderer.py:129` (meta station `m02`) | `factories/<slug>/stations/<id>.yml`, one file per `SpecStation` |
| Emit the harness | `_emit_harness()` `codegen/renderer.py:238-264` (meta station `m07`) | `factories/<slug>/.claude/{agents,commands,skills}` |
| Instantiate a named product | `ensure_product_instance()` `cli.py:72` | `products/<p>/product.yml` (committed) + derived `products/<p>/factory.spec.yml` (effective spec) + `products/<p>/stations/` |
| Build a product end-to-end | `cmd_product_run()` `cli.py:323` → `_run_product_line()` `cli.py:275` over `load_sequence(fdir/"stations")` | station proofs under the product root's `.proof/` |
| Pin | `_pin_from_proofs()` `cli.py:498-511` | `pinned_verdict.json` = `{station_id: proof_sha}` |
| Re-derive (CI) | `rederive_pinned()` `cli.py:435-453` | wipes `.proof/` + `build/`, re-runs the line, then `_compare_to_pinned()` `cli.py:421-432` |

The meta line has **9 stations (m00..m08)**; factory/product lines have 5–13 stations (§08).

## 2. Factory spec grammar (`factory.spec.yml`)

Top-level keys: `factory · domain · machinery · factory_substrate · requirements · governance`.

| Key | Shape | Enforcement |
| --- | --- | --- |
| `factory` | `{name, slug, maturity}` — all required | `spec/validator.py:29-46` |
| `domain` | `{produces, target_framework, required_primitives, product, constraints, capabilities, station_sequence, provision_modes, proof_check_types}`; `produces` and `station_sequence` (≥1) required | `validator.py` |
| `machinery` | `{harness, mcp, infra}` — OPTIONAL, pure DATA (ADR-012), only shape-checked | `_validate_machinery` `validator.py:210` |
| `factory_substrate` | `{anti_rubber_stamp_column, verdict_bus, generated_domain_boundary, memory_schema, rtm, two_verifier_ci, placement_law, context_budget}` | only `anti_rubber_stamp_column == True` and `verdict_bus.max_lines > 0` are hard-enforced — `validator.py:49-59` |
| `requirements` | `{functional: [...], nonfunctional: [...]}` | RTM closure, `validator.py:62-81` |
| `governance` | e.g. `{deferral_tracking: strict}` | `spec/model.py:118,123-126` |

> ⚠️ **Finding:** `spec/factory.schema.json` exists and declares `required: [factory, domain, factory_substrate, requirements]`, but **no Python file references it** (grep returns nothing). Validation is hand-written in `validator.py`, not JSON-Schema-driven. The schema file is dead weight that reads as authoritative — a trap for a re-implementer. Recorded as debt (§09.3).

### 2.1 Station entry (inside `domain.station_sequence`)

Parsed by `_station()` `spec/loader.py:31`. Keys:
`id · name · activation(always|off, default always) · depends_on[] · proof_checks[] · status · builds[] · checks[] · deferral{trigger,since} · tier(core|harden, default core)`.
`id` is required and must be unique (`validator.py:40-45`).

## 3. The station model

`@dataclass Station` — `engine/station.py:12-25`:
`id · name · activation · builds:list[dict] · checks:list[dict] · requires_prev:str|None · depends_on:list[str] · tier · raw:dict`

| Concept | Semantics | Anchor |
| --- | --- | --- |
| `active` | `activation != "off"` | `station.py:42-43` |
| `active_in(dial)` | a `tier: harden` station is INACTIVE when `dial == "draft"` | `station.py:45-49` |
| `when:` on a check | DATA-only guard (`dict[key] -> value`); a non-matching guarded check is **skipped entirely** and never enters `cmds`, preserving a byte-identical `proof_sha` | `engine/runner.py:56-66` |
| `builds` | what the station writes (the analogue of "emits") | — |
| `depends_on` / `requires_prev` | predecessor gating (the analogue of "requires") | `engine/sequence.py:42-88` |

There are **no** `emits`/`requires` fields by those names — a re-implementer looking for them will not find them.

## 4. The line (`Sequence`)

`load_sequence(stations_dir)` — `engine/sequence.py:25-101`:

- loads `*.yml`, skipping `_`-prefixed files;
- orders by `_natural_key` (numeric-aware, so **`s9 < s10`**) — `sequence.py:16-22, 91-101`;
- predecessor resolution: explicit `depends_on` fan-in (ALL must be green), else `requires_prev` / previous-active linear chain;
- a DEFERRED predecessor (`activation: off`, or draft-deferred by the dial) is **transparent**: the gate falls through to *its* predecessors (`sequence.py:54-62, 72-81`). This is what makes the draft dial safe.

Execution — `run_station()` `engine/runner.py:69-106`:
`apply_builds` → `write_active` (`runner.py:32-53`) → resolve + run active checks → `ctx.verifier.verify_station()` (the SEED, not the engine) → `open_gate()` → journal append.

> The engine never computes `passed`. It hands the checks to the seed verifier and asks the gate to
> open. That separation is Lock #1/#2 (§02.2) and must be preserved verbatim.

## 5. The product model (1:N, ADR-015)

A product blueprint (`products/<p>/product.yml`) is small, typed and human-authored. Example keys from
`factories/full-stack-kotlin/products/helpdesk/product.yml` (92 lines):
`station_activation · package_name · api_title · frontend_surface · roles · owner_bypass_roles · entities`.

One entity verbatim:

```yaml
name: Agent
write_roles: [admin]
fields:
  - {name: email, type: string, unique: true}
  - {name: full_name, type: string}
  - {name: tier, type: enum, values: [l1, l2, l3]}
  - {name: active, type: boolean}
```

- `station_activation: {s6: false}` is a **reserved instance key**, popped before the merge into the effective spec (`cli.py:96`).
- `meta product new --factory F --name P <blueprint>` copies the blueprint, runs the line, pins (`cli.py:350-400`).
- `meta product-run --factory F [--product p] [--mode draft|harden]` runs the line end-to-end (`cli.py:323`).
- **Roots:** the default product IS the factory root (`root == chassis`). A named instance has
  `root = factories/<slug>/products/<p>` but `chassis = factories/<slug>` — the generator is shared, the
  evidence is per-product (`engine/run_context.py:15-24`, `cli.py:314-320`).

## 6. RTM — two of them, on purpose

| RTM | What it proves | Anchor |
| --- | --- | --- |
| **Static (M0)** | every `Requirement.satisfied_by` is non-empty and points at an ACTIVE station id | `validator.py:62-81` |
| **Re-derived (dynamic)** | requirement → capability (real, non-phantom) → station(s) (proof present AND `gate_recompute_ok`) → artifact (rendered path exists on disk). `ReqNode.satisfied` requires ALL edges true | `verify/rtm.py:41-46, 70-94` |

`Requirement` = `id (REQ-<AREA>-NNN) · statement · satisfied_by[] · verified_by[] · capability · acceptance · kind` (`spec/model.py:91-104`). A `verified_by` pointing at an undeclared `proof_check.name` is a **phantom verifier** and is M0-red (`validator.py:194-207`).

The dynamic RTM is driven *only* from spec + `.proof/` + the filesystem — "not from prose" (`verify/rtm.py:1-17`). It is exposed both as `meta rtm` and as the `rtm_tree` check kind, sharing one implementation.

## 7. Proof and pin

`.proof/<station>.json`, written by `seed/verifier.py:verify_station()` (`:90-143`):

```json
{"station": "s3", "passed": true,
 "checks": [{"name": "...", "cmd": [...], "exit": 0}],
 "computed_at": "...", "proof_sha": "...", "writer": "...", "log_path": "..."}
```

- `passed = recompute_passed(checks)` = `len(checks) > 0 and all(exit == 0)` (`:56-59`).
- A check that cannot launch → **exit 127** recorded (fail-safe) (`:114-119`).
- `proof_sha = sha256(json({"station": id, "checks": sorted[(name, exit)]}))` — excludes time, output, machine (`:62-72`).
- `gate_recompute_ok(proof)` re-computes both from the proof's own `checks` and rejects mismatch (`:171-185`).
- `pinned_verdict.json` = `{station_id: proof_sha}` for every ACTIVE station (`cli.py:498-511`).
- `ci --rederive` deletes `.proof/` + `build/`, re-runs the line, and demands equality **in both directions** (`cli.py:421-453`). `--all-products` re-derives the default plus every named instance in isolated roots (`cli.py:472-479`).
- The underlying primitive is `verify/verdict.py:rederive_verdict` (`:29-60`): a throwaway `tempfile.mkdtemp` clone with `.proof`/`build` excluded from the copy and then wiped.

## 8. Generation: the substrate orchestrates, it does not generate (ADR-013)

- Codegen lives per-factory in `factories/<f>/codegen/` and is invoked as a station build.
- On generation failure the destination is DELETED before regenerating and left absent — **no fake green** (`codegen/renderer.py:353-396`, esp. `:371-374`).
- Tech is never whitelisted: a declared technology must map to a declared primitive, checked generically (`validator.py:114-122`).
- **All factory codegen is FROZEN** by ADR-023 §3; piercing it requires one `Codegen-freeze-waiver:` line in the owning level's OPEN work-doc, enforced two-sided by the `codegen_freeze` gate.

## 9. Invariant enforcement map (where a re-implementer must look)

| Invariant | Enforced at |
| --- | --- |
| I-2 stations-as-data | by construction: `engine/station.py:1-6`, `sequence.py:1-4`; engine reads only YAML |
| Lock #1 | `seed/verifier.py:2,8-11,55-59` |
| Lock #2 | `engine/gate.py:28-32` → `seed/verifier.py:171-185` |
| Gate DAG (fan-in never skips an unproven branch) | `engine/gate.py:35-45` |
| ADR-012 tech⇒primitive | `spec/validator.py:114-122` |
| No phantom verifier / capability (SAFE-4/7) | `spec/validator.py:194-207` |
| No fake green on generation failure (I-3) | `codegen/renderer.py:353-396` |
| Deferred debt with teeth (opt-in `strict`) | `spec/validator.py:96-111` |
| Cycle-free `depends_on` | `spec/validator.py:168-191` |
| Closed check-kind vocabulary | `verify/checks/registry.py:16-29` |

## 10. Verified claim: no domain branching in the engine

`grep -rniE "kotlin|snipeit|helpdesk|gradle|django|react|postgres"` over `src/metafactory/engine/`,
`src/metafactory/spec/`, `src/metafactory/codegen/` → **zero matches**. All tech-specific behaviour
lives as DATA inside each factory's `factory.spec.yml` (e.g. FSK station `s5` carries
`python3 tools/route_check.py …` as a literal argv). **I-2 holds** in the audited scope.
