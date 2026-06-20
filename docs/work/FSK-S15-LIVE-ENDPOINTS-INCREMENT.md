<!-- meta:doc sha=335b99a801e69733387ddc066c02ba01bcd87bab updated=2026-06-20T18:45Z -->
# Incremento FSK-S15-LIVE-ENDPOINTS

> **Doc de gobierno.** Estado: **CERRADO** ✅ (2026-06-20T18:45Z). Construido por bloqueo. Todo cambio de código
> vivió acá (ADR-010).
>
> **EVIDENCIA DEL CIERRE (re-derivable, no narrada):**
> - **RTM default 18→19 COMPLETE** (REQ-F-014 ← `control_acceso_runtime`: s9, artifact `endpoints/AppServer.kt`);
>   assets 18/19 (s6 LLM diferido keyless, deferral VISIBLE).
> - `ci --rederive` **default 11/11 + assets 10/10 == pin** en clon limpio (re-levanta PG viva + server, re-corre
>   el proof e2e). product-run PASS en ambos.
> - **Diente de DOS+ lados VIVO**: POST rol prohibido→403 / permitido→201 · PUT fila ajena por no-dueño→403 /
>   dueño→200 / bypass→200. `OwnershipGuard` saboteado (`canModify→true`) → el 403 del no-dueño se vuelve 200 → el
>   proof FALLA (exit 1). Server caído → el proof no conecta → rojo (diente nativo de infra_up).
> - **Anti-overfit**: `git diff src/metafactory/ + seed/` = **0 líneas** (server/endpoints = DATA de fábrica).
>   route_check topology/auth/rbac/ownership verdes con la ruta PUT nueva. `meta check` 6/6 (post-cierre).
> - **2 políticas DISTINTAS a runtime** (demo Project/User editor↔viewer ↔ assets Asset/Holder manager↔auditor).
> - Commits: `7efb373` (default) · `42cd155` (assets) · cierre (docs + `meta increment close`).
>
> **Relevo abierto: `FSK-S16` (handoff post-/clear)** — ¿seguir con R2·FSK / otras fábricas, o construir el
> PRIMER PRODUCTO real? Ver el doc de relevo + STATE §Ahora.
>
> **HANDOFF (escrito 2026-06-20 por la sesión que cerró FSK-S14/ownership, con el contexto fresco).** Este doc
> es AUTOCONTENIDO a propósito: asumí que mi contexto murió (`/clear`). Otro orquestador lo construye desde
> acá. Si algo no está acá o en los docs que cita, no existe. Construí por bloqueo, documentá en el gate (no al
> final), commit por fase con trailers I-10.
>
> **POR QUÉ ESTE EJE (decisión del ingeniero, 2026-06-20):** pregunté cuál da la MAYOR mejora a FSK. La
> trilogía de control de acceso (auth → RBAC → ownership) + los workflows están TODOS verificados ESTÁTICA +
> unit, pero **ningún server vivo los invoca sobre requests reales**: FSK genera componentes verificados, no una
> app que CORRE. Este eje cierra esa brecha — el server HTTP del producto sirve las rutas del contrato e
> INVOCA los guards a runtime, verificado e2e — y así toda la inversión de S5/S11–S14 pasa de "probada por
> construcción" a "enforzada a runtime". Compone sobre maquinaria YA probada (el server vivo de s9 + `infra_up`
> + el proof-client urllib + Repository + PG viva + los guards), así que el lift está acotado (NO es un Ktor
> greenfield). Las alternativas descartadas: reglas-de-negocio-LLM (seam MAT-2 ya probado en ASF/full-stack,
> aporte incremental), ABAC arbitrario (pulido de access-control sin dientes a runtime), R2-en-otra-fábrica (no
> mejora FSK). Quedan como ejes posteriores (§7).

## 0. Orientación — leé esto primero (orquestador en frío)
1. `docs/STATE.md` §Ahora → el eje Reutilización (R1 ✅ · R2·FSK ✅: campos + workflows + RBAC + ownership).
   Este incremento NO es R2 (no agrega expresividad a `domain.product`): es **enforcement a RUNTIME** de la
   expresividad que YA existe — el server vivo que asambla contrato + datos + control-de-acceso en una app.
