#!/usr/bin/env python3
"""Apply the second independent pass (SPI) to the corpus — §9.2 CLOSURE, the APPLICATION step.

Turns the 534 committed SPI verdicts (`corpus/spi/batches/<QUEUE>/q*.verdict.jsonl`) into the post-SPI
corpus view, `corpus/spi/APPLIED.json`. This is a PURE DERIVATION from committed data: it never mutates
`corpus/screening/*`, `corpus/extraction/*` or `corpus/digestion/*`, never deletes a row anywhere, and
never touches the network. Everything it produces is judged by `harvest/verify_spi_apply.py` (written
before this file, outside its blast radius) — read that gate for the exact schema/invariants; this module
implements the four rules it enforces, not a rule of its own:

  * pass 1 ABSTAINED (kind ADJUDICACION)                -> the SPI's decision ADDs/EXCLUDEs/HUMAN_QUEUEs
  * the two passes DISAGREE (VERIFICACION/CONFIRMACION) -> HUMAN_QUEUE, never a flip (§3.1)
  * the two passes AGREE   (VERIFICACION/CONFIRMACION)  -> NO_CHANGE
  * veredicto DEGRADAR / FUSIONAR (CALIDAD/IDENTIDAD)   -> DEGRADED / MERGED, recorded, never deleted (§3.3)

Evidence grade (full-text / abstract / title-only) is MEASURED per key from that key's own committed
input record, exactly as the gate recomputes it (`grade_of`, mirrored not imported: the gate must not
import this producer, see its own docstring). A queue's predicates are NOT mutually exclusive (e.g. a
GRIS decision that also lands in the 10% VERIFICACION sample), so the same key can appear in two queues;
its ONE `evidence_grade` entry resolves to whichever queue sorts last alphabetically among the batch
directories -- the same resolution order the gate's own `recomputed` dict uses (`evidence_grades()` is
the single source both this module and `spi_agreement.py` read, so the two never disagree about it).

A title is not an evidence anchor (contract §1 AMENDMENT 2026-07-27): an ADJUDICACION row whose SPI
decision is an inclusion (IN_LABELS) but whose own evidence grade is `title-only` is never emitted as
`ADD_INCLUIR` -- it goes to `HUMAN_QUEUE` instead, because nobody could anchor that admission in the
study's own text. A title-only `ADD_EXCLUIR` STAYS (excluding for lack of retrievable evidence only ever
shrinks the corpus, the conservative direction) but is counted in `counts.title_only_exclusions` so it is
a declared threat to validity, not a silent one.

Usage:
    python3 harvest/spi_apply.py            # derive + print a short human summary, WRITE NOTHING
    python3 harvest/spi_apply.py --write    # additionally write corpus/spi/APPLIED.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import closure_law  # noqa: E402

ROOT = HERE.parent
BATCHES = ROOT / "corpus/spi/batches"
APPLIED = ROOT / "corpus/spi/APPLIED.json"

GRADE_FULL, GRADE_ABSTRACT, GRADE_TITLE = "full-text", "abstract", "title-only"


# --------------------------------------------------------------------------- evidence grade (measured)
def grade_of(inp: dict | None) -> str:
    """Evidence actually in front of the second reader, from ITS OWN input record. Mirrors
    `verify_spi_apply.grade_of` exactly (the gate re-derives this independently on purpose; this is not
    an import, it is the same three-line rule stated twice so a bug in one cannot teach the other to
    agree)."""
    if inp is None:
        return GRADE_TITLE
    pdf = (inp.get("pdf") or "").strip()
    if pdf and (ROOT / pdf).exists():
        return GRADE_FULL
    return GRADE_ABSTRACT if (inp.get("abstract") or "").strip() else GRADE_TITLE


# --------------------------------------------------------------------------- committed batch loading
def load_batch(queue: str, kind: str) -> dict[str, dict]:
    """{key: row} for one queue's committed `q*.<kind>.jsonl` files."""
    out: dict[str, dict] = {}
    qdir = BATCHES / queue
    if not qdir.exists():
        return out
    for f in sorted(qdir.glob(f"q*.{kind}.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                out[row["key"]] = row
    return out


def load_all(kind: str) -> dict[str, dict[str, dict]]:
    """{queue: {key: row}}, iterated in the SAME sorted-directory order `verify_spi_apply.load_spi` uses.
    That order is load-bearing: see the module docstring on cross-queue key collisions."""
    out: dict[str, dict[str, dict]] = {}
    if not BATCHES.exists():
        return out
    for qdir in sorted(p for p in BATCHES.iterdir() if p.is_dir()):
        out[qdir.name] = load_batch(qdir.name, kind)
    return out


def compute_evidence_grade(verdicts: dict[str, dict[str, dict]],
                            inputs: dict[str, dict[str, dict]]) -> dict[str, str]:
    """The canonical {key: grade}, last-write-wins over `verdicts` in ITS iteration order (sorted queue
    directory names) -- identical resolution to the gate's own `recomputed` dict, so a key present in two
    queues never disagrees with itself."""
    grades: dict[str, str] = {}
    for queue, rows in verdicts.items():
        for key in rows:
            grades[key] = grade_of(inputs.get(queue, {}).get(key))
    return grades


def evidence_grades() -> dict[str, str]:
    """Public single source for the corpus-wide evidence-grade mix: both `APPLIED.json` (via `derive`)
    and `spi_agreement.py`'s published mix read from HERE, never recompute their own."""
    return compute_evidence_grade(load_all("verdict"), load_all("input"))


# --------------------------------------------------------------------------- the four rules (§9.2)
def _effect_for(q: closure_law.Queue, key: str, v: dict,
                 pass1_index, grade: str) -> tuple[str, str, str]:
    """(effect, spi_value, one-line reason) for a single committed verdict row, per the rule table in
    `.gen/spi-apply.contract.md` §1. `pass1_index(source)` is a lazily-memoized {key: row} lookup into
    the committed pass-1 sheet (only ever called for VERIFICACION/CONFIRMACION, which are the only kinds
    that need to know what pass 1 decided). `grade` is this key's own MEASURED evidence grade -- needed
    here (not just in `counts`) because a title-only ADJUDICACION inclusion is illegal (§1 AMENDMENT
    2026-07-27): a title is not an evidence anchor."""
    if q.kind == closure_law.KIND_ADJUDICACION:
        dec = (v.get("decision") or "").strip()
        if dec in closure_law.HUMAN_LABELS:
            return ("HUMAN_QUEUE", dec,
                    f"pass 1 abstained and the SPI re-emitted {dec!r} on this adjudication row -- still "
                    "undecided with more evidence in hand, so it stays a human decision.")
        if dec in closure_law.IN_LABELS:
            if grade == GRADE_TITLE:
                return ("HUMAN_QUEUE", dec,
                        f"pass 1 abstained (GRIS/CE-4p) and the SPI decided {dec!r} to include this study, "
                        "but the second reader had only its TITLE in front of it -- an inclusion with no "
                        "evidence anchor is not a decision, so it goes to the human queue instead of the "
                        "corpus (§1 AMENDMENT 2026-07-27).")
            return ("ADD_INCLUIR", dec,
                    "pass 1 abstained (GRIS/CE-4p); the SPI is the only decision that exists here, and "
                    f"it decided {dec!r} -- nothing is being overruled, so membership is added.")
        return ("ADD_EXCLUIR", dec,
                "pass 1 abstained (GRIS/CE-4p); the SPI is the only decision that exists here, and it "
                f"decided {dec!r} -- nothing is being overruled, so membership is excluded "
                + ("(evidence grade was TITLE-only: excluding for lack of retrievable evidence is the "
                   "conservative direction, but it is a declared threat to validity -- see "
                   "counts.title_only_exclusions)." if grade == GRADE_TITLE else "."))

    if q.kind in (closure_law.KIND_VERIFICACION, closure_law.KIND_CONFIRMACION):
        p1 = pass1_index(q.source).get(key, {})
        p1dec = (p1.get("decision") or "").strip()
        spidec = (v.get("decision") or "").strip()
        if p1dec in closure_law.HUMAN_LABELS:
            return ("HUMAN_QUEUE", spidec,
                    f"pass 1 itself abstained ({p1dec!r}) even though this row was drawn into a "
                    f"{q.kind} queue; there is no firm firsthand decision to compare against, so it is "
                    "still undecided -- human queue, never a flip (§3.1).")
        if closure_law.collapse(p1dec) == closure_law.collapse(spidec):
            return ("NO_CHANGE", spidec,
                    f"pass 1 ({p1dec!r}) and the SPI ({spidec!r}) agree at membership level -- "
                    "consolidated by two independent readers, no change.")
        return ("HUMAN_QUEUE", spidec,
                f"pass 1 ({p1dec!r}) and the SPI ({spidec!r}) disagree at membership level -- an agent "
                "may not be the adjudicating human (§3.1), so this goes to the human queue, never a flip.")

    if q.kind == closure_law.KIND_CALIDAD:
        ver = (v.get("veredicto") or "").strip()
        if ver == "DEGRADAR":
            return ("DEGRADED", ver,
                    "veredicto DEGRADAR -- a provenance failure, recorded but never deleted (§3.3).")
        return ("NO_CHANGE", ver, f"veredicto {ver!r} is a quality note, not a membership move.")

    if q.kind == closure_law.KIND_IDENTIDAD:
        ver = (v.get("veredicto") or "").strip()
        if ver == "FUSIONAR":
            canon = (v.get("canonica") or "").strip()
            return ("MERGED", ver,
                    f"veredicto FUSIONAR -- two rows are one study; canonica={canon!r}, both keys kept "
                    "in provenance.")
        return ("NO_CHANGE", ver, f"veredicto {ver!r} -- two rows confirmed distinct, no membership move.")

    raise ValueError(f"unknown queue kind {q.kind!r} for queue {q.name}")  # pragma: no cover - closed set


# --------------------------------------------------------------------------- counts
def _counts(deltas: list[dict], grades: dict[str, str]) -> dict:
    by_effect: Counter = Counter(d["effect"] for d in deltas)
    by_grade: Counter = Counter(grades.values())
    by_queue: dict[str, Counter] = defaultdict(Counter)
    for d in deltas:
        by_queue[d["queue"]][d["spi"]] += 1
    # A title-only ADD_EXCLUIR stays (the conservative direction) but MUST be counted, never discovered
    # later: it is an exclusion nobody read a word of (§1 AMENDMENT 2026-07-27). Derived, never hardcoded.
    title_only_exclusions = sum(
        1 for d in deltas if d["effect"] == "ADD_EXCLUIR" and d["evidence_grade"] == GRADE_TITLE
    )
    return {
        "rows": len(deltas),
        "by_effect": dict(sorted(by_effect.items())),
        "by_grade": dict(sorted(by_grade.items())),
        "by_queue": {q: dict(sorted(c.items())) for q, c in sorted(by_queue.items())},
        "title_only_exclusions": title_only_exclusions,
    }


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


# --------------------------------------------------------------------------- the derivation itself
def derive() -> dict:
    verdicts = load_all("verdict")
    inputs = load_all("input")
    grades = compute_evidence_grade(verdicts, inputs)

    pass1_cache: dict[str, dict[str, dict]] = {}

    def pass1_index(source: str) -> dict[str, dict]:
        if source not in pass1_cache:
            pass1_cache[source] = {r["key"]: r for r in closure_law.source_rows(source) if "key" in r}
        return pass1_cache[source]

    deltas: list[dict] = []
    merged_into: list[dict] = []
    for qname, q in closure_law.QUEUES.items():
        rows = verdicts.get(qname, {})
        for key in sorted(rows):
            v = rows[key]
            grade = grades.get(key, GRADE_TITLE)
            effect, spi_value, reason = _effect_for(q, key, v, pass1_index, grade)
            deltas.append({
                "key": key, "queue": qname, "kind": q.kind, "spi": spi_value,
                "effect": effect, "evidence_grade": grade, "reason": reason,
            })
            if effect == "MERGED":
                canon = (v.get("canonica") or "").strip()
                pareja = (v.get("pareja") or "").strip()
                frm = pareja if canon == key else key
                merged_into.append({"from": frm, "into": canon})

    add_incluir = {d["key"] for d in deltas if d["effect"] == "ADD_INCLUIR"}
    digest_eligible = sorted(
        k for k in add_incluir
        if grades.get(k) != GRADE_TITLE and (ROOT / f"corpus/pdf/{k}.pdf").exists()
    )
    digest_blocked = sorted(add_incluir - set(digest_eligible))

    return {
        "generated_by": "harvest/spi_apply.py",
        "generated_at": _now(),
        "evidence_grade": dict(sorted(grades.items())),
        "membership_delta": deltas,
        "merged_into": sorted(merged_into, key=lambda m: m["from"]),
        "digest_eligible": digest_eligible,
        "digest_blocked_no_fulltext": digest_blocked,
        "counts": _counts(deltas, grades),
    }


# --------------------------------------------------------------------------- CLI
def _summary(applied: dict) -> str:
    c = applied["counts"]
    return "\n".join([
        f"SPI application ({applied['generated_at']}): {c['rows']} verdict rows across "
        f"{len(c['by_queue'])} queues.",
        f"  effects: {c['by_effect']}",
        f"  evidence grade (unique keys): {c['by_grade']}",
        f"  digest_eligible={len(applied['digest_eligible'])} "
        f"digest_blocked_no_fulltext={len(applied['digest_blocked_no_fulltext'])} "
        f"merged_into={len(applied['merged_into'])}",
    ])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="additionally write corpus/spi/APPLIED.json")
    args = ap.parse_args(argv)

    applied = derive()
    print(_summary(applied))
    if args.write:
        APPLIED.parent.mkdir(parents=True, exist_ok=True)
        APPLIED.write_text(json.dumps(applied, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[spi_apply] wrote {APPLIED}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
