<!-- meta:doc sha=5fb7f436f023009f24fa5fe2757e5e0d1ba1da87 updated=2026-06-16T13:13Z -->
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
| 1 | **El seam (`infra_up`)** — check orquestador: `up` en background → reintenta `proof` contra el servicio vivo → teardown SIEMPRE (finally). Diente embebido de dos lados (infra caída ⇒ proof rojo, si no es decorativo). Registry. Reproducible por bloqueo (`test_infra.py`). | ✅ `c1abca5` |
| 2 | **`emit_infra` + dientes M0** — acción de build que escribe el glue de `machinery.infra.emit` desde DATO; validator suma shape-teeth (service sin `name` / emit sin `dest`/`content` → M0 rojo). | ✅ `0113408` |
| 3 | **Demostración viva (dummy)** — `machinery.infra` + estación s03 (servicio socket-Unix stdlib) en la dummy; M0–M8 + `product-run` + `ci --rederive` 4/4 (re-pin); ASF proxy intacto (1/1). | ✅ `14d9ae3` |
| 4 | **Cierre** — STATE/LOG/ROADMAP + este doc; `meta check` verde; `meta increment close`. | ✅ |

## Evidencia (re-derivable, no narrada)
- **Seam por bloqueo** (`tests/test_infra.py`, 16 tests; suite `tests/` 429, era 413): levanta+usa → 0 ·
  servicio que no levanta → rojo · **proof decorativo → rojo** (diente embebido) · teardown libera el
  recurso · workdir ausente → 2 · up no lanza → 127 · down corre en teardown · 2º dominio TCP por el MISMO
  kind (principio #6) · registry pass-through sin nombrar tech · `emit_infra` escribe el glue con subst ·
  M0 RECHAZA emit-sin-dest / service-sin-name / content-no-string.
- **Vivo por CLI sobre el glue REAL emitido de la dummy** (tres lados): servicio levanta + proof lo usa
  → exit 0; infra que no levanta → proof no alcanza → exit 1; proof decorativo → `GATE DECORATIVO` exit 1.
- **Línea completa**: M0–M8 verde; `product-run` PASS; `rtm` 4/4 (`REQ-F-004 SATISFIED <- infra_sandbox:
  s03 [build/infra/server.py✓]`); re-pin 4 proof_sha; `ci --rederive` dummy **4/4** (la infra re-deriva en
  árbol limpio) · ASF **1/1** (pin intacto). `meta check` 5/5.
- **Residuales honestos (declarados)**: `emit_infra` no quita un emit stale que se cae del spec (la
  superficie harness sí regenera el dir; infra escribe destinos explícitos); `runs_in` no tiene un valor
  `sandbox_env` propio (uso `product_env`, el más cercano del enum — cambio de gramática fuera de alcance);
  infra real (Postgres/docker-compose) sigue declarada como DATA, ejercida e2e en F1/F2; el socket Unix
  deja un `.sock` stale tras teardown (el server hace `unlink` antes de bind → inocuo; `build/` gitignored).

## Criterio de cierre (demostrable, no narrable)
1. `infra_up` corre dos lados POR BLOQUEO: infra levanta + proof la usa → exit 0; infra caída / proof que
   no usa el servicio → rojo (`test_infra.py`, runtime real con puertos efímeros).
2. Teardown garantizado: tras `infra_up` el recurso queda libre (no hay proceso colgado).
3. 2º dominio (principio #6): un servicio de forma distinta pasa por el MISMO kind, sin rama por-tech.
4. `emit_infra` escribe el glue declarado desde DATO; M0 RECHAZA infra malformada (shape-teeth, sin nombrar tech).
5. Dummy = línea de 4 estaciones (s03 infra): M0–M8 + `product-run` + `ci --rederive` 4/4 verdes (re-pin);
   ASF intacto (pin 1/1). Demo VIVO por CLI: el servicio levanta y el proof cliente lo usa.
6. `meta check` verde (suite crece); árbol limpio al cierre.
