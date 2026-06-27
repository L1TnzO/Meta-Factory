<!-- meta:doc sha=1acdc33cef8ce74e0c9f390cebef3a0e962000c0 updated=2026-06-27T01:41Z -->
# Incremento FSK-COMPUTED-FIELDS — campo COMPUTADO (un valor derivado por fórmula, no almacenado) · la dimensión de VALORES DERIVADOS

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-22T21:05Z · cerrado 2026-06-23T01:50Z — ver §Evidencia al final). Cerralo flippeando este header a CERRADO **o** con
> `meta increment close --factory full-stack-kotlin`. Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-POLYMORPHIC-REFS con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (y por qué es DECISIÓN tuya)

**El MODELO DE DATOS faithful está COMPLETO.** Cerrados, product-driven por Snipe-IT (11 deferrals): CRUD del grafo ·
self-ref · ownership opcional/RTD · refs requeridos transitivos · verbos checkout/checkin (workflow) · custom-fields
format · ciclos cross-entidad · company-scoping · qty/stock · **ref polimórfico** (el último eje de modelo-de-datos).
El acceso (auth→RBAC→ownership→company-scope) y el comportamiento-núcleo (workflow + stock) están vivos a runtime.

**Lo que falta: la dimensión de VALORES DERIVADOS.** En Snipe-IT el **valor actual** de un activo NO se almacena: se
COMPUTA straight-line desde la compra sobre `Depreciation.months` con un piso. Es un **campo derivado por una FÓRMULA
DETERMINISTA de otros campos** — un KIND de campo NUEVO (no almacenado, computado a runtime). Es el deferral 7.

