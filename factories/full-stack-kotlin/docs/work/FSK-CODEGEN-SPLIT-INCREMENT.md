<!-- meta:doc sha=dd65d53c419dfc1aff9d54eb8d743a382225522f updated=2026-06-27T01:41Z -->
# Incremento FSK-CODEGEN-SPLIT

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-26T03:03Z) (creado 2026-06-26T02:30Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> Contexto del PLAN: Fase 3 SOTA `MONOLITH-REFACTOR` (meta) — autoridad ADR-017 §4.

## Objetivo
Partir el monolito `codegen/scaffold_product.py` (8552 LOC, 174 funcs) en un **paquete cohesivo**
`codegen/scaffold/` (regla multi-archivo, 2026-06-25) **sin cambiar un byte de la salida generada** — la
fábrica y sus 2 productos re-derivan `== pin`.

## Por qué
El gate `quality` (Fase 1 SOTA) marca este archivo ROJO; es el único monolito autorado del repo. El split
lo vuelve navegable (un módulo por concern/estación) y desbloquea el diente hacia-adelante del gate (el
incremento meta `MONOLITH-REFACTOR`). Es un **refactor de preservación de comportamiento**: la prueba es la
re-derivación byte-idéntica, no una revisión de prosa.

## Arquitectura del split (DAG acíclico, derivado del grafo de llamadas)
- **Entry** `codegen/scaffold_product.py` (delgado): shebang + docstring + `main`/`_emit`/`_check_idempotent`/
  `_assets_dir` (framework/glue: argv, escritura del árbol, idempotencia, vendorizado del wrapper Gradle vía
  `__file__`); importa `build_files`/`_load_blueprint` de `scaffold`.
- **Paquete** `codegen/scaffold/` — capas estrictas (cada módulo importa SÓLO de capas inferiores ⇒ sin ciclos):
  - `constants.py` (hoja) — los 81 pins/skeletons/maps de tech del PLAN.
  - `base.py` — helpers compartidos (naming, inspección de blueprint/campos, workflow, kotlin, proof-values).
  - `blueprint.py` — `_load_blueprint` + `_validate_computed_ast` (parser/validador del dominio).
  - emisores por concern (cada uno = templates de una estación): `contract` (OpenAPI) · `data_layer`
    (model/repo/migración/workflow) · `auth` (guards/rutas/route_check) · `server` (AppServer/handlers/seed/
    access-control) · `frontend` (TS app/client/ui/css) · `browser` (checks Playwright/consume) · `buildcfg`
    (gradle/package.json) · `quality_tooling` (detekt/eslint/currency/sbom/supply-scan/a11y/perf) · `pyramid`
    (Kotest) · `observability` (OTel) · `deploy` (hermetic/ci/docker).
  - `__init__.py` — `build_files` (el ensamblador, raíz del DAG) + re-export de `build_files`/`_load_blueprint`.

## Cómo (transform determinista, no delegado — I-3)
El split lo produce un transform mecánico (slices de fuente por span AST byte-preservados + headers de import
computados del grafo de llamadas/constantes). NO se delega a Sonnet: byte-preservación + cableado de imports
es determinista; un LLM agrega riesgo sin valor. El árbitro es `ci --rederive`, no la confianza en el transform.

## Criterio de cierre (demostrable, no narrable)
1. **Byte-identidad**: `build_files(bp)` del blueprint de la fábrica es idéntico módulo-viejo vs paquete-nuevo
   (diff = 0). `python3 codegen/scaffold_product.py --selftest` y `--check-idempotent` PASAN.
2. **Re-derivación**: `meta ci --rederive --all-products` ⇒ las 3 instancias (default + `snipeit` + `assets`)
   re-derivan `== pin` en clon/aislamiento (byte-idéntico al veredicto pineado). RTM intacto.
3. **No-monolito**: ningún módulo del paquete `>2000` LOC ni `>80` funcs (el entry queda delgado); el grafo de
   imports es ACÍCLICO.
4. `git diff` del sustrato (`src/metafactory/`+`seed/`) = **0** (el split vive 100% en la fábrica — DATA, ADR-012).

## Evidencia (cierre — re-derivable, no narrada)
**El paquete** `codegen/scaffold/` (16 archivos, ninguno monolito): `constants.py` (81 pins) · `base.py`
(42 helpers compartidos) · `blueprint.py` (loader + validador AST) · 11 emisores por concern (`contract` ·
`data_layer` · `auth` · `server` · `frontend` · `browser` · `buildcfg` · `quality_tooling` · `pyramid` ·
`observability` · `deploy`) · `__init__.py` (`build_files` + re-export). DAG de imports ACÍCLICO (verificado
por Tarjan en el transform): cada módulo → `base` → `constants`. Entry `scaffold_product.py` = 104 LOC.

**Los 4 criterios, por bloqueo**:
1. **Byte-identidad** — `build_files(bp)` del monolito-viejo (git HEAD) vs el paquete-nuevo: **idéntico en los
   3 blueprints** (hashes SHA-256 por archivo): `webapp` 73 · `snipeit` 75 · `assets` 73 archivos, 0 diffs.
   `python3 codegen/scaffold_product.py --selftest` OK (webapp, 73 archivos) · `--check-idempotent` OK (77
   byte-idénticos en dos generaciones).
2. **Re-derivación clean-clone** — `meta ci --rederive --factory full-stack-kotlin --all-products` ⇒
   **PASS, 3/3 productos re-derivados == su pin** en clon limpio aislado a través del nuevo entry: default
   **12/12** · assets **11/11** · snipeit **11/11** proof_sha == pineado. *(+ product-run default e2e VERDE
   en árbol de trabajo: s11 `deploy_appserver_live` OK — la línea gradle viva corre por el `generate` slot
   → nuevo entry → paquete.)*
3. **No-monolito** — métricas post-split (todas < umbrales 2000 LOC / 80 funcs): `server` 1543/22 ·
   `constants` 1412/0 · `data_layer` 984/19 · `auth` 674/13 · `quality_tooling` 646/24 · `frontend` 634/17 ·
   resto < 350 LOC. Entry 104/4. Grafo de imports acíclico.
4. **`git diff src/metafactory/ + seed/` = 0** en este incremento de FÁBRICA (el split es 100% DATA de
   fábrica, ADR-012). *(El gate `quality` que lo FORZÓ + su diente hacia-adelante viven en el incremento META
   `MONOLITH-REFACTOR`, sustrato — separados por nivel, ADR-016.)*

**Cómo se hizo (honesto)**: transform DETERMINISTA (slices por span AST byte-preservados + headers de import
del grafo de llamadas), **NO delegado a Sonnet** — un refactor byte-idéntico es mecánico (I-3); delegar
generación a un LLM agregaría riesgo sin valor (calibración honesta, lección de Fase 2: el arnés es para
GENERAR, no para preservar bytes). El árbitro fue `ci --rederive`, no la confianza en el transform.
