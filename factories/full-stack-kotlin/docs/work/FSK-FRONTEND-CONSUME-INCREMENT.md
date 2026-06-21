# Incremento FSK-FRONTEND-CONSUME — el cliente TS generado CONSUME el backend vivo (fetch e2e real)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-21T14:58Z · cerrado 2026-06-21T16:29Z; evidencia al pie). Cerralo con `meta increment close --factory full-stack-kotlin` (gateado: árbol
> limpio + estación activa verde) **o** flippeando este header a CERRADO (lo mismo: el `increment status` lee el
> header). Editar `factories/full-stack-kotlin/**` no-`.md` (codegen/spec/stations) exige ESTE incremento
> abierto — el `increment_guard` elige el lifecycle por la RUTA editada (ADR-016).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Venís de
> **FSK-CRUD-BODY-PARSING ✅** (el server vivo lee el JSON del request y lo persiste type-coerced; ver
> `…/work/FSK-CRUD-BODY-PARSING-INCREMENT.md §Evidencia`). El **backend ya está VIVO y CRUD-completo con input
> real**. PERO el frontend NO lo consume: `frontend/src/client.ts` es una **función pura** (`summarize`) que
> nunca hace una request, e `index.html` es un **form estático**. Tu trabajo: que el **cliente TS generado haga
> `fetch` REAL contra el `AppServer` vivo** y pruebe el **round-trip e2e** (crear una fila → leerla de vuelta →
> aseverar) a través del código de cliente REAL. Es contenido de **FÁBRICA, GENERAL** (codegen + spec + un
> 3er check en `stations/s9.yml`): cero nombres de dominio, `git diff` de cualquier `product.yml` = 0.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso; FSK genera, enforza acceso vivo, MUTA y lee el cuerpo real):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, por-producto** (el sandbox de Bash mata gradle: exit 144).
Mantené el cwd de Bash en la RAÍZ del repo (un `cd` a subdir filtra el cwd y rompe el cierre de turno; usá
paths absolutos / subshells). Debe dar **PASS** (s0→s10). RTM 20/21 (único UNSAT = REQ-F-007/s6 LLM keyless).

**2) Leé los lugares donde vive el hueco** (todo en `codegen/scaffold_product.py`):
1. `_client_ts` (~L781): emite `frontend/src/client.ts`. HOY exporta SÓLO `summarize(...)`, una **función pura**
   tipada de `gen/api.ts` (sin red). Acá agregás las funciones de **fetch real** (`create<E>`/`get<E>`) contra el
   server vivo, tipadas contra `components["schemas"]` (DES-6: un drift del contrato rompe `tsc --strict` en s2).
2. `_app_ts` (~L2588) + `_ui_index_html` (~L2520): el entry de bundle y la UI estática. NO los toques en este
   slice (la UI que renderiza + React + Playwright = slice posterior); este incremento es la **capa cliente que
   consume**, no el render en browser.
3. `_app_server_kt` / `_APP_SERVER_SKELETON` (~L3128/L3215): el server vivo que el cliente va a llamar. NO lo
   cambies (ya expone `/seed`, GET/POST/PUT/DELETE `/<plural>/{id}`, GET `/<plural>` count). Sólo lo CONSUMÍS.
4. `stations/s9.yml` (instancia materializada) ⟵ se deriva de `factory.spec.yml` s9 `checks`/`proof_checks`
   (~L686/L699). Acá agregás un **3er check `frontend_consume_live`** (kind `infra_up`), hermano de
   `access_control_live`: mismo bootstrap (installDist + PG + `npm install` en `frontend/`), up = AppServer,
   proof = el consumer node. **NO edites el `stations/s9.yml` de la instancia a mano** (se re-materializa cada
   corrida); editás el `factory.spec.yml` de la FÁBRICA.

