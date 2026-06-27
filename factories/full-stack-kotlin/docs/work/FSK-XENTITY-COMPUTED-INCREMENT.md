<!-- meta:doc sha=95b1eb8a17fdbff9748c5e1df275eff9a63e5092 updated=2026-06-27T01:41Z -->
# Incremento FSK-XENTITY-COMPUTED — el campo COMPUTADO referencia una entidad RELACIONADA (derivación CROSS-ENTITY)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-23T03:16Z · cerrado 2026-06-23T13:38Z — ver §Evidencia). Editar `factories/full-stack-kotlin/**`
> no-`.md` exige un incremento abierto; el siguiente es `FSK-POLY-ASSIGNS` (`docs/work/FSK-POLY-ASSIGNS-INCREMENT.md`).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-SOFT-DELETES con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (y por qué es DECISIÓN tuya)

**El NÚCLEO FUNCIONAL + BEHAVIORAL faithful está COMPLETO.** Cerrados, product-driven por Snipe-IT: modelo de datos
(CRUD del grafo · self-ref · ownership opcional/RTD · refs requeridos transitivos · ciclos cross-entidad · ref
polimórfico) · acceso (auth→RBAC→ownership→company-scope) · comportamiento (workflow checkout/checkin · qty/stock ·
**borrado lógico trash+restore**, recién cerrado) · valores derivados (FSK-COMPUTED-FIELDS, same-entity) · app que
CORRE (CRUD vivo + frontend consume/render + deploy en contenedor).

**Lo que falta de genuinamente nuevo (no breadth pura): la derivación CROSS-ENTITY del campo computado.** Hoy un campo
`computed: <AST>` (FSK-COMPUTED-FIELDS) sólo referencia campos numéricos de la MISMA entidad (1er-cut SAME-ENTITY). La
contracara real de Snipe-IT: la fórmula de depreciación necesita los `depreciation_months`, que en Snipe-IT viven en
una entidad `Depreciation` enlazada vía `AssetModel` — HOY simplificado a un campo de Asset (ver SNIPEIT-DOMAIN.md
deferral 11 + 13). Un eje real: la fórmula puede referenciar `<ref>.<campo>` → resolver el ref (una FK), JOIN a la
tabla del target, leer su columna, computar.

**Por qué es un buen próximo:** (a) completa el straight-line REAL de Snipe-IT (depreciación faithful); (b) es la
contracara natural del eje recién cerrado (FSK-COMPUTED-FIELDS), reusa toda su maquinaria de AST/proof; (c)
**determinista, sin s6/LLM**; (d) acotado (una dimensión NUEVA: el operando `<ref>.<campo>` + un JOIN en `_row_json_fn`);
(e) diente de dos lados nítido (degradar el JOIN/la columna → otro número → SÓLO s9 rojo).

**⚠️ ESTA ES TU DECISIÓN (con más contexto).** Si al investigar decidís que NO es el mejor próximo, alternativas
honestas en §7. Tenés autoridad para reabrir — pero leé los wrinkles ANTES.

### 0.1 LOS WRINKLES
1. **El operando deja de ser un STRING simple** — en FSK-COMPUTED-FIELDS un operando del AST es un número, o un STRING
   que nombra un campo numérico de la MISMA entidad. Acá hay un operando NUEVO: `<ref>.<campo>` (p.ej.
   `"asset_model.cost"` o un nodo `{"ref": "model_id", "field": "cost"}`). Decisión de gramática: ¿extender el string con
   un `.` (parseado) o un nodo dedicado? Mirá `_validate_computed_ast`/`_computed_srcs`/`_computed_kt`/`_ast_uses_div`
   (todos en `codegen/`, alrededor de la línea de `_is_computed`): hoy un string es un nombre de campo local. El nuevo
   operando debe: (a) validar que `<ref>` es un campo `ref` NO-polimórfico de la entidad + `<campo>` es un campo
   numérico del TARGET; (b) resolverse a una columna del JOIN en `_row_json_fn`.
