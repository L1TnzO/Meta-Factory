# Bitácora — Full-Stack Kotlin/TS/PG Factory
> tipo: log · append-only, MÁS NUEVO ARRIBA · inmutable una vez escrito (esquema ADR-021).

## 2026-06-22T17:05Z — FSK-COMPANY-SCOPING ✅: scoping por compañía (multi-tenancy/ABAC) — el 1er eje con FILTRADO de LECTURA
- **Tras 7 ejes, el último gran hueco del modelo de acceso faithful y el 1er eje que FILTRA LECTURAS** (deferral 8).
  Todo lo previo (auth/RBAC/ownership) gateaba ESCRITURAS; con FMCS un actor no-superadmin ve/edita SÓLO las filas
  de SU compañía (`company_id`). Generaliza ownership ("fila × principal") a un scope por atributo compartido
  ("fila × tenant", lectura+escritura). Es ABAC acotado, hermano de FSK-S14 pero distinto.
- **Levantado GENERAL** (codegen de fábrica, cero nombres de dominio, `generality` verde, `git diff src/+seed=0`):
  - **`_load_blueprint`**: valida `company_scoped: <campo ref>` (∈ `ref`) + `company_scope_bypass_roles` ⊆ roles,
    exige `roles` (fail-closed, mismo patrón que `owned_by`).
  - **`CompanyScopeGuard.canAccess(rol, compañíaActor, tenantFila, bypass)`** = `bypass || tenantFila==null ||
    match`. Fila SIN tenant = NO-scopeada (pública). Genérico, type-safe sobre `Role`; + `CompanyScopeGuardTest`
    (4 casos, tier unit, hermano de `OwnershipGuardTest`).
  - **`RoleGuard.companyOf`**: 3er segmento `"Bearer rol:principal:compañía"` (`split(':').getOrNull(2)`);
    `principalOf` safe a 3 segmentos. GATEADO por `scoped` → token de 2 segmentos byte-idéntico (FSK-S15 intacto).
  - **Repository**: `<e>CompanyId` (tenant de UNA fila) + `<e>sByCompany`/`all<E>RowsJsonByCompany` (read-filter
    `WHERE company = ? OR company IS NULL`).
  - **AppServer s9**: `listAll` FILTRA por la compañía del token (read-path NUEVO; destructuring `(count, rows)`
    para no disparar `-Werror`); `modifyVerdict` compone `scopeOk` DESPUÉS de `ownerOk` (otra compañía → 403 aunque
    sea el dueño); `seedRows` siembra ≥2 compañías + una fila scopeada a la 2ª (dueño=actor → aísla scope de
    ownership; `variant` en `_sample`/`_seed_chain` para UNIQUEs sin colisión). `Seed`/`seedJson` wrappean si >160.
  - **Contrato**: `x-company-scoped` (vendor ext inspectable, DES-6).
  - **Proof e2e** (s9 `access_control_live`): read-filter (no-bypass NO ve otra compañía / bypass ve todas) +
    escritura (PUT fila de otra compañía por su dueño → 403 / su compañía → 200 / bypass → 200).
- **Opt-in/byte-neutro**: sin `company_scoped` → default+assets 68/68 byte-idénticos (EYEBALL); **sin check nuevo →
  `proof_sha` intacto, SIN re-pin**. **Adopción PRODUCTO** (ADR-016): `Asset.company_scoped: company_id` +
  `company_scope_bypass_roles: [superadmin, admin]` (FMCS faithful).
- **Verde no fingido (por bloqueo)**: `product-run --product snipeit` PASS · RTM 24/25 (único UNSAT s6 LLM keyless)
  · **diente de DOS lados VIVO** (s9: saboteé `companyScopeBypass()→Role.entries.toSet()` → manager bypass → SÓLO
  `access_control_live` rojo, hermanos verdes → revertí → verde) · `ci --rederive` base 12/12 · assets 11/11 ·
  snipeit 11/11 == pin · `meta check` 6/6 (`generality` verde) · `git diff src/+seed = 0` · default+assets
  product.yml = 0. Detalle: `docs/work/FSK-COMPANY-SCOPING-INCREMENT.md §Evidencia`.
- **Lecciones**: el read-path se sub-estima (token+filtro toca firma+dispatch+proof) · `-Werror` flagea
  `company != null` redundante tras `scoped` → destructuring que smart-castea · `MagicNumber` muerde el literal 3 →
  `getOrNull(2)` · `Seed`/`seedJson` cruzan 160 al sumar campos → helpers de wrap opt-in (byte-neutro a 1 línea).
- **SIGUIENTE**: `FSK-QTY-OPERATIONS` (cantidades, sub-eje de FSK-DOMAIN-OPS) — abierto con handoff.

## 2026-06-22T15:42Z — FSK-XENTITY-CYCLES ✅: ciclos cross-entidad (FK forward/cíclica) — el 1er eje de CICLO en el grafo
- **Tras 6 ejes (modelo-de-datos/comportamiento/validación), el 1er CICLO entre entidades DISTINTAS** (deferral 6).
  Hoy un `ref` BACKWARD/self emite la FK inline en orden de declaración; un `ref` FORWARD (target declarado DESPUÉS →
  abre/cierra un ciclo, p.ej. `Location.manager_id`→User con User declarado después) rompía el migration (FK a tabla
  que aún no existe → SQL error). Es SCHEMA/seed, distinto a todo lo hecho (no access-control ni comportamiento).
- **Levantado GENERAL** (codegen de fábrica, cero nombres de dominio, `generality` verde, `git diff src/+seed=0`):
  - **`_load_blueprint`**: validación fail-closed — un ref forward (`idx[to] > idx[e]`) REQUERIDO → `SystemExit` (un
    lado del ciclo no tiene orden de siembra). Opcional → OK.
  - **`_migration_sql`**: el ref forward → columna `BIGINT` pelada + la FK como constraint **DIFERIDA** (`ALTER TABLE
    <t> ADD CONSTRAINT fk_<t>_<col> FOREIGN KEY (<col>) REFERENCES <dst> (id);`) emitida al FINAL (tras todos los
    `CREATE TABLE`). Determinista (orden de declaración). Backward/self sigue inline (sin cambio).
  - **`_app_kt`** (s0): el sample deja en `null` un ref forward (`idx[to] >= idx[e]`, unifica self-ref + forward).
  - **`_it_repository_kt`** (s7): saltea el forward en el INSERT inicial y, con TODAS las filas sembradas, lo cablea
    **NULL-then-UPDATE**, round-trippea el ciclo VIVO (read-back cruza el id) + diente negativo (FK colgante `-id` →
    la constraint diferida la RECHAZA → `shouldThrow<DataAccessException>`). Imports condicionales (sólo si hay forward).
- **Opt-in/byte-neutro** (EYEBALL importlib HEAD vs working, sin gradle): default+assets **68/68 byte-idénticos**;
  default+assets product.yml = 0. **`proof_sha` INTACTO → SIN re-pin** (vive en s1/s7, ya pineados). No agrega requisito.
- **Adopción PRODUCTO** (ADR-016, incremento `XENTITY-CYCLES-ADOPT`): snipeit re-habilitó `Location.manager_id`→User
  y `Department.manager_id`→User (forward/cíclicos, opcionales) — restaura los ciclos Location↔User y User↔Department.
