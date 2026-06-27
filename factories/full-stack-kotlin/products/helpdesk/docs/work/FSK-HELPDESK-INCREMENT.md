<!-- meta:doc sha=f849a74eda327cd4da45a4e9465d52bf9b623c9a updated=2026-06-27T01:41Z -->
# Incremento FSK-HELPDESK

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-26T03:37Z) (creado 2026-06-26T03:31Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
El **producto benchmark sweet-spot** de la Fase 4 (`REAIM-SWEET-SPOT`): una app CRUD de helpdesk/ticketing
de **5 entidades** —el caso del "80% día-1"— generada por la línea REAL de FSK **sin un solo incremento de
fábrica nuevo** (`git diff codegen/+src/+seed/ = 0`), probando que FSK YA cubre el sweet-spot. Contrasta con
Snipe-IT (19 entidades, 17 ADOPT), que pasa a ser el techo de regresión, no el punto de partida.

## Qué es DATA (el único punto de variación)
`products/helpdesk/product.yml` — un subárbol `domain.product` con topología de dominio PROPIA, distinta de
`tasks` (demo) y `assets`: 5 entidades en orden topológico (Agent · Customer · Category · Ticket · Comment),
RBAC de 3 roles `admin/supervisor/agent`, ownership a nivel de fila (`Ticket owned_by assignee_id → Agent`,
bypass `[admin, supervisor]`), y un WORKFLOW del ciclo de vida del ticket con estado TERMINAL (`closed`) y
un CICLO de reapertura (`resolved → reopened → in_progress`) — una forma de máquina de estado distinta del
stepwise del demo y del fan-out de archivado de assets. s6 (lógica de dominio por LLM vivo) se difiere
keyless (`station_activation: s6: off`, la opción que el propio gate sanciona, doctrina R1).

El producto ejercita TODO el vocabulario FSK del sweet-spot: campos string/int/number/date/boolean/enum +
opcionalidad + ref; workflow (FSK-S12); RBAC (FSK-S13); ownership (FSK-S14); endpoints vivos enforzados a
runtime (FSK-S15); CRUD + body-parsing + frontend que consume/renderiza + browser real (FSK-S16+).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Diseñar el blueprint del sweet-spot (5 entidades, topología propia, sólo capacidades existentes) | ✅ |
| 2 | Pre-validar sin gradle (`scaffold --selftest` + `--check-idempotent` + 0 forward-refs) | ✅ |
| 3 | Generar + pinear por la línea REAL FSK (`meta product new`, e2e gradle+PG+server+Chromium) | ✅ |
| 4 | Probar por bloqueo: RTM + `ci --rederive == pin` + `git diff codegen/+src/+seed/ = 0` | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `meta product new` corre la línea e2e VERDE (11 estaciones, s6 diferido keyless) y pinea. ✅
2. RTM re-derivado de `.proof/`: 25/26 SATISFIED — el único UNSATISFIED es REQ-F-007 (s6 LLM, deferral
   VISIBLE por `activation:off`, idéntico a assets/snipeit). ✅
3. `meta ci --rederive --product helpdesk` re-deriva en clon limpio **== pin** (re-corre gradle+PG en clon). ✅
4. **`git diff codegen/+src/+seed/ = 0`** — cero incrementos de fábrica nuevos: el sweet-spot lo cubre el
   codegen existente, byte-intacto. El único path nuevo es `products/helpdesk/`. ✅ (la tesis del re-apunte)

## Evidencia (por bloqueo)
- **product-run e2e**: `product new full-stack-kotlin/helpdesk — PASS` (11 estaciones; s0–s5, s7–s11; s6 off).
- **RTM**: `25/26 SATISFIED` (REQ-F-007 s6 SHUT = deferral keyless visible). El producto cubre 20 REQ-F +
  6 REQ-NF: contrato fuente única, datos vivos, rutas/RBAC/ownership, workflow, observabilidad, control de
  acceso a runtime, CRUD+entrada tipada, frontend consume+render+browser, build hermético, deploy vivo.
- **`ci --rederive --product helpdesk`**: `PASS · 11/11 proof_sha == pineado` (re-derivado en árbol limpio,
  re-corre gradle+PG en clon; el pin no es custodia, es re-derivación — la prueba anti-fake-green).
- **`git diff codegen/+src/+seed/`**: **0** (cero cambios de codegen/sustrato). Anti-overfit por construcción:
  la generalidad del codegen (gate `generality`) ya prohíbe nombres de dominio en el sustrato; este producto
  no necesitó tocar nada → la generalidad NO es narrada, es un hecho del diff.
- **Toolchain**: JDK 21 (javac), Gradle 9.5.1, Kotlin 2.4.0, Docker PostgreSQL viva, Playwright/Chromium real.

## Alcance honesto (§7)
s6 (lógica de dominio LLM) diferido keyless (doctrina R1, no es límite del mecanismo). El benchmark mide el
núcleo determinista del sweet-spot, que NO depende de una key. La formalización del benchmark como TARGET
verificable + el verbo `meta benchmark` + el gate dos-lados (helpdesk PASA / snipeit FALLA el sweet-spot) viven
en el incremento META hermano `REAIM-SWEET-SPOT` (ADR-016: dos incrementos por nivel).
