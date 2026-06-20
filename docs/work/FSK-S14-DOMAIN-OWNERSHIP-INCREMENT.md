<!-- meta:doc sha=f240b7eaf45ef897fe2422e880e9065f1a3b2cb1 updated=2026-06-20T16:26Z -->
# Incremento FSK-S14-DOMAIN-OWNERSHIP

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-20T16:24Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> **HANDOFF (escrito 2026-06-20 por la sesión que cerró FSK-S13/RBAC, con el contexto fresco).** Este doc es
> AUTOCONTENIDO a propósito: asumí que mi contexto murió (`/clear`). Otro orquestador lo construye desde acá.
> Si algo no está acá o en los docs que cita, no existe. Construí por bloqueo, documentá en el gate (no al
> final), commit por fase con trailers I-10.

## 0. Orientación — leé esto primero (orquestador en frío)
1. `docs/STATE.md` §Ahora → el eje Reutilización (R1 ✅ · R2·FSK ✅: campos + workflows + **RBAC**). Este
   incremento es **R2·FSK eje #4** (autorización a nivel de FILA / ownership — ABAC acotado).
2. `docs/decisions/015` (ADR-015 §4) — R2 es expresividad de `domain.product`, **por-fábrica**, contenido de
   fábrica (ADR-012), grano: un incremento por fábrica/eje. Determinismo en VERIFICACIÓN, no en generación (I-3).
