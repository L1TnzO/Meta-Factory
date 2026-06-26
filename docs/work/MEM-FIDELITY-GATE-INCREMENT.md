<!-- meta:doc sha=0e00844781b4711966d5a317c47cbd3b76605188 updated=2026-06-26T20:09Z -->
# Incremento MEM-FIDELITY-GATE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-26T20:08Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Un gate de FIDELIDAD (`state_fidelity`) que prueba —con diente— que la prosa de «Ahora» no CONTRADICE la
verdad re-derivable del `.proof/`: el sello (ADR-009) dice *si cambió*, pero faltaba decir *si es verdad*.

## Contexto (por qué — ADR-019 §4, M3)
El esquema tiene frescura (sello) pero no FIDELIDAD: nada impide que «Ahora» afirme «fábrica X COMPLETE»
cuando el `.proof/` re-derivado dice lo contrario. Es el hueco que la literatura (Wallat: faithfulness≠
correctness; ClawVM) declara abierto y que NOSOTROS podemos cerrar con DIENTE porque el ground-truth es proof
DETERMINISTA, no prosa ni un juez-LLM. El observador (M5) ya está: este gate fluye a la serie `fidelity` por
nombre (`FIDELITY_CHECKS` ya lista `state_fidelity`), sin tocar `instrument.py`. NO auto-reescribe
(auto-reescribir es lo que causa la deriva; ADR-019 §Rechazado): **falla y señala**.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `projection.rtm_statuses()` — fuente ESTRUCTURADA {slug:(status,sat,total)} re-derivada de `.proof/`; `rtm_status` formatea de ella (salida byte-idéntica) | ✅ |
| 2 | `verify/checks/state_fidelity.py` — detector PURO `fidelity_problems(now_body, statuses)` (afirmación slug↔status que contradice el RTM, slug-más-cercano dentro de ventana) + `_tooth_bites` dos-lados + `main` | ✅ |
| 3 | Cableado a `meta check` (entrada `state_fidelity` tras `state_snapshot`); la serie de fidelidad lo capta solo | ✅ |
| 4 | Diente en la suite: `tests/test_state_fidelity.py` (ambos lados muerden · prosa verdadera pasa · «Ahora» REAL verde) | ✅ |

## El contrato (ADR-019 §4 — two-sided)
Para cada fábrica con status R re-derivado de `.proof/`, en la PROSA de «Ahora» (no el bloque `meta:projection`,
que ya gobierna `projection`):
- **(a)** «Ahora» NO afirma *done* lo que el proof no respalda: un par (slug, `COMPLETE`) cuando R=INCOMPLETE → ROJO.
- **(b)** lo que el proof marca COMPLETE no aparece contradicho: un par (slug, `INCOMPLETE`) cuando R=COMPLETE → ROJO.

El detector empareja cada token de status con la fábrica MÁS CERCANA en la misma línea dentro de una ventana
de caracteres (evita cross-talk entre dos slugs). Vocabulario = las MISMAS palabras que el RTM emite
(COMPLETE/INCOMPLETE y sus flexiones es), acoplando el ground-truth a la salida del proof. Mide FIDELIDAD, no frescura.

## Criterio de cierre (demostrable, no narrable)
1. Inyectar «fábrica X COMPLETE» en «Ahora» cuando el proof dice INCOMPLETE (y viceversa) → `state_fidelity` ROJO AISLADO; quitarlo → VERDE.
2. La prosa VERDADERA (status que coincide con el RTM) NO dispara; el «Ahora» REAL del repo pasa.
3. `state_fidelity` cableado a `meta check` y fluyendo a la serie `fidelity` (M5) sin tocar `instrument.py`.
4. `meta check` verde (suite incluida); cero modelo (oráculo determinista, no juez-LLM).
