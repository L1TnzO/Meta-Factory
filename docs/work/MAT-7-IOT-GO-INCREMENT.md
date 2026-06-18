<!-- meta:doc sha=8168435739cbedaa00ba91e54ac8e840cb55f1f1 updated=2026-06-18T01:47Z -->
# Incremento MAT-7-IOT-GO

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-18T01:47Z) (creado 2026-06-18T01:26Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo

La **prueba final de no-overfitting** (MATURITY-PLAN MAT-7 / ROADMAP F3): un **3er dominio radicalmente
distinto** — una **IoT-Factory en Go** (gateway/broker/telemetría: el lenguaje real de IoT) — generado 100%
desde su spec por un codegen LOCAL (en la fábrica, ADR-012), que emite un producto Go real y lo PRUEBA en su
propio toolchain (DES-8, `go test`), pasando M0–M8 **con `git diff src/metafactory/ + seed/` = 0 líneas**.
Go es el 3er lenguaje DISJUNTO (Go ⟂ python ⟂ ts) y ya está en el canon de `generality_parity` (`_LANG`),
así que el sustrato no se toca. La fábrica HEREDA gratis los mecanismos generales (generate · product_env ·
infra_up) — la **propiedad de composición** (§5): la 3ª fábrica sale madura sin iterar el sustrato. La tech
diverge del skeleton (C aspiracional → Go) por ADR-012 (la tech es elección de PLAN); documentado honesto.

## Diseño (el porqué)

- **Por qué Go, no el C del skeleton**: el gate de MAT-7 exige `generality_parity` verde, que rechaza un 3er
  dominio que comparta LENGUAJE de producto con otro. El skeleton mobile usa `tsc/jest` (= el TS de
  full-stack → colisiona). Go es disjunto, **ya está en `_LANG`** (cero toque al sustrato), hermético
  (stdlib, `GOPROXY=off`, sin red) e instalado (1.26). Es un lenguaje IoT real (gateways/brokers/telemetría),
  fiel al **mix de primitivas** del skeleton IoT (DES-2/3/4/5/6/8/9). El C literal del skeleton no corre acá
  (protoc/qemu/unity no instalados). ADR-012: la tech es elección de plan, no del sustrato.
- **El sustrato no se toca** (ADR-014, la medición dura §6): toda la tech Go vive en `factories/iot/`
  (codegen + spec). `git diff src/metafactory/ + seed/` por este dominio = **0 líneas**. La maquinaria
  (engine + columna + product_env + infra_up + generate + materialize_line) ya existe — la fábrica la hereda.
- **`go test` ES el gate** (análogo del `mypy --strict`/`tsc --strict`): un drift del contrato de mensajes
  tipados rompe `go build`/`go test ./contract`; un nodo huérfano rompe el validador BFS de topología; saltear
  el gate de firma OTA rompe `go test ./ota`. Ésa es la prueba por bloqueo de cada primitiva.
- **Composición (sale madura)**: s3 levanta un broker Go VIVO sobre socket-Unix (el análogo Go EXACTO del
  `node:sqlite` de full-stack y del socket stdlib de dummy) por `infra_up` — demuestra que un mecanismo
  general compone para un 3er toolchain sin tocar el sustrato.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `specs/iot.factory.spec.yml` real (L0–L5: caps DES-6/2/3/5/4, blueprint `domain.product` Go, línea s0 generate+contract / s1 topología BFS / s2 OTA-gate+procedencia / s3 telemetría durable vs broker vivo, machinery harness+infra) — M0 valida 0 problemas | ✅ |
| 2 | `factories/iot/codegen/scaffold_product.py` (determinista, lee el blueprint, emite el producto Go — 12 archivos) + registrar (`meta new`) + M0–M8 verde | ✅ |
| 3 | Línea viva e2e: `product-run` PASS · M0–M8 verde · `pin` 4/4 · `ci --rederive` 4/4 == pineado (re-corre `go vet`/`go test`/broker en clon limpio) · RTM COMPLETE 5/5 | ✅ |
| 4 | `generality_parity` verde con Go como 3er dominio disjunto en product_env/generate/infra_up; `git diff src/metafactory/ + seed/` = **0 líneas** | ✅ |
| 5 | Bloqueo VIVO (4 dientes sobre el producto emitido): drift de contrato → `go vet` rojo (s0) · nodo huérfano → BFS rojo (s1) · saltear OTA → rojo (s2) · broker caído → `infra_up` rojo (s3); regen → verde | ✅ |
| 6 | Docs (STATE/ROADMAP/MATURITY-PLAN + evidencia) + cierre; dummy+ASF+full-stack intactos (principio #4) | ✅ |

## Evidencia (verificable, no narrada)
- **Línea viva e2e**: `product-run --factory iot` PASS (s0 `go vet ./...`+`go test -count=1 ./contract` ·
  s1 `go test ./topology` · s2 `go test ./ota ./provenance` · s3 `infra_up` → broker Go vivo + `go test
  ./telemetry`). M0–M8 verdes (m05 rtm · **m06 clean_runner re-deriva la línea Go en clon hermético ==
  pineado** · m07 agent_shadow+command_runs · m08 product_e2e). pin **4/4**. **`ci --rederive` 4/4 ==
  pineado** (clon limpio re-corre `go vet`+`go test`+broker; `GOPROXY=off`, hermético, sin red). RTM
  **COMPLETE 5/5** (req→capability→station→artifact Go REAL bajo `build/product/`).
- **La medición dura de no-overfitting (§6)**: **`git diff src/metafactory/ + seed/` por MAT-7 = 0 líneas**.
  Toda la tech Go vive en `factories/iot/` (codegen 12-archivos) + `specs/iot…`. El motor generalizó al
  **3er toolchain disjunto** (Go ⟂ python ⟂ ts) con **cero toques al sustrato**. Go ya estaba en `_LANG`
  (canon de `generality_parity`) ⇒ ni el token de lenguaje hizo falta. La 3ª fábrica salió **madura sin
  iterar el sustrato** (MATURITY-PLAN §6.4): heredó generate · product_env · infra_up gratis.
- **Capstone — paridad de 3 lenguajes**: `generality_parity` verde con iot en `domains` de
  product_env/generate/infra_up; iot prueba los 3 verde y es radicalmente distinto de full-stack (`langs
  {go}≠{ts,test}`, primitivas distintas) **y** de ASF (`{go}≠{python}`). `meta check` **6/6**.
- **Bloqueo VIVO (4 dientes sobre el producto Go emitido; corromper→rojo, regen→verde)**:
  1. **s0/DES-6** drift del contrato (`Value float64→string`) → `go vet` exit 1 (`cannot use 1.5 as string`).
  2. **s1/DES-2** nodo huérfano en la topología (`+{ghost/lonely/void}`) → `TestDeclaredTopologyIsValid`
     FAIL (`unreachable from root`), exit 1.
  3. **s2/DES-3** saltear el gate OTA (`if !verify → if false`) → `TestApplyRefusesUnsigned` FAIL, exit 1.
  4. **s3/DES-9** broker que no liga (`os.Exit(0)` antes de `net.Listen`) → `infra_up` exit 1 (`el proof no
     alcanzó la infra viva`). El diente negativo embebido de E1 ya muerde con `go test -count=1` (sin él,
     el cache de `go test` devolvería el PASS rancio — la trampa de cache de Go, atrapada y resuelta).
  Tras cada diente: `product-run` regenera → **GREEN**, `ci --rederive` 4/4 == pineado.
- **No rompe nada (principio #4)**: dummy `ci` **PASS** · full-stack `ci` **PASS** · ASF **intacto** (0
  archivos tocados; sus 11 proofs pineados recomponen verde, keyless). Congelado `@ b1fcb1f` intocado.
- **Decisión de diseño (honesta)**: la tech DIVERGE del skeleton (C/protoc/qemu aspiracional, no instalados)
  → **Go** (ADR-012: la tech es elección de PLAN, no del sustrato). Go provee el MISMO mix de primitivas
  IoT del skeleton (DES-2/3/4/5/6) y es un lenguaje IoT real; es disjunto (requisito de `generality_parity`)
  y hermético. El skeleton mobile (RN/`tsc`) habría COLISIONADO con el TS de full-stack → no sirve para la
  prueba de no-overfitting. Wart heredado (no de MAT-7): el stub vestigial `domain/iotgw.py` (Python-shaped,
  frontera I-5 del chasis — full-stack lleva `webapp.py`, ASF `agent_system.py`); el producto REAL es el
  árbol Go en `build/product`.

## Criterio de cierre (demostrable, no narrable)
1. Un producto IoT en Go GENERADO compila (`go vet`/`go build`), pasa `go test` por estación en su propio
   toolchain (DES-8) y **levanta su broker vivo** (DES-9) — todo por `product_env` + `infra_up`.
   `product-run` PASS · M0–M8 verde · `ci --rederive` == pineado.
2. **`generality_parity` verde** con Go como 3er lenguaje disjunto (Go ⟂ python ⟂ ts) co-validando
   product_env/generate/infra_up; **`git diff src/metafactory/ + seed/` por iot = 0 líneas** (la prueba de
   no-overfitting, §6: la 3ª fábrica sale madura sin tocar el sustrato).
3. **Bloqueo vivo (4 dientes)**: drift de contrato → `go test` rojo · nodo huérfano → BFS rojo · OTA salteable
   → rojo · broker caído → `infra_up` rojo (no decorativo).
4. dummy + ASF + full-stack intactos (`ci` 5/5 · 11/11 · 6/6); congelado `@ b1fcb1f` intocado; `meta check` verde.
