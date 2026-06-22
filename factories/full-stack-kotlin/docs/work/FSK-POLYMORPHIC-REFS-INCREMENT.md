# Incremento FSK-POLYMORPHIC-REFS — ref polimórfico (un ref a una UNIÓN de entidades) · el ÚLTIMO eje de modelo-de-datos

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO**
> (creado 2026-06-22T19:57Z). Cerralo flippeando este header a CERRADO (el `increment status` lee el header) **o**
> con `meta increment close --factory full-stack-kotlin`. Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-QTY-OPERATIONS con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (el ÚLTIMO eje de MODELO-DE-DATOS faithful — y por qué es DECISIÓN tuya)

**El modelo de acceso está COMPLETO** (auth → RBAC → ownership → company-scope, vivo a runtime). **El comportamiento
con STOCK está vivo** (FSK-QTY-OPERATIONS: el checkout de un accesorio decrementa qty con out-of-stock → 409). Cerrados
ya, product-driven por Snipe-IT (10 deferrals): CRUD del grafo · self-ref · ownership opcional/RTD · refs requeridos
transitivos · verbos checkout/checkin (workflow) · custom-fields format · ciclos cross-entidad · company-scoping · **qty/stock**.

**Lo que falta del MODELO DE DATOS faithful: los refs POLIMÓRFICOS.** En Snipe-IT, el TARGET de un checkout es
polimórfico: `Asset.assigned_to` → **User | Location | Asset**; `AccessoryCheckout.assigned_to` ídem. Hoy snipeit lo
**simplifica a User** (`Asset.assigned_user_id` → User, anotado como "gap" en `SNIPEIT-DOMAIN.md`). Un ref polimórfico
es una primitiva de TIPO NUEVA: un `ref` que apunta a una UNIÓN de entidades, no a una sola.

**Por qué es un buen próximo:** es el ÚLTIMO eje de modelo-de-datos genuinamente faithful que queda. Tras él, el
modelo + el acceso + el comportamiento-núcleo quedan COMPLETOS — lo que resta es breadth (las ~226 rutas, soft-deletes,
Kits, EAV dinámico). Es el hermano conceptual de los enums (un valor de un conjunto cerrado) pero sobre refs (un target
de un conjunto cerrado de entidades).

**⚠️ ESTA ES TU DECISIÓN (con más contexto).** Es el eje MÁS THORNY que queda (varios wrinkles, §0.1). Si al
investigar decidís que NO es el mejor próximo, la alternativa honesta (depreciación calculada / campo computado) está
en §7. Tenés autoridad para reabrir esa decisión — pero leé los wrinkles ANTES.

### 0.1 LOS WRINKLES (leélos antes de comprometerte — este eje tiene VARIOS, no es opt-in trivial como qty)
1. **NO hay FK / NO hay integridad referencial en la DB.** No podés poner una FK a una UNIÓN de tablas. Un id
   polimórfico colgante NO lo caza la DB → el diente "FK fail-closed → 409" de FSK-REFS-IN-BODY **NO aplica**. El
   diente se vuelve sobre el ROUND-TRIP de `(tipo, id)`, no sobre la integridad. (Honesto: es una limitación real del
   patrón, no un bug. Documentála.)
2. **DOS columnas por ref polimórfico** (`<campo>_type` VARCHAR + `<campo>_id` BIGINT) — el discriminador + el id. TODO
   el codegen asume **1 campo = 1 columna** (`_COL`, `_migration_sql`, `_row_json_fn`, `_input_fields`, `_seed_chain`,
   `_mutation_fns`, jOOQ). Generalizar "un campo que mapea a 2 columnas" toca MUCHOS sitios. Es el wrinkle estructural.
3. **El target ownership/owner.** `Asset.owned_by = assigned_user_id` — el campo dueño de Asset ES su target de
   asignación. Si `assigned_to` se vuelve polimórfico, **el guard de ownership se rompe** (compara `principal == owner_id`,
   un Long único; un target Location/Asset no es un "User principal"). ⚠️ **NO vuelvas polimórfico el campo `owned_by`.**
   Montá el ref polimórfico en un campo OPCIONAL NO-dueño (o en una entidad pivot), separado de ownership.
4. **El `assigns` del verbo de workflow.** El checkout faithful ASIGNA el target polimórfico. Hoy `assigns: <ref único>`
   setea UNA columna al id del body (`_operation_repo_fns` rama workflow + `_operations_handlers`). Un assigns polimórfico
   setea DOS columnas (type+id) del body → toca la gramática del `assigns` + el handler + el proof. Es un sub-eje aparte.

