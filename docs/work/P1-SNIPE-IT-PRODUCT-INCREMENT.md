<!-- meta:doc sha=d584119aaa69eac4f104892967b3013ff42095bb updated=2026-06-20T18:57Z -->
# Incremento P1-SNIPE-IT-PRODUCT — el PRIMER PRODUCTO real

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-20T18:50Z). Cerralo con `meta increment close`
> (o flip del header a CERRADO). Todo cambio de código vive acá (ADR-010).
>
> **HANDOFF (escrito 2026-06-20 por la sesión que cerró FSK-S15/endpoints-vivos, con el contexto fresco; la
> decisión de dirección la tomó el ingeniero).** Este doc es AUTOCONTENIDO a propósito: asumí que mi contexto
> murió (`/clear`). **Empezás EN FRÍO y eso es DELIBERADO** — esta sesión que escribe está cargada de contexto
> de construir FSK; la INVESTIGACIÓN profunda de Snipe-IT (desmenuzar el repo real, derivar el dominio) merece
> una sesión limpia con presupuesto de contexto entero. Construí por bloqueo, documentá en el gate, commit por
> fase con trailers I-10.
>
> **EL GIRO (decisión del ingeniero, 2026-06-20):** se cierra la fase de PROFUNDIZAR FSK y se abre la de
> PRODUCIR. FSK cruzó el umbral: 5 ejes R2 (campos arbitrarios · workflows · RBAC · ownership · **endpoints
> vivos / control de acceso enforzado a RUNTIME**) sobre una línea s0–s10 que genera una app web REAL
> (contrato OpenAPI fuente única → server Kotlin + client TS · PostgreSQL viva jOOQ/Flyway · trilogía
> auth→RBAC→ownership enforzada a runtime contra la PG · pirámide de tests · a11y/perf · observabilidad · build
> hermético). El próximo paso de MAYOR valor NO es otro eje especulativo (ABAC/LLM-rules = rendimientos
> decrecientes; CRUD-completo/frontend = especulación sin un dominio real que los forme) sino **shippear el
> PRIMER PRODUCTO real** — doctrina anti-fachada (M8) + precedente R1 (el producto rico expuso los huecos
> REALES mejor que adivinarlos). **El producto: Snipe-IT real** (gestión de activos de grado-producción, el
> mandato original; la instancia `assets` actual es sólo un BOCETO Snipe-IT-lite, no un producto).

## 0. Orientación — leé esto primero (orquestador en frío)
1. `docs/STATE.md` §Ahora → el eje Reutilización (R1 ✅ lifecycle · R2·FSK ✅: 5 ejes). FSK es una fábrica
   MADURA que genera una app que CORRE con control de acceso enforzado a runtime. Este incremento la USA para
   producir, no la profundiza (salvo los huecos que el producto real fuerce — §4).
2. **`docs/work/FSK-S15-LIVE-ENDPOINTS-INCREMENT.md` (CERRADO)** — el predecesor: el server vivo que enforza
   auth→RBAC→ownership a runtime. Su **§7 (scope honesto)** lista los huecos que un producto real VA a tocar:
   CRUD-completo (mutación real de columnas, no sólo el veredicto de autz), frontend React que CONSUME los
   endpoints, deploy (Docker build+push). Esos son el trabajo de fábrica que el producto va a FORMAR (§4).
3. **R1 / lifecycle de instancia (ADR-015)** — cómo nace un producto: `factories/full-stack-kotlin/products/
   <p>/` con SÓLO `product.yml` (el blueprint del dominio) + `pinned_verdict.json`; el sustrato re-deriva el
   spec efectivo (`base ⊕ product.yml`) + la línea por corrida. `meta product new --factory full-stack-kotlin
   --product snipeit` lo bootstrapea. Mirá `products/assets/product.yml` — es el MOLDE EXACTO de un blueprint
   de producto (entidades/fields/refs/enums/workflows/roles/write_roles/owned_by/owner_bypass_roles) y el
   boceto Snipe-IT-lite que vas a SUPERAR con el dominio real.