3. **`docs/work/FSK-S13-DOMAIN-RBAC-INCREMENT.md` (CERRADO) — EL PATRÓN A SEGUIR, y el predecesor DIRECTO.**
   Hizo el eje #3 (RBAC: `roles` + `write_roles` → enum `Role` + `RoleGuard` + `x-required-roles` en el
   contrato + modo `rbac` en `route_check.py`, todo en s5; diente de dos lados). Este incremento (#4, ownership)
   se construye IGUAL y COMPONE encima: RBAC dice "qué ROL escribe qué ENTIDAD"; ownership agrega "y además, un
   no-privilegiado sólo toca SUS PROPIAS filas". Mirá también `FSK-S12-DOMAIN-WORKFLOWS` y
   `FSK-S11-DOMAIN-EXPRESSIVENESS` — los cuatro comparten patrón (gramática opt-in del blueprint → guard
   determinista generado → diente de dos lados → 2 productos co-validados → RTM +1 → sustrato `src/+seed/`=0).
4. `reference/PRIMITIVES.md` (**DES-3** = "auth/regla no-salteable"). Ownership es DES-3: una escritura de un
   no-dueño no-privilegiado sobre una fila ajena DEBE bloquearse de forma determinista, como ya hacen s5/auth
   (autenticación), s5/rbac (rol) y los workflows (transición).
5. **Lo que YA existe y vas a EXTENDER (no reinventar)** — la estación **s5** (`FSK-S5-AUTH-ROUTES`) ya tiene
   TRES capas de control de acceso, todas en `factories/full-stack-kotlin/codegen/scaffold_product.py`:
   - `auth/AuthGuard.kt` (`authorize(token)`: Bearer presente → autenticado) — **autenticación** (FSK-S5).
   - `auth/Role.kt` (enum class de `roles`) + `auth/RoleGuard.kt` (`authorize(token, required: Set<Role>)`:
     extrae el rol de `"Bearer <rol>"` y exige membresía; set vacío cae a AuthGuard) — **autorización por rol**
     (FSK-S13). El `RouteTable` registra cada escritura con su `Set<Role>`; `dispatch` cruza via `RoleGuard`.
   - `tools/route_check.py` — analizador estático stdlib (sin PyYAML, sin server) con **3 modos**: `auth`
     (toda op con `security` dentro de `authenticated{}`), `topology` (set de rutas == contrato), `rbac` (cada
     op con `x-required-roles` registrada con ESE `Set<Role>`). Mirá `_contract_ops`/`_contract_role_ops`/
     `_kt_route_roles`/`_rbac` como plantilla EXACTA de cómo parsear el contrato + cruzar vs el Kotlin por tokens.
   - El contrato `openapi.yaml` ya marca `security: bearerAuth` + `x-required-roles: [...]` en cada `post`.
     Ownership AGREGA una capa de **autorización a nivel de fila** encima de esas tres.

### Cómo correr la línea FSK (lecciones caras — NO re-aprendas, son de FSK-S11/S12/S13):
- **El sandbox de Bash MATA gradle** (señal 16 → exit 144, sin output). Toda corrida de línea
  (`product-run`, `ci --rederive`, gradle directo) necesita **`dangerouslyDisableSandbox: true`** en la tool Bash.
- **Corré la línea en FOREGROUND, no en background.** Un `product-run` en background + cierre de turno dispara
  el Stop hook `stop_proof` sobre la estación activa, que CHOCA con el contenedor/puerto de la línea en vuelo.
  La línea tarda ~3 min/producto con gradle caliente; entra en el cap de 600s. Corré `ci --rederive`
  **por-producto** (`--product <p>`), NO `--all-products` (dos líneas no entran en 600s).
- `meta` = `PYTHONPATH=src python3 -m metafactory.cli <verbo>` (no hay wrapper en PATH en este shell).
- **Mantené el cwd de Bash en la raíz del repo** y usá PATHS ABSOLUTOS + subshells `( cd <abs> && … )`. Un `cd`
  filtrado a un subdir rompe el cierre de turno (4 hooks cwd-relativos — memoria `no-cd-subdirs-hook-deadlock`);
  pasa fácil (me pasó en FSK-S13: un `cd factories/...` dejó el cwd colgado y el siguiente comando falló).
- **`proof_protect` DENIEGA cualquier comando de shell que toque `.proof/`** (incluso LEER por `cat`/`python`).
  Para inspeccionar proofs/veredictos usá `meta rtm` / `meta recall` / `meta journal`, NO el filesystem.
- **El default product NO se re-materializa solo**: el check nuevo en `stations/s5.yml` lo agregás A MANO (append
  limpio al final de `checks:`, como hizo FSK-S13 — NO re-materialices con `_materialize_line`: regenera TODAS
  las estaciones y borra comentarios humanos no-spec, drift). Las INSTANCIAS sí se re-materializan en cada corrida
  (`ensure_product_instance`), así que el check les llega solo al re-derivar. Editás DOS lugares: el `factory.spec.yml`
  (proof_checks + checks de s5, para que el spec sea la fuente) Y `stations/s5.yml` (para el default vivo).
- **`gradle test --tests '*Foo'` NO matchea specs Kotest** ("No tests found"). El test de ownership es tier unit
  → vive en `src/test/kotlin/...` y corre con el resto de `gradle test` (como `RoleGuardTest` de FSK-S13). No
  necesitás un source set propio salvo que quieras atribución aislada (entonces idiom `workflowTest`).
- El RTM mapea **requisito → estación(proof) + capability → artifact** (NO usa `verified_by`): para crecer +1
  necesitás una capability con un `artifact` que EXISTA en disco + un requisito `satisfied_by: [s5]`. Artifact
  sugerido: `build/product/src/main/kotlin/webapp/auth/OwnershipGuard.kt` (nombre fijo) o un DIRECTORIO si el
  guard es por-entidad. El check dedicado da atribución limpia y muerde la proof de s5.
- **detekt `ReturnCount` capea una fun en 2 returns** (me mordió en FSK-S13 un `dispatch` con 3) → colapsá a
  booleanos (`a || b`), no early-returns. El guard vive en `src/main/kotlin` (lo escanea detekt + `-Werror`):
  cero warnings, `MatchingDeclarationName` (archivo ⇄ declaración top-level), usá `_kt_call` para líneas largas.
- Las entries de enum de openapi-generator son el **valor literal** (`@Suppress("EnumEntryName")`); los campos
  Kotlin del model son **camelCase** (`holder_id` → `holderId`, por `_camel`). Referenciá `row.holderId` en el
  guard/test → type-bound al model del contrato (diente DES-6).

## 1. Objetivo
Cuarto eje de **R2·FSK**: que `domain.product` pueda expresar **autorización a nivel de FILA (ownership)** — no
sólo "qué rol escribe qué entidad" (RBAC, ya está), sino que **un actor no-privilegiado sólo puede modificar las
filas que le PERTENECEN** (las suyas), enforced de forma DETERMINISTA (sin LLM, I-3). El caso Snipe-IT: un
`manager` administra activos, pero un editor común sólo edita SUS activos asignados; un `admin` (rol
privilegiado) bypassa. Es el último piso de control de acceso para clonar apps reales (autz fila×actor, sobre
rol×entidad). Contenido de fábrica (ADR-012): el sustrato NO se toca.

## 2. El gap exacto (qué falta hoy)
Hoy (s5) el control de acceso es por ENTIDAD: `RoleGuard.authorize(token, write_roles)` decide si el rol puede
escribir la entidad — pero CUALQUIER actor con un rol permitido puede tocar CUALQUIER fila de esa entidad. No
hay noción de DUEÑO de una fila ni de que un no-admin sólo opere sobre las suyas. Ownership agrega esa capa:
una entidad declara qué campo identifica a su dueño (`owned_by`), y un guard cruza el principal del actor contra
el dueño de la fila (con un bypass para roles privilegiados).

## 3. Diseño propuesto (concreto, buildeable — ajustable por el orquestador)
**Gramática (blueprint `domain.product`):** una pieza OPCIONAL por entidad (ausente = el comportamiento de
FSK-S13, sin romper nada — opt-in):
```yaml
roles: [admin, manager, auditor]
owner_bypass_roles: [admin]          # roles privilegiados que IGNORAN ownership (top-level, opcional; default = []).
entities:
  - name: Asset
    write_roles: [admin, manager]
    owned_by: holder_id              # el campo `ref` de ESTA entidad que apunta al principal DUEÑO de la fila
    fields: [...]
```
**Validación (fail-closed, en `_load_blueprint`, cerca del guard de RBAC de FSK-S13):** `owned_by` sólo nombra
un campo de la entidad que sea `type: ref` (el dueño es una FK a un principal); `owner_bypass_roles` ⊆ `roles`
(y sólo si hay `roles`); formas bien formadas. Forma inválida → `SystemExit` (mismo patrón que FSK-S11/S12/S13).

**Flujo END-TO-END (determinista):**
- **Contrato (OpenAPI, DES-6, fuente única):** el schema de la entidad documenta su dueño como extensión
  `x-owned-by: <field>` (vendor extension a nivel del schema object — openapi-generator/openapi-typescript la
  IGNORAN; verificá que el contrato siga parseando, como FSK-S13 con `x-required-roles`). Es la FUENTE
  inspectable de "qué campo es el dueño de cada entidad". (Opcional: `x-owner-bypass-roles` a nivel raíz o de op.)
- **Código generado (Kotlin):** un guard `auth/OwnershipGuard.kt` DETERMINISTA, type-safe sobre `Role`:
  `fun canModify(actorRole: Role, actorPrincipalId: Long, rowOwnerId: Long, bypass: Set<Role>): Boolean =
  actorRole in bypass || actorPrincipalId == rowOwnerId`. Un único guard genérico (no por-entidad) → simple, una
  sola declaración top-level (MatchingDeclarationName ok). El type-binding al model del contrato lo da el TEST
  (construye un `<Entity>` real y lee `row.<ownerFieldCamel>` → un drift del contrato rompe SU compile, diente
  DES-6, como hace `App.kt`/los tests de FSK-S11..S13). Mantenelo estático/determinista (sin server vivo).
- **Verificación estática (extendé `tools/route_check.py`, idiom probado):** un modo nuevo `ownership` que cruza
  que toda entidad con `x-owned-by` en el contrato tenga su ownership CABLEADO en el Kotlin (p.ej. un registro
  `OwnershipPolicy`/un `mapOf(Entity → ownerField)` generado, o el test que referencia ese campo) con ESE campo
  → un drift (cambiar `x-owned-by` sin regenerar el cableado) → `OWNER_MISMATCH`/`MISSING_OWNERSHIP`. Análogo a
  `_rbac`/`_auth`/`_topology`. Diente negativo EMBEBIDO (cada corrida): un probe sucio (`probe/routes/
  wrong_owner.kt` o el equivalente: un cableado con el campo dueño equivocado, FUERA de `src/` → no se shippea)
  DEBE morder por grep, fail-closed — igual que `wrong_roles.kt`/`phantom.kt`/`unguarded.kt`.
- **Test de dos lados (la prueba por bloqueo, tier unit Kotest `src/test`):** `OwnershipGuardTest` asevera TRES
  casos: el DUEÑO modifica su fila ✓ · un NO-dueño no-privilegiado es rechazado ✗ · un rol de `owner_bypass_roles`
  (admin) bypassa ✓. Romper el guard (que devuelva `true` siempre) → el lado del no-dueño falla → rojo (regen →
  verde). El test construye una entidad del contrato y lee su campo dueño → type-bound (diente DES-6).

**Dónde mapea en la línea / RTM (recomendación):** ownership es write-path/auth → su casa natural es **s5**
(donde ya viven AuthGuard/RoleGuard/RouteTable/route_check.py, ahora con auth/rbac/topology). Agregá una
**capability nueva** `ownership_enforced` (familia DES-3) + su **requisito** (REQ-F-013) + un **check**
`ownership_enforced` (`kind: product_env`) en s5 que corra `route_check.py ownership` (+ opcionalmente el test
Kotlin del guard por gradle). El RTM CRECE en 1 (default 17/17 → **18/18**). Artifact de la capability: un path
que exista para ambos productos (p.ej. `build/product/src/main/kotlin/webapp/auth/OwnershipGuard.kt`). **No
agregues una estación nueva** (más barato y honesto extender s5, como FSK-S13). **No hardcodees** campos dueño
en el sustrato — vive 100% en `factories/full-stack-kotlin/codegen/` + el spec + `product.yml`.

### Seams concretos en `factories/full-stack-kotlin/codegen/scaffold_product.py`
- `_load_blueprint` — validación fail-closed de `owned_by`/`owner_bypass_roles` (junto al guard de RBAC de S13).
- `_openapi_yaml` (el schema de cada entidad, donde hoy se emiten `properties`) — emitir `x-owned-by` cuando la
  entidad tiene `owned_by`. (Mirá cómo `_oapi_inline` ya emite `x-initial`/`x-transitions` para enums.)
- **nuevo** `_ownership_guard_kt` — el guard genérico `canModify` type-safe sobre `Role` (cuidado ReturnCount).
- **nuevo** `_test_ownership_kt` — el test de dos lados (dueño ✓ / no-dueño ✗ / bypass ✓), type-bound al model.
- `_route_check_py` — modo `ownership` (parseá `x-owned-by` del schema — sin PyYAML, idiom `_contract_role_ops`/
  `_contract_ops` — y cruzalo contra el cableado Kotlin) + el probe sucio + su rama en `main()` (3→4 modos).
- `build_files` — cablear el guard + el test + el probe + (si va) un registro `OwnershipPolicy`, OPT-IN (sólo
  cuando hay ≥1 entidad con `owned_by`), igual que el bloque RBAC opt-in `if bp.get("roles"):`.
- Cuidado con el límite de 160 de detekt (usá `_kt_call`). El guard vive en `src/main/kotlin` (detekt + `-Werror`):
  cero warnings, `MatchingDeclarationName`, `ReturnCount` ≤ 2.

## 4. Fases (plan; el orquestador las refina)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Gramática + validación + guard generado.** `owned_by`/`owner_bypass_roles` en el blueprint; fail-closed en `_load_blueprint`; `x-owned-by` en el contrato; `OwnershipGuard` type-safe; `route_check.py` modo `ownership` + probe; `OwnershipGuardTest` de dos lados. `--selftest`/`--check-idempotent` verdes; compile+detekt+test del demo verde; cruce estático ownership verde + probe muerde + tamper del contrato → rojo. | ⏳ |
| 2 | **El demo ejercita ownership + re-derive == pin.** Agregá `owned_by` (p.ej. `Project owned_by owner_id`, owner = User) + `owner_bypass_roles: [admin]` al demo; check `ownership_enforced` en s5 (spec + `stations/s5.yml`); línea s0–s10 verde · `ci --rederive` == re-pin · **RTM 17→18**. | ⏳ |
| 3 | **2º producto (assets) con ownership DISTINTO + co-validación (ADR-014).** La instancia `assets` declara ownership propio (p.ej. `Asset owned_by holder_id` — OJO: hoy `holder_id` es `required: false`; hacelo `required: true` para ownership obligatorio, o elegí otra forma); `ci --rederive --product assets` == pin, aislada. | ⏳ |
| 4 | **Cierre.** STATE/ROADMAP/LOG + diff sustrato honesto (objetivo: `src/metafactory/`+`seed/` = **0**) + suite + RTM + cerrar (flip header a CERRADO bajo `seed/lifecycle.py`, o `meta increment close`). | ⏳ |

## 5. Gate (prueba por bloqueo — dientes de dos lados, no decorativos)
- **Ownership enforced (dos+ lados):** el DUEÑO modifica ✓ · un no-dueño no-privilegiado es rechazado ✗ · un rol
  de bypass (admin) bypassa ✓ (en el test Kotlin). Romper el guard (devolver `true`) → el lado del no-dueño falla
  → rojo.
- **Diente negativo EMBEBIDO** (idiom s5, cada corrida): un probe sucio (cableado con el campo dueño equivocado,
  fuera de `src/`) DEBE morder por grep (`OWNER_MISMATCH`/`MISSING_OWNERSHIP`) o el gate es decorativo → rojo.
- **Single-source (DES-6):** el contrato emite `x-owned-by`; el guard/cableado se deriva del MISMO blueprint y el
  test es type-bound al model → tamper del campo dueño del contrato lo cruza el modo `ownership` → rojo (regen →
  verde). (Mismo enfoque honesto que FSK-S13: el tamper-tooth real es el cruce determinista + el compile del
  test type-bound, no una lista paralela decorativa.)
- **Fail-closed (validación):** `owned_by` que no nombra un `ref` de la entidad · `owner_bypass_roles` fuera de
  `roles` · forma inválida → `SystemExit`.
- **Opt-in no-regresivo:** una entidad SIN `owned_by` (o un producto sin `roles`) se comporta EXACTO como
  FSK-S13/S5; el demo y la instancia `assets` siguen verdes si no declaran ownership.

## 6. Criterio de cierre (demostrable, no narrable)
1. `domain.product` expresa ownership: `owned_by` (+ `owner_bypass_roles`); validación fail-closed VIVA.
2. El guard de ownership se GENERA y se EJERCITA por un test/analizador de **dos+ lados** (dueño ✓ / no-dueño ✗ /
   bypass ✓) — corre en el toolchain del producto, romperlo → rojo.
3. **≥2 productos FSK con políticas de ownership DISTINTAS** (entidad/principal distintos) re-derivan `== su pin`
   en clon limpio, aislados (ADR-014).
4. **Anti-overfit:** `git diff src/metafactory/ + seed/` = **0** (ownership es gramática de FÁBRICA). Suite verde ·
   RTM FSK crece (17→18) y cierra.

## 7. Notas de scope (qué NO es este incremento)
- **ABAC arbitrario por atributos** ("un editor edita activos de su DEPARTAMENTO si el costo < X") es un eje
  posterior: necesita un lenguaje de predicados sobre atributos. Este es SÓLO ownership por fila (actor == dueño
  de la fila, con bypass por rol) — el caso ABAC más común, estático y determinista.
- **Endpoints de modificación VIVOS (PUT/PATCH/DELETE por id) + el server HTTP (Ktor)** siguen
  `declared-deferred` (FSK modela GET-list + POST-create; el guard de ownership se verifica determinista + unit
  sobre filas sintéticas, como s5/RBAC se verifica sin server vivo). La verificación prueba que ninguna
  modificación de una fila ajena escapa el control POR CONSTRUCCIÓN, no que hay un endpoint PUT corriendo.
- **Reglas de negocio arbitrarias por LLM** (patrón s6/MAT-2) sigue siendo otro eje R2 (incremento aparte).
- Residual conocido (heredado de FSK-S11/S12/S13): una instancia con la estación LLM s6 **activa con key**
  necesita persistir su `Summary.kt` pineado, pero `products/*/domain_gen/` está gitignored. No lo ejercita este eje.
