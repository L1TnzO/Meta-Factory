<!-- meta:doc sha=86179b97fabca62fcdb634f26b4ace70935aede4 updated=2026-06-13T14:57Z -->
# ADR-002 — La columna anti-sello-de-goma como invariante I-1 de toda fábrica

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-13T02:17Z |
| Referencia | ASF/ADR-006 (origen), reference/ARCHITECTURE.md §3 (I-1), §6 (M1) |

## Contexto

La invención más valiosa de ASF: tres cerrojos independientes que vuelven imposible marcar una
compuerta sin prueba real. Es lo que distingue una fábrica de un teatro de fábrica. ASF la probó
end-to-end (la prueba de bloqueo). El Meta-Factory no la reinventa: la hereda como invariante
no-negociable de toda fábrica que emite.

## Decisión

**Toda fábrica producida nace con la columna de tres cerrojos, instalada por la meta-estación M1
y verificada por la prueba de bloqueo:**

1. **El veredicto no es escribible por el modelo.** `passed` lo computa exclusivamente el verifier
   desde exit codes reales de subprocesos. Un hook `PreToolUse` + `permissions.deny` niegan toda
   escritura a proof/ledger/rtm que no venga del verifier.
2. **La compuerta recomputa el hash** de archivos+resultados y rechaza un veredicto editado.
3. **El hook `Stop` re-corre verify** de la estación actual al cierre del turno y bloquea (exit 2)
   si no pasa.

La columna es parte del **seed congelado** (Stage 0): es la raíz de confianza, se audita a mano y
se modifica solo bajo el gate R3 (reference/SELF-IMPROVEMENT.md §5).

## Consecuencias

- M1 incluye la prueba de bloqueo como criterio de gate: corromper un invariante → la fábrica
  recién nacida produce `passed=false` y nada avanza.
- I-1 es no-negociable en su EXISTENCIA; sus parámetros (qué checks, qué umbrales) los fija la
  factory-spec Mitad A.
- Residual honesto heredado de ASF: la custodia local del ledger depende de la cadena de hooks
  activa → mitigado por ADR-005 (dos verificadores re-derivan desde runner limpio).
