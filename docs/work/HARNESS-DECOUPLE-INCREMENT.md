<!-- meta:doc sha=15aa58e663b3586b62378dccb0f89afb5b8f00b3 updated=2026-06-26T13:48Z -->
# Incremento HARNESS-DECOUPLE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-26T13:23Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Desmontar el **cp-harness**: la columna de enforcement de la fábrica deja de ser una copia mantenida a mano
(hoy un fork rancio, 40–63 líneas atrás del meta) y pasa a ser una **proyección determinista de un único source**,
probada por un gate `column_parity` (drift = rojo), **least-privilege por nivel** y con el enforcement de
delegación (`blast_radius`/`verdict_required`) propagado a la fábrica → I-12 con diente abajo. **Autoridad de
diseño: ADR-018.** Es §1 de ADR-016 Fase 2 (las otras tres §, abajo, son incrementos posteriores).

## Diagnóstico (medido, 2026-06-26)
Tres copias paralelas de cada cerrojo: (1) meta-vivo `.claude/hooks/` · (2) template `template/factory/harness/`
· (3) fábrica `factories/<f>/.claude/hooks/`. **(2)↔(3): 2 líneas** (render fiel). **(1)↔(2): 40–63 líneas**
(fork rancio, nada lo detecta). `blast_radius`/`verdict_required`/`gate_guard` **ausentes** en (2) y (3) → I-12
hueco a nivel fábrica. Precedente que se generaliza: 3/4 cerrojos YA delegan al seed (`increment_guard`→`seed/lifecycle.py`,
`stop_proof`/`commit_guard`→`seed/verifier.py`); el hook es transporte fino. El drift vive en transporte + copia-de-seed.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Gate `column_parity` PRIMERO (gate-first).** `src/metafactory/verify/checks/column_parity.py`. Verificado **ROJO** sobre el drift actual antes de arreglar. Hallazgo: el drift NO eran los 40–63 líneas meta↔template (ese es polish de mensajes del transporte meta, legítimo) sino **`seed/lifecycle.py` rancio en las 5 fábricas** (ley de cadencia pre-ADR-016-Fase-1, sin level-aware). | ✅ |
| 2 | **El source canónico + el transform.** Decisión clave (ADR-005 §4): el gate **NO re-implementa** la proyección — re-materializa la columna con el **renderer REAL de M1** (`apply_builds`: copy_seed + render_tree(harness) + render(external_ci por-fábrica)) en un scratch y compara byte a byte → no puede divergir, y maneja `external_ci.yml` (rendered, no verbatim) sin tocar lo de M7. Re-materializadas las 5 (`m00→m01 --factory`) → `column_parity` **VERDE**; blast radius quirúrgico (sólo `lifecycle.py`, ahora level-aware). | ✅ |
| 3 | **Propagar el enforcement de delegación a la fábrica, least-priv.** `blast_radius`/`verdict_required` en la columna proyectada de fábrica, acotados a sus slots. Wirearlos en `settings.json`. | ⏳ |
| 4 | **I-12 con diente abajo.** `agent_shadow` a nivel fábrica: una prohibición de un agent de fábrica tiene sombra REAL (instalada + cableada). Negativo no-decorativo: borrar el target → rojo. | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `column_parity` existe, está cableado en `meta check`, y es **bilateral**: VERDE sobre la columna proyectada,
   **ROJO** si se inyecta drift en un hook de fábrica (sabotaje aislado → sólo ese check rojo).
2. `ci --rederive` de cada fábrica == su pin (la proyección no cambió ningún artefacto observable; byte-neutral o re-pin honesto y narrado).
3. La columna de fábrica carga `blast_radius`/`verdict_required` y `agent_shadow` a nivel fábrica los reconoce como sombra de una prohibición declarada (I-12 con diente abajo, negativo probado).
4. `meta check` N/N verde (no regresiona el sustrato). Single-source intacto (la ley sigue en `seed/`; la proyección NO es spec-driven — frontera de seguridad, ADR-018 §4).

## Roadmap ADR-016 Fase 2 (este incremento = §1 de 4)
| § | Incremento | Nivel | Estado |
| --- | --- | --- | --- |
| **1** | `HARNESS-DECOUPLE` (este) | meta+fábrica | ABIERTO |
| 2 | `FACTORY-LIFECYCLE-IN-TREE` (H1 activo + retirar incrementos meta-residentes de fábrica) | fábrica | pendiente |
| 3 | `DOC-SEALING` (`doc_stamp`/`doc_set` a docs de fábrica/producto; check no meta-only) | meta+fábrica+producto | pendiente |
| 4 | `LEVEL-SCOPED-CLOSE` (gate de close acotado al nivel) | meta | pendiente |
