# Incremento FSK-DEPLOY-APPSERVER-PG — el AppServer REAL en un contenedor con PG (deploy de verdad)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO** (2026-06-24T21:20Z)
> (creado 2026-06-24). Cerralo flippeando este header a CERRADO **o** con
> `meta increment close --factory full-stack-kotlin`. Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Lo escribió la sesión que cerró
> FSK-FORM-BROWSER-E2E con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (y por qué es la de MAYOR valor restante)

**EL NÚCLEO + LA SUPERFICIE + LOS VALORES-DERIVADOS + LA UX están COMPLETOS** (modelo · acceso · comportamiento ·
valores-derivados [same/cross-entity depth-N + tiempo] · app-que-corre + TODAS las entidades servidas + frontend
que se VE Y se SUBMITEA en un Chromium REAL + deploy smoke). De acá TODO es **profundidad-de-detalle/breadth**.

Este eje cierra **la última media-verdad del DEPLOY**: hoy `deploy_smoke` (estación **s11**, FSK-DEPLOY) CONSTRUYE
la imagen y levanta el contenedor, pero el ENTRYPOINT del dist = `bin/<pkg>` = **`ObsServerKt`** — el server de
**observabilidad PG-free**. La app REAL (el **AppServer** con CRUD/acceso/PG) **NO se despliega en un contenedor**;
sólo corre bajo `java -cp` directo en s9 (`infra_up`, contra una PG en docker pero el server fuera de contenedor).
Este eje despliega el **AppServer REAL en un contenedor**, hablando con una **PG en una red docker**, y lo
smoke-testea con un **request CRUD REAL** (GET `/<plural>` → la fila sembrada vuelve de la PG → prueba que el
contenedor desplegado ALCANZA su base). Cierra **"la app deploya de VERDAD, no el server de obs"**.

**⚠️ ESTA ES TU DECISIÓN (con más contexto).** El ingeniero la eligió como **la de MAYOR valor restante** (último
gran hito de deploy). Es MÁS involucrada que los últimos ejes (red docker entre 2 contenedores) pero el SUSTRATO ya
soporta docker (MAT-3: ASF corrió Postgres/Neo4j en docker; s9/s11 ya corren `docker run`). Si al investigarla
encontrás que conviene otro orden, en §7 hay alternativas honestas + autoridad para reabrir con `meta increment`.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥600000ms** (el sandbox mata gradle).
**cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del hook `stop_proof`;
usá `cd <raíz> && …`). Debe dar **PASS**, RTM snipeit **25/26** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **Puertos s9**: PG 5436/5437/5438 + servers 18593-18595/18597; **s11 18596**. Tu nuevo deploy elegí puertos
LIBRES (p.ej. host 18598 para el AppServer, y una PG en su red sin publicar puerto al host, o 5442 si publicás).
NUNCA dos corridas en paralelo.

**2) ENTENDÉ la maquinaria de deploy EXISTENTE (s11, FSK-DEPLOY — este eje la EXTIENDE, no la reescribe):**
- **`_dockerfile(pkg)` (~7148 de `codegen/scaffold_product.py`)**: el `Dockerfile` generado. Base
  `eclipse-temurin:21-jre@sha256:<digest REAL>` (pineada por digest, s10 `hermetic_build` lo verifica por grep).
  `COPY` del `build/install/<pkg>` (el dist de `installDist`). **`ENTRYPOINT ["/app/bin/<pkg>"]`** = el launcher de
  Gradle cuyo `mainClass` = **`<pkg>.observability.ObsServerKt`** (PG-free). **ACÁ está el quid**: para correr el
  AppServer en vez del ObsServer, NO necesitás otra imagen — `docker run --entrypoint java <img> -cp '/app/lib/*'
  <pkg>.endpoints.AppServerKt` (override del entrypoint con la misma imagen; el dist ya trae TODAS las libs en
  `/app/lib/`). El AppServer lee env: `FSK_AC_PORT`, `FSK_PG_URL`, `FSK_PG_USER`(def postgres), `FSK_PG_PASSWORD`(def
  metafactory), `FSK_WEB_DIR`(def frontend/dist — NO está en la imagen, pero el smoke CRUD no lo necesita).
