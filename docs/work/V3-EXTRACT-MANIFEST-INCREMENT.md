<!-- meta:doc sha=f6825cd4c7df92fba5dadd3d2974a6092e758823 updated=2026-08-03T23:17Z -->
# Increment V3-EXTRACT-MANIFEST

> **Governance doc.** Status: **CLOSED** (2026-08-03T23:17Z) (created 2026-08-03T23:05Z). Close it with `v3 increment close`
> (gated: clean tree + active station green). Every code change lives here (ADR-010).
>
> PASO 1 de `work/V3-EXTRACT-DIRECTION-INCREMENT.md` · nodo `N-0133`.

## Goal

Que **lo que viaja** al extraer la plataforma sea un **DATO verificable** y no una lista en prosa:
`v3/extract_manifest.py` como fuente única, y `extract_package` como su diente.

## Lo que la medición corrigió del doc de dirección

El doc fijó un «paquete mínimo» de **ocho** entradas, medido como *«13 gates verdes · 0 rojos · 4 N/A
en un repo ajeno»*. **Ese verde era el bug recurrente del proyecto con sombrero nuevo**: se veía verde
porque nadie preguntó **qué quedó afuera de la cuenta**. Barriendo los literales de string de los 152
módulos de plataforma aparecieron **24 paths existentes** que las ocho entradas no cubrían. Entre ellos:

| faltaba | por qué importa |
| --- | --- |
| **`.claude/`** | **LA COLUMNA** — hooks, agents, skills, `settings.json`. Sin ella el harness no tiene dientes: blast-radius, verdict-required y la ley del slot viven ahí. El repo extraído habría tenido **cero ley de delegación** |
| **`.github/workflows/`** | **EL SEGUNDO VERIFICADOR** (ADR-005). Sin él, el único verificador del repo extraído es la máquina que escribió el código, y **nada lo habría reportado**: la ley de dos verificadores simplemente dejaría de existir |
| `stations/` | la línea meta m00..m08 — lo que **construye** una factory. Sin ella queda algo que verifica pero no fabrica |
| `template/` · `specs/` | el template de factory y las specs que `generality` resuelve |
| `docs/reference/` | DATO de runtime: `primitives.yml` lo carga `v3/spec/primitives.py`, `dep-allowlist.yml` lo lee `security`, `parity.yml` lo lee `generality` |

**Por qué los otros 29 gates no lo reportaron**: nunca registraron. La suite **se negó** a registrarlos
(la ley de INC-4), y **un gate que no corre no puede votar sobre lo que falta**. El ensayo no midió
«el paquete alcanza»; midió «los gates que el paquete permitía registrar están verdes».

## La segunda categoría (por qué no alcanza una sola lista)

Un path que un módulo nombra no es automáticamente un path que haya que **copiar**: algunos son el
**ESTADO** propio de este repo (su plan tree, sus proofs, sus work-docs) y el destino cría el suyo
desde el turno uno. Con una sola lista, «no está en el manifiesto» significaría a la vez *«nace
fresco»* y *«nos lo olvidamos»* — y ésa es justo la ambigüedad que el PASO 3 necesita que no exista.
Por eso una referencia cae en exactamente una de tres: `PACKAGE` (viaja) · `BORN_FRESH` (decisión
declarada de NO copiar) · **agujero de empaque** (rojo).

`ancestor` es una cuarta respuesta, y existe para que **el manifiesto nunca tenga que mentir**: un
módulo que nombra `docs/` nombra un árbol del que `docs/spec/` viaja y `docs/work/` no. Contestar eso
con una fila `docs/` afirmaría algo falso en las dos direcciones; contestarlo por descendencia dice
exactamente lo que es cierto.

## Contrato del slot (`extract-package-gate`)

`v3/verify/checks/extract_package.py`, mismo molde que el resto de `v3/verify/checks/` (`Verdict` de
`v3.kernel.report`, `main(argv)`, `raise SystemExit(main(sys.argv[1:]))`, docstring con las dos
invocaciones).

**Lado VERDE** — tres leyes, y ninguna puede quedar en silencio:
1. **filas sanas**: cada fila de `PACKAGE` existe en el árbol Y está **trackeada por git**; cada fila
   de `PACKAGE` y de `BORN_FRESH` tiene **razón escrita** (≥40 chars, la misma vara que `codegen_freeze`).
