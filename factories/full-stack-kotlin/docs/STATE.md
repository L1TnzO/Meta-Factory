# Estado — Full-Stack Kotlin/TS/PG Factory
> tipo: estado · fábrica generada por el Meta-Factory · esquema heredado ADR-021 (overwrite)
> Este doc APUNTA; la verdad verificable vive en artefactos (.proof/, ledger, RTM re-derivado).

## Ahora
- Fábrica **full-stack-kotlin** recién nacida por la línea M0–M8 del Meta-Factory. Produce: una app web full-stack de grado-producción: contrato OpenAPI tipado como fuente única, backend Kotlin, frontend TypeScript/React, base de datos PostgreSQL con esquema versionado (Flyway) y queries chequeados en compilación (jOOQ), verificada ENTERA en su propio toolchain bajo criterios duros de ingeniería (dureza estática, frescura de API, seguridad de la cadena de suministro, calidad de experiencia, observabilidad), 100%-generada desde este spec..
- Hereda el sustrato de toda fábrica confiable (columna anti-sello, bus de veredictos, RTM,
  dos verificadores) cableado por construcción — no re-derivado a mano.
- **Expresividad madura (R2/FSK-S11..S16 + CRUD-BODY-PARSING)**: 8 tipos de campo + opcionalidad · workflows
  (máquinas de estado) · RBAC por rol · ownership a nivel de fila · **control de acceso a RUNTIME** (server HTTP
  vivo que invoca Auth→RBAC→Ownership sobre requests reales vs PostgreSQL viva) · **CRUD-mutación real** (FSK-S16:
  POST/PUT/DELETE jOOQ tipado bajo el control de acceso, diente ROUND-TRIP) y, desde **FSK-CRUD-BODY-PARSING
  (2026-06-21)**, **entrada tipada a RUNTIME**: ese server lee el **CUERPO real** del request y lo persiste
  **type-coerced por el schema** (POST inserta los valores del body, GET /{id} devuelve la fila completa
  type-correct, PUT actualiza del body; body malo → 400, fail-closed) vía `kotlinx.serialization.json`. Detalle e
  historia: `docs/LOG.md`.
- **Frontend que CONSUME el backend vivo (FSK-FRONTEND-CONSUME, 2026-06-21)**: el **cliente TS GENERADO** dejó de
  ser funciones puras — `client.ts` gana `create<E>`/`get<E>` que hacen **`fetch` REAL** contra el AppServer vivo
  (type-bound al contrato: `Pick<components["schemas"][<E>]>` → un drift rompe `tsc --strict`, DES-6; `res.json()`
  narrow desde `unknown`, DES-10). Un consumer node (`consume_check.ts`) los IMPORTA y corre el **round-trip e2e**
  (`create<E>` POST → `get<E>` GET → cada campo vuelve EXACTO type-correct) por `node --experimental-strip-types`,
  verificado por un **3er check `frontend_consume_live`** (infra_up) en s9. `fetch` global → sin dep nueva (ADR-012).
- **Frontend que RENDERIZA la lista VIVA (FSK-FRONTEND-RENDER-LIST, 2026-06-21)**: el render generado dejó de ser
  una función que **nadie alimentaba**. El server **LISTA las filas** (`GET /<plural>` → `{"count":N,"rows":[…]}`,
  backward-compat, cada fila vía `Repository.all<E>RowsJson` que REUSA `<e>RowJson` type-correct), el cliente las
  **TRAE** (`list<E>(): Promise<<E>[]>`, narrow desde `unknown`, DES-10) y **`render<E>List`** (ya type-bound al
  contrato; ahora apunta a la entidad **CON DUEÑO**, la única con capa viva) las **renderiza** a markup. El consumer
  (`consume_check.ts`) trae la lista viva y **asevera que el HTML la refleja** (cada fila, incl. la recién creada;
  un render que dropea/garbla/hardcodea → HTML ≠ lista viva → rojo). Extiende el MISMO check `frontend_consume_live`
  (sin check nuevo → `proof_sha` intacto, pin byte-idéntico). RTM snipeit **22/23** (REQ-F-018, capability
  `frontend_render_live`). Diente de dos lados verificado VIVO.
- **EL SUBMIT DEL FORM EN UN CHROMIUM REAL — la UX end-to-end COMPLETA (FSK-FORM-BROWSER-E2E, 2026-06-24)**: el
  frontend ya se RENDERIZABA en un Chromium real (FSK-FRONTEND-BROWSER: la lista viva como `<li>` en el DOM real),
  pero el **SUBMIT del FORM** (el usuario CREA una fila desde el navegador) sólo se probaba en **jsdom**
  (`_browser_form_block` de `consume_check.ts`). Ahora `browser_check.ts` (s9, check `frontend_browser_live`,
  Playwright) gana una **fase de SUBMIT**: LLENA los `<input>` del FORM generado (`page.fill`/`page.check` por
  `[name]`), dispara el submit y asevera que la fila NUEVA aparece en el **DOM REAL** (count `<li>` N→N+1 + el valor
  posteado visible). El handler async del bundle corre EN EL NAVEGADOR REAL: preventDefault + `create<E>` (POST por
  la red) + re-render. `FORM_BODY` = el MISMO dato que el bloque jsdom (escalares por `_proof_form_value` + refs
  no-dueño de `/seed.ownedRefs`); el token de ESCRITURA lo arma el bundle (`browser_entry.ts`) → el submit pasa
  RBAC/ownership. **Lección CARA**: clickear el `<button submit>` de un FORM SIN `action` dispara una navegación GET
  que RECARGA la página ANTES de que el handler async termine (falso rojo) → se dispara el **evento `submit` directo**
  (el MISMO `dispatchEvent` que el jsdom) vía `page.evaluate`, que el sistema de eventos REAL del browser procesa sin
  esa carrera. **Anti-overfit**: todo en `codegen/scaffold_product.py` (FÁBRICA, GENERAL — los 3 productos ganan la
  fase IDÉNTICA); **`git diff src/metafactory + seed = 0`**; **proof_sha byte-neutro** (extiende el check, no agrega →
  **SIN re-pin**). **Probado por bloqueo**: EYEBALL (sólo `browser_check.ts` cambia, 0 Kotlin >160) · `product-run`
  snipeit PASS · RTM snipeit **25/26** (REQ-F-020 `frontend_browser_render`) · **diente VIVO dos-lados** (saboteado el
  re-render del submit → SÓLO los 2 asserts del submit rojos, los de render verdes; `esperaba 4 obtuvo 3`;
  revertí→verde) · `ci --rederive --all-products` **3/3 == pin** (12·11·11) · `meta check` 6/6. **La UX del frontend
  está COMPLETA end-to-end** (render + submit en un browser REAL). Detalle:
  `docs/work/FSK-FORM-BROWSER-E2E-INCREMENT.md §Evidencia` · `docs/LOG.md`. Siguiente: `FSK-DEPLOY-APPSERVER-PG` (el
  AppServer REAL en un contenedor con PG — el último gran hito de deploy).
