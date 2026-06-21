# Incremento FSK-BROWSER-FORM — la UI se MONTA en un DOM real (jsdom) y un FORM postea vía el cliente vivo

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO**
> (creado 2026-06-21T20:54Z). Cerralo flippeando este header a CERRADO (el `increment status` lee el header) **o**
> con `meta increment close --factory full-stack-kotlin`. Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA
> editada (ADR-016).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-REFS-IN-BODY con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (la decisión estratégica — leéla, no la saltees)

Tras FSK-REFS-IN-BODY **la capa de DATOS de Snipe-IT está COMPLETA**: el grafo relacional entero es CRUD-able por
API (entidad con dueño · 1ª ownerless · 1ª con-ref; backend vivo+typed-body+RBAC+ownership+FK fail-closed). Pero la
**capa de UI sigue siendo media-verdad**: el cliente TS `fetch`ea de verdad (`create<E>`/`get<E>`/`list<E>`,
FSK-FRONTEND-CONSUME) y el render produce **markup como STRING** (`render<E>List`, FSK-FRONTEND-RENDER-LIST), pero
**nada monta ese markup en un DOM real, ni hay un FORM que el usuario llene para crear una fila**. El proof corre en
`node` (sin DOM): asevera que el STRING contiene las filas, no que un DOM se actualizó por un evento.

**Qué deja TERMINADO**: el frontend generado **se MONTA en un DOM real** (nodos, no string) y un **FORM** generado
(un input por campo del cuerpo) cuyo submit **postea vía el cliente vivo** (`create<E>` → server vivo → PG) y
**re-renderiza la lista** → la fila recién creada aparece como **nodo del DOM**. Es el salto de "el backend es
usable por API" a "la app es usable por un humano que llena un formulario". El paso de mayor palanca hacia
"Snipe-IT usable" (después queda deploy, y luego ya es product-specific).

**★ EL INSIGHT QUE LO HACE FACTIBLE (no lo pierdas):** **jsdom YA es dependencia de la fábrica** (s8 `a11y_gate`
corre axe-core "HEADLESS en jsdom (sin browser)", ver `factory.spec.yml` y `_a11y_audit_mjs`). jsdom da un
**`document` real + eventos** (`createElement`, `addEventListener`, `form.dispatchEvent(new Event("submit"))`) **sin
binario de browser ni red**. Eso permite "mount real del DOM + submit del form + fetch contra el server vivo"
**hermético**. **Playwright (motor de browser real, necesita red para el binario) SIGUE DIFERIDO** — el diente acá
es el DOM real + el evento + el round-trip, no el render de un Chromium.

**Hermano YA cerrado (de dónde venís):** FSK-REFS-IN-BODY levantó el ref requerido del cuerpo (el espinazo
relacional). Detalle: `docs/work/FSK-REFS-IN-BODY-INCREMENT.md §Evidencia` + `docs/LOG.md` (2026-06-21T20:50Z).

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso: backend vivo + cliente que consume + render-string de la lista):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez** (el sandbox de Bash mata gradle: exit
144). **Mantené el cwd de Bash en la RAÍZ del repo** — un `cd` a un subdir filtra el cwd persistente y rompe el
cierre de turno (deadlock del hook `stop_proof`). Debe dar **PASS** (s0→s10). RTM snipeit **23/24** (único UNSAT =
REQ-F-007/s6 LLM keyless).
⚠️⚠️ **s9 usa PUERTOS FIJOS (18594/18595)** → NUNCA corras dos s9 en paralelo, y NUNCA dejes un `product-run`/`ci` en
BACKGROUND mientras el turno cierra: el hook `stop_proof` RE-CORRE la estación activa (s9) y colisiona el puerto con
tu run de fondo → **falso rojo "el proof no alcanzó la infra viva en 120s"**. Corré s9 en **FOREGROUND** (timeout
≥420000ms) y dejá que termine ANTES de cerrar el turno. (Esto me costó 3 falsos rojos en FSK-REFS-IN-BODY.)

**2) Entendé los 3 seams del frontend que HOY existen** (todo en `codegen/scaffold_product.py`; nº de línea
aproximados, buscá el texto):
- **`_app_ts`** (~L2741): emite `frontend/src/app.ts` con `render<E>List(rows): string` — mapea `rows` → `<li>` del
  1er campo string/enum de la entidad **CON DUEÑO** (la única con capa viva). Devuelve un **STRING** de markup. Es
  el entry que esbuild bundlea (perf, s8) Y lo que el consumer renderiza. **Acá hay que sumar el MOUNT + el FORM.**
- **`_client_ts`** (~L783): emite `frontend/src/client.ts` con `create<E>(base, body)` / `get<E>(base, id)` /
  `list<E>(base)` (`fetch` REAL, type-bound al contrato `Pick<components["schemas"][<E>]>`, `res.json()` narrow
  desde `unknown` con ts-reset, sin `any`). **El form va a llamar `create<E>` tal cual** (no lo toques salvo que
  necesites un tipo de body).
