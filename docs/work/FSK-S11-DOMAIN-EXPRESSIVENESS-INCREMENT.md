<!-- meta:doc sha=bcea3f10046f1a3aa66ca2cc49ef0b4de60c8b70 updated=2026-06-20T02:18Z -->
# Incremento FSK-S11-DOMAIN-EXPRESSIVENESS

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-20T02:18Z) (creado 2026-06-20T00:35Z). Cerralo con `meta increment close`
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
| 1 | **Vocabulario de tipos extendido (scaffold).** `_OAPI_TYPE`/`_KT_SAMPLE`/`_PG_COL` + `_migration_sql` para `int`/`number`/`date` + `enum` (con `values`, → enum class Kotlin type-safe) + opcionalidad (`required: false` → columna nullable, fuera de `required[]`). Validador fail-closed (tipo desconocido · enum sin `values` · ref colgante · `required` no-bool). Wrapping de codegen (App.kt/jOOQ/Repository select/ctor) para entidades anchas bajo el límite de 160 (detekt). TS test + UI/app.ts + RouteTableTest **derivados del blueprint** (eran hardcodeados al demo). | ✅ |
| 2 | **El demo ejercita los tipos nuevos + re-derive == pin.** `Project.budget:number`, `Task.{priority:enum, estimate:int, due:date, notes:string opcional}`. Línea s0–s10 VERDE · `ci --rederive` 11/11 == pin en clon limpio · RTM 15/15. Tipos en OpenAPI(`enum`/`int32`/`double`/`format:date`)/SQL(col+NOT NULL/nullable)/jOOQ/test. PG viva: `FSK_DB_ROUNDTRIP_OK reversible=ok` (date/int/number/enum + opcional-NULL). | ✅ |
| 3 | **2º producto FSK con vocabulario DISTINTO (R1) + co-validación (ADR-014).** `meta product new --factory full-stack-kotlin --name assets blueprints/asset-tracker.yml` (Snipe-IT-lite: `quantity:int`, `cost:number`, `purchased:date`, 2 enums, `holder_id` ref opcional, `notes` opcional). Línea s0–s10 VERDE (s6 LLM diferido `station_activation:off`, keyless) · `ci --rederive --product assets` 10/10 == pin, aislada (raíz propia) · RTM 14/15 (s6 honestamente diferido). | ✅ |
| 4 | **Cierre.** STATE/ROADMAP/LOG + diff sustrato honesto + suite 573 + RTM + `meta increment close`. | ✅ |

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
1. ✅ El vocabulario de tipos del scaffold pasó de **3** (`string`/`boolean`/`ref`) a **8** (`+int`/`number`/
   `date`/`enum` + opcionalidad); fail-closed VIVO (tipo `uuid`→exit 1 · enum sin `values`→exit 1 · ref
   colgante→exit 1; blueprint válido con los 8 → exit 0).
2. ✅ **2 productos FSK con vocabularios de campo DISTINTOS** (demo enriquecido + instancia `assets`)
   re-derivan `== su pin` en CLON LIMPIO, aislados (raíz propia por instancia): default **11/11**, assets **10/10**.
3. ✅ Los tipos nuevos **fluyen END-TO-END** verificado por bloqueo: línea s0–s10 verde con todos los tipos
   contra **PG viva** (`reversible=ok`); diente enum type-safety de **dos lados** (tamper `enum:[...]` del
   contrato → `Unresolved reference 'Status'` → compile rojo · regen → verde). Opcionalidad real: `required`→
   `NOT NULL`, opcional→nullable insertado en NULL por el roundtrip vivo (positivo).
4. **Sustrato: `git diff seed/` = 0** y `src/metafactory/` = **8 líneas en `engine/sequence.py`** — un fix
   **GENERAL** de R1 (un `requires_prev` a una estación diferida es transparente → soporta deferral mid-line),
   **cero nombres de fábrica/tech/dominio** (anti-overfit intacto, verificado por grep). NO es contenido R2: el
   vocabulario de tipos vive 100% en la fábrica (`codegen/`). Suite **573** · RTM default 15/15.

## Sub-hallazgos (gaps de R1 que el producto FSK rico expuso; ninguno es de R2)
> R1 se co-validó con `iot/fleet` + `full-stack/tasks`, fábricas con líneas más simples. La instancia FSK
> (11 estaciones, PG viva, estación LLM mid-line) destapó 3 gaps. **2 se arreglaron como DATA de fábrica
> (sustrato intacto); 1 como fix general de engine** (sustrato, domain-agnóstico).
1. **Chassis-relative `kind: command` check** (DATA): `scaffold_idempotent` corría `codegen/scaffold_product.py`
   con cwd=raíz de instancia, donde `codegen/` no existe (vive en el chasis). Fix DATA: `sh -c` que resuelve
   `codegen` o `../../codegen` según cwd. (iot/full-stack usaban checks `product_env`, nunca un command chassis-relativo.)
2. **Puertos pineados en el rango efímero del SO** (DATA): s1/s7 PG (55434/55435) y s9 obs (58593) caían en
   32768–60999 → el navegador del usuario robó 55434 → gate roja por construcción (exit 125). Fix DATA: 5434/5435/18593.
3. **`requires_prev` no veía a través de una estación diferida** (engine, general): deferir s6 (LLM, keyless)
   wedgeaba s7–s10 aunque sus checks pasaran. R1 sólo había diferido la ÚLTIMA estación (full-stack/tasks s5).
   Fix general en `sequence.py` (8 líneas, domain-agnóstico): predecesor explícito inactivo → transparente.