2. **`docs/work/FSK-S14-DOMAIN-OWNERSHIP-INCREMENT.md` (CERRADO) — el predecesor DIRECTO** y el último piso del
   control de acceso (ownership). Mirá también `FSK-S13-DOMAIN-RBAC` (RBAC) y `FSK-S5-AUTH-ROUTES` (auth +
   topología). Los guards que este incremento va a INVOCAR salieron de ahí. El PATRÓN de construcción (gramática
   → guard determinista → diente de dos lados → 2 productos co-validados → RTM +1 → sustrato=0) se mantiene,
   pero acá el "guard" ya existe: lo nuevo es el **server que lo llama** y la **verificación e2e**.
3. **El patrón de SERVER VIVO ya está en la fábrica (s9, observabilidad) — es lo que vas a EXTENDER/REUSAR, no
   reinventar.** `factories/full-stack-kotlin/codegen/scaffold_product.py`:
   - `_obs_server_kt` → `observability/ObsServer.kt`: el server HTTP **VIVO** del producto (`com.sun.net.
     httpserver`, **stdlib del JDK, NO Ktor**), `mainClass = "<pkg>.observability.ObsServerKt"`. Hoy sirve
     `/health`·`/ready` + emite trazas OTel. **`installDist`** (plugin `application` en `build.gradle.kts`)
     produce `build/install/<pkg>/bin/<pkg>` → `infra_up` lo corre en background como proceso java plano.
   - `_obs_check_py` → `tools/obs_check.py`: el **proof client** stdlib (`urllib`) que hace **requests HTTP
     REALES** contra el server vivo y verifica propiedades (correlation-id en span+log). `OBS_PORT = 18593`
     (DATA, fuera del rango efímero del SO). Es el molde EXACTO del proof client que vas a escribir.
   - El check **`observability_live`** en s9 (`kind: infra_up`): `up` levanta el server (process group, env
     scrubbed DES-8/9), el `proof` hace los requests, **teardown SIEMPRE**; server caído → rojo (diente nativo
     de `infra_up`, MAT-3). Mirá `verify/checks/infra_up.py` y la estación s9 en `factory.spec.yml` + `stations/
     s9.yml` — son el molde de cómo orquestar un server vivo + proof contra él.
4. **Los guards + datos que el server va a CABLEAR (ya existen, generados):**
   - `auth/AuthGuard.kt` (`authorize(token)`: Bearer presente) · `auth/Role.kt` (enum) · `auth/RoleGuard.kt`
     (`authorize(token, required: Set<Role>)`: extrae el rol de `"Bearer <rol>"` via `roleOf` y exige
     membresía) · `auth/OwnershipGuard.kt` (`canModify(actorRole, actorPrincipalId, rowOwnerId, bypass)`) ·
     `auth/OwnershipPolicy.kt` (`ownerField: Map<String,String>` + `bypass: Set<Role>`).
   - `routes/RouteTable.kt` (`appRoutes()` + `dispatch(method, path, token)` que YA cruza `RoleGuard` por ruta).
   - `Repository.kt` (queries jOOQ tipadas `all<Entity>s(ctx)`) + la PG viva (Flyway migrate, ver `DbRoundTrip.
     kt` / `RepositoryIT.kt` — el patrón de levantar PG por `infra_up` con `bootstrap`, MAT-3).
   - El contrato `openapi.yaml`: hoy `GET /<plural>` (list) + `POST /<plural>` (create, con `security` +
     `x-required-roles` + el schema con `x-owned-by`). Para ejercitar OWNERSHIP a runtime hace falta una ruta
     de **modificación por id** (PUT/PATCH/DELETE `/<plural>/{id}`) — hoy NO está (ver §3, es parte del scope).

### Cómo correr la línea FSK (lecciones caras — NO re-aprendas, son de FSK-S11..S14):
- **El sandbox de Bash MATA gradle** (señal 16 → exit 144, sin output). Toda corrida de línea (`product-run`,
  `ci --rederive`, gradle directo) necesita **`dangerouslyDisableSandbox: true`** en la tool Bash.