- **`_deploy_check_py()` (~7169)**: `tools/deploy_check.py` (urllib stdlib). Hoy HTTP-GETea `/health` y exige
  `{"status":"UP"}`. **ACÁ EXTENDÉS** (o agregás un check hermano): tras `/health`, GETeá **`GET /<plural>`** (lectura
  PÚBLICA, sin token) y exigí que vuelva la fila SEMBRADA (`{"count":N,"rows":[…]}`, N≥1) → prueba que el contenedor
  ALCANZÓ la PG (Flyway migró + `seedRows` corrió + el query jOOQ anduvo). Ese es el DIENTE central de "habla con su DB".
- **`stations/s11.yml` (base) + el del producto (`products/snipeit/stations/s11.yml`)**: el `deploy_smoke` actual.
  `bootstrap` = `installDist` + `docker build -q -t fsk_s11_deploy .` + `docker run -d --name fsk_s11_deploy -p
  18596:18593 fsk_s11_deploy`. `proof` = `deploy_check.py http://127.0.0.1:18596`. `down` = `docker rm -f
  fsk_s11_deploy`. **El ObsServer escucha 18593 dentro, mapeado a 18596 host.**

**3) EL DISEÑO (GENERAL, cero nombres de dominio):** la forma RECOMENDADA es un **check NUEVO** en s11 (p.ej.
`deploy_appserver_live`, `kind: infra_up`, hermano de `deploy_smoke`) que:
   - `bootstrap`: `installDist` + `docker build` (REUSÁ la misma imagen `fsk_s11_deploy` si ya la construyó el check
     hermano, o construí una propia con otro tag) + **`docker network create fsk_s11_net`** + **`docker run -d --name
     fsk_s11_pg --network fsk_s11_net -e POSTGRES_PASSWORD=metafactory postgres@sha256:e013e8…`** (la MISMA PG pineada
     por digest que s9, SIN `-p` al host — sólo en la red) + esperar PG ready (`docker exec … pg_isready` en un loop,
     idiom de s9) + **`docker run -d --name fsk_s11_app --network fsk_s11_net -p 18598:18598 --entrypoint java
     fsk_s11_deploy -cp '/app/lib/*' <pkg>.endpoints.AppServerKt`** con env `-e FSK_AC_PORT=18598 -e
     FSK_PG_URL=jdbc:postgresql://fsk_s11_pg:5432/postgres` (el host de la PG = el NOMBRE del contenedor en la red).
   - `up: []` (el `docker run -d` ya lo dejó corriendo; como `deploy_smoke`).
   - `proof`: `deploy_check.py http://127.0.0.1:18598` extendido (o un `tools/deploy_appserver_check.py` nuevo):
     `/health` UP **+** `GET /<plural>` devuelve la fila sembrada (N≥1).
   - `down`: `docker rm -f fsk_s11_app fsk_s11_pg` + `docker network rm fsk_s11_net` (SIEMPRE, idiom infra_up).
   El DATA (pkg, plural, digest de PG) sale del blueprint, igual que s9/s11. Opt-in: igual que `deploy_smoke`,
   `always` (todo producto FSK lo gana). **Decisión tuya**: ¿check NUEVO (mejor — deja el ObsServer smoke intacto) o
   reemplazás `deploy_smoke`? Recomendación: **check NUEVO** (co-valida ambos deploys; el ObsServer PG-free sigue
   siendo el smoke barato).

**EL DIENTE de dos lados** (NATIVO de infra_up + uno propio):
   - **Propio**: con la red bien cableada, `GET /<plural>` del contenedor desplegado → la fila sembrada (200, N≥1) →
     verde. **Saboteá el wiring** (p.ej. `FSK_PG_URL=jdbc:postgresql://NO_EXISTE:5432/postgres`, o NO conectes el
     AppServer a la red, o quitá el `--network`) → el AppServer no alcanza la PG al boot (Flyway falla → el server
     crashea o `GET /<plural>` da 500) → el proof FALLA → **SÓLO `deploy_appserver_live` rojo**, hermanos s11/s9
     verdes → revertí → verde.
   - **Nativo de infra_up**: contenedor caído tras teardown → el MISMO proof no conecta → rojo (prueba el teardown).

