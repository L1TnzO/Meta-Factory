<!-- meta:doc sha=20df4200155c64e819789aac735f09d63661243f updated=2026-07-04T20:05Z -->
# Incremento VOCAB-FREEZE

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-04T20:05Z) (creado 2026-07-04T19:56Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Consolidación B con dientes (COUNCIL-360 §6.2/§6.5): **D-3** — el vocabulario de check-kinds queda
CONGELADO con la misma regla que roles (ADR-020): kind nuevo = acto deliberado (editar `registry.KINDS`
+ ADR; vara: «¿no alcanza `product_env` + un script?»), enforzado por el gate nuevo `kinds` en
`meta check` (19 gates); **más** el observer `graph_query` en el journal — el instrumento de la regla
30-días-en-0 para la superficie de navegación del grafo (§2.6).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Slot `kind-hygiene` delegado (contrato + manifest válido): `kind_hygiene.py` espejo de `role_hygiene` + tests dos-lados | ⏳ |
| 2 | Ojos propios: cableado gate `kinds` en `cmd_check` · doctrina de freeze en `registry.py` · fact `graph_query` en `cmd_graph` | ✅ |
| 3 | `meta check` 19/19 verde (con el gate nuevo contando) | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `.gen/kind-hygiene.verdict.json`: green, acceptance (suite completa) exit 0.
2. `meta check` imprime `kinds ok` — 19 gates. Dos lados probados en tests (kind `kotlin_scan` → rojo).
3. `meta graph <verbo>` deja un fact `graph_query` en `.metamem/journal.jsonl` (re-derivable con `tail`).
