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


# ── H-4 (COLUMN-MAINT, COUNCIL-360 §4.1): corpus expandido + entropía + anti-slopsquatting ────────

from metafactory.verify.checks.security_scan import (  # noqa: E402
    _shannon_bits, declared_deps, dep_problems, scan_text)


class TestH4EntropyDetector:
    def test_high_entropy_quoted_blob_fires(self):
        hits = scan_text('x = "kJ8vQz2xW9pLmN4rT6yB3cD5fG7hSaE0uIoPqRsXy1Zw"')
        assert any(h.startswith("high-entropy-string") for h in hits)

    def test_hex_digest_is_exempt_declared_blind_spot(self):
        # git/sha digests saturate the tree — pure hex is a DECLARED exemption, not a silent one
        hits = scan_text('pin = "9f2b6a1c4e8d3f7a0b5c9d1e2f3a4b5c6d7e8f90"')
        assert not any(h.startswith("high-entropy-string") for h in hits)

    def test_low_entropy_long_string_does_not_fire(self):
        hits = scan_text('x = "' + "abcabcabc" * 5 + '"')
        assert not any(h.startswith("high-entropy-string") for h in hits)

    def test_new_format_anthropic_fires(self):
        assert any(h.startswith("anthropic-key")
                   for h in scan_text('k = "sk-ant-api03-FAKE-EXAMPLE-KEY-000000000000"'))


class TestH4DepAllowlist:
    def _root(self, tmp_path, gradle_dep: str):
        (tmp_path / "docs" / "reference").mkdir(parents=True)
        (tmp_path / "docs" / "reference" / "dep-allowlist.yml").write_text(
            "gradle:\n  - org.postgresql:postgresql\nnpm:\n  - typescript\n", encoding="utf-8")
        b = tmp_path / "factories" / "f" / "build" / "product"
        b.mkdir(parents=True)
        (b / "build.gradle.kts").write_text(
            f'dependencies {{ implementation("{gradle_dep}:1.0") }}\n', encoding="utf-8")
        (b / "package.json").write_text('{"devDependencies": {"typescript": "^5"}}', encoding="utf-8")
        return tmp_path

    def test_allowed_deps_are_green(self, tmp_path):
        root = self._root(tmp_path, "org.postgresql:postgresql")
        assert declared_deps(root) == {"gradle": {"org.postgresql:postgresql"}, "npm": {"typescript"}}
        assert dep_problems(root) == []

    def test_hallucinated_dep_is_red(self, tmp_path):
        root = self._root(tmp_path, "com.evil:left-pad-ai")
        probs = dep_problems(root)
        assert probs and "left-pad-ai" in probs[0] and "alucinado" in probs[0]

    def test_missing_allowlist_is_na_not_red(self, tmp_path):
        root = self._root(tmp_path, "com.evil:left-pad-ai")
        (root / "docs" / "reference" / "dep-allowlist.yml").unlink()
        assert dep_problems(root) == []  # N/A honesto (el main lo reporta como N/A, no verde fingido)
