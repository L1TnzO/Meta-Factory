<!-- meta:doc sha=82487f25e44961bb7a317ec5114a920021290f18 updated=2026-07-03T02:49Z -->
# Incremento HARNESS-FAST-GATE

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-03T02:49Z) (creado 2026-07-02T20:49Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> INC-2 del plan FIJO N=7 de `COST-DOWN` (biblia `work/COST-DOWN-DIRECTION-INCREMENT.md` §4.INC-2). COLUMNA
> (trust-chain) → se escribe y revisa con ojos propios (SELF-IMPROVEMENT §3); no se delega.

## Objetivo
Slots cortos y verificación hermética: partir el gate del slot en iteración-rápida/aceptación-pesada,
hacer el `stop_proof` del meta hermético (nunca re-corre infra pesada al cierre; confía en el pin del clon
limpio si el toolchain local driftó), y cerrar la clase de incidente JDK-vanish con `tools/toolchain.sh`.

## Contrato (S1 — el diseño como DATA, revisado con ojos propios)
- **(a) schema del slot manifest** (`seed/delegation.py`, fuente única; accessor re-exporta):
  `MANIFEST_REQUIRED_KEYS` += `iteration_gate_cmd` (rápido, cada retry) y `acceptance_gate_cmd` (pesado, 1× al
  final) — reemplaza al `gate_cmd` único; un manifest sin AMBOS → `manifest_problems` != [] (rojo). El
  veredicto `status: green` sobre un slot con `acceptance_gate_cmd` exige `acceptance_exit_code == 0`.
- **(d) ley de tamaño de slot (D23)**: `iteration_budget_s` ∈ (0, `ITERATION_BUDGET_MAX_S`=15]; `max_wall_s`
  ∈ (0, `SLOT_WALL_MAX_S`=1800]; `token_budget` int>0 — DECLARADOS, validados en `manifest_problems`.
- **(e) selección mínima de tests por blast-radius (D25)**: `affected_tests(root, allow_globs)` → los
  `tests/test_*.py` cuyo nombre se relaciona con lo que el slot escribe (determinista, 0 deps; el pleno por
  dep-graph es INC-4). Alimenta el `iteration_gate_cmd`.
- **(b) `stop_proof` meta HERMÉTICO** (`.claude/hooks/stop_proof.py`, meta-only — el del template ya recompone
  del pin, no re-ejecuta): `verify --rerun` verde → cierra; rojo → fallback `verify/hermetic.pin_trust(root)`:
  confía en el pin SOLO si (1) la activa recompone verde (pin limpio válido) Y (2) el toolchain local no puede
  re-verificar ese proof (probe). Si confía → no bloquea (nota hermética); si no → bloquea (fallo real).
- **(c) `tools/toolchain.sh`**: `probe` (exit 0 ⟺ hay `javac` 21 alcanzable) · `ensure` (localiza un JDK 21 con
  compilador: `JAVA_HOME` válido → dirs conocidos → descarga adoptium cacheada; imprime `export JAVA_HOME=…`).
  El gate lo `source`ea para tener `JAVA_HOME` (mata la clase JDK-vanish donde el toolchain SÍ hace falta).
- **Bonus obligatorio:** des-diferir el cierre formal de `FSK-MUTABLE-WHEN` — `ci --rederive --all-products` == pin 4/4.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | (a)+(d)+(e) `seed/delegation.py` + accessor + diente two-sided en `tests/test_delegation.py` | ✅ |
| 2 | (b) `verify/hermetic.py` + `stop_proof` meta hermético + diente `tests/test_hermetic.py` | ✅ |
| 3 | (c) `tools/toolchain.sh` (probe/ensure) | ✅ |
| 4 | re-materializar columna 5 fábricas (`seed/delegation.py`) → `column_parity` verde; skill/brain a 2-gates | ✅ |
| 5 | bonus: re-pin FSK `ci --rederive --all-products` == pin 4/4 (toolchain garantiza JDK 21) | ✅ |

### Evidencia Fase 5 (bonus FSK-MUTABLE-WHEN des-diferido)
`tools/toolchain.sh ensure` resolvió JDK 21 (javac 21.0.10) → gradle+docker corrieron. El único drift era
`s5` (ganó el check `mutability_enforced`): re-derivé cada no-adoptante foreground (s5 verde, sha nuevo
`bbb840dd`) → `meta pin` en `base`/`assets`/`helpdesk` (diff s5-only); `snipeit` ya correcto. Confirmación
independiente: **`ci --rederive --all-products` == pin 4/4** (base 12/12·assets 11/11·helpdesk 11/11·
snipeit 11/11). `FSK-MUTABLE-WHEN` cerrado formalmente. Nota de proceso: el 1er intento en background chocó
con el turn-close (race en `.proof/active.json`) → los builds pesados de fábrica van FOREGROUND (s9/s11 usan
puertos fijos + docker). El `stop_proof` hermético hizo su trabajo: NO enmascaró el `s5` rojo transitorio.

## Evidencia (Fases 1–4)
- Suite `tests/` = **796 passed** (incl. +12 dientes nuevos: split-gate requerido · budgets D23 · acceptance-green · `affected_tests` · pin-trust two-sided).
- `meta check` = **17/17** (compile·docs·projection·isolation·generality·quality·pbt·security·deferred·benchmark·dial·**column_parity**·least_priv·roles·state_snapshot·state_fidelity·suite).
- `column_parity` re-verde tras re-materializar `seed/delegation.py` en las 5 fábricas (byte-idénticas).
- `tools/toolchain.sh`: `probe` exit 1 con JAVA_HOME vacío (drift detectado) · `path`/`ensure` resuelven JDK 21 (javac 21.0.10) → `export JAVA_HOME`.

## Criterio de cierre (demostrable, no narrable)
1. `manifest_problems` de un manifest sin `iteration_gate_cmd` → no vacío (rojo); con ambos gates + budgets válidos → [].
2. `verdict_ok` rechaza un green sin `acceptance_exit_code==0` en un slot con acceptance gate.
3. `pin_trust`: pin verde + toolchain no-disponible → confía (no bloquea); pin verde + toolchain disponible → no confía; pin rojo → no confía.
4. `tools/toolchain.sh probe` distingue javac-21-presente/ausente; `ensure` exporta un `JAVA_HOME` con `javac` 21.
5. Suite `tests/` verde · `meta check` verde (incl. `column_parity` tras re-materializar) · `ci --rederive --all-products` == pin (4/4).
