<!-- meta:doc sha=c0bf5e28df6b75f98bf2904df16020f46cda4697 updated=2026-06-27T01:41Z -->
# Incremento FSK-SELF-REF — jerarquías self-ref (Location.parent_id, User.manager_id) → el 1er paso del push Snipe-IT

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (2026-06-22T01:48Z; abierto 2026-06-22T00:06Z). Ver §Evidencia. Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA
> editada (ADR-016).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-DEPLOY con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (la decisión estratégica — leéla, no la saltees)

**FSK está MADURO** (tras FSK-DEPLOY, 2026-06-22): un producto se genera → se prueba e2e → tiene CRUD vivo del grafo
relacional ENTERO bajo control de acceso (auth→RBAC→ownership) a runtime → una UI usable por un humano → y **deploya
en un contenedor que responde**. El último hueco claramente-FSK-general (deploy) está cerrado. **DECISIÓN del
ingeniero (2026-06-22): PIVOTAR a construir Snipe-IT** — el trabajo pasa a ser product-specific, trabajando los **12
deferrals** de `products/snipeit/docs/reference/SNIPEIT-DOMAIN.md`, cada uno **driven por el producto real** (NO
especular ejes FSK-general sueltos).

**Metodología probada** (así se cazaron casi todos los huecos de FSK): el producto Snipe-IT EXPONE un gap → si es
genuinamente FSK-general se arregla **GENERAL** (codegen+spec, cero nombres de dominio, `generality` verde) en su
propio incremento; si es del dominio, vive en el producto. **La mayoría de los deferrals son [GAP-FÁBRICA]** → la
mayoría de los "incrementos Snipe-IT" son fixes de FÁBRICA GENERALES *driven by* el producto. Eso NO contradice el
pivote: la diferencia con "un eje FSK-general especulativo" (lo que NO se eligió) es que acá el gap lo **fuerza un
caso real de Snipe-IT**.

**Este incremento = el deferral 5 (self-ref), el 1er paso del push** porque es el más **tractable + fundacional**:
- **Fundacional**: restaura la **estructura organizativa real** de Snipe-IT — `Location.parent_id`→Location
  (jerarquía de ubicaciones) y `User.manager_id`→User (cadena de management). Hoy ambos están DIFERIDOS (comentados
  en `product.yml`), una infidelidad visible.
- **Tractable**: `SNIPEIT-DOMAIN.md §3.5` lo llama explícitamente **"un gap chico y acotado"**. El fix vive en UNA
  función del codegen y tiene un MODELO ya escrito al lado (`_roundtrip_kt`, ver §2).
- Construye momentum + valida el loop "Snipe-IT driving general fix" sin la complejidad del dueño-nullable (deferral
  3/4, el siguiente candidato — ver §7).

**Hermano YA cerrado (de dónde venís):** FSK-DEPLOY construyó la imagen + smoke del contenedor vivo. Detalle:
`docs/work/FSK-DEPLOY-INCREMENT.md §Evidencia` + `docs/LOG.md` (2026-06-22T00:06Z).

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso: la línea entera s0→s11, sin self-ref todavía):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez** (el sandbox de Bash mata gradle: exit
144). **Mantené el cwd de Bash en la RAÍZ del repo** (un `cd` a un subdir filtra el cwd persistente → deadlock del
hook `stop_proof`). Debe dar **PASS**. RTM snipeit **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **s9 usa PUERTOS FIJOS (18593/18594/18595) y s11 usa 18596** → NUNCA corras dos s9/s11 en paralelo, NUNCA dejes
un `product-run`/`ci` en BACKGROUND al cerrar el turno (el hook `stop_proof` RE-CORRE la estación activa → colisión
de puerto → falso rojo). FOREGROUND (timeout ≥420000ms), dejá terminar ANTES de cerrar el turno.

