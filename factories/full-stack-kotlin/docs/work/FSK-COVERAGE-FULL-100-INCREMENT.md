<!-- meta:doc sha=871b167047c68d47e3270fea55d1dfa19621d9e8 updated=2026-07-10T02:15Z -->
# Incremento FSK-COVERAGE-FULL-100

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-10T01:35Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Cerrar el residual final (~8 líneas, ~0.2%) que `FSK-COVERAGE-FULL` dejó declarado como "boilerplate jOOQ
sin ganancia proporcional" — pedido explícito del ingeniero ("haz esas 8 líneas de todos modos") — con
tráfico y asserts REALES, y re-derivar honestamente si 100% literal es alcanzable o si algo genuino queda.

## Lo que se encontró (2 capas)
1. **2 líneas reales más en `AppServer.kt`** (no contadas en el análisis anterior): las entidades PRIMARIAS
   `ol` (ownerless, Company) y `wr` (with-ref, Accessory) tienen su PROPIO bloque de proof dedicado
   (`OWNERLESS_PLURAL`/`WR_PLURAL` en `constants.py`), SEPARADO del loop `_SERVE_ALL_PROOF` — mi fix anterior
   sólo cubrió las 37 entidades del loop, dejando estas 2 (mismo gap: PUT no cableado → 404) sin cerrar.
2. **El resto (~6-7 líneas, todas en `Repository.kt`) NO era un gap de código — era un BUG del HARNESS**:
   el check `pyramid_integration` (s7, `kind: infra_up`) exige un diente de DOS LADOS por diseño (DES-9): el
   proof (`./gradlew integrationTest`) debe PASAR con la PG viva y debe FALLAR con la PG caída (prueba que
   depende de verdad de la infra). Gradle's jacoco extension para `Test` tasks NO acumula entre corridas
   (`append` ni siquiera existe ya como propiedad en Gradle 9.5.1 — se removió; confirmado con `javap` sobre
   el jar real) — la 2da corrida (PG muerta, falla rápido, cobertura chica) SOBREESCRIBE
   `build/jacoco/integrationTest.exec` de la 1ra corrida (PG viva, cobertura rica) ANTES de que
   `jacocoLiveReport` (s9) lo lea. Esto perdía la cobertura de `Repository.allAccessoryCheckouts` (sin ruta
   HTTP propia — su ÚNICA fuente de cobertura es `RepositoryIT`) cada vez que el pipeline automatizado
   (`product-run --mode harden`) corría. Diagnosticado por eliminación empírica: reproduje manualmente
   `integrationTest` UNA sola vez (sin el 2do lado) → **100.0000%** exacto (4205/4205, XML directo); agregué
   s2 (detekt+compileKotlin) al medio → seguía 100%; simulé el 2do lado (PG caída) → el `.exec` se achicó
   (232869→193631 bytes) y el % cayó, confirmando la causa.

## Mecanismo (3 cambios)
1. `constants.py` (bloque `OWNERLESS_PLURAL`, dentro del `if OWNERLESS_PLURAL:`): agregar `PUT
   {OWNERLESS_PLURAL}/{oid}` → 404 (mismo patrón que `_SERVE_ALL_PROOF`).
2. `constants.py` (bloque `WR_PLURAL`, dentro del `if WR_PLURAL:`): agregar `PUT {WR_PLURAL}/{wid}` → 404.
3. `factory.spec.yml` (`station_sequence` s7, check `pyramid_integration`, campo `proof`): tras
   `./gradlew integrationTest`, si pasa, `cp -f build/jacoco/integrationTest.exec
   build/jacoco/integrationTest_pass.exec` — backupea el `.exec` RICO a otro nombre ANTES de que el 2do
   lado (PG caída) lo pise; `jacocoLiveReport` globea `*.exec` y fusiona (JaCoCo mergea múltiples exec files
   nativamente — no hace falta "append", sólo no perder el archivo). El diente de dos lados de `infra_up`
   SIGUE intacto (la 2da corrida sigue debiendo fallar; sólo se preserva una copia de la 1ra).
   ⚠️ **Gotcha de nivel**: las estaciones VIVEN en `factory.spec.yml` (`domain.station_sequence`), NO en
   `stations/*.yml` — esos son OUTPUT materializado (`ensure_product_instance`/`_materialize_line`), editarlos
   directo no propaga y se pisan solos. Confirmado con `diff` antes/después de un `product-run`.

