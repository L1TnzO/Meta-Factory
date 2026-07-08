<!-- meta:doc sha=0954857894aea03967745b67e568f6d3d6714dfe updated=2026-07-08T21:05Z -->
# Incremento DELEGATION-SLOT-SNIPEIT-VERDICT

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-08T21:05Z) (creado 2026-07-08T21:01Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Vehículo META de vida corta (mismo patrón que `DELEGATION-SLOT-SNIPEIT-FRONTEND`) para persistir
`.gen/fsk-frontend-modelgen-snipeit.verdict.json` — el `generator` no pudo escribirlo él mismo:
`increment_guard` bloquea cualquier `Write`/`Edit` a rutas meta (`.gen/` cuelga de la raíz) sin un
incremento META abierto, y esa ruta no tiene la excepción que sí tiene `blast_radius` (que permite
escribir la verdict_path incondicionalmente). El generator respetó la ley "no rutear por otro
mecanismo tras un bloqueo" (2 veces, correcto) y reportó el veredicto como texto en su lugar. El
orquestador re-derivó TODO de manera independiente (dos verificadores) antes de persistirlo —
no se copió la prosa del generator sin verificar.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Re-derivar independientemente la gate rápida (tsc+eslint) y la pesada (`modelgen_ab_gate.sh snipeit`, 6 ejes) sobre `products/snipeit/build/product/frontend/src/app.{ts,css}` | ✅ |
| 2 | Ojos reales sobre screenshots — encontró un bug REAL que ningún gate atrapó (pantallas apiladas, `#screen` sin limpiar entre `mountX`); devuelto al generator como fallo estructurado, fix cycle 1/2 | ✅ |
| 3 | Re-derivar independientemente el fix (fast+heavy gate + navegación Playwright propia confirmando `.screen` count==1) | ✅ |
| 4 | Persistir `.gen/fsk-frontend-modelgen-snipeit.verdict.json` (status green) + `clear_slot` (manifest ephemeral removido, veredicto queda como evidencia) | ✅ |

## Gotcha operativo (harness gap real, anotado — NO se arregla acá)
`increment_guard` no conoce la excepción que `seed/delegation.py: write_allowed` sí le da al
`verdict_path` (siempre permitido para el `generator`, sea cual sea el blast radius). Como
`increment_guard` es GLOBAL (corre para CUALQUIER sesión, incluida la del `generator`) y es
puramente path-based (`level_workdir`), un veredicto en `.gen/*.verdict.json` (ruta meta) queda
bloqueado si no hay un incremento META abierto — aunque `blast_radius` sí lo autorizaría. Esto forzó
DOS incrementos META de vida corta en este trabajo (manifest + veredicto) en vez de uno. Es un gap de
la COLUMNA (haría falta enseñarle a `increment_guard`/`edit_allowed` la misma excepción de
`verdict_path` que ya tiene `write_allowed`) — se anota como candidato a un increment META futuro
(tocar hooks = trust-chain, ojos propios, fuera de alcance de ESTE increment de producto).

## Criterio de cierre (demostrable, no narrable)
1. `.gen/fsk-frontend-modelgen-snipeit.verdict.json` existe con `status: green`, `acceptance_exit_code: 0`,
   re-derivado por el orquestador (no copiado sin verificar).
2. `.gen/active_slot.json` NO existe (`clear_slot` corrido) — los dientes de blast-radius vuelven a inertes.
3. `git diff` de este nivel (meta) == 0 salvo este doc.
