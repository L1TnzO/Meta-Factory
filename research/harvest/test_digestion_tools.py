"""Offline tests for the SMS-v2 §7.4 DIGESTION toolkit (digestion_law.py +
make_digest_sheet.py + verify_digest_verdicts.py). NO network access
anywhere, and NEVER reads the real corpus/sheets: every fixture below is a
small synthetic tmp_path tree, and every module path constant that would
otherwise point at the real repo is monkeypatched to that tree first.

Section (1) exercises digestion_law.validate_digest's RED/GREEN sides
directly. Section (2) exercises verify_digest_verdicts.main()'s gate (green +
red) via fixture batches/ dirs + a fixture extraction.csv. Section (3)
exercises make_digest_sheet.py's build + merge subcommands via a fixture
extraction.csv (mirrors test_extraction_tools.py, one level down, JSONL
instead of CSV for the batch files).

All paths are computed relative to this file's own location (never cwd)."""

import csv
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import digestion_law  # noqa: E402
import extraction_law  # noqa: E402
import make_digest_sheet as mds  # noqa: E402
import verify_digest_verdicts as vdv  # noqa: E402


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _valid_ext(**overrides) -> dict:
    """A frozen §7.6 extraction row, ground truth for a digest of key W1."""
    ext = {
        "key": "W1",
        "operaciones": "WRITE;ADMISION",
        "representacion": "VECTOR",
        "F": "RETRIEVAL-MEDIDO;WRITE",
        "evidencia_tipo": "ABLATION;BENCHMARK-E2E",
        "plan_estado": "NO",
        "cita": "Doe et al. (2026). A paper.",
    }
    ext.update(overrides)
    return ext


def _valid_rec(**overrides) -> dict:
    """A fully-valid §7.4 digest record matching _valid_ext()'s W1 row."""
    rec = {
        "key": "W1",
        "cita": "Doe et al. (2026). A paper.",
        "problema": "El sistema pierde contexto entre sesiones largas y repite errores ya corregidos.",
        "mecanismo": "Escribe resumenes episodicos tras cada sesion y los recupera por similitud vectorial.",
        "operaciones": ["WRITE", "ADMISION"],
        "representacion": ["VECTOR"],
        "evaluacion": "Evalua sobre LoCoMo con metricas de exito y latencia frente a un baseline sin memoria.",
        "numeros_clave": "+8pp de exito sobre baseline (Tabla 2).",
        "F": ["RETRIEVAL-MEDIDO", "WRITE"],
        "mf_aplicabilidad": [
            {"ancla": "G-M2", "postura": "CONFIRMA", "nota": "Confirma que retrieval medido supera grep (s4.1)."},
        ],
        "notes": "s4.1 tabla 2: metodo de retrieval medido reportado.",
    }
    rec.update(overrides)
    return rec


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )


def _read_jsonl_file(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


# --------------------------------------------------------------------------
# (1) digestion_law.validate_digest -- GREEN + RED
# --------------------------------------------------------------------------

def test_validate_digest_fully_valid_is_green():
    assert digestion_law.validate_digest(_valid_rec(), _valid_ext()) == []


def test_validate_digest_field_set_missing_key_is_red():
    rec = _valid_rec()
    del rec["notes"]
    assert digestion_law.validate_digest(rec, _valid_ext())


def test_validate_digest_field_set_extra_key_is_red():
    rec = _valid_rec()
    rec["extra_field"] = "oops"
    assert digestion_law.validate_digest(rec, _valid_ext())


RED_CASES = {
    "cita_drift": {"cita": "A completely different citation string."},
    "operaciones_drift": {"operaciones": ["WRITE"]},  # ext has WRITE;ADMISION
    "representacion_drift": {"representacion": ["GRAFO"]},  # ext has VECTOR
    "F_drift": {"F": ["WRITE"]},  # ext has RETRIEVAL-MEDIDO;WRITE
    "problema_too_short": {"problema": "short"},
    "mecanismo_too_short": {"mecanismo": "short"},
    "evaluacion_too_short": {"evaluacion": "short"},
    "notes_too_short": {"notes": "short"},
    "numeros_clave_empty_with_numeric_evidence": {"numeros_clave": ""},
    "numeros_clave_ninguno_with_numeric_evidence": {"numeros_clave": "NINGUNO"},
    "mf_aplicabilidad_not_a_list": {"mf_aplicabilidad": "oops"},
    "mf_aplicabilidad_empty_list": {"mf_aplicabilidad": []},
    "mf_aplicabilidad_unknown_ancla": {
        "mf_aplicabilidad": [{"ancla": "BOGUS", "postura": "CONFIRMA", "nota": "algo de contexto util."}],
    },
    "mf_aplicabilidad_unknown_postura": {
        "mf_aplicabilidad": [{"ancla": "G-M2", "postura": "BOGUS", "nota": "algo de contexto util."}],
    },
    "mf_aplicabilidad_empty_nota": {
        "mf_aplicabilidad": [{"ancla": "G-M2", "postura": "CONFIRMA", "nota": ""}],
    },
}


@pytest.mark.parametrize("name", list(RED_CASES))
def test_validate_digest_red_cases(name):
    errs = digestion_law.validate_digest(_valid_rec(**RED_CASES[name]), _valid_ext())
    assert errs, f"{name} should have produced violations"


def test_numeros_clave_ninguno_ok_without_numeric_evidence():
    ext = _valid_ext(evidencia_tipo="CUALITATIVA")
    rec = _valid_rec(numeros_clave="NINGUNO")
    assert digestion_law.validate_digest(rec, ext) == []


def test_docs_versionado_requires_tier_docs_ancla():
    ext = _valid_ext(F="DOCS-VERSIONADO;WRITE")
    rec = _valid_rec(F=["DOCS-VERSIONADO", "WRITE"])  # only G-M2 in mf_aplicabilidad
    assert digestion_law.validate_digest(rec, ext)


def test_docs_versionado_with_tier_docs_ancla_is_green():
    ext = _valid_ext(F="DOCS-VERSIONADO;WRITE")
    rec = _valid_rec(F=["DOCS-VERSIONADO", "WRITE"], mf_aplicabilidad=[
        {"ancla": "TIER-DOCS", "postura": "CONFIRMA", "nota": "Confirma Tier-1 docs=verdad (s3.1)."},
    ])
    assert digestion_law.validate_digest(rec, ext) == []


def test_negativo_requires_negativo_ancla():
    ext = _valid_ext(F="NEGATIVO;WRITE")
    rec = _valid_rec(F=["NEGATIVO", "WRITE"])  # only G-M2 in mf_aplicabilidad
    assert digestion_law.validate_digest(rec, ext)


def test_plan_estado_si_requires_plan_estado_ancla():
    ext = _valid_ext(plan_estado="SI")
    rec = _valid_rec()  # only G-M2 in mf_aplicabilidad
    assert digestion_law.validate_digest(rec, ext)


def test_plan_estado_si_with_plan_estado_ancla_is_green():
    ext = _valid_ext(plan_estado="SI")
    rec = _valid_rec(mf_aplicabilidad=[
        {"ancla": "G-M2", "postura": "CONFIRMA", "nota": "Confirma retrieval medido (s4.1)."},
        {"ancla": "PLAN-ESTADO", "postura": "EXTIENDE", "nota": "Ofrece patron de estado-de-plan (s2)."},
    ])
    assert digestion_law.validate_digest(rec, ext) == []


def test_unknown_key_no_extraction_row_is_red():
    errs = digestion_law.validate_digest(_valid_rec(), {})
    assert errs
    assert any("unknown key" in e for e in errs)


# --------------------------------------------------------------------------
# (2) verify_digest_verdicts.main() -- gate GREEN + RED
# --------------------------------------------------------------------------

def _input_record(key: str, **overrides) -> dict:
    rec = {
        "key": key, "cita": f"Cita {key}.", "operaciones": ["WRITE", "ADMISION"],
        "representacion": ["VECTOR"], "F": ["RETRIEVAL-MEDIDO", "WRITE"],
        "evidencia_tipo": ["ABLATION", "BENCHMARK-E2E"], "plan_estado": "NO",
        "pdf": f"corpus/pdf/{key}.pdf",
    }
    rec.update(overrides)
    return rec


def _ext_row(key: str, **overrides) -> dict:
    row = {
        "key": key, "cita": f"Cita {key}.", "operaciones": "WRITE;ADMISION",
        "representacion": "VECTOR", "F": "RETRIEVAL-MEDIDO;WRITE",
        "evidencia_tipo": "ABLATION;BENCHMARK-E2E", "plan_estado": "NO",
    }
    row.update(overrides)
    return row


def _write_extraction_csv(path: Path, rows: list[dict]) -> None:
    cols = ["key", "cita", "operaciones", "representacion", "F", "evidencia_tipo", "plan_estado"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in cols})