**2) Entendé el gap EXACTO** (todo en `codegen/scaffold_product.py`):
- **`_it_repository_kt`** (el seeder del tier integración, s7 `pyramid_integration`): setea TODOS los refs de cada
  entidad —incluido el OPCIONAL— y referencia `ids[<target>]` ANTES de insertar la fila. Para un **self-ref**
  (`parent_id`→la MISMA entidad) eso es **chicken-and-egg**: `ids[self]` no existe todavía → **`KeyError`** (y aún si
  existiera, FK a una fila no insertada). Por eso `Location.parent_id` y `User.manager_id` están **DIFERIDOS** en
  `products/snipeit/product.yml` (comentados, ver líneas ~98-100 Location y ~128 User).
- **`_roundtrip_kt`** (~L1217, el seeder de s1 `db_roundtrip_live`): **YA hace lo correcto** — sólo captura/usa el id
  de un ref **REQUERIDO** (`f.get("required", True)`); un ref **opcional** (`required: false`) **NO se setea → queda
  NULL** (prueba positiva de que la columna nullable acepta ausencia). **Ese es el MODELO a copiar.**
- La **migración** (`_migration_sql`) y el **roundtrip** YA toleran self-ref opcional (columna nullable → NULL). El
  ÚNICO que rompe es `_it_repository_kt`.

**3) EL DISEÑO (resolvelo GENERAL, cero nombres de dominio):**
- Hacé que **`_it_repository_kt` trate los refs como `_roundtrip_kt`**: para un ref **opcional**, NO lo setees (dejá
  NULL) **o**, si querés PROBAR la jerarquía de verdad (mejor diente), manejá el **self-ref** explícitamente:
  - Insertá la 1ª fila de la entidad con el self-ref en **NULL** (la raíz: `Location` sin padre / `User` sin
    manager).
  - Insertá una 2ª fila apuntando su self-ref al id de la 1ª (el hijo → la raíz) → **prueba la jerarquía viva**.