4. **El vocabulario que FSK YA soporta** (lo que tu blueprint puede expresar HOY, sin tocar la fábrica) — leé
   `factories/full-stack-kotlin/codegen/scaffold_product.py::_load_blueprint` (la gramática + sus dientes
   fail-closed): tipos `string/boolean/int/number/date/ref/enum` + opcionalidad (`required: false`) + `unique`
   · workflows (`enum` con `initial`+`transitions`) · RBAC (`roles` + `write_roles` por entidad) · ownership
   (`owned_by` + `owner_bypass_roles`). Si el dominio Snipe-IT pide algo FUERA de esto, es un hueco de fábrica
   (§4) — un incremento GENERAL, no un hack en el product.yml.

## 1. Objetivo
Producir un **producto Snipe-IT real** (gestión de activos de grado-producción) como instancia de FSK
(`products/snipeit/`), derivado FIELMENTE del sistema real, corrido por la línea FSK hasta **RTM COMPLETE**
(o con deferrals HONESTOS y visibles, como `assets` con s6) y `ci --rederive == pin` en clon limpio. Es un
DELIVERABLE real, no un fixture de co-validación. El producto va a EXPONER los huecos reales de FSK (§4); esos
se arreglan como contenido GENERAL de fábrica (codegen+spec, `git diff src/metafactory/+seed/` = 0 idealmente,
o sólo mecanismo general), DRIVEN por el producto — no especulados.

## 2. El trabajo es RESEARCH-FIRST (por eso una sesión nueva)
**Insumo del ingeniero:** el link del repo de Snipe-IT (canónico: `https://github.com/snipe/snipe-it` —
Laravel/PHP; CONFIRMALO con el ingeniero al arrancar). **Snipe-IT es PHP/Laravel; FSK genera Kotlin/TS/PG** →
NO portás el código: **cosechás el DOMINIO** (modelo de datos + reglas) y lo expresás como blueprint FSK.

**Cómo desmenuzar (fan-out con sub-agentes — para esto SON):** lanzá agentes `Explore`/`general-purpose` sobre
un clon del repo para mapear, en paralelo, las distintas caras del dominio y devolver UN resumen estructurado:
- **Entidades + campos**: los modelos Eloquent (`app/Models/`) + las migraciones (`database/migrations/`) =
  la fuente dura del schema (tablas, columnas, tipos, nullability, unique, FKs). Núcleo: Asset, AssetModel,
  Category, Manufacturer, Location, Company, Supplier, User, License, Accessory, Consumable, Component,
  Depreciation, StatusLabel, CustomField, y las de checkout/checkin/audit.
- **Relaciones (refs)**: las FKs entre tablas → tus campos `ref` (`to:`). Snipe-IT tiene una topología rica
  (Asset → AssetModel → Category/Manufacturer; Asset → Location/Company/Supplier/StatusLabel; checkouts
  polimórficos). Mapeá el grafo; FSK exige que un `ref` apunte a una entidad declarada (fail-closed).
- **Roles/permisos**: el sistema de permisos (`app/Http/...`, `config/permissions.php`, roles superadmin/
  admin/user) → tu `roles` + `write_roles` por entidad. Snipe-IT es granular; mapeá a una política tratable.
- **Workflow del activo**: el ciclo de vida (Status Labels: Ready to Deploy / Deployed / Pending / Archived /
  Broken / Lost...) → un `enum status` con `initial`+`transitions` (como `assets` ya hace, pero el REAL).
- **Ownership**: a quién "pertenece"/está asignado un activo (checkout a un User/Location/Asset) → `owned_by`
  (el campo ref del responsable) + `owner_bypass_roles` (admin administra todo). Esta es la esencia de
  ownership-a-nivel-de-fila que FSK-S14/S15 enforza: un manager toca SUS activos, admin todos.

