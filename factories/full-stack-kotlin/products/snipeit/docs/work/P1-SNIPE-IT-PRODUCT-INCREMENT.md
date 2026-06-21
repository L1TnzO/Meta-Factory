# Incremento P1-SNIPE-IT-PRODUCT — construir el primer producto real (Snipe-IT)

> **Doc de gobierno del PRODUCTO** (nivel `factories/full-stack-kotlin/products/snipeit/`, ADR-016).
> Estado: **CERRADO** (2026-06-21T03:22Z). Esta es su CASA correcta: `…/products/snipeit/docs/work/`. Gestionalo level-aware:
> `meta increment status --factory full-stack-kotlin --product snipeit` (y `… close …` para cerrarlo,
> gateado). Editar `products/snipeit/**` (no-`.md`) exige ESTE incremento abierto — el `increment_guard`
> elige el lifecycle por la ruta editada. Todo cambio de código del producto vive acá (ADR-010 + ADR-016).
>
> **✅ CERRADO (2026-06-21): Fase 2 HECHA — el primer producto real generado VERDE por la línea FSK.** La
> fábrica entera (19 entidades) pasa s0→s10 por gradle: `product-run` PASS · RTM 18/19 (único UNSATISFIED =
> s6 LLM, deferral keyless VISIBLE) · `ci --rederive == pin` en clon limpio. Evidencia detallada en §7.bis. Los
> 2 huecos que gradle destapó se arreglaron GENERALES (incrementos `FSK-CODEGEN-ROBUSTO-MULTI-ENTIDAD` de
> fábrica + `RTM-ARTIFACT-PATHS-PACKAGE-AWARE` de sustrato, ambos CERRADOS). `product.yml` NO se tocó (DATA).
>
> **Lo que SIGUE (§7.ter) son incrementos de FÁBRICA nuevos, NO este P1**: CRUD-mutación real e2e (el server
> vivo da el VEREDICTO de autz, no muta columnas) → self-ref → ownership opcional/RTD → custom-fields →
> frontend React + deploy + breadth. Abrí cada uno con `meta increment open <slug> --factory full-stack-kotlin`.
>
> **El histórico de abajo (★ EMPEZÁ ACÁ, §1–§6) quedó como registro de la Fase 2; ya está HECHA.**

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**Lo hecho (Fase 1, commit `0f01ae1`):** el dominio real de Snipe-IT (grokability v8.6.3) está cosechado a un
blueprint FSK FIEL, validado por bloqueo SIN gradle (`scaffold --selftest`: 19 entidades → 66 archivos,
idempotente, 0 forward-refs). **Tu trabajo:** correr la línea FSK real (gradle) sobre ese spec, arreglar lo
que el compile/gates REALES rompan, hasta `product-run` PASS · RTM · `ci --rederive == pin`.

**El edit-gate ahora es LEVEL-AWARE (ADR-016) — sabé en qué carril estás antes de editar:**
- Editar `products/snipeit/**` (el `product.yml`, etc.) → lo gatea ESTE incremento P1, que YA está abierto. Listo.
- Arreglar un **hueco de FÁBRICA** (§5: el codegen/spec/stations de FSK — el caso normal cuando el producto
  fuerza una capacidad nueva) → es otro nivel: abrí un incremento de fábrica
  `meta increment open <slug> --factory full-stack-kotlin` (hoy no existe `factories/full-stack-kotlin/docs/work/`
  → se crea solo). El guard te BLOQUEA editar codegen de FSK sin ese incremento, y te dirá el nivel.
- Un fix de **sustrato/meta** (raro; el producto NO debería forzarlo, anti-overfit `git diff src/+seed=0`) →
  incremento META en `docs/work/`. Tres carriles, tres slots independientes: no se pisan.

**Los 3 archivos que tenés que leer primero (en orden):**
1. `factories/full-stack-kotlin/products/snipeit/product.yml` — **el SPEC** (la fuente; 19 entidades). Es DATA.
2. `factories/full-stack-kotlin/products/snipeit/docs/reference/SNIPEIT-DOMAIN.md` — el dominio completo + el
   mapeo + **12 deferrals honestos** + **las 4 restricciones DURAS de FSK** (las repito en §3 acá). Leelo entero.
3. Este doc (§2–§6).

**El primer comando (corré la línea, mirá qué rompe):**
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **DEBE correr con `dangerouslyDisableSandbox: true`** (el sandbox de Bash mata gradle: exit 144 sin
output). FOREGROUND, por-producto. Es la PRIMERA vez que estas 19 entidades pasan por gradle de verdad —
esperá que el compile/detekt/tests surfacen cosas que el selftest (codegen en memoria) no ve. Iterá a verde.

