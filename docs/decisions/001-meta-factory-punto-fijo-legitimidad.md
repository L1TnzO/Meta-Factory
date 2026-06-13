<!-- meta:doc sha=0dc41c936bde1183849fb0ebfd87c1811925bdcb updated=2026-06-13T14:57Z -->
# ADR-001 — El Meta-Factory como punto fijo legítimo del auto-mejoramiento

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-13T02:17Z |
| Referencia | reference/VISION.md §2–3, reference/SELF-IMPROVEMENT.md, ASF/ADR-023 (la confesión) |

## Contexto

ASF se construyó dentro de su propia carpeta, sujeto a su propio harness: se fabricó a sí mismo.
El propio ASF confesó el síntoma (ADR-023: *"aplicó ADR-020 a fabricar productos, pero nunca a sí
misma"*) sin nombrar la causa. La causa es un **error de categoría**: ASF no pertenece a su clase
de producto (sistemas agénticos sobre LangGraph), así que para auto-aplicarse tuvo que fingir ser
su propio producto.

## Decisión

**Criterio de legitimidad**: una fábrica F puede aplicarse legítimamente a sí misma si, y solo si,
F pertenece a su propia clase de producto.

- Clase de producto del Meta-Factory = `{ fábricas construidas sobre el harness de Claude Code }`.
- El Meta-Factory **pertenece** a esa clase. Por lo tanto, mejorarse a sí mismo ES lo que hace,
  no una excepción a sus reglas. Es el único punto fijo legítimo del ecosistema (PF-9).
- Es el mismo principio que vuelve legítimo a un compilador que se compila o a un evaluador
  metacircular. La auto-aplicación es sospechosa solo cuando el sistema sale de su clase.

## Consecuencias

- Toda OTRA fábrica (ASF incluida) se construye desde una capa más confiable (su Meta-Factory) y
  NO se auto-aplica → ADR-006 (ASF se regenera como producto).
- El auto-mejoramiento del Meta-Factory recibe el gate MÁS fuerte, no el más débil
  (reference/SELF-IMPROVEMENT.md §3, niveles R0–R3).
- Rechazado: parchear ASF in-place para "arreglar" su auto-fabricación — no toca la causa raíz.
