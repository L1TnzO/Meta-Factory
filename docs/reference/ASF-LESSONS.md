<!-- meta:doc sha=89c1a701e9e3ccc716e0a5e9779f36a3dddb1f42 updated=2026-08-03T23:45Z -->
# ASF lessons — the good to keep, the bad to fix

| Field | Value |
| --- | --- |
| Document | Extraction of learnings from Agent_Systems_Factory (ASF) |
| Method | Full read of the ASF tree: ARCHITECTURE, AUDIT, HONEST-STATE, V2, STATE, LOG, the 23 ADRs, the CONTEXT increment, hooks, agents, commands |
| Reading date | 2026-06-13T02:17Z |
| Purpose | Everything good ascends to the Meta-Factory's substrate (`ARCHITECTURE.md §3`); everything bad becomes a gap closed by design |

> Citations use a path relative to `../../Agent_Systems_Factory/`. ASF is a VERY well thought-out
> system; this doc doesn't diminish it — it harvests it. Its greatest virtue is its honesty
> (AUDIT/HONEST-STATE), which is exactly what makes this extraction possible.

---

## 1. The good (ascends to the Meta-Factory's substrate)

| ASF pattern | Where it lives in ASF | How the Meta-Factory inherits it |
| --- | --- | --- |
| **The anti-rubber-stamp column** (3 locks): a verdict the model can't write, recomputed hash, Stop re-runs verify | ASF/ADR-006, `.claude/hooks/{proof_protect,gate_guard,stop_station_proof}.py`, `settings.json` permissions.deny | I-1, M1 — the first meta-station installs the column in every new factory |
| **Stations as data**, not code branches; zero hardcoded project identity | ARCHITECTURE §9.1, anti-pattern #4 | I-2, M2 |
| **Determinism boundary** clear and honest: model for bounded slots, code for invariants; determinism in process/verification/contracts | §6, PF-1/PF-2, ASF/ADR-009 | I-3, PF-1/PF-2 |
| **A/B/C automation ladder** (automatic / consent / honest-provisional) — avoids the "block or fabricate" binary | §7, ADR-010 | I-4 |
| **Generated/domain boundary**: Copier owns `generated/`, the engineer owns `domain/`, connected by inheritance; an update never overwrites human code | §11.5, ADR-014, `template/` `_skip_if_exists` | I-5, M4 |
| **Placement law / context economy**: every piece in the most deterministic substrate; verdicts to context, logs to disk | ADR-020, `ASF/docs/work/CONTEXT-INCREMENT.md`, `factory check` | I-6, I-7, `CONTEXT-ECONOMY.md` |
| **Memory as a repo artifact** + narrative schema (doc types = mutation semantics) | ADR-019, ADR-021, `.claude/hooks/session_journal.py`, `docs/{STATE,LOG,decisions,work,reference}` | I-8, I-9, M5 — and this repo's own schema |
| **RTM + evidence tree**: requirements with an id + `satisfied_by`; commits with trailers; matrix re-derived from artifacts | ADR-017/018, HONEST-STATE §"Trazabilidad de requisitos", `factory rtm`/`factory trace` | I-10, M5 |
| **Two-verifier doctrine**: re-derivation over custody in external CI | ADR-022, `.githooks/pre-push`, `.github/workflows/factory-ci.yml` | I-11, M6 |
| **Deterministic shadow of the meta layer**: every narrative rule that shouldn't be skipped has a deterministic detector; judgment is never hard-blocked | ADR-023, `engine/narrative.py`, delegation counter | I-12, PF-11 |
| **Honesty about limits** as a first-class artifact | HONEST-STATE.md, AUDIT.md, PF-8 | I-13, this very doc |
| **Generate→verify→promote loop** (the expensive half —verification— is the durable asset) | V2.md, V2.3, `pattern_request.json`, `/factory-promote` | base for the self-improvement loop (`SELF-IMPROVEMENT.md`) |
| **Factory/product isolation** verified by test | PF-6, `test_factory_does_not_import_products` | PF-6, `test_metafactory_does_not_import_factories` |
| **Subagent contracts as an API** (fixed report format = the only thing that enters the orchestrator) | `ASF/.claude/agents/factory-writer.md`, CONTEXT D2 | `CONTEXT-ECONOMY.md §delegation` |
| **Governed-increment discipline** (`/incremento`: open/checkpoint/close; the doc IS the state) | `ASF/.claude/commands/incremento.md`, the 4 docs in `docs/work/` | inherited as-is; see `docs/work/BOOTSTRAP-INCREMENT.md` |

**ASF's most valuable meta-lesson** (AUDIT, closing): *"render+ast en verde NO prueba un
producto que funcione. SEIS bugs invisibles a ese nivel aparecieron al scaffoldear+compilar de
verdad."* → in the Meta-Factory this is **M8, unskippable** (`ARCHITECTURE.md §6`).

---

## 2. The bad (gaps the Meta-Factory closes by design)

Ordered by severity. Each gap cites the evidence in ASF and names the Meta-Factory mechanism that
closes it.

### G-1 · ASF manufactured itself (the root gap)
- **Evidence**: ASF lives in its own folder, subject to its own harness. ADR-023 confesses:
  *"la fábrica aplicó ADR-020 a fabricar productos, pero nunca a sí misma."* The meta layer ended
  up as prose that gets skipped under pressure (STATE stayed stale for a whole session; the
  "birth certificate" never wrote anything; ~1 real delegation in the repo's entire history).
- **Root cause**: a category error — ASF doesn't belong to its own product class (LangGraph
  agents), so it had to pretend to be its own product (`VISION.md §2`).
