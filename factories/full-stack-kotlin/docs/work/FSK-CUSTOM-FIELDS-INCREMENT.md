<!-- meta:doc sha=a4873cabb33ecc183c7541fedea6575b1a47df15 updated=2026-06-27T01:41Z -->
# Incremento FSK-CUSTOM-FIELDS — campos personalizados por modelo (el EJE GRANDE)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (2026-06-22T14:31Z) — Avenue A, **sub-eje `format`/validación** entregado (ver §Evidencia al final). El EAV
> dinámico a runtime (Avenue B) sigue DIFERIDO y VISIBLE. Creado 2026-06-22T13:50Z. El `increment status` lee este header **o**
> con `meta increment close --factory full-stack-kotlin`. Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-DOMAIN-OPS con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (deferral 1 — el EJE GRANDE, el último gran eje de fábrica de Snipe-IT)

**FSK está MUY MADURO.** Cerrados ya: CRUD del grafo entero · self-ref · ownership opcional/RTD · refs requeridos
transitivos (4 ejes de MODELO-DE-DATOS) · **verbos de dominio checkout/checkin** (1er eje de COMPORTAMIENTO,
FSK-DOMAIN-OPS). El trabajo sigue product-driven (`products/snipeit/docs/reference/SNIPEIT-DOMAIN.md §3 #1 / §4 #6`).

**Este = deferral 1 (`SNIPEIT-DOMAIN.md §3 #1`, "alto impacto")**: en Snipe-IT un admin define **campos
personalizados** ("MAC Address", "Garantía", …) que se agrupan en **fieldsets** asociados a **AssetModels**; cada
campo tiene un **tipo** + un **`format`** (regla de validación: ANY/NUMERIC/ALPHA/IP/MAC/URL/EMAIL/DATE/regex) +
opcionalmente **encrypted**. Los valores viven en columnas dinámicas `_snipeit_<slug>_<id>` de la tabla `assets`.
Es **EAV / schema dinámico definido a RUNTIME** — y ahí está la tensión.

**LA TENSIÓN ARQUITECTÓNICA (leéla antes de diseñar)**: toda la arquitectura de FSK es **schema BUILD-TIME**: el
blueprint declara entidades+campos → contrato OpenAPI → SQL de migración → **jOOQ tipa los queries DESDE ese
schema** → kotlinc compila contra columnas REALES (DES-12). Una columna definida a RUNTIME **no existe en compile**
→ no hay tipo jOOQ → no compila. Por eso este eje es el más "fraught": **"custom fields a runtime" choca de frente
con el modelo tipado-en-compile.** No lo resuelvas por inercia — DECIDÍ el avenue primero (§★).

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso: CRUD + control de acceso + verbos checkout/checkin vivos):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥540000ms** (el sandbox mata
gradle: exit 144). **cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del
hook `stop_proof` al cerrar). Debe dar **PASS**, RTM snipeit **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **s7 PG 5435 · s9 puertos 18593-18595 + PG 5436/5437 · s11 18596** → NUNCA dos corridas en paralelo, NUNCA
dejes un `product-run`/`ci` en BACKGROUND al cerrar el turno (`stop_proof` re-corre la estación activa → colisión
de puerto → falso rojo).

**2) INVESTIGÁ Snipe-IT custom fields a fondo ANTES de diseñar** (no lo hagas de memoria). Lo mínimo a entender:
fieldsets ↔ AssetModel (un AssetModel tiene UN fieldset; un fieldset agrupa N custom_fields); los `format` (las
reglas de validación); `field_values` (un select de opciones); encrypted; y la convención de columna
`_snipeit_<slug>`. Fuente: el repo real grokability/snipe-it (custom_fields/custom_fieldsets), y lo ya destilado
en `SNIPEIT-DOMAIN.md §3 #1`.

