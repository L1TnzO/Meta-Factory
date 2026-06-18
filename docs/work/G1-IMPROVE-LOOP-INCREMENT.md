<!-- meta:doc sha=e6e52dd5cf439e018baf620f2262174665d1ecfe updated=2026-06-18T02:42Z -->
# Incremento G1-IMPROVE-LOOP

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-18T02:42Z) (creado 2026-06-18T02:00Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
El loop de mejora **observar→proponer→verificar→promover→rollback** con el **gate de blast-radius**
(`SELF-IMPROVEMENT.md §4`): `meta promote --factory X` re-deriva un candidato y rehúsa la promoción
(no re-pinea, no sube baseline) si **el veredicto de cualquier fábrica downstream baja** — re-generar
para mejorar reemplaza el pin sólo si re-pasa el gate sin bajar ningún veredicto downstream.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | verdict-snapshot (rtm + pinned, re-derivado) + ley de dominación + check `blast_radius` (DATA, sin tech) + baseline; dientes unitarios | ✅ `a6959b5` |
| 2 | `meta promote --factory X` cableado al loop: re-deriva candidato → barrido blast-radius → re-pin+baseline en verde / rehúsa (exit 2) en rojo; façade-trap; dientes por CLI | ✅ `8d6a2c4` |
| 3 | prueba VIVA por bloqueo: promoción real (verde, RTM sube) + bloqueo de regresión (rojo) co-validado en ≥2 fábricas disjuntas (full-stack TS ⟂ iot Go); pin/baseline committeados | ✅ `475314b` |
| 4 | docs (este doc §Evidencia + STATE + ROADMAP G1 ✅), `meta check` 6/6, cerrar incremento | ✅ (este commit) |

## Evidencia (re-derivable, no narrada)

**El mecanismo (sustrato, dominio-agnóstico — ADR-012).** El loop `SELF-IMPROVEMENT.md §4` con el gate
de blast-radius, sin nombrar fábrica ni tech:
- `verify/verdict.py` — el VEREDICTO de una fábrica como cantidad RE-DERIVABLE: `line_green` (la línea
  reconstruye e2e en clon limpio) + `rtm_satisfied/total` (el árbol de evidencia C4). `dominates()` = la
  ley (build roto / SATISFIED caído / total encogido = regresión, HECHO duro no juicio §6); `raised()`
  distingue mejora real de hold (façade-trap). `rederive_verdict()` clona y re-deriva (doctrina de dos
  verificadores; nunca toca el `.proof/` real). Distinto de CUSTODIA (el `proof_sha` de `meta ci`): una
  promoción re-pinea, así que las SHAs cambian legítimo — lo que NO baja es la cobertura.
- `verify/checks/blast_radius.py` — el gate: barre cada fábrica del baseline, BLOQUEA si alguna bajó;
  `decide()` = la decisión PURA (facade/blast/decorative/promote) compartida con el verbo. Negativo
  non-decorativo (doctrina clean_runner): una baseline +1 SATISFIED debe regresar o el veredicto sería prosa.
- `cli.cmd_promote` (`meta promote --factory X [--baseline …] [--allow-hold]`) — re-deriva el barrido,
  dispatchea sobre `decide`, y SÓLO en verde re-pinea (`_pin_from_proofs`, extraído de `cmd_pin`) + sube
  baseline. NO committea: la promoción asciende por diff REVISADO (§4).
- `baseline_verdicts.json` — el registro committeado de veredictos downstream: {dummy(py) 5/5 ⟂
  full-stack(ts) 6/6 ⟂ iot(go) 6/6}, 3 lenguajes de producto disjuntos, una ley.

**Crit. 1 — el gate bloquea por bloqueo (dos lados, no decorativo).** `blast_radius` standalone con todas
las fábricas verdes → exit 0, "una baseline +1 cae a rojo (la ley tiene dientes)". `test_blast_radius.py`
(17 tests verdes): la ley (hold/raise/regresión/façade), el gate (regresión en CUALQUIER fábrica disjunta
bloquea), el diente non-decorativo (si `dominates` ignorara el conteo, `tooth_ok`=False), la decisión.

**Crit. 2 — `meta promote` re-pinea sólo si X mejora-o-mantiene y nadie baja; ante regresión INTACTOS.**
- VERDE (vivo): iot re-deriva 6/6 en clon limpio; `meta promote --factory iot` → "iot mejoró a 6/6;
  re-pineado (5 estaciones) + baseline subido; blast-radius verde (3 fábricas, ninguna bajó)". `ci
  --rederive --factory iot` 5/5 == pineado · RTM iot COMPLETE 6/6.
- BLOQUEO del verbo (vivo): con full-stack regresada y una baseline-temp iot=5/5, `meta promote --factory
  iot` → "BLOQUEADA (exit 2) … pin y baseline INTACTOS"; medido: el sha de `iot/pinned_verdict.json` y el
  `baseline_verdicts.json` real IDÉNTICOS antes/después.
- FAÇADE-trap (vivo): `meta promote --factory dummy` (sin mejora) → "FAIL (exit 2) nada que promover: el
  candidato no superó la baseline (hold, no mejora)".

**Crit. 3 — co-validado en ≥2 fábricas radicalmente distintas (mismo mecanismo).** La regresión la detecta
el MISMO gate en los **3 lenguajes de producto disjuntos**, cada uno restaurado a verde tras la prueba:
- dummy (**python**): marcador `DUMMY_OK`→`DUMMY_BROKEN` → "dummy: la línea NO reconstruye verde".
- full-stack (**typescript**): `export function`→sintaxis TS rota → "full-stack: la línea NO reconstruye verde".
- iot (**go**): `Accept` rompe la idempotencia (acepta duplicados) → "iot: la línea NO reconstruye verde"
  (regresión SEMÁNTICA: el `go test ./dedup` cae, no es error de sintaxis).

**Crit. 4 — anti-overfit (la mejora vivió en la fábrica, el sustrato quedó general).** El diff de sustrato
del incremento (`src/metafactory/ + seed/`, ~311 líneas) es SÓLO el mecanismo general — NO nombra ninguna
fábrica ni tech (`grep -iE 'iot|dedup|full-stack|go test|pytest|node:|docker|…'` sobre el diff `+` = 0).
La mejora de producto (la capacidad `ingestion_idempotente`/DES-4) vivió 100% en `factories/iot/`
(scaffold Go + spec + `stations/s4.yml`). La composición §5: el gate heredó re-derivación · rtm · pin gratis.

**Crit. 5 — verde global.** `meta check` 6/6 (compile · docs · projection · isolation · generality · suite).
Líneas vivas intactas: dummy `ci` 5/5 · full-stack 6/6 · iot 6/6 (re-pin) · ASF 11/11 (sin tocar). Árbol limpio.

## Criterio de cierre (demostrable, no narrable)
1. `blast_radius` bloquea (exit≠0) una promoción que baja el veredicto de CUALQUIER fábrica del barrido, y pasa una honesta — dos lados, no decorativo.
2. `meta promote --factory X` re-pinea X y sube su baseline SÓLO cuando X mejora-o-mantiene y ninguna downstream baja; ante una regresión deja pin y baseline INTACTOS.
3. Co-validado en ≥2 fábricas radicalmente distintas (lenguaje de producto disjunto): la regresión se detecta en cada una por el MISMO mecanismo.
4. Anti-overfit: `git diff src/metafactory/ + seed/` = sólo el mecanismo GENERAL (sin nombrar fábrica ni tech, ADR-012).
5. `meta check` 6/6 · líneas vivas (dummy/full-stack/iot/ASF) intactas · `ci --rederive` por fábrica == pineado.
