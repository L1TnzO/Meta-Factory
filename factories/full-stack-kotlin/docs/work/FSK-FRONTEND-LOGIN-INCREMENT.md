<!-- meta:doc sha=2bc36d487fa1b1a27669c6c42596bac35d2f51d0 updated=2026-07-07T21:28Z -->
# Incremento FSK-FRONTEND-LOGIN — session-picker dev (corte A), CERO backend

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO** (2026-07-07T21:28Z)
> (creado 2026-07-07T20:24Z). Cerralo con `meta increment close` (gateado: árbol limpio + estación activa
> verde). Todo cambio de código vive acá (ADR-010).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO.** INC-5/5 (ÚLTIMO) del arco
> `docs/work/FSK-FRONTEND-SCREENS-DIRECTION-INCREMENT.md` (leé §2 doctrina ahí — NO el doc entero). Corte
> **A** (session-picker dev, decidido por el plan §4 fila 5 — "recomendado contra-el-tiempo"): corte B
> (credenciales reales) queda diferido explícito como INC-6 (trust-chain/Opus, eje de seguridad backend).
> Diseñado por esta sesión (Opus/orquestador) leyendo `codegen/scaffold/{browser,frontend,base,auth,
> constants}.py` con ojos propios (sin digest — 2 archivos acotados). Contrato EXACTO, alta confianza.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA
1. Reproducí el verde (el piso): `PYTHONPATH=src python3 -m metafactory.cli product-run --factory
   full-stack-kotlin --product snipeit` (FOREGROUND, `dangerouslyDisableSandbox`, timeout ≥600000, cwd RAÍZ).
   PASS esperado, RTM 25/26, 23/23 asserts en `browser_check.ts`.
2. **UN SOLO SLOT** (frontend-only, CERO backend) — delegable al `generator`: aplicá §1 completo (5 archivos:
   `browser.py`/`base.py`/`frontend.py`/`constants.py`, los 4 de `codegen/scaffold/`). Blast radius: esos 4
   archivos SOLAMENTE. Gate iteration (rápido, sin gradle/postgres): `tsc --noEmit` + `eslint` + `esbuild`
   sobre un scratch-emit (mismo patrón que los 4 incrementos previos del arco). Gate acceptance (YO/
   orquestador): `product-run --mode draft` primero, luego harden.
3. Verificá por bloqueo (§2): EYEBALL → `product-run` PASS (harden) → diente de DOS partes AISLADO (§2.1, con
   mis ojos) → los 23 dientes PREVIOS siguen verdes (§2.2) → `ci --rederive --all-products` == pin (byte-
   neutro esperado: `roles` ya está declarado en LOS 3 productos hoy → el picker SÍ emite en los 3, pero la
   FORMA/estructura del bundle no cambia el contrato openapi/rutas — confirmá bytes con tus ojos, no asumas)
   → `meta check` verde → cerrar el arco de 5.

## 0. POR QUÉ
`SCREENS-DIRECTION §4` fila 5 (ÚLTIMA del arco): hoy el token de escritura es HORNEADO por pantalla
(`browser_entry.ts`: cada entidad servida tiene UN rol fijo, `role_of(e)` = su 1er `write_role` no-bypass,
decidido en CODEGEN — nunca elegible en runtime). No hay forma de, en el browser real, actuar como OTRO
actor/rol para ver RBAC en acción (un manager vs un auditor, p.ej.). Este incremento agrega un
**session-picker DEV**: un `<select data-role-picker>` con TODOS los roles declarados del blueprint
(`bp["roles"]`, DATA ya conocida en codegen) que, al elegir uno, **reemplaza el rol de la pantalla activa
para TODA la sesión** (arma `Bearer <rol-elegido>:<owner de /seed>`) — la opción `"(default)"` restaura el
comportamiento ACTUAL (rol fijo por pantalla). Es honesto para demo (podés probar RBAC real desde el
browser), **NO es autenticación** (sin credenciales, sin backend, cero sesión persistida) — eso es el corte
B, diferido.

### 0.1 Decisiones de diseño (léelas antes de tocar código — evitan 3 gotchas reales)

