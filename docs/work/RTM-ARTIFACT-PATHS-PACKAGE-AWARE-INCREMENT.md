<!-- meta:doc sha=609295f458b5a12736f478a0ebba78a7b818ffa7 updated=2026-06-21T03:16Z -->
# Incremento RTM-ARTIFACT-PATHS-PACKAGE-AWARE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-21T03:05Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
El RTM (`verify.rtm.build_tree`) renderiza el path de `cap.artifact` con la subst del spec (igual que ya
hace con stations/builds) → un `{{package_name}}` se resuelve POR INSTANCIA. Completa el lifecycle 1:N para
fábricas cuyo layout anida el fuente bajo un directorio con el nombre del paquete.

## Contexto (por qué el sustrato, no la fábrica)
El primer producto FSK con paquete ≠ `webapp` (Snipe-IT → `snipeit`) expuso el hueco: las capabilities de
`factory.spec.yml` declaran su artefacto en `src/main/kotlin/<pkg>/…`, pero `build_tree` leía `cap.artifact`
**verbatim** → buscaba `…/webapp/DbRoundTrip.kt`, ausente para `snipeit` → 8 requisitos UNSATISFIED pese a la
línea verde. Las otras fábricas 1:N (iot `fleetgw`, full-stack `taskapp`) NO lo exponen: su layout (Go/TS) no
anida el fuente bajo un dir con el nombre del paquete, así que sus paths de artefacto son agnósticos al
paquete. Por eso es un hueco del SUSTRATO (la interpretación del spec), no de la fábrica — y el fix es GENERAL
(renderiza cualquier `{{var}}`, NO nombra producto ni tech; sin placeholders es no-op). Lo sanciona el gate
`generality` de `meta check` (verde). El cambio es 1 línea efectiva en `verify/rtm.py` + el import de `render_text`.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `build_tree` renderiza `cap.artifact` con `render_text(…, spec.subst)`. | ✅ (2026-06-21) |

## Evidencia
- `meta rtm --factory full-stack-kotlin --product snipeit`: **18/19 SATISFIED** (los 8 paths antes ausentes
  ahora resuelven a `…/snipeit/…` y existen; el único UNSATISFIED es REQ-F-007 = s6 deferral keyless VISIBLE).
- `meta check` **6/6** (incl. `generality` ⇒ el sustrato no nombra producto/tech; `suite` ⇒ rtm intacto).
- `meta ci --rederive --factory full-stack-kotlin --all-products` **3/3 == pin** (default 11/11 · assets 10/10
  · snipeit 10/10): el cambio no regresiona ningún producto (default `webapp` renderiza a sí mismo).

## Criterio de cierre (demostrable, no narrable)
1. snipeit RTM = sólo deferrals VISIBLES (s6); default/assets RTM intactos.
2. `meta check` 6/6 (`generality` verde = anti-overfit OK pese a `git diff src/ ≠ 0`).
3. `ci --rederive --all-products` == pin para las 3 instancias FSK.
