<!-- meta:doc sha=e3ef1a4c9e7ce4d7a38a52e67fa136ebe1d72b2c updated=2026-06-15T13:29Z -->
<!-- meta:doc sha=PENDING updated=2026-06-15T03:43Z -->
# PRIMITIVES — la filosofía: primitivas de diseño, no herramientas

> tipo: reference (estable) · creado: 2026-06-15T03:43Z
> Autocontenido. Si llegás sin contexto: este doc es la FILOSOFÍA del Meta-Factory. La Meta-Factory NO
> sabe usar Copier, ni LangGraph, ni Next.js. Sabe los CONCEPTOS que esas herramientas resuelven —las
> *primitivas*— y en tiempo de DISEÑO planifica (Claude Code) qué tecnología provee cada primitiva para
> el dominio que toca. La herramienta se decide en el plan SDD o se declara en el spec; **nunca se
> hardcodea en el sustrato** (es herramienta, no filosofía). Decisiones que lo fijan: `ADR-011`, `ADR-012`.

## 0. La frase que ordena esto

> La Meta-Factory es la más generalista de todas: describe cómo debe ser una Factory "perfecta" y se
> replica bajo dominios variados (ASF, Full-Stack, Mobile, IoT…). No es Copier ni lo que envuelve a ASF:
> es el **concepto** de **construir productos de manera segura**. No le enseñás a usar Copier; le enseñás
> la primitiva, y ella decide "ok, necesito esta tecnología". (Mandato del ingeniero, 2026-06-15.)

## 1. La frontera del determinismo (I-3, la regla madre)

El determinismo vive en **proceso + verificación + contratos**, **NUNCA en el contenido generado**.
De ahí salen DOS familias de primitivas con dueños distintos:

| Familia | Quién la posee | Determinista? | Se elige por dominio? |
| --- | --- | --- | --- |
| **Primitivas de SEGURIDAD** (§2) | el Meta-Factory, invariante | **Sí** — código, gates, re-derivación | **No** — son la filosofía, idénticas para toda fábrica |
| **Primitivas de DISEÑO** (§3) | declaradas en el spec / elegidas en el plan SDD | **No** — el modelo genera el contenido | **Sí** — la tecnología que las provee la decide la planificación |

Corolario operativo: Claude Code **genera el 100%** (ADR-011); el determinismo no le ata las manos al
generar — le verifica las manos después. "Envolver a Claude Code en garantías, no reemplazarlo" (VISION §6).

## 2. Primitivas de SEGURIDAD (el sustrato las HORNEA; invariantes a todo dominio)

Estas NO se eligen ni se negocian: toda fábrica las hereda. Son los 13 invariantes vistos como primitivas.

| id | Primitiva | Qué garantiza | Invariante |
| --- | --- | --- | --- |
| **SAFE-1** | Veredicto sólo por prueba | `passed` lo computa SÓLO un verificador determinista desde exit codes reales; el modelo no puede escribir veredictos | I-1 (columna, 3 cerrojos) |
| **SAFE-2** | Verificar construyendo, no renderizando | una fábrica/producto se prueba scaffoldeando+compilando+corriendo en su PROPIO toolchain; render verde no basta | M8 (façade-trap) |
| **SAFE-3** | Re-derivación sobre custodia | confianza = un runner limpio re-deriva el veredicto honesto idéntico; replicable > archivado | I-11 / PF-10 (dos verificadores) |
| **SAFE-4** | Requisitos por artefacto, no por narrativa | RTM re-derivado de `.proof/`: SATISFIED/PROVISIONAL/UNSATISFIED corta el CI | I-10 |
| **SAFE-5** | Slots creativos acotados | el modelo escribe sólo en slots cuyo output se verifica; lo invariante es contrato, no contenido | I-3 |
| **SAFE-6** | Sombra determinista universal | toda regla que no deba saltearse tiene detector/impedimento en hook/CLI; la narrativa declara, el código garantiza | I-12 / PF-11 |
| **SAFE-7** | Honestidad de límites | aspiración nunca confundida con realidad; M0/S0 rehúsan en vez de fabricar defaults; `status` honesto | I-13 |
| **SAFE-8** | Jerarquía de confianza | cada capa la verifica una al menos tan confiable; el seed es la raíz auditada a mano; auto-mod de la cadena = gate más fuerte | SELF-IMPROVEMENT |

## 3. Primitivas de DISEÑO (CONCEPTO; la tecnología la elige el plan SDD / el spec)

Cada fila es **lo que una herramienta RESUELVE**, abstraído de la herramienta. La columna "ejemplos de
tecnología" es ilustrativa — el plan elige según el dominio; el sustrato no la conoce.

