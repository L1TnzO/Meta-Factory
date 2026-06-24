# Incremento TIME-COMPUTED-ADOPT

> **Doc de gobierno** (nivel PRODUCTO `products/snipeit/`, ADR-016). Estado: **CERRADO** (2026-06-24T17:30Z).
> Todo cambio de `product.yml` vive acá (ADR-010). Hermano de la fábrica `FSK-TIME-COMPUTED-INCREMENT.md`.

## Objetivo
`Asset.current_value` deja de ser una constante por-modelo y se vuelve la depreciación straight-line REAL sobre los
MESES TRANSCURRIDOS desde `purchase_date` hasta `now` (usando el operando de tiempo `months_since` que aporta la fábrica
en FSK-TIME-COMPUTED).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `purchase_date` → REQUERIDA (observable: sembrada/posteada → el valor derivado se ve y el diente muerde) | ✅ |
| 2 | `current_value` AST: la cuota mensual `purchase_cost / model_id.depreciation_id.months` se MULTIPLICA por `months_since(purchase_date)` → `max(purchase_cost − cuota * meses_transcurridos, 0)` | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `product-run --product snipeit` **PASS**; RTM snipeit **25/26** (único UNSAT = REQ-F-007/s6 LLM keyless). ✅
2. Diente vivo de DOS lados (en el incremento de fábrica): con `FSK_NOW` fijo el GET `current_value == 21.25`
   (re-derivado), degradar la aritmética del tiempo → sólo `[computed]` rojo, hermanos verdes. ✅
3. `ci --rederive --all-products` == pin (snipeit 11/11) — `git diff product.yml` es el único cambio de producto
   (el `pinned_verdict.json` queda byte-idéntico: proof_sha exit-code-based, no se agregó check/estación). ✅

## Decisión de mapeo (honestidad de fidelidad, P1 §6)
- **`purchase_date` requerida en la adopción** aunque Snipe-IT la deja nullable: el MECANISMO de fábrica admite un
  `date` opcional (NULL → 0 meses → sin depreciación), pero OBSERVAR un valor no-trivial exige sembrar/postear la fecha
  → requerida. Mismo trato (y mismo residual honesto) que el ref-del-medio requerido de FSK-XENTITY-DEPTH2.
- **El reloj se mockea por `FSK_NOW`** (lo fija el `up` de s9 en la fábrica) y el server lo expone por `/seed` → el
  oráculo del proof lo lee de ahí (single source). Sin mock el valor sería no-determinista (depende de hoy).
- El período de depreciación sigue siendo `model_id.depreciation_id.months` (cross-entity DEPTH-2, FSK-XENTITY-DEPTH2).
  La fórmula compone las TRES dimensiones de valores-derivados: same-entity (`purchase_cost`) + cross-entity depth-2
  (`...months`) + tiempo (`months_since(purchase_date)`).
