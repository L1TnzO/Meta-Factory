# Incremento FSK-ACTIONLOG — la bitácora de actividad polimórfica (toda mutación deja rastro)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO** (creado
> 2026-06-24T21:20Z · cerrado 2026-06-24T23:53Z).
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Lo escribió la sesión que cerró
> FSK-DEPLOY-APPSERVER-PG con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## ✅ Evidencia (cierre 2026-06-24T23:53Z)

**Construido GENERAL en `codegen/scaffold_product.py` (eje OPT-IN `audited: true` por-entidad). `git diff
src/metafactory + seed = 0`.** El sistema appendea una fila a la **tabla de SISTEMA `action_logs`** en CADA
mutación de una entidad auditada (create/update/delete + los verbos de DOMINIO checkout/checkin), ATÓMICA con la
mutación, con **SUJETO POLIMÓRFICO** (`subject_type` discriminador = el nombre de la entidad + `subject_id` Long,
sin FK a una unión — wrinkle #1, **COMPONE FSK-POLYMORPHIC-REFS**) + `actor_id` (el principal del token) +
`action` + `created_at`. Lectura por **`GET /action_logs`** (público, `{count,rows[]}`).

- **DECISIÓN de diseño — el append vive en el HANDLER, no en el Repository** (Approach B): la atomicidad se logra
  envolviendo `mutación + appendActionLog` en UNA transacción (`ctx.transaction{}` / `ctx.transactionResult{}` para
  el create que devuelve el id) DENTRO del handler, donde el ACTOR existe (el `principal`/`RoleGuard.principalOf`).
  Las funciones de mutación del Repository quedan **byte-idénticas** (cero cambio de firma) — sólo GANA
  `appendActionLog`/`actionLogCount`/`allActionLogRowsJson` + la tabla. Más quirúrgico que threadear el actor por
  cada firma. La capa del request es el lugar natural del actor.
- **Maquinaria tocada** (toda gateada por `audited`, byte-neutra sin la flag): `_migration_sql` (la tabla
  `action_logs`) · `_repository_kt` (append + lecturas + imports `ACTION_LOGS`/`LocalDateTime`) ·
  `_app_server_handlers` (+param `audited`: doPost/doPut/doDelete envueltos) · `_operations_handlers` (+param
  `audited`: helper `_op_ok` envuelve la rama de éxito de cada verbo, byte-idéntica sin la flag) · `_app_server_kt`
  (handler `handleActionLogs` + contexto `/action_logs`) · `_access_control_check_py` (el diente `%ACTIONLOG_BLOCK%`).
- **Probado por bloqueo, con MIS ojos**:
  - **Eyeball barato** (sin gradle): render snipeit con `audited:true` → migration con `action_logs`, Repository
    con `appendActionLog`, AppServer con los 5 appends (create/delete/update/checkout/checkin) + `/action_logs`,
    proof con el bloque; **0 líneas Kotlin >160**; **base + assets byte-IDÉNTICOS** (sin artefacto actionlog).
  - **`product-run --product snipeit` PASS**; RTM **25/26** (único UNSAT = REQ-F-007/s6 LLM keyless).
  - **Diente VIVO de DOS lados** (vs la dist compilada + PG real, `FSK_NOW=2030-07-15` como s9):
    **cableado** → los 5 asserts `[actionlog]` VERDES; `GET /action_logs` trae las filas reales (create/update/delete
    de `Asset:new_id` por el actor=dueño, sujeto polimórfico correcto). **Saboteado** (borrar el append del create +
    rebuild) → PROOF EXIT 1 con **0 fallas NO-actionlog** (sólo `[actionlog] create`/`>=3`/`actor` rojos; update y
    delete siguen verdes = teeth precisos); **revertido** → verde.
  - **Byte-neutro → NO re-pin**: el diente vive DENTRO de `access_control_live` (s9, check existente) → `proof_sha`
    intacto. **`ci --rederive --product snipeit` PASS 11/11 == pineado**. base/assets cross-check (2º verificador
    Sonnet) == pin. **`meta check` 6/6** (`generality`+`isolation` verdes).
- **Adopción en snipeit** (incremento PRODUCTO `SNIPEIT-ACTIONLOG-ADOPT`): `Asset.audited: true` → la feature
  ESTRELLA de Snipe-IT (Actionlog) viva. `restore` audita-diferido (eje hermano, residual honesto).

---

## 0. POR QUÉ este incremento (y por qué es el de MAYOR valor restante)

**EL NÚCLEO + LA SUPERFICIE + LOS VALORES-DERIVADOS + LA UX + EL DEPLOY (AppServer REAL en un contenedor con
PG sobre una red docker) están COMPLETOS.** De acá TODO es **profundidad de DOMINIO** (breadth) + diferidos de
red. La elección de MAYOR valor para una réplica Snipe-IT FIEL es **el Actionlog**: en Snipe-IT, TODA acción
(checkout, checkin, edición, creación, borrado) deja una fila de auditoría — quién hizo qué, a qué cosa, cuándo.
Es una feature ESTRELLA del producto y, como mecanismo de fábrica, es **GENERAL**: "el sistema appendea una
fila de auditoría en cada mutación, con SUJETO POLIMÓRFICO". **COMPONE FSK-POLYMORPHIC-REFS** (ya construido: el
sujeto auditado es una unión de entidades) **+ FSK-DOMAIN-OPS** (los verbos checkout/checkin también auditan) sin
inventar arquitectura nueva. Acotado: una llamada de append por cada camino de mutación.

