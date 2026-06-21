# Incremento FSK-CRUD-OWNERLESS — la capa VIVA deja de ser opt-in a `owned_by` (CRUD RBAC-only)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-21T18:33Z · cerrado 2026-06-21T19:28Z, commit `feat(fsk): FSK-CRUD-OWNERLESS`). Editar
> `factories/full-stack-kotlin/**` no-`.md` (codegen/spec/stations) exige un incremento abierto — el
> `increment_guard` elige el lifecycle por la RUTA editada (ADR-016). **Evidencia del cierre: §9 al final.**
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión
> anterior (que cerró FSK-FRONTEND-RENDER-LIST) con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (la decisión estratégica — leéla, no la saltees)

El backend FSK está VIVO y completo **para UNA entidad**: la que tiene `owned_by`. Toda la capa viva —el
`AppServer` HTTP, el cliente `create/get/list`, el `render<E>List`, el consumer e2e— es **opt-in a `owned_by`**:
el codegen elige `next((e for e in entities if e.get("owned_by")), …)` y monta SÓLO esa entidad. **El resto del
dominio no tiene capa viva**: genera al nivel de spec/contrato (s0→s8 verde) pero no hay server, ni CRUD, ni UI viva.

Por qué importa: el primer producto real, **Snipe-IT, tiene ~23 entidades y SÓLO `Asset` tiene dueño**. Las otras
~22 (Company, Manufacturer, Supplier, Category, Location, Depreciation, User, AssetModel, License…) son
**reference/ownerless** → hoy ninguna es usable a runtime. **Levantar el opt-in es el paso de MAYOR PALANCA hacia
un Snipe-IT usable** — más que el pulido de frontend (render en browser, form, Playwright), que sólo mejora la
única entidad que ya tiene capa viva. Esta es la dirección que el usuario aprobó: seguir con mejoras GENERALISTAS
de FSK que desbloqueen el DOMINIO, no que sobre-ajusten un slice.

**Hermano (NO este incremento, el siguiente):** **refs en el body** — muchas entidades ownerless tienen un ref
REQUERIDO (p.ej. `AssetModel.category_id`), y hoy `_input_fields` excluye refs y `_mutation_fns` LANZA ante un ref
requerido no-dueño. Eso desbloquea el espinazo relacional. **Este incremento NO toca refs**: arranca por las
entidades ownerless cuyos campos requeridos son TODOS escalares (Company/Manufacturer/Supplier/Category/User…).

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso: FSK genera, enforza acceso vivo, MUTA, lee el cuerpo, el cliente
CONSUME y RENDERIZA la lista viva — todo para la entidad con dueño):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, por-producto** (el sandbox de Bash mata gradle: exit 144).
**Mantené el cwd de Bash en la RAÍZ del repo** — un `cd` a un subdir FILTRA el cwd persistente y rompe el cierre
de turno (deadlock del hook `stop_proof`); usá paths absolutos o subshells `( cd … )`. Debe dar **PASS** (s0→s10).
RTM snipeit **22/23** (único UNSAT = REQ-F-007/s6 LLM keyless).

**2) Entendé el opt-in de HOY** (todo en `codegen/scaffold_product.py`). Buscá `owned_by` / `owned`:
- **`_app_server_kt`** (~L3186): `owned = next(e for e in ents if e.get("owned_by"))` → monta el `AppServer` para
  ESA entidad: `seedRows` (siembra el dueño + 1 fila suya), `modifyVerdict` (RBAC **+ ownership**), un único
  `PLURAL`, un único set de handlers (`_app_server_handlers`). El skeleton `_APP_SERVER_SKELETON` (~L3267) es
  **mono-entidad**: un `createContext(PLURAL)`, un `seedJson`, un `writeRoles()`.
