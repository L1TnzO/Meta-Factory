<!-- meta:doc sha=e6d2c1ca06aaa3fb0ac6290ae67967fa96e56d19 updated=2026-06-13T14:57Z -->
# Visión — Meta-Factory: la fábrica que fabrica fábricas

| Campo | Valor |
| --- | --- |
| Documento | Visión y tesis fundacional |
| Estado | Borrador vivo (pre-implementación) |
| Audiencia | Ingeniería de plataforma, futuras iteraciones (humanas y modelo) |
| Origen | Conversación 2026-06-12; lectura completa de Agent_Systems_Factory (ASF) y del estado del arte (ECC 2.0) |
| Autoridad temporal | git + UTC al minuto (`YYYY-MM-DDTHH:MMZ`) — esquema heredado de ASF/ADR-021 |

> Este documento es autocontenido. Define POR QUÉ existe el Meta-Factory y cuál es el
> argumento que lo vuelve legítimo donde ASF no lo era. La arquitectura concreta vive en
> `ARCHITECTURE.md`; lo aprendido de ASF en `ASF-LESSONS.md`; la seguridad del
> auto-mejoramiento en `SELF-IMPROVEMENT.md`; la economía de contexto en `CONTEXT-ECONOMY.md`.

---

## 1. La tesis en una línea

**ASF estandarizó el sustrato de producción de *agentes*. El Meta-Factory estandariza el
sustrato de producción de *fábricas*** — y es el único sistema de su tipo que puede
construirse y mejorarse a sí mismo sin cometer un error de categoría.

Donde ASF gira alrededor de un framework de dominio (LangGraph + siete capacidades de
producción para agentes), el Meta-Factory gira alrededor de **tunear el harness de Claude
Code** hasta volverlo un entorno absolutamente específico para construir fábricas. Su
producto no es un agente: es **otra fábrica** — ASF, un Full-Stack-Factory, o el que se
especifique.

---

## 2. El problema que motiva todo: ASF se fabricó a sí mismo

ASF es excelente (ver `ASF-LESSONS.md`), pero arrastra una rareza estructural en su origen:
se construyó **dentro de su propia carpeta**, sujeto a su propio `CLAUDE.md`, sus hooks, sus
skills, sus agents. La cosa-que-se-construye y la cosa-que-construye compartieron harness,
reglas y frontera de confianza. ASF se fabricó a sí mismo.

El propio ASF reconoció el síntoma sin nombrar la causa raíz. ADR-023 (sombra determinista)
confiesa: *"la fábrica aplicó ADR-020 (sustrato determinista primero) a fabricar productos,
pero **nunca a sí misma**."* Esa asimetría —enforcement durísimo para el producto, prosa
confiada para la capa meta— es la huella del bootstrap mal hecho: ASF no tenía una capa más
confiable que ella misma que la gobernara, así que se gobernó con narrativa.

### 2.1 Por qué es un error de categoría (y no solo "mala práctica")

Definamos la **clase de producto** de una fábrica F como el conjunto de artefactos que F
sabe construir con garantías.

- Clase de producto de ASF = `{ sistemas agénticos sobre LangGraph }`.
- ASF **no pertenece** a esa clase: ASF es una fábrica sobre el harness de Claude Code, no un
  agente LangGraph.

Por lo tanto, cuando ASF se construye a sí mismo, tiene que **fingir ser su propio producto**:
contorsionarse para que un proceso diseñado para emitir agentes se aplique a algo que no es un
agente. De ahí salen los gaps honestos que el propio ASF documenta (la capa meta sin sombra
determinista, la sub-delegación, el STATE que queda viejo una sesión entera). No son bugs:
son el precio de un sistema aplicándose fuera de su clase.

### 2.2 El criterio de legitimidad del auto-mejoramiento

> **Una fábrica F puede aplicarse legítimamente a sí misma si, y solo si, F pertenece a su
> propia clase de producto.**

Es el mismo principio que vuelve legítimo a un compilador que se compila (un compilador es un
programa, y compila programas), a un evaluador metacircular, o a un combinador de punto fijo.
La auto-aplicación no es sospechosa *per se*: lo es solo cuando el sistema sale de su clase.

---

## 3. El punto fijo: por qué el Meta-Factory SÍ puede mejorarse a sí mismo

- Clase de producto del Meta-Factory = `{ fábricas construidas sobre el harness de Claude Code }`.
- El Meta-Factory **pertenece** a esa clase: él mismo es una fábrica construida sobre el harness
  de Claude Code.

Por lo tanto, el Meta-Factory mejorándose a sí mismo **es la definición de lo que hace**, no una
excepción a sus reglas. Es el único punto fijo legítimo del ecosistema:

```
  Meta-Factory  ─construye→  { ASF, Full-Stack-Factory, ... }  ─construyen→  { agentes, apps, ... }
       │
       └─construye/mejora→  Meta-Factory      ← punto fijo legítimo (está en su propia clase)
```

