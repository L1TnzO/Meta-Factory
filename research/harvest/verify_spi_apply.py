#!/usr/bin/env python3
"""Deterministic gate for the APPLICATION of the second independent pass (SPI) to the corpus — §9.2.

Trust-chain: this gate is written by the ORCHESTRATOR, never by the slot it judges. It re-derives every
number from the COMMITTED verdicts and inputs and compares them against `corpus/spi/APPLIED.json`; it
never imports the artefact's producer (`spi_apply.py`), so a bug there cannot teach this file to agree.

It enforces five things that prose cannot enforce:

 1. COVERAGE — every committed SPI verdict row is graded and, if it is a membership row, has exactly one
    declared effect. Silence about a row is a failure, not a default.

 2. THE HUMAN IS NOT FALSIFIED (protocol §3.1) — a row where the two passes DISAGREE (kinds VERIFICACION
    / CONFIRMACION: pass 1 decided, the SPI decided, they differ) may NEVER move the corpus. Its only
    legal effect is HUMAN_QUEUE. Only rows where pass 1 ABSTAINED (kind ADJUDICACION) may add or remove
    membership, because there the SPI is not overruling a reader: it is the only decision that exists.

 3. NOTHING IS DELETED (protocol §3.3) — a DEGRADAR or a FUSIONAR is a RECORDED fact, so the degraded /
    merged key must still be present in the corpus files on disk. A derivation that "fixes" the corpus by
    erasing rows destroys the provenance that IS the corpus.

 4. EVIDENCE GRADE IS MEASURED, NOT CLAIMED — the grade of each SPI row (full-text / abstract / title-only)
    is recomputed here from the row's own input record: full-text iff its `pdf` field pointed at a file
    that exists on disk, title-only iff it carried no abstract at all, abstract otherwise. A row decided
    from a title may never be promoted into the full-text digest, and the summary may not describe an
    adjudication queue as decided "with the PDF at hand" when it was not.

 5. AGREEMENT.md AGREES WITH THE DERIVATION — the generated summary must publish the evidence-grade mix of
    every adjudication queue, with numbers equal to the ones re-derived here. This is the tooth on the
    error class this phase keeps hitting: an aggregate that is correct read as a claim that does not
    follow from it.

Usage:  python3 harvest/verify_spi_apply.py [--applied corpus/spi/APPLIED.json] [--no-agreement]
Exit 0 only if EVERY check passes. Read-only: it never writes, repairs or regenerates anything.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import closure_law  # noqa: E402

ROOT = HERE.parent
BATCHES = ROOT / "corpus/spi/batches"
APPLIED = ROOT / "corpus/spi/APPLIED.json"
AGREEMENT = ROOT / "corpus/spi/AGREEMENT.md"
EXTRACTION = ROOT / "corpus/extraction/extraction.csv"
DIGEST = ROOT / "corpus/digestion/digest.jsonl"

GRADE_FULL, GRADE_ABSTRACT, GRADE_TITLE = "full-text", "abstract", "title-only"

# The closed vocabulary of effects. An effect outside this set is a silent invention.
EFFECTS = {"ADD_INCLUIR", "ADD_EXCLUIR", "HUMAN_QUEUE", "DEGRADED", "MERGED", "NO_CHANGE"}
# Effects that MOVE corpus membership. Legal only from a queue where pass 1 abstained.
MEMBERSHIP_MOVING = {"ADD_INCLUIR", "ADD_EXCLUIR"}


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_spi(kind: str = "verdict") -> dict[str, dict[str, dict]]:
    """{queue: {key: row}} read straight off the committed batch files."""
    out: dict[str, dict[str, dict]] = {}
    for qdir in sorted(p for p in BATCHES.iterdir() if p.is_dir()):
        rows: dict[str, dict] = {}
        for f in sorted(qdir.glob(f"q*.{kind}.jsonl")):
            for row in _read_jsonl(f):
                rows[row["key"]] = row
        out[qdir.name] = rows
    return out


def grade_of(inp: dict | None) -> str:
    """Evidence actually in front of the second reader. Measured from the input record, not asserted."""
    if inp is None:
        return GRADE_TITLE
    pdf = (inp.get("pdf") or "").strip()
    if pdf and (ROOT / pdf).exists():
        return GRADE_FULL
    return GRADE_ABSTRACT if (inp.get("abstract") or "").strip() else GRADE_TITLE


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--applied", default=str(APPLIED))
    ap.add_argument("--no-agreement", action="store_true", help="skip check 5 (AGREEMENT.md not regenerated yet)")
    args = ap.parse_args()

    errors: list[str] = []
    applied_path = Path(args.applied)
    if not applied_path.exists():
        print(f"FAIL: {applied_path} does not exist", file=sys.stderr)
        return 1
    applied = json.loads(applied_path.read_text(encoding="utf-8"))

    verdicts = load_spi("verdict")
    inputs = load_spi("input")

    # ---------------------------------------------------------------- 1. coverage
    grades: dict[str, str] = applied.get("evidence_grade", {})
    deltas: list[dict] = applied.get("membership_delta", [])
    by_key_delta: dict[tuple[str, str], dict] = {}
    for d in deltas:
        k = (d.get("queue", ""), d.get("key", ""))
        if k in by_key_delta:
            errors.append(f"coverage: duplicate delta for {k}")
        by_key_delta[k] = d

    n_rows = 0
    for queue, rows in verdicts.items():
        kind = closure_law.QUEUES[queue].kind
        for key in rows:
            n_rows += 1
            if key not in grades:
                errors.append(f"coverage: {queue}/{key} has no evidence_grade")
            if (queue, key) not in by_key_delta:
                errors.append(f"coverage: {queue}/{key} has no declared effect")
    for (queue, key) in by_key_delta:
        if key not in verdicts.get(queue, {}):
            errors.append(f"coverage: delta {queue}/{key} matches no committed verdict")
    if not n_rows:
        errors.append("coverage: no committed verdicts found at all")

    # ---------------------------------------------------------------- 2. the human is not falsified
    for d in deltas:
        queue, key, effect = d.get("queue", ""), d.get("key", ""), d.get("effect", "")
        if effect not in EFFECTS:
            errors.append(f"vocabulary: {queue}/{key} declares unknown effect {effect!r}")
            continue
        kind = closure_law.QUEUES[queue].kind if queue in closure_law.QUEUES else "?"
        if effect in MEMBERSHIP_MOVING and kind != closure_law.KIND_ADJUDICACION:
            errors.append(
                f"§3.1 VIOLATED: {queue}/{key} (kind {kind}) moves corpus membership with {effect}. "
                "Only a queue where pass 1 ABSTAINED may move membership; a disagreement goes to the human."
            )
        # The SPI inputs are BLIND by construction: they never carry pass 1's decision, so this gate
        # cannot (and must not) recompute the disagreement here. The invariant that matters is
        # structural and stronger: a queue where pass 1 DECIDED can only ever route to a human.
        if kind in (closure_law.KIND_VERIFICACION, closure_law.KIND_CONFIRMACION):
            if effect not in ("HUMAN_QUEUE", "NO_CHANGE"):
                errors.append(f"§3.1 VIOLATED: {queue}/{key} (kind {kind}) declares {effect}; only HUMAN_QUEUE/NO_CHANGE are legal")

    # effects must be sourced from the right verdict field
    degraded_real = {k for q, rows in verdicts.items() for k, r in rows.items()
                     if (r.get("veredicto") or "").strip() == "DEGRADAR"}
    merged_real = {k for q, rows in verdicts.items() for k, r in rows.items()
                   if (r.get("veredicto") or "").strip() == "FUSIONAR"}
    degraded_claimed = {d["key"] for d in deltas if d.get("effect") == "DEGRADED"}
    merged_claimed = {d["key"] for d in deltas if d.get("effect") == "MERGED"}
    if degraded_claimed != degraded_real:
        errors.append(f"DEGRADED mismatch: claimed {sorted(degraded_claimed)} vs verdicts {sorted(degraded_real)}")
    if merged_claimed != merged_real:
        errors.append(f"MERGED mismatch: claimed {sorted(merged_claimed)} vs verdicts {sorted(merged_real)}")

    # every ADD_* must match the SPI decision actually recorded
    for d in deltas:
        if d.get("effect") in MEMBERSHIP_MOVING:
            v = verdicts[d["queue"]][d["key"]]
            decision = (v.get("decision") or "").strip()
            want_in = decision in closure_law.IN_LABELS
            if (d["effect"] == "ADD_INCLUIR") != want_in:
                errors.append(f"effect mismatch: {d['key']} declares {d['effect']} but verdict says {decision!r}")
            if decision in closure_law.HUMAN_LABELS:
                errors.append(f"effect mismatch: {d['key']} declares {d['effect']} but verdict {decision!r} is a human label")

    # ---------------------------------------------------------------- 3. nothing is deleted
    ext_keys = {r["key"] for r in closure_law._read_csv(EXTRACTION)} if EXTRACTION.exists() else set()
    dig_keys = {r["key"] for r in _read_jsonl(DIGEST)}
    for key in sorted(degraded_real | merged_real):
        if key not in ext_keys and key not in dig_keys:
            errors.append(f"§3.3 VIOLATED: {key} was degraded/merged and is GONE from extraction.csv and digest.jsonl "
                          "— a degraded row is RECORDED, never erased")

    # ---------------------------------------------------------------- 4. evidence grade is measured
    recomputed: dict[str, str] = {}
    for queue, rows in verdicts.items():
        for key in rows:
            recomputed[key] = grade_of(inputs.get(queue, {}).get(key))
    for key, want in recomputed.items():
        got = grades.get(key)
        if got != want:
            errors.append(f"evidence_grade: {key} claims {got!r}, measured {want!r}")

    eligible = set(applied.get("digest_eligible", []))
    add_incluir = {d["key"] for d in deltas if d.get("effect") == "ADD_INCLUIR"}

    # A TITLE IS NOT AN EVIDENCE ANCHOR. `closure_law.EVIDENCE_ANCHORS` requires a decision to be
    # anchored in the study's own text; admitting a study whose title is all anyone ever saw puts a
    # record in the mapping whose eligibility (mechanism / domain / evaluation) was never checked
    # against any content. The conservative direction is allowed and the honest one is required:
    # a title-only EXCLUSION may stand (it only ever shrinks the corpus) but must be COUNTED and
    # published as a threat to validity; a title-only ADMISSION must go to the human instead.
    for d in deltas:
        if d.get("effect") == "ADD_INCLUIR" and recomputed.get(d["key"]) == GRADE_TITLE:
            errors.append(
                f"NO ANCHOR: {d['key']} ({d['queue']}) is ADMITTED to the corpus on its TITLE alone. "
                "A title-only row must be HUMAN_QUEUE — an inclusion with no evidence anchor is not a decision.")
    n_title_excl = sum(1 for d in deltas
                       if d.get("effect") == "ADD_EXCLUIR" and recomputed.get(d["key"]) == GRADE_TITLE)
    declared = (applied.get("counts", {}) or {}).get("title_only_exclusions")
    if declared != n_title_excl:
        errors.append(
            f"counts.title_only_exclusions: declares {declared!r}, measured {n_title_excl}. "
            "Studies excluded without anyone reading a word of them are a threat to validity and the "
            "corpus must carry the number, not discover it later.")
    for key in sorted(eligible):
        if key not in add_incluir:
            errors.append(f"digest_eligible: {key} is not an ADD_INCLUIR")
        if recomputed.get(key) == GRADE_TITLE:
            errors.append(f"digest_eligible: {key} was decided from its TITLE alone and cannot enter a full-text digest")
        if not (ROOT / f"corpus/pdf/{key}.pdf").exists():
            errors.append(f"digest_eligible: {key} has no full text on disk")
    for key in sorted(add_incluir - eligible):
        if (ROOT / f"corpus/pdf/{key}.pdf").exists() and recomputed.get(key) != GRADE_TITLE:
            errors.append(f"digest_eligible: {key} has full text and was included, but is not listed eligible")

    # ---------------------------------------------------------------- 5. the summary agrees
    if not args.no_agreement and AGREEMENT.exists():
        text = AGREEMENT.read_text(encoding="utf-8")
        for queue, rows in verdicts.items():
            if closure_law.QUEUES[queue].kind != closure_law.KIND_ADJUDICACION:
                continue
            mix: dict[str, int] = {}
            for key in rows:
                mix[recomputed[key]] = mix.get(recomputed[key], 0) + 1
            section = re.split(r"^## ", text, flags=re.M)
            body = next((s for s in section if s.startswith(queue)), "")
            if not body:
                errors.append(f"AGREEMENT.md: no section for adjudication queue {queue}")
                continue
            for grade, n in sorted(mix.items()):
                if not re.search(rf"{n}\s*(?:filas?|registros?|rows?)?[^\n]*{re.escape(grade)}|{re.escape(grade)}[^\n]*\b{n}\b", body):
                    errors.append(
                        f"AGREEMENT.md/{queue}: does not publish the evidence mix ({grade}={n}). "
                        "An adjudication queue must state what the reader actually saw."
                    )
            if re.search(r"con el (?:PDF|texto completo) a la vista", body) and mix.get(GRADE_FULL, 0) != len(rows):
                errors.append(
                    f"AGREEMENT.md/{queue}: claims the decision was made 'con el PDF/texto completo a la vista' "
                    f"but only {mix.get(GRADE_FULL, 0)}/{len(rows)} rows had full text on disk")

    for e in errors[:60]:
        print(f"FAIL: {e}", file=sys.stderr)
    if errors:
        print(f"\n{len(errors)} problem(s); SPI application NOT verified", file=sys.stderr)
        return 1
    print(f"OK: SPI application verified — {n_rows} verdict rows graded, {len(deltas)} effects declared, "
          f"{len(degraded_real)} degraded and {len(merged_real)} merged still present in the corpus, "
          f"{len(eligible)} newly digest-eligible")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
