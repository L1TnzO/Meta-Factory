"""Loaders for the Inter2US human-annotated pair files (the E0 ground truth).

The two corpora ship DIFFERENT schemas (measured, not assumed — H1 lesson):
- interview   `all_pairs_annotated.csv`: pandas dump with an unnamed index column;
  columns  ,Unnamed: 0,chunk_id,User Story,Chunk Text,Unnamed: 4,Score  -> 180 rows.
- system_desc `all_pairs_annotated.csv`:
  columns  Group,Chunk Index,Chunk Text,User Story,Coverage,Score,Similarity -> 580 rows.

`datasets/` is read-only ground truth; loaders VALIDATE counts and labels and refuse
silently-wrong data instead of coping with it.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ..config import REPO_ROOT

DATA_ROOT = REPO_ROOT / "datasets" / "inter2us" / "data"

INTERVIEW = "interview"
SYSTEM_DESC = "system_desc"
CORPORA = (INTERVIEW, SYSTEM_DESC)

_DIRS = {INTERVIEW: "public_interview", SYSTEM_DESC: "public_system_desc"}
EXPECTED_COUNTS = {INTERVIEW: 180, SYSTEM_DESC: 580}


@dataclass(frozen=True)
class Pair:
    corpus: str
    index: int  # 0-based position within the corpus file (stable: datasets/ is frozen)
    story: str
    chunk: str
    human: int  # ground-truth Score in {0,1}


def corpus_dir(corpus: str, data_root: Path | None = None) -> Path:
    return (data_root or DATA_ROOT) / _DIRS[corpus]


def system_prompt_path(corpus: str, data_root: Path | None = None) -> Path:
    return corpus_dir(corpus, data_root) / "system_prompt_v1_final_metric.txt"


def load_pairs(corpus: str, data_root: Path | None = None) -> list[Pair]:
    if corpus not in CORPORA:
        raise ValueError(f"unknown corpus {corpus!r}; expected one of {CORPORA}")
    path = corpus_dir(corpus, data_root) / "all_pairs_annotated.csv"
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    pairs: list[Pair] = []
    for i, row in enumerate(rows):
        story = (row.get("User Story") or "").strip()
        chunk = (row.get("Chunk Text") or "").strip()
        score = (row.get("Score") or "").strip()
        if not story or not chunk or score not in {"0", "1"}:
            raise ValueError(f"{path.name} row {i}: malformed pair (score={score!r})")
        pairs.append(Pair(corpus=corpus, index=i, story=story, chunk=chunk, human=int(score)))

    expected = EXPECTED_COUNTS[corpus]
    if len(pairs) != expected:
        raise ValueError(f"{path}: expected {expected} pairs, found {len(pairs)}")
    return pairs
