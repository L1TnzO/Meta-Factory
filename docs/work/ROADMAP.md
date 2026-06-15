<!-- meta:doc sha=04356474f47da1b27078c7416facec078218c806 updated=2026-06-15T19:59Z -->
<!-- meta:doc sha=PENDING updated=2026-06-15T03:43Z -->
# ROADMAP — de la Meta-Factory actual a la generación COMPLETA, GENERALISTA y SEGURA de fábricas

> tipo: work (mapa vivo, semántica OVERWRITE como STATE) · actualizado: 2026-06-15T03:43Z
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Otro
> orquestador implementa desde acá. Si algo no está en la doc, no existe. Orden de lectura para retomar
> en §0. Reescrito 2026-06-15 tras el mandato del ingeniero: **100% generado** (ADR-011), **primitivas
> no herramientas** (ADR-012), determinismo en verificación no en generación (I-3).

## 0. Si llegás sin contexto, leé en este orden

1. `reference/VISION.md` — por qué existe (el punto fijo legítimo) y qué buscaba el ingeniero.
2. `reference/PRIMITIVES.md` — **la filosofía**: primitivas de SEGURIDAD (fijas) vs de DISEÑO (la tech la
   elige el plan). Sin esto, este roadmap se malinterpreta (le pasó a la 1ª versión).
3. `decisions/011` (100% generado, muere I-5) y `decisions/012` (primitivas no herramientas) — las decisiones que reordenaron todo.
4. `reference/REGEN-AUDIT.md` — la MEDICIÓN que originó el roadmap (qué % de ASF regeneramos y qué falta).
5. `reference/ARCHITECTURE.md` — los 13 invariantes, las meta-estaciones M0–M8, los stages 0–3.
6. `STATE.md` — qué es verdad HOY. Después, este doc = el plan.

## 1. North star (el estado final)

> Cualquier `factory.spec.yml` → una **fábrica completa de grado-producción**, para **cualquier dominio**
> (agentes, web full-stack, mobile, IoT…), **generada de manera segura** (cada paso gateado), que produce
> el **mejor estado posible** de sus productos. La Meta-Factory **decide desde las specs** cómo llegar ahí.

Fábricas-objetivo concretas (todas desde su spec, ninguna hardcodeada): **ASF actual y muy mejorado** ·
**Full-Stack-Factory** (frontend+backend+DB) · **Mobile-Factory** · **IoT-Factory** · las que se especifiquen.

"Llegamos" cuando: (a) una factory-spec nueva produce chasis + producto, todo generado y verificado por
construcción; (b) ≥2 dominios radicalmente distintos pasan su M8 real desde sus specs; (c) el orquestador
nunca escribe un veredicto; (d) regenerar desde el spec re-deriva el sistema idéntico (código 100% derivable).

## 2. El modelo de operación (3 fases) — DISEÑO → BUILD → MEJORA

```
factory.spec.yml (inicial: qué fábrica, qué dominio, requisitos)
        │
        ▼   FASE I · DISEÑO  (Claude Code PLANIFICA, bajo SDD, con el skill de primitivas)
   spec → plan → tareas → criterios-de-verificación        [SDD-SOTA con dientes: M0 rehúsa lo incompleto]
   el modelo razona: "este dominio requiere las primitivas {DES-x}; la tech que las provee acá es {…}"
   → declara la tech en el DISEÑO/spec (DATO, no código del sustrato)  ← acá se decide "Copier" o "Plop" o…
        │
        ▼   FASE II · BUILD  (la línea M0–M8; el modelo genera el 100%, la columna verifica)
   cada meta-estación: GENERAR (slot creativo) → la columna VERIFICA (determinista) → M8 construye de verdad
        │
        ▼   FASE III · MEJORA  (el loop; la Meta-Factory empuja el producto a su mejor estado)
   observar → proponer → verificar → promover → rollback   [gate de blast-radius]
```

- **Fuente de verdad = spec + diseño SDD.** El código es artefacto derivable (ADR-011). Regenerar = re-correr.
- **El determinismo envuelve, no genera** (I-3): vive en la verificación, los gates y los contratos; el
  CONTENIDO lo crea Claude Code en slots acotados (SAFE-5). "Envolver a Claude Code, no reemplazarlo" (VISION §6).
- **La tech vive en el plan/spec, no en `src/metafactory/`** (ADR-012). El sustrato es dominio-agnóstico.

