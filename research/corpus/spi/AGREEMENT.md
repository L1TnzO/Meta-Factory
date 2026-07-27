# SPI — acuerdo entre la pasada 1 y la segunda pasada independiente

## Fiabilidad global (sólo estratos VERIFICACION — muestras aleatorias pre-registradas)

- n = 191 registros con doble veredicto ciego
- acuerdo bruto COLAPSADO = 96.9% · **Cohen κ = 0.895** (casi perfecto, Landis & Koch 1977)
- acuerdo bruto EXACTO = 80.1% · Cohen κ = 0.745 (sustancial)

El κ colapsado es el que responde «¿el paper entra al estudio?»; el exacto también exige coincidir en el subtipo de exclusión, distinción que no cambia el corpus.

> Generado por `harvest/spi_agreement.py` desde los veredictos committeados. **Dos revisores-MODELO independientes, no dos humanos** (§9.1): la adjudicación humana se aplica sólo sobre los conflictos listados en `CONFLICTOS.csv`.

## MUESTRA-10PCT (VERIFICACION) — n=110/110

- filas comparables: 100 (se excluyen 9 donde la pasada 1 se ABSTUVO: no son verificables y el segundo lector no puede abstenerse aquí, así que contarlas sería penalizar el coeficiente con un artefacto del diseño); se excluyen 1 por BRECHA DE CEGUERA auto-reportada por el segundo lector (no es desacuerdo ni acuerdo: la medición de fiabilidad nunca ocurrió en ese par)
  - `W7154711690`: reader self-disclosed seeing pass-1 M/T/E/decision via a stray grep on screening_full.csv while checking venue metadata (wave 2, chunk q04, 2026-07-26); the recorded verdict is still the reader's own PDF-grounded read, but the pair is not an independent measurement
- acuerdo EXACTO: 78/100 = 78.0%
- acuerdo COLAPSADO (IN/OUT/HUMANO): 96/100 = 96.0%

| pasada 1 \ SPI | IN | OUT | HUMANO |
| --- | ---: | ---: | ---: |
| **IN** | 31 | 2 | 1 |
| **OUT** | 0 | 65 | 1 |
| **HUMANO** | 0 | 0 | 0 |

## SNOWBALL-SAMPLE10 (VERIFICACION) — n=98/98

- filas comparables: 91 (se excluyen 7 donde la pasada 1 se ABSTUVO: no son verificables y el segundo lector no puede abstenerse aquí, así que contarlas sería penalizar el coeficiente con un artefacto del diseño)
- acuerdo EXACTO: 75/91 = 82.4%
- acuerdo COLAPSADO (IN/OUT/HUMANO): 89/91 = 97.8%

| pasada 1 \ SPI | IN | OUT | HUMANO |
| --- | ---: | ---: | ---: |
| **IN** | 0 | 1 | 0 |
| **OUT** | 0 | 89 | 1 |
| **HUMANO** | 0 | 0 | 0 |

## PREOUT-RESCATADOS (CONFIRMACION) — n=11/11

- filas comparables: 11 (se excluyen 0 donde la pasada 1 se ABSTUVO: no son verificables y el segundo lector no puede abstenerse aquí, así que contarlas sería penalizar el coeficiente con un artefacto del diseño)
- acuerdo EXACTO: 3/11 = 27.3%
- acuerdo COLAPSADO (IN/OUT/HUMANO): 3/11 = 27.3%
- (muestra DIRIGIDA, no aleatoria → no entra en κ)

| pasada 1 \ SPI | IN | OUT | HUMANO |
| --- | ---: | ---: | ---: |
| **IN** | 3 | 8 | 0 |
| **OUT** | 0 | 0 | 0 |
| **HUMANO** | 0 | 0 | 0 |

## GRIS (ADJUDICACION) — n=131/131

La pasada 1 se abstuvo en estas filas; la SPI decide con la evidencia efectivamente disponible en su input (mezcla medida abajo), no necesariamente con el PDF completo. No hay κ: no hay dos decisiones que comparar.

- evidencia efectivamente a la vista: full-text 15 · abstract 69 · title-only 47

- `GRIS`: 61
- `INCLUIR`: 20
- `EXCLUIR-CE2`: 16
- `EXCLUIR-CE1`: 11
- `CE-4p`: 9
- `EXCLUIR-CE5`: 7
- `EXCLUIR-RUBRICA`: 5
- `EXCLUIR-CE4`: 2
- **61 siguen GRIS con la evidencia disponible (no necesariamente el texto completo) → cola humana real.**

## SNOWBALL-GRIS (ADJUDICACION) — n=61/61

La pasada 1 se abstuvo en estas filas; la SPI decide con la evidencia efectivamente disponible en su input (mezcla medida abajo), no necesariamente con el PDF completo. No hay κ: no hay dos decisiones que comparar.

- evidencia efectivamente a la vista: abstract 28 · title-only 33

- `GRIS`: 23
- `INCLUIR`: 18
- `EXCLUIR-CE2`: 9
- `EXCLUIR-CE1`: 5
- `EXCLUIR-RUBRICA`: 3
- `CE3-SECUNDARIO`: 2
- `EXCLUIR-CE5`: 1
- **23 siguen GRIS con la evidencia disponible (no necesariamente el texto completo) → cola humana real.**

## RECONSIDERAR-EXT (CALIDAD) — n=33/33

- `CONFIRMA-RECONSIDERAR`: 18
- `DESCARTA-RECONSIDERAR`: 9
- `DEGRADAR`: 6

## RECONSIDERAR-DIG (CALIDAD) — n=83/83

- `CONFIRMA-RECONSIDERAR`: 53
- `DESCARTA-RECONSIDERAR`: 27
- `DEGRADAR`: 3

## DUPLICADOS (IDENTIDAD) — n=7/7

- `FUSIONAR`: 6
- `DISTINTOS`: 1

## Cola humana resultante

- **113 filas** en `CONFLICTOS.csv` (de 534 revisadas por la SPI): desacuerdos de membresía, GRIS que persisten con la evidencia disponible, degradaciones y fusiones. Todo lo demás quedó CONSOLIDADO por coincidencia de dos lectores independientes.
