# Incremento FSK-XENTITY-CYCLES — ciclos cross-entidad (FK forward/cíclica, el 1er eje de CICLO)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO**
> (creado 2026-06-22T14:35Z). Cerralo flippeando este header a CERRADO (el `increment status` lee el header) **o**
> con `meta increment close --factory full-stack-kotlin`. Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-CUSTOM-FIELDS con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (deferral 6 — el 1er eje de CICLO en el grafo de entidades)

**FSK está MUY MADURO.** Cerrados ya, product-driven por Snipe-IT: CRUD del grafo entero · self-ref · ownership
opcional/RTD · refs requeridos transitivos · **verbos de dominio checkout/checkin** (1er eje de COMPORTAMIENTO) ·
**custom-fields `format`/validación** (Avenue A). Los ejes de modelo-de-datos hechos NUNCA tocaron un CICLO entre
entidades distintas.

**Este = deferral 6 (`SNIPEIT-DOMAIN.md §3 deferral 6 / §4 #7`)**: en Snipe-IT `Location.manager_id → User`,
`Department.manager_id → User`, y `User.{location_id,department_id} → Location/Department` — un CICLO cross-entidad
(`Location ↔ User`, `User ↔ Department`). El blueprint los ROMPE quitando el lado débil (Location/Department NO
referencian a User; ver `product.yml` restricción #1). **Levantar esto = el 1er eje de CICLO**: distinto a todo lo
hecho (es SCHEMA/migración + seed, no access-control ni comportamiento).

**LA RESTRICCIÓN ACTUAL (leéla antes de diseñar)**: el migration (`_migration_sql`, ~L1097) emite la FK **inline**:
`<col> BIGINT REFERENCES <tabla_destino> (id)` — DENTRO del `CREATE TABLE`. Por eso TODO `ref` debe apuntar a una
entidad declarada ANTES (su tabla ya existe). Una FK **forward** (a una entidad declarada DESPUÉS) → la tabla destino
no existe aún → **error SQL**. La self-ref (FSK-SELF-REF) NO chocó con esto (la tabla se referencia a sí misma, existe
en su propio `CREATE TABLE`). El ciclo cross-entidad SÍ: `Location.manager_id → User` con User declarado DESPUÉS.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥540000ms** (el sandbox mata
gradle: exit 144). **cwd de Bash SIEMPRE en la RAÍZ** (un `cd` a un subdir filtra el cwd persistente → deadlock del
hook `stop_proof` al cerrar — pasa fácil, restaurá con `cd /home/enzo/University/Integración/APP/Meta_Factory`).
Debe dar **PASS**, RTM snipeit **24/25** (único UNSAT = REQ-F-007/s6 LLM keyless).
⚠️⚠️ **s7 PG 5435 · s9 puertos 18593-18595 + PG 5436/5437 · s11 18596** → NUNCA dos corridas en paralelo, NUNCA
dejes un `product-run`/`ci` en BACKGROUND al cerrar el turno (`stop_proof` re-corre la estación activa → colisión).

**2) EL DISEÑO (resolvelo GENERAL, cero nombres de dominio — `generality` verde es el anti-overfit real):**
- **La FK forward/cíclica como constraint DIFERIDA**: en `_migration_sql`, detectá un ref cuyo `to` se declara DESPUÉS
  de la entidad (`by[f['to']]` con índice > el de `e`). En vez de la FK inline, emitila como un `ALTER TABLE <tabla_e>
  ADD CONSTRAINT <nombre> FOREIGN KEY (<col>) REFERENCES <tabla_to> (id);` AL FINAL (tras todos los `CREATE TABLE`).
  La columna sigue siendo `BIGINT` (sin `REFERENCES` inline). Idempotente/determinista (orden fijo de los ALTER).