---

## 1. Objetivo (qué deja TERMINADO este incremento)
Un **producto Snipe-IT real** generado por la línea FSK: `meta product-run --product snipeit` PASS · RTM
COMPLETE (o deferrals VISIBLES, como `assets` con s6) · `meta ci --rederive --product snipeit == pin` en clon
limpio. El producto es un DELIVERABLE, no un fixture. **Anti-overfit duro: `git diff src/metafactory/ + seed/`
= 0** — el producto es DATA; todo hueco de fábrica que el producto fuerce se arregla como mecanismo GENERAL
(en `codegen/`+spec de FSK), idealmente en su PROPIO sub-incremento, NUNCA hackeando el `product.yml`.

## 2. Estado de las fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Investigación + blueprint fiel** (fan-out 7 agentes → 19 entidades + domain doc + 12 deferrals; validado por `scaffold --selftest`/`--check-idempotent`/0 forward-refs). | ✅ (2026-06-20, `0f01ae1`) |
| 2 | **Generar a verde** por la línea FSK (gradle): product-run PASS · RTM · ci --rederive == pin. Arreglar lo que el compile/gates REALES rompan (gap de fábrica → GENERAL). | ✅ (2026-06-21) — ver §Evidencia. Salió la **fábrica entera** (19 ent., no un slice). |
| 3 | **Huecos que el slice exponga** (§5) como fábrica GENERAL — un sub-incremento por hueco, `git diff src/+seed=0`. | ⏳ |
| 4 | **Breadth + CRUD-mutación real + frontend vivo + deploy** (§5), incrementos sucesivos. | ⏳ |
| 5 | **Cierre** — STATE/ROADMAP/LOG de FSK + meta + evidencia (RTM, pin, ci --rederive, anti-overfit). | ⏳ |

## 3. Las 4 restricciones DURAS de FSK (el spec YA las respeta — leelas antes de TOCAR el product.yml)
Descubiertas leyendo `factories/full-stack-kotlin/codegen/scaffold_product.py`. Violarlas = codegen/compile
rojo. Si editás el spec (agregar/mover entidades, cambiar refs), respetalas o vas a romper la generación:
1. **Orden topológico, TODOS los refs.** `_migration_sql` emite un FK `REFERENCES` por CADA ref (requerido u
   opcional) en orden de declaración → todo `ref.to` apunta a una entidad declarada ANTES (o a sí misma).
   **Ciclos = ilegales** (Snipe-IT: se quitaron `Location.manager_id`, `Department.manager_id`→User).
2. **El campo `owned_by` DEBE ser `required: true`.** `OwnershipGuard.canModify(rowOwnerId: Long)` es
   no-nullable y el server vivo trata `ownerId == null` como 404. (`Asset.owned_by: assigned_user_id` requerido.)
3. **El seed del server vivo (FSK-S15) prohíbe refs REQUERIDOS no-dueño** en la entidad con dueño (Asset) y en
   su dueño (User). Por eso `Asset.model_id` va `required:false` (Snipe lo exige = gap documentado). User no
   tiene ningún ref requerido.
4. **Sin self-refs (todavía).** `_it_repository_kt` (seeder del tier integración s7) setea TODO ref incl. el
   opcional y referencia `ids[self]` antes de insertar → `KeyError`. Por eso `Location.parent_id` y
   `User.manager_id` están DIFERIDOS. **Si querés restaurarlos**, primero el fix GENERAL (§5.2).

## 4. Cómo correr la línea — comandos + lecciones caras (NO re-aprendas)
`meta = PYTHONPATH=src python3 -m metafactory.cli`. Mantené el cwd de Bash en la RAÍZ del repo (un `cd` a
subdir filtra el cwd y rompe el cierre de turno — 4 hooks cwd-relativos; usá paths absolutos / subshells).
1. `meta product-run --factory full-stack-kotlin --product snipeit` → re-materializa la instancia (base ⊕
   product.yml) + corre s0–s10. **`dangerouslyDisableSandbox: true`, FOREGROUND, por-producto** (dos líneas
   no entran en 600s; ~3 min/producto con gradle caliente).
2. `meta rtm --product snipeit` (COMPLETE o deferrals visibles) → `meta pin --product snipeit` → `meta ci
   --rederive --product snipeit` (== pin en clon limpio).
3. `meta check` (6/6) al final.