**(a) El picker es GLOBAL-por-sesión, NO por-pantalla — y el override es OPCIONAL (`null` por defecto)**. Si
hiciera el rol "fijo tras elegir una vez" con un default distinto de `null` (p.ej. arrancar en el rol de la
1ª pantalla), **rompería el nav multi-entidad**: cada pantalla hoy usa SU PROPIO `role_of(e)` (entidades
distintas pueden tener `write_roles` distintos) — el bloque `%SECOND_BLOCK%` navega a una 2ª entidad y
postea con SU rol. Por eso: `overrideRole: string | null = null` (sin tocar el picker, CERO cambio de
comportamiento — cada `show(s)` sigue usando `s.role`); SOLO cuando el dev elige un rol explícito en el
picker, ESE rol pisa `s.role` en la pantalla ACTIVA hasta que el dev lo cambie de nuevo (o vuelva a
`"(default)"`). **Por esto NINGÚN test previo (dashboard/detalle/edit/operations/delete/trash/2da-entidad)
se toca**: nunca interactúan con el picker → `overrideRole` queda `null` siempre → comportamiento
BYTE-IDÉNTICO al actual.

**(b) El token está CERRADO (closure) al momento de `mount<E>(doc, base, token)` — cambiar el rol exige
RE-MONTAR la pantalla**, no alcanza con mutar una variable: `show(s)` YA hace
`screen.replaceChildren(); await s.mount(document, base, token);` — el picker's `change` listener llama
`void show(activeScreen)` (la pantalla activa guardada en `activeScreen: Screen | undefined`), que
RE-MONTA (nuevo fetch de `list<E>`, form limpio) con el token nuevo. El diente por eso debe: elegir el rol →
esperar a que el remount cargue (`tr[data-id]`) → RECIÉN AHÍ llenar+submitear el form (el form viejo fue
reemplazado).

**(c) `feedback` (el `<p>` del CREATE) no tenía atributo — necesita uno para que el proof lo distinga de
`editFeedback`/`verbFeedback`/`deleteFeedback`/etc.** Se agrega `data-feedback="create"` (UNA línea en
`frontend.py`, mismo precedente que `data-trash-id` vs `data-id`: un hook de testabilidad chico, universal,
sin nombrar dominio). Esto permite un diente NEGATIVO determinista (esperar `textContent === "error"`, no un
`waitForTimeout` a ciegas) — comprobado un rol SIN permiso: `create<E>` tira (RBAC 403), el `catch` del
handler YA existente pone `feedback.textContent = "error"` (sin cambios ahí, sólo el atributo nuevo).

**(d) El rol "equivocado" (para el lado negativo del diente) sale de `_wrong_role_set(bp["roles"],
owned["write_roles"])`** (YA EXISTE en `auth.py:715`, usado hoy para el fixture negativo de RBAC de Kotlin
— reutilizado, no reinventado). Opt-in doble: sin `bp.get("roles")` (RBAC apagado) → el picker entero no se
emite (byte-vacío, BYTE-IDÉNTICO al `browser_entry.ts` actual); con roles pero SIN un rol "equivocado"
disponible (`_wrong_role_set` vacío — todos los roles pueden escribir) → el picker SE EMITE (sirve para
explorar) pero el diente NEGATIVO de `browser_check.ts` no se emite (no hay verdad que probar). Los 3
productos HOY (`snipeit`/`assets`/`helpdesk`) declaran `roles` con roles NO-write (auditor/manager-sin-
bypass/etc.) → el diente completo SÍ corre en los 3.

## 1. DISEÑO (1 slot, 4 archivos — frontend-only, CERO backend)

### 1.1 `codegen/scaffold/base.py` — nueva función, cerca de `_proof_form_value` (línea ~481, antes de
`_mutable_when`)
```python
def _proof_login_value(f: dict):
    """Valor que el diente FSK-FRONTEND-LOGIN postea al probar el CREATE bajo el picker de roles — type-correct
    y DISTINTO de `_proof_post_value`/`_proof_form_value` (evita choque UNIQUE con las filas que esos 2 ya
    crearon en la MISMA corrida de browser_check.ts). `unique` sólo aplica a `string` en este dominio (verificado:
    los 3 blueprints reales sólo marcan `unique: true` en campos string) → los demás tipos reusan el MISMO literal
    de `_proof_form_value` sin riesgo de colisión."""
    t = f["type"]
    if t == "string":
        if f.get("format"):
            return _format_sample(f["format"], alt=True)
        return f"login-{f['name']}" + ("-uniq" if f.get("unique") else "")
    return _proof_form_value(f)
```
(`_format_sample` ya está importado/definido en `base.py` — mismo helper que usa `_proof_form_value`.)

### 1.2 `codegen/scaffold/frontend.py` — `_mount_ts`, UNA línea (cerca de línea 770, junto a la declaración de
`feedback`)
```python
  const feedback = doc.createElement("p");
```
→
```python
  const feedback = doc.createElement("p");
  feedback.setAttribute("data-feedback", "create");
```
(Byte-cost fijo por entidad servida — mismo precedente que `data-trash-id`/`data-restore`: un hook de
testabilidad, no una feature de dominio.)

