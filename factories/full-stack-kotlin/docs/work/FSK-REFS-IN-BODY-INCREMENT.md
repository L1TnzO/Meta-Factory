# Incremento FSK-REFS-IN-BODY — el espinazo RELACIONAL: refs requeridos desde el cuerpo del request

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (abierto 2026-06-21T19:28Z · cerrado 2026-06-21T20:50Z). Evidencia abajo (§Evidencia).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-CRUD-OWNERLESS con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## Evidencia (cierre, 2026-06-21T20:50Z) — demostrado POR BLOQUEO, no narrado

**Qué quedó VIVO.** Una entidad ownerless con un `ref` REQUERIDO no-dueño obtiene **CRUD vivo con la FK del cuerpo**
(el espinazo RELACIONAL). Selección DATA-agnóstica `_live_with_ref` (cero nombres de dominio): la 1ª entidad sin
dueño, con `write_roles`, cuyos refs requeridos apuntan a targets **sembrables** (`_ref_target_seedable`: el target
no tiene refs requeridos propios) → en **snipeit = AssetModel** (`category_id`→Category). default (Task→Project, no
sembrable: Project tiene `owner_id` requerido → cadena de profundidad >1, diferida) y assets (sin refs requeridos
no-dueño) → **None** → opt-out limpio (intactos). El POST acepta el id del ref (`Long` vía `longOf`, codec
compartido), lo persiste type-bound; el server **siembra el target** (`seedRows`/`_seed_chain` generalizado a
`_ref_targets`) y expone su id por **`/seed` `refs`**; el INSERT con FK colgante se **ATRAPA** (`runCatching` →
**409**, no 500). Aditivo: la entidad con dueño y la 1ª ownerless quedan intactas (sus dientes no se mueven).

**1. `product-run` PASS en los 3** (gradle real, foreground por la colisión de puerto fijo de s9): snipeit PASS ·
default PASS · assets PASS. RTM snipeit **23/24** (único UNSAT = REQ-F-007/s6 LLM keyless, deferral VISIBLE).

**2. Diente de DOS lados verificado VIVO.** Saboteé el atrape de la FK (forcé el with_ref al camino sin
`runCatching` + quité el const `HTTP_CONFLICT`, compila limpio sin símbolos sin usar) → `product-run snipeit` **FAIL
1/3**: **SÓLO `access_control_live` ROJO** (`observability_live` + `frontend_consume_live` VERDES) — el ref colgante
deja de ser fail-closed → el proof no obtiene 409 → rojo PRECISO y AISLADO. Revertí → `product-run snipeit` PASS.

**3. `ci --rederive` == pin en los 3** (árbol limpio, aislado): snipeit **10/10** · default **11/11** · assets
**10/10** proof_sha **== pineado**. Como EXTENDÍ el check existente `access_control_live` (sin check nuevo) el
`proof_sha` NO cambió → **pines byte-idénticos, sin re-materializar** (la lección de §3, confirmada al derecho).

**4. `meta check` 6/6** (compile · docs · projection · isolation · **generality** · suite). **Anti-overfit**:
`git diff` de TODO `product.yml` = **0** (el producto es DATA, ADR-012) · `git diff src/metafactory/ + seed/` = **0**
(el sustrato no se tocó; todo cabe en `codegen/scaffold_product.py` + `factory.spec.yml`). El único "nombre de
dominio" en el diff de codegen es un EJEMPLO en un docstring (`_live_with_ref` da AssetModel en snipeit), idéntico al
estilo de `_live_ownerless` — la LÓGICA es DATA-agnóstica.

**5. RTM / trazabilidad.** refs-en-el-body **no agrega requisito nuevo** (evita over-claim: default/assets no tienen
una entidad así): se PLEGÓ en la capability existente **`entrada_tipada_runtime` (REQ-F-016)** — el invariant/tech/
proof ahora cubren el ref del cuerpo + el diente FK-colgante→409. Se quitó "refs-en-el-body = declared-deferred" de
REQ-F-015/016/019 y de `crud_mutacion_runtime`/`crud_ownerless_runtime`. `pinned_verdict.json` es **per-estación**
(s0..s10), NO el RTM → cambiar prosa del spec no toca el pin.