**3) EL DATO QUE LO CAMBIA TODO** (ya verificado): **Node corre TypeScript DIRECTO**, sin paso de compilación.
La línea s7 ya usa `node --experimental-strip-types --disable-warning=ExperimentalWarning --test test/client.test.ts`
(spec L610). El frontend es `"type": "module"`, `tsconfig` con `noEmit:true` + `allowImportingTsExtensions:true`
(los imports llevan extensión `.ts`, p.ej. `import type { components } from "../gen/api.ts"`). → El consumer
puede ser un `.ts` que **importa el cliente generado** y se corre con `node --experimental-strip-types`. Y
**`fetch` es global en Node 18+** (stdlib, sin dep, hermético — no toca `package.json`, no viola ADR-012).

---

## 1. Objetivo (qué deja TERMINADO este incremento)
El **cliente TS generado CONSUME el backend vivo**: hace `fetch` REAL contra el `AppServer` (PG viva detrás) y
prueba el **round-trip e2e a través del código de cliente REAL** — `create<E>(body)` POSTea, `get<E>(id)` GETea,
y lo que vuelve == lo que se envió (type-correct). El diente deja de ser "el server responde bien a un proof
python" y pasa a ser "**el cliente generado y el server generado hablan el MISMO protocolo de cable, e2e**":
contrato → client.fetch → server vivo → PG → respuesta → client.parse. Cierra el hueco "el frontend es funciones
puras que nunca llaman al server". (React que renderiza + deploy + e2e Playwright = slices POSTERIORES.)

## 2. El hueco HOY (estado de partida, preciso)
- `frontend/src/client.ts` exporta `summarize(task): string` — una **función pura** (interpola campos), tipada
  de `gen/api.ts`. **Nunca hace una request.** Es el ÚNICO código de cliente "de dominio".
- `frontend/src/app.ts` exporta `render<E>List(rows)` — string de `<ul>`, también puro (entry de bundle s8).
- `frontend/ui/index.html` — `<form>` estático WCAG (s8 axe), sin JS que postee.
- `tools/access_control_check.py` (s9) prueba el server con **urllib desde python** — NO es el cliente del
  producto. Nada en `frontend/` toca el server vivo. Scope honesto declarado en FSK-S15/S16 (frontend que
  consume = declared-deferred).

## 3. Deliverable + el DIENTE e2e (de dos lados, no decorativo)
**(a)** Funciones de cliente VIVAS en `client.ts` (DES-6, type-safe contra `components["schemas"]`):
`create<E>(base, token, body): Promise<{id:number}>` (POST `/<plural>`) y `get<E>(base, id): Promise<<E>>` (GET
`/<plural>/{id}`), usando `fetch` global. La entidad target = la que tiene `owned_by` (la única que el AppServer
monta). El body type = el `<E>Input` shape (campos escalares requeridos no-dueño; ver `_input_fields` en el
codegen — ya existe de FSK-CRUD-BODY-PARSING).
**(b)** Un consumer node `frontend/consume_check.ts` que IMPORTA esas funciones y, contra el server vivo:
1. GET `/seed` → `{id, owner}` (el principal dueño sembrado; mismo idiom que `access_control_check.py`).
2. `create<E>(base, "Bearer <write_role>:<owner>", {valores DISTINTOS de los samples})` → `{id}` (201).
3. `get<E>(base, id)` → la fila; aseverá que **cada campo posteado vuelve EXACTO y type-correct** (un int es int).
   **Un cliente que ignora la respuesta (o hardcodea) → mismatch → exit 1** (el diente real).
4. (negativo, opcional pero recomendado) `create<E>` con un body de tipo equivocado → el server responde 400 →
   el cliente DEBE propagar el error (no tragarlo): un cliente que no chequea `res.ok` lo delata.
5. **Server caído → `fetch` tira → exit 1** (diente nativo de infra_up).
**(c)** Un 3er check `frontend_consume_live` (kind `infra_up`) en s9 que levanta PG + AppServer + corre el
consumer. Mismo shape EXACTO que `access_control_live` (spec L699): bootstrap installDist + `docker run` PG +
`npm install` en `frontend/`; up = AppServer por `java -cp`; proof = `sh -c "cd frontend && node
--experimental-strip-types --disable-warning=ExperimentalWarning consume_check.ts http://127.0.0.1:<port>"`;
down = `docker rm -f`. **Usá un puerto/contenedor PG DISTINTOS** de access_control_live (`fsk_s9_ac_pg`/18594/5436)
para no colisionar si corren en paralelo — p.ej. `fsk_s9_fe_pg`/otro puerto AppServer/otro puerto PG.