**Producto de la investigación:** un `products/snipeit/product.yml` FIEL (entidades reales, campos reales,
refs reales, roles/workflow/ownership reales) + un breve `docs/reference/SNIPEIT-DOMAIN.md` que justifique las
decisiones de mapeo (qué se incluyó, qué se simplificó/difirió y POR QUÉ — honestidad, no over-claim).

## 3. Cómo instanciar y correr (R1 lifecycle, mecánica YA probada)
1. `meta product new --factory full-stack-kotlin --product snipeit` → crea `products/snipeit/product.yml`
   (editalo con el dominio derivado). `meta = PYTHONPATH=src python3 -m metafactory.cli`.
2. `meta product-run --factory full-stack-kotlin --product snipeit` → re-materializa la instancia + corre la
   línea s0–s10. Iterá hasta verde (el blueprint fail-closed te va a gritar lo malformado en M0/s0).
3. `meta rtm --product snipeit` (COMPLETE o deferrals visibles) → `meta pin --product snipeit` → `meta ci
   --rederive --product snipeit` (== pin en clon limpio).
4. Co-validación ADR-014 ya la dan los productos existentes (demo + assets); el de Snipe-IT es el 3ro.

## 4. Los huecos que el producto VA a forzar (honesto, de FSK-S15 §7) — arreglalos como fábrica GENERAL
Driven por el producto, NO especulados. Cada uno probablemente su propio sub-incremento, contenido de fábrica
(`codegen/`+spec; `git diff src/metafactory/+seed/` = 0 idealmente). En orden de probable necesidad:
1. **CRUD real (mutación)**: hoy POST/PUT del server vivo (FSK-S15) devuelven el VEREDICTO de autorización
   (403/200/201) pero no MUTAN columnas end-to-end (la persistencia probada es seed+read vía Repository). Un
   producto usable necesita INSERT/UPDATE/DELETE reales tipados (jOOQ) bajo el control de acceso ya enforzado.
   El diente: un round-trip e2e (POST crea → GET lista lo creado → PUT muta → GET ve el cambio → DELETE borra).
2. **Frontend React vivo que CONSUME los endpoints**: hoy existen los TIPOS TS del contrato (s0) + una UI
   estática a11y (s8), pero NADA cablea una UI viva al server vivo. Un producto necesita el front que llama a
   los endpoints (e2e, p.ej. Playwright — que FSK-S15 dejó declared-deferred). Diente: un flujo de browser real.
3. **Deploy** (Docker build+push reproducible): el Dockerfile existe (s10, base pineada por digest), el
   build+push de la imagen quedó declared-deferred. Un producto deployable lo necesita.
4. **Lo que el dominio Snipe-IT pida y FSK no exprese** (p.ej. custom fields dinámicos, checkout polimórfico,
   depreciación calculada, multi-tenancy por Company): cada uno → evaluar si es gramática nueva del blueprint
   (incremento de fábrica GENERAL) o si se modela con lo existente. NO hackear el product.yml con casos
   especiales; si FSK no lo expresa, es un eje de fábrica.

## 5. Fases (plan; el orquestador las refina) — NO hervir el océano en un incremento
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Investigación + blueprint fiel.** Fan-out de agentes sobre el repo Snipe-IT → dominio estructurado → `products/snipeit/product.yml` + `docs/reference/SNIPEIT-DOMAIN.md` (decisiones de mapeo, honestas). | ⏳ |
| 2 | **Slice vertical core a verde.** Entidades núcleo (Asset/AssetModel/Category/Manufacturer/Location/User/StatusLabel + workflow del activo + checkout-ownership + roles) por la línea FSK → product-run PASS · RTM (COMPLETE o deferrals visibles) · ci --rederive == pin. | ⏳ |
| 3 | **Huecos que el slice exponga** (§4: probablemente CRUD-mutación primero) como fábrica GENERAL — un sub-incremento por hueco, `git diff src/+seed=0`. | ⏳ |
| 4 | **Breadth** (License/Accessory/Consumable/Component/Audit/Depreciation…) + frontend vivo + deploy, en incrementos sucesivos. | ⏳ |
| 5 | **Cierre del slice.** STATE/ROADMAP/LOG + evidencia (RTM, pin, ci --rederive, anti-overfit). | ⏳ |

