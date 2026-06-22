# Incremento FSK-OWNERSHIP-OPTIONAL — dueño NULLABLE / estado RTD (Ready-To-Deploy) real → el push Snipe-IT

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-22T01:56Z · cerrado 2026-06-22T03:11Z). Evidencia abajo (§Evidencia).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-SELF-REF con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (la decisión estratégica)

**FSK está MADURO** (genera→prueba e2e→CRUD del grafo entero bajo control de acceso→UI usable→deploya). El trabajo es
ahora **product-driven**: construir Snipe-IT trabajando sus **12 deferrals** (`products/snipeit/docs/reference/
SNIPEIT-DOMAIN.md §3`), cada uno forzado por un caso REAL del producto. Ya cerrados por el push: CRUD-mutación
(FSK-S16/body/ownerless/refs), frontend que consume+renderiza, deploy vivo, y **self-ref** (FSK-SELF-REF, el hermano
inmediatamente anterior — leé `docs/work/FSK-SELF-REF-INCREMENT.md §Evidencia`).

**Este = deferrals 3 + 4 (ownership-opcional / RTD), el SIGUIENTE por ser el más CORE de Snipe-IT**: en Snipe-IT un
activo **Ready-To-Deploy está SIN asignar (dueño NULO)** — es el caso NORMAL, no un borde. Hoy el blueprint MIENTE:
`Asset.owned_by: assigned_user_id` está forzado a `required: true` (todo activo tiene dueño obligatorio) porque FSK no
soporta dueño nullable. Es la infidelidad más visible que queda. **Pero es MÁS INVOLUCRADO que self-ref** (toca el
guard de ownership + el server vivo + el seed), por eso va después del self-ref (que era "chico y acotado").

**Hermano YA cerrado (de dónde venís):** FSK-SELF-REF restauró jerarquías self-ref (Location.parent_id,
User.manager_id) con un fix GENERAL del codegen. Lección clave de ahí: **un gap "chico" del handoff (1 función) tocó
3 sitios del codegen** — generar de verdad (gradle) es lo que encuentra los huecos, no el eyeball. Esperá lo mismo acá.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso: la línea entera s0→s11, con self-ref pero dueño aún obligatorio):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez** (el sandbox de Bash mata gradle: exit 144).
**Mantené el cwd de Bash en la RAÍZ del repo** (un `cd` a un subdir filtra el cwd persistente → deadlock del hook
`stop_proof` al cerrar el turno; si te pasa, `cd` de vuelta a la raíz). Debe dar **PASS**. RTM snipeit **24/25** (único
UNSAT = REQ-F-007/s6 LLM keyless). ⚠️⚠️ **s7 PG en 5435 · s9 puertos FIJOS 18593-18595 · s11 18596** → NUNCA dos
corridas en paralelo, NUNCA dejes un `product-run`/`ci` en BACKGROUND al cerrar el turno (el hook `stop_proof` RE-CORRE
la estación activa → colisión de puerto → falso rojo). FOREGROUND (timeout ≥540000ms), dejá terminar ANTES de cerrar.

**2) Entendé el gap EXACTO** (la maquinaria de ownership vive en `codegen/scaffold_product.py`):
- **`OwnershipGuard.canModify`** (`_ownership_guard_kt`, ~L1840): hoy `canModify(actorRole: Role, actorPrincipalId:
  Long, rowOwnerId: Long, bypass: Set<Role>): Boolean = actorRole in bypass || actorPrincipalId == rowOwnerId`. El
  `rowOwnerId: Long` es **NO-NULLABLE** → no puede expresar "fila sin dueño".
- **El server vivo `modifyVerdict`** (`_appserver_kt`, ~L3725) es donde está **la CONFLACIÓN owner-null/404**:
  ```kotlin
  val ownerId = if (authorized) Repository.<e>OwnerId(ctx, id) else null
  return when {
      !authorized -> 403
      ownerId == null -> 404         // ← BUG para RTD: "fila inexistente" Y "fila existente sin dueño" caen acá
      ...canModify(role, principal, ownerId, bypass) -> 200
      else -> 403
  }
  ```
  `<e>OwnerId` (`_row_owner...`, ~L1140) hace `fetchOne` de la columna dueño → devuelve `null` si la fila NO existe
  **o** si la columna dueño ES null. Con dueño REQUERIDO (hoy) la columna nunca es null ⇒ `null ⟺ no-existe ⟺ 404`
  correcto. Con dueño OPCIONAL, una fila RTD existente (dueño null) devolvería **404** — MAL (la fila existe).
- **El blueprint** (`products/snipeit/product.yml`): `Asset` tiene `owned_by: assigned_user_id` y el campo
  `{ name: assigned_user_id, type: ref, to: User, required: true }` (forzado por la restricción #2/#3 del header del
  archivo). Ver también **deferral 4**: `Asset.model_id` está `required: false` aunque Snipe-IT lo exige, por la
  restricción de seed del server vivo (FSK-S15 prohíbe refs REQUERIDOS no-dueño en la entidad-con-dueño).

