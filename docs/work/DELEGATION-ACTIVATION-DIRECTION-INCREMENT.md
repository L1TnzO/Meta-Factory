<!-- meta:doc sha=b00f222d95f13e2a1ed07d45dc930a015b3956f4 updated=2026-06-27T16:58Z -->
# Incremento DELEGATION-ACTIVATION (dirección)

> **Doc de gobierno · DIRECTION.** Estado: **CERRADO** (2026-06-27 — entregable = la especificación de A–D +
> registro en ROADMAP/STATE; ver §7). Semántica work/ por-incremento. Este doc lanza una familia de
> sub-incrementos (Fases A–D); **cada FASE se abre con `meta increment open` al ejecutarla** y se cierra con
> `meta increment close` (gateado). Autocontenido a propósito: asumí que el contexto de la sesión que lo
> escribió murió — otro orquestador implementa DESDE ACÁ. Si algo no está en esta doc, no existe (mandato del
> ingeniero, 2026-06-27).

---

## 0. TL;DR — qué es esto y por qué ahora

La **Fase 2 SOTA (`DELEGATION-HARNESS`, 2026-06-26) CONSTRUYÓ** el arnés verificar-no-revisar: agentes
`orchestrator/generator/verifier/reviewer`, skill `generate-slot`, hooks `blast_radius`/`verdict_required`,
gates `pbt`/`security`/`deferred`. **Pero nunca se ENCENDIÓ.** La medición lo prueba:

- **Tasa de delegación: 0.0%** — el harness está construido y **dormido**.
- **~$13.500 estimados en ~132 sesiones, ~100% Opus.** Cada `claude` arranca como el agente genérico (Opus)
  que hace TODO él mismo: lee bulk, genera bulk, revisa. El cerebro caro hace el trabajo barato.
- **El cache-read de Opus DOMINA el costo** (~$7.320 de re-leer su contexto cada turno, vs ~$3.280 de output).
  El driver de costo es el TAMAÑO del contexto de Opus, no solo qué modelo genera.

Este incremento es la **IGNICIÓN**: hacer que la delegación sea **natural — sin pedirla en cada prompt** — y
propagarla a las fábricas, para dejar el meta Y las fábricas en mejor estado y **más baratos**. No construye
maquinaria nueva: enciende, mide y propaga la que ya existe.

**Baseline a batir (medido 2026-06-27, `meta metrics` + rollup de transcripts):**
| Métrica | Hoy | Objetivo |
| --- | --- | --- |
| `delegation_rate` (journal) | 0.0% (evento nunca emitido) | medible y creciente para trabajo de codegen |
| Split de tokens (output) | Opus ~100% / Sonnet ~0% | bulk-gen → Sonnet/Haiku (target industria: 80–90% a modelos baratos) |
| Contexto de Opus (cache-read) | ~$7.320 (domina) | bajar vía aislamiento (bulk-read fuera de la ventana de Opus) |
| Topología de agentes | 4 meta dormidos + 3 fábrica sin cerebro | rol-split despierto, descriptions afiladas, fábricas con orquestador |

---

## 1. Contexto — el diagnóstico completo (de dónde sale cada número)

### 1.1 Cómo se midió
- `meta metrics` (`src/metafactory/memory/metrics.py::aggregate`) → `DELEGACION tasa 0.0%`. La fórmula es
  `delegations / station_runs` sobre el **journal** (`memory/journal.py`). Conteo de kinds del journal:
  `station_run: 5032 · session_start: 217 · recall: 1` — **NO existe ningún evento `kind="delegation"`**.
- Tool-freq (de `mem_capture.py`, PostToolUse `*` → `.metamem/metrics.jsonl`): `Bash 46.4% · Read 26.1% ·
  Edit 18.6% · Write 3.3% · … · Agent 0.4% (52 llamadas en TODA la historia)`.
