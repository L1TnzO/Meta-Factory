# Incremento FSK-PUT-OPTIONAL — editar CUALQUIER campo (no sólo la columna mutable única)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (2026-06-25T01:05Z; abierto 2026-06-24T23:58Z). Ver **§Evidencia** al final.
> Editar `factories/full-stack-kotlin/**` no-`.md` (codegen/spec/stations) exige ESTE incremento abierto
> — el `increment_guard` elige el lifecycle por la RUTA editada.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Lo escribió la sesión que cerró
> FSK-ACTIONLOG con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (y por qué es el más BOUNDED)

**EL NÚCLEO + LA SUPERFICIE + LOS VALORES-DERIVADOS + LA UX + EL DEPLOY + LA AUDITORÍA están COMPLETOS.** Lo que
RESTA es **breadth de dominio** + diferidos de red. Entre lo restante, **FSK-PUT-OPTIONAL es el más ACOTADO y un
quick-win de CRUD FIEL**: hoy el `PUT /<plural>/{id}` actualiza **UNA sola columna** — la "columna mutable"
(`_mutable_field`: el 1er `string` no-unique, no-ref, no-dueño). El resto de los campos del Asset (los opcionales,
los de otros tipos) **no son PUT-eables**. En Snipe-IT editás CUALQUIER campo de un activo. Cerrar esto vuelve la
**EDICIÓN faithful**: `PUT` acepta los campos updatables del cuerpo (PATCH-like: sólo los provistos), type-coerced
por el schema, y los persiste. **COMPONE FSK-CRUD-BODY-PARSING** (el codec `parse<E>Input` + los samples del proof
ya existen) sin inventar arquitectura nueva. Sin infra nueva (es codegen + la PG que ya levantan s9/s11).

**⚠️ ESTA ES TU DECISIÓN (con más contexto).** Lo elegí como el más bounded/de-mayor-retorno-inmediato, pero en §7
hay alternativas honestas con AUTORIDAD para reabrir si al investigar preferís otro orden (cerrar el eje DEPLOY con
el push a registry, o domain-breadth con Kits).

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥600000ms** (el sandbox mata
gradle). **cwd de Bash SIEMPRE en la RAÍZ** (`cd <raíz> && …`; un `cd` a un subdir filtra el cwd persistente →
deadlock del hook `stop_proof`). Debe dar **PASS**, RTM snipeit **25/26** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **Puertos vivos**: s9 PG 5436/5437/5438 + servers 18593-18595/18597; s11 18596/18598 + PG en `fsk_s11_net`.
NUNCA dos corridas en paralelo (nombres de contenedor FIJOS). Para un diente VIVO manual usá un puerto distinto
(p.ej. PG 5446 / AppServer 18599, como hizo FSK-ACTIONLOG — ver su §Evidencia / `scratchpad/verify_*.sh`).

**2) ENTENDÉ la maquinaria EXISTENTE que vas a COMPONER** (verificá anchors con grep — el archivo se mueve). Todo
vive en `factories/full-stack-kotlin/codegen/scaffold_product.py`:
- **`_mutable_field(e)`** (grep `def _mutable_field`): hoy elige la ÚNICA columna PUT-eable. El eje la GENERALIZA a
  "los campos updatables" (todos los no-dueño, no-computed, no-id; ¿incluir UNIQUE? Snipe-IT sí, pero un UNIQUE
  chocado → la DB rechaza → 409, hay que decidir el código). DECISIÓN tuya: ¿PATCH (sólo claves provistas) o PUT
  full? **Recomendado PATCH-like** (faithful a Snipe-IT, y compone con el parser parcial-tolerante).
- **`_app_server_handlers` → `do_put`** (grep `def _app_server_handlers`, bloque `if mf:`): hoy `parsePut` parsea
  SÓLO `mf["name"]` (un `str(...)`), y llama `Repository.update<E><Field>(ctx, id, value)`. El eje: parsear el
  cuerpo COMPLETO (reusá el codec o una variante PARCIAL que admita claves ausentes) y llamar un `update<E>` general
  que setea las columnas provistas. ⚠️ **FSK-ACTIONLOG ya envuelve `do_put` con `audited`**: el PUT general DEBE
  seguir appendeando el rastro `"update"` — mantené el `appendActionLog(tx, …, "update", …, id)` dentro de la misma
  transacción (el `put_ok` del handler ya lo hace; generalizá el CUERPO del update SIN romper esa rama auditada).
