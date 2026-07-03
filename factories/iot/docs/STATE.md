<!-- meta:doc sha=4b4e883e0f9a789055bf8d50304e8d622fcd9a40 updated=2026-07-03T23:00Z -->
# Estado — IoT Factory
> tipo: estado · fábrica generada por el Meta-Factory · esquema heredado ADR-021 (overwrite)
> Este doc APUNTA; la verdad verificable vive en artefactos (.proof/, ledger, RTM re-derivado).

## Ahora
- Fábrica **iot** recién nacida por la línea M0–M8 del Meta-Factory. Produce: un gateway IoT en Go: contrato de mensajes tipado, topología pub/sub verificable, gate de firma OTA no-salteable, procedencia de lecturas y telemetría durable contra un broker vivo — verificado en su propio toolchain (go vet / go test).
- Hereda el sustrato de toda fábrica confiable (columna anti-sello, bus de veredictos, RTM,
  dos verificadores) cableado por construcción — no re-derivado a mano.
- **✅ `IOT-S1-FIELD-VOCAB` CERRADO (2026-07-03).** El codegen (Go) gana `type: enum` type-safe (const-block +
  `Valid<F>` fail-closed + campo tipado), eje R2 mirror de `FSK-S11` en la 2ª cadena de herramientas; `fleet`
  adopta `Health` (no-requerido) con diente de dos lados probado por sabotaje→rojo. Demo byte-idéntico,
  `ci --rederive --all-products --factory iot` 2/2==pin. Ejecutado como vehículo del KPI opus-share de
  `COST-DOWN` §5 (medición de opus-share/$ pendiente del cierre S3). Detalle: `docs/work/IOT-S1-FIELD-VOCAB-INCREMENT.md`.

## Mapa
- Línea de producto: `stations/` · Dominio (humano): `domain/` · Generado (chasis): `generated/` · Build re-derivable: `build/`
- Raíz de confianza: `seed/` (columna) + `.claude/` (sombras) · CI externo: `seed/external_ci.yml`
- Veredicto pineado (constante honesta): `pinned_verdict.json`
