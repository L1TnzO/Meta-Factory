<!-- meta:doc sha=1b77c710eb02d5b8351a208a1e570ae57d2dd75d updated=2026-06-14T15:27Z -->
# Incremento M4-M7 — completar el sustrato (template · memoria · CI externo · harness)

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-14T02:15Z — sesión opus-4.8). Cerralo con
> `meta increment close` (gateado: árbol limpio + estación activa verde). Cierra STATE §Siguiente #2.
> Dogfood: commit por fase; la cadencia (ADR-010) se prueba sobre su propia obra.

## Objetivo
Cerrar el agujero de sustrato que el bootstrap acotó a propósito: que la línea de una fábrica corra
**M0–M8 COMPLETO** (hoy sólo M0–M3+M8). El dummy debe nacer con **frontera generado/dominio** que
sobrevive un re-scaffold (M4), **memoria+RTM** que re-derivan de artefactos (M5), **doctrina de dos
verificadores** como CI externo real (M6) y **harness completo** con sombras agent→hook (M7). Es el
prerequisito real de regenerar ASF (STATE §Siguiente #1): no hay e2e de ASF sin este sustrato.

## Principio
M4–M7 son **estaciones-como-dato** (I-2): cada una se agrega como un `mNN.yml` + las piezas de template
que renderiza + los `kind`s de check que su gate necesita. No se ramifica el engine; se agrega dato y, si
hace falta, un check nuevo en el registry. El seed (trust-chain) NO se delega; el sustrato sí puede.

## Fases
| Fase | Meta-estación | Contenido | Estado |
| --- | --- | --- | --- |
| P1 | **M4** Template & frontera | `m04.yml` + template `generated/` vs `domain/` (`_skip_if_exists`) + answers/migración; check `boundary_survives` | 🟡 frontera+test hechos, gateados y e2e en el dummy (criterio 1 ✅, `7139e9a`); `answers/migración` pendiente |
| P2 | **M5** Memoria & RTM | `m05.yml` + hornear journal+docs(esquema ADR-021)+métricas(ADR-008) en el template; check `rtm_rederive` | 🟡 gate `rtm_rederive` hecho+gateado+e2e (criterio 2: RTM re-deriva de `.proof/`, corromper un proof lo cambia, ledger consistente; `e3c0e1e`) + MEMORY.md horneado; captura VIVA journal/métricas + proyección RTM en STATE de fábrica → M7/seguimiento |
| P3 | **M6** Dos verificadores | `m06.yml` + workflow de re-derivación (seed ya trae `external_ci.yml`) + veredicto pineado + pre-push; check `clean_runner` | 🟡 gate `clean_runner` hecho+gateado+e2e (criterio 3: runner limpio re-deriva en clon hermético y exige el pineado, desvío→rojo; `989b533`,`d59d64b`) + línea M0–M8 completa verde (criterio 5). DIFERIDO: `pre-push` (mirror local) → M7/harness |
| P4 | **M7** Harness | `m07.yml` + hooks=sombras de columna + agents=contratos + commands + CLAUDE.md ≤ presupuesto; check `agent_shadow` | ⏳ |
| P5 | Integración + cierre | dummy corre M0–M8 completo e2e; RTM COMPLETE re-derivado; STATE/LOG; suite verde; `meta increment close` | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. **(M4, I-5)** Un archivo bajo `domain/` editado a mano **sobrevive** un re-render de la línea (`_skip_if_exists`);
   `generated/` SÍ se regenera. Test negativo: sin la frontera, el re-render lo pisaría → rojo.
2. **(M5)** `meta rtm --factory dummy` re-deriva de `.proof/` el estado por requisito (SATISFIED/PROVISIONAL/
   UNSATISFIED) y el journal deriva de git+ledger, no de prosa; corromper un proof CAMBIA el RTM.
3. **(M6)** Un runner **limpio** (clon fresco) reconstruye el dummy y exige el veredicto pineado: igual → verde;
   desvío en cualquier dirección (proof distinto O pin distinto) → rojo.
4. **(M7, I-12)** Cada prohibición declarada en un agent tiene **sombra** verificable en hook/CLI (un agent sin
   sombra → check rojo); el presupuesto de residencia (CLAUDE.md ≤ N líneas) es medible en el diff.
5. La línea del dummy corre **M0–M8 completo** verde; RTM `COMPLETE` re-derivado de artefactos; el capstone M8
   sigue bloqueando producto roto (test negativo intacto).
6. Suite verde (tests nuevos de M4–M7 incluidos); `meta check` PASS con todas las estaciones; dogfood: commit
   por fase (P1–P5), cerrado por `meta increment close`.
