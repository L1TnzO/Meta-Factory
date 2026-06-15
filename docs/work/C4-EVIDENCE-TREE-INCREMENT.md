<!-- meta:doc sha=90ae539e5ce66c8b6193b87f3b5201fc9156cddc updated=2026-06-15T20:30Z -->
# Incremento C4-EVIDENCE-TREE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-15T20:19Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Generalizar el RTM al **árbol de evidencia por build** completo: **req→capability→station→proof→artifact**,
re-derivado SÓLO de `.proof/` + el spec + los artefactos en disco (SAFE-4, I-10). Hoy `meta rtm`/M5 sólo
re-derivan la espina req→station→proof; faltan dos aristas: **req→capability** (no existe el borde L5→L1) y
la **hoja proof→artifact** (no se asevera que el artefacto que el proof certifica EXISTA). Un borde roto en
cualquier punto baja el requisito a UNSATISFIED — y se prueba por bloqueo.

## Diseño (la frontera)
- **Arista req→capability** (model/loader/validator/schema): `Requirement.capability` (opcional, id de una
  capability declarada). M0 RECHAZA una capability fantasma (como ya hace con `verified_by`→verifier fantasma).
- **Single source `verify/rtm.py`**: el árbol (ReqNode→capability/stations/artifacts) + su re-derivación +
  el render. Lo consumen TANTO `meta rtm` (display, ≤bus) como el gate (block) — sin duplicar la ley (como
  `rederive_pinned`). Un req está SATISFIED iff: mapea a ≥1 estación activa **Y** su capability (si la declara)
  es real **Y** toda estación tiene proof presente + gate-recompute-OK (Cerrojo 2) **Y** todo artefacto que su
  capability declara EXISTE en disco.
- **Hoja proof→artifact (tooth NUEVO)**: el artefacto es el `capability.artifact` declarado (L1, dato). La hoja
  atrapa **evidencia rancia**: el proof dice passed pero el artefacto que certifica desapareció — distinto de
  M5 (flip de exit) y de M6 (rebuild completo). Donde una capability no declara artefacto (proxy/legacy), la
  hoja es vacía: no se fabrica una arista que el spec no declara (honesto).
- **Gate `rtm_tree`** (kind + helper, cableado a m05 junto a `rtm_rederive`): re-deriva el árbol y prueba por
  bloqueo — baseline ≥1 req SATISFIED; corromper el proof (hermético) → UNSATISFIED; **borrar el artefacto**
  (hermético) → UNSATISFIED. Un tooth no-ejercitable (sin artefacto, p.ej. ASF proxy) se REPORTA, no se finge.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Arista req→capability (model/loader/validator/schema; M0 rechaza capability fantasma) + `verify/rtm.py` (árbol+re-derivación+render, single source) + `cmd_rtm` generalizado (mismo bus) + gate `rtm_tree` (kind+helper) cableado a m05 + `test_rtm_tree.py` (12 tests) | ✅ `bb73620` |
| 2 | Dummy = demostrador del árbol COMPLETO: 3 capabilities con `artifact` (build/greeting.py · build/manifest.txt · build/test_greeting.py) + req.capability (REQ-F-00{1,2,3}) + sync `specs/dummy`. M0–M8 verdes (m05 corre rtm_tree); `meta rtm` muestra el árbol; viva por CLI: borrar build/greeting.py → REQ-F-001 UNSATISFIED. Sin re-pin (aristas L1/L5 no tocan `stations/`); ASF proxy verde (hoja vacía, espina probada) | ✅ `649a7ee` |
| 3 | Docs (STATE/ROADMAP/LOG + evidencia) + cierre | ✅ |

## Evidencia (demostrable, no narrable)
- **`meta rtm` re-deriva el árbol completo** (dentro del bus, una línea por requisito): `REQ-F-001 SATISFIED
  <- invariant_marker: s00 [build/greeting.py✓]` … 3/3 para el dummy. Single source `verify/rtm.py`,
  compartido con el gate (sin duplicar la ley).
- **Arista req→capability con dientes (M0)**: `Requirement.capability` (model/loader/schema); el validator
  RECHAZA una capability fantasma (`test_m0_refuses_phantom_capability`), mismos dientes que verifier fantasma.
- **Hoja proof→artifact (tooth NUEVO)**: el `capability.artifact` declarado debe EXISTIR. Atrapa evidencia
  rancia — proof passed pero el artefacto desapareció. Distinto de M5 (flip-exit) y M6 (rebuild). Sin artefacto
  declarado → hoja vacía, no se finge (`test_no_artifact_declared_is_not_faked`).
- **Gate `rtm_tree` (m05, junto a rtm_rederive)**: re-deriva el árbol y prueba por bloqueo — corromper proof
  (hermético) → UNSAT; **borrar el artefacto** (hermético) → UNSAT; proxy sin artefacto → tooth N/A REPORTADO.
- **Dummy = árbol COMPLETO**: 3 capabilities con artifact + req→capability. M0–M8 verdes (`m05: rtm_rederive ok
  · rtm_tree ok`); `meta rtm` 3/3; `ci --rederive` **3/3 proof_sha==pineado** (pin intacto — las aristas L1/L5
  no se materializan en `stations/`). ASF (proxy): `rtm_tree` verde probando la espina, artifact tooth N/A.
- **Prueba por bloqueo VIVA por CLI**: borrar `build/greeting.py` con el proof de s00 INTACTO (passed) →
  `REQ-F-001 UNSATISFIED` (`artefacto ausente: build/greeting.py`), RTM 2/3; restaurar → COMPLETE 3/3.
- **Veredicto**: suite **376** (era 364); `meta check` 5/5; árbol limpio.
- **Diferido honesto (no agujero de C4)**: la hoja cruza existencia del artefacto, no su contenido vs. el proof
  (eso ya lo cubre la re-derivación M6/`ci`); gating DAG multi-predecesor sigue diferido (C2). El árbol es por
  requisito; un grafo capability↔station N:M más rico llega si un dominio lo pide (F1).

## Criterio de cierre (demostrable, no narrable)
1. `meta rtm` re-deriva el árbol **req→capability→station→proof→artifact** de `.proof/`+artefactos, dentro del
   bus (≤N líneas, una por requisito con la arista rota anotada). Un árbol COMPLETO para el dummy multi-estación.
2. **Arista req→capability con dientes**: M0 RECHAZA una `capability` que no existe (capability fantasma);
   probado con un negativo en la suite.
3. **Prueba por bloqueo (gate `rtm_tree`)**: corromper un proof → el requisito cae a UNSATISFIED; **borrar el
   artefacto** que su capability certifica → UNSATISFIED (tooth nuevo de evidencia rancia). Reproducible (hermético).
4. **Generalidad**: ASF (sin la arista nueva) sigue verde — el gate prueba la espina y reporta el tooth de
   artefacto como N/A (no lo finge). Dummy ejercita el árbol completo. Sustrato dominio-agnóstico (ADR-012).
5. Dummy M0–M8 + `product-run` + `ci --rederive` 3/3; viva por CLI (borrar build/greeting.py → REQ-F-001 UNSAT,
   restaurar → COMPLETE). Suite verde, `meta check` verde, árbol limpio.
