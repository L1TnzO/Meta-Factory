<!-- meta:doc sha=94114b44cf2c92b3aeaa6ac2c183d147949446f8 updated=2026-06-20T00:38Z -->
# Incremento FSK-S11-DOMAIN-EXPRESSIVENESS

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-20T00:35Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Primer incremento del eje **R2 (expresividad de `domain.product`, ADR-015 §4)** sobre la fábrica **FSK**:
generalizar el **vocabulario de campos** del scaffold — de los 3 tipos hardcodeados (`string`/`boolean`/`ref`,
todo `NOT NULL`) a un vocabulario **arbitrario** (`integer`/`number`/`date`/`datetime`/`enum` + opcionalidad)
vía **gramática extendida determinista** (no LLM), fluyendo END-TO-END (contrato OpenAPI → schema SQL/jOOQ →
model → test del producto) y verificado por bloqueo. Es el PISO de R2: workflows/RBAC/reglas se apoyan en que
entidades+campos sean expresables primero. Es **contenido de fábrica** (ADR-012): NO toca el sustrato (R1 se
reutiliza, no se modifica). Co-valida con R1 (un 2º producto FSK con vocabulario distinto, ADR-014).

## Alcance (qué SÍ y qué NO)
- **SÍ**: extender los 3 mapas que deben concordar — `_OAPI_TYPE` (contrato), `_KT_SAMPLE` (muestra Kotlin),
  `_PG_COL` (columna PG) — + `_migration_sql` (nullability condicional al modifier `required`). `enum` lleva
  `values:` (→ OpenAPI `enum`, model Kotlin tipado por openapi-generator). El guard de **tipo desconocido**
  (`_load_blueprint`) se mantiene (fail-closed).
- **NO** (incrementos R2 posteriores, por-fábrica): workflows/máquinas de estado, RBAC/autorización por
  rol·entidad, reglas de negocio por LLM (patrón s6/MAT-2). Tampoco toca el sustrato `src/metafactory/`.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Vocabulario de tipos extendido (scaffold).** Extender `_OAPI_TYPE`/`_KT_SAMPLE`/`_PG_COL` + `_migration_sql` para `integer`/`number`/`date`/`datetime` + `enum` (con `values`) + opcionalidad (`required: false` → columna nullable, fuera de `required[]` OpenAPI). Guard de tipo desconocido intacto (fail-closed). Scaffold `--selftest`/`--check-idempotent` verdes. | ⏳ |
| 2 | **El demo ejercita los tipos nuevos + re-derive == pin.** Enriquecer el blueprint del demo con campos de los tipos nuevos (p.ej. `Task.status: enum`, `Task.due: date`, un campo `number`/opcional); M0–M8 + `ci --rederive` == re-pin; los tipos aparecen en OpenAPI(enum/format)/SQL(col+nullability)/jOOQ/test. | ⏳ |
| 3 | **2º producto FSK con vocabulario DISTINTO (R1) + co-validación (ADR-014).** `meta product new --factory full-stack-kotlin --name assets <asset-tracker.yml>` (Snipe-IT-lite: `serial:string unique`, `quantity:integer`, `purchased:date`, `status:enum[deployed,ready,archived,broken]`, `cost:number`); instancia coexistente keyless (s6 LLM `station_activation:off`, doctrina R1); `ci --rederive --product assets` == su pin, aislada. | ⏳ |
| 4 | **Cierre.** STATE/ROADMAP/LOG + `git diff src/metafactory/+seed`=0 + `meta check` + RTM FSK + `meta increment close`. | ⏳ |

## Gate (prueba por bloqueo — dientes de dos lados, no decorativos)
- **Flujo end-to-end por cada tipo nuevo**: declarar un campo `enum`/`date`/`integer`/`number` ⇒ aparece en
  el contrato (enum/format), en la columna SQL (tipo + NOT NULL/nullable según `required`), en el query jOOQ
  tipado y en un test del producto que lo round-trippea. **Romper el flujo de un tipo → rojo** (regen → verde).
- **Enum enforced**: un valor fuera de `values` no compila contra el enum Kotlin generado (o lo rechaza el
  contract test) → rojo.
- **Opcionalidad real** (compone `infra_up`/s1 con PG viva): un campo `required` queda `NOT NULL`; insertar
  NULL en una columna required → DB/test rojo. Un campo opcional acepta ausencia.
- **Tipo desconocido sigue bloqueando** (`_load_blueprint`): un `type` no soportado → `SystemExit` (fail-closed).

## Criterio de cierre (demostrable, no narrable)
1. El vocabulario de tipos del scaffold pasó de **3** (`string`/`boolean`/`ref`) a **≥7** incluyendo
   `enum`/`date`/`integer`/`number` + opcionalidad; un tipo desconocido sigue bloqueando (fail-closed).
2. **≥2 productos FSK con vocabularios de campo DISTINTOS** (demo enriquecido + instancia `assets`)
   re-derivan `== su pin`, aislados (R1 isolation viva: borrar el proof de uno no abre la gate del otro).
3. Los tipos nuevos **fluyen END-TO-END** verificado por bloqueo (contrato → SQL/jOOQ → test), con un diente
   de dos lados mordiendo por cada eje nuevo (enum inválido → rojo · NULL en required → rojo; regen → verde).
4. **`git diff src/metafactory/ + seed/` = 0** (R2 = contenido de fábrica; el sustrato R1 se reutiliza, no se
   toca). `meta check` verde · suite + RTM FSK verdes.
