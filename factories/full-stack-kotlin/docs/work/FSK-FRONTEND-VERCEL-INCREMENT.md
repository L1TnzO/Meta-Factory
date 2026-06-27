<!-- meta:doc sha=587065826e1be9fb68e9091eda7fbcdc955cc89c updated=2026-06-27T15:48Z -->
# Incremento FSK-FRONTEND-VERCEL — re-skin del frontend al lenguaje "tinta + hairline" (estilo dev-platform)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO** (2026-06-27T15:48Z)
> (creado 2026-06-27T15:32Z). Cerralo con `meta increment close` (gateado: árbol limpio + estación activa
> verde). Editar `factories/full-stack-kotlin/**` no-`.md` (codegen/spec/stations) exige ESTE incremento abierto.
>
> El ingeniero pidió (2026-06-27) seguir con el **diseño del frontend** adoptando un sistema de diseño externo:
> `npx getdesign@latest add vercel` (CLI que instala una guía `DESIGN.md` del lenguaje visual de Vercel — una
> dev-platform: tinta casi-negra sobre lienzo casi-blanco, bordes hairline, sombras apiladas sutiles, sans
> geométrica + mono para etiquetas técnicas, pills/radios chicos). Objetivo: que la app **snipeit** se vea así.

---

## 0. POR QUÉ
El arco frontend (RENDER→ALL-ENTITIES→DETAIL→EDIT→OPERATIONS→DASHBOARD→STYLES) dejó la app funcional y estilada,
pero con una hoja genérica (`--accent #2d6cdf`, azul corporativo). Este incremento **re-skinnea** esa hoja al
lenguaje de diseño de la guía instalada (`docs/reference/DESIGN-VERCEL.md`): paleta tinta `#171717` / lienzo-suave
`#fafafa` / hairline `#ebebeb` / link `#0070f3`, sans geométrica (Inter/Geist con fallback a `system-ui`), **mono**
para las etiquetas de campo (la "voz técnica" de la plataforma), radios 6/8/12px, inputs de 40px, botón submit
"tinta" (relleno `#171717`, texto blanco) y sombras apiladas sutiles + anillo hairline.

Frontend-only, CERO backend de dominio. **DATA-agnóstico (ADR-012)**: la hoja estila SÓLO clases semánticas que el
render emite (`nav`, `form`, `li`, `li[data-id]`, `ul.dashboard`, `dl.detail`/`.field`/`dt`/`dd`), cero nombres de
dominio → el MISMO CSS estila cualquier producto FSK (snipeit·assets·helpdesk). Es un cambio de SUSTRATO general.

**Sin re-pin (igual que FSK-FRONTEND-STYLES)**: `proof_sha` digiere `station_id` + pares `(check, exit)` —NO el
contenido del artefacto—, así que cambiar el valor del CSS y el del diente (960→1200) no toca el pin mientras
`frontend_browser_live` siga verde (exit 0). El diente se mueve, no se borra.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Instalar la guía (`getdesign add vercel`) → `docs/reference/DESIGN-VERCEL.md` (fuente de diseño) | ✅ |
| 2 | Re-skin de `_APP_CSS` (constants.py) al lenguaje tinta+hairline; diente `body max-width` 960→1200 | ✅ |
| 3 | Re-generar **snipeit** por la línea real (s0 re-scaffold → s9 prueba en Chromium que la hoja APLICA) | ✅ |
| 4 | `ci --rederive` == pin · `meta check` verde · screenshot de la app re-skinneada | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `meta product-run --factory full-stack-kotlin --product snipeit` VERDE — incluida la estación s9, cuyo diente
   FSK-FRONTEND-STYLES asevera en un Chromium REAL `getComputedStyle(body).maxWidth == "1200px"` (el nuevo valor;
   != el default UA `none`). Saboteá el `<link>`/`/app.css`/el valor → cae a `none` → SÓLO ese check rojo (AISLADO).
2. `meta ci --rederive --factory full-stack-kotlin --product snipeit` → todos los `proof_sha` == pineado (el
   re-skin NO re-pinea: los exit codes no cambian).
3. `meta check` (gate de fábrica + meta) VERDE — el sustrato sigue limpio, DATA-agnóstico y sin deuda de calidad.
4. Evidencia visual: la app snipeit corre (`tools/dev_run.sh snipeit`) y se ve con el lenguaje nuevo (screenshot).

## Evidencia (2026-06-27)
- **Línea real VERDE** — `meta product-run --factory full-stack-kotlin --product snipeit` → exit 0 (todas las
  estaciones). La estación **s9** recompone verde con sus 4 checks de infra-viva en exit 0, incluido
  `frontend_browser_live`: corrió `browser_check.ts` en un **Chromium REAL** contra AppServer+PG vivos y aseveró
  `getComputedStyle(body).maxWidth == "1200px"` → la hoja re-skinneada **se sirve, se linkea y la aplica el browser**.
- **Sin re-pin (concreto)** — `meta ci --rederive --factory full-stack-kotlin --product snipeit` → exit 0 (todos
  los `proof_sha` == pineado). `git status` tras todo el trabajo: SÓLO 4 archivos fuente/doc tocados, **CERO diff
  en `.proof/`/`pinned_verdict.json`** — el re-skin no movió un solo byte de evidencia pineada (los exit codes no
  cambian → el digest no cambia).
- **`meta check` 16/16 verde** — sustrato limpio: `quality` (constants.py < 2000 LOC), `generality`, `least_priv`,
  `state_snapshot`, `state_fidelity`, `dial`, `benchmark`, … todos ok. El CSS sigue DATA-agnóstico.
- **Evidencia visual** — `tools/dev_run.sh snipeit` levantó la app; capturas de Chromium (home/lista/detalle)
  muestran el lenguaje: lienzo `#fafafa`, botones nav ghost hairline 6px, botón submit "tinta" (`#171717` relleno),
  filas como cards con sombra apilada sutil, y en el detalle las **etiquetas de campo en mono mayúsculas** (la voz
  técnica de la plataforma) con valores en tinta.

> **Reusable**: `proof_sha = sha(station_id + sorted[(check, exit)])` excluye el CONTENIDO del artefacto → cualquier
> cambio puramente cosmético del frontend (valor del CSS + valor del diente del browser_check, mientras quede verde)
> es **byte-neutral al pin**. Mover el diente (960→1200) ≠ borrarlo: sigue siendo una propiedad NO-default (`!= 'none'`).
