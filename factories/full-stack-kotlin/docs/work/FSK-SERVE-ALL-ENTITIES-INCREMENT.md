# Incremento FSK-SERVE-ALL-ENTITIES — el AppServer vivo monta CRUD para TODAS las entidades del blueprint

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (2026-06-24; ver §Evidencia al final). Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige un incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-FRONTEND-BROWSER con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (y por qué es DECISIÓN tuya)

**EL NÚCLEO ESTÁ COMPLETO** (modelo · acceso · comportamiento · valores-derivados · app-que-corre + frontend en un
BROWSER REAL). De acá en más TODO es BREADTH y profundidad-de-detalle — los flecos, no el corazón.

Quedaban DOS ejes de breadth VISIBLE: (a) el frontend en un navegador real **[HECHO, FSK-FRONTEND-BROWSER, 2026-06-24]**
y **(b) servir TODAS las entidades/rutas** — ESTE. Hoy el AppServer vivo (`endpoints/AppServer.kt`) monta CRUD para
sólo **3 entidades representativas**: la 1ª con dueño (`owned`), la 1ª ownerless servible (`_live_ownerless`) y la 1ª
con un ref requerido no-dueño (`_live_with_ref`). El resto del dominio (en snipeit: 19 entidades) **existe en el
contrato + el schema + jOOQ pero NO tiene rutas vivas**. Este eje generaliza la SELECCIÓN: el server monta CRUD
RBAC/ownership-aware para CADA entidad del blueprint → el dominio ENTERO se vuelve usable a runtime. Es el último gran
hito de "superficie completa": tras él, el backend faithful está completo de superficie.

**⚠️⚠️ ESTA ES TU DECISIÓN (con más contexto).** Es el de mayor VALOR de superficie pero NO es el más bounded — generalizar
CRUD a N entidades obliga a aplicar a CADA una toda la lógica per-entidad que hoy sólo corre sobre las 3 representativas
(seeding transitivo, refs, verbos qty/workflow, soft-delete, company-scope, poly). Si al planificar ves que el riesgo no
compensa, en §7 hay alternativas HONESTAS y MÁS BOUNDED (time-elapsed es la más tight). Tenés autoridad para reabrir con
`meta increment` — pero leé los wrinkles ANTES.

### 0.1 LOS WRINKLES (leelos — acá está el riesgo)
1. **⚠️ EL RIESGO #1: el SEEDING transitivo para TODA entidad.** El proof e2e (`access_control_check.py`) hace POSTs con
   FKs VÁLIDAS leídas de `/seed`. Hoy `seedRows` siembra el dueño + sus deps transitivas + los targets de la 1ª
   with_ref. Para servir N entidades, `/seed` debe exponer un id sembrado para CADA entidad que el proof ejercite, y el
   seeder debe resolver el grafo de dependencias COMPLETO en orden topológico (ya lo hace parcialmente: `_seed_deps`).
   **Los CICLOS** (Location↔User, deferral 6) y los **refs forward** (constraint diferida) complican el orden — el
   seeder ya los maneja con NULL-then-UPDATE, pero a escala-N hay que probarlo. **Sub-decisión a resolver PRIMERO**:
   ¿el proof ejercita TODAS las entidades, o un subconjunto representativo MÁS amplio? Servir-todas-las-rutas ≠
   probar-todas-de-dos-lados. Una opción HONESTA y bounded: montar las rutas de TODAS, pero el diente e2e sobre un
   conjunto representativo (las 3 de hoy + las nuevas formas), y declarar el resto "montado, no e2e-probado".
2. **El CODEC compartido a escala-N.** `_codec_helpers(served, …)` une los parsers de cuerpo de las entidades servidas
   SIN colisión. Con N entidades, hay que verificar que la unión de coerciones no colisione (nombres de helper
   por-inicial → el bug de FSK-CODEGEN-ROBUSTO ya lo resolvió var-by-initial; re-confirmá a escala). Cada entidad suma
   un `parse<E>Input` + un import + un `handle<E>` + un `createContext`.
3. **detekt a escala-N.** Más entidades = más funciones/imports/ramas en AppServer.kt → `TooManyFunctions` (ya
   `@file:Suppress`), `LongMethod`/`CyclomaticComplexMethod` en `main` (N `createContext`) y en el dispatch. Vas a
   necesitar `@Suppress` opt-in adicionales O partir el server en helpers por-entidad. MaxLineLength 160, NoMultipleSpaces
   (un doble-espacio antes de `//` rojo s2 — me mordió ESTA sesión), PropertyWrapping 120.
