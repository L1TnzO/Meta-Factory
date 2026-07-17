"""Offline tests for the SMS-v2 snowballing round-1 tools (v1_candidates.py +
snowball.py). NO network access anywhere: v1_candidates.py never touches the
network by construction, and every snowball.py test below exercises PURE
logic functions imported directly (never the network-fetching subcommands).

Section (1) real-data invariants pin v1_candidates.py's join logic against
the COMMITTED corpus/sheet/bib — these numbers are measured facts about that
data, not assumptions (see the module docstrings for why DOI alone is not a
match signal). Section (2) exercises snowball.py's pure logic against small
synthetic fixtures.

All paths are computed relative to this file's own location (never cwd)."""

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

BIB = REPO_ROOT / "research/corpus/seeds/v1-references.bib"
CORPUS = REPO_ROOT / "research/corpus/merged/corpus.jsonl"
SHEET = REPO_ROOT / "research/corpus/screening/screening_full.csv"

sys.path.insert(0, str(HERE))
import v1_candidates  # noqa: E402
import snowball  # noqa: E402


# --------------------------------------------------------------------------
# (1) REAL-DATA invariants — v1_candidates.py
# --------------------------------------------------------------------------

def _run_v1_candidates(tmp_path):
    out = tmp_path / "v1_candidates.csv"
    rc = v1_candidates.main([
        "--bib", str(BIB), "--corpus", str(CORPUS), "--sheet", str(SHEET), "--out", str(out),
    ])
    assert rc == 0
    with out.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return rows


def test_v1_candidates_counts(tmp_path):
    rows = _run_v1_candidates(tmp_path)
    assert len(rows) == 27

    decidido = [r for r in rows if r["status"] == "DECIDIDO-V2"]
    candidato = [r for r in rows if r["status"] == "CANDIDATO"]
    assert len(decidido) == 16
    assert len(candidato) == 11

    incluir = [r for r in decidido if r["v2_decision"] == "INCLUIR"]
    gris = [r for r in decidido if r["v2_decision"] == "GRIS"]
    assert len(incluir) == 15
    assert len(gris) == 1


def test_v1_candidates_sort_order(tmp_path):
    rows = _run_v1_candidates(tmp_path)
    statuses = [r["status"] for r in rows]
    # DECIDIDO-V2 block first, then CANDIDATO
    assert statuses == sorted(statuses, key=lambda s: 0 if s == "DECIDIDO-V2" else 1)
    decidido_keys = [r["bibkey"] for r in rows if r["status"] == "DECIDIDO-V2"]
    candidato_keys = [r["bibkey"] for r in rows if r["status"] == "CANDIDATO"]
    assert decidido_keys == sorted(decidido_keys)
    assert candidato_keys == sorted(candidato_keys)


def test_v1_candidates_specific_rows(tmp_path):
    rows = {r["bibkey"]: r for r in _run_v1_candidates(tmp_path)}
    assert rows["prometheus2026"]["v2_decision"] == "GRIS"
    assert rows["prometheus2026"]["status"] == "DECIDIDO-V2"
    assert rows["contextweaver2026"]["status"] == "CANDIDATO"
    assert rows["aesp2026"]["status"] == "CANDIDATO"
    assert rows["clawvm2026"]["status"] == "CANDIDATO"
    # method-only entries are never in the output
    assert "petersen2008sms" not in rows
    assert "petersen2015sms" not in rows
    assert "kitchenham2007guidelines" not in rows


def test_v1_candidates_columns_exact(tmp_path):
    out = tmp_path / "v1_candidates.csv"
    v1_candidates.main([
        "--bib", str(BIB), "--corpus", str(CORPUS), "--sheet", str(SHEET), "--out", str(out),
    ])
    header = out.read_text(encoding="utf-8").splitlines()[0]
    assert header == "bibkey,title,year,arxiv_id,doi,url,in_corpus_key,v2_decision,status"


def test_v1_candidates_strips_braces():
    entries = v1_candidates.parse_bib(BIB.read_text(encoding="utf-8"))
    fields = dict(entries)["experepair2026"]
    title = v1_candidates.strip_braces(fields["title"])
    assert "{" not in title and "}" not in title
    assert "EXPEREPAIR" in title


# --------------------------------------------------------------------------
# (2) synthetic-fixture tests — snowball.py pure logic
# --------------------------------------------------------------------------