## 4. Decisiones de diseño (resolvelas GENERAL, DATA-agnóstico — la parte de fondo)
1. **Cómo corre el consumer (el corazón).** RECOMENDACIÓN: `node --experimental-strip-types` sobre un `.ts` que
   importa `src/client.ts` (§★3 — ya es el idiom de s7). NO compiles a JS (el frontend es `noEmit`), NO agregues
   `tsx`/loaders (dep innecesaria). El consumer importa con extensión `.ts` (`allowImportingTsExtensions`).
   Fallback si la versión de Node pineada no soporta strip-types: bundlear el consumer con esbuild (ya es dep) a
   un `.mjs` temporal y correr ese — pero probá strip-types PRIMERO (es lo que s7 ya hace verde).
2. **Tipos del body POST.** El AppServer espera el `<E>Input` (escalares requeridos no-dueño; el dueño va por el
   token). El cliente debe enviar EXACTO esas claves con el tipo correcto. RECOMENDACIÓN: derivá el body type del
   blueprint (reusá `_input_fields(owned)` del codegen) y, en el consumer, mandá valores DISTINTOS de los samples
   (mismo criterio que `_proof_post_value` de FSK-CRUD-BODY-PARSING — podés factorizar/espejar esa lógica). Un
   `string`→`"fe-<campo>"`, `int`→9, etc. UNIQUE → sufijo único para no chocar con el seed.
3. **El token.** El AppServer usa `Bearer <rol>:<principal>` estático (JWT real diferido). El cliente lo arma con
   un `write_role` (DATA del blueprint, como `access_control_check.py` elige `owner_role`) + el `owner` de `/seed`.
   Mantené el dueño = principal sembrado (satisface el FK→User). NO inventes identidad nueva (otro eje).
4. **`res.ok` y errores.** El cliente DEBE chequear `res.ok`/status y tirar si no (un cliente que traga el 4xx y
   devuelve basura es el anti-patrón que el diente §3.4 caza). Esto también lo type-bound: `res.json()` con
   ts-reset devuelve `unknown` → el cliente DEBE narrow al tipo del contrato (DES-6/DES-10, ya en el toolchain).
5. **¿3er check en s9 vs estación nueva?** RECOMENDACIÓN: **3er check en s9** (`frontend_consume_live`), hermano
   de `access_control_live` — reusa el patrón live-AppServer+PG, sin renumerar la línea ni tocar el DAG de s10
   (`depends_on: [s2,s3,s4,s7,s8,s9]`). Estación nueva = más superficie, innecesaria para un check infra_up más.
6. **¿Slice?** Si entra apretado: (a) `create<E>` + `get<E>` + el round-trip e2e (el diente central) PRIMERO;
   (b) el negativo del 400 después. Mejor un slice verde-de-verdad que dos a medias.

## 5. Maquinaria a REUTILIZAR (no la reinventes)
- **`access_control_live`** (s9, `factory.spec.yml` L699): el TEMPLATE exacto del check infra_up (bootstrap PG +
  installDist, up AppServer por `java -cp`, proof client, down docker rm). Copialo y cambiá proof + puertos +
  nombre de contenedor.
- **`tools/access_control_check.py`** (`_access_control_check_py` ~L3318): el idiom de leer `/seed`, elegir
  `write_role`/`forbidden` del blueprint, y los valores POST distintos de los samples (`_proof_post_value`,
  `_input_fields`). Tu consumer node hace lo MISMO pero en TS via el cliente generado.
