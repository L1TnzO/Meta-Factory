<!-- meta:doc sha=58611c69982c44fa157c0ec81ff19c65fb8740a5 updated=2026-07-03T02:45Z -->
# Incremento FSK-MUTABLE-WHEN

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-03T02:44Z) (creado 2026-06-28T01:03Z). Cierre formal
> des-diferido por el bonus de INC-2 `HARNESS-FAST-GATE` (COST-DOWN): el re-pin de no-adoptantes que necesitaba
> JDK 21 ya está hecho (`tools/toolchain.sh` garantiza el toolchain). Todo cambio de código vive acá (ADR-010).

## Objetivo
Un eje R2 nuevo de FSK: **guard de mutación por estado** (`mutable_when`) — una fila en un estado
"congelado" rechaza PUT/DELETE genéricos (no las operations declaradas, que SON la vía legítima de mover el
estado). Cierra el hueco "no se puede editar/borrar un activo desplegado / un ticket cerrado", que los
workflows (s12) NO cubren (sólo gobiernan la transición del propio campo-enum). Compone sobre auth→RBAC→
ownership (la mutación va SIEMPRE detrás del veredicto). Opt-in: sin la flag, byte-idéntico.

> **Por qué este incremento existe (meta):** primer build de fábrica DRIVEADO por el arnés verificar-no-revisar
> ya ENCENDIDO (DELEGATION-ACTIVATION, ADR-020) → MIDE el payoff real de la SOTA. Opus diseña el contrato y lee
> SÓLO el veredicto; el `writer` (Sonnet) implementa el bulk; al cierre `meta metrics` da el split delegación/costo.

## Gramática (DATA en `domain.product`, opcional, por-entidad)
```yaml
mutable_when: { field: status, not_in: [deployed] }   # XOR `in: [...]` — los estados MUTABLES
```
`field` = un campo enum de la entidad (workflow o enum plano). Semántica: PUT/DELETE sobre una fila cuyo
`field` ∉ el set mutable → **409**. Conjunto mutable type-bound al enum del contrato (DES-6). Producto elegido:
**snipeit** `Asset` (`{field: status, not_in: [deployed]}`) — el ÚNICO con operations (checkout ready→deployed)
para alcanzar el estado congelado a runtime y probarlo VIVO.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Contrato + alcance (Opus): gramática, semántica, seam (`modifyVerdict`→`current`→`conflict()`), blast-radius | ✅ |
| 2 | Codegen del slot (writer/Sonnet, verificar-no-revisar): helper+guard+`x-mutable-when`+route_check mode+proof vivo+shape-teeth+capability+product.yml | ✅ |
| 3 | Verificación (Opus): re-pin no-adoptantes + `ci --rederive --all-products`==pin (4/4) + `meta check` | ✅ |
| 4 | Medición del payoff: `meta metrics` (split delegación/costo — 159k tok a Sonnet, ver DELEG-PAYOFF-MEASURE) | ✅ |

## Cierre (2026-07-03, des-diferido por INC-2 HARNESS-FAST-GATE)
El único blocker del cierre formal era JDK 21 para re-pinear a los no-adoptantes (`s5` ganó el check
`mutability_enforced` → su `proof_sha` cambió; los pins de `base`/`assets`/`helpdesk` quedaron rancios). Con
`tools/toolchain.sh` (INC-2) garantizando JDK 21 + docker vivo:
- Re-derivado foreground cada no-adoptante → `s5` verde con sha nuevo `bbb840dd` (idéntico entre ellos: el `s5`
  sin `mutable_when` es byte-idéntico) → `meta pin` (diff s5-only) en `base`, `assets`, `helpdesk`. `snipeit`
  ya estaba correcto (adoptante).
- **`ci --rederive --factory full-stack-kotlin --all-products` == pin 4/4** (base 12/12 · assets 11/11 ·
  helpdesk 11/11 · snipeit 11/11) — la re-derivación independiente de dos-verificadores, con el stack real
  (JDK 21 + gradle + docker PG/AppServer). RTM FSK COMPLETE (27/27).

## Criterio de cierre (demostrable, no narrable)
1. **Vivo de dos lados** (snipeit s9 `access_control_live`): activo `ready`→PUT 200 · checkout→`deployed`→PUT 409 + DELETE 409 · (checkin→PUT 200). Diente embebido: saboteado el guard, `deployed` PUT→200 → ROJO.
2. **Estático**: `route_check.py` modo `mutability` cruza `x-mutable-when` (contrato) ↔ el set Kotlin; tamper de un lado → `MUTABILITY_MISMATCH`.
3. **Shape-tooth fail-closed**: `mutable_when` malformado (field ausente / no-enum / `in`&`not_in` juntos / valor fuera del enum) → scaffold exit 1.
4. `meta product-run --product snipeit` PASS · `ci --rederive --product snipeit` == pin (re-pineado) · RTM snipeit +1 (`mutation_frozen`/REQ-F-0xx) · `meta check` N/N · **`git diff src/metafactory/ + seed/` = 0** (todo en `codegen/`+`tools/`+spec+product.yml) · `assets`/`helpdesk` byte-idénticos (opt-in).
5. Payoff MEDIDO: `meta metrics` reporta el split delegación/costo de este incremento (el writer hizo el bulk; Opus quedó chico).
