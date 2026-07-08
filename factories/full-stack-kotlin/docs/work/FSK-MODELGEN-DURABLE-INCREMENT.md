<!-- meta:doc sha=43821703b70c80da7b9cce61ba03a9b0f7d88fd4 updated=2026-07-08T17:44Z -->
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
1. Diente `design_floor` opt-in + no-regresión `assets` (columna, ojos) — two-sided ANTES del mecanismo.
2. Mecanismo override (copiar en vez de emitir) + flag `frontend_surface` (byte-neutral para no-adoptantes).
3. Wiring s9 → design_floor opt-in.
4. Verificar: `meta check` verde · `ci --rederive assets`==pin · el diente rojo/verde probado a mano.

## Handoff — hechos descubiertos (para no re-leer el motor)
**Mitad META LISTA: `CHECK-WHEN-GUARD` ✅ (meta commits 0f1085e·d2e9c07).** El motor YA tiene el opt-in
por-check: un check con `when: {frontend_surface: model-native}` corre SÓLO para productos model-nativos y se
saltea byte-neutral (no toca el pin de `assets`). Lo que resta es SÓLO adopción FSK. Seams verificados:
- **Flag**: `frontend_surface: model-native` top-level en `products/<p>/product.yml`. Fluye solo a
  `subst[frontend_surface]` (`spec.subst` aplana `domain.product`) — cero cambios en loader/`_subst_for`.
- **Ley del pin** (`seed/verifier.compute_proof_sha`): sha sobre `{station_id, sorted[(name,exit)]}` → SÓLO
  los checks que corrieron. Un check `when`-salteado ⇒ `proof_sha` idéntico. `pinned_verdict.json` = `{sid: sha}`.
- **s9 opt-in**: agregar a `stations/s9.yml` un check `frontend_design_floor` (kind `infra_up`, patrón de los
  otros 4: boot app + PG fresca + `proof:` corre `tools/design_floor_check.ts`) con `when: {frontend_surface:
  model-native}`. ⚠️ DECISIÓN ABIERTA (S1, arrancar acá): `design_floor_check.ts` toma `URL SHOT PROBE CONTRACT`
  y PROBE+CONTRACT se DERIVAN del spec en Python (ver `tools/modelgen_ab_gate.sh` §2/§2b). Como check s9 hay que
  derivarlos — o un wrapper `.py`, o que el `.ts` los lea de `factory.spec.yml`. Elegir antes de cablear.
- **Copy-vs-emit**: en s0 la superficie se COPIA de `products/<p>/frontend/app.{ts,css}` en vez de emitir el
  template. Puntos: `codegen/scaffold/frontend.py` (app.ts) + `constants._APP_CSS` (app.css). Mismo flag.
- **Primer producto durable**: la superficie model-nativa que ganó el A/B es de `helpdesk` (sweet-spot 5 ent.),
  vive en `build/` gitignored → COMMITEARLA a `products/helpdesk/frontend/app.{ts,css}` (o regenerarla) para
  probar el lado VERDE del diente. snipe-it (19 ent., split en slots Sonnet) es INC-B, NO este increment.
- **Cierre**: FSK STATE está stale (pre-existente) → actualizar su «Ahora» al cerrar (limpia el residual docs).

## Evidencia
_(pendiente)_
