---
name: design-primitives
description: >-
  Design-time procedure for the Meta-Factory: given a NEW factory's domain, map the design
  primitives (DES-*) it requires, choose the technology that provides each, and declare them in the
  factory-spec. Use when designing/planning a new factory or filling a spec-stub's tech choices.
  Materializes reference/PRIMITIVES.md §3. The technology is a PLAN choice (ADR-012) — never hardcoded
  in v3/. Output is verified by `spec.cli design-review` — the M0 design gate (B2): a tech
  per required primitive (plan) AND a verifier per requirement (criterios). M0 refuses an incomplete design.
---

# Skill · Design primitives (map domain → primitives → technology)

> You are the designer of a new factory. Your job is NOT to generate code: it is to produce the **design**
> (a `factory.spec.yml` v2) that the build (M0–M8) will consume. The technology is chosen by **you, here,
> by judgment** under the philosophy — and you **declare it in the spec as DATA**. The substrate
> (`v3/`) knows no technology (ADR-012); if you feel like "adding a backend", that is a
> philosophy bug.

## When you use me
- A new domain arrives (web, mobile, IoT, data-pipeline, whatever) and its factory must be designed.
- There is a spec-stub with `domain.produces` + (optional) `domain.required_primitives` and the techs are missing.

## The catalog (single source)
The DESIGN primitives live as DATA in `docs/reference/primitives.yml` (human mirror:
`PRIMITIVES.md §3`). They are CONCEPTS (what a tool solves), not tools. Today: DES-1..DES-13
(regenerable scaffolding · verifiable topology · unskippable control points · durable state ·
provenance · typed contracts · gated evaluability · proof in the product's toolchain ·
isolation boundary · static analysis with teeth · API currency/freshness · versioned schema
+ checked queries · product supply-chain/security). DES-10..13 were uncovered by the
full-stack-kotlin domain (hard criteria). **Read the YAML before mapping** — it is the living
quarry and may grow.

## Procedure (4 steps)
1. **Understand the domain.** Read `domain.produces` and what the factory must guarantee. Ask: which
   product invariants must be VERIFIABLE? Every verifiable invariant points at a primitive.
2. **Map required primitives.** For each invariant, pick the DES primitive that captures it. Record them
   in `domain.required_primitives: [DES-x, …]`. Rule: a primitive enters only if the domain NEEDS it
   (honesty, SAFE-7) — do not inflate the list. If an invariant fits no DES, it is a **new
   primitive**: add it to `primitives.yml` + to `PRIMITIVES.md §3` (the quarry grows), not to the substrate.
3. **Choose the technology per primitive (JUDGMENT).** For each required primitive, pick the tech that
   provides it in THIS domain (agent domain → DES-3 via `interrupt()`; web → DES-3 via auth middleware;
   IoT → DES-3 via secure-boot). Declare it in a `capability` with `{primitive, tech, invariant, proof,
   status}`. The choice is reviewable (it stays in the spec), not deterministic. Treat the catalog's
   `example_techs` as a trigger, not a closed list.
   **MANDATORY question before building ANYTHING bespoke (ADR-023 §2):** which piece has the COMMUNITY
   already validated with thousands of engineer-hours (framework, design-system, library)? If it exists, the
   spec FIXES it as DATA (`tech:`) and the model-native slots CONSUME it; re-doing deterministically what
   should have been model-foundational + other-engineers' pieces is the anti-pattern ADR-023 buries (the
   pseudo-framework). The answer is WRITTEN into the capability (`tech` + `invariant`), not kept in your head.
4. **Close the design with stations + requirements.** Turn the capabilities into a `station_sequence`
   line (with `depends_on` and `proof_checks` declaring `runs_in: product_env` + `toolchain`), and tie the
   requirements with `satisfied_by` (stations) and `verified_by` (real proof_checks).

## Verify your own output (the teeth — now in M0)
```
python3 -m v3.spec.cli validate       <spec>   # well-formed v2 grammar (A1)
python3 -m v3.spec.cli design-review   <spec>   # COMPLETE blueprint: plan + criteria (B2)
```
- `design-review` is **the M0 gate** (B2): it runs inside meta-station m00. It is the SDD design
  flow with teeth, in two phases:
  - **plan** — every `required_primitive` has a capability with a tech, and every referenced
    `primitive` exists in the catalog (this was `design-coverage`, B1; still available as a sub-check).
  - **criteria** — **every requirement cites a `verified_by`** (a real proof_check). A requirement without
    a verifier is an UNfinished design (the SDD verification-criteria phase).
- It only activates if the spec declares `domain.required_primitives` (you assert "I ran the design flow"):
  there M0 demands TOTAL completeness. A stub without primitives is not a blueprint — but it doesn't build either.
- Exit 0 ⇒ blueprint ready for the build. Exit 1 ⇒ the design is NOT ready (`plan:` a tech is missing ·
  `criterios:` a requirement without a verifier). If `validate` or `design-review` go red, do not narrate
  "it is complete": prove it. M0 refuses it anyway.

## The hard rules (non-negotiable)
- **Tech in the spec, NEVER in the substrate** (ADR-012). `v3/` neither imports nor names technology.
- **Status honesty** (SAFE-7): `planned` while it is design; `declared-deferred` if specified
  but its codegen is deferred; `built` ONLY with `proof`. Do not mark `built` what you did not build.
- **Security is not designed**: the SAFE-* primitives (the column) are inherited by every factory; you only
  design the DESIGN primitives (DES-*).
