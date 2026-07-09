"""scaffold — FSK product scaffolder package (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).

`build_files(bp)` assembles the full product tree (the pure bp->files map); `_load_blueprint` parses
the blueprint. The thin entry scaffold_product.py imports both. Deterministic codegen (DATA, ADR-012)."""
from __future__ import annotations


from .auth import _auth_guard_kt, _company_scope_guard_kt, _ownership_guard_kt, _ownership_policy_kt, _probe_phantom_route, _probe_unguarded_route, _probe_wrong_mutability, _probe_wrong_owner, _probe_wrong_roles, _role_enum_kt, _role_guard_kt, _route_check_py, _routes_kt
from .base import _live_entities, _owner_poly, _workflow_obj
from .browser import _browser_check_ts, _browser_entry_ts, _build_bundle_mjs, _consume_check_ts
from .buildcfg import _build_gradle, _settings_gradle, _ts_package_json
from .constants import _TS_TSCONFIG
from .contract import _openapi_yaml
from .data_layer import _app_kt, _it_repository_kt, _migration_sql, _repository_kt, _roundtrip_kt, _store_kt, _workflow_fields, _workflow_kt
from .deploy import _ci_sh, _deploy_appserver_check_py, _deploy_check_py, _dockerfile, _hermetic_check_py
from .frontend import _app_css, _app_ts, _client_ts, _ts_client_test, _ui_index_html
from .observability import _file_span_exporter_kt, _obs_check_py, _obs_server_kt, _observability_kt
from .pyramid import _probe_fail_test_kt, _test_authguard_kt, _test_company_scope_guard_kt, _test_ownership_guard_kt, _test_role_guard_kt, _test_routetable_kt, _test_store_kt, _test_workflow_kt, _ts_probe_fail_test
from .quality_tooling import _a11y_audit_mjs, _a11y_scorer_mjs, _api_surface_lock, _budget_json, _currency_lint_py, _detekt_yml, _editorconfig, _eslint_config, _perf_measure_mjs, _perf_scorer_mjs, _probe_bad_kt, _probe_bad_ts, _probe_bad_ui_html, _probe_bloated_ts, _probe_leak_secret, _probe_stale_kt, _probe_stale_ts, _probe_vuln_sbom, _reset_dts, _sbom_json, _supply_chain_lock, _supply_chain_scan_py
from .server import _access_control_check_py, _app_server_kt
from .blueprint import _load_blueprint

__all__ = ["build_files", "_load_blueprint"]