- **`_mutation_fns` → `update<E><Field>`** (grep `def _mutation_fns`, bloque `if owner and mf:`): hoy emite
  `update<E><Field>(ctx, id, value: String): Int` (una columna). El eje emite un `update<E>(ctx, id, patch: <E>Patch)`
  (o reusa `<E>Input` con campos nullable) que setea cada columna provista type-bound (jOOQ `.set(COL, value)` por
  campo presente). Type-coerción del cuerpo por el schema (DES-12), como el INSERT.
- **El codec** (grep `def _codec_helpers`, `parse<E>Input`): el parser del POST exige TODOS los requeridos. Para un
  PATCH necesitás un parser TOLERANTE (claves ausentes → no-set). DECISIÓN: ¿un `parse<E>Patch` nuevo, o reusar el
  parser con un data class de campos nullable? El más limpio: un data class `<E>Patch` (todas las columnas updatables
  nullable) + un parser que setea sólo las presentes. Fail-closed: una clave presente con tipo equivocado → 400.
- **El diente** (grep `def _access_control_check_py`, el bloque del owned PUT, `%PUT_BODY%`/`MUT_COL`): hoy postea
  `{MUT_COL: PUT_VALUE}` y verifica que GET lo refleja. El eje: PUT un campo OPCIONAL (≠ MUT_COL) → GET lo ve
  actualizado; PUT varios a la vez (PATCH) → todos actualizados; un PUT con tipo equivocado en un opcional → 400.
  El diente DEBE seguir verde en el campo mutable existente (no regresión).

**3) EL DISEÑO (GENERAL, cero nombres de dominio):**
   - El blueprint NO necesita una flag nueva: el eje generaliza el comportamiento existente del PUT. (Opt-in natural:
     una entidad con UNA sola columna updatable → byte-idéntico al previo; el cambio sólo "aparece" con ≥2 updatables.)
     ⚠️ Verificá: ¿default/assets tienen entidad-con-dueño con >1 columna updatable? Si sí, su PUT cambia →
     NO byte-neutro para ellos. **MIDE ESTO PRIMERO con el eyeball** (render base/assets/snipeit, diff el
     AppServer/Repository). Mantené el caso 1-columna byte-idéntico si podés (degrada al `update<E><Field>` actual).
   - PATCH-like: el cuerpo trae un SUBCONJUNTO de las columnas updatables; el server setea SÓLO esas; las ausentes
     quedan intactas. Type-coerced por el schema (un `int` es int, fail-closed → 400).
   - El UPDATE va SIEMPRE detrás del MISMO `modifyVerdict` (RBAC + ownership + company-scope) — no cambia el acceso.
   - **COMPONE FSK-ACTIONLOG**: el PUT general sigue appendeando `"update"` atómico (no rompas la transacción del
     `put_ok` auditado).

**EL DIENTE de dos lados (VIVO contra el AppServer + PG real):**
   - **Verde**: PUT `{<campo opcional>: <valor>}` por el dueño → 200 → GET `/{id}` ve el valor NUEVO en ESE campo
     (y los demás intactos); PUT multi-campo → todos actualizados.
   - **Saboteá**: que el `update<E>` ignore un campo (o lo hardcodee) → GET no refleja ese campo → **SÓLO el assert
     del PUT-opcional rojo**, hermanos verdes → revertí → verde.
   - **Negativo**: PUT con un opcional del tipo equivocado → 400 (no 500, no 200 que traga).

---

## 1. RE-PIN — depende de tu forma de probar (LEÉ ESTO)
`compute_proof_sha` (`seed/verifier.py`) hashea `station_id + sorted (check_name, exit)`. **Si NO agregás un check
nuevo** (el diente del PUT-opcional vive DENTRO de `access_control_live` de s9, que ya ejercita el PUT) → **proof_sha
byte-neutro → NO re-pin** (igual que FSK-ACTIONLOG/SOFT-DELETES extendieron el proof sin re-pinear). **PERO** ojo: si
la generalización del codegen cambia los artefactos de **default/assets** (porque tienen >1 columna updatable), su
artefacto cambia pero el `proof_sha` NO (mismo set de checks/exits) → **igual no re-pin**, pero `git diff` de sus
generados ≠ 0 → confirmá que es un cambio GENERAL legítimo (la gate `generality` lo sanciona, no el `==0` literal —
ver memoria `anti-overfit-is-generality-gate`). **Recomendación**: meté el assert DENTRO de `access_control_check.py`
→ byte-neutro de pin. Si por aislamiento preferís un check propio → re-pin de los 3.

