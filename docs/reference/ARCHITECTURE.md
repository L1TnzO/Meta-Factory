<!-- meta:doc sha=32fe43cbe5f9dcf150a522c352470f00b528c066 updated=2026-07-04T14:26Z -->
# Arquitectura del Meta-Factory

| Campo | Valor |
| --- | --- |
| Documento | Fundamentos de arquitectura |
| Estado | Borrador para revisión (pre-implementación) |
| Alcance | Define el sustrato sobre el que se construye el Meta-Factory y toda fábrica que produce |
| Depende de | `VISION.md` (el porqué), `ASF-LESSONS.md` (de dónde sale el sustrato) |

> Autocontenido. Terminología propia en §1. Las decisiones se expanden en `docs/decisions/`.
> **As-built:** este doc es la FUNDACIÓN (2026-06-15, pre-implementación) y se conserva como fue
> escrita. El mapa de lo CONSTRUIDO (módulos reales, flujos, diagramas, modo workspace, semántica
> exacta del pin) vive en `ARCHITECTURE-MAP.md` (2026-07-04).

---

## 1. Terminología

- **Meta-Factory**: la plataforma descrita aquí. Su producto son *fábricas*. Reside en la raíz.
- **Fábrica (producto)**: un sistema generado por el Meta-Factory que, a su vez, fabrica
  artefactos de un dominio (ASF fabrica agentes; un Full-Stack-Factory fabricaría apps web).
- **Producto-de-fábrica**: lo que una fábrica produce (un agente, una app). El Meta-Factory no
  los toca directamente; los gobierna *transitivamente* a través de la fábrica.
- **Factory-spec**: la especificación SDD que define una fábrica. Dos mitades (§5).
- **Sustrato de producción de fábricas**: los 13 invariantes transversales que toda fábrica
  confiable necesita, independientes del dominio que fabrique (§3).
- **La columna anti-sello-de-goma** (heredada de ASF/ADR-006): los tres cerrojos que vuelven
  imposible marcar una compuerta sin prueba real. El corazón de la confianza.
- **Bus de veredictos**: el contrato por el cual toda operación cara devuelve un veredicto
  ≤N líneas + puntero al artefacto; el log crudo nunca entra al contexto del orquestador.
- **Seed (semilla)**: el kernel de confianza mínimo, auditado a mano y congelado, del que todo
  lo demás deriva su confianza (§7, Stage 0).
- **Meta-estación (Mk)**: unidad atómica de la línea que construye una *fábrica* (§6).
- **Sombra determinista** (ASF/ADR-023): por cada obligación narrativa que no deba saltearse,
  un hook/CLI que la detecta o impide. El sustrato narrativo declara; el determinista garantiza.

---

## 2. Tres contextos de construcción (ASF tenía dos)

ASF distinguió **construcción de fábrica** vs **construcción de producto**. El Meta-Factory
agrega un nivel y los renombra para evitar confusión:

| Nivel | Qué se construye | Responsable | Mecánica de determinismo | Frecuencia |
| --- | --- | --- | --- | --- |
| **N2 — Meta** | el Meta-Factory mismo | ingeniería de plataforma + Claude Code, gobernado por el **seed congelado** | la columna + los dos verificadores aplicados a sí mismo (punto fijo, §7) | baja |
| **N1 — Fábrica** | una fábrica (ASF, Full-Stack) | la línea de meta-estaciones del Meta-Factory, operada vía Claude Code | meta-estaciones M0–M8 con compuertas | media (una por fábrica + cada update de template) |
| **N0 — Producto** | un agente / una app | la línea de estaciones de *esa fábrica* | el modelo de estaciones de la fábrica (heredado de ASF) | alta |

Principio que cruza los tres niveles (de ASF, generalizado): **cada nivel es verificado por una
capa al menos tan confiable como él; la auto-modificación de la cadena de confianza se gatea por
re-derivación desde la capa inmediatamente más confiable** (§7, `SELF-IMPROVEMENT.md`).

