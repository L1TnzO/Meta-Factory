"""Offline tests for the SMS-v2 §7.6 EXTRACTION toolkit (extraction_law.py +
make_extraction_sheet.py + verify_extraction_verdicts.py). NO network access
anywhere, and NEVER reads the real corpus/sheets: every fixture below is a
small synthetic tmp_path tree, and every module path constant that would
otherwise point at the real repo is monkeypatched to that tree first.

Section (1) exercises extraction_law.validate_row's RED/GREEN sides directly.
Section (2) exercises verify_extraction_verdicts.main()'s gate (green + red)
via fixture batches/ dirs. Section (3) exercises make_extraction_sheet.py's
build + merge subcommands via fixture screening sheets + a fixture PDF dir.

All paths are computed relative to this file's own location (never cwd)."""

import csv
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import extraction_law  # noqa: E402
import make_extraction_sheet as mes  # noqa: E402
import verify_extraction_verdicts as vev  # noqa: E402


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _valid_row(**overrides) -> dict:
    row = {
        "key": "W1", "mem_tipos": "EPISODICA", "representacion": "VECTOR",
        "operaciones": "WRITE;ADMISION", "trigger": "EVENTO-DETERMINISTA",
        "retrieval": "EMBEDDINGS", "mide_lectura": "SI", "alcance": "SESION",
        "multiagente": "NO", "fidelidad_procedencia": "NO",
        "benchmarks": "LoCoMo", "metricas": "EXITO;LATENCIA",
        "fallos_mitigaciones": "staleness -> TTL de 7 dias",
        "evidencia_tipo": "ABLATION;BENCHMARK-E2E",
        "F": "RETRIEVAL-MEDIDO;WRITE", "handoff": "PUNTEROS;CONTENIDO",
        "plan_estado": "NO", "cita": "Doe et al. (2026). A paper.",
        "notes": "s3.2 tabla 2: +8pp con memoria.",
    }
    row.update(overrides)
    return row


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )


def _write_verdict_csv(path: Path, rows: list[dict], header: list[str] | None = None) -> None:
    header = header if header is not None else extraction_law.VERDICT_COLUMNS
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in header})


# --------------------------------------------------------------------------
# (1) extraction_law.validate_row -- GREEN + RED
# --------------------------------------------------------------------------

def test_validate_row_fully_valid_is_green():
    assert extraction_law.validate_row(_valid_row()) == []


RED_CASES = {
    "unknown_token": {"mem_tipos": "ALIENIGENA"},
    "na_not_alone": {"representacion": "NA;VECTOR"},
    "empty_evidencia_tipo": {"evidencia_tipo": ""},
    "mide_lectura_si_without_retrieval_medido": {"mide_lectura": "SI", "F": "WRITE"},
    "empty_cita": {"cita": ""},
    "bad_handoff_mix": {"handoff": "NO;PUNTEROS"},
}


@pytest.mark.parametrize("name", list(RED_CASES))
def test_validate_row_red_cases(name):
    errs = extraction_law.validate_row(_valid_row(**RED_CASES[name]))
    assert errs, f"{name} should have produced violations"


def test_validate_row_column_set_mismatch_is_red():
    row = _valid_row()
    del row["notes"]
    assert extraction_law.validate_row(row)


# --------------------------------------------------------------------------
# (2) verify_extraction_verdicts.main() -- gate GREEN + RED
# --------------------------------------------------------------------------

def _input_record(key: str) -> dict:
    return {
        "key": key, "title": f"Title {key}", "year": 2025, "abstract": "abs",
        "F_screening": "WRITE", "pdf": f"corpus/pdf/{key}.pdf",
    }


@pytest.fixture
def gate_batches(tmp_path, monkeypatch) -> Path:
    batches = tmp_path / "batches"
    batches.mkdir()
    monkeypatch.setattr(vev, "BATCHES", batches)
    return batches


def test_gate_green(gate_batches):
    _write_jsonl(gate_batches / "e01.input.jsonl", [_input_record("W1")])
    _write_verdict_csv(gate_batches / "e01.verdict.csv", [_valid_row(key="W1")])
    assert vev.main([]) == 0


def test_gate_red_key_mismatch(gate_batches):
    _write_jsonl(gate_batches / "e01.input.jsonl", [_input_record("W1"), _input_record("W2")])
    _write_verdict_csv(gate_batches / "e01.verdict.csv", [_valid_row(key="W1")])  # missing W2
    assert vev.main([]) == 1


