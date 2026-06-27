<!-- meta:doc sha=3dc61031f98c75216a6fa9321171a886ea2cae89 updated=2026-06-27T01:41Z -->
# Incremento FSK-OWNER-POLY — el `owned_by` de una entidad es un ref POLIMÓRFICO (el owner cruza una UNIÓN, wrinkle #3)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-23T19:45Z · cerrado 2026-06-24T00:30Z). Evidencia de cierre en §Evidencia (abajo).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-CREATES-PIVOT con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## ✅ Evidencia de cierre (2026-06-24, demostrable, no narrable)

**El `owned_by` puede ser un ref POLIMÓRFICO — el dueño cruza una UNIÓN (tipo, id), wrinkle #3 CERRADO.** Camino
BOUNDED REALIZADO (incluso más limpio que el §★ sugería): en vez de agregar un param a `canModify`, el gating vive
en `modifyVerdict` como **`effectiveOwnerId = (ownerType == targets[0]) ? ownerId : null`** → un owner de tipo
NO-principal ≡ owner NULL → cae al branch owner-NULL de FSK-OWNERSHIP-OPTIONAL → **`OwnershipGuard.canModify` (Long?)
queda INTACTO**. Compone ownership-optional + poly, cero modelo nuevo de auth.

**Decisión clave (con más contexto): NO se fusionó `assigned_to`↔`checkout_target`.** El bloque de operaciones del
proof POSTea una fila propiedad del actor y hace checkout→checkin **por el dueño**; si `checkout` reasignara el
`owned_by`, el dueño cambiaría a `(User, 7)` → el checkin posterior por el dueño daría 403 (no 200) y el re-apply
409→403 → ROMPERÍA el proof de operaciones. Además es más HONESTO: en Snipe-IT el editor de un activo ≠ su holder
(managers/admins editan, no el asignado). → `assigned_to` ES el owner-poly; `checkout_target` + las operaciones
quedan intactas.

**Cambios (todo `codegen/scaffold_product.py`, FÁBRICA, GENERAL, opt-in byte-neutro):** helper `_owner_poly` ·
gramática (levanta la restricción wrinkle #3) · `_repository_kt` (`<e>OwnerId` lee `<owner>_id` + nuevo `<e>OwnerType`
lee `<owner>_type`) · `_modify_verdict_kt` (params `owner_type_fn`/`principal_entity`; lee tipo, gatea id) ·
`_mutation_fns` (el POST fija `type=targets[0]`, `id=ownerId`) · `_seed_chain` (param `owner_poly_type`; la fila del
dueño = `(User, ownerId)`, la 2ª = `(Location, ownerId)` — **mismo id, distinto tipo = el diente**) · el seed de
`scopedId` (company-scope) también pasa `owner_poly_type` · `_test_ownership_guard_kt` (cruza `<owner>_id` Long?) ·
`_app_server_kt` (resuelve `to` poly → `targets[0]`, wirea todo) · `build_files` (`owner_optional` incluye poly).

**Adopción PRODUCTO** (`products/snipeit/product.yml`, incremento `OWNER-POLY-ADOPT`): `Asset.assigned_user_id` →
`assigned_to` poly `[User, Location, Asset]`, sigue siendo `owned_by`.

**Verde por BLOQUEO:**
- **EYEBALL byte-neutro**: con el scaffold NUEVO y `product.yml` sin cambiar, los 3 productos byte-IDÉNTICOS a HEAD
  (0 diffs) → el cambio es puro opt-in. Tras la adopción: base/assets **byte-idénticos**, snipeit con el diff esperado.
- **product-run --product snipeit PASS** · **RTM snipeit 24/25** (único UNSAT = REQ-F-007/s6 LLM keyless, deferral VISIBLE).
- **Diente de DOS lados VIVO y PRECISO** (proof manual sobre el server real + PG): degradé el gate de tipo
  (`ownerType == "User"` → `ownerType != "__never__"`, neutralizado pero `ownerType` SIGUE usado → COMPILA, sin
  hallazgo estático) → la fila asignada a una Location se vuelve "del actor" → **"PUT fila RTD por no-bypass → 403"
  se vuelve 200 (ROJO)**, con `health → 200` (server VIVO = es MI aserción) y TODAS las hermanas (dueño-principal,
  bypass, ajena, ops, qty, creates) VERDES → sabotaje quirúrgico → revertí → verde.
- **`ci --rederive` base + assets + snipeit == pin** (clones limpios, SIN re-pin — `proof_sha` intacto, `pinned_verdict.json`
  sin cambios) · **`meta check` 6/6** (generality verde) · **`git diff src/metafactory + seed = 0`** · default/assets
  `product.yml = 0`.

