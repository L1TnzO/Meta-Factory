<!-- meta:doc sha=c732251674b285a4900f9578b1370b39985a9e07 updated=2026-07-04T20:10Z -->
# Incremento SESSION-CLASS-AS-DATA

> **Doc de gobierno.** Estado: **DIFERIDO** (diseñado 2026-07-04T02:58Z, sesión S1). Reabrir con
> `meta increment open SESSION-CLASS-AS-DATA` DESPUÉS de la corrida S2 que cierra el KPI opus-share
> (COST-DOWN §5). Origen: pedido del ingeniero 2026-07-03 («que el cambio de modelo no dependa de
> leer entre líneas») + diseño conversado en S1. Contexto: `reference/FOUNDATIONS-REAUDIT.md §4`.

## Objetivo
El ruteo S1/S2/S3 (ADR-021) deja de depender de memoria humana: la clase de la PRÓXIMA sesión es un
DATO escrito una vez (en S1, cuando hay juicio), ejecutado mecánicamente, y el mismatch lo detecta la
máquina al primer turno — no el ingeniero leyendo prosa entre líneas.

## Piezas (3 con dientes + 2 observers)
1. **`session_class` como dato**: campo en la WorkOrder del plan (`.gen/plan.json`, `plan.py`) y/o en
   el header del work-doc: `S1|S2|S3` + modelo. Enum CERRADO validado (como los demás vocabs, ADR-020).
   Se congela cuando S1 diseña; nunca se re-decide por prompt.
2. **`meta session`**: lee el incremento/plan abierto e imprime el comando de lanzamiento EXACTO
   (p. ej. `claude --model sonnet --agent orchestrator`). Cero decisión en el humano.
3. **Diente de mismatch (COLUMNA — trust-chain, ojos propios, NO se delega)**: SessionStart compara el
   modelo de la sesión vs la clase del INC abierto; en mismatch GRITA con el comando correcto («este
   INC es S2 y abriste Opus → matá esta sesión y corré `meta session`»).
4. **Cierre prescriptivo literal**: `meta increment close` / el handoff terminan con un bloque
   inequívoco: «PRÓXIMA SESIÓN: `/clear` → `<comando>` → `<primer verbo>`».
5. **Schema-tooth del work-doc** (check en `meta check`): secciones obligatorias (Objetivo · Alcance ·
   Criterio de cierre decidible · Evidencia al cerrar). Dos lados: doc sintético sin criterio → rojo.

## Observers (medición pedida por el ingeniero — datos YA registrados en journal + ledger)
- **A**: aperturas de INC frías (inicio de sesión limpia + handoff) vs calientes (final de sesión
  cargada) → $/resultado por clase. Observer, NO gate (N chico, confundido por clase de INC).
- **B**: calidad de INCs pre-diseñados (plan S1, p. ej. COST-DOWN N=7) vs ad-hoc → proxy medible =
  escalaciones + retries + $/incr (`meta outcome`).

## Criterio de cierre (demostrable)
1. `meta session` imprime el comando correcto para cada fila del plan (verificable en frío).
2. Mismatch sintético → SessionStart grita (dos lados: match=silencio, mismatch=grito con comando).
3. Schema-tooth rojo sobre un work-doc sintético sin criterio de cierre; verde sobre los reales.
4. Observers A/B corren sobre el historial existente y emiten tabla.

## No-alcance (honesto)
- NO cambiar el modelo del hilo a mitad de sesión (imposible por plataforma; económicamente inútil —
  la residencia domina, 89% medido).
- NO daemon/heurística que «detecte» la clase al vuelo (anti-palanca COST-DOWN §6: no sobre-hookear).
- NO base de datos / MCP para incrementos: git + `.gen/plan.json` + verbos `meta` YA son ese sistema
  (ADR-019: podar antes de agregar; una segunda fuente de verdad deriva).
