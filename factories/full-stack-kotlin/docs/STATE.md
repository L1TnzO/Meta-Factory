# Estado — Full-Stack Kotlin/TS/PG Factory
> tipo: estado · fábrica generada por el Meta-Factory · esquema heredado ADR-021 (overwrite)
> Este doc APUNTA; la verdad verificable vive en artefactos (.proof/, ledger, RTM re-derivado).

## Ahora
- Fábrica **full-stack-kotlin** recién nacida por la línea M0–M8 del Meta-Factory. Produce: una app web full-stack de grado-producción: contrato OpenAPI tipado como fuente única, backend Kotlin, frontend TypeScript/React, base de datos PostgreSQL con esquema versionado (Flyway) y queries chequeados en compilación (jOOQ), verificada ENTERA en su propio toolchain bajo criterios duros de ingeniería (dureza estática, frescura de API, seguridad de la cadena de suministro, calidad de experiencia, observabilidad), 100%-generada desde este spec..
- Hereda el sustrato de toda fábrica confiable (columna anti-sello, bus de veredictos, RTM,
  dos verificadores) cableado por construcción — no re-derivado a mano.
- **Expresividad madura (R2/FSK-S11..S16 + CRUD-BODY-PARSING)**: 8 tipos de campo + opcionalidad · workflows
  (máquinas de estado) · RBAC por rol · ownership a nivel de fila · **control de acceso a RUNTIME** (server HTTP
  vivo que invoca Auth→RBAC→Ownership sobre requests reales vs PostgreSQL viva) · **CRUD-mutación real** (FSK-S16:
  POST/PUT/DELETE jOOQ tipado bajo el control de acceso, diente ROUND-TRIP) y, desde **FSK-CRUD-BODY-PARSING
  (2026-06-21)**, **entrada tipada a RUNTIME**: ese server lee el **CUERPO real** del request y lo persiste
  **type-coerced por el schema** (POST inserta los valores del body, GET /{id} devuelve la fila completa
  type-correct, PUT actualiza del body; body malo → 400, fail-closed) vía `kotlinx.serialization.json`. Detalle e
  historia: `docs/LOG.md`.
- **Sigue** (huecos honestos → próximos incrementos): PUT-total vs PATCH-split · refs no-dueño desde el body ·
  UNIQUE-from-body→409 · CRUD de entidades sin dueño · ownership opcional/RTD · self-ref · custom-fields ·
  **frontend React que consume + deploy + e2e Playwright** (el último gran eje: el backend ya está vivo y CRUD-completo).

## Mapa
- Línea de producto: `stations/` · Dominio (humano): `domain/` · Generado (chasis): `generated/` · Build re-derivable: `build/`
- Raíz de confianza: `seed/` (columna) + `.claude/` (sombras) · CI externo: `seed/external_ci.yml`
- Veredicto pineado (constante honesta): `pinned_verdict.json`
