<!-- meta:doc sha=c9228ad0393c94d08634ddd35374e91030f2f184 updated=2026-07-11T15:38Z -->
# PRIMITIVES — the philosophy: design primitives, not tools

> type: reference (stable) · created: 2026-06-15T03:43Z
> Self-contained. If you arrive without context: this doc is the PHILOSOPHY of the Meta-Factory. The
> Meta-Factory does NOT know how to use Copier, or LangGraph, or Next.js. It knows the CONCEPTS that
> those tools solve — the *primitives* — and at DESIGN time (Claude Code) it plans which technology
> provides each primitive for the domain at hand. The tool is decided in the SDD plan or declared in
> the spec; **it is never hardcoded into the substrate** (it is a tool, not philosophy). Decisions
> that fix this: `ADR-011`, `ADR-012`.

## 0. The sentence that orders this

> La Meta-Factory es la más generalista de todas: describe cómo debe ser una Factory "perfecta" y se
> replica bajo dominios variados (ASF, Full-Stack, Mobile, IoT…). No es Copier ni lo que envuelve a ASF:
> es el **concepto** de **construir productos de manera segura**. No le enseñás a usar Copier; le enseñás
> la primitiva, y ella decide "ok, necesito esta tecnología". (Mandato del ingeniero, 2026-06-15.)

## 1. The frontier of determinism (I-3, the mother rule)

Determinism lives in **process + verification + contracts**, **NEVER in the generated content**.
From this come TWO families of primitives with different owners:

| Family | Who owns it | Deterministic? | Chosen per domain? |
| --- | --- | --- | --- |
| **SECURITY primitives** (§2) | the Meta-Factory, invariant | **Yes** — code, gates, re-derivation | **No** — they are the philosophy, identical for every factory |
| **DESIGN primitives** (§3) | declared in the spec / chosen in the SDD plan | **No** — the model generates the content | **Yes** — the technology that provides them is decided by planning |

Operative corollary: Claude Code **generates 100%** (ADR-011); determinism does not tie its hands
while generating — it verifies its hands afterward. "Wrap Claude Code in guarantees, don't replace
it" (VISION §6).

## 2. SECURITY primitives (the substrate BAKES them; invariant across every domain)

These are NOT chosen or negotiated: every factory inherits them. They are the 13 invariants seen as
primitives.

| id | Primitive | What it guarantees | Invariant |
| --- | --- | --- | --- |
| **SAFE-1** | Verdict only by proof | `passed` is computed ONLY by a deterministic verifier from real exit codes; the model cannot write verdicts | I-1 (column, 3 locks) |
| **SAFE-2** | Verify by building, not rendering | a factory/product is tested by scaffolding+compiling+running on its OWN toolchain; a green render is not enough | M8 (façade-trap) |
| **SAFE-3** | Re-derivation over custody | trust = a clean runner re-derives the identical honest verdict; replicable > archived | I-11 / PF-10 (two verifiers) |
| **SAFE-4** | Requirements by artifact, not by narrative | RTM re-derived from `.proof/`: SATISFIED/PROVISIONAL/UNSATISFIED cuts the CI | I-10 |
| **SAFE-5** | Bounded creative slots | the model only writes in slots whose output is verified; what's invariant is the contract, not the content | I-3 |
| **SAFE-6** | Universal deterministic shadow | every rule that must not be skippable has a detector/blocker in a hook/CLI; the narrative declares, the code guarantees | I-12 / PF-11 |
| **SAFE-7** | Honesty of limits | aspiration is never confused with reality; M0/S0 refuse rather than fabricate defaults; honest `status` | I-13 |
| **SAFE-8** | Trust hierarchy | each layer is verified by one at least as trustworthy; the seed is the hand-audited root; self-modification of the chain = the strongest gate | SELF-IMPROVEMENT |

## 3. DESIGN primitives (CONCEPT; the technology is chosen by the SDD plan / the spec)

Each row is **what a tool SOLVES**, abstracted from the tool. The "technology examples" column is
illustrative — the plan chooses per domain; the substrate doesn't know it.

