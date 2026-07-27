<!-- meta:doc sha=e978400256d6f13ce875fe442230537487d32742 updated=2026-07-27T21:41Z -->
# 02 — Invariants (NORMATIVE)

> This is the part of the system that must survive any rebuild. Everything else — the CLI shape, the
> hook mechanism, the file layout, the language — is implementation and may be replaced freely.
> Source of the numbered list: `docs/reference/ARCHITECTURE.md:66-75` (I-1..I-10), refined by
> `docs/reference/PRIMITIVES.md:40-45` (SAFE-N) and the ADR corpus `docs/decisions/001..030`.

## 1. The ten invariants, restated for a re-implementer

| # | Invariant | Restated as an acceptance criterion for v3 |
| --- | --- | --- |
| **I-1** | Anti-rubber-stamp column (3 locks) | `passed` is computed ONLY by a deterministic verifier from real OS exit codes; the model can neither write nor edit a verdict; a turn cannot close with an unproven station. A rebuild that lets any model text become `passed` has failed, no matter how good it looks. |
| **I-2** | Stations as data | The line is YAML, not branches. **Zero** hardcoded domain identity in the engine. Verified today by grep over `engine/`, `spec/`, `codegen/`: zero matches for kotlin/gradle/django/react/postgres/product names. |
| **I-3** | Determinism frontier | The model does the creative part inside bounded slots; determinism lives in the PROCESS, the VERIFICATION and the CONTRACTS — never in the generated content. Do not try to make the model deterministic; make the acceptance deterministic. |
| **I-4** | A/B/C automation ladder | automatic · draft+consent · provisional-with-honesty. Never "block or fabricate". |
| **I-5** | Generated/domain boundary — **AMENDED by ADR-011**: 100% is generated; there is no hand-written `domain/` to protect. Only regenerable, idempotent scaffolding survives as a primitive. |
| **I-6** | Placement law | Each piece lives in the most deterministic substrate that can hold it; the model is the LAST resort. Verdicts go to context; logs go to disk. |
| **I-7** | Verdict bus | Every expensive operation emits a verdict of ≤N lines plus a pointer. Progressive disclosure, never log-dumping into the reasoning context. Enforced by the `bus_bounded` kind (default N=10). |
| **I-8** | Memory as a repo artifact | Deterministic hooks write the journal from git + ledger, with zero model narrative. Cloning the repo clones the memory. |
| **I-9** | Narrative memory schema | Doc TYPE determines mutation semantics: STATE overwrite · LOG append · `decisions/` immutable · `work/` per-increment · `reference/` stable. |
| **I-10** | RTM + evidence tree | Requirements have stable ids and `satisfied_by`; commits carry station/spec-ref/proof-sha trailers; the requirement↔station↔artifact matrix is RE-DERIVED from artifacts, never narrated. |

## 2. The three locks of I-1 (the heart of the system)

These are the mechanisms that make "green" mean something. A rebuild must reproduce all three or it
has not reproduced the system.

| Lock | Statement | Today's anchor |
| --- | --- | --- |
| **Lock #1** | `passed` derives from real exit codes and from nothing else. Empty check list ⇒ `False` (no vacuous pass). A check that cannot even launch is recorded as exit **127** — fail-safe, not fail-open. | `seed/verifier.py:56-59, 112-119` |
| **Lock #2** | The gate RECOMPUTES `passed` and `proof_sha` from the proof's own `checks` array before opening, and rejects on mismatch — a hand-pasted `passed: true` is caught. | `seed/verifier.py:171-185`, called by `engine/gate.py:28-32` |
| **Lock #3** | The turn cannot close with a non-green active station; the commit cannot happen with a non-green active station. Enforced by wired hooks, and the wiring itself is gated (`column_full` proves the HOOKS block, not just that the library could). | `.claude/hooks/stop_proof.py:42-57`, `commit_guard.py:29-41`, `verify/checks/column_full.py:1-9` |

## 3. Re-derivation over custody (ADR-005) — the strongest idea in the system

Two verifiers exist from the birth of every factory:

1. **Factory CI** — "does the machine still know how to build?" (suite + one dummy; constant cost).
2. **Product CI** — "is this graduated product still healthy?"

Both are **re-derivation, not audit of custody**: rebuild from a clean clone, gates fresh, compare
against the pinned honest verdict; **deviation in ANY direction is red** (`decisions/005:22-25`). The
independence hierarchy is explicit: hooks (same actor) < pre-push (another hour) < remote CI (another
machine and actor — "the only layer untouchable by model, hooks, or the local engineer").

The mechanism that makes this decidable is `proof_sha` **excluding** timestamps, stdout and machine
specifics. Because of that exclusion, two independent runners that reach the same outcome produce the
same hash, and `ci --rederive == pin` is a genuine equivalence test rather than a smoke test.

> **v3 requirement:** keep `proof_sha` byte-compatible with v2 where the check set is unchanged. This
> is what allows the current `pinned_verdict.json` files to serve as the rebuild's acceptance oracle
> (§11.4). If the hash definition changes, the oracle is lost and the rebuild becomes unfalsifiable.

## 4. Anti-decorative rule: a gate must be able to go RED

