# Incremento XENTITY-CYCLES-ADOPT — adoptar los ciclos cross-entidad en el blueprint de Snipe-IT

> **Doc de gobierno del PRODUCTO** (nivel `factories/full-stack-kotlin/products/snipeit/`, ADR-016).
> Estado: **CERRADO** (2026-06-22T15:42Z).
> Es el lado-PRODUCTO del par dual-nivel con la FÁBRICA `docs/work/FSK-XENTITY-CYCLES-INCREMENT.md`
> (el guard elige el lifecycle por la RUTA editada: el codegen es fábrica, el `product.yml` es producto).

## Objetivo
Re-habilitar en `products/snipeit/product.yml` los ciclos cross-entidad reales de Snipe-IT —
`Location.manager_id`→User y `Department.manager_id`→User— que estaban DIFERIDOS (quitados) porque el
migration en orden de declaración no admitía una FK a una tabla declarada DESPUÉS. Habilitado por el fix de
fábrica FSK-XENTITY-CYCLES (FK forward/cíclica como constraint DIFERIDA + seed NULL-then-UPDATE).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `Location.manager_id`→User (forward/cíclico, opcional) re-habilitado — cierra Location↔User | ✅ |
| 2 | `Department.manager_id`→User (forward/cíclico, opcional) re-habilitado — cierra User↔Department | ✅ |
| 3 | Comentarios del blueprint (restricción #1 relajada) + `SNIPEIT-DOMAIN.md §3 deferral 6/§4` actualizados | ✅ |

## Criterio de cierre (demostrable, no narrable) — TODOS ✅
1. `product.yml` declara `manager_id`→User en Location y Department, `required: false` (forward → opcional),
   en orden topológico (User declarado después → FK diferida, no agrega predecesor inválido). ✅
2. `product-run --product snipeit` **PASS** — el migration aplica las 2 FKs diferidas (ALTER) y el ciclo se
   siembra/round-trippea VIVO en s7 (`pyramid_integration` vs PostgreSQL viva). ✅
3. `ci --rederive --all-products` **11/11 == pin** para snipeit (proof_sha INTACTO, sin re-pin); default 12/12 +
   assets 11/11 == pin. ✅
4. `git diff` del `product.yml` del default + assets = 0 (sólo cambió el de snipeit, que ES la DATA del producto). ✅

## Evidencia
- **Cambio**: `products/snipeit/product.yml` — Location gana `{ name: manager_id, type: ref, to: User,
  required: false }`; Department gana lo mismo. Ambos son FORWARD (User declarado después) → el migration los
  emite como `ALTER TABLE … ADD CONSTRAINT … FOREIGN KEY … REFERENCES users (id)` al final, y el seed los
  cablea NULL-then-UPDATE. OPCIONALES por construcción (un lado del ciclo no tiene orden de siembra). La
  restricción #1 del header del blueprint se relajó (orden topológico → forward como FK diferida).
- **Verde** (2026-06-22): `product-run --product snipeit` PASS (s0→s11), RTM **24/25** (único UNSAT REQ-F-007 =
  s6 LLM keyless). `ci --rederive --all-products` 12/12·11/11·**11/11** == pin (proof_sha intacto, **sin re-pin**;
  `pinned_verdict.json` sin diff). `meta check` 6/6 (`generality` verde). Diente de dos lados VIVO (quité la
  constraint diferida del migration → **SÓLO** `pyramid_integration` rojo, hermanos s7 verdes; revertí→verde).
  `git diff src/+seed = 0` · default+assets product.yml = 0. Detalle: lado-fábrica
  `docs/work/FSK-XENTITY-CYCLES-INCREMENT.md §Evidencia`.
</content>
</invoke>
