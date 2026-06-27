<!-- meta:doc sha=cd8184fba8de36bd085eade8991504c7f63c119d updated=2026-06-27T02:57Z -->
<!-- meta:doc sha=PENDING updated=2026-06-27T02:55Z -->
# Incremento DIAL-MEASURE

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-27T02:57Z) (creado 2026-06-27T02:50Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
El **sustrato** para ADOPTAR el dial draft→harden (ADR-017 §4): cablear `tier` desde el spec hasta la línea
materializada (el wire que faltaba) + un gate `dial` MEDIDO que le da dientes a un dial adoptado, para que no
pueda re-pudrirse a decorativo. Es la mitad-META; la adopción real de FSK (taggear su capa de rigor) es el
incremento-hermano de FÁBRICA `FSK-DIAL-ADOPT` (ADR-016, dos incrementos por nivel).

## Contexto (por qué este incremento)
`DRAFT-HARDEN-DIAL` (2026-06-26) construyó el MECANISMO (`Station.active_in` + `--mode draft`) y lo probó por
bloqueo en el motor — pero quedó DORMIDO: ninguna fábrica taggeaba estaciones, así que `--mode draft` difería
el conjunto VACÍO (no-op). Dos huecos reales bloqueaban la adopción:
1. **El wire**: `_materialize_line` NO propagaba `tier` → aunque el spec lo declarara, la `stations/<id>.yml`
   regenerada (lo que el motor corre, y lo que `ci --rederive` re-deriva) lo perdía → toda estación quedaba
   `core`. `test_dial.py` no lo expuso porque construye `Station.from_dict({"tier":…})` DIRECTO (saltea
   materialize). Cerrarlo es el corazón de este incremento.
2. **Sin diente**: el dial era "un modo, sin gate". Adoptarlo es justo cuándo un gate gana su lugar: para que
   un dial adoptado quede MEDIDO y no pueda volverse decorativo (taggear todo harden → draft no construye nada).

## El mecanismo (qué deja en el sustrato — general, DATA-driven, ADR-012)
- **`spec/model.py` + `spec/loader.py`**: `SpecStation` gana `tier: core|harden` (default `core`), parseado
  del `station_sequence`. DATA en la línea; el sustrato no nombra estación.
- **`codegen/renderer.py::_materialize_line`**: propaga `tier` a `stations/<id>.yml` **sólo si != core** → una
  fábrica que no adopta tiene su YAML materializado byte-idéntico (su pin intacto). Una `harden` ahora sí llega
  al motor (`Station.active_in("draft")` la difiere). **Este es el wire que faltaba.**
- **`verify/dial.py`** (single source, ADR-005 §4): `measure`/`gate_problems`/`render`, re-derivado SÓLO de
  estado commiteado (el `station_sequence` del spec; sin `.proof/`, sin correr la línea → barato, clon-limpio).
  El delta MEDIDO es ESTRUCTURAL (|harden| de |active| que el draft difiere), no wall-clock (no re-derivable →
  nunca un bit verde/rojo; una medición puntual se NARRA en evidencia).
- **`verify/checks/dial_gate.py`** + cableado a `meta check` (15 checks): dos-lados — un dial ADOPTADO (≥1
  harden) debe diferir un subconjunto PROPIO no vacío (`0 < |harden| < |active|`); all-harden = decorativo →
  ROJO; no-adoptado (0 harden) = N/A (opt-in, honesto, SAFE-7).
- **`meta dial`** (verbo): reporta el split core/harden por fábrica (display, bus-bounded, misma ley que el gate).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `tier` en `SpecStation` (model+loader) + propagación en `_materialize_line` (el wire) | ✅ |
| 2 | `verify/dial.py` (single source) + `dial_gate` cableado a `meta check` + verbo `meta dial` | ✅ |
| 3 | Test por bloqueo del wire + dientes del gate (`tests/test_dial_measure.py`) | ✅ |
| 4 | `meta check` 15/15 (gate nuevo `dial`; N/A en todas hasta que FSK adopte) + docs | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `tests/test_dial_measure.py` verde (7 tests): el loader parsea `tier` · `_materialize_line` lleva `harden`
   y OMITE `core` (byte-neutral) · round-trip materializado → motor difiere en draft · gate verde en
   subconjunto-propio / ROJO en all-harden / N/A en no-adoptado · estación off excluida del conteo. ✅
2. `meta dial` reporta el split de las 5 fábricas (0/5 adoptadas hoy — el wire existe, la adopción es DATA). ✅
3. `meta check` **15/15** (`dial ok`, N/A honesto: ninguna fábrica adoptó aún); el motor no regresiona (los
   pins de las 5 fábricas intactos — `tier` no toca el `proof_sha` ni el YAML materializado de las no-adoptantes). ✅

## Evidencia (por bloqueo)
- `pytest tests/test_dial_measure.py tests/test_dial.py` → 14 passed (wire + motor, specs/materialize reales).
- `meta dial` → PASS, 0/5 adoptadas, cada fábrica con su conteo de estaciones (todas core).
- `meta check` → `15 checks all green` (… benchmark ok · **dial ok** · column_parity …); el gate `dial` es N/A
  honesto hasta que `FSK-DIAL-ADOPT` taggee la capa de rigor de FSK.

## Alcance honesto (§7)
Este incremento entrega el SUSTRATO (wire + gate + verbo), probado por bloqueo, general (cero nombres de
fábrica/tech). La ADOPCIÓN —que FSK declare `tier: harden` en su capa de rigor + la evidencia viva (draft
difiere el rigor y corre el spine; harden == pin)— vive en el incremento-hermano de FÁBRICA `FSK-DIAL-ADOPT`.
El delta wall-clock (draft vs harden en segundos) NO se gatea (no re-derivable); se MEDIRÁ una vez y se narrará
en la evidencia de `FSK-DIAL-ADOPT`.
