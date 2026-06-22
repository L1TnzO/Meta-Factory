# Incremento CUSTOM-FIELDS-ADOPT

> **Doc de gobierno (nivel PRODUCTO `snipeit`, ADR-016).** Estado: **CERRADO** (2026-06-22T14:31Z).
> Creado 2026-06-22T14:11Z. La maquinaria GENERAL vive en la fábrica
> (`factories/full-stack-kotlin/docs/work/FSK-CUSTOM-FIELDS-INCREMENT.md`); este doc cubre sólo la ADOPCIÓN
> (el cambio en `products/snipeit/product.yml`).

## Objetivo
Snipe-IT adopta un **custom field con FORMAT** (FSK-CUSTOM-FIELDS, Avenue A): `Asset` gana
`{ name: mac_address, type: string, format: mac }` — el server vivo VALIDA el valor MAC a runtime.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `Asset.mac_address` (string, format: mac, requerido) en `product.yml` | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `product-run --product snipeit` **PASS** — el server vivo valida el MAC (valor inválido → 400; válido → 201). ✅
2. Diente de DOS lados VIVO (degradar `FMT_MAC`→`.*` → `access_control_live` rojo, hermanos verdes; revertir → verde). ✅
3. `ci --rederive --product snipeit` 11/11 == pin (`proof_sha` intacto, sin re-pin). ✅
4. `git diff` default+assets product.yml = 0; `git diff src/+seed = 0`. ✅

## Evidencia (CERRADO 2026-06-22T14:31Z)
- `product-run --product snipeit` **PASS** · RTM **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless). El server vivo
  (s9) rechaza un `mac_address` que no matchea el patrón MAC → 400 (fail-closed) y acepta uno válido → 201.
- **Diente de DOS lados VIVO**: `FMT_MAC` degradado a `.*` → `observability_live ok · access_control_live FAIL(1) ·
  frontend_consume_live ok` → revertí → **PASS**.
- `ci --rederive` snipeit **11/11** == pin (clon limpio); base 12/12 · assets 11/11 == pin. `meta check` **6/6**.
- `git diff` default+assets product.yml = 0; `git diff src/metafactory + seed = 0`. Pin snipeit intacto (sin re-pin).
- `mac_address` es REQUERIDO (un custom field requerido es expresable en Snipe-IT) → el server vivo lo lee del cuerpo
  (`_input_fields`) y el diente lo ejercita. Es el custom field canónico de Snipe-IT ("MAC Address", format MAC).

**Commit:** `feat(snipeit): Asset.mac_address format:mac (custom field con validación)`.
