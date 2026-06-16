<!-- meta:doc sha=d9129a8c316048007646bf626cbaf48dd864486c updated=2026-06-16T00:22Z -->
# Incremento D1-FULL-COLUMN

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-15T20:50Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
La fábrica generada hereda la **columna anti-sello-de-goma COMPLETA** (no sólo el Cerrojo 1): los
Cerrojos 2 (`commit_guard` recompute) y 3 (`stop_proof` re-corre la activa) como hooks **autocontenidos
en el seed heredado** (cero `metafactory.*`), más un `external_ci` por-fábrica. *Gate*: la fábrica
generada, en clon limpio, **bloquea el sello de goma SOLA** (corromper un veredicto → su propia columna
lo tira a rojo).

## Diseño (decisiones, ojos propios)
- **Autocontención por el seed heredado.** Los hooks cargan `seed/verifier.py` por path (como
  `column_selftest`) y usan `gate_recompute_ok`. El seed **NO se toca** (trust root congelado: sin
  re-auditoría R3, sin re-pin).
- **Los dos locks locales = recompute seed-only, en dos bordes.** `commit_guard` recomputa la activa en
  `git commit` (C2); `stop_proof` recomputa la activa al **cierre del turno** (C3 = "forzar el recómputo
  al cierre", la razón exacta del C3 en `column.md`). Mismo recompute, distinta superficie de fraude
  (commitear un veredicto corrupto vs. cerrar el turno con la activa tampereada sin commitear).
  **Decisión (ojos propios):** NO re-ejecuto los argv guardados en el proof aunque estén resueltos —
  algunos invocan `metafactory.*` (`artifact_contains`/`product_env`), así que re-ejecutar al cierre
  brickearía una sesión interactiva de la fábrica (cada turno reconstruiría un venv / fallaría el import
  del sustrato → rojo fail-safe sobre trabajo legítimo). La **re-ejecución** que atrapa el *artefacto
  rancio*/producto roto sube al `external_ci` por-fábrica (clon limpio que instala el toolchain), tal cual
  `column.md` lo coloca POR ENCIMA de los tres locks locales. D1 entonces atrapa AMBAS clases: tamper
  (locks locales, seed-only) + rancio/roto (external_ci re-derivado).
- **Puntero activo local.** El runner escribe `active.json` TAMBIÉN en el root de la fábrica (hoy sólo en
  el meta-root) para que su columna encuentre la estación activa. Cambio en sustrato (`engine/runner.py`),
  no en seed.
- **Alcance honesto de "cadencia":** `gate_guard` (orden de la línea) es concern del *meta* (el engine
  gatea la línea; la fábrica no corre `meta station`). `increment_guard`/cadencia exige el lifecycle de
  incrementos que la fábrica aún no tiene cableado → **DIFERIDO** (aid de proceso, no frontera de
  seguridad, ADR-010 addendum). D1 hornea los **Cerrojos de seguridad** (1/2/3) con dientes.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Hooks heredados `commit_guard` (C2, recompute en commit) + `stop_proof` (C3, recompute al cierre) autocontenidos + `active.json` local + wiring `settings.json` del template; `test_column_full` a nivel HOOK | ✅ a7443d9 |
| 2 | Capstone `column_full` (check que invoca los hooks heredados en clon hermético → exit 2; negativo-del-negativo) cableado a M1; sombras I-12 en los agents (writer→commit_guard/stop_proof) ⇒ `agent_shadow`/M7 exige la columna completa | ✅ 633b87d |
| 3 | `external_ci` por-fábrica (`{{slug}}`); regenerar dummy + ASF con la columna completa (pin intacto); capstone vivo por CLI (corromper veredicto → la columna de la fábrica bloquea); docs/cierre | ✅ d448aa5·788a695·788a695 |

## Evidencia (re-derivable, no narrable)
- **Columna heredada autocontenida (criterios 1·2):** dummy lleva `commit_guard.py`+`stop_proof.py`+
  `proof_protect.py` cableados (`.claude/settings.json`), cero `metafactory.*` (verificado por AST en
  `test_column_full`). `meta station m01 --factory dummy` → gates `seed_present·column_blocks·column_wired`
  verdes. `test_column_full` (19 tests): proof tampereado (passed pegado / proof_sha editado) → commit_guard
  exit 2 **y** stop_proof exit 2; verde-limpio → 0/0; el check `column_full` cae a rojo si falta un hook /
  si un hook siempre permite / si siempre bloquea (prueba de DOS lados, no decorativa); pasa contra la dummy real.
- **agent_shadow (criterio 3):** M7 verde con las sombras nuevas (writer→commit_guard/stop_proof) — exige
  que existan y estén cableadas; el negativo (borrar una sombra → rojo) lo trae `agent_shadow` de fábrica.
- **external_ci por-fábrica (criterio 4):** `factories/dummy/seed/external_ci.yml` → `name: dummy-external-ci`,
  `meta ci --rederive --factory dummy`; el de ASF → `agent-systems-factory`. Ya no es el del meta por default.
- **Línea + dos verificadores (criterio 5):** dummy M0–M8 PASS · `product-run` PASS · `ci --rederive` 3/3
  (pin intacto: la columna L4 no toca la línea de producto) · `meta check` 5/5 (suite 394). ASF: M0–M8 PASS ·
  `ci --rederive` 1/1 (intacto) — y AHORA también hereda la columna completa (principio #4).
- **Capstone VIVO por CLI (criterio 6):** clon limpio de la dummy en `/tmp` (sin la columna del Meta-Factory) →
  verde-limpio: commit_guard 0 / stop_proof 0; corromper `s02.json` (passed=true sobre check exit≠0) → 2/2;
  `proof_sha` editado → 2. La fábrica generada bloquea el sello de goma SOLA, con su propio seed.

## Residual honesto (declarado, no oculto)
- **Lock 3 local = recompute, no re-ejecución** (ver Diseño): el *artefacto rancio* lo atrapa el `external_ci`
  por-fábrica (clon limpio con toolchain), no el `stop_proof` local. Es la capa que `column.md` pone por encima.
- **`increment_guard`/cadencia NO heredados:** la fábrica no tiene el lifecycle de incrementos cableado
  (eso toca D2, generación de harness). Es aid de proceso, no Cerrojo de seguridad (ADR-010 addendum).
- **`gate_guard` del meta sobre-matchea texto:** parsea `station X --factory Y` en CUALQUIER comando (p.ej.
  un mensaje de commit que lo nombra) → falso positivo. Es del harness del *meta*, no de la columna heredada;
  follow-up fuera de D1 (acotar a invocaciones reales de `meta station`).

## Criterio de cierre (demostrable, no narrable)
1. La dummy generada lleva `commit_guard.py` + `stop_proof.py` heredados, **cableados** en su
   `settings.json`, y autocontenidos (cero import de `metafactory.*`).
2. **Prueba por bloqueo a nivel HOOK** (`test_column_full` + capstone `column_full`): contra la columna
   heredada, un proof con `passed`/`proof_sha` tampereado activo → `commit_guard` exit 2 (commit) **y**
   `stop_proof` exit 2 (cierre); un proof verde-limpio → ambos exit 0 (no sobre-bloquea). El *artefacto
   rancio* (proof intacto, artefacto corrompido) lo atrapa el `external_ci` re-derivado (criterio 4).
3. `agent_shadow` (M7) exige los hooks nuevos presentes+cableados (borrar uno → rojo).
4. `external_ci` de la dummy re-deriva la **dummy** (`--factory dummy`), no el meta.
5. Línea M0–M8 + `product-run` + `ci --rederive` 3/3 + `meta check` verdes tras regenerar; ASF intacto.
6. **Capstone vivo por CLI**: en la dummy regenerada, corromper un veredicto a mano → su propia
   `commit_guard`/`stop_proof` bloquea (exit 2), sin la columna del Meta-Factory.
