<!-- meta:doc sha=4e15332d1bed4974058311f1aa6ea72d0bcd4e4e updated=2026-07-31T23:27Z -->
# 11 — Build plan for v3 (JUDGMENT)

## 1. Strategy: rebuild the control plane, port the kernel, keep the oracle

This is **not** a greenfield rewrite. It is a rebuild with a test oracle that already exists:

- the **kernel** (proof/station/sequence/gate/pin/report) is ported nearly verbatim — it is the moat;
- the **control plane** is rebuilt on the SDK — it is where all accidental complexity lives;
- the **five factories stay exactly where they are** and are migrated one at a time;
- acceptance is decided by re-derivation against the committed pins, not by review.

## 2. The parity criterion — and its honest limit

`proof_sha = sha256(json({"station": id, "checks": sorted[(name, exit)]}))`.

It hashes **check name and exit code** — not the command, not the implementation, not the output. Two
consequences, and both matter:

✅ **A re-implementation preserves parity by construction** as long as it keeps the same check NAMES and
those checks still exit 0. We may replace the machinery behind `column_selftest` or `product_env`
entirely and still re-derive an identical pin. This is what makes an SDK rebuild verifiable at all.

⚠️ **The pin does NOT detect a weakened check.** A check with the same name that still exits 0 but now
tests nothing produces an identical `proof_sha`. The pin proves *the same checks still pass*; it does
**not** prove *the checks are still as strong*.

> Therefore the acceptance of v3 is TWO conditions, never one:
> **(P1)** `ci --rederive --all-products` == the committed `pinned_verdict.json` for all 5 factories, and
> **(P2)** every two-sided witness still goes RED when sabotaged — the red side is re-run, not assumed.
> P1 alone would accept a hollow rebuild.

## 3. Increment sequence

Each increment is bounded, has a deterministic gate, and is closed with `meta increment close`. Sizes
are honest estimates, not commitments.

| # | Increment | Delivers | Gate (the acceptance test) | Size |
| --- | --- | --- | --- | --- |
| **INC-0** | `SDK-PROBE` | answers to the six open questions of §10.11; a pinned `sdk_facts.json`; a symbol-table test | the test fails loudly if any quoted SDK symbol moves; the six answers are recorded as DATA, not prose | S |
| **INC-1** | `KERNEL-PORT` | `v3/kernel/*` transcribed from §14 (the spec, not the v2 code) | **hermetic**: recompute `proof_sha` with the NEW code over the 84 committed **pin-anchored vectors** and compare to the TEN committed `pinned_verdict.json` (5 factory + 5 product lines). No toolchain, no builds, seconds to run | M |
| **INC-2** | `CONTROL-PLANE` | `control/{options,agents,hooks,tools,permissions}` — the 12 hooks as callbacks, the 5 roles as `AgentDefinition`, the verbs as MCP tools | the `column_full` analogue: a **tampered proof** must be refused by the WIRED hooks running under the SDK host; two-sided (untampered ⇒ green) | L |
| **INC-3** | `DELEGATION-V3` | `Slot` dataclass, `SubagentStart` binding, `can_use_tool` + hook double layer, typed verdict, `rewind_files` rollback | `slot_footprint` two-sided (GREEN / RED / FAIL-CLOSED) **plus** one real delegated slot end-to-end whose bash-mediated write is caught | M |
| **INC-4** | `CHECKS-PORT` | the 29 kinds + the 23 gates on the new registry | all 23 run; **all two-sided witnesses re-bite**; the new rule lands: a gate without a red witness cannot register — which forces `generality` to finally get one | L |
| **INC-5** | `MEMORY-DOCS` | docs manifest, seal, INDEX, lineage, STATE teeth | the 5 corpus gates run over the EXISTING corpus (327 docs, 2,722 citations) and each has a re-runnable red side — the corpus is the fixture | M |
| **INC-6** | `ECONOMY-TYPED` | ledger and outcome from typed usage; **the context meter** (§10.6); iteration metrics (§09.4 A-2) | two-sided ledger gate + the escape-threshold observer emits real numbers for (a) and (b); the transcript parser is DELETED | M |
| **INC-7** | `MIGRATE-DUMMY` | the fixture factory on v3 | `ci --rederive` == pin (5/5 stations) | S |
| **INC-8** | `MIGRATE-IOT` | a LIVE factory, hermetic Go, no external services — **and the product INSTANCE (R1)** | `ci --rederive` == pin for **every TARGET**: 15/15 stations across 3 (`dummy`, `iot`, `iot/fleet`) | S |
| **INC-9** | `MIGRATE-FSK` | the real system: 12 stations, 3 products, live PG + Chromium | `ci --rederive --all-products` == pin (27/27) + `meta benchmark` 2/2 in the expected class | XL |
| **INC-10** | `MIGRATE-FROZEN` | ASF + full-stack — **re-verification only, zero new generation** | `ci --rederive` == pin (11/11, 6/6) | S |
| **INC-11** | `CUTOVER` | v2 substrate deleted; `meta` becomes the thin shell over v3 | all of P1 + P2 green in one clean-clone run on another machine (the ADR-005 independence layer) | M |

