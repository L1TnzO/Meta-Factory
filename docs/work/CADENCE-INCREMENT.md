<!-- meta:doc sha=ca4f0a04b2cd46a5956af432a520c3193757edd6 updated=2026-06-14T01:14Z -->
# Incremento CADENCE — disciplina de commit: todo código vive en un incremento; cadencia por fase

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-14T00:55Z — sesión opus-4.8). Cerralo con
> `meta increment close` (gateado: árbol limpio + estación activa verde). Implementa ADR-010.
> Dogfood: este incremento se construye DENTRO de sí mismo (la cadencia se prueba sobre su propia obra).

## Objetivo
Cerrar el #5 de STATE («política de commit fuera de incremento, diseño abierto»). El pecado central del
bootstrap fue **0 commits** en un build largo sin estructura. La cura (reencuadre del ingeniero): no razonar
casos borde dentro/fuera, sino **disolver la frontera — todo cambio de código (no-`.md`) exige un incremento
abierto**; y dentro del incremento, el trabajo probado se commitea antes de avanzar o cerrar. Determinista,
cero-modelo, re-derivable.

## Diseño (dos capas)
- **Capa 1 · Increment-gate**: PreToolUse Write|Edit|MultiEdit bloquea editar no-`.md` bajo el repo si no hay
  incremento abierto (`projection.open_increment`). `.md` siempre permitido (es como se ABRE un incremento).
- **Capa 2 · Cadencia**: deuda = incremento abierto + código no-`.md` sin commitear. Dientes: advance-time
  (`gate_guard`: no avanzás de estación con deuda), close-time (`stop_proof`: no cerrás el turno con trabajo
  PROBADO sin commitear), close-increment (`meta increment close` rehúsa con deuda), surface (`meta check`).
- Bloquea, NO auto-commitea (igual que `commit_guard`): el modelo escribe el mensaje con trailers I-10.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| C1 | `cadence.py` (señal) + `meta increment open/close/status` + `tests/test_cadence.py` | ⏳ |
| C2 | hooks: `increment_guard` nuevo + extender `gate_guard`/`stop_proof` + `settings.json` + tests de bloqueo | ⏳ |
| C3 | surface en `meta check` + `ADR-010` + STATE #5 + LOG + cierre del incremento | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `cadence.debt` True con (incremento+código sin commitear), False al commitear/limpiar, False sin incremento.
2. `increment_guard` bloquea (exit 2) un Edit a `*.py` sin incremento; permite con incremento; permite `*.md` siempre.
3. `gate_guard`/`stop_proof` bloquean (exit 2) con deuda fabricada; pasan (exit 0) sin deuda.
4. `meta increment open` rehúsa si ya hay uno abierto; `meta increment close` rehúsa con deuda.
5. Suite verde (tests de cadencia incluidos); `meta check` 5/5 PASS con el surface de deuda funcionando.
6. Dogfood: el incremento se construyó dentro de sí, commit por fase (C1–C3), cerrado por `meta increment close`.
