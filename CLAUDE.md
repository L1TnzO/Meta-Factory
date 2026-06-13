<!-- meta:doc sha=f62d7be843514e30e11cc3e8737a56dd832229f7 updated=2026-06-13T15:21Z -->
# Meta-Factory — orientación (fase de diseño)

> PROVISIONAL: orientación de arranque para la fase de diseño/bootstrap. Las reglas operativas
> REALES (presupuesto de residencia, ley de colocación, gates) se GENERAN al construir el harness
> en el bootstrap (meta-estación M7). Este archivo solo enruta; no es la maquinaria.

## Empezá acá
1. Leé `docs/STATE.md` — punto de entrada único y estado actual (si tenés amnesia, empezá ahí).
2. Para construir: `docs/work/BOOTSTRAP-INCREMENT.md` — la línea M0–M3+M8 + el seed congelado.
3. Mapa completo de la documentación: `START-HERE.md`.

## Estado
**BOOTSTRAP EJECUTADO (2026-06-13).** Ya hay código verificado por bloqueo: `seed/` (columna),
`src/metafactory/` (engine·spec·bus·cli), `stations/` (M0–M3+M8), `template/factory/`, y un
dummy-fábrica producido en `factories/dummy/`. Los 8 criterios de cierre pasan (ver
`docs/work/BOOTSTRAP-INCREMENT.md §Evidencia`). Diferido: M4–M7, regeneración de ASF, métricas/memoria-T2.

## Reglas de esta fase
- **NO tocar `../Agent_Systems_Factory/` (ASF)**: es referencia CONGELADA de cosecha y paridad
  (decisions/006). Se regenera como producto recién después del bootstrap.
- **Marcas de tiempo**: `YYYY-MM-DDTHH:MMZ` (UTC, al minuto). Git es la autoridad (`date -u`).
- **Citas de ADR**: Meta-Factory = `ADR-NNN` bare; ASF = `ASF/ADR-NNN` (ambos numeran desde 001 — el
  prefijo evita colisión). Un bare `ADR-009` SIEMPRE es el del Meta-Factory (`decisions/009`).
- **Esquema de docs (mutación por tipo)**: STATE overwrite · LOG append (más nuevo arriba) ·
  decisions/ inmutable · work/ por-incremento · reference/ estable. Actualizar el doc correcto ES
  parte del trabajo, no es opcional (ADR-007: la memoria es fase de gate + checkpoint, no una pregunta).
- **El seed (Stage 0) es trust-chain**: se escribe y revisa con ojos propios, no se delega
  (SELF-IMPROVEMENT §3). Lo determinista al CLI, lo impedido a hooks, lo de-cada-turno acá (con
  presupuesto), lo de-rol a agents, lo histórico a docs (CONTEXT-ECONOMY §3, ley de colocación).