def build_files(bp: dict) -> dict[str, str]:
    pkg = bp["package_name"]
    ents = bp["entities"]
    pkgdir = f"src/main/kotlin/{pkg}"
    # FSK-MODELGEN-DURABLE (ADR-024): superficie humana pineada (frontend/app.ts + app.css). `surface` es {}
    # salvo que el producto opte in con `frontend_surface: model-native` (el loader carga el override en bp).
    # Cuando está, se COPIA verbatim el override en vez de emitir el template. Byte-neutral: {} -> template.
    surface = bp.get("_frontend_surface") or {}
    files = {
        "openapi.yaml": _openapi_yaml(bp),
        "settings.gradle.kts": _settings_gradle(pkg),
        "build.gradle.kts": _build_gradle(pkg),
        f"{pkgdir}/Store.kt": _store_kt(pkg, ents),     # Store.kt ⇄ object Store (DES-10 MatchingDeclarationName)
        f"{pkgdir}/App.kt": _app_kt(pkg, ents),
        # capa de datos (s1): schema versionado + jOOQ tipado + round-trip vivo
        "src/main/resources/db/migration/V1__init.sql": _migration_sql(bp),
        f"{pkgdir}/Repository.kt": _repository_kt(pkg, ents),
        f"{pkgdir}/DbRoundTrip.kt": _roundtrip_kt(pkg, ents),
        # dureza estática (s2, DES-10): config de los linters + fixtures NEGATIVOS (DATA de la fábrica)
        "config/detekt.yml": _detekt_yml(),
        ".editorconfig": _editorconfig(),
        "probe/kotlin/Bad.kt": _probe_bad_kt(),
        # frescura de API (s3, DES-11): el oráculo pineado + el linter determinista + el probe stale (DATA)
        "config/api-surface.lock": _api_surface_lock(),
        "tools/currency_lint.py": _currency_lint_py(),
        "probe/currency/StaleApi.kt": _probe_stale_kt(),
        "frontend/package.json": _ts_package_json(pkg),
        "frontend/tsconfig.json": _TS_TSCONFIG,
        "frontend/src/client.ts": _client_ts(ents),
        "frontend/src/reset.d.ts": _reset_dts(),
        "frontend/eslint.config.js": _eslint_config(),
        "frontend/probe/bad.ts": _probe_bad_ts(),
        "frontend/probe-currency/stale.ts": _probe_stale_ts(),
        # seguridad de la cadena de suministro (s4, DES-13): SBOM + oráculo de advisories + scanner + probes
        "sbom.json": _sbom_json(pkg),
        "config/supply-chain.lock": _supply_chain_lock(),
        "tools/supply_chain_scan.py": _supply_chain_scan_py(),
        "probe/security/vuln-sbom.json": _probe_vuln_sbom(),
        "probe/security/leak.txt": _probe_leak_secret(),
        # auth + topología de rutas (s5, DES-3/DES-2): guard + registro de rutas Kotlin + analizador + probes
        f"{pkgdir}/auth/AuthGuard.kt": _auth_guard_kt(pkg),
        f"{pkgdir}/routes/RouteTable.kt": _routes_kt(pkg, ents, bool(bp.get("roles"))),
        "tools/route_check.py": _route_check_py(),
        "probe/routes/phantom.kt": _probe_phantom_route(),
        "probe/routes/unguarded.kt": _probe_unguarded_route(ents),
        # pirámide de tests (s7, DES-8): suites graduadas (unit Kotlin + integración PG + unit TS) + probe negativo
        f"src/test/kotlin/{pkg}/AuthGuardTest.kt": _test_authguard_kt(pkg),
        f"src/test/kotlin/{pkg}/RouteTableTest.kt": _test_routetable_kt(pkg, ents),
        f"src/test/kotlin/{pkg}/StoreTest.kt": _test_store_kt(pkg, ents),
        f"src/integrationTest/kotlin/{pkg}/RepositoryIT.kt": _it_repository_kt(pkg, ents),
        f"src/testProbe/kotlin/{pkg}/ProbeShouldFailTest.kt": _probe_fail_test_kt(pkg),
        "frontend/test/client.test.ts": _ts_client_test(ents),
        "frontend/probe-test/fail.test.ts": _ts_probe_fail_test(),
        # calidad de experiencia (s8, DES-7): UI accesible generada + drivers a11y/perf + scorers + probes
        "frontend/ui/index.html": _ui_index_html(bp),
        "frontend/src/app.ts": surface["app_ts"] if surface else _app_ts(ents),   # FSK-MODELGEN-DURABLE: pinned override or template
        "frontend/eval/budget.json": _budget_json(len(_live_entities(ents))),
        "frontend/eval/a11y_audit.mjs": _a11y_audit_mjs(),
        "frontend/eval/a11y_scorer.mjs": _a11y_scorer_mjs(),
        "frontend/eval/perf_measure.mjs": _perf_measure_mjs(),
        "frontend/eval/perf_scorer.mjs": _perf_scorer_mjs(),
        "frontend/eval/probe/bad_ui.html": _probe_bad_ui_html(),
        "frontend/eval/probe/bloated.ts": _probe_bloated_ts(len(_live_entities(ents))),
        # observabilidad (s9, DES-5): server HTTP vivo + tracing OTel + logs estructurados + proof client (DATA)
        f"{pkgdir}/observability/FileSpanExporter.kt": _file_span_exporter_kt(pkg),
        f"{pkgdir}/observability/Observability.kt": _observability_kt(pkg),
        f"{pkgdir}/observability/ObsServer.kt": _obs_server_kt(pkg),
        "tools/obs_check.py": _obs_check_py(),
        # build hermético reproducible (s10, DES-1): la mini-columna del producto + el proof hermético + la
        # config de repro del build + la receta de deploy (Dockerfile base pineada por digest) — DATA de fábrica.
        "ci.sh": _ci_sh(),
        "tools/hermetic_check.py": _hermetic_check_py(pkg),
        "Dockerfile": _dockerfile(pkg),
        # deploy vivo (s11, DES-1): el smoke del contenedor construido — le pega /health y exige UP (DATA).
        "tools/deploy_check.py": _deploy_check_py(),
        # deploy del AppServer REAL en un contenedor con PG en una red docker (s11 deploy_appserver_live, DES-1):
        # le pega /health (connect+migrate al boot) + GET <plural> (fila sembrada → alcanza su PG). El plural,
        # horneado del blueprint (DATA), deja el argv de la estación product-agnóstico (sólo el base_url).
        "tools/deploy_appserver_check.py": _deploy_appserver_check_py(bp),
    }
    # workflows / máquinas de estado (s7, DES-3, R2/FSK-S12): OPT-IN — sólo se emiten para los campos enum que
    # declaran `transitions` (un enum sin máquina se comporta EXACTO como FSK-S11). El guard vive en el código
    # autorado (workflow/, type-bound al contrato); el test de dos lados, en la pirámide unit (src/test).
    for e, f in _workflow_fields(ents):
        obj = _workflow_obj(e, f)
        files[f"{pkgdir}/workflow/{obj}.kt"] = _workflow_kt(pkg, e, f)
        # tier dedicado `workflowTest` (source set propio, idiom integrationTest/testProbe): aísla el diente del
        # workflow → el check `workflow_enforced` lo corre solo (atribución limpia, sin filtro Kotest frágil).
        files[f"src/workflowTest/kotlin/{pkg}/workflow/{obj}Test.kt"] = _test_workflow_kt(pkg, e, f)
    # RBAC / autorización por rol (s5, DES-3, R2/FSK-S13): OPT-IN — sólo cuando el blueprint declara `roles`. El
    # enum Role + el RoleGuard se generan del blueprint; el RouteTable registra cada escritura con su set de
    # roles (ver _routes_kt); el contrato emite x-required-roles; route_check.py (modo rbac) cruza ambos; el
    # probe sucio (route_check rbac) y el test de dos lados (tier unit) muerden. Sin `roles`, FSK-S5 intacto.
    scoped_entities = [e for e in ents if e.get("company_scoped")]   # FSK-COMPANY-SCOPING (opt-in)
    if bp.get("roles"):
        files[f"{pkgdir}/auth/Role.kt"] = _role_enum_kt(pkg, bp["roles"])
        files[f"{pkgdir}/auth/RoleGuard.kt"] = _role_guard_kt(pkg, bool(scoped_entities))
        files["probe/routes/wrong_roles.kt"] = _probe_wrong_roles(bp)
        files[f"src/test/kotlin/{pkg}/auth/RoleGuardTest.kt"] = _test_role_guard_kt(pkg, bp)
    # company-scoping / multi-tenancy (FSK-COMPANY-SCOPING, DES-3): OPT-IN — sólo cuando ≥1 entidad declara
    # `company_scoped`. El guard CompanyScopeGuard.canAccess (genérico, type-safe sobre Role) + el test de DOS+
    # lados (tier unit). El AppServer vivo (s9) lo enforza (read-filter por compañía + verdict de escritura); el
    # bypass es DATA del blueprint (lo inyecta el AppServer). Compone sobre ownership+RBAC (exige `roles`). El
    # contrato emite x-company-scoped (FUENTE inspectable, DES-6). Sin `company_scoped`, FSK-S15 intacto.
    if scoped_entities:
        files[f"{pkgdir}/auth/CompanyScopeGuard.kt"] = _company_scope_guard_kt(pkg)
        files[f"src/test/kotlin/{pkg}/auth/CompanyScopeGuardTest.kt"] = _test_company_scope_guard_kt(pkg, bp)
    # ownership / autorización a nivel de FILA (s5, DES-3, R2/FSK-S14): OPT-IN — sólo cuando ≥1 entidad declara
    # `owned_by`. El guard OwnershipGuard.canModify (genérico, type-safe sobre Role) + el registro OwnershipPolicy
    # (entidad→campo dueño, derivado del blueprint); el contrato emite x-owned-by; route_check.py (modo ownership)
    # cruza ambos; el probe sucio (wrong_owner.kt) + el test de dos+ lados (tier unit, type-bound al model)
    # muerden. Compone sobre RBAC (exige `roles`). Sin `owned_by`, FSK-S13 intacto (sólo rol×entidad).
    owned = [e for e in ents if e.get("owned_by")]
    if owned:
        # FSK-OWNERSHIP-OPTIONAL: si CUALQUIER entidad con dueño lo declara `required: false` (un RTD sin
        # asignar), canModify pasa a `Long?` (acepta filas sin dueño); con todos los dueños requeridos queda
        # EXACTO (byte-idéntico → default/assets sin re-derivar). Opt-in por el `required` del `owned_by`.
        owner_optional = any(_owner_poly(e) is not None   # FSK-OWNER-POLY: un dueño poly es SIEMPRE owner-optional
                             or not next(f for f in e["fields"] if f["name"] == e["owned_by"]).get("required", True)
                             for e in owned)
        files[f"{pkgdir}/auth/OwnershipGuard.kt"] = _ownership_guard_kt(pkg, owner_optional)
        files[f"{pkgdir}/auth/OwnershipPolicy.kt"] = _ownership_policy_kt(pkg, owned, bp.get("owner_bypass_roles") or [])
        files["probe/routes/wrong_owner.kt"] = _probe_wrong_owner(bp)
        files[f"src/test/kotlin/{pkg}/auth/OwnershipGuardTest.kt"] = _test_ownership_guard_kt(pkg, bp)
        # endpoints VIVOS + control de acceso a RUNTIME (s9, DES-3, R2/FSK-S15): el server HTTP del producto
        # monta GET/POST/PUT de la entidad con dueño e INVOCA los guards (Auth→RBAC→ownership) + persiste/lee
        # contra la PG VIVA (Repository) → la trilogía de control de acceso pasa de estática/unit a runtime. El
        # proof e2e (urllib) lo asevera de DOS+ lados (403 por rol / 403 por dueño / 200 dueño / 200 bypass). El
        # server vive en src/main/kotlin (lo compila s0/s1, lo lintea detekt); el check `access_control_live`
        # (s9, infra_up) lo levanta por `java -cp` del dist (installDist) contra la PG viva. Opt-in: sólo con
        # owned_by (compone sobre ownership/RBAC). El sustrato no nombra tech: todo `codegen/`+spec (ADR-012).
        files[f"{pkgdir}/endpoints/AppServer.kt"] = _app_server_kt(pkg, bp)
        files["tools/access_control_check.py"] = _access_control_check_py(bp)
        # frontend que CONSUME + RENDERIZA el backend vivo (s9, DES-6/DES-4, FSK-FRONTEND-CONSUME/RENDER-LIST): el
        # cliente TS generado (frontend/src/client.ts) gana create<E>/get<E>/list<E> (fetch REAL contra el AppServer)
        # y el render generado (frontend/src/app.ts: render<E>List) renderiza la lista viva; el consumer node
        # (frontend/consume_check.ts) los importa y prueba e2e (round-trip create→get + list→render) contra el server
        # vivo + PG. El check `frontend_consume_live` (s9, infra_up) lo corre por `node --experimental-strip-types`.
        # Opt-in: sólo con owned_by (compone sobre el server vivo de FSK-S15). Sin tech nueva: fetch global, ADR-012.
        files["frontend/consume_check.ts"] = _consume_check_ts(bp)
        # frontend en un BROWSER REAL (s9, DES-7/DES-4, FSK-FRONTEND-BROWSER): el render generado (mount<E>/
        # render<E>List) deja de probarse SÓLO en jsdom y se monta en un Chromium HEADLESS real (Playwright). El
        # entry del bundle (browser_entry.ts) llama mount<E> al cargar la página REAL; esbuild (build_bundle.mjs)
        # lo bundlea a dist/app.js; el AppServer lo sirve MISMO-ORIGEN (GET / + GET /app.js → sin CORS); el proof
        # (browser_check.ts) abre GET / en Chromium y asevera que la lista VIVA se renderiza en el DOM real. El
        # check `frontend_browser_live` (s9, infra_up) lo corre. Opt-in: sólo con owned_by (la única con mount<E>).
        files["frontend/src/browser_entry.ts"] = _browser_entry_ts(bp)
        # FSK-FRONTEND-STYLES: la hoja de estilos (ARCHIVO APARTE, regla multi-archivo). esbuild la compila a
        # dist/app.css (build_bundle.mjs, 2da pasada); el AppServer la sirve en GET /app.css; index.html la linkea;
        # el proof browser_check.ts asevera que APLICA en Chromium real. DATA-agnóstica (estila clases semánticas).
        files["frontend/src/app.css"] = surface["app_css"] if surface else _app_css()   # FSK-MODELGEN-DURABLE: pinned override or template
        files["frontend/build_bundle.mjs"] = _build_bundle_mjs()
        files["frontend/browser_check.ts"] = _browser_check_ts(bp)
    # mutable_when / freeze by state (s5, DES-3, FSK-MUTABLE-WHEN): OPT-IN — sólo cuando ≥1 entidad
    # declara `mutable_when`. El probe sucio (wrong_mutability.kt) tiene un setOf INCORRECTO (incluye
    # estados FROZEN) → route_check.py (modo mutability) muerde (MUTABLE_MISMATCH); mutability_enforced
    # lo exige por grep (fail-closed). Vive en probe/mutability/ (fuera de src/) → no se compila ni se
    # shippea. Sin `mutable_when`, no se emite nada (byte-identical para todo lo previo).
    if any(e.get("mutable_when") for e in ents):
        files["probe/mutability/wrong_mutability.kt"] = _probe_wrong_mutability(bp)
    return files