def test_reconstruct_abstract_basic():
    assert snowball.reconstruct_abstract({"Hello": [0], "world": [1]}) == "Hello world"


def test_reconstruct_abstract_out_of_order_and_repeats():
    idx = {"the": [0, 4], "quick": [1], "fox": [3], "brown": [2]}
    assert snowball.reconstruct_abstract(idx) == "the quick brown fox the"


def test_reconstruct_abstract_empty():
    assert snowball.reconstruct_abstract({}) == ""
    assert snowball.reconstruct_abstract(None) == ""


def test_atomic_write_text_no_tmp_file_left(tmp_path):
    target = tmp_path / "out.txt"
    snowball.atomic_write_text(target, "hello world")
    assert target.read_text(encoding="utf-8") == "hello world"
    leftovers = list(tmp_path.glob(".*.tmp"))
    assert leftovers == []


def test_atomic_write_csv_roundtrip(tmp_path):
    target = tmp_path / "out.csv"
    rows = [{"a": "1", "b": "x"}, {"a": "2", "b": "y"}]
    snowball.atomic_write_csv(target, ["a", "b"], rows)
    assert list(tmp_path.glob(".*.tmp")) == []
    with target.open(newline="", encoding="utf-8") as fh:
        out_rows = list(csv.DictReader(fh))
    assert out_rows == rows