- **VALORES DERIVADOS COMPLETOS — un campo computado depende del TIEMPO transcurrido (FSK-TIME-COMPUTED, 2026-06-24)**:
  el AST de un campo computado gana el operando de TIEMPO `months_since(<campo date>)` = los MESES entre una fecha y
  `now`. `Asset.current_value` (snipeit) dejó de ser una constante por-modelo y se volvió la depreciación straight-line
  REAL `max(purchase_cost − (purchase_cost/model_id.depreciation_id.months) * months_since(purchase_date), 0)` — BAJA con
  el tiempo. **El wrinkle `now` no-determinista** se resuelve por MOCK (`FSK_NOW`, el server lo lee, default = hoy real) +
  SINGLE-SOURCE: el server EXPONE `now` por `/seed` → el oráculo del proof lo LEE de ahí, sin literal duplicado (cero
  drift). `monthsSince`=`ChronoUnit.MONTHS.between`; el oráculo Python lo espeja. Extiende, no reescribe: op de tiempo en
  un set cerrado fail-closed (arg = campo `date`), `today`/`monthsSince` miembros opt-in del Repository, rowJson +
  oráculo opt-in. Surfaceó **ktlint PropertyWrapping (>120 ≠ MaxLineLength 160)** → el computed-val se envuelve a 120; y
  la línea `Seed(...)` con `now` pasó de 160 → se arma como lista + se envuelve con `_kt_call`. **Probado por bloqueo**:
  base/assets **byte-IDÉNTICO**; `product-run` snipeit PASS (RTM 25/26); **diente vivo dos-lados** (`MONTHS`→`YEARS` →
  SÓLO `[computed]` rojo: 1 rojo / 178 verdes, server vivo) + **bonus** (dos `FSK_NOW` → `42.5` vs `21.25`, prueba que
  `now` entra); `ci --rederive --all-products` == pin (12·11·11, **SIN re-pin**: proof_sha exit-code-based); `meta check`
  6/6; **`git diff src/metafactory + seed = 0`**. **La dimensión de VALORES DERIVADOS (same-entity + cross-entity depth-N
  + tiempo) queda COMPLETA.** Detalle: `docs/work/FSK-TIME-COMPUTED-INCREMENT.md §Evidencia` · `docs/LOG.md`. Siguiente:
  `FSK-FORM-BROWSER-E2E` (el submit del FORM en un Chromium real).
- **TODO EL DOMINIO USABLE A RUNTIME — la última superficie del backend faithful (FSK-SERVE-ALL-ENTITIES, 2026-06-24)**:
  el AppServer vivo dejó de montar CRUD para sólo **3 entidades representativas** (la con dueño + la 1ª ownerless + la 1ª
  with_ref) y ahora monta CRUD RBAC/ownership-aware para **TODAS las entidades servibles** → **snipeit sirve 18** (era 3).
  Camino BOUNDED: se generaliza la SELECCIÓN, no se reescribe el server. `_servible_ownerless` (toda ownerless con
  `write_roles`+cuerpo POSTeable, MENOS las pivotes `creates` —ya servidas vía su verbo padre—) alimenta `_live_entities`
  (fuente única Repository↔AppServer); las primarias (ownerless/with_ref) siguen gobernando el seed + los dientes
  especiales (qty/creates/poly) **byte-estables**; las `extras` se montan con `_ownerless_handlers` (ya parametrizado,
  `catch_fk` si tienen ref requerido) + un contexto c/u. El proof gana un bloque `serve-all` (opt-in) que ejercita de DOS
  lados las escalares-solo NUEVAS (snipeit: 7) por POST fresco sin seed/FK. 3 gaps ktlint a escala arreglados GENERAL
  (enum VALUES largo→`_kt_call`; `all<E>RowsJson` lambda-chain→budget `PROPERTY_WRAP`; `object Repository`→`@Suppress
  ("LargeClass")`), opt-in por tamaño. **Probado por bloqueo**: assets **byte-IDÉNTICO** (ya servía todo), base gana Task;
  `product-run` snipeit+base PASS; **diente vivo dos-lados** (saboteado `writeRolesManufacturer` → SÓLO sus 2 aserciones
  rojas, hermanas verdes); `ci --rederive --all-products` **3/3 == pin** (12·11·11, **SIN re-pin**: proof_sha exit-code-
  based, extiende checks existentes sin agregar); `meta check` 6/6; **`git diff src/metafactory + seed = 0`**. **Con esto
  el backend faithful está COMPLETO de SUPERFICIE**; lo que resta es profundidad-de-detalle. Detalle:
  `docs/work/FSK-SERVE-ALL-ENTITIES-INCREMENT.md §Evidencia` · `docs/LOG.md`. Siguiente: `FSK-TIME-COMPUTED`.
- **FRONTEND EN UN BROWSER REAL — el 1er eje de BREADTH tras el núcleo (FSK-FRONTEND-BROWSER, 2026-06-24)**: el frontend
  GENERADO dejó de probarse SÓLO en jsdom y se monta en un **Chromium HEADLESS REAL** (Playwright). El AppServer gana
  `GET /` (una página mínima) + `GET /app.js` (sirve el bundle desde disco vía `FSK_WEB_DIR`) → MISMO-ORIGEN (sin CORS);
  un entry de bundle (`frontend/src/browser_entry.ts`, type-checked por `tsc --strict`) importa `mount<E>` y al cargar la
  página REAL lo invoca contra `location.origin` → trae la lista VIVA (`GET /<plural>`, PG real detrás) y la renderiza en
  el **DOM REAL** del navegador; esbuild (`build_bundle.mjs`, ya dep de s8) lo bundlea a un IIFE + escribe `index.html`. El
  proof (`frontend/browser_check.ts`) maneja Chromium vía **`playwright-core`** (rev pineada 1217; binario en
  `~/.cache/ms-playwright`, precondición de entorno como docker) y asevera que cada fila viva (mismo `GET /<plural>` que
  `mount<E>`) aparece como `<li>` en el DOM real. **4º check infra_up de s9 `frontend_browser_live`** (server 18597 + PG
  5438 + el bundle). Diente de DOS lados VIVO (degradar `render<E>List` → la fila no aparece en el DOM real → SÓLO el
  check nuevo rojo, "lista viva ≥1" verde = server/data vivos; verificado contra la dist real). **Anti-overfit**: todo en
  `codegen/scaffold_product.py` + `factory.spec.yml` (FÁBRICA, GENERAL — los 3 productos ganan la misma capa IDÉNTICA,
  cero nombres de dominio); **`git diff src/metafactory + seed = 0`**. RTM snipeit **25/26** (REQ-F-020, capability
  `frontend_browser_render`, DES-7). **Con el núcleo COMPLETO, éste abre la BREADTH; el siguiente eje grande de superficie
  = servir TODAS las entidades** (`docs/work/FSK-SERVE-ALL-ENTITIES-INCREMENT.md`). Detalle:
  `docs/work/FSK-FRONTEND-BROWSER-INCREMENT.md §Evidencia` · `docs/LOG.md`.