## 3. Principios no-negociables (gobiernan TODO incremento)

1. **Determinismo en verificación, no en generación** (I-3, ADR-012). Si un incremento mete `import <tech>`
   en el sustrato o templatea contenido deterministamente, está mal planteado.
2. **100% generado; spec+diseño = fuente de verdad** (ADR-011). No hay código humano protegido.
3. **Primitivas, no herramientas** (ADR-012). La tech se decide en planning / se declara en el spec.
4. **Seguridad horneada** (PRIMITIVES §2, SAFE-1..8): toda fábrica generada hereda la columna completa.
5. **Probar por bloqueo, nunca fake-green** (SAFE-1/2). Cada incremento cierra con una *prueba de bloqueo*.
6. **Dos dominios antes de promover** (G-8 generalizado, ADR-012): cada capa del motor se valida con ≥2
   dominios radicalmente distintos; lo que sólo sirve a uno es supuesto no parametrizado.
7. **Status honesto** (I-13): nada `built` sin proof; lo no construido es `declared-deferred`, visible.

## 4. Los incrementos (TODOS, ordenados por dependencia)

> Formato: **id · objetivo** — qué construye · *gate* (prueba por bloqueo) · depende-de. Cada uno es un
> incremento gobernado (ADR-010: abrir con `meta increment open`, código gateado, commit por fase).

### Fase 0 · Filosofía y fundaciones — ✅ HECHO esta sesión (2026-06-15)
- `reference/PRIMITIVES.md` (catálogo de primitivas), `ADR-011`, `ADR-012`, este ROADMAP. No es código:
  es la base que evita malinterpretar lo de abajo. (`REGEN-AUDIT.md` ya medía el hueco.)

### Fase A · Spec generalista (la fuente de verdad sabe describir cualquier fábrica)
- **A1 · Gramática factory-spec v2 (SDD-SOTA con dientes).** ✅ **HECHO (2026-06-15, `A1-GRAMMAR-V2`)**.
  `spec/{model,loader,validator}.py` + `factory.schema.json` describen las 6 capas: L0 identidad · L1
  dominio (`capabilities` {invariant, artifact, proof, **primitiva DES-x**, `tech`, status}) · L2 línea
  (`stations` {depends_on, proof_checks {cmd, **runs_in**, **toolchain**, status}}) · L3 maquinaria
  (harness/mcp/infra como DATO) · L4 sustrato (SAFE-*) · L5 requisitos {acceptance, satisfied_by, **verified_by**}.
  `validate_grammar_v2` agrega los dientes (negativos que BLOQUEAN: cap-sin-proof, tech-sin-primitiva,
  primitive mal formado, depends_on inexistente/inactivo/ciclo, verifier fantasma, status/runs_in fuera de
  enum) **shape-only, sin nombrar tech** (ADR-012, test lo prueba). Dummy y ASF verdes (secciones opcionales).
  Evidencia: `work/A1-GRAMMAR-V2-INCREMENT.md`. Depende: Fase 0.
- **A2 · ASF descrito COMPLETO en v2 + skeletons Full-Stack/Mobile/IoT que validan.** ✅ **HECHO
  (2026-06-15, `A2-ASF-SKELETONS`)**. `specs/agent-systems-factory…` = blueprint del ASF pineado
  (`ASF-PROVENANCE.md` @ `b1fcb1f`): 7 caps→primitivas DES, línea S0–S8 como stations v2 (depends_on +
  proof_checks), machinery, requirements con verified_by — status `declared-deferred` (codegen=F1).
  `specs/skeletons/{full-stack,mobile,iot}` ejercen la MISMA gramática con dominios radicalmente distintos
  (tsc/vitest/playwright · jest/detox · protoc/unity/qemu). *Gate cumplido*: los 4 validan 0 problemas;
  anti-overfit por test (≥6 primitivas/≥6 toolchains/4 frameworks); **reviewer fresco Opus: PASS 0 CRITICAL/HIGH**
  (1 MEDIUM arreglado: arista linaje `s2→s3`; el 2º DES-3 de atribución provisional → B1). Evidencia:
  `work/A2-ASF-SKELETONS-INCREMENT.md`. Depende: A1.