**Seams tocados** (todo en `codegen/scaffold_product.py`): `_KT_FIELD_TYPE` (`ref`→`Long`) · `_input_fields`
(incluye el ref requerido no-dueño) · `_live_with_ref`/`_ref_targets`/`_ref_target_seedable` (selección nueva) ·
`_live_entities` (suma with_ref) · `_mutation_fns` (ref del body) · `_parse_fn`/`_codec_helpers` (`longOf` + import
`kotlinx.serialization.json.long`) · `_ownerless_handlers(catch_fk)` (FK-catch→409) · `_app_server_kt` +
`_APP_SERVER_SKELETON` (seed de targets, `/seed refs`, mount, `HTTP_CONFLICT`) · `_access_control_check_py` +
skeleton (bloque with-ref: válido→201+round-trip, colgante→409, prohibido→403, tipo-equivocado→400, count).

**Huecos que QUEDAN** (próximos ejes, ver el SIGUIENTE incremento): cadenas de refs de profundidad >1 (target con su
propio ref requerido, p.ej. Task→Project→User) · self-refs (`Location.parent_id`) · refs polimórficos · refs
OPCIONALES del body · CRUD de TODAS las entidades vivas (hoy 1 con dueño + 1ª ownerless + 1ª con-ref) · render EN
BROWSER (mount DOM + eventos) + el form que postea · deploy real (Dockerfile vivo) + e2e Playwright.

---

## 0. POR QUÉ este incremento (la decisión estratégica — leéla, no la saltees)

La capa viva ya cubre **(a)** la entidad con dueño (CRUD bajo ownership) y **(b)** la 1ª entidad **ownerless** escalar
(CRUD RBAC-only, FSK-CRUD-OWNERLESS). Pero **toda entidad cuyo POST necesita un `ref` REQUERIDO no-dueño sigue afuera
de la capa viva**: hoy `_input_fields` EXCLUYE los refs y `_mutation_fns`/`_seed_chain` **LANZAN** ante un ref requerido
no-dueño (restricción #3 del blueprint FSK histórico). Eso bloquea el **espinazo relacional** del dominio.

Por qué es el de MAYOR palanca ahora: en Snipe-IT **muchas** entidades tienen un `ref` requerido a otra entidad —
`AssetModel.category_id`→Category, `License.category_id`, `Accessory.category_id`, `Consumable.category_id`,
`Component.category_id`, … (grep `required (faithful)` en `products/snipeit/product.yml`). Sin refs-en-el-body, esas
entidades generan a nivel de contrato (s0→s8) pero **no son creables a runtime**. Levantar esto hace que **el grafo
relacional entero** (no entidades aisladas) sea usable: creás una Category, después un AssetModel que la referencia,
después un Asset que referencia el AssetModel. **Es el paso que convierte "entidades sueltas usables" en "una app
relacional usable".**

**Hermano YA cerrado (de dónde venís):** FSK-CRUD-OWNERLESS levantó el opt-in a `owned_by` para la 1ª entidad ownerless
ESCALAR. Este incremento levanta la siguiente restricción: el `ref` requerido en el cuerpo. Detalle:
`docs/work/FSK-CRUD-OWNERLESS-INCREMENT.md §9` + `docs/LOG.md` (2026-06-21T19:28Z).

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso: server vivo con CRUD para la entidad con dueño + la 1ª ownerless escalar):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, por-producto** (el sandbox de Bash mata gradle: exit 144).
**Mantené el cwd de Bash en la RAÍZ del repo** — un `cd` a un subdir FILTRA el cwd persistente y rompe el cierre de
turno (deadlock del hook `stop_proof`); usá paths absolutos o subshells `( cd … )`. Debe dar **PASS** (s0→s10). RTM
snipeit **23/24** (único UNSAT = REQ-F-007/s6 LLM keyless).

**2) Entendé los 5 seams que HOY rechazan/excluyen el ref** (todo en `codegen/scaffold_product.py`; los nº de línea
son aproximados, buscá el texto):
- **`_input_fields`** (~L908): `… and f["type"] != "ref" …` → **EXCLUYE** los refs del cuerpo. Hay que incluir el ref
  requerido **no-dueño** (el dueño SIGUE viniendo del token, no del body — no lo toques).
- **`_input_data_class`** + **`_KT_FIELD_TYPE`** (~L104): un `ref` debe mapear a **`Long`** (el id de la FK). Hoy
  `_KT_FIELD_TYPE` no tiene `ref` (porque `_input_fields` los excluía).
