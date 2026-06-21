# Incremento FSK-CRUD-MUTACION-REAL — el server vivo MUTA columnas (no sólo da el veredicto)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO**
> (creado 2026-06-21T03:40Z). Cerralo con `meta increment close --factory full-stack-kotlin` (gateado: árbol
> limpio + estación activa verde). Editar `factories/full-stack-kotlin/**` no-`.md` (codegen/spec/stations)
> exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada (ADR-016).
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Este es el **primer
> hueco de §5** que el primer producto real (Snipe-IT) expuso, ya registrado: hoy el server vivo de FSK
> (FSK-S15) **da el VEREDICTO de autorización (403/200/201/404) pero NO muta columnas end-to-end**. Tu trabajo
> es hacer que MUTE de verdad (INSERT/UPDATE/DELETE tipados con jOOQ) bajo el control de acceso YA enforzado.
> Es **contenido de FÁBRICA, GENERAL** (codegen + spec + `stations/s9.yml`), driven por el producto: cero
> nombres de Snipe-IT, `git diff` de cualquier `product.yml` = 0.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso desde el que partís; FSK ya genera y enforza acceso vivo):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, por-producto** (el sandbox de Bash mata gradle: exit 144).
Mantené el cwd de Bash en la RAÍZ del repo (un `cd` a subdir filtra el cwd y rompe el cierre de turno —
hooks cwd-relativos; usá paths absolutos / subshells). Esto debe dar **PASS** (s0→s10) antes de tocar nada.

**2) Leé los 3 lugares donde vive el hueco** (en `codegen/scaffold_product.py`, salvo la station):
1. `_APP_SERVER_SKELETON` (~L2906) + `_app_server_kt` (~L2848): el server HTTP VIVO. **Mirá `handle()`,
   `statusForPost`, `statusForPut`** — devuelven SÓLO el status; el body de no-GET es `{"status":N}`. No hay
   ruta DELETE (cae a 404). `seedRows`/`_seed_chain` (~L2827) **SÍ persiste** (INSERT jOOQ tipado real) → esa
   es la maquinaria a reutilizar para el INSERT del POST.
2. `_repository_kt` (~L838): `all{E}s` (SELECT all, vivo) + `{e}OwnerId` (SELECT del dueño de 1 fila). **No hay
   UPDATE/DELETE** expuestos. El INSERT existe SÓLO inline en `_seed_chain`.
3. `tools/access_control_check.py` (`_access_control_check_py`, ~L3024): el proof e2e. Hoy asevera SÓLO los
   códigos (201/403/200/404), **nunca que el dato cambió**. Acá agregás el round-trip de mutación.

---

## 1. Objetivo (qué deja TERMINADO este incremento)
El server vivo de FSK **MUTA columnas reales** bajo el control de acceso ya enforzado: **POST** inserta una fila
(jOOQ tipado) y se OBSERVA, **PUT** actualiza una columna y se OBSERVA, **DELETE** (nueva ruta) borra y se
OBSERVA — todo type-bound al schema (DES-12) y gateado por Auth→RBAC→Ownership (FSK-S13/S14/S15, intacto). El
diente deja de ser sólo el VEREDICTO: pasa a ser el **round-trip e2e** (el dato realmente apareció/cambió/se fue).

## 2. El hueco HOY (estado de partida, preciso)
`handle()` enruta: `GET` colección → `{"count": Repository.all(ctx).size}` (lectura viva ✅) · `POST` colección
→ `statusForPost(token)` = 201/403 **(NO inserta)** · `PUT /{id}` → `statusForPut(ctx,token,id)` = 200/403/404
**(NO actualiza)** · cualquier otra → 404 (**no hay DELETE**). El veredicto de autz YA es correcto y con diente
(saboteás un guard → 403 se vuelve 200 → el proof falla). Lo que falta es que el 201/200/DELETE **efectúen la
mutación**. Scope honesto declarado en STATE (FSK-S15 §7) y en `…/products/snipeit/docs/work/P1-…md §5.1`.

## 3. Deliverable + el DIENTE e2e (de dos lados, no decorativo)
Extendé `access_control_check.py` para aseverar la MUTACIÓN, no sólo el código. Round-trip sugerido (reusa
`/seed`, que expone `{id, owner}` de la fila sembrada; el actor cuyo principal == ese `owner` es dueño):
1. `GET` colección → `count = N0`.
2. `POST` (rol permitido, **principal = el owner sembrado**) → 201; el body o un `GET` siguiente exponen el id nuevo.
3. `GET` colección → `count == N0 + 1` (**el INSERT pasó de verdad** — si POST devolviera 201 sin insertar, falla).
4. `PUT /{idNuevo}` (por el DUEÑO) cambiando una columna escalar → 200; `GET /{idNuevo}` (nueva ruta de lectura
   de 1 fila) devuelve el **valor nuevo** (si PUT 200 sin update → valor viejo → falla).
