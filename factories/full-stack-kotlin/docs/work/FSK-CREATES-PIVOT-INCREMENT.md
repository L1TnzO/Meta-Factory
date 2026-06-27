<!-- meta:doc sha=bb81c30fd463a21a69f82ffe16155c0931dce117 updated=2026-06-27T01:41Z -->
# Incremento FSK-CREATES-PIVOT — un verbo de workflow/stock INSERTA una fila PIVOTE (el checkout M:N real)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (creado 2026-06-23T16:41Z · cerrado 2026-06-23T19:38Z — ver §Evidencia). Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-POLY-ASSIGNS con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (y por qué es DECISIÓN tuya)

**El NÚCLEO FUNCIONAL + BEHAVIORAL faithful está COMPLETO** (cerrado en FSK-POLY-ASSIGNS, 2026-06-23): modelo de datos
(CRUD del grafo · self-ref · ownership opcional/RTD · refs requeridos transitivos · ciclos cross-entidad · **ref
polimórfico** · **checkout polimórfico**) · acceso (auth→RBAC→ownership→company-scope) · comportamiento (**workflow
checkout/checkin con assigns poly** · qty/stock · trash/restore) · valores derivados (computado same+cross-entity) ·
app que CORRE (CRUD vivo + frontend + deploy). **Lo que resta es BREADTH** — los flecos, no el corazón.

**El último MECANISMO behavioral genuino que falta: un verbo que CREA (INSERTA) una fila, no que muta una existente.**
Hoy un verbo de dominio (FSK-DOMAIN-OPS) hace UPDATE: muta un enum (workflow), asigna/limpia un ref (assigns/clears
poly o simple) o decrementa un int (qty). NINGUNO **inserta una fila nueva**. En Snipe-IT el checkout de un **accesorio**
es un M:N real: además de decrementar el stock disponible, **inserta una fila en `accessories_checkout`** (el log de
"quién tiene qué"). Hoy `Accessory.checkout` sólo `decrements: qty` (FSK-QTY-OPERATIONS); la fila pivote
(`AccessoryCheckout`) existe como entidad CRUD pero el verbo NO la crea. Este incremento agrega `creates: <PivotEntity>`
a un verbo → al disparar, **INSERTA una fila** en la pivote seteando el FK-al-sujeto + los campos del cuerpo.

**Por qué es un buen próximo:** (a) es el ÚLTIMO mecanismo behavioral genuino (insert-on-verb, vs los tres update-on-verb
ya hechos); (b) COMPONE sobre FSK-QTY-OPERATIONS (el verbo qty ya existe; sólo SUMA el insert) + FSK-REFS-IN-BODY (el
insert con FK del cuerpo, fail-closed) — poco mecanismo nuevo; (c) determinista, sin s6/LLM; (d) diente de dos lados
claro (tras el verbo, la fila pivote EXISTE con el sujeto + el cuerpo correctos).

**⚠️ ESTA ES TU DECISIÓN (con más contexto).** Si al investigar decidís que NO es el mejor próximo, alternativas honestas
en §7 (owner polimórfico · cross-entity depth-2 · breadth pura de rutas). Tenés autoridad para reabrir — pero leé los
wrinkles ANTES.

### 0.1 LOS WRINKLES
1. **La pivote necesita un ref AL SUJETO** — `AccessoryCheckout.accessory_id → Accessory`. El verbo (sobre Accessory)
   setea ESE FK al id del sujeto; los OTROS campos de input (`assigned_user_id`, `note`) vienen del cuerpo. Detectá el
   FK-al-sujeto por `to == <entidad del verbo>` (como el self-ref de `_it_repository_kt`). Fail-closed si la pivote no
   tiene un ref al sujeto.
2. **El insert con FK del cuerpo es fail-closed** — `assigned_user_id` es un ref → la FK debe existir → un id colgante
   → `runCatching` → **409** (como FSK-REFS-IN-BODY: el server siembra un User y `/seed` expone su id; un id+9999 → 409).