## 2. Lecciones CARAS ya destiladas (de FSK-ACTIONLOG + las previas)
- **VALIDÁ BARATO ANTES DE GRADLE** (≈10s): adaptá `scratchpad/eyeball_actionlog.py` (FSK-ACTIONLOG lo dejó —
  carga el scaffold, setea el blueprint en memoria, renderiza migration/repository/appserver/proof, diffea claves +
  chequea 0 líneas Kotlin >160 + base/assets byte-idénticos). **Hacelo antes de tocar gradle.**
- **El diente VIVO se corre MANUAL y RÁPIDO** contra la dist viva: PG en docker + el AppServer por
  `java -cp 'build/install/snipeit/lib/*' snipeit.endpoints.AppServerKt` con `FSK_PG_URL`/`FSK_AC_PORT`/`FSK_NOW=2030-07-15`
  (el oráculo `[computed]` está pineado a ESA fecha — otra fecha → falso rojo por redondeo de meses), esperá `/health`
  con `curl --retry 60 --retry-connrefused`, PUT-eá y GET. **`infra_up` NO surfacea el stdout del proof** → corré el
  proof MANUALMENTE. FSK-ACTIONLOG dejó `scratchpad/verify_actionlog.sh` + `sabotage_actionlog.sh` como molde (PG
  `postgres@sha256:e013e8…` cacheada, puertos 5446/18599).
- **El sabotaje runtime NO debe romper lo estático** (degradá lógica/SQL/data, no Kotlin): borrá/garbleá un `.set()`,
  no rompas sintaxis. Rebuild con `./gradlew installDist -q --console=plain` en `build/product` (el `increment_guard`
  BLOQUEA el tool Edit sobre rutas `build/` de un producto → saboteá con Bash `sed`, no con Edit).
- **ktlint/detekt al escalar** (cada uno mordió un eje): MaxLineLength 160 · PropertyWrapping >120 (un `val x=<expr>`
  largo se envuelve) · NoMultipleSpaces (doble-espacio antes de `//` enrojece s2) · MagicNumber (literal 3+, no 0/0.0)
  · ReturnCount≤2 · CyclomaticComplexMethod≤15 · LongMethod≤60 · @Suppress(LargeClass) si la clase pasa 600. El PUT
  general puede empujar `doPut`/`update<E>` — @Suppress por TAMAÑO opt-in, no a mano.
- **`ci --rederive` opera sobre el ÁRBOL DE TRABAJO** (borra `.proof/`+`build/`, re-deriva in-place). UNO A UNO
  (<10min cada uno) o `--all-products`. **Delegá las corridas pesadas (base+assets cross-check) a un subagente Sonnet**
  — pero escribí el codegen + el diente con TUS ojos. **proof_protect DENIEGA tocar `.proof/` por shell** → `meta rtm`.

## 3. Re-pin (SÓLO si agregás check/estación) + disciplina (ADR-016)
1. (Sólo si check/estación nuevo) Editá `factory.spec.yml` **y** sincronizá el `stations/<id>.yml` committeado a mano
   (⚠️ editar `station_sequence` re-materializa los PRODUCTOS pero NO el base committeado `stations/<id>.yml`).
