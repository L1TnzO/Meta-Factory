<!-- meta:doc sha=aba8c4f2bb49ba13294dd98f286bc2a18c51de10 updated=2026-06-15T13:20Z -->
# Estado — Meta-Factory
> tipo: estado · actualizado: 2026-06-15T13:18Z · sesión: opus-4.8 (Fase A ✅ — A1 gramática v2 + A2 ASF/skeletons; reviewer fresco PASS) · presupuesto: ≤80 líneas
> Este doc APUNTA; la verdad verificable VIVE en artefactos (`.proof/`, ledger, RTM re-derivado, INDEX, logs).
> Esquema: heredado de ASF/decisions/021. Punto de entrada único: si tenés amnesia, empezá acá.

<!-- meta:projection (generado de hechos; NO editar a mano, se refresca con `meta checkpoint`) -->
> Proyección de hechos (Tier 0 → STATE). Fuente: artefactos re-derivables; no es narrativa.
- Incremento abierto: ninguno
- RTM por fábrica (re-derivado de `.proof/`): agent-systems-factory: COMPLETE (1/1) · dummy: COMPLETE (1/1)
<!-- /meta:projection -->

## Ahora — qué es verdad hoy
- **Dirección FIJADA (2026-06-15)**: la Meta-Factory genera el **100%** desde specs, eligiendo tecnología por
  **primitivas** en la planificación SDD (ADR-011/012, `reference/PRIMITIVES.md`); determinismo en verificación,
  no en generación (I-3). Mapa completo y autocontenido de incrementos (fases A–G → ASF-mejorado+Full-Stack+Mobile+IoT): `work/ROADMAP.md`.
