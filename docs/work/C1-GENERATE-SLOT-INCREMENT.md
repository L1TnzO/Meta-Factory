<!-- meta:doc sha=e01e7641a5b7e85f6ab574a3902e5602fa87d2e7 updated=2026-06-15T17:50Z -->
# Incremento C1-GENERATE-SLOT

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-15T17:50Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
La generación deja de ser lógica del sustrato y pasa a ser un **slot creativo orquestado**: una estación
genera un artefacto invocando al **generador declarado en DATO** (`via`), con el blueprint como **brief**;
el sustrato sólo orquesta (escribe el brief, corre el generador) — **no escribe contenido ni veredicto** — y
la **columna VERIFICA** el output. Corromperlo → SHUT. El sustrato no importa NINGUNA tech de generación (ADR-012).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Acción `generate` en `codegen/renderer.py` (brief + `via` + sin-faking) + ADR-013 + guard ADR-012 (sin tech de generación en el sustrato) + tests del renderer | ⏳ |
| 2 | Prueba por bloqueo END-TO-END reproducible (`test_generate.py` sobre el `run_station` real + seed verifier + gate): PASS / corromper-brief→SHUT / sin-generador→SHUT / dominio-agnóstico (2 generadores) | ⏳ |
| 3 | Prueba viva por CLI (factory scratch con línea de producto `generate` → `meta product-run` PASS, corromper → SHUT) + docs (STATE/ROADMAP/LOG + evidencia acá) | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. Una estación con un slot `generate` produce un artefacto vía un generador DECLARADO EN DATO; la columna lo
   verifica y el gate ABRE — sin que el sustrato escriba el artefacto ni el veredicto.
2. **Prueba por bloqueo**: corromper el brief (input de la generación) → el generador emite un artefacto sin el
   invariante → columna SHUT. Un generador que no produce nada → artefacto ausente → columna SHUT (el sustrato
   no finge el artefacto). Ambas reproducibles en la suite.
3. **Dominio-agnóstico** (principio #6): el MISMO seam corre ≥2 generadores radicalmente distintos (p.ej. emitir
   Python y emitir TS) sin ninguna rama por-tech en el sustrato.
4. **Guard ADR-012**: `src/metafactory/` no contiene ningún token de tecnología de generación; el generador es
   `via` (dato), nunca código del sustrato. Test lo prueba.
5. Suite verde, `meta check` verde, árbol limpio, scratch removido.
