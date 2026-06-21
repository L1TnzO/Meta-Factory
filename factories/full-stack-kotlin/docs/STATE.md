# Estado — Full-Stack Kotlin/TS/PG Factory
> tipo: estado · fábrica generada por el Meta-Factory · esquema heredado ADR-021 (overwrite)
> Este doc APUNTA; la verdad verificable vive en artefactos (.proof/, ledger, RTM re-derivado).

## Ahora
- Fábrica **full-stack-kotlin** recién nacida por la línea M0–M8 del Meta-Factory. Produce: una app web full-stack de grado-producción: contrato OpenAPI tipado como fuente única, backend Kotlin, frontend TypeScript/React, base de datos PostgreSQL con esquema versionado (Flyway) y queries chequeados en compilación (jOOQ), verificada ENTERA en su propio toolchain bajo criterios duros de ingeniería (dureza estática, frescura de API, seguridad de la cadena de suministro, calidad de experiencia, observabilidad), 100%-generada desde este spec..
- Hereda el sustrato de toda fábrica confiable (columna anti-sello, bus de veredictos, RTM,
  dos verificadores) cableado por construcción — no re-derivado a mano.
- **Expresividad madura (R2/FSK-S11..S16 + CRUD-BODY-PARSING)**: 8 tipos de campo + opcionalidad · workflows
  (máquinas de estado) · RBAC por rol · ownership a nivel de fila · **control de acceso a RUNTIME** (server HTTP
  vivo que invoca Auth→RBAC→Ownership sobre requests reales vs PostgreSQL viva) · **CRUD-mutación real** (FSK-S16:
  POST/PUT/DELETE jOOQ tipado bajo el control de acceso, diente ROUND-TRIP) y, desde **FSK-CRUD-BODY-PARSING
  (2026-06-21)**, **entrada tipada a RUNTIME**: ese server lee el **CUERPO real** del request y lo persiste
  **type-coerced por el schema** (POST inserta los valores del body, GET /{id} devuelve la fila completa
  type-correct, PUT actualiza del body; body malo → 400, fail-closed) vía `kotlinx.serialization.json`. Detalle e
  historia: `docs/LOG.md`.
- **Frontend que CONSUME el backend vivo (FSK-FRONTEND-CONSUME, 2026-06-21)**: el **cliente TS GENERADO** dejó de
  ser funciones puras — `client.ts` gana `create<E>`/`get<E>` que hacen **`fetch` REAL** contra el AppServer vivo
  (type-bound al contrato: `Pick<components["schemas"][<E>]>` → un drift rompe `tsc --strict`, DES-6; `res.json()`
  narrow desde `unknown`, DES-10). Un consumer node (`consume_check.ts`) los IMPORTA y corre el **round-trip e2e**
  (`create<E>` POST → `get<E>` GET → cada campo vuelve EXACTO type-correct) por `node --experimental-strip-types`,
  verificado por un **3er check `frontend_consume_live`** (infra_up) en s9. `fetch` global → sin dep nueva (ADR-012).
- **Frontend que RENDERIZA la lista VIVA (FSK-FRONTEND-RENDER-LIST, 2026-06-21)**: el render generado dejó de ser
  una función que **nadie alimentaba**. El server **LISTA las filas** (`GET /<plural>` → `{"count":N,"rows":[…]}`,
  backward-compat, cada fila vía `Repository.all<E>RowsJson` que REUSA `<e>RowJson` type-correct), el cliente las
  **TRAE** (`list<E>(): Promise<<E>[]>`, narrow desde `unknown`, DES-10) y **`render<E>List`** (ya type-bound al
  contrato; ahora apunta a la entidad **CON DUEÑO**, la única con capa viva) las **renderiza** a markup. El consumer
  (`consume_check.ts`) trae la lista viva y **asevera que el HTML la refleja** (cada fila, incl. la recién creada;
  un render que dropea/garbla/hardcodea → HTML ≠ lista viva → rojo). Extiende el MISMO check `frontend_consume_live`
  (sin check nuevo → `proof_sha` intacto, pin byte-idéntico). RTM snipeit **22/23** (REQ-F-018, capability
  `frontend_render_live`). Diente de dos lados verificado VIVO.
- **CRUD vivo para entidades SIN dueño (FSK-CRUD-OWNERLESS, 2026-06-21)**: la capa viva dejó de ser **opt-in a
  `owned_by`**. El server vivo monta TAMBIÉN la 1ª entidad **ownerless** servible (con `write_roles`, campos
  requeridos todos escalares; DATA-agnóstico: **User**/**Holder**/**Company** en los 3 productos) con CRUD gobernado
  por **RBAC-only** — handlers sufijados por entidad (`doPost<E>`/`listAll<E>`/`getOne<E>`/`doDelete<E>`), verdict
  `RoleGuard.authorize` (sin `OwnershipGuard` ni `ownerId` del token), `insert<E>(ctx, input)` de TODOS los escalares
  del cuerpo, codec del cuerpo COMPARTIDO sobre la unión de entidades servidas. **El DOMINIO ENTERO** (no sólo la
  entidad con dueño) empieza a ser usable a runtime. Diente RBAC de DOS lados (rol prohibido→403 sin INSERT /
  permitido→201+count+1 · round-trip del cuerpo · DELETE prohibido→403 / permitido→200→404), extiende el MISMO
  `access_control_live` (sin check nuevo → `proof_sha` intacto, pin byte-idéntico). Capability `crud_ownerless_runtime`
  (DES-3) + **REQ-F-019** → RTM default **24/24 COMPLETE**. Verificado VIVO (sólo `access_control_live` rojo al sabotear).
