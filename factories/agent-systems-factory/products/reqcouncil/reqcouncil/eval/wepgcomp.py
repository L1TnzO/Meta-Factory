"""E2 industry corpora (WEPGCOMP + +Lugar): oracle loaders + curated transcript paths.

The oracle for each corpus is the **"Oracle" sheet** of `Requisitos - {corpus}.xlsx`
(sheets 2-3 = ChatGPT/DeepSeek outputs OF the WER-2025 study, NOT our ground truth).
Parsed with stdlib `zipfile` + `xml.etree` (no new dependency — measured 2026-07-06).

Loaders VALIDATE the MEASURED counts (46/34, 40/6, 24/10) and the {FUNC,NOTF} id
prefixes and refuse silently-wrong data instead of coping with it (the golden.py lesson).
The transcripts are the one-time-curated `.txt` (H6 §0): the H1 ingest parses them as-is.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from ..config import REPO_ROOT

DATA_ROOT = REPO_ROOT / "datasets" / "wepgcomp_maislugar"

WEPGCOMP = "wepgcomp"
MAISLUGAR = "maislugar"
CORPORA = (WEPGCOMP, MAISLUGAR)

_XLSX = {WEPGCOMP: "Requisitos - WEPGCOMP.xlsx", MAISLUGAR: "Requisitos - +Lugar.xlsx"}
_TRANSCRIPT = {WEPGCOMP: "transcript_wepgcomp.txt", MAISLUGAR: "transcript_maislugar.txt"}
STUDY_PROMPT = "prompt_wepgcomp_study.txt"  # E4 arm (b): the WER-2025 study prompt

# Measured 2026-07-06 (H6 relevance): the "Oracle" sheet id prefixes = {FUNC, NOTF}.
# These are the corrected counts the README now carries (the "~86/~64" were estimates).
EXPECTED = {
    WEPGCOMP: {"total": 46, "func": 40, "nfr": 6},
    MAISLUGAR: {"total": 34, "func": 24, "nfr": 10},
}

_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_NS = {"m": _M[1:-1]}
_FUNC, _NFR = "FUNC", "NOTF"


@dataclass(frozen=True)
class OracleItem:
    """One gold requirement from the Oracle sheet. `is_nfr` is derived from the id."""

    id: str  # FUNC01 | NOTF06
    text: str
    is_nfr: bool


def corpus_dir(data_root: Path | None = None) -> Path:
    return data_root or DATA_ROOT


def transcript_path(corpus: str, data_root: Path | None = None) -> Path:
    _require(corpus)
    return corpus_dir(data_root) / _TRANSCRIPT[corpus]


def study_prompt_path(data_root: Path | None = None) -> Path:
    return corpus_dir(data_root) / STUDY_PROMPT


def _require(corpus: str) -> None:
    if corpus not in CORPORA:
        raise ValueError(f"unknown corpus {corpus!r}; expected one of {CORPORA}")


def _shared_strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(f"{_M}t")) for si in root.findall("m:si", _NS)]


def _cell_text(cell: ET.Element, shared: list[str]) -> str:
    if cell.get("t") == "inlineStr":
        node = cell.find("m:is", _NS)
        return "".join(t.text or "" for t in node.iter(f"{_M}t")) if node is not None else ""
    v = cell.find("m:v", _NS)
    if v is None or v.text is None:
        return ""
    return shared[int(v.text)] if cell.get("t") == "s" else v.text


def _oracle_sheet_target(z: zipfile.ZipFile) -> str:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_target = {r.get("Id"): r.get("Target") for r in rels}
    for sheet in wb.findall("m:sheets/m:sheet", _NS):
        if sheet.get("name") == "Oracle":
            target = rid_target[sheet.get(f"{_R}id")]
            return target if target.startswith("xl/") else f"xl/{target}"
    raise ValueError("no 'Oracle' sheet in workbook (sheets 2-3 are study outputs, not gold)")


def _col(ref: str) -> str:
    return "".join(ch for ch in ref if ch.isalpha())


def _read_oracle_rows(xlsx_path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(xlsx_path) as z:
        shared = _shared_strings(z)
        sheet = ET.fromstring(z.read(_oracle_sheet_target(z)))
    rows: list[dict[str, str]] = []
    for row in sheet.findall("m:sheetData/m:row", _NS):
        cells = {_col(c.get("r", "")): _cell_text(c, shared) for c in row.findall("m:c", _NS)}
        rows.append(cells)
    return rows


def load_oracle(corpus: str, data_root: Path | None = None) -> list[OracleItem]:
    """The Oracle-sheet gold items, count/prefix-validated. Raises on any drift."""
    _require(corpus)
    rows = _read_oracle_rows(corpus_dir(data_root) / _XLSX[corpus])
    items: list[OracleItem] = []
    for i, row in enumerate(rows):
        rid = (row.get("A") or "").strip()
        text = (row.get("B") or "").strip()
        if rid == "ID" and (row.get("B") or "").strip().lower().startswith("descri"):
            continue  # header row
        if not rid and not text:
            continue  # trailing blank row
        if not rid or not text:
            raise ValueError(f"{corpus} oracle row {i}: malformed (id={rid!r} text={text!r})")
        if not (rid.startswith(_FUNC) or rid.startswith(_NFR)):
            raise ValueError(f"{corpus} oracle row {i}: unexpected id prefix {rid!r} "
                             f"(want {_FUNC}/{_NFR})")
        items.append(OracleItem(id=rid, text=text, is_nfr=rid.startswith(_NFR)))

    exp = EXPECTED[corpus]
    n_nfr = sum(1 for it in items if it.is_nfr)
    n_func = len(items) - n_nfr
    if (len(items), n_func, n_nfr) != (exp["total"], exp["func"], exp["nfr"]):
        raise ValueError(
            f"{corpus} oracle: expected total={exp['total']} func={exp['func']} "
            f"nfr={exp['nfr']}, found total={len(items)} func={n_func} nfr={n_nfr}"
        )
    return items
