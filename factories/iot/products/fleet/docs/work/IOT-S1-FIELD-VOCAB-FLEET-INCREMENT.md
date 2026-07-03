<!-- meta:doc sha=a0172f89654f31dd36e10d422c604211a9a00e8b updated=2026-07-03T22:58Z -->
# Incremento IOT-S1-FIELD-VOCAB-FLEET

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-03T22:58Z) (creado 2026-07-03T22:47Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

> **Companion product-level increment** de `factories/iot/docs/work/IOT-S1-FIELD-VOCAB-INCREMENT.md` (nivel
> fábrica): existe SOLO porque `product.yml` es un archivo de nivel PRODUCTO (ADR-016, `increment_guard`
> level-aware) y necesita su propio incremento ABIERTO para poder editarse. El contrato/gate/blast-radius
> completos viven en el doc de fábrica — éste es el ticket de gobierno del nivel producto.

## Objetivo
`fleet/product.yml` adopta el campo `enum` `Health` (no-requerido) habilitado por el codegen de
`IOT-S1-FIELD-VOCAB` (nivel fábrica).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Adoptar `{ name: Health, type: enum, values: [ok, degraded, down] }` en `message.fields` | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `product-run --factory iot --product fleet` PASS con el campo `Health` presente y probado (positivo+negativo).
2. `ci --rederive --all-products --factory iot` == pin (fleet re-pineado).

## Evidencia
Detalle completo en el companion de nivel fábrica (`IOT-S1-FIELD-VOCAB-INCREMENT.md §Evidencia`). Resumen:
`product-run --factory iot --product fleet` PASS con `Health` presente; `message_test.go` generado tiene
`TestValidHealthAcceptsDeclaredMember` + `TestValidHealthRejectsUnknownMember` (confirmado leyendo el archivo).
`ci --rederive --all-products --factory iot` 2/2==pin (`fleet/pinned_verdict.json` byte-idéntico — `proof_sha`
hashea `(station, checks exit)`, no contenido Go; ver nota en el companion).
