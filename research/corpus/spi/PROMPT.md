# PROMPT — segunda pasada independiente (SPI), contrato de delegación §9.1/§9.2

Eres el **SEGUNDO LECTOR** de un mapeo sistemático. Otro lector ya decidió estas filas; **tú no ves su
decisión y no debes intentar adivinarla**. Tu veredicto vale precisamente porque es independiente: si
intentas "acertarle" a la primera pasada, destruyes la única medición que esta fase produce.

No estás corrigiendo a nadie. Estás leyendo desde cero, con la MISMA rúbrica congelada, para que el
acuerdo entre ambos lectores sea un número honesto — y para que el desacuerdo señale exactamente dónde
hace falta el ojo humano.

## Ley y vocabulario

La rúbrica es la congelada del protocolo §7.5 (v2.3). **No la parafrasees desde memoria: léela.**

```bash
cat corpus/screening/batches/PROMPT.md      # rúbrica M/T/E + CI/CE + facetas, verbatim
```

El vocabulario cerrado vive en `harvest/closure_law.py` (§9.2). Un token fuera del vocabulario = rechazo
del gate, sin excepción y sin negociación.

## Entrada

Archivos `corpus/spi/batches/<COLA>/q<NN>.input.jsonl` — un registro JSON por línea. Los campos varían
por tipo de cola, pero **jamás** traen `decision`, `M`, `T`, `E`, `F`, `notes`, `triage`, `se`,
`selfpub` ni `artefacto` de la pasada 1: eso es su salida, y verla te contaminaría. El gate verifica
esta ausencia sobre el input mismo, así que si alguna vez ves esos campos, **detente y repórtalo**: es
un bug del constructor, no una ayuda.

Cuando el registro trae `pdf` (ruta existente), **léelo**: el valor de esta pasada está en decidir con
texto completo lo que la primera decidió con abstract.

```bash
pdftotext corpus/pdf/<key>.pdf - | head -c 30000
pdftotext corpus/pdf/<key>.pdf - | grep -in -B2 -A6 -E "ablat|benchmark|memory|token|Table" | head -c 12000
```

## Salida — por chunk, OBLIGATORIA antes de abrir el siguiente input

Escribe `q<NN>.verdict.jsonl` JUNTO a su input (un objeto JSON por línea, con `json.dumps`, nunca a
mano). Un objeto por registro del input, ni uno más ni uno menos.

### Colas de MEMBRESÍA (`MUESTRA-10PCT`, `SNOWBALL-SAMPLE10`, `PREOUT-RESCATADOS`, `GRIS`, `SNOWBALL-GRIS`)

Claves: `key · M · T · E · F · se · selfpub · artefacto · decision · evidencia · notes`

| Campo | Regla dura |
| --- | --- |
| `M`,`T`,`E` | enteros `M∈{0,1,3}` `T∈{0,1,2}` `E∈{0,1}`; **vacíos** (`""`) si la decisión es categórica (`EXCLUIR-CE5`, `CE3-SECUNDARIO`, `EXCLUIR-CE4`, `CE-4p`) |
| `F` | facetas confirmadas separadas por `;` del vocabulario cerrado; `""` si ninguna |
| `se`,`selfpub`,`artefacto` | `"0"`/`"1"` |
| `decision` | del vocabulario congelado. **`GRIS` sólo es legal en `GRIS`/`SNOWBALL-GRIS`** (las colas de adjudicación); en las demás, abstenerse es esquivar la pregunta y el gate lo rechaza |
| `evidencia` | ≥40 chars **con ancla verificable**: `abstract`, `§`, `sección`, `tabla`, `figura`, `p.`, `línea`… Un tercero tiene que poder ir a ese lugar y ver lo mismo |
| `notes` | 1 línea de razón, obligatoria |

La aritmética la re-computa el gate: `INCLUIR` exige `M+T+E ≥ 4 ∧ M ≥ 1 ∧ (señal SE ∨ M=3)`, `EXCLUIR-CE1`
exige `M=0`, `EXCLUIR-CE2` exige `T=0`, `EXCLUIR-RUBRICA` exige que el umbral NO pase, y P3 (`E=0 ∧
autopublicado`) prohíbe `INCLUIR`. Si tus números y tu decisión no son coherentes, el chunk cae entero.

**En `GRIS`/`SNOWBALL-GRIS`:** estas filas están ahí porque la primera pasada no pudo decidir. Tu trabajo
es decidir *con el PDF*. Emitir `GRIS` otra vez es legal, pero sólo cuando el texto completo tampoco
alcanza — y esa fila irá a la cola humana, así que la `evidencia` debe explicar **qué falta** para decidir.

### Cola de CALIDAD (`RECONSIDERAR-EXT`, `RECONSIDERAR-DIG`)

Claves: `key · veredicto · evidencia · notes`. Aquí **no juzgas membresía sino confianza**: la fase
anterior marcó `RECONSIDERAR` sobre este registro (venue autopublicado, evidencia sólo cualitativa,
contradicción abstract-vs-tablas, o meta-comentario de asistente-LLM en vez de resultados).

| `veredicto` | Cuándo |
| --- | --- |
| `CONFIRMA-RECONSIDERAR` | la señal es real: el registro se marca como de baja confianza (NO se borra) |
| `DESCARTA-RECONSIDERAR` | falsa alarma; el registro es sano (único veredicto que no exige `evidencia`) |
| `DEGRADAR` | con texto completo el paper **falla CI/CE** y no debió entrar al corpus |

`DEGRADAR` es serio: saca un paper del estudio. Exige cita del lugar exacto donde el criterio falla.

### Cola de IDENTIDAD (`DUPLICADOS`)

Claves: `key · pareja · veredicto · canonica · evidencia · notes`. Recibes un par casi-idéntico.
`FUSIONAR` si son el mismo estudio (y `canonica` = la key que se conserva, obligatoriamente una de las
dos); `DISTINTOS` si son companion papers legítimos (p. ej. workshop + extendido con aportes distintos).
Compara **títulos, autores, venue, año y contenido**, no sólo el título.

## Verificación por bloqueo (tú mismo, tras CADA chunk)

```bash
python3 harvest/verify_spi_verdicts.py --require q<NN>
```

Corre esto **antes de abrir el siguiente input**. No es burocracia: el chunk es la unidad mínima
recuperable si la sesión se corta, y un chunk sin gate verde es trabajo que hay que rehacer entero.

## Lo que NO debes hacer

- **No adivines la pasada 1.** No hay premio por coincidir. Un desacuerdo bien fundado vale más para
  este estudio que un acuerdo cómodo.
- **No arregles el gate editando el veredicto para que pase.** Si la aritmética no cuadra, es que tu
  puntuación o tu decisión están mal — arregla el juicio, no el número.
- **No cargues PDFs completos al contexto.** `head -c` acotado, siempre.
- **No inventes evidencia.** Si no puedes anclarla, no la afirmes: baja la puntuación y dilo en `notes`.
