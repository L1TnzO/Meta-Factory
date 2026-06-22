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
| 1 | Company | multi-tenancy → ref opcional (scoping NO enforzado, ver §3) |
| 2 | Manufacturer | `name` unique |
| 3 | Supplier | |
| 4 | Depreciation | `months`+`depreciation_min`+`depreciation_type`(enum amount/percentage); CÁLCULO diferido |
| 5 | Category | `category_type` enum cerrado (5 valores) |
| 6 | Location | jerarquía `parent_id` (self) + `manager_id` DIFERIDOS (ver §3) |
| 7 | Department | `manager_id` DIFERIDO (ciclo) |
| 8 | User | el **dueño** (principal de ownership); SIN refs requeridos (restricción de seed) |
| 9 | AssetModel | `category_id` requerido (faithful) |
| 10 | **Asset** | **workflow** (`status`) + **ownership** (`owned_by: assigned_user_id`) |
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

**Ownership** → `Asset.owned_by: assigned_user_id` (el activo "pertenece" a su asignado). Un `manager` toca
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

2. **Checkout polimórfico** (Asset/Accessory `assigned_to` → User|Location|Asset) [SIMPLIF + GAP-FÁBRICA].
   FSK `ref` apunta a UNA entidad. Se simplificó a **User** (el caso dominante). Para fidelidad plena se
   necesitaría una primitiva de ref polimórfico (unión de targets) — gap de fábrica.

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

6. **Ciclos de referencia rotos**: `Location.manager_id`→User y `Department.manager_id`→User [SIMPLIF].
   Crearían ciclos (Location↔User, User↔Department) que el migration en orden de declaración no admite (FK a
   tabla posterior). Se QUITARON (los lados débiles). El management de ubicación/departamento se difiere.

7. **Depreciación calculada** [GAP-FÁBRICA]. Se almacenan los INPUTS (`months`, `depreciation_min`,
   `depreciation_type`) pero el valor actual (straight-line: `(cost−piso)·(1−meses_transcurridos/months)+piso`)
   es lógica derivada. FSK no tiene campos computados; el cálculo viviría en s6 (lógica de dominio por LLM,
   hoy diferida keyless) o pediría una primitiva de campo computado — gap.

8. **Multi-tenancy / company scoping** [GAP-FÁBRICA]. `company_id` se modela como ref, pero el SCOPING
   transversal (toda query filtrada por la compañía del actor, superuser exento) no es expresable: la ownership
   de FSK es por-fila por-un-dueño, no un filtro de tenant. El filtro por compañía es un gap (ABAC/scoping).

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

12. **Diferidos menores** [SIMPLIF]: soft-deletes (`deleted_at`), Actionlog (auditoría polimórfica), Kits
    (bundles), CheckoutRequest/Acceptance (solicitudes/firma), campos operativos (counters, image, timestamps,
    ldap, 2FA, password — no-dominio), y la mayoría de las ~226 rutas (el blueprint genera el contrato CRUD +
    el server de control de acceso; el resto de la superficie de endpoints es breadth posterior).

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
7. **Ciclos cross-entidad** (deferral 6) — **SIGUIENTE (FSK-XENTITY-CYCLES, abierto)**: el 1er eje de CICLO en el grafo.
   Hoy todo `ref` apunta a una entidad declarada ANTES (el migration emite `REFERENCES` en orden de declaración); los
   ciclos de Snipe-IT (Location/Department.manager_id→User con User declarado DESPUÉS) están rotos quitando el lado
   débil. Levantarlo pide FK forward/cíclica como constraint DIFERIDA (`ALTER TABLE ADD CONSTRAINT` tras crear ambas
   tablas) + seed NULL-then-UPDATE (el ref forward debe ser OPCIONAL). Bounded, faithful, distinto a lo hecho (es
   SCHEMA, no access-control). Ver `docs/work/FSK-XENTITY-CYCLES-INCREMENT.md` (handoff abierto).
8. **Diferidos DUROS** (red/scope): push de la imagen a un registry · e2e Playwright (browser real) ·
   AppServer-en-contenedor con PG · checkout polimórfico (deferral 2) · cantidades (qty decrement en checkout de
   Accessory/Consumable — sub-eje de los verbos) · company-scoping (deferral 8) · EAV dinámico a runtime (Avenue B).

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
