<!-- meta:doc sha=94f68b00f935684c1e08d45b7b5590d98f62eba7 updated=2026-06-13T14:57Z -->
# Economía de contexto — mantener el orquestador limpio

| Campo | Valor |
| --- | --- |
| Documento | Doctrina de economía de contexto y delegación del Meta-Factory |
| Hereda | ASF/ADR-020 (ley de colocación), ASF/CONTEXT-INCREMENT (bus de veredictos, agents meta) |
| Extiende | delegación como DEFAULT ergonómico (cierra G-3); enrutamiento de modelo como dato (cierra G-4/W4); el bus como contrato universal de observación |
| Estado del arte | `agent-harness-construction` (ECC): action/observation/recovery/context budget quality |

> El dolor explícito del ingeniero: *"que no tenga que revisar cosas que le consumen el contexto
> como loco… ejecutar comandos y leer outputs de un test… cada llamada posterior se hace más cara
> y se deteriora. Mantener el orquestador siempre lo más limpio."* Este doc es la respuesta.

---

## 1. La unidad de economía: tokens RESIDENTES, no tokens totales

De ASF/ADR-020, la observación que ordena todo:

> La economía correcta NO son tokens totales: son **tokens residentes en el contexto largo-vivo
> del orquestador**. Un log de pytest en un subagente muere con el subagente; en el orquestador
> se paga N veces (re-leído cada turno hasta compactación) y **degrada sus decisiones**.

Corolario (PF-12): **el orquestador opera sobre interfaces** (specs, veredictos, reportes,
decisiones); los subagentes sobre implementación (código, logs verbosos). El objetivo no es que
el modelo lea poco: es que lea **lo que se amortiza** (specs, interfaces, gobierno) y nunca lo
que es one-shot voluminoso (un dump de test, un log de build).

---

## 2. El bus de veredictos (I-7): el contrato universal de observación

Toda operación cara del Meta-Factory y de cada fábrica producida —`check`, `verify`, `gate`,
`trace`, `rtm`, `ci`, build, lint, type-check— devuelve un **veredicto acotado**, nunca un dump.
El formato unifica la "observation design" del estado del arte (`agent-harness-construction`:
todo output de herramienta lleva `status / summary / next_actions / artifacts`) con el `factory
check` de ASF:

```
VEREDICTO  <verb> — <status: PASS|FAIL|PROVISIONAL>   (exit <code>)
RESUMEN    <una línea>
CONTEOS    <por herramienta: ruff 0 · mypy 0 · pytest 431/431>
FALLOS     <≤N como file:line — mensaje>     (vacío si PASS)
ARTEFACTO  <path del log COMPLETO en disco>  ← el dump vive acá, no en el contexto
PRÓXIMO    <acción accionable, si aplica>
```

Reglas del bus (de ASF/CONTEXT D1, generalizadas):

- **Veredicto al contexto, log al disco.** El log entero (`.meta_check/<UTC>.log`, gitignored)
  nunca entra a ningún contexto por defecto.
- **El camino barato es el ergonómico, no el policíaco.** Brief es el DEFAULT sin flags; verbose
  es opt-in. NO se agrega un hook que bloquee `pytest` a pelo — castigaría también a los writers,
  y los hooks no distinguen llamador. La economía se logra haciendo que lo barato sea lo fácil.
- **Exit ≠ 0 si algo falla** → CI-able y verificable por el orquestador **sin leer nada**.
- **Revelación progresiva ante rojo** (reemplaza el truncado ciego, que esconde señal):
  1. el **veredicto** del bus — muchas veces alcanza;
  2. `triage` (haiku) sobre el path del log — centavos; el log crudo jamás toca al orquestador;
  3. **slice quirúrgico** del log SOLO si el orquestador decide que es load-bearing.
  El triage es TESTIGO, no autoridad: la autoridad sigue siendo el exit code + el log en disco.

---

## 3. La ley de colocación (I-6): dónde vive cada pieza

La cadena de preguntas de ASF/ADR-020, adoptada literal. Cada pieza vive en el **sustrato más
determinista que pueda sostenerla**; solo escala al modelo cuando requiere juicio genuino:

1. ¿Debe ser **GARANTIZADO verdadero**? → CLI (`src/metafactory/`): testeable, tipado, sin fe.
2. ¿Debe ser **IMPEDIDO/CAPTURADO** aunque el modelo se porte mal? → hook (defensa de frontera).
3. ¿Debe influir en **CADA turno**? → `CLAUDE.md` (el ÚNICO siempre-residente; se paga alquiler
   por línea: presupuesto mínimo, medible en diff).
4. ¿Es un **procedimiento a demanda**? → skill (paginado, carga al invocarse).
5. ¿Es un **rol con contexto/herramientas propias**? → agent (paginado, carga EN el subagente).
6. ¿Es **conocimiento/historia**? → docs/ADRs (residencia cero).

Corolarios vinculantes (heredados):

- **Lo determinista no se agentifica** (el verifier no es un agente) y **el juicio no se hookea**
  (los hooks no juzgan).
- **Los hooks casi no crecen**: corren en cada evento de cada sesión — el sustrato más caro de
  expandir. Pregunta previa obligatoria: *"¿esto no es un check del CLI?"*.
- **Cada prohibición declarada en un agent tiene sombra determinista** en hook/CLI (I-12).
- **El reporte del subagente es la API**: formato fijo en la definición del agent — lo único que
  entra al contexto del orquestador.

---

## 4. Delegación como DEFAULT, no como disciplina (cierra G-3)

ASF midió la sub-delegación pero el default seguía favoreciendo el inline. El Meta-Factory invierte
la ergonomía para que **delegar sea más barato que no delegar**:

