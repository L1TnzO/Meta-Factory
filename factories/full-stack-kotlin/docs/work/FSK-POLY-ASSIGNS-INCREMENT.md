# Incremento FSK-POLY-ASSIGNS — el verbo de workflow ASIGNA a un ref POLIMÓRFICO (checkout a User|Location|Asset)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO**
> (creado 2026-06-23T13:38Z). Cerralo flippeando este header a CERRADO **o** con
> `meta increment close --factory full-stack-kotlin`. Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-XENTITY-COMPUTED con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (y por qué es DECISIÓN tuya)

**El NÚCLEO FUNCIONAL + BEHAVIORAL faithful está COMPLETO.** Cerrados, product-driven por Snipe-IT: modelo de datos
(CRUD del grafo · self-ref · ownership opcional/RTD · refs requeridos transitivos · ciclos cross-entidad · **ref
polimórfico**) · acceso (auth→RBAC→ownership→company-scope) · comportamiento (**workflow checkout/checkin** · qty/stock
· trash/restore) · valores derivados (computado same-entity + **cross-entity**) · app que CORRE (CRUD vivo + frontend +
deploy).

**Lo que falta de genuinamente nuevo (no breadth pura): el `assigns` POLIMÓRFICO del verbo.** Hoy un verbo de workflow
con `assigns` (FSK-DOMAIN-OPS) asigna a un ref de UN SOLO target (un `Long` al cuerpo → `set(<campo>, target)`). En
Snipe-IT el checkout asigna a un target POLIMÓRFICO — un activo se asigna a un **User | Location | Asset**
(`assigned_to_type` + `assigned_to_id`). FSK-POLYMORPHIC-REFS ya modela el ref polimórfico (DATA) y FSK-DOMAIN-OPS ya
monta el verbo con `assigns` (BEHAVIOR); este incremento los COMPONE: un verbo que asigna a un ref polimórfico setea las
DOS sub-columnas (`<campo>_type` + `<campo>_id`) del cuerpo del verbo.

**Por qué es un buen próximo:** (a) cierra el último eje BEHAVIORAL genuino (el checkout polimórfico FAITHFUL); (b)
COMPONE dos primitivas YA probadas (cero invención de mecanismo nuevo); (c) **determinista, sin s6/LLM**; (d) diente de
dos lados claro (el round-trip de (tipo, id) tras el verbo). Tras él, lo que resta es **breadth pura**.

**⚠️ ESTA ES TU DECISIÓN (con más contexto).** Si al investigar decidís que NO es el mejor próximo, alternativas
honestas en §7. Tenés autoridad para reabrir — pero leé los wrinkles ANTES.

### 0.1 LOS WRINKLES
1. **El `assigns` apunta a un ref POLIMÓRFICO** — hoy `_load_blueprint` valida que `assigns`/`clears` nombran un campo
   `ref` (línea ~582: `fld_by[ref].get("type") != "ref"`). Un ref polimórfico TAMBIÉN tiene `type: "ref"` (con `to` =
   lista), así que la validación pasa — pero el resto del codegen asume UN target. Hay que detectar el caso poly
   (`_is_poly(fld_by[assigns])`) y ramificar.
2. **La mutación setea DOS columnas, no una** — `_operation_repo_fns` (línea ~1685) hoy emite `set(<campo>, target)` con
   un `target: Long`. Para un assigns poly: `set(<campo>_TYPE, type).set(<campo>_ID, id)` con DOS args del cuerpo (el
   discriminador `type: String` + el `id: Long`). La firma del repo-fn cambia (`(ctx, id, assignType, assignId)`).
3. **El handler parsea DOS valores del cuerpo** — `_operations_handlers` (línea ~4614) hoy hace `longArg(body,
   "<campo>")` para el target. Para poly: parsear `<campo>_type` (String, validar ∈ los targets de la unión — fail-
   closed, como el codec `enumOf` del poly) + `<campo>_id` (Long). Mirá cómo `_codec_helpers`/`enumOf` valida el
   discriminador en FSK-POLYMORPHIC-REFS (el `<campo>_type` es un enum CERRADO de los nombres de target).