## Alcance (blast radius)
- `factories/full-stack-kotlin/codegen/scaffold/constants.py` (2 líneas de proof)
- `factories/full-stack-kotlin/factory.spec.yml` (1 campo `proof` de 1 check, s7)
- NO toca lógica de negocio Kotlin, NO toca `product.yml`, NO agrega rutas HTTP.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | PUT→404 en el bloque OWNERLESS primario (Company) | ✅ |
| 2 | PUT→404 en el bloque WITH-REF primario (Accessory) | ✅ |
| 3 | Diagnóstico del harness: aislar por qué el pipeline automatizado da 99.9% pero la reproducción manual da 100% | ✅ |
| 4 | Fix del harness: backup del `.exec` rico de `integrationTest` antes del 2do lado de `infra_up` | ✅ |
| 5 | Verificar: `product-run --mode harden` → `FSK_COVERAGE_LINE_PCT=100.0` reproducible vía el pipeline OFICIAL | ✅ |
| 6 | `ci --rederive --all-products` + `meta check` + docs | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `product-run --factory full-stack-kotlin --product snipeit --mode harden` reporta
   `FSK_COVERAGE_LINE_PCT=100.0` en `.proof/logs/s9-*.log` (el pipeline OFICIAL, no una reproducción manual).
2. `ci --rederive --factory full-stack-kotlin --all-products` 4/4 == pin.
3. `meta check` verde.
4. El fix del harness (`factory.spec.yml`) no debilita el diente de dos lados de `infra_up` — la 2da corrida
   (PG caída) sigue siendo REQUERIDA a fallar (la lógica de `infra_up` no cambió, sólo se agregó un `cp` que
   sólo corre si la 1ra corrida pasa).
5. Docs (`SNIPEIT-SPEC.md §11`, STATE/LOG meta+factory) reflejan el 100% real y el gotcha de harness encontrado.

## Evidencia (cierre, 2026-07-10)
1. `.proof/logs/s9-2026-07-10T0202Z.log`, `check=coverage_live exit=0`: stdout termina en
   `FSK_COVERAGE_LINE_PCT=100.0` — SIN líneas `FSK_COVERAGE_GAP` (el script sólo las imprime si `pct < 100.0`).
   `product-run --mode harden` completo PASS (s0..s11).
2. `ci --rederive --factory full-stack-kotlin --all-products` → **PASS**, 4/4 == pin:
   `full-stack-kotlin: 12/12` · `assets: 11/11` · `helpdesk: 11/11` · `snipeit: 12/12`, SIN re-pin
   (`proof_sha` deriva de exit-codes, no de contenido — el conjunto de checks en verde no cambió).
3. `meta check` → 19/19 verde.
4. Verificado por lectura: el `proof` de `pyramid_integration` sigue siendo `./gradlew integrationTest`
   como comando principal — el `&& cp ...` sólo se ejecuta si ese comando ya tuvo éxito (semántica `&&`); la
   2da invocación (con la PG caída, vía `infra_up`'s propio mecanismo down→re-proof) sigue fallando porque
   `integrationTest` en sí falla (no se cambió esa parte) — el `cp` simplemente no llega a correr en ese caso.
5. `SNIPEIT-SPEC.md §11` actualizado (100% real, criterio 9 ahora PASA completo). STATE/LOG (meta+factory).

**Nota de proceso**: el ingeniero pidió explícitamente cerrar las ~8 líneas restantes tras el cierre de
`FSK-COVERAGE-FULL`. El resultado NO fue "escribir más tests hasta llegar a 100" — fue encontrar que 2/8
líneas eran un gap de código real (mismo patrón ya conocido, aplicado a 2 entidades que el fix anterior
había pasado por alto) y que las otras ~6 NO eran un gap de código en absoluto sino un BUG DEL HARNESS DE
MEDICIÓN (el diente de dos lados de `infra_up` pisando su propio `.exec` bueno). Esta distinción importa:
si se hubiera "cerrado" el número agregando más aserciones GET sin diagnosticar la causa, el 100% habría
sido decorativo/inestable (dependiente de qué corrida se mida). El fix real fue de UNA línea (un `cp`) en
la definición de la estación, no en el código de negocio ni en tests nuevos — y preserva intacto el diente
de dos lados que `infra_up` existe para garantizar.
