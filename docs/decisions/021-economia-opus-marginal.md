<!-- meta:doc sha=a03c7390b479252b1431ffc7e20344c275902f73 updated=2026-07-02T14:33Z -->
# ADR-021 — Economía Opus-marginal: ruteo por SESIÓN, doctrina de cache, y el plan fijo COST-DOWN

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-07-02T14:35Z |
| Decide | el ingeniero (2026-07-02, «Dale, sí — ponlo en un documento fundacional» tras el diseño re-preciado); ejecuta el orquestador |
| Generaliza | ADR-017 §3 (routing como dato — acá sube del slot a la SESIÓN), ADR-020 (roles cerrados; el modelo es parámetro de invocación, no rol nuevo), ADR-010 (incremento como unidad), I-12 (toda regla tiene sombra determinista — acá, el ledger) |
| Referencia | **`work/COST-DOWN-DIRECTION-INCREMENT.md` (LA BIBLIA — auto-contenida: evidencia §1 · doctrina §2 · catálogo §3 · plan fijo §4 · KPIs §5)** · `work/DELEG-PAYOFF-MEASURE-INCREMENT.md` (mediciones crudas) |

## Contexto (medido, no narrado)

$2,761.18 en 32 sesiones, **opus 89%** del costo. La delegación por slots (ADR-020) delegó 159k tokens a
Sonnet y la aguja no se movió (0.06% acumulado): ataca el OUTPUT de Opus pero el costo real es su
**RESIDENCIA** — turnos × contexto (Bash 6,170 · Read 3,496 · Edit 2,430 acumulados) re-leídos del cache en
cada turno mecánico, más thinking facturado como output. Con la tabla de precios vigente (Opus 4.8
$5/$6.25/$10/$0.50/$25 · Sonnet 5 $2/… · Haiku 4.5 $1/… — hit=10% base, w5m=1.25×, w1h=2×), la descomposición
de una sesión tipo es ~45% cache-hits + ~40% output/thinking + ~7% churn de cache + ~2% writes. Dos hechos
verificados 2026-07-02: `billing.py` preciaba solo `(input, output)` (ciego al cache) y la línea FSK **no
llama a ningún modelo** (el día-a-día caro es la sesión Opus que la babysittea, no la línea).

## Decisión

**(a) Modelo operativo Opus-marginal — ruteo por SESIÓN.** La correctitud la dan los GATES (radios por hook,
veredicto obligatorio, retry ≤2, pin de clon limpio), no el IQ del ejecutor → el modelo de una sesión es un
parámetro de PRECIO. Tres clases: **S1 DISEÑO** (Opus corto, thinking alto → plan como data) · **S2 EJECUCIÓN**
(`claude --model sonnet --agent orchestrator`, mecánico, escala por archivo de escalación — nunca "piensa más
fuerte") · **S3 REVISIÓN/CIERRE** (Opus muy corto, residuo con ojos). El día-a-día (producto desde spec) NO
usa Opus: shell directo o Sonnet. Sin rol nuevo (vocabulario ADR-020 intacto).

**(b) Doctrina de cache.** Cada hit refresca el TTL → el cache muere por HUECO > TTL, no por duración.
Regla cerrada: 1h conviene ⟺ esperás ≥1 hueco >5min por sesión (2 writes 5m = 2.5× > 1 write 1h = 2×) — en
sesiones de trabajo real, SIEMPRE que el knob exista. Las 3 cartas que dominan sin knob: hueco al FINAL →
**matar la sesión** (rehidratar ≈500 tok) · hueco DURANTE → **keep-warm poll ≤4min** (0.1× vs 1.25×, 12.5×) ·
**compactación = incidente, meta 0**. El knob TTL/proxy es condicional a medición (INC-5), no fe.

**(c) El plan es FIJO: N=7 incrementos, orden inmutable, congelado en la biblia §4.**
`COST-RUNBOOK` → `PRICING-LEDGER` → `HARNESS-FAST-GATE` → `CONTEXT-LEAN-TEETH` → `PLAN-EXECUTE-SPLIT` →
`CACHE-SHAPE` (condicional: churn >10% del gasto, si no N/A) → `HEADLESS-SLOTS` (condicional: residencia
durante slots ≥10%, si no N/A). Las sesiones futuras EJECUTAN (leen biblia §2 + su §4.INC-n); los desvíos se
declaran como residual en el work-doc del INC — no se re-planifica la dirección.

**(d) El costo es DECIDIBLE.** La tabla de precios real (5 columnas, fechada, con vencimiento de la promo
Sonnet 2026-08-31) vive como DATA en el ledger; `meta outcome` reporta por incremento $ total · share por
tier · expiraciones · compactaciones · churn · % delegado. Targets: **opus ≤35% · compactaciones 0 · churn
<20 · $/incremento −60%**. "Llegamos" = 2 incrementos consecutivos post-INC-4 cumpliendo todos.

## Consecuencias (honestas)

- **Piso irreducible ≈20–30%** del gasto actual (S1+S3+escalaciones+columna-con-ojos): la promesa es 3–5×
  por incremento y ~10× solo en el día-a-día determinista — no 10× global.
- Con esta tabla, Opus→Sonnet da ≤2.5× (no 5×): la ganancia real es multiplicativa (ruteo × contexto-lean ×
  menos-turnos × higiene-de-cache). Un ejecutor S2 puede flotar: el peor caso es desperdicio 2.5× más barato,
  acotado por retry ≤2 + escalación; jamás código malo aceptado (gates).
- Anti-palancas TAN fijas como el plan (biblia §6): no multi-agente paralelo para codegen secuencial (~15×
  medido) · no bajar S1/columna a Sonnet (lección Snipe-IT) · no acortar la verificación · no obsesionarse
  con el TTL (5–15% de la factura) · re-evaluar ruteo al vencer la promo Sonnet (2026-09-01).