3. **OBSERVAR la fila insertada es lo no-trivial** — el proof necesita VER que la fila pivote apareció. Opciones (elegí
   la más limpia, byte-neutra): (a) la pivote ya es una entidad VIVA servible (tiene refs requeridos → `_live_with_ref`
   podría servirla) → `GET /<pivot>s` lista y el round-trip cruza la fila nueva; (b) `/seed` expone un contador de la
   pivote antes/después; (c) un `GET /<pivot>s` con count N→N+1 tras el verbo. El verbo qty vive sobre la entidad
   with_ref (Accessory en snipeit) → mirá cómo `_QTY_PROOF` ya tiene `WR_PLURAL`/`qtyId` en scope.
4. **El verbo COMPONE qty + creates** — `Accessory.checkout` hace AMBOS: `decrements: qty` Y `creates: AccessoryCheckout`.
   El repo-fn del verbo qty hoy es un UPDATE condicional (`AND qty > 0`); el creates SUMA un INSERT. Decidí el orden y la
   atomicidad (¿el insert sólo si el decremento afectó 1 fila? — faithful: no checkout-eás si no hay stock). El handler
   ya devuelve 409 si qty==0; el insert va DESPUÉS del decremento exitoso.

**Conclusión honesta**: el camino BOUNDED — **un verbo gana `creates: <PivotEntity>` → al disparar (tras pasar el guard
+ el decremento/transición), INSERTA una fila en la pivote (FK-al-sujeto = el id del sujeto + los campos de input del
cuerpo, fail-closed en FK colgante) → el proof cruza que la fila EXISTE con el sujeto+cuerpo correctos**. Adopción
faithful: `Accessory.checkout` gana `creates: AccessoryCheckout` (hoy sólo `decrements: qty`).

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥540000ms** (el sandbox mata gradle).
**cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del hook `stop_proof` al
cerrar; si pasa, `cd` de vuelta a la raíz INMEDIATAMENTE; usá subshells `( cd … )` para no filtrarlo). Debe dar **PASS**,
RTM snipeit **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **s7 PG 5435 · s9 puertos 18593-18595 + PG 5436/5437 · s11 18596** → NUNCA dos corridas en paralelo, NUNCA dejes un
`product-run`/`ci` en BACKGROUND al cerrar el turno (`stop_proof` re-corre la estación activa → colisión de puerto/PG).

**2) EL DISEÑO (GENERAL, cero nombres de dominio):**
- **Gramática** (`_load_blueprint`, ~535+ donde se validan `operations`): permitir `creates: <Entity>` en un verbo;
  validar fail-closed que `<Entity>` existe Y tiene un `ref` cuyo `to` == la entidad del verbo (el FK-al-sujeto).
- **`_operation_repo_fns`**: para un verbo con `creates`, emitir un INSERT en la tabla pivote
  (`ctx.insertInto(PIVOT).set(<subjectFK>, subjectId).set(<col>, <param>)…`) con los campos de input del cuerpo. Sin
  `creates`, byte-idéntico.
- **`_operations_handlers`**: parsear los campos de input de la pivote (los `_input_fields` de la pivote MENOS el
  FK-al-sujeto) del cuerpo, llamar al insert tras el guard/decremento; FK colgante → `runCatching` → 409.
- **El proof** (`_QTY_PROOF` o un bloque hermano): tras el verbo, la fila pivote EXISTE con el sujeto+cuerpo correctos.
  Diente: dropear/degradar el `set(<subjectFK>, …)` → la fila no aparece / con sujeto equivocado → SÓLO s9 rojo.

