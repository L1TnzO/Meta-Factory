<!-- meta:doc sha=1ded91bf8769934ee21996d06ff361efdd10a66f updated=2026-06-27T01:41Z -->
# Incremento OWNER-POLY-ADOPT

> **Doc de gobierno** (nivel PRODUCTO `factories/full-stack-kotlin/products/snipeit/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-23T23:34Z · cerrado 2026-06-24T00:30Z). La maquinaria GENERAL vive en el incremento de FÁBRICA
> `FSK-OWNER-POLY`; este incremento es la ADOPCIÓN del producto (sólo `product.yml`).

## Objetivo
`Asset.assigned_user_id` → `assigned_to` poly `[User, Location, Asset]`, sigue siendo `owned_by` — cierra el
wrinkle #3 (el `owned_by` ahora cruza una UNIÓN). Faithful a `assets.assigned_type+assigned_to` de Snipe-IT REAL.

## Decisión de modelado
- `assigned_to` ES el owner-poly. El POST lo fija a `(type=User, id=principal del token)`; una asignación a un
  tipo NO-principal (Location/Asset) ≡ RTD → sólo bypass modifica.
- `checkout_target` (poly, no-dueño) + las operaciones `checkout`/`checkin` quedan **INTACTAS**: acoplar "el verbo
  reasigna al dueño" con el control de acceso por-principal es un eje BEHAVIORAL aparte (rompería el proof de
  operaciones — el dueño cambiaría y no podría hacer checkin; y semánticamente el editor de un activo ≠ su holder).

## Evidencia de cierre (demostrable, no narrable)
1. `git diff product.yml ≠ 0` (la adopción); `default`/`assets` `product.yml = 0` (eje OPT-IN).
2. **product-run --product snipeit PASS** · **RTM snipeit 24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
3. **Diente de DOS lados VIVO** (proof manual sobre PG): degradar el gate de tipo en `modifyVerdict` → la fila
   asignada a una Location se vuelve "del actor" → "PUT fila RTD por no-bypass → 403" se vuelve 200, SÓLO en
   `access_control_live` (s9), server VIVO, hermanas verdes → revertí → verde.
4. **`ci --rederive` snipeit == pin** (sin re-pin — `proof_sha` intacto). `SNIPEIT-DOMAIN.md` actualizado (wrinkle #3).
