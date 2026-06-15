<!-- meta:doc sha=2bfcf454a8820b91bd654271f67e11760a573040 updated=2026-06-15T17:52Z -->
# ADR-013 — Generación como slot orquestado: el sustrato orquesta y verifica, no genera

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-15T18:00Z |
| Decide | el orquestador (sesión C1), bajo el mandato del ingeniero (ADR-011/012) |
| Implementa | ADR-011 (100% generado), ADR-012 (primitivas no herramientas), I-3 (frontera del determinismo) |
| Referencia | `work/ROADMAP.md §Fase C`, `reference/PRIMITIVES.md`, ADR-002 (columna) |

## Contexto

Fase A/B dejaron la fuente de verdad (spec v2) describiendo cualquier fábrica y la planificación SDD
eligiendo la tech por primitiva (M0 rehúsa el diseño incompleto, B2). Faltaba el **motor de build**: cómo
la línea M0–M8 produce los artefactos a partir del blueprint design-complete. El sustrato ya sabía
*renderizar* plantillas (`render`/`render_tree`): substitución `{{}}` determinista cuya LÓGICA vive en
`src/metafactory/`. Eso alcanza para el chasis, pero como modelo general de generación viola dos cosas:
mete determinismo en el **contenido** (I-3) y, si se extendiera a "un backend por stack", hornearía
**herramientas** en la plataforma (el error ya rechazado en ADR-012).

## Decisión

La generación es un **slot creativo ORQUESTADO**, materializado por la acción de build `generate`
(`codegen/renderer.py::_generate`). El contrato:

1. El sustrato **escribe el brief** (la rebanada del blueprint contra la que se genera) — INPUT derivado
   determinísticamente de los datos del spec, NO el artefacto.
2. El sustrato **corre el generador DECLARADO EN DATO** (`via`, una argv). El sustrato **no nombra ninguna
   tech**: `via` puede ser un scaffolder determinista, un renderizador, o `claude -p "<brief>"`. El generador
   es el ÚNICO que escribe `dest`.
3. El sustrato **no escribe el artefacto NI el veredicto**. Si el generador falla, no arranca o no produce
   nada, `dest` queda ausente/incorrecto y la **columna** (los `checks` de la estación, vía `seed/verifier.py`)
   computa el rojo honesto. El veredicto sigue teniéndolo un único escritor (Cerrojo 1).
4. Cada corrida empieza con `dest` ausente (salvo `skip_if_exists`): un generador que falla NUNCA pasa sobre
   un artefacto rancio — el gate refleja exactamente lo que ESTA generación produjo (invariante no-fake).

El generador recibe su contrato por entorno: `METAFACTORY_BRIEF` (path), `METAFACTORY_DEST` (path a escribir),
`METAFACTORY_ROOT` (raíz de la fábrica); la argv `via` también recibe substitución `{{var}}`.

## Consecuencias

- **El determinismo envuelve, no genera** (I-3): vive en la columna (verificación) y en el brief (contrato),
  nunca en el contenido. "Envolver a Claude Code, no reemplazarlo" (VISION §6) se vuelve mecanismo.
- **Generalidad por construcción** (ADR-012, principio #6): el seam no tiene rama por-tech; el MISMO
  `generate` corre generadores radicalmente distintos (emitir Python ↔ emitir TS) sin tocar el sustrato.
  Un test lo prueba con ≥2 generadores; el guard de aislamiento prohíbe tokens de tech de generación en `src/`.
- **`render` vs `generate`**: `render` (lógica de generación en el sustrato) queda para el **chasis** trivial
  y parametrizable; `generate` (lógica fuera, en el generador-dato) es el modelo para el **producto** y todo
  contenido no-templatizable. La frontera I-5 (`skip_if_exists`) aplica a ambos.
- **Residual honesto (declared-deferred, no agujero de C1)**: el gate de C1 usa un generador determinista
  de prueba para que la prueba-por-bloqueo y la re-derivación de dos-verificadores sean reproducibles. Cablear
  un `via: [claude, -p, …]` VIVO es el MISMO seam con otra data; se ejercita para código de producto real en F1.
  Lo que C1 prueba —y cierra— es el seam + los dientes de la columna sobre su output.

## Rechazado

- "Backends de generación deterministas por stack en el sustrato" (ya rechazado en ADR-012): hornea
  herramientas y mete determinismo en la generación. `generate` lo evita: la tech es siempre `via` (dato).
- "Que `generate` decida pass/fail (raise si el generador falla)": rompería el único-escritor-de-veredictos
  (Cerrojo 1). La generación es best-effort; la columna es el árbitro.