2. **El JOIN en `_row_json_fn`** — hoy `<e>RowJson` hace `select(cols).from(TBL).where(ID.eq(id))`. Para leer
   `<ref>.<campo>` necesitás un LEFT JOIN a la tabla del target (`from(TBL).leftJoin(TGT).on(TBL.<REF>.eq(TGT.ID))`) y
   seleccionar `TGT.<CAMPO>`. ⚠️ El ref puede ser OPCIONAL (FK nullable) → LEFT JOIN + null-safe (`?: 0.0`, ya es el
   patrón). ⚠️ jOOQ DDLDatabase tipa toda columna nullable → el `!!`/`?:` ya está resuelto en el codegen existente.
3. **El proof re-deriva la MISMA fórmula** — `_COMPUTED_PROOF` (`_ceval` en Python) hoy lee las fuentes de `POST_BODY`
   (los campos posteados). Para una fuente cross-entity, el valor NO está en `POST_BODY` — está en la fila del TARGET
   que el server sembró (/seed lo expone, o lo lee con un GET al target). El proof debe resolver `<ref>.<campo>`
   leyendo la fila del target (vía el id del ref que POSTeó). Es el wrinkle más sutil: el oráculo Python necesita el
   valor del target. Pensá exponer el valor sembrado del target en `/seed` (como `ownedRefs`).
4. **Same-entity sigue intacto** — el 1er-cut (`Asset.current_value` same-entity) DEBE seguir verde. El nuevo operando
   es OPT-IN: una fórmula sin `<ref>.<campo>` se comporta EXACTO (byte-neutro). El eje es ADITIVO.

**Conclusión honesta**: el camino BOUNDED — **un operando `<ref>.<campo>` en el AST → validación (ref no-poly +
campo numérico del target) + LEFT JOIN en `_row_json_fn` + el proof lee el valor del target**. La adopción faithful:
restaurar `Depreciation`/`AssetModel.depreciation_months` como entidad y que `Asset.current_value` lo derive
cross-entity. Diente: degradar el JOIN (leer la columna local en vez de la del target, o dropear el JOIN) → otro número
→ SÓLO s9 rojo.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥540000ms** (el sandbox mata gradle).
**cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del hook `stop_proof` al
cerrar; si pasa, `cd` de vuelta a la raíz INMEDIATAMENTE). Debe dar **PASS**, RTM snipeit **24/25** (único UNSAT =
REQ-F-007/s6 LLM keyless).
⚠️⚠️ **s7 PG 5435 · s9 puertos 18593-18595 + PG 5436/5437 · s11 18596** → NUNCA dos corridas en paralelo, NUNCA dejes un
`product-run`/`ci` en BACKGROUND al cerrar el turno (`stop_proof` re-corre la estación activa → colisión de puerto/PG).

**2) EL DISEÑO (GENERAL, cero nombres de dominio):**
- **Gramática del AST** (`_validate_computed_ast` + `_computed_srcs` + `_computed_kt`, todos cerca de `_is_computed`):
  un operando nuevo `<ref>.<campo>` (string con `.` o nodo `{"ref","field"}`). Validá: `<ref>` ∈ campos `ref` NO-poly
  de la entidad; `<campo>` ∈ campos numéricos no-computados del TARGET (`bp` tiene el grafo). Fail-closed (ref
  inexistente / campo no-numérico → M0/scaffold rojo, mismo patrón que el AST same-entity).
- **El JOIN** en `_row_json_fn`: si algún AST de la entidad usa un operando cross-entity, el SELECT gana un LEFT JOIN
  por cada `<ref>` distinto (`leftJoin(TGT).on(TBL.<REF>.eq(TGT.ID))`) y selecciona `TGT.<CAMPO>`. Las fuentes
  cross-entity se extraen a `val`s `Double` null-safe (mismo patrón que las same-entity).
- **El proof** (`_COMPUTED_PROOF`/`_ceval`): para una fuente `<ref>.<campo>`, el oráculo Python lee el valor del target
  (vía /seed o un GET al target por el id que POSTeó). Diente: degradar el JOIN en el codegen → otro número → SÓLO s9 rojo.

**EL DIENTE de dos lados**: degradar `_row_json_fn` (leer la columna LOCAL en vez de `TGT.<CAMPO>`, o dropear el JOIN) →
el GET devuelve otro número → **SÓLO** `access_control_live` (s9) rojo, hermanos + s0–s8 verdes → revertí → verde. ⚠️ El
sabotaje debe degradar la LÓGICA/SQL, no la forma Kotlin (un cambio que rompe detekt/ktlint en s2 NO sirve).

