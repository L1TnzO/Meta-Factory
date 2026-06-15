<!-- meta:doc sha=0e114c2a86252e8b2647ec0e24825ab2a0dee00d updated=2026-06-15T20:00Z -->
# Incremento C3-PRODUCT-ENV-PROOF

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-15T19:44Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Hacer EJECUTABLE el `runs_in: product_env` (hoy sólo descriptivo, L2): un proof_check corre en el
**toolchain DEL producto** (pytest ↔ tsc ↔ node — DATA por spec, ADR-012), en un env **aislado** del de
la fábrica (sin `PYTHONPATH`/`VIRTUAL_ENV` del Meta-Factory: el producto no aprueba pidiendo prestado el
toolchain de la fábrica, DES-8/SAFE-2). Es el **M8 real generalizado** (SAFE-2): el MISMO mecanismo acepta
`tsc`/`node` sin tocar el sustrato. Engine·gate·verifier·seed **intactos** (sólo un kind nuevo + un helper).

## Diseño (la frontera)
- **Kind nuevo `product_env`** (`verify/checks/registry.py`) → resuelve al helper de sustrato
  `metafactory.verify.checks.product_env`. La check lleva como DATA: `workdir` (subdir del producto),
  `bootstrap` (argv, opcional — `uv venv` ↔ `npm ci` ↔ `python -m venv`) y `cmd` (argv del proof — pytest ↔
  tsc ↔ node). El sustrato **no nombra tech**: bootstrap/cmd son argv (ADR-012); el guard lo prueba.
- **El helper ORQUESTA, no verifica** (como el slot `generate`, ADR-013): corre bootstrap→proof con
  `cwd=workdir` y env **scrubbed** (saca `PYTHONPATH`/`VIRTUAL_ENV`/`PYTHONHOME`). Exit 0 sii ambos exit 0;
  nunca levanta excepción más allá del veredicto (fail-safe: 127 si no lanza, 2 si falta el workdir). La
  columna sigue siendo el único árbitro — el helper sólo encadena exit codes (Cerrojo 1 intacto).
