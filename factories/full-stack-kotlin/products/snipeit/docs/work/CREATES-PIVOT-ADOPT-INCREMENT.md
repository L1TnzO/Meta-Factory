<!-- meta:doc sha=8dca90854caf966d25d26d0a5b16ad5777aebef4 updated=2026-06-27T01:41Z -->
# Incremento CREATES-PIVOT-ADOPT

> **Doc de gobierno del PRODUCTO** (nivel `products/snipeit/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-23T19:21Z · cerrado 2026-06-23T19:38Z — ver §Evidencia). Todo cambio de `product.yml` vive acá (ADR-010).

## Objetivo
Adoptar FSK-CREATES-PIVOT en Snipe-IT: el verbo `Accessory.checkout` deja de ser sólo `decrements: qty` y pasa a
ser el M:N real (`creates: AccessoryCheckout`), insertando la fila del log de checkout de accesorios.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `Accessory.checkout` gana `creates: AccessoryCheckout`; la pivote gana `assigned_user_id`+`note` REQUERIDOS | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `product-run --product snipeit` PASS · RTM 24/25 · el server vivo (s9) INSERTA la fila pivote (sujeto + cuerpo). ✅
2. `ci --rederive snipeit` == pin (sin re-pin). ✅

## §Evidencia — CERRADO 2026-06-23T19:38Z
- `product.yml`: `Accessory.operations` = `[{ name: checkout, decrements: qty, creates: AccessoryCheckout }]`;
  `AccessoryCheckout` con `accessory_id` (FK-al-sujeto), `assigned_user_id` (FK al User, fail-closed) y `note` REQUERIDOS.
- Verde por bloqueo (compartido con el incremento de FÁBRICA FSK-CREATES-PIVOT §Evidencia): product-run PASS · RTM 24/25 ·
  diente de dos lados VIVO (degradar el `set(NOTE)` → sólo `[creates] round-trippea note` rojo, server UP) ·
  `ci --rederive snipeit` **11/11 == pin** (sin re-pin) · default/assets product.yml = 0.
- Gap faithful menor documentado: `note` se modeló REQUERIDO (Snipe permite NULL) para que entre al cuerpo del verbo;
  el target del checkout de accesorios es User (en Snipe-IT plenamente polimórfico User|Location|Asset — diferido al
  eje owner-poly / a una generalización del body-FK del `creates` a un target ≠ el dueño).