- **`_input_fields(owned)`** (~L870 tras FSK-CRUD-BODY-PARSING): los campos escalares requeridos no-dueño = el
  shape del body. **`_client_ts`** ya importa `gen/api.ts` y mapea `components["schemas"]` → reusá ese tipado.
- **`node --experimental-strip-types --disable-warning=ExperimentalWarning`** (s7, spec L610): el runner TS exacto.
- **`fetch` global** (Node 18+): sin dep, sin import.

## 6. Restricciones DURAS de FSK que SIGUEN vigentes (no las rompas)
Las del blueprint (`…/products/snipeit/docs/reference/SNIPEIT-DOMAIN.md`): dueño = principal (FK→User), token
estático `Bearer <rol>:<principal>`, type-coercion fail-closed (el server ya da 400 — el cliente lo propaga).
El server es **opt-in** (sólo con `owned_by`) → el check `frontend_consume_live` también: sin entidad con dueño,
no se emite (igual que AppServer). `tsc --strict` + ESLint strict + `no-explicit-any` siguen mordiendo (DES-6/10).

## 7. Disciplina + dónde van los docs
- **Contenido de FÁBRICA GENERAL** (`codegen/scaffold_product.py` + `factory.spec.yml` + el check en s9):
  **cero nombres de dominio**, `git diff` de TODO `product.yml` = 0. El producto es DATA (ADR-012).
- **Anti-overfit real = el gate `generality` de `meta check`, NO `git diff src==0` literal.** Lo normal acá es
  NO tocar sustrato (`src/metafactory/`+`seed/`): todo cabe en codegen/spec. Si necesitás sustrato → incremento
  META aparte (`meta increment open <slug>`) + `generality` verde.
- **RTM**: capability nueva `frontend_consume_live` (DES-6/DES-4) + **REQ-F-017**, verified_by el check nuevo,
  artifact `…/frontend/src/client.ts` (o `consume_check.ts`) — exactamente como FSK-CRUD-BODY-PARSING sumó
  `entrada_tipada_runtime`+REQ-F-016 (el validador permite 2 reqs por check; sólo prohíbe ids duplicados / refs
  fantasma). Actualizá la descripción de s9 (`proof_checks` + `checks`) para incluir el 3er check.
- **Docs**: estado/historia de la FÁBRICA → `factories/full-stack-kotlin/docs/{STATE.md,LOG.md}` (ADR-016); el
  meta STATE sólo se toca para marcar el hueco como ✅. El gobierno de ESTE incremento → este doc (flip a CERRADO
  + §Evidencia al cerrar). **Commit = parte del trabajo (ADR-010), nunca lo preguntes**; trailers I-10
  (`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`).
- **Probá POR BLOQUEO**: `product-run` PASS · `rtm`/`ci --rederive` == pin · `meta check` 6/6. **No fakees
  verde**: un cliente que devuelve el body que envió sin ir al server (eco local) es el anti-patrón — por eso el
  round-trip va contra el server VIVO y la fila vuelve de la PG, no de memoria.

## 8. Cómo correr la línea — comandos + lecciones caras (NO re-aprendas)
`meta = PYTHONPATH=src python3 -m metafactory.cli`. **`dangerouslyDisableSandbox: true`** en TODA corrida de
gradle/línea. FOREGROUND, por-producto (~3 min con gradle caliente).
1. `meta product-run --factory full-stack-kotlin --product snipeit` (re-materializa la instancia + s0→s10).
2. `meta rtm --factory full-stack-kotlin --product snipeit` (deferral s6 visible OK) → `meta pin …`. **El spec se
   comparte entre los 3 productos** → un cambio de codegen/spec obliga a re-pinear los 3: `meta pin --factory
   full-stack-kotlin` (default), `--product assets`, `--product snipeit`; después `meta ci --rederive --factory
   full-stack-kotlin --all-products` (== pin, sin regresión). Cerrá con `meta checkpoint` si `projection` cae rojo.
