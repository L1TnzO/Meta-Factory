# Incremento FSK-FRONTEND-RENDER-LIST — el frontend RENDERIZA la lista VIVA (lista del server → cliente → UI)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-21T16:30Z · cerrado 2026-06-21T18:30Z, commit en §Evidencia). El deliverable está VIVO y
> probado por bloqueo (ver §Evidencia). Editar `factories/full-stack-kotlin/**` no-`.md` (codegen/spec/stations)
> exige un incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada (ADR-016).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Venís de
> **FSK-FRONTEND-CONSUME ✅** (2026-06-21, commit 0c981dd; ver `…/work/FSK-FRONTEND-CONSUME-INCREMENT.md
> §Evidencia`). El cliente TS generado ya **CONSUME** el backend vivo: `frontend/src/client.ts` gana
> `create<E>`/`get<E>` que hacen `fetch` REAL contra el `AppServer`, y un consumer node
> (`frontend/consume_check.ts`) prueba el round-trip `create→get` e2e bajo el check `frontend_consume_live`
> (s9, infra_up). PERO la UI **todavía no renderiza datos vivos**: `frontend/src/app.ts::render<E>List(rows)`
> es una **función pura** (rows → `<ul><li>…</li></ul>`) que el bundle de s8 mide pero que **nadie alimenta con
> filas del server**, y `GET /<plural>` del `AppServer` devuelve **sólo `{"count":N}`** (no las filas). Tu
> trabajo: que la UI **RENDERICE la LISTA VIVA** — el server LISTA las filas, el cliente las TRAE (`list<E>`), y
> `render<E>List` las renderiza; probado e2e (un render que dropea/garbla filas → rojo). Contenido de **FÁBRICA,
> GENERAL** (codegen + spec): cero nombres de dominio, `git diff` de cualquier `product.yml` = 0.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso; FSK genera, enforza acceso vivo, MUTA, lee el cuerpo real y el cliente
CONSUME):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, por-producto** (el sandbox de Bash mata gradle: exit 144).
Mantené el cwd de Bash en la RAÍZ del repo (un `cd` a subdir filtra el cwd y rompe el cierre de turno; usá
paths absolutos / subshells). Debe dar **PASS** (s0→s10). RTM 21/22 (único UNSAT = REQ-F-007/s6 LLM keyless).

**2) Leé los 4 lugares donde vive el hueco** (todo en `codegen/scaffold_product.py`):
1. **`_client_consume_ts`** (~L820, lo emitió FSK-FRONTEND-CONSUME): hoy emite `create<E>`/`get<E>`. Acá agregás
   `list<E>(base): Promise<<E>[]>` (GET `/<plural>` → las filas), tipado contra `components["schemas"][<E>]`
   (DES-6: drift → `tsc --strict` rojo en s2). `res.json()` es `unknown` (ts-reset) → narrow sin `any`.
2. **El dispatch del server** (`_APP_SERVER_SKELETON`, la línea `method == "GET" && collection -> … {"count":…}`,
   ~L3344) + **`_app_server_handlers`** (~L3088): hoy GET colección devuelve `{"count":N}`. Acá lo extendés a
   `{"count":N,"rows":[…]}` — **backward-compatible** (el `count` SIGUE → `access_control_check.py::_count`
   intacto). Cada fila = el JSON type-correct que **`_row_json_fn`/`<e>RowJson`** YA produce (~L929) — reusalo.
3. **`render<E>List`** (`_app_ts`, ~L2657): **YA EXISTE** (pura, `rows → <ul><li>${r.<field>}</li></ul>`, entry de
   bundle s8). NO la reescribas; ALIMENTALA con las filas vivas en el consumer. Renderiza el 1er campo
   string/enum de la 1ª entidad (derivado del blueprint, sin hardcode).
4. **`_consume_check_ts`/`_CONSUME_CHECK_SKELETON`** (~L3590, el consumer node): hoy hace `create→get`. Acá
   agregás el paso `list<E>()` (vivo) → `render<E>List(rows)` → **aseverá que el HTML refleja la lista viva**
   (cada fila sembrada + la creada por `create<E>` aparece; un render que dropea filas → rojo).

