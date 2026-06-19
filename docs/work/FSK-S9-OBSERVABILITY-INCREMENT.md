<!-- meta:doc sha=9cd7557e6554195ad17ba59a41c155abba1e7b8c updated=2026-06-19T14:31Z -->
# Incremento FSK-S9-OBSERVABILITY — Full-Stack Kotlin · observabilidad del producto bajo gate (s9)

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-19T14:24Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Otro orquestador
> construye desde acá. Si algo no está acá (o en la spec/handoff que referencia), no existe. Orden de lectura: §0.

## 0. Si llegás sin contexto, leé en este orden
1. Este doc entero (el plan + handoff de la DÉCIMA estación de build de la fábrica FSK).
2. `docs/work/FSK-S8-A11Y-PERF-INCREMENT.md` (**CERRADO**) — la estación anterior; s9 cuelga de s8
   (`depends_on: [s8]`). s8 dejó **Lighthouse** `declared-deferred` porque necesita un **server HTTP vivo**
   (Ktor) + Chrome; s9 es la estación que **introduce el primer server HTTP vivo del producto**.
3. `src/metafactory/verify/checks/infra_up.py` (**E1/MAT-3, DES-9**) — el mecanismo de sustrato que s9 COMPONE:
   ORQUESTA un `bootstrap` (una vez, env scrubbed) → levanta un `up` en background (process group) → REINTENTA
   un `proof` contra el servicio VIVO → teardown SIEMPRE, con un **diente nativo de dos lados** (con la infra
   caída el proof DEBE fallar, o es decorativo→rojo). Ya es `general` (`parity.yml`: [dummy, full-stack, ASF]).
   s9 lo ejercita con un 4º servicio: el **propio server HTTP del producto** (no un contenedor de DB).
4. `factories/full-stack-kotlin/factory.spec.yml` (s1 `db_roundtrip_live`, s7 `pyramid_integration`) — la
   PLANTILLA concreta de cómo se cablea un `kind: infra_up` (bootstrap/up/proof/down como DATA).
5. `docs/work/FULLSTACK-KOTLIN-INCREMENT.md §5–§6` (DISEÑO) — DES-5 (`observabilidad_producto`) y la línea
   s0–s10/DAG: s9 = observabilidad, cuelga de s8, precede a s10 (build hermético + mini-columna).
6. `factories/full-stack-kotlin/codegen/scaffold_product.py` — el codegen (DATA, ADR-012) que emite el árbol
   del producto. s9 suma: la **capa de observabilidad** Kotlin (server HTTP vivo + tracing OTel + logs
   estructurados) + el **proof client** stdlib + las deps OTel al `build.gradle.kts` y al `sbom.json`.

