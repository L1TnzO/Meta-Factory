<!-- meta:doc sha=0541732927d4303c86f6b668905cec30d46ad75d updated=2026-07-10T23:29Z -->
# H1 — Ingesta + Almacén · **CERRADO** (2026-07-05)

> Hito 1 de `../design/04-implementation-plan.md §3`. Entregable: parser, chunker 3s1, anclas,
> esquema SQL. Gate de salida: re-derivar los chunks de Inter2US **byte-idénticos** al CSV del paper.

## Contrato
- `parse_transcript(text) -> list[Turn]` — líneas `[H:MM:SS] spk_N: texto`; estricto (línea no
  conforme ⇒ `ValueError`); texto stripped; **turnos consecutivos del mismo hablante fusionados**.
- `chunk_turns(turns, 3, 1) -> list[Chunk]` — ventana deslizante con **cola parcial** (N turnos ⇒
  N chunks); render `Spk {n}: {texto}` unido por `\n`.
- `chunks_to_csv(source, chunks) -> str` — header `source,chunk_id,text,turns_per_chunk,turn_stride`,
  LF, quoting csv estándar.
- `chunk_anchor(transcript_sha, window_start_turn)` — ancla content-addressed (design/02 §1.3).
- `store/schema.sql` — DDL de design/02 §3 (7 tablas). Sin diente propio en H1: su verificación
  real (dao + PG vivo) llega en H3 — diferido declarado, no olvidado.

## Descubrimiento que fijó el contrato (derivado, no asumido)
El esquema golden NO es "ventanas de 3 sobre turnos crudos": exige (a) fusionar turnos
consecutivos del mismo hablante (133 crudos → 132 fusionados), (b) strip por turno, (c) cola
parcial (los 2 últimos chunks tienen 2 y 1 turnos). Reproducido primero como spike de lectura
sobre el CSV real; recién con paridad byte-exacta demostrada se escribió el módulo.

## Evidencia (gate verde, 2026-07-05)
```
$ python3 -m pytest tests/ -v            → 6 passed  (test_chunk_parity.py)
    · test_inter2us_chunk_parity_byte_identical   ← EL gate: CSV producido == golden, byte a byte
    · count/shape (132 chunks · 3s1 · cola parcial) · fusión de hablantes · anclas estables ·
      línea no conforme ⇒ ValueError
$ python3 -m reqcouncil ingest datasets/inter2us/data/public_interview/int1.txt --source int1 \
    | diff - datasets/inter2us/data/public_interview/chunks_turns_3s1.csv   → exit 0 (vacío)
```

## Hallazgo colateral — conteos golden corregidos
`wc -l` sobre CSV con celdas multilínea había inflado los números citados en diseño/informe:
| Claim previo | Medido (csv.reader) |
|---|---|
| 394 chunks | **132** (394 = líneas físicas) |
| 38 historias | **37** |
| 541 pares anotados | **180** entrevista (74⁺/106⁻) + **580** system-desc (302⁺/278⁻) = **760** para E0 |
Propagado a `design/01..04`, `informe/00·02·03·04·FICHA`, `datasets/README.md`.

## Residual honesto
- `schema.sql` no ejecutado contra PG real todavía (H3).
- Formatos de entrada (b) líneas etiquetadas simples y (c) CSV pre-chunkeado (design/02 §1) no
  implementados aún — solo el formato (a) del corpus primario; se agregan cuando un corpus los
  necesite (E2 traerá texto desde PDF).
- El flag TF-IDF del chunk (feature para Gap Hunter) diferido a H3 con el resto del runtime council.