4. **Per-entidad: cada una trae sus wrinkles.** Una entidad servida puede tener: refs requeridos (FSK-REFS-IN-BODY),
   verbos qty/workflow (FSK-DOMAIN-OPS/QTY), soft-delete (read-filter), company-scope (read-filter + verdict), poly
   refs, self-refs, computed fields. Hoy el código aplica esto a las 3 representativas. Generalizar = aplicar la MISMA
   maquinaria por-entidad en un loop. Decidí: ¿una entidad con dueño además de `owned`? ¿qué entidad "manda" el /seed
   principal? Mantené `owned` como la entidad-de-control-de-acceso (su diente ownership es el corazón) y suma las demás
   como CRUD RBAC-only (como las ownerless de hoy), salvo que tengan su propio `owned_by`.

**Conclusión honesta**: el camino BOUNDED de PRIMER-CUT — NO re-escribir el AppServer; sino **generalizar `served`** (hoy
3 entidades fijas) a "todas las entidades servibles" y **el loop que ya existe** (`_ownerless_handlers` por entidad) a
N, manteniendo la entidad con dueño como la de control-de-acceso. El diente nuevo: el proof ejercita ≥1 entidad NUEVA
(antes no montada) de dos lados (rol prohibido→403 / permitido→201 + round-trip), probando que el dominio creció.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥600000ms** (el sandbox mata gradle).
**cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del hook `stop_proof` al
cerrar; usá subshells `( cd … )`). Debe dar **PASS**, RTM snipeit **25/26** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **Puertos en uso**: s7 PG 5435 · s9 PG 5436/5437/5438 + servers 18593-18595/18597 · s11 18596. El nuevo check de
ESTA sesión (`frontend_browser_live`) usa **PG 5438 + server 18597**. NUNCA dos corridas en paralelo.

**2) ENTENDÉ la selección actual** (`codegen/scaffold_product.py`):
- `_app_server_kt(pkg, bp)` (~5036): el server. `served = [owned] + [ownerless] + [with_ref]` (~5077). Generalizá ESTO.
- `_live_ownerless(entities)` (~1410) / `_live_with_ref(entities)` (~1461): eligen 1 entidad cada uno. El eje = pasar de
  "la 1ª" a "todas las servibles".
- `_ownerless_handlers(e, …)`: emite el bloque de handlers de UNA entidad ownerless. Ya está parametrizado → llamalo en
  loop por cada entidad nueva.
- `_seed_deps` / `_seed_chain` / `_ref_targets`: el seeder transitivo. A escala-N tiene que sembrar el grafo entero.
- `access_control_check.py` (`_access_control_check_py`): el proof e2e. Sumale el bloque de ≥1 entidad nueva (dos lados).

**3) EL DISEÑO (GENERAL, cero nombres de dominio):** generalizá `served` a todas las entidades servibles (con
`write_roles` + cuerpo sembrable), montá el loop de handlers+contextos por cada una, extendé `/seed` y el seeder al
grafo completo, y el proof a ≥1 entidad nueva. Mantené `owned` como la de control-de-acceso (su diente ownership intacto).

**EL DIENTE de dos lados**: una entidad NUEVA (antes no montada) responde a runtime — POST rol prohibido→403 (sin
INSERT) / permitido→201 + round-trip del cuerpo. Degradá su guard RBAC → SÓLO `access_control_live` rojo, hermanos s9
verdes → revertí → verde. Server caído → rojo (nativo de infra_up).

---

## 1. RE-PIN — depende. Si SÓLO extendés `access_control_live` (s9) y `seedRows`/AppServer sin check nuevo →
sólo s9 (y quizá s2/s0 si cambia el conteo de archivos) re-pinea. Si NO agregás check/estación nuevos y el `proof_sha`
de las estaciones afectadas cambia, re-pin esas. Como SIEMPRE: `meta pin --product <p>` para los 3 productos tras
verde, luego `ci --rederive` == pin. Documentá qué cambió.

