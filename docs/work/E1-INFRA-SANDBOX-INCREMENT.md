<!-- meta:doc sha=abc97850c456ebc248d14bfb46d101dd6370db2e updated=2026-06-16T01:43Z -->
# Incremento E1-INFRA-SANDBOX

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-16T01:43Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
La **infra** de una fábrica deja de ser L3 descriptivo (`tech/primitive/status`) y se vuelve EJECUTABLE:
se DECLARA en el spec (`machinery.infra`: services/topología + el glue a emitir + el ciclo de vida), se
GENERA (acción `emit_infra`, paralela a `emit_harness` de D2) y un gate la LEVANTA en el sandbox y un
proof la USA (check `infra_up`, orquestador como `product_env` de C3). El sustrato no nombra tech (ADR-012);
`up`/`proof`/`down` son DATA que el plan eligió. La columna L4 sigue heredada (no spec-driven).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **El seam (`infra_up`)** — check orquestador: `up` en background → reintenta `proof` contra el servicio vivo → teardown SIEMPRE (finally). Diente embebido de dos lados (infra caída ⇒ proof rojo, si no es decorativo). Registry. Reproducible por bloqueo (`test_infra.py`: positivo · servicio que no levanta · proof decorativo · teardown limpio · 2º dominio). | ⏳ |
| 2 | **`emit_infra` + dientes M0** — acción de build que escribe el glue de `machinery.infra.emit` desde DATO; validator suma shape-teeth (service sin `name` / emit sin `dest`/`content` → M0 rojo). | ⏳ |
| 3 | **Demostración viva (dummy)** — `machinery.infra` + estación s03 (servicio TCP stdlib) en la dummy; M0–M8 + `product-run` + `ci --rederive` 4/4 (re-pin); ASF proxy intacto (1/1). | ⏳ |
| 4 | **Cierre** — STATE/LOG/ROADMAP + este doc; `meta check` verde; `meta increment close`. | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `infra_up` corre dos lados POR BLOQUEO: infra levanta + proof la usa → exit 0; infra caída / proof que
   no usa el servicio → rojo (`test_infra.py`, runtime real con puertos efímeros).
2. Teardown garantizado: tras `infra_up` el recurso queda libre (no hay proceso colgado).
3. 2º dominio (principio #6): un servicio de forma distinta pasa por el MISMO kind, sin rama por-tech.
4. `emit_infra` escribe el glue declarado desde DATO; M0 RECHAZA infra malformada (shape-teeth, sin nombrar tech).
5. Dummy = línea de 4 estaciones (s03 infra): M0–M8 + `product-run` + `ci --rederive` 4/4 verdes (re-pin);
   ASF intacto (pin 1/1). Demo VIVO por CLI: el servicio levanta y el proof cliente lo usa.
6. `meta check` verde (suite crece); árbol limpio al cierre.
