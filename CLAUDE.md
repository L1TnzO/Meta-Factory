<!-- meta:doc sha=87308f0c428d5445af1aa1bd34a1bd77b30e292f updated=2026-07-02T17:49Z -->
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
- **Especializar por ROL, nunca por dominio — con dientes (2026-06-27, ADR-020)**: los agentes de delegación
  se especializan por **modelo · tools · contrato-de-verificación**, NO por dominio. El dominio
  (kotlin/frontend/sql) lo carga el **slot manifest** por invocación (`.gen/active_slot.json`), nunca un
  agente nuevo — proliferar por dominio rompe ADR-012 (tech = plan) y crea ambigüedad de ruteo. El vocabulario
  de roles es **CERRADO** (`agent_roles.CANONICAL` = orchestrator·generator·verifier·reviewer + sinónimos
  legacy `writer`≡generator·`triage`≡verifier de las 5 fábricas, grandfathered ADR-017, no churneados);
  agregar un rol es un acto DELIBERADO (editar el constante + ADR). Lo enforza el gate `roles` de `meta check`
  (un agent nombrado por dominio cae a rojo). El `verifier` (digest de UN artefacto conocido) se distingue del
  built-in `Explore` (búsqueda fan-out) — son complementarios, por eso se mantiene (ADR-020 §D1).
- **Runbook de costos — ruteo por SESIÓN, no se re-decide en cada prompt (2026-07-02, ADR-021)**: el modelo de
  cada sesión/turno es un parámetro de **PRECIO**, no de seguridad — la correctitud la dan los GATES + la
  COLUMNA revisada con ojos propios, NO el IQ del ejecutor. El juicio caro (Opus) se gasta SOLO donde no hay
  gate: contratos, alcance, residuo irreducible, columna. Ruteá por clase de tarea:

  | Clase | Modelo · sesión | Cuándo |
  | --- | --- | --- |
  | **S1 DISEÑO** | Opus, thinking alto, sesión CORTA (matá antes de ~100k ctx) | contratos, alcance, ADRs, la columna (trust-chain) |
  | **S2 EJECUCIÓN** | **Sonnet** (`claude --model sonnet --agent orchestrator`) | ejecutar un INC ya diseñado → commits + veredictos; rojo-persistente/seguridad/ambigüedad → archivo de escalación, NUNCA «pensar más fuerte» |
  | **S3 CIERRE** | Opus, sesión muy corta | leer `meta outcome`/veredictos/escalaciones, revisar residuo, cerrar, handoff |
  | **DÍA-A-DÍA** | shell directo o Sonnet — **NUNCA Opus** | producto-desde-spec-existente (la línea de fábrica es 0-modelo; palanca #1 en $/mes, costo 0) |

  Reglas sin knob, SIEMPRE activas (no requieren nada de la API): (a) **kill-don't-idle** — hueco al FINAL →
  matá la sesión; rehidratar cuesta ~500 tok, nunca la dejes abierta «por las dudas». (b) **keep-warm** —
  hueco DURANTE (gate/slot corriendo) → gate en `run_in_background` + turno de poll cada ≤4 min (0.1×P, 12.5×
  más barato que expirar el cache). (c) **compactación = INCIDENTE, meta 0** — re-write total en frío;
  matar-y-rehidratar la domina siempre. (d) **thinking dial** — alto SOLO en S1; medio/bajo en S2 y turnos
  mecánicos (thinking se cobra como output, $25/M). (e) **higiene de prefijo** — no editar
  CLAUDE.md/agents/settings a mitad de sesión (invalida el cache desde ahí hacia adelante); agrupá los cambios
  de columna en un solo tramo. (f) **draft por defecto** en el loop interno (`product-run --mode draft`, 41.7s
  vs 98s medido), **harden solo al cierre**. (g) **vehículo sweet-spot** para runs medidos: `helpdesk`
  (5 entidades), NO `snipeit` (19 — techo de regresión). La matemática del cache y la respuesta cerrada a
  «TTL 1h vs 5m» → biblia §2.3; la doctrina completa + el plan FIJO N=7 →
  `docs/work/COST-DOWN-DIRECTION-INCREMENT.md` (regla de rebanada: leé SOLO §2 + tu fila §4.INC-n). Estas
  reglas no tienen diente propio; las MIDE INC-1 (`PRICING-LEDGER`) vía `meta outcome`.
