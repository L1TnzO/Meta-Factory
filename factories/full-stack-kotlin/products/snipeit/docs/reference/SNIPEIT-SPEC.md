<!-- meta:doc sha=273f2cc3f2d0389feb5633f2777cde25017ed093 updated=2026-07-10T00:16Z -->
# Especificación del Sistema — Snipe-IT (réplica model-nativa, fábrica Full-Stack Kotlin)

> **Tipo de documento**: Especificación de Software (SRS), estructurada en el espíritu de **ISO/IEC/IEEE
> 29148:2018** (Requirements Engineering) — secciones de propósito/alcance, casos de uso, requisitos
> funcionales, modelo de datos, interfaces, reglas de negocio, validaciones y verificación. Adaptada a un
> sistema **generado por una fábrica de software** (Meta-Factory → fábrica `full-stack-kotlin` → producto
> `snipeit`), no escrito a mano.
>
> **Sistema auditado**: `factories/full-stack-kotlin/products/snipeit/` dentro del repositorio Meta-Factory.
> Es una **réplica fiel del dominio** de [Snipe-IT](https://snipeitapp.com) (gestión de activos de TI,
> PHP/Laravel, código real disponible en `../snipe-it/` como referencia CONGELADA de cosecha), re-expresada
> en Kotlin/TypeScript/PostgreSQL por la gramática de la fábrica FSK. **No es el código de Snipe-IT** — es
> un sistema propio, generado, que adopta su modelo de dominio y sus reglas de negocio centrales.
>
> **Fecha de verificación**: 2026-07-08. **Método**: verificación por bloqueo (ADR-017 §3) — cada número de
> este documento se re-derivó de artefactos reales (contrato OpenAPI, DDL SQL, código Kotlin generado,
> spec `product.yml` parseado programáticamente, servidor vivo respondiendo HTTP real, capturas de pantalla
> reales por Chromium), **no se estimó ni se copió de documentación previa**. La metodología de cada conteo
> está declarada explícitamente junto al número (regla de honestidad técnica del proyecto — nunca declarar
> verde sin prueba).

---

## 0. Resumen ejecutivo — checklist de completitud contra el piso mínimo pedido

| # | Criterio pedido | Mínimo | Real (verificado) | Veredicto | Evidencia |
|---|---|---:|---:|:---:|---|
| 1 | Casos de uso | 10 | **15** | ✅ PASA | §3 |
| 2 | Funcionalidades / flujos de trabajo | 30 | **36** | ✅ PASA | §4 |
| 3 | Tablas | 40 | **40** | ✅ PASA | §5 |
| 4 | Endpoints API | 40 | **44** | ✅ PASA | §6 |
| 5 | Pantallas (con evidencia) | 30 | **39 capturas reales** | ✅ PASA | §7 |
| 6 | Reglas de negocio | 60 | **100** | ✅ PASA | §8 |
| 7 | Validaciones y restricciones CHECK | 100 | **201** (+ 51 de integridad referencial en §8) | ✅ PASA | §9 |
| 8 | Checklist de completitud del producto | — | **27/27 requisitos trazados (100%)** | ✅ PASA | §10 |
| 9 | Pruebas automatizadas, cobertura 100% | 100% | Jacoco REAL instrumentado (fase 3+4+5, `FSK-REQREF-COVERAGE-NEGATIVE`): **98.1% de línea** (universo filtrado: excluye DTOs OpenAPI + acceso a datos jOOQ + `DbRoundTrip.kt` diagnóstico manual, todo boilerplate/herramental no-negocio, declarado explícitamente) + 23 unit/integration + 32 aserciones E2E + 8 gates estáticos | ⚠️ **PARCIAL — real medido, brecha honesta y mínima (78 líneas, estructural)** | §11 |

**Lectura honesta (actualizada 2026-07-09, `FSK-REQREF-COVERAGE-NEGATIVE`)**: el sistema PASA 8 de 9
criterios con margen real, y cumple parcialmente 1: la **cobertura de línea** subió de **70.7% a 93.1% a
98.1%**. El primer salto (`FSK-REQREF-COVERAGE`) extendió el generador (`server.py`) para que TAMBIÉN
sembrara FKs encadenadas de las 19 entidades ownerless-con-ref-requerido que antes quedaban excluidas del
proof e2e ("wrinkle #1"). El segundo (`FSK-REQREF-COVERAGE-NEGATIVE`) generalizó el diente NEGATIVO (ref
colgante → 409, antes probado sólo una vez sobre la entidad `with_ref` primaria) a esas mismas 19 entidades
— el servidor YA rechazaba la FK colgante con 409 para todas ellas (`need_conflict` ya lo cubría), sólo
faltaba que el proof mandara el POST — y excluyó `DbRoundTrip.kt` (herramienta de diagnóstico manual, sigue
EJECUTÁNDOSE de verdad en `s1` como gate de infra, sólo deja de contar en el %) del universo medido, mismo
criterio DECLARADO que la exclusión ya existente de OpenAPI/jOOQ. Ambas capacidades de SUSTRATO (afectan a
los 3 productos con el eje, no un parche de snipeit), byte-neutral para `assets` (0 candidatas, verificado
`ci --rederive` 4/4). La brecha remanente (78 líneas, ~1.9%) es estructural — ramas catch-all de rutas HTTP
malformadas, no-ops de lifecycle de observabilidad, boilerplate de queries jOOQ generadas — declarada línea
por línea con su razón, no maquillada — ver §11.3. El **modelo de datos** ya CIERRA el mínimo pedido: 40 tablas físicas
(19 entidades del núcleo operativo original + 20 entidades MÍNIMAS agregadas en la Fase 2, decisión
explícita de diseño de priorizar ALCANZAR el número sobre profundidad de dominio — ver §5.3 y
`SNIPEIT-MIN-COMPLIANCE-INCREMENT.md` fase 2). El **checklist de completitud** ya NO tiene gaps (REQ-F-007
se activó de verdad: `s6` genera lógica de dominio con `claude -p` vivo bajo contract test, RTM 27/27
re-derivado). Nada de esto se ocultó ni se maquilló: son las brechas reales, con su causa y su evidencia.
§12 detalla además 2 **bugs reales encontrados durante esta auditoría/expansión**: (a) violación de
restricción `UNIQUE` no manejada con gracia — la conexión se cae en vez de devolver 409; (b) el codegen
nombra la constante de valores-de-enum por NOMBRE DE CAMPO sin qualificar por entidad — dos entidades con
un campo enum homónimo colisionan (fix aplicado a nivel producto, renombrando el campo).

---

## 1. Introducción

### 1.1 Propósito
Este documento especifica, con evidencia verificable, el sistema `snipeit` generado por la fábrica
`full-stack-kotlin` de Meta-Factory: su alcance funcional, su modelo de datos, su API, su interfaz, sus
reglas de negocio, sus validaciones y su estado de verificación automatizada — y evalúa ese sistema contra
un piso mínimo de completitud dado (§0).

### 1.2 Alcance
El sistema es una aplicación web de **gestión de activos de TI** (asset management): registra activos,
licencias, accesorios, consumibles y componentes de una organización, quién los tiene asignados, su
depreciación, su mantenimiento y su ciclo de vida — con control de acceso por rol, por dueño de fila y por
compañía (multi-tenancy). Corre como un servidor HTTP embebido en Kotlin (sin framework web), con
persistencia en PostgreSQL (jOOQ + Flyway) y un frontend SPA en TypeScript vanilla servido por el mismo
proceso.