- **Verde, no fingido**: `product-run --product snipeit` **PASS** · RTM **24/25** · **diente de DOS lados VIVO** (s7:
  comenté `out += deferred` → quité la constraint diferida → la FK colgante dejó de rechazarse → **SÓLO**
  `pyramid_integration` rojo, hermanos s7 verdes; revertí→verde; el sabotaje SQL/Python no tripea s2 estático) ·
  `ci --rederive --all-products` 12/12·11/11·11/11 == pin · `meta check` 6/6 (`generality` verde). Detalle:
  `docs/work/FSK-XENTITY-CYCLES-INCREMENT.md §Evidencia`.
- **Sub-eje diferido**: un ref forward REQUERIDO que cierre ciclo (sin orden de seed) — sigue como deferral honesto.
- **SIGUIENTE**: FSK-COMPANY-SCOPING (multi-tenancy / ABAC con filtrado de lectura, deferral 8) — handoff en
  `docs/work/FSK-COMPANY-SCOPING-INCREMENT.md`.

## 2026-06-22T14:31Z — FSK-CUSTOM-FIELDS ✅: campos personalizados con `format`/validación (Avenue A) — el EJE GRANDE, acotado
- **El eje GRANDE de Snipe-IT (custom fields, deferral 1), entregado ACOTADO** (handoff §★): resuelta la decisión de
  diseño = **Avenue A** (campos DECLARADOS en el blueprint) **sub-eje `format`/validación**. Un campo `string` gana un
  modifier OPCIONAL `format: <nombre>` (vocabulario CERRADO `numeric`/`alpha`/`email`/`url`/`ip`/`mac`) — la REGLA DE
  VALIDACIÓN del VALOR, el aporte NUEVO de un custom field sobre un string normal. El **EAV dinámico a runtime
  (Avenue B)** sigue DIFERIDO y VISIBLE (la tensión schema build-time vs runtime no se resuelve por inercia).
- **Levantado GENERAL** (codegen de fábrica, `generality` verde, `git diff src/+seed=0`), opt-in/byte-neutro:
  - **Gramática + vocabulario cerrado**: `_FORMAT_REGEX` (nombre→patrón). Validación fail-closed en `_load_blueprint`
    (`format` sólo sobre `string`; nombre ∈ `_FORMAT_REGEX`; format fantasma → `raise`).
  - **El codec a RUNTIME** (`_codec_helpers`/`_parse_fn`): un string con `format` se parsea con `strFmt(o, k,
    FMT_<NAME>)` = `require(re.matches(s))` → no-match (match COMPLETO) → null → **400** (compone sobre
    FSK-CRUD-BODY-PARSING; `Regex` default-import → sin import nuevo; un `FMT_<NAME>` por format usado, dedup/sorted).
  - **El contrato** (`_oapi_inline`): `x-format: <nombre>` vendor extension (openapi-generator/openapi-typescript la
    IGNORAN), fuente inspectable de la regla (DES-6).
  - **El proof** (`_access_control_check_py`): bloque opt-in `%BAD_FORMAT_BLOCK%` — cuerpo válido de TIPO pero que
    VIOLA el format → 400 + count sin cambiar; los samples del POST/FORM pasan a valores VÁLIDOS para el format.
- **Opt-in/byte-neutro** (EYEBALL importlib HEAD vs working, sin gradle): default+assets **68/68 byte-idénticos**;
  default+assets product.yml = 0. **`proof_sha` INTACTO → SIN re-pin** (la regla vive dentro de `access_control_live`/
  s9 + s0 + s5, ya pineados). **No agrega requisito** (se prueba dentro de `access_control_live`, sin over-claim).
- **Adopción PRODUCTO** (ADR-016, incremento `CUSTOM-FIELDS-ADOPT`): snipeit `Asset` gana `{ name: mac_address, type:
  string, format: mac }` (requerido) — el custom field canónico de Snipe-IT ("MAC Address", format MAC).
- **Verde, no fingido**: `product-run --product snipeit` **PASS** · RTM **24/25** · **diente de DOS lados VIVO** (s9:
  `FMT_MAC` degradado a `.*` → `observability_live ok · access_control_live FAIL(1) · frontend_consume_live ok` →
  revertí → PASS) · `ci --rederive` 12/12·11/11·11/11 == pin · `meta check` 6/6 (`generality` verde). **Lección**: el
  sabotaje que muerde a RUNTIME sin tocar lo estático fue degradar el PATRÓN (`re` sigue usado, los `{n}` viven dentro
  del string del regex → no MagicNumber). Detalle: `docs/work/FSK-CUSTOM-FIELDS-INCREMENT.md §Evidencia`.

## 2026-06-22T13:45Z — FSK-DOMAIN-OPS ✅: verbos de DOMINIO (checkout/checkin) — el 1er eje de COMPORTAMIENTO
- **El primer eje de COMPORTAMIENTO tras 4 ejes de MODELO-DE-DATOS** (CRUD · self-ref · ownership opcional · refs
  requeridos). En Snipe-IT la operación CENTRAL no es un PUT genérico: es **checkout** (asignar un activo a un usuario:
  `status ready→deployed` + set `assigned_to`) y **checkin** (devolver: `deployed→ready` + clear `assigned_to`). Son
  **VERBOS de dominio**: transiciones NOMBRADAS de un campo enum-workflow con efecto sobre un campo `ref`, que MUTAN
  bajo **precondición de WORKFLOW** + RBAC + ownership. **Cierra el over-claim "workflow enforced"**: el guard
  `canTransition` (FSK-S12) estaba SÓLO-UNIT (s7); ahora se INVOCA a RUNTIME desde el verbo.
- **Levantado GENERAL** (codegen de fábrica, `generality` verde, `git diff src/+seed=0`), opt-in por placeholders:
  - **Gramática del blueprint** (DATA, ADR-012): una entidad con dueño declara `operations: [{name, field, from, to,
    assigns|clears}]`. Validación fail-closed en `_load_blueprint`: `operations` exige `owned_by`; `field` debe ser un
    enum CON `transitions`; `from`/`to` ∈ values **Y la transición `from→to` DEBE estar DECLARADA** (un verbo no puede
    nombrar una transición inexistente → `raise`); `assigns`/`clears` (excluyentes) nombran un `ref`.
  - **El contrato** (`_openapi_yaml`): emite `post /<plural>/{id}/<verbo>` con `security` + `x-required-roles` →
    `route_check` (auth/rbac) lo cruza GRATIS contra el RouteTable (single-source DES-6). **El registro de rutas**
    (`_routes_kt`): registra la ruta del verbo DENTRO del guard, con el roleset del POST.
  - **La mutación** (`_operation_repo_fns`, Repository): `<e><Field>Of` lee el estado actual (String) + `<verbo><E>` es
    el UPDATE atómico (campo=`to` + `set(ref, target)` / `setNull(ref)`).
  - **El handler** (`_operations_handlers`, AppServer): un `return when` (ReturnCount ≤ 2) que COMPONE **modifyVerdict**
    (RBAC + ownership) → **precondición de WORKFLOW VIVA** (`<Entity><Field>Workflow.canTransition(estado_actual, to)`,
    con `Enum.valueOf(current)`) → mutación. Estado inválido → **409**; rol/dueño → 403/404. `conflict()`/`HTTP_CONFLICT`
    CENTRALIZADOS (antes sólo en el bloque with-ref) cuando hace falta (with_ref O operations). El `handle` dispatcher
    gana `@Suppress("CyclomaticComplexMethod")` (tabla de ruteo generada; opt-in) por las 2 ramas nuevas.