### 1.3 `codegen/scaffold/browser.py` — `_browser_entry_ts(bp)` (líneas 102–172), la función completa
**Objetivo**: opt-in TOTAL sobre `bp.get("roles")` — con roles vacío, el output debe ser BYTE-IDÉNTICO al de
HOY (confirmalo armando el diff mental antes de escribir: ninguna línea nueva si `roles` es falsy).

Reemplazá el cuerpo de la función así (mantené `served`/`bypass`/`role_of`/`names`/`imports`/
`dashboard_screen`/`screens` SIN CAMBIOS — sólo se toca desde `roles = bp.get("roles") or []` en adelante y
el bloque `return (...)` final):

```python
    roles = bp.get("roles") or []
    # FSK-FRONTEND-LOGIN (corte A, session-picker dev): un <select data-role-picker> con TODOS los roles del
    # blueprint + "(default)". Elegir un rol PISA el rol de la pantalla ACTIVA (overrideRole) hasta que el dev
    # vuelva a "(default)" (null -> cae a `s.role`, el comportamiento actual, sin tocar el picker). Opt-in TOTAL:
    # sin `roles` (RBAC apagado) -> CERO líneas nuevas, byte-idéntico al browser_entry.ts previo.
    role_picker_decl = (
        '  const rolePicker = document.createElement("select");\n'
        '  rolePicker.setAttribute("data-role-picker", "");\n'
        '  const defaultOpt = document.createElement("option");\n'
        '  defaultOpt.value = "";\n'
        '  defaultOpt.textContent = "(default)";\n'
        '  rolePicker.appendChild(defaultOpt);\n'
        f'  const ROLES: readonly string[] = {json.dumps(roles)};\n'
        '  for (const r of ROLES) {\n'
        '    const opt = document.createElement("option");\n'
        '    opt.value = r;\n'
        '    opt.textContent = r;\n'
        '    rolePicker.appendChild(opt);\n'
        '  }\n'
        '  let overrideRole: string | null = null;\n'
        '  let activeScreen: Screen | undefined = undefined;\n'
    ) if roles else ''
    show_body = (
        '    activeScreen = s;\n'
        '    screen.replaceChildren();\n'
        '    const role = overrideRole ?? s.role;\n'
        '    const token = `Bearer ${role}:${seed.owner}`;\n'
        '    await s.mount(document, base, token);\n'
    ) if roles else (
        '    screen.replaceChildren();\n'
        '    const token = `Bearer ${s.role}:${seed.owner}`;\n'
        '    await s.mount(document, base, token);\n'
    )
    role_picker_listener = (
        '  rolePicker.addEventListener("change", () => {\n'
        '    overrideRole = rolePicker.value === "" ? null : rolePicker.value;\n'
        '    if (activeScreen !== undefined) {\n'
        '      void show(activeScreen);\n'
        '    }\n'
        '  });\n'
    ) if roles else ''
    role_picker_append = '  app.appendChild(rolePicker);\n' if roles else ''
    return (
        "// FSK-FRONTEND-ALL-ENTITIES — el ENTRY del bundle del browser: importa mount<E> (app.ts) de CADA entidad\n"
        "// servida y arma un NAV (un boton por entidad) + un #screen; al elegir una entidad MONTA su pantalla\n"
        "// contra el AppServer MISMO-ORIGEN (location.origin) -> trae la lista VIVA y la renderiza en el DOM REAL.\n"
        "// esbuild (build_bundle.mjs) lo bundlea a un IIFE (dist/app.js); el AppServer lo sirve en GET /app.js.\n"
        "// FSK-FRONTEND-LOGIN (corte A): un <select data-role-picker> deja actuar como CUALQUIER rol declarado\n"
        "// para la sesion completa (session-picker DEV, no auth real -- ver work-doc).\n"
        f'import {{ {imports} }} from "./app.ts";\n\n'
        "interface Screen {\n"
        "  label: string;\n"
        "  role: string;\n"
        "  mount: (doc: Document, base: string, token: string) => Promise<void>;\n"
        "}\n\n"
        "const SCREENS: readonly Screen[] = [\n"
        f"{screens}"
        "];\n\n"
        "async function boot(): Promise<void> {\n"
        "  const base = location.origin;\n"
        "  const seedRes = await fetch(`${base}/seed`);\n"
        "  const seed = (await seedRes.json()) as { owner: number };\n"
        '  const app = document.getElementById("app") ?? document.body;\n'
        '  const nav = document.createElement("nav");\n'
        '  const screen = document.createElement("div");\n'
        '  screen.id = "screen";\n'
        f"{role_picker_decl}"
        "  const show = async (s: Screen): Promise<void> => {\n"
        f"{show_body}"
        "  };\n"
        f"{role_picker_listener}"
        "  for (const s of SCREENS) {\n"
        '    const btn = document.createElement("button");\n'
        "    btn.textContent = s.label;\n"
        '    btn.setAttribute("data-entity", s.label);\n'
        '    btn.addEventListener("click", () => {\n'
        "      void show(s);\n"
        "    });\n"
        "    nav.appendChild(btn);\n"
        "  }\n"
        f"{role_picker_append}"
        "  app.appendChild(nav);\n"
        "  app.appendChild(screen);\n"
        "  const first = SCREENS[0];\n"
        "  if (first !== undefined) {\n"
        "    await show(first);\n"
        "  }\n"
        "}\n\n"
        "void boot();\n")
```
⚠️ `json` ya está importado al tope de `browser.py` (lo usa `_consume_check_ts`/`_browser_check_ts` hoy) —
NO agregues un import nuevo.

