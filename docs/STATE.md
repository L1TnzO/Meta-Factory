<!-- meta:doc sha=2747ee12e632f69f0eb496738306e3af18018e73 updated=2026-06-13T20:18Z -->
# Estado — Meta-Factory
> tipo: estado · actualizado: 2026-06-13T15:14Z · sesión: opus-4.8 (bootstrap ejecutado) · presupuesto: ≤80 líneas
> Este doc APUNTA; la verdad verificable VIVE en artefactos (`.proof/`, ledger, RTM re-derivado, INDEX, logs).
> Esquema: heredado de ASF/decisions/021. Punto de entrada único: si tenés amnesia, empezá acá.

<!-- meta:projection (generado de hechos; NO editar a mano, se refresca con `meta checkpoint`) -->
> Proyección de hechos (Tier 0 → STATE). Fuente: artefactos re-derivables; no es narrativa.
- Incremento abierto: MEMORY-INCREMENT.md
- RTM por fábrica (re-derivado de `.proof/`): dummy: COMPLETE (1/1)
<!-- /meta:projection -->

## Ahora — qué es verdad hoy
- **Fase: BOOTSTRAP EJECUTADO. Ya hay CÓDIGO y está verificado POR BLOQUEO.** El punto fijo dejó de ser
  aspiración (`reference/VISION.md §3`): la línea M0–M8 construye un dummy-fábrica e2e y la columna
  anti-sello bloquea de verdad (no por prosa). El Meta-Factory sigue siendo "un Claude Code con
  superpoderes para construir fábricas", ahora con la maquinaria mínima cableada y demostrada.
- **Construido (F1–F4 de `work/BOOTSTRAP-INCREMENT.md`, ✅)**:
  - `seed/` (Stage 0, trust-chain, hecho a mano): `verifier.py` (200 líneas stdlib, ÚNICO escritor de
    veredictos; `passed` solo desde exit codes reales), `column.md` (3 cerrojos), `external_ci.yml`.
  - `src/metafactory/` (Stage 1): engine dominio-agnóstico (station/sequence/gate/runner; estaciones
    como dato I-2), spec (modelo/loader/validator + `factory.schema.json`, espina SDD), verify (bus de
    veredictos I-7 + checks), codegen (render del chasis), `cli.py` (`meta check/new/station/product-run/rtm/ci/pin/verify`).
  - `stations/m00–m03+m08.yml` (meta-estaciones como dato), `template/factory/` (chasis heredable),
    columna `.claude/hooks/` (proof_protect·gate_guard·stop_proof·commit_guard·doc_stamp) + `settings.json`.
  - `factories/dummy/` (PRODUCIDO por la línea) desde `specs/dummy.factory.spec.yml`.
  - ADR-009 vivo: sello in-band en cada `.md` + `INDEX.md` generado + check de consistencia en `meta check`.
- **Verificado (8 criterios, output REAL en `work/BOOTSTRAP §Evidencia`)**: `meta check` verde (≤10 líneas,
  log al disco) y rojo con `file:line`; e2e M0–M8 con 5 gates + RTM `COMPLETE` re-derivado de artefactos;
  capstone (3 cerrojos bloquean); M8 negativo; re-derivación en clon limpio (proof_sha == pineado;
  corrompido → ≠ → rojo); aislamiento PF-6; **seed auditado por reviewer opus de contexto fresco: 0 CRITICAL**
  (2 HIGH arreglados, 1 MEDIUM by-design). Suite: **137 tests verdes**.
- **9 ADR** sin cambio de estado (001–006+009 Aprobados; 007–008 Propuestos). El código implementa el diseño.

## Agujeros honestos (ahora de implementación, no solo de diseño)
- **M4–M7 NO construidos**: template de producto completo + frontera generado/dominio (M4), memoria+RTM
  completos + métricas (M5), dos-verificadores como workflow corriendo en CI real (M6), harness completo
  de la fábrica (M7). El bootstrap acotó deliberadamente a M0–M3+M8.
- **Métricas gratis (ADR-008) y memoria T2 (ADR-007, índice semántico) NO implementadas** — siguen Propuestas.
- **Trusting-trust PARCIAL**: la re-derivación atrapa custodia comprometida; NO un compromiso de la FUENTE
  de `verifier.py` (eso lo atrapa el review R3 del diff, no un verificador diverso). Residual honesto declarado.
- **ASF NO regenerado** (ADR-006, diferido): sigue CONGELADO como referencia de cosecha y paridad — NO tocado.
- **Hooks: los 5 VERIFICADOS EN VIVO tras reiniciar** (sesión 2): `doc_stamp` auto-sella + regenera
  INDEX, `proof_protect`/`permissions` deniegan `.proof/`, `gate_guard`/`commit_guard`/`stop_proof`
  bloquean por exit code. En la sesión de CONSTRUCCIÓN no estaban activos (escritos a mitad) — de ahí
  la doc discrecional. Detalle: `reference/HONEST-STATE.md §2`. G-8 (cascada): probado contra UNA fábrica.
- **Disciplina de proceso fallada (honesto)**: documenté al CIERRE, no incremental; 0 commits durante
  la construcción → sin evidencia-por-requisito en vivo. Es G-M1/G-3 en vivo. Detalle: `reference/HONEST-STATE.md`.

## Siguiente — en orden
1. Regenerar ASF como producto (ADR-006): factory-spec de ASF (Half A = sus opiniones), correr M0–M8, paridad.
2. Completar M4–M7 (el sustrato que el dummy aún no ejerció: frontera generado/dominio, RTM/memoria completos,
   CI externo como workflow real, harness completo).
3. Ratificar ADR-007/008 → métricas gratis (M5) + índice de recuperación medido.
4. Segunda fábrica (Full-Stack) para forzar la parametrización real del sustrato (G-8).

## Mapa
- Bitácora: `LOG.md` · Decisiones: `decisions/` (001–009) · Trabajo: `work/BOOTSTRAP-INCREMENT.md` (cerrado)
- Referencia: `reference/` · Índice GENERADO: `../INDEX.md` · Arranque: `../START-HERE.md`
- Código: `../seed/` · `../src/metafactory/` · `../template/` · `../factories/dummy/` · CLI: `../meta`
- Fuente cosechada (congelada): `../../Agent_Systems_Factory/`