- **El ref forward DEBE ser OPCIONAL** (`required: false` → nullable): el seed inserta la fila con la FK forward en
  NULL (la entidad destino aún no está sembrada) y, si querés ejercer el ciclo VIVO, hacés un UPDATE después
  (NULL-then-UPDATE, idéntico espíritu al root→child de FSK-SELF-REF). **Validación fail-closed** en `_load_blueprint`:
  un ref forward REQUERIDO → `raise` honesto (no se puede sembrar un ciclo con un lado requerido sin un orden que no
  existe — eso es deferral, declaralo). Mantené el `raise` de ciclos de `_ensure_seeded`/`_seed_deps` (FSK-OWNED-
  REQUIRED-REFS) coherente: un ref forward OPCIONAL ya no es un error (se siembra NULL), uno REQUERIDO sí.
- **Opt-in/byte-neutro**: sin ref forward (default/assets/snipeit-actual, todos los refs apuntan atrás o a sí mismos)
  → migration/seed byte-idénticos. Verificá con el EYEBALL §3 ANTES del gradle (default/assets 68/68 byte-idénticos).

**EL DIENTE de dos lados** (criterio §6.2): el ciclo VIVE — una fila con la FK forward apuntando a una fila que EXISTE
round-trippea (read-back cruza el id); una FK forward COLGANTE (id inexistente) → la constraint diferida la RECHAZA
(insert/update falla). **El tooth NATURAL vive en s7** (`_it_repository_kt`, el tier integración vs PG viva, como
`pyramid_integration` de FSK-SELF-REF) o s8 (`_roundtrip_kt`): saboteá el wiring del ciclo (FK forward → id inexistente,
o quitá la constraint diferida del migration → el colgante deja de ser rechazado) → **SÓLO** ese check rojo, hermanos
verdes → revertí → verde. ⚠️ **El sabotaje que muerde a RUNTIME/DB NO puede introducir un hallazgo ESTÁTICO**
(detekt/ktlint en s2) que muerda antes — ponelo donde no lo linte detekt (el lado SQL/Python, o un id que sigue siendo
`Long`). Lección CARA, §3.

**¿Live en s9?** En snipeit el ciclo es sobre Location/Department/User — NINGUNA es la entidad con dueño (Asset) ni la
ownerless servible (Company). Así que el server vivo (s9) probablemente NO necesita cambios: el tooth es de SCHEMA/seed
(s1/s7/s8). Confirmá con el EYEBALL qué generadores tocás. NO agregues check/estación si podés evitarlo (§1).

---

## 1. ⚠️ RE-PIN — ¿hace falta?
Si el cambio vive DENTRO de los checks existentes (s1 migración aplica · s7 integración · s8 roundtrip, ya pineados),
el **`proof_sha` queda INTACTO** → pines byte-idénticos, **SIN re-pin** (como los últimos 6 incrementos). **NO agregues
check/estación nuevos si podés evitarlo.** `git diff snipeit/product.yml ≠ 0` es ESPERADO; el sustrato +
default/assets product.yml DEBEN quedar en 0. `proof_sha = sha256({station, sorted(check_name, exit)})` — invariante a
qué hace el código. Si SÍ agregás un check/estación → re-pin justificado, y **re-materializá el chasis por defecto**
(restaurá los hand-edits de `stations/s*.yml`, re-pineá los 3 productos).

## 2. Maquinaria a REUTILIZAR (no la reinventes) — TODO en `codegen/scaffold_product.py`
- **`_migration_sql`** (~L1097) — emite el `CREATE TABLE` con la FK inline `REFERENCES` (L1112). ACÁ va la rama de la
  FK forward → ALTER diferido. `by` (mapa nombre→entidad) y el índice de declaración te dan "¿está `to` declarado
  después?".
- **`_load_blueprint`** (~L176) — la validación fail-closed del blueprint; agregá la regla del ref forward (opcional OK,
  requerido → raise) con el mismo patrón que `operations`/`format`/`owned_by`.
- **`_it_repository_kt`** (~L2705) / **`_roundtrip_kt`** (~L1365) — los seeders del tier integración (s7, vs PG viva) y
  el roundtrip (s8). ACÁ va el NULL-then-UPDATE del ciclo (mirá cómo FSK-SELF-REF siembra root→child con `_sets` y
  valores ALT en las UNIQUE; el patrón del ciclo es el hermano cross-entidad). El diente de dos lados VIVE acá.
