# Incremento FSK-CRUD-BODY-PARSING — el server vivo acepta el CUERPO real del request (no samples fijos)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO**
> (creado 2026-06-21T13:49Z). Cerralo con `meta increment close --factory full-stack-kotlin` (gateado: árbol
> limpio + estación activa verde) **o** flippeando este header a CERRADO (lo mismo: el `increment status` lee el
> header). Editar `factories/full-stack-kotlin/**` no-`.md` (codegen/spec/stations) exige ESTE incremento
> abierto — el `increment_guard` elige el lifecycle por la RUTA editada (ADR-016).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Venís de **FSK-S16
> ✅** (CRUD-mutación real: el server vivo MUTA columnas — POST/PUT/DELETE jOOQ tipado — bajo el control de
> acceso, ver `…/work/FSK-CRUD-MUTACION-REAL-INCREMENT.md §Evidencia`). PERO esas mutaciones usan **valores
> FIJOS del codegen** (samples deterministas + `"mutated"`), **NO el cuerpo del request**. Tu trabajo: que el
> server lea el **JSON del body** y persista esos valores **type-coerced por el schema** (DES-12). Es contenido
> de **FÁBRICA, GENERAL** (codegen + spec): cero nombres de dominio, `git diff` de cualquier `product.yml` = 0.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso; FSK ya genera, enforza acceso vivo y MUTA con valores fijos):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, por-producto** (el sandbox de Bash mata gradle: exit 144).
Mantené el cwd de Bash en la RAÍZ del repo (un `cd` a subdir filtra el cwd y rompe el cierre de turno; usá
paths absolutos / subshells). Debe dar **PASS** (s0→s10). RTM 19/20 (único UNSAT = REQ-F-007/s6 LLM, deferral
keyless VISIBLE).

**2) Leé los lugares donde vive el hueco** (todo en `codegen/scaffold_product.py`):
1. `_app_server_handlers` (~L2930): construye `doPost`/`doPut`/`getOne`/`doDelete`. **`doPost` llama
   `Repository.insert<E>(ctx, principal)` SIN leer el body**; **`doPut` llama `update<E><Col>(ctx, id,
   MUT_VALUE)`** con el valor FIJO `"mutated"`; **`getOne` devuelve sólo `{id, <mutable_col>}`**. El server
   NUNCA toca `ex.requestBody`.
2. `_mutation_fns` (~L862): emite `insert<E>`/`update<E><Col>`/`delete<E>`/`<e><Col>` en `Repository.kt`. El
   INSERT arma `set(col, <sample>)` por campo requerido (samples de `_sample`, UNIQUE→`nanoTime`). Acá es donde
   los valores deben venir del **body** (parametrizar) en vez de samples.
3. `_APP_SERVER_SKELETON` (~L3074): el server (`handle()` dispatcher, `respond`, `main`). El server EMITE JSON
   a mano (string templates). Acá agregás la lectura+parseo del body y el 400.
4. `_access_control_check_py` + `_ACCESS_CONTROL_CHECK_SKELETON` (~L3193/L3219): el proof e2e. Hoy asevera el
   round-trip de mutación con el valor FIJO `"mutated"`. Acá agregás: POST {valores del body} → GET ve ESOS
   valores; body malo → 400.

**3) EL DATO QUE LO CAMBIA TODO** (ya verificado): el build **YA depende de `kotlinx-serialization-json`**
(`_build_gradle` ~L507) y los modelos OpenAPI se generan **`@Serializable`** (kotlinx_serialization,
`configOptions` ~L542). **NO hace falta hand-rollear un parser JSON** — `kotlinx.serialization.json` está en el
classpath (es un dep INTENCIONAL de esta fábrica, no viola ADR-012). Confirmá el nombre/paquete de la clase
modelo generada (Pascal de la entidad, p.ej. `Asset`) y usá `Json.decodeFromString`/`Json.parseToJsonElement`.

---

## 1. Objetivo (qué deja TERMINADO este incremento)
El server vivo **acepta el cuerpo real del request** y lo persiste **type-coerced por el schema**: **POST**
inserta una fila con los **valores del body** (no samples fijos), **PUT** actualiza las columnas presentes en
el body (PATCH-like), **GET /{id}** devuelve la **fila completa** (todas las columnas). El diente deja de ser
"mutó a un valor fijo" y pasa a ser "**mutó a lo que el cliente envió**". Body malformado / tipo equivocado /
required ausente → **400** (no 500, no decorativo).

