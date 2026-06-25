# Incremento FSK-PUT-UNIQUE-REFS — los flecos del PATCH: PUT de campos UNIQUE (→409) + de refs

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **BACKLOG (no abierto)**.
> RE-PRIORIZADO 2026-06-25: el ingeniero pidió VER la app terminada con sus PANTALLAS → el incremento ABIERTO pasó a
> ser **FSK-FRONTEND-ALL-ENTITIES** (frontend breadth, `…/work/FSK-FRONTEND-ALL-ENTITIES-INCREMENT.md`). Este eje
> (los flecos del PATCH backend) sigue siendo un incremento REAL y bien-scopeado — reabrilo cuando toque cerrar la
> fidelidad de edición. Para trabajarlo, flippeá este header a ABIERTO (y asegurate de que no haya otro abierto).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Lo escribió la sesión que cerró
> FSK-PUT-OPTIONAL con MÁS contexto. NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (y por qué es el más BOUNDED)

**FSK-PUT-OPTIONAL (2026-06-25) volvió el PATCH faithful para los campos ESCALARES no-dueño de la entidad-con-dueño**
— pero DEJÓ FUERA, a propósito, dos clases de campo. `_patchable_fields` (en `codegen/scaffold_product.py`) excluye
hoy: el dueño, los computed, los **UNIQUE**, los **ref**, y los de workflow. Los dos primeros y el último son
exclusiones CORRECTAS y permanentes (el dueño se fija al crear; un computed es read-only; el workflow se mueve por sus
verbos). **Pero UNIQUE y ref son flecos honestos**: en Snipe-IT editás el `asset_tag` (UNIQUE) y reasignás el
`supplier_id`/`location_id` (refs) de un activo. Cerrar ESTOS dos vuelve la EDICIÓN **completa**.

**Es el más ACOTADO de lo restante**: NO inventa arquitectura — es ENSANCHAR `_patchable_fields` + decidir dos códigos
de error (UNIQUE chocado → 409; ref colgante → 409), reusando el `catch_fk`/`conflict()` que YA existe para el POST
(FSK-REFS-IN-BODY). Sin infra nueva (codegen + la PG que ya levantan s9/s11).

**⚠️ ESTA ES TU DECISIÓN (con más contexto).** Lo elegí como el cierre natural del eje EDICIÓN. En §7 hay
alternativas con AUTORIDAD para reabrir si preferís otro orden (cerrar el eje DEPLOY con push-a-registry, o
domain-breadth con Kits, o auditar `restore`/ownerless — todas legítimas).

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥600000ms** (el sandbox mata
gradle). **cwd de Bash SIEMPRE en la RAÍZ** (`cd <raíz> && …`; un `cd` a un subdir filtra el cwd persistente →
deadlock del hook `stop_proof`). Debe dar **PASS**, RTM snipeit **25/26** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **Puertos vivos**: s9 PG 5436/5437/5438 + servers 18593-18595/18597; s11 18596/18598 + PG en `fsk_s11_net`.
NUNCA dos corridas en paralelo (nombres de contenedor FIJOS). Para un diente VIVO manual usá puertos distintos
(p.ej. PG 5446 / AppServer 18599) — FSK-PUT-OPTIONAL dejó `scratchpad/verify_put.sh` + `eyeball_put.py` como molde.

**2) ENTENDÉ lo que FSK-PUT-OPTIONAL ya construyó** (TODO en `codegen/scaffold_product.py`; verificá anchors con grep):
- **`_patchable_fields(e)`** (grep `def _patchable_fields`): hoy `f["type"] != "ref" and not f.get("unique") and …`.
  El eje QUITA esos dos filtros (o los hace condicionales) → un UNIQUE y un ref entran al `<E>Patch`.
- **`_mutation_fns` → `update<E>`** (grep `fun update{name}(`): el set DINÁMICO `Map<org.jooq.Field<*>, Any?>`. Un
  UNIQUE escalar entra IGUAL (es un `.set(COL, value)` más). Un **ref** entra como `Long` (la sub-columna `_id`); un
  ref colgante → la FK falla → `DataAccessException`. ⚠️ Un **ref poly** updatable = 2 sub-columnas (mirá
  `_poly_subfields`/`_owner_poly`): el eje PUEDE diferir el ref poly (sólo refs SIMPLES no-dueño primero) — decisión
  tuya, declarala.
- **`parse<E>Patch`** (grep `def _patch_parse_fn`): usa `_coerce_expr` (compartido). Un UNIQUE string ya coerce con
  `str`; un ref ya coerce con `longOf` (el codec emite `longOf` si hay un ref en `_input_cols`, PERO si el ÚNICO ref
  updatable no está en el POST, asegurate de que el tipo `ref` entre a la UNIÓN del codec — `_codec_helpers` ya
  recibe los campos del patch vía el parámetro `patch`, así que `longOf` se emite. VERIFICALO en el eyeball).
