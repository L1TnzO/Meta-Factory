<!-- meta:doc sha=6e1ce00a27dbcce37be22c5d33f9a7277e67149e updated=2026-06-27T01:41Z -->
# Incremento FSK-XENTITY-DEPTH2 — un campo computado CROSS-ENTITY a DEPTH-2 (una cadena de 2 refs `<r1>.<r2>.<campo>`)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (2026-06-24). Abierto 2026-06-24T00:30Z. Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada.
> Evidencia de cierre al final (§Evidencia). La adopción de NIVEL PRODUCTO vive en
> `products/snipeit/docs/work/XENTITY-DEPTH2-ADOPT-INCREMENT.md`.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-OWNER-POLY con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (y por qué es DECISIÓN tuya)

**EL NÚCLEO ESTÁ COMPLETO.** Con FSK-OWNER-POLY (2026-06-24) se cerró el ÚLTIMO gap de MODELO+AUTH (el wrinkle #3).
Hoy el backend faithful tiene: modelo de datos completo (CRUD del grafo · self-ref · ownership opcional/RTD · refs
requeridos transitivos · ciclos cross-entidad · ref polimórfico · **owner polimórfico**) · acceso
(auth→RBAC→ownership→company-scope) · comportamiento (workflow · qty/stock · trash/restore · insert-on-verb/pivote ·
assigns polimórfico) · valores derivados (computado same-entity + cross-entity **depth-1**) · app que CORRE + frontend
que consume+renderiza + deploy. **Lo que resta es BREADTH y PROFUNDIDAD-de-detalle — los flecos, no el corazón.**

**Este incremento ataca el ÚLTIMO refinamiento genuino de VALORES DERIVADOS: cross-entity DEPTH-2.** Hoy
`Asset.current_value` resuelve `model_id.depreciation_months` (depth-1: el ref DIRECTO Asset→AssetModel). Pero en
Snipe-IT REAL el período de depreciación NO vive en el modelo: vive en `Depreciation`, alcanzado por
`AssetModel.depreciation_id` (deferral 13 de `SNIPEIT-DOMAIN.md`). Depth-2 resuelve una CADENA de 2 refs:
`Asset.model_id → AssetModel.depreciation_id → Depreciation.months` — dos JOINs encadenados. Es el más BOUNDED de los
ejes restantes (extiende FSK-XENTITY-COMPUTED, mecanismo PROBADO, cero auth/behavior nuevo) y el de MENOR riesgo.

**⚠️⚠️ ESTA ES TU DECISIÓN (con más contexto).** El núcleo está terminado: la elección del próximo eje es ahora una
cuestión de PRIORIDADES de breadth. Si al investigar decidís que depth-2 NO es lo más valioso, en §7 hay alternativas
HONESTAS y bien framed (la más fuerte: **frontend que renderiza en un BROWSER real + e2e Playwright + servir las ~226
rutas** — lo que hace que el producto "se sienta una app"). Tenés autoridad para reabrir con `meta increment` — pero
leé los wrinkles ANTES.

### 0.1 LOS WRINKLES
1. **El ref del MEDIO es OPCIONAL.** `AssetModel.depreciation_id` es `required: false` (faithful: un modelo puede no
   tener esquema de depreciación). El depth-1 de FSK-XENTITY-COMPUTED exigió ref+campo REQUERIDOS (1er-cut: el valor
   siempre observable). Depth-2 con un ref del medio opcional ⟹ cuando `depreciation_id` es NULL, el JOIN no matchea →
   el operando es null → la fórmula DEBE caer a un default (0) sin crashear. **Camino bounded**: un operando cross-entity
   cuyo JOIN da null → `?: 0.0` (el mismo idiom null-safe que `safeDiv`). Documentá que el 1er-cut de depth-2 admite
   ref-del-medio OPCIONAL (default 0), generalizando el "ref/campo opcional → default 0" que el depth-1 difirió.
   Alternativa más bounded (menos faithful): exigir `depreciation_id` requerido en la adopción (no cierra ciclo → viable).
2. **time-elapsed sigue DIFERIDO (y es un eje APARTE).** El `current_value` REAL deprecia sobre el tiempo TRANSCURRIDO
   (meses desde `purchase_date` hasta HOY), no sobre UN período. Eso necesita un operando "meses entre una fecha y now"
   = una computación con DATE/tiempo (no-determinista respecto del reloj → el oráculo del proof tendría que fijar/mockear
   `now`). NO lo metas en depth-2: es el eje **FSK-TIME-COMPUTED** (su propio incremento). Depth-2 sigue computando UN
   período de depreciación, pero leyendo el período REAL (Depreciation.months) en vez del proxy (AssetModel.depreciation_months).
3. **Dos JOINs en el mismo chasis de query.** El `_row_json_fn` ya wrappea (ChainWrapping) cuando WIDE+JOIN>160; con 2
   JOINs encadenados re-evaluá el wrapping. Un JOIN por ref DISTINTO (no dupliques si dos operandos comparten el mismo r1).

**Conclusión honesta**: el camino BOUNDED — **el AST de un campo computado admite un operando `<r1>.<r2>.<campo>` (dos
puntos); `_validate_computed_ast` valida la CADENA (r1 ∈ refs no-poly de la entidad; r2 ∈ refs no-poly del target de r1;
campo ∈ numéricos del target de r2); el `_row_json_fn` emite 2 LEFT JOINs encadenados; un ref-del-medio NULL → operando
0.0 (null-safe)**. Adopción faithful: `Asset.current_value` pasa a usar `model_id.depreciation_id.months` (Depreciation
alcanzada por un ref opcional) → cierra el deferral 13 de `SNIPEIT-DOMAIN.md`.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥540000ms** (el sandbox mata gradle).
**cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del hook `stop_proof` al
cerrar; usá subshells `( cd … )`). Debe dar **PASS**, RTM snipeit **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **s7 PG 5435 · s9 puertos 18593-18595 + PG 5436/5437 · s11 18596** → NUNCA dos corridas en paralelo, NUNCA dejes un
`product-run`/`ci` en BACKGROUND al cerrar el turno.

