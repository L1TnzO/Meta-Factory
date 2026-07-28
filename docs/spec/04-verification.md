<!-- meta:doc sha=cabbdac2afb934781d17066f892cc8d5ba4f7357 updated=2026-07-28T19:08Z -->
# 04 — The verification system (descriptive)

## 1. The two verifiers (ADR-005)

Every factory is born (meta station M6) with two CI verifiers:

1. **Factory CI** — "does the machine still know how to build?" (suite + one dummy; constant cost).
2. **Product CI** — "is this graduated product still healthy?"

Both are **re-derivation, not custody audit**: rebuild from a clean clone, run the gates fresh, compare
against the pinned honest verdict; deviation in ANY direction is red (`decisions/005:22-33`).
Independence hierarchy, stated in the ADR: hooks (same actor) < pre-push (another hour) < remote CI
(another machine and actor — *"the only layer untouchable by model, hooks, or the local engineer"*).
One implementation: all logic in `meta ci`; the hook and the YAML are transports of the same line.

## 2. `meta check` — the 23 gates (`cli.py:147-192`)

| # | Gate | Proves | Two-sided | Scope |
| --- | --- | --- | --- | --- |
| 1 | `compile` | `compileall` over `src/metafactory` + `seed` | no | repo |
| 2 | `docs` | doc corpus consistent: sealed & current, INDEX complete, no dangling links, STATE not stale | not found | repo |
| 3 | `projection` | memory projection is consistent | UNKNOWN | repo |
| 4 | `isolation` | `pytest tests/test_isolation.py` | no | repo |
| 5 | `generality` | ADR-014: a `status: general` substrate mechanism is proven green in ≥2 domains | **no witness found** | repo (gates only `status:general`) |
| 6 | `quality` | deterministic size/coupling/cycle bar over the live substrate graph | yes (`tests/fixtures/quality/monolith_shaped.py`) | repo |
| 7 | `pbt` | property-based gate over the graph; sabotage must bite | yes (`METAFACTORY_PBT_SABOTAGE=1`) | repo |
| 8 | `evidence_liveness` | a living doc's `CITES`-shaped refs resolve | yes (`tests/fixtures/docs/dangling_reference.md`) | repo |
| 9 | `security` | heritable secret / supply-chain scan, network-free, stdlib | yes (`tests/fixtures/security/planted_secrets.txt`) | repo |
| 10 | `deferred` | declared-deferred entries carry `trigger`/`since` and accumulation is measured | yes (fixture spec) | opt-in (`governance.deferral_tracking: strict`) |
| 11 | `benchmark` | sweet-spot products MEET the target and ceiling products must NOT | yes | opt-in per product |
| 12 | `dial` | an adopted draft→harden dial defers a non-empty PROPER subset | yes | opt-in per factory |
| 13 | `column_parity` | a factory's inherited column is byte-identical to M1's real re-materialization | yes | per-factory sweep |
| 14 | `least_priv` | the factory column is the exact least-privilege subset (no leak, no gap) ⊊ meta | yes | per-factory sweep |
| 15 | `roles` | every `.claude/agents/*.md` role ∈ closed vocabulary | yes (embedded self-test planting a synthetic domain-named agent `kotlin-writer`; prints `GATE DECORATIVO` if it fails to flip) | repo (meta + all factories) |
| 16 | `kinds` | every check-kind in YAML ∈ frozen `registry.KINDS` | yes (via `tests/test_kind_hygiene.py`) | repo |
| 17 | `codegen_freeze` | the ADR-023 §3 codegen freeze is not pierced without a written waiver | yes (3 synthetic scenarios) | repo, triggered by factories with `codegen/` |
| 18 | `plan` | `.gen/plan.json` is well-formed if present; N/A-green if absent | yes | opt-in |
| 19 | `slot_footprint` | delegation footprint honesty; real hooks fail **closed** on a broken law | yes (GREEN / RED / FAIL-CLOSED) | repo + live-slot mode |
| 20 | `design_eval` | the adopted design-critique evaluator actually discriminates (pinned critiques vs pinned floor) | yes (embedded self-test) | opt-in (factory publishes `design/criteria.yml`) |
| 21 | `state_snapshot` | STATE's `## Ahora` stays a bounded snapshot, not a growing log | yes | repo |
| 22 | `state_fidelity` | `Ahora` prose does not contradict the RTM re-derived from `.proof/` | yes (synthetic oracle, no filesystem) | repo |
| 23 | `suite` | `pytest -q tests` | no | repo |

`--skip` is honest: a skipped gate never counts as green and is printed as skipped (`cli.py:194-205`).

**Two-sidedness census: 14 / 23 carry an explicit red-side witness.** `compile`, `isolation`, `suite`
are test runners (inherently one-sided). `docs`, `projection` were not confirmed. **`generality` has no
red-side witness found** — the only gate whose tooth is unproven. This is debt, not a design choice.

## 3. Check kinds — the frozen vocabulary (29)

Single source `verify/checks/registry.py:21-28`:

```
py_compile · import_runs · artifact_contains · spec_validate · rtm_closure · design_review · pytest ·
isolation · docs_check · command · column_selftest · column_full · bus_bounded · product_run ·
boundary_survives · rtm_rederive · rtm_tree · clean_runner · agent_shadow · product_env ·
command_runs · infra_up · mcp_tools · eval_gate · eval_floor · live_run · blast_radius ·
scenario_corpus · products_rederive
```