**Por qué es un buen próximo:** cierra la dimensión de valores derivados (la contracara del modelo de datos: no "qué
guarda" sino "qué deriva"). Es **MÁS LIMPIO que el ref polimórfico** (sin los wrinkles de 2-columnas/no-FK/owner) pero
introduce **una primitiva de FÓRMULA** que NO debe volverse domain-specific. **No necesita s6/LLM**: una fórmula
aritmética es determinista (la dependencia "keyless" de SNIPEIT-DOMAIN era para custom-logic por LLM; el straight-line
es aritmética pura, I-3 = determinismo en la verificación). Tras él, lo que resta es **breadth pura** (las ~226 rutas,
soft-deletes/Actionlog, Kits, EAV dinámico/Avenue B) — los flecos, no el corazón.

**⚠️ ESTA ES TU DECISIÓN (con más contexto).** Si al investigar decidís que NO es el mejor próximo, alternativas
honestas en §7 (los sub-ejes del polimórfico que quedaron diferidos, o breadth). Tenés autoridad para reabrir — pero
leé los wrinkles ANTES.

### 0.1 LOS WRINKLES (este eje es más limpio que el poly, pero tiene los suyos)
1. **0 columnas, no 1 ni 2.** Un campo computado es el INVERSO del poly: el poly era 1 campo → 2 columnas; el computado
   es 1 campo → **0 columnas** (puramente derivado). NO va al `migration`, NO al `insert`, NO al `_input_fields` (no se
   postea), NO al seed. PERO **SÍ** se serializa en `rowJson` (computado de las columnas fuente) y SÍ se documenta en el
   contrato (read-only). Es la simetría con `_is_poly`: vas a querer un `_is_computed(f)` que lo EXCLUYE de los emisores
   por-columna (`_cols_of` debería filtrarlo) y lo INCLUYE en una pasada aparte de rowJson.
2. **El mini-vocabulario de FÓRMULA debe quedar GENERAL** (cero nombres de dominio — `generality` verde es el anti-overfit
   real). NO hardcodees "straight-line" ni "depreciation". La primitiva GENERAL: una expresión aritmética sobre **campos
   numéricos del blueprint** (de la MISMA entidad, 1er-cut) + literales, con un set CERRADO de operadores (`+ - * /`,
   quizá `min`/`max` para el piso). Avenida limpia: un **AST declarado** (`computed: { op: "-", args: [...] }`) —
   fail-closed por construcción (sólo campos declarados + operadores del set; M0/`_load_blueprint` RECHAZA un campo
   inexistente o un operador fuera del set, como el guard de `format` y de tipos). Un string `"a - b/c"` necesitaría un
   parser + sanitización (más superficie, más riesgo) → preferí el AST salvo que justifiques lo contrario.
3. **Dónde se COMPUTA.** Dos opciones: (a) a READ-time en el server (`rowJson` lee las columnas fuente y computa el
   valor, lo mete en el JSON) — el "no almacenado, computado a runtime" FAITHFUL, y el tooth es directo; (b) columna
   GENERATED de Postgres — acopla a la DB y complica jOOQ. **Recomendado: (a)**, computar en `_row_json_fn` (la MISMA
   función donde el poly serializa) tras las columnas. El tipo del resultado es numérico (number/int).
4. **División por cero / piso / redondeo.** Una fórmula con `/ months` revienta si `months==0`. Decidí el contrato
   (¿`months` requerido > 0? ¿guard que devuelve 0?). Mantenelo DETERMINISTA y documentado.
5. **Cross-entity (Asset→AssetModel→Depreciation.months) es OTRO eje.** En Snipe-IT los meses viven en `Depreciation`
   (entidad relacionada), no en `Asset`. Un 1er-cut SAME-ENTITY (la fórmula sólo referencia campos de la PROPIA entidad)
   es BOUNDED y honesto: dale a `Asset` un campo numérico propio (p.ej. `depreciation_months`) y computá sobre
   `purchase_cost`/`depreciation_months` del MISMO Asset. La derivación cross-entity (resolver el ref y leer la columna
   del target) se DIFIERE (documentá el gap, como se difirió todo lo cross-entity transitivo en su momento).

**Conclusión honesta**: el camino BOUNDED y limpio: **un campo computado SAME-ENTITY, aritmético (`+ - * /` + quizá
`min`/`max`), declarado como AST, computado en `rowJson`**, sobre la entidad CON DUEÑO viva (Asset) o la with_ref
(Accessory) — donde el round-trip del GET es observable. Diente: POST con los campos fuente → GET devuelve el valor
COMPUTADO correcto; degradar la fórmula (cambiar un operador / un operando) → el GET devuelve otro número → SÓLO s9 rojo.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥540000ms** (el sandbox mata gradle:
exit 144/1). **cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del hook
`stop_proof` al cerrar). Debe dar **PASS**, RTM snipeit **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **s7 PG 5435 · s9 puertos 18593-18595 + PG 5436/5437 · s11 18596** → NUNCA dos corridas en paralelo, NUNCA dejes un
`product-run`/`ci` en BACKGROUND al cerrar el turno (`stop_proof` re-corre la estación activa → colisión de puerto/PG).

**2) EL DISEÑO (GENERAL, cero nombres de dominio):**
- **Gramática del blueprint** (`_load_blueprint`): un campo `type: number`/`int` puede declarar `computed: <AST>`.
  Fail-closed (mismo patrón que `format`/workflow/poly): cada `field` referenciado ∈ los campos de la entidad y es
  numérico; cada `op` ∈ el set CERRADO; el campo NO entra a migration/insert/seed. Opt-in: sin `computed` el campo se
  comporta EXACTO (byte-neutro para todo lo previo).
- **`_is_computed(f)`** (hermano de `_is_poly`, ya en el codegen): True si el campo tiene `computed`. **`_cols_of(e)`**
  debería EXCLUIR los computados (no son columnas) — análogo a cómo el poly los EXPANDE. Mirá `_cols_of`,
  `_input_fields`/`_input_cols`, `_migration_sql`, `_seed_chain`: todos deben SALTEAR un campo computado.
- **`_row_json_fn`** (la fn donde el poly serializa sus 2 columnas): tras emitir las columnas reales, agregá una pasada
  que, por cada campo computado, emite `"<campo>":${<expr Kotlin derivada del AST sobre r[COL fuente]>}`. El AST → una
  expresión Kotlin aritmética (cuidá los tipos: jOOQ devuelve `Double?`/`Int?`; null-safe). **Acá vive el diente.**