### 4.1 El contrato de delegación cuesta ~0 líneas
Vive en la definición del agent (`.claude/agents/<rol>.md`), no se re-tipea por delegación. ASF
ya tenía esto (`factory-writer.md`); el Meta-Factory lo hornea en el `template/factory/` para que
toda fábrica nazca con su familia de agents. El reporte del agent es la API (formato fijo:
ARCHIVOS · COMANDOS+exit · EVIDENCIA · AFIRMO-vs-VERIFICADO · ISSUES).

### 4.2 El procedimiento que reemplaza al "vibe" (de ASF/CONTEXT D3, en CLAUDE.md ≤ presupuesto)
Orden de preguntas, no reglas duras:
1. ¿La salida es una **DECISIÓN** o un **DIFF**? Decisión → orquestador (jamás se delega).
   Diff → writer.
2. ¿Lo que voy a leer se **amortiza** (spec, interfaces, gobierno) o es one-shot (detalle de
   implementación)? One-shot voluminoso → delegar o pedir mapa a `Explore`.
3. **Prueba del prompt**: si el contrato de delegación cuesta más líneas que el cambio, lo hago yo.
4. ¿La **verificación** del resultado es determinista (`meta check`, gates)? Sí → delegar es
   barato (el riesgo de un subagente que se equivoca lo atrapa la gate). No (requiere juicio) →
   hacerlo directo.
5. ¿Toca la **cadena de confianza** (gate/verifier/hooks/commit_guard)? El orquestador lee ese
   diff con sus propios ojos, lo haya escrito quien sea.

### 4.3 Por qué esto sí mueve la aguja donde ASF no la movió
ASF dejó la delegación a juicio con un contador que la medía. El Meta-Factory agrega tres
palancas ergonómicas: (a) el bus de veredictos hace que el resultado de un subagente se verifique
en ≤N líneas —el orquestador no "paga" por confiar en el subagente—; (b) el contrato de ~0 líneas
elimina la fricción de armar el prompt; (c) el enrutamiento de modelo (§5) hace que elegir el
agente barato sea un lookup, no una decisión. **Medir sigue vigente** (el contador del journal),
pero ahora el default empuja en la dirección correcta.

---

## 5. Enrutamiento de modelo como DATO (cierra G-4 / el residual W4 de ASF)

ASF dejó "reviewer en opus para trust-chain" como regla narrativa sin sombra, porque *"el
mecanismo de agents no soporta selección condicional de modelo."* El Meta-Factory cierra esto
moviendo la decisión al **orquestador, guiado por una tabla de enrutamiento versionada** (dato,
no prosa). El orquestador clasifica el trabajo y lanza `Agent(subagent_type=…, model=…)` según:

| Clase de trabajo | Agent | Modelo | Por qué |
| --- | --- | --- | --- |
| Diff que toca la **cadena de confianza** | `reviewer` | **opus** | máximo riesgo; el reviewer fresco caza fachada/trust-holes |
| Diff voluminoso **no** trust-chain | `writer` | **sonnet** | implementación acotada, verificada por gate |
| Triage de un **log** rojo | `triage` | **haiku** | ≤5 líneas: causa probable, tests afectados, punteros |
| **Decisión** de arquitectura | (ninguno) | orquestador | jamás se delega (regla 1 de §4.2) |

La tabla vive como dato (`.claude/` o un YAML del repo) y un comando/skill la lee para elegir. La
**sombra determinista** del enrutamiento es doble: (a) el contador de delegaciones registra
`subagent_type` + `model` por evento (ASF/ADR-023 ya lo captura), así el journal mide si el
enrutamiento realmente ocurre; (b) la regla trust-chain ("el orquestador lee el diff con sus ojos")
sigue activa como red de seguridad si el enrutamiento fallara. Cierra W4 sin pedirle al mecanismo
de agents algo que no da.

---

## 6. Política de `/clear` y ritual de checkpoint (de ASF/CONTEXT D4)

El contexto es **caché**; el repo es la **base de datos**. Clear es gratis si todo está
externalizado, carísimo si no. Heredamos la disciplina de ASF (`/incremento`):

- **Frontera de INCREMENTO** → clear siempre (el cierre ya externaliza; rehidratar = handoff
  estándar desde docs versionados).
- **Frontera de FASE** → clear si la fase siguiente no necesita lo residente.
- **Cambio de TIPO de trabajo** (diseño / ejecución / operación de línea) → clear: los residuos de
  un modo anclan al otro.
- **Regla de oro**: NUNCA clear con estado no externalizado → checkpoint primero (enmienda/estado
  al doc de gobierno + LOG + STATE), clear después.
- La **auto-compactación** es un resumen escrito por el modelo —la narrativa en la que este repo no
  confía—. Si se acerca a mitad de fase: cerrar fase o checkpoint + clear deliberado. **Rehidratar
  desde docs versionados > rehidratar desde un summary de compactación.**
- Con orquestador flaco (post-checkpoint), el riesgo deja de ser bloat y pasa a ser **STALENESS**
  (creencias residentes sobre archivos que los subagentes ya cambiaron). La cura no es recordar:
  es **re-verificar** (`meta check`, gates) — determinista y barato.

---

## 7. El presupuesto, medible en el diff

Lo único siempre-residente que un humano paga cada turno es `CLAUDE.md`. Por eso tiene
**presupuesto explícito** (factory-spec `factory_substrate.context_budget.claude_md_max_lines`) y
todo diff que lo agrande debe justificarlo contra la cadena de la ley de colocación (§3). Un PR
que agrega contexto siempre-residente sin pasar esa cadena es un hallazgo del reviewer, no un
detalle de estilo. La economía de contexto deja de ser una buena intención y se vuelve un número
en el diff — exactamente como ASF volvió número la trazabilidad (RTM) y la frescura (devcheck).
