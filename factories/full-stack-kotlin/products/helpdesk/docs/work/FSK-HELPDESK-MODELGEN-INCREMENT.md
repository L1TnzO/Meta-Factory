<!-- meta:doc sha=4068628e903b53cf5c45a93072c11db42c0e02b5 updated=2026-07-10T16:13Z -->
# Incremento FSK-HELPDESK-MODELGEN

> **Doc de gobierno.** Nivel **product-instance** (`products/helpdesk`, ADR-016). Estado: **ABIERTO**
> (creado 2026-07-08T21:28Z, retomado 2026-07-10 sesión S2 Sonnet). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Adoptar el modo **model-nativo DURABLE (ADR-024)** en `helpdesk`: activar `frontend_surface: model-native`
sobre la superficie ganadora del experimento A/B (`products/helpdesk/frontend/app.{ts,css}`, ya tracked
desde el checkpoint `9a5d54e`, byte-idéntica al build aceptado — sha `46c53c7…`/`b3328a6…`), y dejar
**escrita** la respuesta a la pregunta comunitaria obligada de ADR-023 §2 que el A/B nunca hizo
explícita (cierra el gap G2 de la auditoría 2026-07-10, `HONEST-STATE.md`).

Es la adopción MÁS BARATA posible: NO requiere un slot LLM nuevo (la superficie ya existe y ya pasó
`design_floor` en verde — de-riskeado por `FSK-DESIGNFLOOR-DERISK`, que corrió el mismo mecanismo con el
mismo flag y revirtió). Este increment sólo hace DURABLE lo que ese de-risk probó transitorio.

## Diseño (la pieza comunitaria — G2, la pregunta que faltaba)
La pregunta obligada de `design-primitives` paso 3 («¿qué pieza ya validó la comunidad?») es hoy
meta-only (alcance = diseño de FÁBRICAS). `product.yml` no tiene campo estructurado para piezas
comunitarias — ese gap de infraestructura queda abierto (HONEST-STATE, no se inventa un schema nuevo acá
por juicio: es una decisión de diseño de columna, S1). Lo que SÍ hace este increment es responder la
pregunta en prosa, retroactivamente, para la superficie ya elegida:

- **Pieza comunitaria elegida**: TypeScript vanilla, sin framework de UI (ni React/Vue/Svelte ni una
  librería de manejo de estado). El patrón es DOM directo (`document.createElement`/`replaceChildren`)
  data-driven desde el spec efectivo.
- **Por qué**: el mismo juicio que ya se aplicó (sin escribirlo) en snipeit — un renderer genérico de
  ~700 LOC para un CRUD de 5-19 entidades no justifica el costo de adopción de un framework (bundle,
  build-step, curva de dependencias) cuando el contrato funcional (`browser_check.ts`) es selectores DOM
  planos. La "pieza validada por la comunidad" es el LENGUAJE + la plataforma (TS + DOM API estándar),
  no una librería de terceros — decisión legítima de ADR-023 §2 (community-fixed-as-data no exige SIEMPRE
  una librería externa; puede fijar "sin librería" cuando el dominio no lo justifica).
- Queda escrito también en `products/helpdesk/product.yml` (comentario junto al flag).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Verificar sha-identidad de la superficie tracked contra el build A/B aceptado | ✅ |
| 2 | Activar `frontend_surface: model-native` + escribir la respuesta comunitaria (product.yml + este doc) | ✅ |
| 3 | `eval "$(bash tools/toolchain.sh ensure)"` + `meta ci --rederive full-stack-kotlin/helpdesk` en árbol limpio (foreground) → confirmar 5 checks, `frontend_design_floor` exit 0, RE-PIN esperado | ✅ |
| 4 | `meta ci --rederive full-stack-kotlin/assets` == pin existente (no-regresión del no-adoptante) | ✅ |
| 5 | `meta check` verde + cierre (`meta increment close`) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `products/helpdesk/frontend/app.{ts,css}` TRACKED + `frontend_surface: model-native` en `product.yml`
   (ya cumplido — la superficie es sha-idéntica al build A/B aceptado, verificado con `sha256sum`).
2. `meta ci --rederive full-stack-kotlin/helpdesk` en árbol limpio: 5 checks corren, `frontend_design_floor`
   sale `exit 0`, helpdesk queda RE-PINEADO (esperado — es adoptante, no byte-neutral).
3. `meta ci --rederive full-stack-kotlin/assets` == pin existente (no-regresión del no-adoptante).
4. `git diff codegen/ src/metafactory/ seed/ factory.spec.yml stations/ == 0` (el producto no toca
   fábrica ni sustrato, ADR-012).
5. La respuesta comunitaria (G2) queda escrita en este doc + `product.yml` — no en la cabeza de nadie.

## §Evidencia
**Resultado: VERDE.** Segunda adopción durable, la más barata posible (cero slot LLM — la superficie ya
existía y ya había pasado `design_floor` de-riskeada).

1. **Sha-identidad** ✅: `sha256sum` de `products/helpdesk/frontend/app.ts`/`app.css` tracked =
   `46c53c732d4889e50fddd76fc60fb3d45ed616b2f905442509aab52a036e5d99` /
   `b3328a6a24115aa533b663ede561ed3ccf3844c8da8b0b2fec008e3beac75b1b` — idéntico al registrado en
   `FSK-MODELGEN-DURABLE-INCREMENT.md §Evidencia` (build A/B aceptado).
2. **`ci --rederive full-stack-kotlin/helpdesk`** (árbol limpio, foreground): mismatch de pin esperado
   (`10/11 == pineado`, `s9` cambió por el check nuevo) → `.proof/s9.json` real: `passed: true`, **5
   checks**, `frontend_design_floor: exit 0` (los 4 previos también `exit 0`). `meta pin --factory
   full-stack-kotlin --product helpdesk --verify` → **PASS, 11/11 proof_sha == nuevo pin** (re-derivación
   independiente post-pin).
3. **No-regresión `assets`** ✅: `ci --rederive full-stack-kotlin/assets` → **PASS, 11/11 == pin
   existente** (byte-neutral, no-adoptante).
4. **Cero drift de fábrica/sustrato** ✅: `git diff --stat` sobre `codegen/ src/metafactory/ seed/
   factory.spec.yml stations/` (todos de la fábrica) = vacío antes de cualquier cambio de este increment.
5. **`meta check`** ✅: 20/20 (el único rojo intermedio, `docs-consistency` por `STATE.md` de fábrica
   stale, se cerró re-sellando `factories/full-stack-kotlin/docs/STATE.md §Ahora` con este episodio).
6. **Respuesta comunitaria (G2)** ✅: escrita en §Diseño (arriba) + comentario en `product.yml` — TS
   vanilla sin framework, juicio explícito con motivo, no un gap de infraestructura sin respuesta.

### Nota honesta — lo que este increment NO cierra
El campo estructurado de comunidad en `product.yml` (que `design-primitives` baje de meta-only a
product-level) sigue sin existir — es una decisión de columna (S1, requiere ADR/schema). Este increment
cierra el TRIGGER concreto de G2 (dejar la respuesta escrita para la próxima superficie que se diseñe),
no la infraestructura completa. Queda como residual honesto en `HONEST-STATE.md` si se decide construirla.
