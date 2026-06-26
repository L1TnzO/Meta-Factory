<!-- meta:doc sha=5d643727882a758fec0019bdd3e3311642b2ddf7 updated=2026-06-26T02:05Z -->
# Incremento DELEGATION-HARNESS

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-26T02:05Z) (creado 2026-06-25T23:10Z). Cerralo con `meta increment close`
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
| 1 | **El loop verificar-no-revisar** (núcleo del arnés): `src/metafactory/delegation.py` (ley del slot, single-source DATA-agnóstica) + hooks finos `blast_radius` (PreToolUse) y `verdict_required` (Stop→SubagentStop), wired SÓLO en el frontmatter del `generator` + agents `generator`(sonnet, Write-acotado)·`verifier`(haiku, ro)·`reviewer`(opus, escalación)·`orchestrator`(opus) + skill `generate-slot` (contrato→manifiesto→spawn→veredicto). Diente DOS lados por bloqueo (escribir fuera del slot→exit2 · terminar sin veredicto→exit2 · inerte sin manifiesto). | ✅ |
| 2 | **Tipo de gate `pbt`** (property-based): kind nuevo que orquesta un `pbt_cmd` DECLARADO (DATA, ADR-012); dogfood sobre una propiedad REAL del grafo de Fase 1 (incremental ≡ full; serde round-trip) con un mini-PBT stdlib (0 deps). Diente dos lados: propiedad sana→verde · impl saboteada→la propiedad la atrapa→rojo. Cableado a `meta check`. **Construido DOGFOODEANDO el loop de Fase 1** (spawn de un generator Sonnet vía el protocolo `generate-slot`) = dogfood vivo. | ✅ |
| 3 | **Gate `security_scan` heredable**: generaliza lo que FSK ya gatea (supply-chain/secretos, s4) a un KIND de sustrato reusable; dogfood sobre el propio sustrato (scan de secretos stdlib, sin red, 0 deps). Diente dos lados: fixture con secreto plantado→rojo · sustrato limpio→verde. | ✅ |
| 4 | **`declared-deferred` con dientes + outcome por-incremento**: schema/model/loader ganan `deferral {trigger, since}` + `governance.deferral_tracking: strict` (opt-in); el validator EXIGE `deferral` cuando strict. Check `declared_deferred` re-deriva la acumulación estructural por fábrica + dos-lados vía fixture. `meta outcome` = RTM/fábrica (ΔRTM vs baseline) + deuda + puntero al billing-ledger ⇒ "terminado" y "valió la pena" decidibles. | ✅ |

## Disciplina (no negociable)
- **Trust-chain para la columna (CLAUDE.md/SELF-IMPROVEMENT §3)**: los HOOKS y la ley del slot
  (`src/metafactory/delegation.py` — meta-level por ahora; aún NO heredado a las fábricas generadas como `seed/`)
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
5. **`declared-deferred` con dientes** — *REFINADO tras medición (no narrado): el tooth es OPT-IN, no
   retroactivo.* Medición: **49 deferrals legacy bare** en las specs commiteadas (FSK 41 en PROSA dentro de
   `tech:` + ASF 8 estructurales). Un tooth HARD ("declared-deferred sin deferral → M0 rojo") las pondría a
   todas en falso-rojo (regresión + churn cross-fábrica, viola ADR-016). ⇒ el tooth es `governance.
   deferral_tracking: strict` (opt-in): bajo strict, un `declared-deferred` sin `deferral{trigger,since}` →
   M0 ROJO; con él → verde; un `deferral` malformado → rojo SIEMPRE (shape). Legacy bare → verde (forward
   pressure, no breakage). El check `declared_deferred` reporta la acumulación ESTRUCTURAL. `meta outcome`
   emite RTM/fábrica + ΔRTM + costo.
6. **`meta check` verde** (incl. `generality` ⇒ anti-overfit: nada nombra fábrica/dominio/tech) · regla
   multi-archivo respetada (el gate `quality` la enforza sobre el propio sustrato nuevo).

## Punteros
- **ADR-017** (`docs/decisions/017-espina-de-grafo-y-delegacion-verificada.md`) — §2/§3/§4 gobiernan este plan.
- **Fase 1** (`docs/work/GRAPH-SPINE-KEYSTONE-INCREMENT.md`) — el grafo-columna + `quality` + billing que extendemos.
- **Mecánica Claude Code**: docs oficiales hooks (`code.claude.com/docs/en/hooks`) + sub-agents — verificada en sesión.
- **Memoria de sesión**: `sota-redesign-graph-spine` (recipe verificar-no-revisar) · `target-operating-model-sota`.