## 2. El hueco HOY (estado de partida, preciso)
- `doPost` inserta con `Repository.insert<E>(ctx, principal)` → samples FIJOS (`_sample`: string→`"sample-…"`,
  int→`2`, …; UNIQUE→`"u${'$'}{System.nanoTime()}"`). El body se IGNORA.
- `doPut` → `Repository.update<E><Col>(ctx, id, MUT_VALUE)` con `MUT_VALUE = "mutated"` FIJO. El body se ignora.
- `getOne` → `{"id":N,"<col>":<valor>}` (sólo la 1ª columna mutable, no la fila completa).
- El server no lee `ex.requestBody`, no parsea JSON, no tiene 400. Scope honesto declarado en FSK-S16 §5.1
  ("body-parsing de JSON real = declared-deferred") y en REQ-F-015 acceptance.

## 3. Deliverable + el DIENTE e2e (de dos lados, no decorativo)
Extendé `access_control_check.py` (genera el body, asevera que VUELVE). Round-trip sugerido:
1. **POST** (rol permitido, dueño sembrado) con `{"<colA>": <vA>, "<colB>": <vB>, …}` (valores DISTINTOS de los
   samples) → 201 + id.
2. **GET /{id}** → la fila completa trae **exactamente** `<vA>/<vB>/…` (type-correct: un int es int, un string
   es string). **Un server que ignora el body → GET devuelve los samples ≠ lo posteado → rojo** (el diente real).
3. **PUT /{id}** con `{"<colX>": <vX-nuevo>}` (por el dueño) → 200; GET /{id} muestra `<vX-nuevo>`.
4. **Body malo** (JSON inválido / tipo equivocado p.ej. string donde va int / required ausente) → **400**
   (diente negativo; un server que traga cualquier cosa → 500 o 201 → rojo).
5. **Los dientes de FSK-S16 siguen**: count round-trip (POST→count+1, DELETE→count−1+404) y de acceso (rol
   prohibido→403 sin mutar, no-dueño→403 sin mutar).

## 4. Decisiones de diseño (resolvelas GENERAL, DATA-agnóstico — la parte de fondo)
1. **Parser JSON (el corazón).** RECOMENDACIÓN: usá **`kotlinx.serialization.json`** (ya en el classpath, §★3).
   Dos sub-opciones: (a) **deserializar al modelo `@Serializable` generado** (`Json.decodeFromString<Modelo>(body)`)
   — type-safe, el contrato ES el parser (DES-6+DES-12), ideal para **POST** (objeto completo); (b)
   **`Json.parseToJsonElement(body).jsonObject`** y leer sólo las claves presentes — ideal para **PUT/PATCH**
   (parcial). Probá (a) para POST y (b) para PUT. Hand-rollear un parser = NO (innecesario). Configurá
   `Json { ignoreUnknownKeys = true }` para tolerar campos extra.
2. **Type-coercion JSON→columna jOOQ (DES-12).** El codegen ya conoce el tipo de cada campo
   (`_OAPI_TYPE`/`_sample`): string→String, int→Int, number→Double, boolean→Boolean, date→`LocalDate.parse`,
   enum→String (¿validar ∈ `values`? recomendado, 400 si no), ref→Long. Generá, por entidad, el mapeo
   body→`set(col, <coerced>)` type-bound. Un tipo equivocado → **400** (capturá la excepción de
   parseo/coerción), NUNCA 500.
3. **El dueño del POST: del body o del principal?** Restricción DURA de FSK: el dueño DEBE existir (FK→User).
   Mantené **dueño = principal del token** (NO del body) → no rompe el FK. Crear filas con dueños arbitrarios
   = sembrar Users primero = OTRO eje; difiéralo. El body provee el resto de columnas requeridas/escalares.
