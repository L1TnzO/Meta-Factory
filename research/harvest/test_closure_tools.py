"""Offline tests for the SMS-v2 §9 CLOSURE toolkit: closure_law.py + make_spi_sheet.py + harvest_grey.py,
exercised against the REAL gates (verify_spi_verdicts.check_inputs, verify_grey.main) so a passing test
here means the artifacts a real run produces would actually satisfy the gates that judge them -- not a
reimplementation of the gate's own rules (a checker that only proves the happy path proves nothing).

NO network access anywhere: every seed fetch is faked via a monkeypatched harvest_grey._fetch, belt-and-
suspenders-checked by patching urllib.request.urlopen to explode. NEVER reads the real committed corpus:
closure_law's own source-sheet path constants are monkeypatched to small synthetic tmp_path fixtures for
every test that builds SPI inputs. All paths are computed relative to this file's own location, never cwd.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import closure_law  # noqa: E402
import make_spi_sheet as mss  # noqa: E402
import harvest_grey as hg  # noqa: E402
import verify_spi_verdicts as vsv  # noqa: E402
import verify_grey as vg  # noqa: E402


# ============================================================================
# shared helpers
# ============================================================================

def _keys_where(predicate, want: bool, count: int, prefix: str) -> list[str]:
    """The first `count` synthetic keys (prefix + zero-padded index) for which `predicate(key) is want`
    -- lets fixtures land rows in/out of the hash-sampled queues (MUESTRA-10PCT / SNOWBALL-SAMPLE10)
    deterministically, by using the LAW's own sampling functions instead of hardcoding magic keys."""
    found: list[str] = []
    i = 0
    while len(found) < count:
        key = f"{prefix}{i:04d}"
        if predicate(key) is want:
            found.append(key)
        i += 1
        if i > 1_000_000:  # pragma: no cover - safety valve, should never trigger
            raise RuntimeError(f"could not find {count} keys with predicate={want} for prefix {prefix!r}")
    return found


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in header})


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


FULL_HEADER = ["key", "id", "doi", "arxiv_id", "year", "venue", "sources", "has_pdf", "sig_mem_title",
               "sig_se", "sig_agent", "sig_divergent", "sig_mf_facets", "triage", "M", "T", "E", "F",
               "decision", "notes", "title", "abstract_400"]
SNOW_HEADER = ["key", "origin", "backward_n", "forward_n", "total", "year", "doi", "title",
               "abstract_400", "M", "T", "E", "F", "se", "selfpub", "artefacto", "decision", "notes"]
EXT_HEADER = ["key", "source", "year", "title", "pdf_status", "F_screening", "mem_tipos", "representacion",
              "operaciones", "trigger", "retrieval", "mide_lectura", "alcance", "multiagente",
              "fidelidad_procedencia", "benchmarks", "metricas", "fallos_mitigaciones", "evidencia_tipo",
              "F", "handoff", "plan_estado", "cita", "notes"]
DUP_HEADER = ["key_a", "key_b", "similarity", "kind", "title_a", "title_b", "year_a", "year_b",
              "source_a", "source_b"]


def _full_row(key: str, decision: str, triage: str = "IN", notes: str = "nothing special here.") -> dict:
    return {c: "" for c in FULL_HEADER} | {
        "key": key, "id": f"https://openalex.org/{key}", "year": "2026", "triage": triage,
        "M": "1", "T": "1", "E": "1", "F": "WRITE", "decision": decision, "notes": notes,
        "title": f"Full-sheet title {key}", "abstract_400": f"Abstract of {key}.",
    }


def _snow_row(key: str, decision: str, origin: str = "backward", notes: str = "nothing special.") -> dict:
    return {c: "" for c in SNOW_HEADER} | {
        "key": key, "origin": origin, "backward_n": "1", "forward_n": "0", "total": "1", "year": "2026",
        "M": "1", "T": "1", "E": "1", "F": "WRITE", "se": "0", "selfpub": "0", "artefacto": "0",
        "decision": decision, "notes": notes,
        "title": f"Snowball title {key}", "abstract_400": f"Snowball abstract of {key}.",
    }


