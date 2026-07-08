<!-- meta:doc sha=b73fc95d5db62e291a193001ef4c5e3331b21ceb updated=2026-07-08T18:06Z -->
# Incremento FSK-MODELGEN-DURABLE

> **Doc de gobierno.** Estado: **ABIERTO** (2026-07-08T15:53Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Implementar el mecanismo de **ADR-024**: hacer que un producto FSK tenga una **superficie humana
model-nativa DURABLE** (`frontend/src/app.ts` + `frontend/src/app.css`) — commiteada, no re-derivada,
verificada por `design_floor`, pineada — SIN romper los productos-template pineados (`assets`). Es la
mitad que falta: el A/B (`FSK-FRONTEND-MODELGEN-AB`) construyó la mitad VERIFICAR; esto construye la
COEXISTENCIA (override + opt-in + design_floor estándar). Prerrequisito de `FSK-SNIPEIT-MODELGEN`.

Es COLUMNA (toca la ley de pin/ci y el perfil de verificación) → se escribe y revisa con ojos propios,
no se delega (SELF-IMPROVEMENT §3, ADR-024 «trust-chain»).

## Diseño (el juez primero — dientes deterministas antes que el mecanismo)
1. **Override pineado (DATO).** `products/<p>/frontend/app.ts` + `app.css` = superficie model-nativa
   TRACKED. `product.yml`: `frontend_surface: model-native` (opt-in explícito). El codegen del frontend
   (`codegen/scaffold/frontend.py` para `app.ts`, `constants._APP_CSS` para `app.css`), cuando el
   producto declara el opt-in, **COPIA el override** en `build/` en vez de emitir el template.
2. **`design_floor` promovido a s9 OPT-IN.** El check `tools/design_floor_check.ts` (6 ejes, ya
   escrito para el A/B) se corre desde s9 SÓLO si el producto tiene superficie model-nativa. Los
   productos-template (`assets`) no lo corren → siguen verdes en su pin (ADR-023 §3 intacto).
3. **Verificar-no-re-derivar.** Para un producto opt-in, `ci` re-VERIFICA (s8/s9 + design_floor sobre la
   superficie commiteada) en vez de re-derivar la superficie. El pin ES el artefacto verificado.

## Dientes (two-sided, columna)
- **`design_floor` opt-in**: producto opt-in con superficie clobbereada/faltante → ROJO; producto-template
  sin opt-in que igual corriera design_floor → error de config → ROJO. (ADR-024 §5)
- **No-regresión de `assets`**: `ci --rederive assets` == pin (el opt-in no toca a los no-adoptantes).
- **Byte-neutralidad del no-adoptante**: un producto sin `frontend_surface` re-deriva byte-idéntico
  (el flag emite sólo si != default, patrón `tier` de DIAL-MEASURE).

## Alcance (blast radius)
`codegen/scaffold/frontend.py` · `codegen/scaffold/constants.py` (o `buildcfg`/loader del flag) ·
la wiring de s9→design_floor (estación/perfil) · `tools/` si el gate necesita el modo estándar. NO toca
el cliente tipado ni los checks browser/consume (se preservan template).

## Plan
1. **✅ Mecanismo override (copiar en vez de emitir) + flag `frontend_surface`** (byte-neutral, este INC/factory).
   `_load_blueprint` carga el override (fail-closed: opt-in exige app.ts+app.css) en `bp["_frontend_surface"]`;
   `build_files` copia verbatim en los 2 puntos de emisión (`__init__.py` líneas app.ts/app.css). Verificado
   byte-neutral: `--check-idempotent` de un no-adoptante = 77 archivos idénticos (path template intacto).
2. **⏳ Wrapper `tools/design_floor_probe.py` + wiring s9** → `frontend_design_floor` con `when:` (este INC/factory).
3. **⏳ Refactor `modelgen_ab_gate.sh §2/§2b/§3`** para llamar al wrapper (single-source de la derivación).
4. **⏳ Verificar factory:** `meta check` verde · `ci --rederive assets`==pin (byte-neutral) · lado ROJO del diente
   (design_floor sobre un frontend TEMPLATE falla = baseline arm-A).
5. **⏳ Adopción helpdesk = INCREMENTO SEPARADO (product-instance).** ⚠️ DESCUBRIMIENTO: `product.yml` es de nivel
   `products/helpdesk` (ADR-016, el edit-gate por-nivel lo BLOQUEA desde el increment factory). El flag +
   commitear la superficie + probar el lado VERDE (design_floor pasa en la app model-nativa VIVA) son un
   increment en `products/helpdesk/docs/work/` (precedente: `FSK-FRONTEND-MODELGEN-HELPDESK`). Split de 3 niveles:
   META `CHECK-WHEN-GUARD` ✅ · FACTORY `FSK-MODELGEN-DURABLE` (mecanismo, este) · PRODUCT-INSTANCE helpdesk-adopt.
   La superficie ganadora YA está capturada (byte-idéntica al build) en `products/helpdesk/frontend/app.{ts,css}`
   (UNTRACKED — la commitea el increment helpdesk).

## Handoff — hechos descubiertos (para no re-leer el motor)
**Mitad META LISTA: `CHECK-WHEN-GUARD` ✅ (meta commits 0f1085e·d2e9c07).** El motor YA tiene el opt-in
por-check: un check con `when: {frontend_surface: model-native}` corre SÓLO para productos model-nativos y se
saltea byte-neutral (no toca el pin de `assets`). Lo que resta es SÓLO adopción FSK. Seams verificados:
- **Flag**: `frontend_surface: model-native` top-level en `products/<p>/product.yml`. Fluye solo a
  `subst[frontend_surface]` (`spec.subst` aplana `domain.product`) — cero cambios en loader/`_subst_for`.
- **Ley del pin** (`seed/verifier.compute_proof_sha`): sha sobre `{station_id, sorted[(name,exit)]}` → SÓLO
  los checks que corrieron. Un check `when`-salteado ⇒ `proof_sha` idéntico. `pinned_verdict.json` = `{sid: sha}`.
- **s9 opt-in**: agregar a `stations/s9.yml` un check `frontend_design_floor` (kind `infra_up`, patrón de los
  otros 4: boot app + PG fresca + `proof:` corre la derivación+`design_floor_check.ts`) con `when:
  {frontend_surface: model-native}`.
- **✅ DECISIÓN S1 (2026-07-08, ojos-propios): wrapper Python — NO el `.ts` leyendo el spec.** `design_floor_check.ts`
  toma `URL SHOT PROBE CONTRACT`; PROBE+CONTRACT se DERIVAN del spec (`modelgen_ab_gate.sh §2/§2b`, heredocs
  Python). Se elige el **wrapper Python** porque: (a) el spec (`products/<p>/factory.spec.yml`) NO vive en el cwd
  del check (`build/product/frontend`) sino en `../../factory.spec.yml` — que el `.ts` lo lea acopla la herramienta
  browser al layout del árbol fuente y le mete parseo YAML + dependencia node, rompiendo su contrato documentado
  (erasable-types, names-no-domain, cwd=frontend autocontenido); (b) leer el plan ya ES tarea Python (ADR-012) — el
  `.ts` sólo renderiza/chequea; (c) un `tools/design_floor_probe.py` **single-sourcea** la derivación: lo usan TANTO
  el s9 check COMO `modelgen_ab_gate.sh` (elimina la duplicación de heredocs). El `.ts` queda intacto.
  **Wiring:** nuevo `tools/design_floor_probe.py <url> <spec_path> [shot]` = el `proof:` del check `frontend_design_floor`
  (workdir `build/product`, spec en `../../factory.spec.yml`, `tools/` ya se copia al build): lee spec → deriva
  PROBE+CONTRACT → corre `node design_floor_check.ts` con cwd=`frontend` → propaga exit. `modelgen_ab_gate.sh §2/§2b/§3`
  se refactoriza para llamar al mismo wrapper.
- **Copy-vs-emit**: en s0 la superficie se COPIA de `products/<p>/frontend/app.{ts,css}` en vez de emitir el
  template. Puntos: `codegen/scaffold/frontend.py` (app.ts) + `constants._APP_CSS` (app.css). Mismo flag.
- **Primer producto durable**: la superficie model-nativa que ganó el A/B es de `helpdesk` (sweet-spot 5 ent.),
  vive en `build/` gitignored → COMMITEARLA a `products/helpdesk/frontend/app.{ts,css}` (o regenerarla) para
  probar el lado VERDE del diente. snipe-it (19 ent., split en slots Sonnet) es INC-B, NO este increment.
- **Cierre**: FSK STATE está stale (pre-existente) → actualizar su «Ahora» al cerrar (limpia el residual docs).

## Evidencia
**Paso 1 (mecanismo copy-vs-emit) — HECHO + verificado (2026-07-08):**
- `blueprint.py._load_blueprint`: guard `frontend_surface` fail-closed (valor ∈ {model-native}; opt-in exige
  `frontend/app.{ts,css}`) → carga override en `bp["_frontend_surface"]`. `__init__.py.build_files`: `surface =
  bp.get("_frontend_surface") or {}`; app.ts/app.css = `surface[...] if surface else _app_ts/_app_css` (byte-neutral).
- **Byte-neutralidad probada (light):** no-adoptante (`helpdesk` SIN flag) → `scaffold --selftest` 73 archivos ·
  `--check-idempotent` 77 byte-idénticos. Sin flag = 0 claves nuevas = codegen idéntico (no re-pin).
- **Superficie verde capturada:** `products/helpdesk/frontend/app.{ts,css}` = sha-idéntica al build ganador del
  A/B (app.ts `46c53c7…`, app.css `b3328a6…`). UNTRACKED (la commitea el increment helpdesk).

**Refinamientos de wiring descubiertos (para el próximo, corrige el §Handoff):**
- **Ambos tools quedan factory-level, hermanos** (`tools/design_floor_probe.py` + `tools/design_floor_check.ts`).
  El `.ts` es product-AGNÓSTICO (JSON args) → NO se emite per-producto (evita meter 211 líneas como literal de
  codegen). El wrapper se auto-localiza el `.ts` por `Path(__file__).parent` y deriva el frontend del spec_path:
  `Path(spec_path).resolve().parent / "build/product/frontend"` (ambos anclados en product_root, sin acople a la
  profundidad del build). `proof:` s9 lo referencia con `python3 ../../../../tools/design_floor_probe.py <url>
  ../../factory.spec.yml` (workdir `build/product`; `products/<p>/build/product` está 4 niveles bajo la raíz de
  fábrica — fijo/determinista, mismo patrón que `modelgen_ab_gate.sh` que ya llega al `.ts` por `$HERE`).
- **Env del proof NO scrubbeado de libs:** `seed/verifier.py` hace `env = dict(os.environ)` (sólo augmenta
  PYTHONPATH) → `yaml` DISPONIBLE (6.0.3). El wrapper puede `import yaml` (como ya hace el heredoc de
  `modelgen_ab_gate.sh`). El "stdlib puro" de `obs_check.py` es disciplina de portabilidad, no un límite del env.
- **Derivación a single-sourcear** (copiar de `modelgen_ab_gate.sh`): PROBE = 1ª entidad con campo opcional y sin
  ref requerido, body = requeridos rellenos (§2). CONTRACT = por-entidad, todos los campos MENOS el `owned_by`
  (server-set, §2b). El wrapper corre `node --experimental-strip-types … design_floor_check.ts <url> <shot|-> <probe|-> <contract|->`
  con cwd=frontend y propaga el exit.
