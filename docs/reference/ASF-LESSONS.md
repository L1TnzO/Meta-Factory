<!-- meta:doc sha=6091e426930ca8f38d951a487ce087edb8cdf13e updated=2026-06-13T14:57Z -->
# Lecciones de ASF — lo bueno a conservar, lo malo a corregir

| Campo | Valor |
| --- | --- |
| Documento | Extracción de aprendizajes de Agent_Systems_Factory (ASF) |
| Método | Lectura completa del árbol de ASF: ARCHITECTURE, AUDIT, HONEST-STATE, V2, STATE, LOG, los 23 ADR, el incremento CONTEXT, hooks, agents, commands |
| Fecha de lectura | 2026-06-13T02:17Z |
| Para qué | Todo lo bueno asciende al sustrato del Meta-Factory (`ARCHITECTURE.md §3`); todo lo malo se vuelve un gap cerrado por diseño |

> Citas con ruta relativa a `../../Agent_Systems_Factory/`. ASF es un sistema MUY bien pensado;
> este doc no lo desmerece — lo cosecha. Su mayor virtud es su honestidad (AUDIT/HONEST-STATE),
> que es justo lo que permite esta extracción.

---

## 1. Lo bueno (asciende al sustrato del Meta-Factory)

| Patrón de ASF | Dónde vive en ASF | Cómo lo hereda el Meta-Factory |
| --- | --- | --- |
| **La columna anti-sello-de-goma** (3 cerrojos): veredicto no escribible por el modelo, hash recomputado, Stop re-corre verify | ASF/ADR-006, `.claude/hooks/{proof_protect,gate_guard,stop_station_proof}.py`, `settings.json` permissions.deny | I-1, M1 — la primera meta-estación instala la columna en cada fábrica nueva |
| **Estaciones como dato**, no ramas de código; cero identidad de proyecto hardcodeada | ARCHITECTURE §9.1, anti-patrón #4 | I-2, M2 |
| **Frontera del determinismo** clara y honesta: modelo para slots acotados, código para invariantes; el determinismo en proceso/verificación/contratos | §6, PF-1/PF-2, ASF/ADR-009 | I-3, PF-1/PF-2 |
| **Escalera de automatización A/B/C** (auto / consentimiento / provisional honesto) — evita el binario "bloquear o fabricar" | §7, ADR-010 | I-4 |
| **Frontera generado/dominio**: Copier dueño de `generated/`, ingeniero de `domain/`, conexión por herencia; un update no pisa código humano | §11.5, ADR-014, `template/` `_skip_if_exists` | I-5, M4 |
| **Ley de colocación / economía de contexto**: cada pieza en el sustrato más determinista; veredictos al contexto, logs al disco | ADR-020, `docs/work/CONTEXT-INCREMENT.md`, `factory check` | I-6, I-7, `CONTEXT-ECONOMY.md` |
| **Memoria como artefacto del repo** + esquema narrativo (tipos de doc = semántica de mutación) | ADR-019, ADR-021, `.claude/hooks/session_journal.py`, `docs/{STATE,LOG,decisions,work,reference}` | I-8, I-9, M5 — y el esquema de ESTE repo |
| **RTM + árbol de evidencia**: requisitos con id + `satisfied_by`; commits con trailers; matriz re-derivada de artefactos | ADR-017/018, HONEST-STATE §"Trazabilidad de requisitos", `factory rtm`/`factory trace` | I-10, M5 |
| **Doctrina de los dos verificadores**: re-derivación sobre custodia en CI externo | ADR-022, `.githooks/pre-push`, `.github/workflows/factory-ci.yml` | I-11, M6 |
| **Sombra determinista de la capa meta**: toda regla narrativa que no deba saltearse tiene detector determinista; el juicio nunca se hard-blocka | ADR-023, `engine/narrative.py`, contador de delegaciones | I-12, PF-11 |
| **Honestidad de límites** como artefacto de primera clase | HONEST-STATE.md, AUDIT.md, PF-8 | I-13, este mismo doc |
| **Loop generar→verificar→promover** (la mitad cara —verificación— es el activo durable) | V2.md, V2.3, `pattern_request.json`, `/factory-promote` | base del loop de auto-mejora (`SELF-IMPROVEMENT.md`) |
| **Aislamiento fábrica/producto** verificado por test | PF-6, `test_factory_does_not_import_products` | PF-6, `test_metafactory_does_not_import_factories` |
| **Contratos de subagente como API** (formato de reporte fijo = lo único que entra al orquestador) | `.claude/agents/factory-writer.md`, CONTEXT D2 | `CONTEXT-ECONOMY.md §delegación` |
| **Disciplina de incrementos gobernados** (`/incremento`: abrir/checkpoint/cerrar; el doc ES el estado) | `.claude/commands/incremento.md`, los 4 docs de `docs/work/` | heredado tal cual; ver `docs/work/BOOTSTRAP-INCREMENT.md` |

