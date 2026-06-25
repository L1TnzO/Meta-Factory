<!-- meta:doc sha=8e4f68e3e1613a12bbb88b9052e28d8d2bb33393 updated=2026-06-25T21:36Z -->
# ADR-017 — Re-dirección SOTA: espina de grafo de proyecto + delegación verificada (no revisada)

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-25T21:35Z |
| Decide | el ingeniero (2026-06-25, tras auditoría profunda de 6+3 subagentes); ejecuta el orquestador |
| Generaliza | ADR-004 (bus de veredictos / economía de contexto), ADR-007 (memoria single-source), ADR-008 (métricas gratis), ADR-009 (docs content-addressed / sha-stamps), ADR-012 (primitivas no herramientas: la tech es PLAN), ADR-013 (generación como slot orquestado) |
| Referencia | `work/SOTA-REDESIGN-DIRECTION-INCREMENT.md` (roadmap faseado + punteros); memoria de sesión `sota-redesign-graph-spine`, `target-operating-model-sota`, `honest-reassessment-2026-06-25` |

## Contexto

Auditoría profunda (2026-06-25, Opus de cerebro + 6+3 subagentes Sonnet leyendo el bulk que el orquestador
nunca cargó — dogfood del modelo de costos). Hallazgo central, fundado en evidencia:

- **El motor FUNCIONA.** La FSK genera apps reales (snipeit = 15.435 LOC Kotlin, jOOQ type-safe, JOINs que
  computan depreciación al leer) verificadas contra **PG/HTTP/Chromium VIVOS**, no por prosa. La verificación
  tiene **dientes que atraparon bugs reales** (`be3805c` fail-open, `a002dae` requires_prev, MAT-4 falso-rojo);
  **0 reverts en 374 commits**. El codegen **no es overfit** (<0,5%; los literales de dominio viven en comentarios).
- **Lo que FALTA es la capa de DIRECCIÓN (outer-loop).** `meta increment close` verifica *cumplimiento de
  proceso* (árbol limpio + estación verde), NO que se entregó el alcance prometido; el `declared-deferred` es un
  **escape sin gate** (nada mide su acumulación ni le pone fecha) → presión sistemática a incrementos cada vez
  más chicos. Las "métricas" (`.metamem/metrics.jsonl`) son **conteo de tool-calls**, sin atribución de outcome
  por-incremento → no hay instrumento ingenieril para decidir si un incremento valió la pena.
- **Costo y mantenibilidad.** Se usó Opus-xhigh para casi todo (no es consciencia de costos), y existe un
  monolito (`factories/full-stack-kotlin/codegen/scaffold_product.py`, ~8,5k líneas, 221 funciones) que viola
  cohesión/descubribilidad — funciona pero no se puede navegar ni delegar barato.
- **Snipe-IT fue un benchmark demasiado duro** (17 incrementos ADOPT para un producto): pasa a **regresión**,
  no a punto de partida. El sweet-spot real es el 80% CRUD del día 1.

El estado del arte (investigado, fuentes en §Referencias del incremento) **colapsa** los hilos que tratábamos
por separado —navegación, delegación barata, handoff, calidad, costo— en **un solo artefacto**.

## Decisión

### 1. La espina: UN grafo de conocimiento del proyecto, content-addressed y consultable
Un solo grafo unifica navegación + contrato-de-delegación + handoff + alcance-de-verificación (es la MISMA
pieza para los cuatro). No es "agregar un grafo": es reconocer que el **RTM** (`req→capability→station→proof→
artifact`) y el **grafo de ADRs/`.proof/`** que YA tenemos son grafos, y unirlos con el grafo **estructural
del código** que falta.

- **Nodos**: `File · Symbol · Requirement · Decision(ADR) · Station · Spec · Proof`.
- **Aristas**: `DEFINED_IN · CALLS · IMPORTS · IMPLEMENTS · VERIFIES · GOVERNS · SUPERSEDES · GENERATES · SATISFIES`.
- Consultas de 2 saltos ("¿qué ADR gobierna esta función?", "¿qué requisitos satisface este módulo?") **sin una
  sola llamada a LLM**.
- **Incrementalidad** = los sha-stamps de ADR-009 EXTENDIDOS del doc al código: hash por nodo +
  dirty-propagation por aristas → re-deriva sólo el sub-grafo cambiado (Merkle-DAG, como Nix/Bazel/Cursor).
- **La tech es PLAN, no mandato (ADR-012).** Candidatas de arranque mínimo: `tree-sitter` (py/kt/ts/go) +
  PageRank (repo-map ~1k tokens para todo el repo) + un store liviano. SCIP, embeddings, un graph-DB dedicado o
  un CPG son **upgrades diferidos-hasta-medición**. Regla dura: la estructura se RE-DERIVA del AST, **no se
  narra**; los embeddings sólo para búsqueda difusa, **nunca** para "quién llama a esto".
- **Ventaja de partida**: el error #1 del SOTA es el "grafo sólo-código" (Cursor/Aider/Cody lo son). Nosotros
  arrancamos con requisitos y decisiones cableados.

### 2. Delegación "verificar, no revisar" (generación barata y SEGURA)
Cómo delegar GENERACIÓN (escribir, no sólo leer) a un modelo más barato sin que un modelo caro lea cada línea
—porque si Opus revisa todo, la delegación no ahorra nada—. Generaliza ADR-013 (slot orquestado) y ADR-004
(bus de veredictos):

1. **Contrato primero**: se escribe la interfaz tipada/schema ANTES de generar → el type-checker es el revisor.
2. **Blast-radius acotado**: el subagente `generator` (Sonnet) escribe SÓLO en el slot, enforzado por hook
   `PreToolUse` (la máquina, no la confianza). Alcance-de-cambio == alcance-de-verificación.
