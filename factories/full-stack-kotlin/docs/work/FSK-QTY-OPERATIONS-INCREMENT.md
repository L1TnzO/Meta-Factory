<!-- meta:doc sha=30511e6f99e30a6ad7d14ed7819a17a0e8eff102 updated=2026-06-27T01:41Z -->
# Incremento FSK-QTY-OPERATIONS — cantidades / stock (checkout que decrementa qty) + operaciones en entidades SIN dueño

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-22T18:39Z · cerrado 2026-06-22T19:46Z). Evidencia abajo (§Evidencia). Editar
> `factories/full-stack-kotlin/**` no-`.md` (codegen/spec/stations) exige un incremento abierto — el
> `increment_guard` elige el lifecycle por la RUTA editada.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-COMPANY-SCOPING con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (el 1er eje de COMPORTAMIENTO con STOCK — y por qué es DECISIÓN tuya)

**FSK está MUY MADURO y el modelo de ACCESO está COMPLETO.** Cerrados ya, product-driven por Snipe-IT: CRUD del
grafo entero · self-ref · ownership opcional/RTD · refs requeridos transitivos · **verbos checkout/checkin**
(comportamiento, FSK-DOMAIN-OPS) · **custom-fields format** (validación) · **ciclos cross-entidad** (schema/seed) ·
**company-scoping** (ABAC/multi-tenancy, el 1er filtrado de lectura). La cadena de acceso completa (auth → RBAC →
ownership → company-scope) está VIVA a runtime (s9, AppServer vs PG).

**Lo que FALTA del comportamiento real de Snipe-IT: las CANTIDADES.** En Snipe-IT, Accessory/Consumable/Component
tienen `qty` (stock). El checkout de un accesorio/consumible a un usuario **decrementa el stock disponible** (o crea
una fila de asignación contra la cual se computa la disponibilidad) y, si no hay stock, **falla** (out-of-stock).
Esto es el sub-eje diferido de FSK-DOMAIN-OPS (`SNIPEIT-DOMAIN.md §4 #9`).

**Por qué es un buen próximo:** es el último gran eje de COMPORTAMIENTO genuinamente product-driven y faithful.
FSK-DOMAIN-OPS cubrió las transiciones de WORKFLOW (checkout/checkin de Asset = transición de estado `status`); las
cantidades son un KIND de operación DISTINTO (un decremento aritmético con guard de stock, no una transición de
máquina de estado).

**⚠️ ESTA ES TU DECISIÓN (con más contexto).** La sesión que cerró company-scoping NO lo eligió antes por su
**WRINKLE** (ver §0.1). Si al investigar decidís que NO es el mejor próximo, las alternativas honestas están en §7.
Tenés autoridad para reabrir esa decisión — pero leé el wrinkle ANTES.

### 0.1 EL WRINKLE (leélo antes de comprometerte — son ~2 sub-ejes, no claramente bounded)
1. **El server vivo hoy monta `operations` SÓLO en la entidad CON DUEÑO** (Asset). Las entidades con qty
   (Accessory/Consumable) son **SIN dueño** (las sirve `_ownerless_handlers`, RBAC-only). Para ejercer qty VIVO a
   runtime (el diente honesto vive en s9) hay que **montar verbos en una entidad ownerless** — un sub-eje en sí
   ("operations on ownerless entities"). `_operations_handlers`/`_operations_dispatch` asumen `owned` + `modifyVerdict`
   (que compone ownership); una ownerless gatea sólo por RBAC (`RoleGuard.authorize(token, writeRoles<E>())`).
