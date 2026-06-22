# Incremento FSK-COMPANY-SCOPING — multi-tenancy / acceso por atributo (ABAC), con FILTRADO de lectura

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO**
> (creado 2026-06-22T15:45Z). Cerralo flippeando este header a CERRADO (el `increment status` lee el header) **o**
> con `meta increment close --factory full-stack-kotlin`. Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-XENTITY-CYCLES con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (deferral 8 — el 1er eje de ACCESO-POR-ATRIBUTO + el último gran hueco de acceso)

**FSK está MUY MADURO.** Cerrados ya, product-driven por Snipe-IT: CRUD del grafo entero · self-ref · ownership
opcional/RTD · refs requeridos transitivos · **verbos checkout/checkin** (comportamiento) · **custom-fields
format** (validación) · **ciclos cross-entidad** (schema/seed). La trilogía de control de acceso (auth → RBAC →
ownership) está VIVA a runtime (s9, AppServer vs PG). **Lo que FALTA del modelo de acceso real de Snipe-IT: el
SCOPING por compañía (multi-tenancy, FMCS).**

**Este = deferral 8 (`SNIPEIT-DOMAIN.md §3 deferral 8 / §4 #8`)**: con `full_multiple_companies_support` ON, en
Snipe-IT un actor no-superadmin sólo ve/edita las filas de SU compañía (`company_id`). Casi toda entidad lleva
`company_id` (ya modelado como ref opcional en el blueprint, ver `product.yml`). **Por qué es el mejor próximo:**
1. **Bounded + product-driven + faithful** (el `company_id` ya existe en el blueprint; falta ENFORZARLO).
2. **Genuinamente NUEVO**: es el 1er eje que agrega **FILTRADO de LECTURA** (list/get, hoy PÚBLICOS) — todo lo
   anterior gateaba ESCRITURAS. Generaliza ownership (dueño = principal-match por-fila) a un **scope por atributo
   compartido** (company-match transversal, incl. lecturas). Es ABAC acotado, hermano de FSK-S14 pero distinto.
3. **Completa la historia de acceso**: auth → RBAC (rol×entidad) → ownership (fila×dueño) → **company-scope
   (fila×tenant, lectura+escritura)**.

**LA TENSIÓN A RESOLVER (leéla antes de diseñar)** — es una DECISIÓN de diseño, resolvela GENERAL:
- **El TOKEN hoy** (`_role_guard_kt`, ~L1968) es `"Bearer <rol>:<principalId>"` — `roleOf` ignora el sufijo,
  `principalOf` extrae el `<principalId>`. Company-scoping necesita ADEMÁS la **compañía del actor**. Avenida
  recomendada: extender el token a `"Bearer <rol>:<principalId>:<companyId>"` + `companyOf(token): Long?`
  (estático/determinista, JWT real sigue diferido) — byte-neutro para quien no usa el eje (sin `:<companyId>` →
  null, como `principalOf` sin `:<id>` → null). NO inventes un server de identidad.
- **El FILTRADO de LECTURA** es lo nuevo y delicado: hoy GET `/<plural>` y GET `/<plural>/{id}` son PÚBLICOS (sin
  guard). Con scoping, un actor no-bypass ve SÓLO su compañía. Decidí: ¿el GET ahora exige token? (probablemente sí
  para la entidad scopeada). El read-filter vive en el Repository (un `WHERE company_id = ?` parametrizado, type-bound
  a jOOQ — preferilo, es lo faithful) o filtrando en memoria sobre `all<E>RowsJson` (más frágil).

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥540000ms** (el sandbox mata
gradle: exit 144). **cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del
hook `stop_proof` al cerrar; restaurá con `cd /home/enzo/University/Integración/APP/Meta_Factory`).
Debe dar **PASS**, RTM snipeit **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **s7 PG 5435 · s9 puertos 18593-18595 + PG 5436/5437 · s11 18596** → NUNCA dos corridas en paralelo, NUNCA
dejes un `product-run`/`ci` en BACKGROUND al cerrar el turno (`stop_proof` re-corre la estación activa → colisión).

**2) EL DISEÑO (resolvelo GENERAL, cero nombres de dominio — `generality` verde es el anti-overfit real):**
- **Gramática del blueprint** (mismo patrón que `owned_by`/`owner_bypass_roles` en `_load_blueprint`, ~L254-278):
  `company_scoped: <campo ref>` por entidad (nombra la FK al tenant) + `company_scope_bypass_roles` (top-level, los
  roles que IGNORAN el scope, p.ej. superadmin). Fail-closed: exige `roles`; el campo debe ser un `ref`; los bypass
  ⊆ roles. Opt-in: sin `company_scoped` el producto es EXACTO (FSK-S15 intacto, byte-idéntico).