A gate that cannot fail proves nothing. The house style is a **two-sided tooth**: the gate ships with a
synthetic GREEN witness and a synthetic RED witness, and several gates literally print `GATE
DECORATIVO` and exit 1 if the red side fails to bite (`role_hygiene.py:70`, `rtm_tree.py:109-110`,
`state_fidelity.py:151`, `state_snapshot.py:137`).

Measured status today: **14 of 23** `meta check` gates carry an explicit two-sided witness; `compile`,
`isolation`, `suite` are inherently one-sided (they are test runners); `generality_parity` has **no
red-side witness found** — recorded as debt in §09.

**v3 rule (tightened):** a new gate is not accepted into the registry without a red-side witness, and
the absence of one is itself a gate.

## 5. Closed vocabularies (govern by data, not by convention)

Whenever the system had a category that could grow arbitrarily, it froze it into a constant and put a
gate on it. This is the pattern that kept the system from sprawling and it must be preserved.

| Vocabulary | Single source | Gate | Size today |
| --- | --- | --- | --- |
| check kinds | `verify/checks/registry.py:21-28` | `kinds` (`kind_hygiene`) | 29 |
| agent roles | `agent_roles.py:25-42` | `roles` (`role_hygiene`) | 5 canonical + 2 legacy |
| work-doc types | ADR-029 | `lineage` | `direction` \| `increment` |
| slot enums (`trust_level`, `cost_class`, `side_effects`, `model_policy` keys) | `seed/delegation.py:60-63` | manifest validation, pre-spawn | 3/3/3/3 |
| column roles per level | `column_scope.py:23-65` | `least_priv` | 11 meta ⊋ 6 factory |
| doc mutation semantics | I-9 | `docs_check` | 5 types |

**Adding an entry to any of these is a deliberate governance act: edit the constant + write an ADR.**
That is the rule that has prevented the vocabulary explosion typical of agent frameworks.

## 6. Least privilege as a projection, not a copy (ADR-018)

The factory column is a **strict subset** of the meta column, derived from ONE source
(`column_scope.py`), and the subset relation is gated (`least_priv`): a factory that gains a
meta-only capability is red, and a factory missing a required one is also red. Today:

```
META_COLUMN   = ENFORCEMENT{proof_protect, increment_guard, commit_guard, stop_proof, gate_guard}
              ∪ DELEGATION{blast_radius, verdict_required}
              ∪ MEMORY{doc_stamp, mem_capture, mem_rollup, session_start, pre_compact}       # 11
FACTORY_COLUMN = {proof_protect, increment_guard, commit_guard, stop_proof} ∪ DELEGATION      # 6
```

The exclusions are justified per role (`column_scope.py:69-76`): station sequencing is meta-operated,
and the memory subsystem does not descend.

> **v3 keeps the invariant and changes the mechanism.** Today the subset is realised by COPYING files
> into each factory and gating the copies (`column_parity`, `column_full`, `column_selftest`,
> `least_priv`). In v3 the subset is a dict comprehension over one in-process registry, and
> `least_priv` becomes a set assertion — see §09.2 and §10.5.

## 7. Delegation law (ADR-017/020) — verify, do not review

| Rule | Mechanism today |
| --- | --- |
| A slot is a CONTRACT written before delegating | `.gen/active_slot.json`, required keys `slot_id · allow_globs · verdict_path · iteration_gate_cmd · acceptance_gate_cmd` (`seed/delegation.py:42`) |
| The generator cannot write outside its blast radius | `blast_radius.py` PreToolUse deny, per-agent, fail-CLOSED |
| The generator cannot finish without a verdict | `verdict_required.py` at SubagentStop, fail-CLOSED |
| The generator cannot finish with a change footprint outside the slot | git-observed footprint ⊆ `allow_globs ∪ {verdict_path} ∪ .gen/** ∪ baseline_dirty` (`delegation.py:188-213`) |
| The orchestrator accepts on the VERDICT, not the diff | `verdict_ok()` (`delegation.py:250-281`): required keys, valid status, `acceptance_exit_code == 0` when green, size budget respected |
| The COLUMN is never delegated | doctrine (`SELF-IMPROVEMENT §3`); it is written and reviewed with human/orchestrator eyes |

**Honest calibration, kept verbatim from ADR-017:** gates do NOT catch semantic no-ops, most security
bugs, hallucinated packages, or ambiguous specs. The gate is trusted for the BULK; expensive eyes are
spent only on the irreducible residue. Any rebuild that presents delegation as "safe because gated"
without this caveat is misrepresenting the system.

## 8. What is explicitly NOT an invariant

Recording this matters as much as the list above, because it is what the rebuild is free to discard:

- The `meta` CLI verb surface and its stdout format.
- Hooks being separate OS processes wired through `.claude/settings.json`.
- Agents being Markdown files with YAML frontmatter.
- The physical copy of the harness into each factory (`_emit_harness`).
- Metrics being obtained by parsing a transcript file.
- The deterministic template codegen (`codegen/scaffold/`) — **frozen** by ADR-023 and explicitly not
  carried forward (§09.3, §11.6).
- Spanish/English duality in doc headers.