---

## 1. RE-PIN — **SÍ, probablemente** (check NUEVO → estación cambia). LEÉ ESTO:
`compute_proof_sha` (`seed/verifier.py`) hashea **`station_id + (check_name, exit_code)`**. Si AGREGÁS un check
(`deploy_appserver_live`) a s11, el conjunto de `(check_name, exit)` de s11 CAMBIA → el `proof_sha` de s11 cambia →
**hay que re-pinear los 3 productos** (como hizo FSK-DEPLOY al agregar s11). Flujo:
1. Editá `factory.spec.yml` (s11 gana el check en `machinery`/`station_sequence`) **y** sincronizá el `stations/s11.yml`
   committeado a mano **o** `meta station m02 --factory full-stack-kotlin` y revisá `git diff stations/` (revirtiendo
   el drift cosmético de otros sN — ⚠️ editar `station_sequence` re-materializa los PRODUCTOS pero NO el base
   committeado `stations/<id>.yml`).
2. `product-run --product snipeit` (+ default + assets) PASS.
3. `meta pin --factory full-stack-kotlin --all-products` (re-pinea los 3) **o** el flujo de pin que uses.
4. `ci --rederive --all-products` DEBE dar 3/3 == el pin NUEVO.
Si en cambio **REEMPLAZÁS** el `deploy_smoke` existente (mismo nombre de check, mismo exit), el proof_sha NO cambia →
sin re-pin — pero perdés el smoke ObsServer barato. (Por eso se recomienda check NUEVO + re-pin.)

## 2. Maquinaria a REUTILIZAR (verificá los anchors con grep — el archivo se mueve)
- `_dockerfile` (~7148) · `_deploy_check_py` (~7169) · `_obs_server_kt` (~4267) · `_ci_sh` (~7009) · el bloque de
  `build_files` que escribe `Dockerfile`/`tools/deploy_check.py` (~7282-7290).
- **El AppServer** (`endpoints/AppServer.kt`, `_app_server_kt`): su `main` lee `FSK_AC_PORT`/`FSK_PG_URL`/
  `FSK_PG_USER`/`FSK_PG_PASSWORD`/`FSK_WEB_DIR`; hace Flyway migrate + `seedRows` (siembra el dueño + filas) + monta
  GET/POST/PUT/DELETE. **`GET /<plural>` es PÚBLICO** (sin token) → ideal para el smoke. `/health` → `{"status":"UP"}`.
- **El idiom docker de s9** (`stations/s9.yml`): `docker run -d --name … -e POSTGRES_PASSWORD=metafactory -p …:5432
  postgres@sha256:e013e8…`; espera ready con `docker exec … pg_isready` en loop; teardown `docker rm -f`. La PG por
  digest: `postgres@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb`.
- **El idiom docker de s11** (`stations/s11.yml`): `docker build -q -t <tag> .` + `docker run -d --name … -p host:cont
  <tag>` + `down: docker rm -f <name>`.

## 3. Lecciones CARAS ya destiladas (de FSK-FORM-BROWSER-E2E + las previas)
- **El override del entrypoint es la clave**: la imagen YA trae todas las libs (`/app/lib/*`). NO necesitás un 2º
  Dockerfile ni cambiar el `mainClass` — `docker run --entrypoint java <img> -cp '/app/lib/*' <pkg>.endpoints.AppServerKt`
  corre el AppServer con la MISMA imagen. (Si preferís, podés hacer el Dockerfile PARAMÉTRICO o un 2º ENTRYPOINT, pero el
  override es lo más bounded y byte-neutro para el ObsServer smoke.)
- **El host de la PG en una red docker = el NOMBRE del contenedor** (`jdbc:postgresql://fsk_s11_pg:5432/postgres`), NO
  `localhost`. Ambos contenedores deben estar en la MISMA red (`--network fsk_s11_net`). El `-p` al host sólo para el
  AppServer (para que el proof lo alcance); la PG no necesita `-p` (sólo la ve el AppServer por la red).