## 2. Maquinaria a REUTILIZAR (verificá los anchors con grep)
- **`_app_server_kt`** (~5036): el server; `served` (~5077) es la fuente única de qué se monta.
- **`_ownerless_handlers(e, catch_fk, ops, by)`**: el generador de handlers por-entidad (ya parametrizado).
- **`_codec_helpers(served, creates_parsers)`**: el codec unionado (sin colisión por-inicial).
- **`_seed_deps` / `_seed_chain`**: el seeder transitivo topológico (ya maneja ciclos NULL-then-UPDATE).
- **`access_control_check.py`** (`_access_control_check_py(bp)`): el proof e2e urllib — el modelo a extender.

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **PROOF MANUAL para feedback RÁPIDO del diente** (recompilás la dist ~3min, no ~9 del product-run): la dist de la
  última corrida verde vive en `products/snipeit/build/product/build/install/snipeit`. Levantá PG en docker
  (`postgres@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb`, `-p 5439:5432`, pass
  `metafactory`), corré `java -cp 'build/install/snipeit/lib/*' snipeit.endpoints.AppServerKt` (env `FSK_AC_PORT`/
  `FSK_PG_URL`/`FSK_WEB_DIR=frontend/dist`) y tu proof contra él. ⚠️ El infra_up NO surfacea el stdout del proof → un
  fallo se ve como "no alcanzó la infra viva en 120s" con stdout VACÍO; el proof manual lo DESTAPA.
- **No uses `sleep` en foreground** (el harness lo bloquea). Esperá el server con
  `curl --retry 40 --retry-delay 1 --retry-connrefused -sf http://127.0.0.1:<port>/health`.
- **`com.sun.net.httpserver` NO loguea la excepción de un handler** (cierra la conexión). Si TODOS los checks rojos ⟹ el
  server crashea (reproducí manual); si los HERMANOS están VERDES ⟹ el server VIVE, es TU aserción.
- **`proof_protect` DENIEGA tocar `.proof/` por shell** — el **Read tool SÍ** lee `.proof/logs/` (son RESÚMENES).
- **`ci --rederive` opera sobre el ÁRBOL DE TRABAJO** (borra `.proof/`+`build/`, re-deriva in-place de la fuente
  ACTUAL — NO clona git). NO necesitás commitear antes de `ci --rederive`. UNO A UNO en foreground (~5-9 min c/u; o
  **delegá a un subagente Sonnet** que los corra secuenciales — lo hizo ESTA sesión). `meta check` es el self-check
  del meta (RÁPIDO, NO re-deriva).
- **EYEBALL byte-neutro SIN gradle** (HEAD vs working): `importlib` carga el scaffold HEAD (`git show HEAD:…`) y el
  working, llama `_load_blueprint(root)` + `build_files(bp)` para base/assets/snipeit y diffea las claves (added/
  removed/changed). Para los productos NO-adoptantes confirmá que NO cambian; para una mejora GENERAL los 3 cambian
  IGUAL (sin nombres de dominio). Tras tocar `product.yml` RE-MATERIALIZÁ:
  `ensure_product_instance(chassis, product_root, meta_root, slug)`.
- **ktlint/detekt** (Kotlin): MaxLineLength 160, **NoMultipleSpaces** (un doble/triple-espacio antes de `//` red s2 —
  me mordió ESTA sesión), PropertyWrapping 120, NoUnusedImports + -Werror, ChainWrapping, LongMethod ≤ 60 (`@Suppress`
  opt-in), ReturnCount ≤ 2, CyclomaticComplexMethod ≤ 15, TopLevelPropertyNaming (un `const val` top-level va en
  SCREAMING_SNAKE; un `val` no-const en camelCase). **tsc --strict** + **eslint** del lado TS.
- **VALIDÁ BARATO ANTES DE GRADLE** (lo hizo ESTA sesión, ~10s vs ~9min): generá los archivos con `importlib` +
  `build_files`, escribilos en `build/product/...`, y corré `npx tsc --noEmit` (el gate s2 TS) + `npx eslint` + (si
  tocás el frontend) `node build_bundle.mjs`. Atrapa errores de tipo/lint/bundle SIN el product-run completo.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento, breadth)
