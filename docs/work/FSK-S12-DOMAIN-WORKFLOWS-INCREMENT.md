<!-- meta:doc sha=1b93efd7956ca92f5e101e7cef6115e2096d04e4 updated=2026-06-20T14:04Z -->
<!-- meta:doc sha=PENDING updated=2026-06-20T02:23Z -->
# Incremento FSK-S12-DOMAIN-WORKFLOWS

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-20T14:04Z) (creado 2026-06-20T02:23Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> **HANDOFF (escrito 2026-06-20 por la sesión que cerró R2·FSK/FSK-S11).** Este doc es AUTOCONTENIDO a
> propósito: asumí que el contexto de quien lo abrió murió (`/clear`). Otro orquestador lo construye desde acá.
> Si algo no está acá o en los docs que cita, no existe. Construí por bloqueo, documentá en el gate (no al
> final), commit por fase con trailers I-10.

## 0. Orientación — leé esto primero (orquestador en frío)
1. `docs/STATE.md` §Ahora → el eje Reutilización (R1 ✅ · R2·FSK ✅). Este incremento es **R2·FSK eje #2**.
2. `docs/decisions/015` (ADR-015 §4) — R2 es expresividad de `domain.product`, **por-fábrica**, contenido de
   fábrica (ADR-012), grano: un incremento por fábrica/eje. Determinismo en VERIFICACIÓN, no en generación (I-3).
3. **`docs/work/FSK-S11-DOMAIN-EXPRESSIVENESS-INCREMENT.md` (CERRADO) — EL PATRÓN A SEGUIR.** Hizo el eje #1
   (vocabulario de campos: agregó `enum`/`int`/`number`/`date` + opcionalidad). Este incremento (#2, workflows)
   se construye igual: extiende el blueprint, fluye end-to-end, co-valida 2 productos, dientes de dos lados.
4. `reference/PRIMITIVES.md` (DES-3 = "auth/regla no-salteable" — los workflows son su pariente: una transición
   de estado inválida DEBE bloquearse de forma determinista).

### Cómo correr la línea FSK (lecciones caras de esta sesión — NO re-aprendas):
- **El sandbox de Bash MATA gradle** (señal 16 → exit 144, sin output). Toda corrida de línea
  (`product-run`, `ci --rederive`, gradle directo) necesita **`dangerouslyDisableSandbox: true`** en la tool Bash.
- **Corré la línea en FOREGROUND, no en background.** Un `product-run` en background + cierre de turno dispara
  el Stop hook `stop_proof` sobre la estación activa, que CHOCA con el contenedor/puerto de la línea en vuelo
  (mismo nombre `fsk_s1_pg` / puerto). En foreground termina en s10 (sin puerto) → stop_proof seguro. La línea
  tarda ~3 min/producto con gradle caliente; entra en el cap de 600s. Corré `ci --rederive` **por-producto**
  (`--product <p>`), NO `--all-products` (dos líneas no entran en 600s).
- `meta` = `PYTHONPATH=src python3 -m metafactory.cli <verbo>` (no hay wrapper en PATH en este shell).
- Mantené el cwd de Bash en la raíz del repo (el Stop hook y otros 3 hooks son cwd-relativos; un `cd` filtrado
  a un subdir rompe el cierre de turno — ver memoria `no-cd-subdirs-hook-deadlock`). Usá `( cd <abs> && … )`.
- Los puertos PG/obs ya están FUERA del rango efímero (5434/5435/18593) — no los toques.
- **El scaffold hardcodea el vocabulario del demo** (gotcha recurrente de R1): cuando agregues el feature,
  revisá CADA generador que lo toque (`grep` por nombres de entidad/campo del demo). En FSK-S11 mordió en el TS
  test, la UI/`app.ts` y `RouteTableTest`. Generá desde el blueprint, no hardcodees.
- Deferir una estación mid-line YA funciona (`activation: off` en `product.yml`, fix de engine de FSK-S11).

## 1. Objetivo
Segundo eje de **R2·FSK**: que `domain.product` pueda expresar **workflows / máquinas de estado** sobre un campo
`enum` — no sólo un valor de un conjunto cerrado (lo que FSK-S11 ya da), sino **transiciones VÁLIDas entre
estados** + un **estado inicial**, enforced de forma DETERMINISTA (sin LLM, I-3). Una transición ilegal se
bloquea por construcción. Es el siguiente PISO para clonar apps reales con ciclo de vida (Snipe-IT: un activo
`ready→deployed→archived`, nunca `archived→deployed`). Contenido de fábrica (ADR-012): el sustrato NO se toca.

## 2. El gap exacto (qué falta hoy)
Hoy un campo `enum` (FSK-S11) es un conjunto cerrado de valores: el contrato lo declara (`enum: [...]`),
openapi-generator emite un enum class Kotlin type-safe, y el producto puede tener `status = ready`. Pero
**cualquier** valor del enum es asignable a **cualquier** otro: no hay noción de que `archived` sea terminal o
que `ready→broken` sea válido pero `archived→deployed` no. Un workflow agrega esa **estructura de transición**.

## 3. Diseño propuesto (concreto, buildeable — ajustable por el orquestador)
**Gramática (blueprint `domain.product`):** un campo `enum` gana dos modifiers OPCIONALES (ausentes = enum libre,
el comportamiento de FSK-S11, sin romper nada):
```yaml
- name: status
  type: enum
  values: [ready, deployed, broken, archived]
  initial: ready                 # estado de una entidad recién creada (default de la columna / del ctor)
  transitions:                   # la máquina de estado: de qué estado se puede ir a cuáles
    ready:    [deployed, broken]
    deployed: [ready, broken, archived]
    broken:   [ready, archived]
    archived: []                 # terminal
```
**Validación (fail-closed, en `_load_blueprint`):** `initial` ∈ `values`; toda clave y todo destino de
`transitions` ∈ `values`; `transitions`/`initial` sólo sobre campos `enum`. Tipo/forma inválida → `SystemExit`
(mismo patrón que el guard de tipo desconocido de FSK-S11).

**Flujo END-TO-END (determinista):**
- **Contrato (OpenAPI, DES-6, fuente única):** el `enum` queda igual; la máquina se documenta como extensión
  `x-transitions`/`x-initial` en el schema del campo (single-source: el guard Kotlin se deriva de AHÍ, no de una
  lista paralela — un drift rompe el build, como todo en FSK).
- **Código generado (Kotlin):** un `object <Entity><Field>Workflow` con `val initial: <Enum>` y
  `fun canTransition(from: <Enum>, to: <Enum>): Boolean` DERIVADO del mapa de transiciones (cuando NO hay
  transitions declaradas, el guard no se emite — feature opt-in). Type-safe sobre el enum class de FSK-S11.
- **Tests del producto (la prueba por bloqueo, determinista):** un test generado que asevera una transición
  VÁLIDA permitida **y** una INVÁLIDA rechazada (diente de DOS lados). Idiom: tier unit de s7 (Kotest), como
  `RouteTableTest`/`StoreTest`. Opcional (extensión): un contract `main()` corrido por gradle (idiom s6) o un
  endpoint de update que llame al guard (DES-3 "no-salteable" real).
- **DB (opcional):** `initial` como default de columna; el enforcement vive en el app-guard (no en un trigger
  PG), consistente con que la lógica de dominio es código verificado.

**Dónde mapea en la línea / RTM (DECISIÓN del orquestador, con recomendación):** el workflow es una regla de
dominio del write-path. Recomendación: agregá una **capability nueva** `workflow_enforced` (familia DES-3) con
su **requisito** (L5) y un **check determinista** (`kind: product_env`) que corra el test del workflow — así el
RTM CRECE en 1 (el demo enriquecido pasa a 16/16; la instancia a su número), que es lo que le da al incremento
su claim "por bloqueo". Lo más liviano: sumá el check a **s7** (pirámide de tests) o a **s5** (write-path/auth).
Evitá agregar una estación nueva (la línea s0–s10 ya cierra; una capability+check sobre una estación existente
es más barato y honesto). **No hardcodees** el workflow en el sustrato — vive 100% en `factories/full-stack-kotlin/codegen/`.

### Seams concretos en `factories/full-stack-kotlin/codegen/scaffold_product.py`
- `_load_blueprint` — validación fail-closed de `initial`/`transitions` (cerca del guard de enum de FSK-S11).
- `_oapi_inline` / `_openapi_yaml` — emitir `x-transitions`/`x-initial` en el schema del campo enum (single-source).
- **nuevo** `_workflow_kt(entity, field)` → `<Entity><Field>Workflow.kt` (el guard derivado del contrato).
- **nuevo** `_test_workflow_kt(...)` → el test de dos lados (válida ✓ / inválida ✗), añadido a `build_files`.
- `build_files` (≈ línea 2280) — cablear los archivos nuevos SÓLO cuando hay `transitions` (opt-in).
- Cuidado con el límite de 160 de detekt (usá los helpers de wrapping `_kt_call`/`_jooq_chain` ya existentes).

## 4. Fases (plan; el orquestador las refina)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Gramática + validación + guard generado.** Modifiers `initial`/`transitions` en el blueprint; fail-closed en `_load_blueprint`; `x-transitions`/`x-initial` en el contrato; `_workflow_kt` (guard `canTransition`/`initial`, type-bound al enum class del contrato) + `_test_workflow_kt` (dos lados, tier `workflowTest`). `--selftest`/`--check-idempotent` verdes. | ✅ |
| 2 | **El demo ejercita un workflow + re-derive == pin.** `Task.priority` gana `initial: low` + transiciones stepwise (low↔high prohibido); capability `workflow_enforced` (DES-3) + REQ-F-011 + check en s7; línea s0–s10 verde · `ci --rederive` 11/11 == re-pin · **RTM 15→16 COMPLETE**. | ✅ |
| 3 | **2º producto con workflow DISTINTO (R1) + co-validación (ADR-014).** La instancia `assets` gana un workflow sobre `Asset.status` con estado TERMINAL `archived` (forma distinta del demo); `ci --rederive --product assets` 10/10 == pin, aislada · RTM 15/16 (s6 LLM diferido honesto). | ✅ |
| 4 | **Cierre.** STATE/ROADMAP/LOG + diff sustrato honesto (`src/metafactory/`+`seed/` = **0**) + suite verde + RTM + `meta increment close`. | ✅ |

## Evidencia (cierre 2026-06-20)
- **Gramática + guard (por bloqueo)**: un enum gana `initial`/`transitions` opcionales → el codegen emite
  `workflow/<Entity><Field>Workflow.kt` (`object` con `val initial` + `fun canTransition`, mapa `allowed`
  derivado del blueprint) type-bound al enum class del contrato. Validación fail-closed VIVA (4 casos
  verificados: `initial` fuera de values · destino fuera · origen fuera · `transitions` en no-enum → `SystemExit`).
- **Diente de DOS lados VIVO** (tier `workflowTest`, Kotest, source set propio idiom `integrationTest`/`testProbe`):
  guard correcto → 3 tests verdes; guard que **acepta todo** (`= true`) → `una transición no declarada es
  rechazada` FAILED → `workflowTest` rojo. Cubre los dos lados (válida ✓ / inválida ✗) + `initial`.
- **DES-6 (single-source)**: el contrato emite `x-initial`/`x-transitions` (vendor extensions inspectables,
  ignoradas por openapi-generator/openapi-typescript — el contrato no rompe); el guard se deriva del MISMO
  blueprint y es **type-bound** al enum class del contrato → tamper del `enum:` → `<Enum>` unresolved →
  compile rojo (el mismo mecanismo probado en FSK-S11, ahora cubriendo la máquina de estado).
- **2 productos, workflows de FORMA distinta** (criterio #3): demo `Task.priority` (stepwise simétrico, sin
  terminal) ↔ assets `Asset.status` (ciclo de vida con TERMINAL `archived`, fan-out asimétrico). Ambos
  `ci --rederive` == pin en clon limpio, aislados: **default 11/11 · assets 10/10**.
- **RTM**: default **COMPLETE 16/16** (REQ-F-011 ← `workflow_enforced` ← s7, artifact `…/webapp/workflow/`);
  assets 15/16 (REQ-F-011 ✓; REQ-F-007 s6 LLM diferido keyless, honesto). `meta check`: suite/isolation/
  generality verdes (otras fábricas intactas).
- **Anti-overfit**: `git diff src/metafactory/ + seed/` = **0** en todo el incremento — los workflows viven
  100% en `codegen/` + el spec + `stations/s7.yml` + `product.yml` (DATA de fábrica, ADR-012). Compuso sobre
  `product_env` + la pirámide de s7 ya existentes (§6, como s0–s10). Ninguna otra fábrica tocada.
- **Opt-in no-regresivo**: `Holder.department` (ambos productos) es un enum SIN `transitions` → no emite guard
  ni test (FSK-S11 intacto). El feature es opt-in a nivel de campo.

## 5. Gate (prueba por bloqueo — dientes de dos lados, no decorativos)
- **Transición enforced (dos lados):** el test generado prueba que una transición declarada VÁLIDa pasa Y una
  INVÁLIDA es rechazada por `canTransition`. Romper el guard (que acepte todo) → el lado inválido falla → rojo.
- **Single-source (DES-6):** el guard se deriva del contrato (`x-transitions`); tamper del contrato → el guard
  generado cambia → un test que lo cruza muerde (regen → verde).
- **Fail-closed (validación):** `initial` fuera de `values` · destino de transición inexistente · `transitions`
  sobre un campo no-enum → `SystemExit` del scaffold (como el guard de tipo de FSK-S11).
- **Opt-in no-regresivo:** un enum SIN `transitions` se comporta EXACTO como FSK-S11 (no se emite guard); el
  demo actual y la instancia `assets` siguen verdes si no declaran workflow.

## 6. Criterio de cierre (demostrable, no narrable)
1. `domain.product` expresa workflows: `enum` + `initial` + `transitions`; validación fail-closed VIVA.
2. El guard `canTransition` se GENERA del contrato y se EJERCITA por un test del producto de **dos lados**
   (válida ✓ / inválida ✗) — corre en el toolchain del producto, romperlo → rojo.
3. **≥2 productos FSK con workflows DISTINTOS** re-derivan `== su pin` en clon limpio, aislados (ADR-014).
4. **Anti-overfit:** `git diff src/metafactory/ + seed/` = 0 (los workflows son gramática de FÁBRICA — si tocás
   el sustrato, replanteá: probablemente lo metiste en el lugar equivocado). Suite verde · RTM FSK crece y cierra.

## 7. Notas de scope (qué NO es este incremento)
- **RBAC/autorización por rol** y **reglas de negocio arbitrarias por LLM** (patrón s6/MAT-2) son ejes R2
  SIGUIENTES (incrementos aparte, por-fábrica). Este es SÓLO workflows/máquinas-de-estado, determinista.
- Los diferidos de entorno-vivo de la línea FSK (Ktor vivo, Playwright e2e s7, Lighthouse s8, imagen Docker s10,
  feed OSV vivo s4) son ortogonales — no los toca este incremento (ver `STATE`/spec, todos `declared-deferred`).
- Residual conocido (de FSK-S11): una instancia con la estación LLM s6 **activa con key** necesitaría persistir
  su `Summary.kt` pineado, pero `products/*/domain_gen/` está gitignored. No lo ejercita este eje (workflows son
  deterministas, keyless); queda como gap de R1+s6 para otro incremento.