**La lección meta más valiosa de ASF** (AUDIT, cierre): *"render+ast en verde NO prueba un
producto que funcione. SEIS bugs invisibles a ese nivel aparecieron al scaffoldear+compilar de
verdad."* → en el Meta-Factory esto es **M8, insalteable** (`ARCHITECTURE.md §6`).

---

## 2. Lo malo (gaps que el Meta-Factory cierra por diseño)

Ordenados por severidad. Cada gap cita la evidencia en ASF y nombra el mecanismo del
Meta-Factory que lo cierra.

### G-1 · ASF se fabricó a sí mismo (el gap raíz)
- **Evidencia**: ASF vive en su propia carpeta, sujeto a su propio harness. ADR-023 confiesa:
  *"la fábrica aplicó ADR-020 a fabricar productos, pero nunca a sí misma."* La capa meta quedó
  como prosa que se saltea bajo presión (STATE quedó viejo una sesión entera; la "partida de
  nacimiento" nunca escribió nada; ~1 delegación real en toda la historia del repo).
- **Causa raíz**: error de categoría — ASF no pertenece a su clase de producto (agentes
  LangGraph), así que tuvo que fingir ser su propio producto (`VISION.md §2`).
- **Cierre**: PF-9 + ADR-006 — el Meta-Factory ES el punto fijo legítimo; ASF se regenera como
  producto, gobernado por una capa más confiable que él.

### G-2 · Sobre-acoplamiento a UNA clase de sistema
- **Evidencia**: HONEST-STATE §"Acoplamiento de opiniones": *"la fábrica es opinionada al stack
  del RE Agent (Neo4j/W3C PROV, escalera de atribución, interrupt análisis→decisión, RAGAS).
  Es una fábrica para una CLASE, no universal. Generalizar = parametrizar esas opiniones."*
- **Cierre**: la factory-spec Mitad A (`ARCHITECTURE.md §5`) — las opiniones de ASF se vuelven
  parámetros del dominio. El Meta-Factory no las hereda; las recibe como spec.

### G-3 · Sub-delegación: el orquestador caro rara vez deriva al barato
- **Evidencia**: el ingeniero lo observó directamente ("Opus 4.8 MUY rara vez deriva a Sonnet
  4.6"). ASF lo midió (ADR-023, contador de delegaciones) pero *"la serie está vacía"*; *"5
  agentes definidos, ~1 delegación real en toda la historia del repo."* ASF eligió **medir antes
  de forzar** (correcto), pero el default ergonómico seguía favoreciendo mantener todo en el
  orquestador.
- **Cierre**: `CONTEXT-ECONOMY.md` — delegación como **default ergonómico** (no disciplina):
  contrato de delegación de ~0 líneas (vive en el agent), bus de veredictos que hace que NO
  delegar sea lo caro, y enrutamiento de modelo como dato.

### G-4 · El enrutamiento de modelo no tenía sombra determinista (residual W4)
- **Evidencia**: STATE §"Agujeros honestos" y CONTEXT §review de cierre: *"'reviewer en opus para
  trust-chain' es regla narrativa sin sombra determinista — el mecanismo de agents no soporta
  selección condicional de modelo."* Quedó como W4 RESIDUAL ACEPTADO.
- **Cierre**: el Meta-Factory mueve la decisión de modelo al **orquestador, guiada por dato**: un
  comando/skill lee la clasificación del diff (trust-chain / bulk / log) y elige
  subagente+modelo según una tabla de enrutamiento versionada. La selección condicional la hace
  el orquestador con `Agent(..., model=...)`, no el mecanismo de definición de agents. Cierra W4.

### G-5 · Falta una espina SDD formal
- **Evidencia**: el ingeniero lo señaló ("podría faltar SDD o similares"). ASF tiene S0 +
  spec.yml + RTM —que es *casi* SDD— pero no está enmarcado como un ciclo SDD disciplinado
  (spec→plan→tareas→verificación) ni como la fuente única de verdad explícita.
- **Cierre**: ADR-003 — espina SDD de primera clase, **enforced deterministamente** (M0 rehúsa
  specs incompletas; el RTM bloquea ante UNSATISFIED). Más fuerte que las herramientas SDD
  basadas en prompt del estado del arte, porque el incumplimiento corta una compuerta.

### G-6 · El façade-trap: plomería stubbeada + verificación contra el render
- **Evidencia**: AUDIT §"el problema de fondo: los dos errores se COMPONEN" — templates con TODOs
  en los puntos más difíciles (S1/S4 fachadas) + proof_checks apuntando a tests inexistentes +
  verifier corriendo desde el venv equivocado = *"el sello de goma reencarnado a nivel de
  plantilla."* Seis bugs aparecieron solo al scaffoldear+compilar de verdad.
- **Cierre**: M8 insalteable (e2e real: scaffold+compile+run en el venv del producto). Y la regla
  generalizada: **una fábrica se verifica construyendo, no renderizando.**

### G-7 · El residual de custodia del verifier (parcialmente cerrado en ASF)
- **Evidencia**: HONEST-STATE §"Lock 2 endurecido": *"`gates.ledger.json` y los registros de
  predecesores siguen siendo artefactos en disco protegidos por hooks + deny-list + SHA — no se
  re-derivan desde un proceso verificador; esa protección depende de que la cadena de hooks esté
  activa."* ASF lo mitigó con ADR-022 (CI externo) pero lo agregó **tarde** en su vida.
- **Cierre**: I-11/M6 — la doctrina de los dos verificadores se hornea **desde el nacimiento** de
  cada fábrica, no como un retrofit. El CI externo re-deriva; la custodia local deja de ser la
  raíz de confianza.

### G-8 · El patrón cascada: probada en pocas formas de spec
- **Evidencia**: STATE y HONEST-STATE repetidamente: *"Probada en 3 formas de spec; formas nuevas
  casi seguro destapan cascada (patrón visto 2×)."*
- **Cierre**: el loop generar→verificar→promover (heredado) + un corpus de **scenario-specs** de
  fábrica (del estado del arte: meta-harness/autocontext) que ejercitan formas diversas antes de
  promover. Ver `SELF-IMPROVEMENT.md §loop`.

### G-9 · Bootstrapping del entorno frágil / ecosistemas previos retirados
- **Evidencia**: ASF/ADR-004 SUPERSEDED (agentmemory descartado tras verificar npm+daemon+53 tools);
  gentleai/engram retirados (2026-06-10, con backup); el bug de `PROJECTS_ROOT` apuntando fuera
  del repo (AUDIT §bug confirmado) que sobrevivió *"porque ningún test ejercita factory new →
  station de punta a punta."*
- **Cierre**: M8 (e2e desde el primer incremento, no como Fase 4 tardía) + dependencias mínimas
  declaradas en el seed; cero daemons externos (memoria como artefacto del repo, I-8).

---

## 3. Síntesis: la fórmula del Meta-Factory

> **Meta-Factory = (todo el sustrato determinista que ASF descubrió, ascendido a template) +
> (las opiniones de ASF, descendidas a factory-spec) + (los 9 gaps de §2, cerrados por diseño) +
> (el punto fijo que vuelve legítimo el auto-mejoramiento).**

ASF nos costó iterar mucho porque descubrió el sustrato a los golpes (5 fases de remediación,
2 patrones cascada, 6 bugs de façade). El Meta-Factory existe para que **eso no se repita**: el
sustrato ya está cosechado y verificado, así que la próxima fábrica nace con todo cableado —
el one-shot que el ingeniero pidió.
