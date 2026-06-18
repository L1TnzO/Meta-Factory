<!-- meta:doc sha=6bba21e3588e565422af85aec7630727f3782846 updated=2026-06-18T16:59Z -->
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
| P1 | **m04 frontera-como-DATO (opt-in honesto)**: el stub dominio/generado lo declara la spec como contenido inline en `domain.product` (fluye a `spec.subst`); `emit_boundary` lo escribe SÓLO si está declarado; m04 deja de renderizar el template Python del sustrato. La frontera I-5 (split humano/generado) sólo aplica donde el producto LO TIENE: la dummy es el ejemplar; full-stack/iot/ASF (producto 100% scaffolded, sin capa humana) hacen opt-out y `boundary_survives` reporta N/A honesto. Mata el template Python del sustrato + los `domain/webapp.py`/`iotgw.py`/`agent_system.py`(demo) + `generated/runner.py` vestigiales. | ⏳ |
| P2 | **Gate DAG multi-predecesor**: `engine/gate.py` + `Station` honran TODOS los `depends_on` (no sólo `requires_prev`); una estación fan-in queda SHUT si CUALQUIER predecesor no está verde. Prueba por bloqueo con fixture fan-in. | ⏳ |
| P3 | **`gate_guard` acotado**: una mención de `station X --factory Y` en prosa/quote no dispara el deny; un `meta station` fuera de orden REAL sí. | ⏳ |

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