**El NÚCLEO FUNCIONAL + BEHAVIORAL + de MODELO/AUTH faithful está COMPLETO.** Lo que resta es BREADTH y
PROFUNDIDAD-de-detalle. Siguiente abierto: **FSK-XENTITY-DEPTH2** (ver `docs/work/FSK-XENTITY-DEPTH2-INCREMENT.md`).

---

### Handoff original (referencia histórica — el diseño que esta sesión ejecutó)

---

## 0. POR QUÉ este incremento (y por qué es DECISIÓN tuya)

**El NÚCLEO FUNCIONAL + BEHAVIORAL faithful está COMPLETO** (cerrado en FSK-CREATES-PIVOT, 2026-06-23): modelo de datos
(CRUD del grafo · self-ref · ownership opcional/RTD · refs requeridos transitivos · ciclos cross-entidad · **ref
polimórfico** · checkout polimórfico) · acceso (auth→RBAC→ownership→company-scope) · comportamiento (workflow ·
qty/stock · trash/restore · **insert-on-verb / pivote M:N**) · valores derivados (computado same+cross-entity) · app que
CORRE. **Lo que resta es BREADTH y PROFUNDIDAD-de-detalle** — los flecos, no el corazón.

**Este incremento ataca el ÚLTIMO GAP genuino de MODELO+AUTH: el wrinkle #3 — un `owned_by` POLIMÓRFICO.** Hoy el dueño
de una fila cruza un `Long` ÚNICO (el principal del token == `row.owner_id`). Por eso, en Snipe-IT, el polimórfico vivió
SIEMPRE en un campo NO-dueño (`Asset.checkout_target` ≠ `Asset.assigned_user_id`). Pero en Snipe-IT REAL `assigned_to` ES
el owner Y es polimórfico (`User | Location | Asset`): un activo puede estar asignado a un usuario, a una ubicación o a
otro activo. Este eje hace que `owned_by` pueda ser un ref polimórfico → el OwnershipGuard cruza **(tipo, id)** en vez de
un Long.

**⚠️ ES EL EJE MÁS INVASIVO** (toca el CORE de auth: `OwnershipGuard.canModify` · `OwnershipPolicy` · `modifyVerdict` ·
`OwnershipGuardTest` · `route_check ownership`). PERO hay un camino BOUNDED limpio (§★) que COMPONE dos primitivas YA
probadas — **FSK-OWNERSHIP-OPTIONAL** (un dueño NULL → sólo bypass) + **FSK-POLYMORPHIC-REFS** (el ref de 2 columnas) —
con la observación clave: **un owner de tipo NO-principal (Location/Asset) se comporta EXACTO como un owner NULL** (no hay
principal contra quien cruzar → sólo un rol de bypass modifica). Cero modelo nuevo de auth.

**⚠️⚠️ ESTA ES TU DECISIÓN (con más contexto).** Si al investigar decidís que owner-poly NO es el mejor próximo,
alternativas honestas, BIEN framed, en §7 (**cross-entity DEPTH-2** — más bounded, menos riesgo; **breadth pura** — el
producto "se siente real"). Tenés autoridad para reabrir con `meta increment` — pero leé los wrinkles ANTES.

### 0.1 LOS WRINKLES
1. **¿Qué target es "el principal"?** El principal del token (`role:principal:company`) es un **id de User** (el actor).
   Para un owner poly `[User, Location, Asset]`, la pertenencia por-principal SÓLO aplica cuando `owner_type` == la
   entidad-principal (User). NO hay marca explícita de "entidad-principal" en el blueprint. Camino bounded:
   **convención `targets[0]` = la entidad-principal** (en snipeit `assigned_to`/`assigned_user_id` apunta a User, que ya
   ES el owner no-poly de hoy → `[User, Location, Asset]` con User primero). Documentá la convención. Alternativa más
   explícita (menos mágica): una clave `principal_target: User` en el campo. Sin forma DATA-agnóstica de VERIFICAR cuál
   target es "principal" más allá de la convención — anótalo en el codegen.
2. **owner NO-principal = owner NULL** (la observación que vuelve el eje BOUNDED): cuando `owner_type` ∈ {Location,
   Asset} (no es la entidad-principal), NO hay principal que sea dueño → `canModify` cae al MISMO branch que el owner
   NULL de FSK-OWNERSHIP-OPTIONAL: **sólo un rol de bypass modifica**. Así `canModify(role, principal, ownerType,
   ownerId, bypass)` = `role in bypass || (ownerType == PRINCIPAL_ENTITY && ownerId == principal)`.
