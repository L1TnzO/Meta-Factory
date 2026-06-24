# Snipe-IT — dominio cosechado y mapeo a la gramática FSK

> tipo: reference · estable · justifica el blueprint `products/snipeit/product.yml`.
> **Fuente**: github.com/grokability/snipe-it, **v8.6.3** (Laravel/PHP), clon investigado 2026-06-20.
> **Método**: fan-out de 7 sub-agentes sobre el repo real (migraciones · modelos Eloquent · permisos ·
> workflows · reglas/validaciones · rutas · vistas). El raw de la investigación (≈6.4k líneas) vive en el
> clon (`_research/01..07.md`), re-derivable; ESTE doc es la destilación autoritativa.

Snipe-IT es PHP/Laravel; FSK genera Kotlin/TS/PostgreSQL. **No se porta el código: se cosecha el DOMINIO**
(modelo de datos + reglas) y se expresa en la gramática del blueprint FSK. Este doc registra (1) el dominio
real, (2) qué entró al blueprint y cómo, y (3) las decisiones de mapeo — inclusiones y **deferrals honestos**
(infidelidades deliberadas + huecos de fábrica) — para no over-claim. La honestidad sobre la fidelidad es la
regla (P1 §6): si algo se simplificó o difirió, está acá con su POR QUÉ.

---

## 1. El dominio real (resumen autoritativo)

Snipe-IT es gestión de activos de TI de grado-producción: **41 modelos**, **446 migraciones**, **~226
endpoints API**, **30 Form Requests** de validación, **22 Policies**. Núcleo:

### Entidades y la topología de referencias (el grafo)
- **Asset** (activo) — la entidad central. `belongsTo` AssetModel (`model_id`), StatusLabel (`status_id`),
  Location (`location_id` efectiva + `rtd_location_id` "ready to deploy"), Company, Supplier. Vía el modelo
  alcanza Manufacturer/Category/Depreciation (`hasOneThrough` AssetModel). **Checkout polimórfico**:
  `assigned_to`/`assigned_type` → {User | Location | Asset}. `belongsToMany` License (pivot `license_seats`)
  y Component (pivot `components_assets`). `hasMany` Maintenance, Actionlog.
- **AssetModel** (`models`) — plantilla make/model. `belongsTo` Category, Manufacturer, Depreciation,
  CustomFieldset (`fieldset_id`); `belongsToMany` CustomField (defaults por modelo).
- **Reference/lookup**: Category (con `category_type` ∈ asset/accessory/consumable/component/license),
  Manufacturer, Supplier, Location (jerarquía self `parent_id` + `manager_id`→User), Company (multi-tenancy),
  Depreciation (esquema lineal: `months` + piso), StatusLabel (etiquetas con tipo deployable/pending/
  archived/undeployable), Department.
- **User** — `belongsTo` Company/Location/Department/manager(self). `belongsToMany` Group (permisos),
  Company (pivot FMCS `company_user`). Recibe checkouts polimórficos de Asset/Accessory; tiene seats de
  License, asignaciones de Consumable.
- **Consumibles de checkout** (4 tipos, cada uno distinto):
  - **License** → **LicenseSeat** (un row por asiento; se asigna a User O a Asset; finito = `seats`).
  - **Accessory** (qty) → **AccessoryCheckout** (pivot polimórfico User|Location|Asset; con checkin).
  - **Consumable** (qty) → **ConsumableAssignment** (`consumables_users`; consumo PERMANENTE, sin checkin).
  - **Component** (qty) → **ComponentAssignment** (`components_assets`, con `assigned_qty`; a Assets; checkin
    parcial reduce qty).
- **Maintenance** (`maintenances`) — registros por activo (8 tipos: maintenance/repair/upgrade/PAT test/
  calibration/sw-support/hw-support/config-change; `is_warranty`, `start_date`, `completion_date`, `cost`).
- **Soporte**: CustomField/CustomFieldset (campos dinámicos), Actionlog (auditoría polimórfica), Group
  (permisos), CheckoutRequest (solicitudes), CheckoutAcceptance (firma/EULA), Kit (bundles), Depreciation.

### El workflow del activo (la máquina de estado real)
El estado efectivo NO es un enum plano: es **(StatusLabel.type) × (asignación)**. Los 4 tipos de etiqueta:
`deployable`, `pending`, `archived`, `undeployable`. De ahí:
- **RTD** (Ready-To-Deploy): label deployable + sin asignar.
- **Deployed**: label deployable + `assigned_to` no nulo.
- **Pending**: label pending. **Archived**: flag archived (no checkout-eable). **Undeployable** (broken/lost).
Transiciones: checkout (RTD→Deployed), checkin (Deployed→RTD, resetea location a `rtd_location_id`), cambio de
etiqueta (guard: no poner una etiqueta no-deployable/no-pending a un activo asignado → auto-checkin).