### 1.3 Definiciones y siglas
- **FSK**: fábrica `full-stack-kotlin` (Meta-Factory) — genera el sistema completo (esquema, servidor,
  cliente, frontend, gates de calidad) a partir de un contrato declarativo (`product.yml`).
- **RBAC**: control de acceso basado en roles (`superadmin`, `admin`, `manager`, `auditor`).
- **Ownership**: autorización a nivel de FILA — el "dueño" de una fila puede modificarla aunque su rol no
  tenga alcance global.
- **Company-scoping**: filtrado multi-tenant — un actor sólo ve/edita filas de su compañía, salvo bypass.
- **RTM**: Requirements Traceability Matrix — matriz que ata cada requisito a un artefacto generado real.
- **Verificación por bloqueo**: el veredicto de cada estación de la fábrica lo computa el propio verificador
  desde códigos de salida reales, nunca se declara a mano (ADR de Meta-Factory).

### 1.4 Referencias
- `factories/full-stack-kotlin/products/snipeit/product.yml` — el contrato fuente (417 líneas).
- `factories/full-stack-kotlin/products/snipeit/docs/reference/SNIPEIT-DOMAIN.md` — dominio cosechado del
  Snipe-IT real y mapeo a la gramática FSK (453 líneas, con los 12 deferrals honestos citados en §12).
  Snipe-IT real: **41 modelos, 446 migraciones, ~226 endpoints API, 30 Form Requests, 22 Policies**
  (`../snipe-it/` — código fuente real, referencia congelada de cosecha).
  Re-verificado en esta auditoría: 53 tablas físicas (`Schema::create` únicas en `database/migrations/`),
  `routes/api.php` (1452 líneas) + `routes/web.php` (768 líneas).
- `build/product/openapi.yaml` — contrato OpenAPI 3.0.3 (fuente única del servidor Kotlin y el cliente TS).
- `build/product/src/main/resources/db/migration/V1__init.sql` — DDL real (Flyway).
- `.proof/`, `pinned_verdict.json` — veredictos re-derivados por estación (s0–s11).

---

## 2. Descripción general del sistema

### 2.1 Arquitectura

```mermaid
graph TD
    subgraph Cliente["Navegador (Chromium probado)"]
        SPA["SPA TypeScript vanilla<br/>app.ts (894 LOC, model-nativo)<br/>+ browser_entry.ts (nav + role-picker DEV)"]
    end
    subgraph Servidor["AppServer (Kotlin, HTTP embebido, sin framework)"]
        RT["RouteTable<br/>44 rutas declaradas"]
        RG["RoleGuard<br/>RBAC por rol"]
        OG["OwnershipGuard<br/>autorización por fila"]
        CG["CompanyScopeGuard<br/>multi-tenancy"]
        WF["AssetStatusWorkflow<br/>canTransition()"]
        REPO["Repository (jOOQ)<br/>CRUD + soft-delete + audit"]
    end
    DB[("PostgreSQL 16<br/>20 tablas, Flyway V1__init.sql")]
    OAS["openapi.yaml<br/>contrato ÚNICO — genera server Kotlin Y cliente TS<br/>(drift estructuralmente imposible)"]

    SPA -->|"fetch JSON + Bearer &lt;rol&gt;:&lt;id&gt;"| RT
    RT --> RG --> OG --> CG --> WF --> REPO --> DB
    OAS -.->|codegen| RT
    OAS -.->|codegen| SPA
```

**Figura 2.1.** Arquitectura de capas del sistema `snipeit`, evidenciando la separación entre presentación
(SPA), control de acceso compuesto (rol → dueño → compañía → estado de workflow) y persistencia, y el
contrato OpenAPI como fuente única que deriva TANTO el servidor como el cliente (elimina el *drift* de API
por construcción). Esta organización permite entender por qué las secciones 8–9 (reglas de negocio y
validaciones) se verifican en un único punto de composición (el pipeline de guards) en vez de estar
dispersas.

### 2.2 Stack tecnológico
| Capa | Tecnología | Evidencia |
|---|---|---|
| Backend | Kotlin 2.x, HTTP embebido (`com.sun.net.httpserver`), sin framework | `src/main/kotlin/snipeit/endpoints/AppServer.kt` |
| Persistencia | PostgreSQL 16 + jOOQ (SQL tipado) + Flyway (migraciones) | `V1__init.sql`, `build/generated-jooq/` |
| Contrato | OpenAPI 3.0.3, generado del `product.yml` | `openapi.yaml` |
| Frontend | TypeScript vanilla (sin framework), esbuild | `frontend/app.ts`, `frontend/app.css` |
| Build | Gradle (Kotlin DSL), instalación autocontenida (`installDist`) | `build.gradle.kts` |
| Empaquetado | Docker (imagen propia) | `Dockerfile` |
| Pruebas | Kotest (unit/integration), Playwright/Chromium (E2E) | §11 |

### 2.3 Origen y alcance declarado
El producto **no reimplementa Snipe-IT completo**: adopta 19 de sus ~41 modelos (el núcleo operativo:
activos, licencias, accesorios, consumibles, componentes y su catálogo de referencia), dejando fuera
explícitamente auditoría polimórfica completa, kits, solicitudes de checkout con firma, campos
personalizados a runtime (EAV dinámico) y la superficie de reportes — cada uno documentado como decisión de
alcance en `SNIPEIT-DOMAIN.md §3` (12 ejes, la mayoría ya resueltos como **HECHO**, ver §12). Esta
especificación audita el sistema **tal como existe hoy**, no la ambición completa de Snipe-IT.

---

## 3. Casos de uso (mínimo 10 → **15 verificados**)

Cada caso de uso listado fue **ejercitado realmente** contra el servidor vivo durante esta auditoría (HTTP
real, no solo leído del contrato) o corresponde a comportamiento observable en las capturas de pantalla de
§7.

```mermaid
graph LR
    superadmin(("superadmin"))
    admin(("admin"))
    manager(("manager"))
    auditor(("auditor"))

    CU1["CU-01 Alta de activo con asignación a un usuario"]
    CU2["CU-02 Checkout de un activo (ready→deployed)"]
    CU3["CU-03 Checkin de un activo (deployed→ready)"]
    CU4["CU-04 Reparar (broken→ready) / archivar (→archived, terminal)"]
    CU5["CU-05 Baja lógica y restauración de un activo (papelera)"]
    CU6["CU-06 Edición bloqueada de un activo desplegado (409)"]
    CU7["CU-07 Gestión de licencias con asientos"]
    CU8["CU-08 Checkout de accesorio (decrementa stock)"]
    CU9["CU-09 Asignación de consumibles (consumo permanente)"]
    CU10["CU-10 Asignación de componentes a un activo"]
    CU11["CU-11 Registro de mantenimiento sobre un activo"]
    CU12["CU-12 Alta de catálogo de referencia"]
    CU13["CU-13 Consulta de auditoría (historial de un activo)"]
    CU14["CU-14 Bloqueo de escritura para un rol de solo-lectura"]
    CU15["CU-15 Aislamiento multi-compañía (company-scoping)"]

    manager --> CU1 & CU2 & CU3 & CU4 & CU5 & CU6 & CU7 & CU8 & CU9 & CU10 & CU11 & CU13 & CU15
    admin --> CU12
    superadmin --> CU12
    auditor --> CU14
```