**time-elapsed** (`current_value` sobre meses TRANSCURRIDOS, FSK-TIME-COMPUTED, necesita mockear `now`) ·
**AppServer-en-contenedor con PG** (s11 hoy usa el ObsServer PG-free; deploy_smoke despliega el ObsServer, no el
AppServer) · **EAV dinámico a runtime** (custom-fields Avenue B) · **PUT de campos opcionales arbitrarios** ·
**Actionlog** (auditoría polimórfica) · **Kits** (bundles) · **push de la imagen a un registry** · **e2e del FORM en
browser** (hoy FSK-FRONTEND-BROWSER prueba el RENDER de la lista en Chromium; el submit del FORM en browser real sigue
sólo en jsdom).

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py`, `factory.spec.yml`, `stations/`) es nivel FÁBRICA → **este incremento** lo
  cubre (header ABIERTO). Las estaciones VIVEN en `factory.spec.yml` (`station_sequence` + `contract.capabilities` +
  `requirements`), NO en `stations/*.yml` (esos son el output materializado por producto, regenerado cada corrida).
- **La adopción** (si tocás `products/snipeit/product.yml`) es nivel PRODUCTO → abrí TAMBIÉN
  `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar `product.yml`. (Servir-todas
  probablemente NO toque product.yml — se DERIVA del blueprint; si es así, no hace falta el incremento de producto.)
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen + los 3 `pinned_verdict.json`) con el incremento ABIERTO,
  luego `docs(fsk): cerrar FSK-SERVE-ALL-ENTITIES (§Evidencia) + abrir <siguiente>` flipeando el header a CERRADO.
- **Probá POR BLOQUEO**: EYEBALL · `product-run --product snipeit` PASS · diente de dos lados vivo (una entidad NUEVA,
  sólo el check afectado rojo) · `ci --rederive` (base + assets + snipeit) == pin · `meta check` 6/6 (`generality`
  verde) · `git diff src/metafactory + seed = 0`.

## 6. Criterio de cierre (demostrable, no narrable)
1. El AppServer vivo monta CRUD para ≥1 entidad ANTES no montada (idealmente todas las servibles), gobernado por
   RBAC/ownership, persistiendo contra la PG viva. `product-run --product snipeit` **PASS**.
2. **Diente de DOS lados verificado VIVO**: una entidad NUEVA — POST rol prohibido→403 (sin INSERT) / permitido→201 +
   round-trip; degradá su guard → SÓLO el check afectado rojo, hermanos verdes → revertí → verde.
3. EYEBALL · `ci --rederive` (base + assets + snipeit) == pin (re-pin documentado) · `meta check` 6/6 · `git diff
   src/metafactory + seed = 0`.
4. STATE/LOG (fábrica) + SNIPEIT-DOMAIN (sacá "~226 rutas / servir todas" de los diferidos duros) actualizados. Abrí el
   SIGUIENTE con su handoff (§7).

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE (con AUTORIDAD para reabrir)
**El núcleo está terminado; de acá es breadth/profundidad.** Si servir-todas-las-entidades no compensa el riesgo ahora,
o querés algo MÁS tight:
- **time-elapsed (FSK-TIME-COMPUTED) — la MÁS BOUNDED**: el `current_value` sobre meses TRANSCURRIDOS desde la compra
  hasta hoy. Necesita un operando "meses entre una fecha y now" en el AST computado + **mockear `now`** en el oráculo
  del proof (determinismo). Extiende FSK-XENTITY-DEPTH2/computed; mecanismo conocido; cierra el último fleco de
  VALORES DERIVADOS. Recomendada si querés un eje chico y limpio.
- **AppServer-en-contenedor con PG (s11)**: hoy `deploy_smoke` (s11) despliega el ObsServer PG-free; desplegar el
  AppServer real necesita la PG en el contenedor (docker-compose-lite o red docker bajo infra_up). Cierra "deploy de la
  app de verdad, no del server de obs".
- **Actionlog (auditoría polimórfica)** · **Kits (bundles)** · **EAV dinámico (Avenue B)** · **PUT de opcionales** ·
  **e2e del FORM en browser** (extender FSK-FRONTEND-BROWSER al submit en Chromium, no sólo el render).

### ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El backend faithful (modelo·acceso·comportamiento·valores-derivados) está COMPLETO, la app CORRE, el frontend se VE en
un navegador REAL y deploya (smoke).** Lo que RESTA es superficie (servir todas las entidades — ESTE) y profundidad-de-
detalle (time-elapsed, Kits, Actionlog, EAV, PUT-opcionales, deploy del AppServer-en-contenedor). El siguiente gran hito
de superficie es que TODO el dominio sea usable a runtime, no sólo 3 entidades.

---

## §Evidencia — CERRADO 2026-06-24 (opus-4.8)

**Hecho (primer-cut BOUNDED, exactamente como recomendaba §0.1):** el AppServer vivo monta CRUD para TODAS las
entidades ownerless servibles, no sólo 3 representativas. snipeit pasó de servir **3** entidades (Asset · Company ·
Accessory) a **18** (Asset con dueño + 17 ownerless). El dominio ENTERO es usable a runtime.

**Diseño (todo en `codegen/scaffold_product.py`, FÁBRICA, GENERAL, cero nombres de dominio):**
- **`_servible_ownerless(entities)`** (nuevo): toda ownerless con `write_roles` + cuerpo POSTeable (`_input_fields`),
  EXCEPTO las pivotes de un verbo `creates` — esas ya se sirven vía su verbo padre y montarlas aparte DUPLICARÍA su
  `<e>RowJson` (redeclaración → no compila). `_live_entities = owned + _servible_ownerless` → fuente única que cruzan
  Repository (insert/rowJson/Input por entidad) y AppServer (qué sirve). `_has_req_ref(e)` (nuevo) decide `catch_fk`.
- **`_app_server_kt`**: `ownerless`/`with_ref` siguen siendo las PRIMARIAS (gobiernan el seed + los dientes especiales
  qty/creates/poly, byte-estables); las DEMÁS servibles (`extras`) se montan con `_ownerless_handlers` (ya
  parametrizado) + un contexto c/u (`%EXTRA_BLOCKS%`/`%EXTRA_CONTEXTS%`). `need_conflict` generalizado a
  `any(_has_req_ref) over servibles or operations`.
- **`access_control_check.py`**: bloque `serve-all` (opt-in) que ejercita de DOS lados las escalares-solo NUEVAS
  (más allá de la ownerless primaria): POST rol prohibido→403 sin INSERT / permitido→201 + round-trip + tipo
  equivocado→400 + DELETE 403/200/404. POST fresco, sin seed/FK (count RELATIVO → robusto a filas pre-sembradas).
  Las con-ref se montan pero NO se e2e-prueban acá (necesitarían sembrar su FK — honesto, wrinkle #1).
- **ktlint a escala (gaps reales que destapó gradle, arreglados GENERAL):** (a) un enum VALUES largo (`Maintenance.type`,
  8 valores → 170c) pasaba MaxLineLength → `_kt_call` lo envuelve (byte-idéntico para enums cortos); (b) `all<E>RowsJson`
  con nombre largo (ConsumableAssignment/ComponentAssignment, 142-145c) tripeaba la regla ktlint **Wrapping** ("Missing
  newline after {") que salta BAJO el 160 → `_jooq_chain` gana `budget` y las lambda-chains usan `PROPERTY_WRAP` (120);
  (c) el `object Repository` con 18 entidades supera **LargeClass** (600) → `@Suppress("LargeClass")` cuando el cuerpo
  es grande. Los tres opt-in por tamaño → default/assets sin re-derivar.

**Probado POR BLOQUEO (con ojos propios):**
- **EYEBALL** (HEAD vs working, `build_files` de los 3): **assets byte-IDÉNTICO** (ya servía todo: Holder+Asset);
  base ~2 archivos (gana Task servido); snipeit 3 archivos (Repository 503→1061 · AppServer 701→1872 ·
  access_control_check 458→487). Cero líneas Kotlin >160; sin imports sin usar; 103/103 `Repository.X` llamados por
  AppServer existen; proof py_compile OK; `accessorycheckoutRowJson` 1× (sin dup); `main` 37 líneas (<60).
- **`product-run --product snipeit` PASS** (s0→s11) · **`product-run` base PASS** (base cambió).
- **DIENTE de DOS lados VIVO** (proof manual contra el dist recompilado + PG docker): saboteado
  `writeRolesManufacturer()→Role.entries.toSet()` (RBAC neutralizado) → SÓLO las 2 aserciones de Manufacturer rojas
  (`[serve-all] /manufacturers POST rol PROHIBIDO (manager) -> 403: esperaba 403, obtuvo 201`), TODAS las hermanas
  (owned · ownerless · demás serve-all) VERDES → exit 1 localizado. Versión limpia → s9 verde.
- **`ci --rederive --all-products` PASS — 3/3 == pin** (base 12/12 · assets 11/11 · snipeit 11/11) · **`meta check`
  6/6** (`generality` verde) · **`git diff src/metafactory + seed = 0`** (sólo `codegen/scaffold_product.py`).
- **proof_sha BYTE-NEUTRO → SIN re-pin**: el increment EXTIENDE checks existentes (access_control_live/s2) sin agregar
  ninguno; `compute_proof_sha` hashea `station_id + (check_name, exit)` (NO el artefacto) → pin byte-idéntico (commit
  feat = sólo el codegen). `ci --rederive` re-deriva los MISMOS proof_sha == pin.

**Criterio de cierre §6: 1 ✅ · 2 ✅ · 3 ✅ · 4 ✅ (este §Evidencia + SNIPEIT-DOMAIN actualizado + el SIGUIENTE abierto:
`FSK-TIME-COMPUTED-INCREMENT.md`).**
