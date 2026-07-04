"""test_mutation_escape — the mutation-testing instrument itself (E4/H-3, COUNCIL-360 §6.4.5).

Hermetic: every target/gate here is a TOY built in `tmp_path`, never a real repo file. Proves, by
blocking: (1) comment lines are excluded from candidate sites, kotlin operators are detected; (2) a
mutant swaps exactly the named occurrence and nothing else; (3) site selection is deterministic per
seed; (4) a real two-sided campaign — a COVERED branch's mutant is KILLED, an UNCOVERED branch's mutant
ESCAPES — with the escape_rate computed correctly and the target file's bytes restored; (5) restoration
holds even when every mutant is killed by an always-failing gate; (6) a bare usage error exits 2.
"""
from __future__ import annotations

import sys
from pathlib import Path

from metafactory.verify.mutation import (
    KT_OPERATORS,
    PY_OPERATORS,
    apply_mutant,
    main,
    mutant_sites,
    run_campaign,
    select_sites,
)


def test_mutant_sites_skips_comment_lines_python():
    source = "if a == b:\n    pass\n# a == b (comment, must not count)\n"
    op_index = PY_OPERATORS.index(("==", "!="))
    matches = [s for s in mutant_sites(source, PY_OPERATORS) if s["op_index"] == op_index]
    assert len(matches) == 1
    assert matches[0] == {"line_no": 1, "op_index": op_index, "occurrence_in_line": 0}


def test_mutant_sites_skips_comment_lines_kotlin_and_detects_and():
    source = "if (a && b) { return }\n// a && b (comment, must not count)\n"
    op_index = KT_OPERATORS.index(("&&", "||"))
    matches = [s for s in mutant_sites(source, KT_OPERATORS) if s["op_index"] == op_index]
    assert len(matches) == 1
    assert matches[0]["line_no"] == 1


def test_mutant_sites_string_only_line_is_skipped():
    source = '"a == b, just a string"\nif a == b:\n    pass\n'
    op_index = PY_OPERATORS.index(("==", "!="))
    matches = [s for s in mutant_sites(source, PY_OPERATORS) if s["op_index"] == op_index]
    assert len(matches) == 1
    assert matches[0]["line_no"] == 2


def test_mutant_sites_counts_multiple_occurrences_on_one_line():
    source = "if a == b == c:\n"
    op_index = PY_OPERATORS.index(("==", "!="))
    matches = [s for s in mutant_sites(source, PY_OPERATORS) if s["op_index"] == op_index]
    assert [s["occurrence_in_line"] for s in matches] == [0, 1]


def test_apply_mutant_swaps_exactly_the_named_occurrence():
    source = "a = x == y\nb = p == q\nc = m == n\n"
    op_index = PY_OPERATORS.index(("==", "!="))
    site = {"line_no": 2, "op_index": op_index, "occurrence_in_line": 0}
    mutated = apply_mutant(source, site, PY_OPERATORS)
    lines = mutated.splitlines()
    assert lines[0] == "a = x == y"
    assert lines[1] == "b = p != q"
    assert lines[2] == "c = m == n"


def test_apply_mutant_selects_the_right_occurrence_among_several():
    source = "if a == b == c:\n"
    op_index = PY_OPERATORS.index(("==", "!="))
    mutated_first = apply_mutant(source, {"line_no": 1, "op_index": op_index, "occurrence_in_line": 0}, PY_OPERATORS)
    mutated_second = apply_mutant(source, {"line_no": 1, "op_index": op_index, "occurrence_in_line": 1}, PY_OPERATORS)
    assert mutated_first == "if a != b == c:\n"
    assert mutated_second == "if a == b != c:\n"


def test_select_sites_is_deterministic_per_seed():
    sites = [{"line_no": i, "op_index": 0, "occurrence_in_line": 0} for i in range(10)]
    a = select_sites(sites, seed=7, limit=5)
    b = select_sites(sites, seed=7, limit=5)
    assert a == b
    assert len(a) == 5

    c = select_sites(sites, seed=99, limit=5)
    assert [s["line_no"] for s in a] != [s["line_no"] for s in c]


def test_select_sites_returns_all_when_fewer_than_limit():
    sites = [{"line_no": i, "op_index": 0, "occurrence_in_line": 0} for i in range(3)]
    assert len(select_sites(sites, seed=7, limit=12)) == 3


_CALC_SOURCE = (
    "def covered(a, b):\n"
    "    if a == b:\n"
    "        return \"equal\"\n"
    "    return \"different\"\n"
    "\n"
    "\n"
    "def uncovered(x):\n"
    "    if x >= 0:\n"
    "        return \"non-negative\"\n"
    "    return \"negative\"\n"
)

_TEST_CALC_SOURCE = (
    "from calc import covered\n"
    "\n"
    "\n"
    "def test_covered_equal():\n"
    "    assert covered(1, 1) == \"equal\"\n"
    "\n"
    "\n"
    "def test_covered_different():\n"
    "    assert covered(1, 2) == \"different\"\n"
)


def test_run_campaign_kills_covered_and_escapes_uncovered(tmp_path):
    target = tmp_path / "calc.py"
    target.write_text(_CALC_SOURCE, encoding="utf-8")
    (tmp_path / "test_calc.py").write_text(_TEST_CALC_SOURCE, encoding="utf-8")

    gate_cmd = [sys.executable, "-m", "pytest", "-q", "test_calc.py"]
    result = run_campaign(target, gate_cmd, operators=PY_OPERATORS, seed=7, limit=12, cwd=tmp_path)

    assert result["target"] == str(target)
    assert result["sites_total"] == 2      # the "==" in covered() and the ">=" in uncovered()
    assert result["tested"] == 2
    assert result["killed"] == 1           # mutating covered()'s "==" flips a behavior the gate asserts
    assert result["escaped"] == 1          # mutating uncovered()'s ">=" is never exercised by the gate
    assert result["escape_rate"] == 0.5
    assert len(result["escaped_sites"]) == 1
    assert result["escaped_sites"][0]["before"] == ">="
    assert result["gate_cmd"] == gate_cmd
    assert result["seed"] == 7

    # the mutation instrument must NEVER leave a mutant on disk.
    assert target.read_bytes() == _CALC_SOURCE.encode("utf-8")


def test_run_campaign_restores_bytes_even_when_gate_always_fails(tmp_path):
    target = tmp_path / "calc.py"
    target.write_text(_CALC_SOURCE, encoding="utf-8")
    original = target.read_bytes()

    gate_cmd = [sys.executable, "-c", "raise SystemExit(3)"]
    result = run_campaign(target, gate_cmd, operators=PY_OPERATORS, seed=7, limit=12, cwd=tmp_path)

    assert result["tested"] == 2
    assert result["killed"] == 2
    assert result["escaped"] == 0
    assert result["escape_rate"] == 0.0
    assert target.read_bytes() == original


def test_main_usage_error_exits_2():
    assert main([]) == 2


def test_main_missing_target_exits_2(tmp_path):
    missing = tmp_path / "nope.py"
    assert main([str(missing), "python", "5", "7", "--", sys.executable, "-c", "pass"]) == 2


def test_main_runs_campaign_and_exits_0(tmp_path, capsys):
    target = tmp_path / "calc.py"
    target.write_text(_CALC_SOURCE, encoding="utf-8")
    (tmp_path / "test_calc.py").write_text(_TEST_CALC_SOURCE, encoding="utf-8")

    rc = main([str(target), "python", "12", "7", "--", sys.executable, "-m", "pytest", "-q", "test_calc.py"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "escape_rate=" in out
    assert target.read_bytes() == _CALC_SOURCE.encode("utf-8")