def test_gate_red_wrong_header(gate_batches):
    _write_jsonl(gate_batches / "e01.input.jsonl", [_input_record("W1")])
    bad_header = extraction_law.VERDICT_COLUMNS[:-1]  # drop 'notes'
    row = _valid_row(key="W1")
    del row["notes"]
    _write_verdict_csv(gate_batches / "e01.verdict.csv", [row], header=bad_header)
    assert vev.main([]) == 1


def test_gate_red_missing_required_chunk(gate_batches):
    assert vev.main(["--require", "e01,e02"]) == 1


# --------------------------------------------------------------------------
# (3) make_extraction_sheet.py -- build + merge, fixture mini-sheets
# --------------------------------------------------------------------------

def _sheet_row(key, year, title, F, decision, abstract_400):
    return {
        "key": key, "year": str(year), "title": title, "F": F,
        "decision": decision, "abstract_400": abstract_400,
    }


def _setup_build_env(tmp_path, monkeypatch):
    """3 INCLUIR rows across the two screening sheets: C1 (F=SEGURIDAD;COSTO
    -> rank 1, pdf ok, 2023), A1 (F=RETRIEVAL-MEDIDO -> rank 9, pdf ok,
    2024), B1 (F=DOCS-VERSIONADO -> rank 0, pdf MISSING, 2025). Expected
    order: pdf-ok group first by priority (C1, A1), then pdf-missing (B1)
    regardless of its lower rank."""
    full = tmp_path / "screening_full.csv"
    snowball = tmp_path / "screening_snowball.csv"
    cols = ["key", "year", "title", "F", "decision", "abstract_400"]
    with full.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerow(_sheet_row("A1", 2024, "Paper A1", "RETRIEVAL-MEDIDO", "INCLUIR", "abstract of A1"))
        w.writerow(_sheet_row("B1", 2025, "Paper B1", "DOCS-VERSIONADO", "INCLUIR", "abstract of B1"))
        w.writerow(_sheet_row("Z1", 2020, "Paper Z1", "WRITE", "EXCLUIR-CE1", "not included"))
    with snowball.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerow(_sheet_row("C1", 2023, "Paper C1", "SEGURIDAD;COSTO", "INCLUIR", "abstract of C1"))

    pdf_dir = tmp_path / "pdf"
    pdf_dir.mkdir()
    (pdf_dir / "A1.pdf").write_bytes(b"%PDF-fake")
    (pdf_dir / "C1.pdf").write_bytes(b"%PDF-fake")

    extraction_dir = tmp_path / "extraction"
    monkeypatch.setattr(mes, "SCREENING_FULL", full)
    monkeypatch.setattr(mes, "SCREENING_SNOWBALL", snowball)
    monkeypatch.setattr(mes, "PDF_DIR", pdf_dir)
    monkeypatch.setattr(mes, "CORPUS_JSONL", tmp_path / "corpus.jsonl")  # absent on purpose
    monkeypatch.setattr(mes, "SEEDS_JSONL", tmp_path / "seeds.jsonl")  # absent on purpose
    monkeypatch.setattr(mes, "EXTRACTION_DIR", extraction_dir)
    monkeypatch.setattr(mes, "EXTRACTION_CSV", extraction_dir / "extraction.csv")
    monkeypatch.setattr(mes, "BATCHES", extraction_dir / "batches")
    return extraction_dir


def test_build_three_row_sheet_scarcity_order(tmp_path, monkeypatch):
    extraction_dir = _setup_build_env(tmp_path, monkeypatch)
    assert mes.main(["build"]) == 0

    with (extraction_dir / "extraction.csv").open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        rows = list(reader)

    assert header == extraction_law.IDENTITY_COLUMNS + extraction_law.VERDICT_COLUMNS[1:]
    assert [r["key"] for r in rows] == ["C1", "A1", "B1"]
    assert [r["pdf_status"] for r in rows] == ["ok", "ok", "missing"]
    assert [r["source"] for r in rows] == ["snowball", "main", "main"]
    for r in rows:  # verdict cells all empty on a fresh build
        assert all(r[c] == "" for c in extraction_law.VERDICT_COLUMNS[1:])


