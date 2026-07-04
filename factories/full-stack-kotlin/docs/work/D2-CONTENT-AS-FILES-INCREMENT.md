<!-- meta:doc sha=0d4dd6f165d162fd97ec1444a19f2c946c4b1061 updated=2026-07-04T20:32Z -->
# Incremento D2-CONTENT-AS-FILES

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-04T20:32Z) (creado 2026-07-04T20:15Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
D-2 (COUNCIL-360 §5/§6.4.3, ADR-022): el YAML de estación ORQUESTA; el contenido embebido (archivos
Kotlin/Gradle enteros como literales escapados en `s6.yml` — sin highlighting, sin lint, diffs
ilegibles) migra a archivos REALES en `stations/templates/s6/`, referenciados con `action: render`
(misma semántica `render_text` que `write` → salida byte-idéntica). Cero cambio de sustrato: `render`
ya existía y es dominio-agnóstico (ADR-012). Transformación DETERMINISTA hecha con script + aserción
de bytes — NO delegada (lección MONOLITH-REFACTOR: byte-idéntico ≠ slot).

## Alcance declarado (honesto)
- Migrados: `stations/s6.yml` (fábrica) + las 3 copias materializadas de producto
  (`products/{assets,helpdesk,snipeit}/stations/s6.yml`, `activation: off`) → 4 blobs c/u a los
  MISMOS templates de fábrica (fuente única), con aserción bytes-template == bytes-YAML por copia.
- El `brief` del action `generate` (prompt LLM) se queda en el YAML: es orquestación (el contrato del
  slot), no contenido de producto.
- ASF s9 (2) y full-stack s3 (2) NO se migran: fábricas REGRESSION-FROZEN (ADR-022 §1) — tocarlas
  sería descongelar sin motivo.
- De paso (evidencia-rancia real detectada por el árbol RTM): `factory.spec.yml` REQ-F-021 tenía el
  artifact con path LITERAL pre-rename (`com/obs/server/`) mientras las demás reqs usan
  `{{package_name}}/endpoints/` — alineado al placeholder.

## Criterio de cierre (demostrable, no narrable)
1. Extracción con aserción: 4 templates escritos == bytes del YAML original (settings 32B ·
   build.gradle.kts 722B · Model.kt 652B · SummaryContract.kt 1715B); sin `{{}}` en el contenido. ✅
2. `meta ci --rederive --factory full-stack-kotlin --all-products` → **4/4 == pin** (12/12 + 11/11×3)
   con las estaciones nuevas — byte-identidad de conducta, CERO re-pin. ✅ 2026-07-04
3. `meta rtm --factory full-stack-kotlin` → **27/27** (REQ-F-021 vuelve a SATISFIED). ✅ 2026-07-04