3. **La gramática HOY PROHÍBE poly en `owned_by`** (`_load_blueprint`, ~líneas 374-377: «el campo `owned_by` no puede
   ser polimórfico … wrinkle #3»). Este eje LEVANTA esa restricción de forma controlada (no la borra: la cambia por
   «si owned_by es poly, compone ownership-optional + 2 columnas»). Un owner poly SIEMPRE es como un owner-optional
   (puede ser no-principal → sin principal-dueño) → el server lo trata como `owner_optional`.
4. **modifyVerdict carga (tipo, id), no un Long**: `<e>OwnerId` hoy lee `OWNER_ID` (Long?); con poly hay que leer
   TAMBIÉN `OWNER_TYPE` (String?). El verdict cruza ambos. El `route_check ownership` cruza `x-owned-by` del contrato
   contra `OwnershipPolicy` — con poly, `owned_by` nombra el campo lógico (no las 2 columnas); lo más limpio es que el
   contrato exponga `x-owned-by: assigned_to` (el campo) y la Policy mapee a las 2 columnas.
5. **El POST fija el dueño al creador** (restricción #3 del blueprint FSK): `_mutation_fns` setea `set(OWNER, ownerId)`.
   Con poly, el creador es un User → `set(OWNER_TYPE, "User").set(OWNER_ID, ownerId)`. Una fila creada por su dueño
   round-trippea bajo ownership (tipo User); la 2ª fila (RTD / asignada a Location) la siembra el server (no el POST).

**Conclusión honesta**: el camino BOUNDED — **`owned_by` puede ser poly → 2 columnas (`<f>_type`/`<f>_id`); el
OwnershipGuard.canModify gana `ownerType` y matchea por-principal SÓLO si `ownerType == targets[0]` (la entidad-principal),
si no cae a bypass-only (= el branch owner-NULL de FSK-OWNERSHIP-OPTIONAL); modifyVerdict carga ambas columnas; el POST
fija (type=targets[0], id=principal)**. Adopción faithful: `Asset.assigned_user_id` se vuelve `assigned_to` poly
`[User, Location, Asset]` y ES el `owned_by` (cierra wrinkle #3) — y el `checkout_target` de FSK-POLY-ASSIGNS se FUSIONA
con él (ya no hacen falta dos campos poly).

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
- **Gramática** (`_load_blueprint`, ~374-377): permitir `owned_by` poly; fail-closed: el campo poly del `owned_by` es
  válido (≥2 targets, `_is_poly`) y se trata SIEMPRE como owner-optional.
- **`owner_optional`** (`build_files`, ~6488): hoy `any(not <owned_by>.required for e in owned)`. Sumá: **un `owned_by`
  poly ⟹ owner_optional True** (un owner no-principal no tiene principal → como NULL).
- **`OwnershipGuard.canModify`** (`_ownership_guard_kt`): variante poly → firma `(role, principal, ownerType: String?,
  ownerId: Long?, bypass)`; body `role in bypass || (ownerType == "<PRINCIPAL_ENTITY>" && ownerId == principal)`. El
  `PRINCIPAL_ENTITY` = `targets[0]`. Sin poly, byte-idéntico (cuidá ReturnCount ≤ 2 — ya está al límite).
- **`modifyVerdict`** (`_modify_verdict_kt`) + **`<e>OwnerId`/`<e>OwnerType`** (`_repository_kt`): cargá las 2 columnas;
  pasá ambas a canModify. Reusá el patrón owner-optional (existencia separada del dueño).
- **`_mutation_fns`** (el POST): `set(OWNER_TYPE, "<PRINCIPAL_ENTITY>").set(OWNER_ID, ownerId)`.
- **El seeder** (`_app_server_kt` seed): siembra la fila del dueño (type=principal-entity) + una 2ª fila RTD/no-principal
  (type=Location, otro id) para el diente bypass-only. /seed expone ambas.
- **El proof** (`access_control_check.py`): el diente de DOS lados — (a) la fila asignada al actor (type=User,
  id=principal) → el actor la modifica (200); otro principal → 403; (b) la fila asignada a una Location (no-principal) →
  el actor NO la modifica (403), sólo bypass (200). Degradar el match de `ownerType` → un no-principal se vuelve
  modificable → SÓLO `access_control_live` (s9) rojo.

**EL DIENTE de dos lados**: una fila owned por (User, principal) → el actor modifica (200) / otro principal → 403; una
fila owned por (Location, x) → sólo bypass (200), el actor → 403. Degradá `canModify` (p.ej. ignorar `ownerType`,
tratar todo como principal) → un owner Location se vuelve "del actor" → 403 esperado se vuelve 200 → **SÓLO** s9 rojo,
hermanos + s0–s8 verdes → revertí → verde. ⚠️ El sabotaje debe degradar la LÓGICA, no la forma Kotlin (mantené los
params usados para no tripear `-Werror`).

---

## 1. ⚠️ RE-PIN — probablemente NO hace falta
El cambio vive DENTRO de `access_control_live` (s9) y de los guards/tests unit YA existentes, SIN check/estación nuevos
→ `proof_sha` INTACTO → pines byte-idénticos. `git diff snipeit/product.yml ≠ 0` ESPERADO; el sustrato + default/assets
product.yml DEBEN quedar en 0. (Si tocaras `OwnershipGuardTest`/`route_check` de forma que cambie la ESTRUCTURA de
checks, re-evaluá — pero el camino bounded reusa los checks existentes.) Co-validá que `OwnershipGuardTest` (unit, s7) y
`route_check ownership` (s5) sigan verdes con la firma poly.

## 2. Maquinaria a REUTILIZAR — TODO en `codegen/scaffold_product.py` (verificá los anchors con grep)
- **FSK-OWNERSHIP-OPTIONAL**: `_ownership_guard_kt(owner_optional=True)` (la firma `Long?` + el branch bypass-only del
  owner NULL) · `_modify_verdict_kt(owner_optional)` (existencia separada del dueño) · el `owner_optional` de `build_files`.
- **FSK-POLYMORPHIC-REFS**: `_is_poly` · `_poly_subfields` (las 2 columnas `<f>_type`/`<f>_id`) · `_cols_of` (ya expande
  poly) · el `enumOf` del discriminador (set CERRADO de targets) · `_row_json_fn` (serializa las 2 sub-columnas).
- **FSK-POLY-ASSIGNS**: cómo un verbo ya setea `<campo>_type`+`<campo>_id` (mismo idiom para el POST del owner).
- **OwnershipPolicy / route_check ownership**: `_ownership_policy_kt` (`<E> → <owned_by>` campo lógico) · `route_check.py`
  modo ownership (cruza `x-owned-by` del contrato vs la Policy por tokens).

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **EYEBALL SIN gradle ANTES de cada corrida lenta**: hay un `eyeball.py` reutilizable en el scratchpad de la sesión
  anterior (carga el scaffold HEAD vs working con `importlib`, llama `build_files(bp)` para base/assets/snipeit y diffea
  byte a byte usando `products/<p>/factory.spec.yml` ya materializado). Lo nuevo va OPT-IN (sin poly en owned_by →
  byte-idéntico); NUNCA cambies un comentario/constante INCONDICIONALMENTE. Tras tocar product.yml, RE-MATERIALIZÁ el
  spec efectivo: `python3 -c "import metafactory.cli as c, pathlib; c.ensure_product_instance(pathlib.Path('factories/full-stack-kotlin'), pathlib.Path('factories/full-stack-kotlin/products/snipeit'), pathlib.Path('.'), 'snipeit')"`.
- **Un sabotaje que muerde a RUNTIME no puede meter un hallazgo ESTÁTICO antes.** Degradá la LÓGICA, no la forma.
  **ktlint MaxLineLength=160 (firmas largas → wrap); `NoMultipleSpaces`; detekt LongMethod ≤ 60, CyclomaticComplexMethod
  ≤ 15, ReturnCount ≤ 2 (canModify ya está al límite — cuidá no pasarte), MagicNumber ignora -1/0/1/2; NoUnusedImports +
  -Werror (un param sin usar → rojo); StringTemplate sin llaves sobre un identificador simple; jOOQ tipa toda columna
  NULLABLE.** Un `@Suppress` sobre una declaración necesita una línea EN BLANCO antes (SpacingBetweenDeclarations…).
- **com.sun.net.httpserver NO loguea la excepción de un handler** (cierra la conexión). Si s9 cae: chequeá los HERMANOS
  (`observability_live`/`frontend_consume_live`) — VERDES ⟹ el server vive, es TU aserción; TODOS rojos ⟹ el server
  crashea (reproducí MANUALMENTE: `docker run … postgres@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb`
  PG 5438 + `java -cp build/install/snipeit/lib/* snipeit.endpoints.AppServerKt` + curl).
- **`proof_protect` DENIEGA tocar `.proof/` por shell** — el **Read tool SÍ** lee `.proof/logs/` (son RESÚMENES).
- **`ci --rederive` por producto**: `--product snipeit`/`--product assets` y SIN `--product` (la base). UNO A UNO en
  foreground (< 10 min c/u). `meta check` es el self-check del meta (RÁPIDO, NO re-deriva productos).
- **Diente más limpio = un valor escalar equivocado a 200** (no un crash/409): para owner-poly, degradá el MATCH de
  `ownerType` (la fila Location se vuelve "del actor") → 403→200, server VIVO. Mantené los params usados (sin `-Werror`).

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento, breadth)
**cross-entity DEPTH-2** (Asset→AssetModel→Depreciation.months) + **time-elapsed** · **EAV dinámico a runtime**
(custom-fields Avenue B) · **PUT de campos OPCIONALES arbitrarios** · **e2e Playwright / browser real** ·
**AppServer-en-contenedor con PG** (s11 hoy usa el ObsServer PG-free) · **Actionlog (auditoría polimórfica)** · **Kits
(bundles)** · **las ~226 rutas**.

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py` + quizá spec/stations si la grama nueva necesita validación M0) es nivel FÁBRICA
  → **este incremento** lo cubre (header ABIERTO).
- **La adopción** (`products/snipeit/product.yml`: `assigned_user_id` → `assigned_to` poly = `owned_by`) es nivel PRODUCTO
  → abrí TAMBIÉN `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) + `feat(snipeit): …` (product.yml) + `docs(fsk): cerrar
  FSK-OWNER-POLY (§Evidencia) + abrir <siguiente>`. **Commiteá el CÓDIGO mientras el incremento está ABIERTO**, luego
  flipeá el header a CERRADO en el commit de docs.
