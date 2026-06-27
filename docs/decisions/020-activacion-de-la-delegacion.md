<!-- meta:doc sha=8c55ffce51aafa3952377023361961e3a5e21b0c updated=2026-06-27T21:49Z -->
# ADR-020 — Activación de la delegación: routing por defecto, métrica de costo, y especialización por ROL

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-27T21:50Z |
| Decide | el ingeniero (2026-06-27, «Construye D» tras revisar A/B/C); ejecuta el orquestador |
| Generaliza | ADR-017 (espina de grafo + verificar-no-revisar + routing como dato), ADR-018 §4 (la columna/disciplina la inyecta el sustrato, NO el spec), ADR-012 (tech = plan, nunca hardcodeada), I-12 (toda prohibición de un agent tiene sombra determinista) |
| Referencia | `work/DELEGATION-ACTIVATION-DIRECTION-INCREMENT.md` (la dirección A–D + §5.2 que pidió este ADR), `work/DELEG-MEASURE-INCREMENT.md` (B), `work/DELEG-ACT-META-INCREMENT.md` (A), `work/DELEG-ACT-FACTORY-INCREMENT.md` (C), `work/DELEG-TOPOLOGY-HYGIENE-INCREMENT.md` (D), `src/metafactory/agent_roles.py` (vocabulario canónico, single-source), `reference/OBSERVABILITY-METRICS.md` (el split de tokens) |

## Contexto

La Fase 2 SOTA (`DELEGATION-HARNESS`, 2026-06-26) **construyó** el arnés verificar-no-revisar (agentes
`orchestrator`/`generator`/`verifier`/`reviewer`, skill `generate-slot`, hooks `blast_radius`/`verdict_required`,
gates `pbt`/`security`/`deferred`) **pero nunca lo encendió**: medición 2026-06-27 = `delegation_rate` **0.0%**,
~100% Opus, el cache-read de Opus dominando el costo (~$7.320). El interruptor estaba sin tocar.

El incremento-familia `DELEGATION-ACTIVATION` (Fases A–D) lo **encendió y propagó**: B midió (la métrica dejó
de mentir 0% — el emisor matcheaba el tool viejo `Task`→`Agent`), A activó la delegación natural del meta (regla
permanente en `CLAUDE.md`, `description` proactivas, alias `--agent orchestrator`, NO `agent` global), C propagó
el cerebro a las 5 fábricas (el emisor inyecta `orchestrator` + `generate-slot`), D hizo la higiene de topología
(esta ADR). El §5.2 de la dirección pidió **un ADR corto** que fije las decisiones de arquitectura con
consecuencias en `column_scope` y en el costo — inmutables y citables, como ADR-017/018. Este es ese ADR; lo
diferimos hasta D (cuando (a)–(d) estuvieran TODAS decididas) para no crear un ADR parcial que después haya que
superseder (el churn de historia que el proyecto prohíbe).

## Decisión

1. **(a) Routing por defecto vía `CLAUDE.md`, NO `agent` default global.** La delegación es natural —no se pide
   en cada prompt— por una **regla permanente en la residencia** (`CLAUDE.md` carga en cada sesión sin reemplazar
   el system-prompt) + `description` proactivas (`MUST BE USED…`/`Use PROACTIVELY…`) + el alias manual
   `claude --agent orchestrator` para builds pesados. Se **rechaza** `"agent": "orchestrator"` global en
   `settings.json`: reemplazaría el system-prompt base de Claude Code en CADA sesión (incluso un fix casual
   bootearía en modo orquestador). Granular y reversible > agresivo y global.

2. **(b) El KPI de costo es la `delegation` + el split de tokens por modelo, no la prosa.** «Más barato» es
   **verificable**: `meta metrics` LIDERA con el conteo de delegaciones (evento `kind="delegation"` del journal,
   emitido por el predicado `instrument.is_subagent_spawn` sobre el tool `Agent`) + el split de output/costo por
   tier (Opus/Sonnet/Haiku). La palanca #1 es el **aislamiento de contexto** (sacar el bulk-read de la ventana de
   Opus, porque su cache-read domina), no sólo mover la generación a Sonnet.

