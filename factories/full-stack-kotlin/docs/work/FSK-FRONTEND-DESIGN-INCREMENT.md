<!-- meta:doc sha=6a6f10b6cc788d82f81873ea5d4d3f802695100f updated=2026-07-08T01:36Z -->
# FSK-FRONTEND-DESIGN — diagnóstico + plan (arco de diseño visual)

> **Estado: DIFERIDO** (diagnóstico CERRADO con ojos reales 2026-07-08; los INCs del plan quedan
> por diseñar en una S1 corta). Reabrir a ABIERTO al arrancar el primer INC.

## §Por qué existe
El ingeniero vio la réplica de Snipe-IT generada y el frontend es **genuinamente horrendo**
("pareciera que no se ha hecho nada"). Este doc fija el POR QUÉ (diagnóstico con screenshots del
app vivo) y el CÓMO se arregla ahora y se previene a futuro. FSK es full-stack: BUENAS UIs son
parte del producto, no un nice-to-have.

## §Diagnóstico (visto en vivo: snipeit por `dev_run.sh`, Chromium real, 2026-07-08)

### Síntomas (lo que se VE)
1. **Formularios sin labels ni placeholders** — el form de alta de Asset renderiza ~6 `<input>`
   DESNUDOS: es imposible saber qué campo es cuál. (El `ui/index.html` estático de s0 SÍ tiene
   `<label>`; el render de la SPA en `frontend.py` NO los emite.) Esto solo ya lee como "roto".
2. **Tabla con TODOS los campos crudos** — Asset = 24 columnas → overflow horizontal más allá del
   body 1200px (columnas cortadas fuera de pantalla, sin scroll-container); headers `SNAKE_CASE`
   crudos; los nullables imprimen el string literal **"null"** en toda la grilla; números sin
   formato (`845.8333333333334`); FKs como ids numéricos crudos.
3. **Sin app-shell** — la SPA no tiene header/título (solo un `<select>` de rol "(default)"
   flotando); la nav son 19 ghost-buttons envueltos en 2 filas; dashboard = tarjetas de conteo
   planas; vacío vertical enorme debajo.
4. **FKs como `<input type=number>`** (`company_id: [    ]`) en vez de selects poblados de la
   entidad referida.
5. Widgets (tabs Details/History, Trash, paginación) flotan desanclados al fondo de la misma
   columna única.
6. Menor, de API: pluralización naive en rutas (`/companys`, `/categorys`, `/accessorys`).

### Causas raíz (por qué la máquina produjo esto)
1. **No hay capa de diseño**: el frontend es template determinista — `codegen/scaffold/frontend.py`
   emite strings de HTML semántico crudo; TODO el "design system" es UNA hoja de 153 líneas de
   selectores-de-elemento (`_APP_CSS` en `constants.py`). El re-skin Vercel fue TOKENS
   (color/radio/sombra) sobre un layout inexistente. **Tokens ≠ layout**: no hay shell, ni grid de
   formulario, ni curación de columnas, ni formateo de valores.
2. **El gate mide "el CSS aplica", no diseño**: el diente es `body max-width != none` + asserts de
   presencia DOM. Verificar-no-revisar colapsa al gate; la estética NO tiene gate → la fábrica
   optimiza al verde, y verde ≠ lindo. Es exactamente el residuo de calibración conocido (los gates
   no atrapan no-ops semánticos; "feo" ES un no-op semántico).
3. **Los increments de frontend fueron por CAPACIDAD, no por PANTALLA**: cada arco
   (list→detail→edit→operations→search→trash→tabs→login) agregó un widget con su assert y lo apiló
   en la misma columna. Nadie compuso nunca una pantalla.
4. **Desajuste de escala**: el estilo se validó en helpdesk (5 entidades, sweet-spot); snipeit
   (19 entidades, Asset de 24 campos) es el techo de regresión declarado — la nav envuelta y la
   tabla todas-las-columnas degeneran exactamente ahí.
5. **Sin ojos en el loop**: hasta hoy ninguna sesión MIRÓ el app renderizado; Playwright asserta
   bits de DOM/computed-style. Diseño sin ojos.

### Hipótesis del ingeniero, evaluadas
- «Solo tiene el design system de Vercel» → parcialmente cierto pero NO es la causa raíz: el
  problema no es CUÁL skin, es que no hay capa de layout/componentes que el skin vista. Más skins
  no arreglan inputs sin label ni tablas de 24 columnas.
