<!-- meta:doc sha=71ef5eb452c3f1cb2e394c2dcd5b8dfc721275a2 updated=2026-06-18T19:35Z -->
<!-- meta:doc sha=PENDING updated=2026-06-18T18:10Z -->
# Incremento — Full-Stack Kotlin/TS/PG Factory (DISEÑO)

> tipo: work (por-incremento) · creado: 2026-06-18T18:10Z · sesión: opus-4.8
> **Estado: **CERRADO** (2026-06-18T19:35Z) · fase: DISEÑO ✅ (este doc) → BUILD (próxima(s) sesión(es))
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que escribió esto MURIÓ. El próximo
> orquestador implementa desde acá con contexto en blanco. Si algo no está acá (o en la spec/cantera que
> referencia), no existe. Orden de lectura para retomar: §0.

## 0. Si llegás sin contexto, leé en este orden
1. Este doc entero (es el plan y el handoff).
2. `specs/full-stack-kotlin.factory.spec.yml` — el blueprint VALIDADO (pasa `validate` + `design-review`).
3. `docs/reference/PRIMITIVES.md §3` + `docs/reference/primitives.yml` — la cantera DES, ahora con DES-10..13.
4. `specs/full-stack.factory.spec.yml` (la full-stack TS MÍNIMA ya construida) — tu PLANTILLA concreta de
   cómo se ve una línea con `builds`/`checks` ejecutables y codegen (`factories/full-stack/codegen/`).
5. `.claude/skills/design-primitives/SKILL.md` + `docs/STATE.md` + `docs/work/ROADMAP.md`.

## 1. Qué es esta fábrica y por qué (la decisión, no trivial)
Una **Full-Stack-Factory de grado-producción** que genera apps web world-class **bajo criterios DUROS de
ingeniería**. Mandato del ingeniero (2026-06-18): lenguajes que **fallan FUERTE en compilación** (no
silenciosos como Python), **homogéneos/estables en el tiempo** (para que el LLM genere SOTA hoy Y mañana),
con **ecosistema maduro / no reinventar la rueda** y **sin lenguajes de 2ª clase**.

**Pila elegida (PLAN, ADR-012 — NO hardcodear en `src/metafactory/`)**: **Kotlin (JVM) backend · TypeScript/
React frontend · PostgreSQL** con **jOOQ** (SQL chequeado en compilación) + **Flyway** (migraciones
versionadas). Contrato **OpenAPI como fuente única** → stubs Kotlin + client TS generados (drift imposible).

**Por qué esta pila** (rankeada contra los criterios; detalle del razonamiento abajo): mejor equilibrio de
*dureza en compilación* (null-safety + `sealed`/`when` exhaustivo + jOOQ compile-checked) × *ecosistema
maduro/corpus LLM enorme* (JVM = 25 años de librerías, todo first-class) × *estabilidad* (backcompat del
JVM legendaria) × *mainstream* (Kotlin oficial de Android). El frontend paga el impuesto-browser
irreducible (TS/React, máximo corpus y madurez) con el **contrato tipado generado** como pieza portante
(DES-6). Alternativa #2 que NO se eligió: Rust+TS (gana dureza máxima, pierde corpus/fricción).

## 2. Reencuadre CLAVE: "spec perfecta" ≠ "todo built de una"
La spec queda **completa y honesta** (pasa los gates de diseño), pero **casi todo arranca `status: planned`**
(SAFE-7: aspiración ≠ realidad). El motor construye **por incrementos, capacidad por capacidad, probada por
bloqueo y anti-overfit** — igual que A–G. Flipear a `built` sin proof es mentir; el `increment_guard`/columna
lo impiden. Este doc cierra la fase de DISEÑO; deja el BUILD listo para arrancar (§7 handoff).