**3) LA DECISIÓN DE DISEÑO (resolvela explícitamente — es lo más importante de este increment):**
- **Avenue A — custom fields DECLARADOS en el blueprint (recomendado para EMPEZAR, BOUNDED)**: los campos
  personalizados se declaran en DATA (no se crean a runtime). El aporte NUEVO sobre los campos normales es el eje
  **`format`/regla de validación**: un campo gana un modifier `format: ip|mac|email|url|numeric|regex:<pat>` y el
  codegen emite la **validación a RUNTIME** (el codec del cuerpo, `_codec_helpers`/`_parse_fn`, rechaza un valor que
  no matchea → 400, fail-closed). Esto **COMPONE** sobre el body-parsing ya construido + el diente de "tipo
  equivocado → 400". El **fieldset↔model** se modela como "estos campos viven en la entidad X" (ya es así). Captura
  (tipo + format + validación), DIFIERE la definición-a-runtime. Es tratable en UN increment y da valor real.
- **Avenue B — EAV dinámico a RUNTIME (faithful, FRAUGHT, probablemente DEMASIADO para un increment)**: una tabla
  genérica `custom_field_values(entity_id, field_id, value_text/jsonb)` + una tabla de DEFINICIONES, con los valores
  validados/tipados en código de app (NO por jOOQ/compile). Rompe el modelo tipado-en-compile → es un cambio de
  arquitectura, no aditivo. **Recomendación: NO arrancar acá.** Si lo elegís, acotalo y declaralo como su propio eje.
- **RECOMENDACIÓN de quien cerró FSK-DOMAIN-OPS**: arrancá por **Avenue A**, y dentro de A, por el **sub-eje
  `format`/validación** (el aporte más limpio y composable: añade una regla de validación a runtime sobre el
  body-parsing). Eso de-riskea y deja la definición-dinámica (B) explícitamente diferida y VISIBLE. Un increment
  honesto y acotado > un mega-increment que toca todo. Validá la decisión con el ingeniero si dudás.

**EL DISEÑO (resolvelo GENERAL, cero nombres de dominio — `generality` verde es el anti-overfit real):** sea cual
sea el avenue, la regla nueva (p.ej. `format`) es DATA del blueprint (un modifier de campo), el codegen la emite, y
un gate la PRUEBA por bloqueo. Opt-in/byte-neutro: un campo sin la regla nueva → contrato/migración/codec/proof
byte-idénticos (verificá con el EYEBALL §3 ANTES del gradle: default/assets deben quedar 68/68 byte-idénticos).

**EL DIENTE de dos lados** (criterio §6.2): un valor que VIOLA la regla (p.ej. un `format: mac` con "no-es-mac") →
**400** a runtime; un valor válido → 201. Saboteá la validación generada (que acepte cualquier cosa) → el 400 se
vuelve 201 → **SÓLO el check afectado rojo** (s9 `access_control_live`), hermanos verdes → revertí → verde. ⚠️ **El
sabotaje que muerde a RUNTIME NO puede introducir un hallazgo ESTÁTICO** (detekt/ktlint) que muerda antes en s2 —
ponelo donde no lo linte detekt, o en el lado Python del proof (lección CARA, §3).

---

## 1. ⚠️ RE-PIN — ¿hace falta?
Si la regla nueva vive DENTRO de los checks existentes (s9 `access_control_live` / s0 compile / s5 route_check, todos
ya pineados), el **`proof_sha` queda INTACTO** → pines byte-idénticos, **SIN re-pin** (como los últimos 5
incrementos). **NO agregues check/estación nuevos si podés evitarlo.** `git diff snipeit/product.yml ≠ 0` es
ESPERADO; el sustrato + default/assets product.yml DEBEN quedar en 0. `proof_sha = sha256({station, sorted(check_name,
exit)})` — invariante a qué hace el código. **Si default/assets re-derivan ≠ pin**, tu cambio NO fue opt-in/byte-neutro.
Si SÍ agregás un check/estación (p.ej. una migración con una tabla EAV nueva probada en s1) → re-pin justificado, y
**re-materializá el chasis por defecto** (restaurá los hand-edits de `stations/s*.yml`, re-pineá los 3 productos).

## 2. Maquinaria a REUTILIZAR (no la reinventes) — TODO en `codegen/scaffold_product.py`
- **`_load_blueprint`** (~L161) — la validación fail-closed del blueprint; agregá ahí la validación del modifier nuevo
  (mismo patrón que `operations`/`transitions`/`owned_by`: forma + dominio cerrado + raise honesto).