- **El contrato** (`_openapi_yaml`/`_oapi_inline`): documentá el campo computado como propiedad read-only (`readOnly:
  true`, o una extensión `x-computed`). NO va en `required[]` (no se postea). Verificá que openapi-generator/typescript
  sigan parseando (route_check no mira el schema de campos, pero el model Kotlin/TS se genera).
- **El proof** (`_access_control_check_py` + un bloque OPT-IN como `_QTY_PROOF`/`_POLY_PROOF`): POST la entidad con los
  campos fuente (p.ej. `purchase_cost`, `depreciation_months`) → GET /{id} devuelve `<campo computado>` == el valor
  esperado (calculalo en Python con la MISMA fórmula). Diente: degradar la fórmula en el codegen → el GET devuelve otro
  número → SÓLO `access_control_live` rojo.

**EL DIENTE de dos lados** (igual que poly/qty): POST {fuentes} → GET devuelve el valor computado CORRECTO. Saboteá la
expresión Kotlin (cambiá un `-` por `+`, o un operando) → el GET devuelve otro número → **SÓLO** `access_control_live`
(s9) rojo, hermanos (`observability_live`+`frontend_consume_live`) + s0–s8 verdes → revertí → verde. ⚠️ **El sabotaje
debe degradar la LÓGICA/aritmética, no la forma Kotlin** (un cambio que rompe detekt/ktlint en s2 NO sirve — lección CARA).

---

## 1. ⚠️ RE-PIN — casi seguro NO hace falta
Si el cambio vive DENTRO de `access_control_live` (s9, ya pineado) — extendiendo el proof, sin agregar check/estación —
el **`proof_sha` queda INTACTO** → pines byte-idénticos, **SIN re-pin** (como los últimos ~13 incrementos, incl. poly y
qty). `git diff snipeit/product.yml ≠ 0` es ESPERADO; el sustrato + default/assets product.yml DEBEN quedar en 0. Si SÍ
agregás un check/estación → re-pin justificado + re-materializá el chasis por defecto + re-pineá los 3 productos.

## 2. Maquinaria a REUTILIZAR — TODO en `codegen/scaffold_product.py` (verificá los anchors con grep)
- **El patrón EXACTO del poly** (FSK-POLYMORPHIC-REFS, recién cerrado) es tu mejor modelo: `_is_poly`/`_poly_subfields`/
  `_cols_of`/`_input_cols` (helpers tras `_pascal`) + los guards `not _is_poly(f)` en selección/seed + los bloques
  OPT-IN del proof (`_WR_POLY_VALID`/`_POLY_PROOF`). Copiá la ESTRUCTURA: un predicado, un filtro en `_cols_of`, una
  pasada en `_row_json_fn`, un guard de `_load_blueprint`, un bloque OPT-IN en el proof. Vacío sin `computed` → byte-idéntico.
- **`_load_blueprint`**: los guards de `format`/workflow/poly son la plantilla de validación fail-closed.
- **`_row_json_fn`**: el poly serializa sus 2 columnas acá; el computado AGREGA su valor derivado acá.
- **`_oapi_inline`/`_openapi_yaml`**: cómo el poly/format/enum documentan props + extensiones.
- **`_access_control_check_py`** + los bloques `_QTY_PROOF`/`_POLY_PROOF`: copiá el patrón OPT-IN (vacío → byte-idéntico;
  el bloque corre al final del try, reusa base/seed/_send/_body/_expect_value; el DATA nuevo va DENTRO del bloque
  substituido, NUNCA en el SKELETON — una línea al skeleton cae en TODOS los productos → rompe byte-neutralidad).

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **EYEBALL SIN gradle ANTES de cada corrida lenta** (cazó el 100% de los problemas de byte-neutralidad en qty Y poly):
  un scratch python con `importlib` que carga el scaffold HEAD vs working, llama `build_files(bp)` para default/assets/
  snipeit-SIN-el-eje, y **diffea** (deben quedar byte-idénticos). El de esta sesión: `/tmp/eyeball_poly.py` —
  adaptalo (inyectá un campo computado, dumpeá Migration/Repository/openapi/proof, verificá default/assets/snipeit-sin-
  computed idénticos HEAD vs working). Snapshot HEAD: `git show HEAD:factories/full-stack-kotlin/codegen/scaffold_product.py
  > /tmp/scaffold_head.py`. Patrón clave: lo nuevo va OPT-IN (vacío → byte-idéntico); NUNCA cambies un comentario/
  constante incondicionalmente.
