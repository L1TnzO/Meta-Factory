<!-- meta:doc sha=1add96f125cd17d46bae36af1885e2fb15bd91e2 updated=2026-06-18T22:13Z -->
# Incremento FSK-S1-SCHEMA-PG — Full-Stack Kotlin · datos (s1)

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-18T22:13Z) (creado 2026-06-18T21:13Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Otro orquestador
> construye desde acá. Si algo no está acá (o en la spec/handoff que referencia), no existe. Orden de lectura: §0.

## 0. Si llegás sin contexto, leé en este orden
1. Este doc entero (es el plan + handoff de la SEGUNDA estación de build de la fábrica FSK).
2. `docs/work/FSK-S0-SCAFFOLD-CONTRACT-INCREMENT.md` (**CERRADO**) — la estación anterior: cómo quedó el
   codegen determinista, el toolchain pineado (`codegen/assets/`) y la línea s0 verde e2e. s1 cuelga de s0.
3. `docs/work/FULLSTACK-KOTLIN-INCREMENT.md §6` (DISEÑO, **CERRADO**) — la línea s0–s10 y el DAG (autoridad).
4. `specs/full-stack-kotlin.factory.spec.yml` — el blueprint. Acá viven las caps `datos_esquema_chequeado`
   (DES-12) y `datos_durables_vivos` (DES-4) y la `machinery.infra` con el container `postgres`.
5. `specs/full-stack.factory.spec.yml` + `factories/full-stack/codegen/scaffold_product.py` — la PLANTILLA TS
   de una línea con `infra_up` (DB viva por socket). El análogo MAT-3/ASF de **Postgres real bajo `infra_up`
   con `bootstrap`** (`factories/agent-systems-factory/`, s3 cross-instancia vs Postgres) es tu referencia
   más cercana para la DB viva en Kotlin.

## 1. Objetivo (qué deja TERMINADO este incremento — una frase)
**s1 en `built` por proof real**: el producto Kotlin gana una capa de datos donde **la DB GRITA en
compilación** (esquema PostgreSQL versionado por Flyway + tipos jOOQ generados del schema vivo: un query a una
columna inexistente = error de `kotlinc`, DES-12) **y persiste contra una PostgreSQL VIVA** (un test de
integración del producto hace un round-trip create+list contra una PG efímera levantada por `infra_up`; DB
caída → rojo, DES-4). Cuelga de s0 (`depends_on: [s0]`) y es la base de la lógica/pruebas de s6–s7.

## 2. Alcance EXACTO — capacidades, primitivas, proof_checks (de la spec, no inventar)
| capability (L1) | DES | proof_check (s1) | runs_in | requisito |
| --- | --- | --- | --- | --- |
| `datos_esquema_chequeado` | DES-12 | `schema_checked` (Flyway up+down en PG efímera + jOOQ codegen del schema vivo + `kotlinc`; romper una columna usada en un query → compile error) | product_env ⊕ infra_up | REQ-F-003 (re-añadir) |
| `datos_durables_vivos` | DES-4 | `db_roundtrip_live` (`infra_up` levanta PostgreSQL + bootstrapea el toolchain del producto; Kotest de integración create+list contra la DB viva; DB caída → rojo) | infra_up | REQ-F-004 (re-añadir) |

- Ambas caps arrancan `status: planned`; flipean a `built` **sólo** con `proof` real recompuesto (SAFE-7) — el
  `increment_guard`/columna lo impiden, no es disciplina. Re-añadir `REQ-F-003`/`REQ-F-004` al bloque
  `requirements` (con `satisfied_by`/`verified_by` → los proof_checks de s1) — hoy DIFERIDAS en la spec.
- **NO** tocar s2–s10 (cuelgan de s1; son sus propios incrementos, "capacidad por capacidad").

## 3. Dependencia bloqueante — el toolchain de datos hermético (medir, no asumir)
Medido en s0 (`command -v`): **docker ✅** (29.5), **psql ✅** (PG 18.3), **java ✅** (JDK 21 pineado en
`codegen/assets/`). Lo que s1 agrega y hay que pinear/vendorizar (como s0 pineó Gradle/Kotlin):
- **Imagen PostgreSQL pineada por digest** (p.ej. `postgres:18-alpine@sha256:…`) — sin digest, `ci --rederive`
  no es reproducible. Es DATA de la fábrica (`machinery.infra.services[postgres]`), no del sustrato.
- **jOOQ + Flyway por el wrapper Gradle pineado** (deps del caché Gradle; red sólo en el 1er resolve, como s0).
  **DECISIÓN de build (refina §6)**: jOOQ usa **DDLDatabase** → deriva los tipos PARSEANDO los `.sql` de
  Flyway, **SIN DB viva** → el gate DES-12 (`schema_checked` = `jooqCodegen` + `compileKotlin`) es **hermético**
  y NO acopla la compilación a docker. La DB viva queda SÓLO para el round-trip DES-4 (`db_roundtrip_live`,
  `infra_up`). Es mejor que el "DB arriba DURANTE el build" que §6 marcó como riesgo — separación limpia
  DES-12 (compile, hermético) ⟂ DES-4 (runtime, vivo). Plugin oficial `org.jooq.jooq-codegen-gradle` (Gradle 9).
- **Hermeticidad**: `ci --rederive` re-levanta el container (Testcontainers/docker) en clon limpio. SAFE-3 pasa
  a depender de docker para esta fábrica — la MISMA decisión de ingeniero que MAT-3 (ASF vs Postgres real) por
  fidelidad a §12. Si el entorno del clon no tiene docker, el residual se declara `declared-deferred` VISIBLE
  (no se finge verde), igual que ASF defería infra solo-CI.

## 4. Plan por fases (cada cambio de código vive en este incremento; commit por fase, trailers I-10)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Esquema + migraciones** ✅ — el codegen emite `src/main/resources/db/migration/V1__init.sql` (Flyway versionado) desde `domain.product` (3 entidades; tablas en plural evitan `user` reservado de PG) + FKs en orden de dependencia. | ✅ |
| 2 | **jOOQ (DDLDatabase) + DES-12 hermético** ✅ — jOOQ deriva tipos de los `.sql` SIN DB viva; `Repository.kt` usa queries tipadas (todas las columnas); **diente VIVO**: drop de una columna usada → `Unresolved reference` → `gradle` exit 1; regen → exit 0. | ✅ |
| 3 | **DB viva (DES-4) por `infra_up`** ✅ — `db_roundtrip_live` (container postgres pineado por digest, `bootstrap`=compile). `DbRoundTrip.kt`: Flyway migrate + jOOQ create/list + clean (reversibilidad). **Diente de dos lados VIVO**: DB caída → connect refused → `gradle` exit 1. | ✅ |
| 4 | **s1 materializada + verde e2e** ✅ — s1 en `station_sequence` (`depends_on: [s0]`) + REQ-F-003/004; `validate`+`design-review` 0; `product-run` PASS; **RTM COMPLETE 5/5** (artifacts reales `V1__init.sql` + `DbRoundTrip.kt`); pin; **m06 `clean_runner` == pineado**. | ✅ |
| 5 | **Pin + cierre** ✅ — `ci --rederive` **2/2 == pineado** (re-levanta el container en clon limpio); M0–M8 verde; **anti-overfit `git diff src/metafactory/ + seed/` = 0**; dummy intacta (5/5); STATE/ROADMAP; `meta increment close`. | ✅ |

## 5. Criterio de cierre (demostrable por BLOQUEO, no narrable)
1. `meta product-run --factory full-stack-kotlin` corre s0+s1 y queda **PASS**; pin escrito.
2. `meta ci --rederive --factory full-stack-kotlin` re-deriva en clon limpio **== pineado** (re-levanta la PG
   efímera; hermético salvo la dependencia de docker declarada §3).
3. **RTM** cubre **REQ-F-003** (`schema_checked`) y **REQ-F-004** (`db_roundtrip_live`) con artifacts reales.
4. **≥2 dientes VIVOS**: (a) drift de schema (drop/rename de una columna usada por un query) → `kotlinc` rojo
   vía jOOQ; regen → verde (DES-12). (b) DB caída → el round-trip del producto rojo; DB arriba → verde (DES-4,
   diente de dos lados). Cada uno: corromper→rojo, regenerar→verde.
5. **`meta check` 6/6** verde; **anti-overfit**: `git diff src/metafactory/ + seed/` = **0** (o sólo mecanismo
   general; cero nombres de jOOQ/Flyway/Postgres en el sustrato — son DATA de la fábrica, como MAT-3/MAT-7).
   Las otras fábricas (dummy/full-stack/iot/ASF) **intactas** (`ci` == pineado, principio #4).

## 6. Riesgos / notas honestas (resueltas en el build)
- **Orden DB-viva-durante-el-build** — RESUELTO por la decisión §3: jOOQ **DDLDatabase** parsea los `.sql`,
  NO necesita la PG arriba para el codegen → DES-12 hermético (compile sin docker). La PG viva queda SÓLO
  para DES-4 (round-trip runtime). Separación más limpia que el acople compile↔docker que se temía.
- **Determinismo del codegen jOOQ** — MOOT para los gates: el output de jOOQ vive en `build/generated-jooq`
  (gitignored, producido por Gradle, no por el scaffold) → no entra en `scaffold_idempotent` (que compara la
  salida del scaffold Python) ni en el `proof_sha`. `ci --rederive` 2/2 == pineado lo confirma.
- **docker en el clon de `ci --rederive`** — el entorno lo tiene (29.5); SAFE-3 depende de docker para esta
  fábrica (decisión del ingeniero, fidelidad a MAT-3). Si un clon no lo tuviera, el residual se declararía
  VISIBLE (no se finge) — no fue necesario.
- s1 es codegen DETERMINISTA (sin LLM). La **lógica de dominio viva por LLM** es s6 (DES-8, patrón MAT-2),
  otro incremento — no acá.

## 7. Evidencia de cierre (por bloqueo, 2026-06-18 — re-derivable, no narrada)
- **M0–M8 verde**: `validate`+`design-review` 0 problemas · `product-run` PASS (s1: `schema_checked` ok ·
  `db_roundtrip_live` ok) · m03–m05 evidencia · **m06 `clean_runner` == pineado** (re-deriva la línea
  Kotlin/jOOQ + el round-trip docker en clon limpio) · m07 harness · m08 product_e2e.
- **RTM COMPLETE 5/5**: REQ-F-001/002/NF-001 (s0) + **REQ-F-003** ← `datos_esquema_chequeado` [s1,
  `…/db/migration/V1__init.sql`✓] + **REQ-F-004** ← `datos_durables_vivos` [s1, `…/webapp/DbRoundTrip.kt`✓].
- **`ci --rederive` full-stack-kotlin 2/2 == pineado** (re-levanta el contenedor PG en árbol limpio).
- **2 dientes VIVOS (exit codes reales)**: (a) DES-12 — drop de una columna usada → `Unresolved reference` →
  `gradle` **exit 1**; regen → **exit 0**. (b) DES-4 — DB caída → `FSK_DB_ROUNDTRIP_FAIL: Connection refused`
  → `gradle` **exit 1** (el negativo embebido de `infra_up` ya lo exige cada corrida verde).
- **Anti-overfit**: `git diff src/metafactory/ + seed/` = **0**. La capa de datos (jOOQ 3.21.6 / Flyway
  10.20.1 / `postgres@sha256:e013e867`) vivió 100% en la fábrica (DATA); compuso sobre `infra_up` (E1/MAT-3)
  + `product_env` sin tocar el sustrato — la propiedad de composición §6 del ROADMAP, como MAT-7/FSK-s0.
- **Fábricas intactas**: sólo cambió `factories/full-stack-kotlin/`; dummy `ci` 5/5 == pineado (spot-check);
  full-stack/iot/ASF inalteradas por construcción (cero diff fuera de la fábrica + sustrato).