- **`_client_consume_ts`** (~L803): `owned = next(...)`; emite `create<E>/get<E>/list<E>` SÓLO para el owned.
- **`_app_ts`** (~L2641): `e = next((x for x in entities if x.get("owned_by")), entities[0])`; `render<E>List` del owned.
- **`_consume_check_ts`** (~L3623) + `_CONSUME_CHECK_SKELETON`: el consumer e2e, mono-entidad (el owned).
- **`_input_fields`** (~L885): excluye refs. **`_mutation_fns`** (~L957): **LANZA** ante un ref requerido no-dueño.
- En la emisión (`build_files`, ~L3903 / `_emit`): el bloque `if owned:` agrega `endpoints/AppServer.kt` +
  `frontend/consume_check.ts`. Sin owned, nada de eso se emite.

**3) EL DATO QUE LO CAMBIA TODO:** una entidad **ownerless** no necesita ownership — su `modifyVerdict` es **sólo
RBAC** (no hay dueño que cargar, no hay `OwnershipGuard`). El INSERT no setea `ownerId`; **todas** las columnas
escalares requeridas vienen del body (no hay campo que venga del token). Eso lo hace MÁS simple que el caso con
dueño, no más complejo — el guard se reduce a `RoleGuard.authorize(token, writeRoles)`.

---

## 1. Objetivo (qué deja TERMINADO este incremento)

La capa VIVA (server CRUD + cliente + render + consumer e2e) deja de ser opt-in a `owned_by`: **una entidad SIN
dueño también obtiene CRUD vivo, gobernado por RBAC** (rol prohibido → 403; permitido → 201 + INSERT real;
GET lista/`{id}`; DELETE). Demostrado e2e sobre la PG viva, con el MISMO rigor que el caso con dueño.

**Scope acotado (recomendado, decidilo vos):** mountá la **primera entidad ownerless cuyos campos requeridos son
TODOS escalares** (sin ref requerido) **y que tenga `write_roles`** (para el diente RBAC). Heurística DATA-agnóstica
(cero nombres de dominio): `next((e for e in entities if not e.get("owned_by") and e.get("write_roles") and not
any(f["type"]=="ref" and f.get("required",True) for f in e["fields"])), None)`. En los 3 productos existe: default→
`User`, assets→`Holder`, snipeit→`Company`. **Refs requeridos en el body = el incremento HERMANO (difiérelo acá).**

**Decisión de arquitectura (la parte de fondo — resolvela GENERAL):** ¿generalizás el `AppServer` a **N entidades
servidas** (lista `[owned (con ownership)] + [ownerless-scalar (RBAC-only)]`, cada una con su `createContext`,
`seedRows`, handlers), o agregás **un 2º contexto** aditivo junto al existente? RECOMENDACIÓN: el 2º contexto
aditivo como PRIMER paso (menos superficie, menos riesgo; el owned server queda intacto → sus dientes no se
mueven), dejando la generalización a N como pulido posterior. Lo que importa para el cierre: que una entidad
**sin dueño** tenga CRUD vivo RBAC-only probado e2e.

---

## 2. Deliverable + el DIENTE e2e (de dos lados, no decorativo)

**(a) Server** — para la entidad ownerless elegida: rutas vivas `GET /<plural>` (count+rows[]), `GET /<plural>/{id}`,
`POST` (RBAC → 201 + INSERT del body, type-coerced), `DELETE /<plural>/{id}` (RBAC). `modifyVerdict` ownerless =
sólo `RoleGuard.authorize`. `seedRows` siembra ≥1 fila (sin dueño). REUSÁ `_input_data_class`, `_body_codec`,
`_row_json_fn`, `all<E>RowsJson`, `_app_server_handlers` (parametrizándolos por entidad; hoy asumen el owned —
generalizá la firma, no dupliques). Pasa detekt (≤160/línea, ≤2 returns/fun, sin wildcard) + `-Werror`.

**(b) Cliente** — `create<E>/get<E>/list<E>` para la entidad ownerless (mismo patrón `fetch`+`res.ok`+narrow desde
`unknown`). El `create<E>` ownerless **no manda dueño** (no hay), manda todos los escalares requeridos.

**(c) Render + consumer** — `render<E>List` y el consumer e2e cubren también la entidad ownerless: round-trip
`create→get` + `list→render` (reusá el patrón de RENDER-LIST). **El diente RBAC nuevo:** un rol **PROHIBIDO** (fuera
de `write_roles`) → POST 403 y el count **NO cambia**; un rol permitido → 201 y count+1. Saboteá el guard (que un
rol prohibido pase) → rojo. Server caído → rojo (nativo infra_up).