3. `meta check` 6/6 (incluí `generality`).
- **Lecciones YA resueltas (no re-aprendas)**: (a) el server vivo largo se corre por `java -cp
  build/install/<pkg>/lib/*`, NUNCA `gradle run` (daemon forkea el JVM → leak de puerto); ya cableado en s9.
  (b) `proof_protect` DENIEGA tocar `.proof/` por shell (incluso leer) → usá `meta rtm`. El árbol generado
  (`products/<p>/build/product/...`) SÍ es legible. (c) **Eyeball sin gradle ANTES de cada corrida lenta**:
  `python3 -c "import sys; sys.path.insert(0,'factories/full-stack-kotlin/codegen'); import scaffold_product as S;
  ...; print(S.build_files(bp)['frontend/src/client.ts'])"` + `--check-idempotent` (caza syntax/imports en
  segundos). (d) ESLint strict `no-explicit-any` + `tsc --strict` (s2) muerden el cliente — narrow `unknown` del
  `res.json()`, no `any`. (e) Para EYEBALLEAR el diente vivo sin la línea entera: levantá PG + AppServer a mano
  como hace el §Evidencia de FSK-CRUD-BODY-PARSING (docker run PG + `java -cp ... AppServerKt` + corré el
  consumer), y verificá que un sabotaje del cliente da exit 1.

## 9. Criterio de cierre (demostrable, no narrable)
1. `product-run --product snipeit` PASS · el check `frontend_consume_live` (s9) verde: el cliente TS generado
   `create<E>` + `get<E>` contra el server vivo, y el round-trip aseverá cada campo posteado type-correct **+**
   (recomendado) el negativo 400 propagado **+** server caído → rojo (nativo infra_up).
2. **Diente de DOS lados verificado VIVO**: saboteá el cliente (que `get<E>` devuelva un literal / ignore la
   respuesta del server), corré, confirmá ROJO en s9, revertí → verde. (Idem si el cliente no chequea `res.ok`.)
3. `ci --rederive --all-products` == pin (default + assets + snipeit). `meta check` 6/6 (`generality` verde).
   **`git diff` de todo `product.yml` = 0**. Idealmente `git diff src/metafactory/ + seed/` = 0 (cabe en codegen+spec).
4. El scope honesto se actualiza: STATE/LOG (fábrica) registran "frontend consume e2e ✅" y los huecos que QUEDAN
   (React que renderiza la lista + el form que postea · deploy real (Dockerfile vivo) · e2e Playwright (browser) ·
   CRUD de entidades sin dueño · refs del body · custom-fields) como próximos incrementos.

## 10. Contexto que ya está hecho (de dónde venís)
- **FSK-CRUD-BODY-PARSING ✅ (2026-06-21)**: el server vivo lee el JSON real del request y lo persiste
  type-coerced por el schema (POST inserta los valores del body, GET /{id} fila completa type-correct, PUT del
  body, body malo → 400). RTM snipeit 20/21, REQ-F-016 `entrada_tipada_runtime`. Detalle: `…/work/
  FSK-CRUD-BODY-PARSING-INCREMENT.md §Evidencia` + `…/docs/LOG.md` (2026-06-21T14:52Z).
- **El backend FSK está VIVO y CRUD-completo con input real** (auth → RBAC → ownership → mutación → cuerpo
  tipado, todo enforzado a runtime vs PG viva). Este incremento es el SIGUIENTE escalón: que la **cara cliente**
  lo CONSUMA — el primer eslabón del frontend real, antes de React que renderiza + deploy + e2e Playwright.

---

## Evidencia (cierre 2026-06-21T16:14Z) — demostrable, no narrable
**Deliverable entregado** (todo en `codegen/scaffold_product.py` + `factory.spec.yml`; `git diff src/metafactory/ +
seed/` = **0**, `git diff product.yml` = **0**):
- **(a)** `client.ts` gana `create<E>(base, token, body): Promise<{id:number}>` (POST `/<plural>`) y
  `get<E>(base, id): Promise<<E>>` (GET `/<plural>/{id}`) con `fetch` global, **type-bound al contrato**: el body es
  `Pick<components["schemas"][<E>], …>` de `_input_fields` (un drift del contrato → el Pick no compila en `tsc
  --strict`, s2, DES-6); `res.json()` se narrow desde `unknown` (ts-reset) sin `any` (DES-10). OPT-IN: sólo la
  entidad con dueño (sin `owned_by`, `client.ts` queda con `summarize`, FSK-S15 intacto). `tsconfig` ganó
  `lib:["ES2022","DOM"]` para tipar `fetch`/`Response` (GENERAL, un frontend legítimamente incluye DOM).