---

## 3. El sustrato de producción de fábricas (los 13 invariantes)

Esto es lo que ASF descubrió —a los golpes— que necesita TODA fábrica confiable, sin importar
qué fabrique. Es el análogo, un nivel arriba, de las "siete capacidades de producción" de ASF.
**El Meta-Factory hornea estos 13 en cada fábrica que emite, verificados por construcción.**

| # | Invariante | Qué garantiza | Origen en ASF |
| --- | --- | --- | --- |
| I-1 | **Columna anti-sello-de-goma** (3 cerrojos) | el veredicto `passed` lo computa solo un verificador determinista desde exit codes reales; los artefactos de prueba son inmutables para el modelo; un hook `Stop` re-corre verify | ASF/ADR-006 |
| I-2 | **Estaciones como dato** | la línea es una secuencia de YAML, no ramas en el código; cero identidad de dominio hardcodeada | §9.1, anti-patrón #4 |
| I-3 | **Frontera del determinismo** | modelo para lo creativo (slots acotados), código para lo invariante; el determinismo vive en proceso+verificación+contratos, nunca en el contenido generado | PF-1/PF-2, ASF/ADR-009 |
| I-4 | **Escalera de automatización A/B/C** | automático / borrador+consentimiento / provisional-con-honestidad; nunca "bloquear o fabricar" | ADR-010 |
| I-5 | **Frontera generado/dominio** ⚠️ **AMENDADO por `ADR-011`** (2026-06-15): el 100% se genera, NO hay `domain/` humano que proteger; sobrevive sólo la primitiva **DES-1** (andamiaje regenerable e idempotente, `reference/PRIMITIVES.md`). Copier es UNA herramienta elegible en el plan, no la plataforma (`ADR-012`). Texto histórico → | Copier es dueño de `generated/` (100% sobrescribible), el ingeniero de `domain/`; conexión por herencia/inyección → un update no pisa código humano | ADR-014 |
| I-6 | **Ley de colocación** | cada pieza en el sustrato más determinista que la sostenga; el modelo es el último recurso; veredictos al contexto, logs al disco | ADR-020 |
| I-7 | **Bus de veredictos** | toda operación cara emite veredicto ≤N líneas + puntero; revelación progresiva (triage haiku → slice quirúrgico) | `factory check`, D1 de CONTEXT |
| I-8 | **Memoria como artefacto del repo** | hooks deterministas escriben el journal desde git+ledger (cero narrativa del modelo); clonar el repo = clonar la memoria | ADR-019 |
| I-9 | **Esquema de memoria narrativa** | tipos de doc = semántica de mutación: STATE (overwrite), LOG (append), decisions/ (inmutable), work/ (por-incremento), reference/ (estable) | ADR-021 |
| I-10 | **RTM + árbol de evidencia** | requisitos con id estable y `satisfied_by`; commits con trailers station/spec-refs/proof-sha; matriz requisito↔estación↔commit↔archivo re-derivada de artefactos | ADR-017/018 |
| I-11 | **Doctrina de los dos verificadores** | re-derivación sobre custodia: un CI externo reconstruye el veredicto en runner limpio y lo compara contra el pineado honesto; única capa intocable | ADR-022 |
| I-12 | **Sombra determinista de la capa meta** | toda regla narrativa que no deba saltearse tiene su detector/impedimento determinista; el juicio nunca se hard-blocka | ADR-023 |
| I-13 | **Honestidad de límites** | HONEST-STATE / AUDIT como artefactos de primera clase; aspiración nunca confundida con realidad; S0/M0 rehúsan en vez de fabricar defaults | PF-8, HONEST-STATE.md |

> Estos 13 son el "Half B" de toda factory-spec (§5): el Meta-Factory los provee estandarizados.
> Lo que cambia entre fábricas es el "Half A" (el dominio que fabrica).

---

## 4. Principios fundamentales (heredados y extendidos)

