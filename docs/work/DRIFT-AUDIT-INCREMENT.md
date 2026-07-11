<!-- meta:doc sha=716ff779d99b9d974e15746b1ea9036ac551900b updated=2026-07-11T20:58Z -->
# Incremento DRIFT-AUDIT

> **Doc de gobierno.** Status: **CLOSED** (2026-07-11T20:58Z) (creado 2026-07-11T20:45Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Close the ADR-026 F3 drift audit, WIDENED per SOTA-PARITY §5 row 4: one S1 pass over the graph's liveness
output + `meta outcome`/`meta benchmark` vs the ADR-021/VISION targets with the verdict landed in
`reference/HONEST-STATE.md §7bis` (F3 proper), + the assumption ledger as COST-DOWN §2.7 (SOTA-PARITY
INC-5), + the CLAUDE.md prefix trim with inline vigency tags (SOTA-PARITY INC-6). Docs + prefix only —
zero substrate code.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | F3 audit from graph output (no hand-grep): `meta doc orphans` (100 candidates) + `evidence_liveness` (GREEN 283/2,373/106, red witness alive) + `meta outcome`/`metrics`/`benchmark`; verdict → `HONEST-STATE.md §7bis` | ✅ |
| 2 | INC-5 `ASSUMPTION-LEDGER` → `COST-DOWN §2.7` (single source for re-measure triggers; 15×-folklore row replaced by the INC-2 measured REJECT; token_budget row marked FIRED/recalibrated ≈40k spawn floor; 2026-09-01 pricing cliff = first live calendar trigger) | ✅ |
| 3 | INC-6 `PREFIX-TRIM`: CLAUDE.md ONE editing stretch (prefix-hygiene rule (e)) — historical «State» ¶s → pointer (placement law), roles ¶ compressed to `agent_roles.py` single-source, waiver format → `codegen_freeze` docstring pointer, + INC-5 inline tags. **Measured: 114→108 ln · 10,449→10,028 B (−4%) tags included.** INC-6(b) orchestrator repomap-first line: already live (batched into INC-1's column stretch as designed) | ✅ |
| 4 | STATE «Ahora» + LOG episode; `meta check` green; close | ✅ |

## Evidencia (re-derivable, commands not prose)
- **`evidence_liveness` GREEN**: 283 docs · 2,373 citations · 106 evidence refs resolve; red-side witness
  (`tests/fixtures/docs/dangling_reference.md`) alive. Zero path rot in living docs.
- **`meta doc orphans` = 100 candidates** (91 at F1). Verdict per cluster in HONEST-STATE §7bis:
  ~86 closed work docs = expected dormancy (F4 stays deferred — INDEX 159 ln < 250, triage failed 0×);
  the 4 DOC-CLEANUP-named clusters (F1-AUDIT · MAT-6-REAUDIT · REGEN-AUDIT · OBSERVABILITY-METRICS) are
  **no longer orphans** (reachable via FOUNDATIONS-REAUDIT / ASF-PROVENANCE / MEMORY-ARCHITECTURE /
  COUNCIL-360) → KEEP as dated evidence, no prune; 7 living/generated false positives (3 factory LOG +
  4 generated MEMORY.md) = observer noise, noted, no action.
- **Targets**: opus 86% vs ≤35% 🔴 · churn 776 (Δ+68) vs <20 🔴 · compactions 3 cum./0 new 🟡→🟢 ·
  delegation 1.01% · RTM 55/55 🟢 · benchmark 2/2 expected class 🟢 (`meta outcome`/`metrics`/`benchmark`).
- **Prefix trim measured**: `wc -l -c CLAUDE.md` 114/10,449 → 108/10,028. Churn re-measure = next
  comparable session window vs baseline 776 (trigger row in §2.7 via the audit-expiry rows).

## Criterio de cierre (demostrable, no narrable)
1. `HONEST-STATE.md §7bis` exists with the graph-derived verdicts (sealed ADR-009). ✅
2. `COST-DOWN-DIRECTION-INCREMENT.md §2.7` assumption ledger exists inside the §2 slice, with the
   2026-09-01 calendar trigger set. ✅
3. CLAUDE.md trimmed in ONE stretch with before/after bytes MEASURED (not narrated). ✅
4. `meta check` green · tree clean · `meta increment close` flips this header.