- «Faltan skills de diseño (comunidad)» → los skills actúan en TIEMPO DE DISEÑO sobre el SUSTRATO
  (los templates del codegen), porque el frontend FSK es codegen determinista (solo s0+s6 generan
  archivos). Un skill no toca el app generado; guía los increments que mejoran
  `frontend.py`/`app.css`. Útil, pero segundo orden.
- «Faltaba el MCP de chrome-devtools» → cierra el gap de "sin ojos" para el LOOP DE DISEÑO
  (sesiones S1), no para los gates (que deben seguir Playwright/herméticos, 0-modelo). Ver §MCP.

## §Plan de arreglo (INCs de fábrica, en orden de dependencia — cada uno slot delegable con gate)
1. **FSK-FRONTEND-FORM-LABELS** (chico, ganancia enorme): label-sobre-input en la SPA, nombres
   humanizados (Title Case desde snake_case), placeholders, marca de required.
   Diente: todo `input/select` del form tiene `<label for>` asociado (two-sided, sabotaje→rojo).
2. **FSK-FRONTEND-SHELL**: app-shell = sidebar con la nav de entidades + topbar (título del
   producto + role-picker) + área de contenido. Diente: `aside nav` presente + layout grid computado.
3. **FSK-FRONTEND-TABLE-CURATION**: la lista muestra subconjunto CURADO de columnas (heurística:
   name/tag/fechas/enums primero, nunca `*_id` crudo), valores formateados (null→"—", bool→✓/—,
   números redondeados), contención horizontal (scroll-container).
   Dientes: columnas ≤ umbral · **ninguna celda == "null"** · sin overflow (`scrollWidth ≤ clientWidth`).
4. **FSK-FRONTEND-FK-SELECT**: refs → `<select>` poblado del list vivo de la entidad referida (el
   codegen YA conoce las refs desde el spec). Diente: cada ref del form es select con ≥1 option viva.
5. **FSK-FRONTEND-FORM-GRID**: form como grid responsive (2-3 col) con fieldsets agrupados
   (escalares/refs/flags). Diente: `grid-template-columns != none` computado.
6. *(opcional)* **theme-as-data**: `theme:` en product.yml elige entre N skins embarcados
   (ADR-012 tech=plan); un skin comunitario = un CSS que pasa los mismos gates.

Todo sigue DATA-agnóstico (ADR-012): derivado del spec (campos, refs, enums), cero conocimiento de
dominio en el sustrato.

## §Prevención (lo durable)
1. **Gate design-floor** (determinista, two-sided, en s9): sin inputs sin label · sin "null"
   literal renderizado · sin overflow horizontal a 1280px · shell presente · contraste computado
   ≥4.5 en tokens de texto. No mide belleza; PISO la clase de fealdad vista hoy.
2. **Screenshot en §Evidencia**: todo increment de frontend cierra con screenshot del app vivo —
   el residuo estético irreducible es ojo humano (VISION §5.2), hacerlo parte del cierre.
3. **Vehículo doble**: validar diseño en helpdesk (sweet-spot) Y snipeit (techo: 19 ent/24 campos)
   — la fealdad es fenómeno de escala.

## §MCP chrome-devtools (decisión de tooling)
- CLI-como-MCP está bien; un plugin no agrega nada esencial acá (bundle de lo mismo).
- **Quedó en scope GLOBAL (user)** → sus ~26 tool-defs entran al prefijo de CADA sesión de CADA
  proyecto = impuesto de contexto permanente contra ADR-021(e). Recomendación: sacarlo de global y
  habilitarlo por sesión de diseño frontend (`claude --mcp-config` o scope local al arrancar el
  arco). Los tools MCP registran al INICIO de sesión (una sesión ya abierta no los ve).
- Los GATES siguen siendo Playwright herméticos (0-modelo); el MCP es para el loop humano/S1.

## §Reproducción del diagnóstico
`eval "$(bash tools/toolchain.sh ensure)" && bash factories/full-stack-kotlin/tools/dev_run.sh snipeit`
→ seed por API (`Bearer superadmin:1`, rutas `/companys`·`/assetmodels`·`/assets`) → screenshot con
playwright-core del node_modules del producto (`--no-sandbox`). Evidencia de hoy: /tmp/fsk_home.png ·
/tmp/fsk_asset_list.png · /tmp/fsk_asset_full.png (re-derivable).

## §Ruteo de costo (ADR-021)
Diagnóstico = HECHO (esta sesión). Diseño de contratos+gates de INC-1..5 = S1 Opus CORTA.
Ejecución = S2 (`claude --model sonnet --agent orchestrator`), slots via `generate-slot`, aceptar
por VEREDICTO; vehículo de validación `helpdesk`, regresión final contra `snipeit`.