2. **sin solapamiento contradictorio**: si `classify()` de una fila devuelve algo distinto de la lista
   que la declara, es rojo (el desempate por prefijo-más-largo tiene que coincidir con la intención).
3. **suficiencia** (el diente real): barrer con `ast` los literales de string de **todo `.py` de
   plataforma (`v3/`, `seed/`, `tools/`)**; para cada literal que parezca un path repo-relativo Y
   **exista** en el árbol, `classify()` no puede devolver `None`. Un literal que no existe en el árbol
   no es agujero (no se puede empacar lo que no está).

**Lado ROJO** (`V3_EXTRACT_PACKAGE_SABOTAGE=1`, también exit 0) — ≥4 escenarios sintéticos sobre
funciones **puras**, sin tocar el árbol real:
(1) un módulo de plataforma referencia un path existente fuera del manifiesto → debe marcarse;
(2) una fila de `PACKAGE` apunta a algo que no existe → debe marcarse;
(3) una fila sin razón escrita → debe marcarse;
(4) un manifiesto sano → **no** debe marcarse (si no, bloquearía todo manifiesto legítimo).

**Registro**: en `v3/verify/suite.py`, `_register_economy` (no tiene original en v2 → queda FUERA del
censo de `gate_census`), con `witness=Witness("sabotage_env", "V3_EXTRACT_PACKAGE_SABOTAGE")`.

**Restricciones**: `quality` verde (techos de tamaño de archivo/función) · cero deps nuevas · sin
nombrar dominio/tecnología (ADR-012) · el barrido no puede importar los módulos, sólo parsearlos.

## Phases
| Phase | Content | Status |
| --- | --- | --- |
| 1 | `v3/extract_manifest.py` — PACKAGE (15) + BORN_FRESH (10) + `classify` | done |
| 2 | slot `extract-package-gate` → `extract_package.py` + registro | done |
| 3 | aceptación: los dos lados + `quality` + registro + footprint del slot | done |

## El slot encontró un error MÍO, y ésa es la noticia

El slot volvió **ROJO**, y el rojo no era del generador: el gate recién escrito encontró un defecto
**pre-existente en `v3/extract_manifest.py`** — la fila `BORN_FRESH` de `docs/STATE.md` tenía una
razón de **34 chars**, bajo la vara de 40 que el propio contrato manda. El archivo estaba **fuera del
radio de explosión** del slot, así que el generador **no pudo arreglarlo**: lo reportó y paró.

Eso es exactamente para lo que existe el radio. Un generador con permiso de escritura amplio habría
«arreglado» el manifiesto del orquestador para ponerse verde, y el rojo —que era **correcto**— habría
desaparecido sin que nadie lo viera. La corrección la hizo el dueño del archivo.

## Evidencia

| prueba | resultado |
| --- | --- |
| `python3 -m v3.verify.checks.extract_package` | **PASS** — 15 PACKAGE + 10 BORN_FRESH sanas, sin contradicción de solapamiento, **83** paths referenciados **todos cubiertos** |
| `V3_EXTRACT_PACKAGE_SABOTAGE=1 …` | **PASS**, **10** escenarios sintéticos (razón · existencia · solapamiento · suficiencia, lado agujero y lado sano) |
| `python3 -m v3.verify.checks.quality` | **PASS** — 147 archivos limpios a 2000/80/200 |
| registro en la suite | **43 gates** (era 42) |
| footprint del slot (`delegation.footprint.sweep`) | **GREEN** — 6 observados, **0 fuera** del radio, 4 dirty de baseline |
| experimento negativo: sacar `.claude/` de `PACKAGE` | **ROJO** (10 problemas: solapamiento + suficiencia sobre `.claude/agents`, `.claude/hooks`, `.claude/projects`) |

## Close criterion (demonstrable, not narrated)
1. ✅ `python3 -m v3.verify.checks.extract_package` → PASS, **0 agujeros** sobre los módulos de plataforma.
2. ✅ `V3_EXTRACT_PACKAGE_SABOTAGE=1 …` → PASS con **10** escenarios (el lado rojo muerde).
3. ✅ El gate **registrado** en la suite (43) y `quality` verde.
4. ✅ Experimento negativo sobre el manifiesto real: sacar `.claude/` de `PACKAGE` → **rojo**.
