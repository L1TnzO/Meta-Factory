<!-- meta:doc sha=9b96aab90407fc002e9b2103043e119ef7796cd5 updated=2026-07-10T15:29Z -->
# HONEST-STATE — implementado vs definido (sin maquillaje)

> tipo: reference (I-13, honestidad de límites). Artefacto de primera clase: la aspiración NUNCA se
> confunde con la realidad. Si este doc y STATE.md discrepan, gana el artefacto verificable.
> Escrito 2026-06-13T15:30Z tras una pregunta directa del ingeniero sobre disciplina de proceso.

## 0. La pregunta honesta que originó este doc
¿Documenté a medida o solo al final? ¿Los hooks de memoria están vivos? ¿Hay commits de evidencia por
requisito? Respuesta sin maquillaje: **documenté AL FINAL, los hooks NO estuvieron activos, y hubo
CERO commits durante la construcción.** Es G-M1/G-3 en vivo —el mismo trap de ASF— y es la prueba
empírica de por qué el diseño exige sombra determinista.

## 1. La disciplina que el factory predica vs la que seguí
| Premisa del diseño | ¿La seguí construyendo? | Evidencia |
| --- | --- | --- |
| Documentar es FASE del flujo (DOCUMENT del gate), no tarea final | ❌ NO — batch al cierre (F5) | STATE/LOG/BOOTSTRAP se tocaron recién en el cierre |
| Captura incremental por hook (doc_stamp PostToolUse) | ❌ NO disparó | empírico: un `.md` escrito quedó SIN sello hasta correr `doc-sync` a mano |
| Commit por requisito/estación con trailers (I-10) | ❌ NO — 0 commits en toda la construcción | `git rev-list --count HEAD` = 0 |
| RTM re-derivado de artefactos | ✅ SÍ | de `.proof/`, no de narrativa |
| Probar por BLOQUEO, no por prosa | ✅ SÍ | los 8 criterios con exit codes reales |

**Por qué pasó (causa, no excusa):** escribí los hooks de la columna y de memoria DENTRO de la sesión
(a mitad). Claude Code carga los hooks al INICIO de sesión → **nunca estuvieron vivos para mi propio
trabajo**. Sin la sombra determinista activa, el orquestador (yo) volvió a la escritura discrecional —
exactamente lo que el diseño predice. Es la validación más fuerte de la tesis: la maquinaria existe,
pero inactiva no me salvó. El factory tenía razón sobre sí mismo.

**Riesgo concreto que esto creó:** si la generación se cortaba tras F2, el próximo orquestador habría
encontrado código real con STATE.md diciendo "DISEÑO, cero código" y un LOG vacío — documentación
MENTIROSA, peor que ausente. No ocurrió solo porque llegué al cierre.

## 2. Hooks / harness: estado de ACTIVACIÓN
- Escritos y cableados en `.claude/settings.json`: proof_protect · gate_guard · stop_proof ·
  commit_guard · doc_stamp.
- **Sesión 1 (construcción): NINGUNO activo** — se cargan al inicio de sesión y `settings.json` se
  escribió a mitad. Por eso documenté discrecional (§1). Esa es la causa raíz, no una excusa.
- **Sesión 2 (tras reiniciar, 2026-06-13T19:54Z): LOS 5 VERIFICADOS EN VIVO por el harness real:**
  - `doc_stamp` (PostToolUse) auto-selló un `.md` nuevo y regeneró `INDEX.md` (lo reportó el propio harness).
  - `proof_protect` + `permissions.deny` denegaron un `Write` a `.proof/` y un `open()`/`rm` por shell.
  - `gate_guard` bloqueó `meta station m02` salteando m01 — ANTES de ejecutar el comando.
  - `commit_guard` denegó `git commit` con la estación activa roja.
  - `stop_proof` bloqueó el cierre del turno (exit 2) con la estación roja y re-invocó al modelo.
- **Finding (a afinar, no urgente):** `proof_protect` es sobre-celoso — bloquea cualquier comando que
  mencione `.proof/` y contenga un `>` (incluso `2>/dev/null` de solo-lectura). Es safe-side (jamás deja
  ESCRIBIR un veredicto; solo molesta lecturas con redirección); achicar el regex es trabajo futuro.

## 3. Técnicas de memoria: implementado vs definido
> ACTUALIZADO 2026-06-13 sesión 2 (incremento MEMORIA): el subsistema se CONSTRUYÓ. ADR-007/008 → Aprobado+Implementado.

