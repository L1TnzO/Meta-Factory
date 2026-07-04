<!-- meta:doc sha=e8dd5036074d303903db6ee61af728102adf3457 updated=2026-07-04T20:14Z -->
# Incremento COLUMN-MAINT

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-04T20:14Z) (creado 2026-07-04T20:08Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Mantenimiento de columna/pipeline declarado barato por COUNCIL-360 §4.3: **H-5** (el doble-sello
`sha=PENDING`: `doc_stamp` prependeaba el sello fresco sin remover el placeholder del autor → fecha
falsa hasheada al cuerpo, ruido de triaje en INDEX) y **H-4** (`security_scan` era 5 regexes: sin
corpus estándar, sin entropía, sin defensa anti-slopsquatting para deps generadas por LLM).
Frontera de seguridad + pipeline de sellos = COLUMNA → escrito con ojos propios, sin delegar
(SELF-IMPROVEMENT §3).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | H-5: `strip_residual_seals` en `stamp()` (self-healing) + diente en `check()` (pseudo-sello líder fuera de `decisions/` → problema) + tests dos-lados | ✅ |
| 2 | H-5 decisión explícita: `decisions/` = clase inmutable EXENTA (des-churn > pureza; los 4 residuales 011/012/015/018 quedan grandfathered); ADR-022 (de HOY) limpiado a mano; `doc-sync` curó 15 docs | ✅ |
| 3 | H-4: `_PATTERNS` 5→14 formatos (corpus estándar: anthropic/openai/stripe/google/gitlab/npm/pypi/sendgrid/jwt) + detector de entropía (≥32 chars base64ish citados, ≥4.8 bits/char; hex puro EXENTO — punto ciego DECLARADO, los sha saturan el árbol) | ✅ |
| 4 | H-4 anti-slopsquatting: `docs/reference/dep-allowlist.yml` (DATA curada, re-derivada de los builds verdes) + `dep_problems()` — dep declarada fuera de la allowlist → ROJO con remedio; agregar una dep = acto deliberado (regla ADR-020/022) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `pytest tests/test_docs_manifest.py tests/test_security_scan.py` → 41 passed (dos lados: PENDING
   se stripea y queda idempotente · decisions preservado · entropía dispara/hex exento · dep alucinada
   `left-pad-ai` → rojo · allowlist ausente → N/A no verde). ✅ 2026-07-04
2. `grep -rl "sha=PENDING" docs/` → SOLO las 4 decisions grandfathered. ✅
3. Gate real: `security_scan .` → sustrato limpio (127 archivos) · diente RED 5 formatos (antes 3) ·
   16 deps ⊆ allowlist. ✅
4. `meta check` 19/19 verde.
