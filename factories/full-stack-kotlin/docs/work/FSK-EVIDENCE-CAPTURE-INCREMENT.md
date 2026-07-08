<!-- meta:doc sha=e1ee07ea90ae0587bf65bc682df8f7277129bff3 updated=2026-07-08T22:08Z -->
# Incremento FSK-EVIDENCE-CAPTURE

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-08T22:08Z) (creado 2026-07-08T21:52Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Herramienta de fábrica DATA-agnóstica para capturar, contra un producto FSK levantado en vivo
(`dev_run.sh`), un screenshot real por cada pantalla navegable (Chromium/Playwright), como evidencia de
documentación — sin nombres de dominio *hardcodeados* (lee `nav button[data-entity]` del DOM real).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `tools/screenshot_evidence.mjs`: navega el nav real, captura dashboard + list/detail por entidad + extras (tabs/trash) del screen hand-wired, `fullPage: true` | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. Ejecutado contra `snipeit` levantado real (`dev_run.sh snipeit`): 39 capturas reales generadas en
   `products/snipeit/docs/reference/evidence/` (uso real documentado en
   `products/snipeit/docs/work/SNIPEIT-COMPLETENESS-SPEC-INCREMENT.md`).
2. Sin nombres de entidad/dominio en el código de la herramienta (grep negativo: ningún literal
   `Asset`/`Company`/etc. fuera de comentarios de ejemplo) — reutilizable para cualquier producto FSK con
   la misma convención de shell (`nav button[data-entity]`, `select[data-role-picker]`).
