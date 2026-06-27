<!-- meta:doc sha=ca44b3fa08de30f43eae71d2dc98ae55a050faee updated=2026-06-27T02:28Z -->
# Incremento FACTORY-DOC-MIGRATE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-27T02:22Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> Nivel: **META** (mueve docs entre homes + actualiza punteros vivos; NO toca `src/`/`seed/`).
> Autoridad de diseño: `docs/reference/GOVERNANCE-LAYERING.md §6/§7` (Opción A faseada, Fase 2 §2) + ADR-016.

## Objetivo
Cerrar **ADR-016 Fase 2 §2**: migrar los **16 incrementos `FSK-S0..S15`** —trabajo de NIVEL-FÁBRICA que hoy
vive mal en `docs/work/` del **meta**— a su home correcto `factories/full-stack-kotlin/docs/work/` (donde sus
42 hermanos `FSK-*` ya viven), dejando la regla single-source del §1 (la casa de un doc = el nivel cuyo
trabajo describe) consistente para el carril de la fábrica FSK. Sin esto, el §1 sigue VIOLADO (lo dice la
propia tabla §2 del doc de gobierno, fila «los incrementos de la FÁBRICA … viven en `docs/work/` del meta ❌»).

## Por qué ahora (composición con §3)
§3 (`FACTORY-DOC-SEAL`, 2026-06-27) acaba de bajar el sello content-addressed (ADR-009) a **cada home por
nivel**: el home de fábrica ya SELLA y CHEQUEA frescura POR-HOME. §2 lo PUEBLA — los 16 docs migrados quedan
sellados + verificados en su home propio, y salen del `doc_set` meta (e INDEX). El sello es content-only (sha
del cuerpo, excluyendo la línea-sello), así que el move es **byte-idéntico**: los 16 conservan su `sha`
intacto → la migración es un MOVE puro, no un re-escrito (propiedad verificable).

## Decisiones de alcance (lo que NO se toca, a propósito)
- **Historia inmutable INTACTA** (CLAUDE.md: no churnear `decisions/`/`LOG`): `decisions/015` (1 mención
  `work/FSK-S10-…`) y las entradas viejas de `LOG.md` se DEJAN — el path `docs/work/` era literalmente cierto
  cuando se escribieron; reescribirlas rompería sus sha-stamps y la semántica append/inmutable. Son historia.
- **Punteros vivos SÍ se actualizan**: `GOVERNANCE-LAYERING` (autoridad §2), meta `STATE` (bullet ADR-016),
  `ROADMAP` (nota-cabecera en el bloque histórico FSK, single-source — NO churn por-línea de 13 menciones).
- **Los 16 docs migrados NO se editan** (move puro byte-idéntico). Sus menciones internas `work/FSK-S…` quedan
  como historia congelada (igual trato que LOG/decisions).
- **Ningún functional link** a estos docs vive en `START-HERE.md`/`docs/STATE.md` (los 2 que escanea el diente
  de links colgantes) → el move no rompe ese check. Verificado por grep.
- **Frescura por-home**: al sumar 16 docs al home de fábrica, su `STATE.md` debe committearse en el MISMO
  commit (mismo `%ct` ⇒ no «más viejo que») o el diente de frescura por-home se pone rojo. Se toca + commitea.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `git mv` los 16 `FSK-S0..S15-INCREMENT.md` → `factories/full-stack-kotlin/docs/work/` (byte-idéntico) | ✅ |
| 2 | Punteros vivos: GOVERNANCE §2/§7 + meta STATE + ROADMAP nota-cabecera + meta LOG (append) | ✅ |
| 3 | Home de fábrica: factory STATE (bullet + frescura) + factory LOG (append) | ✅ |
| 4 | `meta doc-sync` (regen INDEX, re-sella editados; los 16 conservan sha) + `meta check` 14/14 + pytest | ✅ |
| 5 | Diente: tamper un doc migrado → sello del home de fábrica ROJO aislado → revert verde | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. Los 16 `FSK-S0..S15-INCREMENT.md` viven en `factories/full-stack-kotlin/docs/work/`; CERO `FSK-S*` bajo
   `docs/work/` del meta; sus `sha` de sello idénticos a antes del move (MOVE puro probado).
2. INDEX.md (meta) ya NO lista los 16; el `doc_set` meta los excluye; el home de fábrica los sella+chequea.
3. `meta check` 14/14 (integridad + frescura POR-HOME verdes en meta y fábrica) + `pytest tests/` verde.
4. Diente VIVO: editar un doc migrado SIN re-sellar → `meta check` cae (sello rancio en el home de fábrica),
   AISLADO (no afecta el sello meta); re-sync → verde.
5. GOVERNANCE-LAYERING §2/§7 marca §2 ✅; STATE/LOG narran la migración; `git diff` sin residuo no-commiteado.

## Evidencia (re-derivable, por bloqueo)
- **MOVE puro probado:** los 16 `FSK-S0..S15` ahora en `factories/full-stack-kotlin/docs/work/` (0 leftovers en
  `docs/work/` del meta); git los trackea como **16 renames (R)**, no delete+add. Los `sha` de sello pre==post
  move (capturados en el run de migración; p.ej. `FSK-S0` = `a3e3aacb…` antes y después) → el sello es
  content-only, el move no toca el cuerpo.
- **`doc_set`/INDEX:** `grep 'docs/work/FSK-S' INDEX.md` = **0** filas (salieron del set meta); INDEX regenerado
  por `doc-sync` (`0 re-stamped` — el hook `doc_stamp` ya había sellado cada edit; los 16 conservan su sello).
- **`meta check` 14/14** (`docs ok` incluye integridad + frescura POR-HOME en meta y fábrica; `column_parity ok`)
  · `pytest tests/test_docs_manifest.py tests/test_isolation.py` **29 passed** · suite completa verde (`suite ok`).
- **Diente VIVO (dos lados + aislado):** tamper del cuerpo de un doc migrado por shell (sin pasar por Edit → sin
  re-sello del hook) → `factories/full-stack-kotlin/docs/work/FSK-S0-…md:1: stale seal` y **CERO docs del meta
  flageados** → `meta check` **FAIL 1/14 (exit 1)**; `git checkout --` (revert del move staged) → `docs check: 0
  problem(s)`, sello restaurado a `a3e3aacb…`. La frescura y la integridad muerden EN el home de fábrica sin
  acoplar al meta (cierra el sentido de P4 + prueba §3 sobre datos reales).
- **Footprint docs-only:** `git status` en `src/ seed/ stations/ template/` = **0**; cambios = 16 renames + 7
  punteros (`INDEX`, meta `LOG`/`STATE`, `GOVERNANCE`, `ROADMAP`, factory `LOG`/`STATE`) + este doc. `ci
  --rederive` **N/A** (ningún archivo de línea-de-producto tocado; `column_parity ok` lo confirma).
- **Disciplina:** historia inmutable sin churnear — `decisions/015` (1 mención `work/FSK-S10-…`) y entradas
  viejas de `LOG` intactas (el path era cierto al escribirlas). Los 16 docs migrados sin editar (move puro).
