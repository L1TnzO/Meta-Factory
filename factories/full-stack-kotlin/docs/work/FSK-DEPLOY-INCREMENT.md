# Incremento FSK-DEPLOY — el Dockerfile generado se CONSTRUYE en una imagen y el contenedor responde VIVO

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO**
> (creado 2026-06-21T21:59Z). Cerralo flippeando este header a CERRADO (el `increment status` lee el header) **o**
> con `meta increment close --factory full-stack-kotlin`. Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA
> editada (ADR-016).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-BROWSER-FORM con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (la decisión estratégica — leéla, no la saltees)

Tras FSK-BROWSER-FORM la app es **usable por un humano**: la capa de DATOS de Snipe-IT está COMPLETA (el grafo
relacional entero es CRUD-able por API) y la UI **se monta en un DOM real + un FORM postea** (la fila aparece como
nodo del DOM). El **ÚNICO hueco FSK-general** que separa de "Snipe-IT *deployado* y enfocarse SÓLO en el producto"
es el **deploy real**: hoy el `Dockerfile` **se GENERA** (base pineada por digest, `COPY` del dist, `ENTRYPOINT`) pero
**el gate `hermetic_build` (s10) sólo lo VERIFICA POR GREP** (que la base esté pineada por `@sha256:`) — **NUNCA
construye la imagen ni levanta el contenedor**. Es la misma "media-verdad" que browser-form cerró para la UI, pero
para el deploy: la receta existe, nadie la ejecuta.

**Qué deja TERMINADO**: el `Dockerfile` generado **se CONSTRUYE en una imagen real** (`docker build`) y el
**contenedor LEVANTA y RESPONDE VIVO** a una request HTTP real (smoke-test contra el server del producto corriendo
DENTRO del contenedor). Es el salto de "la receta de deploy está pineada" a "la imagen construye y el contenedor
sirve". Tras esto, lo que QUEDA es product-specific (los 12 deferrals de `SNIPEIT-DOMAIN.md`) — **ya es "enfocarse en
el producto", no en FSK**.

**Hermano YA cerrado (de dónde venís):** FSK-BROWSER-FORM montó la UI en un DOM real + el FORM que postea. Detalle:
`docs/work/FSK-BROWSER-FORM-INCREMENT.md §Evidencia` + `docs/LOG.md` (2026-06-21T21:59Z).

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso: backend vivo + UI montada + Dockerfile verificado por grep):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez** (el sandbox de Bash mata gradle: exit
144). **Mantené el cwd de Bash en la RAÍZ del repo** (un `cd` a un subdir filtra el cwd persistente → deadlock del
hook `stop_proof`). Debe dar **PASS** (s0→s10). RTM snipeit **23/24** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **s9 usa PUERTOS FIJOS (18593/18594/18595)** → NUNCA corras dos s9 en paralelo, NUNCA dejes un `product-run`/`ci`
en BACKGROUND al cerrar el turno (el hook `stop_proof` RE-CORRE la estación activa → colisión de puerto → falso
rojo). Corré FOREGROUND (timeout ≥420000ms) y dejá terminar ANTES de cerrar el turno.

**2) Entendé el seam que HOY existe** (todo en `codegen/scaffold_product.py`):
- **`_dockerfile(pkg)`** (~L4403): emite el `Dockerfile` del producto. HOY:
  ```
  FROM eclipse-temurin:21-jre@<DOCKER_BASE_DIGEST>
  WORKDIR /app
  COPY build/install/<pkg>/ /app/        # el dist autocontenido que produce `./gradlew installDist` (s9)
  EXPOSE <OBS_PORT>                       # 18593
  ENTRYPOINT ["/app/bin/<pkg>"]          # el launcher del dist
  ```
- **El `ENTRYPOINT` corre `bin/<pkg>` = el `mainClass` del dist = `<pkg>.observability.ObsServerKt`** (ver
  `application { mainClass.set(...) }` ~L511, y `_obs_server_kt` ~L3055). **★ ObsServerKt NO necesita PG**: es el
  server de observabilidad (stdlib `com.sun.net.httpserver`) con **`/health` → `{"status":"UP"}`**, `/ready` →
  `{"status":"READY"}`, `/users` (in-memory). Escucha en `FSK_OBS_PORT` (default `OBS_PORT`=18593). **→ el smoke del
  contenedor puede ser PG-free**: `docker run -p` la imagen + HTTP-GET `/health` → `{"status":"UP"}`. (El AppServer
  CRUD —que SÍ necesita PG— NO es el entrypoint del dist; un smoke del AppServer-en-contenedor = scope MAYOR, diferilo.)
