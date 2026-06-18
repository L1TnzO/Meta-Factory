<!-- meta:doc sha=cd1840da3d0a03f2c78d53b79db498c09d221249 updated=2026-06-18T21:14Z -->
# Incremento FSK-S1-SCHEMA-PG — Full-Stack Kotlin · datos (s1)

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-18T21:13Z). Cerralo con `meta increment close`
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
- **jOOQ + Flyway por el wrapper Gradle pineado** (plugins/deps resueltos del caché Gradle vendorizado de s0,
  o agregados al caché offline). El codegen jOOQ corre sobre el **schema vivo** que Flyway migró en la PG
  efímera → necesita la DB arriba DURANTE el build (orden: `infra_up` up → Flyway migrate → jOOQ codegen →
  `compileKotlin`). Decidir si jOOQ corre dentro del `bootstrap` de `infra_up` o como paso del build Gradle.
- **Hermeticidad**: `ci --rederive` re-levanta el container (Testcontainers/docker) en clon limpio. SAFE-3 pasa
  a depender de docker para esta fábrica — la MISMA decisión de ingeniero que MAT-3 (ASF vs Postgres real) por
  fidelidad a §12. Si el entorno del clon no tiene docker, el residual se declara `declared-deferred` VISIBLE
  (no se finge verde), igual que ASF defería infra solo-CI.

## 4. Plan por fases (cada cambio de código vive en este incremento; commit por fase, trailers I-10)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Esquema + migraciones**: el codegen de fábrica emite `db/migration/V1__init.sql` (Flyway) desde `domain.product` (las 3 entidades de s0) + la config jOOQ. Migración **reversible** (up/down). Smoke: Flyway migrate+revert contra una PG efímera. | ⏳ |
| 2 | **jOOQ del schema vivo + DES-12 con dientes**: jOOQ genera tipos del schema migrado; un repository Kotlin tipado usa un query real; **diente**: borrar/renombrar una columna usada → `kotlinc` rojo (`Unresolved reference`); regen → verde. | ⏳ |
| 3 | **DB viva (DES-4) por `infra_up` + `bootstrap`**: declarar el check `db_roundtrip_live` (kind `infra_up`, container postgres pineado, `bootstrap` = toolchain del producto). Kotest de integración: create+list round-trip contra la DB viva. **Diente de dos lados**: DB caída → rojo. | ⏳ |
| 4 | **s1 ejecutable + materializado + verde e2e**: re-añadir s1 a `station_sequence` (`depends_on: [s0]`, activa, proof_checks) + REQ-F-003/004; `validate`+`design-review` 0 problemas; `meta product-run` PASS; **RTM COMPLETE** con artifacts reales (`db/migration/`, `DbIntegrationTest.kt`); pin; **m06 `clean_runner` == pineado**. | ⏳ |
| 5 | **Pin + cierre**: caps→`built`; `product-run` PASS + **`ci --rederive` == pineado** (re-levanta el container); RTM verde; M0–M8 verde; **anti-overfit `git diff src/metafactory/ + seed/` = 0** (o sólo mecanismo general — `infra_up`/`product_env` ya existen de E1/MAT-3; jOOQ/Flyway/PG = DATA); STATE/ROADMAP; `meta increment close`. | ⏳ |

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

## 6. Riesgos / notas honestas
- **Orden DB-viva-durante-el-build**: jOOQ necesita el schema MIGRADO vivo para generar tipos; eso obliga a
  tener la PG arriba en el build, no sólo en el test. Es la diferencia con la DB-en-test de full-stack-TS:
  acá la DB participa de la COMPILACIÓN (DES-12). Resolver dónde vive ese paso (bootstrap de `infra_up` vs
  build Gradle) antes de escribir el codegen.
- **Determinismo del codegen jOOQ**: el output de jOOQ debe ser idéntico entre corridas (orden de columnas,
  timestamps) o `scaffold_idempotent`/`ci --rederive` rompe. Pinear versión de jOOQ y normalizar el output.
- **docker en el clon de `ci --rederive`**: si no está disponible, declarar el residual VISIBLE (no fingir);
  el gate de s1 no puede ser honesto sin la DB viva.
- s1 es codegen DETERMINISTA (sin LLM). La **lógica de dominio viva por LLM** es s6 (DES-8, patrón MAT-2),
  otro incremento — no acá.