**3) EL DISEÑO (resolvelo GENERAL, cero nombres de dominio — `generality` verde es el anti-overfit real):**
- **`canModify`** acepta `rowOwnerId: Long?`: `actorRole in bypass || (rowOwnerId != null && actorPrincipalId ==
  rowOwnerId)`. Semántica honesta: una fila SIN dueño (RTD) sólo la modifica un rol de **bypass** (no hay principal
  contra quien cruzar). Opt-in: cambiá la firma **sólo** cuando el `owned_by` de la entidad es `required: false`; con
  dueño requerido, mantené el `Long` no-nullable EXACTO (byte-idéntico → default/assets/proof_sha intactos). **O**
  hacelo `Long?` siempre y comprobá que default/assets re-derivan == pin.
  ⚠️ Cuidado: cambiar la firma SIEMPRE también cambia `OwnershipGuardTest.kt` (s7) y el sample → re-deriva ≠ pin de
  default/assets a menos que el cambio sea byte-neutro. **Recomendado: opt-in por `required` del `owned_by`.**
- **`modifyVerdict`** rompe la conflación: separá EXISTENCIA de DUEÑO. Agregá `Repository.<e>Exists(ctx, id): Boolean`
  (o reusá `<e>RowJson != null`) y:
  ```kotlin
  when {
    !authorized -> 403
    !exists -> 404                 // fila inexistente
    canModify(role, principal, ownerId, bypass) -> 200   // ownerId puede ser null (RTD): sólo bypass pasa
    else -> 403
  }
  ```
  Sólo cuando el `owned_by` es nullable; con dueño requerido, dejá `modifyVerdict` EXACTO (byte-idéntico).
