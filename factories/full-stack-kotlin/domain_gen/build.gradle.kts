// domain_gen — módulo Kotlin AUTOCONTENIDO (decoupleado de build/product) que ejercita la lógica
// de dominio GENERADA por el LLM (Summary.kt) bajo un contract test. Mismas versiones que el
// producto (Kotlin 2.4.0 / gradle 9.5.1 / JDK 21) → cache de ~/.gradle caliente → ci --rederive
// sin red. application/run corre el main() del contract (idiom JavaExec, igual que `roundtrip` s1).
plugins {
    kotlin("jvm") version "2.4.0"
    application
}
repositories { mavenCentral() }
// -Werror (dureza, DES-10): la lógica LLM-generada compila bajo la MISMA barra que el producto.
kotlin {
    jvmToolchain(21)
    compilerOptions { allWarningsAsErrors = true }
}
application { mainClass.set("domain.SummaryContractKt") }
