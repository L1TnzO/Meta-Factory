<!-- meta:doc sha=67af5e2ae44c1df8af9958347f6006d71b62ab21 updated=2026-06-20T00:28Z -->
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
| 1 | **Seam de sustrato**: `RunContext.chassis` (default=root) + `_generate` resuelve el `via` relativo contra el chasis. Test: generador en chasis, output en workdir distinto. Suite sin regresión (default byte-idéntico). | ✅ (`7f484ce`) |
| 2 | **Lifecycle de instancia**: `ensure_product_instance` (spec efectivo `base⊕product.yml` + materializar stations) + `_run_product_line`/`rederive_pinned`/`_pin_from_proofs` toman `(root, chassis)` + verbo `meta product {new,list}` + `--product` en product-run/ci/pin/rtm + `ci --rederive --all-products`. `infra_up` con cwd-alias corto (budget sun_path para workdirs hondos). Test: 1 fábrica → 2 productos distintos, cada pin re-deriva; isolation. Dominio 1 (Go): `iot/fleet`. | ✅ (`0b79775`) |
| 3 | **Gate con dientes**: check `products_rederive` (clon → re-deriva CADA instancia == su pin; negativo no-decorativo: pin tampereado → mismatch), cableado en m06 (N/A-pass sin instancias). **Co-validación 2 dominios disjuntos**: `iot/fleet` (Go) **y** `full-stack/tasks` (TS, s3 claude pineado §7, s5 diferido honesto); `ci --rederive --product` == pin en ambos (keyless); m06 iot verde en secuencia con `products_rederive`; isolation + negativo VIVOS por CLI. `station_activation` override (la instancia difiere honestamente una estación live sin provider — lo que el propio `live_run` sugiere). Anti-overfit: `git diff src/+seed` = ~287 líneas, **cero nombres de fábrica/tech**, seed intacto. | ✅ |
| 4 | **Cierre**: STATE «Ahora» + ROADMAP R1→✅ + LOG + sello. `meta check` verde · `ci --rederive` default == pineado. `meta increment close`. | ✅ |

## Criterio de cierre (demostrable, no narrable) — TODOS verdes
1. ✅ **≥2 productos por UNA fábrica**: `iot` (default 5/5 + `fleet` 5/5) y `full-stack` (default 6/6 + `tasks` 5/5), cada `meta ci --rederive --product <p> == su pin` en árbol limpio.
2. ✅ **Isolation por bloqueo**: VIVO — `rm -rf factories/iot/products/fleet/.proof` → `ci --rederive --factory iot` (default) sigue 5/5; raíces `.proof/` separadas. Test `test_products_are_isolated`.
3. ✅ **Gate con dientes**: `products_rederive` (m06) re-deriva cada instancia == su pin en clon limpio y BLOQUEA ante desvío; pin tampereado → rojo (no-decorativo); N/A honesto sin instancias. iot pasa **m00..m06 en secuencia**. Tests `test_products_rederive_gate` / `_na_without_instances`.
4. ✅ **Co-validación 2 dominios disjuntos** (ADR-014): el MISMO mecanismo instancia `iot/fleet` (Go) **y** `full-stack/tasks` (TS, keyless) — toolchains disjuntos.
5. ✅ **Anti-overfit (ADR-012)**: `git diff src/+seed` ~287 líneas, **cero nombres de fábrica/tech** (grep verde); seed intacto; instancias = DATA (`product.yml`).
6. ✅ **Sin regresión**: `meta check` verde · suite 573 · `ci --rederive` default == pineado (iot 5/5, full-stack 6/6, dummy 5/5 — el seam no rompe el 1:1).

## Diferido honesto (NO fingido)
- **Migrar el demo a instancia #1** (simetría total default↔instancia): R1 probó coexistencia default+instancia + isolation, que es la claim mínima honesta; la migración destructiva de las pins de 4 fábricas es follow-up, no la pide R1.
- **Expresividad de `domain.product` (R2)**: el scaffold de `iot`/`full-stack` hardcodea el vocabulario de campos de su demo (un 2º producto varía nombre/package/topología, no campos arbitrarios). Es contenido por-fábrica (ADR-015 §4), un eje separado.
- **Factories con línea LLM/heavy** (full-stack s5, ASF, FSK): instancian con key/pin (§7) o `station_activation:off` (deferral honesto que el propio gate sugiere) — config de instancia, no límite del mecanismo.
