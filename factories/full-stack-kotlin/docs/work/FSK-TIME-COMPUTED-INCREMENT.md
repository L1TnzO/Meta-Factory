# Incremento FSK-TIME-COMPUTED — un campo computado depende del TIEMPO TRANSCURRIDO (meses entre una fecha y `now`)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO**
> (creado 2026-06-24). Cerralo flippeando este header a CERRADO **o** con
> `meta increment close --factory full-stack-kotlin`. Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-SERVE-ALL-ENTITIES con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (y por qué es DECISIÓN tuya)

**EL NÚCLEO + LA SUPERFICIE están COMPLETOS** (modelo · acceso · comportamiento · valores-derivados · app-que-corre +
frontend en browser real + **TODAS las entidades servidas a runtime**). De acá en más TODO es **profundidad-de-detalle** —
los flecos, no el corazón.

Este eje es **el ÚLTIMO fleco de VALORES DERIVADOS** y **el MÁS BOUNDED** de los que quedan. Hoy `Asset.current_value`
(snipeit) se computa a partir de `model_id.depreciation_id.months` — el PERÍODO de depreciación (un número estático leído
por 2 JOINs, FSK-XENTITY-DEPTH2). Pero la depreciación REAL de Snipe-IT corre sobre los **meses TRANSCURRIDOS** desde la
fecha de compra (`purchase_date`) hasta **HOY**. Falta UNA pieza: que el AST de un campo computado pueda referir un operando
"**meses entre una fecha y `now`**". Con eso, `current_value` deja de ser una constante por-modelo y se vuelve la
depreciación de verdad (baja con el tiempo).

**⚠️ ESTA ES TU DECISIÓN (con más contexto).** Es el más limpio y acotado, y CIERRA el eje de valores-derivados con
elegancia. Pero si al planificar preferís un eje de mayor VALOR percibido, en §7 hay alternativas HONESTAS (la más fuerte:
**AppServer-en-contenedor con PG en s11** — hoy el deploy_smoke despliega el ObsServer PG-free, no el AppServer real).
Tenés autoridad para reabrir con `meta increment`.

### 0.1 EL WRINKLE CENTRAL — `now` es NO-DETERMINISTA (acá está TODO el riesgo)
Un campo que depende de "hoy" cambia cada día → el proof (que cruza el GET contra un oráculo Python re-derivado)
**no sería determinista** salvo que **MOCKEES `now`**. El patrón del repo para inyectar un valor de entorno determinista
ya existe (mirá `FSK_WEB_DIR`/`FSK_PG_URL`/`FSK_OBS_PORT` en el scaffold): el server lee
**`val today = System.getenv("FSK_NOW")?.let { LocalDate.parse(it) } ?: LocalDate.now()`** (default = hoy real; el proof
fija `FSK_NOW=2030-06-15` o similar). El ORÁCULO del proof conoce ese mismo `FSK_NOW` (lo pasa por env al server VIVO en
s9 vía el `up` de infra_up — DATA de fábrica) y siembra `purchase_date` con un valor DETERMINISTA conocido → puede
re-derivar los meses transcurridos EXACTOS. **Sin mock = test flaky = fingir verde un día y rojo al siguiente. NO lo hagas.**

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥600000ms** (el sandbox mata gradle).
**cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del hook `stop_proof` al
cerrar; usá `cd <raíz> && …` en cada comando o subshells `( cd … )`). Debe dar **PASS**, RTM snipeit **25/26** (único
UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **Puertos en uso por s9**: PG 5436/5437/5438 + servers 18593-18595/18597; s11 18596. NUNCA dos corridas en paralelo.

**2) ENTENDÉ la maquinaria de campos computados** (`codegen/scaffold_product.py`, ya MADURA — este eje la EXTIENDE, no la
reescribe):
- **`_validate_computed_ast` (~252)**: valida el AST fail-closed. Op-set cerrado **`_COMPUTED_OPS`** (`+ - * / min max`).
  Un nodo = número | nombre-de-campo-numérico | `<r1>.<r2>.<campo>` cross-entity | `{op, args}`. **ACÁ agregás** el
  operando de tiempo (un nuevo op, p.ej. `months_since`, cuyo arg ES un campo `date` — fail-closed: el arg debe ser un
  `date` de la entidad).
- **`_computed_srcs` (~289)**: los nombres de campo que el AST referencia (las columnas que rowJson lee a `val`s). El
  campo `date` del nuevo op tiene que entrar acá (rowJson debe leerlo).