5. `DELETE /{idNuevo}` (por el DUEÑO) → 200/204; `GET` colección → `count == N0` (**el DELETE pasó**); `GET
   /{idNuevo}` → 404.
6. **Los dientes de ACCESO siguen**: POST rol prohibido → 403 **y `count` NO cambia**; PUT/DELETE de fila ajena
   por no-dueño → 403 **y la columna/fila NO cambia**. (Esto es lo que prueba que la mutación está DETRÁS del guard.)

## 4. Maquinaria a REUTILIZAR (no la reinventes)
- **INSERT tipado**: `_seed_chain` (L2827) ya arma un `ctx.insertInto(TBL).set(col, sample)…returning(ID)…`
  para sembrar el dueño + 1 fila. El INSERT del POST es ESO, parametrizado por el dueño = principal del actor.
- **SELECT vivo**: `Repository.all{E}s` (para `count`) ya existe. Agregá `Repository.{e}ById`/`{e}<col>` (lectura
  de 1 fila / 1 columna) y `Repository.update{E}<col>` / `delete{E}` (UPDATE/DELETE tipados, idiom jOOQ del
  roundtrip). jOOQ ya está cableado (DDLDatabase, schema versionado) — un query a columna inexistente NO compila
  (DES-12, el diente "la DB grita en compilación").
- **Guards**: `RoleGuard.authorize/roleOf/principalOf`, `OwnershipGuard.canModify`, `OwnershipPolicy.bypass` ya
  están y ya se invocan en `statusForPut`. La mutación va DESPUÉS del veredicto OK, en la misma rama.

## 5. Decisiones de diseño (resolvelas GENERAL, DATA-agnóstico — son la parte de fondo)
1. **¿Body parsing o reutilizar valores deterministas?** El server hoy NO lee el body del request. Lo más barato
   y suficiente para el diente: el **POST inserta con los MISMOS samples deterministas del seed** (campos
   requeridos) + dueño = principal del actor → no hace falta parsear JSON todavía. El **PUT** muta UNA columna a
   un valor nuevo determinista (p.ej. `"<viejo>-mut"` o un sample distinto). Si después querés body real (JSON →
   columnas tipadas), es un eje aparte — difícil en general; difiéralo.
2. **Qué columna muta el PUT (elección GENERAL del codegen desde el spec).** Heurística DATA-agnóstica: el
   primer campo `string` NO-`unique`, NO-ref, NO-dueño de la entidad con dueño. Para Asset de Snipe-IT eso es
   `name` (opcional). El codegen la elige; si la entidad no tiene ninguna, el deliverable degrada (documentá el caso).
3. **Dueño del row en el POST y el FK.** Restricción dura de FSK: la entidad con dueño sólo puede setear el dueño
   + escalares (no otros refs requeridos — ver §6.3). El dueño es un FK→User: el principal del actor DEBE existir
   como fila User. Por eso el e2e usa **el actor cuyo principal == el `owner` sembrado** (que /seed ya garantiza
   que existe) → el INSERT del POST satisface el FK. (Crear filas con dueños arbitrarios = sembrar Users primero
   = otro eje; difiéralo.)
4. **Ruta `GET /{id}` y `DELETE /{id}`.** Agregalas a `handle()`: `GET /{id}` lee 1 fila (la columna mutable, o
   404); `DELETE /{id}` = mismo gate que PUT (RBAC + ownership) + `Repository.delete{E}`.
5. **¿Slice?** Si entra apretado, fasealo: (a) POST-inserta + observar `count`; (b) PUT-actualiza + `GET /{id}`;
   (c) DELETE-rutea+borra. Cada uno con su diente. Mejor un slice verde-de-verdad que tres a medias.

