<!-- meta:doc sha=40a2c2f0af497aa0615c4bcd988d21228fdb1b46 updated=2026-06-27T15:06Z -->
# Incremento LEAST-PRIV-DECOUPLE

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-27T15:06Z) (creado 2026-06-27T14:59Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Cerrar el último residual SOTA (ADR-018 §3, ADR-016 Fase 2): el alcance de la columna **por nivel** deja de
ser una lista de archivos curada a mano en `template/factory/harness/` y pasa a ser una **declaración
single-source en el sustrato** + un **gate `least_priv` de dos lados** que prueba la propiedad de
mínimo-privilegio (la fábrica hereda SÓLO lo que gobierna, NO la columna entera del meta por inercia).

## Contexto (medido, no a ojo)
- La columna de la fábrica YA es un subconjunto: 6 de los 12 hooks del meta — falta `gate_guard` (correr
  estaciones es META-operado, gov-table «opera: el meta sobre la fábrica») y los 5 hooks de
  memoria/observabilidad (`doc_stamp`/`mem_capture`/`mem_rollup`/`session_start`/`pre_compact`, meta-only
  hoy, HONEST-STATE §7). Gobierna: `proof_protect`·`increment_guard`·`commit_guard`·`stop_proof` (enforcement)
  + `blast_radius`·`verdict_required` (delegación, bajados en §1 `FACTORY-DELEGATION-TEETH`).
- El hueco honesto: **ningún diente prueba que ese subconjunto sea el correcto.** `column_parity` sólo prueba
  fidelidad-al-template (in-tree ≡ render(template)); si alguien agrega `session_start.py` al template, lo
  renderiza a la fábrica y `column_parity` pasa feliz → sobre-privilegio sin detección.
- La frontera de seguridad se mantiene (ADR-018 §4): el alcance es **código del sustrato**, NO DATA de spec
  — un spec adversario no puede ensanchar su propio privilegio.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `column_scope.py` (sustrato): declaración single-source `META_COLUMN` / `FACTORY_COLUMN` (⊊) + `META_ONLY` derivado, con la calibración (por qué cada hook NO baja) | ✅ |
| 2 | gate `least_priv` (`verify/checks/least_priv.py`) cableado a `meta check`: fábrica = scope exacto · ⊊ meta · template ≡ scope · declaración ≡ realidad · diente RED dos-lados | ✅ |
| 3 | tests (`tests/test_least_priv.py`) + docs (ADR-018 §3 cerrado en GOVERNANCE-LAYERING §7 + STATE/LOG; ADR inmutable NO se churnea) | ✅ |

## Evidencia
- `meta check` **16/16** (era 15/15): `least_priv` cableado y verde — cada una de las **5 fábricas** hereda
  exactamente `FACTORY_COLUMN` (6 hooks) ⊊ `META_COLUMN` (12); 6 meta-only fuera; diente RED dos-lados vivo.
- `pytest tests/test_least_priv.py` **8/8**: prueba por bloqueo aislada — sobre-privilegio (hook meta-only
  filtrado a la fábrica → ROJO `over-privilege`, sólo ese hook) · incompletitud (hook gobernado ausente →
  ROJO `incomplete`, sólo ese hook) · sobre-privilegio del template (la fuente de la proyección) · fantasma
  de declaración (rol declarado sin hook real en el meta) · `FACTORY_COLUMN ⊊ META_COLUMN`.
- Sin re-pin: el scope es del SET de roles, no de bytes; `least_priv` no toca `proof_sha` (lo de bytes ya lo
  prueba `column_parity`). Frontera de seguridad intacta (ADR-018 §4): el scope es sustrato, no DATA de spec.

## Criterio de cierre (demostrable, no narrable)
1. `least_priv` verde en `meta check`: cada fábrica hereda exactamente `FACTORY_COLUMN`; `FACTORY_COLUMN ⊊ META_COLUMN`; el template y la realidad del meta coinciden con la declaración.
2. Prueba por bloqueo (dos lados): plantar un hook meta-only en un árbol de fábrica sintético → ROJO «sobre-privilegio»; quitar un hook gobernado → ROJO «incompleto»; comparador decorativo → ROJO.
3. `meta check` verde (gate nuevo incluido) · `pytest tests/` verde · `git diff` sin residuo no-commiteado.