### 1.4 `codegen/scaffold/browser.py` — imports (línea 9), agregá 2 símbolos
Línea actual:
```python
from .base import _audited, _editable, _input_fields, _is_poly, _live_entities, _mutable_when, _operable, _patchable_fields, _proof_form_value, _proof_post_value, _proof_wrong_value, _render_field, _soft_delete, _table, _table_fields, _workflow_ops
```
→ agregá `_proof_login_value` (orden alfabético, junto a `_proof_form_value`):
```python
from .base import _audited, _editable, _input_fields, _is_poly, _live_entities, _mutable_when, _operable, _patchable_fields, _proof_form_value, _proof_login_value, _proof_post_value, _proof_wrong_value, _render_field, _soft_delete, _table, _table_fields, _workflow_ops
```
Agregá una línea NUEVA (después de la línea de `.constants`, antes de cualquier otro código):
```python
from .auth import _wrong_role_set
```
(`auth.py` sólo importa de `.base` → sin ciclo; confirmalo con un `import` real del módulo tras escribir, no
asumas.)

Y en la línea de `.constants` (línea 10), agregá `_LOGIN_ASSERT_BLOCK` (orden alfabético, junto a
`_HISTORY_ASSERT_BLOCK`):
```python
from .constants import _BROWSER_CHECK_SKELETON, _CONSUME_CHECK_SKELETON, _DASHBOARD_ASSERT_BLOCK, _DELETE_ASSERT_BLOCK, _DETAIL_ASSERT_BLOCK, _EDIT_ASSERT_BLOCK, _HISTORY_ASSERT_BLOCK, _LOGIN_ASSERT_BLOCK, _MW_UNFREEZE_BLOCK, _OPERATIONS_ASSERT_BLOCK, _SEARCH_ASSERT_BLOCK, _SEARCH_PAGE_SIZE, _SECOND_SCREEN_BLOCK, _STYLES_ASSERT_BLOCK, _TABLE_ASSERT_BLOCK, _TRASH_ASSERT_BLOCK
```

### 1.5 `codegen/scaffold/browser.py` — `_browser_check_ts(bp)`, agregar el bloque LOGIN al final
Los locales `owned`, `scalars`, `owned_ref_fields`, `flds` YA están calculados arriba en esta misma función
(§ líneas 235–249 del archivo actual — leélas, son las que usa el `owned_ref_merge` de la sección FORM_BODY).
**Reusalos tal cual, no los recalcules.** Justo ANTES del `return (_BROWSER_CHECK_SKELETON...)` final de la
función (después de que `trash_block`/`delete_block`/etc. ya estén armados — el orden de construcción de
variables locales no importa mientras estén antes del `return`), agregá:

```python
    # FSK-FRONTEND-LOGIN (corte A): el diente del session-picker -- opt-in DOBLE (roles declarados Y un rol
    # "equivocado" real disponible para el lado negativo). Reusa `owned`/`scalars`/`owned_ref_fields` YA
    # calculados arriba (la misma fuente que FORM_BODY) -- NO los recalcules.
    roles_list = bp.get("roles") or []
    wrong_roles = _wrong_role_set(roles_list, owned["write_roles"]) if roles_list else []
    login_block = ""
    if roles_list and wrong_roles:
        login_form_body = {f["name"]: _proof_login_value(f) for f in scalars}
        owned_ref_merge_login = (
            "\n    for (const [k, v] of Object.entries(seed.ownedRefs ?? {})) {\n"
            "      LOGIN_BODY[k] = v;\n    }"
        ) if owned_ref_fields else ""
        login_block = (_LOGIN_ASSERT_BLOCK
                       .replace("%ROLE_OPTIONS_JSON%", json.dumps([""] + roles_list))
                       .replace("%WRONG_ROLE%", wrong_roles[0])
                       .replace("%LOGIN_FORM_BODY%", json.dumps(login_form_body))
                       .replace("%OWNED_REF_MERGE_LOGIN%", owned_ref_merge_login))
```