## 6. Restricciones DURAS de FSK que SIGUEN vigentes (no las rompas)
Las 4 del blueprint (en `…/products/snipeit/docs/reference/SNIPEIT-DOMAIN.md` + P1 §3). Las que tocan esto:
- **(#2) `owned_by` es `required:true`** y `OwnershipGuard.canModify(rowOwnerId: Long)` es no-nullable → el INSERT
  del POST DEBE setear el dueño.
- **(#3) El seed/INSERT del server vivo prohíbe refs REQUERIDOS no-dueño** en la entidad con dueño (Asset) y su
  dueño (User) — `_seed_chain` ya lo enforza (SystemExit). El POST hereda eso: setea dueño + escalares requeridos.
- **(#1) Orden topológico / FK**: todo ref seteado apunta a una fila existente (ver §5.3 para el dueño).

## 7. Disciplina + dónde van los docs
- **Es contenido de FÁBRICA GENERAL** (codegen `scaffold_product.py` + `factory.spec.yml` + `stations/s9.yml`):
  **cero nombres de Snipe-IT**, `git diff` de TODO `product.yml` = 0. El producto es DATA (ADR-012).
- **Anti-overfit real = el gate `generality` de `meta check`, NO un `git diff src==0` literal.** Si por algún
  motivo necesitás tocar el SUSTRATO (`src/metafactory/`+`seed/`), eso es OTRO nivel → abrí un incremento META
  (`meta increment open <slug>`) y probá que `generality` queda verde (el cambio no nombra dominio/tech). Lo
  normal acá es NO tocar sustrato: todo cabe en codegen/spec/stations de la fábrica.
- **Probá POR BLOQUEO**: `product-run` PASS · `rtm`/`ci --rederive` == pin · `meta check` 6/6. **No fakees verde**:
  un 200 que no muta es exactamente el anti-patrón que el round-trip e2e (§3) caza.
- **Docs**: el estado/decisiones de la FÁBRICA → `factories/full-stack-kotlin/docs/` (STATE/LOG de la fábrica si
  existen, o el meta STATE/LOG). El gobierno de ESTE incremento → este doc. **Commit = parte del trabajo (ADR-010),
  nunca lo preguntes**; mensaje con trailers I-10 (`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`).

## 8. Cómo correr la línea — comandos + lecciones caras (NO re-aprendas)
`meta = PYTHONPATH=src python3 -m metafactory.cli`. **`dangerouslyDisableSandbox: true`** en TODA corrida de
gradle/línea. FOREGROUND, por-producto (~3 min con gradle caliente).
1. `meta product-run --factory full-stack-kotlin --product snipeit` (re-materializa la instancia + s0→s10).
2. `meta rtm --product snipeit` (deferrals visibles OK) → `meta pin --product snipeit` → `meta ci --rederive
   --factory full-stack-kotlin --all-products` (== pin: default + assets + snipeit, NO regresiones).
3. `meta check` 6/6.
- **Server vivo largo: `java -cp build/install/<pkg>/lib/*`**, NUNCA `gradle run`/JavaExec (el daemon forkea el
  JVM fuera del process-group → leak de puerto → falsa-verde). Ya cableado en s9; respetalo.
- **`proof_protect` DENIEGA tocar `.proof/` por shell** (incluso leer) → usá `meta rtm`/`recall`/`journal`.
- **Las INSTANCIAS se re-materializan cada corrida** (no edites sus `stations/`/`factory.spec.yml`/`build/` a mano —
  gitignored, derivados). Sólo editás el codegen/spec/stations de la FÁBRICA. El proof check vive en
  `_access_control_check_py` (template), no en el `tools/` materializado.
- **`access_control_live` es `kind: infra_up` en `stations/s9.yml`**: bootstrap levanta la PG viva + installDist;
  `up` corre el server por `java -cp`; el proof es `tools/access_control_check.py`. Si agregás aserciones, salen
  del template `_access_control_check_py`.

## 9. Criterio de cierre (demostrable, no narrable)
1. `product-run --product snipeit` PASS · el proof `access_control_live` asevera el **round-trip de mutación**
   (POST→count+1 · PUT→valor nuevo en `GET /{id}` · DELETE→count−1, `GET /{id}`→404) **además** del veredicto de
   acceso (rol prohibido→403 sin mutar · no-dueño→403 sin mutar).
2. **Diente de DOS lados verificado VIVO**: sabotear la mutación (POST/PUT/DELETE que devuelven OK sin tocar la
   DB) → el proof FALLA. Sabotear un guard → el 403 se vuelve 200 → falla (intacto).
3. `ci --rederive --all-products` == pin (default + assets + snipeit; sin regresión). `meta check` 6/6
   (`generality` verde). **`git diff` de todo `product.yml` = 0** (es fábrica, no producto).
4. El scope honesto se actualiza: STATE/LOG (meta y/o fábrica) registran "CRUD-mutación real ✅" y los huecos que
   QUEDAN (self-ref → ownership opcional/RTD → custom-fields → frontend+deploy+breadth) como próximos incrementos.

## 10. Contexto que ya está hecho (de dónde venís)
- **P1·Snipe-IT Fase 2 ✅ (2026-06-21)**: el primer producto real (19 entidades) se genera VERDE por la línea FSK
  (`docs/LOG.md` 2026-06-21T03:22Z; P1 doc §7.bis). Dos huecos se arreglaron GENERALES en el camino:
  `FSK-CODEGEN-ROBUSTO-MULTI-ENTIDAD` (codegen para productos anchos) + `RTM-ARTIFACT-PATHS-PACKAGE-AWARE`
  (sustrato: render del path de artefacto por instancia). Los tres incrementos quedaron CERRADOS.
- **La trilogía de control de acceso vive** (FSK-S13 RBAC · S14 ownership · S15 endpoints vivos): el server YA
  invoca Auth→RBAC→Ownership sobre requests reales contra PG viva. Este incremento es el SIGUIENTE escalón:
  que esos endpoints, además de decidir, MUTEN.
