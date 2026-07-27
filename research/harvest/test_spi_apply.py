"""Offline tests for `spi_apply.py` (§9.2 CLOSURE application), exercised against the REAL gate
(`verify_spi_apply.main`) so a passing test here means an artifact this module produces would actually
satisfy the gate that judges it -- not a reimplementation of the gate's own rules. Follows
`test_closure_tools.py` conventions: no network, no dependence on cwd, never touches the real committed
corpus (every path the two modules read is monkeypatched to a small synthetic `tmp_path` fixture).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import closure_law as cl  # noqa: E402
import spi_apply as sa  # noqa: E402
import verify_spi_apply as vsa  # noqa: E402


# ============================================================================
# shared helpers
# ============================================================================

def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def _write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in header})


def _put_queue(batches: Path, queue: str, rows: list[tuple[dict, dict]]) -> None:
    """Write one q01 chunk (input + verdict) for `queue`. `rows` is [(input_row, verdict_row), ...],
    each carrying its own 'key' -- chunk splitting is irrelevant to spi_apply.py, which globs q*.*.jsonl."""
    qdir = batches / queue
    qdir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(qdir / "q01.input.jsonl", [r[0] for r in rows])
    _write_jsonl(qdir / "q01.verdict.jsonl", [r[1] for r in rows])


def _load_applied(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_applied(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _delta(data: dict, queue: str, key: str) -> dict:
    for d in data["membership_delta"]:
        if d["queue"] == queue and d["key"] == key:
            return d
    raise KeyError((queue, key))


@pytest.fixture
def spi_env(tmp_path, monkeypatch):
    """A small synthetic corpus wired into spi_apply.py + verify_spi_apply.py + closure_law, covering one
    member of every queue KIND plus the specific traps the contract calls out: a title-only row the SPI
    decided to INCLUDE, with a PDF that landed on disk anyway (a title is not an evidence anchor -- §1
    AMENDMENT 2026-07-27 -- so it must become HUMAN_QUEUE, never ADD_INCLUIR, and never digest_eligible), a
    title-only row the SPI decided to EXCLUDE (that one STAYS ADD_EXCLUIR -- the conservative direction --
    but must be counted in `counts.title_only_exclusions`), a pass-1 ABSTAINED row drawn into a
    VERIFICACION queue (must go HUMAN_QUEUE, never NO_CHANGE/ADD_*), and a key that is a member of TWO
    queues at once (GRIS + MUESTRA-10PCT are not mutually exclusive predicates in the real corpus) to prove
    `evidence_grade` resolves the same way spi_apply and the gate both resolve it."""
    root = tmp_path
    batches = root / "corpus/spi/batches"
    applied = root / "corpus/spi/APPLIED.json"
    pdf_dir = root / "corpus/pdf"
    pdf_dir.mkdir(parents=True)
    extraction = root / "corpus/extraction/extraction.csv"
    digest = root / "corpus/digestion/digest.jsonl"
    sheet_full = root / "corpus/screening/screening_full.csv"
    sheet_snow = root / "corpus/screening/screening_snowball.csv"

    monkeypatch.setattr(sa, "ROOT", root)
    monkeypatch.setattr(sa, "BATCHES", batches)
    monkeypatch.setattr(sa, "APPLIED", applied)

    monkeypatch.setattr(vsa, "ROOT", root)
    monkeypatch.setattr(vsa, "BATCHES", batches)
    monkeypatch.setattr(vsa, "APPLIED", applied)
    monkeypatch.setattr(vsa, "AGREEMENT", root / "corpus/spi/AGREEMENT.md")
    monkeypatch.setattr(vsa, "EXTRACTION", extraction)
    monkeypatch.setattr(vsa, "DIGEST", digest)

    monkeypatch.setattr(cl, "SHEET_FULL", sheet_full)
    monkeypatch.setattr(cl, "SHEET_SNOWBALL", sheet_snow)

    monkeypatch.setattr(sys, "argv", ["verify_spi_apply.py", "--no-agreement"])

    (pdf_dir / "FULL0001.pdf").write_bytes(b"%PDF-1.4 fixture")
    (pdf_dir / "TITLEPDF01.pdf").write_bytes(b"%PDF-1.4 fixture")   # the trap: pdf exists, grade is TITLE
    (pdf_dir / "SHARED01.pdf").write_bytes(b"%PDF-1.4 fixture")

    # ---- GRIS (ADJUDICACION, source=full) ------------------------------------------------------
    gris_rows = [
        ({"key": "FULL0001", "title": "t", "abstract": "a real abstract, plenty of words.", "year": "2026",
          "pdf": "corpus/pdf/FULL0001.pdf"},
         {"key": "FULL0001", "decision": "INCLUIR", "evidencia": "e", "notes": "n"}),
        ({"key": "GRISOUT01", "title": "t", "abstract": "a real abstract, plenty of words.", "year": "2026"},
         {"key": "GRISOUT01", "decision": "EXCLUIR-CE1", "evidencia": "e", "notes": "n"}),
        ({"key": "GRISSTAY01", "title": "t", "abstract": "", "year": "2026"},
         {"key": "GRISSTAY01", "decision": "GRIS", "evidencia": "e", "notes": "n"}),
        ({"key": "TITLEPDF01", "title": "t", "abstract": "", "year": "2026"},
         {"key": "TITLEPDF01", "decision": "INCLUIR", "evidencia": "e", "notes": "n"}),
        # title-only EXCLUSION: stays ADD_EXCLUIR (conservative direction) but must be COUNTED
        ({"key": "TITLEEXCL01", "title": "t", "abstract": "", "year": "2026"},
         {"key": "TITLEEXCL01", "decision": "EXCLUIR-CE1", "evidencia": "e", "notes": "n"}),
        # collides with MUESTRA-10PCT below: same key, DIFFERENT evidence in this queue's own input
        ({"key": "SHARED01", "title": "t", "abstract": "", "year": "2026"},
         {"key": "SHARED01", "decision": "EXCLUIR-CE2", "evidencia": "e", "notes": "n"}),
    ]
    _put_queue(batches, "GRIS", gris_rows)

    # ---- MUESTRA-10PCT (VERIFICACION, source=full) ---------------------------------------------
    muestra_rows = [
        ({"key": "AGREE01", "title": "t", "abstract": "abc", "year": "2026"},
         {"key": "AGREE01", "decision": "INCLUIR", "evidencia": "e", "notes": "n"}),
        ({"key": "DISAGREE01", "title": "t", "abstract": "abc", "year": "2026"},
         {"key": "DISAGREE01", "decision": "INCLUIR", "evidencia": "e", "notes": "n"}),
        ({"key": "ABSTAINED01", "title": "t", "abstract": "abc", "year": "2026"},
         {"key": "ABSTAINED01", "decision": "INCLUIR", "evidencia": "e", "notes": "n"}),
        ({"key": "SHARED01", "title": "t", "abstract": "abc", "year": "2026",
          "pdf": "corpus/pdf/SHARED01.pdf"},
         {"key": "SHARED01", "decision": "EXCLUIR-CE1", "evidencia": "e", "notes": "n"}),
    ]
    _put_queue(batches, "MUESTRA-10PCT", muestra_rows)
    _write_csv(sheet_full, ["key", "decision"], [
        {"key": "AGREE01", "decision": "INCLUIR"},
        {"key": "DISAGREE01", "decision": "EXCLUIR-CE1"},
        {"key": "ABSTAINED01", "decision": "GRIS"},
        {"key": "SHARED01", "decision": "GRIS"},
    ])

    # ---- RECONSIDERAR-EXT (CALIDAD, source=extraction) -----------------------------------------
    ext_rows = [
        ({"key": "DEG0001", "title": "t"},
         {"key": "DEG0001", "veredicto": "DEGRADAR", "evidencia": "e", "notes": "n"}),
        ({"key": "CONF0001", "title": "t"},
         {"key": "CONF0001", "veredicto": "CONFIRMA-RECONSIDERAR", "evidencia": "e", "notes": "n"}),
    ]
    _put_queue(batches, "RECONSIDERAR-EXT", ext_rows)
    _write_csv(extraction, ["key", "notes"], [
        {"key": "DEG0001", "notes": "kept, degraded"},
        {"key": "CONF0001", "notes": "kept"},
    ])
    _write_jsonl(digest, [{"key": "DUPA0001", "cita": "the merged-away copy, still on record (§3.3)"}])

    # ---- DUPLICADOS (IDENTIDAD, source=duplicados) ---------------------------------------------
    dup_rows = [
        ({"key": "DUPA0001", "pareja": "DUPB0001", "title_a": "t", "title_b": "t"},
         {"key": "DUPA0001", "pareja": "DUPB0001", "veredicto": "FUSIONAR", "canonica": "DUPB0001",
          "evidencia": "e", "notes": "n"}),
        ({"key": "DUPA0002", "pareja": "DUPB0002", "title_a": "t", "title_b": "t"},
         {"key": "DUPA0002", "pareja": "DUPB0002", "veredicto": "DISTINTOS",
          "evidencia": "e", "notes": "n"}),
    ]
    _put_queue(batches, "DUPLICADOS", dup_rows)

    return {"root": root, "batches": batches, "applied": applied, "extraction": extraction, "digest": digest}


# ============================================================================
# (1) the real gate, happy path -- required case 1
# ============================================================================

def test_well_formed_application_passes_the_gate(spi_env):
    assert sa.main(["--write"]) == 0
    assert spi_env["applied"].exists()
    assert vsa.main() == 0


def test_default_run_writes_nothing(spi_env):
    assert not spi_env["applied"].exists()
    assert sa.main([]) == 0                 # no --write: prints a summary, touches nothing
    assert not spi_env["applied"].exists()


# ============================================================================
# (2) derive() itself: every rule-table row, asserted directly -- the gate CANNOT check the
#     HUMAN_QUEUE-vs-NO_CHANGE choice for VERIFICACION/CONFIRMACION (its own docstring: the SPI inputs
#     are blind by construction), so only a direct assertion on the derivation proves it is right.
# ============================================================================

def test_derive_effects_match_the_rule_table(spi_env):
    data = sa.derive()

    # ADJUDICACION: pass 1 abstained -> the SPI's own decision is the only one that exists
    assert _delta(data, "GRIS", "FULL0001")["effect"] == "ADD_INCLUIR"
    assert _delta(data, "GRIS", "GRISOUT01")["effect"] == "ADD_EXCLUIR"
    assert _delta(data, "GRIS", "GRISSTAY01")["effect"] == "HUMAN_QUEUE"     # SPI re-abstained (GRIS)

    # VERIFICACION: agree -> NO_CHANGE, disagree -> HUMAN_QUEUE, never a flip
    assert _delta(data, "MUESTRA-10PCT", "AGREE01")["effect"] == "NO_CHANGE"
    assert _delta(data, "MUESTRA-10PCT", "DISAGREE01")["effect"] == "HUMAN_QUEUE"

    # VERIFICACION where pass 1 ITSELF abstained: nothing to compare -> still undecided, never ADD_*
    assert _delta(data, "MUESTRA-10PCT", "ABSTAINED01")["effect"] == "HUMAN_QUEUE"

    # CALIDAD / IDENTIDAD
    assert _delta(data, "RECONSIDERAR-EXT", "DEG0001")["effect"] == "DEGRADED"
    assert _delta(data, "RECONSIDERAR-EXT", "CONF0001")["effect"] == "NO_CHANGE"
    assert _delta(data, "DUPLICADOS", "DUPA0001")["effect"] == "MERGED"
    assert _delta(data, "DUPLICADOS", "DUPA0002")["effect"] == "NO_CHANGE"

    assert {"from": "DUPA0001", "into": "DUPB0001"} in data["merged_into"]

    # every declared effect carries a non-empty one-line reason
    assert all((d.get("reason") or "").strip() for d in data["membership_delta"])


def test_title_only_inclusion_is_human_queue_never_added_even_with_a_pdf_on_disk(spi_env):
    """The specific trap (§1 AMENDMENT 2026-07-27): TITLEPDF01 was decided INCLUIR from its title alone (no
    abstract, no pdf in its OWN input) even though a PDF happens to exist on disk for that key. A title is
    not an evidence anchor -- the inclusion must go HUMAN_QUEUE, never ADD_INCLUIR, and it must never be
    digest_eligible NOR digest_blocked_no_fulltext (it never entered the corpus at all, so it is not a
    blocked ADD_INCLUIR either)."""
    data = sa.derive()
    delta = _delta(data, "GRIS", "TITLEPDF01")
    assert delta["effect"] == "HUMAN_QUEUE"
    assert "no evidence anchor" in delta["reason"]
    assert data["evidence_grade"]["TITLEPDF01"] == sa.GRADE_TITLE
    assert "TITLEPDF01" not in data["digest_blocked_no_fulltext"]
    assert "TITLEPDF01" not in data["digest_eligible"]


def test_title_only_exclusion_stays_add_excluir_but_is_counted(spi_env):
    """The conservative counterpart: TITLEEXCL01 was decided EXCLUIR-CE1 from its title alone. Excluding
    for lack of retrievable evidence only ever shrinks the corpus, so it STAYS ADD_EXCLUIR -- but it must
    be counted in `counts.title_only_exclusions` (a declared threat to validity, not a silent one)."""
    data = sa.derive()
    assert _delta(data, "GRIS", "TITLEEXCL01")["effect"] == "ADD_EXCLUIR"
    assert data["evidence_grade"]["TITLEEXCL01"] == sa.GRADE_TITLE
    assert data["counts"]["title_only_exclusions"] == 1


def test_full_text_add_incluir_is_digest_eligible(spi_env):
    data = sa.derive()
    assert data["evidence_grade"]["FULL0001"] == sa.GRADE_FULL
    assert "FULL0001" in data["digest_eligible"]


def test_key_in_two_queues_resolves_evidence_grade_the_same_way_the_gate_does(spi_env):
    """SHARED01 is a member of BOTH GRIS and MUESTRA-10PCT (the real corpus has 47 such collisions: the
    queue predicates are not mutually exclusive). Its ONE evidence_grade entry must resolve to whichever
    queue sorts last among the batch directory names -- MUESTRA-10PCT, alphabetically after GRIS -- which
    is exactly what `verify_spi_apply.grade_of`'s own `recomputed` dict does."""
    data = sa.derive()
    assert data["evidence_grade"]["SHARED01"] == sa.GRADE_FULL     # MUESTRA-10PCT's own input has the pdf
    # and that MUESTRA-10PCT row is HUMAN_QUEUE: pass 1 abstained (GRIS) even inside this VERIFICACION queue
    assert _delta(data, "MUESTRA-10PCT", "SHARED01")["effect"] == "HUMAN_QUEUE"
    assert _delta(data, "GRIS", "SHARED01")["effect"] == "ADD_EXCLUIR"