## 3. Lo que se HEREDA gratis (el "domar al LLM/Claude Code", copy-paste real)
NO se rediseña: la fábrica generada lo hereda verbatim (L4 substrate + harness emitido D2 + lifecycle H1).
- **Columna 3-cerrojos (SAFE-1)**: el modelo no puede escribir un veredicto verde (`seed/verifier.py` +
  hooks `proof_protect`/`commit_guard`/`stop_proof`). Heredada byte-idéntica, L4 no-negociable.
- **Verificar construyendo, no renderizando (SAFE-2, M8)**: cada gate corre en el toolchain del PRODUCTO.
- **Dos verificadores / re-derivación (SAFE-3)**: `external_ci` por-fábrica; `ci --rederive == pineado`.
- **Slots creativos acotados (SAFE-5)**: el LLM escribe sólo donde el output se verifica (slot `generate`,
  ADR-013 + contract test) — la lógica de dominio se genera VIVA bajo gate (patrón MAT-2), pineada (§7).
- **Sombra determinista universal (SAFE-6)**: agents con `shadows` (writer/reviewer/triage).
- **Lifecycle de incrementos (H1)**: `seed/lifecycle.py` heredado + `increment_guard` → no hay código sin
  incremento abierto.  **Economía de contexto**: leer el bus de veredictos (≤10 líneas), no dumps de tests.
**Lo NUEVO que tamea al LLM contra obsolescencia/blandura** (lo que sí hay que diseñar/construir): el
**MCP-recall scopeado** + los **gates de dureza (DES-10), frescura (DES-11), esquema (DES-12) y seguridad
(DES-13)**. Esos atrapan los errores del LLM determinísticamente (I-3: determinismo en la verificación).

## 4. La cantera CRECIÓ — DES-10..13 (ratificadas en `primitives.yml` + `PRIMITIVES.md §3`)
Un full-stack world-class con criterios duros fuerza primitivas que DES-1..9 no cubrían (regla del skill:
si un invariante no encaja, es primitiva NUEVA → a la cantera, NUNCA al sustrato). No infladas (SAFE-7):
- **DES-10 · Análisis estático con dientes** ("grita en desarrollo"): el código falla fuerte por *calidad*
  (no sólo tipos): sin `any`, sin warnings, exhaustividad, complejidad acotada, errores no tragados.
  Tech: detekt+ktlint+`-Werror` (Kotlin) · ESLint strict+`no-explicit-any`+`ts-reset` (TS). Finding ⇒ rojo.
- **DES-11 · Currency / frescura de API** (determinista, NO "modelo barato" — I-3): el código generado usa
  sólo superficie de API **no-deprecada y pineada**; lo viejo se bloquea sin LLM. Tech: oráculo de superficie
  pineado (allow-list de símbolos por versión, alimentado por el MCP/Context7) + linter determinista.
- **DES-12 · Esquema versionado + queries chequeados** (la DB que GRITA en compilación): migraciones
  versionadas/reversibles; un query contra una columna inexistente = error de compilación; drift detectado.
  Tech: Flyway (migraciones) + jOOQ (tipos generados del schema vivo). Drift ⇒ rojo.
- **DES-13 · Cadena de suministro / seguridad del producto**: el producto no shippea vulns conocidas,
  secretos ni código inseguro. Tech: OWASP dep-check/`npm audit`/Gradle + Semgrep/CodeQL (SAST) + gitleaks
  (secretos) + SBOM. Hallazgo ⇒ rojo. (Distinto de SAFE-*, que protege la cadena de confianza de la FÁBRICA.)
> El resto de lo world-class se expresa con primitivas EXISTENTES (no inflo): a11y+perf = DES-7;
> observabilidad del producto (logs/tracing/health) = DES-5; config 12-factor validada = DES-6;
> auth no-salteable = DES-3; pirámide de tests = DES-8; DB viva = DES-4/DES-9.

