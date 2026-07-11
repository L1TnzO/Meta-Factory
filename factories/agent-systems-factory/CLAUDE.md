# Factory agent-systems-factory — residency (the every-turn layer)

> Budget: this file is the ONLY always-resident one (I-6). Rent is paid per line — minimal and
> measurable in the diff. The deterministic lives in the CLI/gates; the historical, in `docs/`. Here,
> only what must influence EVERY turn. The `agent_shadow` gate (M7) measures this budget.

## Start here
1. `docs/STATE.md` — the factory's current state (single entry point).
2. The product line lives in `stations/` (stations as data); the SDD contract, in `factory.spec.yml`.

## Every-turn rules (what the harness already enforces — don't repeat it in prose)
- **The verdict is never written by hand**: `passed` is computed ONLY by `seed/verifier.py` from real
  exit codes (Lock 1). Do not touch `.proof/` — the `proof_protect` hook denies it.
- **Never declare green without proof**: run the gate (`meta station`/`meta product-run`) and read the
  verdict bus (≤N lines), never the test dump.
- **Two verifiers**: local custody is not the root of trust; re-derivation on a clean runner is
  (`seed/external_ci.yml` + the pinned verdict).
- **Delegate by default (not asked per prompt, ADR-017)**: the brain is the `orchestrator` (Opus). A
  **bounded code slot with a gate** (compile·tests·static) is routed via the `generate-slot` skill to the
  `writer` (Sonnet) and accepted/rejected on the VERDICT, not the diff; **bulk reads** (logs, trees, specs)
  go to the `triage` (Haiku). Keep the orchestrator's context SMALL. For a heavy build: `claude --agent
  orchestrator`. Every agent prohibition has a deterministic SHADOW (I-12) — it never rests on prose.
- **Whatever touches the trust chain** (gate/verifier/hooks/`seed/`) is written and read by the orchestrator
  with its own eyes — it is the column, never delegated.
- **Multi-file for maintainability**: new code (codegen and generated artifacts) is split into cohesive
  files, not a monolith; do not add NEW files of thousands of lines (if one trends to ~800+, split it).
  Existing monoliths are known debt — do not rewrite unless asked.
- **Model-native generation (ADR-023/024)**: template codegen is FROZEN-with-pin — do NOT feed it
  (touching `codegen/` requires a written waiver in the work-doc, ADR-023 §3); new surfaces/axes are born as
  gated slots (`generate-slot`) with COMMUNITY pieces fixed as DATA in the spec (ADR-023 §2); an adopted
  human surface is a PINNED override (`products/<p>/frontend/`, `frontend_surface: model-native`) that is
  re-VERIFIED (`design_floor`), not re-derived.

## Placement (where each piece goes)
CLI if it must be guaranteed · hook if it must be prevented even when the model misbehaves · here if it
influences every turn · skill if on-demand · agent if it is a role · `docs/` if it is history (zero residency).
