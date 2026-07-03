"""affected_report — selection-ratio digest over `affected.affected_tests` (dogfood D25c).

`affected_tests` answers "which tests are affected"; this module answers the decidable follow-up the S2
loop / S3 review actually needs: "how much of the whole suite did we SKIP?" It composes `affected_tests`
(no new graph logic) with a real filesystem glob over `tests/test_*.py` as the "whole suite" denominator,
and exposes both a small dict API and a `python3 -m metafactory.graph.affected_report --changed <path>...`
CLI entry point that prints a human-eyeballable count/ratio line.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .affected import TEST_DISCOVERY_ROOT, affected_tests


def discover_all_tests(repo_root: Path | str) -> list[str]:
    """Every `tests/test_*.py` file under `repo_root`, as sorted repo-relative POSIX path strings — the
    "whole suite" denominator for the selection ratio. A real filesystem glob (not graph-derived), so it
    counts test files even if they have no IMPORTS edges at all (e.g. no local imports)."""
    root = Path(repo_root)
    test_dir = root / TEST_DISCOVERY_ROOT
    if not test_dir.is_dir():
        return []
    return sorted(
        p.relative_to(root).as_posix()
        for p in test_dir.rglob("test_*.py")
    )


def affected_report(repo_root: Path | str, changed_paths: list[str]) -> dict:
    """The selection-ratio report: which tests are affected, how many total tests exist, and what
    fraction of the suite that is — so a caller can decide "is it safe to skip the rest".

    Keys: `affected` (sorted list[str]), `total` (int, all discovered tests), `affected_count` (int),
    `ratio` (float, `affected_count / total`, `0.0` if `total == 0` — no division by zero).
    """
    affected = affected_tests(repo_root, changed_paths)
    total = len(discover_all_tests(repo_root))
    affected_count = len(affected)
    ratio = (affected_count / total) if total else 0.0
    return {
        "affected": affected,
        "total": total,
        "affected_count": affected_count,
        "ratio": ratio,
    }


# ── CLI (S2/S3 eyeball entry point) ───────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m metafactory.graph.affected_report",
        description="Print the tests/test_*.py files affected by the given changed paths, plus the "
                    "selection ratio (how much of the whole suite that is).",
    )
    parser.add_argument("--changed", nargs="+", required=True, metavar="PATH",
                        help="one or more changed file paths (relative to cwd, or absolute)")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    report = affected_report(repo_root, args.changed)
    for test_path in report["affected"]:
        print(test_path)
    percent = report["ratio"] * 100
    print(f"affected: {report['affected_count']}/{report['total']} ({percent:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
