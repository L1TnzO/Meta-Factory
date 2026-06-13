<!-- meta:doc sha=394707bf5baa80739be18e219c2bc7364564b4b0 updated=2026-06-13T20:10Z -->
# Incremento MEMORIA — dejar el subsistema de memoria terminado y SOTA

> **Doc de gobierno.** Este doc ES el estado del incremento de memoria. Creado 2026-06-13T20:05Z
> (sesión 2, hooks vivos). Estado: **ABIERTO**. Esta vez la disciplina se sigue de verdad:
> captura continua (el engine escribe hechos), documentar a medida, commit por fase.

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
| MF1 | Tier 0 journal de eventos + captura at-source en el engine | ⬜ |
| MF2 | Tier 0 métricas gratis + `meta metrics` + tabla de costo | ⬜ |
| MF3 | Fix G-M1: proyección determinista + staleness check + `meta checkpoint` | ⬜ |
| MF4 | Tier 2 `meta recall` medido (lexical+recencia+importancia) | ⬜ |
| MF5 | SessionStart rehydration + Stop rollup | ⬜ |
| MF6 | Docs (ADR-007/008 Aprobado/Implementado, lecciones) + tests | ⬜ |

## Criterio de cierre (demostrable, no narrable)
1. Correr una línea escribe eventos en el journal sin intervención del modelo (captura continua).
2. `meta metrics` emite un veredicto acotado con split de costo por modelo y tasa de delegación, cero modelo.
3. `meta check` falla si la proyección de STATE está vieja respecto de los hechos, y verde tras `meta checkpoint`.
4. `meta recall <query>` devuelve la rebanada relevante (no el corpus) y registra un evento `recall` (medición).
5. El hook SessionStart inyecta contexto al arrancar y loguea qué inyectó.
6. Todo gitignored salvo los docs; borrar `.metamem/` y regenerar no pierde la verdad (re-derivable).
7. Suite de tests del módulo memory verde; `meta check` verde.
