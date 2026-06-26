<!-- meta:doc sha=7f0fb531b110527d6f93c4b024f8ca9ae184c0b4 updated=2026-06-26T18:05Z -->
# Incremento FACTORY-DELEGATION-TEETH (escindido de HARNESS-DECOUPLE Fases 3–4)

> **Doc de gobierno.** Estado: **DIFERIDO** (escindido 2026-06-26 al cerrar `HARNESS-DECOUPLE` en su núcleo).
> Para ejecutar: poné el banner en abierto a mano (editá el campo de estado de este header — un `.md` siempre
> es editable; NO uses `meta increment open`, que rehúsa pisar un doc que ya existe) y confirmá con
> `meta increment status`. (El header dice DIFERIDO a propósito: la ley del lifecycle sólo cuenta como abierto el
> marcador canónico, así que este doc no ocupa el slot meta mientras espera.) **Autoridad: ADR-018** (§ delegación
> least-priv abajo). Es la mitad-de-teeth de ADR-016 Fase 2 §1; la mitad-de-fundación (`column_parity`) ya la
> entregó `HARNESS-DECOUPLE`.

## Por qué se escindió (no es deuda escondida)
`HARNESS-DECOUPLE` tenía dos capacidades distintas bajo un slug: **(a)** la columna de fábrica es una proyección
fiel de un único source (drift = rojo) — *fundación*; **(b)** la columna de fábrica además **lleva el enforcement
de delegación** (`blast_radius`/`verdict_required`) y `agent_shadow` lo reconoce con diente a nivel fábrica —
*propagación de teeth*. (a) está entregada y verde (`column_parity`, ADR-018 §1). (b) es trabajo genuinamente
separable y NO se cumplió → se baja acá en vez de declararse hecho. La fundación es exactamente lo que (b) necesita
para no driftear cuando se proyecte.

## Objetivo
Cerrar el hueco de **I-12 a nivel fábrica**: hoy `blast_radius`/`verdict_required`/`gate_guard` viven SÓLO en el
meta-vivo (frontmatter del `generator`, Fase 2 DELEGATION-HARNESS); la columna PROYECTADA a la fábrica no los
carga, así que una prohibición de un agent de fábrica no tiene sombra real. Propagarlos por la MISMA proyección
determinista que `column_parity` ya verifica (no copia a mano), acotados least-privilege a los slots de cada nivel.

## Fases (heredadas de HARNESS-DECOUPLE 3–4)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Propagar el enforcement de delegación a la fábrica, least-priv.** `blast_radius`/`verdict_required` en la columna proyectada de fábrica, acotados a sus slots; wirearlos en el `settings.json` proyectado. Debe pasar `column_parity` (la proyección, no copia). | ⏳ |
| 2 | **I-12 con diente abajo.** `agent_shadow` a nivel fábrica: una prohibición de un agent de fábrica tiene sombra REAL (instalada + cableada). Negativo no-decorativo: borrar el target → rojo, aislado. | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. La columna proyectada de cada fábrica carga `blast_radius`/`verdict_required` acotados a sus slots, y
   `column_parity` sigue VERDE (se propagó por proyección, no a mano → no introdujo drift).
2. `agent_shadow` a nivel fábrica reconoce la sombra de una prohibición declarada de un agent de fábrica;
   negativo probado: borrar el target → rojo, sabotaje aislado (sólo ese check).
3. `ci --rederive` de cada fábrica == su pin (re-pin honesto y narrado si la columna proyectada cambió bytes).
4. `meta check` N/N verde; single-source intacto (la ley en `seed/`, la columna NO spec-driven, ADR-018 §4).

## Punteros
- `HARNESS-DECOUPLE-INCREMENT.md` — el núcleo entregado (`column_parity`) + la nota de descope.
- ADR-018 — la columna como proyección de un único source (least-priv por nivel).
- `DELEGATION-HARNESS-INCREMENT.md` (Fase 2 SOTA) — el origen de `blast_radius`/`verdict_required` arriba.