- **Corré la línea en FOREGROUND, no en background.** Un `product-run`/`ci` en background + cierre de turno
  dispara el Stop hook `stop_proof` sobre la estación activa, que CHOCA con el contenedor/puerto de la línea en
  vuelo. La línea tarda ~3 min/producto con gradle caliente; entra en el cap de 600s. Corré `ci --rederive`
  **por-producto** (`--product <p>`), NO `--all-products` (dos líneas no entran en 600s).
- **El server vivo necesita un PUERTO** (como `OBS_PORT=18593`). Elegí un puerto DATA fuera del rango efímero
  del SO (32768–60999) o un **socket Unix** (el idiom de full-stack-TS/iot, sin puerto, re-derivable y sin
  flake). `infra_up` hace teardown SIEMPRE; aun así, server vivo + PG viva = dos servicios → el `up` debe
  orquestar ambos (mirá cómo MAT-3 compuso `product_env ⊕ infra_up` con `bootstrap`).
- `meta` = `PYTHONPATH=src python3 -m metafactory.cli <verbo>` (no hay wrapper en PATH en este shell).
- **Mantené el cwd de Bash en la raíz del repo** y usá PATHS ABSOLUTOS + subshells `( cd <abs> && … )`. Un `cd`
  filtrado a un subdir rompe el cierre de turno (4 hooks cwd-relativos — memoria `no-cd-subdirs-hook-deadlock`).
- **`proof_protect` DENIEGA cualquier comando de shell que toque `.proof/`** (incluso LEER por `cat`/`python`).
  Para inspeccionar proofs/veredictos usá `meta rtm` / `meta recall` / `meta journal`, NO el filesystem.
- **El default product NO se re-materializa solo**: un check nuevo en una estación lo agregás A MANO (append
  limpio en `stations/<id>.yml` + el `factory.spec.yml`) — NO re-materialices con `_materialize_line` (regenera
  TODAS las estaciones y borra comentarios humanos no-spec). Si AGREGÁS UNA ESTACIÓN NUEVA (s11), sí hay que
  materializar su `stations/s11.yml` (y cablear `station_sequence` + `depends_on` en el spec); revertí las
  estaciones que no tocaste (`git checkout stations/sX.yml`). Las INSTANCIAS se re-materializan en cada corrida.
- **`gradle test --tests '*Foo'` NO matchea specs Kotest** (usa source sets propios). Pero acá el grueso de la
  prueba es e2e por `infra_up` (proof client urllib contra el server vivo), NO unit — el unit (guards) ya está.
- El RTM mapea **requisito → estación(proof) + capability → artifact**: para crecer +1 necesitás una capability
  con un `artifact` que EXISTA en disco + un requisito `satisfied_by: [<estación>]`. Artifact sugerido: el
  server que monta las rutas (p.ej. `build/product/src/main/kotlin/webapp/.../AppServer.kt`) o el proof client.
- **detekt `ReturnCount` ≤ 2 / `MaxLineLength` 160 / `MatchingDeclarationName`** sobre `src/main/kotlin` (+
  `-Werror`): el server nuevo vive ahí → cuidá imports ordenados sin wildcard, sin excepción tragada (mirá los
  `@Suppress` puntuales de `DbRoundTrip.kt`/`FileSpanExporter.kt` para los casos legítimos). Los campos Kotlin
  del model son **camelCase** (`holder_id`→`holderId`, por `_camel`); el contrato/`x-owned-by` es snake_case.

## 1. Objetivo
Que el producto FSK exponga un **server HTTP VIVO** que sirve las rutas del contrato (list/create, y
**modify-by-id**) e **INVOCA los guards generados** (AuthGuard → RoleGuard → OwnershipGuard) + persiste vía
`Repository` contra la **PostgreSQL viva**, verificado **END-TO-END** por requests HTTP reales: una escritura
con rol prohibido → **403**, una modificación de una fila ajena por un no-dueño no-privilegiado → **403**, el
dueño (o un rol de bypass) → **200**. Transforma la trilogía de control de acceso de "probada por construcción"
(estático + unit de S5/S13/S14) a **"enforzada a runtime"** — el server que convierte los componentes
verificados de FSK en una **app que corre**. Contenido de fábrica (ADR-012): el sustrato NO se toca.