- **codec `_codec_helpers`/`_parse_fn`** (~L3060/L3030): el `coerce` dict no tiene `"ref"`. Hace falta un coercionador
  `longOf(o, k)` (un `Long` del JSON: `prim(...).long`, estricto `require(!p.isString)`) + import
  `kotlinx.serialization.json.long`. El contrato YA modela el ref como `{type: integer, format: int64}` (`_OAPI_TYPE`
  ~L95), así que el `Pick` del cliente lo incluye sin cambios de contrato.
- **`_mutation_fns`** (~L1018): `elif f["type"] == "ref": raise SystemExit(...)` → cambialo a `set(col,
  input.<camel>)` (el id del body) para el ref requerido **no-dueño**. El dueño (`owned_by`) SIGUE siendo `ownerId`.
- **`_live_ownerless`** (~L922) y/o el seam de selección: hoy `and not any(f["type"]=="ref" and required …)` EXCLUYE
  entidades con ref requerido. Levantá eso para la entidad elegida (ver §1 scope).

**3) EL PROBLEMA DURO (resolvelo bien — es la razón de que sea un incremento aparte):** un `ref` requerido es una **FK
a una fila que DEBE EXISTIR**. Para que el proof POSTee un AssetModel válido, una Category tiene que existir y el proof
tiene que saber su `id`. Tres caminos (elegí; recomendación abajo):
- **(A) Sembrar el target + exponer su id por `/seed`** (recomendado, menos superficie): el `AppServer` siembra UNA
  fila de cada entidad que es target de un ref requerido de una entidad servida, y `/seed` expone `{…, "<tabla>":
  <id>}`. El proof lee ese id y lo manda en el body. Reusa el idiom de `seedRows`/`_seed_chain` (que YA siembra el
  owner); generalizalo a "sembrá los targets de refs requeridos". **Cuidado con el orden topológico** (sembrá Category
  antes que AssetModel) y con cadenas (un target con su PROPIO ref requerido → recursión/orden).
- **(B) Encadenar a través del cliente vivo**: si el target ES una entidad servida (p.ej. Category es ownerless
  escalar), el proof la CREA por POST, captura el id, y POSTea la entidad referenciante. Más fiel a "una app relacional"
  pero exige que el target esté servido.
- **(C)** combinar: sembrar como piso + un test de encadenamiento e2e arriba.

**El DIENTE NUEVO de dos lados (el corazón del incremento):** ref **VÁLIDO** (id existente) → **201**; ref **COLGANTE**
(id inexistente, p.ej. `id+9999`) → la FK lo rechaza → el server debe responder **400/409 fail-closed** (NO 500, NO
tragar). Hoy el INSERT con FK rota tiraría `DataAccessException` → hay que ATRAPARLA en el handler (igual que
`parse<E>Input` atrapa el body malo → 400). Saboteá el atrape (que un ref colgante pase / 500) → rojo.

---

## 1. Objetivo + scope acotado (qué deja TERMINADO)

Una entidad con un `ref` REQUERIDO no-dueño obtiene **CRUD vivo**: el POST acepta el id del ref en el cuerpo, lo
persiste type-bound (la FK existe → 201; cuelga → 4xx fail-closed). Demostrado e2e sobre la PG viva, mismo rigor que
los hermanos.

**Scope acotado (recomendado, decidilo vos):** montá **la 1ª entidad con un ref requerido no-dueño cuyos OTROS campos
requeridos son escalares** y cuyo target del ref es **seedable/servible** (heurística DATA-agnóstica, cero nombres de
dominio). En snipeit eso es **AssetModel** (`category_id`→Category, resto escalar); Category es ownerless escalar
(seedable). **Diferí**: cadenas de refs de profundidad >1, refs OPCIONALES desde el body (son otro eje menor),
self-refs (`Location.parent_id`→Location, ciclo), y refs polimórficos. **Mantené intactas** la entidad con dueño y la
1ª ownerless escalar (sus dientes no se mueven).

**Decisión de arquitectura (resolvela GENERAL):** ¿extendés la selección `_live_entities` para incluir la entidad
con-ref (y su target como entidad sembrada), o agregás un seam de "seed de targets de refs requeridos"? RECOMENDACIÓN:
generalizá `seedRows` para sembrar los targets requeridos (camino A) y extendé `_live_ownerless`→`_live_with_refs` para
admitir refs requeridos cuyos targets son seedables. Lo que importa para el cierre: que una entidad **con ref requerido**
tenga CRUD vivo probado e2e con el diente ref-válido/ref-colgante.