def test_evidence_grades_helper_matches_applied_json(spi_env):
    assert sa.main(["--write"]) == 0
    written = _load_applied(spi_env["applied"])
    assert sa.evidence_grades() == written["evidence_grade"]


# ============================================================================
# (3) NEGATIVE: corrupt a well-formed APPLIED.json, the REAL gate must reject it -- required cases 2-6
# ============================================================================

def test_verificacion_row_given_add_incluir_is_rejected_the_31_tooth_bites(spi_env):
    """Required case 2: a VERIFICACION row declaring ADD_INCLUIR must be RED (§3.1: an agent may not be
    the adjudicating human where pass 1 already decided or firmly disagreed)."""
    assert sa.main(["--write"]) == 0
    data = _load_applied(spi_env["applied"])
    _delta(data, "MUESTRA-10PCT", "AGREE01")["effect"] = "ADD_INCLUIR"
    _dump_applied(spi_env["applied"], data)
    assert vsa.main() == 1


def test_row_missing_from_membership_delta_is_coverage_red(spi_env):
    """Required case 3: silence about a committed verdict row is a failure, not a default."""
    assert sa.main(["--write"]) == 0
    data = _load_applied(spi_env["applied"])
    data["membership_delta"] = [
        d for d in data["membership_delta"]
        if not (d["queue"] == "RECONSIDERAR-EXT" and d["key"] == "CONF0001")
    ]
    _dump_applied(spi_env["applied"], data)
    assert vsa.main() == 1