**Conclusión honesta**: hay ~3 sub-ejes acoplables (la PRIMITIVA del ref polimórfico · el assigns polimórfico del verbo ·
evitar el owner). El camino BOUNDED y limpio: **primero la PRIMITIVA sola** (un campo `ref` OPCIONAL no-dueño con
`to: [A, B, …]` sobre una entidad VIVA, con diente de ROUND-TRIP del cuerpo: POST `{<campo>_type, <campo>_id}` → GET
los devuelve EXACTOS), DEFERÍ el assigns-polimórfico y el owner-polimórfico. Driven por el producto: dale a Asset (o a
Accessory, la with_ref viva) un campo OPCIONAL polimórfico nuevo, o transformá un opcional existente. Decidí vos tras investigar.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥540000ms** (el sandbox mata gradle:
exit 144/1). **cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del hook
`stop_proof` al cerrar; restaurá con `cd /home/enzo/University/Integración/APP/Meta_Factory`).
Debe dar **PASS**, RTM snipeit **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **s7 PG 5435 · s9 puertos 18593-18595 + PG 5436/5437 · s11 18596** → NUNCA dos corridas en paralelo, NUNCA dejes un
`product-run`/`ci` en BACKGROUND al cerrar el turno (`stop_proof` re-corre la estación activa → colisión de puerto/PG).