- **Fase A ✅ (2026-06-15) — la spec describe y prueba ser generalista**:
  - **A1 (`A1-GRAMMAR-V2`)**: factory-spec v2 en 6 capas (L0–L5) + `validate_grammar_v2` con dientes — M0
    RECHAZA lo deshonesto (cap-sin-proof, tech-sin-primitiva, primitive mal formado, depends_on roto/ciclo,
    verifier fantasma, status/runs_in inválido) **sin nombrar ninguna tech** (ADR-012, probado). 12 negativos bloquean.
  - **A2 (`A2-ASF-SKELETONS`)**: ASF descrito COMPLETO en v2 (`specs/agent-systems-factory…`: 7 caps→DES,
    línea S0–S8 con depends_on/proof_checks, machinery; blueprint `declared-deferred`, DIVERGE del proxy s00
    registrado) + 3 skeletons (`specs/skeletons/{full-stack,mobile,iot}`) de dominios radicalmente distintos.
    Los 4 validan 0 problemas; anti-overfit por test; **reviewer fresco Opus PASS 0 CRITICAL/HIGH**. Suite 310.
  - **Sigue B1** (skill de primitivas de diseño: dado un dominio, mapea DES→tech) — `work/ROADMAP.md §Fase B`.
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
  - `src/metafactory/stations/m00–m06+m08.yml` (meta-estaciones como dato; M4 frontera, M5 memoria, M6 dos verificadores), `template/factory/` (chasis heredable),
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
- **M4–M7 ✅ — `M4-M7-INCREMENT` CERRADO** (6 criterios): los 4 gates LANDED+e2e — M4 `boundary_survives`,
  M5 `rtm_rederive`, M6 `clean_runner` (clon hermético re-deriva y exige el pineado), M7 `agent_shadow`
  (toda sombra de un agent existe/cableada; CLAUDE.md ≤ presupuesto). Línea M0–M8 verde; capstone M8 demostrado.
  DIFERIDO (contenido, no dientes; en §Siguiente): `answers/migración`, captura viva, `pre-push`, `commands/`, columna→template (#5).
- **Subsistema de MEMORIA COMPLETO** (incremento MEMORIA, sesión 2; ADR-007/008 Implementados):
  Tier 0 (journal at-source + métricas/costo), fix de G-M1 (proyección + `meta checkpoint` + check),
  Tier 2 medido (`meta recall`), rehidratación SessionStart. Único diferido a propósito: índice
  semántico (embeddings), **hasta que la medición lo justifique** (`reference/HONEST-STATE.md §3`).
- **Trusting-trust PARCIAL**: la re-derivación atrapa custodia comprometida; NO un compromiso de la FUENTE
  de `verifier.py` (eso lo atrapa el review R3 del diff, no un verificador diverso). Residual honesto declarado.
- **ASF regenerado como CHASIS** (ADR-006; `ASF-REGEN` CERRADO): la línea M0–M8 produjo `factories/agent-systems-factory/`
  (seed byte-idéntico, columna real, RTM `COMPLETE 1/1`, dos-verificadores `proof_sha==pineado`, prueba de bloqueo;
  reviewer fresco 0 CRITICAL). Las opiniones de ASF (LangGraph, 7 capacidades, S0–S8, modos, interrupt) DESCENDIDAS a
  `factory.spec.yml` como DATO; producto = PROXY honesto. El codegen real S0–S8 = **6 hallazgos G-8 DIFERIDOS**
  (`work/ASF-REGEN-INCREMENT.md §Hallazgos`). El ASF congelado (`../../Agent_Systems_Factory/`) NO tocado.
- **Hooks: los 5 VERIFICADOS EN VIVO tras reiniciar** (sesión 2): `doc_stamp` auto-sella + regenera
  INDEX, `proof_protect`/`permissions` deniegan `.proof/`, `gate_guard`/`commit_guard`/`stop_proof`
  bloquean por exit code. En la sesión de CONSTRUCCIÓN no estaban activos (escritos a mitad) — de ahí
  la doc discrecional. Detalle: `reference/HONEST-STATE.md §2`. G-8 (cascada): ahora probado contra DOS fábricas (dummy + agent-systems-factory).
  **6º hook `increment_guard` + cadencia en `gate_guard`/`stop_proof` (ADR-010)**: VERIFICADO EN VIVO — y
  re-ejercitado en ASF-REGEN: `gate_guard` bloqueó avanzar a m05 con chasis sin commitear, `commit_guard`
  rehusó commitear con estación roja → cadencia real por fase (6 commits). Detalle: `reference/HONEST-STATE.md §2`.
  **Residual ACEPTADO (ADR-010 addendum)**: docs `.md` fuera de un incremento NO tienen cadencia de commit
  (proporcionalidad — la rebanada peligrosa ya enforced por `meta check`); mitigación: la regla en `CLAUDE.md`.
- **Disciplina de proceso fallada (honesto)**: documenté al CIERRE, no incremental; 0 commits durante
  la construcción → sin evidencia-por-requisito en vivo. Es G-M1/G-3 en vivo. Detalle: `reference/HONEST-STATE.md`.

## Siguiente — en orden
> **DIRECCIÓN (2026-06-15, mandato del ingeniero)**: la Meta-Factory genera el **100%** (ADR-011) desde
> el spec, eligiendo la tecnología en la **planificación SDD** a partir de **primitivas** (`reference/PRIMITIVES.md`,
> ADR-012), no de herramientas hardcodeadas. Determinismo en la verificación, no en la generación (I-3).
> **Mapa completo y AUTOCONTENIDO de TODOS los incrementos**: `work/ROADMAP.md` — modelo Diseño→Build→Mejora,
> fases A–G, estado final ASF-mejorado + Full-Stack + Mobile + IoT. Lo de abajo es backlog histórico que el ROADMAP subsume.
1. ✅ ASF regenerado como chasis (`ASF-REGEN` CERRADO). FOLLOW-UP G-8 (lo destapado): parametrizar el codegen de producto
   multi-estación (la línea S0–S8 real de ASF) y `seed/external_ci.yml` por-fábrica (hoy defaultea a `--factory dummy`).
2. Follow-ups de M4-M7 (ya CERRADO): harness `commands/`, captura viva journal/métricas en la fábrica,
   `pre-push` mirror, `answers/migración` (re-scaffold determinista). Contenido, no dientes (las gates están).
3. ✅ `proof_protect` over-block afinado (`2061ec6`): la escritura se liga al target; lecturas/menciones/`2>&1` pasan; test nuevo. Cerrojo 1 intacto.
4. Segunda fábrica (Full-Stack) para forzar la parametrización real del sustrato (G-8); índice
   semántico de memoria SOLO cuando la serie `recall` muestre que el lexical no alcanza.
5. **Propagar la disciplina de commit (ADR-010) al `template/factory/harness`**: el núcleo ya está
   Implementado en el harness de la meta-factory (`increment_guard` + cadencia en `gate_guard`/`stop_proof`
   + `meta increment` + surface). Falta hornearlo en el sustrato para que TODA fábrica generada lo herede
   (verificar en el dummy, G-8). Y refinar: ¿gatear también EJECUTAR la línea (`meta station`) sin incremento?

## Mapa
- Bitácora: `LOG.md` · Decisiones: `decisions/` (001–012; **011** 100%-generado, **012** primitivas-no-herramientas) · Trabajo: `work/ROADMAP.md` (mapa vivo) · `work/BOOTSTRAP-INCREMENT.md` (cerrado)
- Referencia: `reference/` (filosofía: `PRIMITIVES.md`) · Índice GENERADO: `../INDEX.md` · Arranque: `../START-HERE.md`
- Código: `../seed/` · `../src/metafactory/` (engine + `stations/` = meta-estaciones M0–M8 como dato) · `../template/` · `../factories/{dummy,agent-systems-factory}/` · CLI: `../meta`
- Fuente cosechada (congelada): `../../Agent_Systems_Factory/` @ `b1fcb1f` (pin: `reference/ASF-PROVENANCE.md`) · auditoría A/B regenerada vs original: `reference/REGEN-AUDIT.md`