- **`_row_json_fn` (~1634)**: emite el Kotlin del rowJson, incluyendo la ARITMÉTICA del AST. **ACÁ emitís**
  `ChronoUnit.MONTHS.between(<purchaseDate>, today).toDouble()` para el nuevo op (con `today` = el `FSK_NOW` mockeable; y
  el import `java.time.temporal.ChronoUnit`). Ojo: un `date` opcional null → decidí 0.0 (o el oráculo lo refleja).
- **`_COMPUTED_PROOF` + `_ceval` (en `_access_control_check_py`, busca `_COMPUTED_PROOF`)**: el oráculo Python que replica
  EXACTO la aritmética Kotlin. **ACÁ replicás** `months_between(purchase, FSK_NOW)` con la MISMA semántica que
  `ChronoUnit.MONTHS.between` para LocalDate: `m = (y2-y1)*12 + (mo2-mo1) - (1 if d2 < d1 else 0)`. El oráculo conoce
  `FSK_NOW` (env) y el `purchase_date` sembrado/posteado.
- **`_SEED_NUM` (~117) / `_KT_SAMPLE` (~107)**: los samples deterministas para el seed/oráculo. Un `date` ya tiene sample
  (`"2026-01-15"` para POST, mirá `_proof_post_value`); fijá `FSK_NOW` lo bastante adelante para meses>0.

**3) EL DISEÑO (GENERAL, cero nombres de dominio):** un nuevo op de AST (`months_since`/`age_months`) cuyo arg es un campo
`date` → el rowJson computa `ChronoUnit.MONTHS.between(date, today)` con `today` mockeable por `FSK_NOW`; el oráculo lo
replica. **Adopción snipeit**: `Asset.current_value` pasa a usar los meses transcurridos desde `purchase_date` (en vez de,
o además de, `depreciation_id.months` como tope). Opt-in: sin el nuevo op, todo byte-idéntico (default/assets sin re-derivar).

**EL DIENTE de dos lados**: con `FSK_NOW` fijo y `purchase_date` sembrado, el GET de `current_value` == la fórmula
re-derivada (que usa los meses transcurridos EXACTOS). Degradá la aritmética del rowJson (p.ej. `MONTHS`→`YEARS`, o restá
mal) → el GET devuelve otro número → SÓLO `access_control_live` (s9) rojo, hermanos verdes → revertí → verde. (Bonus
diente del MOCK: corré el server con DOS `FSK_NOW` distintos → `current_value` cambia → prueba que `now` realmente entra.)

---

## 1. RE-PIN — probablemente **NO** (proof_sha byte-neutro). LEÉ ESTO, te ahorra confusión:
`compute_proof_sha` (`seed/verifier.py`) hashea **`station_id + (check_name, exit_code)`**, **NO** el artefacto generado.
Si EXTENDÉS un check existente (`access_control_live`/s9) o el rowJson SIN agregar/quitar un check ni una estación, el
proof_sha NO cambia → `pinned_verdict.json` byte-idéntico → **el commit feat es SÓLO el codegen** (como FSK-SERVE-ALL,
FSK-XENTITY-DEPTH2, etc.). `ci --rederive --all-products` re-deriva los MISMOS proof_sha == pin. Sólo re-pineás si
agregás/quitás un CHECK o una ESTACIÓN (cambia el set name/exit). Igual: tras verde, `ci --rederive --factory
full-stack-kotlin --all-products` DEBE dar 3/3 == pin.

## 2. Maquinaria a REUTILIZAR (verificá los anchors con grep — el archivo se mueve)
- `_validate_computed_ast` · `_computed_srcs` · `_ast_uses_div` (~252-310) · `_COMPUTED_OPS`/`_COMPUTED_BINARY` (cerca).
- `_row_json_fn` (~1634): la emisión del AST a Kotlin (mirá cómo hoy maneja `+ - * / min max` y los operandos
  cross-entity vía `_xref_resolve` ~221).
- `_COMPUTED_PROOF`/`_XSRC_SETUP`/`_ceval` (en `_access_control_check_py`): el oráculo del proof.
- Inyección de env determinista: patrón `System.getenv("FSK_*") ?: <default>` (ya en seedRows/AppServer/Obs).

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **proof_sha es exit-code-based** (§1): extender un check no re-pinea. NO te asustes si `git status` no muestra cambios
  en `pinned_verdict.json` tras `meta pin` — es CORRECTO (el pin es byte-idéntico).