- **Un sabotaje que debe morder a RUNTIME no puede introducir un hallazgo ESTÁTICO antes.** Degradá la aritmética, no la
  forma Kotlin. **ktlint/detekt MaxLineLength=160; LongMethod ≤ 60 (`@Suppress` opt-in); CyclomaticComplexMethod ≤ 15;
  ReturnCount ≤ 2; MagicNumber ignora -1/0/1/2 pero NO 3+ (usá constantes/`getOrNull(idx)`); NoUnusedImports + -Werror.**
  **CUIDADO con los tipos numéricos**: jOOQ devuelve `Double?`/`Int?`; una fórmula que mezcla Int y Double necesita
  conversiones explícitas (`-Werror` flagea); null-safe (`?: 0.0`).
- **`meta verify` re-corre la estación ACTIVA con `build=False`** (no regenera). La activa tras un product-run es **s11**.
  Para un tooth en s9: **sabotear el codegen + `product-run`** (rojo en s9, las posteriores no corren) → revertir →
  `product-run` verde (restaura la activa verde, clave para que `stop_proof` no bloquee el cierre). El sabotaje preciso
  se manifiesta como "infra_up no alcanzó la infra en 120s" (infra_up REINTENTA el proof determinista-fallido → timeout)
  con SÓLO `access_control_live` rojo y los hermanos verdes.
- **`meta station` corre la META-línea (m00-m08), NO la línea FSK.** Para la línea FSK: `product-run`.
- **`proof_protect` puede DENEGAR tocar `.proof/` por shell** — el **Read tool SÍ** lee `.proof/logs/` (RESUMEN: check +
  exit; el `exit=0` es la señal autoritativa).
- **`ci --rederive` por producto**: `--product snipeit`/`--product assets` y SIN `--product` (la base/default). NO existe
  `--product default`. Cada uno es un clon limpio (≈< 10 min) → corrélos UNO A UNO en foreground.
