# Bitácora — Full-Stack Kotlin/TS/PG Factory
> tipo: log · append-only, MÁS NUEVO ARRIBA · inmutable una vez escrito (esquema ADR-021).

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
