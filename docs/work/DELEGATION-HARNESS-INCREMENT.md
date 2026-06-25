<!-- meta:doc sha=a04e6f37542e47dd277ecb0ae9b16a9b351cd918 updated=2026-06-25T23:11Z -->
# Incremento DELEGATION-HARNESS

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-25T23:10Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> Autoridad del PLAN: **ADR-017** (§2 verificar-no-revisar · §3 routing como dato · §4 gates de calidad).

## Objetivo
Construir la **Fase 2 SOTA completa**: el **arnés de delegación "verificar-no-revisar"** (agents/skills/hooks de
`.claude/`, con dientes de máquina) + tres **tipos de gate nuevos** (PBT · seguridad/supply-chain heredable ·
`declared-deferred` con trigger/fecha + outcome por-incremento) — de modo que delegar generación a Sonnet sea
**barato Y seguro** (Opus lee veredictos, no código) y que "terminado" y "valió la pena" sean **decidibles**.

## Por qué (contexto auto-contenido — sobrevive sin la memoria ni la sesión previa)
ADR-017 halló que el motor FUNCIONA pero falta la capa de DIRECCIÓN: (a) no hay forma de delegar GENERACIÓN sin
que Opus relea cada línea (la delegación no ahorra), (b) el `declared-deferred` es un escape SIN gate, (c) no hay
outcome por-incremento. La Fase 1 (`GRAPH-SPINE-KEYSTONE`) dejó el grafo-columna + el gate `quality` + el
billing-ledger. Esta fase FORMALIZA el patrón que la Fase 1 ejerció a mano (delegar 2 módulos a Sonnet, verificar
por bloqueo): lo vuelve **maquinaria de la columna** con dientes deterministas.

## Mecánica del harness verificada (Claude Code 2.1.193 — autoridad: docs oficiales, no supuestos)
- **Hooks por-agente en frontmatter** (`.claude/agents/*.md`): corren SÓLO mientras ese subagente está activo y se
  limpian al terminar. Un `Stop` en frontmatter se auto-convierte a `SubagentStop`. ⇒ el hook de blast-radius y el
  de veredicto viven DENTRO del `generator`, **nunca globales** → cero riesgo a esta sesión ni a los Explore.
- **Input de hook trae `agent_id` + `agent_type`** (= `name` del frontmatter) → self-scoping si hiciera falta.
- **Subagente con nombre** = contexto fresco, devuelve SÓLO su mensaje final → aislamiento más fuerte que un fork
  (el código generado se queda en el contexto del worker; al padre vuelve sólo el VEREDICTO).
- **Frontmatter**: `name`/`description`/`tools`/`disallowedTools`/`model`(sonnet|haiku|opus)/`hooks`/`maxTurns`/
  `permissionMode`. `exit 2`: PreToolUse bloquea la tool · SubagentStop impide que el subagente termine.
- **Convenciones del repo**: hooks = transportes finos, la lógica en `seed/` (single-source, heredable) ·
  rutas absolutas por ubicación del script · `.gen/` ya gitignored = casa del brief y del veredicto del slot.

## Fases (orden por dependencia)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **El loop verificar-no-revisar** (núcleo del arnés): `seed/delegation.py` (ley del slot, single-source) + hooks finos `blast_radius` (PreToolUse) y `verdict_required` (Stop→SubagentStop) + agents `generator`(sonnet, Write-acotado)·`verifier`(haiku, ro)·`reviewer`(opus, escalación)·`orchestrator`(opus) + skill `generate-slot` (contrato→manifiesto→spawn→veredicto). Diente DOS lados por bloqueo (escribir fuera del slot→exit2 · terminar sin veredicto→exit2 · inerte sin manifiesto). | ⏳ |
| 2 | **Tipo de gate `pbt`** (property-based): kind nuevo que orquesta un `pbt_cmd` DECLARADO (DATA, ADR-012) en el env del producto; dogfood sobre una propiedad REAL del grafo de Fase 1 (incremental ≡ full; serde round-trip) con un mini-PBT stdlib (0 deps). Diente dos lados: propiedad sana→verde · impl saboteada→la propiedad la atrapa→rojo. Cableado a `meta check`. **Construido USANDO el loop de Fase 1** (spawn del `generator`) = dogfood vivo. | ⏳ |
| 3 | **Gate `security_scan` heredable**: generaliza lo que FSK ya gatea (supply-chain/secretos, s4) a un KIND de sustrato reusable; dogfood sobre el propio sustrato (scan de secretos + SBOM trivial, 0 deps). Diente dos lados: fixture con secreto plantado→rojo · limpio→verde. `general` por paridad (≥2 fábricas) o declared-deferred honesto. | ⏳ |
| 4 | **`declared-deferred` con dientes + outcome por-incremento**: schema gana `deferral {trigger, since}`; el validator EXIGE `deferral` cuando `status: declared-deferred` (M0 bloquea el escape sin trigger). Check `declared_deferred` re-deriva todos los diferidos, BLOQUEA si falta trigger/fecha, REPORTA acumulación. `meta outcome` = ΔRTM (satisfechos/total antes↔después) + puntero al billing-ledger ⇒ "terminado" y "valió la pena" decidibles. | ⏳ |

