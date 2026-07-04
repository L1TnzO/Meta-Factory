<!-- meta:doc sha=5a57b6b96d4081647f88e53bdffce5dc446731df updated=2026-07-04T19:53Z -->
# Estado — Agent Systems Factory
> tipo: estado · fábrica generada por el Meta-Factory · esquema heredado ADR-021 (overwrite)
> Este doc APUNTA; la verdad verificable vive en artefactos (.proof/, ledger, RTM re-derivado).

## Ahora
- **🧊 REGRESSION-FROZEN (2026-07-04, COUNCIL-360 §6.2 camino B · §6.5).** Esta fábrica queda
  CONGELADA-CON-PIN: cero incrementos nuevos; su pin la mantiene verde gratis en `meta ci --rederive`
  (custodia ~0 costo de atención). NO se borra — es evidencia de paridad (ADR-014: dominio Python del
  claim de generalidad) y de la regeneración F1. **Descongelar = acto DELIBERADO**: exige motivo
  escrito acá + reabrir con un incremento de fábrica. El sistema VIVO es meta + full-stack-kotlin + iot.
- Fábrica **agent-systems-factory** nacida por la línea M0–M8 del Meta-Factory. Produce: una fábrica de sistemas de agentes LangGraph de grado-producción (línea S0–S8): topología tipada verificable que compila vía get_graph(), HITL no-salteable por alcanzabilidad, estado durable resumible, observabilidad con provenance y evaluación con compuertas que bloquean.
- Hereda el sustrato de toda fábrica confiable (columna anti-sello, bus de veredictos, RTM,
  dos verificadores) cableado por construcción — no re-derivado a mano.

## Mapa
- Línea de producto: `stations/` · Dominio (humano): `domain/` · Generado (chasis): `generated/` · Build re-derivable: `build/`
- Raíz de confianza: `seed/` (columna) + `.claude/` (sombras) · CI externo: `seed/external_ci.yml`
- Veredicto pineado (constante honesta): `pinned_verdict.json`