2. **`operations` hoy EXIGE `owned_by`** (`_load_blueprint` ~L330: "el verbo decide acceso por ownership —
   fail-closed") y EXIGE que el `field` sea un **enum con `transitions`** (un workflow). El qty-checkout NO tiene
   workflow: es un decremento de un campo `int` + (opcional) la inserción de una fila pivot. Es un **KIND de
   operación NUEVO** → la gramática de `operations` necesita una rama nueva (p.ej. `decrements: <campo int>` +
   `creates: <entidad pivot>` con su FK), distinta de la rama workflow (`field`/`from`/`to`/`assigns`/`clears`).

**Conclusión honesta**: son DOS cosas (verbos-en-ownerless + operación-de-KIND-qty). Está bien — framealo como un
incremento con dos partes claras, o **splitealo** (1º "operations on ownerless" usando una entidad ownerless con
workflow… pero ⚠️ snipeit NO tiene una ownerless con workflow → ese split NO es product-driven; por eso el camino
natural es hacer ambos juntos, driven por Accessory/Consumable). Decidí vos.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥540000ms** (el sandbox mata
gradle: exit 144). **cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del
hook `stop_proof` al cerrar; restaurá con `cd /home/enzo/University/Integración/APP/Meta_Factory`).
Debe dar **PASS**, RTM snipeit **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **s7 PG 5435 · s9 puertos 18593-18595 + PG 5436/5437 · s11 18596** → NUNCA dos corridas en paralelo, NUNCA
dejes un `product-run`/`ci` en BACKGROUND al cerrar el turno (`stop_proof` re-corre la estación activa → colisión).

**2) EL DISEÑO (resolvelo GENERAL, cero nombres de dominio — `generality` verde es el anti-overfit real):**
- **Gramática del blueprint** (en `_load_blueprint`, donde hoy se valida `operations` ~L323-340): introducí un
  KIND de operación que decrementa stock. Avenida recomendada: una operación con `decrements: <campo int>` (en vez
  de `field`/`from`/`to`) + opcionalmente `creates: <entidad>` (la fila pivot de asignación, p.ej.
  AccessoryCheckout). Fail-closed: `decrements` ∈ los campos `int` de la entidad; `creates` ∈ entidades; **el KIND
  workflow y el KIND qty son MUTUAMENTE EXCLUYENTES** por operación. Y RELAJÁ la exigencia de `owned_by` para el
  KIND qty (el acceso es RBAC-only en una ownerless) — pero seguí fail-closed (qty exige `write_roles`).
- **El repo** (`_operation_repo_fns` ~L1263, hermano de `_mutation_fns`): para el KIND qty, un UPDATE
  condicional `SET qty = qty - 1 WHERE id = ? AND qty > 0` (devuelve filas afectadas: 0 → out-of-stock) + (si
  `creates`) el INSERT del pivot. Type-bound a jOOQ (columna inexistente → no compila, DES-12).
