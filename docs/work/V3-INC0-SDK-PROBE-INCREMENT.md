<!-- meta:doc sha=e9e6ec07c1a43d226bb35ece49227bddb2f8baf1 updated=2026-07-28T16:28Z -->
# Incremento V3-INC0-SDK-PROBE

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-28T16:27Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> Autoridad: `ADR-031` (Approved 2026-07-28) · spec `docs/spec/10-target-sdk.md §11` + `11-build-plan.md`
> · nodos `N-0012` (padre) + `N-0064`…`N-0066`. Nivel: meta. Ubicación del código: `v3/` (ADR-031 §2).

## Objetivo

Convertir las ocho preguntas abiertas del SDK en DATOS re-verificables (`v3/sdk_facts.json`) y pinear
la tabla de símbolos, de modo que INC-2 se diseñe contra una API medida y no contra una recordada.

## Contexto: por qué INC-0 existe

`10-target-sdk.md` fue escrito leyendo el wheel `claude-agent-sdk` 0.2.128 el 2026-07-27. Ese wheel
**ya no está en disco** (búsqueda del 2026-07-28: sin resultados). Es decir: hoy toda la arquitectura
objetivo descansa en símbolos citados de una lectura que no se puede repetir sin volver a instalar.
Ése es exactamente el riesgo que §11.5 nombra («la API se mueve bajo nuestros pies») y por eso este
incremento va primero.

## Primer contacto — medido 2026-07-28, antes de escribir código

| # | Pregunta | Resultado | Cómo se midió |
| --- | --- | --- | --- |
| — | ¿La CLI instalada coincide con el pin de la spec? | **Sí, exacto**: `2.1.220 (Claude Code)` | `claude --version` |
| — | ¿El SDK 0.2.128 instala en este entorno? | **Sí** (Python 3.14, pip 26.0.1) | `pip install claude-agent-sdk==0.2.128` |
| — | ¿Sobreviven los símbolos que la spec cita? | **Sí, 9/9 presentes**, 145 exports | `ClaudeAgentOptions · AgentDefinition · HookMatcher · tool · create_sdk_mcp_server · ClaudeSDKClient · query · PermissionResultDeny · SdkPluginConfig` |
| Q8 | ¿Hace falta un OAuth aparte, o se hereda el de la CLI? | **Se hereda**: `~/.claude/.credentials.json` (600) existe y basta; NO hay `ANTHROPIC_API_KEY` en el entorno y aun así responde | ver fila siguiente |
| — | ¿La CLI ANIDA dentro de una sesión de Claude Code? | **Sí**, exit 0 | `claude -p "…" --model haiku` ejecutado desde dentro de esta sesión → `NESTED_OK` |

**Consecuencia para el desarrollo:** v3 se puede construir y probar desde esta misma sesión de Claude
Code, sin credenciales nuevas y sin salir del entorno. Q8 queda contestada para la CLI; falta
confirmarla para el **cliente Python** (que lanza la CLI como subproceso, así que se espera lo mismo —
pero esperado ≠ medido, y el nodo sigue abierto hasta que haya un `ResultMessage` real).

## Fases

| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `v3/` nace: layout mínimo (§10.2), README que dice qué es y qué NO es, y el diente de frontera de importación (`N-0066`) | ⏳ |
| 2 | Sonda ejecutable `v3/probe/` que contesta las 8 preguntas y escribe `v3/sdk_facts.json` (DATOS, no prosa) | ⏳ |
| 3 | Test de tabla de símbolos: falla RUIDOSAMENTE si cualquier símbolo citado por §10 se movió | ⏳ |
| 4 | Q7 (`N-0064`), la pregunta que decide el gate de INC-2: ¿un `deny` de un callback deniega de verdad, de forma no evitable desde dentro de la sesión? | ⏳ |

## Criterio de cierre (demostrable, no narrable)

1. `v3/sdk_facts.json` existe, está commiteado, y contiene las **8** respuestas como datos tipados
   (no prosa), cada una con el comando que la produjo.
2. El test de tabla de símbolos corre y **pasa**; sabotearlo (renombrar un símbolo esperado) lo pone
   **rojo** — dos lados, según I-1.
3. El diente de frontera de importación corre y pasa: ningún módulo bajo `v3/` importa `metafactory`,
   ningún `sys.path` apunta a `src/`. Sabotearlo (añadir el import) lo pone rojo.
4. Q7 contestada con evidencia ejecutable, no con una lectura del código del SDK.
5. `git status` limpio y `meta check` sin regresiones respecto al estado de apertura (5 rojos
   pre-existentes: `docs`(FSK, N-0063) · `evidence_liveness` · `codegen_freeze` · `state_snapshot` ·
   `suite`). **Este incremento no debe añadir un sexto.**

## Fuera de alcance (explícito)

- Portar el kernel — es INC-1, y su oráculo es `oracle_ref` (`N-0067`).
- Escribir el host — es INC-2, el go/no-go (`N-0068`).
- Mejorar cualquier cosa de v2: `11-build-plan.md §5` lo prohíbe hasta el cutover, con las dos
  excepciones ya autorizadas (ADR-031 A3).
