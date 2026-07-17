"""Offline pytest for research/harvest/snowball_screen.py — the screening
driver for SMS-v2 snowball candidates. NO network access anywhere (the module
itself never imports urllib).

Sections (1)-(5) exercise the driver against SYNTHETIC fixtures written to
tmp_path, with the module's path constants monkeypatched so no test ever
touches the real committed corpus. Section (6) is the real-data invariant:
`build --dry-run` against the COMMITTED CANDIDATES/ENRICHED/V1SCREEN/V1VERDICT
files must report the measured totals (1126 = 1117 candidates + 9 v1, v1
pre-merged == 9) and must not write anything.

All paths are computed relative to this file's own location (never cwd)."""

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import snowball_screen  # noqa: E402

VERDICT_HEADER = ["key", "M", "T", "E", "F", "se", "selfpub", "artefacto", "decision", "notes"]
CANDIDATE_HEADER = ["wid", "doi", "year", "title", "backward_n", "forward_n", "total", "seeds_sample"]

MERGE_LINE_RE = re.compile(
    r"merged=(\d+) skipped\(already-decided\)=(\d+) rejected=(\d+)"
)


# --------------------------------------------------------------------------
# Shared synthetic fixture
# --------------------------------------------------------------------------
#
# 7 candidate rows (SKEY100/008/200/300/001/013/999) + 1 v1 row (SKEY010):
#   SKEY100  "Memory System Alpha"        total=5  year=2023  -> dup KEEP
#   SKEY008  "Memory System, Alpha!!"     total=3  year=2023  -> DUPLICADO-INTRA
#   SKEY200  "An Old Scope Paper"         total=1  year=2021  -> FUERA-ALCANCE
#   SKEY300  ""                           total=2  year=""    -> SIN-METADATOS
#   SKEY001  "Fresh Model Paper A"        total=8  year=2024  -> pending
#   SKEY013  "Fresh Model Paper B"        total=6  year=2022  -> pending
#   SKEY999  "Gold Six" (gold-manual)     total=0  year=2024  -> pending
#   SKEY010  v1 record, pre-merged INCLUIR from V1VERDICT
#
# sha256(key)%10 == 0 ("sample hit"): SKEY008, SKEY010, SKEY013.
# sha256(key)%10 != 0 ("sample miss"): SKEY100, SKEY001, SKEY999, SKEY200, SKEY300.
# SKEY008 is a pre-decision row and SKEY010 is v1-origin: both are sample
# HITS that must still be EXCLUDED from SAMPLE10 — the decisive part of the
# queues test is that only SKEY013 (a genuine model decision + sample hit)
# survives both exclusion rules.

