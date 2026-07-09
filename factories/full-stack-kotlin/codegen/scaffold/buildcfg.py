"""scaffold.buildcfg — Build configuration emitters (Gradle, package.json).

Part of the FSK product scaffolder (split from scaffold_product.py, Fase 3 MONOLITH-REFACTOR).
Deterministic codegen (DATA, ADR-012); the substrate names no Kotlin/Gradle/OpenAPI."""
from __future__ import annotations


from .constants import AXE_VERSION, DETEKT_VERSION, ESBUILD_VERSION, ESLINT_VERSION, FLYWAY_VERSION, JACOCO_VERSION, JDK_TOOLCHAIN, JOOQ_VERSION, JSDOM_VERSION, KOTEST_VERSION, KOTLINX_SER_VERSION, KOTLIN_VERSION, OPENAPI_GEN_VERSION, OPENAPI_TS_VERSION, OTEL_VERSION, PLAYWRIGHT_VERSION, POSTGRES_JDBC_VERSION, TS_ESLINT_VERSION, TS_RESET_VERSION, TS_VERSION


def _settings_gradle(pkg: str) -> str:
    return (f'// workspace Gradle AUTÓNOMO del producto (DES-9): nombra la raíz, sin includeBuild a la\n'
            f'// fábrica. El env de la gate (product_env) scrubbea PYTHONPATH/VENV → cargar la fábrica falla.\n'
            f'rootProject.name = "{pkg}"\n')