- **Closure**: PF-9 + ADR-006 — the Meta-Factory IS the legitimate fixed point; ASF is regenerated
  as a product, governed by a layer more trustworthy than itself.

### G-2 · Over-coupling to ONE class of system
- **Evidence**: HONEST-STATE §"Acoplamiento de opiniones": *"la fábrica es opinionada al stack
  del RE Agent (Neo4j/W3C PROV, escalera de atribución, interrupt análisis→decisión, RAGAS).
  Es una fábrica para una CLASE, no universal. Generalizar = parametrizar esas opiniones."*
- **Closure**: factory-spec Half A (`ARCHITECTURE.md §5`) — ASF's opinions become domain
  parameters. The Meta-Factory doesn't inherit them; it receives them as spec.

### G-3 · Sub-delegation: the expensive orchestrator rarely routes to the cheap one
- **Evidence**: the engineer observed it directly ("Opus 4.8 MUY rara vez deriva a Sonnet
  4.6"). ASF measured it (ADR-023, delegation counter) but *"la serie está vacía"*; *"5
  agentes definidos, ~1 delegación real en toda la historia del repo."* ASF chose to **measure
  before forcing** (correct), but the ergonomic default kept favoring keeping everything in the
  orchestrator.
- **Closure**: `CONTEXT-ECONOMY.md` — delegation as an **ergonomic default** (not discipline):
  a ~0-line delegation contract (lives in the agent), a verdict bus that makes NOT delegating the
  expensive choice, and model routing as data.

### G-4 · Model routing had no deterministic shadow (residual W4)
- **Evidence**: STATE §"Agujeros honestos" and CONTEXT §review de cierre: *"'reviewer en opus para
  trust-chain' es regla narrativa sin sombra determinista — el mecanismo de agents no soporta
  selección condicional de modelo."* It remained W4 ACCEPTED RESIDUAL.
- **Closure**: the Meta-Factory moves the model decision to the **orchestrator, guided by data**:
  a command/skill reads the diff's classification (trust-chain / bulk / log) and picks
  subagent+model according to a versioned routing table. The orchestrator makes the conditional
  selection with `Agent(..., model=...)`, not the agent-definition mechanism. Closes W4.

### G-5 · Missing a formal SDD spine
- **Evidence**: the engineer pointed it out ("podría faltar SDD o similares"). ASF has S0 +
  spec.yml + RTM —which is *almost* SDD— but it isn't framed as a disciplined SDD cycle
  (spec→plan→tasks→verification) nor as the explicit single source of truth.
- **Closure**: ADR-003 — first-class SDD spine, **enforced deterministically** (M0 refuses
  incomplete specs; RTM blocks on UNSATISFIED). Stronger than state-of-the-art prompt-based SDD
  tools, because non-compliance cuts a gate.

### G-6 · The façade-trap: stubbed plumbing + verification against the render
- **Evidence**: AUDIT §"el problema de fondo: los dos errores se COMPONEN" — templates with TODOs
  at the hardest points (S1/S4 façades) + proof_checks pointing at nonexistent tests +
  verifier running from the wrong venv = *"el sello de goma reencarnado a nivel de
  plantilla."* Six bugs appeared only when actually scaffolding+compiling for real.
- **Closure**: unskippable M8 (real e2e: scaffold+compile+run in the product's venv). And the
  generalized rule: **a factory is verified by building, not by rendering.**

### G-7 · The verifier's custody residual (partially closed in ASF)
- **Evidence**: HONEST-STATE §"Lock 2 endurecido": *"`gates.ledger.json` y los registros de
  predecesores siguen siendo artefactos en disco protegidos por hooks + deny-list + SHA — no se
  re-derivan desde un proceso verificador; esa protección depende de que la cadena de hooks esté
  activa."* ASF mitigated it with ADR-022 (external CI) but added it **late** in its life.
- **Closure**: I-11/M6 — the two-verifier doctrine is baked in **from the birth** of every
  factory, not as a retrofit. The external CI re-derives; local custody stops being the root of
  trust.

### G-8 · The cascade pattern: proven on few spec shapes
- **Evidence**: STATE and HONEST-STATE repeatedly: *"Probada en 3 formas de spec; formas nuevas
  casi seguro destapan cascada (patrón visto 2×)."*
- **Closure**: the generate→verify→promote loop (inherited) + a corpus of factory
  **scenario-specs** (from the state of the art: meta-harness/autocontext) that exercise diverse
  shapes before promoting. See `SELF-IMPROVEMENT.md §loop`.

### G-9 · Fragile environment bootstrapping / previously retired ecosystems
- **Evidence**: ASF/ADR-004 SUPERSEDED (agentmemory discarded after verifying npm+daemon+53
  tools); gentleai/engram retired (2026-06-10, with backup); the `PROJECTS_ROOT` bug pointing
  outside the repo (AUDIT §bug confirmado) that survived *"porque ningún test ejercita factory
  new → station de punta a punta."*
- **Closure**: M8 (e2e from the first increment, not as a late Phase 4) + minimal dependencies
  declared in the seed; zero external daemons (memory as a repo artifact, I-8).

---

## 3. Synthesis: the Meta-Factory's formula

> **Meta-Factory = (all the deterministic substrate ASF discovered, ascended to template) +
> (ASF's opinions, descended to factory-spec) + (the 9 gaps in §2, closed by design) +
> (the fixed point that makes self-improvement legitimate).**

ASF cost us a lot of iteration because it discovered the substrate the hard way (5 remediation
phases, 2 cascade patterns, 6 façade bugs). The Meta-Factory exists so **that doesn't repeat**:
the substrate is already harvested and verified, so the next factory is born with everything
wired in — the one-shot the engineer asked for.