| id | Primitiva (el concepto) | Qué resuelve | Ejemplos de tecnología (NO hardcodeados) |
| --- | --- | --- | --- |
| **DES-1** | Andamiaje regenerable | el producto es derivable del spec+diseño; regenerar es idempotente. Con 100%-generado (ADR-011) **no hay código humano que proteger**: la fuente es el spec, el código es derivable | Copier (Py) · Plop/Hygen (TS) · plantillas · el propio Claude Code |
| **DES-2** | Topología verificable | la estructura del producto es chequeable estáticamente contra un invariante (sin correr el modelo) | grafo compilado LangGraph (`get_graph()`) · AST de rutas · schema de IaC |
| **DES-3** | Puntos de control no-salteables | ciertas rutas no se pueden evitar; verificado por alcanzabilidad sobre la estructura compilada | `interrupt()` de LangGraph · middleware de auth · guards |
| **DES-4** | Estado durable / resumible | un fallo no reejecuta lo completado | PostgresSaver · event store · cola con checkpoints |
| **DES-5** | Procedencia / trazabilidad | toda salida rastrea a su evidencia; join key por nodo | OTel + Neo4j W3C PROV · logs estructurados · audit trail |
| **DES-6** | Contratos tipados en fronteras | interfaces tipadas y chequeadas (`consumes`/`produces`) | Pydantic · TypeScript types · OpenAPI · protobuf |
| **DES-7** | Evaluabilidad con compuertas | calidad medida por gates que BLOQUEAN (umbral → CI rojo) | RAGAS/DeepEval · tests de contrato · lighthouse CI |
| **DES-8** | Proof en el toolchain DEL producto | la verificación corre en el entorno del producto, no de la fábrica | pytest/mypy (Py) · tsc/vitest/eslint (TS) · detox (mobile) |
| **DES-9** | Frontera de aislamiento | el producto no contamina a la fábrica ni viceversa | venv/sys.path · workspace · container |

> Esta tabla ES el contenido del **skill de diseño** (§4). Crece: cuando un dominio nuevo (Mobile, IoT)
> destapa una primitiva no listada, se agrega acá — es la cantera viva. Cada primitiva nombra el
> CONCEPTO y deja la tecnología abierta.
>
> **Espejo legible-por-máquina (B1)**: el catálogo vive como DATO en `reference/primitives.yml` (single
> source que el skill y el check `design_coverage` consumen); esta tabla es el espejo humano. Un test ata
> ambos (`tests/test_design.py`): agregar una primitiva = editar el YAML + esta tabla, nunca el validator.

## 4. Dónde viven las primitivas: el skill de diseño (tiempo de DISEÑO)

Las primitivas de DISEÑO se invocan **en el momento que la fábrica se diseña**, no en runtime. Viven en
un **skill** de Claude Code (la primitiva nativa para procedimiento a-demanda; ARCHITECTURE §8, ASF/ADR-001).
El flujo (detallado en `ROADMAP.md §Operación`):

1. **Spec inicial** → qué fábrica, qué dominio, qué debe producir, requisitos (SDD, fuente única de verdad).
2. **Planificación SDD** (el skill + la potencia de planificación de Claude Code): por cada primitiva de
   diseño que el dominio requiere, el modelo **elige la tecnología** que la provee y la **declara en el
   diseño/spec** (ej.: dominio agente → DES-2/3 vía LangGraph; dominio web → DES-2 vía router + DES-6 vía
   TS types). La elección es JUICIO (no determinista) bajo la filosofía; queda como artefacto revisable.
3. **Build determinista** (M0–M8): el modelo genera el 100%; la columna verifica; M8 construye de verdad.

La regla dura (ADR-012): **ninguna tecnología se hardcodea en `src/metafactory/`**. Si aparece `import copier`
o `langgraph` en el sustrato, es un bug de filosofía: esa decisión pertenece al plan o al spec.

## 5. El SDD formal SOTA que se adopta

Estado del arte (~2026): **GitHub Spec Kit · Kiro (AWS) · Tessl** formalizan el ciclo
`spec → plan → tareas → verificación` con fuente única de verdad, **pero lo enforced con prompts**
(ADR-003). El Meta-Factory adopta **ese mismo ciclo con DIENTES**: M0 rehúsa specs incompletas (corta
una compuerta), el RTM re-derivado corta el CI ante UNSATISFIED. No inventamos un SDD: tomamos el SOTA
y lo volvemos determinista. Ése es el precedente que dejan estos specs.

## 6. Cómo leer esto junto al resto

- La SEGURIDAD (§2) es fija → `ARCHITECTURE.md §3` (los 13 invariantes), `SELF-IMPROVEMENT.md`.
- El DISEÑO (§3) es abierto → este doc es la cantera; el `ROADMAP.md` lista los incrementos que lo construyen.
- Las DECISIONES irreversibles → `ADR-011` (100% generado, muere I-5), `ADR-012` (primitivas no herramientas).
