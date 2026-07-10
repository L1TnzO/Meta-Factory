"""H6 zero-LLM gates for the E2 (WEPGCOMP/+Lugar) oracle loader and the E3
(ReqElicitBench) adapter/sampler. Everything here runs without a network call so a green
live E2/E3 run is trustworthy; the machinery AROUND the LLM is pinned by construction.
"""

from __future__ import annotations

import zipfile
from collections import Counter
from pathlib import Path

import pytest

from reqcouncil.eval import reqelicit, wepgcomp
from reqcouncil.eval.wepgcomp import MAISLUGAR, WEPGCOMP, load_oracle
from reqcouncil.ingest import chunk_turns, parse_transcript


# ---------------------------------------------------------------- E2 oracle loader

def test_oracle_counts_and_prefixes_match_measured_reality():
    """46/34 total, 40/6 and 24/10 FUNC/NOTF — the corrected counts, enforced."""
    for corpus, exp in wepgcomp.EXPECTED.items():
        items = load_oracle(corpus)
        n_nfr = sum(1 for it in items if it.is_nfr)
        assert (len(items), len(items) - n_nfr, n_nfr) == (exp["total"], exp["func"], exp["nfr"])
        assert all(it.id.startswith(("FUNC", "NOTF")) for it in items)
        assert all(it.is_nfr == it.id.startswith("NOTF") for it in items)


def test_oracle_wepgcomp_first_item_spot_check():
    first = load_oracle(WEPGCOMP)[0]
    assert first.id == "FUNC01"
    assert first.is_nfr is False
    assert "professores e doutorandos" in first.text  # Portuguese, per §4.5.2 validity note


def test_oracle_maislugar_nfr_present():
    nfrs = [it for it in load_oracle(MAISLUGAR) if it.is_nfr]
    assert len(nfrs) == 10
    assert nfrs[-1].id == "NOTF10"


def test_curated_transcripts_parse_and_chunk():
    """The H6 §0 curation is parseable by the strict H1 ingest and chunks 1:1 with turns."""
    for corpus, n_chunks in ((WEPGCOMP, 28), (MAISLUGAR, 113)):
        text = wepgcomp.transcript_path(corpus).read_text(encoding="utf-8")
        turns = parse_transcript(text)
        chunks = chunk_turns(turns)
        assert len(turns) == n_chunks and len(chunks) == n_chunks


def _write_min_xlsx(path: Path, rows: list[tuple[str, str]]) -> None:
    """Minimal single-sheet ('Oracle') xlsx with inline strings — no sharedStrings needed."""
    def cell(ref: str, val: str) -> str:
        return f'<c r="{ref}" t="inlineStr"><is><t>{val}</t></is></c>'

    sheet_rows = "".join(
        f'<row r="{i+1}">{cell(f"A{i+1}", rid)}{cell(f"B{i+1}", txt)}</row>'
        for i, (rid, txt) in enumerate([("ID", "Descrição"), *rows])
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{sheet_rows}</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Oracle" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    ct = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/xml"/></Types>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rIdWB" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)


def test_oracle_rejects_wrong_count(tmp_path):
    _write_min_xlsx(tmp_path / "Requisitos - WEPGCOMP.xlsx", [("FUNC01", "a"), ("NOTF01", "b")])
    with pytest.raises(ValueError, match="expected total=46"):
        load_oracle(WEPGCOMP, data_root=tmp_path)


def test_oracle_rejects_bad_prefix(tmp_path):
    rows = [("XYZ01", "bad prefix")] + [(f"FUNC{i:02d}", "x") for i in range(1, 46)]
    _write_min_xlsx(tmp_path / "Requisitos - WEPGCOMP.xlsx", rows)
    with pytest.raises(ValueError, match="unexpected id prefix"):
        load_oracle(WEPGCOMP, data_root=tmp_path)


# ------------------------------------------------------------ E3 adapter + sampler

def test_scenarios_join_is_the_measured_100():
    scenarios = reqelicit.load_scenarios()
    assert len(scenarios) == reqelicit.EXPECTED_SCENARIOS == 100
    s0 = scenarios[0]
    assert s0.task_id.startswith("task_")
    assert s0.application_type
    assert len(s0.golden_stories) >= 1
    # the 2 reused names must contribute DISTINCT scenarios (the correction's whole point)
    coaching = [s for s in scenarios if s.name == "Coaching Match and Session Management System"]
    assert len(coaching) == 2
    assert coaching[0].initial_requirements != coaching[1].initial_requirements


def test_render_round_trips_through_the_h1_parser():
    for scenario in reqelicit.load_scenarios()[:5]:
        text = reqelicit.render_transcript(scenario)
        turns = parse_transcript(text)
        got = [(t.speaker, t.text) for t in turns]
        assert got == reqelicit.expected_turns(scenario)


def test_hare_quota_hand_fixture():
    # a=4,b=3,c=3 total=10, 5 seats: shares 2.0/1.5/1.5 -> floors 2/1/1 (=4), one seat
    # to the largest remainder (.5 tie -> name order picks "b").
    quota = reqelicit._hare_quota({"a": 4, "b": 3, "c": 3}, 5)
    assert quota == {"a": 2, "b": 2, "c": 1} and sum(quota.values()) == 5


def test_sample_is_proportional_and_deterministic():
    scenarios = reqelicit.load_scenarios()
    counts = Counter(s.application_type for s in scenarios)
    expected_quota = reqelicit._hare_quota(dict(counts), 20)

    chosen = reqelicit.sample(scenarios, 20, seed=13)
    assert len(chosen) == 20
    assert Counter(s.application_type for s in chosen) == expected_quota
    assert expected_quota["Showcase Websites"] == 4 and expected_quota["Dashboards"] == 1
    # deterministic: same inputs -> byte-identical selection
    again = reqelicit.sample(scenarios, 20, seed=999)
    assert [s.task_id for s in chosen] == [s.task_id for s in again]


def test_sample_refuses_oversampling():
    scenarios = reqelicit.load_scenarios()
    with pytest.raises(ValueError, match="cannot sample"):
        reqelicit.sample(scenarios, len(scenarios) + 1)
