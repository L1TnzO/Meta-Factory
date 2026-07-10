<!-- meta:doc sha=9c332a9b6679c0c7861f763b70a7035d69513b48 updated=2026-07-10T23:49Z -->
# Estado — Agent Systems Factory
> tipo: estado · fábrica generada por el Meta-Factory · esquema heredado ADR-021 (overwrite)
> Este doc APUNTA; la verdad verificable vive en artefactos (.proof/, ledger, RTM re-derivado).

## Ahora
- **🧊 REGRESSION-FROZEN para el CHASIS s0–s11 (2026-07-04, COUNCIL-360 §6.2 camino B · §6.5) — sigue
  cierto: cero incrementos nuevos sobre s0..s11; su pin las mantiene verdes gratis en `meta ci
  --rederive` (custodia ~0 costo de atención). NO se borra — es evidencia de paridad (ADR-014: dominio
  Python del claim de generalidad) y de la regeneración F1. Descongelar EL CHASIS = acto DELIBERADO.**
- **✅ THAW ADITIVO — primer producto ADOPTADO (2026-07-10, ADR-025, `REQCOUNCIL-ADOPT`).** `products/`
  ya NO está vacío: `products/reqcouncil/` (copiado-no-emitido @ `89ad45b`, ver `PROVENANCE.md`) es la
  1ª adopción de un producto evaluable EXTERNO como producto de ASF — generaliza `design_floor`
  (ADR-024, superficie de frontend) a `eval_floor` (ADR-025, arnés de evaluación semántica): re-verifica
  `runs/pinned/` de ReqCouncil contra su PROPIO piso (`config/thresholds.yml`) sin re-implementar la
  métrica. Esto NO descongela s0..s11 (siguen intocados, mismo pin) — es una estación NUEVA, aditiva:
  **`s12`** (`stations/s12.yml`, `kind: eval_floor`, `requires_prev: s11`). `meta pin` confirma s1..s11
  byte-idénticos (pin sólo AGREGA `s12`); `meta ci --rederive` → 12/12 proof_sha == pineado.
  Incremento `REQCOUNCIL-ADOPT` CERRADO (ambos niveles: fábrica + `products/reqcouncil`).
- Fábrica **agent-systems-factory** nacida por la línea M0–M8 del Meta-Factory. Produce: una fábrica de sistemas de agentes LangGraph de grado-producción (línea S0–S8): topología tipada verificable que compila vía get_graph(), HITL no-salteable por alcanzabilidad, estado durable resumible, observabilidad con provenance y evaluación con compuertas que bloquean.
- Hereda el sustrato de toda fábrica confiable (columna anti-sello, bus de veredictos, RTM,
  dos verificadores) cableado por construcción — no re-derivado a mano.

## Mapa
- Línea de producto: `stations/` (s0..s11 chasis + `s12` producto adoptado) · Dominio (humano): `domain/` · Generado (chasis): `generated/` · Build re-derivable: `build/`
- Producto adoptado: `products/reqcouncil/` (código+config+tests+runs/pinned+runs/degraded+docs
  copiados @89ad45b; `datasets/` 803M en disco, gitignorado, sólo `datasets/MANIFEST.md` trackeado) +
  `PROVENANCE.md` (el pin + la regla dura: NUNCA lleva `product.yml`, ver el doc)
- Raíz de confianza: `seed/` (columna) + `.claude/` (sombras) · CI externo: `seed/external_ci.yml`
- Veredicto pineado (constante honesta): `pinned_verdict.json`
