<!-- meta:doc sha=2988c8deb7d6307f5c2445e78658763ac697095d updated=2026-06-15T19:45Z -->
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
| 1 | Helper `verify/checks/product_env.py` (orquesta bootstrap→proof, env scrubbed) + kind `product_env` en el registry + guard ADR-012 (cero tech en el sustrato) + `tests/test_product_env.py` (helper aislado: pasa, bloquea-en-rojo, bloquea-si-bootstrap-falla, `import metafactory` aislado, workdir ausente→rojo; 2º dominio node por principio #6; e2e por el motor real: estación product_env gatea, corromper→SHUT) | ⏳ |
| 2 | Dummy → línea de **3 estaciones**: s00 también renderiza el test del producto; s02 nueva = proof `product_env` (venv stdlib aislado corriendo el unittest del producto) + REQ-F-003 (verified_by) + sync `specs/dummy` ↔ `factories/dummy` + re-materializar (m02) + re-pin. Prueba VIVA por CLI: `product-run` PASS 3/3, `ci --rederive` 3/3, corromper el producto → s02 SHUT | ⏳ |
| 3 | Docs (STATE/ROADMAP/LOG + esta evidencia) + cierre | ⏳ |

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
