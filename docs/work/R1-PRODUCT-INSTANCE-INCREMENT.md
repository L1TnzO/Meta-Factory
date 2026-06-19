<!-- meta:doc sha=3f3c4efdf2e1c27d83566627a6cb7e9699de81d7 updated=2026-06-19T23:56Z -->
# Incremento R1-PRODUCT-INSTANCE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-19T23:53Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
El motor pasa de **fábrica : 1 producto pineado** a **fábrica : N productos**: cada instancia de producto es
una entrada de dominio (`product.yml`) con su **propio** árbol de evidencia (`.proof/`/`build/`) y su **propio**
pin, regenerable independiente y coexistente con el demo — **mecanismo de sustrato** (general, sin nombrar
fábrica ni tech, ADR-012; promovido sólo en ≥2 dominios distintos, ADR-014). Cierra **R1** de ADR-015 / `ROADMAP §Fase R`.

## Diseño (la decisión de ingeniería, ojos propios)
- **Una instancia vive en `factories/<f>/products/<p>/`** y contiene como FUENTE committeada sólo dos archivos:
  `product.yml` (el subárbol `domain.product` — el único punto de variación entre productos) y
  `pinned_verdict.json` (su pin). Lo demás —`factory.spec.yml` efectivo, `stations/`, `build/`, `.proof/`— es
  **derivable** (gitignored): el sustrato lo re-materializa de `base-spec ⊕ product.yml` en cada corrida.
- **Seam mínimo en el motor (`chassis` vs `root`)**: una instancia corre con `root = products/<p>/` (donde viven
  su evidencia y su pin) pero su generador (`codegen/`) vive en el **chasis** = `factories/<f>/`. El único cambio
  de sustrato en `_generate` es **resolver el path relativo del `via` contra el chasis** (cwd sigue siendo el
  workdir; el scaffold lee/escribe por `METAFACTORY_ROOT`/`DEST` absolutos y sus assets por `__file__`). Para el
  producto **default** (chasis == root) el comportamiento es **byte-idéntico** (el `proof_sha` es exit-code-based;
  el generate es build-time, no afecta el pin).
- **El demo NO se migra (depth-first)**: el producto default sigue en la raíz de la fábrica (1:1 legacy intacto);
  las instancias `products/<p>/` **coexisten**. "≥2 productos" = default + ≥1 instancia; isolation = raíces `.proof/`
  separadas (borrar el proof de A no abre la gate de B, por construcción). La simetría total (demo como instancia
  #1) es follow-up limpio, no la pide R1.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Seam de sustrato**: `RunContext.chassis` (default=root) + `_generate` resuelve el `via` relativo contra el chasis. Test: generador en chasis, output en workdir distinto. Suite sin regresión (default byte-idéntico). | ⏳ |
| 2 | **Lifecycle de instancia**: `ensure_product_instance` (spec efectivo `base⊕product.yml` + materializar stations) + `_run_product_line`/`rederive_pinned`/`_pin_from_proofs` toman `(root, chassis)` + verbo `meta product {new,list}` + `--product` en product-run/ci/pin/rtm + `ci --rederive --all-products`. Test: 1 fábrica → 2 productos distintos, cada pin re-deriva; isolation. | ⏳ |
| 3 | **Gate con dientes**: check `products_rederive` (clon → re-deriva CADA instancia == su pin; negativo no-decorativo: pin tampereado → mismatch), cableado en m06 (N/A-pass sin instancias). **Co-validación en 2 dominios reales** (toolchains disjuntos): 2º producto en `iot` (Go) **y** en `full-stack` (TS); `ci --rederive --product` == pin en ambos; m06 verde con `products_rederive` activo; isolation VIVO por CLI. Anti-overfit: `git diff src/` = sólo mecanismo general (cero nombres de fábrica/tech). | ⏳ |
| 4 | **Cierre**: STATE «Ahora» + ROADMAP R1→✅ + LOG + sello ADR-015. `meta check` verde · `ci --rederive` de las 5 fábricas == pineado. `meta increment close`. | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. **≥2 productos por UNA fábrica**, cada uno `meta ci --rederive --product <p> == su pin` (re-derivado en árbol limpio).
2. **Isolation por bloqueo**: borrar el `.proof/` del producto A NO abre ni altera la gate del producto B (raíces separadas) — probado en test + VIVO por CLI.
3. **Gate con dientes**: `products_rederive` en m06 re-deriva cada instancia y BLOQUEA ante desvío; un pin tampereado cae a rojo (no-decorativo). N/A-pass honesto cuando la fábrica no tiene instancias.
4. **Co-validación ≥2 dominios** (ADR-014): el MISMO mecanismo instancia un 2º producto en `iot` (Go) **y** en `full-stack` (TS) — toolchains disjuntos.
5. **Anti-overfit (ADR-012)**: `git diff src/metafactory/ + seed/` contiene SÓLO mecanismo general — cero nombres de fábrica/tech; las instancias son DATA (`product.yml`).
6. **Sin regresión**: `meta check` verde · las 5 fábricas `ci --rederive == pineado` (el producto default byte-idéntico).
