# CONTRACT · `harvest/spi_apply.py` — apply the second independent pass (SPI) to the corpus

You are implementing ONE derivation. It turns the 534 committed SPI verdicts into the **post-SPI corpus
view**. It is a PURE DERIVATION from committed data: it must never mutate `corpus/screening/*`,
`corpus/extraction/*` or `corpus/digestion/*`, never delete a row anywhere, and never call the network.

Everything below is judged by `harvest/verify_spi_apply.py`, which was written BEFORE you and which you may
NOT edit (it is outside your blast radius). Read it — it is the spec. Do not reimplement its rules by
guessing; import `closure_law` for the vocabulary exactly as the gate does.

## 1. The four rules you are encoding (methodological — do not "improve" them)

| Situation | Queue kind | Effect you must emit | Why |
| --- | --- | --- | --- |
| pass 1 ABSTAINED (`GRIS`, `CE-4p`) | `ADJUDICACION` | `ADD_INCLUIR` / `ADD_EXCLUIR` / `HUMAN_QUEUE` | the SPI is the only decision that exists — nothing is being overruled |
| the two passes DISAGREE | `VERIFICACION`, `CONFIRMACION` | `HUMAN_QUEUE` (never a flip) | an agent may not *be* the adjudicating human (protocol §3.1) |
| the two passes AGREE | `VERIFICACION`, `CONFIRMACION` | `NO_CHANGE` | consolidated by two independent readers |
| `veredicto == DEGRADAR` | `CALIDAD` | `DEGRADED` | provenance failure; recorded, **never deleted** (§3.3) |
| `veredicto == FUSIONAR` | `IDENTIDAD` | `MERGED` | two rows are one study; both keys kept in provenance |
| `veredicto` = `CONFIRMA-`/`DESCARTA-RECONSIDERAR`, `DISTINTOS` | `CALIDAD`, `IDENTIDAD` | `NO_CHANGE` | quality/identity note, no membership move |
| SPI re-emitted `GRIS`/`CE-4p` on an adjudication row | `ADJUDICACION` | `HUMAN_QUEUE` | still undecided with more evidence in hand |

A row whose SPI decision is in `closure_law.HUMAN_LABELS` is **always** `HUMAN_QUEUE`, never an `ADD_*`.

**AMENDMENT 2026-07-27 (a title is not an evidence anchor).** Measuring the first implementation showed 7
studies being ADMITTED to the mapping on their title alone (all from `SNOWBALL-GRIS`, the queue with zero
full text) and 21 excluded the same way. `closure_law.EVIDENCE_ANCHORS` requires a decision to be anchored
in the study's own text, so:

- an `ADD_INCLUIR` whose `evidence_grade` is `title-only` is **illegal** → emit `HUMAN_QUEUE` instead
  (reason must say so). An inclusion nobody could anchor is not a decision, it is a guess.
- an `ADD_EXCLUIR` whose grade is `title-only` **stays** (it only ever shrinks the corpus, the conservative
  direction) but must be counted: add `counts.title_only_exclusions` = that number (expect 21, derive it).
  It becomes a declared threat to validity in the paper, not a silent one.

## 2. Evidence grade — MEASURED, never assumed

For every one of the 534 rows, derive what the second reader actually had in front of it, from that row's
own `q*.input.jsonl` record:

- `full-text`  — the input's `pdf` field is non-empty **and** that path exists on disk;
- `title-only` — no `abstract` text at all;
- `abstract`   — otherwise.

This exists because the summary currently claims the adjudication queues were decided "con el PDF a la
vista" while only 15 of 192 rows had one. A row decided from a title alone may **never** become
`digest_eligible`.

## 3. Output: `corpus/spi/APPLIED.json` (exact schema — the gate reads these names)

```json
{
  "generated_by": "harvest/spi_apply.py",
  "generated_at": "<UTC ISO8601 to the minute>",
  "evidence_grade": {"<key>": "full-text|abstract|title-only"},
  "membership_delta": [
    {"key": "...", "queue": "...", "kind": "...", "spi": "<decision or veredicto>",
     "effect": "ADD_INCLUIR|ADD_EXCLUIR|HUMAN_QUEUE|DEGRADED|MERGED|NO_CHANGE",
     "evidence_grade": "...", "reason": "<one line, why this effect follows from the rule table>"}
  ],
  "merged_into": [{"from": "<key>", "into": "<canonical key>"}],
  "digest_eligible": ["<key>"],
  "digest_blocked_no_fulltext": ["<key>"],
  "counts": {"rows": 534, "by_effect": {...}, "by_grade": {...},
             "by_queue": {"<queue>": {"<decision-or-veredicto>": <n>}}}
}
```

- `evidence_grade` covers **every** row; `membership_delta` has **exactly one** entry per row (all 534,
  including `NO_CHANGE`) — silence about a row is a failure.
- `digest_eligible` = `ADD_INCLUIR` ∩ (`corpus/pdf/<key>.pdf` exists) ∩ (grade != `title-only`).
  Expect **14** today. `digest_blocked_no_fulltext` = the rest of `ADD_INCLUIR` (expect 24). Do not
  hardcode either number — derive them.
- `merged_into.into` comes from the DUPLICADOS verdict's `canonica` field.

## 4. CLI

```
python3 harvest/spi_apply.py            # derive + print a short human summary to stdout, WRITE NOTHING
python3 harvest/spi_apply.py --write    # additionally write corpus/spi/APPLIED.json
```

## 5. `spi_agreement.py` — publish the evidence mix

Extend it (do not restructure it) so `--write` makes `AGREEMENT.md` state, in **each ADJUDICACION queue's
own `## <QUEUE>` section**, the measured evidence mix, e.g. a line of the form:

`- evidencia efectivamente a la vista: full-text 8 · abstract 120 · title-only 3`

and so the section no longer asserts the decision was taken "con el PDF a la vista" / "con el texto completo
a la vista" unless that queue is 100% `full-text`. Replace those phrases with an accurate one that names the
mix. **Do not touch the κ/agreement numbers** — they are correct and already published.

Import the grade derivation from `spi_apply.py` (single source); do not copy it.

## 6. Tests — `harvest/test_spi_apply.py`

Follow `harvest/test_closure_tools.py` conventions: offline, no network, no dependence on cwd, and exercise
the REAL gate (`verify_spi_apply.main`) against synthetic fixtures rather than reimplementing its rules.
Required cases, each on a tiny synthetic corpus in `tmp_path`:

1. a well-formed application passes the gate;
2. a `VERIFICACION` row given `ADD_INCLUIR` → gate RED (the §3.1 tooth actually bites);
3. a row missing from `membership_delta` → gate RED (coverage);
4. a `title-only` row listed in `digest_eligible` → gate RED;
5. an `evidence_grade` that disagrees with the input record → gate RED;
6. a DEGRADAR key erased from the corpus files → gate RED (§3.3).

## 7. Definition of done

- `python3 harvest/spi_apply.py --write` writes `corpus/spi/APPLIED.json`;
- `python3 harvest/spi_agreement.py --write` regenerates `AGREEMENT.md` with the evidence mix;
- `python3 harvest/verify_spi_apply.py` exits 0;
- `python3 -m pytest -q harvest/` is green **including the 145 pre-existing tests** (you may not delete or
  weaken an existing test to go green — if an old test genuinely encodes the old overclaim, say so in the
  verdict's `notes` and leave it failing rather than editing it away).
