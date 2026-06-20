<!-- meta:doc sha=8041296bdd242bc75f9adba300573d47e1b9ee8b updated=2026-06-20T23:36Z -->
<!-- meta:doc sha=PENDING updated=PENDING -->
# Incremento P1-SNIPE-IT-PRODUCT — construir el primer producto real (Snipe-IT)

> **Doc de gobierno.** Estado: **ABIERTO**. Cerralo con `meta increment close` (gateado: árbol limpio +
> estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total: todo lo que
> necesitás para avanzar está ACÁ o en los archivos que este doc nombra. La Fase 1 (el SPEC) está HECHA y
> commiteada; **tu trabajo es la Fase 2: GENERAR el producto por la línea FSK hasta verde.**

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**Lo hecho (Fase 1, commit `0f01ae1`):** el dominio real de Snipe-IT (grokability v8.6.3) está cosechado a un
blueprint FSK FIEL, validado por bloqueo SIN gradle (`scaffold --selftest`: 19 entidades → 66 archivos,
idempotente, 0 forward-refs). **Tu trabajo:** correr la línea FSK real (gradle) sobre ese spec, arreglar lo
que el compile/gates REALES rompan, hasta `product-run` PASS · RTM · `ci --rederive == pin`.

**Los 3 archivos que tenés que leer primero (en orden):**
1. `factories/full-stack-kotlin/products/snipeit/product.yml` — **el SPEC** (la fuente; 19 entidades). Es DATA.
2. `factories/full-stack-kotlin/docs/reference/SNIPEIT-DOMAIN.md` — el dominio completo + el mapeo + **12
   deferrals honestos** + **las 4 restricciones DURAS de FSK** (las repito en §3 acá). Leelo entero.
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
| 2 | **Generar el slice core a verde** por la línea FSK (gradle): product-run PASS · RTM · ci --rederive == pin. Arreglar lo que el compile/gates REALES rompan (gap de fábrica → GENERAL). | ⏳ **ACTIVA** |
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
- **DÓNDE VAN LOS DOCS** (la regla, aclarada esta sesión):
  - Dominio/decisiones de mapeo → `factories/full-stack-kotlin/docs/reference/SNIPEIT-DOMAIN.md`.
  - Cambios de la FÁBRICA (codegen/spec/stations) → `factories/full-stack-kotlin/docs/{STATE,LOG}.md`.
  - Gobierno del incremento (ESTE doc) → `docs/work/` del **meta** — es donde el `increment_guard` ACTIVO
    (`$CLAUDE_PROJECT_DIR/.claude/hooks/`) trackea el incremento abierto y te deja editar el codegen de la
    fábrica. Las hooks anidadas de FSK son DATA dormida en este árbol (sólo cuentan en un checkout standalone).
  - Estado del meta → `docs/STATE.md` + `docs/LOG.md` del meta. Commit = parte del trabajo (ADR-010), nunca lo
    preguntes; mensaje con trailers I-10.

## 7. Criterio de cierre de P1 (demostrable, no narrable)
1. `meta product-run --product snipeit` PASS · RTM COMPLETE (o deferrals VISIBLES) · `ci --rederive --product
   snipeit == pin` en clon limpio.
2. **Anti-overfit**: `git diff src/metafactory/ + seed/` = 0. `meta check` 6/6.
3. Los huecos descubiertos (§5) quedan REGISTRADOS (STATE/ROADMAP del meta + FSK) como sub-incrementos
   sucesivos — el slice core verde es el deliverable de ESTE incremento; CRUD-mutación/frontend/deploy/breadth
   son los siguientes.

## 8. Dónde está la investigación cruda (si la necesitás)
El clon de Snipe-IT vive en `../snipe-it` (hermano del repo, 93M, FUERA del árbol). La investigación
estructurada de los 7 agentes (≈6.4k líneas) está en `../snipe-it/_research/01..07.md` (schema · models ·
permissions · workflows · rules · endpoints · screens). **PUEDE estar borrado** (el ingeniero podía limpiarlo);
si no está, todo lo esencial ya está destilado en SNIPEIT-DOMAIN.md. Re-clonar: `git clone --depth 1
https://github.com/grokability/snipe-it.git ../snipe-it`.
