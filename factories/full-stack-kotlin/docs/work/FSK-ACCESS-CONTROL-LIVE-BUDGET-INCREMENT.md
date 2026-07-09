<!-- meta:doc sha=d0f8910fe1fce9309a2e89d3bebb448c96492694 updated=2026-07-09T03:17Z -->
# Incremento FSK-ACCESS-CONTROL-LIVE-BUDGET

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-09T02:29Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Cerrar 3 gaps GENERALES de la fábrica (ninguno específico de un producto) que salieron a la luz al ensanchar
`snipeit` de 19→39 entidades (`SNIPEIT-MIN-COMPLIANCE-INCREMENT.md` Fase 2): funciones/checks/presupuestos
generados que escalan con la CANTIDAD de entidades servidas y dejan de tener margen en un producto ancho.
Los 3 son cambios de DATOS/umbral (no de semántica) — un producto angosto queda byte-neutral.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **`access_control_live` timeout 120s→240s** (`stations/s9.yml` + `factory.spec.yml`, la copia realmente ejecutada): `access_control_check.py` hace ~O(entidades) round-trips HTTP secuenciales contra una JVM+PG recién levantadas; con 39 entidades el ready-budget de 120s no alcanzaba (reproducido 2x independientes por el `generator`, no un flake — medido con un repro manual `-u` sin buffer que aisló la causa REAL: ver Fase 2). | ✅ |
| 2 | **Gap real encontrado durante el repro** (no solo timing): el codegen nombra la constante de valores-de-enum por NOMBRE DE CAMPO (`STATUS_VALUES`), sin qualificar por entidad — dos entidades con un campo enum llamado igual (`Asset.status` y el `status` que se le había puesto a `ImportJob`) COLISIONAN; la 2ª entidad queda validada contra el set de valores de la 1ª → 400 espurio. Documentado como gap honesto en `SNIPEIT-DOMAIN.md`; el fix real fue a nivel PRODUCTO (renombrar el campo, `import_status`), no sustrato — evita tocar el codegen para un caso no repetido aún. | ✅ |
| 3 | **`detekt LongMethod` en `appRoutes()`** (`codegen/scaffold/auth.py`): la tabla de rutas generada (1 línea por GET/POST/PUT/verbo/restore/trash por entidad) superaba el máximo de 60 líneas con 39 entidades. Mismo idioma YA usado en `data_layer.py` (`@Suppress("LongMethod")` condicional a la cuenta real de líneas, sólo cuando corresponde — no decorativo) aplicado a las 2 variantes (RBAC y no-RBAC) de `appRoutes()`. | ✅ |
| 4 | **`perf_budget_gate` decorativo** (`codegen/scaffold/quality_tooling.py`): el presupuesto de bundle (`_budget_json`) YA escala con `n_served` (base + por-entidad), pero el fixture NEGATIVO (`_probe_bloated_ts`, un blob de tamaño FIJO pensado para superar el presupuesto) no escalaba — con 39 entidades el presupuesto creció por encima del blob fijo y el lado degradado del gate dejó de discriminar (medido: budget 117054 > blob bundleado 100052). Fix GENERAL: el blob ahora se computa `budget(n_served) + margen fijo`, cerrando la clase de bug para cualquier producto futuro (no sólo un 3er bump manual como el histórico 60000→100000). | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `product-run --factory full-stack-kotlin --product snipeit --mode harden` PASS end-to-end (s0..s11, 39 entidades/40 tablas).
2. `ci --rederive --factory full-stack-kotlin --all-products` → 4/4 == pin (sin regresión en assets/helpdesk/default/snipeit).
3. `meta pin --factory full-stack-kotlin --product snipeit --verify` → 12/12 proof_sha == pineado.
4. `meta check` → todos los gates verdes (incl. `suite`, tras actualizar el fixture de `tests/test_benchmark.py` a 39 entidades).
