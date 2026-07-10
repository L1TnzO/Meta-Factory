<!-- meta:doc sha=15e52ce6a64531ada961ac9f1a57a4929f98ddd4 updated=2026-07-10T23:51Z -->
# Incremento REQCOUNCIL-DOCS-HOME-FIX

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-10T23:51Z) (creado 2026-07-10T23:44Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Residuo descubierto en la EJECUCIÓN de `REQCOUNCIL-ADOPT` (ambos niveles ya CERRADOS): el sustrato
`docs_manifest.doc_homes()` trata CUALQUIER `factories/<f>/products/<p>/` con un `docs/` como un
doc-home ADR-009 sellable — generalizando de más. Para un producto R1 real eso es correcto (sus docs
son AUTORADOS por/para el Meta-Factory), pero ReqCouncil es un producto **adoptado, copiado-no-emitido,
deliberadamente SIN `product.yml`** (PROVENANCE.md): su `docs/` es contenido AJENO (41 docs propios de
ReqCouncil, copiados byte-a-byte del pin @89ad45b). `docs_manifest.sync()` (corrido en cada `increment
open/close`) ESTAMPÓ un sello Meta-Factory (`<!-- meta:doc sha=... -->`) en los 41 — rompiendo la
promesa de copia byte-idéntica de `PROVENANCE.md` — y además hizo que `_state_fresh_problem` marque
`products/reqcouncil/docs/STATE.md` (ajeno, congelado) como "posiblemente stale" cada vez que el ÚNICO
doc propio del Meta-Factory ahí adentro (`docs/work/REQCOUNCIL-ADOPT-INCREMENT.md`, el incremento
anidado) se toca — `meta check` cae a 19/20 de forma recurrente y no auto-sanable. Este incremento
cierra el gap: `doc_homes()` sólo reconoce `products/<p>/` como home sellable cuando `p` lleva
`product.yml` (el MISMO signal que ya usa `_list_products`/R1 — reuso, no vocabulario nuevo; DATA-
agnostic, ninguna fábrica/producto se nombra) — y restaura los 41 docs de ReqCouncil a byte-idéntico.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `doc_homes()` (`src/metafactory/docs_manifest.py`): excluir `products/<p>/` sin `product.yml` | ✅ |
| 2 | Restaurar los 41 docs de `products/reqcouncil/docs/**.md` a byte-idéntico del pin @89ad45b (quitar el sello inyectado) — el doc NUEVO propio (`docs/work/REQCOUNCIL-ADOPT-INCREMENT.md`) NO se toca | ✅ |
| 3 | Test nuevo (`test_docs_manifest.py`) + fixture existente actualizada (ahora lleva `product.yml`, era el gap real que el fixture no representaba) | ✅ |
| 4 | `meta check` verde (20/20); `INDEX.md` sin cambios (ya no listaba factories/products — sólo el home meta) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. ✅ `doc_homes(repo_root)` ya no incluye `factories/agent-systems-factory/products/reqcouncil` (verificado
   por invocación directa); un producto R1 CON `product.yml` (`helpdesk`/`snipeit`/`fleet`) sigue incluido —
   no regresión.
2. ✅ `diff -rq` contra `git archive 89ad45b -- docs` → vacío para los 41 docs copiados (única diferencia:
   el work-doc nuevo, que no existía upstream).
3. ✅ `pytest tests/test_docs_manifest.py` → 31/31 (30 preexistentes adaptados a la fixture con
   `product.yml` + 1 nuevo cubriendo el caso adoptado-sin-`product.yml`).
4. **Corrección al criterio original**: NO fue posible llegar a 20/20 sin tocar `docs/STATE.md` de
   `agent-systems-factory` — esa staleness es un residuo INDEPENDIENTE de este incremento (el patrón de
   2-commits feat+cierre de `REQCOUNCIL-ADOPT` dejó su STATE.md con commit más viejo que su work-doc de
   cierre). Se resolvió agregando una línea honesta a ese STATE («incremento CERRADO») — información NUEVA
   real, no un touch hueco. `meta check` → 20/20 tras commitear.