def _write_fixture(tmp_path, monkeypatch):
    candidates = tmp_path / "candidates.csv"
    enriched = tmp_path / "enriched.jsonl"
    v1screen = tmp_path / "v1-screen.jsonl"
    v1verdict = tmp_path / "v1-verdict.csv"
    sheet = tmp_path / "screening_snowball.csv"
    batches = tmp_path / "batches" / "SNOWBALL"
    queues = tmp_path / "queues"

    with candidates.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CANDIDATE_HEADER)
        w.writeheader()
        w.writerows([
            {"wid": "SKEY100", "doi": "https://doi.org/10.1/skey100", "year": "2023",
             "title": "Memory System Alpha", "backward_n": "1", "forward_n": "4",
             "total": "5", "seeds_sample": ""},
            {"wid": "SKEY008", "doi": "https://doi.org/10.1/skey008", "year": "2023",
             "title": "Memory System, Alpha!!", "backward_n": "1", "forward_n": "2",
             "total": "3", "seeds_sample": ""},
            {"wid": "SKEY200", "doi": "https://doi.org/10.1/skey200", "year": "2021",
             "title": "An Old Scope Paper", "backward_n": "0", "forward_n": "1",
             "total": "1", "seeds_sample": ""},
            {"wid": "SKEY300", "doi": "", "year": "", "title": "",
             "backward_n": "1", "forward_n": "1", "total": "2", "seeds_sample": ""},
            {"wid": "SKEY001", "doi": "https://doi.org/10.1/skey001", "year": "2024",
             "title": "Fresh Model Paper A", "backward_n": "3", "forward_n": "5",
             "total": "8", "seeds_sample": ""},
            {"wid": "SKEY013", "doi": "https://doi.org/10.1/skey013", "year": "2022",
             "title": "Fresh Model Paper B", "backward_n": "2", "forward_n": "4",
             "total": "6", "seeds_sample": ""},
            {"wid": "SKEY999", "doi": "https://doi.org/10.1/skey999", "year": "2024",
             "title": "Gold Six", "backward_n": "0", "forward_n": "0",
             "total": "0", "seeds_sample": "gold-manual:2401.00099"},
        ])

    long_abstract_a = "Alpha memory retrieval sentence. " * 15   # > 400 chars
    long_abstract_b = "Bravo memory retrieval sentence. " * 15   # > 400 chars
    assert len(long_abstract_a) > 400 and len(long_abstract_b) > 400

    enriched_recs = [
        {"key": "SKEY100", "title": "Memory System Alpha", "doi": "https://doi.org/10.1/skey100",
         "year": 2023, "abstract": "Short abstract for the kept duplicate row."},
        {"key": "SKEY008", "title": "Memory System, Alpha!!", "doi": "https://doi.org/10.1/skey008",
         "year": 2023, "abstract": "Short abstract for the dropped duplicate row."},
        {"key": "SKEY200", "title": "An Old Scope Paper", "doi": "https://doi.org/10.1/skey200",
         "year": 2021, "abstract": "Short abstract, out of scope by year."},
        {"key": "SKEY001", "title": "Fresh Model Paper A", "doi": "https://doi.org/10.1/skey001",
         "year": 2024, "abstract": long_abstract_a},
        {"key": "SKEY013", "title": "Fresh Model Paper B", "doi": "https://doi.org/10.1/skey013",
         "year": 2022, "abstract": long_abstract_b},
        {"key": "SKEY999", "title": "Gold Six", "doi": "https://doi.org/10.1/skey999",
         "year": 2024, "abstract": "Short abstract for the gold-manual row."},
        # SKEY300 intentionally absent -> enrich miss -> no title AND no abstract.
    ]
    with enriched.open("w", encoding="utf-8") as fh:
        for rec in enriched_recs:
            fh.write(json.dumps(rec) + "\n")

    with v1screen.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "key": "SKEY010", "source": "arxiv", "title": "V1 Sample Paper",
            "year": "2026", "abstract": "V1 full abstract text, proves full-text slicing. " * 5,
        }) + "\n")

    with v1verdict.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=VERDICT_HEADER)
        w.writeheader()
        w.writerow({"key": "SKEY010", "M": "3", "T": "1", "E": "1", "F": "",
                    "se": "0", "selfpub": "0", "artefacto": "0",
                    "decision": "INCLUIR", "notes": "valid v1 premerge test"})

    monkeypatch.setattr(snowball_screen, "CANDIDATES", candidates)
    monkeypatch.setattr(snowball_screen, "ENRICHED", enriched)
    monkeypatch.setattr(snowball_screen, "V1SCREEN", v1screen)
    monkeypatch.setattr(snowball_screen, "V1VERDICT", v1verdict)
    monkeypatch.setattr(snowball_screen, "SHEET", sheet)
    monkeypatch.setattr(snowball_screen, "BATCHES", batches)
    monkeypatch.setattr(snowball_screen, "QUEUES", queues)

    return {
        "sheet": sheet, "batches": batches, "queues": queues,
        "long_abstract_a": long_abstract_a, "long_abstract_b": long_abstract_b,
    }


# --------------------------------------------------------------------------
# (1) build: pre-decisions + v1 premerge
# --------------------------------------------------------------------------

def test_build_pre_decisions_and_v1_premerge(tmp_path, monkeypatch):
    _write_fixture(tmp_path, monkeypatch)
    rows, v1_premerged = snowball_screen.build_rows()
    assert v1_premerged == 1
    by_key = {r["key"]: r for r in rows}

    # intra-candidate duplicate: keeps the higher total.
    assert by_key["SKEY100"]["decision"] == ""
    assert by_key["SKEY008"]["decision"] == "DUPLICADO-INTRA"
    assert by_key["SKEY008"]["notes"] == "duplicado de SKEY100"

    # out-of-scope year.
    assert by_key["SKEY200"]["decision"] == "FUERA-ALCANCE"
    assert "2022" in by_key["SKEY200"]["notes"]

    # no title AND no abstract (enrich miss).
    assert by_key["SKEY300"]["decision"] == "SIN-METADATOS"

    # v1 pre-merge, re-validated with the REAL screening_pass.validate_row.
    v1row = by_key["SKEY010"]
    assert v1row["origin"] == "v1"
    assert v1row["decision"] == "INCLUIR"
    assert (v1row["M"], v1row["T"], v1row["E"]) == ("3", "1", "1")
    assert v1row["notes"] == "valid v1 premerge test"

    # origin tagging.
    assert by_key["SKEY999"]["origin"] == "gold-manual"
    assert by_key["SKEY001"]["origin"] == "snowball"

    pending_keys = {r["key"] for r in rows if not r["decision"]}
    assert pending_keys == {"SKEY100", "SKEY001", "SKEY013", "SKEY999"}
    assert len(rows) == 8