## 6. Disciplina (no se negocia)
- **El producto es DATA** (`product.yml` + lo derivado); un hueco de fábrica se arregla GENERAL (cero nombres
  de Snipe-IT en `src/metafactory/`/`seed/`, ADR-012). Anti-overfit medido: `git diff src/metafactory/+seed/`.
- **La trust-chain ya existe** (la columna FSK + R1 lifecycle): el producto se verifica por la línea FSK
  existente, no inventás gates. Probá por bloqueo (RTM re-derivado + ci --rederive == pin), nunca por prosa.
- **Honestidad sobre fidelidad**: si simplificás/diferís parte del dominio Snipe-IT, DECILO en
  `SNIPEIT-DOMAIN.md` con el por qué (deferral visible, no over-claim) — igual que `assets` difiere s6 keyless.
- **Agentes para el RESEARCH fan-out** (su propósito); la trust-chain (gates/verifier) la leés con ojos propios.

### Lecciones caras de correr la línea FSK (NO re-aprendas — son de FSK-S11..S15):
- **El sandbox de Bash MATA gradle** (exit 144 sin output): toda corrida de línea/gradle necesita
  `dangerouslyDisableSandbox: true`. Corré la línea en **FOREGROUND**, **por-producto** (`--product snipeit`),
  NO `--all-products` (dos líneas no entran en 600s).
- **Server vivo largo bajo infra_up: corré por `java -cp build/install/<pkg>/lib/*` del dist (proceso plano),
  NO `gradle run`/JavaExec** (el daemon de gradle puede forkear el JVM fuera del process-group → leak del
  puerto en el teardown → falsa-verde). installDist da el `lib/` con todas las deps. (Lección FSK-S15.)
- **`proof_protect` DENIEGA tocar `.proof/` por shell** (incluso leer): usá `meta rtm`/`recall`/`journal`.
- **Mantené el cwd de Bash en la raíz del repo** + paths absolutos + subshells `( cd <abs> && … )` (un `cd`
  filtrado a un subdir rompe el cierre de turno — 4 hooks cwd-relativos, memoria `no-cd-subdirs-hook-deadlock`).
- **Las INSTANCIAS se re-materializan en cada corrida** (no editás sus `stations/` a mano); el DEFAULT no
  (ahí sí se appendea a mano `stations/<id>.yml`). El producto Snipe-IT es una instancia → sólo editás su
  `product.yml`.
- **PG/server vivos = docker dependiente** (SAFE-3, decisión de fidelidad): el digest de Postgres ya está
  cacheado (s1/s7/s9). Puertos DATA fuera del rango efímero (s1=5434, s7=5435, s9 AC=5436, server obs=18593,
  AC=18594) — si agregás infra viva nueva, elegí puertos/contenedores propios.

## 7. Criterio de cierre (de este incremento; demostrable, no narrable)
1. `products/snipeit/product.yml` existe y deriva FIELMENTE el dominio Snipe-IT núcleo (Fase 1+2), con
   `docs/reference/SNIPEIT-DOMAIN.md` justificando el mapeo (inclusiones + deferrals honestos).
2. `meta product-run --product snipeit` PASS · RTM COMPLETE (o deferrals visibles) · `ci --rederive --product
   snipeit == pin` en clon limpio.
3. **Anti-overfit**: `git diff src/metafactory/ + seed/` = 0 (el producto es DATA; todo hueco de fábrica
   arreglado fue mecanismo GENERAL). `meta check` 6/6.
4. Los huecos descubiertos (§4) quedan REGISTRADOS (STATE/ROADMAP) como los siguientes incrementos — el slice
   vertical core verde es el deliverable de ESTE; breadth/CRUD-completo/frontend/deploy son sucesivos.
