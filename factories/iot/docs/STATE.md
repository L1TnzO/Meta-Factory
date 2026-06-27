<!-- meta:doc sha=733abc27c14210bbb8785c711c24c621b2c95376 updated=2026-06-27T01:41Z -->
# Estado — IoT Factory
> tipo: estado · fábrica generada por el Meta-Factory · esquema heredado ADR-021 (overwrite)
> Este doc APUNTA; la verdad verificable vive en artefactos (.proof/, ledger, RTM re-derivado).

## Ahora
- Fábrica **iot** recién nacida por la línea M0–M8 del Meta-Factory. Produce: un gateway IoT en Go: contrato de mensajes tipado, topología pub/sub verificable, gate de firma OTA no-salteable, procedencia de lecturas y telemetría durable contra un broker vivo — verificado en su propio toolchain (go vet / go test).
- Hereda el sustrato de toda fábrica confiable (columna anti-sello, bus de veredictos, RTM,
  dos verificadores) cableado por construcción — no re-derivado a mano.

## Mapa
- Línea de producto: `stations/` · Dominio (humano): `domain/` · Generado (chasis): `generated/` · Build re-derivable: `build/`
- Raíz de confianza: `seed/` (columna) + `.claude/` (sombras) · CI externo: `seed/external_ci.yml`
- Veredicto pineado (constante honesta): `pinned_verdict.json`