### Fase B · El skill de diseño + el flujo SDD (la PLANIFICACIÓN elige la tech)
- **B1 · Skill de primitivas de diseño.** ✅ **HECHO (2026-06-15, `B1-DESIGN-SKILL`)**. El catálogo DES vive
  como DATO (`reference/primitives.yml`, single source; test ata md↔yml). El skill
  `.claude/skills/design-primitives/SKILL.md` materializa el procedimiento dominio→primitivas→tech→declarar
  en el spec. Dientes: `design_coverage` (`spec/design.py`, CLI `spec.cli design-coverage`) exige una tech
  por primitiva requerida (`domain.required_primitives`) — CALLABLE, no en el gate M0 (eso es B2).
  *Gate cumplido*: corrido el skill sobre un dominio FRESCO (`specs/skeletons/data-pipeline`, `dagster-dbt`),
  el diseño declara 6 primitivas con tech → `validate`+`design-coverage` verdes; quitar una tech → coverage
  FALLA. Sustrato sin tech (ADR-012). Evidencia: `work/B1-DESIGN-SKILL-INCREMENT.md`. Depende: A1.
- **B2 · Flujo SDD de diseño (multi-fase, con dientes).** ✅ **HECHO (2026-06-15, `B2-SDD-DESIGN-FLOW`)**.
  `design_review` (`spec/design.py`, CLI `spec.cli design-review`) es la compuerta M0 del flujo de diseño:
  ACTIVA sólo si la spec declara `domain.required_primitives` (aseverar "pasé el flujo B1"), exige dos fases
  — **plan** (una tech por primitiva requerida; `design_coverage` cableado al fin) **+ criterios** (todo
  requisito cita un verifier real; el diente nuevo). Cableado a m00 como 3er check (kind `design_review` en
  el registry); `validator.py` SIN TOCAR (sigue catálogo-independiente, decoupling de A1). El *blueprint* que
  consume el build = la spec design-complete que M0 certifica. *Gate cumplido*: **2 dominios** distintos
  (data-pipeline ELT + full-stack web TS) declaran primitivas, cubren+verifican todo → PASAN; prueba por
  bloqueo END-TO-END: `meta station m00` queda SHUT ante un blueprint incompleto (−verifier `criterios:` /
  −tech `plan:`); líneas vivas dummy/ASF verdes (no-op). Evidencia: `work/B2-SDD-DESIGN-FLOW-INCREMENT.md`.
  Depende: B1, A1.

### Fase C · Motor de build generalista (genera el 100%, verifica construyendo)
- **C1 · Generación como slot creativo acotado (no backend hardcodeado).** ✅ **HECHO (2026-06-15,
  `C1-GENERATE-SLOT`)**. La acción de build `generate` (`codegen/renderer.py::_generate`, **ADR-013**) es el
  seam: el sustrato escribe el **brief** (blueprint, INPUT del spec), corre el **generador DECLARADO EN DATO**
  (`via` argv; env `METAFACTORY_BRIEF/DEST/ROOT`), y **no escribe el artefacto NI el veredicto** — la columna
  es el único árbitro (Cerrojo 1 intacto). `via` puede ser un scaffolder determinista o `claude -p "<brief>"`:
  mismo seam, otra data. *Gate cumplido*: prueba por bloqueo reproducible (`test_generate.py`, run_station+seed
  verifier reales) — generate→columna→**OPEN**, brief corrompido→**SHUT**, sin-generador→artefacto ausente→
  **SHUT**, y el mismo seam gatea un artefacto **TS** (principio #6). Prueba VIVA por CLI (scratch `genscratch`
  → `meta product-run` PASS; brief corrompido → SHUT). Guard ADR-012 (test): cero tech de generación en `src/`.
  Residual declared-deferred: el `via` LLM-vivo es el mismo seam, se ejercita en F1. Evidencia:
  `work/C1-GENERATE-SLOT-INCREMENT.md`. Depende: A1, B2.