Heredamos PF-1…PF-8 de ASF (determinismo donde es alcanzable; modelo-para-lo-creativo;
separación lógica/sustrato; probar-y-documentar-antes-de-avanzar; checkpoints pequeños;
aislamiento estricto; automatización máxima segura; honestidad de límites). Agregamos:

- **PF-9 — Legitimidad del punto fijo.** Solo el Meta-Factory se aplica a sí mismo; toda otra
  fábrica se construye desde una capa más confiable (su Meta-Factory). Self-aplicación =
  pertenencia a la propia clase de producto (`VISION.md §2.2`).
- **PF-10 — Re-derivación sobre custodia.** No se confía en un artefacto guardado: se confía en
  poder reconstruirlo idéntico en un runner limpio. Replicable > archivado (ASF/ADR-008).
- **PF-11 — Sombra determinista universal.** Generaliza ADR-023: cualquier obligación de
  cualquier nivel que no deba saltearse recibe su detector determinista. La narrativa declara,
  el código garantiza.
- **PF-12 — El orquestador opera sobre interfaces.** El contexto largo-vivo del modelo potente
  consume specs/veredictos/reportes/decisiones; nunca implementación cruda. La economía no son
  tokens totales: son **tokens residentes** (`CONTEXT-ECONOMY.md`).

---

## 5. La factory-spec: el contrato de entrada SDD

Una fábrica se define por una **factory-spec** (machine-readable `factory.spec.yml` + prosa
`docs/*.md`, cuyo esquema canónico lo **define el Meta-Factory**, no se deriva de ninguna
fábrica). Tiene dos mitades explícitas, igual que el spec de ASF tenía Mitad A / Mitad B —
pero un nivel arriba:

```yaml
# factory.spec.yml  (ilustrativo, recortado)
factory: { name, slug, maturity }

# ── MITAD A: DOMINIO DE LA FÁBRICA (especificado por fábrica) ──
domain:
  produces: "sistemas agénticos de producción"        # qué fabrica esta fábrica
  target_framework: { name: langgraph, provider_agnostic: true }
  product_capabilities:                                 # el "sustrato" que la fábrica hornea en SUS productos
    - { id: observability, tools: [otel, langfuse], invariant: "span con provenance en cada decisión" }
    - { id: traceability,  tools: [neo4j, w3c_prov], invariant: "join key en cada nodo de linaje" }
    # ... (para ASF: las 7 capacidades; para Full-Stack: auth, ci, iac, ...)
  station_sequence:                                     # la línea de ESA fábrica (estaciones como dato, I-2)
    - { id: s00, name: "spec contract", activation: always }
    - { id: s01, name: "observability substrate", activation: always }
    # ... S2..Sn de la fábrica
  provision_modes: [prompt, integration, custom]        # niveles A/B/C por elemento (I-4)
  proof_check_types: [py_compile, deps, imports, pytest, ruff, mypy, topology, schema, substrate]

# ── MITAD B: SUSTRATO DE PRODUCCIÓN DE FÁBRICAS (estandarizado por el Meta-Factory) ──
factory_substrate:
  anti_rubber_stamp_column: true        # I-1 — no opcional, jamás
  verdict_bus:        { max_lines: 10 } # I-7
  generated_domain_boundary: true       # I-5
  memory_schema:      adr021            # I-8/I-9
  rtm:                { required: true }# I-10
  two_verifier_ci:    { rederive: true, pinned_verdict: true } # I-11
  placement_law:      true              # I-6
  context_budget:     { claude_md_max_lines: 120 } # PF-12

# ── REQUISITOS (espina SDD; cada uno con id estable + satisfied_by) ──
requirements:
  functional:
    - { id: REQ-F-001, statement: "...", satisfied_by: [s01] }
```

- **Mitad A** se especifica por fábrica: incluye QUÉ fabrica, contra qué framework, qué
  capacidades hornea en sus productos, y cuál es su secuencia de estaciones (que el
  Meta-Factory materializa como dato, no como código).