- **Eyeball ANTES del gradle**: dump de default/assets (HEAD vs working) **byte-idéntico** (68/68) + `route_check`
  topology/auth/rbac/ownership VERDE sobre el árbol snipeit-con-ops + `py_compile` del proof. La 1ª corrida destapó
  **`handle` complejidad 16 > 15** (detekt CyclomaticComplexMethod) → `@Suppress` opt-in (consistente con el
  `@file:Suppress("TooManyFunctions")` y el `%MAIN_SUPPRESS%` de DbRoundTrip; complejidad inherente a un dispatcher).
- **Producto**: `snipeit/product.yml` `Asset` gana `operations: [checkout, checkin]` (nivel PRODUCTO, ADR-016,
  incremento `DOMAIN-OPS-ADOPT`). El verbo asigna/limpia `assigned_user_id` (= el dueño, también el campo de asignación
  de Snipe-IT). Target polimórfico (User|Location|Asset) → simplificado a User (deferral 2, sigue diferido).
- **Diente de DOS lados VIVO** (s9 `access_control_live`): invertí la precondición (saqué el `!` de `canTransition` en el
  handler — **flip de RUNTIME, sin hallazgo estático**: `current`/Workflow siguen usados) → el verbo rechaza el checkout
  VÁLIDO → `access_control_live FAIL(1)` con `observability_live`/`frontend_consume_live` VERDES → revertí → PASS.
- **Verde, no fingido**: `product-run --product snipeit` PASS · RTM **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless) ·
  `ci --rederive` **3/3 == pin** (base 12/12 · assets 11/11 · snipeit 11/11; `proof_sha` INTACTO → SIN re-pin, el verbo
  vive dentro de s9) · `meta check` 6/6 · `git diff src/+seed = 0` · default+assets product.yml = 0.

## 2026-06-22T04:00Z — FSK-OWNED-REQUIRED-REFS ✅: refs REQUERIDOS no-dueño / SEED TRANSITIVO — el 4º gap del push Snipe-IT
- **El companion directo de FSK-OWNERSHIP-OPTIONAL.** En Snipe-IT `Asset.model_id` es REQUERIDO (un activo SIEMPRE es de
  un modelo), pero el server vivo (FSK-S15) no sabía sembrar un `ref` REQUERIDO no-dueño en la entidad-con-dueño
  (`_seed_chain` hacía `raise`). Faithful pedía un **SEED TRANSITIVO** multi-nivel (Category → AssetModel → Asset).
- **Levantado GENERAL** (codegen de fábrica, `generality` verde, `git diff src/+seed=0`), opt-in por placeholders:
  - **`_seed_chain` se volvió transitivo** (gana `ref_wiring`: un ref requerido no-dueño se cablea al id capturado de su
    target; sin cableado → `raise` honesto). Dos seeders recursivos nuevos: **`_seed_deps`** (cableado de los refs
    requeridos de una entidad) + **`_ensure_seeded`** (siembra topológica, **deduplicada** por registry, **ciclos →
    `SystemExit`** honesto = deferral 6).
  - **`_app_server_kt`**: siembra las deps ANTES del owned, pasa el cableado al owned y a la fila RTD (REUSA via registry),
    suma tablas/imports/tipos de las deps, y expone **`ownedRefs`** (campo→id) en `Seed`/`/seed` para que el POST/FORM traiga
    FKs VÁLIDAS — todo opt-in (sin ref requerido no-dueño → byte-idéntico).
  - **Los proofs** (`access_control_check.py` + `consume_check.ts`): el POST/FORM del owned manda los ESCALARES y **inyecta
    los refs desde `/seed ownedRefs` en runtime** (como el bloque with-ref) → evita el `KeyError` de `_proof_post_value` sobre un ref.
- **La lección de "el handoff sub-estima los sitios" se INVIRTIÓ**: el handoff señalaba `_seed_chain`; el eyeball confirmó que
  **s1 (`_roundtrip_kt`) y s7 (`_it_repository_kt`) YA siembran topológicamente** (2 de 3 seeders listos) y el form (`_app_ts`)
  ya mapea `ref`→`<input number>`+`Number()` — el gap real era **un único camino** (el seed del server vivo, s9).
- **Producto**: `snipeit/product.yml` `Asset.model_id` → `required: true` (faithful). Nivel PRODUCTO (ADR-016).
- **Diente de DOS lados VIVO** (s9 `access_control_live`): saboteé el FK del POST en el proof (lado Python, `+ 9999`) → FK
  colgante → `access_control_live FAIL(1)` con `observability_live`/`frontend_consume_live` VERDES (hermanos de s9, server
  VIVO y alcanzable — el fallo es la aserción 201, no una caída) → revertí → PASS. **(1er intento con `+ 9999L` en el Kotlin
  → detekt MagicNumber → rojo en s2 ANTES de s9 → lección: el sabotaje runtime va al lado no-linteado.)**
- **Verde, no fingido**: `product-run --product snipeit` PASS · RTM **24/25** (único UNSAT = REQ-F-007/s6 keyless) · `ci
  --rederive --factory full-stack-kotlin --all-products` **3/3 == pin** (default 12/12 · assets 11/11 · snipeit 11/11,
  `proof_sha` INTACTO → SIN re-pin) · `meta check` 6/6 (`generality` verde) · `git diff src/metafactory+seed = 0` ·
  default(`factory.spec.yml`)+assets `product.yml` = 0. Detalle: `docs/work/FSK-OWNED-REQUIRED-REFS-INCREMENT.md §Evidencia`.

## 2026-06-22T03:11Z — FSK-OWNERSHIP-OPTIONAL ✅: dueño NULLABLE / RTD real — el 3er gap del push Snipe-IT
- **El caso más CORE de Snipe-IT, arreglado GENERAL.** Un activo Ready-To-Deploy está SIN asignar (dueño NULL): el
  caso NORMAL, no un borde. FSK exigía `owned_by` `required: true` porque `OwnershipGuard.canModify(rowOwnerId: Long)`
  era no-nullable y el server vivo conflaciona owner-nulo con 404. **Levantado opt-in por el `required` del `owned_by`**:
  con dueño REQUERIDO el codegen queda **byte-idéntico** (default/assets sin re-derivar); con dueño NULLABLE emite la
  variante RTD. El handoff señalaba 2 sitios; **generar de verdad destapó 4** (la lección de FSK-SELF-REF, otra vez):
  - **`_ownership_guard_kt`**: `canModify(rowOwnerId: Long?)` → `actorRole in bypass || (rowOwnerId != null &&
    actorPrincipalId == rowOwnerId)`. Una fila SIN dueño sólo la modifica un rol de bypass.
  - **`_modify_verdict_kt`** (NUEVO helper, extraído del skeleton): separa **EXISTENCIA** (reusa `<e>RowJson != null`,
    sin query nueva) de **DUEÑO** → una fila RTD EXISTE (no es 404); inexistente sigue 404. Rompe la conflación.
  - **`_mutation_fns`** (NO en el handoff): el dueño se fija al principal del token SIEMPRE (el creador es dueño),
    aunque la columna sea opcional — antes el skip-optional lo saltaba → `ownerId` sin usar (rojo).
  - **`_seed_chain` + `_sample`** (la 2ª fila, NO en el handoff): el server siembra una 2ª fila RTD (owner NULL,
    valores **ALT** en las UNIQUE: `"alt-asset_tag"` ≠ `"sample-asset_tag"`); `/seed` expone su `rtd` id.
