---
name: r1-product-instance-done
description: R1 (lifecycle 1:N producto) cerrado; gotchas para R2 y para instanciar productos
metadata:
  type: project
---

**R1 ✅ (2026-06-19/20, `R1-PRODUCT-INSTANCE`)**: el motor es 1 fábrica : N productos. Una instancia vive en
`factories/<f>/products/<p>/`, commitea SÓLO `product.yml` (su `domain.product`) + `pinned_verdict.json`; el
sustrato re-deriva el resto. Verbo `meta product {new,list}` + `--product` en product-run/ci/pin/rtm. Gate
`products_rederive` (m06). Seam de motor: `RunContext.chassis`. Co-validado `iot/fleet` (Go) + `full-stack/tasks` (TS).

**Sigue R2** (expresividad de `domain.product`): ver [[spec-sota-roadmap]] y `ROADMAP §Fase R`.

**Gotchas (probados, no en código a primera vista)** — útiles para instanciar productos o elegir dominios de prueba:
- **Los scaffolds hardcodean el vocabulario de campos de su demo**: `iot` asume `DeviceID/Metric/Value/TS/FWVersion`;
  `full-stack` asume `title/done` (en `ui.ts`). Un 2º producto vía R1 varía nombre/package/topología pero DEBE
  respetar ese vocabulario hasta que R2 lo generalice. Campos arbitrarios ⇒ `go vet`/`tsc` rojo.
- **`dummy` NO sirve como dominio de instancia**: su línea de producto renderiza archivos FIJOS del chasis
  (`render src: factories/dummy/domain/greeting.py`), no el blueprint ⇒ una instancia sale idéntica al demo.
  Para probar el lifecycle usá fábricas con scaffold blueprint-driven (iot, full-stack, FSK, ASF).
- **Factories con línea LLM/live** (full-stack s3/s5, ASF s9/s10): una instancia nueva necesita generar+pinear el
  artefacto LLM una vez (§7, después `ci --rederive` es keyless), y diferir la estación live sin provider con
  `station_activation: {sN: off}` en `product.yml` (lo que el propio `live_run` sugiere; el YAML parsea `off`
  como bool → `_norm_activation` lo normaliza).
- **`infra_up` corre con un cwd-alias corto** (symlink /tmp) para que un socket-Unix derivado de `$PWD` quepa en
  el budget `sun_path` (108B) con workdirs de instancia más hondos. El path largo del repo (Integración/…) lo
  hacía tipar; no asumir que un socket bindea sólo porque el demo (path más corto) lo hace.
