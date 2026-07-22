"""Offline tests for dup_scan.py (SMS-V2-PROTOCOL.md §7.1 dedup residual —
measured 2026-07-18: the DOI->arXiv->title-equality chain in merge_dedup.py
let 5 near-duplicate pairs through the 487 INCLUIR corpus, including one
title-EXTENSION pair (SNT-MEM) that byte-identical-title equality alone
cannot catch. NO network access anywhere and NEVER reads the real sheet —
every case runs against small synthetic fixtures / tmp_path CSVs.

All paths are computed relative to this file's own location (never cwd)."""

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dup_scan  # noqa: E402


# --------------------------------------------------------------------------
# normalize_title
# --------------------------------------------------------------------------

def test_normalize_title_lowercases():
    assert dup_scan.normalize_title("Hello World") == "hello world"


def test_normalize_title_collapses_punctuation():
    assert dup_scan.normalize_title("SNT-MEM: Operator-Structured!!") == "snt mem operator structured"


def test_normalize_title_collapses_whitespace_runs():
    assert dup_scan.normalize_title("A   Title\twith\nwhitespace") == "a title with whitespace"


def test_normalize_title_strips_leading_trailing():
    assert dup_scan.normalize_title("  Padded Title  ") == "padded title"


def test_normalize_title_empty_and_none():
    assert dup_scan.normalize_title("") == ""
    assert dup_scan.normalize_title(None) == ""


# --------------------------------------------------------------------------
# find_near_duplicates
# --------------------------------------------------------------------------

def _rec(key, title, year="2024", source="openalex"):
    return {"key": key, "title": title, "year": year, "source": source}


def test_finds_identico_pair():
    records = [
        _rec("W1", "Memory Management Framework"),
        _rec("W2", "Memory Management Framework"),
    ]
    pairs = dup_scan.find_near_duplicates(records)
    assert len(pairs) == 1
    p = pairs[0]
    assert p["kind"] == "IDENTICO"
    assert p["key_a"] == "W1" and p["key_b"] == "W2"
    assert p["similarity"] == 1.0
    assert p["title_a"] == "Memory Management Framework"
    assert p["title_b"] == "Memory Management Framework"


def test_finds_snt_mem_prefijo_regression_case():
    # Real regression: extension title must be typed PREFIJO regardless of
    # the SequenceMatcher ratio (the equality rule alone cannot catch it).
    records = [
        _rec("W7147524247", "SNT-MEM: Operator-Structured Memory Management Framework For Self-Regulating AI Systems"),
        _rec("W7141308334", "SNT-MEM: Operator-Structured Memory Management Framework"),
    ]
    pairs = dup_scan.find_near_duplicates(records)
    assert len(pairs) == 1
    p = pairs[0]
    assert p["kind"] == "PREFIJO"
    assert p["key_a"] == "W7141308334" and p["key_b"] == "W7147524247"


def test_finds_similar_pair_above_threshold():
    # differ by one mid-title word (large/big): no prefix relation, exercises ratio path.
    records = [
        _rec("A1", "Agentic Memory Systems for Large Language Models"),
        _rec("A2", "Agentic Memory Systems for Big Language Models"),
    ]
    pairs = dup_scan.find_near_duplicates(records, threshold=0.85)
    assert len(pairs) == 1
    p = pairs[0]
    assert p["kind"] == "SIMILAR"
    assert p["similarity"] >= 0.85
    assert p["key_a"] == "A1" and p["key_b"] == "A2"


def test_does_not_report_unrelated_titles():
    records = [
        _rec("B1", "Retrieval Augmented Generation for Question Answering"),
        _rec("B2", "Continual Learning in Robotics Control Systems"),
    ]
    assert dup_scan.find_near_duplicates(records) == []


def test_pair_reported_exactly_once_key_order_normalized():
    # higher key appears first positionally; output must still normalize
    # to key_a < key_b and report the pair once.
    records = [
        _rec("Z9", "Duplicate Title Case"),
        _rec("A1", "Duplicate Title Case"),
    ]
    pairs = dup_scan.find_near_duplicates(records)
    assert len(pairs) == 1
    assert pairs[0]["key_a"] == "A1" and pairs[0]["key_b"] == "Z9"


