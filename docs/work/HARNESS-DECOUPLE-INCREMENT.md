<!-- meta:doc sha=cc57027b3bdb3dd2a7ebf8beec4afb1ab7f1a360 updated=2026-06-26T18:05Z -->
# Incremento HARNESS-DECOUPLE

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-26T18:05Z) (creado 2026-06-26T13:23Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> **DESCOPE HONESTO (2026-06-26).** Se cierra en su **núcleo entregado y verde** (Fases 1–2: el gate
> `column_parity`, la fundación de fidelidad-de-proyección que CAZA el drift). Las Fases 3–4 —propagar el
> enforcement de delegación (`blast_radius`/`verdict_required`) + `agent_shadow` con diente A NIVEL FÁBRICA—
> son trabajo genuinamente separable (la fundación detecta drift; la propagación de teeth es otra capacidad)
> y se DIFIEREN a un follow-up nombrado: `FACTORY-DELEGATION-TEETH-INCREMENT.md` (Estado DIFERIDO).
> Esto libera el slot meta para abrir M1 (`MEM-STATE-SNAPSHOT`), respetando un-abierto-por-nivel sin
> fingir verde: el criterio #3 (teeth abajo) NO se cumple y por eso BAJA al follow-up, no se declara hecho.

## Objetivo (ENTREGADO — Fases 1–2)
Desmontar el **cp-harness** en su raíz: la columna de enforcement de la fábrica deja de ser una copia mantenida
a mano (un fork rancio, drift invisible) y pasa a ser una **proyección determinista de un único source**, probada
por un gate `column_parity` (drift = rojo, espejo de `ci --rederive == pin`). **Autoridad de diseño: ADR-018.**
Es §1 de ADR-016 Fase 2.

> **Diferido al follow-up** (`FACTORY-DELEGATION-TEETH`): least-privilege por nivel + enforcement de delegación
> (`blast_radius`/`verdict_required`) propagado a la columna de fábrica → I-12 con diente abajo (`agent_shadow`
> a nivel fábrica). La fundación de proyección (este incremento) es lo que ese follow-up necesita para no driftear.

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
| 3 | **Propagar el enforcement de delegación a la fábrica, least-priv.** `blast_radius`/`verdict_required` en la columna proyectada de fábrica, acotados a sus slots. Wirearlos en `settings.json`. | ⏭️ DIFERIDO → `FACTORY-DELEGATION-TEETH` |
| 4 | **I-12 con diente abajo.** `agent_shadow` a nivel fábrica: una prohibición de un agent de fábrica tiene sombra REAL (instalada + cableada). Negativo no-decorativo: borrar el target → rojo. | ⏭️ DIFERIDO → `FACTORY-DELEGATION-TEETH` |

## Criterio de cierre (demostrable, no narrable) — alcance ENTREGADO (Fases 1–2)
1. ✅ `column_parity` existe, está cableado en `meta check`, y es **bilateral**: VERDE sobre la columna proyectada,
   **ROJO** si se inyecta drift en un hook de fábrica (diente RED plantado en un par sintético → `_tooth_bites`).
2. ✅ `ci --rederive` de cada fábrica == su pin (la re-materialización de `lifecycle.py` no cambió ningún artefacto
   observable; las 5 fábricas re-derivan == pin tras `m00→m01 --factory`).
4. ✅ `meta check` N/N verde (no regresiona el sustrato; 12/12 al cerrar). Single-source intacto (la ley sigue en
   `seed/`; la proyección NO es spec-driven — frontera de seguridad, ADR-018 §4).

> **Criterio 3 — NO cumplido, DIFERIDO (no fingido).** La columna de fábrica cargando `blast_radius`/`verdict_required`
> + `agent_shadow` con diente abajo es la Fase 3–4: se baja al follow-up `FACTORY-DELEGATION-TEETH`. Cerrar sin
> cumplirlo es honesto SÓLO porque el criterio se MUEVE explícitamente, no se declara hecho (verify-not-fake-green).

## Roadmap ADR-016 Fase 2 (este incremento = §1 de 4)
| § | Incremento | Nivel | Estado |
| --- | --- | --- | --- |
| **1** | `HARNESS-DECOUPLE` (este) — núcleo `column_parity` | meta+fábrica | CERRADO (núcleo) |
| 1b | `FACTORY-DELEGATION-TEETH` (Fases 3–4 escindidas: delegación least-priv abajo + `agent_shadow` de fábrica) | meta+fábrica | DIFERIDO |
| 2 | `FACTORY-LIFECYCLE-IN-TREE` (H1 activo + retirar incrementos meta-residentes de fábrica) | fábrica | pendiente |
| 3 | `DOC-SEALING` (`doc_stamp`/`doc_set` a docs de fábrica/producto; check no meta-only) | meta+fábrica+producto | pendiente |
| 4 | `LEVEL-SCOPED-CLOSE` (gate de close acotado al nivel) | meta | pendiente |