- **`_codec_helpers`** (~L3365) / **`_parse_fn`** (~L3346) — el codec del cuerpo (JSON→tipo, fail-closed → 400). Si el
  eje es `format`/validación, ACÁ es donde un valor que no matchea la regla debe ser rechazado (`require(...)`).
- **`_oapi_inline`** (~L359) / **`_openapi_yaml`** (~L258) — el contrato; un `format`/regla se documenta como vendor
  extension (`x-format`, como `x-transitions`/`x-required-roles` — openapi-generator/ts la IGNORAN, verificado).
- **`_migration_sql`** (~L1000) / **`_repository_kt`** (~L1108) — el schema + los queries jOOQ tipados (si el avenue
  necesita columnas/tablas nuevas).
- **`_access_control_check_py`** (~L4060, bloque `_OPERATIONS_PROOF` / `%OPERATIONS_BLOCK%`) — el patrón EXACTO para
  agregar un bloque de proof opt-in byte-neutro (placeholder "" sin la feature → byte-idéntico). Copialo.
- **`build_files`** (~L4920) — el ensamblado; toda emisión opt-in se gatea ahí o dentro de cada generador.
- **Validación M0/codegen**: una regla mal formada → `raise SystemExit` honesto (como las validaciones existentes).

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **EYEBALL SIN gradle ANTES de cada corrida lenta**: scratch python con `importlib` que carga `codegen/
  scaffold_product.py` HEAD vs working, `build_files(bp)` para default/assets, y **diffea** (deben quedar 68/68
  byte-idénticos). El scratch de esta sesión está en `/tmp/eyeball.py` (HEAD vs working para default/assets/snipeit) —
  re-usalo. Para inspeccionar snipeit-con-feature: `/tmp/eyeball3.py`/`/tmp/eyeball4.py` (build a un árbol + dump +
  `route_check` 4 modos + `py_compile` del proof). **Esto cazó el 100% de los problemas de byte-neutralidad y
  contrato↔rutas ANTES de gradle.**
- **Un sabotaje que debe morder a RUNTIME no puede introducir un hallazgo ESTÁTICO antes.** En FSK-DOMAIN-OPS invertí
  la precondición `canTransition` (saqué el `!`) — flip de RUNTIME que NO vuelve ningún símbolo no-usado → mordió en
  s9, no en s2. (Antecedente: `+ 9999L` en Kotlin → detekt MagicNumber → s2; el sabotaje fue al lado Python del proof.)
  **ktlint MaxLineLength=160; detekt MagicNumber ignora -1/0/1/2 pero NO 9999; ReturnCount ≤ 2 (usá `return when`);
  CyclomaticComplexMethod ≤ 15 (un dispatcher generado → `@Suppress` opt-in, como hice con `handle`).**
- **El handoff puede SOBRE- y SUB-estimar los sitios.** Verificá qué generadores YA manejan el caso ANTES de tocarlos.
- **`meta verify` re-corre la estación ACTIVA con `build=False`** (no regenera). La activa tras un product-run es
  **s11**. Para un tooth en s9: **sabotear el codegen + `product-run`** (rojo en s9, las posteriores no corren) →
  revertir → `product-run` verde (restaura la activa verde, clave para que `stop_proof` no bloquee el cierre del turno).
- **`meta station` corre la META-línea (m00-m08), NO la línea FSK.** Para la línea FSK: `product-run`.
- **`proof_protect` DENIEGA tocar `.proof/` por shell** (incluso leer el log) — pero el **Read tool SÍ** lee
  `.proof/logs/` (es un RESUMEN: nombre de check + exit; el `exit=0` es la señal autoritativa).
- **`ci --rederive` por producto**: `--product snipeit`/`--product assets` (instancias) y SIN `--product` (la línea
  base/default, que tiene su propio `pinned_verdict.json` en la raíz de la fábrica). No existe `--product default`.