**3) EL DATO QUE LO CAMBIA TODO** (ya verificado en FSK-FRONTEND-CONSUME): **Node corre TS DIRECTO**
(`node --experimental-strip-types --disable-warning=ExperimentalWarning`, idiom de s7 y del consumer), **`fetch`
es global** (Node 18+ / `lib:["ES2022","DOM"]` ya en `tsconfig`, lo agregó FSK-FRONTEND-CONSUME para tipar
`fetch`/`Response`), y el consumer **no necesita `npm install`** (los `import type` se stripean; `client.ts` sólo
usa `fetch`). El consumer vive en `frontend/` (NO bajo `src/` → fuera del include de tsc y del glob de eslint →
no se type-checkea: es un runner como `access_control_check.py`). El tooth DES-6 vive en `client.ts` (en `src/`,
sí lo muerde `tsc --strict` + eslint strict + `no-explicit-any`).

---

## 1. Objetivo (qué deja TERMINADO este incremento)
La UI **RENDERIZA la LISTA VIVA** end-to-end: el `AppServer` **LISTA las filas** (`GET /<plural>` → `rows[]`,
no sólo `count`), el **cliente generado las TRAE** (`list<E>(): Promise<<E>[]>`, type-bound al contrato), y la
función de **render generada** (`render<E>List`) las renderiza a markup. El diente pasa de "el cliente trae UNA
fila (`get<E>`)" a "**la UI refleja la COLECCIÓN viva**": el server sembró+creó N filas → `list<E>` las trae →
`render<E>List` produce N `<li>` con sus campos → un render que dropea/garbla/hardcodea filas → el HTML ≠ la
lista viva → rojo. Cierra el eslabón "la UI renderiza datos vivos" (sin browser todavía). **El render EN
BROWSER (mount real, eventos), el FORM que postea, deploy (Dockerfile vivo) y e2e Playwright = slices
POSTERIORES** — este es la capa de RENDER de datos vivos, hermética (string assertion, sin browser/dep).

## 2. El hueco HOY (estado de partida, preciso)
- `AppServer` (`_APP_SERVER_SKELETON`): `GET /<plural>` (colección) → `{"count":${Repository.all<E>s(ctx).size}}`
  — devuelve el CONTEO, **nunca las filas**. `Repository.all<E>s(ctx)` (~L1025) ya SELECCIONA las filas (se usa
  para `.size`) → la data ya está, falta serializarla.
- `frontend/src/client.ts`: tiene `summarize` (pura), `create<E>`, `get<E>` (vivos, FSK-FRONTEND-CONSUME).
  **No tiene `list<E>`** → nadie trae la colección.
- `frontend/src/app.ts::render<E>List(rows)`: pura, renderiza `<ul>` — **el bundle de s8 la mide pero NADIE la
  llama con filas reales**. Es el único "render" y nunca ve datos vivos.
- `frontend/consume_check.ts`: hace `create→get` (round-trip de UNA fila). No lista ni renderiza.

## 3. Deliverable + el DIENTE e2e (de dos lados, no decorativo)
**(a)** Server: `GET /<plural>` (colección) → `{"count":N,"rows":[<rowJson>,…]}` — `rows` = cada fila vía
`<e>RowJson` (type-correct, ya existe). `count` SIGUE (backward-compat → `access_control_check.py` intacto).
Pasa detekt (≤160/línea, ≤2 returns/fun, sin wildcard) + `-Werror`. (Pensá: ¿un helper `all<E>RowsJson(ctx)` en
`Repository.kt` que mapea `all<E>s` → `joinToString` de `<e>RowJson`? Mantenelo type-bound al schema, DES-12.)
**(b)** Cliente: `list<E>(base): Promise<<E>[]>` en `client.ts` (GET `/<plural>` → `.rows`), tipado
`components["schemas"][<E>][]`; narrow desde `unknown` sin `any` (ts-reset/DES-10). OPT-IN: sólo la entidad con
dueño (igual que `create<E>`/`get<E>`).
**(c)** Consumer (extender `consume_check.ts`): tras el `create→get` actual, `const rows = await list<E>(base)`
→ `const html = render<E>List(rows)` → aseverá: (i) `rows.length` == N vivo (sembrado + el creado); (ii) el
`html` contiene el campo renderizado de CADA fila viva (incl. el `create<E>` recién posteado). **Un render que
dropea una fila / hardcodea / ignora la lista → el HTML ≠ la lista viva → exit 1.** Server caído → `fetch` tira →
exit 1 (nativo de infra_up).
**(d)** El check **`frontend_consume_live`** (s9, infra_up) YA corre el consumer → cubre esto sin estación nueva.
Sumá una **capability `frontend_render_live`** (DES-1/DES-6) + **REQ-F-018** citando ESE check (el validador
permite ≥1 req por check; sólo prohíbe ids duplicados / refs fantasma) — o, si preferís atribución limpia, un
4º check infra_up hermano (más superficie; el 3er-check bastó para CONSUME, probablemente acá también).