- **El AppServer conecta a PG AL BOOT** (Flyway migrate + seedRows). Si la PG no está lista o es inalcanzable, el
  AppServer **crashea al arrancar** → el contenedor sale → el proof no conecta. Por eso: esperá `pg_isready` ANTES de
  lanzar el AppServer, y dale al AppServer unos reintentos de health (`curl --retry`/urllib loop en el proof).
- **PROOF MANUAL para el diente RÁPIDO** (la dist viva está en `products/snipeit/build/product`): la sesión
  FSK-FORM-BROWSER-E2E levantó PG en docker + AppServer por `java -cp 'build/install/snipeit/lib/*'
  snipeit.endpoints.AppServerKt` con `FSK_AC_PORT`/`FSK_PG_URL`/`FSK_WEB_DIR`, esperó `/health` con `curl --retry 60
  --retry-connrefused`, y corrió el proof a mano. Para ESTE eje el manual es: `docker build` la imagen del build dir +
  `docker network create` + PG + AppServer-contenedor + `deploy_check.py`. **`infra_up` NO surfacea el stdout del
  proof** → un fallo se ve como "no alcanzó la infra viva"; el proof MANUAL (o `docker logs fsk_s11_app`) lo destapa.
  Teardown SIEMPRE: `docker rm -f` + `docker network rm`.
- **VALIDÁ BARATO ANTES DE GRADLE** (≈10s): el script `scratchpad/eyeball.py` (adaptado por cada sesión: carga el
  scaffold working vs HEAD, build_files para base/assets/snipeit, diffea claves + chequea 0 líneas Kotlin >160). Para
  una mejora GENERAL base/assets quedan byte-IDÉNTICOS salvo la pieza nueva (Dockerfile/deploy_check si los tocás).
- **El `kill` de un JVM background (nohup/run_in_background) reporta exit 143/144** (SIGTERM/señal) — es COSMÉTICO, no
  un fallo tuyo; el teardown igual ocurre. Para el server vivo del manual usá `run_in_background: true` del Bash tool
  (el harness lo trackea) o `nohup … &`; matalo por PID al terminar. Verificá que NO queden contenedores `fsk_…` ni
  JVMs `AppServerKt` ni puertos colgados antes de cerrar.
- **`ci --rederive` opera sobre el ÁRBOL DE TRABAJO** (borra `.proof/`+`build/`, re-deriva in-place; NO clona git). UNO
  A UNO foreground o `--all-products`. **Delegá las corridas pesadas a un subagente Sonnet** (~40min de gradle) — pero
  escribí el codegen + el diente con TUS ojos. **proof_protect DENIEGA tocar `.proof/` por shell** — usá `meta rtm`.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento, profundidad/breadth)
**push de la imagen a un registry** (red/credenciales, diferido) · **EAV dinámico a runtime** (custom-fields Avenue B)
· **PUT de campos opcionales arbitrarios** · **Actionlog** (auditoría polimórfica) · **Kits** (bundles) · el largo
tail de ~226 rutas operacionales (counters, image-upload, LDAP, 2FA — no-dominio).

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py`, `factory.spec.yml`, `stations/`, `tools/`) es nivel FÁBRICA → **este
  incremento** lo cubre (header ABIERTO). (Este eje toca `_dockerfile`/`_deploy_check_py`/`factory.spec.yml`
  s11/`stations/s11.yml` — TODO nivel fábrica.)
- **La adopción**: este eje es GENERAL (todo producto FSK gana el deploy real) → casi seguro NO toca `product.yml`
  (no hay vocabulario de dominio nuevo). Si por algo tocás `products/snipeit/product.yml`, abrí TAMBIÉN
  `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) con el incremento ABIERTO + el re-pin, luego
  `docs(fsk): cerrar FSK-DEPLOY-APPSERVER-PG (§Evidencia) + abrir <siguiente>` flipeando el header a CERRADO.