> **CORRECTED 2026-07-31 by INC-11's opening measurement (three things), before writing any code.**
> (a) **The size is wrong: `M` → `XL`.** The row hides five distinct deliverables, none optional — the
> verb surface (`v3/cli.py` + `control/tools.py`; `v3/verify/kinds.py` already *declares* `v3.cli`, and
> it does not exist), the nine v2 symbols that ten meta hooks import, the META line `m00..m08` and its
> 16 factory-line-less kinds (`N-0098`), 67 of 71 test modules, and the deletion itself. Same defect as
> INC-8's row, one layer up: a row that hides a class. (b) **The acceptance vehicle re-derives 5 of the
> 84 pinned stations.** The external CI runs `./meta ci --rederive` with no `--all-products` and no
> `--factory`, so it re-derives **`dummy` only — 1 of 10 targets, 5 of 84 stations**, and it has been
> **FAILING since 2026-07-11** (3 red: `evidence_liveness` = `N-0102`, `codegen_freeze` = `N-0084`,
> `suite`) while local `master` ran **50 commits ahead** of what that second actor ever saw. §11.6
> clause 1 is therefore **not executable as written**: it asks for 55 stations on a machine that can
> produce 5 without JDK 21, PostgreSQL, Chromium and Go. Either the runner earns that toolchain, or the
> clause splits into two actors with DECLARED and different scopes — what it may not do is let "P1
> green on another machine" read as if it covered the 84. (c) **`55/55` across `5/5 factories` is the
> wrong counter for the third time** — the unit is TARGETS, not factories (INC-8 fixed it for
> `iot/fleet`, INC-10 for `full-stack/tasks`). The number is **84 across 10 targets**, and it is the
> sum of the ten committed pins. Two ordering faults the row also hid, recorded here because they are
> decisions and not discoveries: `rehydrate` was sent to **INC-12** by INC-5's correction while
> `session_start` imports it TODAY (INC-11 would delete v2 one increment before its replacement
> exists — it is pulled forward), and **deleting v2 disarms `import_boundary`'s red side**
> (`v3/verify/import_boundary.py:193` plants `import metafactory`; with v2 gone the red is unplantable
> and the gate falls to N/A forever — the `N-0111` class, applied to the very gate that guarded the
> boundary). Full measurement: `docs/work/V3-INC11-CUTOVER-INCREMENT.md`.
>
> **CORRECTED 2026-07-31 by INC-8's execution (three things).** (a) **`6/6` was the wrong counter.**
> `iot`'s pin has **5** stations (`s0..s4`); `6/6` is its **RTM** (6 requirements, the `STATE.md`
> projection). Two different instruments got read as one. (b) **The row's stated deliverable was
> already done.** `iot`'s factory line re-derived 5/5 == pin on v3 with ZERO platform change, measured
> before writing code — INC-7's splice already covered it, since `iot` only exercises `product_env`,
> `infra_up` and `generate`. What the row HID is the **product instance**: `iot` has `products/fleet/`,
> `dummy` had no `products/` at all, and v2's acceptance is `--all-products` = the default PLUS every
> instance, each with its own root and pin. Reporting "5/5" would have left `fleet` entirely unrun
> while the number went up. Hence the acceptance now counts **targets**, not factories. (c) Hermetic Go
> is TRUE and now measured rather than asserted: the generated `go.mod` carries **zero `require`**
> (standard library only), which is why `GOPROXY=off` needs no module cache and no network.
>
> **CORRECTED 2026-07-29 by INC-5's execution (three things).** (a) The corpus numbers were stale:
> measured on the same instrument, it is **327 docs / 2,722 citations**, not 283 / 2,373 — the
> corpus grew ~15 % while the row sat still, which is why the acceptance now names the instrument
> rather than a frozen count. (b) `docs_check` alone was the wrong acceptance: it is ONE of the five
> gates this row owns, and naming it invited the other four to land unmeasured. (c) **`SessionStore`
> handoff is struck from this row.** It is not the corpus — it is the session loop, which §10.0's
> inversion moved: `rehydrate` becomes "what the host injects per leaf" (§15.6, needs the node tree)
> and belongs to **INC-12**; `precompact` becomes a `PreCompact` hook and belongs to **INC-6**; and
> `journal`, examined during INC-5, has no v3 caller until the host runner journals its runs, so it
> too goes to **INC-6** (nodes `N-0086`, `N-0087`, `N-0089`). Porting them here would have carried
> the shape of a loop we deliberately stopped having.
>
> **CORRECTED 2026-07-28 by INC-1's first run.** This row used to say "the 5 factories' already
> committed `.proof/*.json`". **`.proof/` is gitignored** — `git ls-files | grep .proof/` returns
> zero, so that oracle does not exist. What is committed, and exists precisely because someone hit
> this before, is `docs/spec/fixtures/proof-sha-vectors.json` (84 vectors of
> `origin·station·checks·proof_sha`, each anchored to a pin). The hermetic chain is therefore two
> independent links: **recompute the sha from the checks → it must equal the vector → the vector must
> equal the committed pin.** Checking only the first link would be self-referential.