**EL DIENTE de dos lados**: el verbo crea la fila → GET de la pivote la trae con (sujeto, cuerpo). Degradar el insert
(dropear un `set` / sujeto equivocado / no-insertar) → la fila falta o está mal → **SÓLO** `access_control_live` (s9)
rojo, hermanos + s0–s8 verdes → revertí → verde. ⚠️ El sabotaje debe degradar la LÓGICA/SQL, no la forma Kotlin (un
param sin usar → `-Werror` lo flagea ESTÁTICO antes que s9; degradá manteniendo los params usados).

---

## 1. ⚠️ RE-PIN — casi seguro NO hace falta
El cambio vive DENTRO de `access_control_live` (s9) SIN check/estación nuevos → `proof_sha` INTACTO → pines
byte-idénticos, **SIN re-pin** (como qty/poly/computed/soft-deletes/xentity/poly-assigns). `git diff snipeit/product.yml
≠ 0` es ESPERADO; el sustrato + default/assets product.yml DEBEN quedar en 0. (Si el insert necesitara una entidad
pivote NUEVA servida o un check nuevo, re-evaluá — pero el camino bounded reusa la pivote existente.)

## 2. Maquinaria a REUTILIZAR — TODO en `codegen/scaffold_product.py` (verificá los anchors con grep)
- **FSK-QTY-OPERATIONS**: `_qty_ops` · `_operation_repo_fns` (el UPDATE condicional del decremento) ·
  `_operations_handlers` (el handler qty: 409 si qty==0) · `_QTY_PROOF`/`%QTY_BLOCK%` (con `WR_PLURAL`/`qtyId`).
- **FSK-REFS-IN-BODY**: `_live_with_ref` · `_ref_targets`/`_seed_chain` (sembrar el target de una FK) · el `runCatching`
  → 409 del insert con FK colgante · `/seed refs` (exponer el id de la FK válida).
- **FSK-CRUD-OWNERLESS/BODY-PARSING**: `_mutation_fns` (el INSERT tipado de una entidad) · `_input_fields`/`_input_cols`
  · `parse<E>Input`/el codec compartido (parsear el cuerpo del insert).
- **El patrón OPT-IN del proof**: un bloque `%...BLOCK%` vacío sin el eje → byte-idéntico; el DATA nuevo va DENTRO.
- **El patrón "detectar el ref al sujeto"**: `_it_repository_kt` ya detecta self-ref por `to == nombre de la entidad`.

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **EYEBALL SIN gradle ANTES de cada corrida lenta**: hay un `eyeball.py`/`eyeball_head.py`/`regen.py` reutilizables en
  el scratchpad de la sesión anterior (cargan el scaffold HEAD vs working con `importlib`, llaman `build_files(bp)` para
  base/assets/snipeit y **diffean** byte a byte). El que aísla el codegen usa el product.yml de HEAD (`git show
  HEAD:…/product.yml`) para que el diff de snipeit sea SÓLO el eje del codegen, no el del producto. Lo nuevo va OPT-IN
  (vacío → byte-idéntico); NUNCA cambies un comentario/constante INCONDICIONALMENTE (rompe la byte-neutralidad).
- **Un sabotaje que muerde a RUNTIME no puede meter un hallazgo ESTÁTICO antes.** Degradá el SQL/la lógica, no la forma.
  **ktlint MaxLineLength=160 (un `.set()` de más puede wrappear: usá `_jooq_chain`); `NoMultipleSpaces`; detekt
  LongMethod ≤ 60 (un INSERT exhaustivo puede pasarlo → `@Suppress` como `_row_json_fn`/`main`/`seedRows`;
  `SpacingBetweenDeclarationsWithAnnotations` exige un BLANCO antes de un `@Suppress`); CyclomaticComplexMethod ≤ 15;
  ReturnCount ≤ 2; MagicNumber ignora -1/0/1/2 pero NO 3+; NoUnusedImports + -Werror (un param sin usar → rojo);
  ktlint StringTemplate sin llaves sobre identificador simple; jOOQ DDLDatabase tipa toda columna NULLABLE.**