4. **Refs requeridos no-dueño en el body.** Hoy `_mutation_fns` los RECHAZA (restricción #3, SystemExit). Con
   body real podrías aceptar un id existente del body. RECOMENDACIÓN: **difiéralo** (necesita validar que el id
   referido existe → otro eje). Por ahora: dueño = principal + escalares del body; si la entidad tiene un ref
   requerido no-dueño, el server degrada/difiere (documentá, como FSK-S16 hace con la columna mutable).
5. **PUT total (replace) vs PATCH (partial).** RECOMENDACIÓN: **PATCH-like** (actualiza sólo las claves
   presentes en el body) — más simple y útil. PUT-total + el split de verbos = difiéralo.
6. **UNIQUE desde el body.** El cliente provee el valor; si choca, la DB lo rechaza. Capturá la excepción de
   constraint → **409** (no 500). (Para el proof, posteá un valor único.)
7. **¿Slice?** Si entra apretado: (a) POST lee el body + GET devuelve la fila completa (el diente central); (b)
   PUT/PATCH lee el body; (c) 400 en body malo / tipo equivocado. Mejor un slice verde-de-verdad que tres a medias.

## 5. Maquinaria a REUTILIZAR (no la reinventes)
- **`_mutation_fns` (insert/update)**: ya arma `set(col, value)` por campo; parametrizá `value` para que venga
  del body coerced en vez del sample. El shape (returning(ID).fetchOne()… para el insert) se queda igual.
- **`_app_server_handlers`**: `doPost`/`doPut` ya tienen la rama OK (post-veredicto); agregá ahí el
  parseo+coerción+llamada. `getOne` ya emite JSON de 1 fila; ampliala a la fila completa.
- **`_sample`/`_KT_SAMPLE`/`_OAPI_TYPE`**: el catálogo de tipos por campo (referencia para la coerción).
- **Los modelos `@Serializable`** generados por openapi-generator (kotlinx_serialization): el parser type-safe.
- **`respond(ex, status, body)`**: ya existe; agregá un helper `badRequest()` (400) hermano de
  `forbidden()`/`notFound()`.

## 6. Restricciones DURAS de FSK que SIGUEN vigentes (no las rompas)
Las 4 del blueprint (`…/products/snipeit/docs/reference/SNIPEIT-DOMAIN.md`): dueño = principal (FK) ·
`owned_by` required → dueño siempre seteado · refs requeridos no-dueño (ver §4.4) · type-coercion fail-closed
(DES-12: tipo equivocado → 400, no se traga). El server es **opt-in** (sólo con `owned_by`).

## 7. Disciplina + dónde van los docs
- **Contenido de FÁBRICA GENERAL** (codegen `scaffold_product.py` + `factory.spec.yml`): **cero nombres de
  dominio**, `git diff` de TODO `product.yml` = 0. El producto es DATA (ADR-012).
- **Anti-overfit real = el gate `generality` de `meta check`, NO `git diff src==0` literal.** Lo normal acá es
  NO tocar sustrato (`src/metafactory/`+`seed/`): todo cabe en codegen/spec. Si necesitás sustrato → incremento
  META aparte (`meta increment open <slug>`) + `generality` verde.
- **RTM**: considerá una capability nueva `entrada_tipada_runtime` (DES-3/DES-12) + **REQ-F-016**, verified_by
  `access_control_live` (la MISMA check, ahora con el body round-trip), artifact `…/endpoints/AppServer.kt` o
  `Repository.kt` — exactamente como FSK-S16 sumó `crud_mutacion_runtime`+REQ-F-015 (el validador permite que 2
  reqs compartan una check; sólo prohíbe ids duplicados / refs fantasma). Actualizá la descripción de la check
  s9 (`proof_checks` + `checks` de s9) para reflejar el body round-trip.
- **Docs**: estado/historia de la FÁBRICA → `factories/full-stack-kotlin/docs/{STATE.md,LOG.md}` (ADR-016, el
  PRECEDENTE que dejó FSK-S16; el meta STATE sólo se toca para marcar el hueco como ✅). El gobierno de ESTE
  incremento → este doc (flip a CERRADO + §Evidencia al cerrar). **Commit = parte del trabajo (ADR-010), nunca
  lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`).
- **Probá POR BLOQUEO**: `product-run` PASS · `rtm`/`ci --rederive` == pin · `meta check` 6/6. **No fakees
  verde**: un POST que ignora el body y devuelve 201 es exactamente el anti-patrón que el round-trip §3 caza.

## 8. Cómo correr la línea — comandos + lecciones caras (NO re-aprendas)
`meta = PYTHONPATH=src python3 -m metafactory.cli`. **`dangerouslyDisableSandbox: true`** en TODA corrida de
gradle/línea. FOREGROUND, por-producto (~3 min con gradle caliente).
1. `meta product-run --factory full-stack-kotlin --product snipeit` (re-materializa la instancia + s0→s10).
2. `meta rtm --factory full-stack-kotlin --product snipeit` (deferral s6 visible OK) → `meta pin --factory
   full-stack-kotlin --product snipeit`. **El spec se comparte entre los 3 productos** → un cambio de codegen/
   spec obliga a re-pinear los 3: `meta pin --factory full-stack-kotlin` (default), `--product assets`,
   `--product snipeit`; después `meta ci --rederive --factory full-stack-kotlin --all-products` (== pin: default
   + assets + snipeit, sin regresión).
3. `meta check` 6/6 (incluí `generality`).
- **Lecciones de FSK-S16 YA resueltas (no re-aprendas)**: (a) columna UNIQUE → valor único en runtime (ahora
  vendrá del body); (b) `import java.time.LocalDate` (date) va **AL FINAL** del bloque de imports (layout
  ktlint_official: `org.*` → `<pkg>.*` → `java.*`); pure-ASCII lo pone primero → ktlint rojo; (c)
  `@file:Suppress("TooManyFunctions")` ya está en `AppServer.kt` (9→15 fns); agregar un helper de parseo no
  rompe (ya suprimido). detekt: **≤2 returns/fun** (usá `when`/expresiones), MaxLineLength 160.
- **Server vivo largo: `java -cp build/install/<pkg>/lib/*`**, NUNCA `gradle run` (daemon forkea el JVM → leak
  de puerto). Ya cableado en `stations/s9.yml` (`{{package_name}}` se substituye por instancia).
- **`proof_protect` DENIEGA tocar `.proof/` por shell** (incluso leer) → usá `meta rtm`. El árbol generado
  (`products/<p>/build/product/...`) SÍ es legible (no es `.proof/`) — útil para eyeballear el Kotlin/proof
  emitido sin gradle.
- **Eyeball sin gradle**: `python3 -c "import sys; sys.path.insert(0,'factories/full-stack-kotlin/codegen');
  import scaffold_product as S; ..."` + `S.build_files(bp)` imprime el árbol; `--check-idempotent` valida
  byte-identidad. **Hacelo ANTES de cada corrida lenta de gradle** (caza errores de syntax/orden de imports/
  nombres en segundos).
- **Las INSTANCIAS se re-materializan cada corrida** (no edites sus `stations/`/`build/` a mano). Sólo editás
  el codegen/spec de la FÁBRICA. El proof vive en `_access_control_check_py` (template), no en el `tools/`
  materializado.

## 9. Criterio de cierre (demostrable, no narrable)
1. `product-run --product snipeit` PASS · el proof `access_control_live` asevera el **body round-trip** (POST
   {valores} → GET /{id} ve ESOS valores type-correct · PUT {col} → GET ve el valor del body) **+** body malo →
   **400** **+** los dientes de FSK-S16 (count round-trip) y de acceso (403 sin mutar) intactos.
2. **Diente de DOS lados verificado VIVO**: un server que IGNORA el body (devuelve 201/200 con samples) → el
   GET ≠ lo posteado → el proof FALLA (saboteá el codegen, corré, confirmá rojo en s9, revertí). Igual para el
   400 (un server que traga tipo equivocado → no-400 → rojo).
3. `ci --rederive --all-products` == pin (default + assets + snipeit). `meta check` 6/6 (`generality` verde).
   **`git diff` de todo `product.yml` = 0**. Idealmente `git diff src/metafactory/ + seed/` = 0 (cabe en codegen).
4. El scope honesto se actualiza: STATE/LOG (fábrica) registran "body-parsing real ✅" y los huecos que QUEDAN
   (PUT-total/PATCH split · refs del body · CRUD de entidades SIN dueño · custom-fields · frontend React que
   consume + deploy + e2e Playwright) como próximos incrementos.

## 10. Contexto que ya está hecho (de dónde venís)
- **FSK-S16 ✅ (2026-06-21)**: el server vivo MUTA columnas (POST/PUT/DELETE jOOQ tipado) bajo el control de
  acceso; diente de ROUND-TRIP. Pero con valores FIJOS del codegen. Detalle: `…/work/
  FSK-CRUD-MUTACION-REAL-INCREMENT.md §Evidencia` + `…/docs/LOG.md` (2026-06-21T13:44Z).
- **La trilogía de control de acceso vive** (FSK-S13 RBAC · S14 ownership · S15 endpoints vivos) + **FSK-S16
  CRUD-mutación**. Este incremento es el SIGUIENTE escalón: que ese CRUD acepte **input real del cliente** —
  el último gran hueco backend antes del frontend (React que consume + deploy + e2e).