- **`hermetic_check.py`** (~L4382): el gate `hermetic_build` (s10) hace `grep` de que el `Dockerfile` pinea la base
  por `@sha256:` (no tag flotante). **No construye nada.** Este check se queda como está (la hermeticidad del PIN);
  el deploy es un check NUEVO y aparte.
- **docker YA está disponible** por `infra_up` (s9 hace `docker run postgres@sha256:...` para la PG viva — mismo
  mecanismo que usarás para `docker build` + `docker run` del producto). Confirmado: `docker images` lista varias
  `postgres:*-alpine` locales.

**3) ⚠️⚠️⚠️ EL OBSTÁCULO DURO — leelo ANTES de diseñar (te ahorra una sesión perdida):**
- **El `DOCKER_BASE_DIGEST` de HOY es un PLACEHOLDER FICTICIO** (~L80: `sha256:4d7c1e9f...`, un sha INVENTADO). El
  comentario lo dice: *"el digest es el SLOT de pin (DATA): demuestra la disciplina de pin-por-digest, no afirma
  resolver la imagen (build vivo diferido)"*. **`docker build` con ese digest FALLA** (no existe esa imagen).
- **La base `eclipse-temurin:21-jre` NO está local** (sólo hay `postgres:*`). Un `docker build` real debe **PULL**ear
  la base → **NECESITA RED** (justo el límite que el spec llama "build+push diferido por red").
- **→ ESTA es la decisión central del incremento.** Opciones (elegí UNA, con los ojos abiertos):
  - **(A) Digest real + pull único (recomendado SI hay red).** Reemplazá el placeholder por un digest REAL de
    `eclipse-temurin:21-jre` (resolvé con `docker manifest inspect eclipse-temurin:21-jre` o `docker pull` + `docker
    images --digests`). `docker build` pullea la base UNA vez (cacheada después). El `push` a un registry SIGUE
    diferido (eso sí necesita credenciales/red sostenida). **Verificá PRIMERO que hay red** (`docker pull
    eclipse-temurin:21-jre` a mano) antes de cablear nada — si la red está cortada, NO te empantanes acá: pivotá (ver §7).
  - **(B) Base local alternativa.** Si hay una JRE/JDK base ya local (`docker images`), construí FROM esa por digest.
    Menos fiel a la receta pineada, pero hermético. (Hoy NO hay una; (A) es la vía si hay red.)
  - **(C) Diferí el build, verificá el dist-as-server de otra forma.** NO recomendado: correr el dist sin contenedor
    es lo que s9 YA hace; no agrega tooth de "deploy".
- **Si la red para la base está REALMENTE cortada** → este incremento está **bloqueado por red** (declared-deferred
  honesto, como Playwright). En ese caso **NO lo forces**: cerralo como "diferido por red" con la razón medida, y
  abrí en su lugar un eje FSK-general que SÍ cierra hermético (multi-entity forms — ver §7). La honestidad > el verde fingido.

**4) EL DISEÑO (resolvelo GENERAL, cero nombres de dominio):**
- **Un check NUEVO `deploy_smoke`** de kind `infra_up` (mismo shape que los 3 de s9), en una **estación nueva `s11`**
  (recomendado — el DAG: `depends_on: [s10]`) **o** como check adicional de s10. Estructura:
  - **`bootstrap`**: `./gradlew installDist` (produce `build/install/<pkg>/`, el dist que el `COPY` necesita) **+**
    `docker build -t fsk_<pkg>_deploy build/product` (con el `Dockerfile` generado). (installDist quizá ya corrió en
    s9; re-correrlo es barato e idempotente.)
  - **`up`**: `docker run -d --name fsk_<pkg>_deploy -p <host>:<OBS_PORT> fsk_<pkg>_deploy` (puerto FIJO nuevo, FUERA
    del rango efímero y distinto de 18593/18594/18595 para no colisionar; declaralo como const DATA junto a OBS_PORT).
  - **`proof`**: un script stdlib (urllib, idiom de `obs_check.py`/`access_control_check.py`) que HTTP-GETea
    `http://127.0.0.1:<host>/health` y asevera **`{"status":"UP"}`** (y/o `/ready`). Server caído / imagen rota /
    entrypoint malo → URLError o body distinto → exit 1.
  - **`down`**: `docker rm -f fsk_<pkg>_deploy` **+** (opcional) `docker rmi fsk_<pkg>_deploy`.
