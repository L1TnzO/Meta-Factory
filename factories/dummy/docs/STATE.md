<!-- meta:doc sha=62c40ed0a315e21c6bcd4f0b5dc2b2efd77afbab updated=2026-07-11T05:03Z -->
# Estado — Dummy Factory
> tipo: estado · fábrica generada por el Meta-Factory · esquema heredado ADR-021 (overwrite)
> Este doc APUNTA; la verdad verificable vive en artefactos (.proof/, ledger, RTM re-derivado).

## Ahora
- Harness `.claude/` in English (ENGLISH-HARNESS, 2026-07-11, ADR-026 F2a stage 3): spec↔emitted proven byte-in-sync by in-memory render.
- Fábrica **dummy** recién nacida por la línea M0–M8 del Meta-Factory. Produce: un módulo de saludo trivial con un marcador invariante.
- Hereda el sustrato de toda fábrica confiable (columna anti-sello, bus de veredictos, RTM,
  dos verificadores) cableado por construcción — no re-derivado a mano.

## Mapa
- Línea de producto: `stations/` · Dominio (humano): `domain/` · Generado (chasis): `generated/` · Build re-derivable: `build/`
- Raíz de confianza: `seed/` (columna) + `.claude/` (sombras) · CI externo: `seed/external_ci.yml`
- Veredicto pineado (constante honesta): `pinned_verdict.json`