- **OWNER POLIMÓRFICO — el ÚLTIMO gap de MODELO+AUTH (FSK-OWNER-POLY, 2026-06-24): NÚCLEO COMPLETO.** El campo
  `owned_by` de una entidad puede ser un ref POLIMÓRFICO → el dueño de la fila cruza una UNIÓN `(tipo, id)` en vez de
  un `Long` único (wrinkle #3, CERRADO). Camino BOUNDED que COMPONE FSK-OWNERSHIP-OPTIONAL + FSK-POLYMORPHIC-REFS,
  cero modelo nuevo de auth: un owner de tipo NO-principal (Location/Asset) ≡ owner NULL → sólo bypass modifica. El
  gating vive en `modifyVerdict` (**`effectiveOwnerId = ownerType == targets[0] ? ownerId : null`**) → `OwnershipGuard.
  canModify` (Long?) queda **INTACTO** (reusa el branch owner-NULL). Cambios GENERALES opt-in byte-neutro en
  `scaffold_product.py`: gramática (levanta la restricción wrinkle #3), `_repository_kt` (`<e>OwnerId` lee `<owner>_id`
  + nuevo `<e>OwnerType`), `_modify_verdict_kt` (lee tipo, gatea id), `_mutation_fns` (POST fija type=principal/id),
  `_seed_chain` (siembra type+id; la 2ª fila = tipo NO-principal, **mismo id = el diente**), `_test_ownership_guard_kt`
  (cruza `<owner>_id` Long?). **Decisión (con más contexto): NO se fusionó `assigned_to`↔`checkout_target`** — el verbo
  `checkout` reasignaría el dueño y rompería el proof de operaciones (el checkin por el dueño daría 403); y es más
  honesto (el editor de un activo ≠ su holder). **Adopción PRODUCTO**: snipeit `Asset.assigned_user_id` → `assigned_to`
  poly `[User, Location, Asset]` = `owned_by`. Diente de DOS lados VIVO y PRECISO (degradé el gate de tipo → la fila
  asignada a una Location se vuelve "del actor" → "PUT RTD por no-bypass → 403" se vuelve 200, SÓLO en
  `access_control_live` (s9), server VIVO, hermanas verdes; revertí→verde). **product-run PASS · RTM snipeit 24/25 ·
  `ci --rederive` base 12/12·assets 11/11·snipeit 11/11 == pin (SIN re-pin) · `meta check` 6/6 · `git diff src/+seed +
  default/assets product.yml = 0`.** **Con esto el NÚCLEO FUNCIONAL + BEHAVIORAL + de MODELO/AUTH faithful está COMPLETO**
  (data·acceso·comportamiento·valores-derivados·app-que-corre). Lo que RESTA es BREADTH y profundidad-de-detalle.
  Detalle: `docs/work/FSK-OWNER-POLY-INCREMENT.md §Evidencia` · `docs/LOG.md`.
- **CROSS-ENTITY DEPTH-2 — el ÚLTIMO refinamiento de VALORES DERIVADOS (FSK-XENTITY-DEPTH2, 2026-06-24)**: el AST de un
  campo computado admite un operando cross-entity de PROFUNDIDAD ARBITRARIA `<r1>[.<r2>...].<campo>` — una CADENA de refs
  resuelta por un helper único `_xref_resolve` (camina la cadena; cada hop un ref no-poly cuyo `to` ∈ el grafo, REQUERIDO
  **u** OPCIONAL: el LEFT JOIN es null-safe `?: 0.0`; campo final numérico no-computado) que sirve a la VALIDACIÓN, al
  `_row_json_fn` (JOINs por HOP, ENCADENADOS: `on(from.ref.eq(to.ID))` con `from` = la tabla del hop) y al ORÁCULO del
  proof (cruza el `_SEED_NUM` sembrado a N hops). depth-1 y depth-2+ por el MISMO camino. **Adopción**: snipeit
  `Asset.current_value` pasa a `model_id.depreciation_id.months` → lee `Depreciation.months` (el período REAL) por 2 JOINs
  (Asset→AssetModel→Depreciation), cierra el **deferral 13** de SNIPEIT-DOMAIN; `AssetModel.depreciation_id` REQUERIDO en
  la adopción (el seeder transitivo siembra la cadena → valor observable), `depreciation_months` removido (reemplazado por
  la columna REAL). Diente de DOS lados VIVO y PRECISO (degradé el 2º JOIN `eq`→`ne` → SÓLO el `[computed]` assert de s9
  rojo: `esperaba 21.25, obtuvo 42.5`, server VIVO, ~110 hermanos verdes; revertí→verde). **product-run PASS · RTM snipeit
  24/25 · `meta check` 6/6 · `git diff src/+seed + default/assets product.yml = 0` · SIN re-pin** (proof_sha intacto). **EL
  NÚCLEO (modelo·acceso·comportamiento·valores-derivados) está COMPLETO; lo que resta es BREADTH** (el de mayor retorno =
  frontend en un BROWSER real). Detalle: `docs/work/FSK-XENTITY-DEPTH2-INCREMENT.md §Evidencia` · `docs/LOG.md`.
- **INSERT-ON-VERB — el ÚLTIMO mecanismo behavioral (FSK-CREATES-PIVOT, 2026-06-23)**: un verbo qty (`decrements`)
  puede ADEMÁS `creates: <PivotEntity>` — al disparar INSERTA una fila en la pivote (el M:N real del checkout de
  accesorios) seteando el **FK-al-sujeto** (del id de la URL, detectado por `to == la entidad del verbo`) + los campos
  del cuerpo (los requeridos no-sujeto de la pivote). **ATÓMICO** (`ctx.transactionResult`: el decremento qty reusado
  dentro de la transacción + el INSERT; null ⟺ sin stock → 409; FK de cuerpo colgante lanza → rollback → 409). El
  handler devuelve 200 + la fila pivote (`rowJson` re-leído de la PG) para que el proof cruce que EXISTE con el sujeto +
  el cuerpo correctos. COMPONE FSK-QTY-OPERATIONS (decrementa) + FSK-REFS-IN-BODY (FK de cuerpo fail-closed), cero
  mecanismo nuevo. Codegen GENERAL opt-in byte-neutro: gramática (`creates` sólo en verbo qty, fail-closed), data class
  `<Pivot>CreateInput` + `parse…CreateInput` (codec `extra_parsers`, SIN el FK-al-sujeto), `<verbo><E>Create`/`rowJson`
  en `_operation_repo_fns(+by)`, el handler qty con `body`, el bloque qty del proof parametrizado (`%QTY_BODY%`==`{}`
  sin creates → byte-idéntico) + el diente del INSERT pivote. **Adopción PRODUCTO**: snipeit `Accessory.checkout` gana
  `creates: AccessoryCheckout` (la pivote con `assigned_user_id`+`note` requeridos). Diente de DOS lados VIVO (degradé
  `set(NOTE, input.note + "X")` → SÓLO `[creates] round-trippea note` rojo, `/health` UP, hermanos verdes; revertí→verde).
  **product-run PASS · RTM snipeit 24/25 · `ci --rederive` base 12/12·assets 11/11·snipeit 11/11 == pin (SIN re-pin) ·
  `meta check` 6/6 · `git diff src/+seed+default/assets product.yml = 0`.** Con esto el **núcleo BEHAVIORAL faithful
  quedó COMPLETO** (el de MODELO+AUTH lo cerró FSK-OWNER-POLY, arriba). Detalle: `docs/work/FSK-CREATES-PIVOT-INCREMENT.md
  §Evidencia` · `docs/LOG.md`.
- **CHECKOUT POLIMÓRFICO — el último eje behavioral FAITHFUL (FSK-POLY-ASSIGNS, 2026-06-23)**: un verbo de workflow
  con `assigns`/`clears` cuyo campo es un **ref POLIMÓRFICO** (FSK-POLYMORPHIC-REFS) setea/limpia las DOS sub-columnas
  (`<campo>_type`+`<campo>_id`) en vez de un Long único — el checkout que asigna a un **User|Location|Asset**.
  COMPONE dos primitivas probadas (cero mecanismo nuevo): `_operation_repo_fns` (poly → `set(_TYPE).set(_ID)` /
  `clears` poly → `setNull` ambas), `_operations_handlers` (parsea `<campo>_type` vía `enumOf` contra los targets,
  fail-closed → 400; + `<campo>_id`), `_OPERATIONS_PROOF` (placeholders byte-neutros: DEFAULT = ref simple; POLY =
  round-trip de AMBAS + diente fail-closed). Fix GENERAL surfaced: `@Suppress("LongMethod")` en `_row_json_fn` cuando
  el serializador exhaustivo supera 60 líneas (entidad ancha + 2 columnas poly). **Adopción PRODUCTO** (ADR-016):
  snipeit Asset gana `checkout_target` (poly, opcional, ≠ `owned_by` — wrinkle #3); `checkout` lo asigna, `checkin` lo
  libera. Diente de DOS lados VIVO (anulé el discriminador → `"UserX"`≠`"User"` → SÓLO `access_control_live` (s9) rojo,
  hermanos verdes; revertí→verde). RTM snipeit **24/25** (sólo s6 keyless; sin requisito nuevo → se pliega en
  REQ-F-014). **product-run PASS · `ci --rederive` base 12/12·assets 11/11·snipeit 11/11 == pin (SIN re-pin) · `meta
  check` 6/6 · `git diff src/+seed+default/assets product.yml = 0`.** **NÚCLEO FUNCIONAL + BEHAVIORAL FAITHFUL
  COMPLETO** (modelo de datos · acceso · workflow/stock/trash-restore · valores derivados same+cross-entity · checkout
  polimórfico · app que CORRE). Detalle: `docs/work/FSK-POLY-ASSIGNS-INCREMENT.md §Evidencia` · `docs/LOG.md`.
- **CRUD vivo para entidades SIN dueño (FSK-CRUD-OWNERLESS, 2026-06-21)**: la capa viva dejó de ser **opt-in a
  `owned_by`**. El server vivo monta TAMBIÉN la 1ª entidad **ownerless** servible (con `write_roles`, campos
  requeridos todos escalares; DATA-agnóstico: **User**/**Holder**/**Company** en los 3 productos) con CRUD gobernado
  por **RBAC-only** — handlers sufijados por entidad (`doPost<E>`/`listAll<E>`/`getOne<E>`/`doDelete<E>`), verdict
  `RoleGuard.authorize` (sin `OwnershipGuard` ni `ownerId` del token), `insert<E>(ctx, input)` de TODOS los escalares
  del cuerpo, codec del cuerpo COMPARTIDO sobre la unión de entidades servidas. **El DOMINIO ENTERO** (no sólo la
  entidad con dueño) empieza a ser usable a runtime. Diente RBAC de DOS lados (rol prohibido→403 sin INSERT /
  permitido→201+count+1 · round-trip del cuerpo · DELETE prohibido→403 / permitido→200→404), extiende el MISMO
  `access_control_live` (sin check nuevo → `proof_sha` intacto, pin byte-idéntico). Capability `crud_ownerless_runtime`
  (DES-3) + **REQ-F-019** → RTM default **24/24 COMPLETE**. Verificado VIVO (sólo `access_control_live` rojo al sabotear).
- **El ESPINAZO RELACIONAL: refs requeridos no-dueño desde el body (FSK-REFS-IN-BODY, 2026-06-21)**: una entidad
  ownerless con un `ref` REQUERIDO no-dueño dejó de quedar fuera de la capa viva — ahora obtiene **CRUD vivo con la
  FK del CUERPO**. Selección DATA-agnóstica `_live_with_ref` (la 1ª sin dueño, con `write_roles`, cuyos refs
  requeridos apuntan a targets SEMBRABLES — `_ref_target_seedable`): en snipeit **AssetModel** (`category_id`→
  Category); default (Task→Project, cadena profundidad >1) y assets (sin ref requerido no-dueño) → **None**, opt-out
  intacto. El POST acepta el id del ref (`Long` vía `longOf`, codec compartido), type-bound; el server **siembra el
  target** (`seedRows`→`_ref_targets`/`_seed_chain`) y expone su id por **`/seed refs`**; el INSERT con FK colgante
  se **ATRAPA** (`runCatching` → **409**, no 500). **El grafo relacional entero del dominio pasa a ser CRUD-able por
  API** (no sólo entidades sueltas). Diente de DOS lados (ref VÁLIDO→201+round-trip que cruza el id · ref COLGANTE→
  409 fail-closed), extiende el MISMO `access_control_live` (sin check nuevo → `proof_sha` intacto, pin byte-idéntico).
  Verificado VIVO (saboteado el atrape de la FK → SÓLO `access_control_live` rojo, hermanos verdes; revertí→verde).
  **No agrega requisito** (evita over-claim: default/assets no tienen una entidad así): se plegó en **REQ-F-016**
  (`entrada_tipada_runtime`) → RTM snipeit **23/24** (sólo s6 keyless). Sustrato (`src/metafactory/`+`seed/`) = 0;
  `product.yml` = 0. Detalle: `docs/work/FSK-REFS-IN-BODY-INCREMENT.md §Evidencia`.
- **La UI se MONTA en un DOM real + un FORM postea (FSK-BROWSER-FORM, 2026-06-21)**: la capa de UI dejó de ser
  media-verdad (el cliente `fetch`eaba y el render producía un STRING, pero **nada montaba ese markup en un DOM ni
  había un FORM para crear una fila**). Ahora `app.ts` gana **`mount<E>(doc: Document, base, token)`** — crea en el
  `Document` un **FORM** (un `<input>` por campo de `_input_fields`, coacción type-correct por tipo del contrato:
  number/checkbox/date/text; enum casteado a la unión literal, DES-6) cuyo **submit** postea vía **`create<E>`** (el
  cliente vivo), re-trae **`list<E>`** y **RE-RENDERIZA** la lista → **la fila nueva aparece como NODO del DOM**. El
  salto de "usable por API" a "usable por un humano que llena un formulario". ★ Hecho factible porque **jsdom YA es
  dep** (s8 a11y) → `document`+eventos sin browser real (**Playwright sigue diferido**). El proof EXTIENDE el MISMO
  check `frontend_consume_live` (s9): monta en un DOM jsdom, llena el FORM, dispara el `submit` y asevera que un `<li>`
  NUEVO aparece (**count N→N+1**; sin check nuevo → `proof_sha` intacto, **pin byte-idéntico**). `mount<E>` pasa
  `tsc --strict`+ESLint (s2) y el bundle (1943–3687 B < 8192, s8). **No agrega requisito** — se pliega en **REQ-F-018**
  (`frontend_render_live`). Diente de DOS lados verificado VIVO (saboteé el re-render del submit → **SÓLO**
  `frontend_consume_live` rojo, hermanos `observability_live`+`access_control_live` verdes; revertí→verde). Sustrato
  (`src/metafactory/`+`seed/`)=0; `product.yml`=0. Detalle: `docs/work/FSK-BROWSER-FORM-INCREMENT.md §Evidencia`.
- **DEPLOY VIVO — la imagen se CONSTRUYE y el contenedor RESPONDE (FSK-DEPLOY, 2026-06-22)**: la receta de deploy
  dejó de ser una media-verdad (hasta s10 el `Dockerfile` se SHIPPEA y `hermetic_build` verifica el PIN de la base por
  grep, pero **nadie construía la imagen ni levantaba el contenedor**). Ahora un gate nuevo **`deploy_smoke` (estación
  **s11**, `infra_up`, `depends_on: [s10]`)** corre `installDist` + **`docker build`** (Dockerfile generado, base
  `eclipse-temurin:21-jre` pineada por **digest REAL** cacheado) + **`docker run -d`** del contenedor, y un proof
  client stdlib (`tools/deploy_check.py`, urllib) le pega **`/health`** y exige **`{"status":"UP"}`**. El ENTRYPOINT
  del dist = `bin/<pkg>` = **ObsServerKt PG-free** → el smoke NO necesita PostgreSQL (AppServer-en-contenedor con PG =
  scope mayor, diferido). docker es **DATA** (mismo idiom que la PG viva de s9, ADR-012). Diente de DOS lados: NATIVO
  de `infra_up` (contenedor caído tras teardown → el MISMO proof falla) + saboteado el `ENTRYPOINT`/`COPY` → docker no
  arranca → **SÓLO `deploy_smoke` rojo** (s9/s10 verdes), verificado VIVO. Capability `deploy_vivo` (DES-1) +
  **REQ-NF-008** → RTM default **24→25 COMPLETE** (snipeit 24, s6 keyless). Check NUEVO → re-materializar `stations/`
  del default + re-pinear los 3. Sustrato (`src/metafactory/`+`seed/`)=0; `product.yml`=0. **3 product-run PASS · `ci
  --rederive --all-products` 12/12·11/11·11/11 == pin · `meta check` 6/6.** Detalle: `docs/work/FSK-DEPLOY-INCREMENT.md
  §Evidencia`.
- **JERARQUÍAS SELF-REF — el 1er gap del push Snipe-IT, GENERAL (FSK-SELF-REF, 2026-06-22)**: una entidad con un
  `ref` cuyo `to` es ELLA MISMA (jerarquía padre/hijo) dejó de romper el seeder del tier integración. El seeder de s7
  (`_it_repository_kt`) seteaba TODO ref —incl. el self— y referenciaba `ids[self]` ANTES de insertar la fila →
  `KeyError`/FK colgante. Ahora una self-ref se siembra como **cadena raíz→hijo** (DATA-agnóstico, heurística `to ==
  nombre de la entidad`, cero nombres de dominio): la **raíz** con el self-ref en NULL, un **hijo** apuntándola, y un
  **read-back** que cruza el id leído de la PG viva → la **FK self valida la jerarquía VIVA** y round-trippea. El hijo
  usa valores ALTERNOS en sus columnas UNIQUE (no choca con la raíz). También `_app_kt` (el ejercedor del contrato, s0)
  dejó de auto-referenciarse (`managerId = user.id` dentro del propio `val user` → self-ref del sample = `null`). Fix
  100% en **codegen de FÁBRICA** (`scaffold_product.py`); **sin check/estación nuevos → `proof_sha` intacto, pin
  byte-idéntico, SIN re-pin**. **Adopción en el PRODUCTO** (incremento de producto aparte, ADR-016): snipeit re-habilitó
  `Location.parent_id`→Location y `User.manager_id`→User (self-ref opcionales antes diferidos). Diente de DOS lados
  VIVO (self-ref del hijo → id inexistente → **SÓLO** `pyramid_integration` rojo, hermanos s7 verdes; revertí→verde).
  **3 product-run PASS · `ci --rederive --all-products` 12/12·11/11·11/11 == pin · `meta check` 6/6 (`generality`
  verde) · `git diff src/+seed = 0` · default+assets product.yml = 0.** Detalle: `docs/work/FSK-SELF-REF-INCREMENT.md
  §Evidencia`.
- **DUEÑO NULLABLE / RTD real — el 3er gap del push Snipe-IT, GENERAL (FSK-OWNERSHIP-OPTIONAL, 2026-06-22)**: un activo
  Ready-To-Deploy está SIN asignar (dueño NULL) — el caso NORMAL de Snipe-IT, antes inexpresable (FSK exigía `owned_by`
  `required: true`: `canModify(rowOwnerId: Long)` no-nullable + el server vivo conflaciona owner-nulo con 404).
  **Levantado opt-in por el `required` del `owned_by`** (con dueño REQUERIDO el codegen queda byte-idéntico →
  default/assets sin re-derivar): `canModify(rowOwnerId: Long?)` (una fila SIN dueño sólo la modifica un rol de bypass);
  `modifyVerdict` separa **EXISTENCIA** (reusa `<e>RowJson != null`) de **DUEÑO** (RTD existe → no es 404; inexistente
  sigue 404); el server siembra una **2ª fila RTD** (owner NULL, valores ALT en las UNIQUE) que `/seed` expone. El
  handoff señalaba 2 sitios; generar destapó **4** (sumó `_mutation_fns`: el creador es dueño aunque la columna sea
  opcional; y `_seed_chain`/`_sample`: la 2ª fila). Fix 100% en **codegen de FÁBRICA**; **sin check/estación nuevos →
  `proof_sha` intacto, SIN re-pin**. **Adopción PRODUCTO** (ADR-016): snipeit `Asset.assigned_user_id` → `required:
  false`. Diente de DOS lados VIVO (s9 `access_control_live`: saboteé `modifyVerdict` → RTD modificable por cualquiera →
  **SÓLO** `access_control_live` rojo, hermanos s9 verdes; revertí→verde; RTD+no-bypass→403 / RTD+bypass→200 /
  inexistente→404) + UNIT (s7 `OwnershipGuardTest`, 2 casos). **`product-run` PASS · RTM 24/25 · `ci --rederive
  --all-products` 12/12·11/11·11/11 == pin · `meta check` 6/6 (`generality` verde) · `git diff src/+seed = 0` ·
  default+assets product.yml = 0.** Detalle: `docs/work/FSK-OWNERSHIP-OPTIONAL-INCREMENT.md §Evidencia`.
- **REFS REQUERIDOS no-dueño / SEED TRANSITIVO — el 4º gap del push Snipe-IT, GENERAL (FSK-OWNED-REQUIRED-REFS,
  2026-06-22)**: `Asset.model_id` es REQUERIDO en Snipe-IT (un activo SIEMPRE es de un modelo), pero el server vivo
  (FSK-S15) no sabía sembrar un `ref` REQUERIDO no-dueño en la entidad-con-dueño (`_seed_chain` hacía `raise`); el
  target es de PROFUNDIDAD >1 (AssetModel→Category). **Levantado opt-in por placeholder** (sin ref requerido no-dueño →
  byte-idéntico): `_seed_chain` gana `ref_wiring`; dos seeders recursivos nuevos **`_seed_deps`/`_ensure_seeded`**
  siembran TOPOLÓGICAMENTE las dependencias (deduplicado por registry, **ciclos → `raise` honesto = deferral 6**) ANTES
  del owned; el server expone **`ownedRefs`** en `/seed` para que el POST/FORM traiga FKs VÁLIDAS; el RTD reusa las deps.
  Los proofs inyectan los refs desde `/seed` en runtime (evita el `KeyError` sobre un `ref`). **La lección "el handoff
  sub-estima los sitios" se INVIRTIÓ**: s1/s7 YA sembraban topológicamente + el form ya mapeaba `ref`→input → el gap real
  era UN camino (s9). Fix 100% en **codegen de FÁBRICA**; **sin check/estación nuevos → `proof_sha` intacto, SIN re-pin**.
  **Adopción PRODUCTO** (ADR-016): snipeit `Asset.model_id` → `required: true`. Diente de DOS lados VIVO (s9: FK colgante
  en el POST → **SÓLO** `access_control_live` rojo, hermanos s9 verdes; revertí→verde). **`product-run` PASS · RTM 24/25 ·
  `ci --rederive --factory full-stack-kotlin --all-products` 12/12·11/11·11/11 == pin · `meta check` 6/6 (`generality`
  verde) · `git diff src/+seed = 0` · default+assets product.yml = 0.** Detalle: `docs/work/FSK-OWNED-REQUIRED-REFS-INCREMENT.md §Evidencia`.
- **VERBOS DE DOMINIO checkout/checkin — el 1er eje de COMPORTAMIENTO, GENERAL (FSK-DOMAIN-OPS, 2026-06-22)**: tras 4
  ejes de MODELO-DE-DATOS, el 1er eje de COMPORTAMIENTO. La operación central de Snipe-IT no es un PUT genérico: es
  **checkout** (`status ready→deployed` + asigna el activo a un usuario) / **checkin** (`deployed→ready` + lo libera).
  Una entidad con dueño declara **`operations: [{name, field, from, to, assigns|clears}]`** (DATA, ADR-012): un verbo =
  una transición NOMBRADA de un campo enum-workflow + un efecto sobre un `ref`, que MUTA bajo **precondición de
  WORKFLOW + RBAC + ownership**. El codegen emite ruta (`post /<plural>/{id}/<verbo>` + RouteTable, route_check
  auth/rbac GRATIS) + handler (`return when` que compone **modifyVerdict → `canTransition(estado_actual, to)` →
  mutación atómica**; estado inválido → **409**) + mutación tipada (`<verbo><E>` UPDATE) + proof. **Cierra el
  over-claim "workflow enforced"**: el guard `canTransition` (FSK-S12) pasó de SÓLO-UNIT (s7) a **ENFORZADO A RUNTIME**.
  Validación fail-closed: un verbo cuyo `from→to` no es una transición declarada → `raise`. **Opt-in/byte-neutro** (sin
  `operations` → AppServer/Repository/contrato/proof byte-idénticos; **sin check nuevo → `proof_sha` intacto, SIN
  re-pin**). **Adopción PRODUCTO** (ADR-016): snipeit `Asset` gana `operations: [checkout, checkin]`. Diente de DOS
  lados VIVO (s9: invertir la precondición `canTransition` → **SÓLO** `access_control_live` rojo, hermanos verdes;
  revertí→verde). **`product-run` PASS · RTM 24/25 · `ci --rederive --all-products` 12/12·11/11·11/11 == pin · `meta
  check` 6/6 (`generality` verde) · `git diff src/+seed = 0` · default+assets product.yml = 0.** Detalle:
  `docs/work/FSK-DOMAIN-OPS-INCREMENT.md §Evidencia`.
- **CUSTOM FIELDS con FORMAT / validación — el eje GRANDE, ACOTADO, GENERAL (FSK-CUSTOM-FIELDS, 2026-06-22)**: el mayor
  eje de fábrica que Snipe-IT fuerza (deferral 1), entregado acotado. Resuelta la decisión de diseño = **Avenue A**
  (campos DECLARADOS en el blueprint) **sub-eje `format`/validación**: un campo `string` gana un modifier OPCIONAL
  `format: <nombre>` (vocabulario CERRADO `numeric`/`alpha`/`email`/`url`/`ip`/`mac`) — la REGLA DE VALIDACIÓN del
  VALOR (el aporte NUEVO de un custom field sobre un string normal). El codegen la emite (`_FORMAT_REGEX` + validación
  fail-closed en `_load_blueprint`; el codec `strFmt(o, k, FMT_<NAME>)` = `require(re.matches(s))` → no-match → null →
  **400**, compone sobre FSK-CRUD-BODY-PARSING; `x-format` en el contrato, DES-6) y un gate la PRUEBA. El **EAV
  dinámico a runtime (Avenue B)** sigue DIFERIDO y VISIBLE (schema build-time vs runtime). **Opt-in/byte-neutro**
  (default+assets 68/68 byte-idénticos; **`proof_sha` intacto → SIN re-pin**; no agrega requisito → se prueba dentro de
  `access_control_live`). **Adopción PRODUCTO** (ADR-016): snipeit `Asset` gana `mac_address` (string, format: mac,
  requerido) — el custom field canónico de Snipe-IT. Diente de DOS lados VIVO (s9: `FMT_MAC` degradado a `.*` → **SÓLO**
  `access_control_live` rojo, hermanos verdes; revertí→verde). **`product-run` PASS · RTM 24/25 · `ci --rederive`
  12/12·11/11·11/11 == pin · `meta check` 6/6 (`generality` verde) · `git diff src/+seed = 0` · default+assets
  product.yml = 0.** Detalle: `docs/work/FSK-CUSTOM-FIELDS-INCREMENT.md §Evidencia`.
- **CICLOS CROSS-ENTIDAD — el 1er eje de CICLO en el grafo, GENERAL (FSK-XENTITY-CYCLES, 2026-06-22)**: tras 6 ejes
  de modelo-de-datos/comportamiento/validación, el 1er CICLO entre entidades distintas. Hoy un `ref` BACKWARD/self
  emite la FK inline en orden de declaración; un `ref` FORWARD (target declarado DESPUÉS → abre/cierra un ciclo, p.ej.
  `Location.manager_id`→User con User declarado después) rompía el migration (FK a tabla inexistente). **Levantado
  GENERAL** (codegen de fábrica, cero nombres de dominio, `generality` verde): el ref forward se emite como columna
  `BIGINT` pelada + la FK como **constraint DIFERIDA** (`ALTER TABLE … ADD CONSTRAINT … FOREIGN KEY … REFERENCES …`)
  al FINAL del migration (tras todos los `CREATE TABLE`); el seeder de s7 lo cablea **NULL-then-UPDATE** (inserta sin
  el forward, luego `UPDATE` al id capturado), round-trippea el ciclo VIVO vs PG y embebe el **diente negativo** (FK
  forward COLGANTE → la constraint diferida la RECHAZA → `shouldThrow<DataAccessException>`). El forward DEBE ser
  OPCIONAL (un lado del ciclo no tiene orden de siembra; requerido → `raise` honesto en `_load_blueprint`). También
  `_app_kt` (s0) samplea el forward como `null` (unifica self-ref + forward). **Opt-in/byte-neutro** (sin forward refs
  → migration/seeders byte-idénticos; default+assets 68/68 byte-idénticos por EYEBALL; **sin check nuevo → `proof_sha`
  intacto, SIN re-pin**). **Adopción PRODUCTO** (ADR-016): snipeit re-habilitó `Location.manager_id`→User y
  `Department.manager_id`→User (forward/cíclicos, opcionales) — restaura los ciclos Location↔User y User↔Department.
  Diente de DOS lados VIVO (s7: quité la constraint diferida → **SÓLO** `pyramid_integration` rojo, hermanos s7
  verdes; revertí→verde). **`product-run` PASS · RTM 24/25 · `ci --rederive --all-products` 12/12·11/11·11/11 == pin ·
  `meta check` 6/6 (`generality` verde) · `git diff src/+seed = 0` · default+assets product.yml = 0.** Detalle:
  `docs/work/FSK-XENTITY-CYCLES-INCREMENT.md §Evidencia`.
- **COMPANY-SCOPING — el 1er eje de ACCESO-POR-ATRIBUTO (ABAC) + el 1er FILTRADO DE LECTURA, GENERAL
  (FSK-COMPANY-SCOPING, 2026-06-22)**: tras 7 ejes, el último gran hueco del modelo de acceso faithful y el
  1er eje que filtra LECTURAS (todo lo anterior gateaba escrituras). Una entidad con dueño declara
  `company_scoped: <campo ref>` (el TENANT) + `company_scope_bypass_roles` (top-level) → el server vivo (s9)
  **FILTRA la lista por la compañía del actor** (read-path NUEVO: `WHERE company = ? OR company IS NULL` — fila
  sin tenant = NO-scopeada/pública) y **compone el scope DESPUÉS de ownership en el verdict de escritura** (otra
  compañía → 403 aunque sea el dueño; bypass → 200). Generaliza ownership ("fila × principal") a "fila × tenant".
  **Levantado GENERAL** (codegen de fábrica, cero nombres de dominio, `generality` verde): `CompanyScopeGuard`
  (type-safe sobre `Role`, hermano de `OwnershipGuard`) + `CompanyScopeGuardTest` (4 casos unit) · `RoleGuard`
  gana `companyOf` (3er segmento `"Bearer rol:principal:compañía"`, gateado → token de 2 segmentos byte-idéntico)
  · Repository gana `<e>CompanyId` + el read-filter `<e>sByCompany` · `x-company-scoped` en el contrato (DES-6).
  **Opt-in/byte-neutro** (sin `company_scoped` → default+assets 68/68 byte-idénticos por EYEBALL; **sin check
  nuevo → `proof_sha` intacto, SIN re-pin**). **Adopción PRODUCTO** (ADR-016): `Asset.company_scoped: company_id`
  + `company_scope_bypass_roles: [superadmin, admin]` (FMCS faithful). Diente de DOS lados VIVO (s9: saboteé
  `companyScopeBypass()→Role.entries.toSet()` → **SÓLO** `access_control_live` rojo, hermanos verdes;
  revertí→verde). **`product-run` PASS · RTM 24/25 · `ci --rederive` 12/12·11/11·11/11 == pin · `meta check` 6/6
  (`generality` verde) · `git diff src/+seed = 0` · default+assets product.yml = 0.** Lecciones nuevas: el
  read-path se sub-estima · `-Werror` flagea `company != null` redundante tras `scoped` (usar destructuring) ·
  `MagicNumber` muerde el literal 3 (`getOrNull(2)`) · `Seed`/`seedJson` cruzan 160 al sumar campos (wrap opt-in).
  Detalle: `docs/work/FSK-COMPANY-SCOPING-INCREMENT.md §Evidencia`. **La trilogía+1 de acceso (auth → RBAC →
  ownership → company-scope) está COMPLETA y VIVA a runtime.**
- **VERBOS DE STOCK / qty — el 1er eje de COMPORTAMIENTO con stock + 1er VERBO sobre entidad SIN dueño, GENERAL
  (FSK-QTY-OPERATIONS, 2026-06-22)**: un nuevo KIND de operación (`decrements: <campo int>`, detectado por la
  presencia de `decrements`, EXCLUYENTE con el KIND workflow) decrementa el stock con guard out-of-stock —
  RBAC-only sobre una entidad SIN dueño (el 1er montaje de VERBOS fuera de la entidad con dueño). `_load_blueprint`
  valida el KIND (relaja `owned_by`, exige `write_roles` + `decrements`∈int); `_operation_repo_fns` emite un UPDATE
  CONDICIONAL `SET qty=qty-1 WHERE id=? AND qty>0`; `_ownerless_handlers` gana `ops` (handler `POST
  /<plural>/{id}/<verbo>` + dispatch); `_live_with_ref` PREFIERE la entidad con verbos qty; el server siembra una
  fila de stock (`qtyId`). snipeit adoptó `Accessory.checkout`. **Diente de DOS lados VIVO** (s9, quitar `AND qty>0`
  → SÓLO `access_control_live` rojo). Opt-in byte-neutral (default/assets 68/68 + snipeit-sin-qty 70/70; `proof_sha`
  intacto → sin re-pin); `git diff src/+seed=0`; `meta check` 6/6; `ci --rederive` 12/12·11/11·11/11 == pin. Scope
  honesto: `creates: <pivot>` DIFERIDO. Detalle: `docs/work/FSK-QTY-OPERATIONS-INCREMENT.md §Evidencia`.
- **REF POLIMÓRFICO — el ÚLTIMO eje de MODELO-DE-DATOS faithful, GENERAL (FSK-POLYMORPHIC-REFS, 2026-06-22)**: un `ref`
  con `to: <LISTA>` apunta a una UNIÓN de entidades (el hermano sobre refs de lo que el enum es sobre valores). Se
  materializa como DOS columnas — `<campo>_type` (discriminador, enum CERRADO de los nombres de target) + `<campo>_id`
  (BIGINT **SIN FK**: no hay integridad a una unión, la limitación real del patrón). El wrinkle estructural (1 campo →
  2 columnas, que TODO el codegen asumía 1:1) se resolvió con una abstracción única — `_is_poly`/`_poly_subfields`/
  `_cols_of`/`_input_cols` — byte-neutra para todo lo previo: los emisores por-columna iteran `_cols_of`; selección/seed
  excluyen el poly (`not _is_poly`, no es una FK que encadenar). snipeit adoptó `Accessory.checkout_target → [User,
  Location, Asset]` (la entidad with_ref viva). El server vivo round-trippea (tipo, id) y GET los devuelve EXACTOS,
  distinguiendo el target. **Diente de DOS lados VIVO** (s9, degradar el discriminador del rowJson → SÓLO
  `access_control_live` rojo). Opt-in byte-neutral (default/assets 68/68 + snipeit-sin-poly 70/70; `proof_sha` intacto →
  sin re-pin); `git diff src/+seed=0`; `meta check` 6/6; `ci --rederive` 12/12·11/11·11/11 == pin. **Con esto el MODELO
  DE DATOS faithful queda COMPLETO.** Diferido faithful: el `assigns` polimórfico del verbo + el owner polimórfico de
  Asset (wrinkle #3). Detalle: `docs/work/FSK-POLYMORPHIC-REFS-INCREMENT.md §Evidencia`.
- **CAMPO COMPUTADO — la dimensión de VALORES DERIVADOS, GENERAL (FSK-COMPUTED-FIELDS, 2026-06-23)**: un campo
  `int`/`number` puede declarar `computed: <AST>` — un valor DERIVADO por una FÓRMULA aritmética DETERMINISTA de
  otros campos numéricos de la MISMA entidad (no "qué guarda" sino "qué deriva"). Wrinkle estructural INVERSO al
  poly: 1 campo → **0 columnas** (no entra a migration/insert/input/seed; `_cols_of` lo EXCLUYE) — se computa a
  **READ-time en `rowJson`** y se documenta read-only en el contrato (`readOnly: true`+`x-computed`). La fórmula es
  un **AST declarado** (`{op, args}` | número | nombre de campo), fail-closed en `_load_blueprint`: operadores de un
  set CERRADO (`+ - * / min max`), operandos = campos numéricos no-computados o literales (un op/ref/aridad inválido
  → M0 rojo). El codegen extrae las fuentes a `val`s `Double` null-safe y emite la expresión Kotlin (`/` → helper
  `safeDiv` con guard div-por-cero; `min`/`max` → `minOf`/`maxOf`); el proof re-deriva la MISMA fórmula en Python
  (IEEE 754 idéntico → comparación EXACTA). **No necesita s6/LLM** (aritmética pura, I-3). snipeit adoptó
  `Asset.current_value = max(purchase_cost - purchase_cost/depreciation_months, 0)` (1er-cut SAME-ENTITY; la
  derivación cross-entity —months en Depreciation— + time-elapsed siguen diferidas). **Diente de DOS lados VIVO**
  (degradar la aritmética del rowJson `-`→`+` → SÓLO `access_control_live` (s9) rojo, hermanos
  `observability_live`+`frontend_consume_live` verdes; revertí→verde). Opt-in byte-neutral (default/assets 68/68 +
  snipeit-sin-computed 70/70; `proof_sha` intacto → **sin re-pin**); `git diff src/+seed=0`; `meta check` 6/6
  (`generality` verde); `ci --rederive` 12/12·11/11·11/11 == pin. Se pliega en **REQ-F-014** (sin requisito nuevo).
  **Con esto la dimensión de VALORES DERIVADOS queda cubierta — el núcleo funcional faithful está COMPLETO.**
  Detalle: `docs/work/FSK-COMPUTED-FIELDS-INCREMENT.md §Evidencia`.
- **BORRADO LÓGICO — el ÚLTIMO eje BEHAVIORAL, GENERAL (FSK-SOFT-DELETES, 2026-06-23)**: una entidad puede declarar
  `soft_delete: true` → DELETE deja de ser PERMANENTE: pasa a `UPDATE deleted_at` (la fila SIGUE existiendo, invisible
  a las lecturas) y un verbo `restore` IMPLÍCITO la recupera. Faithful a Snipe-IT (Laravel SoftDeletes: NUNCA
  hard-deletea por defecto). `deleted_at DATE` es columna de SISTEMA (como `id`, fuera de `_cols_of`); el read-filter
  `IS NULL` toca TODOS los read-paths de USUARIO (`all<E>s`/`<e>RowJson`/`sByCompany`, compone sobre el read-filter de
  FSK-COMPANY-SCOPING) pero NO los lookups del guard (`<e>OwnerId`/`<e>CompanyId` ven la fila borrada); el verbo
  `restore` (`POST /<plural>/{id}/restore`, `setNull`) se monta como un verbo más, gateado por el MISMO `modifyVerdict`
  que DELETE/PUT, registrado en contrato+RouteTable. **Dos wrinkles de COMPOSICIÓN resueltos**: (1) modifyVerdict
  (owner-OPTIONAL, p.ej. Asset/RTD) chequeaba existencia via `<e>RowJson` que ahora filtra → una fila borrada parecía
  inexistente y restore era IMPOSIBLE (404); fix: existencia SIN filtrar `<e>Exists` (la decisión de acceso es
  independiente del borrado); (2) el UNIQUE inline ocupaba el valor aún borrado → un POST que reusa el valor (proof de
  `operations`) violaba UNIQUE → el server crasheaba; fix FAITHFUL: índice UNIQUE **PARCIAL** `WHERE deleted_at IS NULL`
  (una fila borrada no ocupa el valor → se reusa tras borrar) + el proof re-deletea tras restaurar. **Diente de DOS
  lados VIVO** (saboteé el read-filter `IS NULL` → SÓLO `access_control_live` (s9) rojo, hermanos verdes → revertí →
  verde). Opt-in byte-neutral (default/assets/snipeit-sin-soft 0 diffs; `proof_sha` intacto → **sin re-pin**); `git diff
  src/+seed=0`; `meta check` 6/6 (`generality`); `ci --rederive` 12/12·11/11·11/11 == pin; RTM snipeit **24/25** (sólo s6
  LLM keyless). **NÚCLEO FUNCIONAL + BEHAVIORAL faithful COMPLETO — lo que resta es breadth pura.** Detalle:
  `docs/work/FSK-SOFT-DELETES-INCREMENT.md §Evidencia`.
- **CAMPO COMPUTADO CROSS-ENTITY — la fórmula lee una entidad RELACIONADA, GENERAL (FSK-XENTITY-COMPUTED, 2026-06-23)**:
  la contracara del 1er-cut SAME-ENTITY de FSK-COMPUTED-FIELDS. Un operando del AST puede ser `<ref>.<campo>` →
  resolver un ref REQUERIDO no-poly → LEFT JOIN al target → leer su columna → computar. `_validate_computed_ast`
  acepta el operando con `.` (cruza `<ref>` ∈ refs requeridos + `<campo>` ∈ numéricos requeridos del target,
  fail-closed); `_row_json_fn` (recibe el grafo `by`) separa fuentes same-entity/cross-entity, emite un LEFT JOIN por
  ref distinto y wrappea el chasis de la query (ChainWrapping) cuando entidad ancha + JOIN pasa 160; el oráculo
  (`%XSRC_SETUP%` opt-in) re-deriva con el valor SEMBRADO del target (`_SEED_NUM`, espeja `_KT_SAMPLE`). 1er-cut:
  ref+campo REQUERIDOS, depth-1 (el ref directo); depth-2 (vía `AssetModel.depreciation_id→Depreciation`) +
  time-elapsed diferidos. **Diente de DOS lados VIVO** (anular el valor del JOIN → SÓLO `access_control_live` (s9)
  rojo, hermanos verdes; revertí→verde). Opt-in byte-neutral (base/assets + snipeit-same-entity 0 diffs; `proof_sha`
  intacto → **sin re-pin**); `git diff src/+seed=0`; `meta check` 6/6 (`generality`); `ci --rederive` 12/12·11/11·11/11
  == pin; RTM snipeit **24/25**. snipeit MOVIÓ `depreciation_months` de `Asset` a `AssetModel` (faithful: el período
  es per-modelo) y deriva `current_value` cross-entity. Se pliega en **REQ-F-014**. Detalle:
  `docs/work/FSK-XENTITY-COMPUTED-INCREMENT.md §Evidencia`.
- **★ FSK MADURO (2026-06-22) → el trabajo pasa a ser product-specific (Snipe-IT)**: un producto se **genera** desde
  un blueprint → se **prueba e2e** en su toolchain bajo gates duros → tiene **CRUD vivo del grafo relacional ENTERO**
  (con/sin dueño, refs del body) bajo control de acceso (auth→RBAC→ownership) a runtime → una **UI usable por un
  humano** (monta en DOM + FORM que postea) → y **deploya en un contenedor que responde**. **El último hueco
  claramente-FSK-general (deploy) está cerrado.** Lo que QUEDA:
  - **product-specific = construir Snipe-IT** sobre la fábrica madura: los **12 deferrals** de
    `products/snipeit/docs/reference/SNIPEIT-DOMAIN.md` (~~custom-fields (format/validación)~~ **✓ hecho FSK-CUSTOM-FIELDS
    (Avenue A); EAV dinámico/Avenue B diferido** · checkout polimórfico · ~~RTD/owner-opcional~~ **✓ hecho
    FSK-OWNERSHIP-OPTIONAL** · ~~self-ref~~ **✓ hecho FSK-SELF-REF** · ~~refs requeridos no-dueño / seed transitivo~~
    **✓ hecho FSK-OWNED-REQUIRED-REFS** · ~~verbos de dominio checkout/checkin~~ **✓ hecho FSK-DOMAIN-OPS** ·
    ~~ciclos cross-entidad~~ **✓ hecho FSK-XENTITY-CYCLES** · ~~company-scoping~~ **✓ hecho FSK-COMPANY-SCOPING** ·
    ~~cantidades (qty)~~ **✓ hecho FSK-QTY-OPERATIONS** · ~~checkout polimórfico (modelo de datos)~~ **✓ hecho
    FSK-POLYMORPHIC-REFS** · ~~depreciación calculada same-entity~~ **✓ hecho FSK-COMPUTED-FIELDS** · ~~depreciación
    cross-entity~~ **✓ hecho FSK-XENTITY-COMPUTED** · …).
    **NÚCLEO FUNCIONAL + BEHAVIORAL faithful COMPLETO** (modelo de datos incl. refs polimórficos + acceso
    auth→RBAC→ownership→company-scope + comportamiento workflow/stock/trash-restore + valores derivados same+cross-entity
    + app que corre); ~~borrado lógico~~ **✓ hecho FSK-SOFT-DELETES** · ~~cross-entity computed~~ **✓ hecho
    FSK-XENTITY-COMPUTED**.
    **SIGUIENTE (recomendado, abierto) = `assigns` POLIMÓRFICO del verbo (FSK-POLY-ASSIGNS)** — el último eje
    behavioral genuino: un verbo de workflow (checkout) que ASIGNA a un ref POLIMÓRFICO (setear `<campo>_type` +
    `<campo>_id` del cuerpo del verbo). COMPONE dos ejes ya probados — FSK-POLYMORPHIC-REFS (el ref a una UNIÓN) +
    FSK-DOMAIN-OPS (el verbo de workflow con `assigns`). Completa el checkout polimórfico FAITHFUL (en Snipe-IT el
    target del checkout es User|Location|Asset, hoy simplificado a User). Acotado, determinista, diente claro. **Es
    DECISIÓN de la próxima sesión** (con research): alternativas honestas = `creates`/pivot de qty (insertar
    AccessoryCheckout) · derivación cross-entity DEPTH-2 (Asset→AssetModel→Depreciation.months) · o pivotar a
    **breadth pura** (~226 rutas, Kits, EAV dinámico, Actionlog). Ver `docs/work/FSK-POLY-ASSIGNS-INCREMENT.md` (handoff).
    **Metodología probada**:
    el producto EXPONE un gap → si es genuinamente FSK-general se arregla GENERAL (cero nombres de dominio,
    `generality` verde) en su propio incremento; si es del dominio, vive en el producto. Casi todos los gaps de FSK se
    cazaron así (CRUD/body/frontend/ownerless/refs/form/deploy).
  - **ejes FSK-general OPCIONALES** que un producto puede destapar (no especular hasta que un caso real los pida):
    CRUD/FORM de TODAS las entidades en la UI (hoy form sólo de la entidad con dueño) · edición/borrado desde la UI ·
    cadenas de refs profundidad >1 · refs polimórficos/opcionales · PUT/update ownerless · UNIQUE-from-body→409.
  - **diferidos DUROS (red/scope)**: push de la imagen a un **registry** · **e2e Playwright** (browser real) ·
    AppServer-en-contenedor con PG.

## Mapa
- Línea de producto: `stations/` · Dominio (humano): `domain/` · Generado (chasis): `generated/` · Build re-derivable: `build/`
- Raíz de confianza: `seed/` (columna) + `.claude/` (sombras) · CI externo: `seed/external_ci.yml`
- Veredicto pineado (constante honesta): `pinned_verdict.json`