- **`dangerouslyDisableSandbox: true`** para gradle/docker. cwd SIEMPRE en la raíz. FOREGROUND, un producto a la vez.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento)
Refs **polimórficos** (deferral 2: checkout `assigned_to`→User|Location|Asset), **company-scoping** (deferral 8),
**ciclos cross-entidad** (deferral 6: Location/Department.manager_id→User), **soft-deletes/Actionlog** (deferral 12),
**CANTIDADES** (sub-eje de los verbos: checkout de Accessory/Consumable decrementa `qty`, libera seat de License —
quedó diferido en FSK-DOMAIN-OPS). **EAV dinámico a runtime** (Avenue B de este eje) si no lo abarcás acá.

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py` + quizá `factory.spec.yml`/`stations/*.yml` si la grama nueva necesita
  validación M0 o una estación) es nivel FÁBRICA → **este incremento** lo cubre (header ABIERTO).
- **La adopción** (`products/snipeit/product.yml`) es nivel PRODUCTO → abrí TAMBIÉN `meta increment open --factory
  full-stack-kotlin --product snipeit <slug>` ANTES de tocar `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) + `feat(snipeit): …` (product.yml) + `docs(fsk): cerrar
  FSK-CUSTOM-FIELDS (§Evidencia) + abrir <siguiente>`.
- **Probá POR BLOQUEO**: `product-run --product snipeit` PASS · diente de dos lados vivo · `ci --rederive --factory
  full-stack-kotlin` (base) + `--product assets` + `--product snipeit` == pin (los 3) · `meta check` 6/6 (`generality`
  verde) · `git diff src/+seed = 0` · default+assets product.yml = 0.

## 6. Criterio de cierre (demostrable, no narrable)
1. La regla/feature elegida (recomendado: `format`/validación de campo) declarada en `products/snipeit/product.yml` y
   `product-run --product snipeit` **PASS** — el server vivo VALIDA el valor a runtime (regla violada → 400; válido → 201).
2. **Diente de DOS lados verificado VIVO**: saboteá la validación generada → ROJO **sólo** en el check afectado → revertí
   → verde.
3. `ci --rederive` (base + assets + snipeit) == pin. `meta check` 6/6 (`generality` verde). `git diff src/metafactory +
   seed = 0`. `git diff` default+assets product.yml = 0. (Si tocaste el set de checks → re-pin justificado.)
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md §3 #1 / §4` actualizados. Abrí el SIGUIENTE con su handoff autocontenido (§7).

## 7. Qué viene DESPUÉS (para que sepas dónde estás parado)
Orden del push Snipe-IT (`products/snipeit/docs/reference/SNIPEIT-DOMAIN.md §4`):
- ~~CRUD-mutación~~ ✅ · ~~self-ref~~ ✅ · ~~ownership opcional/RTD~~ ✅ · ~~refs requeridos no-dueño / seed transitivo~~ ✅
  · ~~verbos de dominio checkout/checkin~~ ✅ (FSK-DOMAIN-OPS).
- **(este)** custom-fields (deferral 1) — el eje GRANDE.
- **diferidos DUROS** (red/scope): push a un registry · e2e Playwright · AppServer-en-contenedor con PG · ciclos
  cross-entidad (deferral 6) · checkout polimórfico (deferral 2) · **cantidades** (qty decrement en checkout de
  Accessory/Consumable) · EAV dinámico a runtime (Avenue B) si no se abarcó acá.

---

## Evidencia (CERRADO 2026-06-22T14:31Z) — Avenue A, sub-eje `format`/validación

**Qué se entregó (la DECISIÓN del §★ resuelta = Avenue A, el sub-eje `format`).** Un campo `string` del blueprint
gana un modifier OPCIONAL `format: <nombre>` (vocabulario CERRADO: `numeric`/`alpha`/`email`/`url`/`ip`/`mac`) — la
REGLA DE VALIDACIÓN del VALOR, el aporte nuevo de un custom field sobre un string normal. El codegen la emite y un
gate la PRUEBA por bloqueo. Los campos se DECLARAN en DATA (no se crean a runtime); el EAV dinámico (Avenue B) queda
diferido y VISIBLE (deferral 1 / SNIPEIT-DOMAIN §3 #1). **El EJE GRANDE, acotado a un increment honesto** (handoff §★).

**El mecanismo (todo GENERAL, `git diff src/metafactory + seed = 0`; cero nombres de dominio):**
- **Gramática + vocabulario cerrado** (`scaffold_product.py`): `_FORMAT_REGEX` (nombre→patrón regex). Validación
  fail-closed en `_load_blueprint`: `format` sólo sobre `string`; el nombre ∈ `_FORMAT_REGEX` (un format fantasma →
  `raise`), mismo patrón que el guard de tipos/operations.
- **El codec a RUNTIME** (`_codec_helpers`/`_parse_fn`): un string con `format` se parsea con `strFmt(o, k, FMT_<NAME>)`
  — `val s = str(o, k); require(re.matches(s)) { k }` → un valor que no matchea el patrón (match COMPLETO) → excepción
  → `runCatching` → null → **400** (compone sobre el body-parsing de FSK-CRUD-BODY-PARSING; `Regex` es default-import
  de `kotlin.text` → sin import nuevo). Un `FMT_<NAME>` por format USADO (dedup/sorted, raw-string), cada uno ≥1 parser
  (sin `UnusedPrivateMember`).
- **El contrato** (`_oapi_inline`): un string con `format` documenta la regla como vendor extension `x-format: <nombre>`
  (como `x-transitions`/`x-required-roles`/`x-owned-by`; openapi-generator/openapi-typescript la IGNORAN — el contrato
  sigue parseando) → fuente inspectable de "qué regla valida ese campo" (DES-6).
- **El proof** (`_access_control_check_py`): bloque opt-in `%BAD_FORMAT_BLOCK%` — un cuerpo VÁLIDO de tipo (string)
  pero que VIOLA el format → **400** + el count NO cambia. Los samples del POST/FORM (`_proof_post_value`/
  `_proof_form_value` vía `_format_sample`) pasan a ser valores VÁLIDOS para el format (si no, el POST normal 201 se
  rompería).

**Opt-in/byte-neutro** (verificado por EYEBALL importlib HEAD vs working, sin gradle): **default + assets 68/68
byte-idénticos** (un campo sin `format` → contrato/codec/proof byte-idénticos). `git diff` default+assets product.yml
= 0. **`proof_sha` INTACTO → SIN re-pin** (la regla vive DENTRO de `access_control_live`/s9 + s0 compile + s5
route_check, ya pineados; pin snipeit/assets/default sin tocar).

**Adopción PRODUCTO** (ADR-016, incremento `CUSTOM-FIELDS-ADOPT` aparte): snipeit `Asset` gana
`{ name: mac_address, type: string, format: mac }` (REQUERIDO → el server vivo lo lee del cuerpo, `_input_fields`) —
el custom field canónico de Snipe-IT ("MAC Address" con format MAC).

**Verde, no fingido (POR BLOQUEO):**
- `product-run --product snipeit` **PASS** · RTM **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless; el format NO
  agrega requisito → se prueba dentro de `access_control_live`, sin over-claim).
- **Diente de DOS lados VIVO** (s9): degradé el patrón `FMT_MAC` a `.*` (acepta cualquier string — flip de codegen
  que NO introduce hallazgo estático, la línea llegó a s9) → `observability_live ok · access_control_live FAIL(1) ·
  frontend_consume_live ok` (el POST de formato inválido pasó de 400 a 201) → revertí → **PASS**.
- `ci --rederive` base **12/12** · assets **11/11** · snipeit **11/11** == pin (clones limpios). `meta check` **6/6**
  (`generality` verde). `git diff src/metafactory + seed = 0`.

**Lección destilada (de las del §3):** el sabotaje que muerde a RUNTIME sin tocar lo estático fue **degradar el
PATRÓN** (`FMT_MAC = Regex(".*")`) — `re` sigue usado, ningún símbolo no-usado, ningún MagicNumber (los `{n}` viven
dentro del string literal del regex). Idéntico espíritu al `canTransition` de FSK-DOMAIN-OPS.

**Commits:** `feat(fsk): FSK-CUSTOM-FIELDS — format/validación de campo (Avenue A)` · `feat(snipeit): Asset.mac_address
format:mac` · `docs(fsk): cerrar FSK-CUSTOM-FIELDS + CUSTOM-FIELDS-ADOPT (§Evidencia) + abrir FSK-XENTITY-CYCLES`.
