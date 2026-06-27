<!-- meta:doc sha=60c4d77ca02a4352a4c081aa0d7f061bd261452d updated=2026-06-27T01:41Z -->
# Incremento FSK-SOFT-DELETES — borrado LÓGICO (trash + restore): DELETE no es permanente, las lecturas filtran, un verbo recupera

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-23T01:55Z · cerrado 2026-06-23T03:16Z — ver §Evidencia). Editar `factories/full-stack-kotlin/**`
> no-`.md` exige un incremento abierto; el siguiente es `FSK-XENTITY-COMPUTED` (`docs/work/FSK-XENTITY-COMPUTED-INCREMENT.md`).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-COMPUTED-FIELDS con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (y por qué es DECISIÓN tuya)

**El NÚCLEO FUNCIONAL faithful está COMPLETO.** Cerrados, product-driven por Snipe-IT: modelo de datos (CRUD del grafo ·
self-ref · ownership opcional/RTD · refs requeridos transitivos · ciclos cross-entidad · ref polimórfico) · acceso
(auth→RBAC→ownership→company-scope) · comportamiento (workflow checkout/checkin · qty/stock) · **valores derivados**
(FSK-COMPUTED-FIELDS, recién cerrado) · app que CORRE (CRUD vivo + frontend consume/renderiza + deploy en contenedor).

**Lo que falta de genuinamente BEHAVIORAL (no breadth pura): el BORRADO LÓGICO.** Hoy DELETE es PERMANENTE (hard
`deleteFrom`). **Snipe-IT NUNCA hard-deletea por defecto** — usa SoftDeletes de Laravel pervasivamente (assets, users,
licencias, … se mandan a la "papelera" y se RESTAURAN). Es el deferral 12 y la fidelidad-gap behavioral más grande que
queda. Un eje real: una entidad opta-in `soft_delete: true` → DELETE pasa a `UPDATE deleted_at` (no borra), las
lecturas FILTRAN las filas borradas (read-filter) y un verbo `restore` las recupera.

**Por qué es un buen próximo:** (a) cierra el último eje BEHAVIORAL genuino antes de la breadth pura; (b) es FAITHFUL y
cross-cutting (toca toda entidad); (c) **determinista, sin s6/LLM**; (d) COMPONE primitivas YA probadas — el read-filter
de FSK-COMPANY-SCOPING y el montaje de verbos de FSK-QTY-OPERATIONS/FSK-DOMAIN-OPS; (e) tiene un diente de dos lados
nítido. Tras él, lo que resta es **breadth pura** (~226 rutas, Kits, EAV dinámico, `assigns` polimórfico del verbo,
derivación cross-entity del campo computado).

**⚠️ ESTA ES TU DECISIÓN (con más contexto).** Si al investigar decidís que NO es el mejor próximo, alternativas
honestas en §7. Tenés autoridad para reabrir — pero leé los wrinkles ANTES.

### 0.1 LOS WRINKLES
1. **`deleted_at` es una COLUMNA DE SISTEMA, no un campo de usuario** — como `id`. NO va en `e["fields"]`, NO en
   `_cols_of`/`_input_fields`/`_parse_fn`/el contrato-`required[]` (no se postea ni se valida como entrada). Es nullable
   (`DATE`, NULL = viva; una fecha = borrada-en). Se hilvana EXPLÍCITAMENTE donde hace falta: migration (append de la
   columna) · el read-filter · el DELETE (soft) · el verbo restore. Pensá un helper `_soft_delete(e)` (`bool`, hermano
   de `e.get("company_scoped")`) y enhebrá la columna a mano (mismo patrón que `id`, que tampoco vive en `_cols_of`).
   Alternativa más simple si `DATE` molesta: un `BOOLEAN deleted DEFAULT false` — pero `deleted_at` (nullable date) es
   más faithful y el filtro `IS NULL` es idéntico de simple. Recomendado: `deleted_at DATE` nullable.