- **`_consume_check_ts`** (~L3981) + **`_CONSUME_CHECK_SKELETON`** (~L4016): emite `frontend/consume_check.ts`, el
  proof e2e del check **`frontend_consume_live`** (s9, infra_up). Corre por `node --experimental-strip-types` contra
  el AppServer vivo: round-trip `create<E>`→`get<E>` + trae `list<E>` y asevera que `render<E>List(rows)` (STRING)
  refleja cada fila viva. **Acá hay que sumar el bloque jsdom: mount → submit del form → la fila aparece en el DOM.**

**3) EL DISEÑO (resolvelo GENERAL, cero nombres de dominio):**
- **`app.ts` gana `mount<E>(doc: Document, base: string): Promise<void>`** (o `mountApp`): crea en el `doc` un
  contenedor + una `<ul>` para la lista + un `<form>` con **un `<input>` por campo de `_input_fields(E)`** (name =
  el campo; type-hint por tipo: text/number/checkbox/date — mantenelo simple, todos `<input>` con `name`), + un
  botón submit. Al `submit`: `preventDefault`, lee los valores del form (coerciónalos al tipo del campo: number→
  Number, boolean→checkbox.checked, ref→Number, date/string→string, enum→string), llama `create<E>(base, body)`,
  y al resolver re-trae `list<E>(base)` y **re-renderiza la `<ul>`** (reusá `render<E>List` para el markup, seteá
  `ul.innerHTML`, O —mejor— creá nodos `<li>` con `doc.createElement`). El render del 1er campo string/enum sigue
  siendo el observable.
- **El entry/render NO debe romper esbuild (s8) ni tsc --strict (s2)**: `mount<E>` usa `Document` (lib dom de TS).
  `app.ts` ya importa del cliente; el bundle de perf sigue resolviendo. Si `Document`/`HTMLElement` necesitan la
  `dom` lib en `tsconfig`, verificá que ya esté (s8 usa jsdom en runtime; el TYPE `Document` viene de la lib `dom`
  de TS — chequeá `tsconfig`/`lib`). Si no está, agregala GENERAL (sin nombres de dominio).
- **El proof (extendé `consume_check.ts`, NO sumes check)**: importá `{ JSDOM } from "jsdom"` (idéntico a
  `_a11y_audit_mjs`), construí `const dom = new JSDOM("<!DOCTYPE html><body></body>")`, `mount<E>(dom.window.document,
  base)`, esperá el primer render (lista inicial), después **llená el form** (`input.value = …` /
  `checkbox.checked = …`) y **dispará** `form.dispatchEvent(new dom.window.Event("submit", { cancelable: true, bubbles: true }))`,
  `await` el round-trip (el handler es async — exponé una promesa o poll el DOM con un pequeño retry), y asevera que
  un nuevo `<li>` con el valor posteado **EXISTE como nodo** (`dom.window.document.querySelectorAll("li")`). `fetch`
  global de Node sirve dentro de jsdom (el código bajo prueba usa el `fetch` global, Node 18+).

**EL DIENTE NUEVO de dos lados (el corazón del incremento):** tras el submit, el nodo `<li>` de la fila creada
**aparece en el DOM** (cuéntalos: N→N+1; el texto del nodo == el valor posteado) → **un mount que no re-renderiza, o
un form cuyo submit no postea, o un render que no crea el nodo → el nodo está AUSENTE → rojo**. Lado negativo: un
valor de form inválido (tipo equivocado) → `create<E>` propaga el 400 (el cliente chequea `res.ok`) → la fila **NO**
se agrega (count del DOM sin cambio) + (opcional) un nodo de error. Saboteá el re-render (que el submit no actualice
el DOM) → corré → confirmá ROJO **sólo** en `frontend_consume_live` (hermanos s9 `access_control_live` +
`observability_live` verdes) → revertí → verde.

---

## 1. Objetivo + scope acotado (qué deja TERMINADO)

El frontend de la entidad **CON DUEÑO** (la que ya tiene `render<E>List`/cliente vivo) **se monta en un DOM real
(jsdom)** y un **FORM** generado postea una fila nueva vía `create<E>` → re-render → la fila aparece como **nodo del
DOM**. Demostrado e2e en jsdom contra el AppServer vivo (PG real), mismo rigor que los hermanos.

**Scope acotado (recomendado):** SÓLO la entidad con dueño (la única con `_app_ts`/cliente vivo). **Diferí**: forms
para la entidad ownerless y la con-ref (eje hermano, mismo patrón) · validación client-side más allá de lo que el
server enforza · CSS/layout · edición/borrado desde la UI (sólo CREATE+LIST por ahora) · **Playwright / browser real
(necesita red para el binario) = DIFERIDO duro** (el diente es el DOM real + el evento, no un Chromium).