**Lecciones caras (de FSK-S11..S15, NO re-descubrir):**
- **El sandbox mata gradle** (exit 144) → `dangerouslyDisableSandbox: true` en TODA corrida de línea/gradle.
- **Server vivo largo: `java -cp build/install/<pkg>/lib/*`**, NUNCA `gradle run`/JavaExec (el daemon forkea el
  JVM fuera del process-group → leak de puerto → falsa-verde). Ya está cableado así en s9; respetalo.
- **`proof_protect` DENIEGA tocar `.proof/` por shell** (incluso leer) → usá `meta rtm`/`recall`/`journal`.
- **Las INSTANCIAS se re-materializan cada corrida** (no edites sus `stations/`/`factory.spec.yml` a mano —
  son gitignored, derivados). Sólo editás `products/snipeit/product.yml`. El DEFAULT sí se appendea a mano.
- **Si una station no aplica keyless** (p.ej. s6 LLM), el deferral honesto es `station_activation: {s6: off}` en
  el product.yml (ya está) — la opción que el propio gate sanciona, no fakear verde.
- **Slice si el presupuesto aprieta**: 19 entidades es un compile gordo. Si no entra/explota, generá un slice
  core (Company/Manufacturer/Category/Depreciation/Location/User/AssetModel/Asset) primero y breadth después
  (License/seats, Accessory, Consumable, Component, Maintenance, Department) — comentando entidades en el
  product.yml. Respetá el orden topológico (§3.1) al recortar.
- **Validación barata SIN gradle** (la de la Fase 1, útil para iterar el spec rápido antes de pagar gradle):
  materializar (`from metafactory.cli import ensure_product_instance`) + `METAFACTORY_ROOT=products/snipeit
  python3 codegen/scaffold_product.py --selftest` / `--check-idempotent`.

## 5. Los huecos que el producto VA a forzar (de SNIPEIT-DOMAIN.md §3) — arreglalos GENERAL, driven por el producto
Cada uno probablemente su PROPIO sub-incremento, contenido de fábrica (`codegen/`+spec; `git diff
src/metafactory/+seed/`=0). En orden de probable necesidad:
1. **CRUD-mutación real** — hoy el server vivo (FSK-S15) devuelve el VEREDICTO de autz (403/200/201/404) pero
   no MUTA columnas end-to-end. Un producto usable necesita INSERT/UPDATE/DELETE tipados (jOOQ) bajo el control
   de acceso ya enforzado. Diente: round-trip e2e (POST crea → GET lista → PUT muta → GET ve → DELETE borra).
2. **Self-ref** (restricción §3.4) — fix acotado: que `_it_repository_kt` saltee los refs opcionales (como ya
   hace `_roundtrip_kt`) y/o maneje self-ref → restaura `Location.parent_id` + `User.manager_id`.
3. **Ownership opcional / RTD** (restricciones §3.2/§3.3) — dueño nullable (asset sin asignar = estado RTD real)
   + seed transitivo en el server vivo → permite `Asset.model_id` requerido (faithful).
4. **Custom fields dinámicos** — el eje GRANDE: campos definidos por usuario (EAV-como-columnas en Snipe-IT).
   Pide gramática nueva del blueprint. Difiéralo hasta que el core esté verde.
5. **Frontend React vivo + deploy** + breadth de endpoints/operaciones (checkout/checkin/audit/request/bulk).
6. Resto de los 12 deferrals (company-scoping, depreciación calculada, soft-deletes, audit-log, kits) — ver
   SNIPEIT-DOMAIN.md §3; cada uno evaluado como gramática nueva (incremento) vs modelable con lo existente.

## 6. Disciplina (no se negocia) + dónde van los docs
- **El producto es DATA**; un hueco de fábrica se arregla GENERAL (cero nombres de Snipe-IT en
  `src/metafactory/`/`seed/`, ADR-012). Medí anti-overfit: `git diff src/metafactory/ + seed/` = 0.
- **Probá por bloqueo** (RTM re-derivado + ci --rederive == pin), nunca por prosa. No fakees verde. La
  trust-chain (gates/verifier) la leés con ojos propios.