**⚠️ ESTA ES TU DECISIÓN (con más contexto).** Lo elegí como el de mayor valor-dominio restante, pero en §7 hay
alternativas honestas con AUTORIDAD para reabrir si al investigar preferís otro orden.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥600000ms** (el sandbox mata
gradle). **cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del hook
`stop_proof`; usá `cd <raíz> && …`). Debe dar **PASS**, RTM snipeit **25/26** (único UNSAT = REQ-F-007/s6 LLM
keyless).
⚠️⚠️ **Puertos vivos en uso**: s9 PG 5436/5437/5438 + servers 18593-18595/18597; s11 18596 (smoke ObsServer) +
18598 (AppServer-en-contenedor) + PG en la red `fsk_s11_net` (sin puerto al host). NUNCA dos corridas en paralelo
(nombres de contenedor FIJOS: fsk_s9_*, fsk_s11_*). El Actionlog NO necesita infra nueva (es codegen + la PG que
ya levantan s9/s11).

**2) ENTENDÉ la maquinaria EXISTENTE que vas a COMPONER (verificá anchors con grep — el archivo se mueve):**
Todo vive en `factories/full-stack-kotlin/codegen/scaffold_product.py`.
- **El AppServer** (`_app_server_kt`, ~5170): el server HTTP vivo. Sus HANDLERS de mutación son donde se appendea
  la auditoría: POST (crear), PUT (editar), DELETE (`_handle`/`_ownerless_handlers`/`_operations_handlers`), y los
  VERBOS de dominio (checkout/checkin, FSK-DOMAIN-OPS, `_operations_handlers`). Cada uno es un punto de append.
- **El Repository** (`_repository_kt`, grep `def _repository_kt`): el INSERT/UPDATE/DELETE jOOQ tipado. La fila de
  audit se puede insertar acá (un `appendActionLog(ctx, actor, action, subjectType, subjectId)`) o en el handler.
- **FSK-POLYMORPHIC-REFS** (grep `_owner_poly`, `POLYMORPHIC`, `<f>_type`/`<f>_id`): el sujeto auditado es POLI —
  se materializa en DOS columnas `subject_type` (discriminador enumOf de las entidades) + `subject_id` (Long). YA
  sabés hacer esto (lo hace `owned_by` poly y los refs poli). REUSÁ ese patrón.