def test_title_only_row_falsely_listed_digest_eligible_is_red(spi_env):
    """Required case 4."""
    assert sa.main(["--write"]) == 0
    data = _load_applied(spi_env["applied"])
    assert "TITLEPDF01" not in data["digest_eligible"]      # sanity: correctly excluded by construction
    data["digest_eligible"].append("TITLEPDF01")
    _dump_applied(spi_env["applied"], data)
    assert vsa.main() == 1


def test_evidence_grade_disagreeing_with_the_input_record_is_red(spi_env):
    """Required case 5."""
    assert sa.main(["--write"]) == 0
    data = _load_applied(spi_env["applied"])
    assert data["evidence_grade"]["FULL0001"] == sa.GRADE_FULL
    data["evidence_grade"]["FULL0001"] = sa.GRADE_ABSTRACT
    _dump_applied(spi_env["applied"], data)
    assert vsa.main() == 1


def test_degradar_key_erased_from_the_corpus_is_red(spi_env):
    """Required case 6 (§3.3): a DEGRADAR is a RECORDED fact -- erasing the key from every corpus file it
    could still live in destroys the provenance that IS the corpus."""
    assert sa.main(["--write"]) == 0
    assert vsa.main() == 0
    rows = [r for r in csv.DictReader(spi_env["extraction"].open(encoding="utf-8")) if r["key"] != "DEG0001"]
    _write_csv(spi_env["extraction"], ["key", "notes"], rows)   # digest.jsonl never had it either
    assert vsa.main() == 1


