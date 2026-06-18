<!-- meta:doc sha=450f2df1fc7d594e0b19d8bcb8eb6bfef5a47723 updated=2026-06-18T16:16Z -->
# Incremento G2-SCENARIO-CORPUS

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-18T16:16Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Un **corpus de scenario-specs diversos** (formas de spec variadas, patrón meta-harness: input + veredicto
esperado) que **ejercita el motor** antes de promover, y un gate `scenario_corpus` cableado a `meta promote`:
una promoción se rehúsa si el motor REGRESA en cualquier forma del corpus. Cierra **G-8 de raíz** ("probada en
pocas formas de spec; formas nuevas casi seguro destapan cascada", `ASF-LESSONS §G-8`) y compone con el
blast-radius de G1: blast-radius protege el VEREDICTO de las fábricas downstream; scenario_corpus protege el
COMPORTAMIENTO del motor a través de formas diversas. *Gate*: promover exige verde en N scenarios diversos.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | El mecanismo (sustrato, dominio-agnóstico): `verify/checks/scenario_corpus.py` (corre el motor sobre cada scenario, ley de dos lados + diente de diversidad, `decide()` PURO) + kind en el registry + corpus DATA (`scenarios/corpus.yml` + fixtures de formas diversas) + dientes unitarios | ⏳ |
| 2 | `meta promote` cableado: corre el corpus ANTES de re-pinear; rehúsa (exit 2) si el motor regresa en cualquier forma; corpus verde → sigue al blast-radius. Dientes por CLI | ⏳ |
| 3 | Prueba VIVA por bloqueo: corpus verde; una regresión REAL del motor (un tooth perdido / una forma válida rota) → corpus rojo → `meta promote` BLOQUEADA con pin+baseline IDÉNTICOS antes/después; anti-overfit (grep sobre el diff de sustrato) | ⏳ |
| 4 | Docs (este doc §Evidencia + STATE + ROADMAP G2 ✅), `meta check` 6/6, cerrar incremento | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `scenario_corpus` bloquea (exit≠0) si el motor REGRESA: una forma `valid` rechazada **o** una forma `reject` aceptada (un tooth perdido) — dos lados, no decorativo; y pasa un corpus honesto.
2. Diente de diversidad (cierra G-8 de raíz): un corpus con pocas formas distintas / una sola polaridad cae a ROJO — "pocas formas de spec" es la regresión que G-8 nombra.
3. `meta promote --factory X` exige el corpus verde ANTES de re-pinear; ante una regresión del motor deja pin y baseline INTACTOS (medidos byte-idénticos antes/después).
4. Anti-overfit: `git diff src/metafactory/ + seed/` = sólo el mecanismo GENERAL (sin nombrar fábrica ni tech, ADR-012); el corpus vive como DATA en `scenarios/`.
5. `meta check` 6/6 · líneas vivas (dummy/full-stack/iot/ASF) intactas · `ci --rederive` por fábrica == pineado.