## 2. El gap exacto (qué falta hoy)
Hoy `RouteTable.dispatch(method, path, token)` existe y cruza `RoleGuard`, y `OwnershipGuard.canModify` existe y
está probado unit — pero **nadie los llama con una request real**. El único server vivo (s9 `ObsServer`) sólo
sirve `/health`·`/ready` + trazas; no monta las rutas CRUD del contrato, no invoca los guards, no persiste. No
hay un camino donde un `POST /assets` con `"Bearer auditor"` reciba 403, ni donde un modify de un activo ajeno
por un `manager` no-dueño reciba 403 a runtime. Además el contrato no tiene rutas de modificación por id
(PUT/PATCH/DELETE), que son las que ownership necesita para tener sentido a runtime (modificar una fila
EXISTENTE de un dueño). La verificación de S5/S13/S14 prueba que el control es correcto POR CONSTRUCCIÓN; falta
probar que **ninguna request real lo saltea**.

## 3. Diseño propuesto (concreto, buildeable — ajustable por el orquestador)
**Contrato (OpenAPI, DES-6, fuente única):** emitir, para las entidades con `owned_by` (o para todas — decisión
del orquestador), una ruta de **modificación por id**: `put /<plural>/{id}` con `security: bearerAuth` +
`x-required-roles` (mismo set que el POST) — el schema ya documenta el dueño con `x-owned-by`. Verificá que el
contrato siga parseando (openapi-generator/openapi-typescript). Esto extiende `_openapi_yaml` (y, si querés que
`route_check.py topology` siga cuadrando, el set de rutas Kotlin del `RouteTable` debe incluir la nueva ruta).

**Server vivo (Kotlin, `com.sun.net.httpserver`, REUSÁ el patrón de `ObsServer`):** un server que monta las
rutas del contrato y, en CADA request, ANTES de ejecutar, aplica el control de acceso:
- **list (`GET /<plural>`):** pública (o autenticada, según el contrato) → `Repository.all<Entity>s(ctx)` contra
  la PG viva → 200 con el cuerpo.
- **create (`POST /<plural>`):** `RouteTable.dispatch`/`RoleGuard.authorize(token, requiredRoles)` → rol no
  permitido → **403**; permitido → inserta (o, mínimo, devuelve 201) y, si la entidad tiene dueño, fija el dueño
  = el principal del actor.
- **modify (`PUT /<plural>/{id}`):** RBAC (rol) **y** ownership: cargá la fila (`Repository.<entity>ById(ctx,
  id)` — agregalo, jOOQ tipado), leé su dueño (`row.<ownerFieldCamel>`), y aplicá
  `OwnershipGuard.canModify(actorRole, actorPrincipalId, rowOwnerId, OwnershipPolicy.bypass)` → no-dueño
  no-privilegiado → **403**; dueño o bypass → **200** (y, opcional, ejecutá el update). El veredicto de
  AUTORIZACIÓN (403 vs 200) ES el diente; el update real es un plus.
- **Token con principal:** ownership necesita el id del actor. Extendé el esquema estático/determinista a
  `"Bearer <rol>:<principalId>"` (o un header `X-Principal-Id`) — `RoleGuard.roleOf` ya parsea el rol; agregá un
  `principalOf(token): Long?`. Sin server real de identidad (JWT real = declared-deferred). Decisión de diseño
  del orquestador; mantenelo estático (re-derivable sin red, como `"Bearer <rol>"` de RBAC).

**Verificación e2e (extendé el patrón `infra_up` de s9, idiom probado):** un check `access_control_live` (`kind:
infra_up`) que: `bootstrap` levanta la PG (como MAT-3) + migra; `up` levanta el server vivo (installDist,
process group, env scrubbed); el **proof client** (stdlib `urllib`, molde `obs_check.py`) hace requests REALES y
asevera el control a runtime (DOS+ lados):
- `POST /<plural>` con rol PERMITIDO → 201/200 ✓ · con rol PROHIBIDO (p.ej. `auditor`/`viewer`) → **403** ✓.
- seed de una fila propiedad del principal 7; `PUT /<plural>/{id}` como principal 99 (no-dueño, rol no-bypass) →
  **403** ✓ · como principal 7 (dueño) → **200** ✓ · como un rol de `owner_bypass_roles` (admin) → **200** ✓.