- **Producto**: `snipeit/product.yml` `Asset.assigned_user_id` → `required: false` (RTD real). Nivel PRODUCTO (ADR-016).
- **Diente de DOS lados VIVO** (s9 `access_control_live`): saboteé `modifyVerdict` (RTD→HTTP_OK para cualquiera) →
  `access_control_live FAIL(1)` con `observability_live`/`frontend_consume_live` VERDES (hermanos de s9 — aislado) →
  revertí → verde. Tooth: RTD+no-bypass→403 / RTD+bypass→200 / inexistente→404. + diente UNIT (s7 `OwnershipGuardTest`,
  2 casos nuevos).
- **Verde, no fingido**: `product-run` PASS · RTM **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless) · `ci --rederive
  --all-products` **3/3 == pin** (12/12 · 11/11 · 11/11; **proof_sha intacto → SIN re-pin**, sólo se fortalecieron
  checks existentes) · `meta check` **6/6** (`generality` verde) · `git diff src/metafactory + seed = 0` ·
  default+assets product.yml = 0. Commits `59ebfb9` (codegen) + `c2b4079` (product.yml) + docs.
- **SIGUIENTE** (abierto): FSK-OWNED-REQUIRED-REFS (deferral 4 — `Asset.model_id` requerido vía seed transitivo
  multi-nivel; el server vivo no sabe sembrar un ref requerido no-dueño en la entidad con dueño, FSK-S15 lo `raise`ea).

## 2026-06-22T01:48Z — FSK-SELF-REF ✅: jerarquías self-ref (Location.parent_id, User.manager_id) — 1er gap del push Snipe-IT
- **El 1er gap product-driven del push Snipe-IT, arreglado GENERAL.** Una entidad con un `ref` cuyo `to` es ELLA MISMA
  (jerarquía padre/hijo) rompía la generación. Dos sitios del codegen lo asumían imposible:
  - **`_it_repository_kt`** (seeder del tier integración, s7 `pyramid_integration`): seteaba TODO ref —incl. el self—
    referenciando `ids[self]` ANTES de insertar la fila → `KeyError` (y aún capturado, FK a fila inexistente). Por eso
    Location.parent_id / User.manager_id estaban DIFERIDOS en el blueprint.
  - **`_app_kt`** (el ejercedor del contrato, s0 `contract_single_source`): emitía `managerId = user.id` DENTRO del
    propio `val user = User(...)` → auto-referencia de variable → compile rojo (este lo destapó el 1er product-run, no
    estaba en el handoff: el handoff sólo señaló `_it_repository_kt`).
- **Fix (FÁBRICA, GENERAL, cero nombres de dominio — `codegen/scaffold_product.py`)**: heurística DATA-agnóstica `to ==
  nombre de la entidad`. (a) `_it_repository_kt` siembra la self-ref como **cadena raíz→hijo**: la **raíz** con el
  self-ref en NULL (idiom de `_roundtrip_kt` con un opcional), un **hijo** apuntando a la raíz, y un **read-back** que
  cruza el id leído de la PG viva → la **FK self valida la jerarquía VIVA**. El hijo usa valores **ALTERNOS** en sus
  columnas UNIQUE (`_KT_SAMPLE_ALT`) para no violar el constraint (lo destapó User.username: root y child colisionaban
  en "it" → IntegrityConstraintViolation). `size shouldBe 2` para las entidades self-ref. (b) `_app_kt`: una self-ref
  del sample = `null` (la raíz no tiene padre; `Long?` nullable).
- **Adopción en el PRODUCTO** (incremento de producto APARTE — `products/snipeit/docs/work/SNIPEIT-SELF-REF-INCREMENT.md`,
  ADR-016 dual-nivel, el guard elige por ruta): snipeit re-habilitó `Location.parent_id`→Location y
  `User.manager_id`→User (self-ref opcionales). `Location.manager_id`→User y `Department.manager_id`→User SIGUEN
  diferidos (ciclos cross-entidad, deferral 6, otro incremento).
- **⚠️ `proof_sha` INTACTO**: no agrega check ni estación (el fix vive DENTRO de `pyramid_integration`/s0) → pines
  byte-idénticos, **SIN re-materializar, SIN re-pinear** (distinto de FSK-DEPLOY). `git diff snipeit/product.yml ≠ 0`
  es ESPERADO (trabajo de producto); el sustrato + default/assets product.yml = 0.
- **Diente de DOS lados VIVO**: saboteé el seeder self-ref (hijo → id inexistente `999999L`) → `product-run` →
  **`pyramid_integration FAIL(1)`, gate s7 SHUT**, hermanos s7 (`pyramid_unit`/`pyramid_unit_ts`/`workflow_enforced`)
  **verdes** → revertí → **verde**. (+ el diente nativo de `infra_up`: PG caída → rojo.)
- **Verde (no fingido)**: 3 product-run/`ci --rederive --all-products` **12/12 · 11/11 · 11/11 == pin** · `meta check`
  **6/6** (`generality` verde) · `git diff src/metafactory + seed = 0` · `git diff` default+assets product.yml = 0 ·
  RTM snipeit 24/25 (sólo s6 keyless, sin cambio: self-ref no es requisito nuevo).
- **Lección para la próxima**: un gap "chico y acotado" del handoff (1 función) en la práctica tocó **3** sitios del
  codegen (`_it_repository_kt` + `_app_kt` + el alt-sample de UNIQUE). El eyeball SIN gradle cazó el 1er sitio; el
  gradle real (compile s0 + FK s7) cazó los otros dos. **Generar de verdad sigue siendo el que encuentra los huecos.**

## 2026-06-22T00:06Z — FSK-DEPLOY ✅: la imagen del producto se CONSTRUYE y el contenedor RESPONDE /health VIVO
- **Cierra la ÚLTIMA media-verdad FSK**: hasta s10 el `Dockerfile` se SHIPPEA y `hermetic_build` verifica el PIN de
  la base por **grep**, pero **NADIE construía la imagen ni levantaba el contenedor** (la misma media-verdad que
  browser-form cerró para la UI, pero para el deploy). Ahora la imagen **se CONSTRUYE de verdad** (`docker build`) y
  el **contenedor LEVANTA y RESPONDE** `{"status":"UP"}` en `/health`. Tras esto **FSK está MADURO** → el trabajo
  pasa a ser product-specific (Snipe-IT).
- **Decisión §3 — había RED → opción (A)**: el `DOCKER_BASE_DIGEST` placeholder ficticio se reemplazó por el
  **digest REAL** de `eclipse-temurin:21-jre` (`sha256:8ec353b2…684603`); la base se pulleó UNA vez (cacheada local →
  `docker build` resuelve offline después, como las `postgres@sha256:` de s9). El **push a un registry** (credenciales
  + red sostenida) sigue declared-deferred.
- **Deliverable (FÁBRICA, GENERAL — `codegen/scaffold_product.py` + `factory.spec.yml` + `stations/`, cero nombres de
  dominio)**: (a) consts `DEPLOY_PORT=18596`/`DEPLOY_IMAGE` + `DOCKER_BASE_DIGEST` real; (b) **`_deploy_check_py()`**
  (proof stdlib urllib, le pega `/health` y exige UP — idiom de `obs_check.py`) emitido como `tools/deploy_check.py`;
  (c) **estación `s11`** (`depends_on: [s10]`) con check **`deploy_smoke` kind `infra_up`**: `bootstrap` =
  `installDist` + `docker build -q -t fsk_s11_deploy .` + `docker run -d -p 18596:18593`; `up: []` (el contenedor ES
  el servicio); `proof` = `deploy_check.py /health`; `down` = `docker rm -f`; (d) capability **`deploy_vivo`** (DES-1,
  artifact `Dockerfile`) + **REQ-NF-008**; (e) el ENTRYPOINT del dist = `bin/<pkg>` = **ObsServerKt PG-free** → el
  smoke NO necesita PostgreSQL (AppServer-en-contenedor con PG = scope mayor, diferido).
