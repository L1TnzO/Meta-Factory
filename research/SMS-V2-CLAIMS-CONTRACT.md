# CONTRATO — `claims.yml` deriva de la SPI APLICADA (precondición de la fase E)

> Escrito en sesión de DISEÑO (Opus, 2026-07-27). El diente (`harvest/verify_claims_spi.py`) se escribió
> ANTES que la derivación y vive FUERA del radio del slot que la implementará — mismo patrón que
> `verify_spi_apply.py`. Este documento es el contrato; la implementación es un slot delegado.

## 0. Por qué existe (una frase)

Hoy `claims.yml` deriva de la **pasada 1**: los denominadores del paper incluyen 8 estudios que la segunda
pasada degradó y excluyen los 31 que admitió. Escribir §4.7 antes de arreglar eso sería el sexto
sobreclaim de esta fase — y esta vez uno impreso.

## 1. La distinción que ordena todo (corolario §9.3, fijado 2026-07-27)

Admitir un estudio al **corpus** (nivel PRISMA, basta el criterio de inclusión) y admitirlo al **digest**
(hay texto completo que leer) son decisiones distintas. Por tanto hay **dos denominadores**, nunca
intercambiables:

- **`corpus_v2`** — estudios admitidos tras la SPI. Denominador del **flujo** (§4.4, tipo PRISMA).
- **`digest_v2`** — estudios efectivamente analizados a texto completo. Denominador de **TODO resultado**
  (§5 en adelante). Ningún hallazgo puede computarse sobre `corpus_v2`.

Un tercer conjunto, `flujo1`, describe lo que la pasada 1 hizo *tal como ocurrió*: es historia, no
evidencia. No se corrige nunca (§3.3: nada se re-escribe, todo se añade).

## 2. Álgebra canónica (definiciones NORMATIVAS — el diente recomputa exactamente esto)

Fuente única de la SPI: `corpus/spi/APPLIED.json` (una entrada por fila; el silencio es fallo).

```
degradadas  = { r.key : r.effect == "DEGRADED" }            # 8 claves (9 filas)
admitidas   = { r.key : r.effect == "ADD_INCLUIR" }         # 31 claves
excluidas   = { r.key : r.effect == "ADD_EXCLUIR" }         # 61 claves
fusion      = { p.from -> p.into  for p in merged_into }    # 6 pares
identidad(k) = fusion.get(k, k)                             # fusionar colapsa IDENTIDAD

digest_v2   = { identidad(k) : k ∈ claves(digest.jsonl),
                k ∉ degradadas, identidad(k) ∉ degradadas }
corpus_v2   = { identidad(k) : k ∈ claves(extraction.csv) ∪ admitidas,
                k ∉ degradadas, identidad(k) ∉ degradadas }
pendientes  = { k ∈ digest_eligible : identidad(k) ∉ digest_v2 }     # 13 hoy → 0 al cerrar B
```

**Decisión de diseño (la que no era obvia):** una fusión **colapsa identidad, no evidencia**. En el par
`W4400434708 → W4414360988` el `from` está digerido y el `into` no; la fila del digest **sobrevive bajo la
identidad del `into`**. Un merge nunca puede reducir el número de estudios *leídos*, sólo el número de
estudios *contados dos veces*.

**Filas ≠ estudios.** Los tres pares medidos hoy: DEGRADAR 9/8 · HUMAN_QUEUE 130/125 · CONFLICTOS 113/111.
Todo id que cuente **filas** debe terminar en `Filas`; sin sufijo, un id cuenta **claves únicas**.

**Cola humana: son dos poblaciones, no una.** `CONFLICTOS.csv` (desacuerdos registrados al cerrar la fase A)
y el efecto `HUMAN_QUEUE` (lo que la aplicación derivó, incl. los 7 re-enrutados por título) **no son el
mismo conjunto** — medido: 13 conflictos fuera del efecto, 27 del efecto fuera de conflictos. El paper
declara ambos con su pregunta propia, o no declara ninguno.

## 3. Esquema: `pasada` pasa a ser obligatorio en cada claim

Se añade un campo a los 140 claims. Vocabulario CERRADO:

| `pasada` | qué describe | puede usar | **no** puede usar |
| --- | --- | --- | --- |
| `flujo1` | el flujo tal como ocurrió en la pasada 1 (§4.4) | `sheet_full`, `sheet_snowball`, `extraction`, `digest` | `digest_v2`, `corpus_v2`, `extraction_v2`, `applied` |
| `spi` | la segunda pasada como objeto de estudio (§4.7: κ, acuerdo, efectos) | `spi`, `conflicts`, `applied`, las hojas de la pasada 1 | — |
| `post` | la base de evidencia final (§5+) | `digest_v2`, `corpus_v2`, `extraction_v2`, `applied` | `digest`, `extraction`, `sheet_full`, `sheet_snowball` |

El aislamiento es **estático y decidible** (barrido de nombres con frontera de palabra sobre la cadena
`derivacion`) — por eso es un diente y no una recomendación. Un claim `post` que además no mencione
ninguna vista `_v2` es RED: no es post-SPI, sólo lo dice.

## 4. Ids de carga (el diente los conoce por nombre y recomputa su valor)

El gate no lee el código del derivador: compara el valor **emitido** en `claims.tex` contra su propia
recomputación independiente desde `APPLIED.json` + corpus crudo. Que dos implementaciones distintas
coincidan es lo que hace verde significativo.