**2) EL DISEÑO (GENERAL, cero nombres de dominio):**
- **`_validate_computed_ast`** (~línea 200, param `xnumeric`): hoy un STRING con UN punto `<ref>.<campo>` es depth-1.
  Sumá: un STRING con DOS puntos `<r1>.<r2>.<campo>` → r1 ∈ refs no-poly de la entidad (NO exigir REQUERIDO — wrinkle #1),
  r2 ∈ refs no-poly del target de r1, campo ∈ numéricos no-computados del target de r2. Fail-closed (entidad/campo
  inexistente o no-numérico → SystemExit). Generalizá `xnumeric` a un mapa anidado (o resolvé la cadena recursivamente).
- **`_row_json_fn(e, tbl, by)`** (~línea 1586): hoy parte los operandos same-entity vs cross-entity (1 JOIN por ref).
  Depth-2 → para `<r1>.<r2>.<campo>`: LEFT JOIN al target de r1 (ON r1.id) **luego** LEFT JOIN al target de r2 (ON
  r2.id, desde la 1ª tabla joineada) → leé la columna del 2º target. Un JOIN por ref DISTINTO (dedup). El valor leído
  (nullable por el LEFT JOIN) → `?: 0.0` en la evaluación de la fórmula (null-safe, como `safeDiv`).
- **El oráculo del proof** (`%XSRC_SETUP%`/`%CEVAL_SRC%`, `_computed_srcs`, `_SEED_NUM`): hoy siembra el valor del target
  depth-1. Depth-2 → el valor vive en el target del 2º ref (Depreciation.months); el seeder TRANSITIVO ya lo siembra si
  es alcanzable (mirá `_seed_deps`/`_ensure_seeded`). El oráculo cruza el valor sembrado a 2 hops. Si el ref del medio es
  opcional y NO se siembra → el oráculo espera 0.0 (el default null-safe). **Recomendado: seedeá la cadena completa**
  (el valor derivado es OBSERVABLE) + un caso aparte para el ref-medio NULL → 0.0.

**EL DIENTE de dos lados**: el `current_value` computado cruza depth-2 (lee Depreciation.months vía AssetModel). Degradá
el 2º JOIN (p.ej. leé null / la columna equivocada / saltá el 2º hop) → el valor computado cambia → SÓLO
`access_control_live` (s9, el `[computed]` assert) rojo, hermanos + s0–s8 verdes → revertí → verde. ⚠️ El sabotaje debe
degradar la LÓGICA (el JOIN/lectura), no la forma Kotlin (mantené los identificadores usados para no tripear `-Werror`).

---

## 1. ⚠️ RE-PIN — probablemente NO hace falta
El cambio vive DENTRO del `[computed]` de `access_control_live` (s9) y del `_row_json_fn`, SIN check/estación nuevos →
`proof_sha` INTACTO → pines byte-idénticos. `git diff snipeit/product.yml ≠ 0` ESPERADO (la fórmula); el sustrato +
default/assets product.yml DEBEN quedar en 0. (Si el seeder transitivo necesitara una tabla/import nuevo en el chasis de
seed, re-evaluá — pero es DATA de fábrica, no estructura de checks.)

## 2. Maquinaria a REUTILIZAR — TODO en `codegen/scaffold_product.py` (verificá los anchors con grep)
- **FSK-XENTITY-COMPUTED** (depth-1): `_validate_computed_ast(xnumeric)` · `_computed_srcs` · `_row_json_fn(by)` (el
  split same/cross + el JOIN) · `safeDiv` (el null-safe `/`) · `_ast_uses_div` · `%XSRC_SETUP%`/`%CEVAL_SRC%`/`_SEED_NUM`.
- **FSK-OWNED-REQUIRED-REFS**: `_seed_deps`/`_ensure_seeded` (siembra TRANSITIVA topológica — ya alcanza targets a N hops
  si son refs requeridos; para el ref-medio OPCIONAL puede que tengas que sembrarlo explícitamente para el oráculo).
- **`_cols_of`**: un campo computado = 0 columnas (no se almacena). El depth-2 sigue siendo 0 columnas (read-time).

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **EYEBALL byte-neutro SIN gradle ANTES de cada corrida lenta**: hay un `eyeball.py` reutilizable (carga el scaffold
  HEAD vs working con `importlib`, llama `build_files(bp)` para base/assets/snipeit y diffea byte a byte). Lo nuevo va
  OPT-IN (sin operando de-2-puntos → byte-idéntico). ⚠️ Si tocás la GRAMÁTICA de forma que HEAD rechace el blueprint
  nuevo, el eyeball HEAD-vs-working CRASHEA en snipeit — usalo SÓLO para confirmar base/assets byte-idénticos, e
  inspeccioná la salida WORKING de snipeit aparte. Tras tocar product.yml RE-MATERIALIZÁ:
  `python3 -c "import metafactory.cli as c, pathlib; c.ensure_product_instance(pathlib.Path('factories/full-stack-kotlin'), pathlib.Path('factories/full-stack-kotlin/products/snipeit'), pathlib.Path('.'), 'snipeit')"`.
- **PROOF MANUAL para feedback RÁPIDO del diente** (recompilás la dist ~3min, no ~9 del product-run): la dist de la
  última corrida verde vive en `products/snipeit/build/product/build/install/snipeit`. Levantá PG en docker
  (`postgres@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb`, `-p 5436:5432`), corré
  `java -cp 'build/install/snipeit/lib/*' snipeit.endpoints.AppServerKt` (PG default 5436, puerto 18594) y
  `python3 tools/access_control_check.py http://127.0.0.1:18594` → ves la ASERCIÓN exacta. ⚠️ El infra_up NO surfacea el
  stdout del proof en su log → un fallo se ve como "no alcanzó la infra viva en 120s" con stdout VACÍO; el proof manual lo
  DESTAPA. Para iterar: saboteá el `.kt` GENERADO en `build/product`, `./gradlew installDist`, corré el proof, restaurá
  (build/product se regenera en el próximo product-run/ci → no contamina el pin).
- **`com.sun.net.httpserver` NO loguea la excepción de un handler** (cierra la conexión). Si s9 cae con TODOS los checks
  rojos ⟹ el server crashea (reproducí manual); si los HERMANOS (`observability_live`/`frontend_consume_live`) están
  VERDES ⟹ el server VIVE, es TU aserción (`frontend_consume_live` usa el MISMO AppServerKt).
- **`proof_protect` DENIEGA tocar `.proof/` por shell** — el **Read tool SÍ** lee `.proof/logs/` (son RESÚMENES).
- **`ci --rederive` por producto**: `--product snipeit`/`--product assets` y SIN `--product` (la base). UNO A UNO en
  foreground (< 10 min c/u; `--all-products` en una sola llamada EXCEDE el timeout de 10 min → corrélos por separado o
  delegá a un subagente Sonnet que los corra secuencialmente). `meta check` es el self-check del meta (RÁPIDO, NO re-deriva).
- **Diente más limpio = un valor escalar equivocado** (no un crash): degradá el 2º JOIN → el `[computed]` assert rojo,
  server VIVO. Mantené los identificadores usados (sin `-Werror`).
- **ktlint/detekt**: MaxLineLength 160, PropertyWrapping 120 (¡las `val`!), NoUnusedImports + -Werror, MagicNumber ignora
  -1/0/1/2 (un `0.0` literal NO bitea), ChainWrapping (wide+JOIN>160 → cada `.call` su línea), LongMethod ≤ 60
  (`@Suppress` opt-in cuando el serializador exhaustivo se pasa), ReturnCount ≤ 2, CyclomaticComplexMethod ≤ 15.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento, breadth)