---

## 2. Maquinaria a REUTILIZAR (no la reinventes)
- **`_seed_chain`** (~L3045): YA siembra el owner + la fila con dueño (jOOQ tipado, captura el id). Generalizalo a
  "sembrá una fila de cada target de ref requerido y capturá su id"; hoy LANZA ante un ref requerido no-dueño (mismo
  patrón a levantar que en `_mutation_fns`).
- **`_codec_helpers`/`_parse_fn`** (~L3030/L3060): el codec compartido sobre la unión de entidades servidas — sumale
  `longOf` (coerción de id). El parser de la entidad con-ref lo usa.
- **`_app_server_handlers`** (entidad con dueño) y **`_ownerless_handlers`** (RBAC-only): la entidad con-ref ownerless
  reusa `_ownerless_handlers` casi tal cual (sólo cambia que su `parse<E>Input` ahora incluye el/los ref). El atrape de
  FK colgante → 400/409 va en `doPost<E>` (envolvé el `Repository.insert<E>` en runCatching → badRequest/conflict).
- **`access_control_check.py`** (el proof de `access_control_live`): EXTENDELO con el bloque ref (ref válido→201,
  colgante→4xx). Lee el id del target de `/seed`.

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **⚠️ Re-materializar el chasis SÓLO si sumás/quitás un CHECK.** Si EXTENDÉS `access_control_check.py` (mismo check
  `access_control_live`) → el `proof_sha` NO cambia → **pines byte-idénticos, sin re-materializar, sin re-pinear**
  (así fueron FSK-CRUD-OWNERLESS y RENDER-LIST). **PREFERÍ extender el check existente.** Si en cambio sumás un check
  nuevo (`crud_refs_live`): las instancias re-materializan solas pero el producto **DEFAULT** usa el `stations/`
  COMMITEADO y `product-run` NO lo re-materializa → re-materializá a mano (`from metafactory.codegen.renderer import
  _materialize_line` sobre el factory root con el spec subst) → `git checkout` la churn de `s0.yml` → `product-run`
  default → `pin` default.
- **Server vivo por `java -cp build/install/<pkg>/lib/*`, NUNCA `gradle run`** (el daemon forkea el JVM → leak de
  puerto). Ya cableado en s9 (`factory.spec.yml` ~L729/L743 y la infra de s9).
- **`proof_protect` DENIEGA tocar `.proof/` por shell (incluso leer)** → usá `meta rtm`/`meta recall`; el árbol
  generado (`products/<p>/build/product/...`) SÍ es legible.
- **Eyeball SIN gradle antes de cada corrida lenta** (la sesión anterior cazó TODO sin gradle así): emití los 3
  productos a temp y leé el Kotlin/Python. Patrón que funcionó:
  ```python
  import sys, yaml; from pathlib import Path
  sys.path.insert(0, "factories/full-stack-kotlin/codegen"); import scaffold_product as S
  froot = Path("factories/full-stack-kotlin").resolve()
  bps = {"default": S._load_blueprint(froot)}
  for p in ("assets","snipeit"): bps[p] = yaml.safe_load((froot/"products"/p/"product.yml").read_text())
  for n,bp in bps.items(): files = S.build_files(bp); ...  # escribí AppServer.kt/Repository.kt/access_control_check.py
  ```
  Verificá: `python3 -m py_compile` del proof generado · sin `%PLACEHOLDER%` sin sustituir · `{` vs `}` balanceados ·
  sin líneas en blanco consecutivas (ktlint `no-consecutive-blank-lines`) · `build_files(bp)` idéntico dos veces
  (idempotencia). Un `it[<TBL>.ID]` es `Long?` en jOOQ → `!!` si una fn pide `Long` (lección de RENDER-LIST).
- **Puertos/PG por check** (si sumás infra): `access_control_live` 18594/5436/fsk_s9_ac_pg · `frontend_consume_live`
  18595/5437/fsk_s9_fe_pg. Reusá `access_control_live` y no necesitás puerto nuevo.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes
Token estático `Bearer <rol>:<principal>`. RBAC opt-in (`write_roles`), ownership opt-in (`owned_by`). El **dueño**
sigue viniendo del TOKEN (no del body) — sólo los refs **NO-dueño** entran por el cuerpo. `tsc --strict` + ESLint
strict + `no-explicit-any` + ts-reset muerden `client.ts`; detekt (≤160/línea, ≤2 returns/fun, sin wildcard,
LongMethod ≤60) + `-Werror` muerden el Kotlin; el consumer en `frontend/` NO se type-checkea. **Self-refs +
cadenas-de-refs profundas + refs polimórficos + refs opcionales-del-body = DIFERIDO.**

## 5. Disciplina + dónde van los docs
- **Contenido de FÁBRICA GENERAL** (`codegen/` + `factory.spec.yml`): **cero nombres de dominio**, `git diff` de TODO
  `product.yml` = 0. El producto es DATA (ADR-012). Anti-overfit real = el gate `generality` de `meta check`, NO `git
  diff src==0` literal — pero lo NORMAL acá es NO tocar sustrato (`src/metafactory/`+`seed/`): todo cabe en
  codegen/spec. Si necesitás sustrato → incremento META aparte + `generality` verde.
- **Docs**: historia de la FÁBRICA → `docs/{STATE.md,LOG.md}` (ADR-016). El gobierno de ESTE incremento → este doc
  (flip a CERRADO + §Evidencia al cerrar). **Commit = parte del trabajo (ADR-010), nunca lo preguntes**; trailers I-10
  (`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`).
- **Probá POR BLOQUEO**: `product-run` PASS en los 3 · `ci --rederive --all-products` == pin (los 3) · `meta check`
  6/6 (`generality` verde; `projection` la re-sincroniza `meta checkpoint` si cae roja) · `git diff product.yml` = 0 ·
  idealmente `git diff src/metafactory/ + seed/` = 0. **No fakees verde.**

## 6. Criterio de cierre (demostrable, no narrable)
1. `product-run` PASS en los 3 (default·assets·snipeit). Una entidad **con ref requerido no-dueño** tiene CRUD vivo: el
   proof asevera POST con ref VÁLIDO (del target sembrado/creado) → 201 + INSERT real; el round-trip del cuerpo trae el
   ref correcto. Server caído → rojo.
2. **Diente de DOS lados verificado VIVO**: ref **COLGANTE** (id inexistente) → 400/409 fail-closed (no 500, no 201);
   saboteá el atrape de la FK (que el ref colgante pase / 500) → corré → confirmá ROJO **sólo** en el check de refs
   (hermanos s9 verdes) → revertí → verde.
3. `ci --rederive --all-products` == pin (los 3). `meta check` 6/6 (`generality` verde). `git diff product.yml` = 0.
   Si extendiste `access_control_live` (recomendado), NO hace falta re-materializar (pines byte-idénticos); si sumaste
   un check, re-materializá el chasis + re-pineá el default (§3).
4. El scope honesto se actualiza: STATE/LOG (fábrica) registran "refs requeridos del body ✅" + los huecos que QUEDAN
   (cadenas profundas · self-refs · refs polimórficos · refs opcionales-del-body · CRUD de TODAS las entidades · render/
   form/browser/deploy/Playwright). Abrí el SIGUIENTE con su handoff autocontenido.

## 7. Qué viene DESPUÉS de refs-in-body (para que sepas dónde estás parado)
Con refs-in-body, **la capa de DATOS de Snipe-IT queda completa** (el grafo entero es CRUD-able por API). Lo que falta
para "Snipe-IT usable en un navegador y deployado" (= después podés enfocarte SÓLO en el producto): **(a)** CRUD para
TODAS las entidades vivas (hoy 1 con dueño + 1ª ownerless + 1ª con-ref → generalizar a N) · **(b)** render EN BROWSER
(mount real del DOM + eventos) + el FORM que postea vía el cliente · **(c)** deploy real (el `Dockerfile` ya se genera
pero no se levanta/verifica vivo) + e2e Playwright. Después de esos 2-3 ejes, lo que QUEDA es product-specific (los 12
deferrals de `products/snipeit/docs/reference/SNIPEIT-DOMAIN.md`: custom-fields, checkout polimórfico, company-scoping,
depreciación calculada, …) — eso YA es "enfocarse en el producto", no en FSK.