- **(b)** `frontend/consume_check.ts` IMPORTA esas funciones y, contra el server vivo: GET `/seed` → `{id,owner}`;
  `create<E>(Bearer <write_role>:<owner>, {valores ≠ samples})`; `get<E>(id)` → asevera **cada campo posteado
  type-correct**; + negativo (body de tipo equivocado → 400 → el cliente propaga). Corre por `node
  --experimental-strip-types` (sin `npm install`: los imports de tipo se stripean). NO type-checked (vive en
  `frontend/`, fuera del include de tsc — como `access_control_check.py`).
- **(c)** **3er check `frontend_consume_live`** (kind `infra_up`) en s9, hermano de `access_control_live`: mismo
  AppServer con puerto/PG PROPIOS por env (`FSK_AC_PORT=18595` / `FSK_PG_URL`…5437, contenedor `fsk_s9_fe_pg`).
  Capability `frontend_consume_live` (DES-6) + **REQ-F-017**.

**Verificado POR BLOQUEO**:
- `product-run` **PASS** en los 3 (demo · assets · snipeit) · RTM snipeit **21/22** (REQ-F-017 `frontend_consume_live`
  SATISFIED <- s9 `[…/frontend/src/client.ts✓]`; único UNSAT = REQ-F-007/s6 LLM keyless, deferral VISIBLE).
- `ci --rederive --all-products` **3/3 == pin** (11/11 · 10/10 · 10/10) en clones limpios · `meta check` **6/6**
  (`generality` verde).
- **Diente de DOS lados VIVO y PRECISO**: saboteado `get<E>` (ignora la respuesta del server, devuelve `{}`) →
  `product-run snipeit` **FAIL**, **sólo `frontend_consume_live` rojo** con `observability_live` +
  `access_control_live` VERDES (el server estaba sano; falló el CONSUMO); revertido → **PASS**.
- Eyeball pre-gradle: `--check-idempotent` verde · `node --experimental-strip-types --check` sobre el `client.ts` y
  `consume_check.ts` generados (Node v22.22) → SYNTAX OK.

**Lección reusable (estructura de estación) — para el próximo que agregue/quite un check**: el `proof_sha` de un
gate es `hash(station_id + sorted(check_name, exit))` (`seed/verifier.py::compute_proof_sha`). Agregar un check
CAMBIA ese sha → los **productos INSTANCIA** (`assets`/`snipeit`) re-materializan su línea del spec en cada corrida
(`ensure_product_instance` → `_materialize_line`), así que toman el check nuevo solos; pero el **producto DEFAULT
usa el `stations/` COMMITEADO de la fábrica**, que NO se re-materializa en `product-run`. Hay que re-materializar el
chasis a mano (mismo `_materialize_line`, dest `stations`) para que el default también corra el check nuevo — si no,
su `s9` queda en el sha viejo (2 checks) y `ci --rederive` pasa pero el default NO ejercita el tooth. Acá se
re-materializó `stations/s9.yml` (sólo el check nuevo; la churn cosmética de `s0.yml` se revirtió) y se re-pineó el
default → s9 == el de las instancias (3 checks). Verificado: los 3 pines comparten `s9` y `ci --rederive` 3/3 == pin.

**Scope honesto — lo que QUEDA** (próximos incrementos): React que RENDERIZA la lista + el form que postea (browser)
· deploy real (Dockerfile vivo) · e2e Playwright (browser headless) · CRUD de entidades sin dueño · refs del body ·
custom-fields. El cliente ya CONSUME; falta el RENDER en browser y el ship.