Y en el chain de `.replace(...)` del `return` final de `_browser_check_ts` (donde hoy termina en
`.replace("%TRASH_ASSERT%", trash_block)`), agregá INMEDIATAMENTE DESPUÉS (mismo criterio que TRASH agregó
después de DELETE — al FINAL de la cadena, nunca antes de una rama existente):
```python
            .replace("%TRASH_ASSERT%", trash_block)
            .replace("%LOGIN_ASSERT%", login_block)
```

### 1.6 `codegen/scaffold/constants.py` — 2 cambios

**(a)** En `_BROWSER_CHECK_SKELETON`, la línea que hoy termina en
`...%DELETE_ASSERT%%TRASH_ASSERT%\n  } finally {` (línea ~1373) → agregá `%LOGIN_ASSERT%` al final:
```
    check(navButtons, %NAV_COUNT%, "el nav lista una pantalla por entidad servida (N botones)");%SECOND_BLOCK%%DETAIL_ASSERT%%EDIT_ASSERT%%HISTORY_ASSERT%%OPERATIONS_ASSERT%%DELETE_ASSERT%%TRASH_ASSERT%%LOGIN_ASSERT%
```

**(b)** Agregá `_LOGIN_ASSERT_BLOCK` (nueva constante, cerca de `_TRASH_ASSERT_BLOCK`, después de su cierre):
```python
_LOGIN_ASSERT_BLOCK = '''

    // FSK-FRONTEND-LOGIN (corte A, session-picker dev): un <select data-role-picker> deja elegir CUALQUIER rol
    // declarado del blueprint y reemplaza el rol default de la pantalla ACTIVA para TODA la sesion (Bearer
    // <rol-elegido>:<owner de /seed>); real-login (corte B, credenciales) queda diferido. Diente de DOS partes,
    // AISLADO y AUTOCONTENIDO (crea su propia fila, no depende del estado de bloques previos): actuar con un rol
    // SIN permiso de escritura -> el submit del CREATE es rechazado (RBAC real); volver al rol correcto
    // ("(default)") -> el MISMO submit SI crea la fila. Sabotaje candidato: ignorar la seleccion del picker (el
    // rol rechazado terminaria creando la fila igual) -> SOLO estos asserts rojean, el resto sigue verde.
    await page.waitForSelector("select[data-role-picker]", { timeout: 10000 });
    const rolePickerValues = await page.$$eval("select[data-role-picker] option", (els) => els.map((o) => o.value));
    check(rolePickerValues, %ROLE_OPTIONS_JSON%,
          "FSK-FRONTEND-LOGIN: el picker lista un option por rol declarado (+ \\"(default)\\")");

    const LOGIN_BODY = %LOGIN_FORM_BODY%;%OWNED_REF_MERGE_LOGIN%
    const fillLoginForm = async () => {
      for (const [k, v] of Object.entries(LOGIN_BODY)) {
        const sel = `[name="${k}"]`;
        if (typeof v === "boolean") {
          if (v) { await page.check(sel); } else { await page.uncheck(sel); }
        } else {
          await page.fill(sel, String(v));
        }
      }
    };

    // 1) actuar con un rol SIN permiso de escritura -> re-monta la pantalla (Bearer nuevo) -> el submit se rechaza.
    await page.selectOption("select[data-role-picker]", "%WRONG_ROLE%");
    await page.waitForSelector("tr[data-id]", { timeout: 10000 });
    const beforeWrong = await page.$$eval("tr[data-id]", (els) => els.length);
    await fillLoginForm();
    await page.evaluate(() => {
      document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    });
    try {
      await page.waitForFunction(
        () => document.querySelector('p[data-feedback="create"]')?.textContent === "error",
        { timeout: 10000 });
    } catch {
      // timeout: el submit con el rol SIN permiso no marco error -> el check de abajo flipea (rojo). DIENTE.
    }
    const feedbackWrong = await page.$eval('p[data-feedback="create"]', (el) => el.textContent ?? "");
    check(feedbackWrong, "error",
          "FSK-FRONTEND-LOGIN: actuar con un rol SIN permiso de escritura -> el submit es RECHAZADO (RBAC real, Chromium)");
    const afterWrong = await page.$$eval("tr[data-id]", (els) => els.length);
    check(afterWrong, beforeWrong, "FSK-FRONTEND-LOGIN: el intento rechazado NO crea la fila");

    // 2) volver al rol correcto ("(default)" restaura el rol propio de la pantalla activa) -> el MISMO submit crea la fila.
    await page.selectOption("select[data-role-picker]", "");
    await page.waitForSelector("tr[data-id]", { timeout: 10000 });
    await fillLoginForm();
    await page.evaluate(() => {
      document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    });
    try {
      await page.waitForFunction((n) => document.querySelectorAll("tr[data-id]").length > n, afterWrong, { timeout: 10000 });
    } catch {
      // timeout: el MISMO submit con el rol correcto tambien fallo -> el check de abajo flipea (rojo). DIENTE.
    }
    const afterRight = await page.$$eval("tr[data-id]", (els) => els.length);
    check(afterRight, afterWrong + 1,
          "FSK-FRONTEND-LOGIN: volver al rol correcto -> el MISMO submit SI crea la fila (Chromium REAL)");'''
```
⚠️ Dentro de un template Python `'''...'''`, el literal TS `p[data-feedback="create"]` usa comillas SIMPLES
en JS (`'p[data-feedback="create"]'`) — no hace falta escapar nada extra salvo el `\"` dentro del label de
`check(...)` (ya escrito arriba con `\\"`). Verificá que el string Python compile (ejecutá el módulo) antes
de dar por bueno el slot.

