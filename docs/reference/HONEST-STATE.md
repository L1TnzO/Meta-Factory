<!-- meta:doc sha=b2e76b942c2b2c00b3e389e67ee32d649d818bd5 updated=2026-06-13T15:33Z -->
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
- **Activos en esta sesión: NINGUNO** (verificado empíricamente con un `.md` de prueba).
- Demostrados por invocación directa (la LÓGICA funciona): `stop_proof` exit 2, `proof_protect` deny,
  `recompute` reject. Pero el harness vivo no los corrió ni una vez.
- **Acción requerida: reiniciar la sesión** para que el harness cargue `settings.json`. Recién ahí
  `doc_stamp` auto-estampa, `commit_guard` bloquea commits sin proof, y `stop_proof` re-verifica al cierre.

## 3. Técnicas de memoria: implementado vs definido
| Técnica (MEMORY-ARCHITECTURE / ADR-007/008/009) | Estado |
| --- | --- |
| Tier 1 narrativa (docs tipados, mutación por tipo) | ✅ existe |
| ADR-009: sello in-band + `INDEX.md` generado + check en `meta check` | ✅ implementado (`docs_manifest.py`), verificado |
| ADR-009: hook que auto-estampa (`doc_stamp`) | ⚠️ escrito, NO activo (§2) — corrí `doc-sync` a mano |
| Disparador NO-discrecional (memoria = fase de gate/checkpoint) | ❌ NO en código — solo existe el CHECK de consistencia (detecta drift); nada FUERZA la escritura narrativa por estación |
| Tier 0: journal de eventos + `metrics.jsonl` + `meta metrics` (ADR-008) | ❌ NO implementado (M5, diferido, Propuesto) |
| Tier 2: índice de recuperación + `meta recall` (ADR-007) | ❌ NO implementado (M5, diferido, Propuesto) |

La memoria en-alcance del bootstrap (índice ADR-009) está construida y funciona, pero su
AUTOMATIZACIÓN (el hook) no se ejerció viva. El resto (Tier 0/2) es M5, diferido por diseño. **El FIX
de G-M1 (forzar la escritura como fase) NO está en código** — es el gap más honesto del bootstrap.

## 4. Implementado vs definido (panorama)
- **En alcance y HECHO:** seed (Stage 0), engine+spec+bus+cli (Stage 1), M0–M3+M8, template, columna
  (hooks escritos), dummy-fábrica, índice ADR-009, 137 tests, 8 criterios por bloqueo.
- **Definido pero DIFERIDO (fuera de alcance, explícito):** M4–M7, regeneración de ASF (ADR-006),
  métricas (ADR-008), memoria Tier 0/2 (ADR-007), loop de auto-mejora.
- **Definido, en-alcance, y FALTÓ en la PRÁCTICA (no es scope, es disciplina):** documentación
  incremental, commits de evidencia por requisito, activación viva de los hooks.

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
