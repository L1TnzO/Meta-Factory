<!-- meta:doc sha=709e723a4c9a98641cd9706f20e6a566350d8b8d updated=2026-06-27T02:04Z -->
# Incremento FACTORY-DOC-SEAL

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-27T02:04Z) (creado 2026-06-27T01:38Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> Nivel: **META** (toca `src/metafactory/docs_manifest.py` + hook + check). Autoridad de diseño:
> `docs/reference/GOVERNANCE-LAYERING.md §6` (Opción A faseada, Fase 2 "sellado de docs") + ADR-016.

## Objetivo
Bajar el **sello content-addressed de docs (ADR-009)** del nivel-meta-solo a **cada home de docs por nivel**
(meta · cada fábrica · cada producto), para que los docs autorados de fábrica/producto lleven el mismo
diente de integridad y NO puedan driftar en silencio — con **frescura por-home** (editar un doc de fábrica NO
fuerza re-tocar el STATE del meta: cierra P4, no sólo P3).

## Contexto (autocontenido — leer antes de tocar)
- **El gap medido (hoy):** `docs_manifest.doc_set()` = `repo_root/docs/**.md` + `START-HERE.md` + `CLAUDE.md`.
  Es **meta-only**. `grep -rln "meta:doc sha=" factories/*/docs/` → **cero**: los 57+ docs autorados de las 5
  fábricas (`factories/<f>/docs/{LOG,STATE,reference,work}`) + 2 productos (`…/products/{snipeit,helpdesk}/docs/`)
  no tienen sello → drift indetectable. `meta check` (vía `verify/checks/docs_check.py` → `docs_manifest.check`)
  no los mira.
- **Esto es Fase 2 (§3 "sellado de docs") de ADR-016.** §1 ya cerró (`HARNESS-DECOUPLE` + `FACTORY-DELEGATION-TEETH`).
  §4 (close por-nivel) **ya estaba hecho en Fase 1** (`cmd_increment` con `--factory`/`--product`). §2 (migrar los
  16 `FSK-S*` meta-residentes al home de fábrica) queda como carril aparte (NO en este incremento).
- **Por qué AHORA y por qué este corte:** paralelo directo a `FACTORY-DELEGATION-TEETH` — bajar un diente del
  meta al nivel fábrica. Acá el diente es la **integridad de la narrativa** (el sello), no la delegación.

## Diseño (decidido, DATA-agnóstico)
Parametrizar `docs_manifest.py` por **doc-home** (un dir que contiene `docs/`):
- `doc_homes(repo_root)` → meta (`repo_root`) + cada `factories/<f>/` + cada `factories/<f>/products/<p>/`
  que tenga un dir `docs/`. Parte la RUTA, no hardcodea slugs (igual que el edit-gate level-aware de Fase 1).
- `doc_set(home, *, meta_extras)` → `<home>/docs/**.md` (+ `START-HERE.md`/`CLAUDE.md` SÓLO si `meta_extras`,
  i.e. el home meta). Excluye `INDEX.md` por nombre.
- `check`/`sync`/`_state_fresh_problem` operan **por-home** y se agregan a nivel top.

### Fronteras deliberadas (anti-scope-creep, documentadas)
1. **Sólo narrativas autoradas** (`<home>/docs/**.md`). **NO** se sella `factories/<f>/CLAUDE.md`: es artefacto
   **proyectado/generado** (lo emite el harness) — sellarlo in-tree pelearía con `column_parity`/re-derivación.
   El home meta SÍ sella su `CLAUDE.md`/`START-HERE.md` (son docs meta autorados) → asimetría correcta, refleja
   una diferencia real (autorado vs generado).
2. **INDEX queda meta-only** (es el triage de navegación del meta; una fábrica navega por su propio STATE).
   Evita proliferar archivos generados (`factories/<f>/INDEX.md`) que colisionarían con `column_parity`.
   `check` parte (2) (cobertura de INDEX) corre sólo sobre el doc_set meta.
3. **Frescura por-home, skip-safe**: cada home compara su `docs/STATE.md` contra el doc más nuevo de SU set.
   Si un home no tiene STATE.md (o no está commiteado), se saltea. Cierra P4 (no cross-coupling de niveles).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `docs_manifest.py` parametrizado por home (`doc_homes`, `doc_set(home, meta_extras)`, `check`/`sync`/freshness por-home agregados); INDEX meta-only | ✅ |
| 2 | Wiring: `doc_stamp.py` hook + `cli.py` sync-sites sellan TODOS los homes (sin cambio, van por `sync()`); sello en bloque de los **78** docs de fábrica/producto | ✅ |
| 3 | Tests por bloqueo (tamper doc de fábrica → rojo aislado; meta intacto; frescura no cross-acopla) + `meta check` verde + `ci --rederive` 5 fábricas == pin | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. Todo doc autorado bajo `factories/*/docs/` y `factories/*/products/*/docs/` lleva un sello correcto;
   `meta check` lo verifica (parte (1) integridad corre por-home).
2. **Diente probado por bloqueo**: corromper el body de un doc de fábrica sin re-sellar → `meta check` rojo,
   con el problema apuntando a ESE archivo; los docs meta siguen verdes (aislamiento).
3. **No cross-coupling (P4)**: tocar un doc de fábrica NO dispara el problema de frescura del STATE meta.
   Test del `_state_fresh_problem` por-home.
4. `meta check` N/N verde (sube de 14 ↔ ídem, el check de docs ahora cubre 3 niveles) + `pytest tests/` verde
   + test nuevo del sello por-home.
5. **Re-derivación intacta**: las 5 fábricas `meta ci --rederive --all-products` == pin (el sello toca sólo
   docs autorados, jamás la línea de producto/codegen).
6. ADR-016 + STATE/LOG del meta narran el cierre; `git diff` sin residuo no-commiteado.

## Evidencia (cierre 2026-06-27T02:00Z)
1. **Sello por-nivel (criterio 1)** — `doc_homes` detecta 8 homes (meta + 5 fábricas + 2 productos snipeit/helpdesk);
   `meta doc-sync` selló **78** docs autorados de fábrica/producto (antes: `grep "meta:doc sha=" factories/*/docs/`
   → 0). `meta check` parte (1) los verifica por-home.
2. **Diente por bloqueo (criterio 2)** — `test_tampered_factory_doc_is_red_and_isolated`: corromper el body de
   `factories/demo/docs/LOG.md` sin re-sellar → `check` reporta `stale seal` SÓLO sobre ese archivo (todos los
   problemas mencionan ESE path → aislado). El mismo patrón se observó vivo: `meta check` cayó a 13/14 cuando los
   docs de fábrica estaban sin sellar, y volvió a 14/14 tras `sync`.
3. **No cross-coupling P4 (criterio 3)** — frescura PER-HOME (`_state_fresh_problem(repo, home, *, meta_extras)`):
   surfaceó un drift real (dummy STATE más viejo, por último commit, que su LOG — antes invisible), resuelto al
   commitear los 78 sellos juntos. Editar un doc de fábrica no toca la frescura del STATE meta (sets disjuntos:
   `test_meta_and_factory_doc_sets_do_not_overlap`).
4. **Verde (criterio 4)** — `meta check` **14/14** (compile·docs·projection·isolation·generality·quality·pbt·
   security·deferred·benchmark·column_parity·state_snapshot·state_fidelity·suite) · `pytest tests/` **724** ·
   `test_docs_manifest.py` **26** (21 previos + 5 nuevos del sello por-home).
5. **Re-derivación intacta (criterio 5)** — `ci --rederive --all-products` en árbol limpio (full rebuild),
   **5/5 fábricas == pin**: dummy 5/5 · full-stack 6/6 + tasks 5/5 · iot 5/5 + fleet 5/5 · ASF 11/11 · FSK
   default 12/12 + assets 11/11 + helpdesk 11/11 + snipeit 11/11. Changeset sin tocar `product.yml`/codegen/`.kt`/
   `.ts`/stations (git-verificado).
6. **Narración + árbol limpio (criterio 6)** — `GOVERNANCE-LAYERING.md §6` (autoridad de diseño) + STATE «Ahora»
   + este LOG narran el cierre; ADR-016 (inmutable) NO se editó — su diferido honesto «docs SIN sellar» queda
   cerrado por referencia. Commits: build `feat(docs): FACTORY-DOC-SEAL` + el close. `git diff` sin residuo.

**Deliberadamente fuera de alcance (carriles aparte, honestos):** §2 lifecycle de fábrica in-tree REAL (hoy el
guard del meta cubre por-ruta; falta migrar los 16 `FSK-S*` meta-residentes a `factories/full-stack-kotlin/docs/work/`)
+ `LEAST-PRIV-DECOUPLE`. Ninguno bloquea.