- **ktlint a escala — la regla `Wrapping` ("Missing newline after {") SALTA BAJO el MaxLineLength de 160** (cerca de
  ~140 para una lambda-chain). Si emitís una cadena con un lambda `.mapNotNull { … }` larga, usá `_jooq_chain(..., budget=
  PROPERTY_WRAP)` (120) para que envuelva. Otras: **MaxLineLength 160** (`_kt_call`/`_jooq_chain` ya envuelven),
  **NoMultipleSpaces** (un doble-espacio antes de `//` red s2), **PropertyWrapping 120**, **NoUnusedImports + -Werror**
  (un import de tipo —p.ej. `ChronoUnit`— SIN usar → rojo; emitilo SÓLO si el op está presente), **LargeClass 600**
  (`@Suppress` opt-in en el object Repository), **ReturnCount ≤ 2**, **CyclomaticComplexMethod ≤ 15**, **LongMethod ≤ 60**.
- **VALIDÁ BARATO ANTES DE GRADLE** (≈10s vs ≈9min): un script `importlib` que carga el scaffold working, llama
  `_load_blueprint` (sobre un `factory.spec.yml` temporal con `domain.product` reemplazado por el `product.yml`, así
  obtenés el bp EFECTIVO de cada producto) + `build_files(bp)` para base/assets/snipeit, y diffea las claves HEAD vs
  working (HEAD por `git show HEAD:…codegen/scaffold_product.py` a un temp + importlib). Para una mejora GENERAL los 3
  cambian IGUAL (sin nombres de dominio); confirmá **cero líneas Kotlin >160**, **cero imports sin usar**, y que cada
  `Repository.X` que el AppServer llama existe en Repository. (La sesión de SERVE-ALL dejó `scratchpad/eyeball.py`.)
- **PROOF MANUAL para el diente RÁPIDO** (≈3min recompilar vs ≈9 del product-run): la dist viva de la última corrida
  verde está en `products/snipeit/build/product/build/install/snipeit`. Saboteá el SOURCE generado en
  `products/snipeit/build/product/src/main/kotlin/…` (es gitignored → no contamina; el `increment_guard` BLOQUEA el tool
  Edit en esa ruta de producto → usá Bash/python para escribirlo), recompilá con
  `JH=$(dirname $(dirname $(readlink -f $(command -v javac)))); JAVA_HOME=$JH ./gradlew installDist -q --console=plain`
  (en `build/product`, `dangerouslyDisableSandbox`), levantá PG en docker
  (`postgres@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb`, `-p 5439:5432`, pass
  `metafactory`), corré `java -cp 'build/install/snipeit/lib/*' snipeit.endpoints.AppServerKt` con env
  `FSK_AC_PORT`/`FSK_PG_URL=jdbc:postgresql://localhost:5439/postgres`/`FSK_PG_PASSWORD=metafactory`/`FSK_WEB_DIR=
  frontend/dist` **(+ `FSK_NOW=<fecha>` para ESTE eje)**, esperá con `curl --retry 50 --retry-connrefused -sf
  .../health` (NO `sleep` en foreground, el harness lo bloquea), y corré el proof `python3 tools/access_control_check.py
  http://127.0.0.1:<port>`. **El infra_up NO surfacea el stdout del proof** → un fallo se ve como "no alcanzó la infra
  viva" con stdout vacío; el proof manual lo DESTAPA. Teardown: `kill` el server + `docker rm -f`. (La sesión SERVE-ALL
  lo usó para el diente — verde con ojos propios.)
- **`ci --rederive` opera sobre el ÁRBOL DE TRABAJO** (borra `.proof/`+`build/`, re-deriva in-place; NO clona git). UNO A
  UNO foreground, o `--all-products` hace base+assets+snipeit de una. **Delegá las corridas pesadas a un subagente Sonnet**
  (lo hizo la sesión SERVE-ALL: ~40min de gradle) — pero escribí el codegen + el diente con TUS ojos.