## 2. Verificación

### 2.1 El diente de DOS partes (VIVO en Chromium real, s9) — con MIS ojos
- **Verde**: `browser_check.ts` → 25/25 (los 23 previos + 2 nuevos de `_LOGIN_ASSERT_BLOCK`; más el nuevo
  check de opciones del picker si lo contás aparte — documentá el conteo REAL que veas).
- **Sabotaje candidato A** (`const role = s.role;` — ignora `overrideRole`): el intento con el rol SIN
  permiso en realidad usa el rol correcto por default → el create SIGUE funcionando → `feedbackWrong` sería
  `"ok"` no `"error"` → SOLO el 1er check de LOGIN rojea (y el 2º, "NO crea la fila", también, ya que sí se
  creó) — el resto (detalle/edit/operations/delete/trash/tabla/búsqueda/dashboard/estilos) sigue verde.
- **Sabotaje candidato B** (el listener del picker no llama `show()`): mismo síntoma que A (el rol activo
  nunca cambia) — mismo aislamiento.
- Revertí → 25/25 verde de nuevo.

### 2.2 Los 23 dientes PREVIOS siguen VERDES
Ningún bloque previo interactúa con el picker (`overrideRole` queda `null` toda su ejecución) → deben
comportarse EXACTAMENTE igual. `assets`/`helpdesk`: confirmá que declaran `roles` (SÍ, ambos lo hacen hoy) →
el picker se emite en los 3 productos — no hay caso "byte-vacío" real hoy, pero el código SÍ soporta
`roles` ausente sin romper (confirmalo leyendo el `if roles else` — no hace falta un producto sin roles para
probarlo, es una propiedad del código, no del fixture).

### 2.3 EYEBALL pre-gate (sin gradle, ~20s)
Igual mecánica que los 4 incrementos previos: scratch-emit + `tsc --noEmit` + `eslint src` + `node
build_bundle.mjs`.

### 2.4 Acceptance gate (con gradle, YO/orquestador — no delegado)
`product-run --factory full-stack-kotlin --product snipeit` (FOREGROUND, `dangerouslyDisableSandbox`, cwd
RAÍZ, timeout ≥600000) → PASS. **Medí el bundle** (`src/app.ts` NO cambia — el picker vive SOLO en
`browser_entry.ts`, que NO se mide por `perf_budget_gate` — confirmá con tus ojos que el budget NO se movió;
si se movió, algo tocó `app.ts` por error). `ci --rederive --all-products` + `meta check`, con MIS ojos.
`git diff src/metafactory + seed = 0`. ⚠️ NO hay producto `default`.

## 3. Disciplina (ADR-016/010)
Codegen = nivel FÁBRICA → ESTE incremento. NO toca `product.yml`. UN SOLO slot delegado (frontend-only, CERO
backend — a diferencia de TRASH que fueron 2). Commits sugeridos:
`feat(fsk): session-picker dev de roles en el frontend (FSK-FRONTEND-LOGIN corte A, INC-5/5 SCREENS)`, luego
`docs(fsk): cerrar FSK-FRONTEND-LOGIN + arco FSK-FRONTEND-SCREENS (§Evidencia)`. Gradle FOREGROUND, cwd
SIEMPRE raíz.

