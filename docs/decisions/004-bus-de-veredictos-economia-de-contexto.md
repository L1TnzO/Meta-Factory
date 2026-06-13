<!-- meta:doc sha=e5057bb6eec78899d9dab146ee5115337a34c533 updated=2026-06-13T14:57Z -->
# ADR-004 — Bus de veredictos y economía de contexto del orquestador

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-13T02:17Z |
| Referencia | ASF/ADR-020 + CONTEXT-INCREMENT (origen), reference/CONTEXT-ECONOMY.md, ASF-LESSONS §G-3/G-4 |

## Contexto

Dolor explícito del ingeniero: el orquestador ejecuta comandos y lee outputs de tests que
consumen el contexto, lo encarecen cada turno y degradan sus decisiones. ASF lo resolvió
parcialmente (`factory check`, veredicto ≤10 líneas) pero el patrón no era universal y la
delegación —la otra mitad de la economía— quedó como disciplina que el orquestador rara vez
ejercía (Opus casi nunca delegaba a Sonnet).

## Decisión

**1. Bus de veredictos universal (I-7).** Toda operación cara (check/verify/gate/trace/rtm/ci/
build/lint/type-check), del Meta-Factory y de cada fábrica producida, devuelve un veredicto
acotado (`status/summary/counts/fallos≤N/artefacto/próximo`); el log completo va al disco
(gitignored), nunca al contexto. Revelación progresiva ante rojo: veredicto → triage (haiku) →
slice quirúrgico. El camino barato es el DEFAULT ergonómico; no se hookea pytest a pelo (castiga
al writer).

**2. Delegación como default, no disciplina.** El contrato de delegación cuesta ~0 líneas (vive en
el agent); el bus hace que verificar a un subagente sea ≤N líneas; el enrutamiento de modelo es un
lookup. NO delegar deja de ser lo barato. Se sigue MIDIENDO (contador de delegaciones del journal),
no forzando.

**3. Enrutamiento de modelo como dato (cierra G-4/W4).** Una tabla versionada mapea clase-de-trabajo
→ agent+modelo (trust-chain→reviewer/opus; bulk→writer/sonnet; log→triage/haiku; decisión→
orquestador). El orquestador lee la tabla y lanza `Agent(model=…)`. La sombra determinista es el
contador + la regla trust-chain ("el orquestador lee ese diff con sus ojos") como red de seguridad.

## Consecuencias

- El presupuesto de `CLAUDE.md` (siempre-residente) es un número en la factory-spec, medible en el diff.
- La unidad de economía son **tokens residentes**, no totales (ASF/ADR-020).
- Rechazado: forzar delegación con hard-block (teatro, ASF/ADR-023); truncado ciego de logs
  (esconde señal — la escalera de revelación lo reemplaza).
