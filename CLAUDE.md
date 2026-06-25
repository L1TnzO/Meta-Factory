<!-- meta:doc sha=15ad1d55c8661a64febefd26a52e6cbfe6cc3cd7 updated=2026-06-25T19:06Z -->
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
- **Commit = parte del trabajo, no se pregunta (ADR-010)**: al terminar un cambio —código o docs—,
  commiteá (mensaje con trailers I-10); NUNCA ofrezcas «¿lo commiteo?». Esto OVERRIDE el default genérico
  «commitear sólo cuando el usuario lo pide». El código lo enforza la máquina (`increment_guard`/`gate_guard`);
  los **docs fuera de incremento NO tienen dientes** (residual aceptado, ADR-010 addendum) — ahí la disciplina
  la sostiene esta regla: un parche que REDUCE lo no-commiteado sin agregar ruido, no que lo elimina.
- **El seed (Stage 0) es trust-chain**: se escribe y revisa con ojos propios, no se delega
  (SELF-IMPROVEMENT §3). Lo determinista al CLI, lo impedido a hooks, lo de-cada-turno acá (con
  presupuesto), lo de-rol a agents, lo histórico a docs (CONTEXT-ECONOMY §3, ley de colocación).
- **Multi-archivo por mantenibilidad (2026-06-25)**: el código que escribas de ahora en adelante —sustrato,
  codegen, o artefacto generado— va en archivos cohesivos por responsabilidad, NO en un monolito; no agregues
  archivos NUEVOS de miles de líneas (si uno nuevo tiende a ~800+, partilo en módulos). Los monolitos
  EXISTENTES son deuda conocida (`factories/full-stack-kotlin/codegen/scaffold_product.py`, ~8k líneas) —
  no los reescribas salvo pedido explícito.