---

## 1. ⚠️ RE-PIN — casi seguro NO hace falta
Si el cambio vive DENTRO de `access_control_live` (s9) SIN sumar check/estación nuevos → el **`proof_sha` queda
INTACTO** → pines byte-idénticos, **SIN re-pin** (como qty/poly/computed/soft-deletes). `git diff snipeit/product.yml
≠ 0` es ESPERADO; el sustrato + default/assets product.yml DEBEN quedar en 0. Si SÍ agregás un check/estación →
re-pin justificado + re-materializá el chasis por defecto + re-pineá los 3 productos.

## 2. Maquinaria a REUTILIZAR — TODO en `codegen/scaffold_product.py` (verificá los anchors con grep)
- **FSK-COMPUTED-FIELDS es tu base directa**: `_is_computed` · `_validate_computed_ast` · `_computed_srcs` ·
  `_computed_kt` · `_ast_uses_div` · el prelude de cómputo en `_row_json_fn` · `_COMPUTED_PROOF`/`_ceval`. Todo el
  same-entity ya existe; vos AGREGÁS el operando cross-entity.
- **El JOIN/los refs**: mirá cómo `_repository_kt` resuelve un `ref` a su tabla (`by[f["to"]]`, `_TBL`), cómo el
  AppServer siembra los targets de refs (`_seed_chain`, `ref_targets`, `ownedRefs`/`/seed`). El valor sembrado del
  target lo necesita el proof.
- **El patrón OPT-IN del proof**: copiá la estructura `%...BLOCK%` (vacío sin el eje → byte-idéntico).

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **EYEBALL SIN gradle ANTES de cada corrida lenta** (cazó el 100% de los problemas de byte-neutralidad): un scratch
  python con `importlib` que carga el scaffold HEAD vs working, llama `build_files(bp)` para default/assets/snipeit-SIN-
  el-eje (STRIP la flag/operando nuevo de los bps) y **diffea** (byte-idénticos). Snapshot HEAD: `git show
  HEAD:factories/full-stack-kotlin/codegen/scaffold_product.py > /tmp/.../scaffold_head.py`. Hay un eyeball.py +
  preview.py reutilizables del increment anterior en el scratchpad (adaptá los nombres).
- **Un sabotaje que debe morder a RUNTIME no puede introducir un hallazgo ESTÁTICO antes.** Degradá el SQL/la lógica, no
  la forma Kotlin. **ktlint/detekt MaxLineLength=160; LongMethod ≤ 60; CyclomaticComplexMethod ≤ 15; ReturnCount ≤ 2;
  MagicNumber ignora -1/0/1/2 pero NO 3+; NoUnusedImports + -Werror.** Un `.toDouble()` REDUNDANTE sobre un `Double` →
  -Werror (s0 rojo); `${ident}` con llaves redundantes sobre un identificador simple → ktlint StringTemplate (s2 rojo).
- **com.sun.net.httpserver NO loguea la excepción de un handler** (cierra la conexión en silencio → el proof ve
  `RemoteDisconnected`/`infra_up no alcanzó la infra en 120s`). Para diagnosticar un crash del server: reproducir
  MANUALMENTE — levantar PG (`docker run … postgres@sha256:…`, puerto 5436) + `java -cp build/install/<pkg>/lib/*
  <pkg>.endpoints.AppServerKt` + curl los endpoints + `docker exec <pg> psql` directo a la DB. Así cacé los 2 wrinkles
  de soft-deletes (UNIQUE chocando con la fila borrada; modifyVerdict 404 sobre la fila borrada).
- **`meta verify` re-corre la estación ACTIVA con `build=False`** (no regenera). Para un tooth en s9: **sabotear el
  codegen + `product-run`** (rojo en s9, las posteriores no corren) → revertir → `product-run` verde (restaura la activa
  verde, clave para que `stop_proof` no bloquee el cierre).
- **`proof_protect` puede DENEGAR tocar `.proof/` por shell** — el **Read tool SÍ** lee `.proof/logs/` (los logs son
  RESÚMENES: check + exit; el `exit=0` es la señal autoritativa).
