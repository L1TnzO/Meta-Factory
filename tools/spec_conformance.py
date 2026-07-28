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
# The plan sabotage removes DERIVED closure: a parent stops seeing its open descendants. That is
# pathology D3 (silent completion) reintroduced on purpose — the suite must notice.
PLAN_SABOTAGE = ('\n\ndef effective_state(plan, nid):\n'
                 '    return (plan.get(nid) or {}).get("state", "missing")\n'
                 'def structure_problems(plan):\n'
                 '    return []\n')


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


def _fixture_tree() -> dict:
    """A minimal plan exercising every rule: a done leaf, an open branch, a captured residual."""
    return {
        "R": {"parent": None, "title": "root", "kind": "direction", "state": "open",
              "origin": {"session": "s1", "cause": "manual"}},
        "A": {"parent": "R", "title": "a", "kind": "increment", "state": "done",
              "evidence": ["proof:abc"], "origin": {"session": "s1", "cause": "manual"}},
        "B": {"parent": "R", "title": "b", "kind": "task", "state": "open",
              "origin": {"session": "s2", "cause": "gate_red", "ref": "gate:quality"}},
        "B1": {"parent": "B", "title": "b1", "kind": "residual", "state": "open",
               "origin": {"session": "s2", "cause": "deferral", "ref": "slot:x"}},
    }


def run_plan_suite(ns: dict) -> list[str]:
    """The conformance suite of docs/spec/15-plan-and-memory.md §9."""
    fail: list[str] = []
    need = ("effective_state", "structure_problems", "node_problems", "capture_problems",
            "next_actionable", "ancestry", "open_set")
    for fn in need:
        if not callable(ns.get(fn)):
            fail.append(f"CONF-P1: spec does not define a callable `{fn}`")
    if fail:
        return fail
    t = _fixture_tree()

    # CONF-P2 — derived closure: a parent is open while a descendant is open.
    if ns["effective_state"](t, "R") != "open":
        fail.append("CONF-P2: root must be effectively OPEN (descendants B/B1 are open)")
    if ns["effective_state"](t, "A") != "done":
        fail.append("CONF-P2: a childless done node must be effectively done")
    if ns["effective_state"](t, "B") != "open":
        fail.append("CONF-P2: a node with an open child must be effectively open")

    # CONF-P3 — D3: done over an open descendant is a structural problem.
    bad = dict(t)
    bad["R"] = dict(t["R"], state="done", evidence=["x"])
    if not ns["structure_problems"](bad):
        fail.append("CONF-P3: marking a parent done over open descendants must be flagged")
    if ns["structure_problems"](t):
        fail.append("CONF-P3: the well-formed fixture must have NO structural problem")

    # CONF-P4 — per-node law.
    for nid, node, why in (
        ("X", {"parent": None, "kind": "task", "state": "done",
               "origin": {"cause": "manual"}}, "done without evidence"),
        ("X", {"parent": None, "kind": "task", "state": "dropped",
               "origin": {"cause": "manual"}}, "dropped without a reason"),
        ("X", {"parent": None, "kind": "task", "state": "blocked",
               "origin": {"cause": "manual"}}, "blocked without a trigger"),
    ):
        if not ns["node_problems"]({nid: node}, nid):
            fail.append(f"CONF-P4: must flag a node {why}")

    # CONF-P5 — D1: declared work with no node would leak.
    if not ns["capture_problems"](t, [{"ref": "slot:y", "cause": "deferral"}]):
        fail.append("CONF-P5: undeclared-as-node work must be flagged as a leak")
    if ns["capture_problems"](t, [{"ref": "slot:x", "cause": "deferral"}]):
        fail.append("CONF-P5: work that DOES have a node must not be flagged")

    # CONF-P6 — deterministic leaf selection.
    nxt = ns["next_actionable"](t)
    if nxt != "B1":
        fail.append(f"CONF-P6: next actionable must be the open leaf B1, got {nxt!r}")

    # CONF-P7 — ancestry is root→leaf and cycle-safe.
    if ns["ancestry"](t, "B1") != ["R", "B", "B1"]:
        fail.append("CONF-P7: ancestry must read root → leaf")
    cyc = {"P": {"parent": "Q", "kind": "task", "state": "open", "origin": {"cause": "manual"}},
           "Q": {"parent": "P", "kind": "task", "state": "open", "origin": {"cause": "manual"}}}
    try:
        ns["ancestry"](cyc, "P")
        ns["structure_problems"](cyc)
    except RecursionError:
        fail.append("CONF-P7: a cyclic plan must be REPORTED, never hang or overflow")

    # CONF-P8 — the handoff projection is pure, deterministic and pointer-shaped.
    if not callable(ns.get("render_handoff")):
        fail.append("CONF-P8: spec does not define a callable `render_handoff`")
    else:
        r1, r2 = ns["render_handoff"](t, "R"), ns["render_handoff"](t, "R")
        if r1 != r2:
            fail.append("CONF-P8: the projection must be deterministic (two renders differ)")
        listed = [m.group(1) for m in
                  (re.match(r"\[.\]\s+(\S+)", ln.strip()) for ln in r1.splitlines()) if m]
        if "B1" not in listed or "B" not in listed:
            fail.append(f"CONF-P8: the projection must list the arc's open nodes, listed={listed}")
        if "A" in listed:
            fail.append("CONF-P8: a DONE node must not appear in the open projection")
        # tree order, not id order: a rendered child must FOLLOW its rendered parent immediately.
        deep = {"R": {"parent": None, "title": "r", "kind": "direction", "state": "open",
                      "origin": {"cause": "manual"}},
                "Z": {"parent": "R", "title": "z", "kind": "task", "state": "open",
                      "origin": {"cause": "manual"}},
                "Y": {"parent": "Z", "title": "y", "kind": "task", "state": "open",
                      "origin": {"cause": "manual"}},
                "M": {"parent": "R", "title": "m", "kind": "task", "state": "open",
                      "origin": {"cause": "manual"}}}
        order = [m.group(1) for m in
                 (re.match(r"\[.\]\s+(\S+)", ln.strip()) for ln in
                  ns["render_handoff"](deep, "R").splitlines()) if m]
        if order != ["R", "M", "Z", "Y"]:
            fail.append(f"CONF-P8: projection must be DEPTH-FIRST in tree order, got {order}")
        if ns["render_handoff"](t, "R") == ns["render_handoff"](
                {**t, "B1": dict(t["B1"], state="done", evidence=["e"])}, "R"):
            fail.append("CONF-P8: closing a node must change the projection")
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

    # ── the plan algebra (§15) — a marked block is NORMATIVE, so it must be executed ──
    plan_src, plan_files = extract(root, "plan")
    if not plan_src.strip():
        failures.append("CONF-P1: no `<!-- spec-impl: plan -->` block found in docs/spec/*.md")
    else:
        files = files + plan_files
        try:
            plan_ns = load_module(plan_src, False)
            if sabotage:
                exec(compile(PLAN_SABOTAGE, "<spec:plan-sabotage>", "exec"), plan_ns)
        except Exception as exc:                                  # noqa: BLE001
            failures.append(f"CONF-P1: the extracted plan algebra does not execute: {exc!r}")
        else:
            failures.extend(run_plan_suite(plan_ns))

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
          f"{len(vectors)} pin-anchored vector(s) reproduce; 14 conformance checks green (kernel + plan)")
    print(f"ARTIFACT   {SPEC_DIR}/ (blocks: {', '.join(sorted(set(files)))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