- Costo/split por modelo: rollup de los 132 transcripts de `~/.claude/projects/<proj>/*.jsonl`
  (`metrics.py::rollup_from_transcript` + `cost`, tabla `PRICES`): **Opus 4.8 output 43.7M tok ≈ $13.560 (~100%)**;
  Sonnet output 111k ≈ $5,57 (0.0%). Desglose Opus: **cache-read 4.88B tok ≈ $7.320** · output ≈ $3.280 ·
  cache-creation 28.8M ≈ $540. → **el cache-read es ~2.2× el costo del output**.

### 1.2 El hallazgo: harness construido, interruptor sin encender
Inspección del setup real:
- **META `.claude/agents/`**: `orchestrator` (opus) · `generator` (sonnet, hooks blast_radius+verdict) ·
  `verifier` (haiku, read-only) · `reviewer` (opus). Bien diseñados (rol-split correcto). **Dormidos.**
- **META `.claude/settings.json`**: `agent: <NONE>` → ninguna sesión arranca en modo orquestador. **No hay hook
  `SubagentStop`** → nada emite el evento `delegation` que la métrica intenta leer (el `journal.py` lo DOCUMENTA
  en su cabecera: `delegation {subagent_type, model, description} ← captura de subagentes`, pero nadie lo escribe).
- **META `CLAUDE.md`**: no tiene regla permanente que le diga al agente principal CUÁNDO delegar.
- **FÁBRICAS `factories/*/.claude/agents/`**: topología DISTINTA y más pobre — `triage` (haiku, lee) ·
  `writer` (sonnet, escribe) · `reviewer` (opus). **No hay orquestador (cerebro)**, **no hay skill
  `generate-slot`** (las skills de fábrica son `correr-app`/`verificar-fabrica`), y el `agent` default
  también es `<NONE>`. La `FACTORY_COLUMN` SÍ incluye los dientes de delegación (`blast_radius`+
  `verdict_required`, `column_scope.py`) — la fábrica PUEDE delegar con dientes, pero no tiene el cerebro
  ni el procedimiento. **Construir un producto pasa 100% por Opus igual.**

### 1.3 Por qué importa (la causa raíz, no el síntoma)
El error #1 documentado por la industria, textual: *"over-relying on the orchestrator for execution — if it
writes code directly instead of delegating, the pattern fails"* (MindStudio). Es exactamente el estado actual.
La pieza que falta NO es topología (la tenemos) — es **ACTIVACIÓN**: que el agente principal SIEMPRE sepa
delegar sin que se lo pidan, que la métrica MIDA, y que las fábricas hereden el cerebro.

---

## 2. Cómo funciona la delegación en Claude Code (la base — con fuente)