def _ext_row(key: str, notes: str) -> dict:
    return {c: "" for c in EXT_HEADER} | {
        "key": key, "source": "main", "year": "2026", "title": f"Extraction title {key}",
        "pdf_status": "missing", "F": "WRITE", "cita": f"Cita extraccion {key}.", "notes": notes,
    }


def _digest_row(key: str, notes: str, cita: str | None = None) -> dict:
    return {
        "key": key, "cita": cita or f"Cita digest {key}.", "problema": "p", "mecanismo": "m",
        "operaciones": ["WRITE"], "representacion": ["VECTOR"], "evaluacion": "e",
        "numeros_clave": "NINGUNO", "F": ["WRITE"], "mf_aplicabilidad": [], "notes": notes,
    }


def _dup_row(key_a: str, key_b: str, similarity: str = "0.9") -> dict:
    return {c: "" for c in DUP_HEADER} | {
        "key_a": key_a, "key_b": key_b, "similarity": similarity, "kind": "SIMILAR",
        "title_a": f"Title A {key_a}", "title_b": f"Title B {key_b}",
        "year_a": "2025", "year_b": "2026", "source_a": "main", "source_b": "snowball",
    }


@pytest.fixture
def law_env(tmp_path, monkeypatch):
    """A small, deterministic, synthetic corpus wired into closure_law + make_spi_sheet + PDF_DIR, with
    at least one member (and, where relevant, a decoy that must NOT be a member) for every one of the 8
    real queues. Never touches the real committed corpus/sheets."""
    sheet_full = tmp_path / "screening_full.csv"
    sheet_snow = tmp_path / "screening_snowball.csv"
    extraction = tmp_path / "extraction.csv"
    digest = tmp_path / "digest.jsonl"
    duplicados = tmp_path / "duplicados.csv"
    pdf_dir = tmp_path / "pdf"
    pdf_dir.mkdir()

    # ---- full sheet: MUESTRA-10PCT, PREOUT-RESCATADOS, GRIS ----------------------------------------
    fsi = _keys_where(closure_law.sample10_full, True, 2, "FSI")     # IN the 10% hash sample
    fso = _keys_where(closure_law.sample10_full, False, 9, "FSO")    # guaranteed OUT of the sample
    full_rows = [
        _full_row(fsi[0], "INCLUIR"), _full_row(fsi[1], "INCLUIR"),          # MUESTRA-10PCT members
        _full_row(fso[0], "INCLUIR"),                                        # decoy: INCLUIR but NOT sampled
        _full_row(fso[1], "INCLUIR", triage="PRE-OUT"),                      # PREOUT-RESCATADOS member
        _full_row(fso[2], "EXCLUIR-CE1", triage="PRE-OUT"),                  # decoy: PRE-OUT but NOT rescued
        _full_row(fso[3], "GRIS"), _full_row(fso[4], "CE-4p"),
        _full_row(fso[5], "GRIS"), _full_row(fso[6], "GRIS"), _full_row(fso[7], "GRIS"),  # 5 GRIS members
        _full_row(fso[8], "EXCLUIR-RUBRICA"),                                 # decoy: plain exclusion
    ]
    _write_csv(sheet_full, FULL_HEADER, full_rows)

    # ---- snowball sheet: SNOWBALL-SAMPLE10, SNOWBALL-GRIS ------------------------------------------
    ssi = _keys_where(closure_law.sample10_snowball, True, 3, "SSI")
    sso = _keys_where(closure_law.sample10_snowball, False, 4, "SSO")
    snow_rows = [
        _snow_row(ssi[0], "INCLUIR"), _snow_row(ssi[1], "INCLUIR"),          # SNOWBALL-SAMPLE10 members
        _snow_row(ssi[2], "INCLUIR", origin="v1"),                           # decoy: sampled but origin==v1
        _snow_row(sso[0], "INCLUIR"),                                        # decoy: INCLUIR but NOT sampled
        _snow_row(sso[1], "GRIS"), _snow_row(sso[2], "CE-4p"),               # SNOWBALL-GRIS members
        _snow_row(sso[3], "EXCLUIR-CE2"),                                    # decoy: plain exclusion
    ]
    _write_csv(sheet_snow, SNOW_HEADER, snow_rows)

    # ---- extraction: RECONSIDERAR-EXT (incl. the naive-substring case, faithfully NOT filtered out) ---
    ext_rows = [
        _ext_row("EXT0001", "RECONSIDERAR: single-author, treat with caution."),
        _ext_row("EXT0002", "regular extraction note, nothing to flag."),                       # decoy
        _ext_row("EXT0003", "flagged for spot-check, RECONSIDERAR not warranted (scoped fine)."),  # law quirk
    ]
    _write_csv(extraction, EXT_HEADER, ext_rows)

    # ---- digest: RECONSIDERAR-DIG (no `title` field -- title must fall back to `cita`) --------------
    digest_rows = [
        _digest_row("DIG0001", "RECONSIDERAR: N=1 case study, self-reported metrics only.",
                    cita="Doe et al. (2026). A digest-only paper."),
        _digest_row("DIG0002", "solid empirical study, nothing to reconsider."),                 # decoy
    ]
    _write_jsonl(digest, digest_rows)

    # ---- duplicados: DUPLICADOS (IDENTIDAD) ---------------------------------------------------------
    dup_rows = [_dup_row("DUPA0001", "DUPB0001"), _dup_row("DUPA0002", "DUPB0002")]
    _write_csv(duplicados, DUP_HEADER, dup_rows)

    # ---- one PDF present (for a MUESTRA-10PCT key and for one half of the first duplicate pair) -----
    (pdf_dir / f"{fsi[0]}.pdf").write_bytes(b"%PDF-1.4 fixture")
    (pdf_dir / "DUPA0001.pdf").write_bytes(b"%PDF-1.4 fixture")

    monkeypatch.setattr(closure_law, "SHEET_FULL", sheet_full)
    monkeypatch.setattr(closure_law, "SHEET_SNOWBALL", sheet_snow)
    monkeypatch.setattr(closure_law, "SHEET_EXTRACTION", extraction)
    monkeypatch.setattr(closure_law, "DIGEST", digest)
    monkeypatch.setattr(closure_law, "DUPLICADOS", duplicados)
    monkeypatch.setattr(mss, "PDF_DIR", pdf_dir)
    batches = tmp_path / "spi_batches"
    monkeypatch.setattr(mss, "BATCHES", batches)
    monkeypatch.setattr(vsv, "BATCHES", batches)

    return {
        "batches": batches, "pdf_with": fsi[0], "pdf_without": fsi[1],
        "muestra_members": {fsi[0], fsi[1]}, "muestra_decoy": fso[0],
        "preout_member": fso[1], "preout_decoy": fso[2],
        "gris_members": {fso[3], fso[4], fso[5], fso[6], fso[7]},
        "snow_members": {ssi[0], ssi[1]}, "snow_v1_decoy": ssi[2], "snow_out_decoy": sso[0],
        "snow_gris_members": {sso[1], sso[2]},
        "ext_reconsiderar": "EXT0001", "ext_decoy": "EXT0002", "ext_substring_quirk": "EXT0003",
        "dig_reconsiderar": "DIG0001", "dig_decoy": "DIG0002", "dig_cita": "Doe et al. (2026). A digest-only paper.",
        "dup_pairs": {("DUPA0001", "DUPB0001"), ("DUPA0002", "DUPB0002")},
    }