- **El server vivo, s9** (`_operations_handlers` ~L4096 + `_operations_dispatch` ~L4170 + montaje en
  `_app_server_kt` ~L4218 + `_ownerless_handlers` ~L3924): el handler del verbo qty gatea por RBAC (ownerless) →
  decrementa con guard → out-of-stock → **409**; OK → 200 + (si creates) la fila pivot. **Montar el dispatch del
  verbo en el bloque ownerless** (hoy `_ownerless_handlers` no rutea verbos — ahí está el sub-eje #1 del wrinkle).
- **El contrato** (`_openapi_yaml` ~L335, donde se emiten las rutas de `operations` ~L411): `POST
  /<plural>/{id}/<verbo>` con su `x-required-roles` + `409` (out-of-stock). route_check (topology/auth/rbac) lo
  cruza GRATIS (como FSK-DOMAIN-OPS).

**EL DIENTE de dos lados** (criterio §6.2): el server siembra una entidad ownerless con qty + ≥1 fila con stock.
**Verbo qty**: checkout con stock > 0 → **200** + qty decrementado (GET /{id} lo confirma) + (si creates) la fila
pivot existe; checkout con stock == 0 → **409** (out-of-stock, fail-closed). RBAC: rol prohibido → **403** sin
decrementar. **El tooth NATURAL vive en s9** (`access_control_live`, como FSK-DOMAIN-OPS): saboteá el guard de
stock (`qty > 0` → siempre) o el decremento → el 409 desaparece / el qty no baja → **SÓLO** `access_control_live`
rojo, hermanos s9 verdes → revertí → verde. ⚠️ **El sabotaje que muerde a RUNTIME NO puede introducir un hallazgo
ESTÁTICO** (detekt/ktlint en s2) que muerda antes — degradá la LÓGICA (quitar el `AND qty > 0`), no la forma
Kotlin. Lección CARA, §3.

---

## 1. ⚠️ RE-PIN — ¿hace falta?
Si el cambio vive DENTRO del check existente `access_control_live` (s9, ya pineado) — extendiendo el proof, no
agregando check/estación — el **`proof_sha` queda INTACTO** → pines byte-idénticos, **SIN re-pin** (como los
últimos ~11 incrementos). **NO agregues check/estación nuevos si podés evitarlo.** `git diff snipeit/product.yml ≠
0` es ESPERADO; el sustrato + default/assets product.yml DEBEN quedar en 0. `proof_sha = sha256({station,
sorted(check_name, exit)})` — invariante a qué hace el código. Si SÍ agregás un check/estación → re-pin
justificado, y **re-materializá el chasis por defecto** + re-pineá los 3 productos.

## 2. Maquinaria a REUTILIZAR (no la reinventes) — TODO en `codegen/scaffold_product.py` (anchors ~, verificá)
- **`_load_blueprint`** (~L176, validación de `operations` ~L323-340) — agregá el KIND qty con su validación
  fail-closed; relajá el `owned_by` SÓLO para el KIND qty. Mantené el patrón (excluyente con workflow, refs/ints
  existen).
- **`_operation_repo_fns`** (~L1263) — las queries jOOQ del verbo. Agregá el UPDATE condicional de stock + el
  INSERT del pivot (si `creates`).
- **`_operations_handlers`** (~L4096) / **`_operations_dispatch`** (~L4170) — los handlers + ramas del verbo. Hoy
  asumen `owned`/`modifyVerdict`; generalizá para una entidad ownerless (gate RBAC-only) + el KIND qty (guard de
  stock → 409).
- **`_ownerless_handlers`** (~L3924) — el bloque CRUD RBAC-only de una entidad sin dueño; ACÁ hay que cablear el
  dispatch de los verbos qty (hoy NO rutea verbos — sub-eje #1 del wrinkle).
- **`_app_server_kt`** (~L4218) — el ensamblado del server; mirá cómo monta `operations` para el owned
  (`ops_handlers`/`ops_dispatch`/imports del workflow/`need_conflict`) e imitá el seam para la ownerless con qty.
- **`_live_ownerless`** (~L1068) / **`_live_with_ref`** (~L1088) / **`_live_entities`** (~L1120) — la selección de
  qué entidades obtienen capa viva. ⚠️ **Accessory/Consumable tienen `category_id` REQUERIDO → caen en
  `_live_with_ref`** (no en `_live_ownerless`, que exige sólo-escalares; hoy en snipeit `_live_with_ref` da
  **AssetModel**, la 1ª con ref requerido sembrable). Pensá si el verbo qty se monta sobre la entidad `with_ref` o
  si generalizás la selección/sembrás otra. **Hacé un EYEBALL para ver qué entidad termina sirviendo los verbos.**
- **`_openapi_yaml`** (~L335, rutas de operations ~L411) — agregá `409` a la ruta del verbo qty (out-of-stock).
- **`_access_control_check_py`** (~L4640, bloque `_OPERATIONS_PROOF`) — el proof e2e; agregá el bloque del diente
  qty (200+decremento / 0-stock→409 / rol→403), análogo a `_OPERATIONS_PROOF`/`_COMPANY_SCOPE_PROOF`.

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **EYEBALL SIN gradle ANTES de cada corrida lenta**: scratch python con `importlib` que carga `codegen/
  scaffold_product.py` HEAD vs working, `build_files(bp)` para default/assets, y **diffea** (deben quedar 68/68
  byte-idénticos). El scratch de esta sesión está en `/tmp/eyeball_cs.py` (HEAD vs working para default/assets +
  inyección de un campo en snipeit + dump + AST-check del proof). Adaptalo (inyectá una operación qty en una
  entidad de snipeit y dumpeá AppServer/Repository/proof). Snapshot HEAD:
  `git show HEAD:factories/full-stack-kotlin/codegen/scaffold_product.py > /tmp/scaffold_head.py`. **Esto cazó el
  100% de los problemas de byte-neutralidad ANTES de gradle.**
- **Un sabotaje que debe morder a RUNTIME no puede introducir un hallazgo ESTÁTICO antes.** Degradá la LÓGICA
  (quitar el `AND qty > 0` del UPDATE, o el guard de 409), no la forma Kotlin. **ktlint MaxLineLength=160
  (MAX_LINE_LENGTH); usá `_kt_call`/`_jooq_chain` para wrappear queries largas; detekt MagicNumber ignora
  -1/0/1/2 pero NO el 3+ (usá `getOrNull(idx)`/constantes); ReturnCount ≤ 2 (`return when`);
  CyclomaticComplexMethod ≤ 15 (`@Suppress` opt-in en un dispatcher generado); LongMethod ≤ 60 (seedRows ya está
  a 56 con company-scoping — sumar siembra de stock puede cruzarlo → @Suppress opt-in o factorizá); NoUnusedImports
  + -Werror (imports condicionales sólo si el eje está activo; -Werror flagea condiciones "always true" → evitá
  redundancias, usá destructuring/smart-cast como en `listAll`).**
- **El handoff puede SOBRE- y SUB-estimar los sitios.** Verificá qué generadores YA manejan el caso ANTES de
  tocarlos. El montaje de verbos en ownerless es el sitio que más fácil se sub-estima.
- **`meta verify` re-corre la estación ACTIVA con `build=False`** (no regenera). La activa tras un product-run es
  **s11**. Para un tooth en s9: **sabotear el codegen + `product-run`** (rojo en s9, las posteriores no corren) →
  revertir → `product-run` verde (restaura la activa verde, clave para que `stop_proof` no bloquee el cierre).
- **`meta station` corre la META-línea (m00-m08), NO la línea FSK.** Para la línea FSK: `product-run`.
- **`proof_protect` DENIEGA tocar `.proof/` por shell** (incluso `sed`/`grep`/`cat` del log) — pero el **Read tool
  SÍ** lee `.proof/logs/` (es un RESUMEN: nombre de check + exit; el `exit=0` es la señal autoritativa).
- **`ci --rederive` por producto**: `--product snipeit`/`--product assets` (instancias) y SIN `--product` (la línea
  base/default). No existe `--product default`. Cada uno es un clon limpio (≈< 10 min) → corrélos UNO A UNO en
  foreground.
- **`dangerouslyDisableSandbox: true`** para gradle/docker. cwd SIEMPRE en la raíz. FOREGROUND, un producto a la vez.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento)
Refs **polimórficos** (deferral 2: checkout `assigned_to`→User|Location|Asset — pide una primitiva de ref NUEVA, un
ref a >1 entidad; toca model/migration/seed/contrato), **soft-deletes/Actionlog** (deferral 12), **EAV dinámico a
runtime** (custom-fields Avenue B), **depreciación calculada** (deferral 7, campo computado, necesita s6 keyless o
columna derivada), **ref forward REQUERIDO que cierre ciclo** (sub-eje diferido de FSK-XENTITY-CYCLES).

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py` + quizá `factory.spec.yml`/`stations/*.yml` si la grama nueva necesita
  validación M0 o una estación) es nivel FÁBRICA → **este incremento** lo cubre (header ABIERTO).
- **La adopción** (`products/snipeit/product.yml`: declarar la operación qty en Accessory/Consumable) es nivel
  PRODUCTO → abrí TAMBIÉN `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar
  `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) + `feat(snipeit): …` (product.yml) + `docs(fsk):
  cerrar FSK-QTY-OPERATIONS (§Evidencia) + abrir <siguiente>`.
- **Probá POR BLOQUEO**: `product-run --product snipeit` PASS · diente de dos lados vivo · `ci --rederive --factory
  full-stack-kotlin` (base) + `--product assets` + `--product snipeit` == pin (los 3) · `meta check` 6/6
  (`generality` verde) · `git diff src/+seed = 0` · default+assets product.yml = 0.

## 6. Criterio de cierre (demostrable, no narrable)
1. Una entidad (Accessory/Consumable) declara una operación qty en `products/snipeit/product.yml` y `product-run
   --product snipeit` **PASS** — el server vivo (s9) ejerce el checkout que DECREMENTA stock + crea la asignación,
   bajo RBAC, con out-of-stock → 409 a runtime.
2. **Diente de DOS lados verificado VIVO**: saboteá el guard de stock o el decremento → ROJO **sólo** en
   `access_control_live` (s9) → revertí → verde. Cubrí: stock>0 → 200+decremento · stock==0 → 409 · rol→403.
3. `ci --rederive` (base + assets + snipeit) == pin. `meta check` 6/6 (`generality` verde). `git diff src/metafactory
   + seed = 0`. `git diff` default+assets product.yml = 0. (Si tocaste el set de checks → re-pin justificado.)
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md §3 / §4` actualizados. Abrí el SIGUIENTE con su handoff (§7).

## 7. Qué viene DESPUÉS (para que sepas dónde estás parado) — y las ALTERNATIVAS a ESTE
Si al investigar decidís que qty NO es el mejor próximo (es tu decisión con más contexto), las otras candidatas
BOUNDED, product-driven, framed honestamente:
- **Checkout polimórfico (deferral 2)** [una primitiva NUEVA de ref]: `assigned_to` → User|Location|Asset (unión de
  targets). Más grande: toca el modelo de tipos (un ref que apunta a >1 entidad), el migration (¿columna `*_type` +
  `*_id`?), el seed, el contrato. No es opt-in trivial. Hermano conceptual de los enums pero sobre refs. Es el
  ÚLTIMO eje de MODELO-DE-DATOS faithful que queda.
- **Depreciación calculada (deferral 7)** [campo computado]: necesita s6 (lógica de dominio por LLM, hoy keyless) o
  una primitiva de columna derivada. Diferida por la dependencia keyless.
- **Orden general del push** (`SNIPEIT-DOMAIN.md §4`): ~~CRUD~~ ✅ · ~~self-ref~~ ✅ · ~~ownership opcional~~ ✅ ·
  ~~refs requeridos/seed transitivo~~ ✅ · ~~verbos checkout/checkin~~ ✅ · ~~custom-fields format~~ ✅ · ~~ciclos
  cross-entidad~~ ✅ · ~~company-scoping~~ ✅ · **(este) cantidades/qty** · checkout polimórfico · diferidos DUROS
  (registry · Playwright · AppServer-en-contenedor con PG · EAV dinámico/Avenue B · depreciación calculada).

### ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
La fábrica FSK está madura; el dominio está mapeado (19 entidades, 12 deferrals). De esos 12, **9 cerrados** (CRUD,
self-ref, ownership-opcional/RTD, refs requeridos/seed transitivo, verbos checkout/checkin, custom-fields format,
ciclos cross-entidad, company-scoping, + toda la infra FSK-general). El **modelo de datos + reglas + control de
acceso COMPLETO + app que corre** está entero. Lo que queda para el núcleo funcional: **qty (este)** + **checkout
polimórfico** (2 ejes ~1 sesión c/u). Después, breadth/flecos: las ~226 rutas, soft-deletes/Actionlog, Kits,
CheckoutRequest, EAV dinámico, depreciación. **Estimación honesta: el núcleo funcional está a ~1-2 incrementos más;
la paridad de superficie completa es trabajo mayor pero son los flecos, no el corazón.**

---

## §Evidencia (CERRADO 2026-06-22T19:46Z)

**Qué se construyó** — el 1er eje de COMPORTAMIENTO con STOCK + el 1er montaje de VERBOS sobre una entidad SIN
dueño. Nuevo KIND de operación (`decrements: <campo int>`, detectado por la presencia de `decrements`, EXCLUYENTE
con el KIND workflow `field`/`from`/`to`/`assigns`/`clears`) que decrementa el stock con guard out-of-stock,
RBAC-only, montado sobre la entidad ownerless/with_ref. **Resueltos los 2 sub-ejes del wrinkle** (verbos-en-ownerless
+ KIND qty) en un solo incremento, driven por Accessory (con `category_id` requerido → with_ref).

**Maquinaria (toda en `codegen/scaffold_product.py`, FÁBRICA, GENERAL — cero nombres de dominio):**
- `_load_blueprint`: detecta el KIND qty por `decrements`; valida `decrements`∈int, `write_roles` presente, exclusión
  con las claves de workflow; relaja `owned_by` (RBAC-only). El KIND workflow movió su exigencia de `owned_by` a su rama.
- `_operation_repo_fns`: para el KIND qty, `ctx.update(<T>).set(<QTY>, <QTY>.minus(1)).where(ID.eq(id).and(<QTY>.gt(0))).execute()`
  (0 filas afectadas ⟺ sin stock o fila inexistente). El guard `> 0` ES el diente.
- `_ownerless_handlers(e, catch_fk, ops)`: nuevo param `ops` → handler `POST /<plural>/{id}/<verbo>` (rol→403 ·
  sin stock→409 · OK→200) + ramas del dispatch (1er ruteo de verbos sobre ownerless) + `@Suppress("CyclomaticComplexMethod")` opt-in.
- `_live_with_ref`: PREFIERE una candidata con verbos qty (`_qty_ops`) → snipeit sirve Accessory (antes AssetModel;
  el eje with_ref/FK se ejerce idéntico). Byte-neutro sin qty.
- `_app_server_kt`: filtra los verbos de workflow del owned; siembra una fila de stock (`qtyId`) con su FK requerida
  (reusa los ref targets); importa su tabla; `@Suppress("LongMethod")` opt-in en seedRows (la siembra → 63 líneas).
- `_openapi_yaml`/`RouteTable` ya emitían la ruta del verbo (con 409) para cualquier entidad → route_check la cruza gratis.
- proof e2e (`_QTY_PROOF`): rol prohibido→403 sin decremento · checkout hasta agotar→200+decremento (GET confirma) · sin stock→409.

**Adopción (PRODUCTO, `products/snipeit/product.yml`, incremento `QTY-OPERATIONS-ADOPT`):** `Accessory.operations:
[{ name: checkout, decrements: qty }]`.

**Verde POR BLOQUEO (no fingido):**
- EYEBALL importlib (HEAD vs working): default 68/68 · assets 68/68 · **snipeit-SIN-qty 70/70 byte-idénticos** (opt-in puro).
- `product-run --product snipeit` **PASS** · RTM **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless; qty extiende
  `access_control_live` sin check/estación nuevos → `proof_sha` intacto → **SIN re-pin**).
- **Diente de DOS lados VIVO**: saboteado `AND qty > 0` → checkout sin stock devuelve 200 en vez de 409 → **SÓLO
  `access_control_live` (s9) rojo** (`observability_live`/`frontend_consume_live` verdes + s0–s8 verdes — la
  degradación muerde a RUNTIME, no estáticamente) → revertido → **PASS**.
- `meta check` **6/6** (`generality` verde) · `ci --rederive` base **12/12** + assets **11/11** + snipeit **11/11**
  == pin · `git diff src/metafactory + seed = 0` · default+assets product.yml = 0.

**Scope honesto / DIFERIDO:** `creates: <pivot>` (insertar la fila AccessoryCheckout en el checkout) — un diente
honesto del pivot pide observabilidad de una entidad no-servida (HTTP read del pivot); el modelo `decrements`
(qty := qty-1 con guard) es la aproximación faithful del stock. Va al diferido duro de §4.

**Commits:** `feat(fsk): FSK-QTY-OPERATIONS …` (codegen) + `feat(snipeit): Accessory.checkout decrementa qty …`
(product.yml) + `docs(fsk): cerrar FSK-QTY-OPERATIONS + QTY-OPERATIONS-ADOPT (§Evidencia) + abrir FSK-POLYMORPHIC-REFS`.

**SIGUIENTE = FSK-POLYMORPHIC-REFS** (checkout polimórfico, deferral 2) — el último eje de modelo-de-datos faithful.
Handoff autocontenido en `docs/work/FSK-POLYMORPHIC-REFS-INCREMENT.md`.