2. **DELETE cambia de semántica** (hard → soft) SÓLO para entidades opt-in. El `delete<E>` de `_mutation_fns` + el
   handler `doDelete<E>` del AppServer deben BRANCHEAR por `_soft_delete(e)`. Byte-neutro para las no-soft (siguen
   `deleteFrom`). ⚠️ El DELETE soft devuelve igual 200 y la fila desaparece de las lecturas → **el diente de DELETE
   EXISTENTE del proof (DELETE→200→GET 404) SIGUE pasando idéntico** (lo observable no cambia); lo NUEVO es que la fila
   AÚN EXISTE → restore la trae de vuelta.
3. **El read-filter toca VARIOS read-paths** — `all<E>s` (lista), `<e>RowJson` (get-one + las filas de la lista),
   `<owned>OwnerId`/getOne y cualquier query de lectura. CADA uno debe sumar `WHERE deleted_at IS NULL` para una entidad
   soft. Si te olvidás de uno (p.ej. get-one), una fila borrada se ve por un camino y no por otro → inconsistente. Es la
   superficie principal; el read-filter de FSK-COMPANY-SCOPING (`_COMPANY_SCOPE_PROOF` + el filtrado en el AppServer) es
   el MODELO a copiar (sólo que acá el predicado es `deleted_at IS NULL`, sin bypass por rol — o con un bypass "ver
   papelera" si querés, pero el 1er-cut: filtrar SIEMPRE, restore para recuperar).
4. **`restore` es un VERBO** (`POST /<plural>/{id}/restore`) — compone el montaje de verbos YA existente: mirá cómo
   FSK-QTY-OPERATIONS monta `POST /<plural>/{id}/<verb>` (`_ownerless_handlers(ops=)`) y FSK-DOMAIN-OPS monta los verbos
   de workflow (`_operations_handlers`). restore hace `UPDATE set deleted_at = NULL where id` y se GATEA por el MISMO
   acceso que la entidad (RBAC si ownerless; RBAC+ownership si con dueño). Decisión: ¿restore es un `operation` declarado
   o un verbo IMPLÍCITO que `soft_delete: true` habilita? **Recomendado: implícito** (lo habilita la flag, como
   `deleted_at` — menos DATA, y restore es universal para soft-delete). Pero mirá la gramática de `operations` primero:
   si encaja limpio como op implícita, mejor.
5. **El ciclo del diente sobre UNA fila** — el read-filter Y el DELETE-soft Y restore deben probarse sobre la MISMA
   fila para que el diente sea nítido: POST → DELETE (soft) → GET 404 (filtrada) + count−1 → restore → GET 200 +
   count+1. Hacelo sobre una fila FRESCA al final del try (8-indent, como `_QTY_PROOF`/`_POLY_PROOF`) para no chocar con
   el DELETE existente (que borra `new_id`). ⚠️ Para una entidad CON DUEÑO, restore se gatea por ownership → POSTeá como
   el dueño y restaurá como el dueño (o bypass).

**Conclusión honesta**: el camino BOUNDED y limpio — **`soft_delete: true` por entidad → columna de sistema
`deleted_at` (nullable) + read-filter `IS NULL` en TODOS los read-paths + DELETE soft (UPDATE) + verbo `restore`
implícito**, sobre la entidad CON DUEÑO viva (Asset) donde el round-trip es observable. Diente: DELETE→GET 404 (la fila
sigue EXISTIENDO) → restore→GET 200; sabotear el read-filter (quitar `IS NULL`) → la fila borrada se ve → SÓLO s9 rojo.

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
- **Gramática** (`_load_blueprint`): una entidad puede declarar `soft_delete: true` (top-level por-entidad). Fail-closed
  trivial (bool). Opt-in: sin la flag, byte-neutro para todo lo previo.
- **`_soft_delete(e)`** (hermano de los predicados existentes): `return bool(e.get("soft_delete"))`.
- **`_migration_sql`**: para una entidad soft, APPEND `deleted_at DATE` (nullable, NO en `_cols_of`). Como `id`, es
  columna de sistema.
- **El read-filter**: TODOS los read-paths de una entidad soft suman `.where(<TBL>.DELETED_AT.isNull)` (jOOQ). Tocá
  `all<E>s` (`_repository_kt`), `<e>RowJson` (el SELECT del get-one), el query del owner (`<owned>OwnerId`), y las filas
  de la lista (`all<E>RowsJson` reusa `all<E>s` → ya filtrado). ⚠️ El que se te escape muerde el diente.
- **DELETE soft** (`_mutation_fns` + el handler `doDelete<E>` del AppServer): para soft, `ctx.update(<TBL>).set(
  DELETED_AT, <hoy>).where(ID.eq(id)).execute()` en vez de `deleteFrom`. La fecha = un `LocalDate.now()` o una fija
  determinista (cuidá: si la serializás en rowJson, el round-trip de la FECHA es no-determinista con `now()` → usá una
  constante o NO la expongas en rowJson; el filtro sólo mira `IS NULL`, no el valor).
- **`restore`** (verbo implícito, `POST /<plural>/{id}/restore`): `ctx.update(<TBL>).set(DELETED_AT, null).where(ID.eq(
  id)).execute()`. Montalo como los verbos de qty/workflow; gatealo por el acceso de la entidad. Registralo en el
  contrato + RouteTable (route_check topología/auth/rbac deben cuadrar — mirá cómo lo hizo el verbo qty).
- **El proof** (`_access_control_check_py` + un bloque OPT-IN tipo `_QTY_PROOF`): sobre una fila FRESCA — POST → DELETE
  → GET /{id} == 404 + count−1 → restore → GET /{id} == 200 + count+1. Diente: quitar `IS NULL` del read-filter en el
  codegen → la fila borrada se ve (GET 200 tras DELETE) → SÓLO `access_control_live` rojo.

**EL DIENTE de dos lados**: DELETE (soft) → GET 404 (filtrada, pero la fila EXISTE) → restore → GET 200. Saboteá el
read-filter (quitá `.where(DELETED_AT.isNull)`) → la fila borrada se ve → **SÓLO** `access_control_live` (s9) rojo,
hermanos (`observability_live`+`frontend_consume_live`) + s0–s8 verdes → revertí → verde. **Alternativa de sabotaje**:
degradar el DELETE soft a hard (`deleteFrom`) → restore no encuentra la fila → GET sigue 404 tras restore → rojo. ⚠️ **El
sabotaje debe degradar la LÓGICA/SQL, no la forma Kotlin** (un cambio que rompe detekt/ktlint en s2 NO sirve).

---

## 1. ⚠️ RE-PIN — casi seguro NO hace falta
Si el cambio vive DENTRO de `access_control_live` (s9) + suma una ruta a s5 (como hizo el verbo qty) SIN agregar
check/estación nuevos → el **`proof_sha` queda INTACTO** → pines byte-idénticos, **SIN re-pin** (como qty/poly/computed).
`git diff snipeit/product.yml ≠ 0` es ESPERADO; el sustrato + default/assets product.yml DEBEN quedar en 0. Si SÍ
agregás un check/estación → re-pin justificado + re-materializá el chasis por defecto + re-pineá los 3 productos.

## 2. Maquinaria a REUTILIZAR — TODO en `codegen/scaffold_product.py` (verificá los anchors con grep)
- **El read-filter de FSK-COMPANY-SCOPING** es tu mejor modelo: cómo el AppServer filtra la lista por un predicado
  (acá `deleted_at IS NULL` en vez de `company_id == actor`). Buscá `company_scoped`/`_COMPANY_SCOPE_PROOF`/el filtrado
  en el handler de lista.
- **El montaje de verbos de FSK-QTY-OPERATIONS** (`POST /<plural>/{id}/<verb>`): `_ownerless_handlers(ops=)`,
  `_QTY_PROOF`, `_qty_ops`. Y los de workflow: `_operations_handlers`/`_operation_repo_fns`/`_OPERATIONS_PROOF`. restore
  es un verbo más (la query es un UPDATE de una columna a NULL).
- **El patrón OPT-IN del proof**: copiá `_QTY_PROOF`/`_POLY_PROOF`/`_COMPUTED_PROOF` — un bloque substituido
  (`%SOFT_DELETE_BLOCK%`), vacío sin la flag → byte-idéntico; el DATA nuevo va DENTRO del bloque, NUNCA en el SKELETON.
- **`deleted_at` como columna de sistema**: mirá cómo `id` (`<TBL>.ID`) se enhebra fuera de `_cols_of` (migration hardcodea
  `id`, rowJson lo lee aparte) — replicá ese patrón para `deleted_at`. (Y cómo FSK-COMPUTED-FIELDS metió el `current_value`
  derivado en rowJson fuera de `_cols_of` — el mismo principio de "columna/valor que no es un field de usuario".)

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **EYEBALL SIN gradle ANTES de cada corrida lenta** (cazó el 100% de los problemas de byte-neutralidad en qty/poly/
  computed): un scratch python con `importlib` que carga el scaffold HEAD vs working, llama `build_files(bp)` para
  default/assets/snipeit-SIN-el-eje, y **diffea** (byte-idénticos). Snapshot HEAD: `git show
  HEAD:factories/full-stack-kotlin/codegen/scaffold_product.py > /tmp/.../scaffold_head.py`. Lo nuevo va OPT-IN (vacío →
  byte-idéntico); NUNCA cambies un comentario/constante incondicionalmente.
- **Un sabotaje que debe morder a RUNTIME no puede introducir un hallazgo ESTÁTICO antes.** Degradá el SQL/la lógica, no
  la forma Kotlin. **ktlint/detekt MaxLineLength=160; LongMethod ≤ 60 (`@Suppress` opt-in); CyclomaticComplexMethod ≤
  15; ReturnCount ≤ 2; MagicNumber ignora -1/0/1/2 pero NO 3+; NoUnusedImports + -Werror.** Lecciones del computado:
  un `.toDouble()` REDUNDANTE sobre un `Double` → -Werror (s0 rojo); `${ident}` con llaves redundantes sobre un
  identificador simple → ktlint StringTemplate (s2 rojo). **jOOQ DDLDatabase tipa toda columna NULLABLE** (por eso el
  `!!` en `it[TBL.ID]!!`): `deleted_at` será `LocalDate?` → el filtro `.isNull` es jOOQ nativo (sin null-deref).
- **`meta verify` re-corre la estación ACTIVA con `build=False`** (no regenera). Para un tooth en s9: **sabotear el
  codegen + `product-run`** (rojo en s9, las posteriores no corren) → revertir → `product-run` verde (restaura la activa
  verde, clave para que `stop_proof` no bloquee el cierre). El sabotaje preciso se manifiesta como "infra_up no alcanzó
  la infra en 120s" con SÓLO `access_control_live` rojo y los hermanos verdes.
- **`meta station` corre la META-línea (m00-m08), NO la línea FSK.** Para la línea FSK: `product-run`.
- **`proof_protect` puede DENEGAR tocar `.proof/` por shell** — el **Read tool SÍ** lee `.proof/logs/` (los logs son
  RESÚMENES: check + exit; el `exit=0` es la señal autoritativa, no esperes el stdout per-aserción del proof).
- **`ci --rederive` por producto**: `--product snipeit`/`--product assets` y SIN `--product` (la base/default). NO existe
  `--product default`. Cada uno es un clon limpio (≈< 10 min) → corrélos UNO A UNO en foreground.
- **`dangerouslyDisableSandbox: true`** para gradle/docker. cwd SIEMPRE en la raíz. FOREGROUND, un producto a la vez.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento)
**derivación CROSS-ENTITY del campo computado** (resolver un ref y leer la columna del target — la contracara del
1er-cut same-entity de FSK-COMPUTED-FIELDS) · **`assigns`/owner POLIMÓRFICO** (sub-ejes de FSK-POLYMORPHIC-REFS) ·
**`creates`/pivot de qty** (insertar AccessoryCheckout) · **EAV dinámico a runtime** (custom-fields Avenue B) · **PUT/
update de campos OPCIONALES arbitrarios** (hoy el server inserta/actualiza sólo required + la columna mutable) · **e2e
Playwright / browser real** · **AppServer-en-contenedor con PG** · **las ~226 rutas / Kits** (breadth).

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py` + quizá `factory.spec.yml`/`stations/*.yml` si la grama nueva necesita validación
  M0) es nivel FÁBRICA → **este incremento** lo cubre (header ABIERTO).
- **La adopción** (`products/snipeit/product.yml`: declarar `soft_delete: true` en una entidad —p.ej. Asset—) es nivel
  PRODUCTO → abrí TAMBIÉN `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar
  `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) + `feat(snipeit): …` (product.yml) + `docs(fsk): cerrar
  FSK-SOFT-DELETES (§Evidencia) + abrir <siguiente>`. **Commiteá el CÓDIGO mientras el incremento está ABIERTO**, luego
  flipeá el header a CERRADO en el commit de docs (cerrar primero bloquearía el commit del código).
- **Probá POR BLOQUEO**: EYEBALL byte-neutro · `product-run --product snipeit` PASS · diente de dos lados vivo (sólo s9) ·
  `ci --rederive` (base + assets + snipeit) == pin (los 3) · `meta check` 6/6 (`generality` verde) · `git diff
  src/metafactory + seed = 0` · default+assets product.yml = 0.

## 6. Criterio de cierre (demostrable, no narrable)
1. Una entidad declara `soft_delete: true` en `products/snipeit/product.yml` y `product-run --product snipeit` **PASS**
   — el server vivo (s9): DELETE deja la fila EXISTENTE pero invisible a las lecturas (GET /{id} → 404, count−1) y
   `POST /<plural>/{id}/restore` la recupera (GET /{id} → 200, count+1).
2. **Diente de DOS lados verificado VIVO**: saboteá el read-filter (`IS NULL`) o el DELETE-soft → ROJO **sólo** en
   `access_control_live` (s9) → revertí → verde.
3. EYEBALL byte-neutro (default/assets + snipeit-sin-soft-delete) · `ci --rederive` (base + assets + snipeit) == pin ·
   `meta check` 6/6 (`generality` verde) · `git diff src/metafactory + seed = 0` · default+assets product.yml = 0.
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md §3 deferral 12 / §4` actualizados. Abrí el SIGUIENTE con su handoff (§7).

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE
Si al investigar decidís que soft-deletes NO es el mejor próximo (es tu decisión con más contexto), las otras candidatas
BOUNDED, framed honestamente:
- **Derivación CROSS-ENTITY del campo computado** (la contracara del 1er-cut de FSK-COMPUTED-FIELDS): la fórmula
  referencia un campo de una entidad RELACIONADA (resolver el ref, leer la columna del target en el JOIN). Toca
  `_row_json_fn` (un JOIN a la tabla del target) + la validación del AST (referencias `<ref>.<campo>`). Completa el
  straight-line REAL de Snipe-IT (months viven en `Depreciation` vía AssetModel). Acotado pero "menos dimensión nueva".
- **El `assigns` POLIMÓRFICO del verbo** (sub-eje diferido de FSK-POLYMORPHIC-REFS): un verbo de workflow que asigna a un
  ref polimórfico (setear las 2 columnas `<campo>_type`+`<campo>_id` del cuerpo del verbo). Completa el checkout
  polimórfico FAITHFUL. Toca `assigns` + `_operation_repo_fns`/`_operations_handlers` + el proof.
- **Breadth pura** (si decidís que el núcleo funcional + behavioral YA está): las ~226 rutas · Kits (bundles) · Actionlog
  (auditoría polimórfica) · EAV dinámico. Son los flecos, no el corazón.

### ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El núcleo funcional + behavioral está ESENCIALMENTE COMPLETO**: modelo de datos faithful (incl. refs polimórficos) +
reglas + control de acceso (auth→RBAC→ownership→company-scope) + comportamiento (workflow + stock) + valores derivados
(campo computado) + app que CORRE (CRUD vivo + frontend + deploy). **Soft-deletes (este)** cierra el último eje
behavioral genuino (trash/restore, que Snipe-IT usa pervasivamente). Tras él, la paridad de superficie completa (~226
rutas, Kits, EAV dinámico, cross-entity, assigns polimórfico) es trabajo de BREADTH — los flecos, no el corazón.

---

## §Evidencia — CERRADO 2026-06-23T03:16Z (verde por bloqueo, no narrado)

**Construido GENERAL en `codegen/scaffold_product.py` (FÁBRICA, opt-in byte-neutro), adoptado en `products/snipeit/
product.yml` (`Asset.soft_delete: true`):**
- `_soft_delete(e)` = `bool(e.get("soft_delete"))`; fail-closed (bool) en `_load_blueprint`.
- columna de SISTEMA `deleted_at DATE` appendeada en `_migration_sql` FUERA de `_cols_of` (como `id`).
- read-filter `deleted_at IS NULL` en `all<E>s` · `<e>RowJson` (get-one) · `sByCompany` (compone sobre el
  `company == ? OR company IS NULL`); NO en `<e>OwnerId`/`<e>CompanyId` (el guard ve la fila borrada).
- DELETE soft (`_mutation_fns`: `UPDATE deleted_at = java.time.LocalDate.now()` vs `deleteFrom`); verbo `restore`
  IMPLÍCITO (`setNull`) montado vía `%RESTORE_HANDLER%`/`%RESTORE_DISPATCH%`, gateado por `modifyVerdict`, registrado
  en contrato + RouteTable.
- **Wrinkle de composición #1**: modifyVerdict (owner-OPTIONAL) chequeaba existencia via `<e>RowJson` (ahora filtrado)
  → fila borrada parecía inexistente → restore 404. Fix: `<e>Exists` SIN filtrar (param `exists_fn` de
  `_modify_verdict_kt`, usado sólo en el camino owner-optional cuando soft). Asset es owner-optional (RTD) → pegó.
- **Wrinkle de composición #2**: el UNIQUE inline ocupaba el valor aún borrado → POST que reusa el valor (proof de
  `operations`) → violación de UNIQUE → crash del server (RemoteDisconnected). Fix FAITHFUL: índice UNIQUE **PARCIAL**
  `WHERE deleted_at IS NULL` (jOOQ DDLDatabase parsea el `WHERE`, probado) + el proof re-deletea `new_id` tras restore.

**Verificación POR BLOQUEO:**
- EYEBALL byte-neutro: default/assets/snipeit-SIN-soft → 0 diffs (`build_files` HEAD vs working).
- `product-run --product snipeit` → **PASS**; RTM **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless — deferral VISIBLE).
- **Diente de DOS lados VIVO**: saboteé `one_where` (sin `.and(DELETED_AT.isNull)`) → `product-run` → **SÓLO**
  `access_control_live` (s9) rojo, hermanos (`observability_live`+`frontend_consume_live`) + s0–s8 verdes → revertí →
  `product-run` PASS.
- `ci --rederive`: full-stack-kotlin **12/12** · assets **11/11** · snipeit **11/11** — `proof_sha == pineado` en clon
  limpio (SIN re-pin: la flag sumó una ruta a s5 + lógica a s9, ningún check/estación nuevo).
- `meta check` **6/6** (`generality` verde). `git diff src/metafactory + seed = 0`. default/assets `product.yml` = 0.

**Commits:** `feat(fsk): FSK-SOFT-DELETES …` (codegen) + `feat(snipeit): Asset.soft_delete=true …` (producto) + este
`docs(fsk): cerrar FSK-SOFT-DELETES (§Evidencia) + abrir FSK-XENTITY-COMPUTED`.

**Siguiente (abierto, recomendado):** `FSK-XENTITY-COMPUTED` — derivación cross-entity del campo computado (ver §7 +
`docs/work/FSK-XENTITY-COMPUTED-INCREMENT.md`). Es DECISIÓN de la próxima sesión (alternativas en §7).
