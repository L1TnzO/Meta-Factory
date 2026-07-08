<!-- meta:doc sha=fe9264b99f021dc6595382d73b90a4e98724e0bc updated=2026-07-08T15:54Z -->
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

## Evidencia
_(pendiente)_