- **Diente de dos lados VIVO:** con el guard saboteado (`RoleGuard`/`OwnershipGuard` → autorizar todo) el 403 se
  vuelve 200 → el proof FALLA (no-decorativo). **Server caído → el proof falla** (diente nativo de `infra_up`).
- Teardown SIEMPRE. Sin red externa: PG por contenedor pineado (digest), server local. Re-derivable
  (`ci --rederive` re-levanta server+PG en clon limpio y re-corre el proof — como s9/MAT-3).

**Dónde mapea en la línea / RTM (recomendación):** el server vivo YA vive en **s9** → lo más barato y honesto es
**extender s9** (su `ObsServer` se vuelve el server REAL del producto: instrumentado + sirviendo las rutas con
control de acceso) con un check nuevo `access_control_live` que reusa el `up`/teardown de `infra_up`. Capability
nueva `access_control_live` (familia DES-3) + requisito **REQ-F-014** → **RTM default 18/18 → 19/19**. Artifact:
el server que monta las rutas (un `.kt` que exista para ambos productos). **Alternativa** (si preferís separar
observabilidad de request-handling): una estación nueva **s11** "endpoints vivos + control de acceso a runtime"
con su `AppServer.kt` propio (mismo patrón `com.sun.net.httpserver` + `infra_up`); cuesta materializar
`stations/s11.yml` + cablear `station_sequence`/`depends_on` (ver §0 lecciones). Recomendación: **extender s9**
salvo que el server CRUD ensucie demasiado la historia de observabilidad. **No hardcodees** rutas/roles en el
sustrato — todo en `factories/full-stack-kotlin/codegen/` + el spec + `product.yml` (`git diff src/+seed = 0`).

### Seams concretos en `factories/full-stack-kotlin/codegen/scaffold_product.py`
- `_openapi_yaml` — emitir `put /<plural>/{id}` (security + x-required-roles) para las entidades con `owned_by`.
- `_routes_kt` — registrar la ruta de modificación en el `RouteTable` (para que `route_check.py topology` cuadre).
- `_repository_kt` — agregar `<entity>ById(ctx, id)` tipado (jOOQ) para que el server cargue la fila y lea su dueño.
- `_role_guard_kt` (o un helper nuevo) — `principalOf(token): Long?` (extrae el principal de `"Bearer <rol>:<id>"`).
- **nuevo** `_app_server_kt` (o extender `_obs_server_kt`) — el server `com.sun.net.httpserver` que monta las
  rutas e invoca AuthGuard/RoleGuard/OwnershipGuard + Repository; cuidá detekt (ReturnCount/MaxLineLength) y `-Werror`.
- **nuevo** `_access_control_check_py` — el proof client `urllib` (molde `_obs_check_py`) que hace los requests
  e2e de dos+ lados (403/200 por rol y por dueño) + el diente del guard saboteado + server-caído.
- `build_files` — cablear el server + el proof client + (si va) el registro de rutas, OPT-IN razonable (el server
  siempre sirve list/create; las rutas de ownership sólo si hay `owned_by`). El sustrato no nombra tech.
- Spec + `stations/s9.yml` (o `s11.yml`): el check `access_control_live` (`kind: infra_up`) + la capability +
  REQ-F-014. Editás el `factory.spec.yml` (fuente) Y la estación viva (default no se re-materializa solo).

