<!-- meta:doc sha=8e578e79b942e1d48ba52b3a8e7a5fa46d6fd1af updated=2026-07-09T01:24Z -->
# Incremento S6-INSTANCE-PIN-GITIGNORE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-09T01:23Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
El `.gitignore` raíz asume que TODA instancia de producto FSK deja `s6` diferido (`activation:off`,
"keyless") y por eso ignora `factories/*/products/*/domain_gen/` entero. `snipeit` ahora lo ADOPTA
durablemente (`SNIPEIT-MIN-COMPLIANCE`) — el artefacto LLM ACEPTADO (`Summary.kt`) debe PINEARSE
(committeado = fuente, patrón ADR-013/MAT-2, igual que el `domain_gen/` de la fábrica-raíz ya trackeado)
para que `ci --rederive` en clon limpio lo verifique SIN invocar `claude -p` de nuevo (la CI es keyless).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Excepción puntual en `.gitignore` (negación acotada a `products/snipeit/domain_gen/`, no genérica) + ignorar explícitamente `.kotlin/` (cache transitorio del compilador, no cubierto antes). | ⏳ |
| 2 | Verificar con `git status`/`git check-ignore` que SÓLO el árbol fuente (`*.kts`, `src/**/*.kt`, `gradlew`+wrapper) queda trackeable y `.gradle/`/`build/`/`.kotlin/` transitorios de `domain_gen/` siguen ignorados. | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `git check-ignore -v factories/full-stack-kotlin/products/snipeit/domain_gen/src/main/kotlin/domain/Summary.kt` → NO matchea (trackeable).
2. `git check-ignore -v factories/full-stack-kotlin/products/snipeit/domain_gen/.gradle/x` (o `build/`, `.kotlin/`) → SIGUE matcheando (ignorado).
3. `git add -n factories/full-stack-kotlin/products/snipeit/domain_gen/` lista sólo fuente (sin `.gradle`/`build`/`.kotlin`).
4. Árbol limpio + estación activa verde (gate de cierre del incremento).
