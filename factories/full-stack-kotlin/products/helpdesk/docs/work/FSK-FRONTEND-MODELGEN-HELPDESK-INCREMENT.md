<!-- meta:doc sha=0a1e4255ff425b602ffccbc710bc713c379d1e29 updated=2026-07-08T15:16Z -->
# Incremento FSK-FRONTEND-MODELGEN-HELPDESK

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-08T14:46Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Nivel-producto (`products/helpdesk`) del brazo B del experimento `FSK-FRONTEND-MODELGEN-AB` (ver el
incremento de fábrica `factories/full-stack-kotlin/docs/work/FSK-FRONTEND-MODELGEN-AB-INCREMENT.md`
§Contrato-B, que es el contrato real): un slot `generate-slot` (Sonnet) regenera model-nativamente
`build/product/frontend/src/{app.ts,app.css}` de `helpdesk` — el ÚNICO punto de variación es ese par de
archivos generados (build/, gitignoreado); el producto (`product.yml`) y la fábrica no cambian. Este doc
sólo abre el nivel para que el harness (ADR-010/ADR-016) permita escribir esos dos archivos; el contrato,
los jueces y el criterio de cierre viven en el doc de fábrica (no se duplican acá).

## Alcance
- `build/product/frontend/src/app.ts` — presentación (app-shell, screens, formato, labels).
- `build/product/frontend/src/app.css` — hoja de estilos (Vercel ink+hairline, `docs/reference/DESIGN-VERCEL.md`).

Cerrar este incremento cuando el veredicto del slot (`.gen/fsk-frontend-modelgen-helpdesk.verdict.json`)
sea `green` con `acceptance_exit_code: 0` (re-derivado por `tools/modelgen_ab_gate.sh helpdesk`).