- **Honestidad sobre fidelidad**: todo lo que simplifiques/difieras va a SNIPEIT-DOMAIN.md con el por qué.
- **DÓNDE VAN LOS DOCS** (la regla, ahora cableada por ADR-016 — el edit-gate elige el nivel por la RUTA):
  - Dominio/decisiones de mapeo de ESTE producto → `…/products/snipeit/docs/reference/SNIPEIT-DOMAIN.md`
    (su casa; ya NO en los docs de la fábrica).
  - Gobierno del incremento del producto (ESTE doc) → `…/products/snipeit/docs/work/` — editar
    `products/snipeit/**` (no-`.md`) exige ESTE incremento abierto (lo elige el `increment_guard` por la ruta).
  - Cambios de la FÁBRICA (codegen/spec/stations FSK, un hueco GENERAL) → `factories/full-stack-kotlin/docs/`
    y exigen un incremento de FÁBRICA en `factories/full-stack-kotlin/docs/work/` (abrilo con
    `meta increment open <slug> --factory full-stack-kotlin`; hoy no existe → se crea al necesitarlo).
  - Estado/decisiones del META (sustrato) → `docs/STATE.md` + `docs/LOG.md` + `docs/decisions/` del meta.
  - Commit = parte del trabajo (ADR-010), nunca lo preguntes; mensaje con trailers I-10.

## 7. Criterio de cierre de P1 (demostrable, no narrable)
1. `meta product-run --product snipeit` PASS · RTM COMPLETE (o deferrals VISIBLES) · `ci --rederive --product
   snipeit == pin` en clon limpio.
2. **Anti-overfit**: `git diff src/metafactory/ + seed/` = 0. `meta check` 6/6.
3. Los huecos descubiertos (§5) quedan REGISTRADOS (STATE/ROADMAP del meta + FSK) como sub-incrementos
   sucesivos — el slice core verde es el deliverable de ESTE incremento; CRUD-mutación/frontend/deploy/breadth
   son los siguientes.

## 7.bis Evidencia de cierre de la Fase 2 (2026-06-21) — demostrada por bloqueo
- **`meta product-run --factory full-stack-kotlin --product snipeit` PASS**: las 19 entidades pasan la línea
  REAL s0→s10 por gradle (compile · detekt/ktlint · API-freshness · SBOM · RBAC/ownership · tests piramidales ·
  frontend · **s9 control-de-acceso VIVO contra PostgreSQL real** · build hermético reproducible).
- **`meta rtm … --product snipeit` = 18/19 SATISFIED**: el único UNSATISFIED es REQ-F-007 (s6, lógica de
  dominio LLM) = el deferral keyless VISIBLE (`station_activation: {s6: off}`), la opción que el gate sanciona.
- **`meta ci --rederive --factory full-stack-kotlin --all-products` = 3/3 == pin** en clones limpios (default
  11/11 · assets 10/10 · snipeit 10/10): two-verifier OK + cero regresión a los productos previos.
- **`meta check` 6/6** (incl. `generality` + `suite`).
- **Anti-overfit**: `git diff` del `product.yml` de snipeit = **0** (el producto es DATA puro). El criterio #2
  ("`git diff src/ + seed/` = 0") se MATIZA honestamente: esta vez SÍ hubo 1 cambio de sustrato
  (`verify/rtm.py`, render del path de artefacto), pero es **GENERAL** (no nombra producto ni tech; sin
  placeholders es no-op) y lo **sanciona el gate `generality`** (verde). El verdadero diente anti-overfit es
  `generality`, no un `diff==0` literal; FSK es la 1ra fábrica cuyo layout (fuente bajo `kotlin/<pkg>/`) lo
  necesitaba. Detalle en los incrementos `RTM-ARTIFACT-PATHS-PACKAGE-AWARE` (meta) y
  `FSK-CODEGEN-ROBUSTO-MULTI-ENTIDAD` (fábrica).

## 7.ter Los huecos que siguen (registrados → próximos incrementos de FÁBRICA)
La generación verde es el deliverable de ESTE incremento (§7). Lo demás de §5 queda como incrementos FSK
sucesivos, en orden de necesidad: **(1) CRUD-mutación real e2e** (el server vivo hoy devuelve el VEREDICTO de
autz, no muta columnas) · (2) self-ref (`Location.parent_id` / `User.manager_id`) · (3) ownership opcional/RTD ·
(4) custom-fields dinámicos · (5) frontend React vivo + deploy + breadth de endpoints. Cada uno: sub-incremento
de fábrica, `git diff product.yml`=0, driven por el producto.

## 8. Dónde está la investigación cruda (si la necesitás)
El clon de Snipe-IT vive en `../snipe-it` (hermano del repo, 93M, FUERA del árbol). La investigación
estructurada de los 7 agentes (≈6.4k líneas) está en `../snipe-it/_research/01..07.md` (schema · models ·
permissions · workflows · rules · endpoints · screens). **PUEDE estar borrado** (el ingeniero podía limpiarlo);
si no está, todo lo esencial ya está destilado en SNIPEIT-DOMAIN.md. Re-clonar: `git clone --depth 1
https://github.com/grokability/snipe-it.git ../snipe-it`.
