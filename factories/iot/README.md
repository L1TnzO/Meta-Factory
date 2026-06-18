# IoT Factory — fábrica generada por el Meta-Factory

Produce: **un gateway IoT en Go: contrato de mensajes tipado, topología pub/sub verificable, gate de firma OTA no-salteable, procedencia de lecturas y telemetría durable contra un broker vivo — verificado en su propio toolchain (go vet / go test)**.

Esta fábrica nació con el sustrato de producción de fábricas ya horneado y verificado por
construcción (los 13 invariantes). No se auto-fabrica: la gobierna el Meta-Factory, una capa
más confiable que ella (PF-9).

## Confianza
- `seed/` — la columna anti-sello (3 cerrojos), heredada verbatim y congelada.
- `.claude/` — las sombras deterministas de la columna (hooks + permissions.deny).
- `seed/external_ci.yml` — los dos verificadores: un runner limpio re-deriva y exige el
  `pinned_verdict.json`. La custodia local NO es la raíz de confianza; la re-derivación lo es.

## Operación (vía el engine dominio-agnóstico del Meta-Factory)
- `meta product-run --factory iot` — corre la línea de producto e2e (build → compile → run → invariante).
- `meta rtm --factory iot` — re-deriva el RTM desde artefactos (SATISFIED/UNSATISFIED).
- `meta ci --rederive --factory iot` — re-derivación externa contra el veredicto pineado.