| id | Primitive (the concept) | What it solves | Technology examples (NOT hardcoded) |
| --- | --- | --- | --- |
| **DES-1** | Regenerable scaffolding | the product is derivable from spec+design; regenerating is idempotent. With 100%-generated (ADR-011) **there is no human code to protect**: the source is the spec, the code is derivable | Copier (Py) · Plop/Hygen (TS) · templates · Claude Code itself |
| **DES-2** | Verifiable topology | the product's structure is statically checkable against an invariant (without running the model) | compiled LangGraph graph (`get_graph()`) · route AST · IaC schema |
| **DES-3** | Non-skippable checkpoints | certain routes cannot be avoided; verified by reachability over the compiled structure | LangGraph's `interrupt()` · auth middleware · guards |
| **DES-4** | Durable / resumable state | a failure does not re-execute what's already done | PostgresSaver · event store · checkpointed queue |
| **DES-5** | Provenance / traceability | every output traces back to its evidence; join key per node | OTel + Neo4j W3C PROV · structured logs · audit trail |
| **DES-6** | Typed contracts at boundaries | typed, checked interfaces (`consumes`/`produces`) | Pydantic · TypeScript types · OpenAPI · protobuf |
| **DES-7** | Evaluability with gates | quality measured by gates that BLOCK (threshold → red CI) | RAGAS/DeepEval · contract tests · lighthouse CI |
| **DES-8** | Proof in the product's OWN toolchain | verification runs in the product's environment, not the factory's | pytest/mypy (Py) · tsc/vitest/eslint (TS) · detox (mobile) |
| **DES-9** | Isolation boundary | the product does not contaminate the factory, nor vice versa | venv/sys.path · workspace · container |
| **DES-10** | Static analysis with teeth | code fails HARD for quality, not just types (no `any`/warnings, exhaustiveness, complexity, unswallowed errors): rigor made into a gate | detekt+ktlint+`-Werror` · ESLint strict+`no-explicit-any` · `clippy -D warnings` |
| **DES-11** | API currency / freshness | generated code uses ONLY non-deprecated, pinned API surface; the old is blocked DETERMINISTICALLY (I-3) | version-pinned symbol allow-list (via Context7/MCP) · deprecation linters |
| **DES-12** | Versioned schema + checked queries | data is a contract verifiable at compile time: versioned/reversible migrations + a query to a non-existent column = a compile error (the DB screams) | Flyway+jOOQ · sqlx · sqlc · type-providers |
| **DES-13** | Supply chain / product security | the product does not ship known vulns, secrets, or insecure code (≠ SAFE-*, which protects the trust of the FACTORY) | dep-check/`npm audit` · Semgrep/CodeQL · gitleaks · SBOM |

> This table IS the content of the **design skill** (§4). It grows: when a new domain (Mobile, IoT)
> uncovers a primitive not yet listed, it gets added here — it's the living quarry. Each primitive
> names the CONCEPT and leaves the technology open.
>
> **Machine-readable mirror (B1)**: the catalog lives as DATA in `reference/primitives.yml` (single
> source that the skill and the `design_coverage` check consume); this table is the human mirror. A
> test ties both together (`tests/test_design.py`): adding a primitive = editing the YAML + this
> table, never the validator.

## 4. Where the primitives live: the design skill (DESIGN time)

DESIGN primitives are invoked **at the moment the factory is designed**, not at runtime. They live
in a **skill** of Claude Code (the native primitive for on-demand procedure; ARCHITECTURE §8,
ASF/ADR-001). The flow (detailed in `ROADMAP.md §Operation`):

1. **Initial spec** → which factory, which domain, what it must produce, requirements (SDD, single
   source of truth).
2. **SDD planning** (the skill + Claude Code's planning power): for each design primitive that the
   domain requires, the model **chooses the technology** that provides it and **declares it in the
   design/spec** (e.g.: agent domain → DES-2/3 via LangGraph; web domain → DES-2 via router + DES-6
   via TS types). The choice is JUDGMENT (non-deterministic) under the philosophy; it stays as a
   reviewable artifact.
3. **Deterministic build** (M0–M8): the model generates 100%; the column verifies; M8 builds for
   real.

The hard rule (ADR-012): **no technology is hardcoded into `src/metafactory/`**. If `import copier`
or `langgraph` appears in the substrate, it's a philosophy bug: that decision belongs to the plan or
the spec.

## 5. The SOTA formal SDD being adopted

State of the art (~2026): **GitHub Spec Kit · Kiro (AWS) · Tessl** formalize the cycle
`spec → plan → tasks → verification` with a single source of truth, **but enforce it with prompts**
(ADR-003). The Meta-Factory adopts **that same cycle WITH TEETH**: M0 refuses incomplete specs (cuts
a gate), the re-derived RTM cuts the CI on UNSATISFIED. We are not inventing an SDD: we take the SOTA
and make it deterministic. That's the precedent these specs set.

## 6. How to read this alongside the rest

- SECURITY (§2) is fixed → `ARCHITECTURE.md §3` (the 13 invariants), `SELF-IMPROVEMENT.md`.
- DESIGN (§3) is open → this doc is the quarry; `ROADMAP.md` lists the increments that build it.
- The irreversible DECISIONS → `ADR-011` (100% generated, kills I-5), `ADR-012` (primitives not
  tools).