2. `product-run` base + assets + snipeit PASS (uno a uno). 3. `meta pin` (base) + `--product assets`/`snipeit`.
4. `ci --rederive` por producto == el pin (base 12 · assets 11 · snipeit 11).
- **El codegen es nivel FÁBRICA → ESTE incremento** (header ABIERTO). El PUT-opcional NO necesita tocar
  `product.yml` (es comportamiento general, no una flag) → probablemente **NO** necesitás un incremento de PRODUCTO.
  Si por algo tocás `products/snipeit/product.yml`, abrí `meta increment open … --product snipeit <slug>` ANTES.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` con el incremento ABIERTO, luego `docs(fsk): cerrar
  FSK-PUT-OPTIONAL (§Evidencia) + abrir <siguiente>` flippeando el header a CERRADO.

## 4. Criterio de cierre (demostrable, no narrable)
1. El `PUT /<plural>/{id}` actualiza CUALQUIER campo updatable provisto en el cuerpo (PATCH-like), type-coerced;
   `GET /{id}` lo refleja. `product-run --product snipeit` **PASS**.
2. **Diente de DOS lados verificado VIVO**: PUT un campo OPCIONAL → GET lo ve; saboteá el set de ese campo → SÓLO
   ese assert rojo, hermanos verdes → revertí → verde. (+ tipo equivocado → 400; el campo mutable existente sigue OK.)
3. EYEBALL · (re-pin SÓLO si check nuevo) · `ci --rederive` por producto == pin · `meta check` 6/6 (`generality`
   verde) · `git diff src/metafactory + seed = 0`.
4. STATE/LOG (fábrica) + SNIPEIT-DOMAIN actualizados. Abrí el SIGUIENTE con su handoff (§7).

## 5. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento)
- **push de la imagen a un registry** — el ÚLTIMO diferido DURO de DEPLOY (necesita un registry local hermético;
  ⚠️ requiere `registry:2` cacheado para que `ci --rederive` sea offline — verificá ESO primero). Cierra el ciclo.
- **Kits (bundles)** — un Kit agrupa assets/accesorios/licencias que se checkout-ean juntos. COMPONE FSK-CREATES-PIVOT.
- **EAV dinámico (Avenue B)** — custom-fields definidos a RUNTIME (vs el schema build-time-typed jOOQ). Cambio de
  ARQUITECTURA, no aditivo. El de MAYOR esfuerzo.
- el largo tail de ~226 rutas operacionales no-dominio (counters, image-upload, LDAP, 2FA).
- **auditar `restore` + las entidades ownerless/qty** (FSK-ACTIONLOG dejó esto diferido: hoy sólo audita la
  entidad-con-dueño servida; el `restore` y las ownerless no dejan rastro — eje hermano de bajo costo).

## 6. ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El backend faithful (modelo·acceso·comportamiento·valores-derivados incl. tiempo), la app CORRE, TODAS las
entidades se sirven, el frontend se VE y se SUBMITEA en un navegador REAL, DEPLOYA DE VERDAD, y AUDITA cada
mutación (Actionlog).** Tras el PUT-opcional, la EDICIÓN es faithful (cualquier campo). Lo que RESTA es breadth de
dominio (Kits, el tail no-dominio) + diferidos de red/arquitectura (push a registry, EAV dinámico). **No queda
ningún hueco de NÚCLEO, SUPERFICIE, VALORES-DERIVADOS, UX, DEPLOY ni AUDITORÍA.**

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE (con AUTORIDAD para reabrir)
Si al investigar preferís otro eje (cualquiera es legítimo; reabrí con `meta increment`):
- **FSK-DEPLOY-PUSH-REGISTRY** — cierra el eje DEPLOY (registry local hermético; ⚠️ verificá `registry:2` cacheado
  ANTES — si no, la hermeticidad de `ci --rederive` se rompe). El de mayor "cierre de axis".
- **FSK-KITS** — bundles (M:N agrupado), domain breadth, compone FSK-CREATES-PIVOT.
- **EAV dinámico** — el de mayor esfuerzo/riesgo (cambio de arquitectura).

---

## §Evidencia (cierre 2026-06-25T01:05Z)

**HECHO tal como el handoff lo planteó: el PUT pasó de mutar UNA columna a un PATCH del cuerpo.** GENERAL, cero
nombres de dominio (sancionado por `generality`); `git diff src/metafactory + seed = 0` — toda la generalización
vive en `codegen/scaffold_product.py` (164+/70−).

**Diseño REALIZADO (PATCH-like, recomendación del §0 confirmada):**
- **`_patchable_fields`** (reemplaza `_mutable_field`) = los campos EDITABLES: escalar/enum, **no-dueño**,
  **no-computed**, **no-unique**, **no-ref**, **no-workflow** (+ `_workflow_field_names`: un enum con
  `initial`/`transitions` o el `field` de una `operation` NO es PUT-eable — el estado se mueve por sus verbos,
  DES-3; un PUT directo bypasearía la máquina). UNIQUE y ref los difiere el eje hermano (un UNIQUE chocado → 409;
  la validación de FK del PATCH es otro eje).
- **Repository**: `data class <E>Patch(` (un campo NULLABLE `= null` por updatable) + `update<E>(ctx, id, patch)`
  con un **set DINÁMICO** (`mutableMapOf<org.jooq.Field<*>, Any?>()`; `patch.<f>?.let { sets[<COL>] = it }` por
  campo; `if (sets.isEmpty()) 0 else ctx.update(...).set(sets)...` — un patch sin claves → 0 filas, no-op, sin SQL
  inválido). jOOQ resuelve el bind por el `DataType` de la columna.
- **AppServer**: `parse<E>Patch` TOLERANTE (`if ("k" in o) <coerce> else null` por clave → una ausente no se toca,
  PATCH-semantics; una presente con tipo equivocado → coerción tira → runCatching → null → 400). REUSA el MISMO
  codec — extraje **`_coerce_expr`** (compartido por `_parse_fields_fn` y `_patch_parse_fn`), cero coerción nueva.
  `doPut` arma el patch y, en 200, llama `update<E>`. **COMPONE FSK-ACTIONLOG**: el update sigue dentro de la
  `ctx.transaction{}` que appendea `"update"` a `action_logs` (atómico) — no rompí esa rama auditada.
- **proof s9** (`access_control_check.py`, DENTRO de `access_control_live` → **byte-neutro, SIN re-pin**):
  `PUT_BODY` = multi-campo con valores NUEVOS (`_proof_form_value`, ≠ los del POST), `PATCH_UNTOUCHED` = un
  updatable que está en el POST pero NO en el patch (su valor post-POST es conocido), `PATCH_BAD` = `{1er campo:
  tipo equivocado}`. Asserts: PUT (PATCH) → 200; GET ve **cada** `patch[k]` actualizado; el campo NO-pacheado
  queda **INTACTO**; PATCH tipo equivocado → 400.

**Probado POR BLOQUEO (con mis ojos):**
1. **Eyeball barato (sin gradle)** — los 3 productos renderizan: `<E>Patch` + `update<E>` (Repository),
   `parse<E>Patch` + `doPut(patch)` + `import <E>Patch` (AppServer), `PUT_BODY`/`PATCH_UNTOUCHED`/`PATCH_BAD` +
   el loop (proof). snipeit: 11 campos updatables (incl. `mac_address` con `format` → `strFmt`, `warranty_months`
   int, `requestable`/`byod` bool → el codec ganó `int32`/`bool` + sus imports kotlinx). **0 Kotlin >160** en los 3.
2. **`product-run --product snipeit` PASS** (la línea REAL gradle s0→s11 compiló el `update<E>` dinámico + el
   parser tolerante + el data class) · **RTM 25/26** (único UNSAT = REQ-F-007/s6 LLM keyless).
3. **Diente VIVO de DOS lados** (vs la dist compilada + PG real, `FSK_NOW=2030-07-15`, puerto 18599 / PG 5446):
   - **Cableado** → `access_control_check.py` EXIT 0: los 10 asserts `[patch]` verdes (cada campo round-trippea,
     el NO-pacheado intacto, tipo equivocado → 400) + todos los hermanos s9.
   - **Saboteado** (borrar `patch.purchaseCost?.let { sets[ASSETS.PURCHASE_COST] = it }` + `installDist`) → EXIT 1
     con **UN SOLO assert rojo**: `GET /{id} ve patch[purchase_cost]: esperaba 73.25, obtuvo 42.5`; los 9 campos
     restantes, el intacto, el 400 y todos los hermanos serve-all/ops/ownerless VERDES (server vivo) = teeth
     PRECISOS. Revertido (`ci --rederive` regenera la dist) → verde.
4. **`ci --rederive` == pin en clon limpio**: **snipeit 11/11** (yo) · **base 12/12 + assets 11/11** (segundo
   verificador — el subagente Sonnet se cortó por límite de sesión; los corrí yo) — **byte-neutro → SIN re-pin**
   (el proof_sha hashea el SET de checks/exits, no el artefacto; el diente vive dentro de `access_control_live`).
   base/assets NO son byte-idénticos (su AppServer/Repository ganan la maquinaria del patch) pero re-derivan ==
   su pin — el cambio GENERAL que la gate `generality` sanciona (memoria `anti-overfit-is-generality-gate`).
5. **`meta check` 6/6** (compile · docs · projection · isolation · **generality** · suite) · **`git diff
   src/metafactory + seed = 0`**.

**Diferido honesto** (cada uno su eje hermano, con autoridad para reabrir en el handoff siguiente): PUT de campos
**UNIQUE** (un valor chocado → 409, hay que decidir el código) · PUT de **refs** (validación de FK del PATCH /
reasignar una relación) · PUT/update de entidades **ownerless** (hoy sólo la entidad-con-dueño se monta con PUT) ·
auditar `restore` + ownerless (heredado de FSK-ACTIONLOG). **La EDICIÓN es ahora faithful** para los campos
escalares de la entidad-con-dueño. **NÚCLEO + SUPERFICIE + VALORES-DERIVADOS + UX + DEPLOY + AUDITORÍA + EDICIÓN
COMPLETOS.** Lo que RESTA es breadth de dominio (Kits, el tail no-dominio) + diferidos de red/arquitectura (push a
registry, EAV dinámico). Siguiente handoff: `FSK-PUT-UNIQUE-REFS` (cerrar los flecos de PATCH: UNIQUE→409 + refs).
