"""test_affected_report — selection-ratio digest (dogfood D25c).

Proves `metafactory.graph.affected_report.affected_report` composes `affected_tests` with a real
`tests/test_*.py` glob to produce a decidable "how much of the suite did we skip" number, and that its
CLI entry point prints a parseable count/ratio line.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from metafactory.graph.affected_report import affected_report

REPO = Path(__file__).resolve().parents[1]


def _write(root: Path, relpath: str, text: str) -> None:
    p = root / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _make_repo(root: Path) -> None:
    # same synthetic shape as tests/test_graph_affected.py: leaf <- mid <- test_mid; leaf <- test_leaf;
    # unrelated <- test_unrelated; orphan imported by nobody.
    _write(root, "src/metafactory/leaf.py", "def leaf_fn():\n    return 1\n")
    _write(root, "src/metafactory/mid.py",
           "from metafactory.leaf import leaf_fn\n\n\ndef mid_fn():\n    return leaf_fn()\n")
    _write(root, "src/metafactory/unrelated.py", "def other():\n    return 2\n")
    _write(root, "src/metafactory/orphan.py", "def orphan_fn():\n    return 3\n")
    _write(root, "tests/test_leaf.py",
           "from metafactory.leaf import leaf_fn\n\n\ndef test_leaf():\n    assert leaf_fn() == 1\n")
    _write(root, "tests/test_mid.py",
           "from metafactory.mid import mid_fn\n\n\ndef test_mid():\n    assert mid_fn() == 1\n")
    _write(root, "tests/test_unrelated.py",
           "from metafactory.unrelated import other\n\n\ndef test_unrelated():\n    assert other() == 2\n")


def test_report_shape_has_expected_keys_and_types(tmp_path):
    _make_repo(tmp_path)
    report = affected_report(tmp_path, ["src/metafactory/leaf.py"])
    assert isinstance(report["affected"], list)
    assert isinstance(report["total"], int)
    assert isinstance(report["affected_count"], int)
    assert isinstance(report["ratio"], float)


def test_ratio_matches_affected_over_total_for_a_real_scenario(tmp_path):
    _make_repo(tmp_path)
    report = affected_report(tmp_path, ["src/metafactory/leaf.py"])
    # leaf.py is transitively imported by test_leaf.py and test_mid.py, not test_unrelated.py.
    assert report["affected"] == ["tests/test_leaf.py", "tests/test_mid.py"]
    assert report["affected_count"] == 2
    assert report["total"] == 3  # test_leaf.py, test_mid.py, test_unrelated.py
    assert report["ratio"] == report["affected_count"] / report["total"]
    assert report["ratio"] == 2 / 3


def test_total_matches_independent_glob_of_real_repo_tests(tmp_path):
    # against the REAL Meta-Factory repo (not the synthetic tmp_path one): total must equal an
    # independently-computed glob count, so this assertion doesn't rot silently as the suite grows.
    expected_total = len(sorted(REPO.joinpath("tests").rglob("test_*.py")))
    report = affected_report(REPO, [])
    assert report["total"] == expected_total


def test_empty_changed_paths_returns_no_affected_and_zero_ratio(tmp_path):
    _make_repo(tmp_path)
    report = affected_report(tmp_path, [])
    assert report["affected"] == []
    assert report["affected_count"] == 0
    assert report["ratio"] == 0.0
    assert report["total"] == 3


def test_zero_total_does_not_divide_by_zero(tmp_path):
    # an empty repo (no tests/ dir at all): total == 0 must yield ratio == 0.0, not a crash.
    report = affected_report(tmp_path, ["anything.py"])
    assert report["total"] == 0
    assert report["ratio"] == 0.0


def test_cli_entry_point_prints_affected_and_ratio_line(tmp_path):
    _make_repo(tmp_path)
    r = subprocess.run(
        [sys.executable, "-m", "metafactory.graph.affected_report",
         "--changed", "src/metafactory/leaf.py"],
        capture_output=True, text=True, cwd=str(tmp_path),
        env={"PYTHONPATH": str(REPO / "src")},
    )
    assert r.returncode == 0, r.stdout + r.stderr
    lines = r.stdout.strip().splitlines()
    assert lines[0] == "tests/test_leaf.py"
    assert lines[1] == "tests/test_mid.py"
    assert lines[-1] == "affected: 2/3 (66.7%)"