**(d) Check** — RECOMENDACIÓN: extendé el consumer del check **`frontend_consume_live`** (s9, infra_up) para que
ejercite TAMBIÉN la entidad ownerless, **o** sumá un check hermano `crud_ownerless_live`. ⚠️ Ver §4 (re-materializar).

**RTM/spec:** capability nueva (p.ej. `crud_ownerless_live`, DES-3) + **REQ-F-019** citando el check; actualizá la
descripción del check si lo extendés. `validate` + `design-review` deben dar **0 problemas**.

---

## 3. Maquinaria a REUTILIZAR (no la reinventes)
- **`_input_data_class`/`_body_codec`/`parse<E>Input`** (~L896/L3023): el cuerpo type-coerced. Ownerless = TODOS los
  escalares requeridos del body (no hay dueño del token). Ya casi sirve — sacale el caso especial del owner.
- **`_row_json_fn` + `all<E>RowsJson`** (~L929/L_mutation_fns): serialización de fila/colección type-correct. Igual.
- **`_app_server_handlers`** (~L3088): `doPost/getOne/listAll/doDelete`. Hoy `doPost` setea el dueño del token y
  `modifyVerdict` chequea ownership; para ownerless, `doPost` NO setea dueño y el verdict es sólo RBAC. Parametrizá.
- **`RoleGuard.authorize`/`writeRoles()`** (auth/RoleGuard.kt + el RouteTable): el RBAC ya existe y está probado
  (FSK-S13). El server ownerless lo invoca igual; sólo NO compone `OwnershipGuard`.
- **El patrón de RENDER-LIST** (cliente `list<E>`, consumer `list→render`, `frontend_consume_live`): copialo.

## 4. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **⚠️ Re-materializar el chasis (SÓLO si sumás/quitás un CHECK):** el `proof_sha` de un gate es
  `hash(station_id + sorted(check_name, exit))`. Si agregás un check NUEVO (p.ej. `crud_ownerless_live`), las
  instancias (`assets`/`snipeit`) re-materializan su línea solas (`ensure_product_instance`), pero el producto
  **DEFAULT usa el `stations/` COMMITEADO** y `product-run` NO lo re-materializa → su `s9` queda en el sha viejo y
  `ci --rederive` pasa ENGAÑOSAMENTE sin ejercer el tooth. Receta (la usó FSK-FRONTEND-CONSUME): re-materializá el
  chasis a mano (`from metafactory.codegen.renderer import _materialize_line` sobre el factory root con el spec
  subst) → `git checkout` la churn cosmética de `s0.yml` → `product-run` default → `pin` default. **Si EXTENDÉS el
  consumer de un check EXISTENTE** (sin sumar check) → el `proof_sha` NO cambia → **NO hace falta** (así fue
  RENDER-LIST: pines byte-idénticos). PREFERÍ extender el check existente si podés.
- **Server vivo por `java -cp build/install/<pkg>/lib/*`, NUNCA `gradle run`** (el daemon forkea el JVM → leak de
  puerto). Ya cableado en s9 (mirá los `up:` de `factory.spec.yml` ~L716/L724 y `stations/s9.yml`).
- **`proof_protect` DENIEGA tocar `.proof/` por shell (incluso leer)** → usá `meta rtm` / `meta recall`; el árbol
  generado (`products/<p>/build/product/...`) SÍ es legible.
- **Eyeball SIN gradle antes de cada corrida lenta:** emití los archivos a un temp (`scaffold_product.build_files(bp)`
  → escribí el dict) y `node --experimental-strip-types --check` sobre los `.ts`; para el Kotlin, leé el archivo y
  revisá tipos a ojo (un `it[<TBL>.ID]` es `Long?` en jOOQ → `!!` si una fn pide `Long`; lección de RENDER-LIST).
