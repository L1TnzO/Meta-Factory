"""mutation — E4/H-3 (COUNCIL-360 §6.4.5): the escape-rate instrument.

"App verificada" today only means "passed the DECLARED gates" — the escape rate (what fraction of
single-operator defects the gates actually KILL) is UNKNOWN. This module is a small, deterministic,
stdlib-only v1 mutation-testing instrument (pitest-class for Kotlin sources, mutmut-class for Python
sources): it seeds ONE operator mutation at a time into a target file, re-runs a caller-supplied gate
command, and counts a mutant as KILLED iff the gate exits non-zero (a timeout is also a KILL — a hung
gate is a block, not a pass). What survives (gate stays green) is ESCAPED — the honest reading, since a
mutant nobody can see is by definition a no-op.

v1 does no real parsing: a "site" is a textual occurrence of an operator token on a line that is not a
whole-line comment or a whole-line string literal. This under-approximates (misses operators split
across lines) and over-approximates (a token inside a partial string/docstring on a code line may still
be flagged) — both are accepted v1 honesty, not hidden: an unreachable/no-op mutant only shows up as an
ESCAPE, which is exactly the measurement this instrument exists to produce.

Runs via `python -m metafactory.verify.mutation` (H-6: no new CLI verb; `cli.py` does not grow)."""
from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

# v1 single-operator set for generated/hand-written PYTHON sources, in THIS fixed order (index is part
# of a site's identity, so the order is load-bearing — do not reorder existing entries).
PY_OPERATORS: list[tuple[str, str]] = [
    ("==", "!="),
    ("!=", "=="),
    (" < ", " >= "),
    (" > ", " <= "),
    ("<=", ">"),
    (">=", "<"),
    (" and ", " or "),
    (" or ", " and "),
    ("return True", "return False"),
    ("return False", "return True"),
]

# v1 single-operator set for generated KOTLIN sources, in THIS fixed order.
KT_OPERATORS: list[tuple[str, str]] = [
    ("==", "!="),
    ("!=", "=="),
    ("&&", "||"),
    ("||", "&&"),
    (" > ", " <= "),
    (" < ", " >= "),
    ("true", "false"),
]


def _is_comment_or_string_line(stripped: str) -> bool:
    """A line whose visible content is entirely a comment or a bare string literal — the v1 filter
    (no full parser, so this is a heuristic, not a guarantee): a whole-line comment (# or //) or a line
    that both starts and ends with the same quote marker (triple-double, triple-single, double, single)."""
    if not stripped:
        return False
    if stripped.startswith("#") or stripped.startswith("//"):
        return True
    for quote in ('"""', "'''", '"', "'"):
        if stripped.startswith(quote) and stripped.endswith(quote) and len(stripped) >= 2 * len(quote):
            return True
    return False


def mutant_sites(source: str, operators: list[tuple[str, str]]) -> list[dict]:
    """Every candidate mutation site in `source`: `{"line_no", "op_index", "occurrence_in_line"}`.
    `line_no` is 1-based. `occurrence_in_line` is the 0-based index of this occurrence AMONG matches of
    THIS SAME operator on this line (so a line with two `==` yields two sites, occurrence 0 and 1).
    Lines that are whole-line comments or whole-line string literals are skipped entirely (v1 honesty:
    this is a textual heuristic, not a parser — see module docstring)."""
    sites: list[dict] = []
    for line_no, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if _is_comment_or_string_line(stripped):
            continue
        for op_index, (before, _after) in enumerate(operators):
            occurrence = 0
            start = 0
            while True:
                pos = line.find(before, start)
                if pos == -1:
                    break
                sites.append({"line_no": line_no, "op_index": op_index, "occurrence_in_line": occurrence})
                occurrence += 1
                start = pos + len(before)
    return sites


def apply_mutant(source: str, site: dict, operators: list[tuple[str, str]]) -> str:
    """Return `source` with EXACTLY the one occurrence named by `site` swapped (that site's line, the
    nth occurrence of that operator's `before` token, replaced with its `after`). Reversible by
    construction: the caller owns file IO and can always restore the original text/bytes."""
    lines = source.splitlines(keepends=True)
    line = lines[site["line_no"] - 1]
    before, after = operators[site["op_index"]]
    target_occurrence = site["occurrence_in_line"]

    count = 0
    start = 0
    while True:
        pos = line.find(before, start)
        if pos == -1:
            raise ValueError(f"mutation site not found in source: {site!r}")
        if count == target_occurrence:
            line = line[:pos] + after + line[pos + len(before):]
            break
        count += 1
        start = pos + len(before)

    lines[site["line_no"] - 1] = line
    return "".join(lines)