- **DATA-agnóstico**: la heurística es "ref cuyo `to` == la entidad que lo declara" (self-ref) y "ref `required:
  false`" (opcional). Cero nombres de Snipe-IT/Location/User. El fix sirve para CUALQUIER producto con self-ref.
- **Adopción en el producto**: re-habilitá en `products/snipeit/product.yml` los campos hoy diferidos —
  `{ name: parent_id, type: ref, to: Location, required: false }` en Location y `{ name: manager_id, type: ref, to:
  User, required: false }` en User (descomentalos; respetá el orden topológico — la entidad ya existe, el self-ref no
  agrega un predecesor nuevo). Actualizá el comentario del `product.yml` (ya no es deferral) y el deferral 5 de
  `SNIPEIT-DOMAIN.md §3` (movelo de GAP a hecho).

**EL DIENTE de dos lados:** el tier integración (`pyramid_integration`, s7, infra_up vs PostgreSQL viva) inserta+lee
la jerarquía self-ref → el hijo apunta a la raíz, round-trip cruza el id. **Saboteá**: hacé que el seeder setee el
self-ref del hijo a un id INEXISTENTE → la FK viola → el INSERT falla → s7 rojo. **O** rompé el orden (insertá el
hijo antes que la raíz) → FK rojo. Revertí → verde. (Si elegís el camino "NULL-only", el diente es más flaco:
considerá el camino "raíz+hijo" para un tooth real de jerarquía.)

---

## 1. ⚠️ RE-PIN — la diferencia OPERATIVA vs FSK-DEPLOY (NO la confundas)

FSK-DEPLOY agregó una **estación NUEVA (s11)** → cambió el SET de checks → `proof_sha` nuevo → **re-materializar +
re-pinear** (lo costoso). **ESTE incremento NO agrega check ni estación**: el fix vive DENTRO del check existente
`pyramid_integration` (s7), mismo nombre, mismo exit → **`proof_sha` INTACTO** → **pines byte-idénticos, SIN
re-materializar, SIN re-pinear** (como FSK-BROWSER-FORM/REFS-IN-BODY). Recordá: `proof_sha = sha256({station,
sorted(check_name, exit)})` (`seed/verifier.py:compute_proof_sha`) — es INVARIANTE a qué campos seedea el código,
sólo depende de los nombres de check + exit.

**⚠️ PERO `git diff products/snipeit/product.yml` NO será 0** (re-habilitás campos) — y eso está **BIEN**: es trabajo
de PRODUCTO (el `product.yml` ES la DATA del producto; hacerlo más fiel es el punto). Lo que SÍ debe quedar en 0:
`git diff src/metafactory + seed` (sustrato intacto), `git diff` del `product.yml` del **default** y de **assets**
(no los toques), y `meta check` `generality` verde (el codegen no nombra dominio). El default + assets re-derivan
`==pin` sin cambios; snipeit re-deriva `==pin` también (proof_sha intacto) AUNQUE su product.yml cambió.

---

## 2. Maquinaria a REUTILIZAR (no la reinventes)
- **`_roundtrip_kt`** (~L1217): el MODELO de cómo tratar refs opcionales (skip → NULL). Copiá su patrón a
  `_it_repository_kt`.
- **`_it_repository_kt`**: la función A ARREGLAR (el seeder del tier integración s7).
- **El idiom `infra_up` de s7** (`pyramid_integration`, `stations/s7.yml`): PostgreSQL viva por `docker run
  postgres@sha256:`, el seeder + el test corren contra ella. El diente nativo (DB caída → rojo) ya está.
- **`_migration_sql`** (~L1006 nullability): ya emite columna nullable para `required: false` — la self-ref opcional
  ya migra bien; NO la toques salvo que el orden de FK lo pida (self-FK a la misma tabla es legal en SQL).

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **`meta station` corre la META-línea (m00–m08), NO la línea de producto FSK.** Para re-correr una estación FSK con
  un sabotaje, la vía es **`product-run`** (re-materializa de codegen). **`meta verify`** re-corre la estación ACTIVA
  con `build=False` (no regenera el artefacto) — útil para sabotear el artefacto GENERADO y ver el gate rojo rápido.
- **Puertos FIJOS → FOREGROUND, nunca background al cerrar turno.** El hook `stop_proof` re-corre la estación activa;
  un run de fondo colisiona el puerto → falso rojo. Un producto a la vez, foreground, timeout ≥420000ms.
- **`proof_protect` DENIEGA tocar `.proof/` por shell (incluso leer)** → usá `meta rtm`/`meta recall`; el árbol
  generado (`products/<p>/build/product/...`) SÍ es legible.
- **Eyeball SIN gradle antes de cada corrida lenta**: emití snipeit a `build/product` (`python3
  codegen/scaffold_product.py` desde la fábrica con el blueprint del producto, o `--selftest`) y LEÉ el
  `RepositoryIT.kt` generado + la `V1__init.sql` ANTES de correr gradle. Cazás el self-ref mal seedeado sin esperar.
- **`dangerouslyDisableSandbox: true`** para gradle/docker (el sandbox mata gradle: exit 144).

## 4. Restricciones DURAS de FSK que SIGUEN vigentes
La self-ref que se levanta es **opcional** (nullable). Self-ref REQUERIDO no está en scope (pediría un seed que
inserte la raíz con el self-FK nulo y luego lo actualice — más complejo). Refs **polimórficos** (deferral 2),
**ciclos cross-entidad** (deferral 6: Location.manager_id→User, Department.manager_id→User) y **dueño-nullable/RTD**
(deferral 3/4) siguen DIFERIDOS — cada uno su propio incremento.

## 5. Disciplina + dónde van los docs (⚠️ ESTE incremento toca DOS niveles, ADR-016)
- **El fix del codegen** (`codegen/scaffold_product.py`) es nivel FÁBRICA → **este incremento (factory doc-home)** lo
  cubre; su header ABIERTO ya abre el slot de fábrica.
- **La adopción en `products/snipeit/product.yml`** es nivel PRODUCTO → el `increment_guard` exige un incremento de
  **PRODUCTO** abierto para editar ese archivo (ADR-016, el guard elige por RUTA). Abrí también
  `meta increment open --factory full-stack-kotlin --product snipeit <slug>` (o creá el doc bajo
  `products/snipeit/docs/work/`) ANTES de tocar `product.yml`. **Recomendado**: hacé el fix de codegen PRIMERO
  (probalo re-habilitando una self-ref de prueba en el DEFAULT o un scratch, factory increment), LUEGO adoptá en
  snipeit (product increment). Dos increments distintos, dos niveles — es exactamente el layering de la Fase 1.
- **Contenido de FÁBRICA GENERAL**: cero nombres de dominio en el codegen; `generality` verde es el anti-overfit
  real. **Commit = parte del trabajo (ADR-010), nunca lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus
  4.8 <noreply@anthropic.com>`). Patrón de 2 commits: `feat(fsk): …` (codegen/spec) + `docs(fsk): cerrar
  FSK-SELF-REF (§Evidencia) + abrir <siguiente>` (y/o `feat(snipeit): …` para el product.yml si lo separás).