## Evidencia (cierre — re-derivable, no narrada)
**Código nuevo** (inglés, ADR-017; regla multi-archivo — ningún módulo monolito):
- **Fase 1 (loop, trust-chain, ojos propios)**: `src/metafactory/delegation.py` (ley del slot) ·
  `.claude/hooks/{blast_radius,verdict_required}.py` (transportes finos) · `.claude/agents/{generator,
  verifier,reviewer,orchestrator}.md` · `.claude/skills/generate-slot/SKILL.md` · `tests/test_delegation.py` (16).
- **Fase 2**: `src/metafactory/verify/checks/pbt_gate.py` (kind) + `src/metafactory/graph/pbt_properties.py`
  (el slot DELEGADO) · cableado `pbt` en `cmd_check`.
- **Fase 3**: `src/metafactory/verify/checks/security_scan.py` + `tests/fixtures/security/planted_secrets.txt`
  · `tests/test_security_scan.py` (4) · cableado `security`.
- **Fase 4**: `spec/{model,loader,validator,factory.schema.json}` (+`deferral`/`governance`) ·
  `verify/checks/declared_deferred.py` + `tests/fixtures/governance/strict_untracked.factory.spec.yml` ·
  `verify/outcome.py` + `meta outcome` · `tests/test_deferral_governance.py` (10) · cableado `deferred`.

**Los 6 criterios, por bloqueo**:
1. **Loop dos-lados** — `tests/test_delegation.py` 16 verdes: hooks REALES como subproceso —
   blast_radius dentro→0 / fuera→2 / sin-manifiesto→0 · verdict_required con-veredicto→0 / sin→2 /
   sin-manifiesto→0 · válvula anti-loop. Mecánica Claude Code 2.1.193 verificada (hooks por-agente en
   frontmatter, `Stop→SubagentStop`, `agent_id/agent_type`) ⇒ los dientes viven en el `generator`, NUNCA globales.
2. **Dogfood vivo** — el slot `graph/pbt_properties.py` lo escribió un **generator Sonnet** (subagent_tokens
   **43.354**, 13 tool-uses) vía contrato+manifiesto (`.gen/active_slot.json`); devolvió SÓLO el veredicto
   (`{status:green, check:pbt_gate, exit_code:0}`); **Opus verificó por BLOQUEO** (`meta` corrió `pbt_gate` →
   exit 0), no leyó el código. Billing-ledger `docs/work/DELEGATION-HARNESS-billing.json` (`meta billing`):
   **generate/sonnet 43.354 tok ($0.15) · brain/opus 153k (estimate) · 0 haiku** ⇒ **22% delegado**. *Lección
   honesta*: < Fase 1 (36%) PORQUE casi toda la Fase 2 es la COLUMNA (hooks/ley-del-slot/kinds) = trust-chain,
   correctamente NO delegada; lo único bulk-delegable fue la suite de propiedades.
3. **Gate `pbt` dos-lados** — `meta check` `pbt` ok: propiedad sostenida (seed fijo, re-derivable) + bajo
   `METAFACTORY_PBT_SABOTAGE=1` la propiedad MUERDE (contraejemplo `incremental != full`). Decorativo→rojo.
4. **Gate `security` dos-lados** — `security` ok: sustrato limpio (97 archivos) + fixture plantado → 3 hits
   (aws-key EXAMPLE · secret-assign · PEM). Decorativo→rojo.
5. **`declared-deferred` con dientes** — `deferred` ok: 0 regresión en las 5 fábricas (49 bare legacy verdes) +
   fixture strict-untracked MUERDE; tooth two-sided probado en `test_deferral_governance` (strict+bare→rojo ·
   strict+tracked→verde · malformado→rojo). `meta outcome` → RTM **54/54** + deuda **0/2 tracked** + costo.
6. **`meta check` 10/10 verde** — compile·docs·projection·isolation·generality·quality·**pbt·security·
   deferred**·suite (suite incluye los 30 tests nuevos). `generality` verde ⇒ ningún check nombra fábrica/
   dominio/tech (anti-overfit). `quality` verde ⇒ regla multi-archivo respetada sobre el sustrato nuevo.

**Tech de PLAN ejercida** (ADR-012): stdlib pura (mini-PBT a mano, scanner regex, JSON) — 0 deps nuevas.
**Diferido honesto**: el registro on-disk del `generator` como `subagent_type` necesita reinicio de sesión →
el dogfood vivo usó `general-purpose` pineado a Sonnet con el MISMO protocolo `generate-slot` (los dientes de
máquina ya están probados por bloqueo en `test_delegation.py`; el agent `generator` queda listo para la próxima
sesión). PBT multi-propiedad + security feed-vivo OSV + `strict` adoptado por las fábricas = upgrades-hasta-medición.
El split del monolito sigue siendo **Fase 3 `MONOLITH-REFACTOR`**, FORZADO por `quality` y ahora tomable por
slots acotados vía este arnés.
