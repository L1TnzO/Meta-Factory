<!-- meta:doc sha=1d48e145312d4ee9cc4e18209e45e3730abe7171 updated=2026-06-14T01:57Z -->
# Estado — Meta-Factory
> tipo: estado · actualizado: 2026-06-13T15:14Z · sesión: opus-4.8 (bootstrap ejecutado) · presupuesto: ≤80 líneas
> Este doc APUNTA; la verdad verificable VIVE en artefactos (`.proof/`, ledger, RTM re-derivado, INDEX, logs).
> Esquema: heredado de ASF/decisions/021. Punto de entrada único: si tenés amnesia, empezá acá.

<!-- meta:projection (generado de hechos; NO editar a mano, se refresca con `meta checkpoint`) -->
> Proyección de hechos (Tier 0 → STATE). Fuente: artefactos re-derivables; no es narrativa.
- Incremento abierto: ninguno
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
  - `src/metafactory/stations/m00–m03+m08.yml` (meta-estaciones como dato), `template/factory/` (chasis heredable),
    columna `.claude/hooks/` (proof_protect·gate_guard·stop_proof·commit_guard·doc_stamp) + `settings.json`.
  - `factories/dummy/` (PRODUCIDO por la línea) desde `specs/dummy.factory.spec.yml`.
  - ADR-009 vivo: sello in-band en cada `.md` + `INDEX.md` generado + check de consistencia en `meta check`.
- **Verificado (8 criterios, output REAL en `work/BOOTSTRAP §Evidencia`)**: `meta check` verde (≤10 líneas,
  log al disco) y rojo con `file:line`; e2e M0–M8 con 5 gates + RTM `COMPLETE` re-derivado de artefactos;
  capstone (3 cerrojos bloquean); M8 negativo; re-derivación en clon limpio (proof_sha == pineado;
  corrompido → ≠ → rojo); aislamiento PF-6; **seed auditado por reviewer opus de contexto fresco: 0 CRITICAL**
  (2 HIGH arreglados, 1 MEDIUM by-design). Suite: **137 tests verdes**.
- **10 ADR**: 001–006+009 Aprobados; **007–008** Aprobados + Implementados (MEMORIA, s2); **010 Aprobado +
  Implementado** (disciplina de commit: todo código en un incremento + cadencia por fase, esta sesión).

## Agujeros honestos (ahora de implementación, no solo de diseño)
- **M4–M7 NO construidos**: template de producto completo + frontera generado/dominio (M4), memoria+RTM
  completos + métricas (M5), dos-verificadores como workflow corriendo en CI real (M6), harness completo
  de la fábrica (M7). El bootstrap acotó deliberadamente a M0–M3+M8.
- **Subsistema de MEMORIA COMPLETO** (incremento MEMORIA, sesión 2; ADR-007/008 Implementados):
  Tier 0 (journal at-source + métricas/costo), fix de G-M1 (proyección + `meta checkpoint` + check),
  Tier 2 medido (`meta recall`), rehidratación SessionStart. Único diferido a propósito: índice
  semántico (embeddings), **hasta que la medición lo justifique** (`reference/HONEST-STATE.md §3`).
- **Trusting-trust PARCIAL**: la re-derivación atrapa custodia comprometida; NO un compromiso de la FUENTE
  de `verifier.py` (eso lo atrapa el review R3 del diff, no un verificador diverso). Residual honesto declarado.
- **ASF NO regenerado** (ADR-006, diferido): sigue CONGELADO como referencia de cosecha y paridad — NO tocado.
- **Hooks: los 5 VERIFICADOS EN VIVO tras reiniciar** (sesión 2): `doc_stamp` auto-sella + regenera
  INDEX, `proof_protect`/`permissions` deniegan `.proof/`, `gate_guard`/`commit_guard`/`stop_proof`
  bloquean por exit code. En la sesión de CONSTRUCCIÓN no estaban activos (escritos a mitad) — de ahí
  la doc discrecional. Detalle: `reference/HONEST-STATE.md §2`. G-8 (cascada): probado contra UNA fábrica.
  **6º hook `increment_guard` + cadencia en `gate_guard`/`stop_proof` (ADR-010)**: VERIFICADO EN VIVO
  (sesión nueva, 2026-06-14): sin incremento abierto, `Write` de un `.py` → DENEGADO por el harness con
  el mensaje ADR-010; `.md` y fuera-del-repo permitidos; árbol limpio antes/después (sin fuga del scratch).
  Cierra el patrón "escrito pero no cargado hasta el arranque" de la s2. `gate_guard` ya había bloqueado
  avance con deuda EN VIVO en la sesión de construcción.
  **Residual ACEPTADO (ADR-010 addendum)**: docs `.md` fuera de un incremento NO tienen cadencia de commit
  (`dirty_code` excluye `.md`); NO se endurece, por proporcionalidad — daño chico, la rebanada peligrosa
  (proyección de STATE) ya enforced por `meta check`, y un nag por cada `.md` sería ruido que erosiona los
  dientes reales. Mitigación no-máquina, sin ruido: la regla de commit en `CLAUDE.md` (override del default).
- **Disciplina de proceso fallada (honesto)**: documenté al CIERRE, no incremental; 0 commits durante
  la construcción → sin evidencia-por-requisito en vivo. Es G-M1/G-3 en vivo. Detalle: `reference/HONEST-STATE.md`.

## Siguiente — en orden
1. Regenerar ASF como producto (ADR-006): factory-spec de ASF (Half A = sus opiniones), correr M0–M8, paridad.
2. Completar M4–M7 (el sustrato que el dummy aún no ejerció: frontera generado/dominio, RTM/memoria completos,
   CI externo como workflow real, harness completo).
3. Afinar el `proof_protect` over-block (denylist `.proof/` + `>`) — finding de la sesión 2.
4. Segunda fábrica (Full-Stack) para forzar la parametrización real del sustrato (G-8); índice
   semántico de memoria SOLO cuando la serie `recall` muestre que el lexical no alcanza.
5. **Propagar la disciplina de commit (ADR-010) al `template/factory/harness`**: el núcleo ya está
   Implementado en el harness de la meta-factory (`increment_guard` + cadencia en `gate_guard`/`stop_proof`
   + `meta increment` + surface). Falta hornearlo en el sustrato para que TODA fábrica generada lo herede
   (verificar en el dummy, G-8). Y refinar: ¿gatear también EJECUTAR la línea (`meta station`) sin incremento?

## Mapa
- Bitácora: `LOG.md` · Decisiones: `decisions/` (001–009) · Trabajo: `work/BOOTSTRAP-INCREMENT.md` (cerrado)
- Referencia: `reference/` · Índice GENERADO: `../INDEX.md` · Arranque: `../START-HERE.md`
- Código: `../seed/` · `../src/metafactory/` (engine + `stations/` = meta-estaciones M0–M8 como dato) · `../template/` · `../factories/dummy/` · CLI: `../meta`
- Fuente cosechada (congelada): `../../Agent_Systems_Factory/`