- **`doPut` + `conflict()`** (grep `def _app_server_handlers`, bloque `if patch_fields:`): hoy el update va directo.
  El eje: envolver el `update<E>` en `runCatching { … } ?: conflict()` (UNIQUE chocado / ref colgante →
  `DataAccessException` → 409), EXACTO al patrón del POST ownerless con `catch_fk`. ⚠️ `need_conflict` ya es True
  cuando hay refs requeridos (grep `need_conflict =`); con el PATCH de UNIQUE/ref puede necesitar forzarse True (el
  owned con un UNIQUE/ref updatable). Mirá que `conflict()`/`HTTP_CONFLICT` se EMITAN (si no → no compila).
- **El diente** (grep `def _access_control_check_py`, el bloque `[patch]`, `PUT_BODY`/`PATCH_BAD`): hoy postea
  escalares no-unique. El eje SUMA: (a) PUT `{<unique>: <valor nuevo único>}` → 200 → GET lo ve; (b) PUT `{<unique>:
  <valor YA EXISTENTE>}` → **409** (chocá contra la fila sembrada — el server expone su valor por /seed o usá el del
  POST previo); (c) PUT `{<ref>: <id válido de /seed>}` → 200 → GET ve el id nuevo; (d) PUT `{<ref>: 999999}` → **409**.

**3) EL DISEÑO (GENERAL, cero nombres de dominio):**
   - El blueprint NO necesita flag nueva (ensancha el comportamiento del PUT existente). Opt-in natural: una entidad
     sin UNIQUE/ref updatable → byte-idéntico (el `<E>Patch` no gana esos campos). ⚠️ **MIDE PRIMERO con el eyeball**:
     ¿default/assets ganan un UNIQUE/ref updatable? (assets `Asset.serial` es UNIQUE → su PATCH cambia; default
     `Project` no tiene UNIQUE escalar pero `budget` ya entra.) base/assets NO byte-idénticos pero == pin (generality).
   - **UNIQUE chocado → 409** (no 500, no 200 que traga); **ref colgante → 409**. Mismo `conflict()` del POST.
   - El UPDATE sigue detrás del MISMO `modifyVerdict` + COMPONE FSK-ACTIONLOG (el `"update"` atómico).

**EL DIENTE de dos lados (VIVO contra el AppServer + PG real):**
   - **Verde**: PUT `{unique: nuevo}` / `{ref: id válido}` → 200 → GET lo ve.
   - **Negativo**: PUT `{unique: valor existente}` → 409; PUT `{ref: 999999}` → 409. Saboteá el `runCatching` del
     update (que NO atrape → 500, o que trague → 200) → SÓLO ese assert rojo, hermanos verdes → revertí → verde.

---

## 1. RE-PIN — byte-neutro (igual que FSK-PUT-OPTIONAL)
`compute_proof_sha` hashea `station_id + sorted (check_name, exit)`. El diente vive DENTRO de `access_control_live`
de s9 (ya ejercita el PUT) → **NO agregás check → proof_sha byte-neutro → NO re-pin**. base/assets/snipeit cambian
su artefacto (ganan la maquinaria UNIQUE/ref) pero re-derivan == su pin (la gate `generality` lo sanciona, NO el
`==0` literal — memoria `anti-overfit-is-generality-gate`). Si por aislamiento agregás un check propio → re-pin de
los 3 (editá `factory.spec.yml` Y sincronizá el `stations/<id>.yml` committeado a mano — editar `station_sequence`
re-materializa los PRODUCTOS pero NO el base committeado).

## 2. Lecciones CARAS ya destiladas (de FSK-PUT-OPTIONAL + previas)
- **VALIDÁ BARATO ANTES DE GRADLE** (≈10s): adaptá `scratchpad/eyeball_put.py` (FSK-PUT-OPTIONAL lo dejó — carga el
  scaffold, renderiza los 3 productos en memoria, chequea el `<E>Patch`/`update<E>`/`parse<E>Patch`/`doPut`/el proof
  + 0 Kotlin >160). **Hacelo antes de tocar gradle.** Confirmá que `longOf`/`conflict()` se emitan para snipeit.
- **El diente VIVO se corre MANUAL y RÁPIDO** contra la dist viva: PG en docker (`postgres@sha256:e013e8…` cacheada)
  + el AppServer por `java -cp 'build/install/snipeit/lib/*' snipeit.endpoints.AppServerKt` con
  `FSK_PG_URL`/`FSK_AC_PORT`/`FSK_NOW=2030-07-15` (el oráculo `[computed]` está pineado a ESA fecha). Esperá `/health`
  con `curl --retry 60 --retry-connrefused`. **`infra_up` NO surfacea el stdout del proof** → corré el proof MANUAL.
  FSK-PUT-OPTIONAL dejó `scratchpad/verify_put.sh` (wired|sabotage|revert|clean, PG 5446 / AppServer 18599) como molde.
- **El sabotaje runtime NO debe romper lo estático** (degradá lógica/SQL, no Kotlin). Rebuild con
  `./gradlew installDist -q --console=plain` en `build/product` (el `increment_guard` BLOQUEA Edit sobre rutas
  `build/` de un producto → saboteá con `sed`, no con Edit). `ci --rederive` regenera la dist = revierte el sabotaje.
