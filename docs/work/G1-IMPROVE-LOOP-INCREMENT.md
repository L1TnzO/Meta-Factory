<!-- meta:doc sha=b52cabc1d840a745aa2e22f94077122aaac8797b updated=2026-06-18T02:01Z -->
# Incremento G1-IMPROVE-LOOP

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-18T02:00Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
El loop de mejora **observar→proponer→verificar→promover→rollback** con el **gate de blast-radius**
(`SELF-IMPROVEMENT.md §4`): `meta promote --factory X` re-deriva un candidato y rehúsa la promoción
(no re-pinea, no sube baseline) si **el veredicto de cualquier fábrica downstream baja** — re-generar
para mejorar reemplaza el pin sólo si re-pasa el gate sin bajar ningún veredicto downstream.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | verdict-snapshot (rtm + pinned, re-derivado) + ley de dominación + check `blast_radius` (DATA, sin tech) + baseline; dientes unitarios | ⏳ |
| 2 | `meta promote --factory X` cableado al loop: re-deriva candidato → barrido blast-radius → re-pin+baseline en verde / rehúsa (exit 2) en rojo; façade-trap; dientes por CLI | ⏳ |
| 3 | prueba VIVA por bloqueo: promoción real (verde, RTM sube) + bloqueo de regresión (rojo) co-validado en ≥2 fábricas disjuntas (full-stack TS ⟂ iot Go); pin/baseline committeados | ⏳ |
| 4 | docs (este doc §Evidencia + STATE + ROADMAP G1 ✅), `meta check` 6/6, cerrar incremento | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `blast_radius` bloquea (exit≠0) una promoción que baja el veredicto de CUALQUIER fábrica del barrido, y pasa una honesta — dos lados, no decorativo.
2. `meta promote --factory X` re-pinea X y sube su baseline SÓLO cuando X mejora-o-mantiene y ninguna downstream baja; ante una regresión deja pin y baseline INTACTOS.
3. Co-validado en ≥2 fábricas radicalmente distintas (lenguaje de producto disjunto): la regresión se detecta en cada una por el MISMO mecanismo.
4. Anti-overfit: `git diff src/metafactory/ + seed/` = sólo el mecanismo GENERAL (sin nombrar fábrica ni tech, ADR-012).
5. `meta check` 6/6 · líneas vivas (dummy/full-stack/iot/ASF) intactas · `ci --rederive` por fábrica == pineado.