- **com.sun.net.httpserver NO loguea la excepción de un handler** (cierra la conexión → el proof ve
  `RemoteDisconnected`/"infra_up no alcanzó la infra en 120s"). Si s9 cae así: chequeá primero los HERMANOS
  (`observability_live`/`frontend_consume_live`) — si VERDES, el server vive y es la aserción de TU proof la que falla
  (no un crash); si TODOS rojos, el server crashea → reproducí MANUALMENTE (`docker run … postgres@sha256:…` 5436 +
  `java -cp build/install/<pkg>/lib/* <pkg>.endpoints.AppServerKt` + curl).
- **`proof_protect` DENIEGA tocar `.proof/` por shell** — el **Read tool SÍ** lee `.proof/logs/` (son RESÚMENES).
- **`ci --rederive` por producto**: `--product snipeit`/`--product assets` y SIN `--product` (la base). Cada uno clon
  limpio (< 10 min), UNO A UNO en foreground (cabe en el timeout de 600000ms). `meta check` es el self-check del meta
  (compile/docs/projection/isolation/generality/suite — RÁPIDO, NO re-deriva productos: eso lo hace `ci --rederive`/m06).

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento, breadth)
**owner POLIMÓRFICO** de Asset (wrinkle #3 de poly: el ownership cruza un Long único — requeriría un OwnershipGuard
sobre una unión) · **cross-entity DEPTH-2** (Asset→AssetModel→Depreciation.months) + **time-elapsed** · **EAV dinámico
a runtime** (custom-fields Avenue B) · **PUT de campos OPCIONALES arbitrarios** · **e2e Playwright / browser real** ·
**AppServer-en-contenedor con PG** (s11 hoy usa el ObsServer PG-free) · **Actionlog (auditoría polimórfica)** · **Kits
(bundles)** · **las ~226 rutas**.

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py` + quizá spec/stations si la grama nueva necesita validación M0) es nivel FÁBRICA
  → **este incremento** lo cubre (header ABIERTO).
- **La adopción** (`products/snipeit/product.yml`: el verbo gana `creates`) es nivel PRODUCTO → abrí TAMBIÉN
  `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) + `feat(snipeit): …` (product.yml) + `docs(fsk): cerrar
  FSK-CREATES-PIVOT (§Evidencia) + abrir <siguiente>`. **Commiteá el CÓDIGO mientras el incremento está ABIERTO**, luego
  flipeá el header a CERRADO en el commit de docs.
- **Probá POR BLOQUEO**: EYEBALL byte-neutro · `product-run --product snipeit` PASS · diente de dos lados vivo (sólo
  s9) · `ci --rederive` (base + assets + snipeit) == pin (los 3) · `meta check` 6/6 (`generality` verde) · `git diff
  src/metafactory + seed = 0` · default+assets product.yml = 0.

## 6. Criterio de cierre (demostrable, no narrable)
1. Un verbo declara `creates: <PivotEntity>` y `product-run --product snipeit` **PASS** — el server vivo (s9): el verbo
   INSERTA una fila pivote (FK-al-sujeto = el id del sujeto + los campos del cuerpo), GET de la pivote la trae; FK
   colgante → 409 fail-closed.
2. **Diente de DOS lados verificado VIVO**: degradá el insert (dropear el `set` del FK-al-sujeto / no-insertar) → ROJO
   **sólo** en `access_control_live` (s9) → revertí → verde.