**time-elapsed** (current_value sobre meses transcurridos, eje aparte FSK-TIME-COMPUTED) · **EAV dinámico a runtime**
(custom-fields Avenue B) · **PUT de campos OPCIONALES arbitrarios** · **e2e Playwright / browser real** ·
**AppServer-en-contenedor con PG** (s11 hoy usa el ObsServer PG-free) · **Actionlog (auditoría polimórfica)** · **Kits
(bundles)** · **las ~226 rutas** (hoy el AppServer sirve un SUBCONJUNTO vivo: el owned + 1 ownerless + 1 with_ref).

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py`) es nivel FÁBRICA → **este incremento** lo cubre (header ABIERTO).
- **La adopción** (`products/snipeit/product.yml`: la fórmula de `current_value` → depth-2) es nivel PRODUCTO → abrí
  TAMBIÉN `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) + `feat(snipeit): …` (product.yml) + `docs(fsk): cerrar
  FSK-XENTITY-DEPTH2 (§Evidencia) + abrir <siguiente>`. Commiteá el CÓDIGO con el incremento ABIERTO, luego flipeá el
  header a CERRADO en el commit de docs.
- **Probá POR BLOQUEO**: EYEBALL byte-neutro (base/assets) · `product-run --product snipeit` PASS · diente de dos lados
  vivo (sólo s9) · `ci --rederive` (base + assets + snipeit) == pin · `meta check` 6/6 (`generality` verde) · `git diff
  src/metafactory + seed = 0` · default+assets product.yml = 0.