**2) EL DISEÑO (resolvelo GENERAL, cero nombres de dominio — `generality` verde es el anti-overfit real):**
- **Gramática del blueprint** (`_load_blueprint` ~L176): aceptá `to: [E1, E2, …]` (lista) en un campo `type: ref` →
  marca el ref como POLIMÓRFICO. Fail-closed: cada Eᵢ ∈ entidades; ≥2 targets; el campo **debe ser opcional**
  (`required: false`) — un polimórfico requerido tiene los mismos problemas de seed/FK que un forward-ref (difiérelo
  como FSK-XENTITY-CYCLES difirió el forward requerido); **NO sobre el campo `owned_by`** (wrinkle #3). Mantené el
  guard existente de `to` único (string) intacto → byte-neutro para todos los refs actuales.
- **La migración** (`_migration_sql` ~L1142): un ref polimórfico emite DOS columnas (`<campo>_type VARCHAR(...)` +
  `<campo>_id BIGINT`), **sin** `REFERENCES` (no hay FK a una unión). Hoy un `ref` emite `<campo> BIGINT REFERENCES …`.
- **jOOQ / columnas** (`_COL` ~L1041 mapea name→COL; jOOQ DDLDatabase deriva los tipos): el ref polimórfico tiene 2
  columnas tipadas (VARCHAR + BIGINT). Pensá si introducís un helper `_poly_cols(f)` que devuelve los 2 nombres de
  columna, y dónde el codegen itera "columnas de un campo" (hoy asume 1).
- **rowJson** (`_row_json_fn` ~L1178): serializá AMBAS columnas (`<campo>_type` string entrecomillado +
  `<campo>_id` raw). Es lo que GET /{id} devuelve y el round-trip cruza.
- **Input / body** (`_input_fields` ~L1057 + `_input_data_class` + el codec `_codec_helpers`): un ref polimórfico
  OPCIONAL no entra a `_input_fields` (sólo requeridos). Para un round-trip vivo, o lo hacés requerido (pero §wrinkle:
  requerido se difiere) o agregás el soporte de campos OPCIONALES en el body (otro eje). **Avenida limpia para el 1er
  cut**: montá el polimórfico como REQUERIDO en una entidad NUEVA pivot sembrable, O aceptá el body opcional. Mirá cómo
  `_mutation_fns` arma el INSERT y dónde un campo opcional se saltea hoy.
- **El seed** (`_seed_chain` ~L3615): para sembrar una fila con un polimórfico, setea las 2 columnas (`_type` a un
  literal de target, `_id` al id capturado de ESE target sembrado). Reusá el patrón de `ref_wiring`.
- **El contrato** (`_openapi_yaml` ~L362): documentá el ref polimórfico (p.ej. `<campo>_type` enum cerrado de los
  targets + `<campo>_id` integer, o una extensión `x-polymorphic-targets: [E1, E2]`). route_check no mira el schema de
  campos (sólo rutas/roles) → no debería romper, pero verificá que openapi-generator/typescript sigan parseando.
- **El proof** (`_access_control_check_py` ~L4722, un bloque nuevo `_POLY_PROOF` como `_QTY_PROOF`): POST una fila con
  `{<campo>_type: "<TargetA>", <campo>_id: <idA de /seed>}` → GET /{id} devuelve AMBOS EXACTOS; repetí con `<TargetB>`
  (el discriminador cambia el tipo) → el round-trip prueba que el server distingue el target. Diente: degradar el
  rowJson (dropear `<campo>_type`, o hardcodearlo) → el GET no devuelve el tipo posteado → rojo SÓLO en s9.

**EL DIENTE de dos lados** (criterio §6.2): el round-trip del cuerpo polimórfico. POST `{type:A, id:X}` → GET devuelve
`{type:A, id:X}`; POST `{type:B, id:Y}` → GET devuelve `{type:B, id:Y}`. Saboteá la serialización del discriminador
(`<campo>_type` hardcodeado a un literal, o dropeado del rowJson) → el GET no refleja el target posteado → **SÓLO**
`access_control_live` rojo (s9), hermanos s9 + s0–s8 verdes → revertí → verde. ⚠️ **El sabotaje que muerde a RUNTIME
NO puede introducir un hallazgo ESTÁTICO** (detekt/ktlint en s2) — degradá la LÓGICA/serialización, no la forma Kotlin
(lección CARA, §3).

---

## 1. ⚠️ RE-PIN — ¿hace falta?
Si el cambio vive DENTRO del check existente `access_control_live` (s9, ya pineado) — extendiendo el proof, no agregando
check/estación — el **`proof_sha` queda INTACTO** → pines byte-idénticos, **SIN re-pin** (como los últimos ~12
incrementos, incl. qty). **NO agregues check/estación nuevos si podés evitarlo.** `git diff snipeit/product.yml ≠ 0` es
ESPERADO; el sustrato + default/assets product.yml DEBEN quedar en 0. `proof_sha = sha256({station, sorted(check_name,
exit)})` — invariante a qué hace el código. Si SÍ agregás un check/estación → re-pin justificado + re-materializá el
chasis por defecto + re-pineá los 3 productos.

## 2. Maquinaria a REUTILIZAR (no la reinventes) — TODO en `codegen/scaffold_product.py` (anchors ~, verificá con grep)
- **`_load_blueprint`** (~L176): el guard de `ref` (`if t == "ref" and f.get("to") not in by`) hoy asume `to` string.
  Agregá la rama polimórfica (`to` lista) ANTES, fail-closed. Mantené el camino string intacto (byte-neutro).
- **`_migration_sql`** (~L1142): la rama `if f["type"] == "ref"` emite la FK. Bifurcá: polimórfico → 2 columnas sin FK.
- **`_row_json_fn`** (~L1178) / **`_mutation_fns`** (~L1206) / **`_seed_chain`** (~L3615): los que iteran `e["fields"]`
  y asumen 1 columna por campo. Introducí un helper que expanda un campo polimórfico a sus 2 columnas.
- **`_input_fields`** (~L1057) / **`_input_data_class`** / **`_codec_helpers`** (~L3711): el body. Decidí requerido-en-pivot
  vs opcional-en-body (wrinkle del 1er cut).
- **`_openapi_yaml`** (~L362, `_oapi_inline` ~L491): el schema del campo. Hoy `_oapi_inline` mapea por tipo; agregá el
  polimórfico (2 props o extensión).
- **`_app_server_kt`** (~L4218) + **`_access_control_check_py`** (~L4722, bloque `_QTY_PROOF`/`_OPERATIONS_PROOF` como
  modelo): el seed de la fila polimórfica + el proof del round-trip. Mirá cómo `_QTY_PROOF` (FSK-QTY-OPERATIONS) y
  `_COMPANY_SCOPE_PROOF` se inyectan OPT-IN (vacío → byte-idéntico) — copiá ese patrón EXACTO.
- **selección de entidad viva** (`_live_ownerless`/`_live_with_ref`/`_live_entities` ~L1068-1129): si montás el
  polimórfico sobre una entidad nueva, mirá cómo se elige qué entidad obtiene capa viva (qty PREFIERE la entidad con
  verbos; podés PREFERIR/incluir la entidad con un campo polimórfico de forma análoga).

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **EYEBALL SIN gradle ANTES de cada corrida lenta** (cazó el 100% de los problemas de byte-neutralidad en qty): un
  scratch python con `importlib` que carga `codegen/scaffold_product.py` HEAD vs working, llama `build_files(bp)` para
  default/assets/snipeit-SIN-el-eje, y **diffea** (deben quedar byte-idénticos). El de esta sesión está en
  `/tmp/eyeball_qty.py` — adaptalo (inyectá un campo polimórfico en una entidad de snipeit, dumpeá Migration/Repository/
  AppServer/openapi/proof, y verificá que default/assets/snipeit-sin-poly queden idénticos HEAD vs working). Snapshot
  HEAD: `git show HEAD:factories/full-stack-kotlin/codegen/scaffold_product.py > /tmp/scaffold_head.py`. **El eyeball
  encontró 2 leaks de byte-neutralidad en qty (un comentario unconditional + constantes de skeleton always-present)
  ANTES de gradle.** Patrón clave: lo nuevo va OPT-IN (vacío → byte-idéntico); NUNCA cambies un comentario/constante
  incondicionalmente.
- **Un sabotaje que debe morder a RUNTIME no puede introducir un hallazgo ESTÁTICO antes.** Degradá la LÓGICA/serialización,
  no la forma Kotlin. **ktlint/detekt MaxLineLength=160; LongMethod ≤ 60 (`@Suppress` opt-in — seedRows ya está a 63 con
  qty, sumar siembra polimórfica lo empuja más → @Suppress); CyclomaticComplexMethod ≤ 15 (`@Suppress` opt-in en
  dispatchers generados); ReturnCount ≤ 2; MagicNumber ignora -1/0/1/2 pero NO 3+ (usá `getOrNull(idx)`/constantes);
  NoUnusedImports + -Werror (imports condicionales sólo si el eje está activo; -Werror flagea "always true").** El
  `_jooq_chain`/`_kt_call` wrappean líneas largas (jOOQ es largo por diseño).
- **Un campo que mapea a >1 columna es NUEVO en este codegen.** TODO asume 1:1. El riesgo principal es olvidar un sitio
  que itera columnas (jOOQ "Unresolved reference" si una columna falta, o el round-trip si una no se serializa). El
  EYEBALL + el compile de s0 te lo cazan. (En qty, el compile de s0 cazó una tabla no-importada en AppServer — el mismo
  tipo de "olvidé un sitio".)
- **`meta verify` re-corre la estación ACTIVA con `build=False`** (no regenera). La activa tras un product-run es **s11**.
  Para un tooth en s9: **sabotear el codegen + `product-run`** (rojo en s9, las posteriores no corren) → revertir →
  `product-run` verde (restaura la activa verde, clave para que `stop_proof` no bloquee el cierre). El sabotaje de qty
  manifestó como "infra_up no alcanzó la infra en 120s" (infra_up REINTENTA un proof que falla determinista → timeout) —
  con SÓLO `access_control_live` rojo, hermanos verdes: el diente preciso.
- **`meta station` corre la META-línea (m00-m08), NO la línea FSK.** Para la línea FSK: `product-run`.
- **`proof_protect` puede DENEGAR tocar `.proof/` por shell** — el **Read tool SÍ** lee `.proof/logs/` (es un RESUMEN:
  nombre de check + exit; el `exit=0` es la señal autoritativa; las aserciones individuales del proof NO están en el log).
- **`ci --rederive` por producto**: `--product snipeit`/`--product assets` y SIN `--product` (la base/default). No existe
  `--product default`. Cada uno es un clon limpio (≈< 10 min) → corrélos UNO A UNO en foreground.
- **`dangerouslyDisableSandbox: true`** para gradle/docker. cwd SIEMPRE en la raíz. FOREGROUND, un producto a la vez.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento)
**creates/pivot de qty** (insertar AccessoryCheckout en el checkout — pide observabilidad del pivot no-servido),
**soft-deletes/Actionlog** (deferral 12), **EAV dinámico a runtime** (custom-fields Avenue B), **depreciación calculada**
(deferral 7, campo computado — ver §7), **ref forward REQUERIDO que cierre ciclo** (sub-eje de FSK-XENTITY-CYCLES),
**PUT/update de entidades ownerless**, **e2e Playwright / browser real**, **AppServer-en-contenedor con PG**.

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py` + quizá `factory.spec.yml`/`stations/*.yml` si la grama nueva necesita validación
  M0 o una estación) es nivel FÁBRICA → **este incremento** lo cubre (header ABIERTO).
- **La adopción** (`products/snipeit/product.yml`: declarar el campo polimórfico) es nivel PRODUCTO → abrí TAMBIÉN
  `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) + `feat(snipeit): …` (product.yml) + `docs(fsk): cerrar
  FSK-POLYMORPHIC-REFS (§Evidencia) + abrir <siguiente>`.
- **Probá POR BLOQUEO**: `product-run --product snipeit` PASS · diente de dos lados vivo · `ci --rederive --factory
  full-stack-kotlin` (base) + `--product assets` + `--product snipeit` == pin (los 3) · `meta check` 6/6 (`generality`
  verde) · `git diff src/+seed = 0` · default+assets product.yml = 0.

## 6. Criterio de cierre (demostrable, no narrable)
1. Una entidad declara un campo `ref` POLIMÓRFICO (`to: [E1, E2, …]`) en `products/snipeit/product.yml` y `product-run
   --product snipeit` **PASS** — el server vivo (s9) hace round-trip del cuerpo polimórfico: POST `{<campo>_type,
   <campo>_id}` → GET /{id} lo devuelve EXACTO, distinguiendo el target.
2. **Diente de DOS lados verificado VIVO**: saboteá la serialización del discriminador (`<campo>_type`) o el id → ROJO
   **sólo** en `access_control_live` (s9) → revertí → verde. Cubrí ≥2 targets distintos (el tipo cambia con el target).
3. `ci --rederive` (base + assets + snipeit) == pin. `meta check` 6/6 (`generality` verde). `git diff src/metafactory +
   seed = 0`. `git diff` default+assets product.yml = 0. (Si tocaste el set de checks → re-pin justificado.)
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md §3 / §4` actualizados. Abrí el SIGUIENTE con su handoff (§7).

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE
Si al investigar decidís que el ref polimórfico NO es el mejor próximo (es tu decisión con más contexto), la otra
candidata BOUNDED, framed honestamente:
- **Depreciación calculada (deferral 7)** [campo COMPUTADO]: en Snipe-IT el valor actual de un activo se computa
  straight-line desde la compra sobre `Depreciation.months`, con un piso. Es un **campo derivado de otros campos por una
  fórmula declarada** — un KIND de campo NUEVO (no almacenado, computado a runtime). **No necesita LLM** si lo framás como
  una columna derivada DETERMINISTA (la dependencia "keyless" anotada en SNIPEIT-DOMAIN era para custom-logic por LLM; una
  fórmula straight-line es aritmética pura). Wrinkle: pide un mini-vocabulario de fórmula (¿`computed: { formula: ... }`?)
  que no debe volverse domain-specific → mantenelo GENERAL (operadores aritméticos sobre campos del blueprint). Diente
  limpio: POST un activo con costo+meses → GET devuelve el valor computado correcto; degradar la fórmula → rojo. Es MÁS
  LIMPIO que el polimórfico (sin los wrinkles de 2-columnas/no-FK/owner) pero introduce una primitiva de fórmula.
- **Orden general del push** (`SNIPEIT-DOMAIN.md §4`): ~~CRUD~~ ✅ · ~~self-ref~~ ✅ · ~~ownership opcional~~ ✅ · ~~refs
  requeridos/seed transitivo~~ ✅ · ~~verbos checkout/checkin~~ ✅ · ~~custom-fields format~~ ✅ · ~~ciclos
  cross-entidad~~ ✅ · ~~company-scoping~~ ✅ · ~~cantidades/qty~~ ✅ · **(este) checkout polimórfico** · depreciación
  calculada · diferidos DUROS (creates/pivot · registry · Playwright · AppServer-en-contenedor con PG · EAV dinámico/Avenue B).

### ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
La fábrica FSK está madura; el dominio está mapeado (19 entidades, 12 deferrals). De esos 12, **10 cerrados** (CRUD,
self-ref, ownership-opcional/RTD, refs requeridos/seed transitivo, verbos checkout/checkin, custom-fields format, ciclos
cross-entidad, company-scoping, **qty/stock**, + toda la infra FSK-general). El **modelo de datos + reglas + control de
acceso COMPLETO + comportamiento con stock + app que corre** está entero. Lo que queda para el núcleo funcional:
**el ref polimórfico (este)** — y, opcional, el campo computado (depreciación). **Estimación honesta: el núcleo funcional
está a ~1 incremento más (este); la paridad de superficie completa (~226 rutas, soft-deletes, Kits, EAV) es trabajo mayor
pero son los flecos, no el corazón.** Tras el polimórfico, el MODELO DE DATOS faithful queda COMPLETO.