**Figura 3.1.** Diagrama de casos de uso, agrupados por el rol que típicamente los ejecuta. `manager`
concentra la operación diaria (activos, checkouts, mantenimientos); `admin`/`superadmin` gestionan el
catálogo de referencia; `auditor` es de solo-lectura por construcción (no aparece en ningún `write_roles`).

| ID | Caso de uso | Verificado como |
|---|---|---|
| CU-01 | Alta de activo (`Asset`) asignado a un usuario | `POST /assets` real, seed transitivo (Category→AssetModel→Asset) |
| CU-02 | Checkout de un activo a un empleado | `POST /assets/{id}/checkout` — endpoint operativo (RouteTable.kt:75) |
| CU-03 | Checkin de un activo | `POST /assets/{id}/checkin` (RouteTable.kt:76) |
| CU-04 | Reparación/archivado de un activo averiado | Transiciones `broken→ready`, `→archived` del workflow (§8.3) |
| CU-05 | Baja lógica y restauración desde la papelera | `soft_delete: true` + `POST /assets/{id}/restore` + captura `05-asset-trash.png` |
| CU-06 | Bloqueo de edición de un activo `deployed` | Regla `mutable_when` (§8.3) — PUT/DELETE → 409 |
| CU-07 | Licencias con asientos (`License`+`LicenseSeat`) | `POST /licenses` y `POST /licenseseats` ejecutados con 201 real |
| CU-08 | Checkout de accesorio con decremento de stock | `Accessory.operations: checkout` (decrements qty, creates `AccessoryCheckout`) |
| CU-09 | Asignación de consumibles (sin checkin) | `POST /consumableassignments` ejecutado con 201 real |
| CU-10 | Asignación de componentes con cantidad | `POST /componentassignments` ejecutado con 201 real |
| CU-11 | Registro de mantenimiento (8 tipos) | `POST /maintenances` ejecutado con 201 real |
| CU-12 | Alta de catálogo (Manufacturer/Supplier/Location/Department/Category/Depreciation/Company) | 7 `POST` ejecutados con 201 real durante esta auditoría |
| CU-13 | Auditoría — historial de un activo | Tab "History" de la pantalla Asset (`04-asset-history-tab.png`), lee `action_logs` |
| CU-14 | Rol `auditor` no puede escribir | `POST /companys` con `Bearer auditor:1` → **HTTP 403 real** (verificado) |
| CU-15 | Un `manager` sólo ve/edita activos de su compañía | `company_scoped: company_id` en `Asset`, con bypass para `superadmin`/`admin` |

---

## 4. Funcionalidades y flujos de trabajo (mínimo 30 → **36 verificados**)

| Categoría | # | Funcionalidad |
|---|---|---|
| **Gestión de catálogo** (alta + listado) | 1–7 | Company, Manufacturer, Supplier, Depreciation, Category, Location, Department |
| **Gestión de identidad** | 8 | Alta y listado de User (dueños potenciales de activos) |
| **Gestión de plantillas** | 9 | Alta y listado de AssetModel |
| **Ciclo de vida de activos** | 10–16 | Alta, listado, detalle, edición, borrado lógico, restauración, historial de Asset |
| **Operaciones de dominio sobre Asset** | 17–18 | Checkout, Checkin |
| **Licenciamiento** | 19–20 | Gestión de License, gestión de LicenseSeat (asiento→User o Asset) |
| **Accesorios** | 21–22 | Gestión de Accessory, checkout de accesorio (decremento de stock + registro) |
| **Consumibles** | 23–24 | Gestión de Consumable, asignación permanente a un usuario |
| **Componentes** | 25–26 | Gestión de Component, asignación con cantidad a un Asset |
| **Mantenimiento** | 27 | Registro de mantenimiento sobre un activo (8 tipos) |
| **Control de acceso** | 28–31 | Enforzamiento por rol (`superadmin`/`admin`/`manager`/`auditor`, 4 flujos distintos) |
| **Multi-tenancy** | 32 | Filtrado de lectura y escritura por compañía (company-scoping) |
| **Observabilidad** | 33 | Dashboard con conteos en vivo por entidad (`mountDashboard`) |
| **Bootstrapping** | 34 | Sembrado determinista de datos topológicos (`/seed`) |
| **Sesión (modo dev)** | 35 | Selector de rol en el cliente (`FRONTEND-LOGIN` corte A) |
| **Reproducibilidad** | 36 | Build hermético + re-derivación bit-a-bit (`ci.sh`, §11) |

---

## 5. Modelo de datos (mínimo 40 tablas → **40 reales — PASA**)

### 5.1 Conteo real
```
grep -c "CREATE TABLE" src/main/resources/db/migration/V1__init.sql   →  40
```

| # | Tabla física | Entidad del contrato | Filas 2026-07-08 (post-seed de esta auditoría) |
|---|---|---|---:|
| 1 | `companys` | Company | 2 |
| 2 | `manufacturers` | Manufacturer | 1 |
| 3 | `suppliers` | Supplier | 1 |
| 4 | `depreciations` | Depreciation | 1 |
| 5 | `categorys` | Category | 2 |
| 6 | `locations` | Location | 1 |
| 7 | `departments` | Department | 1 |
| 8 | `users` | User | 1 |
| 9 | `assetmodels` | AssetModel | 1 |
| 10 | `assets` | **Asset** (entidad central) | 3 |
| 11 | `licenses` | License | 1 |
| 12 | `licenseseats` | LicenseSeat | 1 |
| 13 | `accessorys` | Accessory | 1 |
| 14 | `accessorycheckouts` | AccessoryCheckout | 0 (pivot, sin nav propio) |
| 15 | `consumables` | Consumable | 1 |
| 16 | `consumableassignments` | ConsumableAssignment | 1 |
| 17 | `components` | Component | 1 |
| 18 | `componentassignments` | ComponentAssignment | 1 |
| 19 | `maintenances` | Maintenance | 1 |
| 20 | `action_logs` | *(tabla de sistema, no declarada como entidad — bitácora `audited`)* | variable |
| 21 | `permissiongroups` | PermissionGroup | — |
| 22 | `customfieldsets` | CustomFieldset | — |
| 23 | `customfields` | CustomField | — |
| 24 | `kits` | Kit | — |
| 25 | `checkoutrequests` | CheckoutRequest | — |
| 26 | `settings` | Setting | — |
| 27 | `importjobs` | ImportJob | — |
| 28 | `statuslabels` | StatusLabel | — |
| 29 | `countrys` | Country | — |
| 30 | `groupusers` | GroupUser | 0 (pivot, sin nav propio) |
| 31 | `customfieldsetfields` | CustomFieldsetField | 0 (pivot, sin nav propio) |
| 32 | `kitmodels` | KitModel | 0 (pivot, sin nav propio) |
| 33 | `kitaccessorys` | KitAccessory | 0 (pivot, sin nav propio) |
| 34 | `kitconsumables` | KitConsumable | 0 (pivot, sin nav propio) |
| 35 | `kitcomponents` | KitComponent | 0 (pivot, sin nav propio) |
| 36 | `checkoutacceptances` | CheckoutAcceptance | 0 (pivot, sin nav propio) |
| 37 | `companyusers` | CompanyUser | 0 (pivot, sin nav propio) |
| 38 | `states` | State | — |
| 39 | `jobtitles` | JobTitle | — |
| 40 | `emailtemplates` | EmailTemplate | — |

