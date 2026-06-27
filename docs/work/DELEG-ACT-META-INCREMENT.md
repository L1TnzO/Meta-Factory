<!-- meta:doc sha=868b38c9796149537a128f3e44b477c4b5203e70 updated=2026-06-27T20:20Z -->
# Incremento DELEG-ACT-META

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-27T20:20Z) (creado 2026-06-27T20:12Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Que el agente principal del meta **delegue NATURALMENTE — sin pedirlo en cada prompt**: la regla permanente de
routing en `CLAUDE.md` (carga en cada sesión, no reemplaza el system-prompt) + las `description` afiladas con
triggers proactivos + el alias manual para builds pesados. Fase A de `DELEGATION-ACTIVATION`; B ya MIDE
(`work/DELEG-MEASURE-INCREMENT.md`), así que A es verificable. Ver
`work/DELEGATION-ACTIVATION-DIRECTION-INCREMENT.md §4 Fase A`.

## Contexto
La topología verificar-no-revisar (Fase 2 SOTA) está CONSTRUIDA pero dormida: `settings.json` tiene `agent:
NONE`, `CLAUDE.md` no tenía regla de routing, y las 4 `description` describían el rol pero no DISPARABAN
auto-delegación. La pieza que faltaba NO es topología — es **activación**: que el principal SIEMPRE sepa
delegar sin que se lo pidan. Decisión clave (§5.1 del DIRECTION): regla `CLAUDE.md` + descriptions afiladas +
`--agent orchestrator` manual, **NO** un `agent` default global (reemplazaría el system-prompt base en cada
sesión casual → fricción).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| A1 | Regla permanente de delegación en `CLAUDE.md §Reglas` (español — prosa de gobierno de fase-viva, cita ADR-017): rutear slots acotados-con-gate al `generator`, lecturas masivas al `verifier`/`Explore`, contexto de Opus chico, + la excepción trust-chain (la COLUMNA se escribe con ojos propios). | ✅ |
| A2 | `description` afiladas (inglés, ADR-017): `generator` → `MUST BE USED for any bounded code slot that has a deterministic gate`; `verifier` → `Use PROACTIVELY whenever you would otherwise load a large artifact`. `reviewer` y `orchestrator` se dejan **deliberadamente NO-proactivos** (ver Decisión abajo). | ✅ |
| A3 | Alias manual `claude --agent orchestrator` para builds pesados documentado en la misma regla de `CLAUDE.md` — con la advertencia explícita de NO poner `agent` default global. | ✅ |

## Decisión — por qué SÓLO `generator`+`verifier` son proactivos (no los 4)
El eje de auto-delegación es el `description` como **trigger del router implícito**. Hacerlo proactivo es
correcto SÓLO donde el disparo natural debe ocurrir sin pedirlo:
- **`generator`** (escribe bulk con gate) y **`verifier`** (lee bulk) → SÍ proactivos: son el camino por
  defecto del bulk, el corazón de "natural sin pedirlo".
- **`reviewer`** → NO proactivo a propósito: su disparo ES la excepción (red persistente / path de seguridad /
  arquitectura novedosa). Un trigger proactivo lo convertiría en un paso de rutina sobre trabajo ya verde →
  rompe la calibración (ADR-017 §2). El DIRECTION lo dice textual: *"mantener el 'exception, not routine'"*.
- **`orchestrator`** → NO proactivo: es el agente de SESIÓN (`--agent orchestrator`), el cerebro mismo, no un
  subagente que el hilo principal deba spawnear. Un trigger proactivo invitaría a spawnear un segundo cerebro
  (ambigüedad de ruteo). Su `description` ya describe correctamente el uso como session-agent.

## Criterio de cierre (demostrable, no narrable)
1. ✅ `CLAUDE.md` tiene la regla de delegación por defecto (A1) + el alias manual + la advertencia anti-`agent`-
   global (A3), en `§Reglas de esta fase`.
2. ✅ `generator.md` y `verifier.md` llevan triggers proactivos (`MUST BE USED` / `Use PROACTIVELY`); los 4
   frontmatter parsean YAML válido (registran limpio al próximo restart). `reviewer`/`orchestrator` intactos.
3. ✅ `meta check` 16/16 sin regresión (la staleness transitoria de STATE al abrir el incremento se resuelve al
   actualizar STATE + commitear junto — ADR-007).

## Nota honesta — la prueba "proactivo sin pedirlo" es inherentemente de PRÓXIMA sesión
Los `description` se cargan al **inicio de sesión**: una edición en disco NO registra hasta reiniciar (docs
oficiales; ya observado en [[sota-redesign-graph-spine]]). Por eso la prueba viva de "el principal rutea un
slot SIN que se lo pidan" se observa en la **siguiente** sesión, vía `meta metrics` (`DELEGACION` sube durante
codegen real). NO se manufactura acá una delegación de adorno: el trabajo de Fase A es **columna** (gobierno +
config de agentes) → se escribe con ojos propios, que es la excepción explícita de la propia regla. El loop
delegación→medición ya quedó probado end-to-end en la Fase B (`DELEG-MEASURE §Evidencia`, dogfood del
`verifier`/Haiku). La regla `CLAUDE.md` SÍ aplica de inmediato (carga en cada sesión).