3. EYEBALL byte-neutro · `ci --rederive` (base + assets + snipeit) == pin · `meta check` 6/6 · `git diff src/metafactory
   + seed = 0` · default+assets product.yml = 0.
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md` (el M:N del checkout de accesorios) actualizados. Abrí el SIGUIENTE con su
   handoff (§7).

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE
Si al investigar decidís que creates/pivot NO es el mejor próximo (es tu decisión con más contexto), las otras
candidatas BOUNDED, framed honestamente:
- **owner POLIMÓRFICO** (extiende FSK-POLY-ASSIGNS + el OwnershipGuard): que el `owned_by` de una entidad sea un ref
  polimórfico → el guard cruza (tipo, id) en vez de un Long. Toca el CORE de auth (OwnershipGuard/OwnershipPolicy/
  modifyVerdict) → más riesgo, pero cierra el wrinkle #3 (en Snipe-IT el `assigned_to` ES el owner Y es polimórfico).
- **Cross-entity DEPTH-2** (extiende FSK-XENTITY-COMPUTED): la fórmula resuelve una CADENA de refs (Asset→AssetModel→
  Depreciation.months) — un JOIN encadenado. Acotado, "menos dimensión nueva".
- **Breadth pura de superficie**: las ~226 rutas · Kits (bundles) · Actionlog (auditoría polimórfica) · EAV dinámico ·
  PUT de campos opcionales arbitrarios. Son los flecos, no el corazón.

### ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El núcleo funcional + behavioral está COMPLETO** (data + acceso + comportamiento + valores derivados + app que CORRE).
**Creates/pivot (este)** agrega el ÚLTIMO mecanismo behavioral (insert-on-verb, el M:N del checkout de accesorios). Tras
él, lo que resta (owner poly, cross-entity depth-2, las ~226 rutas, Kits, EAV, Actionlog, PUT-opcionales, Playwright,
AppServer-en-contenedor) es trabajo de BREADTH y de PROFUNDIDAD-de-detalle — los flecos, no el corazón.

---

## §Evidencia — CERRADO 2026-06-23T19:38Z

Construido EXACTO como el camino BOUNDED de §0/§★ (cero invención). Todo en `codegen/scaffold_product.py` (FÁBRICA,
GENERAL, opt-in byte-neutro) + adopción en `products/snipeit/product.yml` (PRODUCTO). El ÚLTIMO mecanismo behavioral
genuino: un verbo que INSERTA una fila (vs los tres update-on-verb previos). El **núcleo funcional + behavioral faithful
está COMPLETO** tras este incremento.

- **Codegen** (commit `feat(fsk): FSK-CREATES-PIVOT …`):
  - **Gramática** (`_load_blueprint`, rama qty): `creates: <Entity>` SÓLO en un verbo qty (compone sobre el decremento);
    fail-closed → la pivote debe existir, tener un `ref` AL SUJETO (`to == la entidad del verbo`) y ≥1 campo de cuerpo
    (requerido no-sujeto). `creates` en un verbo de workflow → rechazado.
  - **Helpers** `_creates_ops`/`_creates_subject_fk`/`_creates_body_fields`/`_creates_pivots` (DATA-agnósticos).
  - **`_operation_repo_fns(+by)`**: `<verbo><E>Create` = `ctx.transactionResult { ... }` ATÓMICO (el decremento qty
    EXISTENTE reusado dentro de la transacción + el INSERT pivote; null ⟺ sin stock; FK de cuerpo colgante lanza →
    rollback) · `_row_json_fn(pivote)` (la fila insertada, para devolverla).
  - **Codec**: `_input_data_class`→`_creates_input_data_class` (data class `<Pivot>CreateInput` SIN el FK-al-sujeto) ·
    `_parse_fn`→`_parse_fields_fn` (refactor byte-idéntico, generalizado a parser/dc/campos) · `_codec_helpers(+extra_parsers)`
    emite `parse<Pivot>CreateInput` y unona sus tipos (helpers/enum-VALUES). AppServer importa `{pkg}.<Pivot>CreateInput`.
  - **Handler** (`_ownerless_handlers(+by)`): el verbo qty con `creates` gana `body` → parsea el `<Pivot>CreateInput`
    (body malo → 400) → `<verbo><E>Row` (runCatching: null → 409 sin stock; excepción FK → 409 rollback; OK → 200 + la
    fila pivote `rowJson`); el dispatch pasa `payload`. Sin `creates` el handler qty queda BYTE-IDÉNTICO.
  - **Proof** (bloque qty): el verbo toma `_cobody` (escalares + cada ref de cuerpo cableado al `owner` sembrado) en vez
    de `{}` (`%QTY_BODY%`==`{}` sin creates → byte-idéntico) + `%CREATES_ROUNDTRIP%` (sobre una accessory FRESCA: 201 →
    checkout 200 → la pivote round-trippea SUJETO+cuerpo; FK de cuerpo colgante → 409 rollback). `_QTY_BODY_SETUP`/
    `_CREATES_ROUNDTRIP` opt-in (vacíos sin creates).
- **Producto** (commit `feat(snipeit): Accessory.checkout `creates: AccessoryCheckout`…`): el verbo `checkout` gana
  `creates: AccessoryCheckout` (antes sólo `decrements: qty`); la pivote `AccessoryCheckout` gana `assigned_user_id`
  (FK al User, fail-closed) + `note` (round-trip del diente) REQUERIDOS; `accessory_id` = el FK-al-sujeto (del id de la URL).
- **Verde por bloqueo**:
  1. **EYEBALL byte-neutro** — HEAD-codegen vs working-codegen sobre el MISMO bp: base/assets/snipeit-sin-creates
     byte-idénticos; con creates, el diff de snipeit es EXACTAMENTE 3 archivos (Repository.kt · AppServer.kt · access_control_check.py).
  2. **`product-run --product snipeit` PASS** · **RTM 24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
  3. **Diente de DOS lados VIVO** (sobre el server real + PG): degradé el `set(NOTE, input.note)` → `input.note + "X"` →
     `"posted-noteX"` ≠ `"posted-note"` → **SÓLO** la aserción `[creates] round-trippea note` roja; `/health` UP ANTES y
     DESPUÉS (era la ASERCIÓN, no server-caído) + TODAS las demás creates verdes (sujeto `accessory_id==4` · FK
     `assigned_user_id==1` · FK colgante → 409 rollback) → revertí → verde.
  4. **`ci --rederive`** clon limpio == pin (SIN re-pin, `proof_sha` estructural): base **12/12** · assets **11/11** ·
     snipeit **11/11**.
  5. **`meta check` 6/6** (`generality` verde) · **`git diff src/metafactory + seed = 0`** · default+assets product.yml = 0.
- **Lecciones destiladas** (al LOG + memoria cross-sesión):
  - **Composición qty+creates rompe la byte-neutralidad del cuerpo del verbo qty**: el verbo qty-solo manda `{}`; con
    `creates` EXIGE cuerpo → el bloque qty del proof parametrizó `%QTY_BODY%` (`{}` sin creates → byte-idéntico) +
    `%QTY_BODY_SETUP%` (substring de `%QTY_BODY%` → reemplazar SETUP ANTES que BODY).
  - **Atomicidad por transacción = diente limpio**: sin `transactionResult` el FK colgante decrementa stock ANTES de
    fallar (artefacto que ensucia la contabilidad de stock del proof); la transacción rollback lo deja intacto.
  - **El diente sobre un escalar (note) es el más limpio** (200 + valor equivocado, sin FK, sin `-Werror`): `input.note + "X"`
    mantiene el param usado. Un diente sobre el FK-al-sujeto (`id + 1`) manifiesta como 409 (rollback) — válido pero menos limpio.
  - **Observar la fila insertada** (lo no-trivial, wrinkle #3): NO se sirvió la pivote (más mecanismo); el verbo DEVUELVE
    la fila (rowJson re-leído de la PG) en su respuesta 200 → el proof la cruza directo. El body-FK válido = `seed["owner"]`
    (el User dueño que /seed ya expone) — para un body-FK a otra entidad haría falta sembrarla (diferido, ver §7 del próximo).