- **`_seed_chain`** (~L3421) / **`_seed_deps`/`_ensure_seeded`** (FSK-OWNED-REQUIRED-REFS) — la siembra topológica con
  `raise` de ciclos; mantené coherente: forward OPCIONAL ya no rompe (NULL), forward REQUERIDO sí.
- **`_app_kt`** (~L804) — el ejercedor del contrato (s0); FSK-SELF-REF tuvo que evitar que el sample se auto-referencie.
  Un ciclo cross-entidad puede pedir el mismo cuidado (no encadenar samples que no existen aún).
- **Validación M0/codegen**: una forma mal formada → `raise SystemExit` honesto.

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **EYEBALL SIN gradle ANTES de cada corrida lenta**: scratch python con `importlib` que carga `codegen/
  scaffold_product.py` HEAD vs working, `build_files(bp)` para default/assets, y **diffea** (deben quedar 68/68
  byte-idénticos). El scratch de esta sesión está en `/tmp/eyeball_cf.py` (HEAD vs working para default/assets +
  inspección de un campo inyectado en snipeit) — adaptalo (inyectá un ref forward opcional en una entidad de snipeit y
  dumpeá el migration / V1__init.sql + los seeders). **Esto cazó el 100% de los problemas de byte-neutralidad ANTES de
  gradle** (la corrida lenta sólo confirmó). Snapshot HEAD: `git show HEAD:factories/full-stack-kotlin/codegen/scaffold_product.py > /tmp/scaffold_head.py`.
- **Un sabotaje que debe morder a RUNTIME/DB no puede introducir un hallazgo ESTÁTICO antes.** En FSK-CUSTOM-FIELDS
  degradé el PATRÓN regex a `.*` (flip de codegen, `re` sigue usado → no UnusedPrivateMember, los `{n}` viven dentro
  del string del regex → no MagicNumber). En FSK-DOMAIN-OPS invertí `canTransition`. **ktlint MaxLineLength=160; detekt
  MagicNumber ignora -1/0/1/2 pero NO 9999; ReturnCount ≤ 2 (`return when`); CyclomaticComplexMethod ≤ 15 (`@Suppress`
  opt-in en un dispatcher generado).**
- **El handoff puede SOBRE- y SUB-estimar los sitios.** Verificá qué generadores YA manejan el caso ANTES de tocarlos
  (FSK-OWNED-REQUIRED-REFS descubrió que s1/s7 YA sembraban topológicamente → el gap real era 1 camino).
- **`meta verify` re-corre la estación ACTIVA con `build=False`** (no regenera). La activa tras un product-run es
  **s11**. Para un tooth en s7/s8: **sabotear el codegen + `product-run`** (rojo en s7/s8, las posteriores no corren) →
  revertir → `product-run` verde (restaura la activa verde, clave para que `stop_proof` no bloquee el cierre del turno).
- **`meta station` corre la META-línea (m00-m08), NO la línea FSK.** Para la línea FSK: `product-run`.
- **`proof_protect` DENIEGA tocar `.proof/` por shell** (incluso leer el log) — pero el **Read tool SÍ** lee
  `.proof/logs/` (es un RESUMEN: nombre de check + exit; el `exit=0` es la señal autoritativa).
- **`ci --rederive` por producto**: `--product snipeit`/`--product assets` (instancias) y SIN `--product` (la línea
  base/default). No existe `--product default`. Cada uno es un clon limpio (≈< 10 min) → corrélos UNO A UNO en foreground.
- **`dangerouslyDisableSandbox: true`** para gradle/docker. cwd SIEMPRE en la raíz. FOREGROUND, un producto a la vez.

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento)
Refs **polimórficos** (deferral 2: checkout `assigned_to`→User|Location|Asset), **company-scoping** (deferral 8),
**CANTIDADES** (sub-eje de los verbos: checkout de Accessory/Consumable decrementa `qty` — OJO: requiere montar
`operations` en entidades SIN dueño, el server vivo hoy sólo monta verbos en la entidad con dueño → más que bounded),
**soft-deletes/Actionlog** (deferral 12), **EAV dinámico a runtime** (custom-fields Avenue B), **depreciación
calculada** (campo computado, necesita s6 o columna derivada).

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El codegen** (`scaffold_product.py` + quizá `factory.spec.yml`/`stations/*.yml` si la grama nueva necesita
  validación M0 o una estación) es nivel FÁBRICA → **este incremento** lo cubre (header ABIERTO).