def test_build_only_pdf_ok_rows_chunked_in_scarcity_order(tmp_path, monkeypatch):
    extraction_dir = _setup_build_env(tmp_path, monkeypatch)
    mes.main(["build"])

    batches = extraction_dir / "batches"
    chunks = sorted(batches.glob("e*.input.jsonl"))
    assert [p.name for p in chunks] == ["e01.input.jsonl"]

    lines = [json.loads(ln) for ln in chunks[0].read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert [r["key"] for r in lines] == ["C1", "A1"]
    assert lines[0]["pdf"] == "corpus/pdf/C1.pdf"
    assert lines[0]["abstract"] == "abstract of C1"  # falls back to abstract_400


def test_build_refuses_overwrite_without_force(tmp_path, monkeypatch):
    extraction_dir = _setup_build_env(tmp_path, monkeypatch)
    assert mes.main(["build"]) == 0
    before = (extraction_dir / "extraction.csv").read_text(encoding="utf-8")

    assert mes.main(["build"]) == 1
    assert (extraction_dir / "extraction.csv").read_text(encoding="utf-8") == before
    assert mes.main(["build", "--force"]) == 0


def test_build_never_touches_verdict_csv(tmp_path, monkeypatch):
    extraction_dir = _setup_build_env(tmp_path, monkeypatch)
    batches = extraction_dir / "batches"
    batches.mkdir(parents=True)
    stray = batches / "e05.verdict.csv"
    stray.write_text("key,notes\nW9,keep-me\n", encoding="utf-8")

    assert mes.main(["build", "--force"]) == 0
    assert stray.read_text(encoding="utf-8") == "key,notes\nW9,keep-me\n"


def test_merge_fills_and_is_idempotent(tmp_path, monkeypatch):
    extraction_dir = _setup_build_env(tmp_path, monkeypatch)
    mes.main(["build"])
    batches = extraction_dir / "batches"
    _write_verdict_csv(batches / "e01.verdict.csv", [_valid_row(key="C1"), _valid_row(key="A1")])

    assert mes.main(["merge"]) == 0
    with (extraction_dir / "extraction.csv").open(newline="", encoding="utf-8") as fh:
        rows = {r["key"]: r for r in csv.DictReader(fh)}
    assert rows["C1"]["cita"] == "Doe et al. (2026). A paper."
    assert rows["A1"]["mem_tipos"] == "EPISODICA"
    assert rows["B1"]["cita"] == ""  # untouched: not in any input chunk

    assert mes.main(["merge"]) == 0  # idempotent re-merge of the identical data
    with (extraction_dir / "extraction.csv").open(newline="", encoding="utf-8") as fh:
        rows2 = {r["key"]: r for r in csv.DictReader(fh)}
    assert rows2 == rows


def test_merge_rejects_invalid_verdict(tmp_path, monkeypatch):
    extraction_dir = _setup_build_env(tmp_path, monkeypatch)
    mes.main(["build"])
    batches = extraction_dir / "batches"
    _write_verdict_csv(batches / "e01.verdict.csv", [_valid_row(key="C1", cita=""), _valid_row(key="A1")])

    with (extraction_dir / "extraction.csv").open(newline="", encoding="utf-8") as fh:
        before = fh.read()
    assert mes.main(["merge"]) == 1
    with (extraction_dir / "extraction.csv").open(newline="", encoding="utf-8") as fh:
        after = fh.read()
    assert before == after  # all-or-nothing: nothing applied on abort


def test_merge_refuses_differing_cell_without_force(tmp_path, monkeypatch):
    extraction_dir = _setup_build_env(tmp_path, monkeypatch)
    mes.main(["build"])
    batches = extraction_dir / "batches"
    _write_verdict_csv(batches / "e01.verdict.csv", [_valid_row(key="C1"), _valid_row(key="A1")])
    assert mes.main(["merge"]) == 0

    _write_verdict_csv(batches / "e01.verdict.csv", [
        _valid_row(key="C1", alcance="PROYECTO"), _valid_row(key="A1"),
    ])
    assert mes.main(["merge"]) == 1
    assert mes.main(["merge", "--force"]) == 0
    with (extraction_dir / "extraction.csv").open(newline="", encoding="utf-8") as fh:
        rows = {r["key"]: r for r in csv.DictReader(fh)}
    assert rows["C1"]["alcance"] == "PROYECTO"


# --------------------------------------------------------------------------
# (4) no network access anywhere (belt-and-suspenders)
# --------------------------------------------------------------------------

def test_no_network_calls_anywhere(monkeypatch):
    import urllib.request

    def _boom(*_a, **_k):
        raise AssertionError("network access attempted during offline test run")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    assert extraction_law.validate_row(_valid_row()) == []