- **`ci --rederive` por producto**: `--product snipeit`/`--product assets` y SIN `--product` (la base/default). Cada uno
  es un clon limpio (≈< 10 min) → corrélos UNO A UNO en foreground. NO existe `--product default`.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento)
**`assigns`/owner POLIMÓRFICO** (sub-ejes de FSK-POLYMORPHIC-REFS) · **`creates`/pivot de qty** (insertar
AccessoryCheckout) · **EAV dinámico a runtime** (custom-fields Avenue B) · **PUT/update de campos OPCIONALES
arbitrarios** (hoy el server actualiza sólo required + la columna mutable) · **e2e Playwright / browser real** ·
**AppServer-en-contenedor con PG** · **Actionlog (auditoría polimórfica)** · **las ~226 rutas / Kits** (breadth).

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py` + quizá `factory.spec.yml`/`stations/*.yml` si la grama nueva necesita
  validación M0) es nivel FÁBRICA → **este incremento** lo cubre (header ABIERTO).
- **La adopción** (`products/snipeit/product.yml`: restaurar `Depreciation`/`AssetModel.depreciation_months` + el
  `computed` cross-entity) es nivel PRODUCTO → abrí TAMBIÉN `meta increment open --factory full-stack-kotlin --product
  snipeit <slug>` ANTES de tocar `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) + `feat(snipeit): …` (product.yml) + `docs(fsk): cerrar
  FSK-XENTITY-COMPUTED (§Evidencia) + abrir <siguiente>`. **Commiteá el CÓDIGO mientras el incremento está ABIERTO**,
  luego flipeá el header a CERRADO en el commit de docs.
- **Probá POR BLOQUEO**: EYEBALL byte-neutro · `product-run --product snipeit` PASS · diente de dos lados vivo (sólo
  s9) · `ci --rederive` (base + assets + snipeit) == pin (los 3) · `meta check` 6/6 (`generality` verde) · `git diff
  src/metafactory + seed = 0` · default+assets product.yml = 0.

## 6. Criterio de cierre (demostrable, no narrable)
1. Un campo computado declara un operando `<ref>.<campo>` y `product-run --product snipeit` **PASS** — el server vivo
   (s9): GET /{id} devuelve `<campo computado>` == la fórmula re-derivada sobre las fuentes, incl. el valor leído de la
   entidad RELACIONADA por JOIN.
2. **Diente de DOS lados verificado VIVO**: degradá el JOIN/la columna del target → ROJO **sólo** en
   `access_control_live` (s9) → revertí → verde.
3. EYEBALL byte-neutro (default/assets + snipeit-sin-cross-entity) · `ci --rederive` (base + assets + snipeit) == pin ·
   `meta check` 6/6 (`generality` verde) · `git diff src/metafactory + seed = 0` · default+assets product.yml = 0.
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md` (deferral cross-entity) actualizados. Abrí el SIGUIENTE con su handoff (§7).

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE
Si al investigar decidís que cross-entity-computed NO es el mejor próximo (es tu decisión con más contexto), las otras
candidatas BOUNDED, framed honestamente:
- **El `assigns` POLIMÓRFICO del verbo** (sub-eje diferido de FSK-POLYMORPHIC-REFS): un verbo de workflow que asigna a
  un ref polimórfico (setear las 2 columnas `<campo>_type`+`<campo>_id` del cuerpo del verbo). Completa el checkout
  polimórfico FAITHFUL (en Snipe-IT el target del checkout es User|Location|Asset). Toca `assigns` +
  `_operation_repo_fns`/`_operations_handlers` + el proof. Compone POLYMORPHIC-REFS + DOMAIN-OPS.
- **Breadth pura** (si decidís que el núcleo funcional + behavioral YA está, lo cual es CIERTO): las ~226 rutas · Kits
  (bundles) · Actionlog (auditoría polimórfica) · EAV dinámico. Son los flecos, no el corazón.

### ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El núcleo funcional + behavioral está COMPLETO**: modelo de datos faithful (incl. refs polimórficos) + reglas +
control de acceso (auth→RBAC→ownership→company-scope) + comportamiento (workflow + stock + **trash/restore**) + valores
derivados (campo computado same-entity) + app que CORRE (CRUD vivo + frontend + deploy). **Cross-entity-computed (este)**
completa la depreciación faithful. Tras él, la paridad de superficie completa (~226 rutas, Kits, EAV dinámico, assigns
polimórfico) es trabajo de BREADTH — los flecos, no el corazón.

---

## §Evidencia — CERRADO 2026-06-23T13:38Z (verde por bloqueo, no narrado)

**Construido GENERAL en `codegen/scaffold_product.py` (FÁBRICA, opt-in byte-neutro), adoptado en `products/snipeit/
product.yml`:**
- **Gramática** (`_validate_computed_ast` gana `xnumeric`): un operando STRING con `.` (`<ref>.<campo>`) → `<ref>` ∈ los
  refs REQUERIDOS no-poly de la entidad, `<campo>` ∈ los numéricos REQUERIDOS no-computados del target. `_load_blueprint`
  arma `xnumeric` y lo pasa. Fail-closed (ref/campo inexistente o no-requerido → scaffold rojo). 1er-cut: ref+campo
  REQUERIDOS, depth-1.
- **El JOIN** (`_row_json_fn` ahora recibe `by`; threadeado por `_mutation_fns`/`_repository_kt`): separa fuentes
  same-entity (`c<Campo>`) / cross-entity (`x<Ref><Campo>`); un LEFT JOIN por ref DISTINTO
  (`leftJoin(TGT).on(TBL.<REF>.eq(TGT.ID))`), selecciona `TGT.<CAMPO>`, lee null-safe. Dos refs a la MISMA tabla →
  fail-closed (alias jOOQ diferido). El chasis se emite como cadena de calls que **wrappea (ChainWrapping) cuando una
  entidad ANCHA + el JOIN pasan 160** (`_SEED_NUM` nuevo + la rama de wrap del `sel`).
- **El oráculo** (`_COMPUTED_PROOF` gana `%XSRC_SETUP%`/`%CEVAL_SRC%` OPT-IN): con cross-entity, `XSRC` trae el valor
  SEMBRADO de cada `<ref>.<campo>` (el target de un ref requerido se siembra con samples deterministas = `_SEED_NUM`,
  espeja `_KT_SAMPLE`) y el eval cruza `POST_BODY ∪ XSRC`; sin cross-entity usa `POST_BODY` directo → byte-idéntico.
- **Adopción faithful (snipeit)**: `depreciation_months` MOVIDO de `Asset` a `AssetModel` (per-modelo, requerido);
  `Asset.current_value = max(purchase_cost − purchase_cost/model_id.depreciation_months, 0)` lo lee cross-entity (depth-1).

**Verificación POR BLOQUEO:**
- EYEBALL byte-neutro: base/assets + snipeit-same-entity (la rama opt-in vacía) → 0 diffs.
- `product-run --product snipeit` → **PASS**; RTM **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
- **Diente de DOS lados VIVO**: anulé el valor leído del JOIN (`val x<…> = 0.0`) → `product-run` → **SÓLO**
  `access_control_live` (s9) rojo, hermanos (`observability_live`+`frontend_consume_live`) + s0–s8 verdes → revertí →
  PASS. ⚠️ El 1er intento (`val x = 0.0  // TOOTH`) tenía DOBLE espacio → ktlint `NoMultipleSpaces` (s2, antes de s9):
  un sabotaje runtime no puede meter un hallazgo de FORMA — degradá sólo la LÓGICA.
- `ci --rederive`: full-stack-kotlin **12/12** · assets **11/11** · snipeit **11/11** == pin (SIN re-pin: el eje vive
  dentro de s9, ningún check/estación nuevo).
- `meta check` **6/6** (`generality`). `git diff src/metafactory + seed = 0`. base/assets `product.yml` = 0.

**Commits:** `feat(fsk): FSK-XENTITY-COMPUTED …` (codegen) + `feat(snipeit): Asset.current_value cross-entity …`
(producto) + `docs(fsk): cerrar FSK-XENTITY-COMPUTED (§Evidencia) + abrir FSK-POLY-ASSIGNS`.

**Siguiente (abierto, recomendado):** `FSK-POLY-ASSIGNS` — el `assigns` polimórfico del verbo de workflow (ver §7 +
`docs/work/FSK-POLY-ASSIGNS-INCREMENT.md`). Es DECISIÓN de la próxima sesión (alternativas en §7).
