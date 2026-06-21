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
- **Sigue** (huecos honestos → próximos incrementos): **refs no-dueño desde el body** (el espinazo relacional — el
  EJE HERMANO, el de mayor palanca ahora: muchas ownerless tienen un ref REQUERIDO, p.ej. `AssetModel.category_id`)
  · **CRUD de TODAS las ownerless** (hoy sólo la 1ª) · PUT/update ownerless · producto sólo-ownerless · **render/
  cliente/form para la entidad ownerless** · **render EN BROWSER (mount real DOM + eventos)** · **deploy real
  (Dockerfile vivo)** · **e2e Playwright** · UNIQUE-from-body→409 · PUT-total vs PATCH-split · custom-fields. La capa
  viva ya cubre la entidad con dueño **y la 1ª ownerless**; lo que falta para un Snipe-IT **usable** es levantar los
  refs del body (encadenar entidades relacionadas) antes que el pulido de browser.

## Mapa
- Línea de producto: `stations/` · Dominio (humano): `domain/` · Generado (chasis): `generated/` · Build re-derivable: `build/`
- Raíz de confianza: `seed/` (columna) + `.claude/` (sombras) · CI externo: `seed/external_ci.yml`
- Veredicto pineado (constante honesta): `pinned_verdict.json`