def _build_gradle(pkg: str) -> str:
    return f'''\
// Build pineado y reproducible (DES-1). openApiGenerate genera los models Kotlin del CONTRATO antes de
// compilar; el handler usa esos models → un drift del contrato rompe `compileKotlin` (DES-6).
plugins {{
    kotlin("jvm") version "{KOTLIN_VERSION}"
    kotlin("plugin.serialization") version "{KOTLIN_VERSION}"
    id("org.openapi.generator") version "{OPENAPI_GEN_VERSION}"
    id("org.jooq.jooq-codegen-gradle") version "{JOOQ_VERSION}"
    // Dureza estática (s2, DES-10): detekt corre el análisis de calidad + las reglas ktlint (formatting).
    id("io.gitlab.arturbosch.detekt") version "{DETEKT_VERSION}"
    // Observabilidad (s9, DES-5): `application` produce un launcher (installDist) → infra_up levanta el
    // server HTTP vivo del producto como un proceso java plano (no el daemon de gradle), kill-eable por grupo.
    application
    // Cobertura de línea real (SNIPEIT-MIN-COMPLIANCE fase 3, s9/DES-5): jacoco es un plugin INCORPORADO de
    // Gradle (sin repo extra) — instrumenta la pirámide de tests + el proceso vivo que s9 levanta como agente.
    id("jacoco")
}}
repositories {{ mavenCentral() }}
// `-Werror` (DES-10): TODO warning de kotlinc es error → el código falla FUERTE, no silencioso.
kotlin {{
    jvmToolchain({JDK_TOOLCHAIN})
    compilerOptions {{ allWarningsAsErrors = true }}
}}
// Observabilidad (s9, DES-5): el entrypoint del server HTTP vivo (com.sun.net.httpserver) instrumentado con
// OpenTelemetry. installDist genera build/install/{pkg}/bin/{pkg} → infra_up lo corre en background.
application {{ mainClass.set("{pkg}.observability.ObsServerKt") }}
dependencies {{
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:{KOTLINX_SER_VERSION}")
    // Capa de datos (s1, DES-12/4): jOOQ tipado + Flyway (migraciones versionadas) + driver PostgreSQL.
    implementation("org.jooq:jooq:{JOOQ_VERSION}")
    implementation("org.flywaydb:flyway-core:{FLYWAY_VERSION}")
    implementation("org.flywaydb:flyway-database-postgresql:{FLYWAY_VERSION}")
    implementation("org.postgresql:postgresql:{POSTGRES_JDBC_VERSION}")
    // Codegen jOOQ desde los .sql de Flyway (DDLDatabase) — sin DB viva (hermético, DES-12).
    jooqCodegen("org.jooq:jooq-meta-extensions:{JOOQ_VERSION}")
    // detekt-formatting = las reglas de ktlint DENTRO de detekt (un solo tool, sin conflicto de versiones).
    detektPlugins("io.gitlab.arturbosch.detekt:detekt-formatting:{DETEKT_VERSION}")
    // Observabilidad (s9, DES-5): OpenTelemetry SDK real (el motor de tracing) — el BOM pinea api+sdk.
    implementation(platform("io.opentelemetry:opentelemetry-bom:{OTEL_VERSION}"))
    implementation("io.opentelemetry:opentelemetry-api")
    implementation("io.opentelemetry:opentelemetry-sdk")
}}
// DES-10 — detekt SÓLO sobre el código autorado del producto (src/main/kotlin); los fuentes GENERADOS
// (openapi-generator, jOOQ en build/) quedan fuera por construcción. maxIssues:0 (config) → hallazgo = rojo.
detekt {{
    buildUponDefaultConfig = true
    config.setFrom(files("config/detekt.yml"))
    source.setFrom(files("src/main/kotlin"))
}}
jacoco {{ toolVersion = "{JACOCO_VERSION}" }}
// Cobertura E2E (SNIPEIT-MIN-COMPLIANCE fase 3): un agente Jacoco standalone (clasificador `runtime`,
// fat-jar, usable como -javaagent en un JVM lanzado FUERA de gradle) para instrumentar el proceso que
// `s9` levanta con `java -cp ... webapp.endpoints.AppServerKt`. installDist lo materializa siempre
// (dependsOn) para que la ruta sea estable sin tocar cada bootstrap de s9.yml.
// nombre PROPIO (no "jacocoAgent": esa config ya existe, creada por el plugin `jacoco` mismo, para SU
// uso interno con los Test tasks auto-instrumentados — reusar el nombre choca con "ya existe").
val jacocoAgentCfg = configurations.create("jacocoStandaloneAgent")
dependencies {{ add("jacocoStandaloneAgent", "org.jacoco:org.jacoco.agent:{JACOCO_VERSION}:runtime") }}
// `doLast` con `copy {{}}` imperativo (NO un `Copy` tipado con `into(layout.buildDirectory)`): declarar el
// output como TODO `build/` colisiona con los outputs de otras tasks anidadas ahí (generated-jooq,
// generated/src/main/kotlin) → Gradle lo marca "implicit dependency" (validación estricta) y rompe
// compileKotlin. Un `doLast` ad-hoc no declara outputs estáticos → sin ambigüedad, misma ruta final.
val copyJacocoAgent = tasks.register("copyJacocoAgent") {{
    doLast {{
        copy {{
            from(jacocoAgentCfg)
            into(layout.buildDirectory)
            rename {{ "jacocoagent.jar" }}
        }}
    }}
}}
tasks.named("installDist") {{ dependsOn(copyJacocoAgent) }}
// Diente NEGATIVO embebido (DES-10): detekt sobre un fixture deliberadamente sucio (probe/kotlin) DEBE
// fallar. El check static_hardness exige que muerda (grep de la regla) → un gate decorativo se delata.
tasks.register<io.gitlab.arturbosch.detekt.Detekt>("detektProbe") {{
    buildUponDefaultConfig = true
    config.setFrom(files("config/detekt.yml"))
    setSource(files("probe/kotlin"))
}}
val genDir = layout.buildDirectory.dir("generated")
openApiGenerate {{
    generatorName.set("kotlin")
    inputSpec.set("$rootDir/openapi.yaml")
    outputDir.set(genDir.get().asFile.path)
    globalProperties.set(mapOf("models" to ""))            // sólo models (data classes del contrato)
    configOptions.set(mapOf("serializationLibrary" to "kotlinx_serialization"))
}}
// jOOQ: tipos generados del schema versionado (db/migration/*.sql) por DDLDatabase. La DB GRITA en
// compilación (DES-12): un query a una columna inexistente no compila (ver Repository.kt).
jooq {{
    configuration {{
        generator {{
            name = "org.jooq.codegen.KotlinGenerator"
            database {{
                name = "org.jooq.meta.extensions.ddl.DDLDatabase"
                properties {{
                    property {{ key = "scripts"; value = "src/main/resources/db/migration/*.sql" }}
                    property {{ key = "sort"; value = "flyway" }}
                    property {{ key = "unqualifiedSchema"; value = "none" }}
                    property {{ key = "defaultNameCase"; value = "as_is" }}
                }}
            }}
            generate {{ isRecords = true }}
            target {{
                packageName = "{pkg}.jooq"
                directory = "build/generated-jooq"
            }}
        }}
    }}
}}
sourceSets["main"].kotlin.srcDir(genDir.map {{ it.dir("src/main/kotlin") }})
sourceSets["main"].kotlin.srcDir("build/generated-jooq")
tasks.named("compileKotlin") {{ dependsOn("openApiGenerate", "jooqCodegen") }}

// DES-4 — round-trip del producto contra una PostgreSQL VIVA (lo corre `infra_up` contra el contenedor).
// JavaExec corre SIEMPRE (no up-to-date) → el diente negativo de infra_up re-corre con la DB caída y debe fallar.
tasks.register<JavaExec>("roundtrip") {{
    dependsOn("classes")
    mainClass.set("{pkg}.DbRoundTripKt")
    classpath = sourceSets["main"].runtimeClasspath
}}
// Cobertura (SNIPEIT-MIN-COMPLIANCE fase 3): `roundtrip` YA corre en s1 (db_roundtrip_live, PG viva propia)
// -- sin adjuntarle jacoco explícitamente (el plugin NO lo hace por defecto sobre un JavaExec) esa corrida
// no dejaba ningún .exec, así que DbRoundTrip.kt quedaba fuera del universo medido pese a ejecutarse de
// verdad. El .exec queda en build/jacoco/roundtrip.exec (mismo build/product durante TODO el product-run)
// y `jacocoLiveReport` (s9) lo funde vía su fileTree -- sin forzar un re-run acá (la PG de s1 ya no está viva).
jacoco.applyTo(tasks.named<JavaExec>("roundtrip").get())
tasks.named<JavaExec>("roundtrip") {{
    extensions.configure<org.gradle.testing.jacoco.plugins.JacocoTaskExtension> {{
        destinationFile = layout.buildDirectory.file("jacoco/roundtrip.exec").get().asFile
    }}
}}

// appContract (cobertura, SNIPEIT-MIN-COMPLIANCE fase 3): App.kt es un TESTIGO DE CONTRATO que el codegen
// emite (construye + lee cada entidad del schema; un drift -- campo borrado -- no compila) pero que NINGÚN
// entrypoint shippeado invoca (el `application.mainClass` real es observability.ObsServerKt) -- quedaba
// 100% sin ejercitar en el universo medido. Correrlo (in-process, sin DB/red -- no es un test nuevo, es
// EJERCITAR el artefacto que el propio codegen ya emite para este fin) lo suma HONESTAMENTE. Se fija el
// destinationFile explícito (no asumir auto-config del plugin jacoco sobre JavaExec) para asegurar el .exec.
tasks.register<JavaExec>("appContract") {{
    dependsOn("classes")
    mainClass.set("{pkg}.AppKt")
    classpath = sourceSets["main"].runtimeClasspath
}}
// El plugin jacoco NO adjunta JacocoTaskExtension a un JavaExec por defecto (sólo a Test) -- hay que
// pedírselo explícitamente vía `jacoco.applyTo(...)` (la API pública de JacocoPluginExtension) ANTES de
// poder configurar el destinationFile.
jacoco.applyTo(tasks.named<JavaExec>("appContract").get())
tasks.named<JavaExec>("appContract") {{
    extensions.configure<org.gradle.testing.jacoco.plugins.JacocoTaskExtension> {{
        destinationFile = layout.buildDirectory.file("jacoco/appContract.exec").get().asFile
    }}
}}

// ── Pirámide de tests (s7, DES-8). Framework: Kotest sobre JUnit Platform (cacheado en ~/.gradle igual
//    que jOOQ/Flyway/detekt → ci --rederive sin red). La forma de la pirámide es EJECUTABLE: el tier unit
//    (`test`, src/test) corre SIN infra; el tier integración (`integrationTest`, src/integrationTest) corre
//    contra la PostgreSQL VIVA que infra_up levanta. El probe negativo (`testProbe`, src/testProbe) es un
//    test que DEBE fallar — el check exige que el runner lo reporte FAILED (mata la fachada "0 tests → verde").
dependencies {{
    testImplementation("io.kotest:kotest-runner-junit5:{KOTEST_VERSION}")
    testImplementation("io.kotest:kotest-assertions-core:{KOTEST_VERSION}")
}}
sourceSets {{
    create("integrationTest")
    create("testProbe")
    create("workflowTest")
}}
// integración usa los models/jOOQ/Flyway/PG del main (implementation) + Kotest (testImplementation).
configurations["integrationTestImplementation"].extendsFrom(
    configurations["implementation"], configurations["testImplementation"],
)
configurations["integrationTestRuntimeOnly"].extendsFrom(
    configurations["runtimeOnly"], configurations["testRuntimeOnly"],
)
configurations["testProbeImplementation"].extendsFrom(configurations["testImplementation"])
configurations["testProbeRuntimeOnly"].extendsFrom(configurations["testRuntimeOnly"])
configurations["workflowTestImplementation"].extendsFrom(configurations["testImplementation"])
configurations["workflowTestRuntimeOnly"].extendsFrom(configurations["testRuntimeOnly"])
sourceSets["integrationTest"].apply {{          // ve las clases compiladas del producto (Repository, jOOQ)
    compileClasspath += sourceSets["main"].output
    runtimeClasspath += sourceSets["main"].output
}}
sourceSets["workflowTest"].apply {{            // ve el guard del workflow + los enum class del contrato (main)
    compileClasspath += sourceSets["main"].output
    runtimeClasspath += sourceSets["main"].output
}}
tasks.named("test", Test::class) {{
    useJUnitPlatform()
    testLogging {{ events("failed") }}
}}
// Tier integración: los tests de Repository corren contra la PG VIVA (proof de infra_up); DB caída → rojo.
tasks.register<Test>("integrationTest") {{
    description = "Tier de integración de la pirámide (Repository vs PostgreSQL viva, s7/DES-8)."
    group = "verification"
    testClassesDirs = sourceSets["integrationTest"].output.classesDirs
    classpath = sourceSets["integrationTest"].runtimeClasspath
    useJUnitPlatform()
    testLogging {{ events("failed") }}
    outputs.upToDateWhen {{ false }}   // corre SIEMPRE (idiom roundtrip): infra_up re-corre el proof con la DB caída y DEBE fallar
    mustRunAfter(tasks.named("test"))
}}
// Diente negativo EMBEBIDO (s7): un test que DEBE fallar. El check `pyramid_unit` exige que gradle lo
// reporte FAILED (grep) — un runner que descubre 0 tests o no reporta fallos es DECORATIVO → rojo (fail-closed).
tasks.register<Test>("testProbe") {{
    description = "Probe negativo de la pirámide: un test que DEBE fallar (fail-closed, s7/DES-8)."
    group = "verification"
    testClassesDirs = sourceSets["testProbe"].output.classesDirs
    classpath = sourceSets["testProbe"].runtimeClasspath
    useJUnitPlatform()
    ignoreFailures = true     // la TAREA no rompe el build; el CHECK exige el FAILED por grep
    testLogging {{ events("failed") }}
    outputs.upToDateWhen {{ false }}   // corre SIEMPRE → el FAILED se imprime en cada corrida del gate (no UP-TO-DATE)
}}
// Tier WORKFLOW (s7, DES-3, R2/FSK-S12): el diente de DOS lados de cada máquina de estado (una transición
// declarada válida pasa / una no declarada se rechaza). Source set propio → el check workflow_enforced lo corre
// aislado del resto de la pirámide. Si NO hay enum con `transitions`, el source set está vacío → 0 tests (opt-in).
tasks.register<Test>("workflowTest") {{
    description = "Tier workflow: el guard canTransition de cada enum con transitions (s7/DES-3)."
    group = "verification"
    testClassesDirs = sourceSets["workflowTest"].output.classesDirs
    classpath = sourceSets["workflowTest"].runtimeClasspath
    useJUnitPlatform()
    testLogging {{ events("failed") }}
    outputs.upToDateWhen {{ false }}   // corre SIEMPRE (idiom roundtrip): el diente se re-evalúa cada corrida del gate
}}

// jacocoLiveReport (SNIPEIT-MIN-COMPLIANCE fase 3): fusiona el .exec de TODA la pirámide Gradle
// (test/integrationTest/workflowTest/roundtrip, auto-instrumentados por el plugin jacoco) CON el .exec
// externo que el javaagent (arriba) escribe cuando s9 levanta AppServerKt (accumulate vía append=true en
// el `up` de cada check infra_up) — cobertura real de TODA la batería de verificación, no sólo unit
// tests. Excluye boilerplate GENERADO (DTOs OpenAPI + acceso a datos jOOQ) del universo medido —
// declarado explícitamente (no maquillado), nunca el código de negocio autorado.
tasks.register<org.gradle.testing.jacoco.tasks.JacocoReport>("jacocoLiveReport") {{
    group = "verification"
    // SIN esta dependencia explícita, gradle puede programar jacocoLiveReport ANTES que test/workflowTest (no
    // hay relación implícita entre ellos) -> el fileTree de .exec lo ve VACÍO -> SKIPPED. El orden en el CLI
    // del check `coverage_live` NO alcanza (gradle no lo garantiza sin dependsOn/mustRunAfter). `integrationTest`
    // NO se lista acá a propósito: exige una PostgreSQL VIVA (la que `s7`/`pyramid_integration` ya levanta
    // ANTES en la MISMA corrida de product-run) — `coverage_live` (en `s9`, sin infra propia) sólo LEE el
    // `integrationTest.exec` que ya quedó en disco de esa corrida previa; forzar un re-run acá rompería sin PG.
    dependsOn("test", "workflowTest", "appContract")
    executionData.setFrom(fileTree(layout.buildDirectory.dir("jacoco")) {{ include("*.exec") }})
    sourceDirectories.setFrom(files("src/main/kotlin"))
    classDirectories.setFrom(fileTree(layout.buildDirectory.dir("classes/kotlin/main")) {{
        exclude("org/openapitools/**", "**/jooq/**")
    }})
    reports {{
        xml.required.set(true)
        html.required.set(true)
        xml.outputLocation.set(layout.buildDirectory.file("reports/jacoco/live/live.xml"))
        html.outputLocation.set(layout.buildDirectory.dir("reports/jacoco/live/html"))
    }}
}}

// ── Build hermético reproducible (s10, DES-1). La REPRODUCIBILIDAD es una propiedad DECLARADA del producto
//    (no un default del que dependemos): todo artefacto de archivo (jar/dist) sale byte-idéntico entre builds
//    limpios — timestamps normalizados (sin la hora del build) + orden de entradas estable. El gate
//    hermetic_build la PRUEBA (build `jar` ×2 offline → SHA256 idéntico). El diente vivo flipea
//    `isPreserveFileTimestamps` a true → los jars difieren → rojo.
tasks.withType<AbstractArchiveTask>().configureEach {{
    isPreserveFileTimestamps = false
    isReproducibleFileOrder = true
}}
'''


def _ts_package_json(pkg: str) -> str:
    return ('{\n'
            f'  "name": "{pkg}-client",\n'
            '  "private": true,\n'
            '  "type": "module",\n'
            '  "devDependencies": {\n'
            f'    "typescript": "{TS_VERSION}",\n'
            f'    "openapi-typescript": "{OPENAPI_TS_VERSION}",\n'
            f'    "eslint": "{ESLINT_VERSION}",\n'
            f'    "typescript-eslint": "{TS_ESLINT_VERSION}",\n'
            f'    "@total-typescript/ts-reset": "{TS_RESET_VERSION}",\n'
            f'    "axe-core": "{AXE_VERSION}",\n'
            f'    "jsdom": "{JSDOM_VERSION}",\n'
            f'    "esbuild": "{ESBUILD_VERSION}",\n'
            f'    "playwright-core": "{PLAYWRIGHT_VERSION}"\n'
            '  }\n'
            '}\n')