# ============================================================================
# (4) NEGATIVE: §1 AMENDMENT 2026-07-27 -- "a title is not an evidence anchor"
# ============================================================================

def test_title_only_add_incluir_is_rejected_the_gate_bites(spi_env):
    """A title-only ADD_INCLUIR is illegal: nobody could anchor that admission in the study's own text.
    A well-formed application never emits this (TITLEPDF01 is correctly HUMAN_QUEUE), so this test proves
    the gate itself rejects it if an application ever claimed otherwise."""
    assert sa.main(["--write"]) == 0
    assert vsa.main() == 0
    data = _load_applied(spi_env["applied"])
    assert data["evidence_grade"]["TITLEPDF01"] == sa.GRADE_TITLE
    delta = _delta(data, "GRIS", "TITLEPDF01")
    assert delta["effect"] == "HUMAN_QUEUE"      # sanity: correctly HUMAN_QUEUE by construction
    delta["effect"] = "ADD_INCLUIR"
    _dump_applied(spi_env["applied"], data)
    assert vsa.main() == 1


def test_wrong_title_only_exclusions_count_is_red(spi_env):
    """`counts.title_only_exclusions` must equal the MEASURED number of title-only ADD_EXCLUIR rows (1 in
    this fixture, TITLEEXCL01) -- a wrong number is rejected, not silently trusted."""
    assert sa.main(["--write"]) == 0
    assert vsa.main() == 0
    data = _load_applied(spi_env["applied"])
    assert data["counts"]["title_only_exclusions"] == 1
    data["counts"]["title_only_exclusions"] = 0
    _dump_applied(spi_env["applied"], data)
    assert vsa.main() == 1


def test_absent_title_only_exclusions_count_is_red(spi_env):
    """The count must be PUBLISHED, not merely derivable -- an APPLIED.json that omits
    `counts.title_only_exclusions` entirely is rejected exactly like a wrong one."""
    assert sa.main(["--write"]) == 0
    assert vsa.main() == 0
    data = _load_applied(spi_env["applied"])
    del data["counts"]["title_only_exclusions"]
    _dump_applied(spi_env["applied"], data)
    assert vsa.main() == 1