- **Puertos/PG por check, propios:** `observability_live` 18593 · `access_control_live` 18594/5436/fsk_s9_ac_pg ·
  `frontend_consume_live` 18595/5437/fsk_s9_fe_pg. Si sumás un check infra_up, dale puerto/contenedor PROPIOS.

## 5. Restricciones DURAS de FSK que SIGUEN vigentes
Token estático `Bearer <rol>:<principal>`. RBAC opt-in (`write_roles`), ownership opt-in (`owned_by`). El server
ownerless **no** compone ownership (no hay dueño) — sólo Auth→RBAC. `tsc --strict` + ESLint strict + `no-explicit-any`
+ ts-reset muerden `client.ts`; detekt + `-Werror` muerden el Kotlin; el consumer en `frontend/` NO se type-checkea.
**Refs requeridos en el body = DIFERIDO (incremento hermano).** Mantené el caso CON-dueño intacto (sus dientes no
se mueven).

## 6. Disciplina + dónde van los docs
- **Contenido de FÁBRICA GENERAL** (`codegen/scaffold_product.py` + `factory.spec.yml`): **cero nombres de dominio**,
  `git diff` de TODO `product.yml` = 0. El producto es DATA (ADR-012).
- **Anti-overfit real = el gate `generality` de `meta check`, NO `git diff src==0` literal.** Lo normal acá es NO
  tocar sustrato (`src/metafactory/`+`seed/`): todo cabe en codegen/spec. Si necesitás sustrato → incremento META
  aparte (`meta increment open <slug>`) + `generality` verde.
- **Docs**: historia de la FÁBRICA → `docs/{STATE.md,LOG.md}` (ADR-016); el meta STATE sólo se toca para marcar el
  hueco (lo refresca `meta checkpoint` si `projection` cae rojo). El gobierno de ESTE incremento → este doc (flip a
  CERRADO + §Evidencia al cerrar). **Commit = parte del trabajo (ADR-010), nunca lo preguntes**; trailers I-10
  (`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`).
- **Probá POR BLOQUEO** (igual que RENDER-LIST): `product-run` PASS en los 3 · `ci --rederive --all-products` == pin
  (los 3) · `meta check` 6/6 (`generality` verde) · `git diff product.yml` = 0 · idealmente `git diff
  src/metafactory/ + seed/` = 0. **No fakees verde.**

## 7. Criterio de cierre (demostrable, no narrable)
1. `product-run` PASS en los 3 (default·assets·snipeit). Una entidad **ownerless** tiene CRUD vivo: el consumer
   asevera el round-trip RBAC-only (rol prohibido → 403 sin INSERT; permitido → 201 + count+1; GET lista/`{id}`;
   DELETE) + (si reusás RENDER-LIST) `list→render` de esa entidad. Server caído → rojo.
2. **Diente de DOS lados verificado VIVO**: saboteá el guard RBAC del server ownerless (que un rol prohibido pase) →
   corré → confirmá ROJO **sólo** en el check del CRUD ownerless (hermanos s9 verdes) → revertí → verde.
3. `ci --rederive --all-products` == pin (los 3). `meta check` 6/6 (`generality` verde). `git diff product.yml` = 0.
   **Si sumaste un check: re-materializá el chasis + re-pineá el default** (§4) — verificá que los 3 pines comparten
   el `s9`. Si extendiste un check existente, NO hace falta (pines byte-idénticos).
4. El scope honesto se actualiza: STATE/LOG (fábrica) registran "CRUD ownerless RBAC-only ✅" y los huecos que
   QUEDAN (refs requeridos en el body · CRUD de TODAS las ownerless, no sólo la 1ª · render en browser · form ·
   deploy · Playwright · custom-fields) como próximos incrementos. Abrí el SIGUIENTE (decidí vos: **refs en el
   body** es el candidato natural) con su handoff autocontenido.