## 1. Objetivo (qué deja TERMINADO este incremento — una frase)
**s9 en `built` por proof real**: el producto Kotlin gana **observabilidad EMITIDA y verificada contra un
server HTTP VIVO** (DES-5): una request real produce **(a)** un **trace OpenTelemetry con correlation-id** y
**(b)** un **log estructurado (JSON)** con ese correlation-id, y los endpoints **`/health` y `/ready`**
responden — todo verificado por requests HTTP reales contra el server levantado por **`infra_up`** (no
"renderiza" un config: EMITE en runtime). El gate es **`observability_live` (kind `infra_up`)**: bootstrap
buildea el server, `up` lo levanta, el `proof` (un cliente stdlib del producto) hace las requests y exige que
el span y el log emitidos lleven el correlation-id; **diente nativo de dos lados** de `infra_up` (server caído
→ rojo) + diente vivo "quitar la instrumentación → rojo". Tech (PLAN, ADR-012): **server HTTP del JDK
(`com.sun.net.httpserver`, stdlib — NO Ktor)** + **OpenTelemetry SDK real** (el motor, "no reinventar la
rueda") con un **SpanExporter a archivo**. Divergencia registrada: el **server Ktor COMPLETO + e2e Playwright
(s7) + Lighthouse (s8)** siguen `declared-deferred` (su propio incremento, sobre este primer server vivo).

## 2. Alcance EXACTO — capability, primitiva, proof_checks (de la spec/diseño, no inventar)
| capability (L1) | DES | proof_check (s9) | runs_in | requisito |
| --- | --- | --- | --- | --- |
| `observabilidad_producto` | DES-5 | `observability_live` (infra_up: levanta el server HTTP del producto; el proof hace `/health`+`/ready`+una request instrumentada y exige que el span OTel y el log estructurado emitidos lleven el correlation-id; server caído → rojo, diente nativo) | product_env | REQ-F-010 |

- La cap arranca `status: planned`; flipea a `built` **sólo** con `proof` real recompuesto (SAFE-7) — el
  `increment_guard`/columna lo impiden, no es disciplina. Re-añadir **REQ-F-010** (`observabilidad_producto`);
  id y statement vienen de la spec de DISEÑO (git @ `c318aaf`), adaptados a la tech entregada.
- **NO** tocar s10 (cuelga de s9; es su propio incremento, "capacidad por capacidad").

## 3. Decisiones de build (refinan §5–§6 del diseño; ojos propios, DE-RISKEADAS POR PROTOTIPO antes de codear)
1. **Componer `infra_up`, no inventar un mecanismo (la esencia anti-overfit)**: la observabilidad se prueba
   contra un servicio VIVO ⇒ el mecanismo ya existe (`infra_up`, E1/MAT-3, ya `general`). s9 lo cablea con DATA
   (bootstrap/up/proof/down) con un 4º servicio: el **server HTTP del propio producto** (los 3 anteriores eran
   contenedores PostgreSQL). → **`git diff src/metafactory/ + seed/` = 0**. El sustrato no nombra OTel/HttpServer
   — son DATA de la fábrica. El diente de dos lados (server caído → rojo) es **NATIVO** de `infra_up`.
2. **Server HTTP vivo del JDK (`com.sun.net.httpserver`), NO Ktor — divergencia registrada (ADR-012)**. El
   mandato del ingeniero (FULLSTACK §1) es "no reinventar la rueda" PERO también pila estable/mainstream. Para
   el TRACING uso el **motor real** (OpenTelemetry SDK) — no un tracer de juguete. Para el HTTP elijo el server
   **stdlib del JDK** (cero deps nuevas de framework, ya en JDK 21) en vez de Ktor: es un server HTTP REAL y
   vivo (la propiedad que DES-5 exige), con mínima superficie nueva. Mismo patrón que s5 (Ktor→registro estático
   analizado) y s8 (Lighthouse→esbuild): se entrega la propiedad real con la tech de menor superficie; el **Ktor
   COMPLETO + e2e (Playwright, s7) + Lighthouse (s8)** quedan `declared-deferred`, su propio incremento sobre
   este primer server vivo. **De-riskeado por prototipo**: gradle resuelve `opentelemetry-bom 1.45.0` y compila
   un `SpanExporter` custom + el server bajo `-Werror`; el server vivo responde `/health`+`/ready`+`/users` y
   emite un span + un log con el correlation-id propagado del header — verificado por el **propio `infra_up`**
   del sustrato (positivo + negativo server-caído, exit 0).
3. **OTel real con un SpanExporter A ARCHIVO (no InMemory, no OTLP/red)**. El proof es un proceso SEPARADO que
   lee los spans EMITIDOS desde disco ⇒ el SDK exporta cada span (SimpleSpanProcessor, síncrono) como JSON-lines
   a `obs/spans.jsonl`; el log estructurado se appendea a `obs/access.jsonl`. **Emisión ANTES de responder**:
   el handler termina el span (export síncrono) y emite el log ANTES de mandar el 200 → cuando el cliente ve el
   200, el trace y el log YA están en disco (sin carrera). El server **trunca** ambos archivos al arrancar →
   cada vida del server empieza fresca (hace nítido el diente "sin instrumentación"). Sin red (OTLP/colector =
   `declared-deferred`): cacheado en `~/.gradle` → `ci --rederive` sin red, como jOOQ/Kotest/detekt.
4. **El correlation-id es el hilo de la trazabilidad (DES-5: "toda salida rastrea a su evidencia, clave de
   unión por nodo")**. El proof manda `X-Correlation-Id: <cid>` y exige que el MISMO cid aparezca como atributo
   del span Y como campo del log estructurado — la clave de unión request↔trace↔log. Quitar la instrumentación
   (no abrir el span / no setear el atributo / no loguear) → el cid no aparece → proof rojo (diente vivo).
5. **El gate NO toca s5 (rutas)**. El analizador de rutas de s5 (`route_check.py`) escanea `route("M","/p")`
   (tokens del `RouteTable.kt`); el server de obs usa `createContext("/health")` → NO matchea ese token →
   `route_topology`/`auth_reachability` siguen scopeados al `RouteTable.kt` (intactos). `/health` y `/ready`
   son endpoints OPERACIONALES (no CRUD del contrato): el server de obs es la capa instrumentada que prueba la
   EMISIÓN (DES-5), ortogonal al mapa de rutas del contrato (DES-2/3, s5) y a la persistencia (DES-4, s1/s7).
6. **Honestidad de SBOM (doctrina s4/s7/s8)**: `opentelemetry-api` + `opentelemetry-sdk` (BOM `1.45.0`) son deps
   nuevas del producto → se **agregan al `sbom.json`** y al `build.gradle.kts` desde las MISMAS constantes de pin
   (single source). El scanner de s4 las cruza contra el oráculo de advisories (no están → s4 sigue verde, pero
   la cobertura es real, no un agujero). El `com.sun.net.httpserver` es stdlib del JDK → no es una dep nueva.
7. **El producto SHIPPEA su observabilidad** (mini-columna, s10): la capa de obs (server + exporter + logger) y
   el `obs_check.py` viven en el árbol del producto → son parte del producto, no andamiaje de la fábrica.
8. **`build/product` se regenera** — la capa de obs es codegen DETERMINISTA (sin LLM) → se emite por
   `scaffold_product.py` (s0) cada `product-run`; s9 tiene `builds: []` (sólo PRUEBA), como s1–s5/s7/s8. El
   diente vivo "sin instrumentación" se demuestra corrompiendo el árbol generado + re-corriendo el `infra_up`
   (exit reales), no via `product-run` (que regeneraría y borraría la corrupción) — igual que s1–s8.

## 4. Plan por fases (cada cambio de código vive en este incremento; commit por fase, trailers I-10)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Codegen** — `scaffold_product.py` suma: `src/main/kotlin/webapp/observability/{Observability.kt,FileSpanExporter.kt,ObsServer.kt}` (server HTTP vivo + OTel + logs estructurados) + `tools/obs_check.py` (proof client stdlib) + `application` plugin + deps OTel en `build.gradle.kts` + las coords OTel en `sbom.json`. Idempotente; s0–s8 verdes con los archivos nuevos (compileKotlin/detekt/-Werror/currency/SBOM ok); `installDist` produce el launcher; obs server vivo emite span+log con cid. | ⏳ |
| 2 | **s9 materializada + verde e2e** — s9 en `station_sequence` (`depends_on: [s8]`) con `observability_live` (`kind: infra_up`); cap `observabilidad_producto`→built + REQ-F-010; `validate`+`design-review` 0; M0–M8 verde; `product-run` PASS; **RTM COMPLETE 14/14**; pin 10/10. | ⏳ |
| 3 | **Pin + dientes + cierre** — `ci --rederive` **10/10 == pineado** (re-levanta el server + re-corre el toolchain s0–s8 en clon limpio, sin red); **dientes VIVOS de dos lados** (server caído→`observability_live` rojo [nativo infra_up]; quitar la instrumentación de tracing→span sin cid→rojo; quitar el logging→log sin cid→rojo; regen→verde); `meta check` 6/6; **anti-overfit `git diff src/+seed` = 0**; dummy intacta; STATE/ROADMAP/spec; `meta increment close`. | ⏳ |

## 5. Criterio de cierre (demostrable por BLOQUEO, no narrable)
1. `meta product-run --factory full-stack-kotlin` corre s0..s9 y queda **PASS**; pin escrito.
2. `meta ci --rederive --factory full-stack-kotlin` re-deriva en clon limpio **== pineado** (re-levanta el
   server HTTP del producto + re-corre todo el toolchain s0–s8), **sin red** (OTel cacheado en `~/.gradle`).
3. **RTM** cubre **REQ-F-010** (`observabilidad_producto`) con artifact real bajo `build/product/`.
4. **dientes VIVOS de dos lados**: server caído → `observability_live` rojo (diente nativo de `infra_up`);
   quitar la instrumentación de tracing → el span emitido no lleva el cid → rojo; quitar el logging
   estructurado → rojo. regen → verde.
5. **`meta check` 6/6** verde; **anti-overfit**: `git diff src/metafactory/ + seed/` = **0** (cero nombres de
   OTel/HttpServer en el sustrato — son DATA de la fábrica). dummy/full-stack/iot/ASF **intactas**.

## 6. Riesgos / notas honestas (a resolver/registrar en el build)
- **OTel como dep nueva** — de-riskeado: gradle resuelve `opentelemetry-bom:1.45.0` (api+sdk) y compila bajo
  `-Werror`. La 1ª corrida descarga a `~/.gradle`; `ci --rederive` corre sobre el cache caliente (sin red),
  igual que jOOQ/Flyway/detekt/Kotest. Se agregan al SBOM (s4) → cobertura real.
- **detekt sobre la capa de obs (s2)** — el código nuevo de obs corre por detekt (maxIssues:0) + `-Werror`: hay
  que evitar MagicNumber (status 200, puerto) usando `const val` con nombre, sin excepciones tragadas, imports
  ordenados sin `*`. El gate decide; se itera el markup hasta verde (no la narrativa).
- **Carrera proof↔emisión** — resuelta por diseño: el handler emite (log + `span.end()` síncrono) ANTES de
  responder; el server trunca los archivos al arrancar. El proof hace HTTP primero (falla rápido si el server
  está caído → diente nativo) y lee los archivos después (no lee rancio).
- **Server vivo bajo `infra_up`** — el `up` corre el launcher de `installDist` (un proceso java plano, no el
  daemon de gradle) con `exec` → process-group killable; teardown SIEMPRE (lo prueba el diente nativo). Puerto
  fijo (DATA) como los contenedores PG de s1/s7.
- **Divergencia ADR-012 (no over-claim)** — s9 entrega el PRIMER server HTTP vivo del producto (para
  observabilidad). NO afirma ser el server CRUD completo del contrato: extender el server a servir la UI/API
  completa para el e2e de browser (Playwright, s7) + Lighthouse (s8) es su propio incremento `declared-deferred`.
- **Solapamiento** — ningún gate previo verifica emisión de observabilidad. Eje genuinamente nuevo: trazabilidad
  en runtime (DES-5), ortogonal a calidad-de-código (s2), frescura (s3), seguridad (s4), rutas-estático (s5),
  lógica-LLM (s6), pirámide (s7) y a11y/perf (s8).

## 7. Evidencia de cierre (por bloqueo — re-derivable, no narrada) — A COMPLETAR AL CERRAR
- (M0–M8 · product-run · RTM 14/14 · ci --rederive 10/10 == pineado · dientes vivos · git diff src/+seed=0)