| Técnica (MEMORY-ARCHITECTURE / ADR-007/008/009) | Estado |
| --- | --- |
| Tier 1 narrativa (docs tipados, mutación por tipo) | ✅ existe |
| ADR-009: sello in-band + `INDEX.md` generado + check en `meta check` | ✅ implementado + **activo en vivo** (`doc_stamp` verificado, §2) |
| Tier 0 hechos: journal at-source (engine) + `meta journal` | ✅ `memory/journal.py` — captura CONTINUA, no checkpoint discrecional |
| Tier 0 series: `metrics.jsonl` + `meta metrics` + costo (ADR-008) | ✅ `memory/metrics.py` + hooks `mem_capture`/`mem_rollup`, cero modelo |
| Disparador NO-discrecional (el FIX de G-M1) | ✅ `memory/projection.py` + `meta checkpoint`; `meta check` verifica la proyección (hard) y SURFACE-ea los hechos sin narrar (ADR-023) |
| Tier 2 retrieval MEDIDO: `meta recall` | ✅ `memory/recall.py` (lexical+recencia+importancia); cada recall se MIDE |
| Rehidratación SessionStart | ✅ `memory/rehydrate.py` + hook (activa al reinicio) |
| Índice semántico (embeddings) | ⏳ **diferido-hasta-medición** (postura SOTA, NO un gap): se decide cuando la serie `recall` muestre que el lexical no alcanza |

El gap más honesto del bootstrap (el FIX de G-M1) está **CERRADO en código**: los hechos se capturan
solos (engine at-source), la proyección es determinista y verificada por `meta check`, y los hechos sin
narrar se SURFACE-ean (no se fuerza el juicio, ADR-023). Lo único pendiente es A PROPÓSITO: el índice
semántico, hasta que la medición lo justifique. 30 tests del módulo memory (206 en total).

## 4. Implementado vs definido (panorama)
- **En alcance y HECHO:** seed (Stage 0), engine+spec+bus+cli (Stage 1), M0–M3+M8, template, columna
  (hooks escritos Y verificados en vivo), dummy-fábrica, índice ADR-009, **subsistema de MEMORIA completo
  (Tier 0/1/2 + disparador no-discrecional + rehidratación; ADR-007/008 Implementados)**, 206 tests, 8 criterios.
- **Definido pero DIFERIDO (fuera de alcance, explícito):** M4–M7, regeneración de ASF (ADR-006),
  loop de auto-mejora, índice semántico de memoria (diferido-hasta-medición, §3).
- **Disciplina de proceso:** en el BOOTSTRAP falló (doc al cierre, 0 commits, hooks inactivos — §1).
  En el incremento de MEMORIA se siguió de verdad: commit por fase, hooks vivos, captura continua,
  `meta checkpoint` para narrar. La maquinaria, ahora viva, hizo cumplir lo que antes era discrecional.

## 5. Evidencia por requisito (commits): el estado honesto
La premisa I-10 es "cada requisito ↔ uno o varios commits con trailers (station/spec-refs/proof-sha)".
Durante la construcción: **0 commits** → la premisa NO se cumplió en vivo. Al cierre se hizo una serie
de commits estructurada por área/criterio con trailers `Satisfies:`/`Proof:` (ver `git log`).
**Honesto: es reconstrucción al cierre, NO captura viva por paso.** El RTM sí se re-deriva de `.proof/`
(artefactos), que es la mitad fuerte de I-10; la mitad de commits llegó tarde, como en ASF.

## 6. Para el próximo orquestador
Reiniciá la sesión ANTES de seguir, para que los hooks estén vivos. Commiteá por estación/requisito
(`commit_guard` lo va a exigir). Documentá en el gate, no al final. Si suena a sermón: es literal lo
que yo no hice — por eso lo escribo acá, no en prosa optimista.

## 7. Residuales declarados (memoria v2)
- **Freeze del codegen SIN diente + alcance sin legislar — CERRADO (2026-07-10, `CODEGEN-FREEZE-TOOTH`).**
  El gate `codegen_freeze` (`meta check`, 20 gates) es la sombra determinista de ADR-023 §3: diff en
  `factories/*/codegen/**` sin waiver en el work-doc ABIERTO del nivel dueño → ROJO · waiver sin diff
  (decorativo) → ROJO · auditoría histórica auto-referencial (epoch = commit 4bd9835 que agrega el check;
  escape deliberado `WAIVED_COMMITS` estilo `registry.KINDS`). La frontera de la zona gris quedó LEGISLADA
  en el docstring del check + el work-doc: `alcance=verificacion` (proofs/tests/cobertura emitidos — parte
  VIVA por ADR-023 §1; cita ADR-023 basta) vs `alcance=superficie` (templates/superficie humana — exige ADR
  dedicado). Las 2 perforaciones previas (5b96696·43f295d) quedan grandfathered pre-epoch. **Residuo
  irreducible que queda:** la honestidad del `alcance` declarado la juzgan ojos en revisión — el check
  verifica la FORMA (alcance+motivo+cita), no la semántica.