- **Probá POR BLOQUEO**: EYEBALL · `product-run --product snipeit` PASS · diente de dos lados VIVO (saboteá el wiring
  de la red → SÓLO `deploy_appserver_live` rojo) · re-materializar `stations/` + re-pinear los 3 · `ci --rederive
  --all-products` == el pin NUEVO · `meta check` 6/6 (`generality` verde) · `git diff src/metafactory + seed = 0`.

## 6. Criterio de cierre (demostrable, no narrable)
1. Un check `infra_up` despliega el **AppServer REAL en un contenedor** + una **PG en una red docker**; el proof hace
   `GET /<plural>` al contenedor y la fila SEMBRADA vuelve de la PG (N≥1) + `/health` UP. `product-run --product
   snipeit` **PASS**.
2. **Diente de DOS lados verificado VIVO**: con la red cableada el `GET /<plural>` del contenedor devuelve la fila;
   saboteá el wiring (host de PG inexistente / contenedor fuera de la red) → el AppServer no alcanza la PG → el proof
   FALLA → SÓLO el check nuevo rojo, hermanos verdes → revertí → verde. (+ el nativo de infra_up: teardown → rojo.)
3. EYEBALL · re-materializar `stations/` + **re-pinear los 3** (check NUEVO) · `ci --rederive --all-products` == el pin
   NUEVO · `meta check` 6/6 · `git diff src/metafactory + seed = 0`.
4. STATE/LOG (fábrica) actualizados + SNIPEIT-DOMAIN (sacá "AppServer-en-contenedor con PG" de los diferidos DUROS).
   Abrí el SIGUIENTE con su handoff (§7).

## 7. Qué viene DESPUÉS — y las ALTERNATIVAS a ESTE (con AUTORIDAD para reabrir)
**El núcleo + superficie + valores-derivados + UX están terminados; tras el deploy real, lo que queda es breadth de
dominio + diferidos de red.** Si al investigar este eje preferís otro:
- **push de la imagen a un registry** — el ÚLTIMO diferido DURO de deploy tras éste (necesita un registry/credenciales;
  podría ser un registry local en docker para mantenerlo hermético). Cierra el ciclo de deploy completo.
- **Actionlog (auditoría polimórfica)** — Snipe-IT registra TODA acción (quién/qué/cuándo, sujeto polimórfico). Eje de
  dominio bounded: cada mutación append-ea una fila de auditoría. COMPONE FSK-POLYMORPHIC-REFS.
- **Kits (bundles)** — un Kit agrupa assets/accesorios/licencias que se checkout-ean juntos. Eje de dominio.
- **PUT de campos opcionales arbitrarios** — el más bounded (hoy PUT actualiza los campos requeridos del input; los
  opcionales no son PUT-eables). COMPONE FSK-CRUD-BODY-PARSING.
- **EAV dinámico (Avenue B)** — custom-fields definidos a RUNTIME (vs el schema build-time-typed jOOQ de FSK); cambio
  de ARQUITECTURA, no aditivo. El de mayor esfuerzo.

### ¿Cuánto falta para una réplica Snipe-IT funcional honesta?
**El backend faithful (modelo·acceso·comportamiento·valores-derivados incl. tiempo) está COMPLETO, la app CORRE, TODAS
las entidades se sirven, el frontend se VE y se SUBMITEA en un navegador REAL, y deploya (smoke ObsServer).** Tras
ESTE eje, **deploya de VERDAD el AppServer con su PG**. Lo que RESTA es breadth de dominio (Actionlog, Kits, PUT-
opcionales, el tail de ~226 rutas no-dominio) + diferidos de red (push a registry, EAV dinámico). **No queda ningún
hueco de NÚCLEO, SUPERFICIE, VALORES-DERIVADOS ni UX: son refinamientos de breadth/fidelidad/infra.**

---

## Evidencia (cierre 2026-06-24) — CERRADO ✅

