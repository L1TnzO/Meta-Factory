<!-- meta:doc sha=b38ce985df6f8f209c205ca441cf4e0d95614ec3 updated=2026-06-27T20:13Z -->
# Meta-Factory — orientación (fase de diseño)

> PROVISIONAL: orientación de arranque para la fase de diseño/bootstrap. Las reglas operativas
> REALES (presupuesto de residencia, ley de colocación, gates) se GENERAN al construir el harness
> en el bootstrap (meta-estación M7). Este archivo solo enruta; no es la maquinaria.

## Empezá acá
1. Leé `docs/STATE.md` — punto de entrada único y estado actual (si tenés amnesia, empezá ahí).
2. Para construir: `docs/work/BOOTSTRAP-INCREMENT.md` — la línea M0–M3+M8 + el seed congelado.
3. Mapa completo de la documentación: `START-HERE.md`.

## Estado
**BOOTSTRAP EJECUTADO (2026-06-13).** Ya hay código verificado por bloqueo: `seed/` (columna),
`src/metafactory/` (engine·spec·bus·cli), `stations/` (M0–M3+M8), `template/factory/`, y un
dummy-fábrica producido en `factories/dummy/`. Los 8 criterios de cierre pasan (ver
`docs/work/BOOTSTRAP-INCREMENT.md §Evidencia`). Diferido: M4–M7, regeneración de ASF, métricas/memoria-T2.

**RE-DIRECCIÓN SOTA (2026-06-25, ADR-017).** Tras auditoría profunda: el motor FUNCIONA; falta la capa de
DIRECCIÓN. Próximo norte = un **grafo de proyecto content-addressed** (navegación + delegación + handoff +
alcance-de-verificación en UNA pieza) + **delegación "verificar-no-revisar"** (Opus cerebro · Sonnet genera ·
Haiku lee) + gates de calidad dogfoodeados. Roadmap faseado: `docs/work/SOTA-REDESIGN-DIRECTION-INCREMENT.md`.

## Reglas de esta fase
- **NO tocar `../Agent_Systems_Factory/` (ASF)**: es referencia CONGELADA de cosecha y paridad
  (decisions/006). Se regenera como producto recién después del bootstrap.
- **Marcas de tiempo**: `YYYY-MM-DDTHH:MMZ` (UTC, al minuto). Git es la autoridad (`date -u`).
- **Citas de ADR**: Meta-Factory = `ADR-NNN` bare; ASF = `ASF/ADR-NNN` (ambos numeran desde 001 — el
  prefijo evita colisión). Un bare `ADR-009` SIEMPRE es el del Meta-Factory (`decisions/009`).
- **Esquema de docs (mutación por tipo)**: STATE overwrite · LOG append (más nuevo arriba) ·
  decisions/ inmutable · work/ por-incremento · reference/ estable. Actualizar el doc correcto ES
  parte del trabajo, no es opcional (ADR-007: la memoria es fase de gate + checkpoint, no una pregunta).
- **Commit = parte del trabajo, no se pregunta (ADR-010)**: al terminar un cambio —código o docs—,
  commiteá (mensaje con trailers I-10); NUNCA ofrezcas «¿lo commiteo?». Esto OVERRIDE el default genérico
  «commitear sólo cuando el usuario lo pide». El código lo enforza la máquina (`increment_guard`/`gate_guard`);
  los **docs fuera de incremento NO tienen dientes** (residual aceptado, ADR-010 addendum) — ahí la disciplina
  la sostiene esta regla: un parche que REDUCE lo no-commiteado sin agregar ruido, no que lo elimina.
- **El seed (Stage 0) es trust-chain**: se escribe y revisa con ojos propios, no se delega
  (SELF-IMPROVEMENT §3). Lo determinista al CLI, lo impedido a hooks, lo de-cada-turno acá (con
  presupuesto), lo de-rol a agents, lo histórico a docs (CONTEXT-ECONOMY §3, ley de colocación).
- **Multi-archivo por mantenibilidad (2026-06-25)**: el código que escribas de ahora en adelante —sustrato,
  codegen, o artefacto generado— va en archivos cohesivos por responsabilidad, NO en un monolito; no agregues
  archivos NUEVOS de miles de líneas (si uno nuevo tiende a ~800+, partilo en módulos). Los monolitos
  EXISTENTES son deuda conocida (`factories/full-stack-kotlin/codegen/scaffold_product.py`, ~8k líneas) —
  no los reescribas salvo pedido explícito.
- **Inglés de acá en adelante (2026-06-25, ADR-017)**: el código y los artefactos técnicos NUEVOS (codegen,
  capa de grafo/abstracts, definiciones de `.claude/agents` y skills) se autoran en INGLÉS (norma SWE + mejor
  desempeño del modelo). NO churnees la historia inmutable (`decisions/` previas, `LOG`) ni traduzcas en masa
  la prosa de gobierno española existente (rompería sha-stamps, ADR-009). La transición es hacia-adelante.
- **Delegación por defecto — no se pide en cada prompt (2026-06-27, ADR-017)**: cuando enfrentes un **slot de
  código acotado con gate determinista** (typecheck·compile·tests·PBT·static), ruteálo vía el skill
  `generate-slot` al `generator` (Sonnet) y aceptá/rechazá por el **VEREDICTO**, no por el diff. Las **lecturas
  masivas** (logs, árboles generados, specs largas, el monolito) van al `verifier`/`Explore` (Haiku) que
  devuelve un digest. Mantené el contexto de Opus **CHICO**: no generes bulk ni cargues artefactos grandes en
  el hilo principal (el cache-read de Opus DOMINA el costo — aislar el bulk es la palanca #1). El default es
  delegar; el juicio caro (Opus) se gasta en diseñar el contrato, decidir el alcance y revisar el residuo
  irreducible. **Cuándo NO delegar (honesto):** codegen secuencial con dependencias fuertes (el multi-agente
  usa ~15× tokens — sin paralelismo real es más caro), y la **COLUMNA** (hooks, `seed/`, `delegation.py`,
  settings, agents) que es trust-chain → se escribe y revisa con ojos propios (SELF-IMPROVEMENT §3). Para
  builds pesados de fábrica, lanzá la sesión con `claude --agent orchestrator` (toma la disciplina completa
  desde el turno 1); NO pongas un `agent` default global en `settings.json` — reemplazaría el system-prompt
  base de Claude Code en CADA sesión (incluso un fix casual bootearía en modo orquestador).