- **ktlint/detekt al escalar** (cada eje mordió uno): MaxLineLength 160 · PropertyWrapping >120 (un `val x=<expr>`
  largo se envuelve) · NoMultipleSpaces · MagicNumber (literal 3+) · ReturnCount≤2 · CyclomaticComplexMethod≤15 ·
  LongMethod≤60 · @Suppress(LargeClass) si >600. El `update<E>` con un `runCatching` puede empujar `doPut` — @Suppress
  por TAMAÑO opt-in, no a mano.
- **`ci --rederive` opera sobre el ÁRBOL DE TRABAJO** (borra `.proof/`+`build/`, re-deriva in-place). UNO A UNO
  (<10min) o `--all-products`. **Delegá las corridas pesadas (base+assets) a un subagente Sonnet** — pero escribí el
  codegen + el diente con TUS ojos. **proof_protect DENIEGA tocar `.proof/` por shell** → `meta rtm`.

## 3. Disciplina (ADR-016/ADR-010)
- El codegen es nivel FÁBRICA → ESTE incremento (header ABIERTO). El eje NO necesita tocar `product.yml` (es
  comportamiento general) → probablemente NO necesitás incremento de PRODUCTO. Si tocás `products/snipeit/product.yml`,
  abrí `meta increment open … --product snipeit <slug>` ANTES.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` con el incremento ABIERTO, luego `docs(fsk): cerrar
  FSK-PUT-UNIQUE-REFS (§Evidencia) + abrir <siguiente>` flippeando el header a CERRADO.

## 4. Criterio de cierre (demostrable, no narrable)
1. El `PUT /<plural>/{id}` actualiza también campos UNIQUE y refs (simples no-dueño); UNIQUE chocado → 409, ref
   colgante → 409; type-coerced. `product-run --product snipeit` **PASS**.
2. **Diente de DOS lados verificado VIVO**: PUT unique-nuevo / ref-válido → 200 + GET lo ve; PUT unique-existente /
   ref-colgante → 409; saboteá el atrape → SÓLO ese assert rojo, hermanos verdes → revertí → verde.
3. EYEBALL · (re-pin SÓLO si check nuevo) · `ci --rederive` por producto == pin · `meta check` 6/6 (`generality`
   verde) · `git diff src/metafactory + seed = 0`.
4. STATE/LOG (fábrica) + SNIPEIT-DOMAIN (item 24/25) actualizados. Abrí el SIGUIENTE con su handoff (§7).

## 5. Restricciones que SIGUEN vigentes tras este eje
- **PUT/update de entidades OWNERLESS** (hoy sólo la entidad-con-dueño se monta con PUT) — eje hermano.
- **auditar `restore` + ownerless** (heredado de FSK-ACTIONLOG: hoy sólo audita la entidad-con-dueño servida).
- **push de la imagen a un registry** — el ÚLTIMO diferido DURO de DEPLOY (⚠️ requiere `registry:2` cacheado para
  que `ci --rederive` sea offline — verificá ESO primero). Cierra el ciclo.
- **Kits (bundles)** — un Kit agrupa assets/accesorios/licencias que se checkout-ean juntos. COMPONE FSK-CREATES-PIVOT.
- **EAV dinámico (Avenue B)** — custom-fields a RUNTIME (vs el schema build-time jOOQ). Cambio de ARQUITECTURA, el
  de mayor esfuerzo.
- el largo tail de ~226 rutas operacionales no-dominio (counters, image-upload, LDAP, 2FA).

## 6. ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El backend faithful (modelo·acceso·comportamiento·valores-derivados incl. tiempo), la app CORRE, TODAS las
entidades se sirven, el frontend se VE y se SUBMITEA en un navegador REAL, DEPLOYA DE VERDAD, AUDITA cada mutación, y
la EDICIÓN de campos escalares es faithful.** Tras UNIQUE/refs, la edición es COMPLETA. Lo que RESTA es breadth de
dominio (PUT-ownerless, Kits, el tail no-dominio) + diferidos de red/arquitectura (push a registry, EAV dinámico).
**No queda ningún hueco de NÚCLEO, SUPERFICIE, VALORES-DERIVADOS, UX, DEPLOY, AUDITORÍA ni EDICIÓN-escalar.**

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE (con AUTORIDAD para reabrir)
Si al investigar preferís otro eje (cualquiera es legítimo; reabrí con `meta increment`):
- **FSK-PUT-OWNERLESS** — montar PUT/update sobre las entidades ownerless/serve-all (hoy sólo la con-dueño). Domain
  breadth, compone FSK-SERVE-ALL-ENTITIES.
- **FSK-AUDIT-RESTORE-OWNERLESS** — cerrar el diferido de FSK-ACTIONLOG (auditar `restore` + ownerless). Bajo costo.
- **FSK-DEPLOY-PUSH-REGISTRY** — cierra el eje DEPLOY (⚠️ verificá `registry:2` cacheado ANTES). Mayor "cierre de axis".
- **FSK-KITS** — bundles (M:N agrupado), domain breadth, compone FSK-CREATES-PIVOT.
- **EAV dinámico** — el de mayor esfuerzo/riesgo (cambio de arquitectura).