**Dependency order is real:** INC-1 before everything (nothing is verifiable without the kernel);
INC-0 before INC-2 (do not design against a guessed API); INC-4 before any migration (a factory cannot
re-derive without its check kinds); dummy → iot → FSK by ascending toolchain pain.

## 4. What is ported, rewritten, dropped

| Ported nearly verbatim | Rewritten on the SDK | Dropped |
| --- | --- | --- |
| `seed/verifier.py` (the three locks) | the 12 hooks | `column_parity`, `column_selftest` (no copies left to compare) |
| `engine/{station,sequence,gate,runner}` | agent definitions | the transcript parser |
| `verify/report.py` (verdict bus) | the ~30 CLI verbs as agent-facing tools | `spec/factory.schema.json` (dead file) |
| `spec/{model,loader,validator}` + RTM | metering and routing | `meta recall` tombstone |
| the 29 check kinds and their argv mapping | the delegation plumbing (binding, permissions, rollback) | the Spanish/English dual-accept regex |
| `docs_manifest`, lineage, STATE teeth | session/handoff persistence | per-factory harness copies |
| the ~70 test modules and their RED fixtures | — | — |

### 4.1 About the frozen codegen — a precision on §09.3 K-5

"Do not port the codegen" means: **do not carry it into the meta substrate and do not evolve it.** The
frozen `codegen/` directories stay exactly where they are, inside their factories, as opaque artifacts
that v3 *invokes* as station builds. This is what preserves parity for FSK/ASF/iot. The `codegen_freeze`
gate is ported unchanged, so piercing them still requires a written waiver.

## 5. Risks and their responses

