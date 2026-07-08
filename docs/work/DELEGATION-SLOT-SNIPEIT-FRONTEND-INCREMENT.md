<!-- meta:doc sha=ea021154bb8aee9c80e59e5351d35509ad0d9251 updated=2026-07-08T20:19Z -->
# Incremento DELEGATION-SLOT-SNIPEIT-FRONTEND

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-08T20:14Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Vehículo META mínimo para escribir el manifest efímero `.gen/active_slot.json` (Fase 2 de
`factories/full-stack-kotlin/products/snipeit/docs/work/FSK-SNIPEIT-MODELGEN-INCREMENT.md`): el archivo
vive en la raíz del repo (`level_workdir` lo clasifica `meta`, ADR-016), distinto del nivel del código que
el `generator` escribe (`products/snipeit`, ya autorizado por el increment abierto ahí). `.gen/` es
gitignoreado (config re-derivable, no fuente de verdad) — este doc sólo satisface el gate de nivel, no
declara código propio.

## Gotcha operativo (por qué este increment se CIERRA YA, antes que el generator termine)
`cadence.debt()` (el backstop de `stop_proof`) exige árbol NO-`.md` LIMPIO en **TODO EL REPO** mientras haya
CUALQUIER incremento META abierto (`open_increment` sólo mira `docs/work/` raíz — no está scopeado al nivel
que tocás). Dejar este increment META abierto durante la espera larga del `generator` (background, hasta
~90min) hubiera bloqueado CADA cierre de turno con cualquier archivo no-`.md` sucio en el repo — incluida
la superficie ya capturada de helpdesk (`products/helpdesk/frontend/app.{ts,css}`, untracked, de OTRO
alcance). Por eso: el ÚNICO paso que necesitaba autorización de incremento META (escribir `.gen/active_slot.json`,
un `Write` fuera de `factories/`) ya se hizo — este increment se CIERRA ahora. El spawn del `generator` y el
`clear_slot` posterior (una eliminación vía Bash, no gateada por `increment_guard`) NO necesitan un incremento
META abierto — viven bajo el incremento YA ABIERTO a nivel producto (`FSK-SNIPEIT-MODELGEN`, `products/snipeit`,
que sí puede quedar abierto sin este problema porque `debt()` sólo mira el nivel META). **Lección: un incremento
META debe ser de vida CORTA (una escritura, cerrar), nunca "abierto durante una espera larga".**

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Escribir `.gen/active_slot.json` (slot `fsk-frontend-modelgen-snipeit`, contrato = §Contrato-B de `FSK-FRONTEND-MODELGEN-AB-INCREMENT` + deltas de snipe-it) | ✅ |

(Spawn del `generator`, lectura del veredicto y `clear_slot` — Fases 2/3 originales de este doc — se
completan bajo `FSK-SNIPEIT-MODELGEN-INCREMENT.md` §Fase 2, no acá; no requieren un incremento META abierto.)

## Nota de calibración (D23, no bloqueante)
`manifest_problems` marca `max_wall_s=5400 > 1800` (el techo genérico "un slot que no entra en ~30min es
demasiado grande, partilo"). Excepción DELIBERADA y documentada: es UN slot cohesivo (19 entidades, no
fan-out) — el mismo patrón que ganó el A/B de helpdesk (`FSK-FRONTEND-MODELGEN-AB-INCREMENT`); partirlo por
entidad multiplicaría el costo ~15× (CLAUDE.md, "cuándo NO delegar"). `manifest_problems` NO es un gate duro
de spawn (no está cableado en `blast_radius`/`verdict_required`); es asesoría de `meta plan`/dogfood.
`iteration_budget_s=15` SÍ cumple el techo real (tsc+eslint, medido 2.48s en el slot de helpdesk).

## Criterio de cierre (demostrable, no narrable)
1. `.gen/active_slot.json` escrito con manifest válido (`slot_id`, `allow_globs` exactos a los 2 archivos
   del build de snipeit, contrato apuntando a §Contrato-B + deltas de snipe-it).
2. `git diff` de este nivel (meta) == 0 salvo este doc.
3. El veredicto real del slot (green/red) y su `clear_slot` se documentan en
   `FSK-SNIPEIT-MODELGEN-INCREMENT.md §Evidencia` al cerrar ESE incremento (no éste).