- **El guard** (hermano de `_ownership_guard_kt` ~L2006 + `_ownership_policy_kt` ~L2039): `CompanyScopeGuard.canAccess(
  actorRole, actorCompanyId, rowCompanyId, bypass) = actorRole in bypass || actorCompanyId == rowCompanyId` + un
  `CompanyScopePolicy` (registro entidad→campo tenant + bypass). type-safe sobre `Role`.
- **Runtime, s9** (`_app_server_kt` ~L3921 + `_app_server_handlers` + `_modify_verdict_kt`): el verdict de
  MODIFICACIÓN compone company-scope DESPUÉS de RBAC+ownership; y —lo NUEVO— el GET filtra por compañía (read-path).
  El token gana `companyOf`. Mirá cómo FSK-S15 cableó ownership en el dispatch para imitar el seam.
- **El contrato** (DES-6 inspectable): una vendor extension `x-company-scoped: <campo>` (como `x-owned-by`) →
  `route_check.py` (~L2181) gana un 5º modo `company_scope` que cruza el campo del contrato contra el Kotlin
  (tamper de un lado → MISMATCH, como `ownership`).

**EL DIENTE de dos lados** (criterio §6.2): el server siembra ≥2 filas de DISTINTA compañía + un actor de una de
ellas. **Lectura**: el actor no-bypass GET lista → ve SÓLO su compañía (la otra NO aparece); un actor bypass ve
todas. **Escritura/modificación**: PUT de una fila de OTRA compañía por no-bypass → 403; de la suya → 200; bypass →
200. **El tooth NATURAL vive en s9** (`access_control_live`, el server vivo, como FSK-S15/OWNERSHIP-OPTIONAL):
saboteá `CompanyScopeGuard.canAccess` (→ `true`) o el `WHERE company_id` del read-filter → el 403/el filtro
desaparece → **SÓLO** `access_control_live` rojo, hermanos s9 (`observability_live`, `frontend_consume_live`)
verdes → revertí → verde. ⚠️ **El sabotaje que muerde a RUNTIME NO puede introducir un hallazgo ESTÁTICO**
(detekt/ktlint en s2) que muerda antes — degradá la LÓGICA (return true / quitar el WHERE), no la forma Kotlin.
Lección CARA, §3.

---

## 1. ⚠️ RE-PIN — ¿hace falta?
Si el cambio vive DENTRO del check existente `access_control_live` (s9, ya pineado) — extendiendo el proof, no
agregando check/estación — el **`proof_sha` queda INTACTO** → pines byte-idénticos, **SIN re-pin** (como los
últimos ~10 incrementos: body/frontend/ownerless/refs/form/self-ref/ownership-opt/owned-refs/domain-ops/
custom-fields/xentity-cycles). **NO agregues check/estación nuevos si podés evitarlo.** `git diff snipeit/product.yml
≠ 0` es ESPERADO; el sustrato + default/assets product.yml DEBEN quedar en 0. `proof_sha = sha256({station,
sorted(check_name, exit)})` — invariante a qué hace el código. Si SÍ agregás un check/estación → re-pin justificado,
y **re-materializá el chasis por defecto** (restaurá los hand-edits de `stations/s*.yml`, re-pineá los 3 productos).

## 2. Maquinaria a REUTILIZAR (no la reinventes) — TODO en `codegen/scaffold_product.py`
- **`_load_blueprint`** (~L254-321) — la validación fail-closed de `owned_by`/`owner_bypass_roles`/`operations`;
  agregá `company_scoped`/`company_scope_bypass_roles` con el MISMO patrón (exige `roles`, campo es `ref`, bypass ⊆ roles).
- **`_role_guard_kt`** (~L1968) — el token estático y `principalOf`/`roleOf`. Agregá `companyOf` (extrae `<companyId>`
  del 3er segmento `:`). Byte-neutro: sin 3er segmento → null.
- **`_ownership_guard_kt`** (~L2006) / **`_ownership_policy_kt`** (~L2039) — los HERMANOS exactos de lo que vas a
  emitir (`CompanyScopeGuard`/`CompanyScopePolicy`). Copiá el shape (type-safe sobre `Role`, registro del blueprint).
