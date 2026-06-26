<!-- meta:doc sha=caa2c80ccc3dce8531dc3a936d5843f85f912c28 updated=2026-06-26T04:06Z -->
# Incremento DRAFT-HARDEN-DIAL

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-26T03:58Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
El **dial borrador→endurecer** de la Fase 4 (ADR-017 §4): operacionalizar el eje velocidad/rigor como una
elección de primera clase. Un `product-run --mode draft` corre SÓLO la columna núcleo (scaffold/datos/auth/
runtime) y DIFIERE la capa de rigor (`tier: harden`), para iterar rápido; `--mode harden` (el default,
byte-idéntico a antes) corre todo. Honesto por construcción: el draft NO finge los gates de rigor — los SALTA
(la estación diferida no tiene proof), y el veredicto se ROTULA como boceto.

## El mecanismo (qué deja en el sustrato — general, DATA-driven)
- **`engine/station.py`**: `Station` gana `tier: core|harden` (default `core`) + `active_in(dial)` — una
  estación `harden` se difiere en `draft` (como `activation: off`), corre en `harden`. La regla vive en UN
  lugar.
- **`engine/sequence.py`**: la rama `depends_on` (fan-in) de `predecessors()` ahora **cae a través** de un
  predecesor INACTIVO (transparente), igual que el caso lineal ya hacía → diferir una estación de rigor NUNCA
  traba una estación núcleo que dependa de ella. **Byte-neutral hoy** (ningún `depends_on` vivo lista una
  estación inactiva; el diente de fan-in de s10 quita un PROOF, no una estación → intacto).
- **`cli.py`**: `_run_product_line(..., dial=...)` difiere las estaciones harden en draft (reusa toda la
  maquinaria active/predecessor); `meta product-run --mode draft|harden` (default harden); el veredicto draft
  se rotula «DIAL=draft (boceto, NO endurecido — N estaciones harden diferidas: …; endurecé antes de pinear)».
- **Anti-fake-green**: el `proof_sha` deriva SÓLO de (station_id, nombres+exits de checks) — NO del `tier`.
  Por eso harden (todas las estaciones) es byte-idéntico al pin existente (cero re-pin), y un draft (subconjunto)
  produce OTRO set de proofs → NO se puede pinear un draft y pasar el `ci --rederive` (que re-corre harden).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `tier` + `active_in` en Station; fall-through transparente del fan-in en Sequence | ✅ |
| 2 | dial en `_run_product_line` + `--mode` en `product-run` + rótulo honesto del boceto | ✅ |
| 3 | Test dos-lados por bloqueo en el motor REAL (`tests/test_dial.py`) | ✅ |
| 4 | `meta check` 11/11 (sin gate nuevo: el dial es un modo) + docs | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `tests/test_dial.py` verde (7 tests, motor REAL): tier semántica · **harden ATRAPA el rigor que falla /
   draft lo SALTA** (mismo line, rojo en harden, verde en draft) · el draft NO escribe proof de la estación
   diferida (no finge) · una estación núcleo que `depends_on` una harden diferida cae a través al spine ·
   harden mantiene el fan-in completo (byte-idéntico). ✅
2. `meta product-run --mode draft` rotula el boceto e2e por CLI (verificado vivo en la línea `dummy`). ✅
3. `meta check` **11/11** (el dial NO agrega gate — es un modo; la suite cubre `test_dial`); el motor no
   regresiona (`test_multistation`/`test_rtm_tree` verdes — el cambio de fan-in es byte-neutral). ✅

## Evidencia (por bloqueo)
- `pytest tests/test_dial.py` → 7 passed (motor real, proofs reales, subprocess reales).
- `pytest test_dial+benchmark+multistation+rtm_tree` → 35 passed (sin regresión del motor).
- `meta product-run --factory dummy --mode draft` → PASS + rótulo «DIAL=draft (boceto, NO endurecido …)».
- `meta check` → `11 checks all green` (compile…quality ok · benchmark ok · suite ok); el dial NO agrega gate.

## Alcance honesto (§7)
Este incremento entrega el **mecanismo** del dial (meta), probado por bloqueo en el motor real. La **adopción**
—que una línea declare qué estaciones son `tier: harden`— es DATA por-fábrica (un incremento de fábrica chico,
byte-neutral porque el tier no toca el proof_sha): hoy ninguna fábrica la declara, así que `--mode draft` sobre
una línea real es no-op honesto (el rótulo lo dice: «0 estaciones harden diferidas»). El siguiente paso natural
y barato es taggear la capa de rigor de FSK (s2 dureza · s3 frescura · s4 supply-chain · s8 a11y/perf · s10
hermético) y/o de `dummy` → el draft saltaría esa capa. **Declared-deferred** con disparador: cuando se quiera
el loop de velocidad sobre una app real. Es el incremento hermano `REAIM-SWEET-SPOT` el que provee el TARGET
que el «endurecer» debe alcanzar.