### Autorización (el modelo real)
**No hay roles fijos.** Hay **Grupos** con un blob JSON de permisos granulares **tri-state** (1=grant,
−1=deny, 0/ausente=inherit) + overrides por usuario + dos superflags (`is_superuser`, `admin`) + permisos
**self.*** de auto-servicio. ~20 categorías de permiso (assets, accessories, consumables, licenses,
components, kits, users, models, categories, departments, statuslabels, customfields, suppliers,
manufacturers, depreciations, locations, companies, reports, import, superuser). **Verbos más allá de CRUD**:
`checkout`, `checkin`, `audit` (assets), `keys` (licenses), `files` (adjuntos), `view.requestable`,
`view.encrypted_custom_fields`. Resolución: superuser → grant usuario → deny usuario → grant grupo → deny por
defecto. **Multi-tenancy (FMCS)**: scoping por `company_id` cuando `full_multiple_companies_support` está on.

### Reglas de negocio clave (más allá de validación de campos)
- **Guards de borrado** (casi toda entidad): no se borra si tiene asociados. License: todos los seats libres.
  User: cero assets/licenses/accessories/managed. Location/Company/Manufacturer: cero referencias. No borrarse
  a sí mismo.
- **Precondición de checkout (asset)**: `assigned_to` nulo Y `status.deployable=1` Y `archived=0`; no a sí
  mismo. **License**: asientos libres ≥1 Y no expirada/terminada. **Cantidades**: no checkout de más
  consumibles/seats que los disponibles; qty de accessory no editable por debajo de lo prestado.
- **Validaciones** (Form Requests + `$rules` en modelos): `asset_tag` required+unique-undeleted; `serial`
  unique condicional (setting); `purchase_cost` numeric gte:0; `model_id`/`status_id` required (asset);
  `category.name` unique por `category_type`; `manufacturer.name` unique; email/url con formato.

### Pantallas (arquetipos)
Navegación: Dashboard → Assets (con sub-filtros de estado) → Licenses → Accessories → Consumables →
Components → Kits → People → Import → Settings (Custom Fields/Status Labels/Models/Categories/.../Depreciation)
→ Reports. Arquetipos: **lista** (Bootstrap-Table API-driven, columnas + filtros + bulk + acciones por fila),
**detalle de 2 columnas** (tabs: detalles/historial/licencias/componentes/files/maintenances/audits — el de
Asset tiene 11 tabs), **formulario CRUD** (con la sección dinámica de custom-fields que aparece al elegir el
modelo, y el selector de estado que muestra/oculta el destino de checkout según deployable).

---

## 2. Qué entró al blueprint (el mapeo)

`products/snipeit/product.yml` declara **19 entidades** en orden topológico, en la gramática FSK
(`string/boolean/int/number/date/ref/enum` + `required`/`unique` · workflow `enum`+`initial`+`transitions` ·
RBAC `roles`+`write_roles` · ownership `owned_by`+`owner_bypass_roles`). Validado por bloqueo:
`scaffold --selftest` (19 entidades → 66 archivos) + `--check-idempotent` (byte-idéntico) + 0 forward-refs en
la migración.

| # | Entidad | Notas de mapeo |
|---|---------|----------------|
| 1 | Company | multi-tenancy → ref; scoping ENFORZADO en Asset (FSK-COMPANY-SCOPING, deferral 8 ✓), ver §3 |
| 2 | Manufacturer | `name` unique |
| 3 | Supplier | |
| 4 | Depreciation | `months`+`depreciation_min`+`depreciation_type`(enum amount/percentage); CÁLCULO diferido |
| 5 | Category | `category_type` enum cerrado (5 valores) |
| 6 | Location | jerarquía `parent_id` (self) + `manager_id` DIFERIDOS (ver §3) |
| 7 | Department | `manager_id` DIFERIDO (ciclo) |
| 8 | User | el **dueño** (principal de ownership); SIN refs requeridos (restricción de seed) |
| 9 | AssetModel | `category_id` requerido (faithful) |
| 10 | **Asset** | **workflow** (`status`) + **ownership** (`owned_by: assigned_to`, POLI [User\|Location\|Asset]) |
| 11 | License | `seats` (int); con asientos |
| 12 | LicenseSeat | pivot `license_seats` como entidad (a User O Asset) |
| 13 | Accessory | qty |
| 14 | AccessoryCheckout | pivot; target polimórfico → simplificado a User |
| 15 | Consumable | qty |
| 16 | ConsumableAssignment | pivot; consumo permanente |
| 17 | Component | qty |
| 18 | ComponentAssignment | pivot `components_assets` con `assigned_qty` |
| 19 | Maintenance | `maintenance_type` enum (8 tipos) |

**RBAC** → 4 roles fijos que aproximan el sistema granular: `superadmin` (is_superuser), `admin` (admin flag),
`manager` (entidades operativas, sólo las suyas vía ownership), `auditor` (read-only — en ningún
`write_roles`). `owner_bypass_roles: [superadmin, admin]`. Reference data + usuarios: `write_roles:
[superadmin, admin]`. Operativas (Asset/License/Accessory/...): `[superadmin, admin, manager]`.

**Workflow** → el ciclo de vida del activo se modela como enum-workflow sobre `Asset.status`
(`[pending, ready, deployed, archived, broken]`, initial `ready`): `archived` es TERMINAL, `broken` se repara
a `ready`. Es la destilación del (StatusLabel.type × asignación) real a la primitiva FSK.