- **FSK-SOFT-DELETES** (grep `soft_delete`, `deleted_at`): el patrón de una COLUMNA DE SISTEMA agregada por el
  motor (no del dominio) — el Actionlog es una TABLA de sistema (`action_logs`) con el mismo espíritu: la declara
  el blueprint con un flag, no el usuario campo-a-campo.
- **El migration SQL** (`_migration_sql`, grep `def _migration_sql`): acá nace la tabla `action_logs`
  (id, created_at, actor_id, action, subject_type, subject_id). Versionada por Flyway como el resto.
- **El seed/diente de los handlers** (`_OPERATIONS_PROOF`, `access_control_check.py`, `_access_control_check_py`):
  el proof e2e que postea/edita/verbo-ea contra el AppServer vivo. ACÁ agregás: tras una mutación, GET
  `/action_logs` (o `/<subject>/<id>/history`) y asevera que apareció la fila de auditoría correcta.

**3) EL DISEÑO (GENERAL, cero nombres de dominio):**
   - El blueprint declara, a NIVEL ENTIDAD o GLOBAL, un flag tipo `audited: true` (o `action_log: {...}`) → el
     motor emite una tabla de SISTEMA `action_logs` + un append en cada mutación de las entidades auditadas. El
     `action` (string: "create"/"update"/"delete"/"<verb>") y el actor (el principal del token) son DATA del
     contexto; el sujeto es POLIMÓRFICO (type+id). DECISIÓN tuya: ¿auditar TODAS las entidades servibles, o sólo
     las marcadas? (recomendado: opt-in por flag → byte-neutro para default/assets que no lo declaran, como todo
     eje OPT-IN de FSK; snipeit lo activa para Asset y los verbos).
   - Una RUTA de lectura: `GET /action_logs` (público o RBAC) → `{"count":N,"rows":[…]}` con la forma habitual
     (cada fila vía un `actionLogRowJson`). Opcional: `GET /<plural>/<id>/history` (la auditoría de UNA fila).
   - El append es ATÓMICO con la mutación (misma transacción: si la mutación commitea, su audit-row también; si
     rollback-ea —p.ej. FK colgante→409—, la audit NO queda). REUSÁ `ctx.transactionResult{}` (ya lo usa
     FSK-CREATES-PIVOT — grep `transactionResult`).

**EL DIENTE de dos lados (VIVO contra el AppServer + PG real):**
   - **Verde**: POST/PUT/verbo una entidad auditada → GET `/action_logs` trae la fila NUEVA (actor correcto,
     action correcta, subject_type+subject_id = la entidad mutada). count N→N+1.
   - **Saboteá**: NO appendees en el handler de PUT (o garbleá el `subject_type`/`action`) → la audit-row falta o
     es incorrecta → **SÓLO el assert de Actionlog rojo**, hermanos verdes → revertí → verde.
   - **Atomicidad** (bonus): una mutación que ROLLBACK-ea (FK colgante → 409) NO debe dejar audit-row → asevera
     que el count NO subió tras un 409.

---

## 1. RE-PIN — depende de tu forma de probar (LEÉ ESTO)
`compute_proof_sha` (`seed/verifier.py`) hashea `station_id + sorted (check_name, exit)`. **Si NO agregás un
check nuevo** (el diente del Actionlog vive DENTRO de un check existente — p.ej. `access_control_live` de s9, que
ya ejercita mutaciones vivas) → **proof_sha byte-neutro → NO re-pin** (el ideal: extendés un check, no agregás).
**Si agregás un check/estación nuevos** → el set de s9 (o sN) cambia → re-pin de los 3. **Recomendación**: meté
el assert de auditoría DENTRO de `access_control_check.py` (el proof que ya postea/edita vivo) → byte-neutro, sin
re-pin (igual que FSK-COMPUTED-FIELDS/SOFT-DELETES extendieron el proof sin re-pinear). Si por aislamiento de
atribución preferís un check propio, re-pineá los 3 (flujo en §3).