def test_atomic_write_jsonl_roundtrip(tmp_path):
    target = tmp_path / "out.jsonl"
    rows = [{"key": "W1"}, {"key": "W2"}]
    snowball.atomic_write_jsonl(target, rows)
    assert list(tmp_path.glob(".*.tmp")) == []
    lines = [json.loads(ln) for ln in target.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines == rows


def _synthetic_corpus():
    return [
        {
            "id": "https://openalex.org/W1000",
            "doi": "10.1000/known-doi",
            "arxiv_id": "2401.00001v2",
            "title": "A Known Memory Paper About Agents",
        },
    ]


def test_candidate_dedup_excludes_by_wid():
    corpus_set = snowball.build_corpus_identity_set(_synthetic_corpus())
    identities = snowball.candidate_identities(wid="W1000", doi="10.9999/other", title="Totally Different")
    assert snowball.is_excluded(identities, corpus_set)


def test_candidate_dedup_excludes_by_doi():
    corpus_set = snowball.build_corpus_identity_set(_synthetic_corpus())
    identities = snowball.candidate_identities(wid="W2000", doi="10.1000/KNOWN-DOI", title="Totally Different")
    assert snowball.is_excluded(identities, corpus_set)


def test_candidate_dedup_excludes_by_arxiv():
    corpus_set = snowball.build_corpus_identity_set(_synthetic_corpus())
    identities = snowball.candidate_identities(wid="W3000", doi="10.9999/other", arxiv_id="2401.00001v5")
    assert snowball.is_excluded(identities, corpus_set)


def test_candidate_dedup_excludes_by_normalized_title():
    corpus_set = snowball.build_corpus_identity_set(_synthetic_corpus())
    identities = snowball.candidate_identities(
        wid="W4000", doi="10.9999/other", title="  A Known Memory Paper, About Agents!!  "
    )
    assert snowball.is_excluded(identities, corpus_set)


def test_candidate_not_excluded_when_genuinely_new():
    corpus_set = snowball.build_corpus_identity_set(_synthetic_corpus())
    identities = snowball.candidate_identities(wid="W5000", doi="10.5555/new", title="A Brand New Paper")
    assert not snowball.is_excluded(identities, corpus_set)


def test_aggregate_candidates_indegree_and_sort_order():
    corpus = _synthetic_corpus()
    backward_rows = [
        {"seed": "seedA", "wid": "W1", "referenced_works": [
            "https://openalex.org/W900", "https://openalex.org/W901",
        ]},
        {"seed": "seedB", "wid": "W2", "referenced_works": [
            "https://openalex.org/W900",
        ]},
    ]
    forward_rows = [
        {"seed": "seedA", "wid": "W1", "citing": [
            {"id": "https://openalex.org/W900", "doi": "10.7/w900", "title": "W900 title", "publication_year": 2024},
        ]},
        {"seed": "seedC", "wid": "W3", "citing": [
            {"id": "https://openalex.org/W900"},
            {"id": "https://openalex.org/W902"},
        ]},
    ]
    rows = snowball.aggregate_candidates(corpus, backward_rows, forward_rows)
    by_wid = {r["wid"]: r for r in rows}

    # W900: backward from seedA+seedB (2 distinct), forward from seedA+seedC (2 distinct) -> total 4
    assert by_wid["W900"]["backward_n"] == 2
    assert by_wid["W900"]["forward_n"] == 2
    assert by_wid["W900"]["total"] == 4
    assert by_wid["W900"]["doi"] == "10.7/w900"
    assert by_wid["W900"]["title"] == "W900 title"

    # W901: backward-only from seedA -> total 1, no metadata yet (enrich fills it later)
    assert by_wid["W901"]["backward_n"] == 1
    assert by_wid["W901"]["forward_n"] == 0
    assert by_wid["W901"]["total"] == 1
    assert by_wid["W901"]["doi"] == ""
    assert by_wid["W901"]["title"] == ""

    # W902: forward-only from seedC -> total 1
    assert by_wid["W902"]["total"] == 1

    # sort order: total desc, then wid asc
    assert [r["wid"] for r in rows] == ["W900", "W901", "W902"]


def test_aggregate_candidates_excludes_in_corpus_wid():
    corpus = [{
        "id": "https://openalex.org/W900", "doi": "", "arxiv_id": "", "title": "Already Known",
    }]
    backward_rows = [{"seed": "seedA", "wid": "W1", "referenced_works": ["https://openalex.org/W900"]}]
    rows = snowball.aggregate_candidates(corpus, backward_rows, [])
    assert rows == []


def test_seeds_join_incluir_plus_gold():
    corpus = [
        {"id": "https://openalex.org/W10", "doi": "10.1/a", "arxiv_id": "2401.00001",
         "title": "Included Paper One"},
        {"id": "https://openalex.org/W11", "doi": "10.1/b", "arxiv_id": "",
         "title": "Included Paper Two"},
        {"id": "https://openalex.org/W12", "doi": "10.1/c", "arxiv_id": "",
         "title": "Excluded Paper"},
    ]
    sheet = [
        {"key": snowball.record_key(corpus[0]), "decision": "INCLUIR"},
        {"key": snowball.record_key(corpus[1]), "decision": "INCLUIR"},
        {"key": snowball.record_key(corpus[2]), "decision": "EXCLUIR-CE1"},
    ]
    gold = {"Fixture Work": (r"fixture", "2402.00002", "test fixture")}

    rows = snowball.build_seed_rows(corpus, sheet, gold)
    origins = [r["origin"] for r in rows]
    assert origins.count("included") == 2
    assert origins.count("gold") == 1
    assert len(rows) == 3

    included = {r["seed_key"]: r for r in rows if r["origin"] == "included"}
    assert included[snowball.record_key(corpus[0])]["openalex_id"] == "W10"
    assert included[snowball.record_key(corpus[0])]["arxiv_id"] == "2401.00001"

    gold_row = next(r for r in rows if r["origin"] == "gold")
    assert gold_row["seed_key"] == "2402.00002"
    assert gold_row["arxiv_id"] == "2402.00002"
    assert gold_row["openalex_id"] == ""


def test_seeds_join_real_gold_has_12_entries():
    # sanity: the real GOLD dict imported from sanity_check_gold.py has 12 works (protocol §7.3)
    assert len(snowball.GOLD) == 12


def test_extract_wid_and_normalize_helpers():
    assert snowball.extract_wid("https://openalex.org/W123") == "W123"
    assert snowball.extract_wid("http://arxiv.org/abs/2401.00001") == ""
    assert snowball.extract_wid("") == ""
    assert snowball.vstrip("2401.00001v3") == "2401.00001"
    assert snowball.vstrip("2401.00001") == "2401.00001"
    assert snowball.normalize_doi("https://doi.org/10.1/ABC") == "10.1/abc"
    assert snowball.normalize_title("  Hello, World!! ") == "hello world"


def test_no_network_calls_anywhere(monkeypatch):
    """Belt-and-suspenders: fail loudly if any test above ever reaches urlopen."""
    import urllib.request

    def _boom(*_a, **_k):
        raise AssertionError("network access attempted during offline test run")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    # re-run a couple of pure functions to prove they still don't touch the network
    assert snowball.reconstruct_abstract({"a": [0]}) == "a"
    corpus_set = snowball.build_corpus_identity_set(_synthetic_corpus())
    assert ("wid", "W1000") in corpus_set