## Disciplina (no negociable)
- **Trust-chain para la columna (CLAUDE.md/SELF-IMPROVEMENT §3)**: los HOOKS y la ley del slot (`seed/delegation.py`)
  son sombras deterministas de la columna (frontera de seguridad) → se escriben y revisan **con ojos propios, no se
  delegan**. Los AGENTS/SKILL (contratos/prompts) y la lógica de los KINDS de check (`verify/checks/`) sí son
  delegables — y la Fase 2 los usa para DOGFOODEAR el loop (el arnés construye parte de sí mismo).
- **Determinismo (I-3)**: blast-radius, veredicto, PBT-gate, security-scan, declared-deferred = re-derivables /
  herramientas reales, NUNCA juicio de LLM. El LLM PROPONE en el slot; la columna VERIFICA.
- **Tech = PLAN (ADR-012)**: `pbt_cmd`/scanner/`pbt`-lib son DATA elegida por el plan; el sustrato no nombra tech
  (mini-PBT/scan stdlib para el dogfood = 0 deps, fiel a Fase 1). Sancionado por el gate `generality`.
- **Multi-archivo (regla 2026-06-25)**: módulos cohesivos; ningún archivo nuevo monolito; hooks = transportes finos.
- **Inglés (ADR-017)**: el código, los `.claude/agents`, el skill y los nuevos checks, en inglés. Esta prosa de
  gobierno sigue en español (corpus + sha-stamps, como la Fase 1).

## Criterio de cierre (demostrable, no narrable)
1. **El loop por bloqueo (dos lados)**: el hook `blast_radius` deja escribir DENTRO del slot (exit 0) y BLOQUEA
   fuera (exit 2); `verdict_required` deja terminar CON veredicto bien-formado (exit 0) y BLOQUEA sin él (exit 2);
   ambos INERTES sin manifiesto activo (no rompen la sesión ni otros agentes). Probado por tests del hook.
2. **Dogfood vivo del loop**: una pieza real (el gate `pbt` de Fase 2) se construye spawneando el `generator`
   Sonnet vía `generate-slot`; el código generado NO entra al contexto de Opus (vuelve sólo el veredicto); el
   billing-ledger registra el split del propio build.
3. **Gate `pbt` dos lados, cableado a `meta check`**: propiedad sana del grafo→verde · impl saboteada→rojo.
4. **Gate `security_scan` dos lados**: secreto plantado→rojo · sustrato limpio→verde (o declared-deferred honesto).
5. **`declared-deferred` con dientes**: un capability `declared-deferred` SIN `deferral` → M0/validate ROJO; CON
   `deferral {trigger, since}` → verde; el check reporta la acumulación. `meta outcome` emite ΔRTM + costo.
6. **`meta check` verde** (incl. `generality` ⇒ anti-overfit: nada nombra fábrica/dominio/tech) · regla
   multi-archivo respetada (el gate `quality` la enforza sobre el propio sustrato nuevo).

## Punteros
- **ADR-017** (`docs/decisions/017-espina-de-grafo-y-delegacion-verificada.md`) — §2/§3/§4 gobiernan este plan.
- **Fase 1** (`docs/work/GRAPH-SPINE-KEYSTONE-INCREMENT.md`) — el grafo-columna + `quality` + billing que extendemos.
- **Mecánica Claude Code**: docs oficiales hooks (`code.claude.com/docs/en/hooks`) + sub-agents — verificada en sesión.
- **Memoria de sesión**: `sota-redesign-graph-spine` (recipe verificar-no-revisar) · `target-operating-model-sota`.

## Evidencia (cierre — re-derivable, no narrada)
<se completa al cerrar: comandos + veredictos por bloqueo + el split del billing-ledger de ESTE build>
