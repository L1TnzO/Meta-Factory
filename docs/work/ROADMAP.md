<!-- meta:doc sha=323172bd638f027523994c788181c6271dd0dd29 updated=2026-06-15T03:18Z -->
<!-- meta:doc sha=PENDING updated=2026-06-15T03:10Z -->
# ROADMAP — de la Meta-Factory actual a la generación COMPLETA y GENERALISTA de fábricas

> tipo: work (mapa vivo, semántica OVERWRITE como STATE) · creado: 2026-06-15T03:10Z
> Origen: la auditoría `reference/REGEN-AUDIT.md` midió que regeneramos ~70–75% del CHASIS de ASF
> pero ~5–10% del MOTOR DE GENERACIÓN y ~0% de la maquinaria (MCP/infra/plantillas), y que la
> factory-spec no describe la fábrica completa. Este doc lista TODOS los incrementos que faltan para
> cerrar ese hueco — no para ASF en particular, sino para CUALQUIER stack. No es ejecución: es el mapa.

## North star (el estado objetivo)

> Cualquier `factory.spec.yml` → una **fábrica completa de grado-producción**, para **cualquier stack**
> (LangGraph-Python, TS full-stack, …), generada **de manera segura** (cada paso gateado por la columna
> anti-sello), que a su vez genera sus productos y se verifica construyendo (M8 real), no renderizando.

Criterios de "llegamos": (1) una factory-spec nueva produce chasis + motor de generación + harness +
infra + MCP, todo heredando la columna completa; (2) **dos** stacks radicalmente distintos (ASF y
Full-Stack) se generan desde sus specs y pasan su M8 real; (3) el orquestador nunca escribe un veredicto.

## La apuesta arquitectónica central (el insight de Copier)

**Copier NO es el mecanismo de generación; es UN backend** (Python/Jinja). Si fuera el mecanismo, el
full-stack TS (frontend + backend + DB relacional) no entraría — Copier no scaffoldea un monorepo TS.

Por eso el sustrato se parte en dos, igual que I-2 (estaciones como dato) pero aplicado al **motor**:

| Lo que el SUSTRATO orquesta (igual para todo stack) | Lo que es DATO/PLUGIN por stack (elegido por `target`/`toolchain` del spec) |
| --- | --- |
| secuencia de estaciones · gate/veredicto · RTM · columna anti-sello · proof-bus · frontera generado/dominio (política) | **generador** (Jinja/Copier para Py · Plop/Hygen/Vite/plantillas para TS · LLM-slot acotado) · **toolchain de proof** (pytest/mypy ↔ tsc/vitest/eslint) · **bootstrap de deps** (uv sync ↔ npm/pnpm install) · **servicios de infra** |

Así ASF (LangGraph/Copier/pytest) y Full-Stack (TS/Plop?/tsc) son **instancias de la misma máquina**.
El motor no sabe Python de TypeScript: corre lo que el spec declara. **Ese es el corazón del roadmap.**

## Mapa de fases (dependencia → arriba habilita abajo)

| Fase | Qué resuelve | Habilita |
| --- | --- | --- |
| **A · Spec completo y generalista** | la fuente de verdad sabe describir CUALQUIER fábrica | todo lo demás (el codegen lee de acá) |
| **B · Motor de generación generalista** | el hueco del ~5–10%: backend-plugin + línea multi-estación + proof en el toolchain del producto | C, D, E |
| **C · Seguridad: columna completa heredada** | "de manera segura" — toda fábrica generada hereda los 3 cerrojos + cadencia | E (fábricas que bloquean de verdad) |
| **D · Maquinaria de fábrica** | el 0%: infra, MCP, frontera generado/dominio generalista | E |
| **E · Dos fábricas de referencia** | forzar la generalización por bloqueo (G-8): ASF completo + Full-Stack | F |
| **F · Loop de mejora** | generate→verify→promote + corpus de scenarios diversos | auto-mejora durable |

## Los incrementos (ordenados; cada uno PRUEBA por bloqueo)

### Fase A — Spec completo y generalista
- **A1 · Gramática factory-spec v2 (dominio-agnóstica, espina SDD con dientes).** Capas L0 identidad ·
  L1 dominio (`capabilities` {invariant, artifact, proof, activation, status}) · L2 línea
  (`stations` {depends_on, templates, proof_checks {cmd, runs_in, status}}) · L3 maquinaria
  (`harness`/`mcp`/`infra`/`scaffolding`) · L4 sustrato · L5 requisitos {acceptance, satisfied_by,
  verified_by}. La generación se describe ABSTRACTA (artifacts + `generator` backend + `toolchain`),
  **no Copier**. `status` enum (built/declared-deferred/planned) = honestidad estructural (I-13).
  *Gate*: M0 valida; **negativos bloquean** (cap sin proof, req con verifier fantasma, depends_on roto); dummy verde (secciones opcionales).
- **A2 · ASF descrito COMPLETO en v2 + skeleton Full-Stack que valida.** ASF entero (7 capacidades con
  proof, S0–S8 con proof_checks, MCP, plantillas, infra, `product_contract` cosechado del `spec.schema.json`
  de ASF). El skeleton Full-Stack ejercita la MISMA gramática con otro stack. *Gate*: ambos validan
  (grammar generalista, no forma-de-ASF); reviewer fresco confirma fidelidad a ASF @ `b1fcb1f`.

### Fase B — Motor de generación generalista (el corazón)
- **B1 · Abstracción `Generator` (backend como plugin).** Interfaz {emitir artifacts desde (spec,station,dir)}.
  Backend 1: Jinja/Copier (Python). La **frontera generado/dominio** (owned vs human) pasa a ser política
  del motor, no de Copier. *Gate*: el backend renderiza un artifact en dir aislado; test de doble-backend
  (mismo artifact lógico por dos caminos) para probar que la interfaz no filtra el stack.