**Measured distribution (2026-07-27, `grep '^\s*kind:'` across all YAML):** 155 `kind:` declarations in
51 files. `product_env` = **94**, `infra_up` = 32, `eval_gate` = 10, `live_run` = 5, `import_runs` = 4,
`command`/`artifact_contains` = 3 each, `mcp_tools` = 2, the rest appear once or twice.

> The registry docstring still claims "72 / ~130" and `kind_hygiene.py:2` says "~32 kinds". Both are
> **stale historical claims**. The live numbers are 94/155 and 29. A re-implementation should derive
> this figure rather than restate it — the inversion it reveals is a real design signal (§09.3).

`resolve_check(check, ctx, station, subst)` (`registry.py:40-192`) maps kind → argv; an unknown kind
raises `ValueError` naming `KINDS` — a construction-time guard, distinct from the `kinds` runtime gate
that scans committed YAML.

## 4. The verdict bus (I-7)

- Struct: `@dataclass Verdict{verb, status, exit_code, summary, counts, failures, artifact, next_action}` — `verify/report.py:23-32`.
- Format (printed, not persisted): `VERDICT <verb> — <PASS|FAIL> (exit N)` / `SUMMARY` / `COUNTS` / `FAILURES ≤5` / `ARTIFACT <log path>` / `NEXT` — `report.py:87-101`.
- Construction: `from_proof()` (`report.py:57-84`) reads `proof["checks"]`, computes pass/fail from `int(c["exit"])`, and mines `file:line` from the on-disk log **only on failure** (`_extract_fileline`, `:35-54`). The raw log is never embedded — only pointed at.
- Bound: check kind `bus_bounded` builds a synthetic 3-check FAILING proof and asserts the formatted verdict is ≤ `max_lines` (default 10). Exit 1 prints `BUS UNBOUNDED` (`checks/bus_bounded.py:1-30`).
- Consumption: `cli._print_verdict()` prints the bounded text; the full log is mirrored to `.meta_check/<ts>.log` and opened on demand (`cli.py:126-138`).

This is the mechanism that keeps an orchestrator's context small. It is a first-class invariant, not an
optimization.

## 5. Exit semantics

- **Contract:** "Every kind is subprocess-shaped: exit 0 == pass" (`registry.py:4`).
- `passed` derives strictly from captured `returncode`s (`seed/verifier.py:112-113`); empty check list ⇒ `False`; unlaunchable check ⇒ exit 127 recorded.
- Lock #2 re-computes and rejects tampering (`:171-185`).
- **Can green appear without a process exiting 0?** No path found. The closest honest exception: **opt-in gates report green as "N/A"** when a factory has not adopted the feature (`plan` with no `.gen/plan.json`, `dial`/`products_rederive` on a non-adopter). That is still a process exiting 0, but it is a *vacuously true* branch, named explicitly as "SAFE-7 doctrine" (`plan_gate.py:9`).

> **v3 requirement:** vacuous-true branches must be *counted and printed* as N/A in the summary line,
> not silently folded into the green count. Today they are printed, but the count is not separated.

## 6. What stops a decorative gate

| Mechanism | Effect |
| --- | --- |
| Two-sided witnesses | 14/23 gates fail loudly (`GATE DECORATIVO`) if their red side stops biting |
| `kind_hygiene` | freezes the check-kind vocabulary; a new kind = edit the constant + an ADR |
| `role_hygiene` | freezes the agent-role vocabulary the same way |
| `generality_parity` | forbids declaring a substrate mechanism `general` on single-domain proof (≥2 factories, proofs re-verified via `gate_recompute_ok`) |
| `column_full` | proves the WIRED hooks block a tampered proof — the seed's locks alone would be decorative if the hooks were never invoked |
| `quality` dogfooding | the meta repo is gated by its own size/coupling bar |

## 7. Honest gaps (quoted, not paraphrased)

From ADR-017 (`decisions/017:71-73`):

> *"Calibración honesta (no es «nunca revisar»): los gates NO atrapan no-ops semánticos (oráculo malo),
> bugs de seguridad (29-45% del código IA), paquetes alucinados (~20%) ni spec ambigua. Se confía en el
> gate para el GRUESO y se gastan ojos de Opus SÓLO en el residuo irreducible."*

Corroborated inside the checks themselves:

- `security_scan.py:4-5` — "AI-written code ships secrets and hallucinated/vulnerable deps at meaningful rates … a green functional gate is necessary but NOT sufficient."
- `rtm_tree.py:111` — the N/A branch admits *"la hoja proof→artifact no se re-deriva — evidencia rancia no detectada"* when no requirement declares an artifact.
- `codegen_freeze.py:29` — "the honesty of the declared `alcance` is judged by eyes at review — the irreducible residue, like every gate here."
- `evidence_liveness.py` — `EVIDENCES` targets (arbitrary code/proof paths) are never gated; many are legitimately ephemeral. Only `CITES`-shaped doc references are checked.
- `generality_parity.py` — no embedded red-side witness found; its two-sidedness is **unconfirmed**.

## 8. Test corpus

~70 test modules pin the gates, one per mechanism, e.g. `test_kind_hygiene`, `test_role_hygiene`,
`test_column_parity`, `test_least_priv`, `test_state_fidelity`, `test_slot_residency`,
`test_delegation`, `test_blast_radius`, `test_rtm_tree`, `test_hermetic`, `test_mutation_escape`.
Red-side fixtures live under `tests/fixtures/` (`quality/monolith_shaped.py`,
`docs/dangling_reference.md`, `security/planted_secrets.txt`, `governance/strict_untracked.factory.spec.yml`).

**v3 keeps this corpus as the migration harness** — it is the most valuable non-obvious asset in the
repo, because it is what makes the rebuild's equivalence claim checkable rather than aspirational.