**Ownership** → `Asset.owned_by: assigned_to` (poli `[User|Location|Asset]`, FSK-OWNER-POLY: el activo "pertenece" a su asignado; un asignado de tipo no-principal ≡ sin dueño). Un `manager` toca
sólo los suyos; admin bypassa. Es la esencia del checkout-a-usuario de Snipe-IT, enforzada a runtime (FSK-S15).

**M:N → entidades**: FSK no tiene M:N; los 4 pivots de Snipe-IT (license_seats, accessories_checkout,
consumables_users, components_assets) se modelan como **entidades propias** con refs — fiel y expresable.

---

## 3. Deferrals honestos — infidelidades deliberadas y HUECOS DE FÁBRICA

Cada uno es deliberado y visible. Los marcados **[GAP-FÁBRICA]** son límites de FSK que un futuro incremento
GENERAL (codegen+spec, `git diff src/+seed=0`) debería levantar — driven por este producto (P1 §4), no
especulados. Los marcados **[SIMPLIF]** son simplificaciones de dominio aceptadas para la réplica.

1. **Custom fields** [GAP-FÁBRICA, alto impacto]. **Sub-eje `format`/validación ✓ HECHO (FSK-CUSTOM-FIELDS, Avenue A,
   2026-06-22)**; **EAV dinámico a runtime (Avenue B) DIFERIDO y VISIBLE**. Snipe-IT permite campos definidos por el
   usuario, con un TIPO + un **`format`** (regla de validación: MAC/IP/EMAIL/URL/NUMERIC/ALPHA), almacenados como
   columnas `_snipeit_<x>` agregadas dinámicamente a `assets` (EAV-como-columnas), agrupados en CustomFieldset y ligados
   a modelos. **Levantado (Avenue A)**: un campo `string` DECLARADO en el blueprint gana `format: <nombre>` (vocabulario
   cerrado) → el server vivo VALIDA el valor a runtime (no-match → 400, fail-closed, vía el codec `strFmt`); GENERAL,
   `git diff src/+seed=0`, opt-in/byte-neutro. snipeit adoptó `Asset.mac_address` (format MAC). **DIFERIDO (Avenue B)**:
   la DEFINICIÓN-A-RUNTIME (un admin crea campos sin re-generar — EAV genérico `custom_field_values` o columnas
   dinámicas) choca con el modelo tipado-en-compile de FSK (jOOQ tipa los queries DESDE el schema build-time); es un
   cambio de ARQUITECTURA, no aditivo. También diferidos: fieldset↔model como entidad de definición, `field_values`
   (select de opciones — hoy expresable como `enum`), `encrypted`. Ver `docs/work/FSK-CUSTOM-FIELDS-INCREMENT.md`.

