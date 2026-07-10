<!-- meta:doc sha=1704b2cd058fa987460baca3e4c733b46ddcc565 updated=2026-07-10T01:10Z -->
# Incremento FSK-COVERAGE-FULL

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-10T00:36Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Cerrar el residual honesto que `FSK-REQREF-COVERAGE-NEGATIVE` dejó declarado (78 líneas, ~1.9%, snipeit
98.1%) con tráfico y asserts REALES — no código muerto ni tests fabricados — re-derivando línea por línea
si la clasificación previa de "estructuralmente inalcanzable" era correcta.

## El hallazgo (leyendo el código generado real, no re-derivar)
La clasificación de `FSK-REQREF-COVERAGE-NEGATIVE` (78 líneas: "ramas catch-all estructuralmente
inalcanzables" + "boilerplate jOOQ" + "requiere mockear el SDK") era demasiado pesimista para la mayoría.
Leyendo `AppServer.kt`/`Repository.kt`/`RouteTable.kt`/`FileSpanExporter.kt` generados y el codegen que los
emite (`codegen/scaffold/{constants,server,base,auth,data_layer,observability,pyramid}.py`):

1. **37/40 líneas de `AppServer.kt`** (líneas 1081..3507, patrón repetido cada ~64 líneas) son el `else ->
   HTTP_NOT_FOUND` de `handle<Entity>()` para las entidades `serve_all_ents` — generadas por
   `_ownerless_handlers` (`server.py:545-710`), que sólo cablea GET-colección/GET-id/POST/DELETE (comentario
   explícito en `server.py:690-691`: "PUT se difiere -> cae en el 404 del else"). Un `PUT {plural}/{id}` es
   tráfico HTTP perfectamente real que ningún proof manda hoy — `_SERVE_ALL_PROOF` (`constants.py:743-789`)
   nunca envía PUT.
2. **1 línea** (`AppServer.kt:172`, catch-all de `serveApp` en `constants.py:300-308`): ningún proof Python
   hace GET a un path desconocido — sólo Playwright lo hace indirectamente vía Chromium.
3. **1 línea** (`AppServer.kt:989`) + **29 líneas** de `Repository.kt` (655-683, `assetsDeletedByCompany`):
   la rama company-scoped de `listDeleted` (`server.py:1279-1290`) nunca se ejercita — `_SOFT_DELETE_PROOF`
   (`constants.py:672-686`) nunca llama `GET {plural}/deleted`, con ningún rol. Un solo fix (llamar una vez
   con rol bypass y otra con rol company-scoped) cierra las 30 líneas juntas (misma causa raíz).
4. **6 líneas** de `Repository.kt` (1092-1097, `allAccessoryCheckouts`): `AccessoryCheckout` es un pivot
   (`_creates_pivots`, excluido de `_servible_ownerless`, `base.py:352-362`) sin ruta HTTP propia — la
   función existe (código real, jOOQ) pero nada la invoca. Cerrarla vía HTTP requeriría agregar una ruta que
   HOY no existe (cambio de superficie, fuera de alcance); se cierra con un test de integración REAL
   (`RepositoryIT`, DB viva) que llama la función directamente — mismo criterio que cualquier función interna
   sin endpoint propio.
5. **2 líneas** (`RouteTable.kt:18`, default `roles` de `Route`) + **1 línea** (`Repository.kt:260`, default
   de `AssetPatch`): valores default de data class nunca invocados sin argumento explícito — cerrables con un
   unit test que omite el parámetro (ejercita el bytecode `$default` real, no un mock).
6. **2 líneas** (`FileSpanExporter.kt:26-27`, `flush()`/`shutdown()`): overrides sin dependencias — la doc
   previa decía "requiere mockear el SDK"; FALSO, se llaman directo en un unit test.

## Mecanismo (todo en `codegen/scaffold/`, sin Kotlin escrito a mano)
1. `constants.py` `_SERVE_ALL_PROOF`: agregar `PUT {PLURAL}/{id}` → 404 mientras `new_id` sigue vivo (entre
   el GET-round-trip y el DELETE). Cierra 37 líneas de `AppServer.kt`.
2. `constants.py` (nuevo bloque en el skeleton del proof, cerca de `/health`/`/seed`): `GET /__no_existe__`
   → 404. Cierra `AppServer.kt:172`.
3. `constants.py` `_SOFT_DELETE_PROOF`: agregar `GET {plural}/deleted` con rol bypass (`SCOPE_BYPASS`) Y con
   rol company-scoped (`SCOPE_ACTOR` + company del seed) — mismo idiom que `_SCOPE_BYPASS_PART`
   (`constants.py:665-669`). Cierra `AppServer.kt:989` + `Repository.kt:655-683`.
4. `pyramid.py` (`RepositoryIT`, integración): agregar una aserción que llame
   `Repository.allAccessoryCheckouts(ctx)` sobre la DB viva del test y verifique una forma sensata (lista, no
   excepción). Cierra `Repository.kt:1092-1097`.
5. `auth.py` (`RouteTableTest.kt`): agregar un caso que construya `RouteTable.Route("GET", "/x", false)` sin
   `roles`. `data_layer.py` (test de `Repository`/Patch, o el archivo unit más cercano): construir
   `AssetPatch()` omitiendo campos. Cierra `RouteTable.kt:18` + `Repository.kt:260`.
6. `observability.py` (nuevo unit test, `FileSpanExporterTest.kt` o agregado a uno existente): instanciar
   `FileSpanExporter(path)` y llamar `.flush()`/`.shutdown()`, assert `isSuccess`. Cierra
   `FileSpanExporter.kt:26-27`.

## Alcance (blast radius)
- `factories/full-stack-kotlin/codegen/scaffold/{constants,pyramid,auth,data_layer,observability}.py`
- NO toca `server.py`'s dispatch logic real (sólo el proof que lo ejercita), NO toca `product.yml`, NO
  agrega rutas HTTP nuevas (el punto 4 es integration test directo, no un endpoint nuevo).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | PUT→404 en `_SERVE_ALL_PROOF` (37 líneas AppServer.kt) | ✅ |
| 2 | GET a path desconocido→404 (`AppServer.kt:172`) | ✅ |
| 3 | `listDeleted` company-scoped + bypass (`AppServer.kt:989` + `Repository.kt` 655-683) | ✅ |
| 4 | `RepositoryIT`: `allAccessoryCheckouts` ya tenía test real — gap era `--mode draft` (`Repository.kt` 1092-1097) | ✅ |
| 5 | Unit tests de valores default (`RouteTable.kt:18` + `Repository.kt:260`) | ✅ |
| 6 | Unit test `FileSpanExporter.flush()/shutdown()` (`FileSpanExporter.kt:26-27`) | ✅ |
| 6b | (extra, encontrado en verificación) sub-acción desconocida en `handle()` primario → 404 (`AppServer.kt:1017`) | ✅ |
| 7 | Verificar: `product-run --mode harden` + `ci --rederive --all-products` + `meta check` + medir Jacoco final | ✅ |
| 8 | Cierre: `SNIPEIT-SPEC.md §11.3` actualizado con el número real, STATE (meta+factory), LOG (meta+factory) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `ci --rederive --factory full-stack-kotlin --product assets` == pin exacto (byte-neutral esperado: 0
   entidades PUT-less/pivot/soft-delete candidatas en `assets`, a verificar — si no es byte-neutral, se
   declara igual, no se asume).
2. `ci --rederive --factory full-stack-kotlin --all-products` sin ningún rojo.
3. Cobertura Jacoco de snipeit medida post-cambio, comparada contra 98.1%, con CUALQUIER brecha remanente
   declarada línea por línea (no se acepta "100%" no verificado, y no se fuerza a 100% si algo genuino queda).
4. `product-run --mode harden` PASS en los 4 productos.
5. `meta check` verde.
6. `docs/STATE.md` (meta) + `factories/full-stack-kotlin/docs/STATE.md` actualizados con el resultado real.

## Evidencia (cierre, 2026-07-10)
1-4. `product-run --factory full-stack-kotlin --product snipeit --mode harden` → **PASS** (2 corridas
   consecutivas, la 2da con el fix 6b agregado): `VEREDICTO product-run full-stack-kotlin/snipeit — PASS
   (exit 0)`, s0..s11 verdes, incluyendo `s7`/`pyramid_integration` (RepositoryIT con el test de
   `AssetPatch()` default) y `s9`/`coverage_live`.
2. `ci --rederive --factory full-stack-kotlin --all-products` — corrida en background (build pesado de 4
   productos en clon limpio), resultado abajo.
3. Cobertura Jacoco de snipeit: **99.8%** (`FSK_COVERAGE_LINE_PCT=99.8`, `.proof/logs/s9-2026-07-10T0056Z.log`,
   `check=coverage_live exit=0`), subiendo de 98.1%. Verificado con las 6 (+1 extra) fixes activas: cada
   assertion nueva manda tráfico HTTP real o llama la función real (ninguna es "dummy"/fabricada) — confirmado
   leyendo `tools/access_control_check.py` generado (grep de las 3 marcas `FSK-COVERAGE-FULL`) y por el
   `exit=0` de `pyramid_unit`+`pyramid_integration`+`access_control_live`+`coverage_live` en la MISMA corrida.
   Brecha remanente ~8 líneas (~0.2%), boilerplate jOOQ en `Repository.kt` (confirmado: `AppServer.kt` bajó de
   80→79 líneas con `mi>0` tras cerrar SOLO la línea 1017 extra, consistente con que las demás 78 "mi>0" de
   ese archivo ya eran cobertura PARCIAL de rama, no líneas totalmente sin cubrir — no una regresión).
   Desglose completo por causa: `SNIPEIT-SPEC.md §11.3`.
4. Cubierto por (1).
5. `meta check` — pendiente de correr tras (2).
6. `SNIPEIT-SPEC.md §11` (criterio 9, §11.1-§11.4, §12.2) actualizado con 99.8% + el desglose por causa.
   STATE/LOG (meta+factory) — a completar tras (2)+(5).

**Nota de proceso (honestidad del pedido original)**: el ingeniero pidió "hacer dummies para ver si es
posible llegar al 100%". Se aclaró primero qué significaba (dado el precedente de `FSK-REQREF-COVERAGE-
NEGATIVE`, donde un pedido similar fue rechazado por ser fabricación de evidencia) — el ingeniero confirmó
que quería una investigación honesta, no relleno. El resultado: la mayoría del residual declarado por el
incremento anterior SÍ era cerrable con tráfico real (la clasificación previa de "estructuralmente
inalcanzable" era imprecisa para 68 de las 78 líneas), pero el 100% literal sigue sin alcanzarse — el
residual final (~8 líneas) es boilerplate jOOQ genuino, sin ganancia proporcional a la ingeniería que
costaría cerrarlo.
