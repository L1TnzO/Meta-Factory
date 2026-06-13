<!-- meta:doc sha=5ae528622436a5d98f2849b5e6cba05a191be507 updated=2026-06-13T20:29Z -->
# Incremento MEMORIA — dejar el subsistema de memoria terminado y SOTA

> **Doc de gobierno.** Este doc ES el estado del incremento de memoria. Creado 2026-06-13T20:05Z
> (sesión 2, hooks vivos). Estado: **CERRADO** (2026-06-13T20:30Z — 7 criterios demostrados, ver
> §Evidencia). Esta vez la disciplina se siguió de verdad: captura continua (el engine escribe
> hechos), commit por fase (MF1–MF6, hooks vivos), `meta checkpoint` para narrar.

## Objetivo
La memoria decide si una fábrica repite errores o deriva (MEMORY-ARCHITECTURE). El bootstrap dejó
Tier 1 (docs) + ADR-009 (índice content-addressed) vivos, pero faltaba: el disparador no-discrecional
de escritura (G-M1), Tier 0 (hechos+métricas), Tier 2 (retrieval medido) y la rehidratación en
SessionStart. Este incremento los construye y los deja **medidos, deterministas y portables**.

## Lecciones de la PRÁCTICA que moldean el diseño (esta sesión, vividas)
1. **Los checkpoints discrecionales se saltean** — documenté al cierre, no incremental (HONEST-STATE §1).
   → La captura de HECHOS debe ser **continua y automática** (el engine escribe al journal en cada gate),
   no solo en checkpoint. El checkpoint cura SIGNIFICADO sobre hechos ya capturados.
2. **Si la generación se corta, el journal de hechos es la red de seguridad** aunque la narrativa esté
   vieja. → Tier 0 primero; el próximo orquestador reconstruye desde hechos, no desde prosa optimista.
3. **Reiniciar pierde TODO el contexto residente** (lo viví al perder la sesión 1). → **SessionStart
   rehydration** no es opcional: inyecta STATE+proyección+últimos hechos al arrancar.
4. **El sello/manifiesto (ADR-009) ya es un aid de frescura** → se integra al retrieval (qué cambió).
5. **Medir antes de invertir** → retrieval lexical+recencia+importancia MEDIDO (SOTA, zero-dep); el
   índice semántico queda diferido-hasta-que-la-medición-lo-justifique (postura SOTA, no un gap).

## Fronteras (no negociables, heredadas)
- **Fuente de verdad = docs tipados + git** (portable: clonar = memoria). El journal/métricas/índice son
  **caché derivado, gitignored, regenerable, NUNCA autoridad**. El índice puede equivocarse sin contaminar la verdad.
- **Re-derivación sobre recuerdo**: la cura de la staleness es re-verificar (`meta check`), no recordar.
  La memoria carga SIGNIFICADO (por qué), no HECHOS recomputables.
- **No forzar el juicio** (ADR-023): lo determinista (proyección, frescura) se hard-checkea; el SIGNIFICADO
  (qué escribir) se surface-ea, no se hard-blockea. Achicar la superficie de juicio, no coaccionarla.
- **Cero modelo en Tier 0** (ADR-008 MUST): todo file-IO + aritmética.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| MF1 | Tier 0 journal de eventos + captura at-source en el engine | ✅ (commit `87ecc4a`) |
| MF2 | Tier 0 métricas gratis + `meta metrics` + tabla de costo | ✅ (Sonnet, 39 tests) |
| MF3 | Fix G-M1: proyección determinista + staleness check + `meta checkpoint` | ✅ (`6df…`/commit MF2-MF3) |
| MF4 | Tier 2 `meta recall` medido (lexical+recencia+importancia) | ✅ (commit `7368bfb`) |
| MF5 | SessionStart rehydration + Stop rollup | ✅ (commit `892ce14`) |
| MF6 | Docs (ADR-007/008 Aprobado/Implementado, lecciones) + tests | ✅ (30 tests, 206 total) |

## Criterio de cierre (demostrable, no narrable)
1. Correr una línea escribe eventos en el journal sin intervención del modelo (captura continua).
2. `meta metrics` emite un veredicto acotado con split de costo por modelo y tasa de delegación, cero modelo.
3. `meta check` falla si la proyección de STATE está vieja respecto de los hechos, y verde tras `meta checkpoint`.
4. `meta recall <query>` devuelve la rebanada relevante (no el corpus) y registra un evento `recall` (medición).
5. El hook SessionStart inyecta contexto al arrancar y loguea qué inyectó.
6. Todo gitignored salvo los docs; borrar `.metamem/` y regenerar no pierde la verdad (re-derivable).
7. Suite de tests del módulo memory verde; `meta check` verde.

## Evidencia de cierre (output real, 2026-06-13T20:12–20:30Z)
1. **✅ captura continua** — `meta product-run` escribió `station_run{s00,passed,gate_open}` al journal
   sin que el modelo hiciera nada (el engine lo hace at-source en cada gate).
2. **✅ `meta metrics`** — veredicto acotado (tasa de delegación, gates, racha); `mem_rollup` parseó un
   transcript → `cost_total` $0.063 (tabla de precios × tokens, cero modelo). Costo verificado (Opus/Sonnet).
3. **✅ proyección no-discrecional** — `meta checkpoint` insertó/refresca el bloque de STATE; `meta check`
   GANÓ el check `projection` (hard) y SURFACE-ea "N hechos sin narrar" en PRÓXIMO (no-block, ADR-023).
4. **✅ `meta recall`** — «trusting trust» devolvió ADR-005 + SELF-IMPROVEMENT §1 + LOG, scoreados; cada
   recall registró `{query, refs}` en el journal (medición). Índice semántico diferido-hasta-medición.
5. **✅ SessionStart** — `meta rehydrate`/`session_start` inyecta incremento+proyección+STATE+hechos+frescura
   y loguea `session_start`. Cierra el problema vivido del reinicio.
6. **✅ portable/regenerable** — `.metamem/` gitignored; borrarlo y regenerar no pierde la verdad (vive en docs+git).
7. **✅ tests + check** — 30 tests del módulo memory (206 en total) verdes; `meta check` PASS (5 checks).
   Disciplina: 6 commits por fase (MF1…MF6), hooks vivos, documentado a medida — NO al cierre (a diferencia del bootstrap).