4. **El proof cruza el round-trip de (tipo, id)** — tras el verbo, GET /{id} debe traer `<campo>_type`/`<campo>_id` ==
   lo asignado. Reusá el patrón de `_POLY_PROOF` (que ya cruza el discriminador de un POST normal) + el patrón de
   `_OPERATIONS_PROOF` (que cruza la mutación de un verbo). El diente: degradar el set del discriminador en el repo-fn →
   el GET no refleja el target asignado → SÓLO s9 rojo.

**Conclusión honesta**: el camino BOUNDED — **un `assigns` cuyo campo es un ref polimórfico → el verbo parsea
`<campo>_type`+`<campo>_id` del cuerpo (fail-closed en el discriminador) → setea ambas sub-columnas → el proof cruza el
round-trip**. La adopción faithful: el `assigned_to` de Asset (hoy `assigned_user_id`→User) pasa a polimórfico
(User|Location|Asset) y el checkout lo asigna. ⚠️ Ojo con el wrinkle #3 de FSK-POLYMORPHIC-REFS: el `owned_by` NO puede
ser polimórfico (el OwnershipGuard cruza un Long único). Snipe-IT usa `assigned_to` (polimórfico, el checkout) DISTINTO
del dueño; acá puede que necesites un campo polimórfico NUEVO (`checkout_target`) separado del `owned_by`, o re-pensar
la relación dueño/asignado. **Investigá esto ANTES** (es la decisión de modelado central).

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
- **Gramática** (`_load_blueprint`, ~582): permitir `assigns` poly (detectar `_is_poly(fld_by[assigns])`). Sin poly el
  camino queda EXACTO (byte-neutro).
- **`_operation_repo_fns`** (~1685): para un `assigns` poly, emitir `set(<campo>_TYPE, assignType).set(<campo>_ID,
  assignId)` con firma `(ctx, id, assignType: String, assignId: Long)`; sin poly, byte-idéntico (`set(<campo>, target)`).
- **`_operations_handlers`** (~4614): parsear `<campo>_type` (String, validar ∈ targets — fail-closed) + `<campo>_id`
  (Long) del cuerpo; un tipo fuera de la unión → 400. Mirá `longArg`/`strArg` y el `enumOf` del codec poly.
- **El contrato + RouteTable**: el verbo ya emite su ruta (FSK-DOMAIN-OPS); el cuerpo del verbo NO se modela (detalle de
  impl, como hoy). Verificá que route_check sigue cuadrando.
- **El proof** (`_OPERATIONS_PROOF` + el patrón de `_POLY_PROOF`): tras el verbo con (tipo, id), GET cruza
  `<campo>_type`/`<campo>_id` == lo asignado. Diente: degradar el set del discriminador → SÓLO s9 rojo.

**EL DIENTE de dos lados**: el verbo asigna (tipo₂, id₂) → GET trae (tipo₂, id₂). Degradar el repo-fn (hardcodear/
dropear el `set(<campo>_TYPE, …)`) → el GET no refleja el target asignado → **SÓLO** `access_control_live` (s9) rojo,
hermanos + s0–s8 verdes → revertí → verde. ⚠️ El sabotaje debe degradar la LÓGICA/SQL, no la forma Kotlin.

---

## 1. ⚠️ RE-PIN — casi seguro NO hace falta
El cambio vive DENTRO de `access_control_live` (s9) SIN check/estación nuevos → `proof_sha` INTACTO → pines
byte-idénticos, **SIN re-pin** (como qty/poly/computed/soft-deletes/xentity). `git diff snipeit/product.yml ≠ 0` es
ESPERADO; el sustrato + default/assets product.yml DEBEN quedar en 0.

