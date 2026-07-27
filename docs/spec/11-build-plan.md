<!-- meta:doc sha=d551863d58c3c34e53c39ec20855572e642d5e88 updated=2026-07-27T21:41Z -->
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
| **INC-1** | `KERNEL-PORT` | `mf/kernel/*` ported from `seed/verifier.py` + `engine/*` | **hermetic**: recompute `proof_sha` with the NEW code over the 5 factories' **already committed** `.proof/*.json` and compare to `pinned_verdict.json`. No toolchain, no builds, seconds to run | M |
| **INC-2** | `CONTROL-PLANE` | `control/{options,agents,hooks,tools,permissions}` — the 12 hooks as callbacks, the 5 roles as `AgentDefinition`, the verbs as MCP tools | the `column_full` analogue: a **tampered proof** must be refused by the WIRED hooks running under the SDK host; two-sided (untampered ⇒ green) | L |
| **INC-3** | `DELEGATION-V3` | `Slot` dataclass, `SubagentStart` binding, `can_use_tool` + hook double layer, typed verdict, `rewind_files` rollback | `slot_footprint` two-sided (GREEN / RED / FAIL-CLOSED) **plus** one real delegated slot end-to-end whose bash-mediated write is caught | M |
| **INC-4** | `CHECKS-PORT` | the 29 kinds + the 23 gates on the new registry | all 23 run; **all two-sided witnesses re-bite**; the new rule lands: a gate without a red witness cannot register — which forces `generality` to finally get one | L |
| **INC-5** | `MEMORY-DOCS` | docs manifest, seal, INDEX, lineage, STATE teeth, `SessionStore` handoff | `docs_check` green over the EXISTING doc corpus (283 docs, 2,373 citations) — the corpus is the fixture | M |
| **INC-6** | `ECONOMY-TYPED` | ledger and outcome from typed usage; **the context meter** (§10.6); iteration metrics (§09.4 A-2) | two-sided ledger gate + the escape-threshold observer emits real numbers for (a) and (b); the transcript parser is DELETED | M |
| **INC-7** | `MIGRATE-DUMMY` | the fixture factory on v3 | `ci --rederive` == pin (5/5 stations) | S |
| **INC-8** | `MIGRATE-IOT` | a LIVE factory, hermetic Go, no external services | `ci --rederive` == pin (6/6) | S |
| **INC-9** | `MIGRATE-FSK` | the real system: 12 stations, 3 products, live PG + Chromium | `ci --rederive --all-products` == pin (27/27) + `meta benchmark` 2/2 in the expected class | XL |
| **INC-10** | `MIGRATE-FROZEN` | ASF + full-stack — **re-verification only, zero new generation** | `ci --rederive` == pin (11/11, 6/6) | S |
| **INC-11** | `CUTOVER` | v2 substrate deleted; `meta` becomes the thin shell over v3 | all of P1 + P2 green in one clean-clone run on another machine (the ADR-005 independence layer) | M |

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

## 6. Definition of done

v3 is done when **all** of these hold in a single clean-clone run on a machine that is not the
development machine:

1. `ci --rederive --all-products` == committed pins, 5/5 factories (55/55 stations).
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
