<!-- meta:doc sha=98211399e0435b234de70241c5b033ea08f9fdd6 updated=2026-07-07T21:50Z -->
# Incremento STOP-PROOF-PRERUN-TRUST

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-07T21:35Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Que la escotilla hermética de `stop_proof` (Cerrojo 3, ADR-021) pueda DISPARAR de verdad: la decisión
confiar/bloquear sobre el pin se toma **ANTES** de cualquier re-run vivo, porque el re-run sobreescribe el
pin incondicionalmente — el orden viejo auto-corrompía un pin verde legítimo al primer cierre de turno con
toolchain evaporado y dejaba la sesión permanentemente trabada.

## El bug (real, reproducible — encontrado en sesión 2026-07-07)
1. `stop_proof.py` corría `verify --rerun` al cierre de CADA turno. `seed/verifier.py::verify_station`
   **sobreescribe el pin** (`_write_atomic(proof_path(...))`) en toda invocación — no tiene modo dry-run.
2. El subprocess del hook no tiene `javac` en PATH (clase de incidente medida: JDK 21 se evapora entre
   sesiones) → los checks s11 de FSK (`command -v javac` + `./gradlew installDist`) fallan en el bootstrap
   de `infra_up` → falso-rojo… que **clobberea el pin verde** recién verificado (visto en vivo: pin verde
   21:24Z → hook 21:30Z lo pisó con rojo).
3. Recién ENTONCES el hook preguntaba `hermetic.pin_trust()` — que lee el pin… ya pisado por el mismo
   re-run drifteado. `gate_recompute_ok` ve rojo → "a real failure, block". La escotilla diseñada
   exactamente para este caso **no podía disparar nunca**; toda sesión posterior quedaba trabada.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `hermetic.preflight()` — decide trust/block/rerun ANTES del re-run vivo, sin tocar el pin (aterrizó en la sesión anterior; pura adición a `verify/hermetic.py`) | ✅ |
| 2 | `stop_proof.py` usa `preflight` primero; el re-run vivo solo corre cuando el toolchain local puede re-verificar (COLUMNA — escrito y revisado con ojos propios; la sesión anterior fue denegada por el clasificador y escaló al humano, que autorizó) | ✅ |
| 3 | Endurecer el hook contra el cwd-fugado conocido (rutas ancladas a `__file__`, subprocess con `cwd=ROOT`) — misma clase de falso-rojo al cierre | ✅ |
| 4 | Tests de `preflight` (4 nuevos en `tests/test_hermetic.py`, incluido el diente de NO-mutación del pin) + re-verde HONESTO del pin s11 (re-run real con toolchain ensured, no edición) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `preflight` decide sin mutar el pin: `tests/test_hermetic.py` 10/10 (4 nuevos: trust/block/rerun/no-pin,
   con assert de bytes-idénticos sobre el pin en trust y block).
2. El hook real, sobre pin VERDE + toolchain drifteado (el caso que antes se auto-corrompía): toma la rama
   "trust", NO corre el re-run, pin byte-idéntico, y solo bloquea por cadencia ADR-010 (commit pendiente).
3. El hook real, sobre pin ROJO + toolchain drifteado: bloquea en ~0s con razón acotada, sin re-run
   redundante, pin byte-idéntico.
4. El pin s11 de `snipeit` vuelve a verde por re-run REAL (exit 0, gradle+docker), no por edición —
   `.proof/` nunca se toca a mano (Cerrojo 1).
5. Suite completa 959/959 + `meta check` 19/19.

## Evidencia (2026-07-07)
- **Fase 1**: `git diff src/metafactory/verify/hermetic.py` = solo `+preflight()` (30 líneas, pura adición).
- **Fases 2–3**: `.claude/hooks/stop_proof.py` reescrito — `preflight` primero; "trust" saltea el re-run;
  "block" corta sin re-run; "rerun" conserva el comportamiento viejo exacto (equivalencia rama-por-rama
  revisada a mano, incluida la caída `Exception → "rerun"` = comportamiento previo). `ROOT/SRC` anclados a
  `Path(__file__).resolve().parents[2]`; `verify --rerun` con `cwd=ROOT` y `PYTHONPATH` absoluto.
- **Criterio 1**: `PYTHONPATH=src pytest tests/test_hermetic.py -q` → **10 passed**.
- **Criterio 3** (medido con el pin rojo clobbereado aún en disco): `echo '{}' | stop_proof.py` → rc 2,
  razón `pinned proof is not clean-green (failing checks: deploy_smoke, deploy_appserver_live) and the
  local toolchain cannot re-verify`, elapsed 0s, sha256 del pin idéntico antes/después.
- **Criterio 4**: `eval "$(bash tools/toolchain.sh ensure)"` (JDK 21 en `~/.antigravity/...`) +
  `meta verify --rerun` → `VEREDICTO verify s11 — PASS (exit 0)`, 2/2 checks, pin nuevo 21:46Z
  (log `products/snipeit/.proof/logs/s11-2026-07-07T2146Z.log`).
- **Criterio 2** (medido con el pin verde nuevo, hook SIN toolchain): rama "trust" impresa («se salta el
  re-run vivo para no clobberear el pin»), sha256 del pin idéntico, y rc 2 SOLO por cadencia ADR-010
  (gate verde sin commitear) — el backstop correcto, no el bug.
- **Criterio 5**: `pytest tests/ -q` → **959 passed**; `meta check` → 19/19 (el único rojo intermedio fue
  `docs` freshness de FSK STATE, pre-existente del cierre 21:29Z, resuelto con el refresco honesto de
  `factories/full-stack-kotlin/docs/STATE.md`).

## Alcance y no-alcance (honesto)
- La autoridad de re-ejecución sigue donde la columna la puso: el CI externo con clon limpio
  (`hermetic.py` docstring) — este incremento NO hace que el hook re-ejecute gates pesados con toolchain
  ensured al cierre de turno (eso desharía HARNESS-FAST-GATE).
- `verify_station` conserva su semántica de siempre-escribe (correcta para su rol de verificador); el
  no-clobber se resuelve en el CALLER (el hook decide antes de invocarlo), no agregando un dry-run al seed.
- Residual conocido que NO se toca acá: `session_start`/`doc_stamp`/`mem_rollup` siguen cwd-relativos
  (memoria `no-cd-subdirs-hook-deadlock`); solo `stop_proof` (el que bloquea el cierre) quedó anclado.
