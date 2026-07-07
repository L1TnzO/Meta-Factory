<!-- meta:doc sha=47bfc1f1f5ead470d30aca2fdade2df5f49a8aa1 updated=2026-07-07T03:54Z -->
# FSK-FRONTEND-SCREENS — dirección: el frontend COMPLETO (todas las pantallas) en idioma Apple

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Tipo: **DIRECCIÓN**
> (plan de N incrementos; NO es un incremento ejecutable en sí). Creado 2026-07-07T03:53Z (S1, Opus).
> **Regla de rebanada**: una sesión S2 que ejecuta el INC-n lee SOLO §2 (doctrina) + su fila §4.INC-n +
> el handoff de su work-doc propio. NO leas este doc entero en cada sesión.
>
> **Estado del plan**: INC-1..6 pendientes. Cada INC se abre con `meta increment open` + su propio
> `docs/work/FSK-<NOMBRE>-INCREMENT.md` (patrón del arco frontend previo) y se cierra por evidencia, no acá.

---

## §0 Objetivo y no-objetivo

**Objetivo**: snipeit **funcional y estéticamente completo** — la UI generada cubre los arquetipos de
pantalla reales de Snipe-IT (`products/snipeit/docs/reference/SNIPEIT-DOMAIN.md §1`: lista-tabla con
columnas/búsqueda, detalle con tabs e historial, papelera, login) en el design language **Apple**
(`docs/reference/DESIGN-APPLE.md`, capturado 2026-07-07 vía `npx getdesign@latest add apple`).

**No-objetivo / restricción dura (ADR-012)**: NINGÚN incremento nombra dominio en codegen. Todo es
maquinaria GENERAL de la fábrica (driven por el spec: schema → columnas; `audited:` → tab historial;
`soft_delete:` → papelera); snipeit solo ADOPTA. assets/helpdesk heredan gratis.

## §1 El piso verificado (2026-07-07, re-derivado — no narrado)

- RTM snipeit **25/26** (único UNSATISFIED = REQ-F-007, s6/LLM **SHUT deliberado** — no es pantalla).
- CRUD browser COMPLETO en Chromium real: dashboard → nav → lista → detalle → FORM create → edit
  (PATCH-like, 11 campos) → verbos (checkout/checkin/restore) → DELETE. 18 entidades servidas.
- Actionlog VIVO (`GET /action_logs`, sujeto polimórfico) · soft-delete+`restore` vivos en backend ·
  deploy Docker+PG · skin Vercel @1200px.
- **Brechas verificadas en codegen** (no en prosa): lista = `<ul><li>` (`scaffold/frontend.py`, sin
  tabla/columnas/búsqueda/paginación) · detalle sin tabs (historial es DATO vivo sin pantalla) · sin
  papelera (el verbo `restore` existe pero nada lista los borrados) · token HORNEADO del seed
  (`Bearer ${role}:${owner}`, `constants.py:1057` — sin login).

## §2 Doctrina de TODOS los incrementos (léela entera; es el contrato común)

1. **Frontend-only salvo la fila diga otra cosa**: extendé el `browser_check.ts` de s9
   (`frontend_browser_render`) — check EXISTENTE → **SIN re-pin**. Una estación/check NUEVO → re-pin de
   TODOS los productos (no lo hagas sin necesidad).
2. **Diente de dos lados AISLADO, siempre**: cableado → assert nuevo verde; sabotaje dirigido → SOLO el
   assert nuevo rojo (render/lista/detalle/edit/operations/dashboard/delete siguen verdes); revert → verde.
3. **DATA-agnóstico**: cero nombres de dominio/producto/tech en `codegen/scaffold/**`. La `generality`
   gate muerde.
4. **Multi-archivo**: CSS en `_APP_CSS`→`app.css` (archivo propio ya cableado); módulo nuevo si un archivo
   tiende a ~800+ líneas. El monolito viejo ya está partido en `codegen/scaffold/` — respetá el DAG.
5. **Budget del bundle**: mide `src/app.ts` (no `dist/`). Pantalla nueva = costo FIJO por producto →
   bump de `BUNDLE_BUDGET_BASE_BYTES`, NO per-entidad (precedente: FORM-EDIT 4096→7936).
6. **Loop interno en draft** (`product-run --mode draft`, 41.7s vs 98s), **harden SOLO al cierre**.
   EYEBALL-emit a scratch antes de gradle (~20s: `tsc --noEmit` + `eslint` + `esbuild` + browser_check).
   PG FRESCA por corrida manual del browser_check (colisión UNIQUE del FORM). Para VER: `tools/dev_run.sh`.
7. **Ruteo (ADR-021)**: cada INC = una sesión **S2 Sonnet** (`claude --model sonnet --agent orchestrator`);
   slots acotados vía `generate-slot`, aceptar por VEREDICTO. Rojo persistente/ambigüedad → archivo de
   escalación, nunca «pensar más fuerte». **EXCEPCIÓN**: INC-6-corte-B toca auth → trust-chain: contrato y
   revisión con ojos de Opus (S1/S3).
8. **Cierre por INC** (todo, no negociable): `product-run` snipeit PASS (harden) · diente §2.2 probado ·
   `ci --rederive --all-products` == pin · `meta check` verde · `git diff src/metafactory+seed` = 0 ·
   work-doc propio con §Evidencia + STATE de la fábrica actualizado · commit (ADR-010) ·
   `meta increment close`.
9. **Gradle FOREGROUND** con `dangerouslyDisableSandbox` y cwd SIEMPRE en la raíz del repo.

## §3 El design language (referencia única)