| Risk | Response |
| --- | --- |
| The SDK API moves under us (0.2.x, fast-moving) | INC-0 pins a symbol table and fails loudly; the version is recorded in the assumption ledger with a re-measure trigger |
| Hook semantics differ from the CLI's hooks in a way that weakens the column | INC-2's gate is the tampered-proof test — if the column does not bite under the SDK, the increment is red and we stop. **This is the go/no-go point of the whole plan** |
| FSK migration (INC-9) is the long pole: live PG, Chromium, gradle, 3 products | run it in `--mode draft` in the inner loop (41.7 s vs 98 s) and harden only at close; keep the toolchain shim (`tools/toolchain.sh`) — JDK 21 has vanished between sessions before |
| The rebuild becomes a second system that never lands | the plan has NO increment that improves anything before INC-11. New capability (A-1..A-9) lands only after cutover, except where it is free (the context meter rides INC-6) |
| Parity accepted on a hollow re-implementation | P2 (§11.2): the red sides are re-run, never assumed |
| Cost of the rebuild itself | INC-1, INC-4, INC-5, INC-7, INC-8 are gate-rich and delegable as slots (S2 sessions, Sonnet). INC-0, INC-2, INC-3 are COLUMN — trust-chain, written and reviewed with one's own eyes, never delegated |

## 5bis. Two amendments from the inversion (§10.0)

1. **INC-2 changes nature.** It is no longer "port the hooks to the SDK"; it is **write the host** —
   the deterministic state machine that owns the loop and calls the model as a bounded function. The
   hooks become defence-in-depth inside a generation leaf. Its gate is unchanged and is still the
   go/no-go of the whole plan: a tampered proof must be refused by the wired enforcement.
2. **A new increment is required, and it is not optional.** `INC-12 INTERACTIVE-MODE`: an attach mode
   that drives the same orchestrator from a conversation. The inversion removes an escape hatch we
   currently rely on — inside Claude Code an operator can notice something odd and go look; a headless
   state machine cannot improvise. Rebuilding that capability deliberately is cheaper than discovering
   its absence after cutover. Gate: the same station, run headless and run attached, produces the same
   pin.

## 6. Definition of done

v3 is done when **all** of these hold in a single clean-clone run on a machine that is not the
development machine:

1. `ci --rederive --all-products` == committed pins, **84/84 stations across the 10 committed pin
   targets** (5 factory lines + 5 product instances) — the unit is a TARGET, not a factory, and the
   count is the sum of the ten `pinned_verdict.json`. ⚠️ **Scope is split by actor and both halves are
   declared, never merged into one number** (INC-11 measurement): the development machine runs all 84;
   the ADR-005 independence layer runs whatever its toolchain permits and **prints what it did not
   run**. Today that is `dummy` 5/5 — 6 % — and calling it "P1 green on another machine" was the
   thing this clause let happen.
2. Every two-sided gate's RED side re-runs and goes red.
3. `meta check` runs 23 gates with zero skips and the N/A branches counted separately.
4. `meta benchmark` — `helpdesk` MEETS, `snipeit` EXCEEDS.
5. `docs_check` green over the existing corpus.
6. A real slot is delegated end-to-end and a bash-mediated write outside the radius is caught.
7. The context meter reports (a) and (b) of the ADR-019 §6 escape rule with real numbers.
8. `total_cost_usd` of the whole acceptance run is recorded in the ledger — the rebuild pays its own
   accounting bill on the first day.

## 7. After cutover — the agenda that this spec unlocked

In priority order, each already argued in §09.4:

1. **A-1** context meter → closes the oldest open clause in the system (ADR-019 §6).
2. **A-2** iteration metrics → the 11.5 % gap; the cheapest genuine contribution available.
3. **A-3** budget as a parameter → turns a red KPI into a runtime constraint.
4. **A-9** memory-risk map → the one named failure mode with no tooth (poisoning).
5. **A-4** generalised negative-knowledge store.
6. **A-8** handoff tooth (pointers/contract).
7. **A-6/A-7** slot rollback and sandbox policy.

## 8. One paragraph for whoever picks this up cold

Port the kernel first and prove it against the committed proofs — that takes an afternoon and it makes
everything afterwards falsifiable. Then build the control plane on the SDK and stop at the tampered-proof
test: if the column does not bite there, the plan is wrong and it is better to know on day three than on
day ninety. Migrate dummy, then iot, then FSK. Do not improve anything until cutover; the temptation to
fix the ten things you will notice on the way is exactly how rebuilds die. Every fix already has a
number in §09.4 and a place in §11.7.
