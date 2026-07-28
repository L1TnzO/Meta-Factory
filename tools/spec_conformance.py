"""spec_conformance — proves `docs/spec/` is RECONSTRUCTION-COMPLETE for the trust kernel.

The claim under test: *a person given only `docs/spec/` can rebuild this system.* That claim is
usually unfalsifiable prose. Here it is a gate.

How: the spec carries its reference implementation inline, in fenced blocks marked

    <!-- spec-impl: kernel -->
    ```python
    ...
    ```

This runner EXTRACTS those blocks (nothing else — not the repo's source), executes them in an empty
namespace with only the standard library, and runs the conformance suite of `12-conformance.md`
against the golden vectors in `docs/spec/fixtures/`, which are anchored to committed pins.

If the spec's prose drifts from the machine, or if a block is incomplete, the vectors stop
reproducing and this gate goes red. The document cannot rot silently.

Two-sided (anti-decorative, §02.4): with SPEC_CONFORMANCE_SABOTAGE=1 the extracted source is mutated
so the digest must change. If the suite still passes under sabotage, the gate prints GATE DECORATIVO
and fails — a gate that cannot go red proves nothing.

Usage:  python3 tools/spec_conformance.py [repo_root]
        SPEC_CONFORMANCE_SABOTAGE=1 python3 tools/spec_conformance.py   # must FAIL
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SPEC_DIR = "docs/spec"
FIXTURE = "docs/spec/fixtures/proof-sha-vectors.json"
MARKER = re.compile(r"<!--\s*spec-impl:\s*([A-Za-z0-9_.-]+)\s*-->\s*\n```python\n(.*?)\n```",
                    re.DOTALL)
# The sabotage makes the digest depend on a field the real algorithm MUST exclude (a timestamp).
SABOTAGE = ('\n\n_orig_compute_proof_sha = compute_proof_sha\n'
            'def compute_proof_sha(station_id, checks):\n'
            '    return _orig_compute_proof_sha(station_id, list(checks) + [{"name": "_t", "exit": 1}])\n')


def extract(root: Path, module: str) -> tuple[str, list[str]]:
    """Concatenate every `spec-impl: <module>` block, in filename then document order."""
    parts, sources = [], []
    for md in sorted((root / SPEC_DIR).glob("*.md")):
        text = md.read_text(encoding="utf-8")
        for name, body in MARKER.findall(text):
            if name == module:
                parts.append(body)
                sources.append(md.name)
    return "\n\n".join(parts), sources


def load_module(source: str, sabotage: bool) -> dict:
    ns: dict = {"__name__": "spec_kernel"}
    exec(compile(source + (SABOTAGE if sabotage else ""), "<spec:kernel>", "exec"), ns)
    return ns


def run_suite(ns: dict, vectors: list[dict]) -> list[str]:
    """The conformance suite of docs/spec/12-conformance.md. Returns a list of failures."""
    fail: list[str] = []

    # CONF-K1 — the kernel surface exists.
    for fn in ("compute_proof_sha", "recompute_passed"):
        if not callable(ns.get(fn)):
            fail.append(f"CONF-K1: spec does not define a callable `{fn}`")
    if fail:
        return fail
    sha, passed = ns["compute_proof_sha"], ns["recompute_passed"]

    # CONF-K2 — every golden vector reproduces (the pin-anchored oracle).
    bad = 0
    for v in vectors:
        checks = [{"name": n, "exit": e} for n, e in v["checks"]]
        if sha(v["station"], checks) != v["proof_sha"]:
            bad += 1
            if bad <= 3:
                fail.append(f"CONF-K2: vector {v['origin']}:{v['station']} does not reproduce")
    if bad > 3:
        fail.append(f"CONF-K2: … and {bad - 3} more vector(s)")

    # CONF-K3 — `passed` semantics, including the no-vacuous-pass rule.
    if passed([]) is not False:
        fail.append("CONF-K3: an empty check list must NOT be 'trivially passed'")
    if passed([{"name": "a", "exit": 0}, {"name": "b", "exit": 0}]) is not True:
        fail.append("CONF-K3: all-zero exits must be passed")
    if passed([{"name": "a", "exit": 0}, {"name": "b", "exit": 1}]) is not False:
        fail.append("CONF-K3: any non-zero exit must not be passed")

    # CONF-K4 — the digest is outcome-addressed: order of checks must not matter.
    a = sha("s0", [{"name": "x", "exit": 0}, {"name": "y", "exit": 1}])
    b = sha("s0", [{"name": "y", "exit": 1}, {"name": "x", "exit": 0}])
    if a != b:
        fail.append("CONF-K4: the digest must be invariant to check ORDER (it sorts)")

    # CONF-K5 — a different exit code must change the sha (the whole point).
    if sha("s0", [{"name": "x", "exit": 0}]) == sha("s0", [{"name": "x", "exit": 1}]):
        fail.append("CONF-K5: a different exit code must produce a different sha")

    # CONF-K6 — the station id participates in the digest.
    if sha("s0", [{"name": "x", "exit": 0}]) == sha("s1", [{"name": "x", "exit": 0}]):
        fail.append("CONF-K6: the station id must participate in the digest")
    return fail


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve() if argv else Path(__file__).resolve().parents[1]
    sabotage = os.environ.get("SPEC_CONFORMANCE_SABOTAGE") == "1"

    source, files = extract(root, "kernel")
    if not source.strip():
        print("VERDICT    spec-conformance — FAIL   (exit 1)")
        print("SUMMARY    no `<!-- spec-impl: kernel -->` block found in docs/spec/*.md")
        print("NEXT       the spec must CARRY its reference implementation, not point at the repo")
        return 1
    fx = root / FIXTURE
    if not fx.exists():
        print("VERDICT    spec-conformance — FAIL   (exit 1)")
        print(f"SUMMARY    missing golden vectors: {FIXTURE}")
        print("NEXT       run `python3 tools/spec_fixture_gen.py`")
        return 1
    vectors = json.loads(fx.read_text(encoding="utf-8"))["vectors"]

    try:
        ns = load_module(source, sabotage)
    except Exception as exc:                                  # noqa: BLE001 — any error is a red
        failures = [f"CONF-K0: the extracted implementation does not execute: {exc!r}"]
    else:
        failures = run_suite(ns, vectors)

    if sabotage:
        if failures:
            print("VERDICT    spec-conformance (SABOTAGE) — PASS   (exit 0)")
            print(f"SUMMARY    the suite bit as it must: {len(failures)} failure(s) under sabotage")
            return 0
        print("VERDICT    spec-conformance (SABOTAGE) — FAIL   (exit 1)")
        print("SUMMARY    GATE DECORATIVO: the suite passed with a sabotaged digest")
        return 1

    if failures:
        print("VERDICT    spec-conformance — FAIL   (exit 1)")
        print(f"SUMMARY    {len(failures)} conformance failure(s) over {len(vectors)} golden vector(s)")
        for f in failures[:5]:
            print(f"FAILURES   {f}")
        print("NEXT       fix the reference implementation IN THE SPEC (docs/spec/), not in src/")
        return 1
    print("VERDICT    spec-conformance — PASS   (exit 0)")
    print(f"SUMMARY    kernel rebuilt from {len(files)} spec file(s); "
          f"{len(vectors)} pin-anchored vector(s) reproduce; 6 conformance checks green")
    print(f"ARTIFACT   {SPEC_DIR}/ (blocks: {', '.join(sorted(set(files)))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