## 2. Lecciones CARAS ya destiladas (de FSK-DEPLOY-APPSERVER-PG + las previas)
- **OPT-IN o nada**: un eje GENERAL debe ser byte-neutro cuando el blueprint NO lo declara. Confirmá `git diff` de
  los artefactos generados de **default + assets = 0** salvo lo que toque su flag (acá: nada, no lo declaran).
- **El sujeto polimórfico** = 2 columnas (`subject_type` discriminador + `subject_id` Long), enumOf de las
  entidades auditadas, fail-closed si el discriminador no matchea. YA lo hacés (owner-poly, refs-poli).
- **Atomicidad por `ctx.transactionResult{}`**: el append + la mutación en la MISMA tx (FSK-CREATES-PIVOT es el
  molde — un INSERT extra atómico con la mutación principal).
- **VALIDÁ BARATO ANTES DE GRADLE** (≈10s): adaptá `scratchpad/eyeball.py` (carga el scaffold working vs HEAD,
  `build_files` para base/assets/snipeit, diffea claves + chequea 0 líneas Kotlin >160). Para un eje OPT-IN,
  base/assets quedan byte-IDÉNTICOS.
- **El diente VIVO se corre MANUAL y RÁPIDO** contra la dist viva (`products/snipeit/build/product`): levantá PG
  en docker + el AppServer por `java -cp 'build/install/snipeit/lib/*' snipeit.endpoints.AppServerKt` con
  `FSK_AC_PORT`/`FSK_PG_URL`, esperá `/health` con `curl --retry 60 --retry-connrefused`, postea/edita y GET
  `/action_logs`. **`infra_up` NO surfacea el stdout del proof** → corré el proof MANUALMENTE para ver el assert.
- **ktlint/detekt al escalar** (cada uno mordió un eje): MaxLineLength 160 · PropertyWrapping >120 (un `val x=…`
  largo se envuelve) · NoMultipleSpaces (un doble-espacio antes de `//` enrojece s2) · MagicNumber (literal 3+) ·
  ReturnCount≤2 · CyclomaticComplexMethod≤15 · LongMethod≤60 · @Suppress(LargeClass) si la clase pasa 600. El
  emisor GENERADO exhaustivo se @Suppress-ea por TAMAÑO (opt-in), no a mano.
- **`ci --rederive` opera sobre el ÁRBOL DE TRABAJO** (borra `.proof/`+`build/`, re-deriva in-place; NO clona
  git). UNO A UNO (cada uno <10min, cabe en un Bash de 600000ms) o `--all-products` (>10min → background o
  delegá). **Delegá las corridas pesadas a un subagente Sonnet** — pero escribí el codegen + el diente con TUS
  ojos. **proof_protect DENIEGA tocar `.proof/` por shell** — usá `meta rtm`. (⚠️ OJO: `ci` SIN `--rederive` NO es
  un read barato — re-ejecuta los checks vivos; no esperes que sea instantáneo.)

## 3. Re-pin (SÓLO si agregás check/estación) + disciplina (ADR-016)
1. Editá `factory.spec.yml` (la estación gana el check) **y** sincronizá el `stations/<id>.yml` committeado a mano
   (⚠️ editar `station_sequence` re-materializa los PRODUCTOS pero NO el base committeado `stations/<id>.yml` —
   renderealo del spec con `package_name=webapp` y diffea: sólo tu check nuevo debe aparecer; ver cómo lo hizo
   FSK-DEPLOY-APPSERVER-PG con un script de render del nodo s11, en su §Evidencia/scratchpad).