## 8. Contexto que ya está hecho (de dónde venís)
- **FSK-FRONTEND-RENDER-LIST ✅ (2026-06-21, commit `feat(fsk): FSK-FRONTEND-RENDER-LIST`)**: la UI renderiza la
  lista VIVA de la entidad con dueño — el server lista (`GET /<plural>` → `{count,rows[]}`), el cliente trae
  (`list<E>`) y `render<E>List` renderiza; el consumer asevera que el HTML refleja la colección viva. Extendió el
  check `frontend_consume_live` (sin check nuevo → pines byte-idénticos). Detalle: `docs/work/
  FSK-FRONTEND-RENDER-LIST-INCREMENT.md §Evidencia` + `docs/LOG.md` (2026-06-21T18:30Z).
- **El backend FSK está VIVO + CRUD + entrada tipada, y el frontend CONSUME + RENDERIZA — todo para la entidad CON
  DUEÑO.** Este incremento abre la capa viva al RESTO del dominio (ownerless), que es lo que un producto real
  (Snipe-IT, ~23 entidades, 1 con dueño) necesita para ser usable. El slot meta queda libre; la fábrica abre su
  propio incremento (ADR-016).

---

## 9. Evidencia del cierre (2026-06-21T19:28Z — demostrable, no narrable)

**Qué quedó hecho.** El server vivo (`AppServer`) monta TAMBIÉN la 1ª entidad **ownerless** servible
(`_live_ownerless`/`_live_entities`, DATA-agnóstico: **User**/**Holder**/**Company** en default/assets/snipeit) con
**CRUD RBAC-only** — handlers sufijados (`doPost<E>`/`listAll<E>`/`getOne<E>`/`doDelete<E>`/`handle<E>`), verdict
`RoleGuard.authorize` (sin `OwnershipGuard` ni `ownerId` del token), `Repository.insert<E>(ctx, input)` de TODOS los
escalares del cuerpo, codec compartido sobre la unión de entidades servidas (`_codec_helpers`). La entidad con dueño
quedó **intacta**. Decisión de arquitectura: **2º contexto aditivo** (lo recomendado en §1), no la generalización a N
(diferida). PUT/update ownerless **diferido** (sin PUT en el dispatch ownerless).

**Cómo se cierra el §7, por bloqueo (cada línea reproducible):**
1. **`product-run` PASS en los 3** (default·assets·snipeit) por la línea real de gradle s0→s10. Una entidad ownerless
   tiene CRUD vivo: el proof `access_control_check.py` (extendido) asevera el round-trip RBAC-only.
2. **Diente de DOS lados verificado VIVO**: saboteado el guard RBAC ownerless en el codegen (de forma que compila pero
   un rol prohibido pasa) → snipeit `product-run` **FAIL, s9 SHUT, `1/3 checks red: access_control_live`** con
   `observability_live` + `frontend_consume_live` **VERDES** → revertido → **PASS**. El diente muerde SÓLO la capa
   ownerless, no a los hermanos.
3. **`ci --rederive --all-products` 3/3 == pin** (default 11/11 · assets 10/10 · snipeit 10/10) · **`meta check` 6/6**
   (`generality` verde; `projection` re-sincronizada por `meta checkpoint`) · **`git diff product.yml` = 0** (los 3) ·
   **`git diff src/metafactory/ + seed/` = 0**. Como se **EXTENDIÓ** el check existente `access_control_live` (sin
   sumar check), el `proof_sha` **no cambió** → pines byte-idénticos, **sin re-materializar el chasis**.
4. **Scope honesto actualizado**: `docs/STATE.md` + `docs/LOG.md` registran "CRUD ownerless RBAC-only ✅" y los huecos
   que QUEDAN. Trazabilidad RTM: capability `crud_ownerless_runtime` (DES-3) + **REQ-F-019** citando el check → RTM
   default **24/24 COMPLETE**, assets/snipeit **23/24** (único UNSAT = REQ-F-007/s6 LLM keyless), **REQ-F-019
   SATISFIED**. El **SIGUIENTE** incremento (`FSK-REFS-IN-BODY`) queda **abierto** con handoff autocontenido.

**Anti-overfit**: el cambio vive 100% en `codegen/scaffold_product.py` + `factory.spec.yml` (DATA de la fábrica, cero
nombres de dominio); `generality` verde lo sanciona. El producto es DATA (ADR-012): `git diff product.yml` = 0.