**Qué se construyó:** un check NUEVO en s11, `deploy_appserver_live` (`kind: infra_up`, hermano de `deploy_smoke`),
despliega el **AppServer REAL en un contenedor que HABLA con una PG en una red docker**. Diseño tal cual el handoff
recomendó (GENERAL, cero nombres de dominio):
- El bootstrap REÚSA la misma imagen `fsk_s11_deploy` (ya construida por `deploy_smoke`) + `docker network create
  fsk_s11_net` + la PG `postgres@sha256:e013e8…` (sólo en la red, sin `-p` al host) + espera `pg_isready` en loop +
  el AppServer en un contenedor de la MISMA imagen con el **ENTRYPOINT override-eado**: `docker run --entrypoint
  java fsk_s11_deploy -cp '/app/lib/*' <pkg>.endpoints.AppServerKt` (la imagen ya trae todas las libs; el
  `bin/<pkg>`=ObsServerKt queda intacto para `deploy_smoke`). El host de la PG = el NOMBRE de su contenedor
  (`jdbc:postgresql://fsk_s11_pg:5432/postgres`); `-p 18598:18598` SÓLO para el AppServer (que el proof lo alcance).
- El proof = un tool nuevo `tools/deploy_appserver_check.py` (stdlib): `/health` UP (el AppServer connecta a PG AL
  BOOT — si no la alcanza, crashea) **+** `GET /<plural>` devuelve la fila SEMBRADA (`count≥1` → alcanza su PG y
  sirve una query jOOQ VIVA a request-time). El `<plural>` sale del blueprint (la entidad con dueño) y se **HORNEA**
  en el tool como DATA (igual que `_dockerfile` hornea el package) → el argv de la estación queda product-agnóstico.

**Maquinaria GENERAL (cero overfit):** todo en `codegen/scaffold_product.py` (`_deploy_appserver_check_py(bp)` +
la entrada en `build_files`) + `factory.spec.yml` s11 + `stations/s11.yml`. **`git diff src/metafactory + seed =
0`** (DATA de fábrica, ADR-012). El `meta check` da `generality` verde.

**Probado POR BLOQUEO (con mis ojos):**
- **EYEBALL** (≈10s): `build_files` emite el tool nuevo en los 3 productos con el plural correcto horneado
  (base `/projects`, snipeit/assets `/assets`), 0 líneas Kotlin >160 (no se tocó Kotlin).
- **`product-run` base/assets/snipeit = PASS**; `deploy_smoke ok · deploy_appserver_live ok`. RTM snipeit **25/26**
  (único UNSAT = REQ-F-007/s6 LLM keyless), REQ-NF-008 (deploy_vivo) SATISFIED.
- **DIENTE de DOS lados VIVO** contra la dist recompilada + PG real en docker: red cableada → `/health UP` +
  `GET /assets → count=3` → verde; **saboteá el cableado** (`FSK_PG_URL → host inexistente`) → el AppServer no
  connecta al boot → `/health` no responde (Connection reset) → exit 1; **revert → verde**. + **diente NATIVO de
  infra_up** (parte del check verde): con el contenedor caído (teardown `docker rm -f` + `network rm`) el MISMO
  proof no conecta → rojo (teardown verificado, no decorativo).
- **RE-PIN de los 3** (check NUEVO → el set `(check_name, exit)` de s11 cambia → `proof_sha` de s11 cambia): la
  línea s11 de cada `pinned_verdict.json` pasó a `3e7e3587…` (sólo esa línea). **Dos verificadores**: `ci
  --rederive` en árbol limpio == el pin NUEVO — snipeit **11/11** (yo), base **12/12** + assets **11/11** (subagente
  Sonnet, cross-check). `meta check` **6/6**.

**Lección destilada:** el proof debe ser un ÚNICO intento RÁPIDO — `infra_up` ya REINTENTA el proof mientras el
AppServer arranca (`_retry_proof` hasta `ready_timeout` = el `timeout` de la estación) y, en la fase NEGATIVA
(contenedor caído), lo corre con un `down_timeout` de 2s → un proof con su propio loop largo haría la fase negativa
lentísima. Esperá `pg_isready` ANTES de lanzar el AppServer (connecta a PG al boot; sin PG lista → crashea).

Commits: `d2bc542` (feat — codegen + spec + station + re-pin de los 3) + el docs de cierre.