# --------------------------------------------------------------------------
# (2) build: overwrite guard
# --------------------------------------------------------------------------

def test_build_refuses_overwrite_without_force(tmp_path, monkeypatch):
    paths = _write_fixture(tmp_path, monkeypatch)

    rc = snowball_screen.cmd_build()
    assert rc == 0
    assert paths["sheet"].exists()

    # the just-written sheet already has non-empty decisions (pre-decisions +
    # v1 premerge) -> a second build without --force must refuse.
    rc2 = snowball_screen.cmd_build()
    assert rc2 == 2

    rc3 = snowball_screen.cmd_build(force=True)
    assert rc3 == 0


# --------------------------------------------------------------------------
# (3) slice: full abstract, correct fields, stable chunking
# --------------------------------------------------------------------------

def test_slice_full_abstract_and_stable_chunking(tmp_path, monkeypatch):
    paths = _write_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(snowball_screen, "CHUNK_SIZE", 2)
    snowball_screen.cmd_build()

    rc = snowball_screen.cmd_slice()
    assert rc == 0

    c00 = paths["batches"] / "c00.input.jsonl"
    c01 = paths["batches"] / "c01.input.jsonl"
    assert c00.exists() and c01.exists()
    assert not (paths["batches"] / "c02.input.jsonl").exists()

    recs0 = [json.loads(ln) for ln in c00.read_text(encoding="utf-8").splitlines()]
    recs1 = [json.loads(ln) for ln in c01.read_text(encoding="utf-8").splitlines()]
    by_key = {r["key"]: r for r in recs0 + recs1}
    assert set(by_key) == {"SKEY001", "SKEY013", "SKEY100", "SKEY999"}

    # total desc: SKEY001(8) > SKEY013(6) > SKEY100(5) > SKEY999(0).
    assert [r["key"] for r in recs0] == ["SKEY001", "SKEY013"]
    assert [r["key"] for r in recs1] == ["SKEY100", "SKEY999"]

    # FULL abstract (not the 400-char sheet cut).
    assert by_key["SKEY001"]["abstract"] == paths["long_abstract_a"]
    assert len(by_key["SKEY001"]["abstract"]) > 400
    assert by_key["SKEY013"]["abstract"] == paths["long_abstract_b"]

    rec = by_key["SKEY001"]
    assert rec["title"] == "Fresh Model Paper A"
    assert rec["year"] == "2024"
    assert rec["venue"] == ""
    assert rec["sources"] == "snowball"
    assert rec["has_pdf"] == 0
    assert rec["pdf"] == ""
    assert by_key["SKEY999"]["sources"] == "gold-manual"

    # do not rewrite an existing chunk file.
    c00.write_text("SENTINEL\n", encoding="utf-8")
    rc2 = snowball_screen.cmd_slice()
    assert rc2 == 0
    assert c00.read_text(encoding="utf-8") == "SENTINEL\n"


# --------------------------------------------------------------------------
# (4) merge: idempotent, rejects arithmetically invalid rows
# --------------------------------------------------------------------------