2. **Checkout polimórfico** (Asset/Accessory `assigned_to` → User|Location|Asset) **✓ HECHO (la PRIMITIVA,
   FSK-POLYMORPHIC-REFS, 2026-06-22)** — el ÚLTIMO eje de MODELO-DE-DATOS faithful. Antes [GAP-FÁBRICA]: un FSK
   `ref` apuntaba a UNA entidad. **Levantado GENERAL** (codegen de fábrica, `generality` verde, `git diff
   src/+seed=0`, sin re-pin): un `ref` con `to: <LISTA>` es POLIMÓRFICO → se materializa como DOS columnas —
   `<campo>_type` (discriminador, enum CERRADO de los nombres de target, doc en el contrato) + `<campo>_id`
   (BIGINT SIN FK: no hay integridad a una unión, wrinkle #1). El server vivo round-trippea (tipo, id) y GET los
   devuelve EXACTOS, distinguiendo el target; diente de DOS lados (degradar el discriminador del rowJson → SÓLO
   s9 rojo). **Adoptado** en `Accessory.checkout_target → [User, Location, Asset]` (la entidad with_ref viva,
   donde el round-trip es observable). La cara BEHAVIORAL — **el `assigns` POLIMÓRFICO del verbo checkout** — **✓
   HECHO (FSK-POLY-ASSIGNS, 2026-06-23)**: un verbo de workflow con `assigns`/`clears` cuyo campo es un ref poly
   setea/limpia las DOS sub-columnas del cuerpo (componiendo FSK-POLYMORPHIC-REFS + FSK-DOMAIN-OPS, cero mecanismo
   nuevo). **Adoptado** en `Asset.checkout_target → [User, Location, Asset]` (campo NUEVO, OPCIONAL): `checkout`
   ASIGNA (setea `checkout_target_type` ∈ la unión fail-closed + `checkout_target_id` del cuerpo), `checkin` LIBERA
   (ambas NULL = RTD). El `checkout_target` es DISTINTO del `owned_by: assigned_user_id` (wrinkle #3: el ownership
   cruza un principal Long único, no una unión → el polimórfico vive en un campo no-dueño; el owner queda como el
   manager responsable, Long). **El checkout polimórfico FAITHFUL queda COMPLETO** (data + behavior). Diente de DOS
   lados VIVO (anulé el discriminador → SÓLO s9 rojo). Ver `docs/work/FSK-POLY-ASSIGNS-INCREMENT.md §Evidencia`.
3. **Owner POLIMÓRFICO** (el `assigned_to` que ES el owner Y es polimórfico, wrinkle #3) **✓ HECHO (FSK-OWNER-POLY,
   2026-06-24)** — el ÚLTIMO gap de MODELO+AUTH. Antes [GAP-FÁBRICA]: el `owned_by` cruzaba un `Long` único → el
   polimórfico vivía en un campo no-dueño (`checkout_target`) y el owner quedaba como un `assigned_user_id` Long. AHORA
   el `owned_by` puede ser un ref polimórfico → el ownership cruza `(tipo, id)`. Camino BOUNDED (compone
   FSK-OWNERSHIP-OPTIONAL + FSK-POLYMORPHIC-REFS, cero modelo nuevo de auth): un owner de tipo NO-principal
   (Location/Asset) ≡ owner NULL → sólo bypass modifica; el gating vive en `modifyVerdict`
   (`effectiveOwnerId = ownerType == targets[0] ? ownerId : null`), `OwnershipGuard.canModify` (Long?) INTACTO.
   **Adoptado**: `Asset.assigned_user_id` → `assigned_to` poly `[User, Location, Asset]` = `owned_by` (faithful a
   `assets.assigned_type+assigned_to`). El POST fija `(User, principal)`; una asignación a un tipo no-principal ≡ RTD.
   `checkout_target` + las operaciones quedan INTACTAS (acoplar "el verbo reasigna al dueño" con el control de acceso
   por-principal es un eje BEHAVIORAL aparte: el editor de un activo ≠ su holder). Diente de DOS lados VIVO (degradé el
   gate de tipo → la fila asignada a una Location se vuelve "del actor" → SÓLO s9 rojo). Ver
   `docs/work/FSK-OWNER-POLY-INCREMENT.md §Evidencia`. **El checkout polimórfico Y el owner polimórfico FAITHFUL quedan
   COMPLETOS — el modelo de datos + auth faithful está terminado.**

3. **Asignación opcional (RTD) vs owner requerido** **✓ HECHO (FSK-OWNERSHIP-OPTIONAL, 2026-06-22)**. Antes
   [GAP-FÁBRICA]: FSK exigía `owned_by` **`required: true`** porque `OwnershipGuard.canModify(rowOwnerId: Long)`
   era no-nullable y el server vivo conflaciona owner-nulo con 404. **Levantado GENERAL** (codegen de fábrica,
   `generality` verde, `git diff src/+seed=0`), opt-in por el `required` del `owned_by`: `canModify(rowOwnerId:
   Long?)` (una fila SIN dueño sólo la modifica un rol de bypass); `modifyVerdict` separa EXISTENCIA (reusa
   `<e>RowJson != null`) de DUEÑO (RTD existe → no es 404); el server siembra una 2ª fila RTD (owner NULL, ALT
   en las UNIQUE) que el proof ejercita VIVO (RTD+no-bypass→403 / RTD+bypass→200 / inexistente→404). Con dueño
   REQUERIDO el codegen queda EXACTO (default/assets byte-idéntico). **`Asset.assigned_user_id` ahora
   `required: false`** (un RTD está SIN asignar — el caso normal). Detalle: `docs/work/FSK-OWNERSHIP-OPTIONAL-
   INCREMENT.md` (fábrica) + `…/OWNERSHIP-OPTIONAL-ADOPT-INCREMENT.md` (producto).

4. **`Asset.model_id` requerido en la entidad-con-dueño / SEED TRANSITIVO** **✓ HECHO (FSK-OWNED-REQUIRED-REFS,
   2026-06-22)**. Antes [GAP-FÁBRICA]: la restricción de seed del server vivo (FSK-S15, el `raise` en `_seed_chain`)
   prohibía refs REQUERIDOS no-dueño en la entidad-con-dueño → `model_id` iba `required: false` aunque Snipe-IT lo
   exige. **Levantado GENERAL** (codegen de fábrica, `generality` verde, `git diff src/+seed=0`): un **seeder
   TRANSITIVO** (`_seed_deps`/`_ensure_seeded`) siembra topológicamente las dependencias por ref requerido (cadena
   multi-nivel **Category → AssetModel → Asset**, deduplicado, ciclos → `raise` honesto = deferral 6) ANTES del
   owned y wirea la FK; `/seed` expone `ownedRefs` (campo→id sembrado) para que el POST/FORM traiga FKs VÁLIDAS.
   Reúsa la fila ASIGNADA y la RTD (FSK-OWNERSHIP-OPTIONAL). Opt-in: sin ref requerido no-dueño (default/assets:
   sólo el dueño) el codegen queda byte-idéntico. s1/s7 ya sembraban topológicamente (sin cambio). **`Asset.model_id`
   ahora `required: true`** (faithful). Diente de DOS lados VIVO: FK colgante en el POST → `access_control_live`
   ROJO, hermanos s9 (observability/frontend) VERDES. Detalle: `docs/work/FSK-OWNED-REQUIRED-REFS-INCREMENT.md`
   (fábrica) + `…/OWNED-REQUIRED-REFS-ADOPT-INCREMENT.md` (producto). PENDIENTE: un ref requerido que cierre CICLO
   (Location/Department.manager_id→User) sigue diferido (deferral 6).

5. **Jerarquías self-ref**: `Location.parent_id`→Location y `User.manager_id`→User **✓ HECHO (FSK-SELF-REF,
   2026-06-22)**. Antes [GAP-FÁBRICA]: FSK no soportaba refs self (`_it_repository_kt` seteaba TODO ref —incl. el
   opcional— y referenciaba `ids[self]` antes de insertar → `KeyError`; y `_app_kt` se auto-referenciaba en el sample).
   **Levantado GENERAL** (codegen de fábrica, cero nombres de dominio, `generality` verde): una self-ref (heurística
   `to == nombre de la entidad`) se siembra como cadena **raíz→hijo** con read-back que valida la FK self contra la PG
   viva; el sample del contrato usa `null`; el hijo difiere en sus UNIQUE. **Ambos campos RE-HABILITADOS** en el
   blueprint (opcionales). `Location.manager_id`/`Department.manager_id`→User SIGUEN diferidos (ciclos cross-entidad,
   ver deferral 6). Detalle: `docs/work/FSK-SELF-REF-INCREMENT.md` (fábrica) + `…/SNIPEIT-SELF-REF-INCREMENT.md` (producto).

6. **Ciclos de referencia cross-entidad**: `Location.manager_id`→User y `Department.manager_id`→User **✓ HECHO
   (FSK-XENTITY-CYCLES, 2026-06-22)**. Antes [SIMPLIF]: crearían ciclos (Location↔User, User↔Department) que el
   migration en orden de declaración no admitía (FK a tabla posterior → inline → SQL error). **Levantado GENERAL**
   (codegen de fábrica, `generality` verde, `git diff src/+seed=0`): un `ref` FORWARD (target declarado DESPUÉS) se
   emite como constraint **DIFERIDA** (`ALTER TABLE ADD CONSTRAINT` tras crear ambas tablas) + columna `BIGINT`
   pelada; el seed lo cablea **NULL-then-UPDATE** (s7: inserta, luego UPDATE al id capturado, round-trippea el ciclo
   VIVO vs PG; FK colgante → la constraint diferida la RECHAZA, diente `shouldThrow`). El forward DEBE ser OPCIONAL
   (un lado del ciclo no tiene orden de siembra; un forward REQUERIDO → `raise` honesto). Opt-in/byte-neutro.
   **Ambos `manager_id`→User RE-HABILITADOS** en el blueprint. **Sigue diferido**: un ref forward REQUERIDO que cierre
   ciclo. Detalle: `docs/work/FSK-XENTITY-CYCLES-INCREMENT.md` (fábrica) + `…/work/XENTITY-CYCLES-ADOPT-INCREMENT.md` (producto).

7. ~~**Depreciación calculada**~~ **✓ HECHO** (FSK-COMPUTED-FIELDS same-entity 2026-06-23 + FSK-XENTITY-COMPUTED
   cross-entity 2026-06-23): la dimensión de VALORES DERIVADOS. Un campo `int`/`number` con `computed: <AST>` deriva su
   valor por una FÓRMULA aritmética DETERMINISTA (no almacenado, computado a READ-time; aritmética pura, sin s6/LLM). El
   AST referencia campos numéricos de la entidad O —cross-entity— `<ref>.<campo>` de una entidad RELACIONADA (LEFT JOIN
   al target). `Asset.current_value = max(purchase_cost − purchase_cost/model_id.depreciation_months, 0)`:
   `depreciation_months` vive en `AssetModel` (faithful: el período es per-MODELO) y se lee cross-entity (depth-1).
   **DIFERIDO**: el período REAL vive en `Depreciation` vía `AssetModel.depreciation_id` (depth-2) + el **time-elapsed**
   (`meses_transcurridos`) del straight-line completo. Detalle: `docs/work/FSK-COMPUTED-FIELDS-INCREMENT.md` +
   `…/FSK-XENTITY-COMPUTED-INCREMENT.md` (fábrica) + los `…-ADOPT-INCREMENT.md` (producto).

8. ~~**Multi-tenancy / company scoping**~~ **✓ HECHO** (FSK-COMPANY-SCOPING, 2026-06-22): el 1er eje de
   ACCESO-POR-ATRIBUTO (ABAC) y el 1er FILTRADO DE LECTURA. Una entidad con dueño declara
   `company_scoped: <campo ref>` (el tenant) + `company_scope_bypass_roles` → el server vivo (s9) FILTRA la
   LECTURA por la compañía del actor (list acotada: `WHERE company = ? OR company IS NULL`) y compone el scope
   en el verdict de escritura (otra compañía → 403 aunque sea el dueño; bypass → 200). Generaliza ownership
   ("fila × principal") a "fila × tenant". `Asset.company_scoped: company_id` (FMCS); diente de dos lados VIVO
   (s9). Ver `docs/work/FSK-COMPANY-SCOPING-INCREMENT.md §Evidencia`.

9. **Permisos granulares tri-state + self-service** [SIMPLIF]. El sistema real (grupos × permisos tri-state ×
   superflags × self.*) se aproxima con 4 roles fijos. Se pierde granularidad (p.ej. checkout sin edit) y el
   auto-servicio. Aceptado: una política tratable, co-validada (ADR-014), distinta de la del demo.

10. **StatusLabel como entidad customizable** [SIMPLIF]. Snipe-IT externaliza las etiquetas (admin define
    labels custom mapeadas a 4 tipos). Se modeló el CICLO como enum-workflow sobre Asset (la primitiva FSK más
    fuerte aquí). La customización de etiquetas se difiere.

11. **Verbos de operación** (checkout/checkin/audit/request/clone/bulk/import). **checkout/checkin ✓ HECHO
    (FSK-DOMAIN-OPS, 2026-06-22)**: `Asset` declara `operations: [checkout, checkin]` y el server vivo expone
    `POST /assets/{id}/{checkout,checkin}` que MUTA semántica bajo guard — **modifyVerdict (RBAC+ownership) →
    precondición de WORKFLOW VIVA (`canTransition(estado_actual, to)`, antes sólo-UNIT) → mutación atómica
    (`status=to` + asigna/limpia `assigned_user_id`)**; estado inválido → 409; diente de dos lados VIVO (s9). Cierra
    el over-claim "workflow enforced". **Sigue [GAP-FÁBRICA]**: la semántica con CANTIDADES (checkout de
    Accessory/Consumable decrementa `qty`, libera seat de License) + Actionlog + audit/request/clone/bulk/import.
    Detalle: `docs/work/FSK-DOMAIN-OPS-INCREMENT.md` (fábrica) + `…/work/DOMAIN-OPS-ADOPT-INCREMENT.md` (producto).

12. ~~**soft-deletes** (`deleted_at`)~~ **✓ HECHO** (FSK-SOFT-DELETES, 2026-06-23): `Asset.soft_delete: true` →
    DELETE lógico (papelera) + `restore` + read-filter `IS NULL` + índice único PARCIAL (reusar `asset_tag` tras
    borrar). Faithful: Snipe-IT NUNCA hard-deletea (Laravel SoftDeletes). **Diferidos menores restantes** [SIMPLIF]:
    Actionlog (auditoría polimórfica), Kits (bundles), CheckoutRequest/Acceptance (solicitudes/firma), campos
    operativos (counters, image, timestamps, ldap, 2FA, password — no-dominio), y la mayoría de las ~226 rutas (el
    blueprint genera el contrato CRUD + el server de control de acceso; el resto de la superficie es breadth posterior).

---

## 4. Próximos pasos (gaps priorizados → incrementos)

Driven por este producto, como contenido de fábrica GENERAL (P1 §4). Orden actualizado tras FSK-DOMAIN-OPS:
1. ~~**CRUD-mutación real** (deferral 11)~~ **✓ HECHO** (FSK-S16 + body-parsing + ownerless + refs-in-body).
2. ~~**Self-ref** (deferral 5)~~ **✓ HECHO** (FSK-SELF-REF, 2026-06-22) — jerarquías Location/User vivas.
3. ~~**Ownership opcional / RTD** (deferral 3)~~ **✓ HECHO** (FSK-OWNERSHIP-OPTIONAL, 2026-06-22) — dueño
   **nullable** + estado Ready-To-Deploy real, opt-in por `required`; diente de dos lados VIVO (s9) + UNIT (s7).
4. ~~**Refs requeridos no-dueño / seed transitivo** (deferral 4)~~ **✓ HECHO** (FSK-OWNED-REQUIRED-REFS,
   2026-06-22) — `Asset.model_id` requerido; el server vivo siembra TRANSITIVAMENTE Category→AssetModel→Asset y
   `/seed` expone `ownedRefs` para FKs válidas en el POST/FORM; diente de dos lados VIVO (s9, FK colgante → rojo).
5. ~~**Operaciones de dominio — checkout/checkin** (deferral 11b)~~ **✓ HECHO** (FSK-DOMAIN-OPS, 2026-06-22): el
   server vivo expone `POST /assets/{id}/{checkout,checkin}` que MUTA semántica bajo guard — modifyVerdict
   (RBAC+ownership) → **precondición de WORKFLOW VIVA** (`canTransition`, antes sólo-UNIT s7) → mutación atómica
   (`status` + asigna/limpia `assigned_user_id`); estado inválido → 409; diente de dos lados VIVO (s9). El 1er eje de
   COMPORTAMIENTO; cierra el over-claim "workflow enforced". Sub-eje diferido: la semántica con CANTIDADES
   (decrementar `qty`, liberar seat).
6. ~~**Custom fields** (deferral 1, el eje GRANDE)~~ **✓ HECHO (sub-eje `format`/validación, FSK-CUSTOM-FIELDS,
   Avenue A, 2026-06-22)**: un campo `string` gana `format: <nombre>` (MAC/IP/EMAIL/URL/NUMERIC/ALPHA) → el server vivo
   VALIDA el valor a runtime (no-match → 400). snipeit adoptó `Asset.mac_address` (format MAC); diente de dos lados VIVO
   (s9). **EAV dinámico a runtime (Avenue B) DIFERIDO** (schema build-time vs runtime). Ver `docs/work/FSK-CUSTOM-FIELDS-INCREMENT.md §Evidencia`.
7. ~~**Ciclos cross-entidad** (deferral 6)~~ **✓ HECHO** (FSK-XENTITY-CYCLES, 2026-06-22): el 1er eje de CICLO en el
   grafo. Un `ref` FORWARD (target declarado DESPUÉS) → FK como constraint DIFERIDA (`ALTER TABLE ADD CONSTRAINT`) +
   seed NULL-then-UPDATE; el forward debe ser OPCIONAL. `Location/Department.manager_id`→User RE-HABILITADOS (ciclos
   Location↔User, User↔Department restaurados). Diente de dos lados VIVO (s7, quitar la constraint diferida → SÓLO
   `pyramid_integration` rojo). Ver `docs/work/FSK-XENTITY-CYCLES-INCREMENT.md §Evidencia`.
8. ~~**Company-scoping / multi-tenancy** (deferral 8)~~ **✓ HECHO** (FSK-COMPANY-SCOPING, 2026-06-22): el 1er eje de
   ACCESO-POR-ATRIBUTO (ABAC) y el 1er FILTRADO DE LECTURA. `Asset.company_scoped: company_id` +
   `company_scope_bypass_roles: [superadmin, admin]` → el server vivo FILTRA la lista por la compañía del actor
   (read-path NUEVO) y compone el scope tras ownership en el verdict de escritura (otra compañía → 403 aunque
   sea el dueño; bypass → 200). Generaliza ownership a "fila × tenant". Diente de dos lados VIVO (s9). Cierra el
   último gran hueco del modelo de acceso faithful. Ver `docs/work/FSK-COMPANY-SCOPING-INCREMENT.md §Evidencia`.
9. ~~**Cantidades (qty)** (sub-eje de FSK-DOMAIN-OPS)~~ **✓ HECHO** (FSK-QTY-OPERATIONS, 2026-06-22): el 1er eje de
   COMPORTAMIENTO con STOCK + el 1er montaje de VERBOS sobre una entidad SIN dueño. Un nuevo KIND de operación
   (`decrements: <campo int>`, ≠ transición de workflow) decrementa el stock con guard out-of-stock. snipeit adoptó
   `Accessory.checkout` (decrements: qty). El server vivo monta `POST /accessorys/{id}/checkout` RBAC-only (rol
   prohibido→403 · sin stock→409 · OK→200+decremento). Resueltos los 2 sub-ejes del wrinkle (verbos-en-ownerless +
   KIND qty). Diente de dos lados VIVO (s9, quitar `AND qty>0` → SÓLO access_control_live rojo). **Sub-eje
   `creates: <pivot>`** (insertar la fila de asignación AccessoryCheckout) **✓ HECHO** (FSK-CREATES-PIVOT, 2026-06-23,
   ver item 15). Ver `docs/work/FSK-QTY-OPERATIONS-INCREMENT.md §Evidencia`.
10. ~~**Checkout polimórfico (deferral 2)** — el ÚLTIMO eje de MODELO-DE-DATOS faithful~~ **✓ HECHO (la
    PRIMITIVA, FSK-POLYMORPHIC-REFS, 2026-06-22)**: un `ref` con `to: <LISTA>` apunta a una UNIÓN de entidades →
    se materializa como 2 columnas `<campo>_type` (discriminador enum cerrado) + `<campo>_id` (BIGINT SIN FK).
    snipeit adoptó `Accessory.checkout_target → [User, Location, Asset]` (la entidad with_ref viva). El server vivo
    round-trippea (tipo, id) distinguiendo el target; diente de DOS lados VIVO (s9, degradar el discriminador →
    SÓLO access_control_live rojo). `git diff src/+seed=0`, sin re-pin. **Con esto el MODELO DE DATOS faithful
    queda COMPLETO.** Diferido faithful: el `assigns` polimórfico del verbo + el `assigned_to` polimórfico de Asset
    (su owner, wrinkle #3). Ver `docs/work/FSK-POLYMORPHIC-REFS-INCREMENT.md §Evidencia`.
11. ~~**Depreciación calculada (deferral 7)** — el 1er CAMPO COMPUTADO~~ **✓ HECHO (FSK-COMPUTED-FIELDS,
    2026-06-23)**: un campo `int`/`number` con `computed: <AST>` deriva su valor por una fórmula aritmética
    DETERMINISTA de otros campos numéricos (no almacenado, READ-time; sin s6/LLM). `Asset.current_value =
    max(purchase_cost − purchase_cost/depreciation_months, 0)` (1er-cut SAME-ENTITY; cross-entity + time-elapsed
    diferidos). Diente de DOS lados VIVO (s9, degradar la aritmética → SÓLO access_control_live rojo). `git diff
    src/+seed=0`, sin re-pin. **Con esto el NÚCLEO FUNCIONAL faithful queda COMPLETO.** Ver
    `docs/work/FSK-COMPUTED-FIELDS-INCREMENT.md §Evidencia`.
12. ~~**Borrado lógico / trash + restore (deferral 12, FSK-SOFT-DELETES)**~~ **✓ HECHO (2026-06-23)** — el ÚLTIMO
    eje BEHAVIORAL. `Asset.soft_delete: true` → DELETE pasa a UPDATE `deleted_at` (no borra; la fila EXISTE invisible)
    + read-filter `IS NULL` (compone company-scope) + verbo `restore` + índice único PARCIAL (reusar `asset_tag` tras
    borrar — faithful). Dos wrinkles de COMPOSICIÓN resueltos: existencia SIN filtrar para modifyVerdict owner-optional
    (RTD) + el UNIQUE parcial. Diente de DOS lados VIVO (s9). **NÚCLEO FUNCIONAL + BEHAVIORAL faithful COMPLETO.** Ver
    `docs/work/FSK-SOFT-DELETES-INCREMENT.md §Evidencia` + `…/SOFT-DELETES-ADOPT-INCREMENT.md` (producto).
13. ~~**Derivación CROSS-ENTITY del campo computado (FSK-XENTITY-COMPUTED)**~~ **✓ HECHO (2026-06-23)** — la fórmula
    de un campo computado referencia `<ref>.<campo>` (resolver el ref REQUERIDO → LEFT JOIN al target → leer su columna).
    `depreciation_months` se MOVIÓ de `Asset` a `AssetModel` (faithful: el período es per-MODELO) y `Asset.current_value
    = max(purchase_cost − purchase_cost/model_id.depreciation_months, 0)` lo lee cross-entity (depth-1). Diente de DOS
    lados VIVO (s9, anular el valor del JOIN → SÓLO access_control_live rojo). `git diff src/+seed=0`, sin re-pin.
    Diferido: depth-2 (el período REAL vive en `Depreciation` vía `AssetModel.depreciation_id`) + el tiempo
    transcurrido. **NÚCLEO FUNCIONAL + BEHAVIORAL faithful COMPLETO.** Ver `docs/work/FSK-XENTITY-COMPUTED-INCREMENT.md
    §Evidencia` + `…/XENTITY-COMPUTED-ADOPT-INCREMENT.md` (producto).
14. ~~**`assigns` POLIMÓRFICO del verbo (FSK-POLY-ASSIGNS, sub-eje de deferral 2)**~~ **✓ HECHO (2026-06-23)** — un verbo
    de workflow (checkout) que ASIGNA a un ref POLIMÓRFICO (setear `<campo>_type` + `<campo>_id` del cuerpo). COMPONE
    FSK-POLYMORPHIC-REFS (el ref a una unión) + FSK-DOMAIN-OPS (el verbo con `assigns`). snipeit adoptó
    `Asset.checkout_target → [User, Location, Asset]` (poly, opcional, ≠ `owned_by` — wrinkle #3); `checkout` lo asigna,
    `checkin` lo libera. Diente de DOS lados VIVO (s9). Ver `docs/work/FSK-POLY-ASSIGNS-INCREMENT.md §Evidencia`.
15. ~~**Insert-on-verb / M:N — la fila pivote (FSK-CREATES-PIVOT, sub-eje de item 9)**~~ **✓ HECHO (2026-06-23)** — el
    ÚLTIMO mecanismo behavioral genuino. Un verbo qty puede ADEMÁS `creates: <PivotEntity>`: al disparar INSERTA una fila
    en la pivote (FK-al-sujeto del id de la URL + el cuerpo), ATÓMICO (transacción decremento+insert; FK colgante →
    rollback → 409). snipeit `Accessory.checkout` gana `creates: AccessoryCheckout` (la pivote con `assigned_user_id`+`note`
    requeridos). Diente de DOS lados VIVO (s9, degradar el `set(NOTE)` → SÓLO access_control_live rojo). **NÚCLEO
    FUNCIONAL + BEHAVIORAL faithful COMPLETO** (data · acceso · comportamiento · valores derivados · app que CORRE). Ver
    `docs/work/FSK-CREATES-PIVOT-INCREMENT.md §Evidencia` + `…/CREATES-PIVOT-ADOPT-INCREMENT.md` (producto). **SIGUIENTE
    (recomendado) = owner POLIMÓRFICO de Asset** (wrinkle #3: `assigned_to` en Snipe-IT ES el owner Y es polimórfico → el
    OwnershipGuard cruza (tipo, id) en vez de un Long). Alternativas: cross-entity depth-2 · breadth pura. Ver
    `docs/work/FSK-OWNER-POLY-INCREMENT.md` (handoff).
16. **Diferidos DUROS** (red/scope/breadth): push de la imagen a un registry · e2e Playwright (browser real) ·
    AppServer-en-contenedor con PG · owner POLIMÓRFICO de Asset (wrinkle #3 de deferral 2) ·
    cross-entity DEPTH-2 (Asset→AssetModel→Depreciation) + time-elapsed · EAV dinámico a runtime (Avenue B) ·
    Actionlog (auditoría polimórfica) · las ~226 rutas · Kits · PUT de campos opcionales arbitrarios.

## 5. Cómo regenerar / continuar (mecánica R1, próxima sesión)
- Spec ya instanciado: `products/snipeit/product.yml` (la fuente). Re-derivar la instancia + correr la línea:
  `meta product-run --factory full-stack-kotlin --product snipeit` (FOREGROUND, `dangerouslyDisableSandbox`,
  por-producto — lecciones FSK-S11..S15 en P1 §6). Iterar a verde → `meta rtm/pin/ci --rederive --product
  snipeit`.
- Si el compile de 19 entidades excede el presupuesto, generar en slices: core (Company/Manufacturer/Category/
  Depreciation/Location/User/AssetModel/Asset) primero; breadth (License/seats, Accessory, Consumable,
  Component, Maintenance, Department) después.
- Validación barata SIN gradle (la de esta sesión): materializar (`ensure_product_instance`) + `scaffold
  --selftest`/`--check-idempotent` sobre `products/snipeit`.