**Decisión de arquitectura (resolvela GENERAL):** ¿`render<E>List` sigue devolviendo string (y `mount` setea
`innerHTML`) o pasa a crear nodos? RECOMENDACIÓN: que `render<E>List` siga devolviendo el string (no rompe el
bundle de perf de s8 ni el assert string del consumer existente) y que **`mount<E>` lo use** (`ul.innerHTML =
render<E>List(rows)`) — aditivo, sin tocar el diente de RENDER-LIST. El FORM y el submit son lo nuevo. Lo que
importa para el cierre: que un **evento de submit en un DOM real** produzca un **nodo nuevo** vía el cliente vivo.

---

## 2. Maquinaria a REUTILIZAR (no la reinventes)
- **`render<E>List`** (`_app_ts`): el markup de la lista (string). `mount<E>` lo reusa para el cuerpo de la `<ul>`.
- **`create<E>`/`list<E>`** (`_client_ts`): el form llama `create<E>(base, body)`; el re-render llama `list<E>(base)`.
  Ya hacen `fetch` real type-bound. NO los reimplementes.
- **`_input_fields(e)`** (~L902): la fuente única de qué campos lleva el cuerpo (escalares requeridos no-dueño + el
  ref requerido no-dueño, FSK-REFS-IN-BODY). El FORM emite **un input por cada uno** (mismo set que el server parsea).
  Coerción por tipo: `_KT_FIELD_TYPE`/`_OAPI_TYPE` te dan el tipo; mapealo a number/checkbox/text en el JS del form.
- **`JSDOM`** (idiom de `_a11y_audit_mjs` ~L2782): `import { JSDOM } from "jsdom"`; `new JSDOM(...)`,
  `dom.window.document`, `dom.window.Event`. jsdom YA está en `package.json` (`JSDOM_VERSION`, ~L761) — sin dep nueva.
- **`consume_check.ts` + su harness infra_up** (`frontend_consume_live`, s9): EXTENDELO con el bloque jsdom. Lee la
  base del server vivo (mismo `argv[0]`).

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **⚠️ s9 PUERTOS FIJOS → corré FOREGROUND, nunca background al cerrar turno.** El hook `stop_proof` re-corre la
  estación activa (s9) al cierre del turno; si tenés un `product-run`/`ci` de s9 en BACKGROUND, colisionan el puerto
  → falso rojo "el proof no alcanzó la infra viva en 120s". (3 falsos rojos en FSK-REFS-IN-BODY por esto.) Un
  producto a la vez, en foreground, timeout ≥420000ms; dejá terminar antes de cerrar el turno.
- **⚠️ Re-materializar el chasis SÓLO si sumás/quitás un CHECK.** Si EXTENDÉS `consume_check.ts` (el MISMO check
  `frontend_consume_live`) → el `proof_sha` NO cambia → **pines byte-idénticos, sin re-materializar, sin re-pinear**
  (`ci --rederive` snipeit/default/assets == pin, byte-idéntico). **PREFERÍ extender el check existente.** Si sumás
  un check nuevo: re-materializá el chasis del DEFAULT a mano + re-pineá (ver §3 de FSK-REFS-IN-BODY). `pinned_verdict.json`
  es **per-estación** (s0..s10), NO el RTM → cambiar prosa del spec (acceptance/tech) NUNCA toca el pin.
- **Server vivo por `java -cp build/install/<pkg>/lib/*`, NUNCA `gradle run`** (el daemon forkea el JVM → leak de
  puerto). Ya cableado en s9.
- **`proof_protect` DENIEGA tocar `.proof/` por shell (incluso leer)** → usá `meta rtm`/`meta recall`; el árbol
  generado (`products/<p>/build/product/...`) SÍ es legible.
- **Eyeball SIN gradle antes de cada corrida lenta** (cacé TODO sin gradle así): emití los 3 productos a temp y leé
  el TS generado. Patrón:
  ```python
  import sys, yaml; from pathlib import Path
  sys.path.insert(0, "factories/full-stack-kotlin/codegen"); import scaffold_product as S
  froot = Path("factories/full-stack-kotlin").resolve()
  bps = {"default": S._load_blueprint(froot)}
  for p in ("assets","snipeit"): bps[p] = yaml.safe_load((froot/"products"/p/"product.yml").read_text())
  for n,bp in bps.items():
      files = S.build_files(bp); assert files == S.build_files(bp)  # idempotente
      # escribí app.ts/consume_check.ts a temp; corré `npx tsc --noEmit` mental / py-check de placeholders
  ```
  Verificá: sin `%PLACEHOLDER%` sin sustituir · `node --experimental-strip-types` parsea el `consume_check.ts` ·
  el `app.ts` no rompe tsc (`Document`/`HTMLElement` desde la lib `dom`) · `build_files(bp)` idéntico dos veces.