## 5. El mapa de capacidades (L1) → primitiva → tech → station que lo prueba
| capability | DES | tech (PLAN) | station |
| --- | --- | --- | --- |
| andamiaje_regenerable | DES-1 | OpenAPI-codegen + Gradle/npm (100%-generado, idempotente) | s0 |
| contrato_tipado_fuente_unica | DES-6 | OpenAPI → stubs Kotlin + client TS; drift→build rojo | s0 |
| aislamiento_producto | DES-9 | workspace Gradle/npm propio; importar la fábrica adentro FALLA | s0 |
| datos_esquema_chequeado | DES-12 | Flyway + jOOQ (query a columna inexistente → compile error) | s1 |
| datos_durables_vivos | DES-4 | PostgreSQL real (Testcontainers) round-trip vivo; DB caída→rojo | s1 |
| dureza_estatica | DES-10 | detekt+ktlint+`-Werror` / ESLint strict+no-any; finding→rojo | s2 |
| frescura_de_api | DES-11 | oráculo de superficie pineado + linter determinista; deprecado→rojo | s3 |
| seguridad_cadena_suministro | DES-13 | dep-audit + Semgrep + gitleaks + SBOM; vuln/secreto→rojo | s4 |
| rutas_protegidas | DES-3 | middleware/guard de auth; ruta protegida sin guard→rojo | s5 |
| topologia_rutas_verificable | DES-2 | AST de rutas vs contrato (sin levantar server) | s5 |
| logica_dominio_generada | DES-8 | LLM vivo (`claude -p`, slot generate) bajo contract test Kotest; stub→rojo; pin §7 | s6 |
| pruebas_piramidales | DES-8 | Kotest (unit) + Testcontainers (integración) + Playwright (e2e) | s7 |
| calidad_experiencia | DES-7 | axe (a11y/WCAG) + Lighthouse (perf budget) + bundle-size; bajo umbral→rojo | s8 |
| observabilidad_producto | DES-5 | logs estructurados + OTel tracing + /health; verificado que EMITE | s9 |
| build_hermetico_reproducible | DES-1 | Gradle wrapper pineado + npm lock + Docker base pineada; re-derive idéntico | s10 |

## 6. La línea de build (L2) — orden y DAG
`s0` scaffold+contrato (DES-1/6/9) → `s1` esquema PG+jOOQ vivo (DES-12/4) → `s2` dureza (DES-10) →
`s3` frescura (DES-11) → `s4` seguridad (DES-13) → `s5` auth+rutas (DES-3/2) → `s6` lógica LLM-gen bajo
gate (DES-8, MAT-2) → `s7` pirámide de tests (DES-8) → `s8` a11y+perf (DES-7) → `s9` observabilidad (DES-5)
→ `s10` build hermético + mini-columna del producto (fan-in DAG: depende de s2,s3,s4,s7,s8,s9 — ejercita el
gating multi-predecesor P2/H2). Cada estación GATEA; `depends_on` arma el DAG. Detalle exacto: la spec.

## 7. HANDOFF — qué hace el próximo orquestador (build, en orden)
> El incremento queda **ABIERTO**: el diseño está commiteado y el árbol limpio. NO reabras diseño; CONSTRUÍ.
0. `meta check` (verde) + leé §0. Confirmá que la spec valida: `PYTHONPATH=src python3 -m metafactory.spec.cli
   validate specs/full-stack-kotlin.factory.spec.yml` y `… design-review …` (deben dar exit 0).
1. **Codegen primero** (vive en la FÁBRICA, ADR-012, NO en el sustrato): creá
   `factories/full-stack-kotlin/codegen/scaffold_product.py` (determinista) que lee `domain.product` y emite
   el árbol del producto (contrato OpenAPI, stubs Kotlin, client TS, migraciones Flyway, etc.). Plantilla:
   `factories/full-stack/codegen/scaffold_product.py`.
2. **Construí estación por estación, PROBANDO POR BLOQUEO** (dos lados: corromper → gate rojo; regen → verde).
   Empezá por `s0`; rellená sus `builds`/`checks` ejecutables (en la spec) replicando el patrón de la
   full-stack TS (action `generate` con `via`, check `kind: product_env`/`infra_up`/`eval_gate`). Subí
   `status` de `planned`→`built` SÓLO con `proof` real (SAFE-7). Re-pin: `meta product-run` + `ci --rederive`.
