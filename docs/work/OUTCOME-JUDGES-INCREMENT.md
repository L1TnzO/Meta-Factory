<!-- meta:doc sha=45e7fa83d9e0c3a0bbfdfd96a0dd95e37b7cc22f updated=2026-07-04T19:56Z -->
# Incremento OUTCOME-JUDGES

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-04T19:56Z) (creado 2026-07-04T19:45Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
COUNCIL-360 §6.4.2 + H-9: los dos jueces económicos que faltaban como número de primera clase del CLI —
**opus-share por transcript** (KPI del norte ADR-021, hasta hoy medido ad-hoc) y **horas-humano wall-clock**
(la restricción vinculante real bajo suscripción, §6.0.2) — más el **rotulado $shadow** (§6.0.1: los $ del
ledger son cupo relativo, no ahorro contante) en el bloque de costo de `meta outcome`.

## Método (demostración del modelo operativo diseñado)
Slot acotado delegado vía `generate-slot` (D-4 operando): contrato tipado `.gen/outcome-judges.contract.md`
· blast radius = 4 archivos · gate partido (pytest focalizado ≤15s / `meta check` 18-gates) · veredicto
`.gen/outcome-judges.verdict.json`. El orquestador acepta por VEREDICTO, no por diff (ADR-017 §2);
spot-check con ojos propios SOLO del diff de `tests/test_pricing_ledger.py` (trust medium: un generator
no debilita asserts existentes sin revisión).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Contrato + manifest (`manifest_problems` = NONE) | ✅ |
| 2 | Generator (Sonnet) implementa `model_split` (dedup `message.id`) + `wall_clock_hours` + 3 claves en `cost_summary` + render `MODELO`/`HORAS`/`shadow-total` + tests dos-lados | ⏳ |
| 3 | Veredicto verde (acceptance = `meta check` exit 0) + spot-check del diff de asserts | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `.gen/outcome-judges.verdict.json`: `status: green` con `acceptance_exit_code: 0` (18/18).
2. `meta outcome --transcript <t>` imprime `MODELO … opus x%` + `HORAS … wall-clock` + `shadow-total`
   — el KPI del norte es un número del CLI, no un script de sesión (H-9 cerrado).
3. Dos lados: sin transcript, las tres claves degradan honestas (None/{}) — jamás un 0 fabricado.
