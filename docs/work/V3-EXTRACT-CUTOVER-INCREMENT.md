<!-- meta:doc sha=c15f3cd1e559212f4f236afdf647cb6464e1bd21 updated=2026-08-05T00:40Z -->
# Increment V3-EXTRACT-CUTOVER

> **Governance doc.** Status: **OPEN** (created 2026-08-05T00:38Z). Close it with `v3 increment close`
> (gated: clean tree + active station green). Every code change lives here (ADR-010).

## Goal
Sacar la plataforma de este repo y dejarla **viva y verificable por sí sola** en
`~/University/Integración/APP/Claude_Agents/v3` — nacida, no copiada — con las dos mitades de la
aceptación declaradas por separado (esta máquina y la otra, ADR-005).

## 0. Lo que el ensayo ya midió (no lo repitas)

Repo construido sólo con las 15 filas `PACKAGE`, un commit, cero ancestría de v2
(`V3-EXTRACT-DIRECTION-INCREMENT.md §6.0`): **44/44 gates REGISTRAN** · `meta check --skip rederive` =
**31 verdes · 7 rojos · 5 N/A**, y **los 7 rojos son exactamente artefactos `BORN_FRESH`**
(`docs`·`evidence_liveness`·`projection`·`state_fidelity`·`state_snapshot`·`telemetry_liveness`·`ledger`).
El repo estaba **copiado pero no nacido**. Esos 7 son, por lo tanto, la lista de aceptación de este
incremento: **se ponen verdes NACIENDO**. Uno que se pusiera verde *copiando* sería el error exacto que
`BORN_FRESH` existe para impedir — importar un verde que nadie volvió a ganarse.

## 1. `v3/oracle_ref.json` VIAJA — y por qué eso no es una deuda

La dirección decía «se retira o se re-apunta». **Medido, la respuesta es la tercera: viaja como SELLO
DE PROCEDENCIA.** Cuatro módulos nombran `oracle_ref` y hacen shell a `git`:

| módulo | qué es hoy |
| --- | --- |
| `checks/pin_integrity.py` | **gate registrado** — usa el ref para verificar la PROCEDENCIA de un pin |
| `column_law_parity.py` | **gate registrado** — pinneado en la fase 2; compara contra el pin, no contra git |
| `line_parity.py` | **huérfano**: nadie lo importa, ningún gate lo corre |
| `parity.py` | **huérfano** — y guarda el último `git show <ref>:<path>` del árbol |

Los dos gates vivos **pasaron VERDES en el ensayo, en un repo sin ancestría**. Eso es la prueba, no la
intención: usan el sha como **nombre** (un sello que dice de dónde salieron los pines), no como
**dirección** (algo que se resuelve). Es la misma distinción que la ley 9 de
`V3-EXTRACT-CORPUS-PARITY`, un nivel más abajo. Un sha en un JSON que nadie le pasa a `git show` es
historia, no un puntero roto.

## 2. Los dos huérfanos: hallazgo, NO trabajo de este incremento

`parity.py` y `line_parity.py` (y `kinds_parity.py`, que tampoco tiene importador ni gate) son el
andamio de INC-1/INC-2: **ningún módulo los importa y ningún gate los corre** (grafo de imports por
AST + los `argv` del registry). Viajarían inertes al destino.

**No se tocan acá, y la razón importa.** Es `N-0139` —seis leyes ejecutables que no corre nadie— con
tres sujetos más y un nombre mejor: *alcanzabilidad*. Decidir cada uno (borrar vs **cablear**:
`registry_law` suena a que hay que correrlo, no a que sobre) es su propio incremento. Meterlo acá
convertiría un cutover en una refactorización, que es exactamente cómo un incremento se come a otro.
Lo que sí deja este incremento es el **sujeto medido**, anotado en el nodo.

## Phases
| Phase | Content | Status |
| --- | --- | --- |
| 1 | **Nacer el repo**: 15 filas `PACKAGE` copiadas con paths preservados (`tar`, nunca `cp -r` por fila) + las 10 filas `BORN_FRESH` **generadas**: `docs/STATE.md`·`LOG.md`·`work/`·`decisions/` propios, `plan/tree.json` propio, `INDEX.md` derivado, `.proof/` ganado corriendo | pending |
| 2 | **Aceptación mitad A (esta máquina)**: `meta check` sin rojos en el destino — los 7 de `§0` verdes por nacimiento — y `rederive` == pin sobre los 10 targets | pending |
| 3 | **Aceptación mitad B**: `meta attach --factory dummy --driver repl` levanta y contesta en el destino; y el segundo verificador (ADR-005) queda armado, imprimiendo lo que NO corrió | pending |
| 4 | **El origen**: qué pasa acá cuando la plataforma ya vive allá (este repo NO se toca en el 1–3; su disposición se decide con el resultado en la mano) | pending |

## Close criterion (demonstrable, not narrated)
1. En `~/University/Integración/APP/Claude_Agents/v3`: **44 gates registran** y `meta check` **sin
   rojos**, con los 7 de `§0` verdes **por haber nacido** (STATE/LOG/INDEX/plan propios), no copiados.
2. `rederive` == pin sobre los **10 targets** en el destino.
3. `meta attach --factory dummy --driver repl` levanta y contesta allá.
4. Este repo (`Meta_Factory`) sigue en **43·0·1 = 44**: el cutover no lo degrada mientras se decide su
   disposición.
5. Las dos mitades declaradas **por separado** (§11.6 de INC-11: nunca fundir dos actores en un número).

## Evidencia
<!-- filled at close -->
