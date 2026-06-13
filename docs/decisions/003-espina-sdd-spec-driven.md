<!-- meta:doc sha=3712dcc63fef206f1fe3602da2dd26f586188925 updated=2026-06-13T14:57Z -->
# ADR-003 — Espina SDD (Spec-Driven Development) de primera clase, enforced

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-13T02:17Z |
| Referencia | reference/ASF-LESSONS.md §G-5, reference/ARCHITECTURE.md §5 (factory-spec), §6 (M0) |

## Contexto

El ingeniero señaló que ASF "podría faltar cosas formales de ingeniería como SDD". ASF tiene S0 +
spec.yml + RTM —*casi* SDD— pero no enmarcado como un ciclo disciplinado spec→plan→tareas→
verificación con una fuente única de verdad. El estado del arte (spec-kit/Kiro/Tessl, ~2026)
formaliza SDD pero lo enforce con prompts; ASF demostró que el enforcement determinista (una
compuerta que corta) es estrictamente más fuerte.

## Decisión

**El Meta-Factory adopta una espina SDD de primera clase, enforced deterministamente:**

- La **factory-spec** (machine-readable + prosa, esquema definido por el Meta-Factory) es la
  fuente única de verdad de qué es una fábrica.
- Todo **requisito** tiene id estable (`REQ-F-NNN`) y `satisfied_by` no vacío que mapea a una
  estación ACTIVA. **M0 rehúsa** specs sin requisitos o con cross-refs inválidas (estación
  inexistente/desactivada/ids duplicados). Sin requisitos declarados, no hay línea.
- El **plan** (arquitectura/decisiones) es derivado y revisable; las **tareas** son las estaciones.
- La **verificación** re-deriva el RTM de artefactos SOLAMENTE (cero narrativa):
  SATISFIED / PROVISIONAL (con acción requerida) / UNSATISFIED (corta el CI). I-10.

## Consecuencias

- "Está listo, nivel producción" es **inafirmable** mientras el RTM no sea COMPLETE — la honestidad
  se vuelve un veredicto, no una promesa (heredado de ASF/HONEST-STATE).
- La diferencia con SDD-por-prompt: el incumplimiento de la espina **corta una compuerta**, no
  genera una sugerencia. M0 es el equivalente del S0 de ASF, un nivel arriba.
- Rechazado: SDD como guía narrativa en CLAUDE.md — sin sombra determinista se saltea (ADR-023).
