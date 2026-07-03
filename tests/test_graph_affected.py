"""test_graph_affected — dep-graph affected-tests (dogfood D25a).

Proves `metafactory.graph.affected.affected_tests` is a graph-PRECISE replacement for the name-matching
heuristic in `metafactory.delegation.affected_tests`: it walks reverse IMPORTS reachability over a code
graph that discovers both the source tree and tests/, so only tests that actually (transitively) import a
changed module come back — not every test whose path happens to share a glob.

A tiny synthetic repo (leaf <- mid <- test_mid; leaf <- test_leaf; unrelated <- test_unrelated; orphan
imported by nobody) makes every case deterministic and isolated from the real repo's own graph shape.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from metafactory.graph.affected import affected_tests

REPO = Path(__file__).resolve().parents[1]


def _write(root: Path, relpath: str, text: str) -> None:
    p = root / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _make_repo(root: Path) -> None:
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


def test_leaf_change_returns_only_its_transitive_test_importers(tmp_path):
    _make_repo(tmp_path)
    result = affected_tests(tmp_path, ["src/metafactory/leaf.py"])
    # test_unrelated.py must NOT appear: it imports `unrelated`, not `leaf` (directly or transitively).
    assert result == ["tests/test_leaf.py", "tests/test_mid.py"]


def test_orphan_module_with_no_importers_returns_empty(tmp_path):
    _make_repo(tmp_path)
    assert affected_tests(tmp_path, ["src/metafactory/orphan.py"]) == []


def test_changed_test_file_includes_itself(tmp_path):
    _make_repo(tmp_path)
    result = affected_tests(tmp_path, ["tests/test_leaf.py"])
    assert result == ["tests/test_leaf.py"]


def test_multiple_changed_paths_union_dedup_sorted(tmp_path):
    _make_repo(tmp_path)
    result = affected_tests(
        tmp_path, ["src/metafactory/leaf.py", "src/metafactory/unrelated.py"],
    )
    assert result == ["tests/test_leaf.py", "tests/test_mid.py", "tests/test_unrelated.py"]


def test_nonexistent_and_non_python_changed_paths_are_skipped_not_crashed(tmp_path):
    _make_repo(tmp_path)
    result = affected_tests(
        tmp_path,
        ["src/metafactory/does_not_exist.py", "README.md", "src/metafactory/leaf.py"],
    )
    assert result == ["tests/test_leaf.py", "tests/test_mid.py"]


def test_cli_entry_point_prints_affected_tests(tmp_path):
    _make_repo(tmp_path)
    r = subprocess.run(
        [sys.executable, "-m", "metafactory.graph.affected", "--changed", "src/metafactory/leaf.py"],
        capture_output=True, text=True, cwd=str(tmp_path),
        env={"PYTHONPATH": str(REPO / "src")},
    )
    assert r.returncode == 0, r.stdout + r.stderr
    lines = r.stdout.strip().splitlines()
    assert lines == ["tests/test_leaf.py", "tests/test_mid.py"]