- **La adopción** (`products/snipeit/product.yml`: re-habilitar `Location.manager_id`→User etc.) es nivel PRODUCTO →
  abrí TAMBIÉN `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) + `feat(snipeit): …` (product.yml) + `docs(fsk): cerrar
  FSK-XENTITY-CYCLES (§Evidencia) + abrir <siguiente>`.
- **Probá POR BLOQUEO**: `product-run --product snipeit` PASS · diente de dos lados vivo · `ci --rederive --factory
  full-stack-kotlin` (base) + `--product assets` + `--product snipeit` == pin (los 3) · `meta check` 6/6 (`generality`
  verde) · `git diff src/+seed = 0` · default+assets product.yml = 0.

## 6. Criterio de cierre (demostrable, no narrable)
1. Una entidad con un `ref` forward/cíclico OPCIONAL declarada en `products/snipeit/product.yml` (p.ej.
   `Location.manager_id`→User re-habilitado) y `product-run --product snipeit` **PASS** — el migration aplica (la FK
   diferida existe), el seed/roundtrip wirea el ciclo VIVO y round-trippea.
2. **Diente de DOS lados verificado VIVO**: saboteá el wiring del ciclo (FK forward → id inexistente, o quitá la
   constraint diferida) → ROJO **sólo** en el check afectado (s7/s8) → revertí → verde.
3. `ci --rederive` (base + assets + snipeit) == pin. `meta check` 6/6 (`generality` verde). `git diff src/metafactory +
   seed = 0`. `git diff` default+assets product.yml = 0. (Si tocaste el set de checks → re-pin justificado.)
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md §3 deferral 6 / §4` actualizados. Abrí el SIGUIENTE con su handoff (§7).

## 7. Qué viene DESPUÉS (para que sepas dónde estás parado) — y las ALTERNATIVAS a ESTE
Si al investigar decidís que los ciclos cross-entidad NO son el mejor próximo (es tu decisión con más contexto), las
otras candidatas BOUNDED, product-driven, framed honestamente:
- **Cantidades (qty)** [behavior, deferral del sub-eje de FSK-DOMAIN-OPS]: checkout de Accessory/Consumable decrementa
  stock + crea la fila de asignación. ⚠️ **Wrinkle**: el server vivo hoy monta `operations` SÓLO en la entidad con
  dueño (Asset, que NO tiene qty); para ejercerlo VIVO habría que montar verbos en entidades SIN dueño (Accessory) o
  poner un qty no-faithful en Asset → es 2 sub-ejes, no claramente bounded. Por eso NO lo elegí primero.
- **Company-scoping (deferral 8)** [authz por atributo compartido]: multi-tenancy — un actor no-superadmin ve/edita
  sólo las filas de SU compañía. Generaliza ownership (dueño = principal-match; company-scope = company-match) y agrega
  FILTRADO de lectura (list/get, hoy públicos) → cambio más grande al modelo de acceso. Live en Asset (s9). Bounded
  pero se parece a FSK-S14 (ownership).
- **Orden general del push** (`SNIPEIT-DOMAIN.md §4`): ~~CRUD~~ ✅ · ~~self-ref~~ ✅ · ~~ownership opcional~~ ✅ ·
  ~~refs requeridos/seed transitivo~~ ✅ · ~~verbos checkout/checkin~~ ✅ · ~~custom-fields format~~ ✅ · **(este)
  ciclos cross-entidad** · diferidos DUROS (registry · Playwright · AppServer-en-contenedor con PG · checkout
  polimórfico · qty · company-scoping · EAV dinámico/Avenue B).