- **proof_protect DENIEGA tocar `.proof/` por shell** — el Read tool SÍ lee `.proof/logs/` (son RESÚMENES).
- **ChronoUnit.MONTHS.between(LocalDate, LocalDate)** = meses COMPLETOS; replicá en Python:
  `(y2-y1)*12 + (mo2-mo1) - (1 if d2 < d1 else 0)`. Cuidado con el ORDEN (purchase → now, no al revés) y con un `date`
  futuro (meses negativos → decidí: `max(0, …)` o dejá que la fórmula lo absorba; el oráculo debe REFLEJAR la decisión).

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento, profundidad)
**AppServer-en-contenedor con PG** (s11 hoy despliega el ObsServer PG-free) · **e2e del FORM en browser** (hoy
FSK-FRONTEND-BROWSER prueba el RENDER en Chromium; el submit del FORM en browser real sigue sólo en jsdom) · **EAV
dinámico a runtime** (custom-fields Avenue B) · **PUT de campos opcionales arbitrarios** · **Actionlog** (auditoría
polimórfica) · **Kits** (bundles) · **push de la imagen a un registry**.

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py`, `factory.spec.yml`, `stations/`) es nivel FÁBRICA → **este incremento** lo cubre
  (header ABIERTO). Las estaciones VIVEN en `factory.spec.yml`, NO en `stations/*.yml` (esos son output materializado por
  producto). ⚠️ Si tocás `factory.spec.yml` `station_sequence` re-materializás los PRODUCTOS pero NO el base committeado
  `stations/<id>.yml` → sincronizá a mano. (ESTE eje probablemente NO toque estaciones — sólo codegen.)
- **La adopción** (si tocás `products/snipeit/product.yml` — p.ej. el AST de `current_value`) es nivel PRODUCTO → abrí
  TAMBIÉN `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) con el incremento ABIERTO, luego `docs(fsk): cerrar
  FSK-TIME-COMPUTED (§Evidencia) + abrir <siguiente>` flipeando el header a CERRADO.
- **Probá POR BLOQUEO**: EYEBALL · `product-run --product snipeit` PASS · diente de dos lados vivo (degradá la aritmética
  → SÓLO s9 rojo) · `ci --rederive --all-products` == pin · `meta check` 6/6 (`generality` verde) · `git diff
  src/metafactory + seed = 0`.

## 6. Criterio de cierre (demostrable, no narrable)
1. Un campo computado puede depender de los MESES TRANSCURRIDOS entre un campo `date` y `now` (mockeable por `FSK_NOW`);
   `Asset.current_value` (snipeit) lo USA. `product-run --product snipeit` **PASS**.
2. **Diente de DOS lados verificado VIVO**: con `FSK_NOW` fijo + `purchase_date` sembrado, GET `current_value` == la
   fórmula re-derivada; degradá la aritmética → SÓLO `access_control_live` rojo, hermanos verdes → revertí → verde.
   (Bonus: dos `FSK_NOW` distintos → distinto `current_value`, prueba que `now` entra.)
3. EYEBALL · `ci --rederive --all-products` == pin (re-pin SÓLO si agregaste check/estación — improbable, §1) · `meta
   check` 6/6 · `git diff src/metafactory + seed = 0`.
4. STATE/LOG (fábrica) + SNIPEIT-DOMAIN (sacá "time-elapsed" de los diferidos) actualizados. Abrí el SIGUIENTE con su
   handoff (§7).

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE (con AUTORIDAD para reabrir)
**El núcleo + superficie están terminados; de acá es profundidad-de-detalle.** Si time-elapsed no te convence ahora, o
querés mayor VALOR:
- **AppServer-en-contenedor con PG (s11) — la de MAYOR valor**: hoy `deploy_smoke` (s11) despliega el ObsServer PG-free;
  desplegar el AppServer REAL necesita la PG en el contenedor (docker-compose-lite o una red docker bajo infra_up). Cierra
  "deploy de la app de VERDAD, no del server de obs". Más involucrada (red docker), pero es el último gran hito de "la app
  deploya de verdad".
- **e2e del FORM en browser**: extender FSK-FRONTEND-BROWSER (que hoy prueba el RENDER de la lista en Chromium) al SUBMIT
  del FORM en el browser real (hoy el submit sólo se prueba en jsdom). Cierra "el usuario crea una fila desde el navegador".
- **EAV dinámico (Avenue B)** · **PUT de opcionales arbitrarios** · **Actionlog (auditoría polimórfica)** · **Kits
  (bundles)** · **push de la imagen a un registry**.

### ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El backend faithful (modelo·acceso·comportamiento·valores-derivados) está COMPLETO, la app CORRE, TODAS las entidades
se sirven a runtime, el frontend se VE en un navegador REAL y deploya (smoke).** Lo que RESTA es profundidad-de-detalle
(time-elapsed —ESTE—, deploy del AppServer-en-contenedor, FORM-en-browser, Kits, Actionlog, EAV, PUT-opcionales). No queda
ningún hueco de SUPERFICIE ni de NÚCLEO: son refinamientos.