def _valid_verdict_record(key: str, **overrides) -> dict:
    rec = _valid_rec(key=key, cita=f"Cita {key}.")
    rec.update(overrides)
    return rec


@pytest.fixture
def gate_env(tmp_path, monkeypatch):
    batches = tmp_path / "batches"
    batches.mkdir()
    monkeypatch.setattr(vdv, "BATCHES", batches)
    ext_csv = tmp_path / "extraction.csv"
    monkeypatch.setattr(vdv, "EXTRACTION_CSV", ext_csv)
    return batches, ext_csv


def test_gate_green(gate_env):
    batches, ext_csv = gate_env
    _write_extraction_csv(ext_csv, [_ext_row("W1")])
    _write_jsonl(batches / "d01.input.jsonl", [_input_record("W1")])
    _write_jsonl(batches / "d01.verdict.jsonl", [_valid_verdict_record("W1")])
    assert vdv.main([]) == 0


def test_gate_red_key_mismatch(gate_env):
    batches, ext_csv = gate_env
    _write_extraction_csv(ext_csv, [_ext_row("W1"), _ext_row("W2")])
    _write_jsonl(batches / "d01.input.jsonl", [_input_record("W1"), _input_record("W2")])
    _write_jsonl(batches / "d01.verdict.jsonl", [_valid_verdict_record("W1")])  # missing W2
    assert vdv.main([]) == 1


def test_gate_red_invalid_record(gate_env):
    batches, ext_csv = gate_env
    _write_extraction_csv(ext_csv, [_ext_row("W1")])
    _write_jsonl(batches / "d01.input.jsonl", [_input_record("W1")])
    _write_jsonl(batches / "d01.verdict.jsonl", [_valid_verdict_record("W1", cita="drifted, not W1's cita")])
    assert vdv.main([]) == 1


def test_gate_red_missing_required_chunk(gate_env):
    assert vdv.main(["--require", "d01,d02"]) == 1


# --------------------------------------------------------------------------
# (3) make_digest_sheet.py -- build + merge, fixture extraction.csv
# --------------------------------------------------------------------------

def _full_ext_row(key, pdf_status, F, cita=None, operaciones="WRITE", representacion="VECTOR",
                   evidencia_tipo="CUALITATIVA", plan_estado="NO") -> dict:
    return {
        "key": key, "pdf_status": pdf_status, "F": F,
        "cita": cita or f"Cita {key}.",
        "operaciones": operaciones, "representacion": representacion,
        "evidencia_tipo": evidencia_tipo, "plan_estado": plan_estado,
    }


def _write_full_extraction_csv(path: Path, rows: list[dict]) -> None:
    cols = ["key", "pdf_status", "F", "cita", "operaciones", "representacion", "evidencia_tipo", "plan_estado"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in cols})