- **El ESPINAZO RELACIONAL: refs requeridos no-dueño desde el body (FSK-REFS-IN-BODY, 2026-06-21)**: una entidad
  ownerless con un `ref` REQUERIDO no-dueño dejó de quedar fuera de la capa viva — ahora obtiene **CRUD vivo con la
  FK del CUERPO**. Selección DATA-agnóstica `_live_with_ref` (la 1ª sin dueño, con `write_roles`, cuyos refs
  requeridos apuntan a targets SEMBRABLES — `_ref_target_seedable`): en snipeit **AssetModel** (`category_id`→
  Category); default (Task→Project, cadena profundidad >1) y assets (sin ref requerido no-dueño) → **None**, opt-out
  intacto. El POST acepta el id del ref (`Long` vía `longOf`, codec compartido), type-bound; el server **siembra el
  target** (`seedRows`→`_ref_targets`/`_seed_chain`) y expone su id por **`/seed refs`**; el INSERT con FK colgante
  se **ATRAPA** (`runCatching` → **409**, no 500). **El grafo relacional entero del dominio pasa a ser CRUD-able por
  API** (no sólo entidades sueltas). Diente de DOS lados (ref VÁLIDO→201+round-trip que cruza el id · ref COLGANTE→
  409 fail-closed), extiende el MISMO `access_control_live` (sin check nuevo → `proof_sha` intacto, pin byte-idéntico).
  Verificado VIVO (saboteado el atrape de la FK → SÓLO `access_control_live` rojo, hermanos verdes; revertí→verde).
  **No agrega requisito** (evita over-claim: default/assets no tienen una entidad así): se plegó en **REQ-F-016**
  (`entrada_tipada_runtime`) → RTM snipeit **23/24** (sólo s6 keyless). Sustrato (`src/metafactory/`+`seed/`) = 0;
  `product.yml` = 0. Detalle: `docs/work/FSK-REFS-IN-BODY-INCREMENT.md §Evidencia`.
- **La UI se MONTA en un DOM real + un FORM postea (FSK-BROWSER-FORM, 2026-06-21)**: la capa de UI dejó de ser
  media-verdad (el cliente `fetch`eaba y el render producía un STRING, pero **nada montaba ese markup en un DOM ni
  había un FORM para crear una fila**). Ahora `app.ts` gana **`mount<E>(doc: Document, base, token)`** — crea en el
  `Document` un **FORM** (un `<input>` por campo de `_input_fields`, coacción type-correct por tipo del contrato:
  number/checkbox/date/text; enum casteado a la unión literal, DES-6) cuyo **submit** postea vía **`create<E>`** (el
  cliente vivo), re-trae **`list<E>`** y **RE-RENDERIZA** la lista → **la fila nueva aparece como NODO del DOM**. El
  salto de "usable por API" a "usable por un humano que llena un formulario". ★ Hecho factible porque **jsdom YA es
  dep** (s8 a11y) → `document`+eventos sin browser real (**Playwright sigue diferido**). El proof EXTIENDE el MISMO
  check `frontend_consume_live` (s9): monta en un DOM jsdom, llena el FORM, dispara el `submit` y asevera que un `<li>`
  NUEVO aparece (**count N→N+1**; sin check nuevo → `proof_sha` intacto, **pin byte-idéntico**). `mount<E>` pasa
  `tsc --strict`+ESLint (s2) y el bundle (1943–3687 B < 8192, s8). **No agrega requisito** — se pliega en **REQ-F-018**
  (`frontend_render_live`). Diente de DOS lados verificado VIVO (saboteé el re-render del submit → **SÓLO**
  `frontend_consume_live` rojo, hermanos `observability_live`+`access_control_live` verdes; revertí→verde). Sustrato
  (`src/metafactory/`+`seed/`)=0; `product.yml`=0. Detalle: `docs/work/FSK-BROWSER-FORM-INCREMENT.md §Evidencia`.
- **Sigue** (huecos honestos → próximos incrementos): **deploy real — el `Dockerfile` se GENERA (base pineada por
  digest) pero no se levanta/verifica vivo**: BUILDear la imagen + smoke-test contra el contenedor (docker ya está
  vía el infra_up de s9/MAT-3; build+push a un registry sigue diferido por red) — **el siguiente eje de mayor palanca:
  el último hueco FSK-general antes de que el trabajo sea product-specific** · **e2e Playwright** (browser real,
  diferido por red para el binario) · **CRUD/FORM de TODAS las entidades vivas** (hoy form sólo para la entidad con
  dueño; ownerless y con-ref difieren, mismo patrón) · edición/borrado desde la UI (hoy CREATE+LIST) · cadenas de refs
  de profundidad >1 (Task→Project→User) · self-refs (`Location.parent_id`) · refs polimórficos · refs OPCIONALES del
  body · PUT/update ownerless · UNIQUE-from-body→409 · custom-fields. **La capa de DATOS de Snipe-IT está COMPLETA y la
  UI es usable por un humano**; lo único que separa de un Snipe-IT *deployado* es el deploy real. Después, lo que QUEDA
  es product-specific (los 12 deferrals de `products/snipeit/docs/reference/SNIPEIT-DOMAIN.md`).

## Mapa
- Línea de producto: `stations/` · Dominio (humano): `domain/` · Generado (chasis): `generated/` · Build re-derivable: `build/`
- Raíz de confianza: `seed/` (columna) + `.claude/` (sombras) · CI externo: `seed/external_ci.yml`
- Veredicto pineado (constante honesta): `pinned_verdict.json`