- **Diente de DOS lados VIVO**: (1) NATIVO de `infra_up` — contenedor caído tras teardown → el MISMO proof re-corrido
  falla (lo ejerce cada corrida verde); (2) saboteado el `ENTRYPOINT` (`/app/bin/NONEXISTENT`) → `meta verify` (re-
  corre s11) → **`deploy_smoke FAIL(127)`, gate s11 SHUT** (docker no arranca el contenedor) → restaurado (re-emit) →
  **verde**. El contenedor sano loguea `FSK_OBS_LISTENING 18593`.
- **Verde (no fingido)**: 3 product-run PASS (default·assets·snipeit, foreground) · `ci --rederive --all-products`
  **12/12 · 11/11 · 11/11 == pin** (byte-idéntico CON s11) · `meta check` **6/6** (`generality` verde) · `git diff
  src/metafactory + seed = 0` · `git diff product.yml = 0` · RTM default **24→25 COMPLETE**.
- **⚠️ Lecciones para la próxima sesión**: (i) el DEFAULT **NO re-materializa** `stations/` (lee los committeados); un
  check/estación NUEVO → re-materializar a mano (`_materialize_line` sobre la fábrica) + re-pinear los 3. **Pero**
  re-materializar TODO sobrescribe el comentario hand-edit de `s0.yml` (nota R1 del fallback `cg=codegen`) →
  restaurar `s0.yml` y quedarse SÓLO con `s11.yml` nuevo. (ii) `meta verify` re-corre la ESTACIÓN ACTIVA con
  `build=False` → ideal para el sabotaje (no regenera el artefacto). (iii) en docker 29.x `docker run -d` con
  ENTRYPOINT roto devuelve **127** en el bootstrap (fail-fast, mejor que esperar el timeout del proof).
- Detalle de cierre: `docs/work/FSK-DEPLOY-INCREMENT.md §Evidencia`.

## 2026-06-21T21:59Z — FSK-BROWSER-FORM ✅: la UI se MONTA en un DOM real (jsdom) + un FORM postea vía el cliente vivo
- **Cierra el hueco de "UI media-verdad"**: el cliente `fetch`eaba de verdad y el render producía markup como
  STRING, pero **nada montaba ese markup en un DOM ni había un FORM** para crear una fila (el proof corría en `node`
  sin DOM, aseverando sobre el string). Ahora el frontend de la entidad CON DUEÑO **se MONTA en un DOM real** y un
  **FORM** generado postea → la fila aparece como **NODO del DOM**. El salto de "usable por API" a "usable por un
  humano que llena un formulario". Tras esto, lo único FSK-general que falta para "Snipe-IT deployado" es el **deploy real**.
- **Deliverable (FÁBRICA, GENERAL — `codegen/scaffold_product.py` + `factory.spec.yml`, cero nombres de dominio)**:
  (a) **`_app_ts`** gana `mount<E>(doc: Document, base, token): Promise<void>` (opt-in a `owned_by`): crea un FORM con
  **un `<input>` por campo de `_input_fields`** (helpers `_form_input_type`/`_form_coerce` — coacción type-correct por
  tipo del contrato: `Number()` para int/number/ref, `.checked` para boolean, `.value` para string/date, `.value as
  <E>["campo"]` para enum, DES-6), cuyo `submit` (async, `void`-IIFE, `try/catch`) postea vía `create<E>`, re-trae
  `list<E>` y **RE-RENDERIZA** (`listContainer.innerHTML = render<E>List(rows)` — REUSA el render-string, aditivo);
  el 400 NO se traga (catch → `feedback="error"`). `app.ts` ahora importa `create<E>`/`list<E>` del cliente vivo.
  (b) **El proof EXTIENDE `consume_check.ts`** (helper `_browser_form_block` + `_proof_form_value`): `import { JSDOM }`
  (idéntico a `_a11y_audit_mjs`), monta en `new JSDOM(...).window.document`, llena el FORM (`input.value`/`.checked`),
  dispara `form.dispatchEvent(new dom.window.Event("submit",{cancelable,bubbles}))`, **poll** del DOM (~5 s) hasta el
  nodo nuevo, asevera **count `<li>` N→N+1** + (si el campo renderizado está en el form) que el `<li>` muestra el valor
  posteado. `FORM_BODY` usa valores DISTINTOS de `POST_BODY` (evita choque UNIQUE en la 2ª inserción).
- **Por qué hermético sin browser**: jsdom YA es dependencia (`JSDOM_VERSION`, s8 a11y) → `document`+eventos+`fetch`
  global de node sin binario de browser ni red. **Playwright (browser real) sigue declared-deferred** (ADR-012).
- **Probado POR BLOQUEO (no narrado)**:
  - **3 product-run PASS** (default·assets·snipeit, foreground): el FORM monta en un DOM jsdom y su submit crea un
    `<li>` nuevo vía `create<E>` contra el AppServer vivo + PG real.
  - **Diente de DOS lados VIVO**: saboteé el re-render del submit (`renderRows(...)`→`await list<E>(...)` sin render)
    → `meta product-run` (default) → **`observability_live ok · access_control_live ok · frontend_consume_live FAIL(1)`**
    (1/3 rojo, SÓLO ése) → revertí → verde. (+ smoke jsdom hermético con `fetch` mockeado: positivo N→N+1 con el valor
    del form en el `<li>`; negativo 400 → fila NO agregada + `feedback="error"`.)
  - **`ci --rederive --all-products` == pin** (default 11/11 · assets 10/10 · snipeit 10/10, byte-idéntico — extendí el
    check existente → `proof_sha` intacto, sin re-materializar/re-pinear).
  - **`meta check` 6/6** (`generality` verde) · `git diff product.yml`=0 · `git diff src/metafactory + seed`=0 ·
    tsc --strict+ESLint verdes (s2), bundle 1943–3687 B < 8192 (s8).
- **Scope honesto / RTM**: **no agrega requisito** (default/assets también montan su entidad con dueño, sin sobre-
  prometer) — se pliega en **REQ-F-018** (`frontend_render_live`), prosa de `tech`/`proof` actualizada (mount+form ya
  NO es deferred; sólo deploy+Playwright). RTM snipeit **23/24** (único UNSAT = s6 LLM keyless), sin cambio de conteo.
- **Lección reafirmada**: `meta station` corre la META-línea (m00–m08), NO la línea de producto FSK → la única forma
  de re-correr s9 con un sabotaje es `product-run` (re-materializa de codegen). Corré s9 FOREGROUND (puerto fijo 18595).

## 2026-06-21T20:50Z — FSK-REFS-IN-BODY ✅: el ESPINAZO RELACIONAL — refs requeridos no-dueño desde el body
- **Cierra el último hueco de la capa de DATOS**: hasta hoy `_input_fields` EXCLUÍA los `ref` y
  `_mutation_fns`/el seed LANZABAN ante un ref requerido no-dueño → toda entidad cuyo POST necesita una FK
  (en Snipe-IT: AssetModel/License/Accessory/Consumable/Component → Category, los pivots → su padre)
  generaba a nivel de contrato pero **no era creable a runtime**. Ahora **el grafo relacional ENTERO es
  CRUD-able por API**: creás una Category, después un AssetModel que la referencia. "Entidades sueltas
  usables" → "una app relacional usable".