Tres mecanismos, de menos a más "natural" (sin pedirlo cada vez). Fuente primaria:
[docs oficiales de subagents](https://code.claude.com/docs/en/sub-agents).

### 2.1 Mecanismo A — auto-delegación por `description` (router implícito)
> *"Claude uses each subagent's description to decide when to delegate tasks… To encourage proactive
> delegation, include phrases like 'use proactively' in your subagent's description field."* — docs oficiales.

El `description` **es el trigger, no la etiqueta**. Las fórmulas confirmadas que disparan auto-delegación:
`Use PROACTIVELY when…`, `MUST BE USED for…` (ejemplos `code-reviewer`/`debugger` de los docs). **Límite:**
dispara cuando el pedido del USUARIO matchea una descripción; para nuestro loop el trigger es "el principal
reconoce un slot acotado con gate" → ese reconocimiento necesita una **instrucción permanente** (Mecanismo C).

### 2.2 Mecanismo B — invocación explícita (3 niveles de fuerza)
Lenguaje natural (nombrás el agente, Claude decide) · `@agent-<name>` (garantiza ese agente) · `--agent <name>`
o setting `agent` (sesión entera). Fuente: docs §"Invoke subagents explicitly".

### 2.3 Mecanismo C — agente de sesión por defecto (la clave de "natural")
Dos formas de que NO haya que decirlo en cada prompt:

| Forma | Qué hace | Costo / riesgo |
| --- | --- | --- |
| `"agent": "orchestrator"` en `settings.json` | TODA sesión arranca con system-prompt+modelo+tools del orquestador | ⚠️ **Reemplaza el system-prompt base de Claude Code ENTERO** (docs: *"the subagent's system prompt replaces the default Claude Code system prompt entirely, the same way --system-prompt does"*). Cada sesión casual (revisar métricas, un fix rápido) bootearía en modo delegación. |
| **Regla permanente en `CLAUDE.md`** | CLAUDE.md carga en CADA sesión (incl. subagentes, docs §"What loads at startup") sin reemplazar nada | ✅ Bajo riesgo, granular. Es nuestra capa de gobierno de fase-viva ([[three-memory-single-source]]: CLAUDE.md owns live-phase rules). |

**Decisión (ver §5.1): NO usar `agent` default global. Usar la regla CLAUDE.md + descriptions afiladas +
`--agent orchestrator` manual para builds pesados.**

### 2.4 Reality-check económico — el patrón de Anthropic NO es el nuestro
[Anthropic — multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
(lead + 3-5 subagentes en paralelo, +90.2% sobre single-agent) es **research paralelo**, no nuestro caso.
Su advertencia honesta, textual: *"multi-agent systems use about 15× more tokens than chats… Most coding tasks
involve fewer truly parallelizable tasks than research. Multi-agent underperforms in domains that require all
agents to share the same context."*

Nuestro modelo NO es el research-swarm. Es **cost-routing + aislamiento de contexto SECUENCIAL**:
1. **Aislamiento** (la palanca #1 dado que el cache-read domina): el `verifier`/`Explore` (Haiku) leen el bulk
   (logs, árboles, specs) y devuelven un digest chico → el bulk NUNCA entra en la ventana de Opus → Opus
   re-lee menos cada turno → baja el cache-read.
2. **Generación barata**: el `generator` (Sonnet) escribe el bulk dentro de un blast-radius con gate → el código
   no entra en el contexto de Opus (Opus lee el VEREDICTO, no el diff).

→ **No apliques "spawneá 3-5 en paralelo" a codegen secuencial: ahí el 15× te juega en contra.** La ganancia es
aislamiento + tier-barato, no paralelismo.

---

## 3. La dirección (resumen autocontenido — sobrevive sin la memoria)

Encender y propagar lo construido, en cuatro fases. **Ninguna fase construye un agente nuevo por dominio** — la
mejor práctica es especializar por **ROL** (modelo·tools·contrato de verificación), no por dominio; el dominio
lo carga el **slot manifest** por invocación (`.gen/active_slot.json`, ya existe). Proliferar agentes por dominio
es la trampa (rompe ADR-012 "tech = plan, nunca hardcodeada" + crea ambigüedad de ruteo). Fuente del eje de
especialización: [docs](https://code.claude.com/docs/en/sub-agents) ("Design focused subagents… each excels at
one specific task") + [best practices](https://rosmur.github.io/claudecode-best-practices/) +
[PubNub](https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/) ("use specialized subagents
**sparingly**; default to the clone/general pattern").

| Fase | Slug del sub-incremento | Qué deja TERMINADO | Nivel (ADR-016) |
| --- | --- | --- | --- |
| **A** | `DELEG-ACT-META` | El agente principal del meta delega NATURALMENTE (regla CLAUDE.md + descriptions afiladas + alias manual) | meta |
| **B** | `DELEG-MEASURE` | La métrica deja de mentir 0%: hook `SubagentStop` → evento `delegation` + split de tokens por modelo en `meta metrics` | meta |
| **C** | `DELEG-ACT-FACTORY` | Las fábricas heredan el cerebro: el emisor de harness emite `orchestrator` + `generate-slot` + regla CLAUDE.md + delegation-capture de fábrica | meta (codegen) → re-proyecta a las 5 |
| **D** | `DELEG-TOPOLOGY-HYGIENE` | Trim de redundancia (`verifier` vs `Explore`) + convergencia de nombres de rol meta↔fábrica + la regla "no proliferar por dominio" escrita con dientes | meta + fábrica |

Orden recomendado: **B antes que A** (medir primero, para que A sea verificable) → A → C → D. Razón: sin la
medición de B, no podés probar que A funcionó (el principio del proyecto: re-verificar > recordar; "done" es
decidible, no narrado).

---

## 4. Las fases en detalle — QUÉ · CÓMO · POR QUÉ · DE DÓNDE

> Cada fase es un sub-incremento independiente con su propio `meta increment open/close`, su gate, y su
> §Evidencia. Lo de abajo es la especificación completa para que cada uno se ejecute sin re-investigar.

### FASE B — `DELEG-MEASURE` (medición con dientes) — HACER PRIMERO

**B1. Emitir el evento `delegation` al journal.**
- **QUÉ:** un hook `SubagentStop` a nivel proyecto (en `settings.json`) que, cuando un subagente termina, anexa
  al journal `kind="delegation"` con `{subagent_type, model}`.
- **CÓMO:**
  1. Crear `.claude/hooks/delegation_capture.py` — transporte de una línea (idéntico patrón a `mem_capture.py`):
     lee el JSON de stdin del hook (que trae `agent_type`, docs: *"`name` … Hooks receive this value as
     `agent_type`"*), resuelve `root` por `$CLAUDE_PROJECT_DIR`, y llama
     `journal.append(root, "delegation", subagent_type=<agent_type>, model=<…>)`. Best-effort (nunca levanta).
  2. Cablear en `settings.json` → `hooks.SubagentStop` (matcher vacío = todos los agentes). Fuente del evento:
     docs §"Project-level hooks for subagent events" (`SubagentStop`, matcher = agent type name, "When a
     subagent completes").
- **POR QUÉ:** `aggregate()` calcula `delegation_rate = delegations/station_runs` sobre eventos que **nadie
  escribe** → 0% por construcción. La `append`/`read` del journal ya soporta el kind; solo falta el emisor.
- **DE DÓNDE:** inspección de `journal.py` (cabecera documenta el evento), `metrics.py::aggregate`, conteo de
  kinds (sin `delegation`), `settings.json` (sin `SubagentStop`); docs oficiales (hook `SubagentStop`).
- **⚠️ Trust-chain:** este hook es **observabilidad, sin dientes** (captura, no enforcement). Aun así es COLUMNA
  → se escribe con ojos propios, no se delega (CLAUDE.md / SELF-IMPROVEMENT §3). Es meta-only por ahora (la
  memoria/observabilidad es meta-only, `column_scope.META_ONLY`); para la fábrica ver Fase C.
- **Gate / cierre:** spawnear un subagente real (p.ej. un `verifier` trivial) y demostrar que `meta metrics`
  ahora reporta `delegation_rate > 0`. Diente: con 0 spawns la tasa es 0; con N spawns sube. `meta check` sin
  regresión.

**B2. Exponer el split de tokens por modelo en `meta metrics`.**
- **QUÉ:** agregar al render de `meta metrics` el split Opus/Sonnet/Haiku (output + costo) de la sesión/serie.
- **CÓMO:** `metrics.py` ya tiene `rollup_from_transcript(path)` + `cost(rollup)` + tabla `PRICES` — están sin
  cablear al verbo `meta metrics`. Pasar el transcript de la sesión (de `~/.claude/projects/<proj>/<session>.jsonl`)
  a `render(root, transcript=...)` (la firma YA lo acepta) y/o leer `~/.claude/stats-cache.json`
  (`modelUsage`/`dailyModelTokens`, VERIFICADO presente — ver `OBSERVABILITY-METRICS.md §1`).
- **POR QUÉ:** el `delegation_rate` cuenta SPAWNS, no tokens. El KPI real de costo es el **split de tokens** y el
  **tamaño del contexto de Opus** (cache-read domina). Sin esto, "más barato" no es verificable.
- **DE DÓNDE:** `OBSERVABILITY-METRICS.md §1/§3/§5` (stats-cache `tokensByModel` VERIFICADO; tabla precios×tokens);
  `metrics.py` (helpers ya existen); mis números del rollup (cache-read $7.320 vs output $3.280).
- **Gate / cierre:** `meta metrics` muestra el split; sanity contra `stats-cache.json`. Observador, no gate.

---

### FASE A — `DELEG-ACT-META` (activación natural del meta)

**A1. Regla permanente de delegación en `CLAUDE.md` (meta).** ⟵ el corazón de "natural sin pedirlo".
- **QUÉ:** un bullet en `CLAUDE.md §"Reglas de esta fase"` que instruya al agente principal genérico a rutear
  por defecto.
- **CÓMO:** texto concreto a agregar (español — es prosa de gobierno de fase-viva, NO artefacto técnico inglés):
  > **Delegación por defecto (no se pide en cada prompt, 2026-06-27, ADR-017):** cuando enfrentes un **slot de
  > código acotado con gate determinista** (typecheck·compile·tests·PBT·static), ruteálo vía el skill
  > `generate-slot` al `generator` (Sonnet) y aceptá/rechazá por el VEREDICTO, no por el diff. Las **lecturas
  > masivas** (logs, árboles generados, specs largas) van al `verifier`/`Explore` (Haiku). Mantené el contexto de
  > Opus CHICO: no generes bulk ni leas artefactos grandes en el hilo principal. Excepción (trust-chain): la
  > COLUMNA (hooks, `seed/`, `delegation.py`, settings) se escribe con ojos propios, no se delega.
- **POR QUÉ:** CLAUDE.md carga en cada sesión sin reemplazar el system-prompt → delegación natural, granular, sin
  forzar cada sesión a modo orquestador. Es la capa correcta ([[three-memory-single-source]]).
- **DE DÓNDE:** docs (auto-delegación + "agent default reemplaza el system-prompt" → por qué CLAUDE.md y no agent
  global); MindStudio (system-prompt orquestador: *"Do not write code yourself unless no sub-agent is available"*);
  inspección (CLAUDE.md sin regla, settings `agent: NONE`).

**A2. Afilar las 4 `description` de los agentes meta.**
- **QUÉ:** reescribir el `description` de `orchestrator/generator/verifier/reviewer` con triggers proactivos
  explícitos (`Use PROACTIVELY when…` / `MUST BE USED when…`) sin perder el contrato actual.
- **CÓMO:** editar el frontmatter de los 4 `.md` (inglés — ADR-017: definiciones de `.claude/agents` se autoran en
  inglés). Ejemplos de transformación:
  - `verifier`: hoy *"Cheap read-only bulk reader…"* → *"… **Use PROACTIVELY whenever you would read a large
    artifact** (log, generated tree, long spec, the monolith) instead of loading it into the main context."*
  - `generator`: añadir *"**MUST BE USED for any bounded code slot that has a deterministic gate** — do not write
    such code in the main thread."*
  - `reviewer`: mantener el "exception, not routine" (no afilar a proactivo — su disparo ES la excepción).
- **POR QUÉ:** el `description` es el trigger del router implícito; triggers proactivos aumentan la auto-delegación.
- **DE DÓNDE:** docs ("include phrases like 'use proactively'") + ejemplos `code-reviewer`/`debugger`.
- **⚠️ Operacional:** *"Subagents are loaded at session start. If you add or edit a subagent file directly on
  disk, restart your session to load it."* (docs). Tras editar, **reiniciar la sesión** para que registren. Ya
  observado en [[sota-redesign-graph-spine]] ("new on-disk agent needs session-restart to register").

**A3. Alias manual `--agent orchestrator` para builds pesados (NO default global).**
- **QUÉ:** documentar (en CLAUDE.md o START-HERE) que las sesiones de construcción pesada de fábrica se lanzan con
  `claude --agent orchestrator` para tomar la disciplina completa desde el turno 1.
- **POR QUÉ / DE DÓNDE:** ver §5.1 (la decisión). El default global reemplazaría el system-prompt en cada sesión.
- **Gate / cierre de Fase A:** tras A1+A2 (+restart), en una sesión nueva el principal rutea un slot real al
  `generator` SIN que se lo pidan, y B lo MIDE (`delegation_rate > 0`, split corre hacia Sonnet). `meta check`
  sin regresión.

---

### FASE C — `DELEG-ACT-FACTORY` (propagar el cerebro a las fábricas)

**C1. El emisor de harness emite el orquestador + el procedimiento de fábrica.**
- **QUÉ:** hoy el codegen emite `triage/writer/reviewer` por fábrica pero NO un `orchestrator`, NO el skill
  `generate-slot`, NO la regla CLAUDE.md de delegación, NO el delegation-capture. Añadir esos 4 al emisor.
- **CÓMO:**
  1. **INVESTIGAR (primer paso del sub-incremento):** localizar EXACTAMENTE el emisor de los `.claude/agents` de
     fábrica. Señal: `git log` de `factories/*/.claude/agents/writer.md` apunta a `M7/M8 — harness emitido` y a
     `FACTORY-DELEGATION-TEETH`; los 5 writer.md tienen md5 distintos (factory-específicos, no copia estática);
     `template/factory/` NO tiene `agents/`. → el emisor es codegen en la línea M7/M8 (harness). Confirmar el módulo.
  2. Extender el emisor para producir, por fábrica: un `orchestrator.md` (rol cerebro, `Agent(writer, triage,
     reviewer)`), el skill `generate-slot` variante-fábrica, el bullet CLAUDE.md de delegación, y el hook
     `delegation_capture` (la `FACTORY_COLUMN` deberá incluirlo si la observabilidad baja a fábrica — ver ⚠️).
  3. **Re-emitir + re-pin**: `meta station` de la línea afectada, luego `ci --rederive --all-products == pin`.
- **POR QUÉ:** la fábrica TIENE dientes de delegación (`blast_radius`+`verdict_required` en `FACTORY_COLUMN`,
  `column_scope.py`) pero ningún cerebro que orqueste ni procedimiento que invoque → la delegación de fábrica está
  tan dormida como la del meta. El objetivo del ingeniero es "dejar las fábricas más baratas": construir un
  producto debe poder rutear bulk a Sonnet, no pasar 100% por Opus.
- **DE DÓNDE:** inspección (`factories/*/.claude/agents` = triage/writer/reviewer sin orchestrator; skills =
  correr-app/verificar-fabrica sin generate-slot; `FACTORY_COLUMN ⊇ _DELEGATION`; git log del emisor).
- **⚠️ Decisiones dentro de C1:**
  - **Idioma:** los agentes de fábrica actuales están en ESPAÑOL (`writer.md` description). ADR-017 → el emisor
    debe autorar los NUEVOS en inglés (transición hacia-adelante; NO traducir en masa lo existente ni churnear
    sha-stamps, ADR-009).
  - **¿La observabilidad baja a fábrica?** Hoy `column_scope` deja `mem_capture`/`session_start`/etc. como
    `META_ONLY` ("write-half sin read-half = dead writeback"). Si querés medir `delegation_rate` DENTRO de una
    fábrica regenerada standalone, hay que decidir si `delegation_capture` entra en `FACTORY_COLUMN` (y entonces
    el `least_priv` gate debe re-calibrarse). Por defecto: NO bajarlo aún — medir la delegación de fábrica desde
    el meta operador (`meta station --factory`). Capturar esta decisión en el ADR si se cambia.

**C2. Convergencia de topología meta ↔ fábrica.**
- **QUÉ:** alinear los nombres/contratos de rol: `triage`(haiku-lee)≈`verifier`, `writer`(sonnet-escribe)≈
  `generator`, `reviewer`≈`reviewer`. La fábrica gana el `orchestrator` que le falta.
- **POR QUÉ:** una sola disciplina mental (mismo rol = mismo nombre = mismo contrato) reduce carga cognitiva y
  ambigüedad de ruteo. No es renombrar por renombrar: es que el operador no tenga dos vocabularios.
- **Gate / cierre de Fase C:** una fábrica regenerada expone el orquestador + `generate-slot`; `ci --rederive
  --all-products == pin`; un producto de prueba (p.ej. `helpdesk`) se construye con `delegation_rate > 0` medible.
  `meta check` (incl. `column_parity`, `least_priv`) 16/16.

---

### FASE D — `DELEG-TOPOLOGY-HYGIENE` (trim, no proliferar)

**D1. Evaluar colapsar `verifier` (meta) contra el built-in `Explore`.**
- **QUÉ:** decidir si el `verifier` custom (Haiku, read-only) se mantiene o se reemplaza por el built-in `Explore`
  (Haiku, read-only, ya registrado).
- **CÓMO:** comparar qué restricción agrega `verifier` que `Explore` no dé. Si no agrega ninguna → deprecarlo y
  apuntar el orquestador/skills a `Explore`. Si agrega (p.ej. un contrato de digest estructurado) → documentarlo
  como la razón de existir.
- **POR QUÉ:** best practice = apoyarse en built-ins, custom solo donde agrega restricción real; menos agentes =
  menos ambigüedad de ruteo + menos mantenimiento (anti-patrón en AMBAS direcciones).
- **DE DÓNDE:** docs (Explore = built-in Haiku read-only) + [PubNub](https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/)
  / [rosmur](https://rosmur.github.io/claudecode-best-practices/) (especializar con moderación).

**D2. La regla "especializar por ROL, nunca por dominio" — escrita con dientes.**
- **QUÉ:** dejar en CLAUDE.md (o el ADR de §5) la invariante: los agentes se especializan por modelo·tools·
  contrato de verificación; el dominio (kotlin/frontend/sql) lo carga el slot manifest, nunca un agente nuevo.
- **POR QUÉ:** previene la trampa que el ingeniero intuyó (proliferar agentes); alinea con ADR-012.
- **Gate / cierre de Fase D:** la decisión sobre `verifier` está tomada y registrada; la regla anti-dominio está
  en gobierno; `meta check` sin regresión.

---

## 5. Decisiones de diseño (los forks — con recomendación y razón)

### 5.1 Activación: regla CLAUDE.md (✅ recomendado) vs `agent` default global
**Recomendación: regla CLAUDE.md + descriptions afiladas + `--agent orchestrator` manual.** NO `agent` global.
- **Por qué no el global:** docs — *"the subagent's system prompt replaces the default Claude Code system prompt
  entirely."* El `orchestrator.md` es un prompt ESTRECHO (loop verificar-no-revisar), no un driver general de
  sesión. Cada sesión casual (como esta, revisar métricas) bootearía en modo delegación → sobre-ingeniería y
  fricción. El default global es la opción agresiva; la regla CLAUDE.md es natural y reversible.

### 5.2 ¿Hace falta un ADR nuevo?
**Recomendación: SÍ, un ADR corto** (¿`ADR-020 — Activación de la delegación: routing por defecto`?) que fije:
(a) el routing por defecto vía CLAUDE.md, no agent-global; (b) la métrica `delegation` + split de tokens como el
KPI de costo; (c) la regla rol-no-dominio; (d) la decisión de si la observabilidad de delegación baja a la
`FACTORY_COLUMN`. Razón: estas son decisiones de arquitectura con consecuencias en `column_scope` y en el costo —
merecen ser inmutables y citables (como ADR-017/018). Las fases B–D lo referencian.

### 5.3 Orden: medir antes de activar
**B → A → C → D.** Sin la medición de B, A no es verificable (re-verificar > recordar; "done" decidible). B es
barato (un hook + cablear helpers existentes) y desbloquea la prueba de todo lo demás.

---

## 6. Reality-check económico (qué ahorra de verdad, y qué NO)

- **Palanca #1 = aislamiento de contexto** (porque el cache-read de Opus domina, ~$7.320). Sacar el bulk-read de
  la ventana de Opus (vía `verifier`/`Explore`) baja lo que Opus re-lee cada turno. Esto importa **tanto o más**
  que mover la generación a Sonnet.
- **Palanca #2 = generación barata** (Sonnet escribe el bulk con gate). Target industria:
  [MindStudio](https://www.mindstudio.ai/blog/smart-orchestrator-cheaper-sub-agent-models-claude-code) — routing
  bien hecho mueve **80–90% del uso de tokens** a modelos baratos → **5–10× menos costo**.
- **Cuándo NO delegar (honesto):** codegen secuencial con dependencias fuertes, o cambios trust-chain (la columna).
  El multi-agente usa ~15× tokens; sin valor que lo justifique, es más caro. No spawnear swarms para trabajo
  secuencial. El slot manifest ya tiene `cost_class` (cheap/standard/premium) y `model_policy` — USARLOS para
  rutear por tier, no mandar todo a un tier fijo.

---

## 7. Criterio de cierre del DIRECTION (este doc)

Este doc-dirección se considera ENTREGADO cuando:
1. Las Fases A–D quedan especificadas (QUÉ·CÓMO·POR QUÉ·DE-DÓNDE) y nombradas como sub-incrementos. ✅ (este doc)
2. Queda registrado en `ROADMAP.md` + un puntero conciso en `STATE «Ahora»` (dentro del presupuesto ≤45 líneas).
3. `meta check` sin regresión (doc-only) y commit con trailers I-10 (ADR-010).

Cada FASE se cierra por separado con su `meta increment close` (gateado: árbol limpio + estación verde) y su
§Evidencia demostrable (no narrable). El éxito GLOBAL se mide contra el baseline de §0.

---

## 8. Punteros (respaldo — el detalle y las fuentes)

- **Fuentes Claude Code (primarias):**
  [docs oficiales de subagents](https://code.claude.com/docs/en/sub-agents) (mecanismo de delegación,
  frontmatter, `SubagentStop`, agent default reemplaza system-prompt, Explore built-in) ·
  [Anthropic — multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
  (orquestador-worker, 15× tokens, "teach the orchestrator to delegate", "scale effort to complexity") ·
  [MindStudio — smart orchestrator → cheaper subagents](https://www.mindstudio.ai/blog/smart-orchestrator-cheaper-sub-agent-models-claude-code)
  (system-prompt de orquestador, 5–10×, error #1 "writes code directly") ·
  [best practices (rosmur)](https://rosmur.github.io/claudecode-best-practices/) ·
  [PubNub — subagent best practices](https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/)
  (granularidad, anti-patrón en ambas direcciones).
- **Repo (lo que ya existe):** `.claude/agents/{orchestrator,generator,verifier,reviewer}.md` ·
  `.claude/skills/generate-slot/SKILL.md` · `.claude/hooks/{blast_radius,verdict_required,mem_capture}.py` ·
  `src/metafactory/memory/{journal,metrics}.py` · `src/metafactory/column_scope.py` (FACTORY_COLUMN ⊇ _DELEGATION) ·
  `factories/*/.claude/agents/{triage,writer,reviewer}.md` · `docs/reference/OBSERVABILITY-METRICS.md`.
- **Gobierno:** `ADR-017` (grafo-columna + verificar-no-revisar + routing como dato) · `ADR-018` (columna como
  proyección least-privilege) · `ADR-016` (layering por nivel) · `ADR-012` (tech = plan) · `ADR-010` (commit =
  parte del trabajo) · `docs/work/SOTA-REDESIGN-DIRECTION-INCREMENT.md` (la Fase 2 que CONSTRUYÓ el harness) ·
  `docs/work/ROADMAP.md`.
- **Memoria de sesión Claude Code:** [[sota-redesign-graph-spine]] (Fase 2 build + lección "restart para registrar
  agente nuevo") · [[target-operating-model-sota]] (modelo operativo objetivo) ·
  [[three-memory-single-source]] (CLAUDE.md = reglas de fase-viva).
</content>
</invoke>