- **C2 · Línea de producto multi-estación (s00→sN como dato, I-2).** ✅ **HECHO (2026-06-15,
  `C2-MULTI-STATION-LINE`)**. Mata el patrón único: m02 ya no renderiza una `s00` fija — la acción
  `materialize_line` (`codegen/renderer.py`) escribe `stations/<id>.yml` por cada `station_sequence` del spec
  (`SpecStation` lleva `builds`/`checks` ejecutables; estructura desde DATO — el contenido sigue siendo el slot
  `generate`, ADR-013). El motor (`_run_product_line`, iterativo) corre la secuencia; cada estación gatea con
  sus checks; la cadena usa `requires_prev` (de `depends_on`). *Gate cumplido*: dummy = línea de **2 estaciones**
  encadenadas (s00 greeting → s01 manifest que embebe s00), RTM 2/2, M0–M8 + `product-run` + `ci --rederive`
  verdes (re-pin s00+s01); ASF s00 materializado ≡ commit (pin válido). Prueba por bloqueo (`test_multistation.py`
  + viva por CLI): corromper s1 → **s1 SHUT**; corromper s0 → **s0 SHUT** + gate de s1 **SHUT** (predecesor).
  Diferido: gating DAG multi-predecesor (hoy cadena lineal). Evidencia: `work/C2-MULTI-STATION-LINE-INCREMENT.md`. Depende: C1.
