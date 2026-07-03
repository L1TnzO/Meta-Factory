<!-- meta:doc sha=9a5c3d203f7ffa37809793094dc1265964d9ebb0 updated=2026-07-03T22:28Z -->
# Estado — IoT Factory
> tipo: estado · fábrica generada por el Meta-Factory · esquema heredado ADR-021 (overwrite)
> Este doc APUNTA; la verdad verificable vive en artefactos (.proof/, ledger, RTM re-derivado).

## Ahora
- Fábrica **iot** recién nacida por la línea M0–M8 del Meta-Factory. Produce: un gateway IoT en Go: contrato de mensajes tipado, topología pub/sub verificable, gate de firma OTA no-salteable, procedencia de lecturas y telemetría durable contra un broker vivo — verificado en su propio toolchain (go vet / go test).
- Hereda el sustrato de toda fábrica confiable (columna anti-sello, bus de veredictos, RTM,
  dos verificadores) cableado por construcción — no re-derivado a mano.
- **🚧 `IOT-S1-FIELD-VOCAB` ABIERTO (2026-07-03).** Extiende el vocabulario de campos del codegen (Go) de
  4 tipos base a `enum` type-safe (const-block + `Valid<F>`), eje R2 mirror de `FSK-S11` en la 2ª cadena de
  herramientas; ejecutado como vehículo del KPI opus-share de `COST-DOWN` §5. Detalle: `docs/work/IOT-S1-FIELD-VOCAB-INCREMENT.md`.

## Mapa
- Línea de producto: `stations/` · Dominio (humano): `domain/` · Generado (chasis): `generated/` · Build re-derivable: `build/`
- Raíz de confianza: `seed/` (columna) + `.claude/` (sombras) · CI externo: `seed/external_ci.yml`
- Veredicto pineado (constante honesta): `pinned_verdict.json`
