<!-- meta:doc sha=04a3f4208486ce11b905df6afab079809e39557f updated=2026-07-08T17:33Z -->
# Incremento CHECK-WHEN-GUARD

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-08T17:33Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Dar al motor un **guard por-check `when:`** (DATO): un check se ejecuta sólo si su mapa `when` coincide con
la substitución efectiva; si no, se **saltea sin dejar rastro** en el veredicto. Es el análogo por-CHECK de
`station_activation` (que gatea a nivel estación). Habilita opt-ins byte-neutrales — un producto que no adopta
re-deriva un `proof_sha` **idéntico** (la ley del pin cuenta sólo los `(name,exit)` que corrieron). Es la
mitad META de `FSK-MODELGEN-DURABLE` (ADR-024): la superficie model-nativa la activa un flag `frontend_surface`
sin re-pinear a los productos-template. General y reusable por cualquier fábrica; no nombra dominio/tech (ADR-012).

## Diseño
- **`runner._check_active(check, subst)`**: `True` salvo que el check tenga `when: {k: v, …}` y algún `k` no
  matchee `subst[k]`. Se filtra en `run_station` ANTES de armar `cmds` → un check salteado no llega a
  `verify_station` → no aporta par `(name,exit)` → `compute_proof_sha` (seed) da el MISMO sha.
- **El flag ya fluye solo**: `spec.subst` aplana `domain.product`, y `product.yml` top-level → `domain.product`
  → `subst[<flag>]`. Cero cambios en `_subst_for`/loader. El schema no tiene `additionalProperties:false` y
  `resolve_check` lee claves fijas → la clave `when` es tolerada.

## Diente (two-sided, dogfooded)
`tests/` prueba, sobre el MISMO set de checks: (a) `when` que matchea → el check CORRE y su `(name,exit)` está
en el veredicto; (b) `when` que NO matchea → el check se SALTEA **y** el `proof_sha` es byte-idéntico al de
correr sin ese check (la invariancia del pin, no sólo la ausencia del check). Sin `when` → corre siempre
(no-op para todos los checks actuales → cero regresión en `meta check`).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `_check_active` + filtro en `run_station` (columna, ojos) | ⏳ |
| 2 | test two-sided (corre / saltea+pin-idéntico / no-op sin `when`) | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `meta check` verde (el guard es no-op para todos los checks sin `when` → cero regresión).
2. El test two-sided pasa: skip ⇒ `proof_sha` idéntico a la corrida sin el check; match ⇒ el check corre.
3. `git diff` acotado a `src/metafactory/engine/runner.py` + el test (no toca fábricas).