- **Aislamiento = el corazón de DES-8**: scrubbear el `PYTHONPATH` del Meta-Factory es lo que impide que el
  producto "pase" importando `metafactory`. Probado por bloqueo (`import metafactory` falla en product_env).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Helper `verify/checks/product_env.py` (orquesta bootstrap→proof, env scrubbed) + kind `product_env` en el registry + `tests/test_product_env.py` (10 tests: helper aislado pasa/bloquea-en-rojo/bloquea-si-bootstrap-falla/`import metafactory` aislado/workdir ausente→2/no-lanza→127; pass-through ADR-012; e2e por el motor real: estación gatea + corromper→SHUT; 2º dominio node por principio #6) | ✅ `afd967b` |
| 2 | Dummy → línea de **3 estaciones**: s00 también rendea el test del producto; s02 nueva = proof `product_env` (venv stdlib aislado corriendo el unittest del producto) + REQ-F-003 (verified_by) + sync `specs/dummy` ↔ `factories/dummy` (P2a `fb4841b`); re-materializar (m02) + re-pin (P2b `5b5386f`). Prueba VIVA por CLI: `product-run` PASS 3/3, M0–M8 + `ci --rederive` 3/3, corromper el test del producto → s02 SHUT (s00/s01 verdes) | ✅ `fb4841b`·`5b5386f` |
| 3 | Docs (STATE/ROADMAP/LOG + esta evidencia) + cierre | ✅ |

## Evidencia (demostrable, no narrable)
- **`runs_in: product_env` ahora EJECUTABLE**: kind `product_env` (`verify/checks/registry.py`) → helper
  `verify/checks/product_env.py`. El helper ORQUESTA bootstrap→proof (argv DATA) con `cwd=workdir` y env
  **scrubbed** (`PYTHONPATH`/`VIRTUAL_ENV`/`PYTHONHOME` del Meta-Factory fuera). Exit 0 sii ambos exit 0;
  fail-safe (127 no-lanza, 2 workdir ausente). Engine·gate·verifier·seed **intactos**.
- **Aislamiento real (DES-8), prueba decisiva**: con `src/` en PYTHONPATH, un subprocess control importa
  `metafactory` OK, pero DENTRO de product_env `import metafactory` **FALLA** (≠0) — el scrubbing es lo que
  impide aprobar con el toolchain de la fábrica. No es cosmético (`test_isolated_from_factory_toolchain`).
- **Tech-agnóstico (ADR-012)**: el registry resuelve `product_env` como **pass-through** — argv opacos
  (`TOOLCHAIN_A`/`TOOLCHAIN_B`) viajan verbatim, el sustrato no los reconoce ni traduce
  (`test_registry_passes_toolchain_through_verbatim`); guard de imports (`test_isolation`) intacto (helper solo-stdlib).
- **2º dominio (principio #6)**: el MISMO kind corre `node --test` (no-Python) — test node verde→0, assert
  fallido→≠0 — sin rama por-tech en el sustrato (`test_same_kind_runs_node_toolchain`).
- **Dummy = línea de 3 estaciones**: s00 (greeting + rendea el test del producto) → s01 (manifest) → s02
  (`product_env`: bootstrap venv stdlib aislado + `unittest` del producto en él). RTM **COMPLETE 3/3**
  (REQ-F-001←s00, REQ-F-002←s01, REQ-F-003←s02). `product-run` PASS; **M0–M8 verdes** (m06 clean_runner
  re-derivó el venv en un clon hermético; m08 capstone corre s02); `ci --rederive` **3/3 `proof_sha==pineado`**
  (re-pin; s00/s01 INTACTOS). ASF **intacto** (pin 1/1, no lo toqué).
- **Prueba por bloqueo VIVA por CLI** (aislada a s02): corromper el test del producto a un valor que el
  producto sano NO devuelve → s00/s01 **VERDES** pero **`gate s02: SHUT`** (`product_unittest FAIL`), RTM **2/3**
  (REQ-F-003 UNSATISFIED) — sólo el toolchain del producto ve el rojo. Y corromper el producto (greet) → s00 SHUT.
- **Veredicto**: suite **364** (era 354); `meta check` verde tras refrescar la proyección; árbol limpio.
- **Diferido honesto (no agujero de C3)**: el dummy usa venv stdlib (offline/portable); el dep-install real con
  red (`uv sync`/`npm ci`) es el MISMO seam con otra data → F1/F2. El 2º dominio en suite tiene guard skipif
  (node en dev); el núcleo Python nunca skipea.

## Criterio de cierre (demostrable, no narrable)
1. Un proof_check `product_env` corre el proof DEL producto en su propio toolchain, en `cwd=workdir`, con env
   scrubbed; exit 0 sii bootstrap+proof exit 0. Reproducible en la suite (motor + seed + gate reales).
2. **Aislamiento real (DES-8)**: `import metafactory` FALLA dentro de product_env (PYTHONPATH scrubbed) — no
   es cosmético; el producto no aprueba con el toolchain de la fábrica.
3. **Prueba por bloqueo**: producto roto → el proof del producto sale ≠0 → estación SHUT; bootstrap roto →
   SHUT (el proof ni corre). Viva por CLI en el dummy (corromper el producto → s02 SHUT) + en la suite.
4. **Tech-agnóstico / 2º dominio (principio #6)**: el MISMO kind corre un toolchain **node** (no-Python) sin
   una rama por-tech en el sustrato; guard ADR-012: cero nombre de tech en `src/`.
5. Dummy = línea de 3 estaciones: `product-run` PASS, `ci --rederive` 3/3 `proof_sha==pineado` (re-pin).
   Suite verde, `meta check` verde, árbol limpio.