- **DATA-agnóstico**: el `Dockerfile`, el nombre de imagen y el endpoint de salud son del blueprint/constantes
  (`pkg`, `OBS_PORT`), cero nombres de dominio. El check es IGUAL para los 3 productos.

**EL DIENTE NUEVO de dos lados:** el contenedor construido **responde `{"status":"UP"}`** en `/health` → un
`Dockerfile` con `ENTRYPOINT` roto, un `COPY` del dist equivocado, o un `EXPOSE`/puerto mal cableado → el contenedor
no responde → **rojo**. **Saboteá** el `ENTRYPOINT` (apuntá a un binario inexistente) **o** el `COPY` (path
equivocado) en `_dockerfile` → corré → confirmá ROJO **sólo** en `deploy_smoke` (los checks de s9 verdes) → revertí → verde.

---

## 1. ⚠️ RE-PINEAR — la diferencia OPERATIVA grande vs. browser-form (NO la pierdas)

FSK-BROWSER-FORM/REFS-IN-BODY **EXTENDIERON un check existente** → mismo nombre, mismo exit → **`proof_sha` intacto**
→ pines byte-idénticos, SIN re-materializar. **`deploy_smoke` es un check NUEVO** → cambia el SET de checks de su
estación → **`proof_sha` CAMBIA** → **DEBÉS re-materializar el chasis del DEFAULT a mano + re-pinear** (si no, `ci
--rederive` da mismatch). Recordá: `proof_sha = sha256({station, sorted (check_name, exit)})` (`seed/verifier.py:
compute_proof_sha`) — agregar un check con nombre nuevo lo mueve, aunque pase verde.

**Procedimiento de re-pin** (el mismo que usó FSK-REFS-IN-BODY cuando agregó un check — leé su §3 si existe; si no):
1. Corré `product-run` del DEFAULT (`meta product-run --factory full-stack-kotlin`) → verde con el check nuevo.
2. Re-pineá el DEFAULT: `meta pin --factory full-stack-kotlin` (escribe `pinned_verdict.json` desde los proofs verdes
   ACTUALES). Lo mismo por producto si su línea cambió de estación-set: `meta pin --factory full-stack-kotlin --product <p>`.
3. **`pinned_verdict.json` es PER-ESTACIÓN** (s0..s11). Si agregaste s11, el pin gana la entrada s11.
4. Validá: `ci --rederive --all-products` == pin (los 3, byte-idéntico CON el check nuevo).
> Mirá `meta pin --help` / `meta promote` para el verbo exacto de re-pin en esta versión del CLI antes de correr.

---

## 2. Maquinaria a REUTILIZAR (no la reinventes)
- **`_dockerfile(pkg)`** (~L4403): la receta. Si elegís (A), cambiás SÓLO el `DOCKER_BASE_DIGEST` (~L80) por uno real.
- **El idiom `infra_up` de s9** (`stations/s9.yml`): `bootstrap`/`up`/`proof`/`down`/`timeout`. Copialo para s11/el
  check nuevo. El `docker run postgres@sha256:...` de s9 es el molde de `docker run`/`docker rm -f`.
- **`obs_check.py`** (`tools/obs_check.py`, `_obs_check_py`): proof stdlib (urllib) que YA pega contra el ObsServer
  vivo en `/health`/`/ready` — el smoke del contenedor es CASI idéntico (sólo cambia el host:port al del contenedor).
- **`installDist`**: ya cableado en s9 (`./gradlew installDist`); produce `build/install/<pkg>/` que el `COPY` lee.

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **`meta station` corre la META-línea (m00–m08), NO la línea de producto FSK.** Para re-correr una estación FSK con
  un sabotaje, la vía es `product-run` (re-materializa de codegen). (Me costó un intento en browser-form.)
- **Puertos FIJOS → FOREGROUND, nunca background al cerrar turno.** El hook `stop_proof` re-corre la estación activa;
  un run de fondo colisiona el puerto → falso rojo. Un producto a la vez, foreground, timeout ≥420000ms.
- **`proof_protect` DENIEGA tocar `.proof/` por shell (incluso leer)** → usá `meta rtm`/`meta recall`; el árbol
  generado (`products/<p>/build/product/...`) SÍ es legible.
- **Eyeball SIN gradle/docker antes de cada corrida lenta** (cacé TODO el codegen de browser-form sin gradle así):
  emití los 3 productos a temp y leé el `Dockerfile` generado + el `s11.yml`. Para el digest real: `docker pull
  eclipse-temurin:21-jre` a mano PRIMERO (confirma red + te da el digest por `docker images --digests`).
