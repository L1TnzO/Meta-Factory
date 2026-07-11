"""Unit tests for metafactory.verify.report (the verdict bus, I-7)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from metafactory._seed import load_seed_verifier
from metafactory.verify import report
from metafactory.verify.report import (
    Verdict,
    _extract_fileline,
    format_verdict,
    from_proof,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _passing_proof(n_checks: int = 3) -> dict:
    checks = [{"name": f"chk{i}", "cmd": ["x"], "exit": 0} for i in range(n_checks)]
    return {
        "station": "s1",
        "passed": True,
        "proof_sha": "abc",
        "log_path": "",
        "checks": checks,
    }


def _failing_proof(n_fail: int = 8, n_pass: int = 3) -> dict:
    checks = (
        [{"name": f"ok{i}", "cmd": ["x"], "exit": 0} for i in range(n_pass)]
        + [{"name": f"fail{i}", "cmd": ["x"], "exit": 1} for i in range(n_fail)]
    )
    return {
        "station": "s1",
        "passed": False,
        "proof_sha": "abc",
        "log_path": "",
        "checks": checks,
    }


# ── from_proof ────────────────────────────────────────────────────────────────

class TestFromProof:
    def test_passing_proof_status_is_pass(self):
        v = from_proof("test", _passing_proof())
        assert v.status == "PASS"
        assert v.exit_code == 0

    def test_failing_proof_status_is_fail(self):
        v = from_proof("test", _failing_proof())
        assert v.status == "FAIL"
        assert v.exit_code == 1

    def test_counts_reflect_each_check(self):
        proof = _passing_proof(3)
        v = from_proof("test", proof)
        assert len(v.counts) == 3

    def test_passing_count_entries_say_ok(self):
        v = from_proof("test", _passing_proof(2))
        assert all("ok" in c for c in v.counts)

    def test_failing_count_entries_show_exit_code(self):
        proof = _failing_proof(n_fail=2, n_pass=0)
        v = from_proof("test", proof)
        assert any("FAIL" in c for c in v.counts)

    def test_failures_capped_at_max_fail(self):
        proof = _failing_proof(n_fail=10, n_pass=0)
        v = from_proof("test", proof, max_fail=5)
        assert len(v.failures) <= 5

    def test_no_failures_when_passed(self):
        v = from_proof("test", _passing_proof())
        assert v.failures == []

    def test_summary_says_all_green_on_pass(self):
        v = from_proof("test", _passing_proof(3))
        assert "green" in v.summary.lower() or "all" in v.summary.lower()

    def test_summary_says_red_count_on_fail(self):
        v = from_proof("test", _failing_proof(2, 1))
        assert "red" in v.summary.lower() or "2" in v.summary

    def test_next_pass_used_on_pass(self):
        v = from_proof("test", _passing_proof(), next_pass="go next", next_fail="fix it")
        assert v.next_action == "go next"

    def test_next_fail_used_on_fail(self):
        v = from_proof("test", _failing_proof(), next_pass="go next", next_fail="fix it")
        assert v.next_action == "fix it"

    def test_empty_checks_gives_fail(self):
        proof = {"station": "s", "passed": False, "proof_sha": "", "log_path": "", "checks": []}
        v = from_proof("test", proof)
        assert v.status == "FAIL"

    def test_verb_is_preserved(self):
        v = from_proof("MyVerb", _passing_proof())
        assert v.verb == "MyVerb"

    def test_log_path_read_for_fileline(self, tmp_path):
        """When a log file exists, from_proof reads it to extract file:line info."""
        log = tmp_path / "test.log"
        log.write_text(
            "## check=fail0 exit=1 cmd=x\n"
            '--- stdout ---\nFile "/home/user/src/module.py", line 42\n'
            "--- stderr ---\n",
            encoding="utf-8",
        )
        proof = _failing_proof(n_fail=1, n_pass=0)
        proof["log_path"] = str(log)
        v = from_proof("test", proof)
        # The failure should contain location info
        assert v.failures
        assert "module.py:42" in v.failures[0] or "fail0" in v.failures[0]


# ── format_verdict ────────────────────────────────────────────────────────────

class TestFormatVerdict:
    def test_bounded_at_10_lines_for_many_failures(self):
        proof = _failing_proof(n_fail=20, n_pass=0)
        v = from_proof("test", proof, max_fail=5)
        text = format_verdict(v)
        assert len(text.splitlines()) <= 10

    def test_no_stdout_or_stderr_in_output(self):
        proof = _failing_proof()
        v = from_proof("test", proof)
        text = format_verdict(v)
        assert "stdout" not in text
        assert "stderr" not in text

    def test_contains_veredicto_line(self):
        v = from_proof("run", _passing_proof())
        text = format_verdict(v)
        assert text.startswith("VERDICT")

    def test_contains_resumen_line(self):
        v = from_proof("run", _passing_proof())
        text = format_verdict(v)
        assert "SUMMARY" in text

    def test_contains_conteos_line(self):
        v = from_proof("run", _passing_proof())
        text = format_verdict(v)
        assert "COUNTS" in text

    def test_fallos_absent_on_pass(self):
        v = from_proof("run", _passing_proof())
        text = format_verdict(v)
        assert "FAILURES" not in text

    def test_fallos_present_on_fail(self):
        v = from_proof("run", _failing_proof(1, 0))
        text = format_verdict(v)
        assert "FAILURES" in text

    def test_artifact_line_present_when_set(self):
        v = Verdict(
            verb="v", status="PASS", exit_code=0,
            summary="ok", artifact="/tmp/log.txt", next_action=""
        )
        text = format_verdict(v)
        assert "ARTIFACT" in text and "/tmp/log.txt" in text

    def test_proximo_line_present_when_set(self):
        v = Verdict(
            verb="v", status="PASS", exit_code=0,
            summary="ok", next_action="do X"
        )
        text = format_verdict(v)
        assert "NEXT" in text and "do X" in text

    def test_proximo_line_absent_when_empty(self):
        v = Verdict(verb="v", status="PASS", exit_code=0, summary="ok")
        text = format_verdict(v)
        assert "NEXT" not in text

    def test_pass_shows_exit_0(self):
        v = from_proof("run", _passing_proof())
        text = format_verdict(v)
        assert "exit 0" in text

    def test_fail_shows_exit_1(self):
        v = from_proof("run", _failing_proof())
        text = format_verdict(v)
        assert "exit 1" in text


# ── _extract_fileline ─────────────────────────────────────────────────────────

class TestExtractFileline:
    def _make_log(self, check_name: str, section_body: str) -> str:
        return f"## check={check_name} exit=1 cmd=x\n{section_body}\n"

    def test_returns_none_when_check_not_found(self):
        result = _extract_fileline("## check=other exit=1 cmd=x\n", "missing")
        assert result is None

    def test_prefers_real_path_over_frozen_frame(self):
        """Real source path should be preferred over <frozen ...> pseudo-frame."""
        log = (
            "## check=mycheck exit=1 cmd=x\n"
            '--- stdout ---\n'
            'File "<frozen importlib._bootstrap>", line 999\n'
            'File "/real/src/module.py", line 55\n'
            "--- stderr ---\n"
        )
        result = _extract_fileline(log, "mycheck")
        assert result is not None
        assert "module.py:55" in result
        assert "frozen" not in result

    def test_picks_deepest_real_frame(self):
        """The deepest (last) real frame is the actual error site."""
        log = (
            "## check=mycheck exit=1 cmd=x\n"
            '--- stdout ---\n'
            'File "/src/top.py", line 10\n'
            'File "/src/bottom.py", line 42\n'
            "--- stderr ---\n"
        )
        result = _extract_fileline(log, "mycheck")
        assert result is not None
        assert "bottom.py:42" in result

    def test_fileline_pattern_matched(self):
        log = (
            "## check=chk exit=1 cmd=x\n"
            "--- stdout ---\n"
            "src/module.py:77: AssertionError\n"
            "--- stderr ---\n"
        )
        result = _extract_fileline(log, "chk")
        assert result is not None
        assert "module.py" in result

    def test_frozen_only_falls_back_gracefully(self):
        """If only frozen frames exist and no real path found, fallback returns a line
        or None — but never crashes, and never returns a path starting with '<'."""
        log = (
            "## check=chk exit=1 cmd=x\n"
            "--- stdout ---\n"
            "some error message here\n"
            "--- stderr ---\n"
        )
        # No traceback frames at all — should return the last non-header line or None
        result = _extract_fileline(log, "chk")
        # Must not raise; if something is returned it should be a short string
        if result is not None:
            assert not result.startswith("<")
            assert len(result) <= 80

    def test_section_scoped_to_named_check(self):
        """Extracting from a section ignores lines from other check sections."""
        log = (
            "## check=other exit=1 cmd=x\n"
            'File "/src/other.py", line 99\n'
            "## check=target exit=1 cmd=x\n"
            'File "/src/target.py", line 5\n'
        )
        result = _extract_fileline(log, "target")
        assert result is not None
        assert "target.py:5" in result
        assert "other.py" not in (result or "")

    def test_real_proof_log_with_seed_verifier(self, tmp_path):
        """Integration: from_proof reads an actual log produced by the seed verifier."""
        v = load_seed_verifier()
        proof = v.verify_station(
            "fail_station",
            [{"name": "will_fail", "cmd": [sys.executable, "-c", "import sys; sys.exit(1)"]}],
            tmp_path,
        )
        verdict = from_proof("test", proof)
        assert verdict.status == "FAIL"
        assert verdict.failures  # at least one failure entry