def test_deterministic_ordering_kind_then_similarity_then_keys():
    records = [
        _rec("S1", "Alpha Beta Gamma Delta Epsilon"),
        _rec("S2", "Alpha Beta Gamma Delta Zeta"),
        _rec("I1", "Constant Duplicate Title"),
        _rec("I2", "Constant Duplicate Title"),
        _rec("P1", "Constant Duplicate Title Extended"),
    ]
    pairs = dup_scan.find_near_duplicates(records, threshold=0.5)
    kinds = [p["kind"] for p in pairs]
    assert kinds == sorted(kinds, key=lambda k: dup_scan._KIND_RANK[k])
    assert kinds[0] == "IDENTICO" and "PREFIJO" in kinds and "SIMILAR" in kinds
    # re-running must yield the exact same order (no set-iteration flakiness)
    assert pairs == dup_scan.find_near_duplicates(records, threshold=0.5)


def test_no_self_pair_for_single_record():
    assert dup_scan.find_near_duplicates([_rec("W1", "Solo Title")]) == []


def test_empty_titles_never_match():
    records = [_rec("E1", ""), _rec("E2", ""), _rec("E3", None)]
    assert dup_scan.find_near_duplicates(records) == []


# --------------------------------------------------------------------------
# scan subcommand — fixture sheet only, NEVER the real corpus
# --------------------------------------------------------------------------

SHEET_HEADER = ["key", "source", "year", "title"]


def _write_fixture_sheet(path, rows):
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=SHEET_HEADER)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_scan_subcommand_writes_exact_header_and_rows(tmp_path):
    sheet = tmp_path / "fixture_sheet.csv"
    out = tmp_path / "queues" / "DUPLICADOS-INCLUIDOS.csv"
    _write_fixture_sheet(sheet, [
        {"key": "W1", "source": "openalex", "year": "2023", "title": "Memory Management Framework"},
        {"key": "W2", "source": "arxiv", "year": "2024", "title": "Memory Management Framework"},
        {"key": "W3", "source": "openalex", "year": "2022", "title": "Totally Unrelated Robotics Paper"},
    ])

    rc = dup_scan.main(["scan", "--sheet", str(sheet), "--out", str(out)])
    assert rc == 0
    assert out.exists()

    with out.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == dup_scan.QUEUE_COLUMNS
        rows = list(reader)

    assert len(rows) == 1
    row = rows[0]
    assert row["key_a"] == "W1" and row["key_b"] == "W2"
    assert row["kind"] == "IDENTICO"
    assert row["year_a"] == "2023" and row["year_b"] == "2024"
    assert row["source_a"] == "openalex" and row["source_b"] == "arxiv"
    assert row["title_a"] == "Memory Management Framework"
    assert row["title_b"] == "Memory Management Framework"


def test_scan_subcommand_no_duplicates_writes_header_only(tmp_path):
    sheet = tmp_path / "fixture_sheet.csv"
    out = tmp_path / "DUPLICADOS-INCLUIDOS.csv"
    _write_fixture_sheet(sheet, [
        {"key": "W1", "source": "openalex", "year": "2023", "title": "Robotics Control Loop Design"},
        {"key": "W2", "source": "arxiv", "year": "2024", "title": "Entirely Different Subject Matter"},
    ])
    rc = dup_scan.main(["scan", "--sheet", str(sheet), "--out", str(out)])
    assert rc == 0
    with out.open(newline="", encoding="utf-8") as fh:
        assert list(csv.DictReader(fh)) == []


def test_scan_subcommand_respects_threshold_flag(tmp_path):
    # same pair as test_finds_similar_pair_above_threshold, but a stricter
    # --threshold pushes it below the SIMILAR cutoff -> queue stays empty.
    sheet = tmp_path / "fixture_sheet.csv"
    out = tmp_path / "DUPLICADOS-INCLUIDOS.csv"
    _write_fixture_sheet(sheet, [
        {"key": "W1", "source": "openalex", "year": "2023", "title": "Agentic Memory Systems for Large Language Models"},
        {"key": "W2", "source": "arxiv", "year": "2024", "title": "Agentic Memory Systems for Big Language Models"},
    ])
    rc = dup_scan.main(["scan", "--sheet", str(sheet), "--out", str(out), "--threshold", "0.99"])
    assert rc == 0
    with out.open(newline="", encoding="utf-8") as fh:
        assert list(csv.DictReader(fh)) == []


def test_no_network_calls_anywhere(monkeypatch):
    """Belt-and-suspenders: fail loudly if this module ever reaches urlopen."""
    import urllib.request

    def _boom(*_a, **_k):
        raise AssertionError("network access attempted during offline test run")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    assert dup_scan.normalize_title("Still Works") == "still works"
    assert dup_scan.find_near_duplicates([_rec("A", "x"), _rec("B", "x")])[0]["kind"] == "IDENTICO"