- **C3 · Proof en el toolchain DEL producto (`runs_in: product_env`).** ✅ **HECHO (2026-06-15,
  `C3-PRODUCT-ENV-PROOF`)**. El `runs_in: product_env` (hoy sólo descriptivo, L2) se vuelve EJECUTABLE: kind
  `product_env` (`verify/checks/product_env.py`) — el sustrato ORQUESTA un `bootstrap` y un `cmd` declarados
  como DATA (pytest ↔ tsc ↔ node — nunca nombrados, ADR-012) en `cwd=workdir` con env **scrubbed**
  (`PYTHONPATH`/`VIRTUAL_ENV`/`PYTHONHOME` del Meta-Factory fuera): el producto no aprueba con el toolchain de
  la fábrica (SAFE-2/DES-8). Exit 0 sii bootstrap+proof exit 0; engine·gate·verifier·seed INTACTOS. *Gate
  cumplido*: dummy = línea de 3 estaciones (s02 corre el unittest del producto en un venv stdlib AISLADO);
  `product-run` PASS, M0–M8 + `ci --rederive` 3/3 (re-deriva el bootstrap del venv en árbol limpio), RTM 3/3;
  ASF intacto (pin 1/1). Prueba por bloqueo (`test_product_env.py` + viva por CLI): `import metafactory` FALLA
  dentro de product_env (DES-8 real, no cosmético); producto roto → SHUT; test del producto en rojo → s02 SHUT
  con s00/s01 VERDES (aislado); 2º dominio `node --test` por el MISMO kind, sin rama por-tech (principio #6).
  Evidencia: `work/C3-PRODUCT-ENV-PROOF-INCREMENT.md`. Depende: C2.
- **C4 · Árbol de evidencia por build (RTM generalizado).** req→capability→station→proof→artifact,
  re-derivado de `.proof/` (SAFE-4). *Gate*: el RTM re-deriva COMPLETE para una fábrica multi-estación;
  corromper un proof lo baja a UNSATISFIED. Depende: C2.

### Fase D · Seguridad: la columna completa heredada ("de manera segura")
- **D1 · Columna completa horneada en lo generado.** Hoy la fábrica generada hereda sólo el Cerrojo 1
  (`proof_protect`); faltan Cerrojos 2/3 (`gate_guard` recompute, `stop_proof` re-verify) + cadencia
  (`commit_guard`/`increment_guard`) + `external_ci` parametrizado por fábrica (REGEN-AUDIT G-8 #6).
  *Gate*: una fábrica generada, en clon limpio, bloquea el sello de goma sola (corromper veredicto → rojo). Depende: C1.
- **D2 · Generación de harness por spec.** `hooks` (con su sombra I-12), `agents` (roles), `commands`,
  `skills` emitidos desde L3. *Gate*: `agent_shadow` verde sobre la fábrica generada; un command generado corre. Depende: C2, D1.

### Fase E · Maquinaria de fábrica (como primitivas elegidas en el plan, NO hardcodeadas)
- **E1 · Infra/sandbox como primitiva (DES-4/5/8) elegida en planning.** `services`/topología/compose se
  declaran en el diseño (el plan eligió Postgres/Neo4j para agentes, Postgres/Node para web…) y se generan.
  *Gate*: la infra declarada levanta en el sandbox y un proof la usa. Depende: B2, C3.
- **E2 · Generación de MCP (primitiva de harness).** El MCP de la fábrica (tools tipados que el
  orquestador llama) desde L3. *Gate*: el MCP generado expone las tools declaradas; el orquestador las invoca. Depende: D2.

### Fase F · Las fábricas de referencia (prueban la generalidad por bloqueo, G-8)
- **F1 · ASF COMPLETO y MEJORADO end-to-end.** La línea S0–S8 real, el producto LangGraph, las 7
  capacidades materializadas; **paridad-o-mejor** vs el ASF pineado `b1fcb1f`. Cierra el ~5–10% de la
  auditoría. *Gate*: un producto de ASF generado pasa su M8 real (topología compilada `get_graph()`, nodos
  con fake-LLM, `mypy --strict` en su venv). Depende: C1–C4, D1–D2, E1.
- **F2 · Full-Stack-Factory desde spec.** Frontend TS + backend TS + DB relacional. El segundo dominio
  radicalmente distinto que PRUEBA que el motor no es Python/agente-bound. *Gate*: un producto full-stack
  generado compila (`tsc`), pasa `vitest` y levanta su DB — todo gateado. Depende: C1–C4, D1–D2, E1.
- **F3 · Mobile-Factory · IoT-Factory.** Dominios adicionales (React Native/Flutter; MQTT/embebido) que
  estiran las primitivas. *Gate*: cada una genera un producto que pasa su M8 en su toolchain. Depende: F1, F2.

### Fase G · Loop de mejora (el "mejor estado posible de los productos")
- **G1 · observar→proponer→verificar→promover→rollback + gate de blast-radius** (`SELF-IMPROVEMENT.md`).
  La Meta-Factory itera una fábrica hacia el mejor estado de su producto, desde su spec. *Gate*: una
  promoción que baje el veredicto pineado de cualquier fábrica downstream → rojo. Depende: F1, F2.
- **G2 · Corpus de scenario-specs diversos.** Formas de spec variadas (ECC 2.0: meta-harness/autocontext)
  ejercitan el motor antes de promover; cierra G-8 de raíz. *Gate*: promover exige verde en N scenarios diversos. Depende: G1.

## 5. Trazabilidad a la auditoría (cada hueco medido → su incremento)

| Hueco (REGEN-AUDIT) | % hoy | Incremento |
| --- | --- | --- |
| spec no describe la fábrica (mcp/infra/templates = 0) | — | A1, A2 |
| no hay flujo de DISEÑO que elija tech por primitiva | — | B1, B2 |
| motor de generación (sólo patrón único) | ~5–10% | C1, C2, C3, C4, F1 |
| columna sólo Cerrojo 1 · commands 0 | ~40% / 0% | D1, D2 |
| infra / MCP | 0% | E1, E2 |
| dominio-agnóstico (anti-G-2, generalidad real) | spec sí, motor no | A2, B1, F2, F3 |
| loop de mejora / best product state | — | G1, G2 |

## 6. Dependencias y paralelización

- **Camino crítico**: A1 → A2 → B1 → B2 → C1 → C2 → {C3, C4} → {D1 → D2} → E1 → F1/F2 → G1 → G2.
- **Paralelizable**: A2 (harvest) corre junto a B1 (skill) una vez A1 fija la gramática. F2/F3 corren tras
  F1 valida el camino. E2 (MCP) puede ir junto a F1.
- **Regla de orden**: no empezar C (motor) sin A (gramática) cerrada — el motor lee del spec; generar sin
  spec es adivinar (la lección que originó este orden).

## 7. Para el próximo orquestador (cómo retomar sin contexto)

- **Re-verificar > recordar**: `meta check` (estado vivo), `meta recall <tema>` (rebanada), `meta rtm`.
- **Disciplina** (no opcional): abrí incremento (`meta increment open <slug>`) antes de tocar código
  (`increment_guard` lo exige); commit por fase con trailers (`commit_guard`); documentá en el gate, no al
  final (la lección de `HONEST-STATE.md §1`: la 1ª construcción documentó al cierre y casi miente).
- **Delegación** (economía): el bulk (harvest, suites, scaffolding) → Sonnet; la trust-chain (gramática,
  columna, primitivas, juicio de cierre) → Opus, con ojos propios (`CONTEXT-ECONOMY.md`).
- **Nunca fake-green**: el cierre lo sella la re-derivación + las gates, no la prosa. Si dudás, es rojo.
- **Cuándo actualizar este doc**: al cerrar cada incremento, marcá su estado acá (✅/🟡) y refrescá STATE.
  Es OVERWRITE: el mapa refleja el presente, no acumula historia (eso es LOG).