- **Mitad B** es donde el Meta-Factory estandariza: los 13 invariantes. Cada clave activa o
  parametriza una meta-estación. **No son negociables en su existencia; sí en su parámetro**
  (p.ej. `max_lines` del bus, no "¿hay bus?").
- **Requirements** es la espina SDD (ADR-003): sin requisitos declarados con `satisfied_by`
  válido, M0 rehúsa. El RTM se re-deriva de artefactos al final (I-10).

---

## 6. La secuencia canónica de meta-estaciones (construir una fábrica)

La línea del Meta-Factory construye una **fábrica**. Cada meta-estación corre las cuatro fases
de ASF (Construir → Probar → Documentar → Compuerta) bajo la columna anti-sello (I-1).

| # | Meta-estación | Construye en la fábrica nueva | Prueba determinista (resumen) |
| --- | --- | --- | --- |
| **M0** | Contrato de factory-spec (SDD) | nada (valida la entrada) | schema + completitud + cierre RTM (todo requisito mapea a una estación activa) |
| **M1** | Seed & columna | el kernel de confianza de la fábrica: verifier + 3 cerrojos + deny-list | corromper un veredicto → la fábrica recién nacida lo rechaza (prueba de bloqueo) |
| **M2** | Engine & estaciones-como-dato | el runner/gate/sequence (dominio-agnóstico) + los YAML de la secuencia declarada | con la misma factory-spec, el orden y el set de rutas son idénticos entre corridas |
| **M3** | Bus de veredictos & CLI | los verbos `check`/`verify`/`gate`/`trace`/`rtm` con salida acotada | un fallo inyectado aparece como `file:line` en ≤N líneas; el log completo está en disco y NO en el veredicto |
| **M4** | Template del producto & frontera generado/dominio | el `template/` de la fábrica + `.copier-answers` + migrations + `_skip_if_exists` de `domain/` | un archivo de dominio sobrevive a un re-scaffold (frontera no decorativa, I-5) |
| **M5** | Memoria & RTM | el árbol `docs/` (esquema ADR-021) + journal determinista + árbol de evidencia | `rtm` re-deriva de artefactos: SATISFIED/PROVISIONAL/UNSATISFIED; el journal deriva de git+ledger |
| **M6** | Dos verificadores (CI externo) | el workflow de re-derivación + el veredicto pineado + pre-push tripwire | runner limpio reconstruye el dummy y exige el veredicto pineado; desvío en cualquier dirección = rojo |
| **M7** | Harness (`.claude/` de la fábrica) | hooks = sombras de la columna; agents = contratos de delegación; commands = flujo del operador; CLAUDE.md ≤ presupuesto | cada prohibición de un agent tiene sombra en hook/CLI (I-12); presupuesto de residencia medible en diff |
| **M8** | Auto-test anti-fachada (e2e) | — (corre la fábrica recién nacida sobre un producto dummy mínimo) | scaffold REAL + compile + correr las gates del dummy en su propio venv; **render verde NO basta** (la lección del façade-trap de ASF) |