- **Probá POR BLOQUEO**: EYEBALL byte-neutro · `product-run --product snipeit` PASS · diente de dos lados vivo (sólo
  s9) · `ci --rederive` (base + assets + snipeit) == pin (los 3) · `meta check` 6/6 (`generality` verde) · `git diff
  src/metafactory + seed = 0` · default+assets product.yml = 0.

## 6. Criterio de cierre (demostrable, no narrable)
1. `owned_by` puede ser un ref POLIMÓRFICO y `product-run --product snipeit` **PASS** — el server vivo (s9): una fila
   owned por (User, principal) la modifica su dueño (200) / otro principal → 403; una fila owned por una entidad
   NO-principal (Location) → sólo bypass (200), el actor no-bypass → 403.
2. **Diente de DOS lados verificado VIVO**: degradá el match de `ownerType` en `canModify` → un owner no-principal se
   vuelve modificable por el actor → ROJO **sólo** en `access_control_live` (s9) → revertí → verde.
3. EYEBALL byte-neutro · `ci --rederive` (base + assets + snipeit) == pin · `meta check` 6/6 · `git diff src/metafactory
   + seed = 0` · default+assets product.yml = 0.
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md` (cierra wrinkle #3) actualizados. Abrí el SIGUIENTE con su handoff (§7).

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE
Si al investigar decidís que owner-poly NO es el mejor próximo (es tu decisión con más contexto):
- **Cross-entity DEPTH-2** (extiende FSK-XENTITY-COMPUTED; **el más BOUNDED, menos riesgo**): la fórmula resuelve una
  CADENA de refs `<ref1>.<ref2>.<campo>` (Asset→AssetModel→`depreciation_id`→Depreciation.months) — un JOIN encadenado.
  Hoy depth-1 (`model_id.depreciation_months`) ya anda; el período REAL vive en `Depreciation` vía
  `AssetModel.depreciation_id` (deferral 13 de SNIPEIT-DOMAIN). Diente limpísimo (el valor computado cruza depth-2). Si
  querés un eje de BAJO riesgo y alto retorno, ESTE es defendible por encima de owner-poly.
- **Breadth pura de superficie** (el producto "se siente real"): servir CRUD de las ~226 rutas (todas las entidades, no
  sólo el subconjunto vivo) · Kits (bundles) · Actionlog (auditoría polimórfica) · EAV dinámico · PUT de campos opcionales
  arbitrarios · e2e Playwright (browser real) · AppServer-en-contenedor con PG (s11). Son los flecos, no el corazón —
  pero es lo que un USUARIO nota al "entrar a la app".

### ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El núcleo funcional + behavioral está COMPLETO** (data + acceso + comportamiento + valores derivados + app que CORRE).
**Owner-poly (este)** cierra el ÚLTIMO gap de MODELO+AUTH (wrinkle #3). Tras él, lo que resta (cross-entity depth-2, las
~226 rutas, Kits, Actionlog, EAV, PUT-opcionales, Playwright, AppServer-en-contenedor) es trabajo de BREADTH y de
PROFUNDIDAD-de-detalle — los flecos, no el corazón. El backend faithful está, en lo esencial, terminado.