## 4. Criterio de cierre
1. `<select data-role-picker>` vivo, lista TODOS los roles del blueprint + `"(default)"`; elegir un rol
   distinto cambia el token real de la sesión (RBAC real observable desde el browser).
2. `product-run --product snipeit` PASS (harden).
3. Diente de DOS partes NUEVO, VIVO y AISLADO (§2.1).
4. Los 23 dientes PREVIOS siguen VERDES (§2.2).
5. EYEBALL (§2.3) · `product-run` PASS (§2.4) · `ci --rederive --all-products` == pin (o diff explicado) ·
   `meta check` verde · `git diff src/metafactory+seed` = 0. STATE/LOG de la fábrica actualizados.

## 5. Qué sigue después (arco FSK-FRONTEND-SCREENS — CIERRA ACÁ)
Corte B (`FSK-FRONTEND-LOGIN-REAL`, credenciales + store de principals + emisión de token) queda diferido
explícito como INC-6, eje de SEGURIDAD backend — trust-chain, contrato+revisión de Opus obligatoria, sesión
propia (NO S2 Sonnet sola). Ver `FSK-FRONTEND-SCREENS-DIRECTION-INCREMENT.md §4` fila 5 / §6. Con el cierre
de este INC, el arco de 5 incrementos (TABLE→SEARCH-PAGE→DETAIL-TABS→TRASH→LOGIN) queda COMPLETO.

## Evidencia (cierre 2026-07-07T21:30Z) ✅

**Qué se construyó**: un `<select data-role-picker>` GLOBAL-por-sesión en `browser_entry.ts` (opt-in total
sobre `bp.get("roles")`) que lista `"(default)"` + TODOS los roles declarados del blueprint; elegirlo pisa
el rol de la pantalla ACTIVA (`overrideRole ?? s.role`) hasta volver a `"(default)"` — RE-MONTA la pantalla
(nuevo `list<E>` + form limpio) porque el token está cerrado (closure) al `mount<E>`. `feedback` (el `<p>`
del CREATE) ganó `data-feedback="create"` para que el diente negativo sea determinista (poll de
`textContent === "error"`, sin `waitForTimeout`). Delegado en **UN SOLO slot** (frontend-only) al `generator`
bajo el arnés: 4 archivos (`base.py` +14/`frontend.py` +1/`browser.py` +76/`constants.py` +69).

**Corrección post-verdict (con mis ojos, no delegada de nuevo)**: el generator devolvió verdict **red**
sólo por presupuesto de bundle (esperado, ver abajo) — pero al re-derivar `ci --rederive --all-products` YO
encontré un bug REAL que el gate de snipeit-solo no ejercitaba: `_wrong_role_set` (auth.py, pensado para el
fixture ESTÁTICO de `route_check.py`) devuelve, cuando `write_roles == roles` (todos pueden escribir), un
SUBCONJUNTO (`write_roles[:-1]`) — NO un rol realmente prohibido. `helpdesk`'s Ticket (`owned_by`) tiene
`write_roles: [admin,supervisor,agent] == roles` exacto → el diente elegía `"admin"` como "rol equivocado",
que en runtime SÍ puede escribir → el submit "rechazado" en realidad SUCEDÍA → el `browser_check.ts` de
helpdesk quedaba en un loop de reintentos de `infra_up` (120s, sin health) en vez de fallar rápido. Fix:
reemplacé el helper reusado por un cómputo directo (`[r for r in roles_list if r not in
owned["write_roles"]]`) — si viene vacío (todos los roles declarados pueden escribir), el picker se emite
igual pero el diente NEGATIVO se omite (no hay verdad que probar; opt-in honesto, como documentaba §0.1(d)
desde el diseño). Quité el import ahora-no-usado `_wrong_role_set`. **Lección reusable**: un helper diseñado
para un fixture ESTÁTICO (mismatch de topología) no es automáticamente correcto para un diente de RUNTIME
(RBAC real) — su contrato de "distinto" ≠ "prohibido"; verificar con LOS 3 productos (no sólo el vehículo de
medición) encontró esto que snipeit solo no hubiera mostrado (snipeit/assets sí tienen un rol genuinamente
prohibido para su entidad dueña).

