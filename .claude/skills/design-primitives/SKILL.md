---
name: design-primitives
description: >-
  Design-time procedure for the Meta-Factory: given a NEW factory's domain, map the design
  primitives (DES-*) it requires, choose the technology that provides each, and declare them in the
  factory-spec. Use when designing/planning a new factory or filling a spec-stub's tech choices.
  Materializes reference/PRIMITIVES.md §3. The technology is a PLAN choice (ADR-012) — never hardcoded
  in src/metafactory/. Output is verified by `spec.cli design-review` — the M0 design gate (B2): a tech
  per required primitive (plan) AND a verifier per requirement (criterios). M0 refuses an incomplete design.
---

# Skill · Primitivas de diseño (mapear dominio → primitivas → tecnología)

> Sos el diseñador de una fábrica nueva. Tu trabajo NO es generar código: es producir el **diseño**
> (un `factory.spec.yml` v2) que el build (M0–M8) consumirá. La tecnología la elegís **vos, acá, por
> juicio** bajo la filosofía — y la **declarás en el spec como DATO**. El sustrato (`src/metafactory/`)
> no conoce ninguna tecnología (ADR-012); si te dan ganas de "agregar un backend", es un bug de filosofía.

## Cuándo me usás
- Llega un dominio nuevo (web, mobile, IoT, data-pipeline, lo que sea) y hay que diseñar su fábrica.
- Hay un spec-stub con `domain.produces` + (opcional) `domain.required_primitives` y faltan las tech.

## El catálogo (single source)
Las primitivas de DISEÑO viven como DATO en `docs/reference/primitives.yml` (espejo humano:
`PRIMITIVES.md §3`). Son CONCEPTOS (qué resuelve una herramienta), no herramientas. Hoy: DES-1..DES-13
(andamiaje regenerable · topología verificable · puntos de control no-salteables · estado durable ·
procedencia · contratos tipados · evaluabilidad con compuertas · proof en el toolchain del producto ·
frontera de aislamiento · análisis estático con dientes · currency/frescura de API · esquema versionado
+ queries chequeados · cadena de suministro/seguridad del producto). DES-10..13 las destapó el dominio
full-stack-kotlin (criterios duros). **Leé el YAML antes de mapear** — es la cantera viva y puede crecer.

## Procedimiento (4 pasos)
1. **Entender el dominio.** Leé `domain.produces` y lo que la fábrica debe garantizar. Preguntá: ¿qué
   invariantes de producto hay que poder VERIFICAR? Cada invariante verificable apunta a una primitiva.
2. **Mapear primitivas requeridas.** Por cada invariante, elegí la primitiva DES que lo captura. Anotalas
   en `domain.required_primitives: [DES-x, …]`. Regla: una primitiva entra sólo si el dominio la NECESITA
   (honestidad, SAFE-7) — no infles la lista. Si un invariante no encaja en ninguna DES, es una **primitiva
   nueva**: agregala a `primitives.yml` + a `PRIMITIVES.md §3` (la cantera crece), no al sustrato.
3. **Elegir la tecnología por primitiva (JUICIO).** Para cada primitiva requerida, elegí la tech que la
   provee en ESTE dominio (dominio agente → DES-3 vía `interrupt()`; web → DES-3 vía middleware de auth;
   IoT → DES-3 vía secure-boot). Declarala en una `capability` con `{primitive, tech, invariant, proof,
   status}`. La elección es revisable (queda en el spec), no determinista. Mirá `example_techs` del catálogo
   como disparador, no como lista cerrada.
4. **Cerrar el diseño con stations + requisitos.** Convertí las capacidades en una línea `station_sequence`
   (con `depends_on` y `proof_checks` que declaran `runs_in: product_env` + `toolchain`), y atá los
   requisitos con `satisfied_by` (estaciones) y `verified_by` (proof_checks reales).

## Verificá tu propio output (los dientes — ahora en M0)
```
PYTHONPATH=src python3 -m metafactory.spec.cli validate       <spec>   # gramática v2 bien formada (A1)
PYTHONPATH=src python3 -m metafactory.spec.cli design-review   <spec>   # blueprint COMPLETO: plan + criterios (B2)
```
- `design-review` es **la compuerta M0** (B2): corre dentro de la meta-estación m00. Es el flujo SDD de
  diseño con dientes, en dos fases:
  - **plan** — cada `required_primitive` tiene una capability con tech, y toda `primitive` referenciada
    existe en el catálogo (esto era `design-coverage`, B1; sigue disponible como sub-check).
  - **criterios** — **cada requisito cita un `verified_by`** (un proof_check real). Un requisito sin
    verifier es un diseño SIN terminar (la fase de criterios de verificación del SDD).
- Sólo se activa si la spec declara `domain.required_primitives` (aseverás "pasé el flujo de diseño"):
  ahí M0 te exige completitud TOTAL. Un stub sin primitivas no es un blueprint — pero tampoco se construye.
- Exit 0 ⇒ blueprint listo para el build. Exit 1 ⇒ el diseño NO está listo (`plan:` te falta una tech ·
  `criterios:` un requisito sin verifier). Si `validate` o `design-review` dan rojo, no narres "está
  completo": probalo. M0 lo rehúsa igual.

## Las reglas duras (no negociables)
- **Tech en el spec, NUNCA en el sustrato** (ADR-012). `src/metafactory/` no importa ni nombra tecnología.
- **Honestidad de status** (SAFE-7): `planned` mientras es diseño; `declared-deferred` si está especificado
  pero su codegen se difiere; `built` SÓLO con `proof`. No marques `built` lo que no construiste.
- **La seguridad no se diseña**: las primitivas SAFE-* (la columna) las hereda toda fábrica; vos sólo
  diseñás las primitivas de DISEÑO (DES-*).