3. **(c) Los agentes se especializan por ROL, nunca por dominio — con dientes.** Un agente se especializa por
   **modelo · tools · contrato-de-verificación**; el dominio (kotlin/frontend/sql) lo carga el **slot manifest**
   por invocación (`.gen/active_slot.json`), nunca un agente nuevo (proliferar por dominio rompe ADR-012 y crea
   ambigüedad de ruteo). El vocabulario de roles es **CERRADO** y single-source en `agent_roles.py`
   (`CANONICAL` = orchestrator·generator·verifier·reviewer; `LEGACY_SYNONYMS` = writer≡generator·triage≡verifier).
   Lo enforza el gate **`roles`** de `meta check` (`role_hygiene`): un agent cuyo NOMBRE de rol cae fuera del
   vocabulario (p.ej. `kotlin-writer`) tira el gate a rojo; el negativo es no-decorativo. Agregar un rol es un
   acto DELIBERADO (editar el constante + un ADR) — esa deliberación ES el diente.

4. **(d) La observabilidad de delegación NO baja a `FACTORY_COLUMN`.** `column_scope` mantiene la captura de
   delegación como **meta-only**: proyectar el write-half (un `delegation_capture` de fábrica) sin el read-half
   (no hay superficie de rehidratación/serie en una fábrica standalone) sería un *dead writeback* (igual que
   `mem_capture`/`session_start`, `column_scope.META_ONLY`). La delegación de una fábrica se mide desde el meta
   operador (`meta station --factory`). Si algún día se quiere medir DENTRO de una fábrica standalone, hay que
   re-calibrar el gate `least_priv` — y eso requeriría su propio ADR.

5. **(D1) Se mantiene el `verifier` custom; NO se colapsa en el built-in `Explore`.** `Explore` es un agente de
   **búsqueda fan-out** que LOCALIZA código leyendo *excerpts* y «no revisa ni audita»; el `verifier` es el
   complemento: lee UN artefacto conocido y voluminoso EN COMPLETO (un log de gate, un árbol generado, una spec
   larga) y devuelve un **digest estructurado acotado** (lidera con el sí/no, los `file:line` que lo fundan, los
   red flags). Son **complementarios, no redundantes** — esa es la razón registrada de existir del custom. El
   orquestador rutea: `Explore` para «dónde/cómo está X», `verifier` para «digerí ESTE artefacto / ¿pasó este gate?».

6. **Convergencia de nombres de rol: forward-only, sin churn.** Las 5 fábricas existentes mantienen
   `writer`/`triage` (cuerpos en español, ADR-017 prohíbe re-autorar/traducir en masa lo existente y churnear
   sha-stamps); la equivalencia de rol está DOCUMENTADA (`LEGACY_SYNONYMS`) para que el operador razone con un
   solo vocabulario, y el gate `roles` la acepta. La convergencia física de los nombres (renombrar el emisor +
   re-emitir las 5) sería un incremento de fábrica aparte, opcional — no se hace acá (residuo honesto).

## Consecuencias

- «Encendido y barato» deja de ser narrado y pasa a ser **medible** (conteo de delegación + split de tokens) y
  **enforzado** (la columna ya tenía los dientes `blast_radius`/`verdict_required`; ahora la topología tiene
  higiene con diente: `roles`).
- `meta check` pasa de 16 a **17 checks** (suma `roles`). El vocabulario de roles es un punto único de cambio
  deliberado: nadie agrega un agente por dominio sin tocar el constante + un ADR.
- El meta y las 5 fábricas heredan el MISMO modelo mental de roles (un vocabulario), sin re-autorar artefactos
  españoles existentes (ADR-017 forward-only). El `Explore` built-in y el `verifier` custom quedan con roles
  distintos y documentados.

## Rechazado

- **`agent` default global en `settings.json`.** Reemplaza el system-prompt base en CADA sesión; sobre-ingeniería
  y fricción para trabajo casual. La regla `CLAUDE.md` es la capa correcta (fase-viva, granular, reversible).
- **Colapsar `verifier` en `Explore`.** `Explore` lee excerpts y no audita; perderíamos el digest-en-completo de
  UN artefacto conocido (el caso del log de gate). Agregan restricciones distintas → se mantienen ambos.
- **Bajar `delegation_capture` a `FACTORY_COLUMN` ahora.** Write-half sin read-half = dead writeback; ensancharía
  el scope de la fábrica sin medición real (re-calibraría `least_priv` sin valor). Se mide desde el meta.
- **Renombrar físicamente `writer`/`triage`→`generator`/`verifier` en las 5 fábricas.** Churn de artefactos
  españoles existentes + sha-stamps contra ADR-017 (forward-only). La equivalencia documentada + el gate dan el
  «un vocabulario» sin el churn. Si se quiere la convergencia física, es un incremento aparte.
