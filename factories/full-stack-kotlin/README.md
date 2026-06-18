# Full-Stack Kotlin/TS/PG Factory — fábrica generada por el Meta-Factory

Produce: **una app web full-stack de grado-producción: contrato OpenAPI tipado como fuente única, backend Kotlin, frontend TypeScript/React, base de datos PostgreSQL con esquema versionado (Flyway) y queries chequeados en compilación (jOOQ), verificada ENTERA en su propio toolchain bajo criterios duros de ingeniería (dureza estática, frescura de API, seguridad de la cadena de suministro, calidad de experiencia, observabilidad), 100%-generada desde este spec.**.

Esta fábrica nació con el sustrato de producción de fábricas ya horneado y verificado por
construcción (los 13 invariantes). No se auto-fabrica: la gobierna el Meta-Factory, una capa
más confiable que ella (PF-9).

## Confianza
- `seed/` — la columna anti-sello (3 cerrojos), heredada verbatim y congelada.
- `.claude/` — las sombras deterministas de la columna (hooks + permissions.deny).
- `seed/external_ci.yml` — los dos verificadores: un runner limpio re-deriva y exige el
  `pinned_verdict.json`. La custodia local NO es la raíz de confianza; la re-derivación lo es.

## Operación (vía el engine dominio-agnóstico del Meta-Factory)
- `meta product-run --factory full-stack-kotlin` — corre la línea de producto e2e (build → compile → run → invariante).
- `meta rtm --factory full-stack-kotlin` — re-deriva el RTM desde artefactos (SATISFIED/UNSATISFIED).
- `meta ci --rederive --factory full-stack-kotlin` — re-derivación externa contra el veredicto pineado.
