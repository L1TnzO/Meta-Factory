<!-- meta:doc sha=b8b89969d1568a6151b46e243f99ea473ff3e8b3 updated=2026-07-08T22:08Z -->
# Incremento SNIPEIT-COMPLETENESS-SPEC

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-08T22:08Z) (creado 2026-07-08T22:02Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Auditar el producto `snipeit` contra un piso mínimo de completitud pedido (10 casos de uso · 30
funcionalidades · 40 tablas · 40 endpoints · 30 pantallas con evidencia · 60 reglas de negocio · 100
validaciones CHECK · checklist de completitud · pruebas con cobertura 100%) y redactar el documento de
especificación humano correspondiente, con cada número re-derivado de artefactos reales (no estimado).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Levantar `snipeit` real (`dev_run.sh`), poblar las 11 entidades que arrancan vacías vía `POST` real, capturar 39 pantallas (`screenshot_evidence.mjs`, incremento hermano `FSK-EVIDENCE-CAPTURE`) | ✅ |
| 2 | Contar tablas/endpoints/reglas/validaciones desde artefactos reales (DDL, OpenAPI, `product.yml` parseado por PyYAML) + probar HTTP real (400/403/409, y un bug real de `UNIQUE` no manejado) | ✅ |
| 3 | Redactar `docs/reference/SNIPEIT-SPEC.md` (checklist de completitud honesto: 6/9 PASA, 3/9 con brecha real declarada) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `docs/reference/SNIPEIT-SPEC.md` existe, con los 9 criterios verificados contra artefactos reales
   (§0 tabla resumen) y metodología de conteo reproducible declarada en cada sección.
2. `docs/reference/evidence/*.png` contiene 39 capturas reales (Chromium, `fullPage`) — no maquetas.
3. Al menos un hallazgo NUEVO no documentado previamente en `SNIPEIT-DOMAIN.md` (el bug de `UNIQUE`, §12
   del spec) — evidencia de que la auditoría se ejecutó contra el sistema vivo, no se copió.
4. Árbol limpio + estación activa verde (gate de cierre del incremento).