def _setup_build_env(tmp_path, monkeypatch) -> Path:
    """7 pdf-ok rows: D1 (F=DOCS-VERSIONADO;WRITE, the priority/scarce facet)
    + C1..C6 (F=WRITE only, common facet) -- plus C7 with pdf_status=missing
    (must never be chunked). Expected order: D1 first (priority facet beats a
    common-facet-only paper), then C1..C6; chunk size 6 -> d01 has 6, d02 has 1."""
    extraction_csv = tmp_path / "extraction.csv"
    rows = [_full_ext_row("D1", "ok", "DOCS-VERSIONADO;WRITE")]
    rows += [_full_ext_row(f"C{i}", "ok", "WRITE") for i in range(1, 7)]
    rows.append(_full_ext_row("C7", "missing", "WRITE"))
    _write_full_extraction_csv(extraction_csv, rows)

    digestion_dir = tmp_path / "digestion"
    monkeypatch.setattr(mds, "EXTRACTION_CSV", extraction_csv)
    monkeypatch.setattr(mds, "DIGESTION_DIR", digestion_dir)
    monkeypatch.setattr(mds, "BATCHES", digestion_dir / "batches")
    monkeypatch.setattr(mds, "DIGEST_JSONL", digestion_dir / "digest.jsonl")
    return digestion_dir


def test_build_orders_priority_facet_first_and_chunks_by_six(tmp_path, monkeypatch):
    digestion_dir = _setup_build_env(tmp_path, monkeypatch)
    assert mds.main(["build"]) == 0

    batches = digestion_dir / "batches"
    chunks = sorted(batches.glob("d*.input.jsonl"))
    assert [p.name for p in chunks] == ["d01.input.jsonl", "d02.input.jsonl"]

    chunk1 = _read_jsonl_file(chunks[0])
    chunk2 = _read_jsonl_file(chunks[1])
    assert len(chunk1) == 6
    assert len(chunk2) == 1

    all_keys = [r["key"] for r in chunk1] + [r["key"] for r in chunk2]
    assert all_keys[0] == "D1"  # DOCS-VERSIONADO (priority) sorts before common-facet-only papers
    assert "C1" in all_keys[1:]
    assert "C7" not in all_keys  # pdf-missing row is never chunked

    for r in chunk1 + chunk2:
        assert set(r.keys()) == set(digestion_law.INPUT_FIELDS)
        assert isinstance(r["F"], list)
        assert isinstance(r["operaciones"], list)
        assert isinstance(r["representacion"], list)
        assert isinstance(r["evidencia_tipo"], list)
        assert r["pdf"] == f"corpus/pdf/{r['key']}.pdf"


def _verdict_from_input(rec: dict) -> dict:
    """A fully-valid digest record synthesised from a build input record,
    obeying every facet->ancla obligation the record's own F/plan_estado imply."""
    key = rec["key"]
    mf = [{"ancla": "G-M2", "postura": "NEUTRAL", "nota": f"Nota de aplicabilidad general para {key}."}]
    if "DOCS-VERSIONADO" in rec["F"]:
        mf.append({"ancla": "TIER-DOCS", "postura": "CONFIRMA", "nota": f"Confirma Tier-1 docs para {key}."})
    if "NEGATIVO" in rec["F"]:
        mf.append({"ancla": "NEGATIVO", "postura": "CONFIRMA", "nota": f"Confirma conocimiento negativo para {key}."})
    if rec.get("plan_estado") == "SI":
        mf.append({"ancla": "PLAN-ESTADO", "postura": "EXTIENDE", "nota": f"Extiende estado-de-plan para {key}."})
    return {
        "key": key,
        "cita": rec["cita"],
        "problema": f"Problema sintetizado para {key} con contexto suficiente para pasar el piso minimo.",
        "mecanismo": f"Mecanismo sintetizado para {key} descrito con detalle suficiente para pasar el piso de treinta.",
        "operaciones": list(rec["operaciones"]),
        "representacion": list(rec["representacion"]),
        "evaluacion": f"Evaluacion sintetizada para {key} con contexto suficiente para el piso minimo.",
        "numeros_clave": "NINGUNO",
        "F": list(rec["F"]),
        "mf_aplicabilidad": mf,
        "notes": f"Nota de evidencia para {key} con longitud suficiente.",
    }