- **El consumer (`frontend/`) NO se type-checkea** (vive fuera del `include` de tsc, como `consume_check.ts` hoy);
  el tooth DES-6 vive en `src/client.ts` (Pick del contrato). Pero `src/app.ts` SÍ pasa tsc --strict + ESLint (s2).

## 4. Restricciones DURAS de FSK que SIGUEN vigentes
Token estático `Bearer <rol>:<principal>`. La capa viva (server+cliente+render) es **opt-in a `owned_by`** para la
entidad con dueño; el form arranca por esa entidad. `tsc --strict` + ESLint strict + `no-explicit-any` + ts-reset
muerden `src/*.ts` (incl. `app.ts`); el consumer en `frontend/` (root) NO. detekt/`-Werror` muerden el Kotlin (no
cambia acá). **Playwright / browser real + CSS/layout + edición/borrado desde UI + forms multi-entidad = DIFERIDO.**

## 5. Disciplina + dónde van los docs
- **Contenido de FÁBRICA GENERAL** (`codegen/` + `factory.spec.yml`): **cero nombres de dominio**, `git diff` de TODO
  `product.yml` = 0. El producto es DATA (ADR-012). Anti-overfit real = el gate `generality` de `meta check`. Lo
  NORMAL es NO tocar sustrato (`src/metafactory/`+`seed/`): todo cabe en codegen/spec. Si necesitás sustrato →
  incremento META aparte + `generality` verde.
- **Docs**: historia de la FÁBRICA → `docs/{STATE.md,LOG.md}` (ADR-016). El gobierno de ESTE incremento → este doc
  (flip a CERRADO + §Evidencia al cerrar). **Commit = parte del trabajo (ADR-010), nunca lo preguntes**; trailers
  I-10 (`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`).
- **Probá POR BLOQUEO**: `product-run` PASS en los 3 (foreground) · `ci --rederive --all-products` == pin (o
  per-producto si el timeout aprieta) · `meta check` 6/6 (`generality` verde) · `git diff product.yml` = 0 ·
  idealmente `git diff src/metafactory/ + seed/` = 0. **No fakees verde.**

## 6. Criterio de cierre (demostrable, no narrable)
1. `product-run` PASS en los 3 (default·assets·snipeit, foreground). El frontend de la entidad con dueño **se monta
   en un DOM jsdom**; un **submit del FORM** crea una fila vía `create<E>` → la fila aparece como **nodo `<li>` en el
   DOM** (count del DOM N→N+1, el texto == el valor posteado). Server caído → rojo.
2. **Diente de DOS lados verificado VIVO**: saboteá el re-render (que el submit no actualice el DOM, o el form no
   postee) → corré → confirmá ROJO **sólo** en `frontend_consume_live` (hermanos s9 `access_control_live` +
   `observability_live` verdes) → revertí → verde. (Negativo: form con valor inválido → 400 propagado → la fila NO
   se agrega.)
3. `ci --rederive --all-products` == pin (los 3). `meta check` 6/6 (`generality` verde). `git diff product.yml` = 0.
   Si extendiste `frontend_consume_live` (recomendado), NO hace falta re-materializar (pines byte-idénticos).
4. El scope honesto se actualiza: STATE/LOG (fábrica) registran "UI montada en DOM + FORM que postea ✅" + los huecos
   que QUEDAN (Playwright/browser real · forms ownerless/con-ref · edición/borrado UI · CSS · deploy). Abrí el
   SIGUIENTE con su handoff autocontenido.

## 7. Qué viene DESPUÉS de browser-form (para que sepas dónde estás parado)
Con el DOM real + el form, la app es **usable por un humano** (crea filas desde un formulario; la lista se
actualiza). Lo que falta para "Snipe-IT usable en un navegador REAL y deployado" (= después podés enfocarte SÓLO en
el producto): **(a)** **deploy real** — el `Dockerfile` ya se genera pero **no se levanta/verifica vivo**; un
incremento que BUILDee la imagen y haga un smoke-test contra el contenedor (docker ya está disponible vía el
infra_up de MAT-3; el build+push de la imagen a un registry sigue diferido por red) · **(b)** **e2e Playwright**
(motor de browser real — necesita red para el binario) · **(c)** forms/edición para TODAS las entidades vivas +
cadenas de refs profundas + self-refs. Después de eso, lo que QUEDA es product-specific (los 12 deferrals de
`products/snipeit/docs/reference/SNIPEIT-DOMAIN.md`: custom-fields, checkout polimórfico, company-scoping,
depreciación calculada, …) — eso YA es "enfocarse en el producto", no en FSK.