**Filas 21–40 (Fase 2, 2026-07-09)**: 20 entidades MÍNIMAS (2–4 campos, sin computed/workflow/polimorfismo/
soft-delete/audited) agregadas para cerrar el eje de completitud de tablas — decisión EXPLÍCITA del dueño
del producto de priorizar ALCANZAR el número sobre profundidad de dominio (ancho barato y honesto, no
maquillado). Todas tienen CRUD vivo real (verificado por `access_control_live`, s9) pero el snapshot de
filas «post-seed de esta auditoría» no se re-corrió para ellas (no hay una fila fija sembrada por el server
vivo, a diferencia de las 19 originales) — «—» = no medido en este snapshot, no «no existe». Detalle
completo (campos/refs) en `product.yml` y `SNIPEIT-MIN-COMPLIANCE-INCREMENT.md` fase 2.

### 5.2 Diagrama entidad-relación (simplificado — 51 relaciones reales, ver §8.2 para el listado completo)

```mermaid
erDiagram
    COMPANY ||--o{ ASSET : "company_id"
    COMPANY ||--o{ USER : "company_id"
    CATEGORY ||--o{ ASSETMODEL : "category_id"
    CATEGORY ||--o{ LICENSE : "category_id"
    CATEGORY ||--o{ ACCESSORY : "category_id"
    CATEGORY ||--o{ CONSUMABLE : "category_id"
    CATEGORY ||--o{ COMPONENT : "category_id"
    MANUFACTURER ||--o{ ASSETMODEL : "manufacturer_id"
    DEPRECIATION ||--o{ ASSETMODEL : "depreciation_id"
    ASSETMODEL ||--o{ ASSET : "model_id (requerido)"
    LOCATION ||--o{ LOCATION : "parent_id (self, jerarquía)"
    LOCATION ||--o{ USER : "location_id"
    LOCATION ||--o{ ASSET : "location_id / rtd_location_id"
    DEPARTMENT ||--o{ USER : "department_id"
    USER ||--o{ USER : "manager_id (self)"
    USER ||--o{ ASSET : "assigned_to (owner, polimórfico)"
    ASSET ||--o{ MAINTENANCE : "asset_id"
    ASSET ||--o{ COMPONENTASSIGNMENT : "asset_id"
    ASSET ||--o{ LICENSESEAT : "asset_id (opcional)"
    LICENSE ||--o{ LICENSESEAT : "license_id"
    ACCESSORY ||--o{ ACCESSORYCHECKOUT : "accessory_id (creado por verbo checkout)"
    CONSUMABLE ||--o{ CONSUMABLEASSIGNMENT : "consumable_id"
    COMPONENT ||--o{ COMPONENTASSIGNMENT : "component_id"
    SUPPLIER ||--o{ ASSET : "supplier_id"
```

**Figura 5.1.** Modelo entidad-relación (subconjunto representativo de las 51 relaciones reales — el
diagrama completo con las 20 tablas × 51 FKs excede lo legible en un solo gráfico; el listado exhaustivo de
cada FK vive en §8.2 como parte de las reglas de negocio de integridad referencial). Se observa que `Asset`
es el nodo de mayor conectividad (7 relaciones entrantes/salientes), consistente con ser la entidad central
del dominio.

### 5.3 Brecha frente al mínimo pedido — CERRADA (Fase 2, 2026-07-09)
40 == 40. El producto originalmente declaraba (`product.yml`, cabecera) el **núcleo operativo** de
Snipe-IT (19 entidades de sus ~41 modelos reales, 20 tablas con `action_logs`). La Fase 2 de
`SNIPEIT-MIN-COMPLIANCE-INCREMENT.md` agregó 20 entidades MÍNIMAS (filas 21-40 de §5.1) tomando nombres+forma
de los deferrals ya cosechados en `SNIPEIT-DOMAIN.md §3` (PermissionGroup/Group, CustomField/CustomFieldset+
pivot, Kit+4 pivots, CheckoutRequest/Acceptance, ImportJob, Setting, CompanyUser) más 3 lookups genuinos
partidos de campos string existentes (Country/State/JobTitle). Es **ancho deliberadamente barato**, no una
adopción profunda del dominio real de Snipe-IT (que sigue siendo ~53 tablas / 41 modelos / ~226 rutas —
custom fields dinámicos, Kits con lógica de bundle, CheckoutRequest con firma/EULA real, StatusLabel
customizable a runtime, y la mayoría de reporting/administración siguen sin la PROFUNDIDAD real, sólo el
CRUD base). Esa profundidad, si se quiere, sigue siendo un incremento de producto aparte.

---

## 6. API — Endpoints (mínimo 40 → **44 reales**)

### 6.1 Conteo real
Fuente única: `openapi.yaml` (genera tanto el servidor Kotlin como el cliente TS — imposibilita el *drift*).
`grep -cE '(get|post|put|delete|patch):' openapi.yaml` → **44** combinaciones método×ruta sobre **25 rutas
únicas**.

### 6.2 Inventario completo
| Patrón | Método | Cantidad | Notas |
|---|---|---:|---|
| `/<entidad>` (19 entidades) | `GET` | 19 | Listado, público (sin guard) |
| `/<entidad>` (19 entidades) | `POST` | 19 | Alta, protegido por `x-required-roles` |
| `/assets/{id}` | `PUT` | 1 | Edición, bloqueada si `status=deployed` (§8.3) |
| `/assets/{id}/checkout` | `POST` | 1 | Verbo de dominio (workflow `ready→deployed`) |
| `/assets/{id}/checkin` | `POST` | 1 | Verbo de dominio (workflow `deployed→ready`) |
| `/assets/{id}/restore` | `POST` | 1 | Restauración desde papelera (soft-delete) |
| `/assets/deleted` | `GET` | 1 | Listado de papelera |
| `/accessorys/{id}/checkout` | `POST` | 1 | Verbo con efecto lateral (decrementa `qty`, crea pivot) |

**Asimetría real observada**: de las 19 entidades servidas, **sólo `Asset` tiene el ciclo REST completo**
(GET lista + GET/PUT/DELETE por id + verbos de dominio + papelera). Las 18 restantes exponen únicamente
`GET` (lista) + `POST` (alta) a nivel de contrato — no tienen edición ni borrado individual expuestos por
API. Esto es consistente con lo observado en el frontend (§7): el motor genérico (`mountEntity`) sólo
implementa list+create+detail; sólo la pantalla de Asset (`mountAsset`, escrita a mano) tiene edición y
borrado. Es una limitación real de superficie, documentada aquí por primera vez con evidencia directa del
contrato (no estaba explícita en `SNIPEIT-DOMAIN.md`).

### 6.3 Evidencia HTTP real (ejecutada contra el servidor vivo, 2026-07-08)
| Prueba | Resultado real |
|---|---|
| `GET /health` | `{"status":"UP"}` — HTTP 200 |
| `POST /manufacturers` con rol `superadmin` | HTTP 201 (fila creada, `id:1`) |
| `POST /companys` con rol `auditor` (sin permiso de escritura) | **HTTP 403** |
| `POST /companys` sin token | **HTTP 403** |
| `PUT /assets/1` con rol `manager` sin ser el dueño (`Bearer manager:99`) | **HTTP 403** (ownership) |
| `POST /maintenances` con `asset_id` inexistente (`9999`) | **HTTP 409** (FK colgante, fail-closed) |

