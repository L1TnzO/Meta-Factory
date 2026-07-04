<!-- meta:doc sha=b7729ffa38b64804ad4964318d5181e570486eee updated=2026-07-04T19:53Z -->
# Estado — Full-Stack Factory
> tipo: estado · fábrica generada por el Meta-Factory · esquema heredado ADR-021 (overwrite)
> Este doc APUNTA; la verdad verificable vive en artefactos (.proof/, ledger, RTM re-derivado).

## Ahora
- **🧊 REGRESSION-FROZEN (2026-07-04, COUNCIL-360 §6.2 camino B · §6.5 · §2.6).** Esta fábrica queda
  CONGELADA-CON-PIN: cero incrementos nuevos; su pin la mantiene verde gratis en `meta ci --rederive`.
  Su paridad (dominio TS) ya está cubierta por Kotlin+Go+Python en el claim de generalidad — candidata
  medida en §2.6, ahora declarada. NO se borra (evidencia de paridad, ADR-014). **Descongelar = acto
  DELIBERADO**: motivo escrito acá + incremento de fábrica. El sistema VIVO es meta + full-stack-kotlin + iot.
- Fábrica **full-stack** nacida por la línea M0–M8 del Meta-Factory. Produce: una app web full-stack mínima: contrato tipado + backend + frontend + DB relacional, verificada en su propio toolchain (tsc --strict / node:test / node:sqlite).
- Hereda el sustrato de toda fábrica confiable (columna anti-sello, bus de veredictos, RTM,
  dos verificadores) cableado por construcción — no re-derivado a mano.

## Mapa
- Línea de producto: `stations/` · Dominio (humano): `domain/` · Generado (chasis): `generated/` · Build re-derivable: `build/`
- Raíz de confianza: `seed/` (columna) + `.claude/` (sombras) · CI externo: `seed/external_ci.yml`
- Veredicto pineado (constante honesta): `pinned_verdict.json`
