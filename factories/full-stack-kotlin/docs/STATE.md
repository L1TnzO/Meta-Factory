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
- **★ FSK MADURO (2026-06-22) → el trabajo pasa a ser product-specific (Snipe-IT)**: un producto se **genera** desde
  un blueprint → se **prueba e2e** en su toolchain bajo gates duros → tiene **CRUD vivo del grafo relacional ENTERO**
  (con/sin dueño, refs del body) bajo control de acceso (auth→RBAC→ownership) a runtime → una **UI usable por un
  humano** (monta en DOM + FORM que postea) → y **deploya en un contenedor que responde**. **El último hueco
  claramente-FSK-general (deploy) está cerrado.** Lo que QUEDA:
  - **product-specific = construir Snipe-IT** sobre la fábrica madura: los **12 deferrals** de
    `products/snipeit/docs/reference/SNIPEIT-DOMAIN.md` (custom-fields dinámicos · checkout polimórfico ·
    ~~RTD/owner-opcional~~ **✓ hecho FSK-OWNERSHIP-OPTIONAL** · ~~self-ref~~ **✓ hecho FSK-SELF-REF** · depreciación
    calculada · company-scoping · …). **Metodología probada**:
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