## 2. Maquinaria a REUTILIZAR — TODO en `codegen/scaffold_product.py` (verificá los anchors con grep)
- **FSK-POLYMORPHIC-REFS**: `_is_poly` · `_poly_subfields` (`<campo>_type`/`<campo>_id`, marcados `poly_type`/`poly_id`)
  · el codec `enumOf` que valida el discriminador · `_POLY_PROOF`/`_WR_POLY_VALID` (el round-trip de (tipo,id)).
- **FSK-DOMAIN-OPS**: `_operation_repo_fns` (la mutación atómica del verbo) · `_operations_handlers` (`longArg` + el
  `return when` que compone modifyVerdict → canTransition → mutación) · `_OPERATIONS_PROOF`/`%OPERATIONS_BLOCK%`.
- **El patrón OPT-IN del proof**: un bloque `%...BLOCK%` vacío sin el eje → byte-idéntico; el DATA nuevo va DENTRO.

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **EYEBALL SIN gradle ANTES de cada corrida lenta**: scratch con `importlib` que carga el scaffold HEAD vs working,
  llama `build_files(bp)` para base/assets/snipeit-SIN-el-eje, y **diffea** (byte-idénticos). Hay un `eyeball.py`
  reutilizable en el scratchpad de la sesión anterior (adaptá los nombres). Snapshot HEAD: `git show
  HEAD:factories/full-stack-kotlin/codegen/scaffold_product.py > /tmp/.../scaffold_head.py`. Lo nuevo va OPT-IN (vacío →
  byte-idéntico); NUNCA cambies un comentario/constante INCONDICIONALMENTE (rompe la byte-neutralidad — pasó con
  `_COMPUTED_PROOF` en FSK-XENTITY-COMPUTED hasta que el XSRC se hizo opt-in con `%XSRC_SETUP%`/`%CEVAL_SRC%`).
- **Un sabotaje que muerde a RUNTIME no puede meter un hallazgo ESTÁTICO antes.** Degradá el SQL/la lógica, no la forma.
  **ktlint MaxLineLength=160; `NoMultipleSpaces` (¡un DOBLE espacio antes de un `//` rompe s2!); detekt LongMethod ≤ 60;
  CyclomaticComplexMethod ≤ 15; ReturnCount ≤ 2; MagicNumber ignora -1/0/1/2 pero NO 3+; NoUnusedImports + -Werror;
  ktlint StringTemplate (sin llaves sobre un identificador simple); jOOQ DDLDatabase tipa toda columna NULLABLE.**
- **com.sun.net.httpserver NO loguea la excepción de un handler** (cierra la conexión → el proof ve `RemoteDisconnected`/
  "infra_up no alcanzó la infra en 120s"). Diagnóstico de un crash: reproducir MANUALMENTE — `docker run … postgres@
  sha256:…` (puerto 5436) + `java -cp build/install/<pkg>/lib/* <pkg>.endpoints.AppServerKt` + curl + `docker exec <pg>
  psql`.
- **`meta verify` re-corre la estación ACTIVA con `build=False`** (no regenera). Para un tooth en s9: sabotear el codegen
  + `product-run` (rojo en s9) → revertir → `product-run` verde (restaura la activa verde, clave para el cierre).
- **`proof_protect` DENIEGA tocar `.proof/` por shell** — el **Read tool SÍ** lee `.proof/logs/` (son RESÚMENES: check +
  exit; el `exit=0` es la señal autoritativa).
- **`ci --rederive` por producto**: `--product snipeit`/`--product assets` y SIN `--product` (la base). Cada uno es un
  clon limpio (≈< 10 min), UNO A UNO en foreground.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento)
