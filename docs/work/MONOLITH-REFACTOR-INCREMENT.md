<!-- meta:doc sha=575d60ea9826cd81e135cc29dd936ced9e341ca7 updated=2026-06-26T03:03Z -->
# Incremento MONOLITH-REFACTOR

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-26T03:03Z) (creado 2026-06-26T02:30Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> Autoridad del PLAN: **ADR-017** (§4 gates de calidad) · roadmap `work/SOTA-REDESIGN-DIRECTION-INCREMENT.md` (Fase 3).

## Objetivo
Cerrar la **Fase 3 SOTA**: eliminar el monolito `factories/full-stack-kotlin/codegen/scaffold_product.py`
(8552 LOC, el ROJO nombrado del gate `quality`) partiéndolo en módulos cohesivos **sin cambiar un byte de
salida** (la fábrica re-deriva `== pin`), y **endurecer el gate** para que su diente sobreviva al split y
**FUERZE hacia adelante** que ninguna codegen de fábrica vuelva a ser un monolito.

## Por qué (auto-contenido — sobrevive sin la memoria ni la sesión previa)
La Fase 1 (`GRAPH-SPINE-KEYSTONE`) cableó el gate `quality` con un diente de DOS lados cuyo lado-ROJO era el
propio monolito FSK (su `evaluate_file` sobre `scaffold_product.py` DEBE marcar violaciones, si no el gate es
decorativo). El gate sólo escanea el SUSTRATO (`src/metafactory`+`seed`) en su lado-VERDE; el monolito era
una **marca de deuda** apuntada, no un build rojo. Partir el monolito **rompe ese diente** (un `scaffold_product.py`
flaco → `evaluate_file` vacío → decorativo → ROJO). Por eso esta fase es DOS cosas acopladas: (a) el split
(vive en el incremento de FÁBRICA `FSK-CODEGEN-SPLIT`), y (b) re-asentar el diente del gate sobre un **fixture
sintético permanente** + agregar un **diente hacia-adelante** sobre la codegen de fábrica. Esta es la parte
META/sustrato.

## Decisión de diseño (registrada)
- **El refactor es un transform DETERMINISTA, NO se delega a Sonnet** (calibración honesta, lección de Fase 2):
  preservar bytes + cablear imports es mecánicamente derivable del grafo de llamadas (I-3: el determinismo
  envuelve). Re-tipear 8552 líneas de templates por un LLM agrega riesgo sin valor; el arnés `generate-slot`
  sigue siendo la herramienta para slots de GENERACIÓN, que un refactor byte-idéntico no es. La prueba es por
  BLOQUEO (`ci --rederive == pin`), no por confianza en el transform.
- **`func_loc` exento en codegen de fábrica** (principio, no overfit): la codegen EMITE strings-template largos
  (un `_app_server_kt` que devuelve 300 líneas de Kotlin es legítimo; partirlo dañaría la legibilidad). Las
  métricas de "monolito" para codegen son TAMAÑO de archivo y CANTIDAD de funciones, no el largo de una función.
  El sustrato (`src/metafactory`) sí gatea las tres (no tiene templates gigantes). El gate no nombra fábrica/
  dominio/tech (lo sanciona `generality`): el scan es un glob `factories/*/codegen/**`.

## Fases (orden por dependencia — cada commit deja `meta check` VERDE)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Re-asentar el diente-ROJO** del gate `quality` sobre un **fixture sintético** (`tests/fixtures/quality/monolith_shaped.py`, viola los umbrales default → ROJO; bajo umbrales laxos → VERDE = guardia anti-decorativo). Quitar el path hardcodeado `scaffold_product.py`. Actualizar los 2 tests de `test_graph.py`. (Precede al split: deja el gate independiente del estado del monolito.) | ✅ |
| 2 | *(incremento de FÁBRICA `FSK-CODEGEN-SPLIT`)* — el split byte-idéntico. | ✅ |
| 3 | **Diente hacia-adelante**: el gate escanea la codegen AUTORADA de fábrica (`factories/*/codegen/**/*.py`, excl. `build/`/`__pycache__`) con `file_loc`+`funcs` (func_loc exento). Post-split TODO pasa (FSK ≤1543 LOC/≤24 funcs · ASF 1633/12 · iot 665/17 · full-stack 431/9). Test de dos lados. | ✅ |
| 4 | Docs: ROADMAP/STATE/LOG + §Evidencia + cerrar. | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. El gate `quality` ya NO referencia `scaffold_product.py`; su lado-ROJO es el fixture sintético — dos lados
   por bloqueo (fixture bajo default → ROJO · bajo laxo → "decorativo"/exit 1). Tests verdes.
2. El gate FUERZA hacia adelante: una codegen de fábrica `>2000` LOC o `>80` funcs → `meta check` ROJO
   (probado de dos lados con el fixture); post-split las 4 fábricas pasan (sin el monolito).
3. `meta check` **10/10 verde** (incl. `generality` ⇒ el gate no nombra fábrica/dominio/tech; `quality` ⇒
   regla multi-archivo respetada sobre el sustrato nuevo).
4. El split en sí (byte-identidad + `ci --rederive --all-products == pin`) está PROBADO en el incremento de
   FÁBRICA `FSK-CODEGEN-SPLIT` (su §Evidencia) — esta fase depende de ese cierre.

## Punteros
- **ADR-017** §4 · `work/SOTA-REDESIGN-DIRECTION-INCREMENT.md` (Fase 3) · `work/GRAPH-SPINE-KEYSTONE-INCREMENT.md`
  (el gate `quality` que extendemos) · incremento de fábrica `factories/full-stack-kotlin/docs/work/FSK-CODEGEN-SPLIT-INCREMENT.md`.

## Evidencia (cierre — re-derivable, no narrada)
**Código** (inglés, ADR-017): `src/metafactory/verify/checks/quality_gate.py` (RED witness re-asentado +
diente hacia-adelante) · `src/metafactory/graph/quality.py` (+`discover_authored_codegen`, glob
DATA-agnóstica) · `tests/fixtures/quality/monolith_shaped.py` (witness sintético, generado/determinista) ·
`tests/test_graph.py` (+3 tests). El split en sí vive en la fábrica (incremento `FSK-CODEGEN-SPLIT`).

**Los 4 criterios, por bloqueo**:
1. **RED witness re-asentado** — el gate ya NO referencia `scaffold_product.py`; su lado-ROJO es
   `tests/fixtures/quality/monolith_shaped.py` (82 funcs > 80 · func_loc 213 > 200). Dos lados: bajo umbrales
   default → diente vivo (exit 0 con RED reportado); bajo umbrales laxos → "DECORATIVO" (exit 1, guardia).
   `test_quality_substrate_clean_synthetic_monolith_red` + `test_quality_gate_check_passes_and_self_guards`.
2. **Diente hacia-adelante** — el gate escanea la codegen autorada de fábrica (`factories/*/codegen/**/*.py`,
   glob; excl. `build/`/`__pycache__`) por `file_loc`+`funcs` (`func_loc` EXENTO: la codegen devuelve
   templates largos legítimos). Dos lados VIVO por CLI: post-split 22 archivos limpios → verde · un archivo
   monolito-shaped soltado en `codegen/` → `meta check` ROJO · removido → verde. Tests
   `test_factory_codegen_forward_tooth_no_monolith` + `…_fires_on_monolith`.
3. **`meta check` 10/10 verde** — compile·docs·projection·isolation·**generality**·**quality**·pbt·security·
   deferred·suite. `generality` verde ⇒ el gate no nombra fábrica/dominio/tech (el path del witness es un
   negative-test acordado; el scan de fábrica es un glob). `quality` verde ⇒ sustrato + codegen de fábrica
   sin monolito.
4. **El split probado en la FÁBRICA** — `FSK-CODEGEN-SPLIT §Evidencia`: byte-identidad en los 3 blueprints +
   `ci --rederive --all-products == pin` + grafo de imports acíclico. **El monolito de 8552 LOC dejó de
   existir** (max ahora `server` 1543 LOC).

**Anti-overfit / honestidad**: el gate pasó de un PATH hardcodeado (`scaffold_product.py`) a un witness
sintético + un glob de fábrica → MÁS general que antes (cero nombres de producción). El split fue un transform
determinista, no delegado (calibración honesta: el arnés `generate-slot` es para GENERAR, no para refactors
byte-idénticos). `git diff seed/` = 0.