- **`docker build` en sandbox**: `dangerouslyDisableSandbox: true` (igual que gradle). docker daemon disponible.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes
La capa viva (server+cliente+render+form) es opt-in a `owned_by`. El `Dockerfile` se shippea siempre (DATA de
fábrica). El `hermetic_build` (grep del pin) NO cambia. **El push a un registry + e2e Playwright (browser real) +
AppServer-en-contenedor (necesita PG) = DIFERIDO** (red/scope). El smoke es del ObsServer (PG-free) por `/health`.

## 5. Disciplina + dónde van los docs
- **Contenido de FÁBRICA GENERAL** (`codegen/` + `factory.spec.yml` + `stations/`): **cero nombres de dominio**,
  `git diff` de TODO `product.yml` = 0. Anti-overfit real = el gate `generality` de `meta check`. Si tocás sustrato
  (`src/metafactory/`+`seed/`) → incremento META aparte + `generality` verde (lo NORMAL es NO tocarlo).
- **Docs**: historia de la FÁBRICA → `docs/{STATE.md,LOG.md}` (ADR-016). El gobierno de ESTE incremento → este doc
  (flip a CERRADO + §Evidencia al cerrar). **Commit = parte del trabajo (ADR-010), nunca lo preguntes**; trailers
  I-10 (`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`). Patrón de 2 commits: `feat(fsk): …` (código/spec)
  + `docs(fsk): cerrar FSK-DEPLOY (§Evidencia) + abrir <siguiente>`.
- **Probá POR BLOQUEO**: `product-run` PASS en los 3 (foreground) · el contenedor RESPONDE `/health` VIVO ·
  diente de dos lados (sabotaje del entrypoint → sólo `deploy_smoke` rojo) · `ci --rederive --all-products` == pin
  (RE-PINEADO con el check nuevo) · `meta check` 6/6 (`generality` verde) · `git diff product.yml` = 0. **No fakees verde.**

## 6. Criterio de cierre (demostrable, no narrable)
1. `product-run` PASS en los 3 (default·assets·snipeit, foreground). La imagen del producto **se CONSTRUYE**
   (`docker build`) y el **contenedor LEVANTA y RESPONDE** `{"status":"UP"}` en `/health` (smoke real, server dentro
   del contenedor). Contenedor caído / imagen rota → rojo.
2. **Diente de DOS lados verificado VIVO**: saboteá el `ENTRYPOINT`/`COPY` del `Dockerfile` (codegen) → corré →
   confirmá ROJO **sólo** en `deploy_smoke` (los checks de s9/s10 verdes) → revertí → verde.
3. `ci --rederive --all-products` == pin (los 3) **RE-PINEADO** (el check nuevo movió `proof_sha` → re-materializaste
   + re-pineaste, §1). `meta check` 6/6 (`generality` verde). `git diff product.yml` = 0.
4. El scope honesto se actualiza: STATE/LOG (fábrica) registran "imagen construida + contenedor vivo ✅" + los huecos
   que QUEDAN (push a registry · Playwright · AppServer-en-contenedor con PG). Abrí el SIGUIENTE con su handoff
   autocontenido (o, si ya no quedan ejes FSK-general, declará "FSK MADURO → enfocarse SÓLO en el producto Snipe-IT").

## 7. Qué viene DESPUÉS (para que sepas dónde estás parado)
Con el deploy real, **FSK está MADURO**: un producto se genera, se prueba e2e, se monta en una UI usable y **se
deploya en un contenedor que responde**. Lo que QUEDA es:
- **(plan B si deploy se bloquea por red)** **CRUD/FORM de TODAS las entidades vivas** (hoy form sólo para la entidad
  con dueño; ownerless y con-ref difieren, mismo patrón) + edición/borrado desde la UI — eje FSK-general que cierra
  hermético (sin red, sin docker). Si el deploy está bloqueado, ESTE es el incremento a abrir en su lugar.
- **product-specific (= "enfocarse en el producto")**: los **12 deferrals** de
  `products/snipeit/docs/reference/SNIPEIT-DOMAIN.md` (custom-fields, checkout polimórfico, company-scoping,
  depreciación calculada, …). Eso YA no es FSK; es construir Snipe-IT sobre una fábrica madura.
- **diferidos duros (red)**: push de la imagen a un registry · e2e Playwright (browser real).
