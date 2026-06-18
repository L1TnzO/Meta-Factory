# Toolchain pineado (PLAN, ADR-012) — Full-Stack Kotlin Factory

> DATA de la fábrica (no del sustrato `src/metafactory/`). El codegen estampa esto en cada producto.
> Probado por bloqueo el 2026-06-18 en este entorno (FSK-S0-SCAFFOLD-CONTRACT, Fase 1): ambos lados
> (green compila / red falla). Re-derivable: versiones pineadas + checksum del wrapper.

| pieza | versión pineada | corre sobre | evidencia (Fase 1) |
| --- | --- | --- | --- |
| Gradle (wrapper) | **9.5.1** (sha256 `bafc141b…7b031f`) | JDK 21 (`JAVA_HOME=/usr/lib/jvm/java-21-openjdk`) | `./gradlew run` → `FSK_SMOKE_OK sum=6` |
| Kotlin (Gradle plugin) | **2.4.0** | jvmToolchain(21) | idem (compila + ejecuta) |
| JDK target | **21** (LTS; `javac` presente) | — | toolchain de Gradle |
| TypeScript | **5.7.3** (`--strict`, `noImplicitAny`) | node v22 | green exit 0 · type-error exit 2 |

## Wrapper vendorizado
`gradle/` contiene el wrapper Gradle 9.5.1 **probado** (gradlew + gradle-wrapper.jar + properties con
`distributionSha256Sum`). El codegen lo copia VERBATIM al árbol del producto → el producto trae su propio
build pineado (el análogo del `gradlew`/`npm ci` de las otras fábricas). Primer `./gradlew` baja la distro
pineada (red, como `npm install` de Full-Stack-TS); `ci --rederive` reusa la caché `~/.gradle`.

## Por qué JDK 21 (no 25)
`java` resuelve a JDK 25 pero `javac` es 21 y `JAVA_HOME` apunta a `java-21-openjdk` (LTS, estable). El
build fija el toolchain a 21 explícitamente — el determinismo del build exige pinear la versión, no heredar
la del PATH (riesgo anotado en el incremento §6).
