# Bitácora — Full-Stack Kotlin/TS/PG Factory
> tipo: log · append-only, MÁS NUEVO ARRIBA · inmutable una vez escrito (esquema ADR-021).

## s1 — capa de datos (DES-12 + DES-4), 2026-06-18
- La línea ganó la estación s1: schema versionado Flyway + jOOQ DDLDatabase (tipos del schema, sin DB
  viva → `compileKotlin` grita ante un query a columna inexistente) y un round-trip create/list contra
  una PostgreSQL VIVA por `infra_up` (contenedor pineado por digest; DB caída → rojo). RTM 5/5, M0–M8
  verde, `ci --rederive` 2/2 == pineado, 2 dientes vivos. Sin tocar el sustrato del Meta-Factory.

## nacimiento — generada por el Meta-Factory
- La fábrica full-stack-kotlin se construyó corriendo M0–M8 sobre su factory-spec. El sustrato no se
  escribió a mano: ascendió del template del Meta-Factory (los 13 invariantes), verificado por gate.
