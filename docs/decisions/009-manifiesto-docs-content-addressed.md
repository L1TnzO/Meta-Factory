<!-- meta:doc sha=adf6735aec8f8cb4e3d8f5281027547eb369694c updated=2026-06-13T14:57Z -->
# ADR-009 — Manifiesto de docs content-addressed: hash de git + sello in-band (vista generada, no a mano)

| Campo | Valor |
| --- | --- |
| Estado | **Aprobado** (ratificado por el ingeniero 2026-06-13). Mecanismo dentro de la memoria de ADR-007 (cuyas sub-decisiones siguen Propuestas). |
| Fecha | 2026-06-13T03:29Z |
| Referencia | MEMORY-ARCHITECTURE §9 (mecanismo COMPLETO — autoridad), §8.2 (la regla que implementa), ADR-007 (memoria), ADR-008 (gratis/determinista), CONTEXT-ECONOMY (residencia) |

## Contexto

El drift de START-HERE (LOG 2026-06-13) probó que un índice mantenido a mano se desactualiza. Y el
orquestador, para saber si un doc cambió, hoy debe recargarlo al contexto (caro, y se confunde al
cargar versiones distintas en momentos distintos). Idea del ingeniero: separar "¿cambió?" (hash,
barato) de "¿qué dice?" (cargar, caro), **reusando git** (que ya es content-addressed), y meter el
hash DENTRO del `.md` para que se cargue junto al contenido (no se puede envolver durante la tool call).

## Decisión (mecanismo completo en MEMORY-ARCHITECTURE §9)

1. **Sello in-band** al tope de cada `.md`: `<!-- meta:doc sha=<git-hash-object del cuerpo> updated=<UTC> -->`.
   Al hacer `Read` del doc, su identidad ya está en contexto, sin tool call aparte.
2. **Idempotente**: el sha se computa sobre el cuerpo EXCLUYENDO la línea del sello (sin chicken-and-egg).
3. **`INDEX.md` generado** = todos los sellos + hora del último commit (`git log -1 --format=%cI`) +
   resumen de 1 línea. Vista que no puede driftear (cierra §8.2); START-HERE se genera de ahí.
4. Lo estampa/regenera un hook **`PostToolUse(Write|Edit)`** — determinista, frecuente, baratísimo,
   cero modelo. NO el modelo a mano. `meta check` verifica consistencia.
5. Tres trabajos: triaje barato, índice no-drifteable, y **aid de retrieval determinista** (frescura)
   que complementa/posterga el índice semántico de Tier 2 (G-M2).

## Boundary (no negociable)

El sello/manifiesto sirve para **TRIAR** (qué no abro, qué cambió, qué está raro-viejo), NUNCA para
reemplazar leer el doc sobre el que se va a DECIDIR. El hash dice "cambió", no "importa el cambio".
Un error de diseño es caro; leer es barato.

## Descartado

Capa de hashing propia (git ya es un árbol de Merkle). Hash por sección (prematuro: doc-entero +
`git diff --stat` primero; sección solo si se mide que importa). Que el modelo etiquete su propio
contexto (no puede; el sello viene del archivo). Prerrequisito: `git init` en el repo (ya previsto).
