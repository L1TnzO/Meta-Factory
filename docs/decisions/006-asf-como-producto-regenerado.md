<!-- meta:doc sha=d0f0a98db9dc649313d55bd392e194d6faa227a8 updated=2026-06-13T14:57Z -->
# ADR-006 — ASF se regenera como producto del Meta-Factory (deja de auto-fabricarse)

| Campo | Valor |
| --- | --- |
| Estado | Aprobado (ejecución diferida al post-bootstrap) |
| Fecha | 2026-06-13T02:17Z |
| Referencia | ADR-001 (legitimidad), reference/ASF-LESSONS.md (la cosecha), reference/ARCHITECTURE.md §5 |

## Contexto

ASF es un sistema muy bien pensado pero arrastra el error de categoría de ADR-001: se fabricó a sí
mismo fuera de su clase de producto. La solución no es parchearlo in-place (no toca la causa raíz);
es **volverlo un producto** de la capa que sí puede gobernarlo legítimamente: el Meta-Factory.

## Decisión

**ASF se descompone en dos y se regenera correndo M0–M8 sobre su propia factory-spec:**

- **Lo reutilizable → asciende al sustrato del Meta-Factory** (los 13 invariantes, I-1…I-13). Deja
  de ser propiedad de ASF y pasa a ser lo que TODA fábrica hereda.
- **Lo opinado → desciende a `factory-spec` Mitad A** (el dominio de ASF): framework LangGraph
  agnóstico-de-proveedor, las 7 capacidades de producción (observabilidad, trazabilidad/linaje,
  estado durable, anclaje de fuentes, atribución, HITL, evaluabilidad), su secuencia S0–S8 como
  dato, sus modos de provisión prompt/integration/custom, su interrupt no-salteable.
- El ASF regenerado vive en `factories/agent-systems-factory/`, aislado, con su propio seed
  heredado, sus gates, su CI externo — gobernado por el Meta-Factory, ya no por sí mismo.

## Consecuencias

- **Criterio de aceptación**: el ASF regenerado debe alcanzar **paridad funcional** con el ASF
  actual (las mismas suites verdes, el mismo RTM honesto del dummy, la prueba de bloqueo). La
  paridad se verifica re-derivando, no narrando.
- ASF se vuelve además el **primer scenario real** que ejercita la parametrización del sustrato
  (G-8): si algo de ASF no entra limpio en la factory-spec, ese es un supuesto no parametrizado del
  Meta-Factory que hay que cerrar.
- **Ejecución diferida**: primero el bootstrap (seed + M0–M3+M8 + dummy-fábrica + prueba de
  bloqueo); recién con el punto fijo probado se regenera ASF. No se toca el ASF actual hasta
  entonces — sigue siendo la referencia de paridad y la fuente cosechada.
- El ASF actual (`../../Agent_Systems_Factory/`) queda como **referencia congelada de cosecha** y
  paridad; no se modifica durante el bootstrap.