2. `product-run` base + assets + snipeit PASS (uno a uno).
3. `meta pin --factory full-stack-kotlin` (base) + `--product assets` + `--product snipeit` (3 pins).
4. `ci --rederive` por producto == el pin NUEVO (base 12 · assets 11 · snipeit 11, +1 si check nuevo).
- **El codegen es nivel FÁBRICA → ESTE incremento** (header ABIERTO). Si tocás `products/snipeit/product.yml`
  (para activar el flag `audited` en snipeit) abrí TAMBIÉN `meta increment open --factory full-stack-kotlin
  --product snipeit <slug>` ANTES (el product.yml es nivel PRODUCTO, ADR-016).
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) con el incremento ABIERTO, luego `docs(fsk): cerrar
  FSK-ACTIONLOG (§Evidencia) + abrir <siguiente>` flippeando el header a CERRADO.

## 4. Criterio de cierre (demostrable, no narrable)
1. Una entidad auditada, al mutarse (POST/PUT/DELETE/verbo) por el AppServer vivo, **appendea una fila de
   `action_logs`** con actor + action + sujeto POLIMÓRFICO correctos; `GET /action_logs` la trae (count N→N+1).
   `product-run --product snipeit` **PASS**.
2. **Diente de DOS lados verificado VIVO**: suprimí/garbleá el append → SÓLO el assert de Actionlog rojo,
   hermanos verdes → revertí → verde. (+ atomicidad: un 409 NO deja audit-row.)
3. EYEBALL · (re-pin SÓLO si check nuevo) · `ci --rederive` por producto == pin · `meta check` 6/6 (`generality`
   verde) · `git diff src/metafactory + seed = 0`.
4. STATE/LOG (fábrica) + SNIPEIT-DOMAIN (Actionlog fuera de los diferidos) actualizados. Abrí el SIGUIENTE con su
   handoff (§7).

## 5. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento)
- **push de la imagen a un registry** — el ÚLTIMO diferido DURO de DEPLOY (necesita un registry local hermético;
  ⚠️ requiere `registry:2` cacheado para que `ci --rederive` sea offline — verificá ESO primero). Cierra el ciclo
  de deploy completo.
- **PUT de campos opcionales arbitrarios** — el MÁS bounded (hoy PUT actualiza los campos requeridos del input;
  los opcionales no son PUT-eables). COMPONE FSK-CRUD-BODY-PARSING.
- **Kits (bundles)** — un Kit agrupa assets/accesorios/licencias que se checkout-ean juntos. COMPONE
  FSK-CREATES-PIVOT.
- **EAV dinámico (Avenue B)** — custom-fields definidos a RUNTIME (vs el schema build-time-typed jOOQ). Cambio de
  ARQUITECTURA, no aditivo. El de MAYOR esfuerzo.
- el largo tail de ~226 rutas operacionales no-dominio (counters, image-upload, LDAP, 2FA).

## 6. ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El backend faithful (modelo·acceso·comportamiento·valores-derivados incl. tiempo) está COMPLETO, la app CORRE,
TODAS las entidades se sirven, el frontend se VE y se SUBMITEA en un navegador REAL, y DEPLOYA DE VERDAD (el
AppServer con su PG en un contenedor sobre una red docker).** Tras el Actionlog, la auditoría —feature estrella—
está. Lo que RESTA es breadth de dominio (Kits, PUT-opcionales, el tail no-dominio) + diferidos de red/arquitectura
(push a registry, EAV dinámico). **No queda ningún hueco de NÚCLEO, SUPERFICIE, VALORES-DERIVADOS, UX ni DEPLOY.**

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE (con AUTORIDAD para reabrir)
Si al investigar preferís otro eje (cualquiera es legítimo; reabrí con `meta increment`):
- **FSK-PUT-OPTIONAL** — el más bounded/rápido (un quick win de CRUD). Bueno si querés un incremento corto.
- **FSK-DEPLOY-PUSH-REGISTRY** — cierra el eje DEPLOY (registry local hermético; ⚠️ verificá `registry:2`
  cacheado ANTES — si no, la hermeticidad de `ci --rederive` se rompe).
- **FSK-KITS** — bundles (M:N agrupado), domain breadth, compone FSK-CREATES-PIVOT.
- **EAV dinámico** — el de mayor esfuerzo/riesgo (cambio de arquitectura).
