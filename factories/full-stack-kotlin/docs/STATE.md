# Estado — Full-Stack Kotlin/TS/PG Factory
> tipo: estado · fábrica generada por el Meta-Factory · esquema heredado ADR-021 (overwrite)
> Este doc APUNTA; la verdad verificable vive en artefactos (.proof/, ledger, RTM re-derivado).

## Ahora
- Fábrica **full-stack-kotlin** recién nacida por la línea M0–M8 del Meta-Factory. Produce: una app web full-stack de grado-producción: contrato OpenAPI tipado como fuente única, backend Kotlin, frontend TypeScript/React, base de datos PostgreSQL con esquema versionado (Flyway) y queries chequeados en compilación (jOOQ), verificada ENTERA en su propio toolchain bajo criterios duros de ingeniería (dureza estática, frescura de API, seguridad de la cadena de suministro, calidad de experiencia, observabilidad), 100%-generada desde este spec..
- Hereda el sustrato de toda fábrica confiable (columna anti-sello, bus de veredictos, RTM,
  dos verificadores) cableado por construcción — no re-derivado a mano.
- **Expresividad madura (R2/FSK-S11..S16)**: 8 tipos de campo + opcionalidad · workflows (máquinas de estado) ·
  RBAC por rol · ownership a nivel de fila · **control de acceso a RUNTIME** (server HTTP vivo que invoca
  Auth→RBAC→Ownership sobre requests reales vs PostgreSQL viva) y, desde **FSK-S16 (2026-06-21)**, **CRUD-mutación
  real**: ese server MUTA columnas (POST inserta · PUT actualiza · DELETE borra, jOOQ tipado) bajo el control de
  acceso, con un diente de ROUND-TRIP e2e (no sólo el veredicto). Detalle e historia: `docs/LOG.md`.
- **Sigue** (huecos honestos → próximos incrementos): body-parsing JSON + PATCH · CRUD de entidades sin dueño ·
  ownership opcional/RTD · self-ref · custom-fields dinámicos · frontend React que consume + deploy + e2e.

## Mapa
- Línea de producto: `stations/` · Dominio (humano): `domain/` · Generado (chasis): `generated/` · Build re-derivable: `build/`
- Raíz de confianza: `seed/` (columna) + `.claude/` (sombras) · CI externo: `seed/external_ci.yml`
- Veredicto pineado (constante honesta): `pinned_verdict.json`