- **`_app_server_kt`** (~L3921) + **`_app_server_handlers`** + **`_modify_verdict_kt`** — el server vivo s9: dónde se
  componen los guards en el dispatch (escritura) y dónde está el read-path (GET list/get) que hay que FILTRAR. El
  server YA siembra ≥2 filas (owner + RTD) → para el diente de scope sembrá filas de ≥2 compañías.
- **`_access_control_check_py`** (buscá `access_control_check` / `def _access_control_check`) — el proof client urllib
  (s9): asevera el veredicto de dos lados a RUNTIME. ACÁ va la aserción de lectura-filtrada + escritura-scopeada.
- **`_route_check_py`** (~L2181) — el analizador estático de rutas; agregá el modo `company_scope` (cruza
  `x-company-scoped` del contrato vs el Kotlin), análogo a `ownership` (~L2405).
- **`_openapi_yaml`** (~L326) — el contrato; agregá `x-company-scoped` (como `x-owned-by`, ~L371+).

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **EYEBALL SIN gradle ANTES de cada corrida lenta**: scratch python con `importlib` que carga `codegen/
  scaffold_product.py` HEAD vs working, `build_files(bp)` para default/assets, y **diffea** (deben quedar 68/68
  byte-idénticos). El scratch de esta sesión está en `/tmp/eyeball_xc.py` (HEAD vs working para default/assets +
  inyección de un campo en snipeit + validación) — adaptalo (inyectá `company_scoped` en una entidad de snipeit y
  dumpeá AppServer/CompanyScopeGuard/contrato/proof). Snapshot HEAD: `git show HEAD:factories/full-stack-kotlin/
  codegen/scaffold_product.py > /tmp/scaffold_head.py`. **Esto cazó el 100% de los problemas de byte-neutralidad
  ANTES de gradle.**
- **Un sabotaje que debe morder a RUNTIME no puede introducir un hallazgo ESTÁTICO antes.** En FSK-XENTITY-CYCLES
  comenté `out += deferred` (lado SQL/Python → no toca Kotlin → s2 verde). En FSK-OWNERSHIP-OPTIONAL saboteé
  `modifyVerdict`. **ktlint MaxLineLength=160 (MAX_LINE_LENGTH); detekt MagicNumber ignora -1/0/1/2; ReturnCount ≤ 2
  (`return when`); CyclomaticComplexMethod ≤ 15 (`@Suppress` opt-in en un dispatcher generado); NoUnusedImports +
  -Werror (imports condicionales sólo si el eje está activo).**
- **El handoff puede SOBRE- y SUB-estimar los sitios.** Verificá qué generadores YA manejan el caso ANTES de tocarlos
  (FSK-OWNERSHIP-OPTIONAL señalaba 2 sitios, generar destapó 4; FSK-OWNED-REQUIRED-REFS al revés). El read-path es el
  sitio que más fácil se sub-estima — hoy el GET es público, agregar token+filtro toca el dispatch Y el proof.
- **`meta verify` re-corre la estación ACTIVA con `build=False`** (no regenera). La activa tras un product-run es
  **s11**. Para un tooth en s9: **sabotear el codegen + `product-run`** (rojo en s9, las posteriores no corren) →
  revertir → `product-run` verde (restaura la activa verde, clave para que `stop_proof` no bloquee el cierre del turno).
- **`meta station` corre la META-línea (m00-m08), NO la línea FSK.** Para la línea FSK: `product-run`.
- **`proof_protect` DENIEGA tocar `.proof/` por shell** (incluso `sed`/`grep`/`cat` del log) — pero el **Read tool SÍ**
  lee `.proof/logs/` (es un RESUMEN: nombre de check + exit; el `exit=0` es la señal autoritativa).
- **`ci --rederive` por producto**: `--product snipeit`/`--product assets` (instancias) y SIN `--product` (la línea
  base/default). No existe `--product default`. Cada uno es un clon limpio (≈< 10 min) → corrélos UNO A UNO en foreground.