## 4. Decisiones de diseño (resolvelas GENERAL, DATA-agnóstico — la parte de fondo)
1. **¿`render<E>List` en el consumer o un entry nuevo?** RECOMENDACIÓN: importá `render<E>List` de `src/app.ts`
   en el consumer (`app.ts` ya exporta esa fn + re-exporta `summarize`). NO dupliques el render. El consumer
   corre por `node --experimental-strip-types` (importa `.ts` con extensión, `allowImportingTsExtensions`).
2. **¿String assertion o jsdom?** RECOMENDACIÓN: **string assertion** (el `html` contiene cada campo vivo) —
   HERMÉTICO, sin `npm install`, sin dep. El mount en jsdom (s8 ya tiene jsdom) o el browser real (Playwright) =
   slice POSTERIOR; no agregues `jsdom` al consumer (forzaría `npm install` en el bootstrap del check).
3. **El shape de `rows`.** `{"count":N,"rows":[…]}` (backward-compat) vs reemplazar por `[…]`. RECOMENDACIÓN: el
   objeto con `count`+`rows` (no rompe `access_control_check.py::_count`, que lee `.count`). `list<E>` lee `.rows`.
4. **El tooth de "N filas".** El server SIEMBRA 1 (el dueño + 1 fila) y el consumer CREA 1 → la lista viva tiene
   ≥2 (ojo: el seed inserta 1 fila de la entidad con dueño; verificá el conteo real leyendo `seedRows`/`_seed_chain`
   en el codegen). Aseverá contra el `count` vivo (no un número fijo) para no overfitear al seed.
5. **Type-binding del render (DES-6).** `render<E>List(rows: readonly <E>[])` ya tipa `<E>` del contrato; el
   `list<E>` devuelve `<E>[]` → un drift del contrato rompe `tsc --strict` en `client.ts` (s2). Mantené el render
   leyendo un campo que EXISTE en el contrato (ya lo hace: 1er string/enum de la 1ª entidad).

## 5. Maquinaria a REUTILIZAR (no la reinventes)
- **`_row_json_fn`/`<e>RowJson`** (~L929): serializa UNA fila type-correct (string/date/enum entrecomillados,
  int/number/boolean/ref crudos). Tu `rows[]` = map de esto. NO re-inventes la serialización.
- **`Repository.all<E>s(ctx)`** (~L1025): ya trae las filas (hoy se usa para `.size`).
- **`_client_consume_ts`** (el bloque `create<E>`/`get<E>` en `client.ts`): copiá el patrón `fetch`+`res.ok`+
  narrow-desde-`unknown` para `list<E>`.
- **`_CONSUME_CHECK_SKELETON`** (el consumer): extendelo (no lo reescribas). Su helper `check(actual, want, label)`
  compara por `JSON.stringify` (type-correct). El `ok`/exit-1 ya está cableado.
- **`render<E>List`** (`_app_ts`): ya existe, ya tipada al contrato. Importala, no la dupliques.
- **`node --experimental-strip-types`** (s7/consumer) · **`fetch` global** (DOM lib en `tsconfig`) — sin dep nueva.

## 6. Restricciones DURAS de FSK que SIGUEN vigentes (no las rompas)
Token estático `Bearer <rol>:<principal>`, dueño = principal (FK→User). El server es **opt-in** (sólo con
`owned_by`) → `list<E>`/`render` también: sin entidad con dueño no se emite (como `create<E>`/`get<E>`/AppServer).
`tsc --strict` + ESLint strict + `no-explicit-any` + ts-reset (`res.json()`→`unknown`) muerden `client.ts` (en
`src/`). detekt (≤160/línea, ≤2 returns/fun, sin wildcard) + `-Werror` muerden el Kotlin del server. El consumer
en `frontend/` NO se type-checkea (es un runner, como `access_control_check.py`).