M8 es la compuerta más importante y la que ASF aprendió tarde (AUDIT §"los dos errores se
componen"): **una fábrica se prueba construyendo de verdad un producto, no verificando que sus
templates renderizan.** Seis bugs invisibles a render+ast aparecieron en ASF solo al
scaffoldear+compilar. M8 lo vuelve obligatorio e insalteable.

### 6.1 El dogfood: el Meta-Factory ES la salida de su propia línea

El Meta-Factory se define por la factory-spec `metafactory.spec.yml`, cuyo `domain.produces` es
*"fábricas"* y cuya secuencia de estaciones SON M0–M8. Correr M0–M8 sobre esa spec **produce el
Meta-Factory**. Ése es el punto fijo de `VISION.md §3` hecho operativo — y la única
auto-aplicación legítima del ecosistema (PF-9).

---

## 7. Estructura del repositorio y la jerarquía de confianza (Stages 0–3)

```
Meta_Factory/
├── seed/                          # ── STAGE 0: kernel de confianza, AUDITADO A MANO, CONGELADO ──
│   ├── verifier.py                #   el ÚNICO escritor de veredictos; computa passed desde exit codes
│   ├── column.md                  #   doctrina inmutable de los 3 cerrojos
│   └── external_ci.yml            #   el workflow de re-derivación (dos verificadores)
│   # Pequeño y legible. Cambiarlo = Nivel C siempre (consentimiento humano) + el seed VIEJO
│   # debe validar el seed NUEVO antes de promover (`SELF-IMPROVEMENT.md §3`).
├── src/metafactory/               # ── STAGE 1: la maquinaria (auto-mejorable bajo la columna) ──
│   ├── cli.py                     #   meta new | station | verify | check | trace | rtm | promote | improve
│   ├── engine/{station,sequence,runner,gate,run_context}.py
│   ├── verify/{checks/, report.py}   # report.py materializa el bus de veredictos (I-7)
│   ├── codegen/{copier_driver,answers,apply_station}.py
│   ├── spec/{model,loader,validator}.py + factory.schema.json   # la espina SDD (I-10, ADR-003)
│   └── stations/{_registry.yml, m00..m08.yml, templates/}        # las meta-estaciones (dato, I-2)
├── .claude/                       # ── el harness de CONSTRUCCIÓN del Meta-Factory ──
│   ├── settings.json              #   hooks (la columna) + permissions.deny
│   ├── commands/                  #   /meta-new, /meta-station, /meta-improve, /incremento
│   ├── agents/                    #   writer(sonnet), reviewer(sonnet|opus), triage(haiku), spec-analyst
│   └── hooks/                     #   proof_protect, gate_guard, stop_proof, commit_guard, post_edit_quality, session_journal, session_start
├── template/                      # ── EL TEMPLATE DE FÁBRICA: lo que toda fábrica HEREDA al nacer ──
│   └── factory/                   #   un chasis de fábrica COMPLETO: seed/ + src/<f>/ + .claude/ + template/ + docs/ + external CI
│       # Toda fábrica emitida ya trae los 13 invariantes cableados y verificados. Es el one-shot.
├── factories/                     # ── STAGE 2: fábricas producidas (aisladas) ──
│   ├── agent-systems-factory/     #   ASF regenerado como PRODUCTO (plug-in LangGraph) — ADR-006
│   └── full-stack-factory/        #   ejemplo de segunda fábrica (plug-in web stack)
│       # cada una con su PROPIO seed (heredado), sus gates, su CI externo. Stage 3 (sus productos)
│       # vive dentro de cada fábrica, fuera del sys.path del Meta-Factory (aislamiento, PF-6).
└── docs/                          # ── memoria narrativa del Meta-Factory (esquema ADR-021) ──
    ├── STATE.md · LOG.md · decisions/ · work/ · reference/
```

**Jerarquía de independencia / confianza** (de ASF/ADR-022, extendida a N niveles; cada capa es
más cara y más confiable que la de abajo):

```
seed congelado (auditado a mano)
  > CI externo del Meta-Factory (otra máquina, re-deriva el dummy-fábrica)
    > columna del Meta-Factory (hooks/CLI, mismo actor)
      > CI externo de cada fábrica producida
        > columna de cada fábrica
          > gates de cada producto-de-fábrica
```

**Aislamiento (PF-6):** la maquinaria del Meta-Factory vive solo en `src/metafactory/`; cada
fábrica, solo en `factories/<slug>/`. Ninguna fábrica está en el `sys.path` del Meta-Factory.
Verificado por prueba (`test_metafactory_does_not_import_factories`), igual que ASF.

---

## 8. El harness de construcción y la correspondencia compuerta→mecanismo

El harness es **Claude Code**, construido alrededor de sus primitivas nativas: **hooks** (el
determinismo de las compuertas), **slash commands** (el flujo del operador), **subagentes** (los
slots creativos y la delegación), **skills** y **settings** (incluido `permissions.deny`).
Ninguna obligación invariante depende de una instrucción en lenguaje natural; se materializa en
estas primitivas. Cada fábrica producida hereda su propio harness análogo (M7).

| Garantía (un nivel arriba que ASF) | Primitiva | Mecanismo |
| --- | --- | --- |
| No avanzar una meta-estación sin la anterior gateada | `PreToolUse` gate_guard (exit 2) | bloquea `meta station` hacia k si la proof de k-1 no pasa o el hash no coincide |
| Artefactos de veredicto intocables por el modelo | `PreToolUse` proof_protect + deny-list | niega escrituras a proof/ledger/rtm que no vengan del verifier |
| No declarar fábrica/estación lista sin prueba | `Stop` stop_proof (exit 2) | re-corre verify de la meta-estación actual; bloquea el turno si falla |
| El commit no atribuye trabajo no probado | `PreToolUse` commit_guard (exit 2) | exige trailers + proof referenciado con passed=true + proof-sha que coincide |
| El orquestador no quema contexto en logs | bus de veredictos (CLI, no hook) | `meta check` emite ≤N líneas + path; el camino barato es el ergonómico (no se castiga al writer) |
| La capa meta no se saltea bajo presión | sombra determinista (I-12, PF-11) | por cada regla narrativa, un detector en hook/CLI; el juicio nunca se hard-blocka |

---

## 9. Matriz de prevención de anti-patrones (subida un nivel)

| # | Anti-patrón | Mecanismo estructural que lo previene |
| --- | --- | --- |
| 1 | **Una fábrica que se auto-fabrica fuera de su clase** (el error de ASF) | PF-9: solo el Meta-Factory se auto-aplica; ASF se regenera como producto (ADR-006) |
| 2 | Render verde tomado por producto funcional (façade-trap) | M8: e2e real obligatorio (scaffold+compile+run), insalteable |
| 3 | Capa meta gobernada por prosa que se saltea bajo presión | PF-11 / I-12: sombra determinista universal |
| 4 | Orquestador caro re-leyendo dumps de tests cada turno | I-7 bus de veredictos; PF-12 interfaces, no implementación |
| 5 | Sub-delegación (Opus hace lo que debía hacer Sonnet) | delegación ergonómica + enrutamiento de modelo como dato (`CONTEXT-ECONOMY.md`) |
| 6 | Compuertas con sello de goma | I-1 columna: veredicto no escribible por el modelo, hash recomputado, Stop re-corre |
| 7 | Identidad de dominio hardcodeada en el código de la fábrica | I-2 estaciones como dato; lo específico vive en la factory-spec |
| 8 | Confiar en un artefacto que nadie puede re-derivar | PF-10 / I-11: re-derivación sobre custodia en CI externo |
| 9 | Auto-mejora que corrompe la propia cadena de confianza | jerarquía de confianza (§7) + gate de blast-radius (`SELF-IMPROVEMENT.md`) |
| 10 | Requisitos "cumplidos" por narrativa, no por evidencia | I-10 RTM re-derivado de artefactos; UNSATISFIED corta el CI |

---

## 10. Primer incremento propuesto

El bootstrap mínimo que demuestra el punto fijo de extremo a extremo está gobernado en
`docs/work/BOOTSTRAP-INCREMENT.md`. En síntesis: escribir a mano el **seed** (Stage 0) y la
maquinaria base (CLI + engine + verifier con el bus de veredictos + validador de factory-spec);
las meta-estaciones M0–M3 + M8; el `template/factory/` acotado a esas estaciones; los hooks de
la columna con `permissions.deny`; y la factory-spec de un **dummy-fábrica** mínimo. Criterio de
aceptación = **demostración de bloqueo**: al corromper el invariante de la columna en el dummy,
la prueba falla, la compuerta no abre, el hook `Stop` bloquea el turno, y el CI externo re-deriva
un veredicto distinto. Recién con eso probado se regenera ASF como producto (ADR-006).
