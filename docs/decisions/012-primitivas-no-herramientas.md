<!-- meta:doc sha=6156e38ebfef3ab66b74e368f3b59aef927a4336 updated=2026-06-15T03:45Z -->
<!-- meta:doc sha=PENDING updated=2026-06-15T03:43Z -->
# ADR-012 — Primitivas de diseño, no herramientas: la tecnología se decide en el plan SDD

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-15T03:43Z |
| Decide | el ingeniero (2026-06-15) |
| Generaliza | I-3 (frontera del determinismo), I-2 (estaciones como dato) |
| Referencia | `reference/PRIMITIVES.md`, ADR-003 (SDD), ADR-011, VISION §5.2/§6 |

## Contexto

Una primera lectura del roadmap propuso "backends de generación deterministas por stack" (Copier para
Python, Plop para TypeScript) horneados en el sustrato. Eso es un error de categoría doble: (1) mete
determinismo en el **contenido generado** (viola I-3), y (2) hornea **herramientas** en la plataforma,
volviéndola opinada a un stack — el mismo G-2 de ASF, un nivel arriba.

El principio correcto: la Meta-Factory es generalista porque encoda **primitivas de diseño** (CONCEPTOS:
qué resuelve Copier, qué resuelve LangGraph) y deja que la **planificación** elija la tecnología que
provee cada primitiva para el dominio concreto. *"No le enseñás a usar Copier; le enseñás la primitiva,
y ella decide 'ok, necesito esta tecnología'."*

## Decisión

- El sustrato (`src/metafactory/`) **NO contiene ninguna tecnología de dominio**. Cero `import copier`,
  cero `langgraph`, cero `next`. Si aparece, es un bug de filosofía.
- Las **primitivas de diseño** (`reference/PRIMITIVES.md §3`) son conocimiento de DISEÑO, no código de
  runtime. Viven en un **skill** invocado en tiempo de diseño.
- La **tecnología** que provee cada primitiva se decide **durante la planificación SDD** (juicio del
  modelo, revisable) y se **declara en el spec/diseño** de la fábrica. Es DATO de la fábrica, como las
  estaciones (I-2), no rama de código del sustrato.
- La frontera: lo que **no debe saltearse** (las primitivas de SEGURIDAD §2) es determinista y fijo; lo
  que es **elección de ingeniería** (qué tech, qué topología) es planificación bajo la filosofía.

## Consecuencias

- **Generalidad real**: el mismo sustrato produce ASF (agentes/LangGraph), Full-Stack (web/TS), Mobile,
  IoT — porque ninguno está en su código; todos son specs que eligen tecnologías para las mismas primitivas.
- **Anti-overfit (G-8 generalizado)**: cada capa del motor se valida con ≥2 dominios radicalmente
  distintos antes de promover; si algo sólo sirve para un stack, es supuesto no parametrizado.
- **El skill es la cantera viva**: un dominio nuevo que destape una primitiva no listada la agrega a
  PRIMITIVES.md §3; nunca se "agrega un backend" al sustrato.
- **Claude Code no es full-determinista, y está bien**: usa su planificación potente para diseñar, bajo
  una misma filosofía (las primitivas + el SDD + la columna). El determinismo lo envuelve, no lo sustituye.

## Rechazado

- "Backends de generación por stack en el sustrato": hornea herramientas (viola esta decisión) y mete
  determinismo en la generación (viola I-3). Copier/Plop/Vite son elecciones de plan, no plataforma.