def _all_rows_by_queue(batches: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for name in closure_law.QUEUES:
        qdir = batches / name
        rows: list[dict] = []
        for p in sorted(qdir.glob("q*.input.jsonl")):
            rows.extend(_read_jsonl(p))
        out[name] = rows
    return out


# ============================================================================
# (1) closure_law sanity -- the pure functions the fixtures above depend on
# ============================================================================

def test_sample10_full_is_deterministic():
    assert closure_law.sample10_full("ABC") == closure_law.sample10_full("ABC")


def test_sample10_snowball_is_deterministic():
    assert closure_law.sample10_snowball("ABC") == closure_law.sample10_snowball("ABC")


def test_bibkey_strips_non_alnum():
    assert closure_law.bibkey("2409.01344v2") == "c240901344v2"


# ============================================================================
# (2) make_spi_sheet.py build -- blindness + coverage, proven against the REAL gate
# ============================================================================

def test_build_all_queues_passes_the_real_inputs_gate(law_env):
    assert mss.main(["build"]) == 0
    assert vsv.check_inputs() == 0


def test_build_creates_a_batches_dir_for_every_queue(law_env):
    mss.main(["build"])
    for name in closure_law.QUEUES:
        assert (law_env["batches"] / name).is_dir()


def test_blindness_no_built_input_carries_a_forbidden_column(law_env):
    mss.main(["build"])
    by_queue = _all_rows_by_queue(law_env["batches"])
    for name, rows in by_queue.items():
        for row in rows:
            leaked = set(row) & set(closure_law.BLIND_FORBIDDEN)
            assert not leaked, f"{name}: row {row.get('key')} leaked {leaked}"


def test_coverage_union_of_chunks_equals_queue_members_exactly(law_env):
    mss.main(["build"])
    for name in closure_law.QUEUES:
        qdir = law_env["batches"] / name
        members = closure_law.queue_members(name)
        if name == "DUPLICADOS":
            expected = {r["key_a"] for r in members}
        else:
            expected = {r["key"] for r in members}

        seen: list[str] = []
        for p in sorted(qdir.glob("q*.input.jsonl")):
            seen.extend(r["key"] for r in _read_jsonl(p))

        assert len(seen) == len(set(seen)), f"{name}: duplicate key across chunks"
        assert set(seen) == expected, f"{name}: built {set(seen)} != queue {expected}"


def test_muestra_10pct_excludes_the_out_of_sample_decoy(law_env):
    mss.main(["build"])
    keys = {r["key"] for r in _read_jsonl(next((law_env["batches"] / "MUESTRA-10PCT").glob("q*.input.jsonl")))}
    assert keys == law_env["muestra_members"]
    assert law_env["muestra_decoy"] not in keys


def test_snowball_sample10_excludes_v1_origin_even_if_hash_sampled(law_env):
    mss.main(["build"])
    keys = {r["key"] for r in _read_jsonl(next((law_env["batches"] / "SNOWBALL-SAMPLE10").glob("q*.input.jsonl")))}
    assert keys == law_env["snow_members"]
    assert law_env["snow_v1_decoy"] not in keys
    assert law_env["snow_out_decoy"] not in keys


def test_preout_rescatados_only_the_rescued_row(law_env):
    mss.main(["build"])
    keys = {r["key"] for r in _read_jsonl(next((law_env["batches"] / "PREOUT-RESCATADOS").glob("q*.input.jsonl")))}
    assert keys == {law_env["preout_member"]}
    assert law_env["preout_decoy"] not in keys


def test_membership_row_shape(law_env):
    mss.main(["build"])
    rows = _read_jsonl(next((law_env["batches"] / "GRIS").glob("q*.input.jsonl")))
    for row in rows:
        assert set(row.keys()) <= {"key", "title", "abstract", "year", "pdf"}
        assert {"key", "title", "abstract", "year"} <= set(row.keys())


def test_optional_pdf_field_present_only_when_file_exists(law_env):
    mss.main(["build"])
    rows = {r["key"]: r for p in (law_env["batches"] / "MUESTRA-10PCT").glob("q*.input.jsonl")
            for r in _read_jsonl(p)}
    assert rows[law_env["pdf_with"]]["pdf"] == f"corpus/pdf/{law_env['pdf_with']}.pdf"
    assert "pdf" not in rows[law_env["pdf_without"]]


def test_calidad_senal_calidad_travels_as_notes_content_never_as_notes_key(law_env):
    mss.main(["build"])
    rows = {r["key"]: r for p in (law_env["batches"] / "RECONSIDERAR-EXT").glob("q*.input.jsonl")
            for r in _read_jsonl(p)}
    row = rows[law_env["ext_reconsiderar"]]
    assert "notes" not in row
    assert row["senal_calidad"].startswith("RECONSIDERAR:")
    assert set(row.keys()) <= {"key", "title", "senal_calidad", "pdf"}
    assert law_env["ext_decoy"] not in rows


def test_calidad_naive_substring_membership_is_not_re_filtered_by_the_builder(law_env):
    """`closure_law`'s RECONSIDERAR-EXT predicate is a naive substring match; the builder must derive
    membership from `queue_members()` alone and never impose a smarter filter of its own."""
    mss.main(["build"])
    rows = {r["key"] for p in (law_env["batches"] / "RECONSIDERAR-EXT").glob("q*.input.jsonl")
            for r in _read_jsonl(p)}
    assert law_env["ext_substring_quirk"] in rows
    assert law_env["ext_substring_quirk"] in {r["key"] for r in closure_law.queue_members("RECONSIDERAR-EXT")}


def test_calidad_title_falls_back_to_cita_when_source_row_has_no_title(law_env):
    mss.main(["build"])
    rows = {r["key"]: r for p in (law_env["batches"] / "RECONSIDERAR-DIG").glob("q*.input.jsonl")
            for r in _read_jsonl(p)}
    row = rows[law_env["dig_reconsiderar"]]
    assert row["title"] == law_env["dig_cita"]
    assert law_env["dig_decoy"] not in rows


def test_identidad_row_shape_and_optional_pdf_pair(law_env):
    mss.main(["build"])
    rows = {r["key"]: r for p in (law_env["batches"] / "DUPLICADOS").glob("q*.input.jsonl")
            for r in _read_jsonl(p)}
    pairs = {(r["key"], r["pareja"]) for r in rows.values()}
    assert pairs == law_env["dup_pairs"]
    row_a = rows["DUPA0001"]
    assert set(row_a.keys()) <= {"key", "pareja", "title_a", "title_b", "year_a", "year_b",
                                  "similarity", "pdf_a", "pdf_b"}
    assert row_a["pdf_a"] == "corpus/pdf/DUPA0001.pdf"
    assert "pdf_b" not in row_a          # DUPB0001.pdf was never created
    row_a2 = rows["DUPA0002"]
    assert "pdf_a" not in row_a2 and "pdf_b" not in row_a2


def test_default_build_refuses_to_clobber_without_force_then_force_rebuilds(law_env):
    assert mss.main(["build"]) == 0
    assert mss.main(["build"]) == 1              # already built, no --force -> refuses (per-queue)
    assert mss.main(["build", "--force"]) == 0    # explicit --force -> rebuilds cleanly


def test_build_single_queue_leaves_others_unbuilt(law_env):
    assert mss.main(["build", "--queue", "GRIS"]) == 0
    assert (law_env["batches"] / "GRIS").is_dir()
    assert not (law_env["batches"] / "MUESTRA-10PCT").exists()


def test_build_unknown_queue_is_red(law_env):
    assert mss.main(["build", "--queue", "NOT-A-QUEUE"]) == 1


# ============================================================================
# (3) chunking -- sizes respect CHUNK_SIZE, ids are stable + zero-padded
# ============================================================================

def test_chunk_sizes_and_zero_padded_stable_ids(law_env, monkeypatch):
    monkeypatch.setattr(closure_law, "CHUNK_SIZE", 2)   # 5 GRIS members -> chunks of 2, 2, 1
    assert mss.main(["build", "--queue", "GRIS"]) == 0

    qdir = law_env["batches"] / "GRIS"
    chunks = sorted(qdir.glob("q*.input.jsonl"))
    assert [p.name for p in chunks] == ["q01.input.jsonl", "q02.input.jsonl", "q03.input.jsonl"]
    sizes = [len(_read_jsonl(p)) for p in chunks]
    assert sizes == [2, 2, 1]

    first_build_keys = [r["key"] for p in chunks for r in _read_jsonl(p)]
    assert mss.main(["build", "--queue", "GRIS", "--force"]) == 0     # rebuild is deterministic
    second_build_keys = [r["key"] for p in sorted(qdir.glob("q*.input.jsonl")) for r in _read_jsonl(p)]
    assert second_build_keys == first_build_keys


def test_build_creates_empty_dir_for_a_zero_member_queue(tmp_path, monkeypatch):
    empty_dup = tmp_path / "duplicados_empty.csv"
    _write_csv(empty_dup, DUP_HEADER, [])
    monkeypatch.setattr(closure_law, "DUPLICADOS", empty_dup)
    batches = tmp_path / "batches"
    monkeypatch.setattr(mss, "BATCHES", batches)
    assert mss.main(["build", "--queue", "DUPLICADOS"]) == 0
    assert (batches / "DUPLICADOS").is_dir()
    assert list((batches / "DUPLICADOS").glob("q*.input.jsonl")) == []


# ============================================================================
# (4) NEGATIVE: corrupt a built input, the REAL gate must reject it
# ============================================================================

def test_gate_rejects_a_leaked_forbidden_column(law_env):
    mss.main(["build"])
    assert vsv.check_inputs() == 0
    path = next((law_env["batches"] / "GRIS").glob("q*.input.jsonl"))
    rows = _read_jsonl(path)
    rows[0]["notes"] = "leaked pass-1 note"          # corrupt: smuggle a forbidden column back in
    _write_jsonl(path, rows)
    assert vsv.check_inputs() == 1


def test_gate_rejects_a_dropped_row(law_env):
    mss.main(["build"])
    assert vsv.check_inputs() == 0
    path = next((law_env["batches"] / "GRIS").glob("q*.input.jsonl"))
    rows = _read_jsonl(path)
    _write_jsonl(path, rows[1:])                      # corrupt: silently drop a row
    assert vsv.check_inputs() == 1


def test_gate_rejects_a_duplicated_key_across_chunks(law_env, monkeypatch):
    monkeypatch.setattr(closure_law, "CHUNK_SIZE", 2)
    mss.main(["build", "--queue", "GRIS"])
    qdir = law_env["batches"] / "GRIS"
    q01 = sorted(qdir.glob("q*.input.jsonl"))[0]
    q02 = sorted(qdir.glob("q*.input.jsonl"))[1]
    smuggled = _read_jsonl(q01)[0]
    rows2 = _read_jsonl(q02)
    _write_jsonl(q02, rows2 + [smuggled])              # corrupt: same key now in two chunks
    assert vsv.check_inputs() == 1


# ============================================================================
# (5) harvest_grey.py -- doc_type inference (pure, against the REAL GREY_TIER1)
# ============================================================================

def test_infer_doc_type_matches_every_real_grey_tier1_seed():
    for seed in closure_law.GREY_TIER1:
        assert hg.infer_doc_type(seed["url"]) in closure_law.GREY_DOC_TYPES


@pytest.mark.parametrize("url,expected", [
    ("https://platform.claude.com/docs/en/x", "platform-docs"),
    ("https://ai.google.dev/gemini-api/docs/y", "platform-docs"),
    ("https://www.anthropic.com/engineering/z", "engineering-blog"),
    ("https://www.anthropic.com/news/z", "engineering-blog"),
    ("https://developers.openai.com/cookbook/examples/x", "cookbook"),
    ("https://code.claude.com/docs/en/memory", "product-docs"),
    ("https://openai.github.io/openai-agents-python/sessions/", "framework-docs"),
])
def test_infer_doc_type_rules(url, expected):
    assert hg.infer_doc_type(url) == expected


def test_infer_doc_type_raises_for_an_unmapped_host():
    with pytest.raises(ValueError):
        hg.infer_doc_type("https://example.com/nowhere")


def test_html_to_text_drops_script_and_style_and_keeps_body_text():
    blob = (b"<html><head><style>.a{color:red}</style><script>var x=1;</script></head>"
            b"<body><h1>Title</h1><p>Real content here.</p></body></html>")
    text = hg.html_to_text(blob, "text/html; charset=utf-8")
    assert "Real content here." in text
    assert "color:red" not in text
    assert "var x=1" not in text


# ============================================================================
# (6) harvest_grey.py -- fetch/manifest, NO network (a fake _fetch), belt-and-suspenders no-urlopen guard
# ============================================================================

FIXTURE_SEEDS = (
    {"key": "fixture-platform", "org": "TestOrg", "tier": "1", "rqs": "RQ1",
     "title": "Fixture platform doc", "url": "https://platform.claude.com/fixture-a"},
    {"key": "fixture-blog", "org": "TestOrg", "tier": "1", "rqs": "RQ2",
     "title": "Fixture engineering blog", "url": "https://www.anthropic.com/engineering/fixture-b"},
)


def _fixture_html(key: str) -> bytes:
    filler = ("This is real fixture prose about agent memory systems, repeated for length. " * 40)
    return f"<html><head><title>t</title></head><body><h1>{key}</h1><p>{filler}</p></body></html>".encode()


@pytest.fixture
def grey_env(tmp_path, monkeypatch):
    grey_dir = tmp_path / "corpus" / "grey"
    monkeypatch.setattr(hg, "GREY_TIER1", FIXTURE_SEEDS)
    monkeypatch.setattr(hg, "GREY_DIR", grey_dir)
    monkeypatch.setattr(hg, "MANIFEST", grey_dir / "manifest.csv")
    monkeypatch.setattr(hg, "SLEEP_S", 0)

    fixture_bytes = {s["url"]: _fixture_html(s["key"]) for s in FIXTURE_SEEDS}
    calls: list[str] = []

    def fake_fetch(url: str):
        calls.append(url)
        if url not in fixture_bytes:
            raise urllib.error.URLError(f"no fixture for {url}")
        return fixture_bytes[url], "text/html; charset=utf-8"

    monkeypatch.setattr(hg, "_fetch", fake_fetch)

    monkeypatch.setattr(vg, "GREY_TIER1", FIXTURE_SEEDS)
    monkeypatch.setattr(vg, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["verify_grey.py"])

    return {"grey_dir": grey_dir, "calls": calls, "root": tmp_path}


def test_no_urlopen_call_anywhere_in_a_fresh_fetch(grey_env, monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("real network access attempted during an offline test")
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    assert hg.main([]) == 0
    assert len(grey_env["calls"]) == 2       # went through the faked _fetch, not urlopen


def test_fetch_writes_html_txt_and_manifest_matching_grey_fields(grey_env):
    assert hg.main([]) == 0
    manifest = grey_env["grey_dir"] / "manifest.csv"
    with manifest.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == closure_law.GREY_FIELDS
        rows = list(reader)
    assert len(rows) == 2
    for row in rows:
        html_path = grey_env["root"] / row["path"]
        assert html_path.exists()
        blob = html_path.read_bytes()
        assert hashlib.sha256(blob).hexdigest() == row["sha256"]
        assert str(len(blob)) == row["bytes"]
        txt_path = html_path.with_suffix(".txt")
        assert txt_path.exists()
        assert str(len(txt_path.read_text(encoding="utf-8"))) == row["chars"]
        assert int(row["chars"]) >= 1500


def test_fetch_passes_the_real_grey_gate(grey_env):
    assert hg.main([]) == 0
    assert vg.main() == 0


def test_resumable_second_run_does_not_refetch(grey_env):
    assert hg.main([]) == 0
    assert len(grey_env["calls"]) == 2
    assert hg.main([]) == 0
    assert len(grey_env["calls"]) == 2       # no new calls -- both seeds were already fresh


def test_force_refetches_even_when_fresh(grey_env):
    hg.main([])
    assert len(grey_env["calls"]) == 2
    hg.main(["--force"])
    assert len(grey_env["calls"]) == 4


def test_a_failed_seed_is_reported_not_fabricated(tmp_path, monkeypatch):
    grey_dir = tmp_path / "corpus" / "grey"
    seeds = (FIXTURE_SEEDS[0], {**FIXTURE_SEEDS[1], "url": "https://www.anthropic.com/engineering/missing"})
    monkeypatch.setattr(hg, "GREY_TIER1", seeds)
    monkeypatch.setattr(hg, "GREY_DIR", grey_dir)
    monkeypatch.setattr(hg, "MANIFEST", grey_dir / "manifest.csv")
    monkeypatch.setattr(hg, "SLEEP_S", 0)

    def fake_fetch(url: str):
        if "missing" in url:
            raise urllib.error.URLError("404 simulated")
        return _fixture_html("fixture-platform"), "text/html; charset=utf-8"
    monkeypatch.setattr(hg, "_fetch", fake_fetch)

    assert hg.main([]) == 1                                    # non-zero: a mandatory seed failed
    rows = {r["key"]: r for r in csv.DictReader((grey_dir / "manifest.csv").open(encoding="utf-8"))}
    assert "fixture-platform" in rows
    assert seeds[1]["key"] not in rows                          # never fabricated a row for the failure


# ============================================================================
# (7) NEGATIVE: corrupt a grey snapshot, the REAL grey gate must reject it
# ============================================================================

def test_grey_gate_rejects_sha256_mismatch(grey_env):
    hg.main([])
    manifest = grey_env["grey_dir"] / "manifest.csv"
    row = next(iter(csv.DictReader(manifest.open(encoding="utf-8"))))
    html_path = grey_env["root"] / row["path"]
    html_path.write_bytes(html_path.read_bytes() + b"<!-- tampered -->")
    assert vg.main() == 1


def test_grey_gate_rejects_missing_mandatory_seed(grey_env):
    hg.main([])
    manifest = grey_env["grey_dir"] / "manifest.csv"
    rows = list(csv.DictReader(manifest.open(encoding="utf-8")))
    kept = [r for r in rows if r["key"] != FIXTURE_SEEDS[0]["key"]]
    with manifest.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=closure_law.GREY_FIELDS)
        w.writeheader()
        w.writerows(kept)
    assert vg.main() == 1


def test_grey_gate_rejects_wrong_header(grey_env):
    hg.main([])
    manifest = grey_env["grey_dir"] / "manifest.csv"
    bad_header = [f for f in closure_law.GREY_FIELDS if f != "chars"]     # drop a required column
    with manifest.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=bad_header)
        w.writeheader()
    assert vg.main() == 1


def test_grey_gate_rejects_below_min_chars(grey_env, monkeypatch):
    monkeypatch.setattr(hg, "_fetch", lambda url: (b"<html><body><p>too short</p></body></html>",
                                                    "text/html; charset=utf-8"))
    assert hg.main([]) == 0
    assert vg.main() == 1
