"""test_security_scan — the heritable secret/supply-chain gate (ADR-017 §4, DELEGATION-HARNESS Fase 3).

Two-sided by blocking: credential formats are caught; clean text is clean; the substrate scans clean and the
planted fixture fires (decorative gate would be a worse failure than an honest red).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from metafactory.verify.checks import security_scan

REPO = Path(__file__).resolve().parents[1]


def test_scan_catches_credential_formats():
    assert security_scan.scan_text("aws_access_key_id = AKIAIOSFODNN7EXAMPLE")
    assert security_scan.scan_text("-----BEGIN RSA PRIVATE KEY-----")
    assert security_scan.scan_text('password = "supersecretvalue123"')
    assert security_scan.scan_text("token = ghp_" + "a" * 36)


def test_scan_clean_text_is_clean():
    assert security_scan.scan_text("def f(x: int) -> int:\n    return x + 1") == []
    assert security_scan.scan_text("# a regex AKIA[0-9A-Z]{16} is not itself a key") == []
    assert security_scan.scan_text('password = ""  # empty / placeholder') == []


def test_gate_two_sided_on_real_repo():
    # GREEN substrate + RED planted fixture both present → exit 0 with a live tooth.
    r = subprocess.run([sys.executable, "-m", "metafactory.verify.checks.security_scan", str(REPO)],
                       capture_output=True, text=True, env={"PYTHONPATH": str(REPO / "src")})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sustrato limpio" in r.stdout and "diente RED vivo" in r.stdout


def test_fixture_actually_fires():
    fx = REPO / "tests/fixtures/security/planted_secrets.txt"
    hits = security_scan.scan_text(fx.read_text(encoding="utf-8"))
    labels = {h.split("@")[0] for h in hits}
    assert {"aws-access-key-id", "private-key-block", "generic-secret-assign"} <= labels