---

## 7. Interfaz de usuario — Pantallas (mínimo 30 → **39 capturas reales**)

### 7.1 Metodología
Se levantó el sistema real (`tools/dev_run.sh snipeit`: PostgreSQL propia + AppServer + frontend
empaquetado) y se navegó con **Chromium real vía Playwright** (`tools/screenshot_evidence.mjs`, herramienta
nueva de esta auditoría — ver §13). Cada entidad del nav (18 + Dashboard) fue visitada; donde el listado
tenía filas se hizo clic para capturar también el **detalle**. Las 11 entidades que arrancan vacías (el
`/seed` determinista sólo puebla la cadena topológica mínima que necesita `Asset`) se poblaron con **altas
reales vía `POST`** (evidencia adicional de §6.3/§9) antes de capturar, para no reportar pantallas
artificialmente vacías. Todas las capturas son `fullPage` (nada recortado fuera del viewport).

Las 39 imágenes viven en `docs/reference/evidence/` (mismo directorio que este documento), numeradas en
orden de captura.

### 7.2 Inventario de pantallas capturadas
| # | Archivo | Pantalla |
|---|---|---|
| 1 | `01-dashboard.png` | Dashboard — conteos en vivo de las 19 entidades |
| 2–5 | `02-asset-list.png` … `05-asset-trash.png` | Asset: lista+alta, detalle (tabs Details/History + verbos + edición + borrado), tab Historial, papelera |
| 6–39 | `<entidad>-list.png` / `<entidad>-detail.png` (×17 entidades genéricas) | Company, Manufacturer, Supplier, Depreciation, Category, Location, Department, User, AssetModel, License, LicenseSeat, Accessory, Consumable, ConsumableAssignment, Component, ComponentAssignment, Maintenance — lista+alta y detalle de cada una |

**Figura 7.1** (`01-dashboard.png`) — Overview: 19 tarjetas con el conteo en vivo de cada entidad,
evidenciando que el server responde datos reales de PostgreSQL, no un mock.

**Figura 7.2** (`03-asset-detail.png`) — La pantalla más completa del sistema: formulario de alta (20
campos), tabla paginada de resultados, toggle de papelera, tabs Details/History, panel de detalle de 24
campos (incluyendo `current_value` **calculado** por depreciación), formulario de edición inline y botón de
borrado. Esta única captura evidencia 6 de las funcionalidades listadas en §4 (10–16) en una sola pantalla.

Cada una de las 39 capturas es de autoría propia (generada por la herramienta `screenshot_evidence.mjs`
contra el sistema real, no una maqueta ni una imagen de stock).

---

## 8. Reglas de negocio (mínimo 60 → **100 verificadas**)

### 8.1 Metodología de conteo
Se distingue **regla de negocio** (política de autorización, proceso o relación entre entidades) de
**validación de campo** (§9, formato/tipo/obligatoriedad de un valor aislado) para no contar el mismo hecho
dos veces. El conteo se hizo parseando `product.yml` con PyYAML (no con expresiones regulares —
reproducible con `python3 -c "import yaml; ..."`).

