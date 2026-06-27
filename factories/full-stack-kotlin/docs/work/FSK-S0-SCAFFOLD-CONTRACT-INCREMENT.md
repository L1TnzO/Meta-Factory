<!-- meta:doc sha=a3e3aacbb08e7512289f99342d37ea92f973810c updated=2026-06-18T20:29Z -->
# Incremento FSK-S0-SCAFFOLD-CONTRACT — Full-Stack Kotlin · fundación (s0)

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-18T20:29Z) (creado 2026-06-18T19:35Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Otro orquestador
> construye desde acá. Si algo no está acá (o en la spec/handoff que referencia), no existe. Orden de lectura: §0.

## 0. Si llegás sin contexto, leé en este orden
1. Este doc entero (es el plan + handoff de la PRIMERA estación de build).
2. `docs/work/FULLSTACK-KOTLIN-INCREMENT.md` (DISEÑO, **CERRADO**) — el handoff macro de la fábrica entera
   (pila, cantera DES-10..13, mapa de capacidades→primitiva→tech→estación, línea s0–s10, restricciones).
3. `specs/full-stack-kotlin.factory.spec.yml` — el blueprint VALIDADO (`validate` + `design-review` exit 0).
   Acá vive s0 (`domain.station_sequence[0]`) con sus 3 `proof_checks` y `domain.product`.
4. `factories/full-stack/codegen/scaffold_product.py` + `specs/full-stack.factory.spec.yml` — tu PLANTILLA
   CONCRETA: cómo se ve un codegen determinista + una línea con `builds`/`checks` ejecutables (slot `generate`,
   `kind: product_env`/`infra_up`). El patrón ya probado en TS; lo replicás en Kotlin.
5. `docs/STATE.md` + `docs/work/ROADMAP.md` (north star A–H ✅; esta fábrica es el post-A–H).

## 1. Objetivo (qué deja TERMINADO este incremento — una frase)
**s0 en `built` por proof real**: el scaffold del producto Kotlin/TS se GENERA 100% desde `domain.product`
por un codegen determinista de la FÁBRICA, con el **contrato OpenAPI como fuente única** (server Kotlin +
client TS derivados; un drift de tipos rompe la compilación), **regeneración idempotente**, y **aislamiento
del producto** (cargar la fábrica dentro del producto → rojo). Es la fundación de la que cuelga s1–s10.

## 2. Alcance EXACTO — capacidades, primitivas, requisitos (de la spec, no inventar)
| capability (L1) | DES | proof_check (s0) | runs_in | requisito |
| --- | --- | --- | --- | --- |
| `andamiaje_regenerable` | DES-1 | `scaffold_idempotent` (regenerar = árbol idéntico) | factory_env | REQ-F-002 |
| `contrato_tipado_fuente_unica` | DES-6 | `contract_single_source` (kotlinc + `tsc --strict`; drift→rojo) | product_env | REQ-F-001 |
| `aislamiento_producto` | DES-9 | `isolation_boundary` (importar la fábrica adentro → rojo) | product_env | (capability) |

Todo arranca `status: planned` (SAFE-7). Flipear a `built` SÓLO con `proof` real recompuesto — el
`increment_guard`/columna lo impiden, no es disciplina. **NO** tocar s1–s10 acá (cuelgan de s0; son sus
propios incrementos, "capacidad por capacidad" — `FULLSTACK-KOTLIN-INCREMENT §2`).

## 3. Dependencia bloqueante #1 — el toolchain hermético (medido esta sesión, no asumido)
Probado en este entorno (`command -v`): **java ✅** (JDK 25 runtime / `javac` 21), **node/npm ✅** (v22/10.9),
**docker ✅** (29.5), **psql ✅** (PG 18.3) — pero **`kotlinc` y `gradle` NO están instalados**. La 1ª tarea
del build es establecer un **toolchain JVM/Kotlin HERMÉTICO y re-derivable** (el análogo del `GOPROXY=off` de
IoT-Go / del `npm ci` pineado de Full-Stack-TS): Gradle **wrapper pineado** (`gradlew` + `gradle-wrapper.jpg`
con checksum) + caché Maven/Gradle offline, de modo que `ci --rederive` reconstruya en clon limpio SIN red.
Si no se logra hermético, el gate de s0 NO puede ser honesto — documentar el residual antes que fingir verde.

## 4. Plan por fases (cada cambio de código vive en este incremento; commit por fase, trailers I-10)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Toolchain pineado + probado** (§3): Gradle 9.5.1 (sha256) + Kotlin 2.4.0 + JDK 21 + TS 5.7.3; wrapper vendorizado en `factories/full-stack-kotlin/codegen/assets/gradle/`; smoke Kotlin (`FSK_SMOKE_OK`) y `tsc --strict` (green 0 / red 2) — `assets/TOOLCHAIN.md` | ✅ |
| 1.5 | **Arquitectura del contrato DE-RISKEADA por bloqueo** (antes de escribir el codegen): OpenAPI como fuente única → `openapi-generator` 7.23 (Kotlin, models + kotlinx-serialization) **compila**; `openapi-typescript` 7.13 (TS) bajo `tsc --strict` **compila**. **Diente DES-6 con dientes REALES en AMBOS**: quitar un campo del contrato → regenerar → Kotlin `Unresolved reference` (compile rojo) · TS `Property does not exist` (tsc rojo). Plugin portal + maven alcanzables | ✅ |
| 2 | **Codegen de fábrica** `factories/full-stack-kotlin/codegen/scaffold_product.py` (determinista, 12 archivos): lee `domain.product` (3 entidades) → emite OpenAPI `openapi.yaml`, build Gradle con `openApiGenerate`, handler+app Kotlin que usan los models generados (refs camelCase), client TS con `openapi-typescript`, wrapper vendorizado. **Vive en la FÁBRICA** (ADR-012). `git diff src/+seed/`=0 | ✅ |
| 3 | **s0 ejecutable + materializado + verde e2e**: spec staged (s0 activo/built + 3 caps built + REQ-F-001/002/NF-001; s1–s10 diferidas) → `validate`+`design-review` 0 problemas; `meta new`+`station m00..m06` PASS; **`product-run` PASS (4 checks)**; **RTM COMPLETE 3/3** (artifacts reales); pin escrito; **m06 `clean_runner` == pineado** (re-deriva la línea Kotlin/TS en clon limpio) | ✅ |
| 4 | **Dientes de dos lados VIVOS** (probados por bloqueo en el árbol real): drift del contrato (drop `User.email`) → Kotlin `compileKotlin` rojo (`Unresolved reference 'email'`) + TS `tsc` rojo (`Property 'email' does not exist`); regenerar → ambos verdes. Aislamiento NO-decorativo: la fábrica ES importable con `PYTHONPATH` (⇒ el pass scrubbed es aislamiento real, no imposibilidad) | ✅ |
| 5 | **Pin + cierre**: s0 status→built; `product-run` PASS + **`ci --rederive` 1/1 == pineado**; RTM 3/3; M0–M8 verde; STATE/ROADMAP actualizados; **anti-overfit `git diff src/+seed/`=0**; `meta increment close` | ✅ |

## 5. Criterio de cierre (demostrable por BLOQUEO, no narrable)
1. `meta product-run --factory full-stack-kotlin` corre s0 y queda **PASS**; pin escrito.
2. `meta ci --rederive` (full-stack-kotlin) re-deriva s0 en clon limpio **== pineado**, SIN red (hermético §3).
3. **RTM** cubre **REQ-F-001** (contract_single_source) y **REQ-F-002** (scaffold_idempotent) con artifacts reales.
4. **≥2 dientes VIVOS** demostrados: (a) drift de contrato → `kotlinc`/`tsc` rojo; regen → verde; (b) cargar
   la fábrica dentro del producto → `isolation_boundary` rojo. Cada uno: corromper→rojo, regenerar→verde.
5. **`meta check` 6/6** verde; **anti-overfit**: `git diff src/metafactory/ + seed/` = **0** (o sólo mecanismo
   general, cero nombres de Kotlin/Gradle/jOOQ; los linters/toolchains son DATA de la fábrica — como MAT-7 salió
   con diff=0). Las otras 3 fábricas (dummy/full-stack/iot/ASF) **intactas** (`ci` == pineado, principio #4).

## 6. Riesgos / notas honestas
- **Gradle wrapper necesita red en el 1er bootstrap** para bajar la distro pineada; la hermeticidad real exige
  caché poblada antes del clon limpio. Si el entorno no lo permite, el residual se declara `declared-deferred`
  VISIBLE (no se finge), igual que ASF defería infra solo-CI.
- **`javac` 21 vs runtime JDK 25**: fijar el `--release`/toolchain de Gradle a una versión soportada y pineada
  (no asumir 25); el determinismo del build depende de pinear la versión.
- El codegen es DETERMINISTA en s0 (sin LLM). La **lógica de dominio viva por LLM** es s6 (DES-8, patrón MAT-2),
  otro incremento — no acá.
