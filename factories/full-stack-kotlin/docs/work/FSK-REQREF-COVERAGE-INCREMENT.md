<!-- meta:doc sha=83395a8abe8ce99c886541547ab08b13b88bfc3a updated=2026-07-09T22:52Z -->
# Incremento FSK-REQREF-COVERAGE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-09T20:59Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Cerrar el residual declarado de `FSK-COVERAGE-INSTRUMENT`/`SNIPEIT-MIN-COMPLIANCE` §11.3: hoy
`access_control_check.py` (el proof e2e que `s9` corre contra el server vivo) sólo ejercita HTTP real de
**una** entidad ownerless-con-ref-requerido (`_live_with_ref`, la `wr`) — TODAS las demás quedan **excluidas
por diseño** ("wrinkle #1"), y sus handlers en `AppServer.kt`/`Repository.kt` nunca reciben tráfico →
0% de cobertura Jacoco pese a ser código real. Extender el generador para que TAMBIÉN siembre FKs
encadenadas y ejercite CRUD real sobre esas entidades — capacidad de SUSTRATO (afecta a toda la fábrica,
no un parche de snipeit) — es lo que este incremento construye.

**Es COLUMNA-adyacente** (generador compartido por 3 productos + cualquier producto futuro, "riesgo genuino
de regresión" ya declarado 2 veces) → diseñado con ojos propios (S1, este doc); la implementación puede
ejecutarse en una sesión S2 siguiendo el diseño AL DETALLE de abajo (no requiere re-descubrir nada, sólo
ejecutar los pasos).

## El hallazgo (medido, no supuesto — no re-derivar, ya está acá)
Con un script Python one-off (`_subst_for` + `scaffold.server._live_with_ref`/`_is_poly`) sobre los 4
productos vivos, la cuenta de entidades ownerless-con-ref-requerido EXCLUIDAS (más allá de la única `wr`
que ya cubre el generador):

| Producto | Entidades totales | `wr` elegida | Excluidas (más allá de `wr`) |
|---|---:|---|---:|
| `assets` | 2 | (ninguna) | **0** — byte-neutral garantizado |
| demo (factory.spec.yml raíz) | 3 | (ninguna, Task→Project no es "seedable" por sí, ver abajo) | **1** (`Task`) |
| `helpdesk` | 5 | (ninguna) | **1** (`Comment`) |
| `snipeit` | 39 | `Accessory` (tiene qty-ops, preferida) | **19**: `AssetModel, License, LicenseSeat, AccessoryCheckout, Consumable, ConsumableAssignment, Component, ComponentAssignment, Maintenance, CustomField, CheckoutRequest, GroupUser, CustomFieldsetField, KitModel, KitAccessory, KitConsumable, KitComponent, CheckoutAcceptance, CompanyUser` |

Esto confirma: (a) es un gap GENERAL de la fábrica, no específico de snipeit (hasta el demo lo tiene); (b)
`assets` queda byte-neutral SIEMPRE (0 candidatas); (c) snipeit es donde el gap pesa (19/39 entidades =
la mayoría del ~29% remanente de `AppServer.kt`+`Repository.kt`).

**Caso peligroso ya identificado** (por qué `_live_with_ref` hoy exige `_ref_target_seedable`, es decir
targets SIN su propio ref requerido): si un target de ref requerido es a su vez una entidad con `owned_by`
(caso demo `Task→Project`, `Project.owner_id` requerido), sembrarlo con el `_seed_chain` genérico (sin
`owner_field`/`owner_var`) **explota** (`raise SystemExit`, línea 127 de `server.py` — "ref requerido
no-dueño sin cableado"), porque el campo dueño de `Project` no está en `ref_wiring` ni se pasa `owner_field`.
Medido con un script de clausura transitiva sobre snipeit: de las 19 excluidas, **4 tocan la entidad
`owned` (`Asset`) en su clausura** (`ComponentAssignment`, `Maintenance`, `CheckoutRequest`,
`CheckoutAcceptance` — esta última vía `CheckoutRequest`); **ninguna toca una entidad `owned_by` DISTINTA**
de `Asset` (snipeit sólo tiene una: `Asset`). Por eso el mecanismo de abajo sólo necesita "primar" el
registry con la entidad `owned` (y el `owner_ent` principal) — no un caso general de owned_by arbitrario.

## Mecanismo (diseño concreto — reusa infraestructura YA EXISTENTE, no inventa una nueva)
`server.py` ya tiene un seeder transitivo GENÉRICO, con memoización + detección de ciclos, construido para
`FSK-OWNED-REQUIRED-REFS` (los refs requeridos del `owned`): `_seed_deps(e, by, registry, visiting, lines)`
+ `_ensure_seeded(t, by, registry, visiting, lines)` (líneas 135–167). Generalizarlo a las 19 (o N)
entidades excluidas es **reusarlo con un registry "primado"**, no reescribirlo:

1. **Primar el registry.** Después de `owned_wiring = _seed_deps(owned, by, dep_registry, set(), dep_lines)`
   (línea 1053, ya existe), copiar `dep_registry` (que YA tiene, transitivamente, todo lo que `owned`
   necesitó — p.ej. en snipeit ya trae `AssetModel`, `Category`, `Depreciation`, porque `Asset.model_id` es
   un ref requerido) y agregarle DOS entradas manuales: `{owned["name"]: "ownedId", owner_ent["name"]:
   "ownerId"}` (las vars YA sembradas por el código existente, líneas 1115/1117). Esto es lo que resuelve el
   caso `Asset` de arriba sin re-sembrar ni tocar el seeding especial de `owned`.
2. **Para cada entidad excluida `e`** (ownerless, `_has_req_ref(e)`, `e is not ol`, `e is not wr`): llamar
   `wiring_e = _seed_deps(e, by, primed_registry, set(), new_lines)`. Esto YA maneja recursión (un target
   que a su vez tiene refs requeridos, p.ej. `KitModel→AssetModel→{Category,Depreciation}`, se resuelve
   solo) Y dedup automático (si dos excluidas comparten un target — p.ej. varias apuntan a `Category` — o si
   una excluida ES target de OTRA — `CustomFieldsetField→CustomField`, y `CustomField` TAMBIÉN está en la
   lista de excluidas — el registry compartido evita el doble-insert: cualquier orden de iteración funciona,
   `_ensure_seeded` memoiza). **No hace falta sembrar una fila de `e` misma** — sólo su `wiring` (los ids de
   sus targets) para el POST del proof; si `e` es AL MISMO TIEMPO target de otra excluida, esa OTRA llamada
   ya la siembra vía `_ensure_seeded` (dentro de `_seed_deps`) y la deja en el registry para reuso.
3. **Exponer por `/seed`.** Nuevo campo `withRefs: Map<String, Map<String, Long>>` (Kotlin), paralelo a
   `ownedRefs` (que es para UNA sola entidad) pero **keyeado por nombre de entidad** — `{"AssetModel":
   {"category_id": 7, "depreciation_id": 3}, "CustomFieldsetField": {"fieldset_id": 5, "field_id": 9}, ...}`.
   Construcción Kotlin: mismo idiom que `ownedRefs` (`joinToString` a JSON manual, ver línea ~1149) pero un
   nivel más anidado — armar por entidad el sub-objeto y unirlos. Opt-in: lista de excluidas vacía (`assets`)
   → `withRefs` queda `{}` → **el bloque entero se cae y `Seed`/`seedJson`/`/seed` quedan BYTE-IDÉNTICOS**
   (mismo patrón que `ownedRefs`/`refs` ya usan para no re-derivar productos sin el eje).
4. **Montar CRUD real para esas entidades en `AppServer.kt`.** Ya existe el mecanismo `extras` (línea 1019,
   FSK-SERVE-ALL-ENTITIES) que monta CRUD RBAC-only con `catch_fk` para entidades servibles — **hoy filtra
   por nada especial, así que probablemente YA MONTA estas 19 entidades como rutas HTTP** (verificar: `extras
   = [e for e in _servible_ownerless(ents) if e["name"] not in primary_names]` — no filtra por
   `_has_req_ref`, a diferencia de `serve_all_ents` en el proof). Si es así, **el server YA sirve estas
   rutas** y el gap es 100% del lado del PROOF (nadie las llama) — confirmar esto primero (es una lectura
   rápida de `_mutation_fns`/dónde se usa `extras`), porque simplifica el alcance: sólo tocar
   `_access_control_check_py` + la exposición `/seed.withRefs`, CERO cambios a las rutas montadas.
5. **Extender el proof (`_access_control_check_py` + `constants.py::_SERVE_ALL_PROOF`).** Generalizar
   `serve_all_ents` (línea 1579) para NO excluir `_has_req_ref` — en su lugar, cada entrada de
   `serve_all_data` gana una clave opcional `"refs_from": "<EntityName>"` cuando la entidad tiene ref
   requerido; el template Python (`_SERVE_ALL_PROOF` en `constants.py`) hace, al construir el POST_BODY de
   esa entrada: `body = dict(entry["post"]); body.update(seed.get("withRefs", {}).get(entry["refs_from"],
   {}))` antes de postear (mismo idiom que `owned_ref_merge`/`WR_REF_FIELDS` ya usan). El diente NEGATIVO
   (FK colgante → 409) es opcional para v1 — el `wr` ya lo prueba una vez; agregarlo a las 19 es más
   ingeniería sin ganancia proporcional de cobertura (decisión: NO en v1, dejarlo si sobra tiempo).

## Alcance (blast radius)
- `factories/full-stack-kotlin/codegen/scaffold/server.py`: `_app_server_kt` (seed priming + `/seed.withRefs`)
  + `_access_control_check_py` (generalizar `serve_all_ents`/`serve_all_data`).
- `factories/full-stack-kotlin/codegen/scaffold/constants.py`: `_SERVE_ALL_PROOF` (template Python del proof,
  leer `withRefs`) + el skeleton Kotlin de `Seed`/`seedJson` (agregar el campo opcional).
- NO toca: `Repository.kt`/`data_layer.py` (las funciones `rowJson`/`insert` YA EXISTEN por entidad, sólo
  faltaba invocarlas desde HTTP real) — a confirmar en el paso 4 del mecanismo; si `extras` ya monta las
  rutas, este incremento no genera Kotlin NUEVO, sólo el seed+proof.
- NO toca: `seed/` (meta), `stations/`, `factory.spec.yml` de ningún producto (el mecanismo es 100% dentro
  del generador — DATA-agnóstico, cero nombres de dominio, ADR-012).

## Plan (fases)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 0 | Confirmar que `extras` (línea 1019) ya monta CRUD HTTP para las 19 excluidas (lectura, sin código) — si no, este incremento crece (montar las rutas) | ✅ confirmado: ya montaba (`catch_fk=_has_req_ref(e)`), cero cambios de rutas |
| 1 | Priming del registry + `/seed.withRefs` en `_app_server_kt` (Kotlin), byte-neutral para `assets` | ✅ (+ fix real: primar también `company_ent`/`ref_targets`/`with_ref`-qty, no anticipado en el diseño) |
| 2 | Generalizar `serve_all_ents`/`_SERVE_ALL_PROOF` para leer `withRefs` y postear+verificar cada excluida | ✅ (+ fix: separar ref_flds/scalar_flds en `_proof_post_value`, evitar KeyError en campo ref) |
| 3 | Verificar: `product-run --mode harden` (los 4 productos) + `ci --rederive --all-products` == pin en `assets` (byte-neutral) / re-pin esperado en demo+helpdesk+snipeit | ✅ 4/4==pin, SIN re-pin en ninguno (`proof_sha` es exit-code, no contenido) |
| 4 | Medir cobertura Jacoco de snipeit post-cambio (`./gradlew jacocoLiveReport`), comparar contra 70.7% baseline, actualizar `SNIPEIT-SPEC.md §11` con el número nuevo + la brecha remanente (si queda alguna) | ✅ 93.1%, medido 2× (draft + ci --rederive), idéntico |
| 5 | Cierre: `meta check` verde, `docs/STATE.md` (meta+factory) actualizados, LOG episodio | ✅ |

## Riesgos / por qué esto NO es un truco barato
- **Interacción con otros ejes opt-in**: `_app_server_kt` ya combina ~12 ejes (workflow, qty-ops, refs
  polimórficos, company-scoping, campos computados, soft-delete, actionlog, owner-poly). El priming del
  registry debe convivir con TODOS sin romper el layout de imports/tablas (`tbls`, línea 1058) — probable
  que `tbls` necesite recalcularse DESPUÉS del nuevo seeding (hoy se computa ANTES, línea 1058, con lo cual
  las tablas de las 19 nuevas entidades sembradas quedarían afuera → `NoSuchElementException`/tabla jOOQ no
  importada). **Anotado explícitamente para no repetir el error.**
- **`owner_poly`** (dueño polimórfico, wrinkle #3): si `owner_ent` es poly, `"ownerId"` como var única puede
  no ser válida para todos los targets — verificar antes de primar (snipeit/demo/helpdesk no son poly hoy,
  pero el mecanismo debe degradar honesto, no fallar silenciosamente, si algún producto futuro lo es).
- **Ciclos**: `_ensure_seeded` ya tira `SystemExit` ante un ciclo (deferral 6 existente) — con 19 entidades
  nuevas en el grafo de dependencias, confirmar que ninguna cierra un ciclo (no debería, son todas
  pivots/hijas, pero verificar con el mismo script de clausura usado para el hallazgo de arriba antes de
  generar, no después).
- **Regresión de los OTROS 2 productos** (`assets`/`helpdesk` ya pineados con sus propios criterios de
  cierre cerrados) — el two-sided real es: `assets` byte-neutral (0 candidatas, matemáticamente garantizado
  por la tabla de arriba) Y helpdesk/demo/snipeit re-pinean con MÁS cobertura, nunca con menos (ningún check
  existente debe volverse rojo).

## Ruteo por sesión (ADR-021)
- **S1 DISEÑO (Opus) — HECHO en este doc** (mecanismo exacto, hallazgo medido, riesgos anotados). No hace
  falta re-leer `server.py` desde cero: los anchors de línea de arriba (1053/1058/1115/1149/1579) son del
  commit `5921bc5` (HEAD al abrir este incremento) — si el archivo cambió, `grep -n "_seed_deps(owned"` /
  `grep -n "serve_all_ents ="` los re-ubica en 1 línea.
- **S2 EJECUCIÓN**: seguir el plan de fases arriba. Es codegen con dependencias fuertes entre ejes (ADR-017
  "cuándo NO delegar") → ejecutar con ojos propios (no delegar a un generator ciego), pero el DISEÑO ya
  redujo el trabajo a pasos mecánicos — no hace falta re-decidir arquitectura, sólo escribir el código
  especificado y verificar con el gate de la Fase 3.
- Env: `eval "$(bash tools/toolchain.sh ensure)"` antes de cualquier gradle; `ci --rederive` de snipeit es
  LENTO (19→39 entidades, boot server+PG+Chromium) → FOREGROUND, nunca background (carrera con turn-close).

## Criterio de cierre (demostrable, no narrable)
1. `ci --rederive full-stack-kotlin/assets` == pin **exacto** (byte-neutral, 0 candidatas — no debe re-pinear).
2. `ci --rederive --all-products` 4/4 (demo/helpdesk/snipeit re-pineados, esperado; ningún rojo).
3. Cobertura Jacoco de snipeit medida post-cambio y comparada contra el baseline 70.7% (`SNIPEIT-SPEC.md
   §11.2` re-derivado), con la brecha remanente (si la hay) declarada línea por línea igual que §11.3 — NO
   se acepta un "100%" no verificado ni un hueco silencioso.
4. `product-run --mode harden` PASS en los 4 productos.
5. `meta check` verde.
6. `docs/STATE.md` (meta) + `factories/full-stack-kotlin/docs/STATE.md` actualizados con el resultado real.

## Evidencia (cierre, 2026-07-09T22:5xZ)
1. `ci --rederive --factory full-stack-kotlin --product assets` → `assets: 11/11 proof_sha == pineado`, exit 0.
   Byte-neutral confirmado (0 entidades candidatas al eje, matemáticamente garantizado por la tabla del
   hallazgo + verificado en clon limpio).
2. `ci --rederive --factory full-stack-kotlin --all-products` → **4/4**: demo `12/12`, assets `11/11`,
   helpdesk `11/11`, snipeit `12/12`, todos `== pineado`. **Ningún producto re-pineó** (a diferencia de lo
   anticipado en el diseño S1): `proof_sha` deriva de exit-codes de checks (`seed/verifier.py::
   compute_proof_sha`), no de contenido generado — el mismo conjunto de checks en verde no fuerza re-pin
   aunque el generador cambió. Lección para el próximo incremento de sustrato: no asumir re-pin por defecto.
3. Cobertura Jacoco de snipeit: **93.1%** (antes 70.7%), medida DOS veces de forma independiente
   (`product-run --mode draft` Y `ci --rederive` en clon limpio) — idéntica en ambas. Brecha remanente
   declarada línea por línea en `SNIPEIT-SPEC.md §11.3` (actualizado): `DbRoundTrip.kt` 227 (sin cambios,
   diagnóstico manual) + `AppServer.kt` 154 (antes 648) + `Repository.kt` 63 (antes 532) + 11 líneas
   dispersas en guards/observability/workflow. NO se declaró "100%" — el ~6.9% remanente queda honesto.
4. `product-run --mode harden` PASS en assets, helpdesk, snipeit (demo cubierto por su propio `ci --rederive`
   full-line, que corre el conjunto completo de estaciones).
5. `meta check` → 19/19 (1 rojo transitorio de `docs` por sello ADR-009 stale tras editar `SNIPEIT-SPEC.md`,
   resuelto con `meta doc-sync`).
6. `docs/STATE.md` (meta, línea "Producto/fábricas") + `factories/full-stack-kotlin/docs/STATE.md` (bullet
   `FSK-REQREF-COVERAGE` nuevo, precede al `FSK-COVERAGE-INSTRUMENT` que cierra) actualizados. Episodios en
   `docs/LOG.md` (meta) + `factories/full-stack-kotlin/docs/LOG.md`.

**2 bugs reales encontrados en la ejecución** (no anticipados por el diseño S1, ambos root-caused corriendo
el server a mano contra PG — no simulados): (a) el registry primado inicial (sólo `dep_registry`+owned+owner)
no alcanzaba — una entidad excluida que necesitaba `Company` (el tenant company-scoped, sembrado por OTRO eje
fuera de `dep_registry`) la re-sembraba con la misma muestra → `IntegrityConstraintViolationException`
(`companys_name_key` duplicado), el servidor no arrancaba; fix: primar también `company_ent`/`ref_targets`/
`with_ref`-con-qty (moviendo `wr_qty_ops` más arriba en la función para que estuviera disponible a tiempo).
(b) el literal del mapa `withRefs` con 19 entidades en una línea excedía `MaximumLineLength` (160, detekt);
fix: `val seedWithRefsArg` propio, una entidad por línea.

**Tiempo real de la sesión** (bajo la restricción de tiempo pedida por el ingeniero): diseño S1 ya estaba
hecho al abrir este incremento; la ejecución S2 fue ~1 sesión (lectura de anclas + 2 fases de código +
2 ciclos de debug real + verificación de los 4 productos + medición + docs). El 100% literal NO se alcanzó
(93.1%) — el residual restante (`DbRoundTrip.kt` + camino negativo de las 19) queda como incremento futuro
acotado si se decide perseguirlo.
