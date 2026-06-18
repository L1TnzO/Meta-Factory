<!-- meta:doc sha=86e82c0eddce7fda704d735e44c1be55899e1aa5 updated=2026-06-18T16:33Z -->
# Incremento G2-SCENARIO-CORPUS

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-18T16:33Z) (creado 2026-06-18T16:16Z). Cerralo con `meta increment close`
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
| 1 | El mecanismo (sustrato, dominio-agnóstico): `verify/checks/scenario_corpus.py` (corre el motor sobre cada scenario, ley de dos lados + diente de diversidad, `decide()` PURO) + kind en el registry + corpus DATA (`scenarios/corpus.yml` + fixtures de formas diversas) + dientes unitarios | ✅ `d4def41` |
| 2 | `meta promote` cableado: corre el corpus ANTES de re-pinear; rehúsa (exit 2) si el motor regresa en cualquier forma; corpus verde → sigue al blast-radius. Dientes por CLI | ✅ `6c4fd15` |
| 3 | Prueba VIVA por bloqueo: corpus verde; una regresión REAL del motor (un tooth perdido / una forma válida rota) → corpus rojo → `meta promote` BLOQUEADA con pin+baseline IDÉNTICOS antes/después; anti-overfit (grep sobre el diff de sustrato) | ✅ (este commit) |
| 4 | Docs (este doc §Evidencia + STATE + ROADMAP G2 ✅), `meta check` 6/6, cerrar incremento | ✅ (este commit) |

## Evidencia (re-derivable, no narrada)

**El mecanismo (sustrato, dominio-agnóstico — ADR-012).** El corpus de scenario-specs diversos del
`SELF-IMPROVEMENT.md §4` (patrón meta-harness/autocontext), sin nombrar fábrica ni tech:
- `verify/checks/scenario_corpus.py` — un **scenario = una FORMA de spec + el veredicto M0 que debe
  producir**. `evaluate_scenario` RE-DERIVA la decisión determinista del motor (`validate` ±
  `design_review`) y la compara con lo declarado: una forma `valid` rechazada **o** una `reject`
  aceptada (un tooth perdido) es una cascada (HECHO duro, no juicio §6). Re-derivación in-proc = re-derivar
  desde la fuente (el validador ES la fuente bajo prueba); sin custodia. `diversity()` = el diente que
  cierra **G-8 de raíz**: firmas STRUCTURALES (no las etiquetas, no se puede gamear) — pocas formas
  válidas distintas / pocas familias de tooth / una sola polaridad → ROJO ("pocas formas de spec" es
  la regresión). `decide()` = la decisión PURA (empty/mismatch/thin/ok) compartida por el verbo y los tests.
- `scenarios/` (DATA) — 12 scenarios: **5 formas VÁLIDAS estructuralmente distintas** (minimal/flat ·
  linear-chain · branching fan-out/fan-in+caps · 6-capas+machinery · design-gate B2) + **7 REJECT** que
  cubren las **4 familias del validador** (schema · substrate · rtm · grammar_v2 ×3) **+ el gate de
  diseño** (B2 incompleto). Standalone: `5 formas válidas distintas · 5 familias de tooth`.
- `cli.cmd_promote` — corre el corpus ANTES del barrido downstream (un motor regresado hace insegura toda
  promoción) y sólo en "ok" sigue al blast-radius. Compone con G1: el corpus protege el COMPORTAMIENTO del
  motor; blast-radius protege el VEREDICTO de las fábricas.

**Crit. 1 — dos lados, no decorativo.** Unitario (`test_scenario_corpus.py`, 18 verdes): forma `valid`
rechazada → cascada · forma `reject` aceptada → "tooth perdido" · reject por otra razón → falla · y el
diente NO-decorativo: si `validate` se vuelve no-op (monkeypatch), una `reject` se acepta → mismatch.
VIVO (P3): una regresión REAL del motor (neutralizado el tooth ADR-012 `tech⇒primitive` en `validator.py`)
→ `scenario_corpus .` ROJO ("reject-grammar-tech-no-primitive: forma INVÁLIDA aceptada"); restaurado → verde.

**Crit. 2 — diente de diversidad (cierra G-8 de raíz).** Unitario: pocas formas válidas / pocas familias
/ una polaridad → "thin". VIVO: corpus recortado a 2 válidas + 1 reject → "CORPUS POCO DIVERSO: 2 formas
VÁLIDAS distintas < 3 (G-8: pocas formas de spec)"; restaurado → verde.

**Crit. 3 — `meta promote` exige el corpus verde; ante regresión pin+baseline INTACTOS.** VIVO: con el
motor regresado, `meta promote --factory iot` → **BLOQUEADA (exit 2)** "el motor no pasa el corpus de
scenarios diversos (pin y baseline INTACTOS)" — `sha256` de `baseline_verdicts.json` + `iot/dummy
pinned_verdict.json` **byte-idénticos** antes/después. El gate PRECEDE al barrido: bloqueó en **0.09s** vs
los ~7s del barrido. Con el corpus verde, `meta promote --factory dummy` pasa el gate, barre las 3
fábricas y cae en el façade-trap esperado (hold 5/5).

**Crit. 4 — anti-overfit.** `git diff 94ff0a5..HEAD -- src/metafactory/ seed/` = SÓLO el mecanismo general
(`scenario_corpus.py` + kind en registry + cableado de `cmd_promote`); grep de nombres de fábrica/tech
(`iot|dedup|full-stack|langgraph|neo4j|postgres|docker|tsc|mypy|go test|pytest|claude|…`) sobre el diff `+`
= **0**. El corpus vive 100% como DATA en `scenarios/` (fuera del sustrato).

**Crit. 5 — verde global.** `meta check` 6/6 (compile · docs · projection · isolation · generality · suite
— la suite incluye los 18 tests nuevos). `ci --rederive --factory iot` 5/5 == pineado. Líneas vivas
intactas (el barrido de `promote` re-derivó dummy/full-stack/iot verdes); ASF sin tocar. Árbol limpio.

## Criterio de cierre (demostrable, no narrable)
1. `scenario_corpus` bloquea (exit≠0) si el motor REGRESA: una forma `valid` rechazada **o** una forma `reject` aceptada (un tooth perdido) — dos lados, no decorativo; y pasa un corpus honesto.
2. Diente de diversidad (cierra G-8 de raíz): un corpus con pocas formas distintas / una sola polaridad cae a ROJO — "pocas formas de spec" es la regresión que G-8 nombra.
3. `meta promote --factory X` exige el corpus verde ANTES de re-pinear; ante una regresión del motor deja pin y baseline INTACTOS (medidos byte-idénticos antes/después).
4. Anti-overfit: `git diff src/metafactory/ + seed/` = sólo el mecanismo GENERAL (sin nombrar fábrica ni tech, ADR-012); el corpus vive como DATA en `scenarios/`.
5. `meta check` 6/6 · líneas vivas (dummy/full-stack/iot/ASF) intactas · `ci --rederive` por fábrica == pineado.
