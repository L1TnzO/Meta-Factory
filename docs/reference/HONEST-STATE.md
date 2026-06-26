<!-- meta:doc sha=d792a5bb53200bca16c4587edcc1b1fb039fe341 updated=2026-06-26T20:33Z -->
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
  COMPLETAS y probadas por bloqueo (`tests/test_precompact.py` + demo e2e). La ACTIVACIÓN en producción son
  2 líneas en `.claude/` (registrar `PreCompact` en `settings.json` + pasar `source` en `session_start.py`):
  requieren aprobación explícita del ingeniero (el clasificador auto-modo bloquea auto-editar el arranque
  del agente, guardrail correcto). Como los hooks se cargan al INICIO de sesión, recién quedan VIVOS tras
  reiniciar (mismo patrón que §2). Hasta entonces: lógica lista, gatillo pendiente de 1 aprobación + reinicio.