- **Probá POR BLOQUEO**: `product-run --product snipeit` PASS (la jerarquía self-ref round-trippea en s7) · diente de
  dos lados (self-ref mal seedeado → SÓLO `pyramid_integration` rojo) · `ci --rederive --all-products` == pin (los 3,
  proof_sha intacto) · `meta check` 6/6 (`generality` verde) · `git diff src/+seed = 0` · default+assets product.yml
  = 0. **No fakees verde.**

## 6. Criterio de cierre (demostrable, no narrable)
1. `products/snipeit/product.yml` re-habilita `Location.parent_id` + `User.manager_id` (self-ref opcionales) y
   `product-run --product snipeit` da **PASS** — la jerarquía se **siembra y round-trippea VIVA** en s7
   (`pyramid_integration` vs PostgreSQL viva). El default + assets siguen PASS (no tocados).
2. **Diente de DOS lados verificado VIVO**: saboteá el seeder self-ref (id inexistente / orden invertido) → corré →
   confirmá ROJO **sólo** en `pyramid_integration` (los hermanos de s7 y el resto verdes) → revertí → verde.
3. `ci --rederive --all-products` == pin (los 3, **proof_sha INTACTO** — NO re-pinaste). `meta check` 6/6
   (`generality` verde). `git diff src/metafactory + seed = 0`. `git diff` del product.yml del default + assets = 0.