## 7. Disciplina + dónde van los docs
- **Contenido de FÁBRICA GENERAL** (`codegen/scaffold_product.py` + `factory.spec.yml`): **cero nombres de
  dominio**, `git diff` de TODO `product.yml` = 0. El producto es DATA (ADR-012).
- **Anti-overfit real = el gate `generality` de `meta check`, NO `git diff src==0` literal.** Lo normal acá es NO
  tocar sustrato (`src/metafactory/`+`seed/`): todo cabe en codegen/spec. Si necesitás sustrato → incremento META
  aparte (`meta increment open <slug>`) + `generality` verde.
- **⚠️ LECCIÓN CARA (re-materializar el chasis):** el `proof_sha` de un gate es `hash(station_id +
  sorted(check_name, exit))` (`seed/verifier.py::compute_proof_sha`). Si agregás/quitás un CHECK (o estación),
  los productos **instancia** (`assets`/`snipeit`) re-materializan su línea del spec solos (`ensure_product_instance`
  → `_materialize_line`), pero el producto **DEFAULT usa el `stations/` COMMITEADO** y `product-run` NO lo
  re-materializa. Si SÓLO cambiás el CONTENIDO de un check existente (descripción, o el .py/.kt que el check corre,
  que s0 regenera) → NO hace falta. Si cambiás la ESTRUCTURA (nuevo check) → re-materializá el chasis a mano y
  re-pineá el default, o su `s9` queda en el sha viejo y el default no ejercita el tooth (aunque `ci --rederive`
  pase). Receta exacta (la usó FSK-FRONTEND-CONSUME): `PYTHONPATH=src python3 -c "from pathlib import Path; from
  metafactory.codegen.renderer import _materialize_line; from metafactory.engine import RunContext; from
  metafactory.cli import _subst_for, _meta_root; from metafactory.spec.loader import load_spec; f=Path('factories/
  full-stack-kotlin').resolve(); _materialize_line(RunContext(root=f, meta_root=_meta_root(), slug='full-stack-kotlin',
  chassis=f), {'action':'materialize_line','dest':'stations'}, _subst_for(load_spec(f/'factory.spec.yml'), f))"` →
  revisá `git diff stations/` (revertí churn cosmética de `s0.yml`: `git checkout -- …/stations/s0.yml`) → `product-run`
  default → `pin` default. Si NO sumás un check (extendés el consumer del check existente), **NO necesitás esto**.
- **RTM**: capability nueva `frontend_render_live` (DES-1/DES-6) + **REQ-F-018**, verified_by el check (el mismo
  `frontend_consume_live` o uno nuevo), artifact `…/frontend/src/app.ts` (o `client.ts`). Si extendés el check
  existente, recordá actualizar su descripción (`proof_checks` + `checks` en s9) para mencionar el render.
- **Docs**: estado/historia de la FÁBRICA → `factories/full-stack-kotlin/docs/{STATE.md,LOG.md}` (ADR-016); el
  meta STATE sólo se toca para marcar el hueco. El gobierno de ESTE incremento → este doc (flip a CERRADO +
  §Evidencia al cerrar). **Commit = parte del trabajo (ADR-010), nunca lo preguntes**; trailers I-10
  (`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`).
- **Probá POR BLOQUEO**: `product-run` PASS · `rtm`/`ci --rederive --all-products` == pin (los 3) · `meta check`
  6/6 (`generality` verde). **No fakees verde**: un render que devuelve un literal sin mirar las filas (o que
  ignora la lista) es el anti-patrón — por eso el HTML se asevera contra la lista VIVA traída de la PG.

## 8. Cómo correr la línea — comandos + lecciones caras (NO re-aprendas)
`meta = PYTHONPATH=src python3 -m metafactory.cli`. **`dangerouslyDisableSandbox: true`** en TODA corrida de
gradle/línea. FOREGROUND, por-producto (~3 min con gradle caliente).
1. `meta product-run --factory full-stack-kotlin --product snipeit` (re-materializa la instancia + s0→s10).
2. **El spec se comparte entre los 3 productos** → un cambio de codegen/spec obliga a re-correr+re-pinear los 3:
   `meta product-run …` (default · `--product assets` · `--product snipeit`) → `meta pin …` (idem) → `meta ci
   --rederive --factory full-stack-kotlin --all-products` (== pin, sin regresión). Cerrá con `meta checkpoint` si
   `projection` cae rojo en `meta check`.
