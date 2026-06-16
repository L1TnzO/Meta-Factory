<!-- meta:doc sha=0c5733ba01b7e2fd08a38ab95e6a9ae7887f8c0c updated=2026-06-16T18:47Z -->
# ADR-014 — Paridad de dos dominios: ningún mecanismo de sustrato promueve probado en uno solo

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-16T18:46Z |
| Decide | el orquestador (sesión MATURITY-PLAN), bajo el mandato del ingeniero (anti-overfitting, 2026-06-16) |
| Generaliza | ADR-012 (primitivas no herramientas), I-3 (frontera del determinismo), SAFE-6 (sombra determinista universal), principio #6 del `work/ROADMAP.md` |
| Referencia | `work/MATURITY-PLAN.md` (§2, §6), `reference/F1-AUDIT-REGEN-VS-LEGACY.md §8/§12`, ADR-011, ADR-013 |

## Contexto

ADR-012 fijó que el sustrato no hornea herramientas y dejó, como **consecuencia narrada**, el anti-overfit:
"cada capa del motor se valida con ≥2 dominios radicalmente distintos antes de promover; si algo sólo
sirve para un stack, es supuesto no parametrizado". Era un **principio sin diente**.

F1 expuso el riesgo en concreto. La auditoría head-to-head (`F1-AUDIT §12`) mostró que el ASF regenerado
emite un producto DELGADO y que cerrar ese hueco —volver bueno a Agent_RE— es la tentación exacta de
**hornear conocimiento de ASF en el sustrato** (un generador LangGraph, un saver Postgres, un scorer
RAGAS) para "que ande ya". Si eso pasa, la Meta-Factory se vuelve buenísima haciendo ASF y, para Full-Stack,
hay que iterarla una y otra vez: el overfitting que el ingeniero pidió evitar explícitamente.

SAFE-6 dice que **toda regla que no deba saltearse tiene un detector/impedimento; la narrativa declara, el
código garantiza**. La regla de los dos dominios no tenía sombra. El `MATURITY-PLAN` —que profundiza la
Fase F justo cuando la presión por hornear tech es máxima— **no puede arrancar** sin volverla compuerta.

## Decisión

1. **Definición.** Un *mecanismo de sustrato* es código nuevo o modificado en `src/metafactory/` o `seed/`
   que aporta una **capacidad** de generación, verificación o gating (no un fix). La tech específica de un
   dominio (LangGraph, Neo4j, React, RAGAS…) NUNCA es mecanismo de sustrato: es contenido de fábrica
   (`factories/<x>/`, `factory.spec.yml`) por ADR-012.

2. **La compuerta (promoción).** Un mecanismo de sustrato **no promueve** —no cierra su incremento ni una
   fábrica puede depender de él— hasta tener una **proof que pasa en ≥2 fábricas de dominios radicalmente
   distintos**. Experimentar/prototipar en un solo dominio está permitido; **confiar y cerrar, no**.

3. **"Radicalmente distinto", operacional.** Los dos dominios deben diferir en **toolchain de producto**
   (p.ej. Python/pytest ↔ TypeScript/vitest) **y** en la mezcla de primitivas de diseño (`PRIMITIVES.md §3`)
   que ejercen. Una segunda fábrica del mismo stack NO cuenta como segundo dominio (no ejerce la generalidad).

4. **La sombra (diente).** Un check `generality_parity` (`verify/checks/`) FALLA (rojo) si un mecanismo
   marcado como sustrato-nuevo tiene proofs para <2 fábricas de dominios distintos. Se cablea al cierre de
   incremento / `external_ci`. Extiende —no reemplaza— el guard de ADR-012 (cero tokens de tech en `src/`).

5. **La medición dura.** `git diff src/metafactory/` atribuible a UN solo dominio = **0 líneas**. Todo lo
   específico de un dominio vive en su carpeta de fábrica. El sustrato sólo crece en mecanismo compartido.

6. **El instrumento.** Para la fase de madurez, **Full-Stack-Factory construida en lockstep** es el segundo
   dominio canónico: cada mecanismo de sustrato (generación-viva por LLM, `eval_gate`, `live_run`) se cierra
   probado en ASF **y** Full-Stack a la vez, no en serie.

## Consecuencias

- **El anti-overfit deja de ser promesa y se vuelve mecánico** (SAFE-6 satisfecho): la disciplina la
  sostiene un exit code, no la prosa — la lección de los docs-sin-cadencia, un nivel arriba.
- **Costo marginal por dominio decreciente**: una vez que un mecanismo pasó la paridad, toda fábrica nueva
  lo hereda gratis. F2 sale más barata que F1; F3 que F2. "Que la factory salga madura sin iterar tanto."
- **La prueba falsable** (`MATURITY-PLAN` MAT-7): el 3er dominio (Mobile/IoT) debe salir maduro con
  `git diff src/metafactory/` = 0. Si obliga a tocar el sustrato, hubo overfitting → el mecanismo culpable
  se rediseña antes de promover. La decisión es, por diseño, refutable.
- **Más lento por mecanismo, honesto en generalidad**: cerrar exige dos dominios verdes. Es el precio de no
  re-iterar la plataforma después. Aceptado.
- **Gobierna la promoción, no la exploración**: se puede prototipar en un dominio; lo que la compuerta
  prohíbe es **declararlo general** sin la segunda prueba.

## Rechazado

- **"Probarlo en un dominio y confiar en que generaliza."** Es exactamente lo que produce el overfitting
  latente; sin diente, la disciplina se erosiona bajo presión de entrega.
- **"Un segundo dominio del mismo stack como segunda prueba."** Mismo toolchain ⇒ no ejerce la generalidad;
  da falso verde. Por eso §3 exige toolchain Y primitivas distintas.
- **"Hornear la tech del dominio detrás de un flag/branch por dominio en el sustrato."** Sigue siendo
  overfitting (ADR-012): la rama por-tech está prohibida; la variación vive en `via`/spec (dato), no en `if`.