4. El scope honesto se actualiza: STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md §3.5` (deferral 5 de GAP → hecho) + §4
   (re-priorizar). Abrí el SIGUIENTE con su handoff autocontenido (ver §7).

## 7. Qué viene DESPUÉS (para que sepas dónde estás parado)
Orden probable del push Snipe-IT (re-priorizado tras DEPLOY; los GAP-FÁBRICA son fixes generales driven by el
producto):
- **(este)** **self-ref** (deferral 5) — jerarquías Location/User.
- **ownership opcional / RTD** (deferrals 3+4) — dueño **nullable** + estado Ready-To-Deploy real + seed transitivo
  en el server vivo. **El más CORE de Snipe-IT** (un activo sin asignar es el caso normal) pero más involucrado
  (toca `OwnershipGuard.canModify(rowOwnerId: Long)` no-nullable + la conflación owner-null/404 del server vivo).
- **custom fields dinámicos** (deferral 1) — el eje GRANDE (gramática de campos dinámicos por modelo, EAV-como-
  columnas). Probablemente el mayor eje de fábrica que Snipe-IT fuerza.
- **operaciones de dominio** (deferral 11): checkout/checkin/audit como verbos que MUTAN semántica (decrementar qty,
  liberar seat, Actionlog) — más allá del veredicto de acceso.
- **diferidos DUROS (red/scope)**: push de la imagen a un registry · e2e Playwright (browser real) · AppServer-en-
  contenedor con PG.

---

## Evidencia (cierre, 2026-06-22T01:48Z) — demostrable, no narrable

**Lo construido (FÁBRICA, GENERAL, cero nombres de dominio — `codegen/scaffold_product.py`)**. El handoff señaló
**1** función (`_it_repository_kt`); el gradle real destapó que eran **3** sitios — el patrón se repetía en cada
generador que asumía "ningún ref apunta a su propia entidad":
1. **`_it_repository_kt`** (seeder s7, el del handoff): una self-ref (heurística DATA-agnóstica `f["to"] ==
   e["name"]`) se siembra como cadena **raíz→hijo** — la raíz con el self-ref en NULL, un hijo apuntándola, y un
   **read-back** (`ctx.select(<selfcol>)…shouldBe <rootId>`) que cruza el id leído de la PG viva. `size shouldBe 2`
   para las entidades self-ref. Patrón calcado de `_roundtrip_kt` (skip-optional→NULL), acotado al self-ref.
2. **`_app_kt`** (ejercedor del contrato, s0 `contract_single_source`) — **NO estaba en el handoff**: emitía
   `managerId = user.id` DENTRO del propio `val user = User(...)` → auto-referencia de variable → compile rojo.
   Fix: una self-ref del sample = `null` (la raíz no tiene padre; `Long?` nullable).
3. **`_KT_SAMPLE_ALT` + el hijo difiere en sus UNIQUE** — **NO estaba en el handoff**: lo destapó `User.username`
   (`unique`): root y child seedeaban ambos `"it"` → `IntegrityConstraintViolationException` (UNIQUE). El hijo usa
   valores alternos en sus columnas `unique`.

`_migration_sql` y `_seed_chain` (s9) NO necesitaron tocarse: ya toleraban la self-ref opcional (columna nullable
self-FK / skip-optional). El sustrato (`src/metafactory/` + `seed/`) = **0**.

**§1 (RE-PIN) confirmado**: NO se agregó check ni estación (el fix vive DENTRO de `pyramid_integration`/s0, mismos
nombres+exit) → `proof_sha` INTACTO → **pines byte-idénticos, SIN re-materializar, SIN re-pinear**. `git status`
no muestra ningún `pinned_verdict.json` modificado.

**Adopción en el producto** (incremento de PRODUCTO aparte, `products/snipeit/docs/work/SNIPEIT-SELF-REF-INCREMENT.md`):
`Location.parent_id`→Location y `User.manager_id`→User re-habilitados (self-ref opcionales).

**Criterio de cierre (§6) — TODOS ✅**:
1. snipeit `product-run` **PASS** (s0→s11); la jerarquía self-ref se siembra y round-trippea VIVA en s7. default +
   assets siguen PASS (no tocados). ✅
2. **Diente de DOS lados VIVO**: saboteé el seeder (hijo self-ref → `999999L`, id inexistente) → `product-run` →
   `pyramid_integration FAIL(1)`, **gate s7 SHUT**, hermanos s7 (`pyramid_unit`/`pyramid_unit_ts`/`workflow_enforced`)
   **verdes** → revertí → **verde**. ✅
3. `ci --rederive --all-products` **12/12 · 11/11 · 11/11 == pin** (proof_sha INTACTO). `meta check` **6/6**
   (`generality` verde). `git diff src/metafactory + seed = 0`. `git diff` default+assets product.yml = 0. ✅
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md §3 deferral 5 (GAP→hecho)/§4 (re-priorizado)` actualizados. SIGUIENTE
   abierto con handoff: `docs/work/FSK-OWNERSHIP-OPTIONAL-INCREMENT.md` (deferrals 3+4). ✅