| id | `pasada` | qué mide exactamente |
| --- | --- | --- |
| `clPostDigest` | post | `len(digest_v2)` — **denominador de resultados** |
| `clPostCorpus` | post | `len(corpus_v2)` — denominador del flujo post-SPI |
| `clPostDegradados` | post | claves degradadas por la SPI (8) |
| `clPostFusiones` | post | pares fusionados (6) |
| `clPostAdmitidosSpi` | post | `ADD_INCLUIR` (31) |
| `clPostExcluidosSpi` | post | `ADD_EXCLUIR` (61) |
| `clPostBloqueadosSinTexto` | post | admitidos al corpus sin texto completo (18) — **amenaza declarada** |
| `clPostPendientesDigest` | post | elegibles aún no digeridos (13 hoy, 0 al cerrar B) |
| `clPostExclusionesSoloTitulo` | post | exclusiones decididas sólo por título (21) — **amenaza declarada** |
| `clFiaKappaColapsado` | spi | κ de Cohen colapsado a membresía |
| `clFiaKappaExacto` | spi | κ exigiendo coincidir en el subtipo |
| `clFiaColaHumanaFilas` | spi | filas con efecto `HUMAN_QUEUE` (130) |
| `clFiaColaHumana` | spi | claves únicas con ese efecto (125) |
| `clFiaConflictosFilas` | spi | filas de `CONFLICTOS.csv` (113) |

Los números entre paréntesis son el estado **medido hoy**, no objetivos a escribir: el derivador los
produce, el gate los recomputa, nadie los teclea.

## 5. Prohibiciones (cada una es un invariante, no un consejo)

1. **No se borra nada del corpus.** Las 8 claves degradadas siguen en `digest.jsonl`; se restan por
   derivación. Borrarlas es RED tanto como olvidarse de restarlas.
2. **κ no se copia de la prosa.** `AGREEMENT.md` es una **vista** (misma clase que `claims.tex`), no una
   fuente. κ se deriva de los verdicts crudos con los helpers que YA existen en el namespace
   (`collapse`, `cohen_kappa`). Una derivación de κ con un literal numérico dentro es RED.
3. **Ningún claim `post` toca el corpus crudo** (§3, aislamiento estático).
4. **Las amenazas declaradas se citan o no existen**: `\clPostExclusionesSoloTitulo`,
   `\clPostBloqueadosSinTexto` y `\clPostDegradados` deben aparecer en `sms-v2.tex`; y
   `\clPostPendientesDigest` es obligatorio **mientras su valor sea > 0**. Un residuo que no se imprime es
   un residuo escondido.

## 6. El diente — `harvest/verify_claims_spi.py` (ya escrito, fuera del radio del slot)

| # | Invariante | RED cuando |
| --- | --- | --- |
| I-1 | esquema | algún claim sin `pasada` o con valor fuera del vocabulario |
| I-2 | aislamiento por pasada | un `post` toca corpus crudo · un `flujo1` toca vistas `_v2` · un `post` sin ninguna vista `_v2` |
| I-3 | la SPI está aplicada | falta `APPLIED.json` · `ADD_EXCLUIR` ∩ digest ≠ ∅ · bloqueados ∩ digest ≠ ∅ |
| I-4 | nada se borra | alguna clave degradada desapareció de `digest.jsonl` |
| I-5 | integridad de la fusión y de los conjuntos | una fusión apunta fuera del corpus · una clave es a la vez degradada y extremo de fusión (colapso indefinido) · elegible ∩ bloqueado ≠ ∅ · elegible/bloqueado que la SPI no admitió |
| I-6 | valores | falta un id de carga, o su valor emitido ≠ recomputación independiente |
| I-7 | residuo publicado | una amenaza declarada no se cita en el `.tex` (o `pendientes>0` sin citar) |
| I-8 | κ derivado | derivación de κ con literal numérico, o κ emitido ≠ el de `AGREEMENT.md` (±0,001) |

Los ocho se probaron **de los dos lados** antes de commitear (verde con un ledger sintético correcto; rojo
con un sabotaje por invariante). La primera versión de I-5 decía «toda clave no degradada sobrevive en
`digest_v2`» y era **tautológica** —`digest_v2` se construye justamente así, no podía ponerse roja nunca—;
se reescribió sobre la calidad del DATO que sostiene el colapso, que sí es falsable. Un invariante que no
puede fallar es decoración, y la decoración en un gate es peor que nada: da verde gratis.

**Estado esperado HOY: ROJO por I-1/I-6** (140 claims sin `pasada`, 14 ids de carga inexistentes). El diente
se commitea rojo **a propósito**: mide el trabajo pendiente en vez de esconderlo. Verde = el slot terminó.

## 7. Radio del slot (blast radius) y veredicto

**Puede escribir**: `sms-v2/claims.yml` · `sms-v2/claims.tex` (regenerado, nunca a mano) ·
`harvest/verify_sms_claims.py` (sólo `build_namespace`: añadir `applied`, `digest_v2`, `corpus_v2`,
`extraction_v2`) · `sms-v2/sms-v2.tex` (sólo §4.7 + amenazas: **macros**, jamás cifras).

**No puede tocar**: `corpus/**` (el corpus es dato, no salida) · `harvest/verify_claims_spi.py` (el diente) ·
`harvest/spi_apply.py` · `corpus/spi/APPLIED.json`.

**Veredicto** = `verify_claims_spi.py` verde **y** `verify_sms_claims.py --emit` verde (los 5 dientes
previos siguen vigentes: sin dígitos desnudos en regiones estrictas, citas existentes en el `.bib`, etc.).

## 8. Lo que este slot NO hace

- **No escribe la prosa de §4.7** — eso es E, después, y con las macros ya disponibles.
- **No mueve los 13 elegibles** — eso es B (chunks `e72+`/`d72+`). El contrato está diseñado para que B
  mueva los números **solo**: cuando los 13 entren al digest, `clPostDigest` sube y
  `clPostPendientesDigest` baja a 0 sin tocar una línea de `claims.yml`. Ése es el criterio de que el
  contrato está bien hecho.
