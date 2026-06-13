<!-- meta:doc sha=65e3945c6848bc2e0a5664c8364b5b22234f7847 updated=2026-06-13T15:33Z -->
# Meta-Factory — la fábrica que fabrica (y mejora) fábricas

> Si llegás nuevo a este repo (humano o modelo): **empezá por `docs/STATE.md`** — es el punto de
> entrada único y el estado actual. Este archivo es solo el mapa.

> **Estado (2026-06-13): BOOTSTRAP EJECUTADO — ya hay código verificado por bloqueo.** El seed
> (`seed/`), la maquinaria (`src/metafactory/`), las meta-estaciones (`stations/`), el template
> (`template/`) y un dummy-fábrica producido (`factories/dummy/`) existen y pasan los 8 criterios de
> cierre. CLI: `./meta check | new | station | product-run | rtm | ci --rederive`. Índice generado
> (no a mano, ADR-009): `INDEX.md`.

## Qué es

Una plataforma que toma una **factory-spec** y emite una **fábrica de grado-producción** (como
Agent_Systems_Factory) ya envuelta en confiabilidad, trazabilidad y economía de contexto. Donde
ASF gira alrededor de un framework de dominio (LangGraph), el Meta-Factory gira alrededor de
**tunear el harness de Claude Code** para construir fábricas. Es el único sistema del ecosistema
que puede mejorarse a sí mismo legítimamente, porque **pertenece a su propia clase de producto**.

## Por qué existe (en una línea)

ASF se fabricó a sí mismo —un error de categoría que dejó su capa meta gobernada por prosa que se
saltea bajo presión—. El Meta-Factory es el punto fijo que lo corrige: cosecha todo el sustrato
determinista que ASF descubrió a los golpes, cierra sus 9 gaps, y vuelve a ASF un producto.

## El mapa de la documentación

| Doc | Qué responde |
| --- | --- |
| [`docs/STATE.md`](docs/STATE.md) | **Empezá acá.** Qué es verdad hoy, agujeros honestos, qué sigue. |
| [`docs/reference/VISION.md`](docs/reference/VISION.md) | El porqué: la tesis, el argumento del punto fijo, los objetivos hechos criterio. |
| [`docs/reference/ARCHITECTURE.md`](docs/reference/ARCHITECTURE.md) | El cómo: 3 niveles, los 13 invariantes, la factory-spec, meta-estaciones M0–M8, stages 0–3. |
| [`docs/reference/ASF-LESSONS.md`](docs/reference/ASF-LESSONS.md) | Lo bueno de ASF (asciende) y los 9 gaps (cerrados por diseño), con citas. |
| [`docs/reference/SELF-IMPROVEMENT.md`](docs/reference/SELF-IMPROVEMENT.md) | Cómo se mejora a sí mismo sin corromper su raíz de confianza (trusting-trust). |
| [`docs/reference/CONTEXT-ECONOMY.md`](docs/reference/CONTEXT-ECONOMY.md) | Cómo mantiene el orquestador limpio: bus de veredictos, delegación, enrutamiento de modelo. |
| [`docs/reference/MEMORY-ARCHITECTURE.md`](docs/reference/MEMORY-ARCHITECTURE.md) | El subsistema de memoria: 3 tiers, disparador de escritura, retrieval medido, y la auditoría del esquema (§8: cobertura/duplicación/gaps). |
| [`docs/reference/OBSERVABILITY-METRICS.md`](docs/reference/OBSERVABILITY-METRICS.md) | Métricas **absolutamente gratis** (cero modelo): qué se captura, dónde se guarda, la vista `meta metrics`. |
| [`docs/reference/HONEST-STATE.md`](docs/reference/HONEST-STATE.md) | **Implementado vs definido, sin maquillaje** (I-13): qué está vivo, qué falta, qué disciplina NO se siguió (docs/commits incrementales), y por qué hay que reiniciar para activar los hooks. |
| [`docs/decisions/`](docs/decisions/) | Los ADR: 001–006 y 009 **Aprobados** (009 = manifiesto content-addressed de docs, git+hook) · 007–008 **Propuestos** (memoria y métricas, pendientes de ratificación). |
| [`docs/work/BOOTSTRAP-INCREMENT.md`](docs/work/BOOTSTRAP-INCREMENT.md) | El primer incremento gobernado: qué construir y el criterio de cierre anti-fachada. |
| [`docs/LOG.md`](docs/LOG.md) | La bitácora episódica (append-only, más nuevo arriba). |

## Convenciones (heredadas de ASF/ADR-021)

- **Marcas de tiempo narrativas**: siempre `YYYY-MM-DDTHH:MMZ` (UTC, al minuto). Git es la autoridad.
- **Tipos de doc = semántica de mutación**: STATE (overwrite), LOG (append), decisions/ (inmutable),
  work/ (por-incremento), reference/ (estable). Actualizar el doc correcto ES parte del trabajo.
- **Fuente cosechada**: `../Agent_Systems_Factory/` — ASF, leído íntegro para extraer su sustrato.
- **Citas de ADR (evitar colisión)**: ASF y el Meta-Factory numeran sus ADR desde 001. Los del
  Meta-Factory se citan bare (`ADR-007`, `decisions/007`); los de ASF, con prefijo (`ASF/ADR-019`).
  En tablas con columna "Origen en ASF" / "dónde vive en ASF", los ADR son de ASF por el encabezado.
