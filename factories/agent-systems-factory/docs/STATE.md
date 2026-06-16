# Estado — Agent Systems Factory
> tipo: estado · fábrica generada por el Meta-Factory · esquema heredado ADR-021 (overwrite)
> Este doc APUNTA; la verdad verificable vive en artefactos (.proof/, ledger, RTM re-derivado).

## Ahora
- Fábrica **agent-systems-factory** recién nacida por la línea M0–M8 del Meta-Factory. Produce: una fábrica de sistemas de agentes LangGraph de grado-producción (línea S0–S8): topología tipada verificable que compila vía get_graph(), HITL no-salteable por alcanzabilidad, estado durable resumible, observabilidad con provenance y evaluación con compuertas que bloquean.
- Hereda el sustrato de toda fábrica confiable (columna anti-sello, bus de veredictos, RTM,
  dos verificadores) cableado por construcción — no re-derivado a mano.

## Mapa
- Línea de producto: `stations/` · Dominio (humano): `domain/` · Generado (chasis): `generated/` · Build re-derivable: `build/`
- Raíz de confianza: `seed/` (columna) + `.claude/` (sombras) · CI externo: `seed/external_ci.yml`
- Veredicto pineado (constante honesta): `pinned_verdict.json`