- **El seed del server vivo** (`_seed_chain`/`seedRows`, s9): hoy fija el campo dueño a `ownerId` (el principal
  sembrado). Para probar RTD VIVO necesitás sembrar **una 2ª fila SIN dueño** (owner null) además de la asignada →
  el proof viviente puede aseverar: PUT de la fila RTD por un no-bypass → 403; por bypass → 200. (Esto es el "diente
  de dos lados" del RTD; sin la 2ª fila el tooth es flaco.)
- **Adopción en el producto** (incremento de PRODUCTO aparte, ADR-016, el guard elige por ruta): en
  `products/snipeit/product.yml` flippeá `assigned_user_id` a `required: false` (RTD real) y actualizá el header
  (restricciones #2/#3) + `SNIPEIT-DOMAIN.md §3 deferral 3`. **Deferral 4 (model_id requerido)** es companion: pediría
  **seed transitivo** en el server vivo (sembrar el `AssetModel` requerido) — evaluá si entra en este incremento o se
  difiere a uno propio (probablemente sea su propio incremento; no te sobre-comprometas).

**EL DIENTE de dos lados** (criterio §6.2): con dueño nullable, el `access_control_live` (s9, infra_up vs PG+server
vivo) debe aseverar: (a) fila RTD (dueño null) modificada por un **no-bypass** → **403**; (b) por un **bypass**
(admin) → **200**; (c) fila inexistente → **404** (no confundida con RTD). **Saboteá**: hacé que `modifyVerdict`
devuelva 200 para RTD+no-bypass (o que canModify ignore el null) → el 403 del RTD se vuelve 200 → el proof FALLA →
SÓLO `access_control_live` rojo, hermanos de s9 (`observability_live`/`frontend_consume_live`) verdes. Revertí → verde.

---

## 1. ⚠️ RE-PIN — ¿hace falta?
Si el fix vive DENTRO de los checks existentes (`access_control_live`/s9 + `pyramid_*`/s7, mismos nombres+exit), el
**`proof_sha` queda INTACTO** → pines byte-idénticos, SIN re-materializar, SIN re-pinear (como FSK-SELF-REF). **NO
agregues check/estación nuevos si podés evitarlo.** `git diff snipeit/product.yml ≠ 0` es ESPERADO (trabajo de
producto); el sustrato + default/assets product.yml DEBEN quedar en 0. **Si default/assets re-derivan ≠ pin**, es que
tu cambio de codegen NO fue byte-neutro para ellos → o lo hacés opt-in por `required`, o re-materializás+re-pineás los
3 (lo caro). `proof_sha = sha256({station, sorted(check_name, exit)})` — invariante a qué campos seedea el código.

## 2. Maquinaria a REUTILIZAR (no la reinventes)
- **`_ownership_guard_kt`** (~L1840): la firma de `canModify` a tocar.
- **`_appserver_kt` / `modifyVerdict`** (~L3725): donde está la conflación 404; **`_row_owner...`** (~L1140) el
  `<e>OwnerId`.
- **`_test_ownership_guard_kt`** (~L2439, `OwnershipGuardTest.kt`, s7 unit): el diente unit de canModify — si cambiás
  la firma, este test cambia (agregá un caso "RTD/dueño null → sólo bypass").
- **`tools/access_control_check.py`** (proof urllib de s9): donde se asevera el veredicto vivo (403/200/404). Acá va
  el tooth RTD. El idiom de infra_up de s9 (PG viva + `java -cp dist/lib/*` para el server, NO `gradle run`).
- **`_seed_chain`** (~L3200): el seeder del server vivo (skip-optional→NULL). Para una 2ª fila RTD, mirá cómo s9
  siembra el dueño + la fila.

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **El handoff sub-estima los sitios.** FSK-SELF-REF tocó 3 (no 1). Antes de cada gradle lento, **eyeball SIN gradle**:
  emití snipeit a `build/product` con un scratch python (`importlib` sobre `codegen/scaffold_product.py`, ver el patrón
  en el §Evidencia de FSK-SELF-REF) y LEÉ `AppServer.kt` (`modifyVerdict`) + `OwnershipGuard.kt` + el migration ANTES
  de correr. Cazás los huecos sin esperar 2-3 min.
- **`meta verify` re-corre la estación ACTIVA con `build=False`** (no regenera) — útil para sabotear el artefacto
  GENERADO y ver el gate rojo rápido, PERO la activa tras un product-run es **s11** (la última). Para un tooth en s9
  por la vía canónica, el camino es **sabotear el codegen + `product-run`** (rojo en s9, s10/s11 no corren) → revertir
  → `product-run` verde (restaura la activa verde, clave para que `stop_proof` no bloquee el cierre del turno).
- **`meta station` corre la META-línea (m00-m08), NO la línea FSK.** Para la línea FSK: `product-run`.
- **`proof_protect` DENIEGA tocar `.proof/` por shell** (incluso leer el log) — pero el Read tool SÍ lee los logs de
  `.proof/logs/`. El árbol generado (`products/<p>/build/product/...`) es legible por shell.
- **`dangerouslyDisableSandbox: true`** para gradle/docker (el sandbox los mata: exit 144).

## 4. Restricciones DURAS de FSK que SIGUEN vigentes
Dueño nullable es lo que se levanta. Refs **polimórficos** (deferral 2: `assigned_to` → User|Location|Asset),
**custom-fields dinámicos** (deferral 1), **ciclos cross-entidad** (deferral 6), **verbos de dominio**
(checkout/checkin/audit, deferral 11b) y **company-scoping** (deferral 8) siguen DIFERIDOS — cada uno su incremento.

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El fix del codegen** (`scaffold_product.py`) es nivel FÁBRICA → **este incremento** lo cubre (header ABIERTO).
- **La adopción en `products/snipeit/product.yml`** es nivel PRODUCTO → abrí TAMBIÉN
  `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar `product.yml`. Dos
  increments, dos niveles (el guard elige por ruta).
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) + `feat(snipeit): …` (product.yml) + `docs(fsk): cerrar
  FSK-OWNERSHIP-OPTIONAL (§Evidencia) + abrir <siguiente>`.
- **Probá POR BLOQUEO** (no fakees verde): `product-run --product snipeit` PASS (RTD round-trippea bajo control de
  acceso) · diente de dos lados vivo (RTD+no-bypass → SÓLO `access_control_live` rojo) · `ci --rederive
  --all-products` == pin (los 3) · `meta check` 6/6 (`generality` verde) · `git diff src/+seed = 0` · default+assets
  product.yml = 0.

## 6. Criterio de cierre (demostrable, no narrable)
1. `products/snipeit/product.yml`: `Asset.assigned_user_id` → `required: false` (RTD real) y `product-run --product
   snipeit` **PASS** — una fila RTD (dueño null) coexiste con una asignada; el control de acceso las distingue VIVO.
2. **Diente de DOS lados verificado VIVO**: RTD+no-bypass → 403 / RTD+bypass → 200 / inexistente → 404 (no
   confundidos). Saboteá → confirmá ROJO **sólo** en `access_control_live` → revertí → verde.
3. `ci --rederive --all-products` == pin (los 3). `meta check` 6/6 (`generality` verde). `git diff src/metafactory +
   seed = 0`. `git diff` default+assets product.yml = 0. (Si tocaste el set de checks → re-pin justificado.)
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md §3 deferral 3 (y 4 si entró)/§4` actualizados. Abrí el SIGUIENTE con su
   handoff autocontenido (ver §7).

## 7. Qué viene DESPUÉS (para que sepas dónde estás parado)
Orden del push Snipe-IT (re-priorizado, ver `products/snipeit/docs/reference/SNIPEIT-DOMAIN.md §4`):
- ~~self-ref~~ ✅ (FSK-SELF-REF) · ~~CRUD-mutación~~ ✅.
- **(este)** **ownership opcional / RTD** (deferrals 3+4).
- **custom fields dinámicos** (deferral 1) — el eje GRANDE: gramática de campos dinámicos por modelo (EAV-como-
  columnas). Probablemente el mayor eje de fábrica que Snipe-IT fuerza.
- **operaciones de dominio** (deferral 11b): checkout/checkin/audit como verbos que MUTAN semántica (decrementar qty,
  liberar seat, Actionlog) — más allá del veredicto de acceso.
- **diferidos DUROS (red/scope)**: push de la imagen a un registry · e2e Playwright (browser real) · AppServer-en-
  contenedor con PG · ciclos cross-entidad (deferral 6) · checkout polimórfico (deferral 2).

---

## Evidencia (CERRADO 2026-06-22T03:11Z) — probado por bloqueo, no narrado

**Qué se levantó.** Un activo Ready-To-Deploy está SIN asignar (dueño NULL) — el caso NORMAL de Snipe-IT.
Opt-in por el `required` del `owned_by`: con dueño REQUERIDO el codegen queda **byte-idéntico** (default/assets
sin re-derivar). El handoff señalaba 2 sitios (firma de `canModify` + conflación 404); **generar de verdad
destapó 4** (la lección de FSK-SELF-REF se repitió):

1. **`_ownership_guard_kt`** — `canModify(rowOwnerId: Long?)`: `actorRole in bypass || (rowOwnerId != null &&
   actorPrincipalId == rowOwnerId)`. Una fila SIN dueño (RTD) no tiene principal contra quien cruzar → sólo un
   rol de bypass la modifica. Opt-in: con dueño requerido, la firma `Long` queda EXACTA.
2. **`_modify_verdict_kt`** (NUEVO helper, extraído del skeleton) — separa **EXISTENCIA** de **DUEÑO**: la
   existencia se lee reusando `<e>RowJson != null` (sin agregar query al Repository), una fila RTD EXISTE (no es
   404), e inexistente sigue 404. Con dueño requerido el cuerpo queda EXACTO (`ownerId == null -> 404`).
3. **`_mutation_fns`** (NO estaba en el handoff) — el dueño se fija al principal del token SIEMPRE (el creador es
   dueño), aunque la columna sea opcional. Antes el skip-optional lo saltaba → `ownerId` quedaría sin usar (rojo).
4. **`_seed_chain` + `_sample`** (la 2ª fila + las UNIQUE, NO en el handoff) — el server siembra una 2ª fila RTD
   (owner NULL, valores **ALT** en las columnas UNIQUE para no chocar con la fila asignada: `asset_tag` =
   `"alt-asset_tag"` ≠ `"sample-asset_tag"`); `/seed` expone su `rtd` id. Sin esto el tooth no tendría fila RTD.

**El producto** (`snipeit/product.yml`): `Asset.assigned_user_id` → `required: false` (RTD real).

**Verde, no fingido:**
- `product-run --product snipeit` **PASS** · RTM **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
- **Diente de DOS lados VIVO** (s9 `access_control_live`): saboteé `modifyVerdict` (rama `ownerId == null ->
  HTTP_OK` → RTD modificable por cualquiera) → `product-run` **FAIL**: `access_control_live FAIL(1)` con
  `observability_live ok` + `frontend_consume_live ok` (hermanos de s9 VERDES — aislado al tooth RTD), s10/s11 no
  corren · revertí → **PASS** (activa s11 verde). Tooth: RTD+no-bypass→403 / RTD+bypass→200 / inexistente→404.
- + **diente UNIT** (s7 `OwnershipGuardTest`): 2 casos nuevos (RTD+no-bypass→false / RTD+bypass→true).
- `ci --rederive --all-products` **3/3 == pin** (default 12/12 · assets 11/11 · snipeit 11/11; **proof_sha intacto
  → SIN re-pin**: sólo se fortalecieron checks existentes, mismos nombres+exit).
- `meta check` **6/6** (`generality` verde) · `git diff src/metafactory + seed = 0` · default+assets product.yml = 0.

**Commits:** `59ebfb9` (feat-fsk codegen) + `c2b4079` (feat-snipeit product.yml) + el docs de cierre.
**Eyeball SIN gradle** (handoff §3): emití snipeit con `importlib` sobre `scaffold_product.py` y leí AppServer/
OwnershipGuard/migration ANTES del gradle → confirmé los 4 sitios y verifiqué que default/assets quedan
byte-idénticos (firma `Long`), sin esperar la línea lenta. cwd de Bash en la RAÍZ todo el tiempo (sin deadlock).