- **Deliverable (FÁBRICA, GENERAL — `codegen/scaffold_product.py` + `factory.spec.yml`, cero nombres de
  dominio)**: (a) **tipo** — `_KT_FIELD_TYPE` mapea `ref`→`Long`; `_input_fields` incluye el ref REQUERIDO
  no-dueño (el dueño SIGUE viniendo del token). (b) **Selección DATA-agnóstica** — `_live_with_ref`: la 1ª
  entidad sin dueño, con `write_roles`, cuyos refs requeridos apuntan a targets SEMBRABLES
  (`_ref_target_seedable`: el target no tiene refs requeridos propios → cadena de profundidad 1) → snipeit
  **AssetModel** (`category_id`→Category); default (Task→Project, profundidad >1) y assets (sin ref req
  no-dueño) → **None**, opt-out intacto. (c) **codec** — `longOf` (id de la FK, estricto `require(!isString)`)
  + import `kotlinx.serialization.json.long`, sobre la unión de entidades servidas. (d) **mutación** —
  `_mutation_fns` setea el ref desde `input.<camel>`. (e) **seed del target** — `seedRows`/`_ref_targets`
  siembra UNA fila de cada target de ref requerido y `/seed` la expone como `"refs":{<campo>:<id>}`. (f)
  **FK fail-closed** — `_ownerless_handlers(catch_fk=True)`: `insert<E>OrConflict` envuelve el INSERT en
  `runCatching` → un ref COLGANTE viola la FK → `DataAccessException` → **409** (`HTTP_CONFLICT`), no 500.
  La entidad con dueño y la 1ª ownerless quedan **intactas** (aditivo, 3er `createContext`).
- **El diente NUEVO de DOS lados** (extiende el check EXISTENTE `access_control_live`, s9 infra_up): ref
  **VÁLIDO** (id del target sembrado, leído de `/seed refs`) → **201** + round-trip que cruza el id del ref ·
  ref **COLGANTE** (id+9999) → **409** fail-closed · rol prohibido → 403 · tipo equivocado → 400 · count
  invariante. **Verificado VIVO**: saboteado el atrape de la FK (with_ref al camino sin `runCatching`) →
  `product-run snipeit` **FAIL 1/3, SÓLO `access_control_live` ROJO** (`observability_live` +
  `frontend_consume_live` VERDES); revertido → PASS.
- **Sin check nuevo → pin byte-idéntico**: como EXTENDÍ `access_control_check.py` (el MISMO
  `access_control_live`), el `proof_sha` NO cambió → `ci --rederive` **snipeit 10/10 · default 11/11 · assets
  10/10 == pineado** en clon limpio, **sin re-materializar**. `pinned_verdict.json` es per-estación (NO el RTM).
- **Trazabilidad**: NO agrega requisito (evita over-claim — default/assets no tienen una entidad con ref
  requerido no-dueño sembrable): se PLEGÓ en `entrada_tipada_runtime` (**REQ-F-016**), cuyo invariant/tech/
  proof ahora cubren el ref del body + el diente FK→409. Se removió "refs-en-el-body = declared-deferred" de
  REQ-F-015/016/019 + `crud_mutacion_runtime`/`crud_ownerless_runtime`. RTM snipeit **23/24** (sólo s6 keyless).
- **Anti-overfit**: `meta check` **6/6** (`generality` verde) · `git diff product.yml` = **0** (producto = DATA)
  · `git diff src/metafactory/ + seed/` = **0** (sustrato intacto; todo en codegen+spec). El único nombre de
  dominio en el diff es un EJEMPLO en docstring (estilo `_live_ownerless`). Probado por gradle real foreground
  (la colisión de puerto fijo de s9 obliga a no-paralelo; un background race con `stop_proof` da falso rojo).
- **Lección confirmada al derecho** (de FSK-CRUD-OWNERLESS/RENDER-LIST): EXTENDER el check existente (no sumar)
  → `proof_sha` intacto → pines byte-idénticos, sin re-materializar el chasis. Detalle: `…/work/FSK-REFS-IN-BODY-INCREMENT.md §Evidencia`.

## 2026-06-21T19:28Z — FSK-CRUD-OWNERLESS ✅: la capa VIVA deja de ser opt-in a `owned_by` (CRUD RBAC-only)
- **Abre el DOMINIO a runtime**: hasta hoy toda la capa viva (server CRUD, cliente, render, consumer e2e) era
  **opt-in a `owned_by`** → sólo la entidad con dueño tenía server/CRUD vivo; el resto del dominio generaba a nivel
  de contrato (s0→s8) pero **ninguna otra entidad era usable a runtime**. En Snipe-IT eso es **1 de ~23** (sólo
  `Asset` tiene dueño). Ahora una entidad **SIN dueño** también obtiene CRUD vivo, gobernado por **RBAC-only**.
- **Deliverable (FÁBRICA, GENERAL — `codegen/scaffold_product.py` + `factory.spec.yml`, cero nombres de dominio)**:
  (a) **Selección** — `_live_ownerless`/`_live_entities` (fuente única que cruzan Repository y AppServer): la 1ª
  entidad sin dueño con `write_roles` cuyos campos requeridos son TODOS escalares (heurística DATA-agnóstica, ADR-012:
  **User** en default · **Holder** en assets · **Company** en snipeit). (b) **Repository** — `_mutation_fns`
  generalizada para `owner=None`: `insert<E>(ctx, input)` sin `ownerId` (todos los escalares del cuerpo); Input + CRUD
  para CADA entidad viva. (c) **Codec compartido** — `_codec_helpers` emite los helpers de coerción (prim/str/
  parse<E>Input) **una vez sobre la unión** de entidades servidas → sin colisión al montar >1 entidad. (d) **Server** —
  bloque ownerless ADITIVO con handlers SUFIJADOS por entidad (`doPost<E>`/`listAll<E>`/`getOne<E>`/`doDelete<E>`/
  `handle<E>`), verdict **RBAC-only** (`RoleGuard.authorize`, sin `OwnershipGuard` ni `ownerId` del token) + un 2º
  `createContext`; **la entidad con dueño queda intacta** (sus dientes no se mueven).
- **El diente RBAC de DOS lados** (extiende el check EXISTENTE `access_control_live`, s9 infra_up): el proof client
  ejercita la entidad ownerless — rol **PROHIBIDO** → 403 y el count NO cambia / rol **PERMITIDO** → 201 + count+1 ·
  round-trip del cuerpo (POST {valores ≠ samples} → GET /{id} type-correct) · body tipo equivocado → 400 · DELETE
  prohibido → 403 (sin borrar) / permitido → 200 → 404. **Verificado VIVO**: saboteado el guard RBAC ownerless (que
  un rol prohibido pase) → **SÓLO `access_control_live` ROJO** (1/3, con `frontend_consume_live` + `observability_live`
  VERDES); revertido → verde.
- **Sin check nuevo**: extiende `access_control_check.py` (el MISMO `access_control_live`) → el `proof_sha` NO cambia →
  **pines byte-idénticos, sin re-materializar el chasis ni re-pinear** (la lección de FSK-FRONTEND-CONSUME no aplicó,
  como en RENDER-LIST). Capability `crud_ownerless_runtime` (DES-3) + **REQ-F-019** citando ese check → RTM default
  **24/24 COMPLETE**, assets/snipeit **23/24** (único UNSAT sigue REQ-F-007/s6 LLM keyless), **REQ-F-019 SATISFIED**.