3. **Anti-overfit SIEMPRE** (§ regla dura): los gates nuevos (loudness/currency/seguridad) deben ser
   **mecanismos de sustrato GENERALES** configurados por DATA (correr-un-linter-y-fallar), NO atados a
   Kotlin/TS. El linter específico es DATA de la fábrica. Verificá `git diff src/metafactory/ + seed/` =
   sólo mecanismo general, cero nombres de tech (como MAT-7 salió con diff=0). Promové a `general` en
   `parity.yml` sólo con ≥2 fábricas (ADR-014).
4. **MCP-recall scopeado** (machinery.mcp, E2): server MCP con SÓLO los docs de las versiones PINEADAS
   (Kotlin/Ktor/jOOQ/React/…), recall bajo demanda — no Context7 crudo. Bonus: puebla la serie `recall`
   (medida vacía) y retro-justifica el índice semántico diferido.
5. **El producto hereda "probar por bloqueo"**: shippea su propio CI que re-corre todos los gates (mini-columna).

## 8. Restricciones — dónde esta pila es INSEGURA (declaradas como DATA en `domain.constraints`)
Pedido explícito del ingeniero: dónde NO usar esta fábrica → futuras fábricas de dominio. Hoy es DATA
documentada; **darle dientes M0 (rehúsa planear un producto en un dominio excluido) es un incremento de
sustrato FUTURO chico** (un check en m00 que lea `domain.constraints`), NO entregado acá — anotado honesto.
- Tiempo-real duro / safety-critical (avionics, médico, automotriz) → GC del JVM no determinista → Rust/Ada/C.
- ML/numérico pesado, entrenamiento → ecosistema equivocado → Python/C++/CUDA.
- Embebido / kernel / drivers → necesita sin-GC → Rust/C (parte ya: IoT-Go).
- Mobile nativo (UI iOS/Android) → esto es web → Mobile-Factory.
- HFT / ultra-baja-latencia → GC inaceptable → C++/Rust.  Smart contracts → Solidity/Move.  Big-data ETL →
  Spark/dbt (skeleton data-pipeline).
- **Fit afirmativo**: apps web transaccionales/CRUD, dashboards, SaaS, herramientas internas, APIs de negocio.

## 9. Evidencia de DISEÑO (esta sesión, probada por bloqueo)
- DES-10..13 ratificadas: `primitives.yml` + `PRIMITIVES.md §3` en sync (el test `test_design.py::
  test_catalog_ids_match_primitives_md_section_3` lo ata) — ver §Evidencia al cerrar.
- `specs/full-stack-kotlin.factory.spec.yml`: `validate` exit 0 · `design-review` exit 0 (plan + criterios
  completos; 13 primitivas requeridas, cada una con tech; cada requisito con verifier real).
- `pytest tests/test_design.py` verde (la cantera creció sin romper el binding).
- Anti-overfit: `git diff src/metafactory/ + seed/` = 0 (sólo DATA + docs; cero sustrato).

## 10. Lo que se le escapaba al ingeniero (capturado acá)
1. El PRODUCTO hereda "probar por bloqueo" (su propio CI). 2. Anti-overfit a nivel fábrica: los gates nuevos
GENERALES configurados por DATA o rompés el gate de paridad (ADR-014). 3. El contrato es la FUENTE, generado
a ambos lados (drift imposible, no "por disciplina"). 4. 100%-generado ⇒ sin código humano ⇒ `boundary`
opta-out (H2) — la app es 100% regenerable, fortaleza no carencia. 5. El MCP scopeado al pin o no sirve.
6. Faltaban: seed data + test de migraciones up/down, gate "sin PII en logs", rate-limiting para APIs públicas.