- **`dangerouslyDisableSandbox: true`** para gradle/docker. cwd SIEMPRE en la raíz. FOREGROUND, un producto a la vez.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento)
**creates/pivot de qty** (insertar AccessoryCheckout — pide observabilidad del pivot no-servido), **`assigns`/owner
POLIMÓRFICO** (sub-ejes diferidos de FSK-POLYMORPHIC-REFS: setear 2 columnas desde el cuerpo del verbo · no volver
polimórfico el `owned_by`), **derivación CROSS-ENTITY del campo computado** (resolver un ref y leer la columna del
target), **soft-deletes/Actionlog** (deferral 12), **EAV dinámico a runtime** (custom-fields Avenue B), **ref forward
REQUERIDO que cierre ciclo** (sub-eje de FSK-XENTITY-CYCLES), **PUT/update de entidades ownerless**, **e2e Playwright /
browser real**, **AppServer-en-contenedor con PG**.

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py` + quizá `factory.spec.yml`/`stations/*.yml` si la grama nueva necesita validación
  M0) es nivel FÁBRICA → **este incremento** lo cubre (header ABIERTO).
- **La adopción** (`products/snipeit/product.yml`: declarar el campo computado en Asset) es nivel PRODUCTO → abrí TAMBIÉN
  `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) + `feat(snipeit): …` (product.yml) + `docs(fsk): cerrar
  FSK-COMPUTED-FIELDS (§Evidencia) + abrir <siguiente>`.
- **Probá POR BLOQUEO**: EYEBALL byte-neutro · `product-run --product snipeit` PASS · diente de dos lados vivo (sólo s9) ·
  `ci --rederive` (base + assets + snipeit) == pin (los 3) · `meta check` 6/6 (`generality` verde) · `git diff
  src/metafactory + seed = 0` · default+assets product.yml = 0.

## 6. Criterio de cierre (demostrable, no narrable)
1. Una entidad declara un campo COMPUTADO (`computed: <AST>` sobre campos numéricos propios) en `products/snipeit/
   product.yml` y `product-run --product snipeit` **PASS** — el server vivo (s9) computa el valor a READ-time: POST
   {fuentes} → GET /{id} devuelve `<campo computado>` == el valor esperado (DETERMINISTA, sin LLM).
2. **Diente de DOS lados verificado VIVO**: saboteá la fórmula (operador/operando) → ROJO **sólo** en
   `access_control_live` (s9) → revertí → verde.
3. EYEBALL byte-neutro (default/assets + snipeit-sin-computed) · `ci --rederive` (base + assets + snipeit) == pin ·
   `meta check` 6/6 (`generality` verde) · `git diff src/metafactory + seed = 0` · default+assets product.yml = 0.
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md §3 deferral 7 / §4` actualizados. Abrí el SIGUIENTE con su handoff (§7).

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE
Si al investigar decidís que el campo computado NO es el mejor próximo (es tu decisión con más contexto), las otras
candidatas BOUNDED, framed honestamente:
- **El `assigns` POLIMÓRFICO del verbo** (sub-eje diferido de FSK-POLYMORPHIC-REFS): hoy un verbo de workflow con
  `assigns: <ref único>` setea UNA columna al id del cuerpo; un assigns polimórfico setea las DOS columnas
  (`<campo>_type`+`<campo>_id`) del cuerpo del verbo. Toca la gramática del `assigns` + `_operation_repo_fns` +
  `_operations_handlers` + el proof. Completa el checkout polimórfico FAITHFUL (hoy la primitiva está, pero el verbo no la
  asigna). Más acotado que el computado, pero menos "dimensión nueva".
- **Breadth pura** (si decidís que el núcleo funcional YA está): soft-deletes (`deleted_at` + filtro de lectura, otro
  read-path) · las ~226 rutas · Kits. Son los flecos.
- **Orden general del push** (`SNIPEIT-DOMAIN.md §4`): todo el MODELO DE DATOS + acceso + comportamiento-núcleo ✅. Queda
  **valores derivados (este)** · `assigns` polimórfico · breadth.

### ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El núcleo funcional está ESENCIALMENTE COMPLETO**: modelo de datos faithful (incl. refs polimórficos) + reglas +
control de acceso (auth→RBAC→ownership→company-scope) + comportamiento (workflow + stock) + app que CORRE (CRUD vivo +
frontend que consume/renderiza + deploy). El campo computado (este) cierra los VALORES DERIVADOS; tras él, la paridad de
superficie completa (~226 rutas, soft-deletes, Kits, EAV dinámico) es trabajo de BREADTH — los flecos, no el corazón.

---

## Evidencia (cierre 2026-06-23T01:50Z)

**QUÉ se construyó** (todo en `codegen/scaffold_product.py`, FÁBRICA — GENERAL, cero nombres de dominio):
- **Gramática**: un campo `int`/`number` con `computed: <AST>`. AST = número | nombre-de-campo | `{op, args}`.
  `_validate_computed_ast` fail-closed en `_load_blueprint`: `op` ∈ set CERRADO `{+ - * / min max}`; operandos = campos
  numéricos NO-computados de la entidad o literales; `-`/`/` BINARIOS. (No el `owned_by`; sólo int/number.)
- **Helpers** (hermanos de `_is_poly`): `_is_computed` · `_computed_srcs` (campos fuente del AST) · `_ast_uses_div` ·
  `_computed_kt` (AST → expresión Kotlin Double).
- **0 columnas**: `_cols_of` y `_input_fields` EXCLUYEN el computado → automáticamente fuera de migration/insert/seed/
  contrato-`required[]`/input/parser/data-class/tests/UI (todos iteran esas fuentes). No es columna, no se postea.
- **Cómputo a READ-time** en `_row_json_fn`: tras el SELECT, extrae cada fuente a un `val Double` null-safe — **un
  `number` ya es `Double?`** → `r[COL] ?: 0.0` (un `.toDouble()` sería REDUNDANTE → `-Werror`, **lección cara**: s0
  rojo en el 1er intento); un `int` es `Int?` → `r[COL]?.toDouble() ?: 0.0`. La expresión del AST: `/` → helper
  `safeDiv(a,b)=if(b==0.0)0.0 else a/b` (miembro del Repository, emitido SÓLO si algún AST vivo usa `/`); `min`/`max`
  → fold a `minOf`/`maxOf`. El valor se serializa como un campo más (number → crudo, **sin llaves** `$vname` =
  identificador simple, ktlint StringTemplate — **2ª lección cara**: `${...}` redundante → s2 rojo).
- **Contrato** read-only (`_oapi_inline`: `readOnly: true`+`x-computed`; tras las columnas en `_openapi_yaml`).
  openapi-generator/typescript lo generan opcional/nullable → ctores con args nombrados no se rompen.
- **Proof** OPT-IN `_COMPUTED_PROOF` dentro de `access_control_live` (s9): re-deriva la MISMA fórmula en Python
  (`_ceval`, IEEE 754 double idéntico al Kotlin → comparación **EXACTA**, el string round-trippea al mismo double) y
  cruza `GET[campo]` contra ella. El DATA (los AST) va DENTRO del bloque substituido (`%COMPUTED_DATA%`), nunca en el
  SKELETON → byte-neutro sin computado.

**Adopción** (`products/snipeit/product.yml`, PRODUCTO, incremento `COMPUTED-FIELDS-ADOPT`): `Asset.current_value =
max(purchase_cost − purchase_cost/depreciation_months, 0)` — 1er-cut SAME-ENTITY (`depreciation_months` propio; cross-
entity + time-elapsed DIFERIDOS). Fuentes hechas REQUERIDAS (el server inserta sólo required → el valor es observable).

**Verde por BLOQUEO**:
- EYEBALL byte-neutro (HEAD vs working): default **68/68** · assets **68/68** · snipeit-sin-computed **70/70**.
- Validación fail-closed probada (positivo + 4 negativos: op `pow` · ref no-numérico · `/` 3-args · bool operando).
- `product-run --product snipeit` **PASS** (s0→s11) · RTM snipeit **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
- **Diente de DOS lados VIVO** (s9): saboteé `_computed_kt` `-`→`+` → `product-run` FAIL, **SÓLO `access_control_live`
  rojo** (hermanos `observability_live`+`frontend_consume_live` verdes; "proof no alcanzó la infra en 120s" = la falla
  determinista reintentada) → revertí → `product-run` PASS.
- `ci --rederive`: snipeit **11/11** · base **12/12** · assets **11/11** == pin (**`proof_sha` intacto → SIN re-pin**).
- `meta check` **6/6** (`generality` verde) · `git diff src/metafactory + seed = 0` · default+assets `product.yml` = 0.

**Honesto (diferido)**: derivación CROSS-ENTITY (resolver un ref y leer la columna del target) · time-elapsed del
straight-line completo · fórmulas que pasan 160 columnas (wrapping diferido — `_row_json_fn` lanza SystemExit honesto) ·
literales ≥3 en una fórmula (detekt MagicNumber los mordería — el set actual usa sólo el piso `0`).

**Siguiente** (determinado con MÁS contexto): **FSK-SOFT-DELETES** (borrado lógico / trash + restore, deferral 12) —
el último eje behavioral genuino antes de la breadth pura. Handoff autocontenido: `docs/work/FSK-SOFT-DELETES-INCREMENT.md`.