**`creates`/pivot de qty** (insertar AccessoryCheckout) · **owner POLIMÓRFICO** de Asset (wrinkle #3 de poly: el
ownership cruza un Long único) · **cross-entity DEPTH-2** (Asset→AssetModel→Depreciation.months) + **time-elapsed** ·
**EAV dinámico a runtime** (custom-fields Avenue B) · **PUT de campos OPCIONALES arbitrarios** · **e2e Playwright /
browser real** · **AppServer-en-contenedor con PG** · **Actionlog (auditoría polimórfica)** · **las ~226 rutas / Kits**.

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py` + quizá spec/stations si la grama nueva necesita validación M0) es nivel FÁBRICA
  → **este incremento** lo cubre (header ABIERTO).
- **La adopción** (`products/snipeit/product.yml`: el campo polimórfico + el verbo con `assigns` poly) es nivel PRODUCTO
  → abrí TAMBIÉN `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) + `feat(snipeit): …` (product.yml) + `docs(fsk): cerrar
  FSK-POLY-ASSIGNS (§Evidencia) + abrir <siguiente>`. **Commiteá el CÓDIGO mientras el incremento está ABIERTO**, luego
  flipeá el header a CERRADO en el commit de docs.
- **Probá POR BLOQUEO**: EYEBALL byte-neutro · `product-run --product snipeit` PASS · diente de dos lados vivo (sólo
  s9) · `ci --rederive` (base + assets + snipeit) == pin (los 3) · `meta check` 6/6 (`generality` verde) · `git diff
  src/metafactory + seed = 0` · default+assets product.yml = 0.

## 6. Criterio de cierre (demostrable, no narrable)
1. Un verbo de workflow declara un `assigns` a un ref POLIMÓRFICO y `product-run --product snipeit` **PASS** — el server
   vivo (s9): el verbo asigna (tipo, id) del cuerpo, GET /{id} trae `<campo>_type`/`<campo>_id` == lo asignado; un tipo
   fuera de la unión → 400 fail-closed.
2. **Diente de DOS lados verificado VIVO**: degradá el set del discriminador en el repo-fn → ROJO **sólo** en
   `access_control_live` (s9) → revertí → verde.
3. EYEBALL byte-neutro (base/assets + snipeit-sin-poly-assigns) · `ci --rederive` (base + assets + snipeit) == pin ·
   `meta check` 6/6 (`generality` verde) · `git diff src/metafactory + seed = 0` · default+assets product.yml = 0.
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md` (deferral del checkout polimórfico) actualizados. Abrí el SIGUIENTE con su
   handoff (§7).

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE
Si al investigar decidís que poly-assigns NO es el mejor próximo (es tu decisión con más contexto), las otras candidatas
BOUNDED, framed honestamente:
- **`creates`/pivot de qty** (sub-eje diferido de FSK-QTY-OPERATIONS): un verbo que INSERTA una fila pivote (p.ej.
  AccessoryCheckout) en vez de decrementar — el M:N real del checkout de accesorios. Toca `creates` +
  `_operation_repo_fns` (un INSERT en vez de UPDATE) + el proof.
- **Cross-entity DEPTH-2** (extiende FSK-XENTITY-COMPUTED): la fórmula resuelve una CADENA de refs (Asset→AssetModel→
  Depreciation.months) — un JOIN encadenado. Acotado pero "menos dimensión nueva" (un JOIN más profundo).
- **Breadth pura** (si decidís que el núcleo funcional + behavioral YA está, lo cual es CIERTO): las ~226 rutas · Kits ·
  Actionlog (auditoría polimórfica) · EAV dinámico. Son los flecos, no el corazón.

### ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El núcleo funcional + behavioral está COMPLETO**: modelo de datos faithful (incl. refs polimórficos) + acceso
(auth→RBAC→ownership→company-scope) + comportamiento (workflow + stock + trash/restore) + valores derivados
(same-entity + cross-entity) + app que CORRE (CRUD vivo + frontend + deploy). **Poly-assigns (este)** completa el
checkout polimórfico FAITHFUL. Tras él, la paridad de superficie completa (~226 rutas, Kits, EAV dinámico, creates/
pivot, owner polimórfico, cross-entity depth-2) es trabajo de BREADTH — los flecos, no el corazón.