def test_merge_green_writes_digest_jsonl(tmp_path, monkeypatch):
    digestion_dir = _setup_build_env(tmp_path, monkeypatch)
    mds.main(["build"])
    batches = digestion_dir / "batches"

    for chunk_name in ("d01", "d02"):
        recs = _read_jsonl_file(batches / f"{chunk_name}.input.jsonl")
        _write_jsonl(batches / f"{chunk_name}.verdict.jsonl", [_verdict_from_input(r) for r in recs])

    assert mds.main(["merge"]) == 0

    digest_path = digestion_dir / "digest.jsonl"
    assert digest_path.exists()
    out = _read_jsonl_file(digest_path)
    assert len(out) == 7
    assert out[0]["key"] == "D1"  # d01 first, and D1 is first within d01 (input order)
    for rec in out:
        assert set(rec.keys()) == set(digestion_law.DIGEST_FIELDS)


def test_merge_rejects_invalid_record_and_writes_nothing(tmp_path, monkeypatch):
    digestion_dir = _setup_build_env(tmp_path, monkeypatch)
    mds.main(["build"])
    batches = digestion_dir / "batches"

    recs1 = _read_jsonl_file(batches / "d01.input.jsonl")
    verdicts1 = [_verdict_from_input(r) for r in recs1]
    verdicts1[0]["cita"] = "a completely different citation"  # drifts from extraction -> invalid
    _write_jsonl(batches / "d01.verdict.jsonl", verdicts1)

    recs2 = _read_jsonl_file(batches / "d02.input.jsonl")
    _write_jsonl(batches / "d02.verdict.jsonl", [_verdict_from_input(r) for r in recs2])

    assert mds.main(["merge"]) == 1
    assert not (digestion_dir / "digest.jsonl").exists()


def test_merge_orders_by_chunk_name_then_input_order(tmp_path, monkeypatch):
    digestion_dir = _setup_build_env(tmp_path, monkeypatch)
    mds.main(["build"])
    batches = digestion_dir / "batches"

    recs1 = _read_jsonl_file(batches / "d01.input.jsonl")
    verdicts1 = [_verdict_from_input(r) for r in recs1]
    _write_jsonl(batches / "d01.verdict.jsonl", list(reversed(verdicts1)))  # scrambled vs input order

    recs2 = _read_jsonl_file(batches / "d02.input.jsonl")
    _write_jsonl(batches / "d02.verdict.jsonl", [_verdict_from_input(r) for r in recs2])

    assert mds.main(["merge"]) == 0
    out = _read_jsonl_file(digestion_dir / "digest.jsonl")
    expected_order = [r["key"] for r in recs1] + [r["key"] for r in recs2]
    assert [r["key"] for r in out] == expected_order


def test_merge_no_verdicts_is_noop(tmp_path, monkeypatch):
    digestion_dir = _setup_build_env(tmp_path, monkeypatch)
    mds.main(["build"])
    assert mds.main(["merge"]) == 0
    assert not (digestion_dir / "digest.jsonl").exists()


# --------------------------------------------------------------------------
# (3b) make_digest_sheet.py -- add-external (SPI-rescued keys outside the
#      original build pdf-ok universe -- additive, mirrors
#      make_extraction_sheet.py's add-external one level up)
# --------------------------------------------------------------------------