`docs/reference/DESIGN-APPLE.md` (562 líneas — NO la cargues entera en una sesión S2; el INC-1 la digiere
una vez a tokens CSS). Esencia: **Action Blue `#0066cc`** único color interactivo (`#0071e3` focus) ·
ink `#1d1d1f` sobre canvas `#ffffff`/parchment `#f5f5f7` · hairline `#e0e0e0` · SF Pro Display/Text stack
(`system-ui, -apple-system` fallback) · letter-spacing negativo en headlines · **cero gradientes y cero
sombras en chrome** (solo la drop-shadow de "producto sobre superficie") · radios generosos. Reemplaza el
skin Vercel COMPLETO (selectores semánticos intactos — el CSS es lo único que cambia de idioma).

## §4 Los incrementos (el orden ES dependencia: 1 primero para que 2–5 nazcan en idioma Apple)

| INC | Nombre | Qué monta | Backend | Riesgo |
|---|---|---|---|---|
| 1 | `FSK-FRONTEND-APPLE` | Re-skin `_APP_CSS` (constants.py:1115) Vercel→Apple, patrón EXACTO de FSK-FRONTEND-VERCEL (guía→tokens→CSS semántico). El diente de estilos (`getComputedStyle(body).maxWidth`) se MUEVE al container Apple (~980–1024px, decidirlo del guide; actualizar CSS + `_STYLES_ASSERT_BLOCK` + docstrings juntos). | CERO | bajo |
| 2 | `FSK-FRONTEND-TABLE` | Lista `<ul><li>` → `<table>` semántica: `<th>` desde los nombres de campo del schema (orden del spec), `<tr data-id>` (el click-para-detalle EXISTENTE debe seguir verde). Diente: headers + celda con el valor sembrado en DOM real; sabotaje → solo asserts de tabla rojos. Budget: bump BASE esperado. | CERO | bajo |
| 3 | `FSK-FRONTEND-SEARCH-PAGE` | Búsqueda client-side (input filtra filas por texto, case-insensitive) + paginación client-side (page-size fijo + controles prev/next/contador) sobre la lista YA traída. Corte honesto: server-side LIMIT/OFFSET queda DIFERIDO EXPLÍCITO (seeds chicas; solo si el volumen lo exige). Diente: tipear el valor sembrado → 1 fila; tipear basura → 0 filas + estado vacío visible; paginar → cuenta correcta. | CERO | bajo |
| 4 | `FSK-FRONTEND-DETAIL-TABS` | Detalle → 2 columnas con tabs. Tab «Historial» SOLO para entidades `audited: true` (opt-in, como el eje): monta `GET /action_logs` filtrado client-side por `subject_type`+`subject_id`. Diente: create+edit del FORM → abrir historial → las filas `[actionlog]` reales en DOM (compone el diente actionlog existente); entidad no-audited → sin tab. | CERO (dato ya vivo) | medio (filtro por sujeto es client-side sobre `GET /action_logs` completo — si el log crece, diferir un query-param es honesto) |
| 5 | `FSK-FRONTEND-TRASH` | Papelera para entidades `soft_delete: true`: vista «borrados» + botón restore (verbo YA enforzado). **Backend MÍNIMO**: un read-path `GET /<plural>?deleted=true` (RBAC-gated, invierte el filtro `IS NULL`, compone company-scope) — HOY nada lista los borrados. Diente: delete → fila aparece en papelera; restore → vuelve a la lista viva; sabotaje del filtro → solo asserts trash rojos. | read-path chico en AppServer codegen | medio |
| 6 | `FSK-FRONTEND-LOGIN` | Pantalla de login. **DECISIÓN AL ABRIR — dos cortes**: **(A) session-picker dev**: elegir actor/rol del `/seed`, arma el token actual `Bearer role:owner`, CERO backend — honesto para demo, NO es auth real. **(B) credenciales reales**: store de principals + password + emisión de token → eje de SEGURIDAD backend, trust-chain, contrato+revisión Opus obligatoria, sesión propia. **Recomendado contra-el-tiempo: A ahora; B queda como INC-7 diferido explícito y declarado.** | A: CERO · B: sí (auth) | A: bajo · B: ALTO (security path) |

## §5 Estimación y cadencia (medida, no deseada)

Cadencia real del arco frontend previo: **~1 incremento por sesión S2** (DETAIL→EDIT→OPERATIONS→DASHBOARD
→STYLES cerraron a ese ritmo; todos cabalgaron s9 sin re-pin). Con corte A en INC-6:
**6 incrementos ≈ 6 sesiones S2 ≈ 2–3 días** en serie + esta S1 (plan) + una S3 corta de cierre de arco.
Con corte B: +1 incremento y +revisión Opus (no lo pongas en el camino crítico de la demo).

## §6 Qué NO está en este plan (declarado, no escondido)

- s6/LLM (REQ-F-007): apagado deliberado; encenderlo es OTRA dirección (no es pantalla).
- Fidelidad de dominio restante (SNIPEIT-DOMAIN §4 item 20): Kits · EAV-a-runtime · flecos PUT-UNIQUE/refs
  · push a registry — no son pantallas; incrementos más grandes, fuera de este arco.
- Server-side search/pagination (diferido en INC-3) · query-param de actionlog (diferido en INC-4) ·
  login real (corte B, diferido si se elige A).

## §7 Apertura (mecánica exacta, para la próxima sesión)

```
meta increment open  # nivel factories/full-stack-kotlin, nombre FSK-FRONTEND-APPLE
# crear docs/work/FSK-FRONTEND-APPLE-INCREMENT.md (handoff autocontenido, patrón FSK-FRONTEND-VERCEL)
# ejecutar (S2) → cerrar por §2.8
```