- **`dangerouslyDisableSandbox: true`** para gradle/docker. cwd SIEMPRE en la raíz. FOREGROUND, un producto a la vez.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento)
Refs **polimórficos** (deferral 2: checkout `assigned_to`→User|Location|Asset), **CANTIDADES** (sub-eje de los
verbos: checkout de Accessory/Consumable decrementa `qty` — OJO: requiere montar `operations` en entidades SIN dueño,
el server vivo hoy sólo monta verbos en la entidad con dueño → más que bounded), **soft-deletes/Actionlog** (deferral
12), **EAV dinámico a runtime** (custom-fields Avenue B), **depreciación calculada** (campo computado, necesita s6 o
columna derivada), **ref forward REQUERIDO que cierre ciclo** (sub-eje diferido de FSK-XENTITY-CYCLES).

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py` + quizá `factory.spec.yml`/`stations/*.yml` si la grama nueva necesita
  validación M0 o una estación) es nivel FÁBRICA → **este incremento** lo cubre (header ABIERTO).
- **La adopción** (`products/snipeit/product.yml`: declarar `company_scoped: company_id` en Asset etc. +
  `company_scope_bypass_roles`) es nivel PRODUCTO → abrí TAMBIÉN `meta increment open --factory full-stack-kotlin
  --product snipeit <slug>` ANTES de tocar `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) + `feat(snipeit): …` (product.yml) + `docs(fsk): cerrar
  FSK-COMPANY-SCOPING (§Evidencia) + abrir <siguiente>`.
- **Probá POR BLOQUEO**: `product-run --product snipeit` PASS · diente de dos lados vivo · `ci --rederive --factory
  full-stack-kotlin` (base) + `--product assets` + `--product snipeit` == pin (los 3) · `meta check` 6/6 (`generality`
  verde) · `git diff src/+seed = 0` · default+assets product.yml = 0.

## 6. Criterio de cierre (demostrable, no narrable)
1. Una entidad con `company_scoped: <campo ref>` declarada en `products/snipeit/product.yml` (p.ej. Asset scopeado
   por `company_id`) + `company_scope_bypass_roles` y `product-run --product snipeit` **PASS** — el server vivo
   FILTRA la lectura por compañía y gatea la escritura por compañía a runtime (s9).
2. **Diente de DOS lados verificado VIVO**: saboteá `CompanyScopeGuard.canAccess` (→ true) o el read-filter (quitá el
   `WHERE company_id`) → ROJO **sólo** en `access_control_live` (s9) → revertí → verde. Cubrí AMBOS lados nuevos:
   lectura-filtrada Y escritura-scopeada.
3. `ci --rederive` (base + assets + snipeit) == pin. `meta check` 6/6 (`generality` verde). `git diff src/metafactory +
   seed = 0`. `git diff` default+assets product.yml = 0. (Si tocaste el set de checks → re-pin justificado.)
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md §3 deferral 8 / §4` actualizados. Abrí el SIGUIENTE con su handoff (§7).

## 7. Qué viene DESPUÉS (para que sepas dónde estás parado) — y las ALTERNATIVAS a ESTE
Si al investigar decidís que company-scoping NO es el mejor próximo (es tu decisión con más contexto), las otras
candidatas BOUNDED, product-driven, framed honestamente:
- **Cantidades (qty)** [behavior, sub-eje de FSK-DOMAIN-OPS]: checkout de Accessory/Consumable decrementa stock +
  crea la fila de asignación. ⚠️ **Wrinkle**: el server vivo hoy monta `operations` SÓLO en la entidad con dueño
  (Asset, que NO tiene qty); para ejercerlo VIVO habría que montar verbos en entidades SIN dueño (Accessory) o poner
  un qty no-faithful en Asset → es 2 sub-ejes, no claramente bounded. Por eso NO lo elegí primero.
- **Checkout polimórfico (deferral 2)** [una primitiva NUEVA de ref]: `assigned_to` → User|Location|Asset (unión de
  targets). Más grande: toca el modelo de tipos (un ref que apunta a >1 entidad), el migration, el seed, el contrato.
  No es opt-in trivial. Hermano conceptual de los enums pero sobre refs.
- **Depreciación calculada (deferral 7)** [campo computado]: necesita s6 (lógica de dominio por LLM, hoy keyless) o
  una primitiva de columna derivada. Diferida por la dependencia keyless.
- **Orden general del push** (`SNIPEIT-DOMAIN.md §4`): ~~CRUD~~ ✅ · ~~self-ref~~ ✅ · ~~ownership opcional~~ ✅ ·
  ~~refs requeridos/seed transitivo~~ ✅ · ~~verbos checkout/checkin~~ ✅ · ~~custom-fields format~~ ✅ · ~~ciclos
  cross-entidad~~ ✅ · **(este) company-scoping** · diferidos DUROS (registry · Playwright · AppServer-en-contenedor
  con PG · checkout polimórfico · qty · EAV dinámico/Avenue B · depreciación calculada).