**Bump de presupuesto (con mis ojos, no delegado — como manda §2.4)**: `data-feedback="create"` vive en
`_mount_ts`, que SÍ es parte de `src/app.ts` (lo que mide `perf_budget_gate`) — la nota del slot manifest
("este slot no toca ese archivo") era INCORRECTA para esa línea puntual; el generator lo detectó y NO
bumpeó el budget él mismo (correcto, es mi trabajo). Costo real: +810 B totales en snipeit (18 entidades
servidas) = **+45 B/entidad EXACTOS** (una línea fija por cada `mount<E>` emitido) → a diferencia de TRASH/
DETAIL-TABS (costo FIJO por producto, sólo 1 entidad afectada), ACÁ el costo escala con `n_served` → el
bump correcto es `BUNDLE_BUDGET_PER_ENTITY_BYTES` (no BASE): 1920→1965. Medido: snipeit real 77 404 B,
budget previo 76 944 B (ratio 0.9941, FAIL) → budget nuevo 77 754 B (ratio 1.0045, mismo margen que TRASH).

**Diente de DOS partes (en realidad 3 asserts + 1 de estructura), VIVO en Chromium real (snipeit) —
verificado CON MIS OJOS** (no sólo el verdict del generator), corriendo `browser_check.ts` a mano contra un
server real (`tools/dev_run.sh`, PG fresca por sabotaje):
- **Verde** (cableado): **27/27 asserts OK** (los 23 previos del arco + 4 nuevos): el picker lista
  `["","superadmin","admin","manager","auditor"]`; actuar como `auditor` (rol SIN permiso de escritura para
  Asset, `write_roles=[superadmin,admin,manager]`) → el submit del CREATE es RECHAZADO (`feedback ==
  "error"`, el conteo de filas NO sube); volver a `"(default)"` → el MISMO submit SÍ crea la fila.
- **Sabotaje** (cambié `const role = overrideRole ?? s.role;` → `const role = s.role;` en la FUENTE
  `browser.py` y re-emití — no el artefacto generado): el picker sigue OK (renderiza igual), pero el intento
  con `auditor` en realidad usa el rol default (SIGUE escribiendo) → los 3 asserts del diente rojearon
  exactamente (`"error"` esperado, obtuvo `"ok"`; conteo esperado 4, obtuvo 5; conteo esperado 6, obtuvo 5)
  — los 23 dientes previos quedaron VERDES, aislado confirmado.
- Revert → re-emití → **27/27 verde de nuevo**, exit 0.

**Verificación (con mis ojos, no delegada):**
- **`product-run --factory full-stack-kotlin --product snipeit`** (harden) → **PASS** (tras el bump de
  budget); antes del bump, `perf_budget_gate` FAIL (ratio 0.994), reproducido independientemente.
- **`product-run --product helpdesk`** → FAIL determinístico (timeout 120s, `frontend_browser_live`) ANTES
  del fix de `wrong_roles`; **PASS** después.
- **`ci --rederive --factory full-stack-kotlin --all-products`** → **4/4 == pin** (fábrica 12/12, snipeit
  11/11, assets 11/11, helpdesk 11/11) — confirmado DESPUÉS del fix (antes del fix: 3/4, helpdesk 8/11 con
  s9/s10/s11 sin re-derivar por el hang).
- **`meta check`: 19/19** (compile/docs/projection/isolation/generality/quality/pbt/security/deferred/
  benchmark/dial/column_parity/least_priv/roles/kinds/plan/state_snapshot/state_fidelity/suite — todo
  verde).
- `git diff src/metafactory + seed = 0` (sustrato meta intacto). Cambios: `codegen/scaffold/{base,frontend,
  browser,constants}.py` (4 archivos) + `docs/STATE.md` (fábrica) + este work-doc + `docs/work/
  DELEGATE-FSK-FRONTEND-LOGIN-INCREMENT.md` (meta, evidencia del arnés).

**Gotcha operativo reconfirmado (stop_proof + product-run en background)**: el `generator` corre su propio
`product-run` (gate declarado en el manifest) que escribe al MISMO `.proof/active.json` compartido — mientras
corría en background, el `stop_proof` del turno del orquestador vio la estación `s11` en rojo (el intento del
generator con JDK aún no resuelto en ESA invocación puntual) y bloqueó el cierre de turno. Resuelto SIN
race: un watcher `until [ -f verdict ]; do sleep 5; done` en `run_in_background` (Bash), NUNCA una corrida
`product-run` propia mientras el generator podía seguir corriendo la suya (mismos puertos fijos/PG/docker).

**Arco `FSK-FRONTEND-SCREENS` COMPLETO** (5/5): TABLE→SEARCH-PAGE→DETAIL-TABS→TRASH→**LOGIN**. Corte B
(`FSK-FRONTEND-LOGIN-REAL`, credenciales + store de principals + emisión de token) queda diferido explícito
como INC-6, eje de SEGURIDAD backend (trust-chain, Opus obligatorio, sesión propia).
