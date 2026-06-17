<!-- meta:doc sha=a1491a7202bb51c71bc188e8c9bda6161de5e9c4 updated=2026-06-17T16:56Z -->
# Incremento MAT-3-PRODUCT-INFRA

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-17T16:56Z) (creado 2026-06-17T16:13Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo

Cablear `infra_up` (E1) al **M8 del PRODUCTO** de forma genérica: el producto generado se prueba en su
propio toolchain (DES-8) **contra la infra VIVA declarada**, no contra un glue de línea ni un mock. La
fábrica declara los services en `factory.spec.yml`; con la infra caída el proof del producto cae a rojo
(diente de dos lados de E1). Co-validación en **2 dominios** (principio #6): **ASF** (Postgres checkpointer
real + Neo4j linaje real, contenedores efímeros) y **Full-Stack** (su DB relacional viva, vía el producto).

## Decisión de fidelidad (mandato del ingeniero, 2026-06-17)

La infra de ASF en la **línea verde por defecto** usa **contenedores reales** (Postgres + Neo4j en docker,
efímeros, health-gate, teardown SIEMPRE) — máxima fidelidad a `F1-AUDIT §12` y paridad con la legacy. El
trade-off ACEPTADO: `ci --rederive` (clon limpio, con dientes) pasa a **requerir docker + imágenes**. No es
fake-green: verificado en este entorno que el daemon levanta Postgres/Neo4j, son alcanzables desde el host
(el path del producto) y el teardown libera el recurso; las imágenes están **cacheadas** (re-derive sin red
mientras estén presentes). Si docker/imágenes faltan, el gate cae a rojo HONESTO (no se finge verde).
Full-Stack conserva su DB viva por socket-Unix (node:sqlite, hermética) — el contenedor lo ejerce ASF; así
el MISMO mecanismo de sustrato queda probado sobre **dos kinds de infra** (docker-container ⟂ socket-service)
y **dos toolchains** (python ⟂ node), evidencia de generalidad MÁS fuerte.

## Diseño (el porqué)

- **El mecanismo de sustrato es MÍNIMO y compartido.** `infra_up` ya: levanta `up` en background (process
  group), reintenta `proof` contra el servicio vivo, hace teardown SIEMPRE (`down` + killpg) y exige el
  diente de dos lados (infra caída → proof rojo). Ya scrubbea el env (DES-8/9) y corre el proof con
  `cwd=workdir`. Lo ÚNICO que falta para "M8 del producto" es un **`bootstrap` opcional** (una vez, antes
  del retry-loop) que prepare el toolchain del producto — exactamente la composición `product_env ⊕
  infra_up`. Sigue sin nombrar tech (ADR-012): `bootstrap`/`up`/`proof`/`down` son argv-DATA. El contenedor
  (`docker run` foreground + `docker rm -f` en `down`) es DATA de fábrica, no rama del motor.
- **Por qué el producto, no el glue.** Hoy `infra_up` prueba un cliente standalone (full-stack s2:
  `dbclient.ts`). MAT-3 hace que el `proof` sea el **test del PRODUCTO** (su `domain/`/handler corriendo en
  su venv/node), de modo que la infra viva respalda el producto REAL. El diente de dos lados deja de ser
  decorativo: con Postgres caído, `test_state.py` (resume vs checkpointer) DEBE fallar — prueba que el
  producto usa el checkpointer vivo, no MemorySaver.
- **Re-derivación con infra real (reconciliar SAFE-3).** El producto y sus artefactos se PINEAN como hasta
  ahora; `ci --rederive` re-corre la línea (re-levanta los contenedores) en clon limpio y exige el veredicto
  pineado. El no-determinismo de red NO entra: los proofs gatean por PROPIEDADES (resume sin reejecución,
  traversal de linaje con la join-key), no por bytes del modelo (eso es MAT-5).
- **Anti-overfitting (LEY DE CAPAS).** El `bootstrap` de `infra_up` es mecanismo general (lo hereda toda
  fábrica). Las imágenes/drivers/topología viven en `factories/<x>/` y los specs. `git diff
  src/metafactory/` por dominio = 0 (se mide). `generality_parity` re-certifica `infra_up` con su nueva
  capacidad probada en 2 dominios.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Sustrato**: `infra_up` acepta `bootstrap` opcional (una vez, scrubbed, antes del retry-loop) + cableado en registry/main; tests por bloqueo (bootstrap corre una vez · bootstrap roto → rojo antes de `up` · proof del producto contra servicio vivo verde · infra caída → rojo se mantiene). `git diff` acotado al mecanismo | ✅ 2026-06-17T16:18Z |
| 2 | **Co-validación Full-Stack**: el PRODUCTO (test de integración tipado al contrato) respaldado por la DB viva; s2 con `infra_up` (proof = test del producto, no el glue) + bootstrap del toolchain (npm install); re-pin · product-run · `ci --rederive` 4/4 == pineado. `git diff src/metafactory/` = 0 | ✅ 2026-06-17T16:28Z |
| 3 | **ASF Postgres (s3)**: codegen `durable_checkpointer` (PostgresSaver real) + test resume-no-reexec **cross-instancia** (instancia fresca contra la MISMA PG resume sin reejecutar — MemorySaver no podría); s3 → `infra_up` (up=`docker run postgres:16-alpine`, bootstrap=`setup_env.py`, proof=`pytest test_state.py`, down=`docker rm -f`); deps += langgraph-checkpoint-postgres/psycopg. product-run + m06 clean + `ci --rederive` **7/7 == pineado** (venv fresco + PG real); teardown limpio. `git diff src/metafactory/` = 0 | ✅ 2026-06-17T16:38Z |
| 4 | **ASF Neo4j (s2)**: s2 ACTIVADA (de `off`→`always`); codegen `LineageStore` (driver neo4j, PROV salida↔evidencia) + test traversal backward/forward + join-key vs Neo4j real; s2 → `infra_up` (up=`docker run neo4j`, bootstrap=`setup_env.py`, down=`docker rm -f`); deps += neo4j; mypy override `neo4j.*`. **RTM 8/8** (s2 sube cobertura, REQ-F-007) · pin 8/8 · `ci --rederive` 8/8 == pineado (venv fresco + PG + Neo4j); teardown limpio. `git diff src/metafactory/` = 0 | ✅ 2026-06-17T16:46Z |
| 5 | **Promoción + paridad**: `machinery.infra` `built` en ambos specs; `parity.yml` agrega ASF a `infra_up` (general en 2 KINDS de infra: socket node + docker python); `generality_parity` verde LEGÍTIMO; demos VIVAS por CLI (infra caída → proof del PRODUCTO rojo, 3 frentes) | ✅ 2026-06-17T16:49Z |
| 6 | **Docs/evidencia**: STATE · ROADMAP · MATURITY-PLAN (MAT-3 ✅) · evidencia + cierre; dummy intacta | ✅ 2026-06-17T16:53Z |

## Criterio de cierre (demostrable, no narrable)
1. `infra_up` corre un `bootstrap` declarado una vez y luego el proof del PRODUCTO contra la infra viva; el
   diente de dos lados (infra caída → proof rojo) se mantiene. Tests nuevos verdes; suite sube.
2. **ASF**: s3 prueba **resume-sin-reejecución vs Postgres REAL** y s2 **traversal de linaje vs Neo4j REAL**
   (contenedores efímeros, teardown SIEMPRE). Con el contenedor caído, cada proof cae a rojo. RTM sube
   (s2 activada). `product-run` + `ci --rederive` == pineado (re-levanta los contenedores).
3. **Full-Stack**: el endpoint/handler del PRODUCTO respaldado por la DB viva pasa su gate; DB caída → rojo.
   `ci --rederive` == pineado.
4. **2 dominios, mismo kind**: `infra_up` product-backed verde en ASF (docker) y Full-Stack (socket);
   `generality_parity` verde LEGÍTIMO. `git diff src/metafactory/` = solo el mecanismo `bootstrap` (anti-overfit).
5. `meta check` verde; dummy intacta; demos vivas por CLI registradas en §Evidencia.

## Evidencia (re-verificable, no narrada)

**Sustrato (P1, único cambio en `src/`).** `infra_up.run(...)` acepta `bootstrap` opcional: corre UNA vez en
`workdir` con env scrubbed (DES-8) ANTES de `up` (un bootstrap roto no cuesta contenedor) y NO se re-corre en
la fase negativa (diente de dos lados intacto). Cableado en `registry.py` (5º arg JSON) + `main()`. Tests por
bloqueo (`tests/test_infra.py`, 3 nuevos): corre exactamente una vez · falla antes de `up` (su `up` nunca
lanza) · pasa por el registry como DATA. `git diff src/metafactory/ + seed/` = **~10 líneas funcionales, solo
`bootstrap`** (medido en P2/P3/P4: 0 líneas adicionales — anti-overfit §5).

**ASF (P3 Postgres + P4 Neo4j), docker REAL.**
- s3 `resume_no_reexec` → `infra_up`: `up`=`docker run postgres:16-alpine` (efímero, limpia stale), `bootstrap`=
  `setup_env.py` (venv + `langgraph-checkpoint-postgres`/`psycopg`), `proof`=`pytest test_state.py`, `down`=
  `docker rm -f`. El test `test_resume_without_reexecution_vs_real_postgres` arma el grafo con un
  `durable_checkpointer` (PostgresSaver) en **instancia A** (corre research+synthesize→interrupt) y resume en
  una **instancia B FRESCA** contra la MISMA Postgres SIN re-ejecutar (MemorySaver no podría). proof `s3.json`
  exit 0, `writer: seed/verifier.py`.
- s2 ACTIVADA (`off`→`always`) `lineage_join_key` → `infra_up`: `up`=`docker run neo4j:5.26.0-community`
  (timeout 150 por boot lento), `proof`=`pytest test_lineage.py`. `LineageStore` (driver `neo4j`) recorre
  backward (salida→evidencia) y forward (evidencia→salida) sobre PROV y exige que ningún nodo quede sin la
  join-key. proof `s2.json` exit 0.
- **RTM COMPLETE 8/8** (REQ-F-007 nueva) · pin 8/8 · M0–M8 verde (m05 `rtm_tree` con artifact de linaje · m06
  `clean_runner` re-deriva en clon limpio levantando ambos contenedores) · `ci --rederive` **8/8 == pineado**.
  Sin fugas de contenedor (verificado `docker ps -a` tras cada corrida).

**Full-Stack (P2), socket node:sqlite.** s2 `db_round_trip` → `infra_up`: `bootstrap`=`npm install`, `up`=server
`node:sqlite`, `proof`=`node --test test/db_integration.test.ts` (test del PRODUCTO tipado al contrato, round-trip
create+list contra la DB viva; el glue `dbclient.ts` se removió del emit). product-run PASS · pin 4/4 ·
`ci --rederive` **4/4 == pineado** (clon limpio re-corre npm install + node:test + DB viva).

**Diente de dos lados VIVO (demos por CLI, infra CAÍDA → proof del PRODUCTO ROJO).**
- ASF resume vs Postgres caído → `OperationalError` (FAILED); los tests in-memory (MemorySaver) siguen verdes (4 passed).
- ASF linaje vs Neo4j caído → `ServiceUnavailable` (FAILED).
- Full-Stack producto vs DB caída → `connect ECONNREFUSED db.sock` (# pass 0).

**Anti-overfit + no-regresión.** `infra_up` `general` en `parity.yml` con [dummy, full-stack, agent-systems-factory]
(2 KINDS de infra: socket node ⟂ docker python); `generality_parity` verde LEGÍTIMO (recompone proofs, no
levanta contenedores). dummy intacta (`ci --rederive` 5/5 == pineado). `meta check` verde tras refrescar la
proyección.

**Decisión registrada (mandato del ingeniero).** Contenedores reales en la línea verde por fidelidad a
`F1-AUDIT §12`/paridad legacy ⇒ SAFE-3 pasa a ser **docker-dependiente** (`ci --rederive` requiere docker +
imágenes; cacheadas localmente, re-derive sin red posible). Sin docker/imágenes → gate ROJO honesto, no
fake-green. Verificado al inicio: daemon vivo, Postgres/Neo4j levantan, alcanzables desde el host, teardown libera.