def _full_verdict_extraction_row(key, pdf_status="ok", **overrides) -> dict:
    """A fully-verdicted §7.6 extraction row (every VERDICT_COLUMNS[1:] cell non-empty) --
    the ground truth add-external requires before it will chunk a key."""
    row = {
        "key": key, "pdf_status": pdf_status,
        "mem_tipos": "EPISODICA", "representacion": "VECTOR",
        "operaciones": "WRITE;ADMISION", "trigger": "EVENTO-DETERMINISTA",
        "retrieval": "EMBEDDINGS", "mide_lectura": "SI", "alcance": "SESION",
        "multiagente": "NO", "fidelidad_procedencia": "NO",
        "benchmarks": "LoCoMo", "metricas": "EXITO;LATENCIA",
        "fallos_mitigaciones": "staleness -> TTL de 7 dias",
        "evidencia_tipo": "ABLATION;BENCHMARK-E2E",
        "F": "RETRIEVAL-MEDIDO;WRITE", "handoff": "PUNTEROS;CONTENIDO",
        "plan_estado": "NO", "cita": f"Cita {key}.",
        "notes": "s3.2 tabla 2: +8pp con memoria.",
    }
    row.update(overrides)
    return row


def _write_extraction_csv_full(path: Path, rows: list[dict]) -> None:
    cols = ["key", "pdf_status"] + extraction_law.VERDICT_COLUMNS[1:]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in cols})


def _setup_add_external_env(tmp_path, monkeypatch, extra_rows: list[dict] | None = None) -> Path:
    """7 already-chunked pdf-ok rows (D1 + C1..C6, via a real `build` run; C7 has
    pdf_status=missing so build never chunks it) plus whatever `extra_rows` the caller appends
    AFTER build already ran -- mimicking a companion extraction-wave slot landing new
    fully-verdicted rows that `build` never saw. add-external's whole reason to exist is
    chunking exactly those keys, additively."""
    digestion_dir = tmp_path / "digestion"
    extraction_csv = tmp_path / "extraction.csv"
    base_rows = [_full_verdict_extraction_row("D1", F="DOCS-VERSIONADO;WRITE")]
    base_rows += [_full_verdict_extraction_row(f"C{i}", F="WRITE") for i in range(1, 7)]
    base_rows.append(_full_verdict_extraction_row("C7", pdf_status="missing"))
    _write_extraction_csv_full(extraction_csv, base_rows)

    monkeypatch.setattr(mds, "EXTRACTION_CSV", extraction_csv)
    monkeypatch.setattr(mds, "DIGESTION_DIR", digestion_dir)
    monkeypatch.setattr(mds, "BATCHES", digestion_dir / "batches")
    monkeypatch.setattr(mds, "DIGEST_JSONL", digestion_dir / "digest.jsonl")
    assert mds.main(["build"]) == 0  # chunks D1+C1..C6 into d01/d02; C7 excluded (pdf missing)

    if extra_rows:
        _write_extraction_csv_full(extraction_csv, base_rows + extra_rows)
    return digestion_dir


def _keys_file(tmp_path: Path, keys: list[str]) -> Path:
    path = tmp_path / "keys.json"
    path.write_text(json.dumps(keys), encoding="utf-8")
    return path


def test_add_external_chunks_new_key(tmp_path, monkeypatch):
    digestion_dir = _setup_add_external_env(tmp_path, monkeypatch, extra_rows=[
        _full_verdict_extraction_row("EXT1", F="WRITE"),
    ])
    batches = digestion_dir / "batches"
    d01_before = (batches / "d01.input.jsonl").read_text(encoding="utf-8")
    d02_before = (batches / "d02.input.jsonl").read_text(encoding="utf-8")
    keys_path = _keys_file(tmp_path, ["EXT1"])

    assert mds.main(["add-external", "--keys", str(keys_path)]) == 0

    # existing d01/d02 are byte-for-byte untouched
    assert (batches / "d01.input.jsonl").read_text(encoding="utf-8") == d01_before
    assert (batches / "d02.input.jsonl").read_text(encoding="utf-8") == d02_before
    # numbering continues from the existing max (d02 -> d03)
    new_chunk = batches / "d03.input.jsonl"
    assert new_chunk.exists()
    lines = _read_jsonl_file(new_chunk)
    assert [ln["key"] for ln in lines] == ["EXT1"]
    rec = lines[0]
    assert set(rec.keys()) == set(digestion_law.INPUT_FIELDS)
    assert rec["F"] == ["WRITE"]
    assert rec["operaciones"] == ["WRITE", "ADMISION"]
    assert rec["pdf"] == "corpus/pdf/EXT1.pdf"


