<!-- meta:doc sha=ae73e42d65c49d1571a26c8df07c64c3cb291b1d updated=2026-06-25T21:33Z -->
# Incremento SOTA-REDESIGN-DIRECTION

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-25T21:30Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Cristalizar la dirección del rediseño SOTA en un **ADR-017** + un **roadmap faseado**, dejando un puntero
AUTO-CONTENIDO para que los próximos incrementos sepan QUÉ construir y EN QUÉ ORDEN — sin re-explorar.

## Contexto (por qué este incremento)
Auditoría profunda (6 + 3 subagentes, 2026-06-25, Opus de cerebro + Sonnet/guía leyendo el bulk). Hallazgo
central: **el motor FUNCIONA** (FSK genera apps reales, verificadas contra PG/HTTP/Chromium VIVOS; la
verificación tiene dientes que atraparon bugs reales; 0 reverts en 374 commits) — lo que falta es la **capa
de dirección**: gobierno de alcance (el `declared-deferred` es un escape sin gate), navegación barata, y un
modelo de delegación que no queme Opus-xhigh en todo. Snipe-IT fue un benchmark demasiado duro (17 ADOPT
para un producto) → pasa a regresión, no a punto de partida. El estado del arte **colapsa** los hilos
(navegación · delegación barata · handoff · calidad · costo) en **un solo artefacto**: un grafo de
conocimiento del proyecto, content-addressed. Detalle completo + fuentes en §Punteros.

## La dirección (resumen auto-contenido — sobrevive sin la memoria)
- **Grafo-columna.** Un solo grafo consultable: nodos `File·Symbol·Requirement·Decision(ADR)·Station·Spec·Proof`;
  aristas `DEFINED_IN·CALLS·IMPORTS·IMPLEMENTS·VERIFIES·GOVERNS·SUPERSEDES·GENERATES·SATISFIES`. Build con
  tree-sitter (py/kt/ts/go) + PageRank (repo-map ~1k tokens) + SCIP para refs precisas; **incremental por hash
  (extiende los sha-stamps de ADR-009; Merkle-DAG)**. Ya tenemos RTM + ADR + `.proof/` como grafos → arrancamos
  ADELANTE (el error #1 del SOTA es "grafo sólo-código"; Cursor/Aider/Cody lo son). El grafo **ES** la navegación,
  **ES** el contrato de delegación, **ES** el handoff y **ES** el alcance de verificación — la misma pieza.
- **Verificar-no-revisar** (cómo delegar generación barata y segura): contrato-primero (el type-checker es el
  revisor) → subagente `generator` Sonnet con `Write` ACOTADO por hook (blast-radius enforzado por la máquina)
  → se auto-verifica (typecheck·compile·tests·**PBT**·static) → devuelve un **veredicto** estructurado, NO el
  código (vía `context:fork`) → Opus lee el veredicto, no el código; escala a Opus SÓLO en paths de seguridad
  o rojo persistente. PBT es el upgrade clave (expone 30-32% de bugs que los tests por-ejemplo no ven).
- **Routing de modelos como DATO** (ya es valor declarado, VISION §4, nunca operacionalizado): Opus = cerebro
  (diseña/decide/revisa-residuo, contexto chico) · Sonnet = genera · Haiku = lee. Agentes rigurosos en
  `.claude/agents` (scope `use_when`/`do_not_use_when` + tools de mínimo privilegio + contrato verificable), no por vibes.
- **Calibración honesta:** no es "nunca revisar" — confiar en el gate para el grueso y gastar ojos de Opus SÓLO
  en el residuo irreducible (seguridad, arquitectura nueva sin cobertura, rojo que persiste).

## Roadmap faseado (lo que sigue — los PRÓXIMOS incrementos)
| Fase | Incremento (slug propuesto) | Qué deja TERMINADO |
| --- | --- | --- |
| **0 (ESTE)** | `SOTA-REDESIGN-DIRECTION` | ADR-017 + roadmap fijados; dirección consultable y auto-contenida |
| 1 | `GRAPH-SPINE-KEYSTONE` | grafo mínimo (tree-sitter+PageRank+RTM/ADR/proof, sha-incremental) **+ gate de tamaño/acoplamiento determinista, dogfoodeado en el sustrato** (el monolito = rojo) + billing-ledger por corrida/estación. Construido delegando el bulk a Sonnet (prueba el modelo de costos) |
| 2 | `DELEGATION-HARNESS` | agentes orchestrator/generator/verifier/reviewer + skill `generate-slot` (`context:fork`) + hooks (blast-radius, verdict, handoff) + tipo de gate **PBT** + gates de seguridad/supply-chain generalizados + gate al `declared-deferred` (trigger/fecha) |
| 3 | `MONOLITH-REFACTOR` | el gate de Fase 1 FUERZA partir `scaffold_product.py` (corte de templates → split framework/glue), por slots acotados que Sonnet puede tomar |
| 4 | `REAIM-SWEET-SPOT` | benchmark del 80% CRUD (5-8 entidades; Snipe-IT → regresión) + dial borrador→endurecer + cosecha del vocabulario `AgentSpec`/`WorkOrder` de PWF |
| *dif.* | `LEAST-PRIV-DECOUPLE` | desacople "cp-harness" least-privilege (ADR-016 Fase 2), natural recién post-grafo + post-quality-gates |

## Fases (de ESTE incremento)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Escribir `docs/decisions/017-*.md` (ADR: grafo-columna + verificar-no-revisar + routing de modelos como dato) | ⏳ |
| 2 | Registrar el roadmap faseado en `docs/work/ROADMAP.md` + nota «Siguiente» concisa en STATE | ⏳ |
| 3 | Ratificar "inglés de acá en adelante" en CLAUDE.md (sustrato vivo; NO churnear historia inmutable) | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `docs/decisions/017-*.md` existe (Estado: Aceptado) y fija la arquitectura SIN volver obligatoria una tech (ADR-012).
2. El roadmap faseado (Fases 0-4 + diferido) queda en `docs/work/ROADMAP.md`; los próximos incrementos quedan nombrados.
3. `meta check` 6/6 (doc-only: no regresiona el sustrato).

## Punteros (documentación de respaldo — el detalle completo)
- **Memoria de sesión Claude Code** (diagnóstico + diseño + fuentes SOTA): `honest-reassessment-2026-06-25` ·
  `target-operating-model-sota` · `sota-redesign-graph-spine`.
- **Repo:** `docs/STATE.md` · `docs/reference/VISION.md` (§5.2: la corrección semántica es humana) ·
  `docs/reference/CONTEXT-ECONOMY.md` · ADR-007 (memoria) · ADR-009 (sha-stamps) · ADR-012 (tech = plan) ·
  ADR-016 (layering por nivel) · `docs/work/ROADMAP.md`.
- **Fuentes SOTA clave:** repo-map de Aider (tree-sitter+PageRank) · SCIP (scip-code.org) · RepoGraph (ICLR 2025) ·
  PBT para codegen (arXiv 2506.18315) · Anthropic "Building Effective Agents".
