<!-- meta:doc sha=31a1d7bc7afba93da0d9153dff4e064b646d1485 updated=2026-06-20T14:13Z -->
<!-- meta:doc sha=PENDING updated=2026-06-20T14:11Z -->
# Incremento FSK-S13-DOMAIN-RBAC

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-20T14:11Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> **HANDOFF (escrito 2026-06-20 por la sesión que cerró FSK-S12/workflows).** Este doc es AUTOCONTENIDO a
> propósito: asumí que el contexto de quien lo abrió murió (`/clear`). Otro orquestador lo construye desde acá.
> Si algo no está acá o en los docs que cita, no existe. Construí por bloqueo, documentá en el gate (no al
> final), commit por fase con trailers I-10.

## 0. Orientación — leé esto primero (orquestador en frío)
1. `docs/STATE.md` §Ahora → el eje Reutilización (R1 ✅ · R2·FSK ✅: campos + workflows). Este incremento es
   **R2·FSK eje #3** (autorización por rol).
2. `docs/decisions/015` (ADR-015 §4) — R2 es expresividad de `domain.product`, **por-fábrica**, contenido de
   fábrica (ADR-012), grano: un incremento por fábrica/eje. Determinismo en VERIFICACIÓN, no en generación (I-3).
3. **`docs/work/FSK-S12-DOMAIN-WORKFLOWS-INCREMENT.md` (CERRADO) — EL PATRÓN A SEGUIR.** Hizo el eje #2
   (workflows: `enum` + `initial`/`transitions` → guard `canTransition` determinista, type-bound al enum del
   contrato, diente de dos lados). Este incremento (#3, RBAC) se construye IGUAL: extiende la gramática del
   blueprint, genera un guard determinista, fluye end-to-end, co-valida 2 productos, dientes de dos lados.
   También mirá `FSK-S11-DOMAIN-EXPRESSIVENESS` (eje #1, vocabulario de campos) — los tres comparten patrón.
4. `reference/PRIMITIVES.md` (**DES-3** = "auth/regla no-salteable"). RBAC es DES-3 puro: una operación que un
   rol NO tiene permitida DEBE bloquearse de forma determinista, como ya hace s5 con la autenticación.
5. **Lo que YA existe y vas a EXTENDER (no reinventar)** — la estación **s5** (`FSK-S5-AUTH-ROUTES`) ya da el
   andamiaje de rutas/auth: `auth/AuthGuard.kt` (Bearer present → autorizado), `routes/RouteTable.kt` (las
   escrituras se registran dentro de `authenticated {}`), `tools/route_check.py` (analizador estático, stdlib,
   sin PyYAML, con 2 modos `auth`/`topology` que cruzan las rutas Kotlin contra el contrato OpenAPI). El
   contrato ya marca `security: bearerAuth` en cada `post`. RBAC AGREGA la capa de **autorización por rol**
   encima de esa **autenticación**.

### Cómo correr la línea FSK (lecciones caras — NO re-aprendas):
- **El sandbox de Bash MATA gradle** (señal 16 → exit 144, sin output). Toda corrida de línea
  (`product-run`, `ci --rederive`, gradle directo) necesita **`dangerouslyDisableSandbox: true`** en la tool Bash.
- **Corré la línea en FOREGROUND, no en background.** Un `product-run` en background + cierre de turno dispara
  el Stop hook `stop_proof` sobre la estación activa, que CHOCA con el contenedor/puerto de la línea en vuelo.
  La línea tarda ~3 min/producto con gradle caliente; entra en el cap de 600s. Corré `ci --rederive`
  **por-producto** (`--product <p>`), NO `--all-products` (dos líneas no entran en 600s).
- `meta` = `PYTHONPATH=src python3 -m metafactory.cli <verbo>` (no hay wrapper en PATH en este shell).
- Mantené el cwd de Bash en la raíz del repo (el Stop hook y otros 3 hooks son cwd-relativos; un `cd` filtrado
  a un subdir rompe el cierre de turno — memoria `no-cd-subdirs-hook-deadlock`). Usá `( cd <abs> && … )` subshells.
- **El default product NO se re-materializa solo**: tras editar el spec (`station_sequence`/checks), re-materializá
  `stations/<id>.yml` desde el spec con `_materialize_line` (snippet en FSK-S12 §commits). Las INSTANCIAS sí se
  re-materializan en cada corrida (`ensure_product_instance`). OJO: re-materializar regenera TODAS las estaciones
  y borra comentarios humanos no-spec (drift); revertí las que no tocaste (`git checkout stations/sX.yml`).
- **`gradle test --tests '*Foo'` NO matchea specs Kotest** ("No tests found"). Si querés un check dedicado que
  corra SÓLO un subconjunto de tests, usá un **source set propio** (idiom `integrationTest`/`testProbe`/
  `workflowTest`) con su task `Test`, no un filtro `--tests`. (Lección de FSK-S12.)
- El RTM mapea **requisito → estación(proof) + capability → artifact** (NO usa `verified_by`): para que el RTM
  CREZCA +1 necesitás una capability con un `artifact` que exista en disco (usá un DIRECTORIO si el nombre de
  archivo depende de la entidad, p.ej. `…/webapp/workflow/`) + un requisito `satisfied_by` una estación cuya
  proof abra. El check dedicado da atribución limpia y muerde la proof de esa estación.
- Las entries de enum de openapi-generator son el **valor literal** (`@Suppress("EnumEntryName")`): referenciá
  `<Entity>.<FieldPascal>.<value>` (p.ej. `Asset.Status.ready`), como en `_workflow_kt`/`_enum_ref`.

## 1. Objetivo
Tercer eje de **R2·FSK**: que `domain.product` pueda expresar **autorización por rol (RBAC)** sobre las
operaciones de escritura — no sólo "hay que estar autenticado" (lo que s5 ya da), sino **qué ROL puede hacer
QUÉ operación sobre QUÉ entidad**, enforced de forma DETERMINISTA (sin LLM, I-3). Una escritura con un rol no
autorizado se bloquea por construcción. Es el siguiente PISO para clonar apps reales con control de acceso
(Snipe-IT: un `viewer` ve activos pero no los crea/archiva; un `admin` sí). Contenido de fábrica (ADR-012):
el sustrato NO se toca.

## 2. El gap exacto (qué falta hoy)
Hoy (s5) `AuthGuard.authorize(token)` sólo verifica que haya un Bearer token (AUTENTICACIÓN). El contrato marca
`security: bearerAuth` en cada `post` y `route_check.py` (modo `auth`) prueba que toda escritura esté dentro de
`authenticated {}` — pero **cualquier** token autenticado puede hacer **cualquier** escritura. No hay noción de
ROLES ni de que `viewer` no pueda `POST /assets`. RBAC agrega esa capa de **autorización**: el token porta un
rol, la operación declara qué roles la pueden ejecutar, y el guard cruza ambos.

## 3. Diseño propuesto (concreto, buildeable — ajustable por el orquestador)
**Gramática (blueprint `domain.product`):** dos piezas OPCIONALES (ausentes = el comportamiento de s5, sin
romper nada — opt-in):
```yaml
roles: [admin, editor, viewer]      # el universo de roles del producto (top-level de domain.product)
entities:
  - name: Asset
    write_roles: [admin, editor]    # quién puede ESCRIBIR (POST) esta entidad; ausente = cualquier autenticado
    fields: [...]
```
**Validación (fail-closed, en `_load_blueprint`):** `write_roles` sólo si `roles` está declarado; todo rol de
`write_roles` ∈ `roles`; `roles`/`write_roles` bien formados (listas de strings). Forma inválida → `SystemExit`
(mismo patrón que el guard de tipo de FSK-S11 y el de workflows de FSK-S12).

**Flujo END-TO-END (determinista):**
- **Contrato (OpenAPI, DES-6, fuente única):** la op de escritura documenta los roles requeridos como extensión
  `x-required-roles: [admin, editor]` en el `post` (vendor extension, openapi-generator/openapi-typescript la
  IGNORAN — verificá que el contrato siga parseando, como hizo FSK-S12 con `x-transitions`). El contrato es la
  FUENTE inspectable de "qué rol necesita cada escritura".
- **Código generado (Kotlin):** un enum `Role` type-safe (generado del blueprint, NO del contrato — el contrato
  no tiene un schema de Role; o emitilo como un `enum class Role` propio en `auth/`) + un guard
  `RoleGuard`/extensión de `AuthGuard`: `fun authorize(token: String?, required: Set<Role>): Boolean` que
  extrae el rol del token (decisión de diseño: el token tipado, p.ej. `"Bearer <role>"`, igual que s5 usa
  `"Bearer "` como esquema — mantenelo estático/determinista, sin server vivo) y verifica membresía. El
  `RouteTable` registra cada escritura con sus roles requeridos y `dispatch` los pasa al guard. Opt-in: una
  entidad sin `write_roles` → `dispatch` se comporta como s5 (sólo exige autenticación).
- **Verificación estática (extendé `tools/route_check.py`, idiom probado):** un modo nuevo `rbac` que cruza que
  toda op con `x-required-roles` en el contrato esté registrada en el `RouteTable` con ESE set de roles
  (alcanzabilidad de RBAC), análogo a los modos `auth`/`topology`. Diente negativo EMBEBIDO (no-decorativo,
  cada corrida): un probe sucio (`probe/routes/wrong_roles.kt`: una escritura con el set de roles equivocado,
  FUERA de `src/` → no se shippea) DEBE morder por grep, fail-closed — igual que `probe/routes/phantom.kt`/
  `unguarded.kt` de s5.
- **Test de dos lados (la prueba por bloqueo):** un test del producto (tier unit Kotest, `src/test`, idiom
  `AuthGuardTest`/`RouteTableTest`, o un source set dedicado como `workflowTest` si querés atribución aislada)
  que asevera: un rol PERMITIDO escribe ✓ Y un rol NO-permitido es rechazado ✗. Romper el guard (que autorice
  todo) → el lado prohibido falla → rojo (regen → verde).

**Dónde mapea en la línea / RTM (recomendación):** RBAC es write-path/auth → su casa natural es **s5**
(`FSK-S5-AUTH-ROUTES`), donde ya viven `AuthGuard`/`RouteTable`/`route_check.py`. Agregá una **capability nueva**
`rbac_enforced` (familia DES-3) + su **requisito** (REQ-F-012) + un **check** `rbac_enforced` (`kind:
product_env`) en s5 que corra el analizador `route_check.py rbac` (+ opcionalmente el test Kotlin del guard).
El RTM CRECE en 1 (default 16/16 → 17/17). Artifact de la capability: un path que exista para ambos productos
(p.ej. `build/product/src/main/kotlin/webapp/auth/` o el `RoleGuard.kt` si el nombre es fijo). **No agregues una
estación nueva** (más barato y honesto extender s5). **No hardcodees** roles en el sustrato — vive 100% en
`factories/full-stack-kotlin/codegen/` + el spec + `product.yml`.

### Seams concretos en `factories/full-stack-kotlin/codegen/scaffold_product.py`
- `_load_blueprint` — validación fail-closed de `roles`/`write_roles` (cerca del guard de workflows de FSK-S12).
- `_openapi_yaml` (el `post` de cada entidad) — emitir `x-required-roles` cuando la entidad tiene `write_roles`.
- `_auth_guard_kt` / **nuevo** `_role_guard_kt` — el enum `Role` + el guard de autorización por rol type-safe.
- `_routes_kt` — registrar cada escritura con sus roles requeridos; `dispatch` los cruza contra el guard.
- `_route_check_py` — modo `rbac` (parsea `x-required-roles` del contrato — sin PyYAML, mirá `_contract_ops` —
  y lo cruza contra los roles registrados en el Kotlin) + el probe sucio.
- `build_files` — cablear el guard nuevo + el probe + (si va) el test, OPT-IN (sólo cuando hay `roles`).
- Cuidado con el límite de 160 de detekt (usá `_kt_call`/`_jooq_chain`). El guard vive en `src/main/kotlin`
  (lo escanea detekt + `-Werror`): cero warnings, `MatchingDeclarationName` (archivo ⇄ declaración top-level).

## 4. Fases (plan; el orquestador las refina)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Gramática + validación + guard generado.** `roles`/`write_roles` en el blueprint; fail-closed en `_load_blueprint`; `x-required-roles` en el contrato; enum `Role` + `RoleGuard`/`AuthGuard` extendido; `route_check.py` modo `rbac` + probe. `--selftest`/`--check-idempotent` verdes; compile+detekt del demo verde. | ⏳ |
| 2 | **El demo ejercita RBAC + re-derive == pin.** Agregá `roles` + `write_roles` al demo; check `rbac_enforced` en s5; test de dos lados; línea s0–s10 verde · `ci --rederive` == re-pin · **RTM 16→17**. | ⏳ |
| 3 | **2º producto (assets) con roles DISTINTOS + co-validación (ADR-014).** La instancia `assets` declara roles propios (p.ej. `viewer` no escribe activos); `ci --rederive --product assets` == pin, aislada. | ⏳ |
| 4 | **Cierre.** STATE/ROADMAP/LOG + diff sustrato honesto (objetivo: `src/metafactory/`+`seed/` = **0**) + suite + RTM + `meta increment close`. | ⏳ |

## 5. Gate (prueba por bloqueo — dientes de dos lados, no decorativos)
- **RBAC enforced (dos lados):** un rol PERMITIDO escribe ✓ Y un rol NO-permitido es rechazado ✗ (en el test
  Kotlin y/o en `route_check.py rbac`). Romper el guard (autorizar todo) → el lado prohibido falla → rojo.
- **Diente negativo EMBEBIDO** (idiom s5, cada corrida): un probe sucio (escritura con roles equivocados, fuera
  de `src/`) DEBE morder por grep o el gate es decorativo → rojo (fail-closed).
- **Single-source (DES-6):** el contrato emite `x-required-roles`; el guard/analizador se deriva del MISMO
  blueprint y es type-safe sobre el enum `Role` → tamper del set de roles del contrato lo cruza el modo `rbac`
  → rojo (regen → verde). (Mismo enfoque honesto que FSK-S12: el tamper-tooth real es el cruce determinista, no
  una lista paralela decorativa.)
- **Fail-closed (validación):** `write_roles` sin `roles` · rol fuera de `roles` · forma inválida → `SystemExit`.
- **Opt-in no-regresivo:** una entidad SIN `write_roles` (o un producto sin `roles`) se comporta EXACTO como
  FSK-S5 (sólo autenticación); el demo actual y la instancia `assets` siguen verdes si no declaran RBAC.

## 6. Criterio de cierre (demostrable, no narrable)
1. `domain.product` expresa RBAC: `roles` + `write_roles`; validación fail-closed VIVA.
2. El guard de autorización por rol se GENERA y se EJERCITA por un test/analizador de **dos lados** (rol
   permitido ✓ / rol prohibido ✗) — corre en el toolchain del producto, romperlo → rojo.
3. **≥2 productos FSK con políticas de rol DISTINTAS** re-derivan `== su pin` en clon limpio, aislados (ADR-014).
4. **Anti-overfit:** `git diff src/metafactory/ + seed/` = **0** (RBAC es gramática de FÁBRICA). Suite verde ·
   RTM FSK crece (16→17) y cierra.

## 7. Notas de scope (qué NO es este incremento)
- **Autorización a nivel de FILA / ownership (ABAC)** ("un editor sólo edita SUS activos") es un eje posterior:
  necesita identidad de fila + el owner en runtime, no sólo el rol. Este es SÓLO RBAC por rol×entidad, estático.
- **Reglas de negocio arbitrarias por LLM** (patrón s6/MAT-2) es otro eje R2 siguiente (incremento aparte).
- El **server HTTP vivo (Ktor) + e2e (Playwright)** siguen `declared-deferred` (la verificación de RBAC es
  estática + unit, por diseño, como s5: prueba que ninguna escritura escape el control por construcción).
- Residual conocido (heredado de FSK-S11/S12): una instancia con la estación LLM s6 **activa con key** necesita
  persistir su `Summary.kt` pineado, pero `products/*/domain_gen/` está gitignored. No lo ejercita este eje.