3. **Auto-verificación**: el worker corre sus propios gates (typecheck·compile·tests·**PBT**·static) y devuelve
   un **veredicto** estructurado `{status, check, exit_code, log_ref}`, **no el código** (vía `context:fork` →
   el código generado nunca entra al contexto de Opus).
4. **Opus lee el veredicto, no el código.** VERDE → acepta. ROJO → falla estructurada de vuelta a Sonnet, ≤2
   reintentos. Rojo persistente **o** path de seguridad → escala al `reviewer` Opus *sobre la falla puntual*.
5. **PBT (property-based testing) es el upgrade de gate clave**: expone 30-32% de bugs que los tests por-ejemplo
   no ven.

**Calibración honesta (no es "nunca revisar"):** los gates NO atrapan no-ops semánticos (oráculo malo),
bugs de seguridad (29-45% del código IA), paquetes alucinados (~20%) ni spec ambigua. Se confía en el gate
para el GRUESO y se gastan ojos de Opus SÓLO en el **residuo irreducible** (seguridad, arquitectura nueva sin
cobertura, rojo persistente; la corrección semántica final es humana, VISION §5.2).

### 3. Routing de modelos como DATO + agentes rigurosos
Operacionaliza un valor ya declarado (VISION §4 / CONTEXT-ECONOMY, nunca cumplido): **Opus = cerebro**
(diseña/decide/revisa-residuo, contexto chico y limpio) · **Sonnet = genera** · **Haiku = lee** el bulk. Los
roles viven en `.claude/agents` con **scope explícito** (`use_when`/`do_not_use_when`), **tools de mínimo
privilegio** y **contrato de salida verificable** — delegación rigurosa, no por vibes. La seguridad la da que
el orquestador **verifica por bloqueo**, no por confiar en la prosa del subagente.

### 4. Gates de calidad SWE deterministas, dogfoodeados en el sustrato
La calidad (tamaño de archivo, ciclos de dependencia, código muerto, acoplamiento/cohesión) se vuelve **gate
determinista** (herramientas reales, no juicio de LLM — I-3), apuntado TAMBIÉN al sustrato: el monolito FALLA
su propio gate → el gate FUERZA el refactor (no rewrite heroico). Se generaliza lo que FSK ya gatea
(a11y/perf/SBOM/supply-chain) a una capa heredable. El `declared-deferred` se vuelve **deuda gateada con
trigger/fecha**, y se agrega **outcome por-incremento** (Δ RTM, Δ expresividad, costo/tokens estilo
billing-ledger) para que "terminado" y "valió la pena" sean DECIDIBLES.

### 5. Inglés de acá en adelante — para CÓDIGO y artefactos técnicos nuevos
El **sustrato vivo nuevo** (código, codegen, la capa de grafo/abstracts, definiciones de agents/skills) se
autora en **inglés** (norma SWE + mejor desempeño del modelo). NO se churnea la **historia inmutable**
(`decisions/` previas, `LOG`) ni se traduce en masa la prosa de gobierno española existente (ADR-009: romper
sha-stamps sería ruido). ADR-017 es la bisagra: español por pertenecer al corpus que cita, decide inglés-hacia-adelante.

## Consecuencias

- **Una piedra angular, no cinco proyectos**: el grafo (Fase 1) subsume navegación + contrato-de-delegación +
  handoff. Se construye **delegando el grueso a Sonnet con el patrón de §2** → prueba el modelo de costos en el acto.
- **Handoff con dientes**: el grafo + un gate de auto-contención vuelven el handoff chico y re-derivable (el
  `STATE.md` de 773 líneas contra su presupuesto de 80 es el anti-patrón a cerrar).
- **El refactor del monolito deja de ser heroico**: lo FUERZA el gate de Fase 1, por slots acotados que Sonnet toma.
- **Roadmap faseado** (autoridad: `work/SOTA-REDESIGN-DIRECTION-INCREMENT.md`): Fase 1 grafo+gate+ledger ·
  Fase 2 arnés de delegación (agents/skills/hooks + PBT + gates seguridad/supply-chain + gate al diferido) ·
  Fase 3 refactor del monolito · Fase 4 re-apuntar al sweet-spot + dial borrador→endurecer · diferido:
  desacople least-privilege "cp-harness" (ADR-016 Fase 2).
- **No es un rebuild de cero**: es construir la capa de dirección/medición sobre un motor que funciona, y dejar
  que esa capa empuje la limpieza.

## Rechazado

- **Empezar por el gran rebuild** (split framework/glue o desacople cp-harness primero). Son refactors de un
  motor que funciona; sin el grafo y los gates que los vuelven medibles y seguros, es rewrite a ciegas. Van en Fase 3+.
- **Tres grafos separados** (código ⟂ RTM ⟂ ADR). Pierde las consultas cross ("¿qué decisión gobierna este
  símbolo?") que son justo el valor; el SOTA recomienda UNO unificado.
- **Mandar una tech concreta del grafo en el sustrato** (p. ej. hardcodear Joern/Kuzu/embeddings). Violaría
  ADR-012: la tech es PLAN, elegida por primitiva, con upgrades diferidos-hasta-medición.
- **Embeddings como navegación primaria.** No responden "quién llama a esto"; sólo búsqueda difusa. Error SOTA #1.
- **"Nunca revisar" / confiar en la prosa del subagente.** Auto-engaño: los gates dejan huecos honestos
  (seguridad, oráculo malo). La regla es verificar-por-bloqueo + ojos de Opus en el residuo irreducible.
- **Traducir en masa la historia española a inglés.** Rompería sha-stamps (ADR-009) por ruido cosmético.