- **B2 · Línea de producto multi-estación (s00→sN como dato).** El motor corre el `station_sequence`
  del spec; cada estación emite sus artifacts y la gatea su `proof_checks`. Mata el patrón único actual.
  *Gate*: una fábrica con ≥2 estaciones genera y gatea cada una; corromper el artifact de s1 → s1 SHUT.
- **B3 · Proof en el toolchain DEL PRODUCTO (`runs_in: product_env`).** El bootstrap de deps y los
  comandos de verificación son DATO por stack (uv/pytest/mypy ↔ npm/tsc/vitest). Es el M8 real para
  productos no triviales + el árbol de evidencia por build (ASF/ADR-017-018, generalista). *Gate*: un
  proof_check corre pytest en el venv del producto y bloquea ante rojo; el mismo mecanismo acepta `tsc`.

### Fase C — Seguridad: la columna completa heredada ("de manera segura")
- **C1 · Columna completa horneada en el template.** Hoy la fábrica generada hereda sólo el Cerrojo 1
  (`proof_protect`); faltan Cerrojo 2/3 (`gate_guard` recompute, `stop_proof` re-verify) + cadencia
  (`commit_guard`/`increment_guard`) + `external_ci` parametrizado por fábrica (G-8 #6). *Gate*: una
  fábrica generada, en clon limpio, bloquea el sello de goma (corromper veredicto → rojo) sola.
- **C2 · Generación de harness por spec.** `hooks` (con su sombra I-12), `agents` (roles), `commands`
  (skills) emitidos desde L3. *Gate*: `agent_shadow` verde sobre la fábrica generada; un command declarado existe y corre.

### Fase D — Maquinaria de fábrica (lo que está en 0%)
- **D1 · Generación de infra/sandbox generalista.** `services` + topología + compose desde L3
  (Postgres/Neo4j para ASF; Postgres/Node/Vite para full-stack). *Gate*: la infra declarada levanta en el sandbox.
- **D2 · Generación de MCP.** El `factory-infra` MCP (tools tipados que el orquestador llama) desde L3.
  *Gate*: el MCP generado expone las tools declaradas; el orquestador las invoca contra el sandbox.
- **D3 · Frontera generado/dominio generalista.** La política "owned-por-el-motor vs escrito-por-humano"
  (I-5) independiente del backend (`_skip_if_exists` de Copier es UNA impl). *Gate*: re-generar no pisa `domain/`.

### Fase E — Dos fábricas de referencia (forzar la generalización por bloqueo, G-8)
- **E1 · ASF COMPLETO end-to-end.** La línea S0–S8 real, el producto LangGraph, las 7 capacidades
  materializadas; **paridad funcional con el ASF pineado** (`b1fcb1f`) por re-derivación. Cierra el ~5–10%.
  *Gate*: un producto de ASF generado pasa su M8 real (topología compilada, nodos, mypy --strict en su venv).
- **E2 · Full-Stack-Factory desde spec.** Frontend TS + backend TS + DB relacional. Es el **segundo
  backend** que PRUEBA que el motor (B) no es Python/Copier-bound. *Gate*: un producto full-stack generado
  compila (`tsc`), pasa sus tests (`vitest`) y levanta su DB — todo gateado, ningún veredicto a mano.

### Fase F — El loop de mejora
- **F1 · generate→verify→promote + corpus de scenario-specs.** Formas de spec diversas (del estado del
  arte: meta-harness/autocontext) ejercitan el motor antes de promover. Cierra G-8 de raíz: el patrón
  cascada deja de aparecer porque el corpus lo ejercita. *Gate*: promover exige verde en N scenarios diversos.

## Trazabilidad a la auditoría (cada hueco medido → su incremento)

| Hueco (REGEN-AUDIT) | % hoy | Incremento que lo cierra |
| --- | --- | --- |
| spec no describe la fábrica (mcp/infra/templates = 0) | — | **A1, A2** |
| motor de generación (codegen 941 + 53 plantillas) | ~5–10% | **B1, B2, B3, E1** |
| columna sólo Cerrojo 1 · commands 0 | ~40% / 0% | **C1, C2** |
| infra / MCP | 0% | **D1, D2** |
| frontera generado/dominio real | doctrina sin codegen | **B1, D3** |
| dominio-agnóstico (anti-G-2) | spec sí, motor no | **B1, E2** |

## Principios que NO se negocian en todo el roadmap

1. **Generación gateada**: el `verifier` es el único que escribe veredictos; cada fábrica/producto se
   verifica construyendo (M8 real por stack), nunca renderizando. La columna aplica AL acto de generar.
2. **Status honesto (I-13)**: nada `built` sin proof por bloqueo; lo no construido es `declared-deferred`, visible.
3. **Dos stacks antes de promover (G-8)**: cada capa del motor se ejercita con ASF *y* Full-Stack; si algo
   sólo funciona para uno, es un supuesto no parametrizado, no una victoria.

## Qué NO está en este roadmap (frontera honesta)

- Los PRODUCTOS de las fábricas (los agentes LangGraph, las apps full-stack) no se miden acá: medimos la
  capacidad de la FÁBRICA de generarlos. (Decisión del ingeniero, 2026-06-15.)
- Métricas cuantitativas (costo/cache/hooks): el subsistema existe (`OBSERVABILITY-METRICS.md`); su
  expansión es ortogonal a este roadmap.
