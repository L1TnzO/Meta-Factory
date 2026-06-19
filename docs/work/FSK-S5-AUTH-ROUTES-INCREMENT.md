<!-- meta:doc sha=934035d08a7851b0d3555b85372847bc2cb0514c updated=2026-06-19T02:43Z -->
# Incremento FSK-S5-AUTH-ROUTES — Full-Stack Kotlin · auth no-salteable + topología de rutas (s5)

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-19T02:30Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Otro orquestador
> construye desde acá. Si algo no está acá (o en la spec/handoff que referencia), no existe. Orden de lectura: §0.

## 0. Si llegás sin contexto, leé en este orden
1. Este doc entero (el plan + handoff de la SEXTA estación de build de la fábrica FSK).
2. `docs/work/FSK-S4-SUPPLYCHAIN-INCREMENT.md` (**CERRADO**) — la estación anterior: el patrón del
   **analizador determinista stdlib** (sin LLM, sin red) que el producto SHIPPEA (mini-columna, s10) +
   **diente negativo EMBEBIDO** (probe sucio + grep, fail-closed) y cómo s4 compuso sobre `product_env` con
   `git diff src/+seed/` = 0. s5 cuelga de s4 (`depends_on: [s4]`) y reusa EXACTAMENTE esa forma: un
   mecanismo general (`product_env`) corre DATA de la fábrica (un analizador estático), dos ejes (DES-2/DES-3).
3. `docs/work/FULLSTACK-KOTLIN-INCREMENT.md §5–§6` (DISEÑO, **CERRADO**) — DES-3 (`rutas_protegidas`) y DES-2
   (`topologia_rutas_verificable`) y la línea s0–s10 / DAG: s5 = auth + rutas, cuelga de s4, precede a s6.
4. `factories/full-stack-kotlin/factory.spec.yml` — el blueprint BUILDABLE. Acá viven las caps
   `rutas_protegidas` (DES-3) y `topologia_rutas_verificable` (DES-2) y la estación s5 con sus dos checks
   (`auth_reachability`, `route_topology`).
5. `factories/full-stack-kotlin/codegen/scaffold_product.py` — el codegen (DATA de la fábrica, ADR-012) que
   emite el guard de auth + el registro de rutas (Kotlin real) + el analizador estático + los probes negativos.

## 1. Objetivo (qué deja TERMINADO este incremento — una frase)
**s5 en `built` por proof real**: el producto Kotlin gana DOS gates de rutas, ambos **estáticos** (sin
levantar el server) y DETERMINISTAS (stdlib, sin LLM, sin red, I-3): **(DES-3, `rutas_protegidas`)** ninguna
ruta protegida por el contrato se alcanza sin pasar por el **guard de auth** (punto de control no-salteable,
verificado por **alcanzabilidad estática** sobre el árbol de rutas declarado) y **(DES-2,
`topologia_rutas_verificable`)** el mapa de rutas es chequeable contra el **contrato OpenAPI** (una ruta sin
contrato o un contrato sin ruta → rojo). El codegen emite un **guard** (`auth/AuthGuard.kt`) + un **registro
de rutas** (`routes/RouteTable.kt`, Kotlin real que compila: las rutas de escritura se registran dentro de
`authenticated { }`) + un **analizador estático** (`tools/route_check.py`, stdlib) con dos modos (`topology`,
`auth`) que cruza las rutas declaradas (`src/main/kotlin`) contra `openapi.yaml`. Rerutear una ruta protegida
fuera del guard, o declarar una ruta sin contrato, → **build rojo**, con un **diente negativo embebido** que
exige que el analizador MUERDA fixtures sucios cada corrida (fail-closed). Cuelga de s4; precede a s6 (lógica LLM).

## 2. Alcance EXACTO — capabilities, primitivas, proof_checks (de la spec/diseño, no inventar)
| capability (L1) | DES | proof_check (s5) | runs_in | requisito |
| --- | --- | --- | --- | --- |
| `rutas_protegidas` | DES-3 | `auth_reachability` (`route_check.py auth openapi.yaml src/main/kotlin` → 0: toda ruta protegida por el contrato está dentro de `authenticated {}`; sobre `probe/routes/unguarded.kt` el analizador DEBE morder `UNGUARDED` o decorativo→rojo) | product_env | REQ-F-005 (re-añadir) |
| `topologia_rutas_verificable` | DES-2 | `route_topology` (`route_check.py topology openapi.yaml src/main/kotlin` → 0: el set de rutas == el contrato; sobre `probe/routes/phantom.kt` el analizador DEBE morder `EXTRA` o decorativo→rojo) | product_env | REQ-F-006 (re-añadir) |

