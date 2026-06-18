<!-- meta:doc sha=ae4318cd18ba2c531c731285d6e656f8e1664f0b updated=2026-06-18T17:33Z -->
# Incremento H2-SUBSTRATE-HYGIENE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-18T16:48Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Cerrar tres warts de sustrato VERIFICADOS EN CÓDIGO (no en docs rancios) sin tocar la generalidad ya
probada: (P1) la frontera I-5 de m04 deja de estar casada con Python y se vuelve DATO en el lenguaje de
cada fábrica · (P2) el gate de la línea de producto deja de ser lineal y honra el DAG `depends_on`
completo · (P3) el `gate_guard` del meta deja de sobre-matchear `station … --factory …` en prosa.
> Hallazgo de arranque: el 4º wart histórico (`proof_protect` sobre-celoso, `HONEST-STATE §2`) **ya estaba
> cerrado** (su docstring documenta el narrowing por token-boundary). La nota del doc estaba rancia; se
> verifica contra el código, no contra la narrativa. Queda fuera de alcance por estar HECHO.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| P1 | **m04 frontera-como-DATO (opt-in honesto)**: el stub dominio/generado lo declara la spec como contenido inline en `domain.product` (fluye a `spec.subst`); `emit_boundary` lo escribe SÓLO si está declarado; m04 deja de renderizar el template Python del sustrato. La frontera I-5 (split humano/generado) sólo aplica donde el producto LO TIENE: la dummy es el ejemplar; full-stack/iot/ASF (producto 100% scaffolded, sin capa humana) hacen opt-out y `boundary_survives` reporta N/A honesto. Mata el template Python del sustrato + los `domain/webapp.py`/`iotgw.py`/`agent_system.py`(demo) + `generated/runner.py` vestigiales. | ✅ `88c13d3` — dummy ejercitada verde (byte-idéntico, sin re-pin) + diente 2 lados (monkeypatch→rojo); opt-out N/A py⟂ts⟂go; suite 528 · meta check 6/6 · ci 4 fábricas == pin |
| P2 | **Gate DAG multi-predecesor**: `engine/gate.py` + `Station` honran TODOS los `depends_on` (no sólo `requires_prev`); una estación fan-in queda SHUT si CUALQUIER predecesor no está verde. Prueba por bloqueo con fixture fan-in. | ✅ — `Sequence.predecessors()` (DAG) + `gate` itera TODOS; `materialize_line` emite `depends_on` para fan-in (>1), `requires_prev` para lineal (sin churn). Fixture fan-in con proofs REALES: OPEN sólo con a∧b∧c verdes, SHUT si a O b cae/falta (10 tests); líneas lineales intactas |
| P3 | **`gate_guard` acotado**: una mención de `station X --factory Y` en prosa/quote no dispara el deny; un `meta station` fuera de orden REAL sí. | ✅ — matcher `match_station_cmd` acotado a una INVOCACIÓN (`meta station … --factory …` en borde de comando, prefijo env/`./` opcional); prosa/echo/commit-msg → None. 13 tests + demo VIVO: el hook real ALLOW (exit 0) un `git commit -m "…meta station…"`. Lógica de bloqueo intacta (engine = gate real) |

## Criterio de cierre (demostrable, no narrable)
1. **P1**: el sustrato no hardcodea lenguaje en la frontera I-5 (template Python borrado; `m04`+`emit_boundary`
   sólo enrutan DATO); la dummy declara su frontera inline y `boundary_survives` la EJERCITA verde con sus
   dos lados (drop `skip_if_exists` → edición comida → rojo); full-stack/iot/ASF opt-out → `boundary_survives`
   N/A honesto (no fingido) y CERO `domain/*.py`+`generated/runner.py` vestigiales en su árbol; dummy
   `domain/greeting.py`+`generated/runner.py` byte-idénticos (sin re-pin).
2. **P2**: un fixture fan-in (estación con `depends_on: [a, b]`) → gate SHUT si a O b no recompone verde,
   OPEN sólo con ambos verdes (dos lados, no decorativo); las líneas lineales vivas intactas.
3. **P3**: `gate_guard` no deniega un `echo "... station m02 --factory iot ..."`; sí deniega un `meta
   station` real fuera de orden (sombra del engine intacta).
4. **Global**: `meta check` 6/6 · `ci --rederive` dummy/full-stack/iot/ASF == pineado · `git diff
   src/metafactory/ + seed/` sólo mecanismo general (0 nombres de fábrica/tech).

## Evidencia (output REAL, no narrado)
- **P1** `88c13d3`: byte-identity dummy (`emit_boundary` == comiteado) → sin re-pin; `boundary_survives`
  EJERCITADO verde en dummy + N/A en full-stack(ts)/iot(go)/ASF(py); diente 2 lados por monkeypatch (regresión
  de `_emit_boundary` → ROJO) + declaración parcial → ROTTEN. Borrados: `template/factory/product/` + 6 stubs.
- **P2** `99571dc`: `tests/test_engine.py::TestDagGate` con proofs REALES (no mocks) — fan-in a,b→c OPEN sólo
  con a∧b∧c verdes; SHUT si a O b cae/falta; `materialize_line` emite el DAG para fan-in, `requires_prev` para
  lineal (cero churn). Líneas lineales y pins intactos.
- **P3** `<este commit>`: `match_station_cmd` acotado; 13 tests dos lados; demo VIVO — el hook real ALLOW
  (exit 0) un `git commit -m "…meta station m02 --factory iot…"`. Lógica de bloqueo intacta (engine = gate real).
- **Global**: suite 551 verde · `meta check` 6/6 · `ci --rederive` dummy 5/5 · full-stack 6/6 · iot 5/5 ·
  ASF 11/11 == pineado (árbol limpio, docker s2/s3) · anti-overfit `git diff src/+seed/` = sólo mecanismo general.
- **Hallazgo**: el 4º wart histórico (`proof_protect` sobre-celoso, `HONEST-STATE §2`) ya estaba CERRADO en
  código (docstring documenta el narrowing por token-boundary); la nota estaba rancia — fuera de alcance.
