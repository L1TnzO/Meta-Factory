<!-- meta:doc sha=6456af0e79b55460d0463a1e90f82609327fd181 updated=2026-06-26T03:49Z -->
# Incremento REAIM-SWEET-SPOT

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-26T03:41Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
El **mecanismo de benchmark** de la Fase 4 (ADR-017 §4): convertir "qué es un producto TERMINADO de la clase
sweet-spot (la app CRUD del 80% día-1)" de PROSA a un **TARGET verificable**, dos-lados, re-derivado de estado
COMMITEADO — y con él volver la degradación de Snipe-IT a "techo de regresión, no punto de partida" un HECHO
DURO, no una frase. Es el incremento META hermano de `FSK-HELPDESK` (ADR-016: dos incrementos por nivel).

## El mecanismo (qué deja en el sustrato)
- **`benchmarks/sweet-spot-crud.yml` (DATA, como `scenarios/` o `parity.yml`)**: declara el TARGET de la clase
  —`entity_count` ∈ [5,8] + 6 capacidades núcleo (datos vivos · RBAC · ownership · workflow · control de
  acceso a runtime · frontend que renderiza)— y clasifica productos: `helpdesk` = `sweet_spot` (DEBE cumplir),
  `snipeit` = `ceiling` (DEBE fallar). El sustrato no nombra producto/fábrica; el DATA sí (ADR-012).
- **`src/metafactory/verify/benchmark.py`**: re-deriva el PERFIL de cada producto SÓLO de estado commiteado
  —spec base de la fábrica (capability→estación, la MISMA arista que camina `rtm.py`) + `product.yml`
  (#entidades) + `pinned_verdict.json` (qué estaciones están pineadas verdes)—. Sin `.proof/`, sin re-correr
  la línea: barato y funciona en clon limpio. Una capacidad está satisfecha sii TODA estación que la satisface
  está pineada. `gate_problems()` = la ley única (display + gate, ADR-005 §4).
- **`verify/checks/benchmark_gate.py`** cableado a `meta check`: GREEN = todo `sweet_spot` cumple · RED (diente
  de dos lados) = todo `ceiling` NO cumple (un techo que cumpliera ⇒ bound sin tope = decorativo → rojo); un
  benchmark de un solo lado no tiene dientes → rojo; sin archivo de benchmark → N/A honesto (SAFE-7).
- **`meta benchmark [name]`**: el verbo de display (bus-bounded) — perfil de cada producto vs el target.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | DATA del target (`benchmarks/sweet-spot-crud.yml`) + re-derivación de estado commiteado (`benchmark.py`) | ✅ |
| 2 | Gate dos-lados (`benchmark_gate.py`) + verbo `meta benchmark` + cableado a `meta check` | ✅ |
| 3 | Tests por bloqueo (techo decorativo · regresión sweet-spot · un-solo-lado · cap sin pin · N/A) | ✅ |
| 4 | ROADMAP/STATE marcan Fase 4 §1+§2 ✅; LOG narra; memoria refrescada | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `meta benchmark` PASS: helpdesk [sweet_spot] cumple (5 ent, 6/6 caps) · snipeit [ceiling] FALLA (19 ent
   fuera de [5,8]) → la degradación de Snipe-IT es un HECHO re-derivable. ✅
2. `tests/test_benchmark.py` verde, dos-lados por bloqueo (9 tests): techo decorativo (bound 5-25 → snipeit
   pasa → rojo) · regresión sweet-spot (floor 6 → helpdesk no cumple → rojo) · un-solo-lado → rojo · cap
   `logica_dominio_generada` (s6 diferido, sin pin) → no satisfecha · N/A sin archivos. ✅
3. `meta check` **11/11** (era 10/10 + el gate `benchmark`); `generality` verde (el sustrato no nombra
   producto/fábrica/tech). ✅
4. Anti-overfit: `git grep` de nombres de producto/fábrica en `src/metafactory/` del benchmark = 0 (viven en
   el DATA). ✅

## Evidencia (por bloqueo)
- `meta benchmark` → `PASS · 2/2 productos en su clase esperada` (helpdesk MEETS · snipeit below/over → ceiling ok).
- `pytest tests/test_benchmark.py` → 9 passed.
- `meta check` → `11 checks all green` (… deferred ok · **benchmark ok** · suite ok); era 10/10.
- Anti-overfit: cero nombres de producto/fábrica en `benchmark.py`/`benchmark_gate.py` (DATA en `benchmarks/`).

## Alcance honesto (§7)
El benchmark mide estado COMMITEADO (entidades + estaciones pineadas), no re-corre la línea (eso es
`products_rederive`/`ci --rederive`, ya gateados). "Capacidad satisfecha" = su estación pineada verde, no una
re-evaluación viva — correcto: el pin YA es re-derivable y gateado aparte. El dial borrador→endurecer y la
cosecha del vocabulario PWF son los incrementos hermanos siguientes de la Fase 4.