## 6. Criterio de cierre (demostrable, no narrable)
1. Un campo computado admite un operando `<r1>.<r2>.<campo>` (depth-2) y `product-run --product snipeit` **PASS** — el
   `current_value` de un Asset lee `Depreciation.months` vía `AssetModel.depreciation_id` (2 JOINs), con el ref del medio
   NULL → 0.0.
2. **Diente de DOS lados verificado VIVO**: degradá el 2º JOIN/lectura → el `[computed]` assert de s9 rojo → revertí → verde.
3. EYEBALL byte-neutro (base/assets) · `ci --rederive` (base + assets + snipeit) == pin · `meta check` 6/6 · `git diff
   src/metafactory + seed = 0` · default+assets product.yml = 0.
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md` (cierra deferral 13) actualizados. Abrí el SIGUIENTE con su handoff (§7).

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE (con AUTORIDAD para reabrir)
**El núcleo está terminado; de acá en más es breadth.** Si al investigar decidís que depth-2 NO es lo más valioso ahora:
- **Frontend REAL en un browser + e2e Playwright (la alternativa MÁS FUERTE para "se siente una app")**: hoy el frontend
  es un cliente TS que un `node` consumer ejercita (round-trip + render-a-string) — NO hay un React montado en un browser
  ni un Playwright que haga click. Este eje monta la app real y la prueba en un navegador headless. Es lo que un USUARIO
  nota al "entrar a la app". El más alto retorno percibido.
- **Servir las ~226 rutas (todas las entidades, no el subconjunto vivo)**: hoy el AppServer monta el owned + 1 ownerless +
  1 with_ref. Generalizar a CRUD de TODAS las entidades del blueprint hace el backend "completo" de superficie.
- **time-elapsed (FSK-TIME-COMPUTED)**: el current_value sobre meses TRANSCURRIDOS (necesita mockear `now` en el oráculo).
- **AppServer-en-contenedor con PG (s11)** · **Actionlog (auditoría polimórfica)** · **Kits (bundles)** · **EAV dinámico
  (Avenue B)** · **PUT de campos opcionales arbitrarios**.

### ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El núcleo funcional + behavioral + de MODELO/AUTH/valores-derivados(depth-1) está COMPLETO** (app que CORRE, consume,
renderiza y deploya). **Depth-2 (este)** cierra el ÚLTIMO refinamiento de valores derivados. Tras él, lo que resta
(frontend-en-browser, ~226 rutas, time-elapsed, Kits, Actionlog, EAV, PUT-opcionales) es trabajo de BREADTH y
PROFUNDIDAD-de-detalle — los flecos. El backend faithful está, en lo esencial, TERMINADO; el siguiente gran hito es el
FRONTEND real (browser).

---

## §Evidencia (cierre 2026-06-24)

**Construido — el AST de un campo computado admite un operando CROSS-ENTITY de PROFUNDIDAD ARBITRARIA**
`<r1>[.<r2>...].<campo>` (depth-1 y depth-2+ por el MISMO camino). Todo en `codegen/scaffold_product.py` (DATA de
fábrica, ADR-012); `src/metafactory/ + seed/` = **0 líneas**.

- **Helper único `_xref_resolve(start, by, parts, …)`** — camina la cadena de refs (cada hop un ref no-poly de la
  entidad en curso cuyo `to` ∈ el grafo; REQUERIDO **u** OPCIONAL: el LEFT JOIN es null-safe `?: 0.0`) y exige que
  el campo final sea numérico no-computado. Devuelve `(steps, tgt, tfld)` → sirve a la VALIDACIÓN, al `_row_json_fn`
  y al ORÁCULO del proof (un solo lugar de verdad). Generaliza a profundidad N.
- **Validación** (`_validate_computed_ast`): un string con punto(s) llama `_xref_resolve` (fail-closed). Se le pasa
  `(e, by)` en vez del viejo mapa `xnumeric` (depth-1-only). Relaja la exigencia de "ref requerido" del 1er-cut
  depth-1 (el null-safety lo cubre) — sin efecto en ningún producto (base/assets sin computado; snipeit pasa a depth-2).
- **`_row_json_fn`**: los JOINs se construyen por HOP, deduplicados por PREFIJO de cadena, ENCADENADOS (`leftJoin(to)`
  + `on(from.ref.eq(to.ID))` con `from` = la tabla del hop, no la entidad) → depth-2 = 2 JOINs encadenados
  (Asset→AssetModel→Depreciation). El `val` de fuente se nombra con TODOS los segmentos (`xR1R2Campo`, sin colisión).
- **Oráculo** (`_COMPUTED_PROOF`/XSRC): `_xref_resolve` resuelve el campo final → su valor sembrado `_SEED_NUM` se
  cruza a N hops (`{"model_id.depreciation_id.months": 2}`).

**Verde por bloqueo (demostrado, no narrado):**
- **EYEBALL byte-neutro** — HEAD-vs-working sobre los 3 productos: `base` y `assets` **byte-idénticos** (0 diffs); el
  refactor preserva depth-1 EXACTO. (snipeit no se puede comparar HEAD-vs-working porque HEAD rechaza el blueprint
  depth-2 nuevo — limitación esperada del eyeball; la salida WORKING de snipeit se inspeccionó aparte.)
- **Salida WORKING de snipeit** (`assetRowJson`): 2 `leftJoin` encadenados, el 2º `on(ASSETMODELS.DEPRECIATION_ID.eq(
  DEPRECIATIONS.ID))` (from = ASSETMODELS, no ASSETS), selecciona `DEPRECIATIONS.MONTHS`, lee null-safe; sin líneas >160.
- **`product-run --product snipeit` PASS** · RTM **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
- **Diente de DOS lados VIVO y preciso** (proof MANUAL contra la dist compilada — el infra_up no surfacea el stdout):
  degradé el 2º JOIN (`eq`→`ne`, sabotaje de LÓGICA que compila) → de ~110 asserts SÓLO `[computed]` rojo
  (`esperaba 21.25, obtuvo 42.5`: el chain intacto da `max(42.5 − 42.5/2, 0)=21.25`, el degradado lee months null →
  `0.0` → `42.5`), con `/health` 200 y todos los hermanos verdes (server VIVO) → revertí → verde.
- **`ci --rederive`** base + assets + snipeit == pin (clones limpios, sin re-pin: `proof_sha` intacto — el cambio vive
  DENTRO del `[computed]` de s9 y del `_row_json_fn`, cero check/estación nuevos) · **`meta check` 6/6** (`generality`
  verde) · **`git diff src/metafactory + seed = 0`** · default+assets `product.yml` = 0.

**Adopción faithful**: `Asset.current_value = max(purchase_cost − purchase_cost/model_id.depreciation_id.months, 0)`
→ lee `Depreciation.months` (el período REAL) vía `AssetModel.depreciation_id` (2 JOINs). Cierra el **deferral 13** de
`SNIPEIT-DOMAIN.md`. Decisión: el ref del medio es REQUERIDO en la adopción (observabilidad del seed transitivo);
el mecanismo admite opcional (null→0.0), pero sembrarlo observable necesitaría extender el seeder (residual, eje aparte).

**3 commits** (codegen · product.yml · docs). El SIGUIENTE incremento abierto: ver el handoff hermano.