## 4. Fases (plan; el orquestador las refina)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Contrato + server + guards cableados.** `put /<plural>/{id}` en el contrato; `principalOf` en el token; `<entity>ById` en Repository; el server `com.sun.net.httpserver` que monta las rutas e invoca los guards; compile + detekt + `-Werror` verdes; `--selftest`/`--check-idempotent` verdes; `route_check.py topology/auth/rbac/ownership` siguen verdes con la ruta nueva. | ⏳ |
| 2 | **El demo enforza a runtime + re-derive == pin.** Check `access_control_live` (`kind: infra_up`) en s9 (spec + `stations/s9.yml`); el proof client e2e (403 por rol / 403 por dueño / 200 dueño / 200 bypass); línea verde · `ci --rederive` == re-pin · **RTM 18→19**. Diente VIVO: guard saboteado → 403 se vuelve 200 → rojo; server caído → rojo. | ⏳ |
| 3 | **2º producto (assets) e2e + co-validación (ADR-014).** La instancia `assets` enforza su propia política (Asset/Holder, manager no-dueño → 403) a runtime; `ci --rederive --product assets` == pin, aislada. | ⏳ |
| 4 | **Cierre.** STATE/ROADMAP/LOG + diff sustrato honesto (`src/metafactory/`+`seed/` = **0**) + suite + RTM + cerrar (flip header a CERRADO / `meta increment close`). | ⏳ |

## 5. Gate (prueba por bloqueo — dientes de dos lados, no decorativos)
- **Control de acceso a RUNTIME (dos+ lados):** request real con rol PROHIBIDO → **403** ✓ / permitido → 200 ✓;
  modify de fila AJENA por no-dueño no-priv → **403** ✓ / dueño o bypass → 200 ✓. Saboteá el guard (autorizar
  todo) → el 403 se vuelve 200 → el proof FALLA → rojo (regen → verde).
- **Server-caído (diente nativo `infra_up`):** con el server abajo el proof client falla (connection refused) →
  rojo — prueba que el proof habla con un server VIVO, no con una fachada (façade-trap, como s9/MAT-3).
- **Single-source (DES-6):** el server deriva rutas/roles/dueño del MISMO contrato/guards generados del
  blueprint; un drift (ruta sin contrato, rol/dueño cambiado) lo cruzan `route_check.py` (topology/rbac/
  ownership) + el compile type-bound → rojo.
- **Re-derivable sin red externa:** `ci --rederive` re-levanta server + PG (contenedor pineado por digest) en
  clon limpio y re-corre el proof == pin (como s9/MAT-3; SAFE-3 docker-dependiente, decisión de fidelidad).

## 6. Criterio de cierre (demostrable, no narrable)
1. El producto expone un **server HTTP vivo** que sirve las rutas del contrato e **invoca los guards** (auth +
   RBAC + ownership) + persiste vía Repository contra la PG viva.
2. El control de acceso se EJERCITA **e2e** por un proof client de **dos+ lados** (403 por rol / 403 por dueño /
   200 dueño / 200 bypass) contra el server VIVO; saboteá el guard → rojo; server caído → rojo.
3. **≥2 productos FSK** enforzan políticas DISTINTAS a runtime (demo Project/User ↔ assets Asset/Holder) y
   re-derivan `== su pin` en clon limpio, aislados (ADR-014).
4. **Anti-overfit:** `git diff src/metafactory/ + seed/` = **0** (el server/endpoints son contenido de FÁBRICA).
   Suite verde · RTM FSK crece (18→19) y cierra.

## 7. Notas de scope (qué NO es este incremento)
- **JWT/identidad real, sesiones, refresh tokens:** `declared-deferred`. El token es estático/determinista
  (`"Bearer <rol>:<principal>"`) — suficiente para probar que el control NO se saltea, sin un IdP vivo.
- **Frontend que CONSUME los endpoints (React vivo) + e2e de browser (Playwright):** siguen `declared-deferred`
  (la verificación es server-side por proof client, como s5/s9). El client TS tipado ya existe (s0).
- **CRUD completo (update real de columnas, DELETE con cascada, paginación, filtros):** opcional — el diente es
  la DECISIÓN de autorización (403/200), no la mutación. Hacé el mínimo honesto; el resto es eje posterior.
- **Ejes R2 restantes** (reglas-de-negocio por LLM bajo gate · ABAC arbitrario por atributos · R2 en otras
  fábricas) siguen pendientes, un incremento por fábrica/eje (ADR-012) — ver `work/ROADMAP.md §Fase R`.
- Residual conocido (heredado de FSK-S11..S14): una instancia con la estación LLM s6 **activa con key** necesita
  persistir su `Summary.kt` pineado, pero `products/*/domain_gen/` está gitignored. No lo ejercita este eje.