ASF intentó ser este punto fijo sin serlo. El Meta-Factory lo es por diseño. La consecuencia
operativa es directa y la adoptamos como decisión (ADR-006 de este repo):

> **ASF deja de auto-fabricarse y se regenera como *producto* del Meta-Factory.**

Lo reutilizable de ASF —el sustrato determinista de toda fábrica confiable— asciende al
*template* del Meta-Factory. Lo opinado de ASF —LangGraph, Neo4j, W3C PROV, RAGAS, las siete
capacidades— desciende a *especificación*: se vuelve la "business logic" del producto-fábrica
llamado ASF. ASF no pierde nada; gana un gobernante más confiable que él.

---

## 4. Qué buscamos (los objetivos del ingeniero, hechos criterio)

El mandato fue explícito. Lo traducimos a propiedades verificables, no aspiraciones:

| Objetivo del ingeniero | Propiedad del Meta-Factory | Cómo se garantiza |
| --- | --- | --- |
| "Barato y bien; iterar poco; el one-shot muy bueno" | Toda fábrica **nace** con el sustrato completo cableado | el `template/factory/` ya trae columna, bus de veredictos, RTM, memoria, CI externo |
| "Que le cueste MUCHO alucinar" | El modelo solo escribe en **slots acotados**, verificados después | frontera determinismo (PF-1/PF-2 de ASF), columna anti-sello |
| "Que no revise cosas que le consumen el contexto (outputs de tests)" | **Bus de veredictos**: veredicto ≤N líneas + puntero al log; logs al disco | `CONTEXT-ECONOMY.md`; el orquestador nunca recibe dumps |
| "Mantener el orquestador limpio" | **Ley de colocación** (ASF/ADR-020) adoptada y extendida; delegación por defecto | `CONTEXT-ECONOMY.md` |
| "Trazabilidad: que los requisitos REALMENTE se cumplieron" | **RTM re-derivado de artefactos** (cero narrativa): SATISFIED/PROVISIONAL/UNSATISFIED | `factory rtm` heredado y generalizado |
| "Que todo sea revisable" | Todo cambio es un diff; revisor adversarial de contexto fresco | agent `reviewer`, diff-reviewable por construcción |
| "Super seguro, confiar en el determinismo" | **Doctrina de los dos verificadores** desde el nacimiento de cada fábrica | re-derivación sobre custodia (ASF/ADR-022) |
| "Falta SDD u otras formalidades de ingeniería" | **Espina SDD de primera clase**: spec→plan→tareas→verificación, enforced | `ADR-003`; S0/M0 rehúsan specs incompletas |
| "Opus rara vez deriva a Sonnet (caro)" | **Enrutamiento de modelo como dato** + delegación ergonómica | `CONTEXT-ECONOMY.md` §enrutamiento; cierra el residual W4 de ASF |

---

## 5. Alcance y no-alcance

### 5.1 Alcance

- Estandarizar y hornear el **sustrato de producción de fábricas** (los 13 invariantes
  reutilizables extraídos de ASF; ver `ARCHITECTURE.md §3`).
- Definir una **espina SDD** que toma una *factory-spec* y emite una fábrica de grado-producción.
- Hornear en cada fábrica producida la **economía de contexto** (bus de veredictos) y la
  **seguridad determinista** (la columna + los dos verificadores) por construcción.
- Soportar el **auto-mejoramiento seguro** del propio Meta-Factory y de las fábricas que produce,
  bajo el loop observar→proponer→verificar→promover→rollback con control de blast-radius.

### 5.2 No-alcance

- **No** es una fábrica de un framework particular. LangGraph es un cliente (vía ASF); Next.js
  sería otro. Ninguno es la plataforma.
- **No** garantiza la corrección *semántica* del producto final de una fábrica — esa
  imposibilidad se hereda de ASF (HITL + eval + gold set como input humano irreducible).
- **No** sustituye al ingeniero: produce fábricas probadas y documentadas; la dirección,
  la aprobación y los datos de verdad de campo son humanos.
- **No** confía en narrativa donde puede haber determinismo (ADR-023 de ASF, generalizado):
  toda obligación que no deba saltearse tiene sombra determinista.

---

## 6. La frase que ordena el proyecto

> "El Meta-Factory es un Claude Code con superpoderes para el dominio de *construir fábricas* —
> pero sigue siendo Claude Code."

Es la frase del ingeniero sobre ASF ("la factory es un Claude Code con superpoderes para
sistemas agénticos"), subida un nivel. Todo el determinismo, toda la confiabilidad, toda la
economía: son **maneras de envolver a Claude Code en garantías**, no de reemplazarlo. Claude
Code genera maravillas; el Meta-Factory las vuelve confiables, trazables y baratas de producir.