3. `meta check` 6/6 (incluí `generality`).
- **Lecciones YA resueltas (no re-aprendas)**: (a) el server vivo se corre por `java -cp
  build/install/<pkg>/lib/*`, NUNCA `gradle run` (daemon forkea el JVM → leak de puerto); ya cableado en s9.
  (b) `proof_protect` DENIEGA tocar `.proof/` por shell (incluso leer) → usá `meta rtm`; el árbol generado
  (`products/<p>/build/product/...`) SÍ es legible. (c) **Eyeball sin gradle ANTES de cada corrida lenta**: generá
  los archivos a un temp y `node --experimental-strip-types --check` sobre `client.ts`/`consume_check.ts` (caza
  errores de strip-types en segundos) + `--check-idempotent`. (d) Para EYEBALLEAR el diente vivo sin la línea
  entera: el check `frontend_consume_live` usa puerto/PG propios (`FSK_AC_PORT=18595`/`FSK_PG_URL`…5437,
  contenedor `fsk_s9_fe_pg`) ≠ `access_control_live` (18594/5436) ≠ `observability_live` (18593) — no colisionan.
  (e) **Diente de DOS lados VIVO** (criterio de cierre): saboteá `render<E>List` (que devuelva un literal / dropee
  filas), corré, confirmá ROJO **sólo** en el check del render (los hermanos s9 verdes), revertí → verde.

## 9. Criterio de cierre (demostrable, no narrable)
1. `product-run --product snipeit` PASS · el render de la lista viva verde: `list<E>` trae las filas del server,
   `render<E>List` produce el HTML, y el consumer asevera que refleja la lista VIVA (N filas, cada campo) **+**
   server caído → rojo (nativo infra_up).
2. **Diente de DOS lados verificado VIVO**: saboteá el render (literal / dropear filas), corré, confirmá ROJO en
   s9 (sólo el check del render), revertí → verde.
3. `ci --rederive --all-products` == pin (default + assets + snipeit). `meta check` 6/6 (`generality` verde).
   **`git diff` de todo `product.yml` = 0**. Idealmente `git diff src/metafactory/ + seed/` = 0 (cabe en codegen+spec).
   **Si sumaste un check: re-materializá el chasis + re-pineá el default** (§7 lección cara) — verificá que los 3
   pines comparten el `s9` (o el gate tocado).
4. El scope honesto se actualiza: STATE/LOG (fábrica) registran "frontend renderiza la lista viva ✅" y los huecos
   que QUEDAN (render EN BROWSER (mount/eventos) · el FORM que postea via el cliente · deploy real (Dockerfile
   vivo) · e2e Playwright (browser headless) · CRUD de entidades sin dueño · refs del body · custom-fields) como
   próximos incrementos.

## 10. Contexto que ya está hecho (de dónde venís)
- **FSK-FRONTEND-CONSUME ✅ (2026-06-21, commit 0c981dd)**: el cliente TS generado CONSUME el backend vivo —
  `client.ts` gana `create<E>`/`get<E>` (`fetch` real, type-bound al contrato vía `Pick<…>`); un consumer node
  (`consume_check.ts`) prueba el round-trip `create→get` e2e por `node --experimental-strip-types`, verificado por
  el check `frontend_consume_live` (s9, infra_up, puerto/PG propios). Capability `frontend_consume_live` +
  REQ-F-017. `tsconfig` ganó `lib:["ES2022","DOM"]` para tipar `fetch`/`Response`. Detalle: `…/work/
  FSK-FRONTEND-CONSUME-INCREMENT.md §Evidencia` + `…/docs/LOG.md` (2026-06-21T16:14Z).
- **El backend FSK está VIVO + CRUD-completo + entrada tipada, y el cliente lo CONSUME** (auth → RBAC → ownership
  → mutación → cuerpo tipado → cliente que hace `fetch`, todo e2e vs PG viva). Este incremento es el SIGUIENTE
  eslabón del frontend real: que la **UI RENDERICE** los datos que el cliente trae — antes del render EN BROWSER,
  el form que postea, deploy y e2e Playwright.

---

## Evidencia (cierre 2026-06-21T18:30Z) — demostrable, no narrable