- **Probado por bloqueo**: `product-run` PASS en los 3 (default·assets·snipeit) · `ci --rederive --all-products`
  **3/3 == pin** (11/11·10/10·10/10) · `meta check` **6/6** (`generality` verde, `projection` re-sincronizada por
  `checkpoint`) · `git diff src/metafactory/ + seed/ = 0` (sustrato intacto) · `git diff product.yml = 0` (los 3).
- **Alcance honesto (lo que QUEDA)**: **refs requeridos en el body** (el espinazo relacional — el eje hermano, el
  SIGUIENTE incremento) · CRUD de **TODAS** las ownerless (hoy sólo la 1ª) · PUT/update ownerless · producto
  sólo-ownerless (sin entidad-ancla con dueño) · render/cliente/form para la entidad ownerless · browser/deploy/Playwright.

## 2026-06-21T18:30Z — FSK-FRONTEND-RENDER-LIST ✅: la UI RENDERIZA la lista VIVA (server lista → cliente trae → render)
- **Cierra el eslabón "la UI renderiza datos vivos"**: hasta hoy `render<E>List` era una función pura que el bundle
  de s8 medía pero que **NADIE alimentaba con filas del server**, y `GET /<plural>` devolvía sólo `{"count":N}` (no
  las filas). Ahora el server **LISTA**, el cliente **TRAE** y el render **RENDERIZA** la colección viva, e2e.
- **Deliverable (FÁBRICA, GENERAL — `codegen/scaffold_product.py` + `factory.spec.yml`, cero nombres de dominio)**:
  (a) **Server** — `GET /<plural>` (colección) pasa de `{"count":N}` a `{"count":N,"rows":[<rowJson>,…]}` vía un
  helper `listAll`; cada fila la serializa `Repository.all<E>RowsJson` que **REUSA `<e>RowJson`** (mapea `all<E>s →
  <e>RowJson(id)`, type-correct, DES-12). `count` SIGUE primero → **backward-compat** (`access_control_check.py::_count`
  intacto). (b) **Cliente** — `client.ts` gana `list<E>(base): Promise<<E>[]>` (GET → `.rows`; `res.json()` narrow
  desde `unknown` a `unknown[]` sin `any`, ts-reset/DES-10; el callsite castea a `<E>[]` type-bound al contrato).
  (c) **Render** — `render<E>List` (ya type-bound a `components["schemas"][<E>]`, DES-6) ahora apunta a la entidad
  **CON DUEÑO** (la única con capa viva — `_app_ts` elige `owned` si existe, si no cae en `entities[0]` para que s8
  siga midiendo el bundle). (d) **Consumer** — `consume_check.ts` extiende el round-trip: tras `create<E>→get<E>`,
  hace `list<E>(base) → render<E>List(rows)` y **asevera que el HTML refleja la lista VIVA** (la fila recién creada
  está en la lista traída; el markup contiene el campo renderizado de CADA fila; ≥2 filas vivas).
- **El diente** pasó de "el cliente trae UNA fila" a "**la UI refleja la COLECCIÓN viva**": un render que
  **dropea/garbla/hardcodea** filas, o un `list<E>` truncado/stale → `HTML ≠ lista viva` → rojo. **Verificado VIVO
  (dos lados)**: saboteado `render<E>List` (drop de filas) → **sólo `frontend_consume_live` ROJO**, con
  `observability_live` + `access_control_live` VERDES; revertido → verde.
- **Sin check nuevo**: extiende el MISMO `frontend_consume_live` (s9, infra_up) → el `proof_sha` NO cambia → **no
  hubo que re-materializar el chasis ni re-pinear** (la lección cara de FSK-FRONTEND-CONSUME **no aplicó**: los 3
  pines quedaron byte-idénticos). Capability `frontend_render_live` (DES-6) + **REQ-F-018** citando ese check → RTM
  snipeit **22/23** (único UNSAT sigue REQ-F-007/s6 LLM keyless). `tsc --strict`/ESLint/`no-explicit-any`/ts-reset
  muerden `client.ts`; el consumer en `frontend/` no se type-checkea (runner). Sin dep nueva (`fetch` global, ADR-012).
- **Probado por bloqueo**: `product-run` PASS en los 3 (default·assets·snipeit) · `ci --rederive --all-products`
  **3/3 == pin** · `meta check` **6/6** (`generality` verde, `projection` re-sincronizada por `checkpoint`) · `git
  diff src/metafactory/ + seed/ = 0` (sustrato intacto) · `git diff product.yml = 0` (los 3). Un gap de tipo jOOQ
  surgió y se fijó GENERAL: `it[<TBL>.ID]` es `Long?` → `!!` (consistente con `fetchOne()!!`/`get(...)!!` ya usados).
- **Sigue** (lo de mayor palanca para un Snipe-IT **usable**): CRUD de entidades **sin dueño** (la capa viva es
  opt-in a `owned_by` → 1 de ~23 en Snipe-IT) + **refs del body** (el espinazo relacional), ANTES que el render en
  browser / form / Playwright. Handoff: `docs/work/FSK-CRUD-OWNERLESS-INCREMENT.md`.

## 2026-06-21T16:14Z — FSK-FRONTEND-CONSUME ✅: el cliente TS generado CONSUME el backend vivo (fetch e2e real)
- **Abre el eje frontend real**: hasta hoy el frontend era **funciones puras** (`client.ts::summarize` interpola
  campos; `app.ts::render<E>List` arma `<ul>`; `index.html` es un form estático) — **nada en `frontend/` tocaba
  el server vivo**; el único proof e2e era `access_control_check.py` (urllib desde Python, NO el cliente del
  producto). Ahora el **cliente TS GENERADO hace `fetch` REAL contra el AppServer vivo** y se prueba el
  **round-trip e2e a través del código de cliente real**: contrato → `client.fetch` → server vivo → PG →
  respuesta → `client.parse`. El cliente y el server generados hablan el MISMO protocolo de cable, e2e.
- **Deliverable**: `client.ts` gana `create<E>(base, token, body)` (POST `/<plural>`) y `get<E>(base, id)` (GET
  `/<plural>/{id}`) usando `fetch` global, **type-bound al contrato** — el body es un `Pick<components["schemas"]
  [<E>], …>` de las claves de `_input_fields` (un drift del contrato rompe el Pick en `tsc --strict`, s2, DES-6);
  `res.json()` se NARROW desde `unknown` (ts-reset) sin `any` (DES-10). Un consumer node
  (`frontend/consume_check.ts`) IMPORTA esas funciones y corre el round-trip por `node --experimental-strip-types`
  (idiom de s7, sin paso de compilación). **`fetch` es global (DOM lib / Node 18+) → sin dep nueva, no viola
  ADR-012**; el consumer no necesita `npm install` (los imports de tipo se stripean).
- **El diente** pasó de "el server responde bien a un proof Python" a "**el cliente generado y el server generado
  hablan el mismo protocolo, e2e**": `create<E>(body ≠ samples)` POSTea → `get<E>(id)` GETea → **cada campo
  posteado vuelve EXACTO y type-correct** (un int es int, un string es string); + negativo: body de tipo
  equivocado → 400 → el cliente lo **propaga** (un cliente que no chequea `res.ok` lo traga → rojo); + server
  caído → `fetch` tira → rojo (nativo de infra_up). **Diente de DOS lados VIVO y PRECISO**: saboteado `get<E>`
  (ignora la respuesta del server, devuelve `{}`) → **s9 ROJO sólo en `frontend_consume_live`**, con
  `observability_live` + `access_control_live` VERDES (el server estaba sano; falló el CONSUMO); revertido → verde.