- Las caps arrancan `status: planned`; flipean a `built` **sólo** con `proof` real recompuesto (SAFE-7) — el
  `increment_guard`/columna lo impiden, no es disciplina. Re-añadir **REQ-F-005** (`auth_reachability`,
  capability `rutas_protegidas`) y **REQ-F-006** (`route_topology`, capability `topologia_rutas_verificable`)
  — hoy DIFERIDAS en la spec; los IDs y verifiers vienen de la spec de DISEÑO (git @ `c318aaf`).
- **NO** tocar s6–s10 (cuelgan de s5; son sus propios incrementos, "capacidad por capacidad").

## 3. Decisiones de build (refinan §5–§6 del diseño; ojos propios)
1. **Análisis ESTÁTICO, no servidor vivo** (el diseño DES-2/DES-3 lo dice literal: "AST de rutas… sin
   levantar el server", "alcanzabilidad estática"). El gate es UN analizador stdlib (`route_check.py`) con
   dos modos — la misma forma que s4 (`supply_chain_scan.py` con `deps`/`secrets`): un mecanismo general por
   DATA, dos ejes (topología DES-2 + auth DES-3). No se levanta HTTP, no hay red → re-derivable (`ci --rederive`).
2. **Registro de rutas Kotlin REAL, sin dependencia de servidor — divergencia de tech registrada** (ADR-012,
   la tech es PLAN): el diseño §5 propuso "middleware de auth (Ktor)". Ktor es un **server HTTP vivo** que el
   gate NUNCA levantaría (la verificación es estática) → meterlo sería façade (un server que no corremos) y
   añadiría una dependencia pesada + entradas al SBOM de s4 a vetar. Reduzco a la forma **honesta y hermética**:
   un **registro de rutas autocontenido** (`RouteTable.kt`: un `route(method, path)` declarativo y un bloque
   `authenticated { }` que marca las rutas protegidas) — **Kotlin real que COMPILA** (entra en `compileKotlin`
   de s0) y que el analizador lee **estáticamente** (AST por tokens, sin compilar). El **guard en runtime**
   (`AuthGuard.authorize` + `RouteTable.dispatch`: una ruta protegida sin token autorizado se rechaza) es
   código real y tipado. Un `routing { }` de Ktor analizado estáticamente y un `RouteTable` analizado
   estáticamente son **la misma máquina, otra data** — como IoT divergió C→Go y la dummy usó sockets stdlib
   en vez de docker. El soporte HTTP vivo (Ktor real + e2e) queda **`declared-deferred`** (es la pirámide de
   tests, s7, y el server real, s9-observabilidad) — mismo shape que el feed-vivo diferido de s4.
3. **El contrato OpenAPI es la FUENTE de "qué está protegido"** (DES-6, single source): el codegen añade
   `securitySchemes: { bearerAuth }` + `security: [{ bearerAuth: [] }]` a cada operación de **escritura**
   (`post`); los `get` (lectura) quedan públicos. Así el contrato — no el código — DECIDE qué ruta es
   protegida, y el analizador cruza el registro de rutas contra ESA decisión: una ruta de escritura fuera del
   guard es un `UNGUARDED` contra el contrato (no contra una lista hardcodeada). No puede driftar.
4. **El diente de dos lados es EMBEBIDO** (doctrina s2/s3/s4): el MISMO analizador sobre fixtures sucios
   (`probe/routes/phantom.kt` con una ruta `/__phantom__` que el contrato no tiene → `EXTRA`;
   `probe/routes/unguarded.kt` con un `route("POST", …)` FUERA de `authenticated {}` → `UNGUARDED`) y **exige
   el hallazgo por grep** (`EXTRA` para topology, `UNGUARDED` para auth) — **fail-closed**. Los probes viven
   FUERA de `src/` (`probe/routes/`) → no se compilan ni se shippean. Dir PROPIO → decoupleado de s2/s3/s4.
5. **Backend-only, honesto (no inflo dual-language)**: a diferencia de s2/s3/s4 (calidad/frescura/seguridad
   aplican a Kotlin Y TS), la **topología de rutas + auth es una preocupación de BACKEND** (el server Kotlin).
   El analizador cruza rutas Kotlin contra el contrato OpenAPI; no hay lado TS. Eso NO es overfit: el
   anti-overfit exige que el MECANISMO sea general (`product_env` corre DATA), no que cada gate toque ambos
   lenguajes. El frontend ya consume el contrato tipado (s0); su superficie de auth es contenido futuro (s8/s9).
6. **Anti-overfit**: el mecanismo es `product_env` (ya `general`, C3/E1) corriendo DATA; el sustrato NO nombra
   auth/ruta/Ktor/OpenAPI. `git diff src/metafactory/ + seed/` = **0** — la composición §6 del ROADMAP, como s0–s4.
7. **El producto SHIPPEA su gate**: `route_check.py` + el guard + el registro de rutas viven en el árbol del
   producto (`tools/`, `src/main/kotlin/…`) → son parte de su mini-columna (s10), no andamiaje de la fábrica.

## 4. Plan por fases (cada cambio de código vive en este incremento; commit por fase, trailers I-10)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Codegen** ✅ — `scaffold_product.py` emite `auth/AuthGuard.kt` (guard de auth) + `routes/RouteTable.kt` (registro de rutas Kotlin real con `authenticated {}`) + `tools/route_check.py` (analizador estático stdlib, modos `topology`/`auth`) + `probe/routes/{phantom,unguarded}.kt` (fixtures negativos) + `security`/`securitySchemes` en `openapi.yaml`. idempotente (selftest + check-idempotent, 35 archivos byte-idénticos); s0–s4 verdes con los nuevos archivos (compone). | ✅ |
| 2 | **s5 materializada + verde e2e** ✅ — s5 en `station_sequence` (`depends_on: [s4]`) con `auth_reachability` + `route_topology` (product_env, dientes embebidos) + caps `rutas_protegidas`/`topologia_rutas_verificable`→built + REQ-F-005/006; `validate`+`design-review` 0; M0–M8 verde; `product-run` PASS (s5 OPEN); **RTM COMPLETE 10/10**; pin 6/6. | ✅ |
| 3 | **Pin + dientes + cierre** ✅ — `ci --rederive` **6/6 == pineado**; **dientes VIVOS de dos lados** (rerutear un `POST` fuera del guard → `auth_reachability` rojo `UNGUARDED`; ruta sin contrato → `route_topology` rojo `EXTRA`; regen→verde) + probe vaciado→`DECORATIVE` (fail-closed); `meta check` 6/6; **anti-overfit `git diff src/+seed` = 0**; dummy intacta (5/5); STATE/ROADMAP; `meta increment close`. | ✅ |

## 5. Criterio de cierre (demostrable por BLOQUEO, no narrable)
1. `meta product-run --factory full-stack-kotlin` corre s0..s5 y queda **PASS**; pin escrito (6/6).
2. `meta ci --rederive --factory full-stack-kotlin` re-deriva en clon limpio **== pineado** (re-corre el
   analizador de rutas + el toolchain entero, incl. el contenedor PG de s1 y los linters de s2/s3/s4), **sin red**.
3. **RTM** cubre **REQ-F-005** (`auth_reachability`) y **REQ-F-006** (`route_topology`) con artifacts reales
   (`AuthGuard.kt` / `RouteTable.kt` bajo `build/product/src/main/kotlin/webapp/`).
4. **dientes VIVOS de dos lados**: mover un `route("POST", …)` fuera de `authenticated {}` en `RouteTable.kt`
   → `auth_reachability` rojo (`UNGUARDED`); declarar/borrar una ruta vs el contrato → `route_topology` rojo
   (`EXTRA`/`MISSING`); regen → verde. Y el **probe negativo embebido** (no-decorativo) muerde cada corrida
   verde (grep `UNGUARDED` + `EXTRA`).
5. **`meta check` 6/6** verde; **anti-overfit**: `git diff src/metafactory/ + seed/` = **0** (cero nombres de
   auth/ruta/Ktor/OpenAPI en el sustrato — son DATA de la fábrica). dummy/full-stack/iot/ASF **intactas**.

## 6. Riesgos / notas honestas (a resolver/registrar en el build)
- **Estático vs servidor vivo** — el gate prueba la TOPOLOGÍA y la ALCANZABILIDAD declaradas (sin levantar
  HTTP). Que el guard rechace en runtime es código real y tipado (`dispatch`), pero el server HTTP vivo + e2e
  (Ktor real, Playwright) es `declared-deferred` (s7 pirámide / s9 observabilidad). Honesto: s5 prueba que
  ninguna ruta protegida ESCAPA del guard por construcción, no una corrida HTTP — ése es el alcance del diseño.
- **El contrato como oráculo de "protegido"** — un `post` sin `security:` en el contrato dejaría de exigir
  guard. Mitigación: el codegen lo emite por construcción para TODA escritura; un drift del contrato (quitar
  `security`) baja la exigencia pero NO crea un falso verde (la ruta seguiría declarada; sólo cambia qué es
  "protegido"). El gate honesto cruza rutas vs el contrato TAL CUAL es.
- **Parseo del contrato sin PyYAML** — `route_check.py` corre en `product_env` scrubbeado (sin la fábrica) →
  stdlib puro, sin PyYAML; parsea `openapi.yaml` con un scanner por indentación del formato FIJO que el codegen
  emite. El lado positivo (rutas reales == contrato real) + el diente embebido (probe DEBE morder) atrapan un
  parser demasiado laxo. El contrato es la FUENTE real (la que `openapi-generator`/`openapi-typescript` consumen).
- **Solapamiento con s2/s3/s4** — eje DISTINTO: s2 calidad, s3 frescura, s4 seguridad-de-cadena, s5
  **rutas** (auth no-salteable + topología vs contrato). Ningún gate previo verifica que una ruta protegida
  pase por el guard ni que el mapa de rutas matchee el contrato → cobertura genuina nueva.
- **`build/product` se regenera** — el slot `generate` (s0) sobre-escribe `build/product`; el diente vivo se
  demuestra corriendo el analizador directo contra el árbol corrompido (exit codes reales), no via
  `product-run` (que regeneraría y borraría la corrupción) — igual que s1/s2/s3/s4.
- s5 es codegen DETERMINISTA (sin LLM). La lógica de dominio viva por LLM es s6 (DES-8, patrón MAT-2).

## 7. Evidencia de cierre (por bloqueo, 2026-06-19 — re-derivable, no narrada)
- **M0–M8 verde** (corridos en orden, gate_guard): m00 `validate`+`design-review` 0 · m02 materializó
  `stations/s5.yml` (auth_reachability + route_topology) · m05 RTM · **m06 `clean_runner` == pineado**
  (re-deriva la línea + el analizador de rutas + detekt/ESLint + el scanner de s4 + el contenedor PG de s1 en
  clon limpio) · m07 harness · m08 product_e2e.
- **product-run PASS** — s5: `auth_reachability` → `FSK_AUTH_OK` · `route_topology` → `FSK_TOPOLOGY_OK` (gate s5 OPEN).
- **RTM COMPLETE 10/10**: REQ-F-001..006 + REQ-NF-001..004 — **REQ-F-005** ← `rutas_protegidas` [s5,
  `…/webapp/auth/AuthGuard.kt`✓] · **REQ-F-006** ← `topologia_rutas_verificable` [s5, `…/webapp/routes/RouteTable.kt`✓].
- **`ci --rederive` full-stack-kotlin 6/6 == pineado** (re-corre el analizador de rutas + detekt + `-Werror`
  + ESLint + el scanner de supply-chain + npm + gradle + el contenedor PG de s1 en clon limpio, **sin red**).
- **dientes VIVOS de dos lados (exit codes reales)** — el árbol generado se corrompe directo (no via
  `product-run`, que regeneraría y borraría la corrupción; igual que s1/s2/s3/s4):
  - clean `auth_reachability` → `FSK_AUTH_OK` exit 0 · `route_topology` → `FSK_TOPOLOGY_OK` exit 0.
  - **auth (DES-3)** — mover `route("POST", "/users")` FUERA de `authenticated {}` en `RouteTable.kt` →
    `UNGUARDED POST /users` → exit 1; regen → exit 0.
  - **topología (DES-2)** — declarar `route("GET", "/ghost")` (sin contrato) en `RouteTable.kt` →
    `EXTRA GET /ghost` → exit 1; regen → exit 0.
  - **fail-closed (probe embebido)** — vaciar `probe/routes/unguarded.kt` → el autorado pasa pero el probe NO
    muerde → `FSK_AUTH_DECORATIVE` → exit 1 (el diente embebido es no-decorativo); regen → exit 0.
- **El gate cubre lo que ningún gate previo verifica**: que una ruta protegida por el contrato pase por el
  guard (DES-3) y que el mapa de rutas matchee el contrato (DES-2) — ortogonal a calidad (s2), frescura (s3)
  y seguridad-de-cadena (s4). El contrato OpenAPI es la FUENTE de "qué está protegido" (DES-6).
- **Anti-overfit**: `git diff src/metafactory/ + seed/` = **0**. El guard (`AuthGuard.kt`) + el registro
  (`RouteTable.kt`) + el analizador (`route_check.py`) + los probes viven 100% en la fábrica (DATA); compuso
  sobre `product_env` (C3/E1) sin tocar el sustrato — la composición §6 del ROADMAP, como s0–s4/MAT-7.
- **Fábricas intactas**: sólo cambió `factories/full-stack-kotlin/`; dummy `ci --rederive` 5/5 == pineado
  (spot-check); full-stack/iot/ASF inalteradas por construcción (diff de sustrato = 0).
- **Diferido honesto**: el **server HTTP vivo (Ktor real) + e2e** (Playwright) que ejercitaría el guard con
  requests reales queda `declared-deferred` (es la pirámide de tests s7 / la observabilidad s9) — mismo shape
  que el feed-vivo diferido de s4. La verificación de s5 es ESTÁTICA por diseño ("alcanzabilidad estática",
  "sin levantar el server"): prueba que ninguna ruta protegida ESCAPA del guard por construcción. El lado TS
  no tiene gate de rutas (auth/routing es backend); su superficie de auth es contenido futuro (s8/s9).