def select_sites(sites: list[dict], *, seed: int, limit: int) -> list[dict]:
    """Deterministic sample: shuffle a copy of `sites` with `random.Random(seed)`, then take the first
    `limit` (all of them if there are fewer than `limit`). Same seed -> same selection, always."""
    pool = list(sites)
    random.Random(seed).shuffle(pool)
    return pool[:limit]


def run_campaign(
    target: Path,
    gate_cmd: list[str],
    *,
    operators: list[tuple[str, str]],
    seed: int = 7,
    limit: int = 12,
    cwd: Path | None = None,
    timeout_s: int = 300,
) -> dict:
    """Run one mutation campaign against a single `target` file: enumerate sites, deterministically
    select up to `limit`, and for each — write the mutant, run `gate_cmd`, classify KILLED (exit != 0,
    a timeout counts as KILLED too — a hung gate is a block) or ESCAPED (gate stayed green) — then
    ALWAYS restore the target's original bytes (in a `finally`, byte-verified; a restoration failure
    raises rather than silently leaving a mutant on disk)."""
    target = Path(target)
    original_bytes = target.read_bytes()
    source = original_bytes.decode("utf-8")
    run_cwd = Path(cwd) if cwd is not None else target.parent

    sites = mutant_sites(source, operators)
    selected = select_sites(sites, seed=seed, limit=limit)
    killed = 0
    escaped_sites: list[dict] = []

    try:
        for site in selected:
            mutated_source = apply_mutant(source, site, operators)
            target.write_bytes(mutated_source.encode("utf-8"))
            try:
                proc = subprocess.run(gate_cmd, cwd=str(run_cwd), timeout=timeout_s, capture_output=True, text=True)
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                rc = 124  # a hung gate is a block: counts as KILLED, never a silent pass
            if rc != 0:
                killed += 1
            else:
                before, after = operators[site["op_index"]]
                escaped_sites.append({
                    "line_no": site["line_no"],
                    "op_index": site["op_index"],
                    "before": before,
                    "after": after,
                })
    finally:
        target.write_bytes(original_bytes)
        if target.read_bytes() != original_bytes:
            raise RuntimeError(f"mutation instrument failed to restore original bytes of {target}")

    tested = len(selected)
    escaped = len(escaped_sites)
    return {
        "target": str(target),
        "sites_total": len(sites),
        "tested": tested,
        "killed": killed,
        "escaped": escaped,
        "escape_rate": (escaped / tested) if tested else 0.0,
        "escaped_sites": escaped_sites,
        "gate_cmd": list(gate_cmd),
        "seed": seed,
    }


_USAGE = "usage: python -m metafactory.verify.mutation <target-file> <python|kotlin> <limit> <seed> -- <gate_cmd...>"


def main(argv: list[str]) -> int:
    """`argv`: `<target-file> <python|kotlin> <limit> <seed> -- <gate_cmd...>`. Runs the campaign and
    prints a bounded report (one line per escaped site + totals + escape_rate) to stdout; writes no
    JSON file (stdout only — the caller redirects if it wants one). Exit 0 whenever the campaign RAN
    (an escape is a MEASUREMENT, not a tool failure); exit 2 on a usage error or a missing target."""
    if len(argv) < 5 or argv[4] != "--" or not argv[5:]:
        print(_USAGE, file=sys.stderr)
        return 2

    target_path = Path(argv[0])
    lang = argv[1]
    try:
        limit = int(argv[2])
        seed = int(argv[3])
    except ValueError:
        print(f"{_USAGE}\nerror: <limit> and <seed> must be integers", file=sys.stderr)
        return 2

    if lang == "python":
        operators = PY_OPERATORS
    elif lang == "kotlin":
        operators = KT_OPERATORS
    else:
        print(f"{_USAGE}\nerror: unknown language {lang!r} (expected python|kotlin)", file=sys.stderr)
        return 2

    if not target_path.is_file():
        print(f"{_USAGE}\nerror: target file not found: {target_path}", file=sys.stderr)
        return 2

    gate_cmd = list(argv[5:])
    result = run_campaign(target_path, gate_cmd, operators=operators, seed=seed, limit=limit)

    for site in result["escaped_sites"]:
        print(f"ESCAPED line {site['line_no']} op {site['op_index']}: {site['before']!r} -> {site['after']!r}")
    print(f"tested={result['tested']} killed={result['killed']} escaped={result['escaped']} "
          f"escape_rate={result['escape_rate']:.3f} sites_total={result['sites_total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