- **Maquinaria**: un **3er check `frontend_consume_live`** (kind `infra_up`) en s9, hermano de `access_control_live`
  — mismo AppServer (puerto/PG PROPIOS por env `FSK_AC_PORT=18595`/`FSK_PG_URL`…5437, contenedor `fsk_s9_fe_pg`,
  para no colisionar). Capability `frontend_consume_live` (DES-6) + **REQ-F-017** → **RTM snipeit 21/22 COMPLETE**
  (único UNSAT = REQ-F-007/s6 LLM keyless, deferral VISIBLE).
- **Probado por bloqueo**: `product-run` PASS en los 3 (demo · assets · snipeit) · `ci --rederive --all-products`
  **3/3 == pin** (11/11 · 10/10 · 10/10) · `meta check` **6/6** (`generality` verde). **Anti-overfit**: `git diff
  src/metafactory/ + seed/` = **0** · `git diff product.yml` = **0** (todo en `codegen/scaffold_product.py` +
  `factory.spec.yml` + el `lib:["ES2022","DOM"]` del `tsconfig` para tipar `fetch`/`Response`; los productos son DATA).
- **Sigue** (huecos honestos → próximos incrementos): **React que RENDERIZA la lista + el form que postea**
  (browser) · **deploy real** (Dockerfile vivo, no sólo el pin) · **e2e Playwright** (browser headless) · CRUD de
  entidades sin dueño · refs del body · custom-fields. El cliente ya CONSUME; falta el RENDER en browser y el ship.

## 2026-06-21T14:52Z — FSK-CRUD-BODY-PARSING ✅: el server vivo lee el CUERPO real del request
- **Cierra el último gran hueco backend de §5**: hasta FSK-S16 el server MUTABA columnas pero con **valores
  FIJOS del codegen** (samples + `"mutated"`), IGNORANDO el body. Ahora **POST inserta con los valores del
  CUERPO** (type-coerced por el schema, DES-12), **GET /{id} devuelve la fila COMPLETA** type-correct (un int
  es int, un string es string), **PUT actualiza la columna al valor del body** (PATCH-like). El dueño sigue
  viniendo del token (no del body) → no rompe el FK→User. Input **fail-closed**: JSON roto / tipo equivocado /
  required ausente → **400** (no 500, no traga).
- **El parser usa `kotlinx.serialization.json`** (dep INTENCIONAL ya en el classpath → sin hand-roll, no viola
  ADR-012): un data class `<E>Input` con coerción estricta por tipo (`str`/`int32`/`dbl`/`bool`/`dateOf`/
  `enumOf∈values`); un número crudo donde va string (o viceversa) lo rechaza la coerción → `runCatching`→null→
  400. `Repository.insert<E>` persiste el body type-bound jOOQ; `<e>RowJson` lee la fila entera serializada.
- **El diente pasó de "mutó a un valor fijo" a "mutó a lo que el cliente envió"** (`access_control_check.py`):
  POST {valores ≠ samples} → GET /{id} trae EXACTAMENTE esos valores type-correct · body malo → 400 · PUT del
  body → GET ve ese valor; + los dientes de FSK-S16 (count round-trip) y de acceso (403 sin mutar) intactos.
  **Diente de DOS lados VIVO y PRECISO**: saboteado UN campo (`status`=sample en vez del body) → s9 rojo con
  `esperaba 'ready', obtuvo 'pending'` mientras `body[asset_tag]`, los 400 y el PUT siguen verdes; revertido → verde.
- **Probado por bloqueo**: `product-run` PASS en los 3 (demo · assets · snipeit) · RTM snipeit **20/21**
  (REQ-F-016 `entrada_tipada_runtime` SATISFIED; único UNSAT = REQ-F-007/s6 LLM keyless, deferral VISIBLE) ·
  `ci --rederive --all-products` **3/3 == pin** (11/11 · 10/10 · 10/10) · `meta check` **6/6** (`generality`
  verde). **Anti-overfit**: `git diff src/metafactory/ + seed/` = **0** · `git diff product.yml` = **0** (todo
  en `codegen/scaffold_product.py` + `factory.spec.yml`; los productos son DATA).
- **2 fixes ktlint en el camino** (no overfit, GENERALES): `runCatching {` de una línea → newline tras `{`
  (regla `Wrapping`); el último handler termina en un solo `\n` (regla `NoConsecutiveBlankLines`). Lección de
  diseño confirmada: la coerción debe tirar sólo excepciones que `runCatching` atrapa, y se catchea vía
  `runCatching`/`getOrNull` (NO `catch (Exception)`, que dispara `TooGenericExceptionCaught`).
- **Sigue**: PUT-total vs PATCH-split · refs requeridos no-dueño desde el body (validar que el id existe) ·
  UNIQUE-from-body→409 · CRUD de entidades sin dueño · self-ref · custom-fields dinámicos · **frontend React
  que consume + deploy + e2e Playwright**. Autoridad: `docs/work/FSK-CRUD-BODY-PARSING-INCREMENT.md`.

## 2026-06-21T13:44Z — FSK-S16 ✅: el server vivo MUTA columnas (no sólo da el veredicto)
- **Cierra el 1er hueco de §5 que Snipe-IT expuso**: hasta FSK-S15 el server vivo DECIDÍA el acceso
  (403/200/201) pero no mutaba columnas end-to-end. Ahora **POST inserta** una fila tipada jOOQ (dueño =
  principal del actor) y devuelve el id · **PUT /{id} actualiza** la 1ª columna `string` no-unique no-dueño ·
  **DELETE /{id} borra** · + ruta viva **GET /{id}**. Todo DESPUÉS del veredicto OK (RBAC + ownership), con
  `modifyVerdict` (ex `statusForPut`) reusado para PUT y DELETE. Mutaciones tipadas en `Repository.kt`.
- **El diente pasó de VEREDICTO a ROUND-TRIP e2e** (`access_control_check.py`): POST→count+1 · PUT→GET /{id}
  ve el valor nuevo · DELETE→count vuelve + 404; los dientes de acceso siguen (prohibido→403 sin mutar,
  no-dueño→403 sin mutar). **Diente de DOS lados VIVO**: UPDATE saboteado (matchea 0 filas) → s9 rojo.
- **Probado por bloqueo**: `product-run snipeit` PASS · RTM **19/20** (REQ-F-015 `crud_mutacion_runtime`
  SATISFIED; único UNSAT = s6 LLM keyless) · `ci --rederive --all-products` **3/3 == pin** · `meta check`
  `generality` verde. **Anti-overfit**: `git diff src/metafactory/ + seed/` = 0 · `git diff product.yml` = 0
  (el cambio vive en `codegen/scaffold_product.py` + `factory.spec.yml`).
- **Gaps GENERALES destapados y arreglados acá** (el handoff no los había previsto): columna UNIQUE → valor
  único en runtime (nanoTime; el seed ya ocupaba el sample) · `import java.time.LocalDate` (date requerido) al
  FINAL por el layout de ktlint_official · `@file:Suppress("TooManyFunctions")` en AppServer (9→15 fns).
- **Sigue**: body-parsing JSON + PATCH · CRUD de entidades sin dueño · ownership opcional/RTD · self-ref ·
  custom-fields · frontend React + deploy + e2e. Autoridad: `docs/work/FSK-CRUD-MUTACION-REAL-INCREMENT.md`.

## nacimiento — generada por el Meta-Factory
- La fábrica full-stack-kotlin se construyó corriendo M0–M8 sobre su factory-spec. El sustrato no se
  escribió a mano: ascendió del template del Meta-Factory (los 13 invariantes), verificado por gate.