**Hecho** (todo en `codegen/scaffold_product.py` + `factory.spec.yml`, FÁBRICA/GENERAL, cero nombres de dominio):
1. **Server** — `_app_server_handlers` gana `listAll(ctx): Pair<Int,String>` → `GET /<plural>` colección pasa de
   `{"count":N}` a `{"count":N,"rows":[…]}` (count primero, **backward-compat**); el dispatch del skeleton llama
   `listAll(ctx)`. Cada fila la serializa **`Repository.all<E>RowsJson`** (nuevo en `_mutation_fns`): mapea
   `all<E>s(ctx) → <e>RowJson(ctx, it[<TBL>.ID]!!)` — **REUSA** la serialización type-correct (DES-12). El `!!`
   porque `it[<TBL>.ID]` es `Long?` (jOOQ) y `<e>RowJson` toma `Long` (consistente con `fetchOne()!!`/`get(...)!!`).
2. **Cliente** — `_client_consume_ts` gana `list<E>(base): Promise<<E>[]>` (GET → `.rows`) + helper `expectRows`
   que narrow `res.json()` de `unknown` a `unknown[]` (ts-reset/DES-10, sin `any`); el callsite castea a `<E>[]`.
3. **Render** — `_app_ts` ahora elige la entidad **CON DUEÑO** (`next((x for x… if x.owned_by), entities[0])`) →
   `render<E>List` apunta a la entidad con capa viva (consistente con `list<E>`/`create<E>`/`get<E>`); sin dueño
   cae en `entities[0]` y s8 sigue midiendo el bundle. (En los 3 productos `owned != entities[0]`: Project/Asset/Asset.)
4. **Consumer** — `_CONSUME_CHECK_SKELETON` importa `list<E>` (de `client.ts`) + `render<E>List` (de `app.ts`) y,
   tras `create→get`, hace `list<E>(base) → render<E>List(rows)` y asevera: (i) la fila creada está en la lista
   traída; (ii) el HTML contiene el campo renderizado de CADA fila viva; (iii) ≥2 filas. `%RENDER_FIELD%` = el 1er
   string/enum de la entidad con dueño (MISMA heurística que `_app_ts`).
5. **Spec** — capability `frontend_render_live` (DES-6) + **REQ-F-018** (`verified_by: [frontend_consume_live]`,
   `capability: frontend_render_live`); descripción del check y notas de deferral actualizadas. `validate` +
   `design-review` = **0 problemas**.

**Probado POR BLOQUEO**:
- `product-run` **PASS** en los 3 (default · assets · snipeit), s0→s10.
- **RTM snipeit 22/23** SATISFIED — `REQ-F-018 SATISFIED <- frontend_render_live: s9 [app.ts✓]` (único UNSAT
  sigue `REQ-F-007`/s6 LLM keyless). s9: `observability_live`+`access_control_live`+`frontend_consume_live` = exit 0.
- **Diente de DOS lados VIVO**: saboteado `render<E>List` (`rows.filter(() => false).map(…)` → dropea filas) →
  `product-run --product snipeit` **FAIL** con `1/3 checks red` = **sólo `frontend_consume_live` FAIL(1)**,
  `observability_live ok · access_control_live ok`; revertido → verde.
- `ci --rederive --all-products` **3/3 == pin** (11/11 · 10/10 · 10/10). `meta check` **6/6** (`generality` verde;
  `projection` re-sincronizada con `meta checkpoint`).
- **Anti-overfit**: `git diff src/metafactory/ + seed/ = 0` (sustrato intacto) · `git diff product.yml = 0` (los 3).
  **Sin check nuevo** → `proof_sha` intacto → los 3 `pinned_verdict.json` quedaron **byte-idénticos** (no hizo
  falta re-materializar el chasis: la lección cara de FSK-FRONTEND-CONSUME NO aplicó este eje).

**Commit**: `feat(fsk): FSK-FRONTEND-RENDER-LIST` (trailers I-10).

**Siguiente** (decidido y abierto sin intervención, ADR-016): **`FSK-CRUD-OWNERLESS`** — levantar el opt-in a
entidades **sin dueño** (lo de mayor palanca para un Snipe-IT usable: hoy la capa viva cubre 1 de ~23 entidades) +
preparar refs del body. Handoff autocontenido: `docs/work/FSK-CRUD-OWNERLESS-INCREMENT.md`.