- **Swap Fable 5 — REVERTIDO el mismo día (2026-07-10, pedido del ingeniero).** Opus vuelve a ser la norma
  en TODO el ruteo (runbook S1/S3 + agents meta `orchestrator`/`reviewer` → `model: opus`); Fable 5 queda
  RESERVADO a sesiones especiales de infraestructura meta que el ingeniero lanza explícitamente. Los agents
  de fábrica nunca cambiaron (`model: opus`, emitidos por `delegation_brain.py`) — el residual del swap en
  el emisor MUERE: ya no hay drift que cerrar.
- **Frescura comunitaria SIN herramienta (2026-07-10, auditoría model-first).** La pregunta OBLIGADA de
  ADR-023 §2 («¿qué pieza ya validó la comunidad?») tiene procedimiento (skill `design-primitives` paso 3)
  y diente indirecto (M0 `design-review`: capability sin `tech` → rojo), pero la RESPUESTA sale del
  training-data del modelo: no hay `.mcp.json`, ni context7, ni paso de web-lookup en S1 — riesgo de fijar
  como DATO versiones viejas/deprecadas. Propuesta: increment `COMMUNITY-FRESHNESS` — MCP context7 (o
  WebSearch) habilitado SÓLO para sesiones S1 de diseño (NUNCA dentro de slots del generator — least-priv;
  `forbidden_tools` ya modela la denegación) + la versión exacta queda PINEADA en la spec, así la frescura
  es input de diseño y el determinismo lo sostiene el pin. Es superficie de supply-chain del cerebro
  (output de MCP entra al contexto que decide) → exige ADR propio, no un `claude mcp add` casual.
  Trigger: próxima spec nueva (F1/ASF) o el primer pin comunitario que resulte deprecado al verificarlo.
- **La pregunta comunitaria no baja al nivel PRODUCTO (2026-07-10, auditoría model-first).**
  `design-primitives` es meta-only y su alcance declarado es el diseño de FÁBRICAS (`factory.spec.yml`);
  `product.yml` no tiene campo estructurado para piezas de comunidad, y la superficie model-nativa ya
  adoptada (snipeit `app.ts` = TS vanilla data-driven, sin framework) no re-preguntó — sus deltas quedaron
  congelados por ley de increment, decisión legítima pero NO pasó por el paso 3. Mitigado: toda sesión corre
  desde la raíz meta (workspace-model, ARCHITECTURE-MAP §2), así que el skill ESTÁ disponible; lo que falta
  es que el procedimiento de spec-de-producto lo OBLIGUE. Trigger: la adopción model-nativa de `helpdesk`
  (la próxima superficie que se diseñe debe dejar la respuesta comunitaria ESCRITA).
- **M4 (MEM-PRECOMPACT-SNAPSHOT) — proyección a fábrica DIFERIDA (2026-06-26).** El roadmap clasificó M4
  como `meta(+col)` y pidió proyectarlo al template/fábrica (ADR-018). Tras leer la columna real, M4
  aterrizó **sólo a nivel meta**: PreCompact NO es enforcement (la columna de fábrica son los 4 cerrojos,
  frontera de seguridad), la capa de memoria (`session_start`/`mem_capture`/`mem_rollup` + el observador
  M5 en `src/metafactory/memory/` + `.metamem`) es **meta-only hoy**, y la RE-INYECCIÓN vive en
  `SessionStart` —que tampoco existe en la columna de fábrica— así que proyectar la mitad-escritura sin la
  mitad-lectura sería un **writeback muerto**. Trigger para des-diferir: cuando la fábrica adquiera un
  subsistema de memoria (session_start/rehydrate proyectados) — adyacente a M6. Detalle:
  `work/MEM-PRECOMPACT-SNAPSHOT-INCREMENT.md §Decisión de alcance`.
- **M4 — ACTIVACIÓN del hook (sello de honestidad).** La LÓGICA (`memory/precompact.py`), el script
  (`.claude/hooks/pre_compact.py`), la re-inyección (`rehydrate`, backward-compatible) y la serie M5 están
  COMPLETAS y probadas por bloqueo (`tests/test_precompact.py` + demo e2e). La ACTIVACIÓN —2 líneas en
  `.claude/` (registrar `PreCompact` en `settings.json` + pasar `source` en `session_start.py`)— se aplicó
  CON aprobación explícita del ingeniero (el clasificador auto-modo la había bloqueado como auto-modificación
  del arranque, guardrail correcto; la aprobación lo levantó). **Cableada y commiteada.** Como los hooks se
  cargan al INICIO de sesión, recién queda VIVA en producción **tras reiniciar la sesión** (mismo patrón que
  §2: la maquinaria existe pero inactiva hasta el próximo arranque). Hasta el reinicio: cableado completo,
  fuego pendiente sólo del próximo `SessionStart`.