def test_add_external_aborts_on_not_ready_key(tmp_path, monkeypatch):
    digestion_dir = _setup_add_external_env(tmp_path, monkeypatch, extra_rows=[
        _full_verdict_extraction_row("EXT1", F="WRITE"),
    ])
    batches = digestion_dir / "batches"
    keys_path = _keys_file(tmp_path, ["EXT1", "C7"])  # C7 has pdf_status=missing

    assert mds.main(["add-external", "--keys", str(keys_path)]) == 1
    assert not (batches / "d03.input.jsonl").exists()


def test_add_external_aborts_on_incomplete_verdict(tmp_path, monkeypatch):
    digestion_dir = _setup_add_external_env(tmp_path, monkeypatch, extra_rows=[
        _full_verdict_extraction_row("EXT2", F="WRITE", notes=""),  # incomplete: notes empty
    ])
    batches = digestion_dir / "batches"
    keys_path = _keys_file(tmp_path, ["EXT2"])

    assert mds.main(["add-external", "--keys", str(keys_path)]) == 1
    assert not (batches / "d03.input.jsonl").exists()


def test_add_external_aborts_on_key_collision(tmp_path, monkeypatch):
    digestion_dir = _setup_add_external_env(tmp_path, monkeypatch)
    batches = digestion_dir / "batches"
    keys_path = _keys_file(tmp_path, ["D1"])  # already chunked by build into d01.input.jsonl

    assert mds.main(["add-external", "--keys", str(keys_path)]) == 1
    assert not (batches / "d03.input.jsonl").exists()


def test_add_external_all_or_nothing_on_partial_collision(tmp_path, monkeypatch):
    digestion_dir = _setup_add_external_env(tmp_path, monkeypatch, extra_rows=[
        _full_verdict_extraction_row("EXT1", F="WRITE"),
    ])
    batches = digestion_dir / "batches"
    keys_path = _keys_file(tmp_path, ["EXT1", "D1"])  # EXT1 valid, D1 already chunked

    assert mds.main(["add-external", "--keys", str(keys_path)]) == 1
    assert not (batches / "d03.input.jsonl").exists()


def test_add_external_orders_priority_facet_first_scoped_to_new_keys_only(tmp_path, monkeypatch):
    """Priority order among the NEW keys must be computed over just their own rows -- NOT
    recomputed globally over the full corpus (that would silently change historical chunks)."""
    digestion_dir = _setup_add_external_env(tmp_path, monkeypatch, extra_rows=[
        _full_verdict_extraction_row("EXT-COMMON1", F="WRITE"),
        _full_verdict_extraction_row("EXT-COMMON2", F="WRITE"),
        _full_verdict_extraction_row("EXT-PRIORITY", F="NEGATIVO;WRITE"),
    ])
    batches = digestion_dir / "batches"
    keys_path = _keys_file(tmp_path, ["EXT-COMMON1", "EXT-COMMON2", "EXT-PRIORITY"])

    assert mds.main(["add-external", "--keys", str(keys_path)]) == 0
    new_chunk = batches / "d03.input.jsonl"
    lines = _read_jsonl_file(new_chunk)
    assert lines[0]["key"] == "EXT-PRIORITY"  # NEGATIVO is a priority facet, sorts first


# --------------------------------------------------------------------------
# (4) no network access anywhere (belt-and-suspenders)
# --------------------------------------------------------------------------

def test_no_network_calls_anywhere(monkeypatch):
    import urllib.request

    def _boom(*_a, **_k):
        raise AssertionError("network access attempted during offline test run")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    assert digestion_law.validate_digest(_valid_rec(), _valid_ext()) == []
