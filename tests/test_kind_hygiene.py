"""test_kind_hygiene — the tooth for D-3 (COUNCIL-360 §5): freeze the check-kind vocabulary, mirror
of `role_hygiene`/ADR-020. Two-sided over hermetic tmp roots + a positive over the real repo:
  - GREEN: kinds used across the two check surfaces (station YAMLs + factory-spec proof_checks) are
    all inside the closed `registry.KINDS` vocabulary;
  - RED: a domain-named kind (`kotlin_scan`) in a station YAML, or a made-up kind in a factory-spec's
    proof_checks, flips the gate red and names the offending file+kind;
  - usage error with no argv -> 2;
  - the real repo is clean (the freeze already holds over every real station/spec).
"""
from __future__ import annotations

from pathlib import Path

from metafactory._seed import repo_root
from metafactory.verify.checks import kind_hygiene


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_green_closed_vocabulary(tmp_path, capsys):
    _write(
        tmp_path / "src" / "metafactory" / "stations" / "m00.yml",
        "id: m00\nchecks:\n  - { name: a, kind: product_env }\n  - { name: b, kind: command }\n",
    )
    _write(
        tmp_path / "factories" / "acme" / "factory.spec.yml",
        "domain:\n  station_sequence:\n"
        "    - id: s0\n      proof_checks:\n        - { name: p, kind: pytest }\n",
    )
    rc = kind_hygiene.main([str(tmp_path)])
    assert rc == 0
    assert "OK kind hygiene" in capsys.readouterr().out


def test_red_domain_named_kind_in_station_yml(tmp_path, capsys):
    _write(
        tmp_path / "src" / "metafactory" / "stations" / "m00.yml",
        "id: m00\nchecks:\n  - { name: a, kind: kotlin_scan }\n",
    )
    rc = kind_hygiene.main([str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "kotlin_scan" in out
    assert "m00.yml" in out


def test_red_made_up_kind_in_factory_spec(tmp_path, capsys):
    _write(
        tmp_path / "factories" / "acme" / "factory.spec.yml",
        "domain:\n  station_sequence:\n"
        "    - id: s0\n      proof_checks:\n        - { name: p, kind: made_up_kind }\n",
    )
    rc = kind_hygiene.main([str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "made_up_kind" in out
    assert "factory.spec.yml" in out


def test_usage_error_with_no_argv():
    assert kind_hygiene.main([]) == 2


def test_real_repo_is_clean():
    assert kind_hygiene.main([str(repo_root())]) == 0