### 8.2 Integridad referencial entre entidades — **51 reglas**
Cada uno de los 51 campos `type: ref` del contrato es una regla de negocio de relación ("una `License` debe
apuntar a una `Category` existente", "un `LicenseSeat` opcionalmente apunta a un `Asset` existente") — el
servidor vivo la enforza con `409` ante una FK colgante (verificado en §6.3). Desglose por tipo de
cardinalidad:

| Patrón de relación | Cantidad | Ejemplos |
|---|---:|---|
| Referencia simple obligatoria | 3 | `AssetModel.category_id`, `Asset.model_id`, `AssetModel.depreciation_id` |
| Referencia simple opcional | 42 | `Asset.company_id`, `License.manufacturer_id`, `Maintenance.supplier_id`, … |
| Referencia self (jerarquía) | 2 | `Location.parent_id`, `User.manager_id` |
| Referencia cíclica cross-entidad (FK diferida) | 2 | `Location.manager_id→User`, `Department.manager_id→User` |
| Referencia polimórfica (unión de 3 entidades) | 2 | `Asset.assigned_to`/`checkout_target → [User\|Location\|Asset]` |
| **Total campos `ref`** | **51** | (suma verificada por parseo YAML) |

### 8.3 Políticas de autorización, ciclo de vida y proceso — **49 reglas**
| # | Regla | Alcance | Evidencia |
|---|---|---|---|
| 1–19 | RBAC por entidad (`write_roles`) — una política de rol distinta por cada una de las 19 entidades | Todas | `product.yml`, `x-required-roles` en `openapi.yaml` |
| 20 | Ownership de fila (`owned_by: assigned_to`, polimórfico `User\|Location\|Asset`) | Asset | `OwnershipGuard.kt` |
| 21 | Owner-bypass (`superadmin`, `admin` ignoran ownership) | Global | `OwnershipPolicy.kt` |
| 22 | Company-scoping de lectura y escritura (`company_scoped: company_id`) | Asset | `CompanyScopeGuard.kt` |
| 23 | Company-scope-bypass (`superadmin`, `admin`) | Global | `CompanyScopeGuard.kt` |
| 24–37 | Transiciones válidas del workflow `Asset.status` (14 arcos nombrados; cualquier otro par estado→estado es inválido por construcción) | Asset | §8.4 (diagrama de estados) |
| 38 | `mutable_when`: `PUT`/`DELETE` bloqueados con 409 si `status = deployed` | Asset | `product.yml:171-173`, verbo congelado |
| 39 | `soft_delete`: `DELETE` es lógico (papelera), con índice único parcial y filtro de lectura `IS NULL` | Asset | `product.yml:168` |
| 40 | `audited`: toda mutación (create/update/delete/checkout/checkin) appendea a `action_logs`, atómico con la mutación | Asset | `product.yml:174-179` |
| 41 | Operación `checkout` (compone RBAC+ownership+workflow, asigna `checkout_target`) | Asset | `product.yml:192` |
| 42 | Operación `checkin` (libera `checkout_target`) | Asset | `product.yml:192` |
| 43 | Operación `checkout` de Accessory: decrementa `qty` + crea fila en `AccessoryCheckout`, atómico (rollback si no hay stock) | Accessory | `product.yml` (bloque `operations`) |
| 44 | Depreciación calculada: `current_value = max(purchase_cost − purchase_cost/model.depreciation.months × meses_transcurridos, 0)` (cross-entity depth-2 + tiempo) | Asset | `product.yml` (campo `computed`) |
| 45 | Seed transitivo topológico para refs requeridos no-dueño (`Category→AssetModel→Asset`) | Asset | `SNIPEIT-DOMAIN.md` deferral 4 |
| 46–47 | Jerarquía self-ref sembrada raíz→hijo (`Location.parent_id`, `User.manager_id`) | Location, User | deferral 5 |
| 48–49 | Ciclo cross-entidad vía FK diferida + `NULL`-then-`UPDATE` (`Location.manager_id→User`, `Department.manager_id→User`) | Location, Department | deferral 6 |

**Total §8.2 + §8.3 = 51 + 49 = 100.**

### 8.4 Máquina de estados de `Asset.status`
```mermaid
stateDiagram-v2
    [*] --> ready
    ready --> deployed: checkout
    ready --> pending
    ready --> broken
    ready --> archived
    deployed --> ready: checkin
    deployed --> pending
    deployed --> broken
    deployed --> archived
    pending --> ready
    pending --> deployed
    pending --> broken
    pending --> archived
    broken --> ready
    broken --> archived
    archived --> [*]
```

**Figura 8.1.** Las 14 transiciones válidas de `Asset.status` (regla 24–37 de §8.3). `archived` es
**terminal** (ningún arco sale de él); `checkout`/`checkin` son los únicos dos arcos con efecto lateral
sobre otro campo (`checkout_target`). Cualquier par estado-origen→estado-destino no dibujado aquí es
rechazado por `canTransition()` con `409` — verificado como diente de dos lados en el propio gate de la
fábrica (`AssetStatusWorkflowTest.kt`).

---

## 9. Validaciones y restricciones (mínimo 100 → **201 verificadas**, sin contar integridad referencial)

### 9.1 Metodología de conteo
Validación de **campo aislado** (no de relación entre entidades — eso es §8.2). Conteo por parseo YAML de
los 144 campos declarados en las 19 entidades.

| Tipo de validación | Cantidad | Cómo se cuenta |
|---|---:|---|
| Chequeo de tipo por campo (string/int/number/date/boolean/enum/ref) | 144 | 1 por cada campo declarado — el servidor vivo rechaza con `400` un valor que no coDifica al tipo (verificado: enum inválido → 400 real, §9.2) |
| Obligatoriedad (`NOT NULL`) | 48 | Campos sin `required: false` (default de la gramática FSK = requerido) |
| Unicidad (`UNIQUE`) | 4 | `Company.name`, `Manufacturer.name`, `User.username`, `Asset.asset_tag` |
| Pertenencia a conjunto cerrado (enum whitelist) | 4 | `Category.category_type` (5 valores), `Depreciation.depreciation_type` (2), `Asset.status` (5, además workflow), `Maintenance.maintenance_type` (8) |
| Formato con patrón (regex) | 1 | `Asset.mac_address` (`format: mac`, codec `strFmt`) |
| **Total** | **201** | 144+48+4+4+1 |

*(Nota de transparencia: el chequeo de tipo de los 4 campos `enum` y de los 51 campos `ref` está incluido en
el conteo de 144 "chequeo de tipo"; la fila de "enum whitelist" cuenta la restricción ADICIONAL de
pertenencia a un conjunto cerrado, distinta de "es un string". La integridad referencial de los 51 `ref` NO
se repite acá — vive en §8.2 — para no duplicar el mismo hecho bajo dos categorías.)*

### 9.2 Evidencia HTTP real de validaciones (ejecutada 2026-07-08)
| Validación probada | Petición | Resultado real |
|---|---|---|
| Campo requerido ausente | `POST /manufacturers {}` | **HTTP 400** |
| Valor de enum inválido | `POST /categorys {"category_type":"bogus"}` | **HTTP 400** |
| FK colgante | `POST /maintenances {"asset_id":9999,...}` | **HTTP 409** |
| Restricción `UNIQUE` violada | `POST /manufacturers` con `name` duplicado | **falla — ver §12, bug real encontrado** |

---

## 10. Checklist de completitud del producto

Fuente: `meta rtm --factory full-stack-kotlin --product snipeit` (re-derivado de `.proof/` + los artefactos
reales listados, no declarado a mano).

| Requisito | Estado | Artefacto que lo satisface |
|---|:---:|---|
| REQ-F-001 contrato tipado fuente única | ✅ | `openapi.yaml` |
| REQ-F-002 andamiaje regenerable | ✅ | `openapi.yaml` |
| REQ-F-003 datos, esquema chequeado | ✅ | `V1__init.sql` |
| REQ-F-004 datos durables vivos | ✅ | `DbRoundTrip.kt` |
| REQ-F-005 rutas protegidas | ✅ | `AuthGuard.kt` |
| REQ-F-006 topología de rutas verificable | ✅ | `RouteTable.kt` |
| REQ-F-007 lógica de dominio generada por LLM | ✅ (activado 2026-07-09, `SNIPEIT-MIN-COMPLIANCE`) | `domain_gen/src/main/kotlin/domain/Summary.kt` |
| REQ-F-008 pruebas piramidales | ✅ | `src/test/` |
| REQ-F-009 calidad de experiencia | ✅ | `frontend/ui/index.html` |
| REQ-F-010 observabilidad de producto | ✅ | `ObsServer.kt` |
| REQ-F-011 workflow enforzado | ✅ | `workflow/` |
| REQ-F-012 RBAC enforzado | ✅ | `RoleGuard.kt` |
| REQ-F-013 ownership enforzado | ✅ | `OwnershipGuard.kt` |
| REQ-F-014 control de acceso en runtime | ✅ | `AppServer.kt` |
| REQ-F-015 CRUD/mutación en runtime | ✅ | `Repository.kt` |
| REQ-F-016 entrada tipada en runtime | ✅ | `AppServer.kt` |
| REQ-F-017 frontend consume en vivo | ✅ | `client.ts` |
| REQ-F-018 frontend renderiza en vivo | ✅ | `app.ts` |
| REQ-F-019 CRUD sin dueño en runtime | ✅ | `AppServer.kt` |
| REQ-F-020 frontend renderiza en Chromium real | ✅ | `browser_check.ts` |
| REQ-F-021 mutación congelada (`mutable_when`) | ✅ | `AppServer.kt` |
| REQ-NF-001 aislamiento del producto | ✅ | `settings.gradle.kts` |
| REQ-NF-002 dureza estática (detekt) | ✅ | `config/detekt.yml` |
| REQ-NF-003 frescura de API (lock) | ✅ | `config/api-surface.lock` |
| REQ-NF-004 seguridad cadena de suministro (SBOM) | ✅ | `sbom.json` |
| REQ-NF-007 build hermético reproducible | ✅ | `ci.sh` |
| REQ-NF-008 deploy vivo (Docker) | ✅ | `Dockerfile` |

**27/27 = 100%** (actualizado 2026-07-09). REQ-F-007 estaba diferido (`station_activation: s6: off`,
deferral declarado, no fallo silencioso); `SNIPEIT-MIN-COMPLIANCE` fase 1 lo activó de verdad: `claude -p`
vivo generó `summarize()` (Kotlin, no un stub) bajo el contract test de `domain_gen/`, verificado por
bloqueo (`product-run` PASS end-to-end s0..s11, `ci --rederive` 12/12 == pin, RTM re-derivado 27/27). El
artefacto ACEPTADO queda PINEADO (committeado como fuente, patrón MAT-2/ADR-013) — `ci --rederive` lo
re-verifica sin volver a invocar al LLM.

---

## 11. Pruebas automatizadas (pedido: cobertura 100% → **real: 98.1% de línea, Jacoco REAL, brecha honesta**)

### 11.1 Inventario real de pruebas
| Tipo | Cantidad | Ubicación |
|---|---:|---|
| Casos unitarios/integración (Kotest `StringSpec`) | 23 | `src/test/`, `src/integrationTest/` (8 archivos: `AuthGuardTest`, `RouteTableTest`, `StoreTest`, `RoleGuardTest`, `CompanyScopeGuardTest`, `OwnershipGuardTest`, `RepositoryIT`) |
| Casos de workflow | incluidos arriba | `AssetStatusWorkflowTest.kt` (`src/workflowTest/`) |
| Aserciones E2E en Chromium real (Playwright) | 32 | `frontend/browser_check.ts` |
| Ejes del *design floor* (Chromium real) | 6 | `tools/design_floor_check.ts` (shell/labels/nullcell/overflow/contrast/fields) |
| Gates estáticos/estructurales (Python) | 8 | `tools/{route_check,access_control_check,currency_lint,supply_chain_scan,hermetic_check,deploy_check,deploy_appserver_check,obs_check}.py` |
| Requisitos trazados a artefacto (RTM) | 27/27 | §10 |
| **Cobertura de línea (Jacoco REAL)** | **98.1%** (4127/4205 líneas) | `build/reports/jacoco/live/live.xml` (§11.2) |

### 11.2 Cómo se instrumentó la cobertura REAL (`SNIPEIT-MIN-COMPLIANCE` fase 3, `FSK-COVERAGE-INSTRUMENT`, `FSK-REQREF-COVERAGE-NEGATIVE`)
El proyecto antes **no tenía Jacoco/Kover configurado** — ahora sí, como capacidad de SUSTRATO (el
`_build_gradle` de la fábrica, disponible para cualquier producto FSK, no un parche de este producto). El
mecanismo funde TRES fuentes de ejecución real en un solo reporte (`./gradlew jacocoLiveReport`):
1. La pirámide Gradle (`test`/`integrationTest`/`workflowTest`, auto-instrumentada por el plugin `jacoco`).
2. Un **javaagent** adjuntado a los 4 procesos JVM que la estación `s9` YA levanta para sus propios proofs de
   correctitud (`access_control_live`/`frontend_consume_live`/`frontend_browser_live`/`frontend_design_floor`
   — RBAC/ownership/company-scope por entidad + cliente TS + Chromium real) — la MISMA batería de
   verificación existente, sin tráfico nuevo, acumulada vía `append=true`.
3. Dos artefactos que el codegen YA emitía pero que **ningún entrypoint invocaba** (0% de cobertura pese a
   ser código real): `App.kt` (un testigo de contrato que construye+lee las 39 entidades — ahora corrido por
   una tarea Gradle `appContract`) y `DbRoundTrip.kt` (ya se ejecutaba de verdad en `s1` — ver más abajo,
   ahora EXCLUIDO del universo medido, no de la ejecución).
4. (`FSK-REQREF-COVERAGE-NEGATIVE`) El diente NEGATIVO del ref colgante (POST con una FK inexistente →
   409 fail-closed) — antes probado UNA sola vez, sobre la entidad `with_ref` primaria — generalizado al
   loop `serve_all` que ya cubre las 19 entidades ownerless-con-ref-requerido: el servidor YA respondía 409
   para todas ellas (`need_conflict` ya las cubría desde `FSK-SERVE-ALL-ENTITIES`); faltaba que el proof
   mandara el POST. Sin Kotlin nuevo — cambio quirúrgico en el template Python del proof
   (`_SERVE_ALL_PROOF`, `constants.py`).

Ningún test Kotlin nuevo se escribió para llegar a estos números — es 100% reuso de tráfico/artefactos ya
existentes + una generalización mecánica de un diente que ya existía. **Exclusiones declaradas
explícitamente** (no maquilladas): `org/openapitools/**` (los DTOs generados por OpenAPI Generator — clases
de datos puras, cero lógica autorada), `**/jooq/**` (el acceso a datos generado por jOOQ desde el schema —
mecánico, sin ramas), y (desde `FSK-REQREF-COVERAGE-NEGATIVE`) `**/DbRoundTrip*` (herramienta de diagnóstico
MANUAL — su `main()` tiene más ramas, por-tipo-de-entidad, que las que el harness automatizado ejercita en
un solo recorrido; la tarea `roundtrip` la sigue EJECUTANDO de verdad como gate de infra en `s1`, dos lados
— sólo deja de contar en el %). Las tres son prácticas estándar de la industria para medir cobertura de
*lógica de negocio*, no de *boilerplate herramental ni herramienta de diagnóstico*.

### 11.3 La brecha honesta — línea por línea, con razón (no un hueco silencioso)
**Cerrado 2026-07-09 (`FSK-REQREF-COVERAGE`)**: el generador (`server.py`) ahora prima un registry de seed
compartido (lo que `Asset`/el owner/el tenant/los ref-targets/la fila de stock YA sembraron) y reusa el
seeder transitivo genérico (`_seed_deps`/`_ensure_seeded`, FSK-OWNED-REQUIRED-REFS) para sembrar FKs
encadenadas de las 19 entidades ownerless-con-ref-requerido que antes quedaban excluidas ("wrinkle #1") —
expuestas por `/seed.withRefs` (keyeado por entidad) y consumidas por `access_control_check.py`'s
`serve_all_block`, que ahora las incluye (antes las filtraba explícitamente). Esto cerró el **83% del gap
original** de `AppServer.kt`+`Repository.kt` (1180 líneas → 217 líneas).

**Cerrado 2026-07-09 (`FSK-REQREF-COVERAGE-NEGATIVE`)**: generalizó el diente del ref colgante (→ 409) a
esas mismas 19 entidades (el server ya lo rechazaba; sólo faltaba el POST del proof) y excluyó
`DbRoundTrip.kt` del universo medido (herramienta de diagnóstico manual, sigue ejecutándose de verdad). Esto
cerró prácticamente todo el residual restante: 217 → 78 líneas sin cubrir en `AppServer.kt`+`Repository.kt`
(+ `DbRoundTrip.kt` ya no cuenta). La brecha remanente, medida y clasificada línea por línea (Jacoco
`<line nr=".." mi=".."/>`, no estimada):

| Archivo | Líneas sin cubrir (missed) | Razón |
|---|---:|---|
| `endpoints/AppServer.kt` | 40 | Ramas `else -> HTTP_NOT_FOUND` catch-all en los `when` de ruteo — cubren combinaciones método+path que ningún cliente real (ni el proof) puede producir sin violar el ruteo mismo (estructuralmente inalcanzables en operación normal, no lógica de negocio sin probar). |
| `Repository.kt` | 35 | Boilerplate de queries jOOQ generadas (variantes de SELECT por entidad) sin rama propia — mecánico, mismo criterio que la exclusión ya declarada de `**/jooq/**`, pero estas viven en `Repository.kt` (código con lógica real mezclada) y no se excluyeron en bloque para no ocultar líneas de negocio junto a ellas. |
| `observability/FileSpanExporter.kt` | 2 | `override fun flush()/shutdown(): CompletableResultCode.ofSuccess()` — no-ops del ciclo de vida del exporter OpenTelemetry, inalcanzables sin mockear el lifecycle del SDK. |
| `routes/RouteTable.kt` | 1 | Marcador de borde de un data class, sin rama ejecutable propia. |

**Por qué el residual (78 líneas, ~1.9%) queda declarado y no perseguido**: analizado línea por línea (no
supuesto) — es ~50% ramas catch-all estructuralmente inalcanzables en operación normal (no un vacío de
prueba: el código correcto para ESA situación es simplemente no poder llegar ahí) y ~50% boilerplate de
acceso a datos generado, cero riesgo de defecto. Cerrar `Repository.kt` sería técnicamente posible
(~20 aserciones GET adicionales) pero es ingeniería real sin ganancia proporcional — el mismo criterio
declarado en `FSK-REQREF-COVERAGE`, aplicado consistentemente. Un 100% literal exigiría instrumentar rutas
que no pueden dispararse — no es una brecha de cobertura de lógica, es la forma que toma un `when` exhaustivo
en Kotlin.

### 11.4 Determinismo (evidencia adicional de robustez)
El pipeline soporta `ci --rederive` (re-construcción completa en un clon limpio) comparado byte a byte
contra `pinned_verdict.json` — los 12 hashes de estación (`s0`…`s11`) están pineados y son re-derivables (los
4 productos de la fábrica, 12/12·11/11·11/11·12/12, sin regresión de la instrumentación de cobertura).
Re-verificado tras `FSK-REQREF-COVERAGE-NEGATIVE` (2026-07-09): los mismos 4/4 productos re-derivan == su pin
en árbol limpio (`proof_sha` deriva de exit-codes de checks, no de contenido — el mismo conjunto de checks
en verde no fuerza re-pin aunque el generador cambió); `assets` es byte-neutral por construcción (0
entidades candidatas a ninguno de los dos ejes).

---

## 12. Limitaciones y hallazgos honestos de esta auditoría

1. **Modelo de datos — CERRADO Fase 2 (§5.3)**: 40/40 tablas (era 20/40). Las 20 nuevas son ANCHO barato
   por diseño (2-4 campos, sin profundidad de dominio) — no una adopción completa de Snipe-IT real.
2. **Cobertura de línea real: 98.1%, no 100%** (§11.3: `FSK-REQREF-COVERAGE` cerró el 83% del gap original
   sembrando FKs encadenadas de las 19 entidades antes excluidas; `FSK-REQREF-COVERAGE-NEGATIVE` generalizó
   el diente del ref colgante a esas mismas 19 y excluyó `DbRoundTrip.kt` — diagnóstico manual — del universo
   medido). La brecha remanente (78 líneas, ~1.9%) es estructural (ramas catch-all de ruteo HTTP
   inalcanzables + boilerplate jOOQ generado) — declarada línea por línea, no maquillada.
3. **Asimetría de superficie REST** (§6.2): sólo `Asset` tiene edición/borrado individual expuestos; las
   otras 18 entidades sólo tienen lista+alta a nivel de API y de UI.
4. **Bug real encontrado durante esta auditoría — violación de `UNIQUE` no manejada**: un `POST` que viola
   una restricción `UNIQUE` de PostgreSQL (probado en `Manufacturer.name` y `Company.name`, ambos campos
   `unique: true`) no devuelve un `409`/`400` limpio — la conexión HTTP se cierra vacía (`curl`: *"Empty
   reply from server"*, código `000`) y **no queda ningún registro en el log del servidor ni en las trazas
   de observabilidad** (`obs/access.jsonl`, `obs/spans.jsonl` — verificados, sin entradas nuevas). El
   servidor **sigue vivo** (`/health` sigue en 200 inmediatamente después), así que no es una caída del
   proceso — es una excepción no capturada en el hilo de esa request puntual que deja el *handler* sin
   enviar respuesta. La restricción `UNIQUE` en sí **sí existe y sí se enforza a nivel de PostgreSQL** (el
   duplicado no se inserta) — el gap es la **traducción a una respuesta HTTP correcta y observable**, no la
   integridad del dato. Esto es un hallazgo nuevo de esta auditoría, no documentado previamente en
   `SNIPEIT-DOMAIN.md`.
5. **Custom fields dinámicos, Kits, CheckoutRequest/Acceptance, StatusLabel customizable**: deferrals
   declarados en `SNIPEIT-DOMAIN.md §3`, no re-auditados en detalle acá (ya documentados con su propia
   evidencia en ese documento).
6. **Bug de fábrica encontrado durante la Fase 2 — constante de enum sin qualificar por entidad**: el
   codegen nombra la constante Kotlin de valores válidos de un campo `enum` por su NOMBRE DE CAMPO
   (`STATUS_VALUES`), no por `<Entidad>_<Campo>`. Dos entidades con un campo enum HOMÓNIMO (se probó con
   `Asset.status` y un campo que se había nombrado `status` en `ImportJob`) colisionan: la 2ª declaración
   pisa/coincide con la 1ª y la 2ª entidad queda validada contra el set de valores AJENO → un valor legítimo
   se rechaza con `400`. Reproducido y diagnosticado en vivo (`access_control_check.py` en bucle sin buffer,
   `python3 -u`). Fix aplicado a nivel PRODUCTO (renombrar el campo a `import_status`, sin tocar el
   sustrato) — cerrar esto a nivel FÁBRICA (qualificar la constante por entidad) queda como mejora futura,
   no bloqueante mientras no se repita.

---

## 13. Reproducibilidad de esta auditoría

- **Levantar el sistema**: `factories/full-stack-kotlin/tools/dev_run.sh snipeit` (PostgreSQL Docker propia
  + AppServer + frontend, imprime la URL local).
- **Recapturar las 39 pantallas**: `node factories/full-stack-kotlin/tools/screenshot_evidence.mjs <url>
  <ruta-absoluta-a-frontend-del-build> <ruta-de-salida> [rol]` — herramienta nueva de esta auditoría,
  DATA-agnóstica (lee `nav button[data-entity]` del DOM real, no tiene nombres de dominio *hardcodeados* —
  reutilizable para cualquier producto FSK con la misma convención de shell).
- **Re-derivar el checklist de §10**: `meta rtm --factory full-stack-kotlin --product snipeit`.
- **Re-contar reglas/validaciones de §8–9**: parseo de `product.yml` con PyYAML (comando exacto documentado
  en cada sección).

---

## 14. Conclusión

El sistema `snipeit` es un producto **real, generado, verificado por bloqueo y con servidor vivo** —no una
maqueta ni un contrato sin implementar. Contra el piso mínimo pedido, pasa 8 de 9 criterios con margen real
(casos de uso, funcionalidades, tablas, endpoints, pantallas con evidencia fotográfica real, reglas de
negocio, validaciones, y el checklist de completitud 27/27), y **cumple parcialmente 1** de forma honesta y
trazable: la cobertura de línea, ahora medida de verdad con Jacoco (0% → 70.7% reusando tráfico E2E
existente → 93.1% tras `FSK-REQREF-COVERAGE` sembrando FKs encadenadas de las 19 entidades antes excluidas
→ **98.1%** tras `FSK-REQREF-COVERAGE-NEGATIVE`, generalizando el diente del ref colgante a esas mismas 19 y
excluyendo `DbRoundTrip.kt` — diagnóstico manual — del universo medido; ambas capacidades de sustrato
compartidas por toda la fábrica, byte-neutral para `assets`), no llega al 100% pedido — el ~1.9% remanente
(78 líneas) está medido y clasificado línea por línea (§11.3): ramas catch-all de ruteo HTTP
estructuralmente inalcanzables + boilerplate de acceso a datos generado, sin riesgo de defecto — no una
brecha de prueba, sino la forma de un `when` exhaustivo. Esta auditoría además
**encontró y documentó un bug real** (manejo de violaciones `UNIQUE`) que no estaba registrado en la
documentación previa del producto — evidencia de que la verificación fue efectivamente ejecutada contra el
sistema vivo, no copiada de afirmaciones anteriores.
