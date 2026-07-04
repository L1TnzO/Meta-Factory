<!-- meta:doc sha=d2cd545724bb43756523296dd155460c70cfd923 updated=2026-07-04T20:10Z -->
# ADR-022 — Consolidación B: superficie activa a la mitad, vocabularios congelados, jueces externos

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-07-04T20:05Z |
| Decide | el ingeniero (2026-07-04, «aplicá todo lo diseñado» tras COUNCIL-360 §6); ejecuta el orquestador |
| Generaliza | ADR-020 (vocabularios cerrados: de roles a check-kinds), ADR-021 (D-6: los $ son shadow-prices), ADR-014 (paridad: lo congelado sigue siendo evidencia), I-11 (el segundo actor por fin corre) |
| Referencia | **`reference/COUNCIL-360-AUDIT.md §4–§6` (la auditoría completa: H-1..H-9, D-1..D-8, síntesis)** · `reference/ARCHITECTURE-MAP.md` (as-built + §8 THREAT-MODEL) |

## Contexto (medido, no narrado)
COUNCIL-360 (2026-07-04) cerró tres iteraciones de diseño con un veredicto: **la topología actual es la
óptima conocida para el régimen declarado** (proyecto personal · generar-verificado-sin-leer-el-código);
ninguna alternativa simulada la domina (§6.2). El óptimo no es otra topología — es la MISMA con la mitad
de la superficie activa y jueces instalados. El cuello medido no era el motor (funciona: FSK genera apps
reales verificadas) sino el ALQUILER COGNITIVO de la superficie (Silla 8) y la ausencia de jueces
EXTERNOS (el sistema se medía a sí mismo).

## Decisión (lo que queda en vigor)
1. **Camino B — el sistema VIVO es meta + full-stack-kotlin + iot.** `dummy` queda como FIXTURE del pin
   (cuerpo de prueba de la línea meta). `agent-systems-factory` y `full-stack` (TS) quedan
   **REGRESSION-FROZEN declarado en su STATE**: cero incrementos nuevos; el pin las mantiene verdes
   gratis (`meta ci --rederive`); descongelar = acto deliberado con motivo escrito. Nada se borra:
   congelar-con-pin, no podar (la custodia de lo congelado cuesta ~0).
2. **D-3 — el vocabulario de check-kinds queda CONGELADO** (`registry.KINDS`, regla espejo de ADR-020):
   kind nuevo = acto deliberado (editar la constante + ADR) con vara «¿no alcanza `product_env` + un
   script?». Diente: gate `kinds` (`kind_hygiene.py`) en `meta check`, repo-wide, dos lados.
3. **D-6 — economía en shadow-prices.** Bajo suscripción, los $ del ledger miden CUPO relativo, no
   ahorro contante; el rotulado «$shadow» es disciplina de salida (`cost_report`). La restricción
   vinculante real = cupo + horas-humano → ambos jueces son números de 1ª clase del CLI
   (`transcript_model_split` con dedup `message.id` · `wall_clock_hours`), no scripts de sesión (H-9).
4. **Los tres jueces externos** (§6.3.c) entran al árbol como evidencia re-derivable: segundo actor de
   CI (H-1, verde desde run 28717567792) · tasa de escape por mutation testing (E4) · grupo de control
   con spec AJENA (E1+D-8, `specs/foreign-conduit/` verbatim de terceros, proveniencia pineada).
5. **D-4 — patrón iot como única vía de extensión**: todo eje nuevo de fábrica nace como slot S2 salvo
   justificación escrita en su work-doc.
6. **C (3ª fábrica real) es opción CON FECHA**, no backlog abierto: solo se abre si aparece un dominio
   con uso propio real; mientras tanto B es la casa. La regla 30-días-en-0 (§2.6) rige la superficie de
   navegación del grafo (observer `graph_query`).

## Consecuencias
- La narrativa «N fábricas activas» se retira a «2 vivas + 1 fixture + 2 congeladas-verificables» — es
  RENUNCIA narrativa, no pérdida de capacidad (re-derivación intacta, ADR-014 se sostiene).
- El threat model queda DESINFLADO por escrito (`ARCHITECTURE-MAP §8`): la amenaza defendida es
  deriva/autoengaño con dientes; adversario activo/plataforma/supply-chain-profundo quedan declarados
  fuera (D-7). El pin ancla veredictos, no bytes (H-2).
- Todo cambio futuro de vocabulario (roles, kinds) o descongelamiento deja rastro: constante + ADR +
  motivo en STATE — deliberación como diente, no como costumbre.