def test_merge_idempotent_and_rejects_invalid(tmp_path, monkeypatch, capsys):
    _write_fixture(tmp_path, monkeypatch)
    snowball_screen.cmd_build()

    verdict_path = tmp_path / "manual.verdict.csv"
    with verdict_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=VERDICT_HEADER)
        w.writeheader()
        w.writerow({"key": "SKEY001", "M": "3", "T": "1", "E": "1", "F": "",
                    "se": "0", "selfpub": "0", "artefacto": "0",
                    "decision": "INCLUIR", "notes": "valid merge test"})
        # INCLUIR requires M+T+E>=4; 1+1+1=3 fails the threshold.
        w.writerow({"key": "SKEY100", "M": "1", "T": "1", "E": "1", "F": "",
                    "se": "0", "selfpub": "0", "artefacto": "0",
                    "decision": "INCLUIR", "notes": "invalid merge test"})

    rc = snowball_screen.cmd_merge([str(verdict_path)])
    out = capsys.readouterr().out
    m = MERGE_LINE_RE.search(out)
    assert m is not None
    assert (m.group(1), m.group(2), m.group(3)) == ("1", "0", "1")  # merged/skipped/rejected
    assert rc == 1  # non-zero because something was rejected

    rows = {r["key"]: r for r in snowball_screen.read_sheet()}
    assert rows["SKEY001"]["decision"] == "INCLUIR"
    assert rows["SKEY001"]["notes"] == "valid merge test"
    assert rows["SKEY100"]["decision"] == ""  # rejected -> untouched

    # second merge of the SAME verdict file: the valid row is now
    # already-decided -> skipped (idempotent); the invalid row is still
    # undecided -> re-validated -> rejected again.
    rc2 = snowball_screen.cmd_merge([str(verdict_path)])
    out2 = capsys.readouterr().out
    m2 = MERGE_LINE_RE.search(out2)
    assert m2 is not None
    assert (m2.group(1), m2.group(2), m2.group(3)) == ("0", "1", "1")
    assert rc2 == 1

    rows2 = {r["key"]: r for r in snowball_screen.read_sheet()}
    assert rows2["SKEY001"]["decision"] == "INCLUIR"
    assert rows2["SKEY100"]["decision"] == ""


# --------------------------------------------------------------------------
# (5) queues: GRIS/CE-4p queue + deterministic 10% sample
# --------------------------------------------------------------------------

def test_queues_gris_and_deterministic_sample10(tmp_path, monkeypatch):
    paths = _write_fixture(tmp_path, monkeypatch)
    snowball_screen.cmd_build()

    rows = snowball_screen.read_sheet()
    by_key = {r["key"]: r for r in rows}
    by_key["SKEY100"]["decision"] = "CE-4p"
    by_key["SKEY100"]["notes"] = "manual CE-4p for queues test"
    by_key["SKEY001"]["decision"] = "INCLUIR"
    by_key["SKEY001"]["notes"] = "manual include for queues test"
    by_key["SKEY013"]["decision"] = "GRIS"
    by_key["SKEY013"]["notes"] = "manual gris for queues test"
    snowball_screen.write_sheet(rows)

    rc = snowball_screen.cmd_queues(quiet=True)
    assert rc == 0

    gris_path = paths["queues"] / "SNOWBALL-GRIS.csv"
    sample_path = paths["queues"] / "SNOWBALL-SAMPLE10.csv"

    with gris_path.open(newline="", encoding="utf-8") as fh:
        gris_keys = {r["key"] for r in csv.DictReader(fh)}
    with sample_path.open(newline="", encoding="utf-8") as fh:
        sample_keys = {r["key"] for r in csv.DictReader(fh)}

    assert gris_keys == {"SKEY100", "SKEY013"}
    # SKEY008 (DUPLICADO-INTRA) and SKEY010 (v1-origin, INCLUIR) both hash to
    # a sample "hit" but must be excluded by the pre-decision/v1-origin
    # rules; SKEY013 is the only genuinely model-decided sample hit.
    assert sample_keys == {"SKEY013"}

    before_sample = sample_path.read_bytes()
    before_gris = gris_path.read_bytes()
    snowball_screen.cmd_queues(quiet=True)
    assert sample_path.read_bytes() == before_sample
    assert gris_path.read_bytes() == before_gris


# --------------------------------------------------------------------------
# pure-helper coverage
# --------------------------------------------------------------------------

def test_normalize_title_and_abstract_400():
    assert snowball_screen.normalize_title("  Memory, System!! Alpha  ") == "memory system alpha"
    assert snowball_screen.normalize_title("") == ""
    assert snowball_screen.normalize_title(None) == ""

    text = "line one\nline two\r\nline three"
    collapsed = snowball_screen.collapse_abstract_400(text)
    assert "\n" not in collapsed and "\r" not in collapsed
    assert collapsed == "line one line two line three"

    long_text = "x" * 500
    assert len(snowball_screen.collapse_abstract_400(long_text)) == 400


# --------------------------------------------------------------------------
# (6) REAL-DATA invariant — against the committed corpus, no monkeypatch.
# --------------------------------------------------------------------------

def test_real_data_invariant_dry_run():
    assert not snowball_screen.SHEET.exists()
    rows, v1_premerged = snowball_screen.build_rows()
    assert len(rows) == 1126  # 1117 candidates + 9 v1 (measured, committed data)
    assert v1_premerged == 9

    rc = snowball_screen.cmd_build(dry_run=True)
    assert rc == 0
    assert not snowball_screen.SHEET.exists()  # dry-run must not write anything
